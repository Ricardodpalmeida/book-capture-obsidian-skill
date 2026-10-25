# Security Notes

## Scope
Local security checks are implemented to block personal data leaks and host-specific assumptions in the skill package.

- Target path: `skill/book-capture-obsidian/`
- Scanner: `scripts/security_scan_no_pii.sh`
- Scanned file types: `md, txt, py, sh, json, yaml, yml, toml, ini, cfg, env, csv`

## Detection categories and fail conditions
Each category has a strict fail condition. Any single match fails the scan.

1. **Hardcoded local user paths**
   - Detects: `/home/<user>/...`, `/Users/<user>/...`, `C:\Users\<user>\...`
   - Fail condition: any absolute path containing a concrete local username

2. **Host-specific filesystem paths**
   - Detects absolute paths under machine-local roots like `/opt`, `/srv`, `/mnt`, `/media`, `/private`, `/Volumes`
   - Fail condition: any hardcoded machine-local absolute path

3. **Email addresses**
   - Fail condition: any email-like literal

4. **Phone numbers**
   - Detects international `+` format and grouped 9-digit phone-like format
   - Fail condition: any phone-like literal

5. **Localhost/private-network host assumptions**
   - Detects: `localhost`, loopback addresses, `.local` hostnames, RFC1918 private IP ranges
   - Fail condition: any local host/IP reference that couples behavior to a specific environment

6. **Token signatures**
   - Detects common formats for GitHub, OpenAI, AWS, Slack, GCP, Hugging Face, and JWT-like secrets
   - Fail condition: any value matching known API key/access token signatures

7. **Private key material**
   - Detects private key headers and long SSH key blobs
   - Fail condition: any private key-like material

8. **Generic secret assignments**
   - Detects long value assignments tied to `token`, `secret`, `api_key`, `password`
   - Fail condition: any hardcoded credential-like assignment with long value

## How to run
Run the security scan only:

```sh
sh scripts/security_scan_no_pii.sh
```

Run local CI checks (tests + security scan):

```sh
sh scripts/run_ci_local.sh
```

## Exit codes
- `0`: no findings
- `1`: one or more fail conditions matched
- `2`: scanner execution/tooling error

## Guardrails
- Never commit personal contact details or personal filesystem paths.
- Never commit real credentials, secrets, or key material.
- Keep examples and tests deterministic and anonymized.
