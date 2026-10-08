#!/usr/bin/env python3
import argparse
import importlib.util
from pathlib import Path
import re


def main():
    parser = argparse.ArgumentParser(description="Test genuine broker SSO without printing accounts or cookies")
    parser.add_argument("host", type=Path, help="Reviewed upstream linux-entra-sso.py")
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("upstream_sso", args.host)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load the upstream native host")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    broker = module.SsoMib()
    if not broker.check_broker_online():
        raise RuntimeError("The experimental user identity broker is not running")
    response = broker.get_accounts()
    accounts = response.get("accounts", [])
    print("Broker account count:", len(accounts))
    if len(accounts) != 1:
        raise RuntimeError("Expected exactly one account; explicit account selection is required")
    cookie = broker.acquire_prt_sso_cookie(accounts[0], "https://login.microsoftonline.com/")
    if "error" in cookie:
        error = cookie["error"]
        print("Broker rejected the SSO request; error values suppressed")
        if isinstance(error, dict):
            for key in ("code", "errorCode", "statusCode"):
                value = str(error.get(key, ""))
                if re.fullmatch(r"[A-Za-z0-9_-]{1,80}", value):
                    print(key + ":", value)
        raise RuntimeError("No broker SSO cookie acquired")
    items = cookie.get("cookieItems", [cookie])
    if not items or not all(isinstance(item.get("cookieContent"), str)
                            and bool(item["cookieContent"]) for item in items):
        raise RuntimeError("Broker did not return nonempty SSO cookie data")
    if not all(item.get("cookieName") == "x-ms-RefreshTokenCredential" for item in items):
        raise RuntimeError("Unexpected broker cookie name")
    print("Genuine broker PRT SSO cookie acquired; value not printed or saved")
    print("This verifies acquisition only, not Chromium injection or Conditional Access success")


if __name__ == "__main__":
    main()
