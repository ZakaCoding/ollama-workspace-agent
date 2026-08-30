# Release Guide

This document describes how to cut a new release of OwA.

## Prerequisites

- Push access to the `main` branch
- `PYPI_API_TOKEN` secret configured in the GitHub repository settings

## Steps

### 1. Bump the version

Update `version` in `pyproject.toml`:

```toml
version = "0.4.0"
```

### 2. Update the changelog

In `CHANGELOG.md`, rename `[Unreleased]` to the new version with today's date:

```md
## [0.4.0] - 2026-09-01
```

Add a fresh empty `[Unreleased]` section above it:

```md
## [Unreleased]

## [0.4.0] - 2026-09-01
```

### 3. Commit and push

```bash
git add pyproject.toml CHANGELOG.md
git commit -m "chore: release v0.4.0"
git push
```

### 4. Tag and push

```bash
git tag v0.4.0
git push origin v0.4.0
```

This triggers the GitHub Actions publish workflow which builds the package and uploads it to PyPI automatically.

## Notes

- The tag name must match the version in `pyproject.toml` (e.g. tag `v0.4.0` → version `0.4.0`).
- PyPI will reject a publish if the version already exists — always bump before tagging.
- The GitHub Release page is created automatically by the workflow with a link to the changelog.
