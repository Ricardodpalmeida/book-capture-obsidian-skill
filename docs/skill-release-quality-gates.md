# Skill Release Quality Gates

Use this checklist before marking a skill release as READY or RELEASED.

## 1) Version discipline
- [ ] If any packaged content changed after a published version, bump version.
- [ ] Never replace or patch assets under an already published version.

## 2) Build integrity
- [ ] Build from a clean working tree.
- [ ] Build from the exact tagged commit intended for release.
- [ ] Generate `.skill.tgz` and `.sha256` for the release artifact.

## 3) Repo, GitHub, ClawHub parity
- [ ] Record the tag and commit SHA.
- [ ] Verify GitHub release asset digest matches local `.sha256`.
- [ ] Verify ClawHub latest version matches intended version.
- [ ] Verify ClawHub `inspect --files` hashes match tagged repo and packaged files for critical files (`SKILL.md`, scripts, references).

## 4) Packaged instruction validation
- [ ] Open `SKILL.md` from the packaged artifact and validate commands.
- [ ] Ensure no repo-root-only commands are referenced.
- [ ] Ensure required scripts/references exist inside the package.

## 5) Release readiness gate
- [ ] Update `RELEASE_READINESS.md` with exact published version and artifact IDs.
- [ ] Mark READY or RELEASED only after all checks above pass.
- [ ] If any check fails, stop release declaration and cut a corrective new version.
