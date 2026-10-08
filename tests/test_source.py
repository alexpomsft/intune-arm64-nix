import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SourceTests(unittest.TestCase):
    def test_package_pins(self):
        values = json.loads((ROOT / "runtime/versions.json").read_text())
        self.assertRegex(values["box64_commit"], r"^[0-9a-f]{40}$")
        for package in values["microsoft_packages"].values():
            self.assertRegex(package["sha256"], r"^[0-9a-f]{64}$")
            self.assertTrue(package["version"].endswith("-noble"))

    def test_debian_index_fields(self):
        path = ROOT / "runtime/fetch-microsoft.py"
        spec = importlib.util.spec_from_file_location("fetch_microsoft", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.fields("Package: example\nDescription: line\n continuation\n"),
                         {"Package": "example", "Description": "line\n continuation"})

    def test_identity_is_opt_in(self):
        launcher = (ROOT / "runtime/run").read_text()
        self.assertIn('case "${INTUNE_COMPAT_OS:-}" in', launcher)
        self.assertIn('/usr/lib/arm64-host/os-release', launcher)
        self.assertNotIn("--disable-sandbox", launcher)
        self.assertNotIn("WEBKIT_DISABLE_SANDBOX", launcher)
        self.assertIn("WEBKIT_FORCE_SANDBOX=1", launcher)

    def test_sources_have_no_original_home_path(self):
        for directory in ("runtime", "scripts", "patches", "docs"):
            for path in (ROOT / directory).rglob("*"):
                if path.is_file() and "__pycache__" not in path.parts:
                    self.assertNotRegex(path.read_text(), r"/home/[^/\s]+/")


if __name__ == "__main__":
    unittest.main()
