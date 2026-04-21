"""Update the canonical RaceLink_WLED release version for a release."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

VERSION_PATTERN = re.compile(
    r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
    r"(?P<suffix>[-+][0-9A-Za-z.-]+)?$"
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update version.json with a RaceLink_WLED release version.",
    )
    parser.add_argument(
        "--version-file",
        default=Path("version.json"),
        type=Path,
        help="Path to the canonical release version JSON file.",
    )
    parser.add_argument(
        "--version",
        default="",
        help="Explicit release version. If omitted, increment the current patch version.",
    )
    return parser.parse_args()


def _normalize_version(version: str) -> str:
    normalized = str(version).strip().removeprefix("v")
    if not normalized:
        return normalized
    if not VERSION_PATTERN.fullmatch(normalized):
        raise ValueError(
            "Version must look like semantic versioning, for example 0.1.3 or 0.1.3-rc1"
        )
    return normalized


def _increment_version(current_version: str) -> str:
    match = VERSION_PATTERN.fullmatch(current_version)
    if match is None:
        raise ValueError(f"Current release version is not valid semver: {current_version}")

    major = int(match.group("major"))
    minor = int(match.group("minor"))
    patch = int(match.group("patch")) + 1
    suffix = match.group("suffix") or ""
    return f"{major}.{minor}.{patch}{suffix}"


def bump_release_version(*, version_file: Path, version: str) -> str:
    """Write an explicit or auto-incremented version into version.json."""
    payload = json.loads(version_file.read_text(encoding="utf-8"))
    current_version = str(payload["version"]).strip().removeprefix("v")
    target_version = _normalize_version(version) or _increment_version(current_version)
    payload["version"] = target_version
    version_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return target_version


def main() -> int:
    args = _parse_args()
    version = bump_release_version(
        version_file=args.version_file.resolve(),
        version=args.version,
    )
    sys.stdout.write(f"{version}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
