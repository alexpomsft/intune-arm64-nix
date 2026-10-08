import os
from pathlib import Path
import subprocess
import time

os.umask(0o077)
base = Path(__file__).resolve().parent
environment = os.environ.copy()
environment["PYTHONHOME"] = str(base / "rootfs/usr")
environment["BOX64_DYNAREC"] = "0"


def descendants(pid):
    result = [pid]
    for child in result:
        try:
            children = Path(f"/proc/{child}/task/{child}/children").read_text()
        except FileNotFoundError:
            continue
        result.extend(int(value) for value in children.split())
    return result


with (base / "webkit-verified-probe.log").open("w") as log:
    process = subprocess.Popen(
        [str(base / "run"), str(base / "rootfs/usr/bin/python3.12"),
         str(base / "probe-webkit.py"), "--login-form"],
        env=environment, stdout=log, stderr=subprocess.STDOUT,
    )
    verified = False
    network_verified = False
    deadline = time.monotonic() + 90
    try:
        while process.poll() is None and time.monotonic() < deadline:
            ui_namespace = None
            renderers = []
            for pid in descendants(process.pid):
                try:
                    command = Path(f"/proc/{pid}/cmdline").read_bytes()
                    namespace = os.readlink(f"/proc/{pid}/ns/mnt")
                    status = Path(f"/proc/{pid}/status").read_text()
                    process_environment = Path(f"/proc/{pid}/environ").read_bytes().split(b"\0")
                except FileNotFoundError:
                    continue
                if b"probe-webkit.py" in command and b"box64" in command:
                    ui_namespace = namespace
                if b"/usr/lib/intune-arm64/WebKitWebProcess" in command:
                    renderers.append((namespace, status, process_environment))
                if b"/usr/lib/intune-arm64/WebKitNetworkProcess" in command:
                    network_verified |= b"BOX64_DYNAREC=0" in process_environment
            for namespace, status, process_environment in renderers:
                fields = dict(line.split(":", 1) for line in status.splitlines()
                              if ":" in line)
                if (ui_namespace and namespace != ui_namespace
                        and fields["Seccomp"].strip() == "2"
                        and fields["NoNewPrivs"].strip() == "1"
                        and b"BOX64_DYNAREC=1" in process_environment
                        and len(fields["NSpid"].split()) >= 2):
                    verified = True
            time.sleep(0.05)
        if process.poll() is None:
            raise TimeoutError("Sandboxed WebKit did not complete within 90 seconds")
        if process.returncode:
            raise RuntimeError(f"WebKit probe exited {process.returncode}; see private log")
        if not verified:
            raise RuntimeError("Could not verify kernel renderer isolation")
        if not network_verified:
            raise RuntimeError("Could not verify interpreted TLS network process")
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
print("The visible Microsoft sign-in form loaded with a separate renderer mount/PID namespace, "
      "NoNewPrivs=1, kernel Seccomp=2, renderer dynarec=1, and network dynarec=0")
