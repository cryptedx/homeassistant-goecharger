import importlib.util
import unittest
from pathlib import Path


spec = importlib.util.spec_from_file_location(
    "release_script",
    Path(__file__).parents[1] / "scripts" / "release.py",
)
release_script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release_script)


class ReleasePlannerTests(unittest.TestCase):
    def test_no_tag_bootstraps_current_version_without_file_changes(self):
        plan = release_script.plan_release("0.27.1", None, ["feat: new switch"], [])

        self.assertEqual(plan.version, "0.27.1")
        self.assertTrue(plan.should_release)
        self.assertFalse(plan.changed_files)

    def test_fix_commit_bumps_patch(self):
        plan = release_script.plan_release("0.27.1", "v0.27.1", ["fix: read charger status"], [])

        self.assertEqual(plan.version, "0.27.2")
        self.assertTrue(plan.should_release)

    def test_feat_commit_bumps_minor_on_zero_major(self):
        plan = release_script.plan_release("0.27.1", "v0.27.1", ["feat: add charger lock"], [])

        self.assertEqual(plan.version, "0.28.0")

    def test_dependency_scope_bumps_patch(self):
        plan = release_script.plan_release("0.27.1", "v0.27.1", ["chore(deps): bump goecharger"], [])

        self.assertEqual(plan.version, "0.27.2")

    def test_docs_only_commit_does_not_release(self):
        plan = release_script.plan_release("0.27.1", "v0.27.1", ["docs: clarify setup"], ["README.md"])

        self.assertFalse(plan.should_release)

    def test_integration_file_change_without_conventional_commit_bumps_patch(self):
        plan = release_script.plan_release(
            "0.27.1",
            "v0.27.1",
            ["Update charger sensors"],
            ["custom_components/goecharger/sensor.py"],
        )

        self.assertEqual(plan.version, "0.27.2")

    def test_changelog_gets_new_release_and_resets_unreleased(self):
        changelog = """# Changelog

## Unreleased

- Keep this note.

## 0.27.1 - 2026-06-24

- Previous release.
"""

        updated = release_script.update_changelog(changelog, "0.27.2", "2026-06-24", ["fix: read charger status"])

        self.assertIn("## Unreleased\n\n## 0.27.2 - 2026-06-24\n\n- Keep this note.", updated)
        self.assertIn("## 0.27.1 - 2026-06-24", updated)

    def test_empty_unreleased_uses_commit_subjects(self):
        changelog = """# Changelog

## Unreleased

## 0.27.1 - 2026-06-24

- Previous release.
"""

        updated = release_script.update_changelog(
            changelog,
            "0.27.2",
            "2026-06-24",
            ["fix: read charger status", "docs: clarify setup"],
        )

        self.assertIn("- fix: read charger status\n- docs: clarify setup", updated)


if __name__ == "__main__":
    unittest.main()
