# Reproduction record and publishing boundary

## Original host result

On October 7, 2026, the prototype ran on an Apple M2 Max with 16 KiB kernel
pages, Arch Linux ARM and Omarchy/Hyprland. The installed Microsoft clients
were extracted AMD64 packages, not native ARM builds.

Certificate sign-in, real enrollment and completed server check-ins worked.
Native ARM64 pwquality enforcement met the five tested password thresholds;
the LUKS-encrypted device passed the client's encryption check.
Native Chromium subsequently accessed Outlook using the existing broker and
the signed Siemens Linux Entra SSO extension.

The original default keyring alias, separate login collection alias and
genuine host OS identity were checked intact after the setup. Password-change
enforcement was explicitly approved; fingerprint/login authentication and
autologin were preserved. Reboot/background persistence was subsequently
verified October 8 as recorded below; complete tenant custom policy compliance
remains unresolved.

## Fresh source reproduction

A separate, fresh runtime was prepared from this repository without
overwriting the enrolled installation. It:

1. Downloaded and verified both pinned Microsoft packages.
2. Indexed/extracted Ubuntu AMD64 dependencies.
3. Applied the complete patch to the pinned clean Box64 checkout.
4. Built Box64 and both native C helpers.
5. Passed actual native kernel syscall-denial checks.
6. Rendered the real public Microsoft login form with enabled input and
   verified renderer mount/PID isolation, NNP/seccomp and split execution modes.

Source-only unit checks cover package-pin shapes, index parsing, opt-in
identity/sandbox settings and absence of the original user home path.
Startup checks also exercise bounded private logs, symlink refusal, safe
policy summaries, exit-zero without server confirmation, unit path escaping,
and rejection of a previous boot's successful status.
Native Chromium host framing was verified separately; real Outlook access
was confirmed interactively, not inferred from a successful token call.

Fresh enrollment was not repeated in the new runtime because that would
create an additional work device and duplicate sensitive state. Root
installers/PAM were not rerun from the new repository against the working
installation. Portability improvements to installer arguments were
syntax-checked; they are not proof of a second root deployment.

## Startup implementation

On October 8, the user broker was moved from its exact manually launched
process into the graphical-session `Type=dbus` unit without resetting cached
credentials. Cold user-D-Bus activation worked; native messaging subsequently
acquired a genuine SSO cookie. Native inspection confirmed that the D-Bus
owner belonged to the supervised service cgroup. Both original collection
aliases remained unchanged and unlocked, and saved PAM/sudo/SDDM/autologin
hashes still matched.

The daemon socket and graphical-session agent timer are enabled. Cold system
D-Bus activation and cold daemon socket activation both succeeded after
fixing the private `/opt` mountpoint dependency. Native root payload
inspection again confirmed UID 0, zero effective capabilities and
`NoNewPrivs=1`; no host Microsoft executable directory was created.

Supervised agent runs completed actual server check-ins, retaining 17
`Compliant`, two `Error` and one `Unknown` setting outcomes. The same two
custom configuration failures and unknown custom compliance remain.
Direct agent journald writes initially bypassed stdout capture. After
masking journal endpoints in the agent-only namespace, another real check-in
completed with zero raw agent/identity entries in the new service journal
interval. Both required completion markers remained in the private log.

The durable verifier passed for the current boot, including genuine framed
native-messaging cookie acquisition and unlocked collection metadata.
After an explicitly approved reboot on October 8, the user reported that
things were working. Verification without manually starting services or
running an agent passed: the enabled timer triggered at 10:59:52 CEST,
the agent completed a confirmed server check-in in the new boot, both
collections were unlocked, and framed native messaging acquired a genuine
broker SSO cookie. The timer remained active with its next run scheduled.
Saved PAM/sudo/SDDM/autologin hashes matched, and host OS identity remained
`archarm`. Startup/reboot persistence is therefore verified on this host.
The user reported working behavior generally; this was not a separately
instrumented interactive Outlook test. Two setting errors and one unknown
outcome remain, so reboot success is not full tenant compliance.

## Local source checks

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q runtime scripts
bash -n scripts/prepare-runtime runtime/run runtime/device-broker-run runtime/daemon-run runtime/install-device-broker runtime/install-daemon
```

The source has no Nix integration yet. A future Nix port must provide native
host dependencies, FHS-compatible guest paths, writable private state,
Secret Service/PCSC/D-Bus integration and the same actual sandbox gates.
Changing architecture metadata alone is not a native Intune build.

## Before publishing

Publish only source, patches and these sanitized documents. The runtime,
downloads, compiled helpers, upstream checkouts, logs and state are ignored.
Never add tenant scripts or authenticated diagnostic bodies.

No GitHub repository is required to build locally. Publishing is an explicit
later action; do not assume successful GitHub authorization or push as part
of preparing this source tree.
