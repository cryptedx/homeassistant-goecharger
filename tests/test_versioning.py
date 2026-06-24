import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)


class VersioningTests(unittest.TestCase):
    def manifest(self):
        return json.loads(
            (ROOT / "custom_components" / "goecharger" / "manifest.json").read_text(
                encoding="utf-8"
            )
        )

    def manifest_version(self):
        return self.manifest()["version"]

    def test_manifest_version_is_semver(self):
        self.assertRegex(self.manifest_version(), SEMVER)

    def test_manifest_version_is_documented_in_changelog(self):
        changelog_path = ROOT / "CHANGELOG.md"
        self.assertTrue(changelog_path.exists(), "CHANGELOG.md must exist")

        changelog = changelog_path.read_text(encoding="utf-8")

        self.assertIn(f"## {self.manifest_version()}", changelog)

    def test_goecharger_v1_dependency_is_current(self):
        self.assertIn("goecharger==0.1.0", self.manifest()["requirements"])


if __name__ == "__main__":
    unittest.main()
