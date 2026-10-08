from contextlib import redirect_stdout
from datetime import datetime, timezone
from importlib.machinery import SourceFileLoader
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path, loader=SourceFileLoader(name, str(path)))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


AGENT = load("agent_checkin", ROOT / "runtime/agent-checkin.py")
INSTALLER = load("install_user_startup", ROOT / "scripts/install-user-startup")
VERIFIER = load("verify_startup", ROOT / "runtime/verify-startup.py")


class StartupTests(unittest.TestCase):
    def test_zero_exit_requires_both_server_markers(self):
        self.assertFalse(AGENT.confirmed_checkin(0, "Finished successfully"))
        self.assertFalse(AGENT.confirmed_checkin(0, "Completed device checkin"))
        text = "Completed device checkin\nSuccessfully checked in with Intune"
        self.assertTrue(AGENT.confirmed_checkin(0, text))
        self.assertFalse(AGENT.confirmed_checkin(1, text))

    def test_summary_excludes_policy_contents_and_old_outcomes(self):
        text = ("Reporting status to Intune statuses=[new_compliance_state: Error]\n"
                "Reporting status to Intune statuses=[private-script-value, "
                "new_compliance_state: Compliant, new_compliance_state: Unknown]\n")
        result = AGENT.outcomes(text)
        self.assertEqual(result, {"Compliant": 1, "NonCompliant": 0, "Error": 0, "Unknown": 1})
        self.assertNotIn("private-script-value", str(result))
        self.assertIsNone(AGENT.outcomes("no report"))

    def test_wrapper_saves_private_truthful_status(self):
        for text, expected in (("private-script-value", False),
                               ("private-script-value\nCompleted device checkin\n"
                                "Successfully checked in with Intune", True)):
            with self.subTest(confirmed=expected), tempfile.TemporaryDirectory() as directory:
                process = MagicMock()
                process.__enter__.return_value = process
                process.stdout = io.BytesIO(text.encode())
                process.wait.return_value = 0
                stdout = io.StringIO()
                with patch.object(AGENT, "__file__", str(Path(directory) / "agent-checkin.py")), \
                        patch.object(AGENT.subprocess, "Popen", return_value=process), redirect_stdout(stdout):
                    self.assertEqual(AGENT.main(), 0 if expected else 1)
                state = Path(directory) / "state/state/intune"
                summary = json.loads((state / "checkin-status.json").read_text())
                self.assertEqual(summary["server_checkin_confirmed"], expected)
                self.assertNotIn("private-script-value", stdout.getvalue())
                self.assertNotIn("private-script-value", str(summary))
                for name in ("checkin-status.json", "checkin-last.log"):
                    self.assertEqual((state / name).stat().st_mode & 0o777, 0o600)

    def test_log_symlink_does_not_modify_its_target(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            target = base / "preserved"
            target.write_text("unchanged")
            state = base / "state/state/intune"
            state.mkdir(parents=True)
            (state / "checkin-last.log").symlink_to(target)
            with patch.object(AGENT, "__file__", str(base / "agent-checkin.py")), self.assertRaises(OSError):
                AGENT.main()
            self.assertEqual(target.read_text(), "unchanged")

    def test_yesterdays_boot_is_not_reboot_confirmation(self):
        now = datetime.now(timezone.utc)
        summary = {"boot_id": "previous-boot", "server_checkin_confirmed": True,
                   "completed_at": now.isoformat()}
        result = VERIFIER.checkin_freshness(summary, "current-boot", now)
        self.assertFalse(result["agent_checkin_this_boot"])
        self.assertTrue(result["agent_checkin_recent"])

    def test_private_log_is_bounded(self):
        with tempfile.TemporaryFile("w+b") as output:
            for _ in range(30):
                AGENT.retain_tail(output, b"x" * 64, limit=256)
                self.assertLessEqual(output.tell(), 256)
            AGENT.retain_tail(output, b"server confirmation", limit=256)
            output.seek(0)
            self.assertTrue(output.read().endswith(b"server confirmation"))

    def test_unit_path_escaping(self):
        self.assertEqual(INSTALLER.unit_argument(Path('/tmp/a%"$\\b')),
                         '/tmp/a%%\\"$$\\\\b')

    def test_activation_preserves_service_boundaries(self):
        for name in ("device-broker-activation.service", "user-broker-activation.service"):
            text = (ROOT / "runtime" / name).read_text()
            self.assertIn("Exec=/usr/bin/false", text)
            self.assertIn("SystemdService=microsoft-identity-", text)
        broker = (ROOT / "runtime/user-broker.service.in").read_text()
        self.assertIn("Type=dbus", broker)
        self.assertIn("ConditionEnvironment=DISPLAY", broker)
        self.assertIn("PartOf=graphical-session.target", broker)
        self.assertNotIn("INTUNE_COMPAT_OS", broker)
        launcher = (ROOT / "runtime/run").read_text()
        self.assertIn("log_mounts=(--tmpfs /run/systemd/journal)", launcher)
        for name in ("device-broker-run", "daemon-run"):
            text = (ROOT / "runtime" / name).read_text()
            self.assertIn("--tmpfs /opt", text)
            self.assertIn('--ro-bind "$base" "$base"', text)
            self.assertIn("--remount-ro /opt", text)
            self.assertIn("--cap-drop ALL", text)


if __name__ == "__main__":
    unittest.main()
