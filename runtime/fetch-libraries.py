#!/usr/bin/env python3
import hashlib
import lzma
import re
import subprocess
import sys
import urllib.request
from collections import deque
from pathlib import Path

BASE = Path(__file__).resolve().parent
CACHE = BASE / "downloads"
ROOT = BASE / "rootfs"
CACHE.mkdir(exist_ok=True)
ROOT.mkdir(exist_ok=True)


def fetch(url, path, digest=None):
    if not path.exists():
        with urllib.request.urlopen(url, timeout=120) as response:
            data = response.read()
        if digest and hashlib.sha256(data).hexdigest() != digest:
            raise RuntimeError(f"Checksum mismatch: {url}")
        path.write_bytes(data)
    if digest and hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise RuntimeError(f"Checksum mismatch: {path}")
    return path.read_bytes()


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


packages = {}
providers = {}
# Security and updates take precedence over the release pocket.
for server, suite in [
    ("https://security.ubuntu.com/ubuntu", "noble-security"),
    ("https://archive.ubuntu.com/ubuntu", "noble-updates"),
    ("https://archive.ubuntu.com/ubuntu", "noble"),
]:
    release = fields(
        fetch(f"{server}/dists/{suite}/Release", CACHE / f"{suite}-Release").decode()
    )
    checksums = {
        entry.split()[2]: entry.split()[0]
        for entry in release["SHA256"].splitlines()
        if entry.strip()
    }
    for component in ["main", "universe"]:
        member = f"{component}/binary-amd64/Packages.xz"
        data = fetch(
            f"{server}/dists/{suite}/{member}",
            CACHE / f"{suite}-{component}-Packages.xz",
            checksums[member],
        )
        for paragraph in lzma.decompress(data).decode().split("\n\n"):
            package = fields(paragraph)
            if not package:
                continue
            name = package["Package"]
            package["Server"] = server
            packages.setdefault(name, package)
            for provided in package.get("Provides", "").split(","):
                provided = provided.strip().split(" ", 1)[0]
                if provided:
                    providers.setdefault(provided, name)
        print(f"Indexed {suite}/{component}", flush=True)

queue = deque(sys.argv[1:])
seen = set()
while queue:
    name = queue.popleft()
    if name in seen:
        continue
    name = providers.get(name, name) if name not in packages else name
    if name not in packages:
        raise RuntimeError(f"No AMD64 package for dependency: {name}")
    if name in seen:
        continue
    seen.add(name)
    package = packages[name]
    archive = CACHE / Path(package["Filename"]).name
    fetch(
        f'{package["Server"]}/{package["Filename"]}',
        archive,
        package["SHA256"],
    )
    members = subprocess.check_output(["bsdtar", "-tf", str(archive)], text=True)
    payload = next(member for member in members.splitlines() if member.startswith("data.tar"))
    extract = subprocess.Popen(
        ["bsdtar", "-xOf", str(archive), payload], stdout=subprocess.PIPE
    )
    try:
        subprocess.run(
            ["bsdtar", "-xf", "-", "-C", str(ROOT)],
            stdin=extract.stdout,
            check=True,
        )
    finally:
        extract.stdout.close()
    if extract.wait():
        raise RuntimeError(f"Failed to extract {archive}")
    print(f'{name} {package["Version"]}', flush=True)
    for group in ",".join(
        [package.get("Pre-Depends", ""), package.get("Depends", "")]
    ).split(","):
        if not group.strip():
            continue
        alternatives = [
            re.split(r"[\s:(\[]", alternative.strip(), maxsplit=1)[0]
            for alternative in group.split("|")
        ]
        dependency = next(
            (item for item in alternatives if item in packages or item in providers),
            None,
        )
        if dependency is None:
            raise RuntimeError(f"Unresolved dependency of {name}: {group}")
        queue.append(dependency)

print(f"Extracted {len(seen)} packages; no maintainer scripts executed.")
