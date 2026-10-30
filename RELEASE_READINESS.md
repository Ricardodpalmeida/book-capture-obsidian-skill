# Release checks

For the current source, run `sh scripts/run_ci_local.sh`: unit tests, six script self-checks and the privacy/secret scan. Inspect the diff and match README/configuration to the behavior. The historical v1.0.0 report remains in Git history.

Build with `sh scripts/package_skill_local.sh --with-security-scan`. Verify the archive contains SKILL.md, scripts, references, templates, requirements and license; exclude caches, credentials and personal inputs.

After an authorized release, verify the exact public version and downloadable package. An accepted upload or pending scan is not a published release. Keep the previous available version until the new package is usable.

Photo extraction additionally requires the selected barcode/OCR runtime. Unit tests do not prove a user's vault, Google project quota or installed OCR environment works; report those only when exercised.
