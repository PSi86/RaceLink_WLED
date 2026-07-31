"""Helpers for staging RaceLink_WLED release profiles into a WLED checkout."""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from scripts.release_staging import stage_environment

# The profiles a release actually builds and publishes.
#
# RaceLink_Node_v7_classic_esp32_emac is committed but deliberately absent:
# its internal-EMAC Ethernet support is still in bring-up and has never been
# released. The omission is intentional, not an oversight — add it here once
# Ethernet ships, and note that it is the first classic ESP32 in the set, so
# its bootloader sits at 0x1000 rather than 0x0 (release_staging.py cross-
# checks that and will refuse to stage it if the offsets disagree).
SHIPPING_PROFILE_FILENAMES = (
    "RaceLink_Node_v1_c3_ct62.platformio_override.ini",
    "RaceLink_Node_v3_s2_llcc68.platformio_override.ini",
    "RaceLink_Node_v3_s2_llcc68_epaper.platformio_override.ini",
    "RaceLink_Node_v4_s3_llcc68.platformio_override.ini",
    "RaceLink_Node_v5_s3_eth.platformio_override.ini",
    "RaceLink_Node_v6_s3_heltec_wpaper.platformio_override.ini",
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


def stage_release_assets(
    *,
    profile_path: Path,
    build_root: Path,
    dist_dir: Path,
    release_version: str,
    metadata: dict,
) -> list[dict]:
    """Stage every asset for one profile's environments.

    Returns a sidecar entry per environment; the caller accumulates them across
    profiles and writes the release index once.

    The upstream WLED release a build wraps is no longer part of the filenames.
    It is recorded once per release as ``wled_ref`` in the assets.json sidecar,
    which is where every consumer already read it from -- repeating it in each
    of thirty filenames only made them longer.

    Note the source: PlatformIO's build directory, not WLED's
    ``build_output/release``. Both hold the same application image, but the
    build directory also holds the bootloader and the partition table that the
    factory image needs, and it is what the flash-image offsets in PlatformIO's
    metadata point at.
    """
    dist_dir.mkdir(parents=True, exist_ok=True)

    return [
        stage_environment(
            env=env.name,
            version=release_version,
            build_dir=build_root / env.name,
            dist_dir=dist_dir,
            metadata=metadata,
        )
        for env in parse_profile_environments(profile_path)
    ]
