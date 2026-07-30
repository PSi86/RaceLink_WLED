import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
BUILD_WORKFLOW = ROOT / ".github" / "workflows" / "build.yml"
RELEASE_WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
BUILD_SCRIPT = ROOT / "scripts" / "build_and_stage_profiles.sh"


class ArtifactStagingTests(unittest.TestCase):
    """Guards for the flashable-artifact pipeline.

    These failure modes are all silent: an esptool major bump that renames the
    merge subcommand, a rehearsal that drifts from the real release, or a
    publish glob that quietly drops the new assets.
    """

    def test_both_workflows_run_the_same_build_and_stage_script(self):
        # The rehearsal on a pull request is only worth anything if it runs the
        # same code the release does.
        for workflow in (BUILD_WORKFLOW, RELEASE_WORKFLOW):
            with self.subTest(workflow=workflow.name):
                source = workflow.read_text(encoding="utf-8")
                self.assertIn("scripts/build_and_stage_profiles.sh", source)

    def test_esptool_major_is_pinned_in_both_workflows(self):
        # esptool 5 renamed merge_bin to merge-bin; release_artifacts.py emits
        # the dashed form, so an unpinned major would break a release.
        for workflow in (BUILD_WORKFLOW, RELEASE_WORKFLOW):
            with self.subTest(workflow=workflow.name):
                source = workflow.read_text(encoding="utf-8")
                self.assertIn('python -m pip install "esptool>=5,<6"', source)

    def test_metadata_is_collected_before_the_build(self):
        # `pio project metadata` cleans the build directory, so collecting it
        # after `pio run` deletes the firmware.bin that is about to be staged.
        # Everything it reports is derived from the configuration, so the files
        # it names do not have to exist yet.
        source = BUILD_SCRIPT.read_text(encoding="utf-8")
        metadata = source.index("project metadata")
        build = source.index("platformio run")
        staging = source.index("stage-assets")

        self.assertLess(metadata, build, "project metadata must run before the build")
        self.assertLess(build, staging, "stage-assets needs the built firmware")

    def test_release_index_is_written_after_every_profile(self):
        source = BUILD_SCRIPT.read_text(encoding="utf-8")

        self.assertLess(source.index("stage-assets"), source.index("finalize"))

    def test_built_envs_list_is_kept_out_of_the_published_directory(self):
        # dist/ is published wholesale; scaffolding in there would ship.
        source = BUILD_SCRIPT.read_text(encoding="utf-8")

        self.assertNotIn("dist/built_envs.txt", source)
        self.assertIn(": > built_envs.txt", source)

    def test_every_staged_asset_is_published(self):
        source = RELEASE_WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("files: dist/*", source)
        self.assertIn("path: dist/*", source)

    def test_release_notes_warn_about_the_factory_image(self):
        # Collapse whitespace: the notes are a wrapped YAML block, so asserting
        # on exact line breaks would fail the next time someone rewraps them.
        source = " ".join(RELEASE_WORKFLOW.read_text(encoding="utf-8").split())

        self.assertIn("USB serial only", source)
        self.assertIn("commissioning tool, never an update tool", source)

    def test_build_workflow_publishes_nothing(self):
        source = BUILD_WORKFLOW.read_text(encoding="utf-8")

        self.assertNotIn("action-gh-release", source)
        self.assertNotIn("git tag", source)
        self.assertNotIn("git push", source)
        self.assertIn("contents: read", source)

    def test_build_workflow_runs_on_pull_requests(self):
        source = BUILD_WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("pull_request:", source)
        self.assertIn("workflow_dispatch:", source)


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
        self.assertIn("softprops/action-gh-release@v3", source)
        self.assertIn("tag_name: ${{ steps.release_version.outputs.tag }}", source)


if __name__ == "__main__":
    unittest.main()
