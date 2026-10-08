#!/usr/bin/env python3
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess


def state(unit, property_name, user=False):
    command = ["systemctl"]
    if user:
        command.append("--user")
    return subprocess.check_output(command + ["show", unit, "--property=" + property_name, "--value"],
                                   text=True).strip()


def secret_collection(alias):
    from gi.repository import Gio, GLib
    connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    path = connection.call_sync("org.freedesktop.secrets", "/org/freedesktop/secrets",
                               "org.freedesktop.Secret.Service", "ReadAlias",
                               GLib.Variant("(s)", (alias,)), GLib.VariantType.new("(o)"),
                               Gio.DBusCallFlags.NONE, 10000, None).unpack()[0]
    if path == "/":
        return {"present": False, "unlocked": False}
    locked = connection.call_sync("org.freedesktop.secrets", path,
                                 "org.freedesktop.DBus.Properties", "Get",
                                 GLib.Variant("(ss)", ("org.freedesktop.Secret.Collection", "Locked")),
                                 GLib.VariantType.new("(v)"), Gio.DBusCallFlags.NONE,
                                 10000, None).unpack()[0]
    return {"present": True, "unlocked": not locked}


def checkin_freshness(summary, boot, now):
    age = (now - datetime.fromisoformat(summary["completed_at"])).total_seconds()
    return {
        "agent_checkin_this_boot": bool(summary["boot_id"] == boot and summary["server_checkin_confirmed"]),
        "agent_checkin_recent": bool(summary["server_checkin_confirmed"] and 0 <= age < 7200),
    }


def main():
    parser = argparse.ArgumentParser(description="Verify startup without exposing identities or credentials")
    parser.add_argument("--runtime", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--check-browser-host", action="store_true")
    args = parser.parse_args()
    runtime = args.runtime.expanduser().resolve()
    report = {}
    for unit in ("microsoft-identity-device-broker.service", "intune-daemon.socket"):
        report[unit] = {"active": state(unit, "ActiveState") == "active",
                        "enabled": state(unit, "UnitFileState") == "enabled"}
    for unit in ("microsoft-identity-broker.service", "intune-agent.timer"):
        report[unit] = {"active": state(unit, "ActiveState", user=True) == "active",
                        "enabled": state(unit, "UnitFileState", user=True) == "enabled"}
    report["device_broker_activation_installed"] = Path(
        "/usr/share/dbus-1/system-services/com.microsoft.identity.devicebroker1.service").exists()
    report["agent_service_result"] = state("intune-agent.service", "Result", user=True)
    report["login_collection"] = secret_collection("login")
    report["default_collection"] = secret_collection("default")
    summary_path = runtime / "state/state/intune/checkin-status.json"
    report["agent_checkin_this_boot"] = False
    report["agent_checkin_recent"] = False
    if summary_path.exists():
        summary = json.loads(summary_path.read_text())
        boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
        report.update(checkin_freshness(summary, boot, datetime.now(timezone.utc)))
        report["last_setting_outcomes"] = summary["setting_outcomes"]
    if args.check_browser_host:
        host = Path.home() / ".config/chromium/linux-entra-sso"
        subprocess.run(["/usr/bin/python3", str(runtime / "probe-native-messaging.py"), str(host)], check=True)
        report["native_browser_cookie_acquisition"] = True
    print(json.dumps(report, indent=2))
    required = [
        report["device_broker_activation_installed"],
        report["intune-daemon.socket"]["active"], report["intune-daemon.socket"]["enabled"],
        report["microsoft-identity-broker.service"]["active"],
        report["microsoft-identity-broker.service"]["enabled"],
        report["intune-agent.timer"]["active"], report["intune-agent.timer"]["enabled"],
        report["login_collection"]["unlocked"], report["default_collection"]["unlocked"],
        report["agent_checkin_this_boot"], report["agent_checkin_recent"],
        report["agent_service_result"] == "success",
    ]
    if not all(required):
        raise SystemExit("Startup verification incomplete; a scheduled check-in may still be pending.")
    print("Startup wiring and this-boot server check-in verified; full tenant compliance is separate.")


if __name__ == "__main__":
    main()
