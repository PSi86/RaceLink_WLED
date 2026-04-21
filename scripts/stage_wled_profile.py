"""CLI entrypoints for staging RaceLink_WLED release profiles into WLED."""

from __future__ import annotations

import argparse
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
        help="Rename built WLED artifacts into RaceLink release assets.",
    )
    stage_assets.add_argument("--profile", required=True, type=Path)
    stage_assets.add_argument("--release-dir", required=True, type=Path)
    stage_assets.add_argument("--dist-dir", required=True, type=Path)
    stage_assets.add_argument("--release-version", required=True)
    stage_assets.add_argument("--wled-ref", required=True)

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
    staged = stage_release_assets(
        profile_path=args.profile.resolve(),
        release_dir=args.release_dir.resolve(),
        dist_dir=args.dist_dir.resolve(),
        release_version=args.release_version,
        wled_ref=args.wled_ref,
    )
    for path in staged:
        sys.stdout.write(f"{path}\n")
    return 0


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    if args.command == "stage-profile":
        return _run_stage_profile(args)
    if args.command == "stage-assets":
        return _run_stage_assets(args)
    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
