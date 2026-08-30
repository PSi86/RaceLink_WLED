import json
import pathlib
import tempfile
import unittest

from scripts.apply_wled_patches import resolve_pr_numbers
from scripts.resolve_wled_release import resolve_wled_ref
from scripts.wled_source import (
    LATEST_REF,
    NO_PATCHES,
    WledSource,
    load_source_pin,
    parse_source_pin,
    source_pin_path,
)


def _write(payload: object) -> pathlib.Path:
    handle = tempfile.NamedTemporaryFile(
        "w", suffix=".json", delete=False, encoding="utf-8"
    )
    with handle:
        json.dump(payload, handle)
    return pathlib.Path(handle.name)


class SourcePinFileTests(unittest.TestCase):
    """The committed pin is what both workflows build from."""

    def test_the_committed_pin_parses(self):
        pin = load_source_pin()
        self.assertTrue(pin.ref)

    def test_the_committed_pin_names_a_tag_rather_than_a_branch(self):
        # A branch would put the pin back where it started: the tree moves and
        # nothing here records that it did. 'latest' is allowed but has to be
        # chosen, and is not what this repository ships pinned to.
        ref = load_source_pin().ref
        self.assertNotIn("/", ref, "the pin should be a tag, not a branch or a path")
        self.assertNotEqual(ref, LATEST_REF, "shipping unpinned defeats the pin")

    def test_the_pin_lives_where_the_workflows_look_for_it(self):
        self.assertTrue(source_pin_path().is_file())

    def test_the_readme_tells_people_to_check_out_the_pinned_tag(self):
        # The quick start hands out a clone command with the tag in it. A
        # reader following a stale one builds against a WLED these profiles
        # were never tested on -- and finds out at the compiler, or later.
        readme = (pathlib.Path(__file__).resolve().parents[1] / "readme.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            f"git clone --branch {load_source_pin().ref} "
            "https://github.com/wled/WLED.git",
            readme,
        )


class ParseSourcePinTests(unittest.TestCase):
    def test_patch_prs_are_normalised_for_the_cli(self):
        pin = parse_source_pin({"ref": "v16.0.1", "patch_prs": [5521, 5533]})
        self.assertEqual(pin, WledSource(ref="v16.0.1", patch_prs="5521,5533"))

    def test_patch_prs_may_be_absent_or_empty(self):
        for payload in ({"ref": "v16.0.1"}, {"ref": "v16.0.1", "patch_prs": []}):
            with self.subTest(payload=payload):
                self.assertEqual(parse_source_pin(payload).patch_prs, "")

    def test_notes_are_prose_and_not_a_typo(self):
        # JSON has nowhere else to record why a pull request is pinned.
        pin = parse_source_pin({"ref": "v16.0.1", "notes": ["why 5521 is here"]})
        self.assertEqual(pin.ref, "v16.0.1")

    def test_an_unknown_key_is_a_typo_rather_than_a_setting(self):
        # A misspelled key would otherwise be ignored in silence, and the build
        # would quietly use the default it was meant to change.
        with self.assertRaisesRegex(ValueError, "unknown key"):
            parse_source_pin({"ref": "v16.0.1", "patch_pr": [5521]})

    def test_a_missing_or_empty_ref_fails(self):
        for payload in ({}, {"ref": ""}, {"ref": "  "}, {"ref": 16}):
            with self.subTest(payload=payload):
                with self.assertRaisesRegex(ValueError, "'ref' must be"):
                    parse_source_pin(payload)

    def test_patch_prs_must_be_pull_request_numbers(self):
        for entry in ("5521", -1, 0, True, None):
            with self.subTest(entry=entry):
                with self.assertRaisesRegex(ValueError, "not a pull request number"):
                    parse_source_pin({"ref": "v16.0.1", "patch_prs": [entry]})

    def test_a_non_object_payload_fails(self):
        with self.assertRaisesRegex(ValueError, "must contain a JSON object"):
            parse_source_pin([5521])


class LoadSourcePinTests(unittest.TestCase):
    def test_a_missing_pin_names_the_file_it_wants(self):
        missing = pathlib.Path(tempfile.gettempdir()) / "no_such_wled_source.json"
        with self.assertRaisesRegex(FileNotFoundError, "no_such_wled_source.json"):
            load_source_pin(missing)

    def test_malformed_json_fails_with_the_path(self):
        broken = _write("")
        broken.write_text("{not json", encoding="utf-8")
        try:
            with self.assertRaisesRegex(ValueError, "not valid JSON"):
                load_source_pin(broken)
        finally:
            broken.unlink()


class ResolutionPrecedenceTests(unittest.TestCase):
    """An input overrides the pin; a blank input is not an input."""

    def test_an_explicit_ref_wins_over_the_pin(self):
        self.assertEqual(
            resolve_wled_ref("v16.0.0", pinned_ref="v16.0.1"), "v16.0.0"
        )

    def test_a_blank_ref_falls_through_to_the_pin(self):
        # This is the case that matters: the workflow always passes the input,
        # and it is empty on every run nobody filled it in.
        for blank in ("", "   "):
            with self.subTest(blank=repr(blank)):
                self.assertEqual(
                    resolve_wled_ref(blank, pinned_ref="v16.0.1"), "v16.0.1"
                )

    def test_an_explicit_patch_list_wins_over_the_pin(self):
        self.assertEqual(resolve_pr_numbers("5533", pinned="5521"), [5533])

    def test_a_blank_patch_list_falls_through_to_the_pin(self):
        for blank in ("", "   "):
            with self.subTest(blank=repr(blank)):
                self.assertEqual(resolve_pr_numbers(blank, pinned="5521"), [5521])

    def test_building_unpatched_has_to_be_said_out_loud(self):
        # Blank means "not specified", so "no patches" needs a word of its own
        # -- otherwise the two are indistinguishable and #5521 goes missing
        # without anything failing.
        for spelling in (NO_PATCHES, "NONE", " none "):
            with self.subTest(spelling=spelling):
                self.assertEqual(resolve_pr_numbers(spelling, pinned="5521"), [])

    def test_latest_is_still_reachable_from_the_pin_and_the_input(self):
        # Not exercised against the network here -- resolve_wled_ref would call
        # the GitHub API. What is asserted is that both routes agree on the
        # sentinel, so the escape hatch cannot rot.
        self.assertEqual(LATEST_REF, "latest")
        self.assertEqual(
            parse_source_pin({"ref": LATEST_REF}).ref, LATEST_REF
        )


if __name__ == "__main__":
    unittest.main()
