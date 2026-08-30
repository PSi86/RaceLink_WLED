import pathlib
import shutil
import unittest
from uuid import uuid4

from scripts.release_profiles import (
    SHIPPING_PROFILE_FILENAMES,
    is_release_profile,
    iter_shipping_profiles,
    parse_profile_environments,
    rewrite_custom_usermods,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]


class ReadmeProfileListTests(unittest.TestCase):
    """The readme is where someone picks the profile for their board.

    It listed four of the six shipping profiles for long enough that two
    boards had no documented way to be built, while naming a `bak_` file as
    if it were one of them. A list maintained by hand drifts; this is what
    keeps it honest.
    """

    def setUp(self):
        self.readme = (ROOT / "readme.md").read_text(encoding="utf-8")

    def test_every_shipping_profile_is_documented(self):
        for filename in SHIPPING_PROFILE_FILENAMES:
            with self.subTest(filename=filename):
                self.assertIn(filename, self.readme)

    def test_no_profile_is_documented_that_a_release_does_not_build(self):
        # Naming one is fine -- the readme explains what the two extra files
        # are -- but not in the list of what a release ships.
        shipping_list = self.readme.split("Six profiles are built")[1].split(
            "SHIPPING_PROFILE_FILENAMES"
        )[0]

        for path in sorted((ROOT / "build_profiles").glob("*.ini")):
            if path.name in SHIPPING_PROFILE_FILENAMES:
                continue
            with self.subTest(filename=path.name):
                self.assertNotIn(path.name, shipping_list)


class ReleaseProfilesTests(unittest.TestCase):
    def test_iter_shipping_profiles_returns_only_shipping_profiles(self):
        profiles = iter_shipping_profiles(ROOT / "build_profiles")

        self.assertEqual(
            [path.name for path in profiles],
            [
                "RaceLink_Node_v1_c3_ct62.platformio_override.ini",
                "RaceLink_Node_v3_s2_llcc68.platformio_override.ini",
                "RaceLink_Node_v3_s2_llcc68_epaper.platformio_override.ini",
                "RaceLink_Node_v4_s3_llcc68.platformio_override.ini",
                "RaceLink_Node_v5_s3_eth.platformio_override.ini",
                "RaceLink_Node_v6_s3_heltec_wpaper.platformio_override.ini",
            ],
        )

    def test_non_release_profiles_are_excluded(self):
        self.assertFalse(
            is_release_profile(
                ROOT / "build_profiles" / "all_profiles.platformio_override.ini"
            )
        )
        self.assertFalse(
            is_release_profile(
                ROOT / "build_profiles" / "bak_RaceLink_Node_v3_s2_llcc68.platformio_override.ini"
            )
        )

    def test_profile_environment_parser_returns_only_env_sections(self):
        environments = parse_profile_environments(
            ROOT / "build_profiles" / "RaceLink_Node_v3_s2_llcc68_epaper.platformio_override.ini"
        )

        self.assertEqual(
            [env.name for env in environments],
            ["RaceLink_Node_v3_s2_llcc68_epaper"],
        )
        self.assertEqual(environments[0].release_name, "RaceLink_Node_V3_TYPE_50")

    def test_custom_usermods_are_rewritten_to_local_modules(self):
        source = (
            "[env:test]\n"
            "custom_usermods = https://github.com/PSi86/RaceLink_WLED.git#main battery\n"
        )

        rewritten = rewrite_custom_usermods(source)

        self.assertIn("custom_usermods = Battery RaceLink_WLED", rewritten)
        self.assertNotIn("https://github.com/PSi86/RaceLink_WLED.git", rewritten)

    def test_rewritten_profile_can_be_saved_as_platformio_override(self):
        source = (
            "[env:test]\n"
            "custom_usermods = something else\n"
        )

        temp_dir = ROOT / f".rewrite-profile-{uuid4().hex}"
        temp_dir.mkdir()
        self.addCleanup(lambda: shutil.rmtree(temp_dir, ignore_errors=True))
        target = temp_dir / "platformio_override.ini"
        target.write_text(rewrite_custom_usermods(source), encoding="utf-8")
        self.assertIn("Battery RaceLink_WLED", target.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
