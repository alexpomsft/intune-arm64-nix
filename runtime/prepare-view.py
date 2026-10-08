#!/usr/bin/env python3
from pathlib import Path
import shutil

base = Path(__file__).resolve().parent
view = base / "view/lib"
if view.exists():
    raise SystemExit("Refusing to replace an existing native-library view")
view.mkdir(parents=True)
for source in Path("/usr/lib").iterdir():
    if source.name not in ("arm64-host", "x86_64-linux-gnu", "intune-arm64", "ssl"):
        (view / source.name).symlink_to("/usr/lib/arm64-host/" + source.name)
for name in ("arm64-host", "x86_64-linux-gnu", "intune-arm64"):
    (view / name).mkdir()
(view / "ssl").symlink_to("/etc/ssl")
shutil.copy2(base / "box64-build/box64", view / "intune-arm64/box64")
for name in ("WebKitWebProcess", "WebKitNetworkProcess"):
    shutil.copy2(base / "rootfs/usr/lib/x86_64-linux-gnu/webkit2gtk-4.1" / name,
                 view / "intune-arm64" / name)
print("Prepared native-library aliases and original translated WebKit helpers")
