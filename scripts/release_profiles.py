"""Helpers for staging RaceLink_WLED release profiles into a WLED checkout."""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

SHIPPING_PROFILE_FILENAMES = (
    "RaceLink_Node_v1_c3_ct62.platformio_override.ini",
    "RaceLink_Node_v3_s2_llcc68.platformio_override.ini",
    "RaceLink_Node_v3_s2_llcc68_epaper.platformio_override.ini",
    "RaceLink_Node_v4_s3_llcc68.platformio_override.ini",
)

USERMOD_LINE_PATTERN = re.compile(r"^(?P<prefix>\s*custom_usermods\s*=\s*)(?P<value>.*)$")
ENV_HEADER_PATTERN = re.compile(r"^\[env:(?P<name>[^\]]+)\]\s*$")
RELEASE_NAME_PATTERN = re.compile(r'-D\s+WLED_RELEASE_NAME=\\"(?P<name>[^"]+)\\"')


@dataclass(frozen=True)
class ProfileEnvironment:
    """Release-relevant environment metadata extracted from one profile file."""

    name: str
    release_name: str


def iter_shipping_profiles(profiles_dir: Path) -> list[Path]:
    """Return the known shipping release profiles in stable order."""
    paths: list[Path] = []
    for filename in SHIPPING_PROFILE_FILENAMES:
        path = profiles_dir / filename
        if not path.is_file():
            raise FileNotFoundError(f"Missing shipping profile: {path}")
        paths.append(path)
    return paths


def is_release_profile(path: Path) -> bool:
    """Return whether the file is part of the release set."""
    if path.name in SHIPPING_PROFILE_FILENAMES:
        return True
    if path.name == "all_profiles.platformio_override.ini":
        return False
    if path.name.startswith("bak_"):
        return False
    return False


def rewrite_custom_usermods(source: str) -> str:
    """Rewrite all custom_usermods directives to the local staging layout."""
    lines = []
    for line in source.splitlines():
        match = USERMOD_LINE_PATTERN.match(line)
        if match:
            line = f"{match.group('prefix')}Battery RaceLink_WLED"
        lines.append(line)
    return "\n".join(lines) + ("\n" if source.endswith("\n") else "\n")


def parse_profile_environments(profile_path: Path) -> list[ProfileEnvironment]:
    """Extract env names and WLED release names from a profile file."""
    environments: list[ProfileEnvironment] = []
    current_env: str | None = None
    current_release_name: str | None = None

    for raw_line in profile_path.read_text(encoding="utf-8").splitlines():
        env_match = ENV_HEADER_PATTERN.match(raw_line.strip())
        if env_match:
            if current_env is not None:
                if not current_release_name:
                    raise ValueError(
                        f"Missing WLED_RELEASE_NAME for env {current_env} in {profile_path}"
                    )
                environments.append(
                    ProfileEnvironment(
                        name=current_env,
                        release_name=current_release_name,
                    )
                )
            current_env = env_match.group("name").strip()
            current_release_name = None
            continue

        if current_env is None:
            continue

        release_match = RELEASE_NAME_PATTERN.search(raw_line)
        if release_match:
            current_release_name = release_match.group("name").strip()

    if current_env is not None:
        if not current_release_name:
            raise ValueError(
                f"Missing WLED_RELEASE_NAME for env {current_env} in {profile_path}"
            )
        environments.append(
            ProfileEnvironment(
                name=current_env,
                release_name=current_release_name,
            )
        )

    return environments


def stage_profile_override(*, profile_path: Path, wled_dir: Path) -> Path:
    """Stage one profile as platformio_override.ini inside a WLED checkout."""
    rewritten = rewrite_custom_usermods(profile_path.read_text(encoding="utf-8"))
    target = wled_dir / "platformio_override.ini"
    target.write_text(rewritten, encoding="utf-8")
    return target


def stage_local_usermod(*, repo_root: Path, wled_dir: Path) -> Path:
    """Copy the local RaceLink_WLED usermod payload into the WLED usermods folder."""
    target_dir = wled_dir / "usermods" / "RaceLink_WLED"
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    for path in repo_root.iterdir():
        if not path.is_file():
            continue
        if path.name != "library.json" and path.suffix not in {".cpp", ".h"}:
            continue
        shutil.copy2(path, target_dir / path.name)

    return target_dir


def sanitize_ref_for_filename(raw_ref: str) -> str:
    """Convert a WLED ref into a stable filename fragment."""
    value = re.sub(r"[^0-9A-Za-z._-]+", "-", str(raw_ref).strip())
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "unknown-ref"


def stage_release_assets(
    *,
    profile_path: Path,
    release_dir: Path,
    dist_dir: Path,
    release_version: str,
    wled_ref: str,
) -> list[Path]:
    """Rename WLED output artifacts to stable RaceLink release filenames."""
    dist_dir.mkdir(parents=True, exist_ok=True)
    staged_paths: list[Path] = []
    ref_fragment = sanitize_ref_for_filename(wled_ref)

    for env in parse_profile_environments(profile_path):
        candidates = sorted(release_dir.glob(f"WLED_*_{env.release_name}.bin*"))
        if not candidates:
            raise FileNotFoundError(
                f"Could not find build_output/release artifact for {env.release_name}"
            )

        for candidate in candidates:
            suffix = "".join(candidate.suffixes)
            target = dist_dir / (
                f"RaceLink_WLED-{release_version}-{env.name}-{ref_fragment}{suffix}"
            )
            shutil.copy2(candidate, target)
            staged_paths.append(target)

    return staged_paths
