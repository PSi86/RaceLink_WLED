import json
import pathlib
import shutil
import unittest
from uuid import uuid4

from scripts.bump_release_version import bump_release_version

ROOT = pathlib.Path(__file__).resolve().parents[1]


class BumpReleaseVersionTests(unittest.TestCase):
    def _write_version_file(self, version: str) -> pathlib.Path:
        temp_dir = ROOT / f".bump-release-version-{uuid4().hex}"
        temp_dir.mkdir()
        version_file = temp_dir / "version.json"
        version_file.write_text(
            json.dumps({"version": version}, indent=2) + "\n",
            encoding="utf-8",
        )
        self.addCleanup(lambda: shutil.rmtree(temp_dir, ignore_errors=True))
        return version_file

    def test_explicit_version_is_normalized(self):
        version_file = self._write_version_file("0.1.0")

        version = bump_release_version(version_file=version_file, version="v1.2.3")

        self.assertEqual(version, "1.2.3")
        self.assertEqual(
            json.loads(version_file.read_text(encoding="utf-8"))["version"],
            "1.2.3",
        )

    def test_empty_version_increments_patch(self):
        version_file = self._write_version_file("0.1.0")

        version = bump_release_version(version_file=version_file, version="")

        self.assertEqual(version, "0.1.1")

    def test_invalid_explicit_version_fails(self):
        version_file = self._write_version_file("0.1.0")

        with self.assertRaisesRegex(ValueError, "Version must look like semantic versioning"):
            bump_release_version(version_file=version_file, version="banana")

    def test_invalid_current_version_fails(self):
        version_file = self._write_version_file("banana")

        with self.assertRaisesRegex(ValueError, "Current release version is not valid semver"):
            bump_release_version(version_file=version_file, version="")


if __name__ == "__main__":
    unittest.main()
