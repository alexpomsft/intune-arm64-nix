# intune-arm64-nix

An experimental way to run the proprietary AMD64 Microsoft Intune Linux
client and identity broker on an ARM64 Linux host, using a private Box64
runtime and native bubblewrap/WebKit sandbox helpers.

**Enrollment, automatic post-reboot server check-ins and Chromium SSO worked on an Apple M2 Max running
Arch Linux ARM/Omarchy with 16 KiB pages. This is not a supported Microsoft
configuration, a compliance bypass, or a finished Nix integration.** Despite
the repository name, there is currently no Nix flake, derivation, or NixOS
module. The implementation below is the tested Arch-oriented prototype.

## What worked, and what did not

Enrollment/browser results observed October 7, 2026; startup work October 8:

| Capability | Result |
|---|---|
| YubiKey PIV certificate sign-in | Worked through the existing native PCSC service |
| Existing Secret Service integration | Worked; existing default collection preserved |
| JavaScript-enabled Microsoft login form | Rendered with TLS verification and renderer sandboxing |
| Device enrollment | Server accepted enrollment; client saved device registration |
| Agent check-ins | Manual and supervised server check-ins confirmed, with native password-policy outcomes |
| Native password enforcement | Five required settings reported compliant after an explicitly approved native PAM change |
| Disk encryption | Reported compliant on the tested LUKS-encrypted host |
| Host OS identity | Remained Arch ARM; optional Intune namespace reported Ubuntu 24.04 |
| Tenant custom configuration | Two privileged scripts failed |
| Tenant custom compliance | Remained unknown |
| Browser Conditional Access / Outlook | User confirmed Outlook works in native ARM64 Chromium with the pinned Siemens SSO bridge |
| User broker startup and recovery | Supervised graphical-session startup and cold user-D-Bus activation verified |
| Root boot activation and scheduled check-ins | Installed; cold system-D-Bus/socket activation and supervised check-in verified |
| Real reboot / automatic keyring availability | Verified October 8: automatic current-boot check-in, unlocked collections and native browser SSO |

Successful enrollment is **not** proof of full compliance or browser access.
The optional Ubuntu identity also makes distro/version inventory inaccurate:
those passes do not prove that an Arch ARM machine meets an Ubuntu policy.
Get your organization's approval before using this with a work tenant.

## Why emulation?

Microsoft's tested Intune `1.2609.5-noble` and identity broker `3.0.2-noble`
packages are AMD64 binaries. The community packaging projects repackage
these proprietary executables; recompiling a PKGBUILD does not produce an
ARM64 client. A VM would enroll the guest, not this host.

This project contains **our source tooling and a Box64 patch only**.
Microsoft executables and Ubuntu libraries are downloaded from their
respective repositories into a private runtime, never committed here.

## Prerequisites

The tested environment is ARM64 Arch Linux with a graphical desktop,
XWayland, systemd, user/system D-Bus, GNOME Keyring Secret Service, native
bubblewrap, native libseccomp headers, a C compiler, CMake, Ninja, Git,
Python, pkg-config and `bsdtar`.

Install prerequisites using your distribution's normal package manager.
On Arch, relevant packages include `base-devel`, `cmake`, `ninja`, `git`,
`python`, `libarchive`, `bubblewrap`, `libseccomp`, `gnome-keyring`,
`libsecret`, `python-gobject`, `gcr-4` and `xorg-xwayland`. Certificate
authentication additionally needs native `ccid`, `opensc`,
`yubico-piv-tool` and `pcsc-tools`, and a running `pcscd.socket`.
Existing desktop installations may already provide most of these.

Do not replace a working fingerprint stack, keyring default, autologin
configuration, or native TPM libraries as a preparatory step.

## Prepare and verify a private runtime

```bash
git clone https://github.com/alexpomsft/intune-arm64-nix.git
cd intune-arm64-nix
./scripts/prepare-runtime
```

The default destination is `${XDG_DATA_HOME:-$HOME/.local/share}/intune-arm64`.
An explicit first argument selects a different destination. **Existing
destinations are refused**, protecting an enrolled prototype.

Provisioning downloads the pinned Microsoft packages, checks their hashes,
extracts Ubuntu AMD64 dependencies without running Debian maintainer scripts,
fetches the pinned Box64 revision, applies the seccomp bridge patch, builds
native helpers, and creates private library aliases.
It performs no root installation, global binfmt registration, PAM changes,
OS identity changes, keyring creation, enrollment, or service enablement.

Ubuntu Release/index/package SHA256 chains are checked over HTTPS, but
Release GPG signatures are **not** verified. Dependency resolution is a
simple experimental traversal, not a Debian version solver. Ubuntu library
versions can change independently of the pinned Microsoft packages.
See [architecture and provenance](docs/architecture.md).

