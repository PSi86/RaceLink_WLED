import pathlib
import shutil
import unittest
from uuid import uuid4

from scripts.release_profiles import (
    is_release_profile,
    iter_shipping_profiles,
    parse_profile_environments,
    rewrite_custom_usermods,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]


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
