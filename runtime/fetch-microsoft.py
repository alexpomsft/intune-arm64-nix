#!/usr/bin/env python3
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess
import urllib.request

BASE = Path(__file__).resolve().parent
SERVER = "https://packages.microsoft.com/ubuntu/24.04/prod/"
INDEX = SERVER + "dists/noble/main/binary-amd64/Packages.gz"


def fields(text):
    result = {}
    key = None
    for line in text.splitlines():
        if line.startswith(" ") and key:
            result[key] += "\n" + line
        elif ":" in line:
            key, value = line.split(":", 1)
            result[key] = value.lstrip()
    return result


def main():
    versions = json.loads((BASE / "versions.json").read_text())["microsoft_packages"]
    root = BASE / "rootfs"
    cache = BASE / "downloads"
    root.mkdir(exist_ok=True)
    cache.mkdir(exist_ok=True)
    with urllib.request.urlopen(INDEX, timeout=120) as response:
        packages = [fields(p) for p in gzip.decompress(response.read()).decode().split("\n\n")]
    dependencies = set()
    for name, pin in versions.items():
        matches = [p for p in packages if p.get("Package") == name
                   and p.get("Version") == pin["version"] and p.get("Architecture") == "amd64"]
        if len(matches) != 1:
            raise RuntimeError(f"Pinned Microsoft package not found uniquely: {name} {pin['version']}")
        package = matches[0]
        if package["SHA256"] != pin["sha256"]:
            raise RuntimeError(f"Microsoft index differs from reviewed checksum: {name}")
        filename = package["Filename"]
        if filename.startswith("/") or ".." in Path(filename).parts:
            raise RuntimeError(f"Unexpected package path: {name}")
        archive = cache / Path(filename).name
        if not archive.exists():
            with urllib.request.urlopen(SERVER + filename, timeout=120) as response:
                archive.write_bytes(response.read())
        if hashlib.sha256(archive.read_bytes()).hexdigest() != pin["sha256"]:
            raise RuntimeError(f"Microsoft package checksum mismatch: {name}")
        members = subprocess.check_output(["bsdtar", "-tf", str(archive)], text=True).splitlines()
        payload = next(m for m in members if m.startswith("data.tar"))
        extract = subprocess.Popen(["bsdtar", "-xOf", str(archive), payload], stdout=subprocess.PIPE)
        try:
            subprocess.run(["bsdtar", "-xf", "-", "-C", str(root)], stdin=extract.stdout, check=True)
        finally:
            extract.stdout.close()
        if extract.wait():
            raise RuntimeError(f"Failed to extract {name}")
        for group in ",".join([package.get("Pre-Depends", ""), package.get("Depends", "")]).split(","):
            dependency = re.split(r"[\s:(\[]", group.strip().split("|")[0], maxsplit=1)[0]
            if dependency and dependency not in versions:
                dependencies.add(dependency)
        print(f"Extracted verified {name} {pin['version']}; no maintainer scripts executed")
    (BASE / "dependency-seeds.txt").write_text("\n".join(sorted(dependencies)) + "\n")


if __name__ == "__main__":
    main()
