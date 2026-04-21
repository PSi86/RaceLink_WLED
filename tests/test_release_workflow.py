import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class ReleaseWorkflowTests(unittest.TestCase):
    def test_release_workflow_has_required_manual_inputs(self):
        source = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

        self.assertIn("workflow_dispatch:", source)
        self.assertIn(
            'description: "Optional RaceLink_WLED release version override. Leave empty to auto-increment."',
            source,
        )
        self.assertIn('description: "Branch to release from"', source)
        self.assertIn(
            'description: "Optional WLED tag/ref override. Leave empty to use the latest published WLED release."',
            source,
        )

    def test_release_workflow_resolves_versions_guards_duplicates_and_publishes_release(self):
        source = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

        self.assertIn("python scripts/bump_release_version.py --version", source)
        self.assertIn("python scripts/resolve_wled_release.py --wled-ref", source)
        self.assertIn('echo "tag=v${version}" >> "$GITHUB_OUTPUT"', source)
        self.assertIn(
            'git commit -m "Release v${{ steps.release_version.outputs.version }}"',
            source,
        )
        self.assertIn('git tag "${{ steps.release_version.outputs.tag }}"', source)
        self.assertIn('git push origin "HEAD:${{ inputs.target_branch }}" --follow-tags', source)
        self.assertIn('gh release view "${{ steps.release_version.outputs.tag }}"', source)
        self.assertIn("softprops/action-gh-release@v2", source)
        self.assertIn("tag_name: ${{ steps.release_version.outputs.tag }}", source)


if __name__ == "__main__":
    unittest.main()
