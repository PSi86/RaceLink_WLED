"""The pinned WLED sources a RaceLink firmware image is built from.

``wled_source.json`` names the upstream tag and the pull requests applied on
top of it. Both workflows read it, and that is the whole point: with the ref
resolved fresh on every run, the compile-only build on a pull request and the
release built weeks later could rest on entirely different upstream trees, and
neither would say so. A patch list that lives only in a ``workflow_dispatch``
input has the same problem from the other side -- the rehearsal never carries
it, and a release carries it only if whoever pressed the button remembered to
type it.

Both remain overridable per run. The inputs win when set; the sentinels below
are how a run says "ignore the pin" explicitly rather than by leaving a field
blank, which is indistinguishable from not having thought about it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PIN_FILENAME = "wled_source.json"

# Asking for the newest published upstream release instead of the pinned tag.
LATEST_REF = "latest"
# Asking for a stock build of that tag, with none of the pinned patches.
NO_PATCHES = "none"

# "notes" is prose for whoever opens the file next -- JSON has nowhere else to
# record *why* a pull request is pinned. Everything else is a typo.
_KNOWN_KEYS = frozenset({"ref", "patch_prs", "notes"})


@dataclass(frozen=True)
class WledSource:
    """The pinned upstream ref and patch list, as the CLIs take them."""

    ref: str
    patch_prs: str  # comma-separated, in application order; "" for none


def source_pin_path(repo_root: Path | None = None) -> Path:
    return (repo_root or REPO_ROOT) / SOURCE_PIN_FILENAME


def parse_source_pin(payload: object) -> WledSource:
    """Validate a decoded ``wled_source.json`` and normalise it for the CLIs."""
    if not isinstance(payload, dict):
        raise ValueError(f"{SOURCE_PIN_FILENAME} must contain a JSON object")

    unknown = sorted(set(payload) - _KNOWN_KEYS)
    if unknown:
        raise ValueError(
            f"{SOURCE_PIN_FILENAME}: unknown key(s) {', '.join(unknown)}. "
            f"Known keys: {', '.join(sorted(_KNOWN_KEYS))}."
        )

    ref = payload.get("ref")
    if not isinstance(ref, str) or not ref.strip():
        raise ValueError(
            f"{SOURCE_PIN_FILENAME}: 'ref' must be a wled/WLED tag or '{LATEST_REF}'"
        )

    raw_prs = payload.get("patch_prs", [])
    if not isinstance(raw_prs, list):
        raise ValueError(f"{SOURCE_PIN_FILENAME}: 'patch_prs' must be a list of numbers")

    numbers: list[int] = []
    for entry in raw_prs:
        # bool is an int subclass, and `true` in this list is a mistake, not a
        # pull request number.
        if isinstance(entry, bool) or not isinstance(entry, int) or entry <= 0:
            raise ValueError(
                f"{SOURCE_PIN_FILENAME}: {entry!r} is not a pull request number"
            )
        numbers.append(entry)

    return WledSource(ref=ref.strip(), patch_prs=",".join(str(n) for n in numbers))


def load_source_pin(path: Path | None = None) -> WledSource:
    """Read and validate the pin file."""
    pin_path = path or source_pin_path()
    try:
        payload = json.loads(pin_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise FileNotFoundError(
            f"Missing {pin_path}. Both workflows build from it; see its 'notes'."
        ) from error
    except json.JSONDecodeError as error:
        raise ValueError(f"{pin_path} is not valid JSON: {error}") from error
    return parse_source_pin(payload)
