# Architecture, provenance and diagnostic findings

## Process boundaries

The private user launcher isolates HOME and all XDG application state while
retaining the desktop user's D-Bus, Secret Service, display and PCSC access.
Native bubblewrap mounts the host filesystem read-only, exposes `/dev` and a
fresh `/proc`, and permits writes to private application state and `/tmp`.
A writable Intune-only user-runtime directory handles the client's
hard-coded `/run/user/<uid>/intune` path without hiding desktop/keyring sockets.

A symlink library view exposes native ARM libraries through
`/usr/lib/arm64-host` and extracted AMD64 libraries through
`/usr/lib/x86_64-linux-gnu`. Thousands of individual bind arguments are avoided.
Native and guest fonts/library layouts are not installed into host directories.

The root device broker and daemon use a separately copied, root-owned runtime
at `/opt/intune-arm64`, not mutable user executables. Their units apply
`NoNewPrivileges`, read-only system/home protection and private temporary
files. Native bubblewrap drops child capabilities. The device broker can
write identity storage, and the daemon can write only its relevant state.
Only root can own the system device-broker D-Bus name.

Cold startup exposed a previously hidden mountpoint dependency:
`/opt/microsoft` did not exist on the host, and read-only root protection
prevented bubblewrap creating it. Both root launchers now mount a private
tmpfs at `/opt`, expose the immutable runtime and Microsoft package tree
within it, and remount `/opt` read-only. No host `/opt/microsoft` directory
or executable alias is installed. Actual cold activation retained native
UID 0, zero effective capabilities and `NoNewPrivs=1`.

The daemon retains the vendor socket path/mode. A native helper checks
inherited fd 3 and exactly one activation descriptor, then resets `LISTEN_PID`
after bubblewrap's fork. The tested bubblewrap retained the fd by default;
its version did not implement `--preserve-fds`.

These boundaries are not a general guarantee that every guest syscall has
native Linux semantics or that the host is fully isolated from client code.

## WebKit sandbox bridge

Translated libseccomp originally exported x86-64 syscall filters. Native
ARM64 bubblewrap applied them to ARM64 processes, causing a sandbox helper to
die with SIGSYS before the page rendered.

The Box64 patch wraps four libseccomp exports: initialization, release, BPF
export and rule addition. Rule addition resolves the guest x86-64 syscall
number to its name, resolves that name to the native syscall number, and
passes argument comparisons to native `seccomp_rule_add_array`.
Unsupported mappings/counts fail explicitly.

The AMD64 variadic comparison structs are 24 bytes and passed on the guest
stack; the wrapper takes them from `RSP+8`. Unconditional and argument-filtered
kernel denial were verified. This is a narrow wrapper, not a complete
libseccomp compatibility layer.

Box64 ignores some guest seccomp/prctl requests. **Do not claim generic guest
seccomp works.** The renderer's real ARM64 filter and namespace restrictions
are installed by native bubblewrap, checked through native `/proc`.

## Session supervision and private check-ins

The user broker proactively starts with the graphical target because the
Chromium SSO host checks availability before calling it. D-Bus activation
alone does not satisfy that normal startup path. The unit requires imported
`DISPLAY`, owns the real broker name and follows graphical-session shutdown.

The agent timer runs a native wrapper against the existing enrolled state.
Agent output is retained in a bounded private last-run log; the agent-only
namespace masks the native journal endpoints because the client also writes
directly to journald. The service journal contains only safe wrapper
summaries/systemd metadata. Status is atomic, mode 0600, and tied to a boot
ID; verification rejects an old boot's success and an unconfirmed exit zero.
Neither scheduling nor logging isolation changes policy evaluation or
privileged caller validation.

## Allocator and execution modes

JavaScriptCore required:

```text
Malloc=1
JSC_useJIT=false
JSC_useWasm=false
```

These disable JSC-specific allocation/JIT paths, not page JavaScript.
A standalone probe verified context creation, evaluation of `1 + 1`, and
release. A web probe subsequently verified actual login-form JavaScript.

Translated GnuTLS signature verification failed with Box64 dynarec but
succeeded under interpretation. No certificate-verification bypass was used.
The native WebKit helper forces network-process interpretation and
web-process dynarec regardless of the parent's execution mode.
Interpreting the renderer did not yield a usable login form within 60 seconds;
the split-mode probe did.

The portal defaults to dynarec for responsiveness; the broker/agent/root
services default to interpretation. Set `BOX64_DYNAREC=0` and invoke the
absolute portal ELF path through `run` when specifically reproducing an
interpreted portal backend.

Ubuntu OpenSSL's expected trust layout is supplied by host CA settings and a
private `/usr/lib/ssl` alias. TLS verification and dynamic certificate pinning
remain enabled. Some media-plugin and Mesa shutdown warnings persisted.

## Versions and trust

The exact tested Microsoft versions, SHA256 values and Box64 commit are in
`runtime/versions.json`. Box64 is fetched from upstream at that revision and
patched; it is not a published upstream feature.

Microsoft packages are checked against both pinned SHA256 values and the
HTTPS package index. Ubuntu compressed indexes are checked against Release
SHA256 entries, and packages against index SHA256 values. Release GPG
signatures are not checked. No Debian maintainer script runs.

The Ubuntu dependency fetcher prioritizes security, updates and release
pockets, choosing available alternatives/providers. It does not implement
Debian's full version constraints. Dependency versions are not locked.
This is experimental provisioning, not a production supply-chain solution.

QEMU user emulation was tried during diagnosis but is not required by this
implementation. No global QEMU/Box64 binfmt registration is used.

## Deliberately absent

There is no automatic keyring-default change, fingerprint-stack replacement,
autologin removal, global distro spoof, TPM downgrade, credential reset,
CSR shim or Edge installation. Reviewed, separate opt-in startup installers
provide user broker supervision/D-Bus activation, daemon socket boot enablement
and an agent timer without changing those authentication boundaries.
A separate, opt-in native Chromium SSO host is
included; its actual broker/native-messaging path and Outlook sign-in were
verified with the signed upstream extension. It requires the user broker to
remain running; graphical-session startup supplies that prerequisite.
