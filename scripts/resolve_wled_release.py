"""Resolve the WLED source ref to use for RaceLink_WLED release builds."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request

WLED_REPOSITORY = "wled/WLED"
DEFAULT_USER_AGENT = "RaceLink_WLED-release-resolver"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resolve the WLED ref to use for a RaceLink_WLED release.",
    )
    parser.add_argument(
        "--wled-ref",
        default="",
        help="Explicit WLED tag/ref override. If empty, use the latest published WLED release.",
    )
    parser.add_argument(
        "--print",
        choices=("ref", "repository"),
        default="ref",
        dest="print_field",
        help="Requested output field.",
    )
    return parser.parse_args()


def _read_json(url: str) -> object:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": DEFAULT_USER_AGENT,
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def resolve_wled_ref(explicit_ref: str) -> str:
    """Resolve the WLED ref from input or the latest GitHub release."""
    normalized = str(explicit_ref).strip()
    if normalized:
        return normalized

    payload = _read_json(f"https://api.github.com/repos/{WLED_REPOSITORY}/releases/latest")
    if not isinstance(payload, dict) or not payload.get("tag_name"):
        raise RuntimeError("GitHub latest-release API returned an unexpected WLED payload.")
    return str(payload["tag_name"]).strip()


def main() -> int:
    args = _parse_args()
    values = {
        "repository": WLED_REPOSITORY,
        "ref": resolve_wled_ref(args.wled_ref),
    }
    sys.stdout.write(f"{values[args.print_field]}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
