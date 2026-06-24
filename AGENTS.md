# Agent Instructions

## Versioning

- Use SemVer for this repository. The source of truth is
  `custom_components/goecharger/manifest.json`.
- Before every commit, decide whether the change needs a version bump. Bump in
  the same commit when installed integration behavior changes: `fix`, `feat`,
  `perf`, dependency/runtime changes, services, entity behavior, config flow, or
  user-visible translations.
- Skip the bump for docs, tests, CI, comments, and agent instructions when the
  installed integration behavior is unchanged.
- For the current `0.y.z` line: patch = backward-compatible fix, minor =
  backward-compatible feature or breaking user-visible change. Mark breaking
  changes clearly in `CHANGELOG.md`. Use major only when declaring `1.0.0+`
  stability.
- Every version bump must update both `manifest.json` and `CHANGELOG.md`.
- Release tags use `vX.Y.Z` and should point at the commit containing the same
  manifest version.

Run `python3 -m unittest discover -s tests -v` before committing.