Before submitting any credentials:

```bash
runtime="${XDG_DATA_HOME:-$HOME/.local/share}/intune-arm64"
./scripts/verify-seccomp "$runtime"
python3 "$runtime/verify-webkit.py"
```

The first gate constructs rules through translated libseccomp and proves
kernel denial of native `getpid` and argument-filtered `close` in a disposable
child. The second loads the **real public login form**, requires an enabled,
visible username input, and checks renderer namespace isolation,
`NoNewPrivs=1`, `Seccomp=2`, renderer dynarec mode and interpreted network mode.
Neither gate uses credentials or establishes tenant enrollment.

## Authentication and enrollment

Read the [setup runbook](docs/setup.md) before installing privileged services
or creating a keyring. Those operations are deliberately separate from
runtime preparation.

Start the user broker from a terminal and leave it running:

```bash
"$runtime/run" microsoft-identity-broker
```

In another terminal:

```bash
"$runtime/run" intune-portal
```

Use only native graphical authentication dialogs for passwords and YubiKey
PINs. Never pass them in command arguments, environment variables or logs.
Do not reset working credential caches after every UI failure.

### Optional OS identity compatibility test

On the tested rolling-release Arch host, the Terms API received an empty
`os-version` and returned HTTP 400. With explicit consent, this opt-in
namespace-only compatibility test supplied Ubuntu 24.04 metadata:

```bash
INTUNE_COMPAT_OS=ubuntu24.04 "$runtime/run" intune-portal
INTUNE_COMPAT_OS=ubuntu24.04 "$runtime/run" intune-agent
```

The Terms request changed to `os-version=24.04` and returned HTTP 200;
enrollment subsequently succeeded. The host's OS files are not modified,
and the default launcher keeps the genuine host identity.

**This reports an inaccurate distro to Intune. It does not make ARM64/Arch
officially supported.** Do not silently enable it, use it to claim genuine
Ubuntu compliance, or misrepresent the host to your administrator.

## Important limits

The system services are narrowly scoped, with optional persistent activation
described in the [startup runbook](docs/setup.md#startup-and-reboot). The daemon's caller
validation has not been adapted to translated processes: a portal cache-clear
call returned `PeerValidationFailed`, and privileged configuration scripts
failed. This project does not disable that validation or automatically
execute tenant scripts as root.

The Microsoft AMD64 `pam_intune.so` cannot be loaded by native ARM64 PAM.
Optional native `pam_pwquality` enforcement is separate and requires review.
Browser device identity is separate too: Microsoft's Linux documentation
uses Edge signed into a work profile. Chromium being based on the same engine
does not establish that integration. The tested community Siemens bridge
does: the native Python host acquired genuine broker SSO cookies, its framed
native-messaging protocol was verified, and the user confirmed Outlook access
in ARM64 Chromium after enabling the signed extension. Follow the
[Chromium runbook](docs/troubleshooting.md#native-arm64-chromium-bridge).
This is not a guarantee that every Conditional Access policy or custom
compliance requirement will pass.

## Repository contents

`runtime/` contains the portable launchers, helpers, dependency fetchers,
diagnostic probes, systemd units and guarded opt-in installers.
`scripts/` prepares and verifies a fresh runtime.
`patches/` contains the native libseccomp bridge against the pinned Box64.
`docs/` explains setup, preservation guarantees, failure analysis and limits.

There are no Microsoft binaries, dependency archives, logs, keyrings,
certificates, private keys, account/tenant/device state, or tenant scripts.

## Sources and attribution

- [Microsoft Intune Linux installation requirements](https://learn.microsoft.com/en-us/intune/user-help/company-portal/intune-app-linux)
- [Microsoft Linux enrollment and Edge requirements](https://learn.microsoft.com/en-us/intune/user-help/enrollment/enroll-linux)
- [Microsoft standard Linux compliance settings](https://learn.microsoft.com/en-us/intune/device-security/compliance/ref-linux-settings)
- [Sverre's Intune packaging and Arch troubleshooting](https://github.com/sverrejoh/intune-portal-bin)
- [Box64](https://github.com/ptitSeb/box64) and [earlier Intune discussion](https://github.com/ptitSeb/box64/issues/1647)
- [Siemens Linux Entra SSO](https://github.com/siemens/linux-entra-sso), a separately downloaded MPL-2.0 native host/extension
- [Microsoft ARM package request](https://github.com/microsoft/linux-package-repositories/issues/146)

Our tooling is MIT licensed. Box64 patch context retains its upstream MIT
terms in [LICENSES/Box64-MIT.txt](LICENSES/Box64-MIT.txt). Downloaded Microsoft
and Ubuntu software remains subject to its own licenses; our MIT license
does not relicense it.
