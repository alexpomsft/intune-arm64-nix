#!/usr/bin/env python3
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile


def outcomes(text):
    reports = [line for line in text.splitlines() if "Reporting status to Intune statuses=" in line]
    if not reports:
        return None
    states = re.findall(r"\bnew_compliance_state: (Compliant|NonCompliant|Error|Unknown)\b",
                        reports[-1])
    return {state: states.count(state) for state in ("Compliant", "NonCompliant", "Error", "Unknown")}


def confirmed_checkin(exit_code, text):
    return (exit_code == 0 and "Completed device checkin" in text
            and "Successfully checked in with Intune" in text)


def retain_tail(output, chunk, limit=8 * 1024 * 1024):
    output.write(chunk)
    if output.tell() > limit:
        output.seek(-limit // 2, os.SEEK_END)
        tail = output.read()
        output.seek(0)
        output.truncate()
        output.write(tail)


def main():
    os.umask(0o077)
    base = Path(__file__).resolve().parent
    state = base / "state/state/intune"
    state.mkdir(parents=True, exist_ok=True)
    if state.is_symlink():
        raise SystemExit("Refusing a symlinked check-in directory.")
    log = state / "checkin-last.log"
    status = state / "checkin-status.json"
    if status.is_symlink():
        raise SystemExit("Refusing a symlinked check-in status file.")
    descriptor = os.open(log, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w+b") as output:
        info = os.fstat(output.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
            raise SystemExit("Refusing an unsafe check-in log.")
        os.fchmod(output.fileno(), 0o600)
        output.truncate()
        environment = os.environ.copy()
        environment["INTUNE_LOG_LEVEL"] = "info"
        environment["INTUNE_PRIVATE_LOG"] = "1"
        environment.pop("JOURNAL_STREAM", None)
        with subprocess.Popen([str(base / "run"), "intune-agent"], env=environment,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as process:
            while chunk := process.stdout.read1(65536):
                retain_tail(output, chunk)
            exit_code = process.wait()
    text = log.read_text(errors="replace")
    confirmed = confirmed_checkin(exit_code, text)
    summary = {
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
        "agent_exit": exit_code,
        "server_checkin_confirmed": confirmed,
        "setting_outcomes": outcomes(text),
    }
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=state, prefix=".checkin-", delete=False) as output:
            temporary = Path(output.name)
            json.dump(summary, output, indent=2)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, status)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    if not confirmed:
        print(f"Intune check-in failed or lacked server confirmation (agent exit {exit_code}).")
        print(f"Sensitive diagnostic log retained privately at {log}; do not publish it.")
        return 1
    print("Intune server check-in confirmed; setting outcomes:", json.dumps(summary["setting_outcomes"]))
    print("A completed check-in does not imply full tenant compliance.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
