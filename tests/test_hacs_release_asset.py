import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).parents[1]


class HacsReleaseAssetTests(unittest.TestCase):
    def test_hacs_metadata_uses_release_zip_asset(self):
        hacs = json.loads((ROOT / "hacs.json").read_text(encoding="utf-8"))

        self.assertTrue(hacs.get("zip_release"))
        self.assertEqual(hacs.get("filename"), "goecharger.zip")

    def test_release_zip_contains_integration_files_at_archive_root(self):
        script = ROOT / "scripts" / "build_hacs_release.py"
        if not script.exists():
            self.fail("scripts/build_hacs_release.py does not exist")

        spec = importlib.util.spec_from_file_location("build_hacs_release", script)
        build_hacs_release = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(build_hacs_release)

        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "goecharger.zip"
            build_hacs_release.build_zip(target=target)

            with ZipFile(target) as archive:
                names = set(archive.namelist())
                manifest = json.loads(archive.read("manifest.json"))

        self.assertIn("__init__.py", names)
        self.assertIn("manifest.json", names)
        self.assertIn("translations/en.json", names)
        self.assertFalse(any(name.startswith("custom_components/") for name in names))
        self.assertFalse(any("__pycache__" in name for name in names))
        self.assertFalse(any(name.endswith(".pyc") for name in names))
        self.assertEqual(manifest["domain"], "goecharger")


if __name__ == "__main__":
    unittest.main()
