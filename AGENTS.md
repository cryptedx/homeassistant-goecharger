# Agent Instructions

## Language

- Keep source code, comments, tests, workflows, agent instructions, and
  repository-maintenance text in English.
- Localized translation files under `custom_components/goecharger/translations/`
  may use their target language.

## Versioning

- Use SemVer for this repository. The source of truth is
  `custom_components/goecharger/manifest.json`.
- Do not bump versions by hand during normal work. The `Release` workflow bumps
  `manifest.json`, updates `CHANGELOG.md`, creates `vX.Y.Z`, and publishes the
  GitHub Release after changes land on `main`.
- Use Conventional Commit subjects so the release workflow can pick the right
  bump: `fix`/`perf`/dependency scopes = patch, `feat` = minor, breaking changes
  = minor while this repo is on `0.y.z` and major after `1.0.0`.
- If commits are not conventional but files under `custom_components/goecharger/`
  changed, the workflow falls back to a patch release.
- Docs, tests, CI, comments, and agent instructions do not release unless paired
  with installable integration changes.
- Keep optional human-written release notes under `## Unreleased`; the workflow
  moves them into the next release entry. If that section is empty, it generates
  release notes from commit subjects.
- If the repository has no `vX.Y.Z` tag yet, the first workflow run bootstraps a
  GitHub Release for the current manifest version without incrementing it.

Run `python3 -m unittest discover -s tests -v` before committing.
