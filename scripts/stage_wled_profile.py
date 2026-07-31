"""CLI entrypoints for staging RaceLink_WLED release profiles into WLED."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.release_profiles import (
    parse_profile_environments,
    stage_local_usermod,
    stage_profile_override,
    stage_release_assets,
)
from scripts.release_staging import write_release_index

PRODUCT = "RaceLink_WLED"

# Per-profile manifest fragments, assembled by `finalize` and removed again.
FRAGMENT_DIR = ".staging"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Stage RaceLink_WLED build profiles and artifacts for GitHub releases.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    stage_profile = subparsers.add_parser(
        "stage-profile",
        help="Copy the local usermod and selected profile into a WLED checkout.",
    )
    stage_profile.add_argument("--repo-root", required=True, type=Path)
    stage_profile.add_argument("--wled-dir", required=True, type=Path)
    stage_profile.add_argument("--profile", required=True, type=Path)

    stage_assets = subparsers.add_parser(
        "stage-assets",
        help="Stage one profile's build output as RaceLink release assets.",
    )
    stage_assets.add_argument("--profile", required=True, type=Path)
    stage_assets.add_argument(
        "--build-root",
        required=True,
        type=Path,
        help="PlatformIO build directory of the WLED checkout (.pio/build).",
    )
    stage_assets.add_argument("--dist-dir", required=True, type=Path)
    stage_assets.add_argument("--release-version", required=True)
    stage_assets.add_argument(
        "--metadata",
        required=True,
        type=Path,
        help="JSON from `pio project metadata`, collected while this profile is staged.",
    )

    # The WLED ref is a release-level fact, recorded once in the sidecar --
    # staging a profile does not need to know it.
    finalize = subparsers.add_parser(
        "finalize",
        help="Write the assets.json sidecar.",
    )
    finalize.add_argument("--dist-dir", required=True, type=Path)
    finalize.add_argument("--release-version", required=True)
    finalize.add_argument("--wled-ref", required=True)

    return parser


def _run_stage_profile(args: argparse.Namespace) -> int:
    stage_local_usermod(repo_root=args.repo_root.resolve(), wled_dir=args.wled_dir.resolve())
    stage_profile_override(
        profile_path=args.profile.resolve(),
        wled_dir=args.wled_dir.resolve(),
    )
    for env in parse_profile_environments(args.profile.resolve()):
        sys.stdout.write(f"{env.name}\n")
    return 0


def _run_stage_assets(args: argparse.Namespace) -> int:
    dist_dir = args.dist_dir.resolve()
    environments = stage_release_assets(
        profile_path=args.profile.resolve(),
        build_root=args.build_root.resolve(),
        dist_dir=dist_dir,
        release_version=args.release_version,
        metadata=json.loads(args.metadata.resolve().read_text(encoding="utf-8")),
    )

    # Each profile is built and staged in turn, then its override file is
    # overwritten by the next one -- so the sidecar is accumulated on disk
    # rather than held in memory, and assembled by `finalize` at the end.
    fragments = dist_dir / FRAGMENT_DIR
    fragments.mkdir(parents=True, exist_ok=True)
    (fragments / f"{args.profile.stem}.json").write_text(
        json.dumps(environments, indent=2) + "\n", encoding="utf-8"
    )

    for environment in environments:
        for asset in environment["assets"]:
            sys.stdout.write(f"{asset['file']}\n")
    return 0


def _run_finalize(args: argparse.Namespace) -> int:
    dist_dir = args.dist_dir.resolve()
    fragments = sorted((dist_dir / FRAGMENT_DIR).glob("*.json"))
    if not fragments:
        raise SystemExit(f"No staged profiles found in {dist_dir / FRAGMENT_DIR}")

    environments = [
        environment
        for fragment in fragments
        for environment in json.loads(fragment.read_text(encoding="utf-8"))
    ]

    manifest_path = write_release_index(
        dist_dir=dist_dir,
        product=PRODUCT,
        version=args.release_version,
        environments=environments,
        extra={"wled_ref": args.wled_ref},
    )

    # The fragments are scaffolding, not release assets.
    shutil.rmtree(dist_dir / FRAGMENT_DIR)

    sys.stdout.write(f"{manifest_path.name}\n")
    return 0


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    if args.command == "stage-profile":
        return _run_stage_profile(args)
    if args.command == "stage-assets":
        return _run_stage_assets(args)
    if args.command == "finalize":
        return _run_finalize(args)
    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
