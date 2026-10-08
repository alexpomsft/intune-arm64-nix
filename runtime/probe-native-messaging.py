#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
import select
import struct
import subprocess
import time


def main():
    parser = argparse.ArgumentParser(description="Verify native messaging without printing account/token data")
    parser.add_argument("host", type=Path, help="Installed Chromium linux-entra-sso executable")
    args = parser.parse_args()
    process = subprocess.Popen([str(args.host.resolve())], stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def read_exact(count):
        result = b""
        deadline = time.monotonic() + 30
        while len(result) < count:
            timeout = max(0, deadline - time.monotonic())
            if not select.select([process.stdout], [], [], timeout)[0]:
                raise TimeoutError("Native messaging response timed out")
            part = os.read(process.stdout.fileno(), count - len(result))
            if not part:
                raise RuntimeError("Native messaging host closed unexpectedly")
            result += part
        return result

    def request(command, **parameters):
        data = json.dumps({"command": command, **parameters}).encode()
        process.stdin.write(struct.pack("=I", len(data)) + data)
        process.stdin.flush()
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            length = struct.unpack("=I", read_exact(4))[0]
            if length > 1048576:
                raise RuntimeError("Unexpected native message length")
            response = json.loads(read_exact(length))
            if response["command"] == command:
                if "error" in response["message"]:
                    raise RuntimeError("Native host reported an error; sensitive response suppressed")
                return response["message"]
        raise TimeoutError("No matching native messaging response")

    try:
        version = request("getVersion")
        print("Native messaging broker version:", version.get("linuxBrokerVersion", "[absent]"))
        accounts = request("getAccounts").get("accounts", [])
        if len(accounts) != 1:
            raise RuntimeError("Expected exactly one account; explicit selection is required")
        response = request("acquirePrtSsoCookie", account=accounts[0],
                           ssoUrl="https://login.microsoftonline.com/")
        items = response.get("cookieItems", [response])
        if not items or not all(item.get("cookieName") == "x-ms-RefreshTokenCredential"
                                and bool(item.get("cookieContent")) for item in items):
            raise RuntimeError("No valid broker SSO cookie returned")
        print("Framed native messaging acquired genuine SSO cookie data; values/accounts suppressed")
    finally:
        process.stdin.close()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=5)


if __name__ == "__main__":
    main()
