"""Resolve the WLED source ref to use for RaceLink_WLED release builds.

The ref comes from ``wled_source.json`` unless a run overrides it. Resolving
the newest upstream release instead is still available -- pin ``"latest"``, or
pass it as the workflow input -- but it is now something a run asks for rather
than what happens by default. An unpinned ref means the firmware's foundation
can change with no commit in this repository, and the change WLED 17 brings is
not a small one: the shared esp32/esp32s2/esp32s3/esp32c3 build sections move
from ESP-IDF 4.4 to 5.5, and every RaceLink profile inherits from them.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.wled_source import LATEST_REF, load_source_pin

WLED_REPOSITORY = "wled/WLED"
DEFAULT_USER_AGENT = "RaceLink_WLED-release-resolver"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resolve the WLED ref to use for a RaceLink_WLED release.",
    )
    parser.add_argument(
        "--wled-ref",
        default="",
        help=(
            "Explicit WLED tag/ref override. If empty, use the ref pinned in "
            f"wled_source.json; '{LATEST_REF}' resolves the newest published "
            "WLED release instead."
        ),
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


def fetch_latest_release_ref() -> str:
    """Return the tag of the newest published upstream release."""
    payload = _read_json(f"https://api.github.com/repos/{WLED_REPOSITORY}/releases/latest")
    if not isinstance(payload, dict) or not payload.get("tag_name"):
        raise RuntimeError("GitHub latest-release API returned an unexpected WLED payload.")
    return str(payload["tag_name"]).strip()


def resolve_wled_ref(explicit_ref: str, *, pinned_ref: str | None = None) -> str:
    """Resolve the ref from the input, the pin, or the latest upstream release."""
    # An empty input is not a request for anything -- it is the workflow field
    # nobody filled in -- so it falls through to the pin.
    ref = str(explicit_ref).strip()
    if not ref:
        ref = pinned_ref if pinned_ref is not None else load_source_pin().ref

    if ref.strip().lower() == LATEST_REF:
        return fetch_latest_release_ref()
    return ref.strip()


def main() -> int:
    args = _parse_args()
    # The repository is a constant, so answering it must not depend on -- or
    # pay for -- resolving a ref. The workflows ask for both, one call each.
    if args.print_field == "repository":
        sys.stdout.write(f"{WLED_REPOSITORY}\n")
        return 0
    sys.stdout.write(f"{resolve_wled_ref(args.wled_ref)}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
