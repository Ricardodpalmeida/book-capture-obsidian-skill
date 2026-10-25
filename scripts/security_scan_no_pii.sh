#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
TARGET_DIR="$ROOT_DIR/skill/book-capture-obsidian"

if [ ! -d "$TARGET_DIR" ]; then
    echo "ERROR: target directory not found: $TARGET_DIR" >&2
    exit 2
fi

TMP_MATCHES=$(mktemp "${TMPDIR:-/tmp}/book_capture_pii_scan.XXXXXX")
cleanup() {
    rm -f "$TMP_MATCHES"
}
trap cleanup EXIT HUP INT TERM

FAIL_COUNT=0

run_grep() {
    regex=$1
    find "$TARGET_DIR" -type f \
        \( \
            -name '*.md' -o \
            -name '*.txt' -o \
            -name '*.py' -o \
            -name '*.sh' -o \
            -name '*.json' -o \
            -name '*.yaml' -o \
            -name '*.yml' -o \
            -name '*.toml' -o \
            -name '*.ini' -o \
            -name '*.cfg' -o \
            -name '*.env' -o \
            -name '*.csv' \
        \) \
        -exec grep -nHE "$regex" {} +
}

scan_pattern() {
    label=$1
    regex=$2
    fail_condition=$3

    : > "$TMP_MATCHES"

    if run_grep "$regex" > "$TMP_MATCHES" 2>/dev/null; then
        echo "[FAIL] $label"
        echo "       Fail condition: $fail_condition"
        cat "$TMP_MATCHES"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        return 0
    else
        rc=$?
        if [ "$rc" -eq 1 ]; then
            echo "[OK]   $label"
            return 0
        fi

        echo "[ERROR] scan execution failed for pattern: $label" >&2
        exit 2
    fi
}

echo "PII/security scan target: $TARGET_DIR"
echo "Pass criteria: zero matches across all fail conditions."

scan_pattern \
    "Hardcoded local user paths" \
    '(/home/[A-Za-z0-9._-]+/|/Users/[A-Za-z0-9._-]+/|[A-Za-z]:\\Users\\[A-Za-z0-9._-]+\\)' \
    "Any absolute path with a concrete local username"

scan_pattern \
    "Host-specific filesystem paths" \
    '(/opt/[A-Za-z0-9._/-]+|/srv/[A-Za-z0-9._/-]+|/mnt/[A-Za-z0-9._/-]+|/media/[A-Za-z0-9._/-]+|/private/[A-Za-z0-9._/-]+|/Volumes/[A-Za-z0-9._/-]+)' \
    "Any hardcoded machine-local absolute path"

scan_pattern \
    "Email addresses" \
    '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' \
    "Any email-like address literal"

scan_pattern \
    "Phone numbers" \
    '(\+[0-9]{8,15}|[0-9]{3}[[:space:]-][0-9]{3}[[:space:]-][0-9]{3})' \
    "Any international phone number or grouped 9-digit phone-like literal"

scan_pattern \
    "Localhost and private-network host assumptions" \
    '(localhost|127\.0\.0\.1|0\.0\.0\.0|::1|\.local\b|10\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}|192\.168\.[0-9]{1,3}\.[0-9]{1,3}|172\.(1[6-9]|2[0-9]|3[0-1])\.[0-9]{1,3}\.[0-9]{1,3})' \
    "Any local host/IP reference that couples behavior to a specific environment"

scan_pattern \
    "Token signatures (GitHub/OpenAI/AWS/Slack/GCP/HF/JWT)" \
    '(gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{35}|hf_[A-Za-z0-9]{20,}|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})' \
    "Any value matching known API key/access token formats"

scan_pattern \
    "Private key material" \
    '-----BEGIN ([A-Z ]+ )?PRIVATE KEY-----|ssh-rsa [A-Za-z0-9+/=]{50,}|ssh-ed25519 [A-Za-z0-9+/=]{50,}' \
    "Any private key header or long SSH key blob"

scan_pattern \
    "Generic secret assignments" \
    '([Tt][Oo][Kk][Ee][Nn]|[Ss][Ee][Cc][Rr][Ee][Tt]|[Aa][Pp][Ii]_?[Kk][Ee][Yy]|[Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd])[[:space:]]*[:=][[:space:]]*['"'"']?[A-Za-z0-9._-]{16,}['"'"']?' \
    "Any hardcoded credential-like assignment with a long value"

if [ "$FAIL_COUNT" -gt 0 ]; then
    echo "PII/security scan FAILED: $FAIL_COUNT failing category(ies)." >&2
    echo "Fail policy: any single [FAIL] category returns exit code 1." >&2
    exit 1
fi

echo "PII/security scan passed: no matches found."
