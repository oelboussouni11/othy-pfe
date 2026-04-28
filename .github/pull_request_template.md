<!--
Title format: <type>(<scope>): <imperative summary>
Examples:
  feat(auth): add refresh token rotation
  fix(crawler): handle redirect loops
-->

## Summary
<!-- 1-3 bullets: what changed and why -->
-

## Phase / context
<!-- Which BUILD.md phase or issue does this address? -->
- BUILD.md phase:
- Closes #

## Test plan
<!-- What did you actually test? Click-through, command, fixture? -->
- [ ]
- [ ]

## Screenshots / logs
<!-- For UI changes, attach before/after. For backend, paste curl output or test summary. -->

## Checklist
- [ ] Conventional commit title
- [ ] Branched from `dev`, targeting `dev`
- [ ] Tests added or updated
- [ ] `make check` passes locally
- [ ] No secrets, no `console.log`, no commented-out code
- [ ] Migration includes `downgrade()` if a DB change
- [ ] BUILD.md / ARCHITECTURE.md updated if scope or design shifted
