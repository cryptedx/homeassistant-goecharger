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

## Documentation

- Keep `README.md` updated for every user-facing change (new entities,
  discovery flow changes, new config options, diagnostics, or behavior changes).
- If a change affects integration behavior or setup, update `README.md` in the
  same task before merging.

## Documentation Checklist

- [ ] `README.md` reflects behavior/feature changes introduced in this task.
- [ ] Setup or behavior docs mention any new config fields or options.
- [ ] Tests required for changed logic were run before committing.
- [ ] Translation updates were made where user-facing text changed.
- [ ] Release-impacting changes are covered by a conventional commit type.

Run `python3 -m unittest discover -s tests -v` before committing.
