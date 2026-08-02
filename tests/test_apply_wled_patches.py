import unittest

from scripts.apply_wled_patches import diff_url, label_ref, parse_pr_numbers


class ParsePrNumbersTests(unittest.TestCase):
    def test_empty_input_selects_nothing(self):
        # The workflows call this unconditionally, so "no patches" is the
        # normal case and has to be a clean pass-through.
        self.assertEqual(parse_pr_numbers(""), [])
        self.assertEqual(parse_pr_numbers("   "), [])

    def test_separators_and_hashes_are_tolerated(self):
        self.assertEqual(parse_pr_numbers("5521"), [5521])
        self.assertEqual(parse_pr_numbers("5521,5533"), [5521, 5533])
        self.assertEqual(parse_pr_numbers("5521 5533"), [5521, 5533])
        self.assertEqual(parse_pr_numbers(" #5521, #5533 "), [5521, 5533])

    def test_order_is_preserved_and_duplicates_dropped(self):
        # Order matters: patches are applied in sequence and a later one may
        # depend on an earlier one. A repeat would fail on the second apply,
        # which is a confusing way to report a typo in the input.
        self.assertEqual(parse_pr_numbers("5533,5521,5533"), [5533, 5521])

    def test_non_numeric_input_fails(self):
        for raw in ("banana", "refs/pull/5521/head", "55-21", "#"):
            with self.subTest(raw=raw):
                with self.assertRaisesRegex(ValueError, "Not a pull request number"):
                    parse_pr_numbers(raw)

    def test_zero_is_not_a_pull_request(self):
        with self.assertRaisesRegex(ValueError, "Not a pull request number"):
            parse_pr_numbers("0")


class LabelRefTests(unittest.TestCase):
    """The label becomes `wled_ref` in the sidecar, so it has to be truthful."""

    def test_unpatched_ref_is_recorded_verbatim(self):
        self.assertEqual(label_ref("v16.0.1", []), "v16.0.1")

    def test_applied_pull_requests_are_named(self):
        self.assertEqual(label_ref("v16.0.1", [5521]), "v16.0.1+wled/WLED#5521")

    def test_every_applied_pull_request_is_named(self):
        # A build carrying two patches must not read as if it carried one.
        self.assertEqual(
            label_ref("v16.0.1", [5521, 5533]),
            "v16.0.1+wled/WLED#5521+wled/WLED#5533",
        )


class DiffUrlTests(unittest.TestCase):
    def test_diff_comes_from_the_upstream_repository(self):
        # The pull endpoint, not the .diff URL on github.com: that one
        # redirects to a signed host which ignores the token.
        self.assertEqual(
            diff_url(5521),
            "https://api.github.com/repos/wled/WLED/pulls/5521",
        )


if __name__ == "__main__":
    unittest.main()
