"""Apply upstream WLED pull requests on top of a checked-out WLED ref.

A RaceLink build sometimes needs an upstream change that is proposed but not
yet released -- a fix to a usermod the profiles enable, say. The ref itself
cannot express that: ``refs/pull/<n>/head`` builds the *pull request's* base,
which is whatever ``main`` looked like when it was opened, not the WLED release
this firmware is meant to wrap. Between v16.0.1 and main that was 311 commits
and 115 files, so the two are not interchangeable.

So the ref stays a released tag and the pull requests are applied on top of it.
``git apply`` is deliberately strict here: a patch that no longer fits the
release it is being applied to fails the build rather than being fuzzed into
place.

The other half of the job is honesty about what was built. The ref string this
prints is what ``finalize`` records as ``wled_ref`` in the assets sidecar, and a
patched tree that reports a bare ``v16.0.1`` would claim to be a stock release
build. :func:`label_ref` appends the pull requests so the sidecar names every
source that went into the image.

With no pull requests to apply this is a pass-through: the ref is echoed
unchanged and the tree is untouched, so the workflows need no conditional
around it.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

WLED_REPOSITORY = "wled/WLED"
DEFAULT_USER_AGENT = "RaceLink_WLED-release-resolver"

# GitHub serves the unified diff of a pull request from the pull endpoint when
# asked for it by media type. The .diff URL on github.com would do as well, but
# it answers with a redirect to a signed host that ignores the token, and this
# has to keep working for a private fork.
DIFF_MEDIA_TYPE = "application/vnd.github.v3.diff"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Apply wled/WLED pull requests to a checked-out WLED tree.",
    )
    parser.add_argument(
        "--wled-dir",
        required=True,
        type=Path,
        help="The WLED checkout to patch.",
    )
    parser.add_argument(
        "--wled-ref",
        required=True,
        help="The ref that checkout is on, used to build the recorded ref label.",
    )
    parser.add_argument(
        "--patch-prs",
        default="",
        help="Pull requests to apply, separated by commas or whitespace. May be empty.",
    )
    return parser.parse_args()


def parse_pr_numbers(raw: str) -> list[int]:
    """Parse a pull-request list, tolerating commas, spaces and leading '#'."""
    numbers: list[int] = []
    for token in str(raw).replace(",", " ").split():
        candidate = token.lstrip("#")
        if not candidate.isdigit():
            raise ValueError(
                f"Not a pull request number: {token!r}. Give numbers like '5521' "
                "or '5521,5533'."
            )
        number = int(candidate)
        if number <= 0:
            raise ValueError(f"Not a pull request number: {token!r}")
        # Applying the same patch twice fails on the second attempt, which
        # would be a confusing way to report a duplicate in the input.
        if number not in numbers:
            numbers.append(number)
    return numbers


def label_ref(ref: str, pr_numbers: list[int]) -> str:
    """Return the ref string to record for a tree with these patches applied."""
    if not pr_numbers:
        return ref
    applied = "+".join(f"{WLED_REPOSITORY}#{number}" for number in pr_numbers)
    return f"{ref}+{applied}"


def diff_url(pr_number: int) -> str:
    return f"https://api.github.com/repos/{WLED_REPOSITORY}/pulls/{pr_number}"


def _read_diff(url: str) -> bytes:
    headers = {
        "Accept": DIFF_MEDIA_TYPE,
        "User-Agent": DEFAULT_USER_AGENT,
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request) as response:
        return response.read()


def apply_pull_requests(*, wled_dir: Path, ref: str, pr_numbers: list[int]) -> str:
    """Apply each pull request in order and return the ref label to record."""
    for number in pr_numbers:
        # Progress goes to stderr: stdout carries the ref label the caller
        # captures.
        print(f"Applying {WLED_REPOSITORY}#{number} to {ref}", file=sys.stderr, flush=True)
        diff = _read_diff(diff_url(number))
        subprocess.run(
            ["git", "apply", "--verbose", "-"],
            cwd=wled_dir,
            input=diff,
            check=True,
        )
    return label_ref(ref, pr_numbers)


def main() -> int:
    args = _parse_args()
    label = apply_pull_requests(
        wled_dir=args.wled_dir.resolve(),
        ref=args.wled_ref,
        pr_numbers=parse_pr_numbers(args.patch_prs),
    )
    sys.stdout.write(f"{label}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
