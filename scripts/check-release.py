"""Verify that a release tag, package version, and changelog agree."""
import re
import sys
import tomllib
from pathlib import Path


def check_release(root: Path, tag: str) -> str:
    version = tomllib.loads((root / 'pyproject.toml').read_text())['project']['version']
    if tag != f'v{version}':
        raise ValueError(f'Tag {tag!r} does not match package version v{version}')
    changelog = (root / 'CHANGELOG.md').read_text()
    if not re.search(r'^## \[' + re.escape(version) + r'\] - \d{4}-\d{2}-\d{2}$', changelog, re.MULTILINE):
        raise ValueError(f'CHANGELOG.md has no dated entry for {version}')
    return version


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit('Usage: python scripts/check-release.py vVERSION')
    try:
        print('Release metadata valid:', check_release(Path(__file__).resolve().parents[1], sys.argv[1]))
    except ValueError as exc:
        sys.exit(str(exc))
