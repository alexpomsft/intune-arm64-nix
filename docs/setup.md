# Setup runbook: review every state-changing step

This is an unsupported experiment, not an unattended production installer.
Prepare a fresh private runtime and pass the public seccomp/WebKit gates
first. Keep working authentication state and use a test tenant where possible.

## Native certificate support

Use native PCSC/OpenSC packages and enable `pcscd.socket` if needed.
Check that the reader and intended PIV authentication certificate are visible.
Do not publish certificate identities, read private keys, or put a PIN into
shell arguments. Reader detection alone is not successful tenant certificate
authentication.

## Login collection without replacing existing keyrings

The broker hard-codes the Secret Service collection `login`. The tested
desktop initially had a different, unlocked default collection.

If `login` is absent, this native helper creates only that collection and
checks that the existing default alias remains unchanged:

```bash
python3 "$runtime/create-login-keyring.py"
```

Choose the collection's protection in the native GNOME dialog. An encrypted
collection needs an actual unlock path. Fingerprint/autologin does not
automatically provide a password for keyring decryption.

On the tested LUKS-encrypted host, an explicitly approved separate
passwordless collection matched the existing FDE-only keyring model.
That means plaintext keyring storage while the encrypted filesystem is
unlocked; it is **not** separate keyring-file encryption. It was a
machine-specific tradeoff, not the recommended default for everyone.
Automatic availability after reboot was verified on this tested host on
October 8; other hosts still need their own reboot/unlock validation.

Do not copy/rename databases, change the default alias, restart the entire
keyring service, or clear credentials to solve an unrelated renderer issue.
Password complexity compliance is distinct from keyring protection.

## Optional privileged system components

Review the installers and units. They refuse an existing installation rather
than overwriting broker identities or active daemon state.
Never execute a mutable user-owned installer directly as root.

From an interactive terminal, install reviewed root-owned installer copies:

```bash
sudo install -d -m0755 /opt/intune-arm64
sudo install -o root -g root -m0700 "$runtime/install-device-broker" /opt/intune-arm64/install-device-broker
sudo /opt/intune-arm64/install-device-broker "$runtime"
sudo install -o root -g root -m0700 "$runtime/install-daemon" /opt/intune-arm64/install-daemon
sudo /opt/intune-arm64/install-daemon "$runtime"
```

The first copies **package/runtime directories only**, strips special
permission bits/group-other writes, installs the vendor root-only D-Bus
policy, and starts the system device broker. User HOME/XDG state and keyrings
are not copied. `--configure-only` is available solely to finish an already
staged first installation; it is not an upgrade/reset mode.

The second installs the native socket helper and manual daemon/socket units.
No service is enabled at boot and no agent timer is installed.
Do not relax peer validation if custom configuration scripts fail.

Review service state:

```bash
systemctl status microsoft-identity-device-broker.service intune-daemon.service intune-daemon.socket
busctl --system tree com.microsoft.identity.devicebroker1
```

## Enrollment and a manual check-in

Keep the user broker running, open the portal, and complete the native
certificate/PIN flow. Apply the opt-in identity test only with approval, as
described in the README.

The portal writes config registration but this agent reads state registration.
If your agent cannot find it, create a symlink **only when the destination
does not already exist**, never overwrite existing registration:

```bash
mkdir -p "$runtime/state/state/intune"
ln -s "$runtime/state/config/intune/registration.toml" "$runtime/state/state/intune/registration.toml"
INTUNE_COMPAT_OS=ubuntu24.04 "$runtime/run" intune-agent
```

Omit the identity environment variable if the test is not approved.
Look for completed server check-in, not just exit code zero. INFO agent
logs can contain complete tenant policy scripts and account/device identifiers:
keep logs mode 0600, never publish them, and share only carefully redacted
setting names/outcomes.

## Optional native password policy

Do not load the downloaded AMD64 `pam_intune.so` into native ARM64 PAM.
The native `pam_pwquality.so` must already be installed.

The included installer is deliberately specific to the reviewed Arch
`system-auth` stack and the tested rules: length 12 and at least one digit,
lowercase, uppercase and symbol. It refuses unexpected stacks or conflicting
policy aliases. **Check your tenant's actual requirements first.**

After explicit approval:

```bash
sudo install -o root -g root -m0700 "$runtime/install-password-policy" /opt/intune-arm64/install-password-policy
sudo /opt/intune-arm64/install-password-policy
```

It changes only password-provider lines, places native pwquality before the
password providers, makes `pam_unix` consume `use_authtok`, and aliases
`common-password` to the same effective native stack for the agent's reader.
Authentication/account/session lines are verified unchanged. Existing
sudo/SDDM/autologin files are hash-checked, and the original stack is retained
at `/etc/pam.d/system-auth.intune-arm64-backup`.

This governs future password changes, does not read/change the existing
plaintext password, and does not include `enforce_for_root`.
Do not claim all password paths are enforced without reviewing homed,
administrator, or other local account-management paths.
The tested agent reported all five expected numeric settings compliant after
this actual enforcement change; no fabricated policy/runtime records were used.

## Stop, do not reset

Close the experimental portal and stop only the specific broker process you
started. Other Microsoft/browser/WebKit processes may belong to unrelated apps.

```bash
sudo systemctl stop intune-daemon.socket intune-daemon.service microsoft-identity-device-broker.service
```

Stopping these services does not unenroll or delete device identity. Preserve
registration files, private identity keys and credential collections.
Before undoing native password enforcement, review the saved PAM backup and
restore through your normal administrator process; do not blindly overwrite
later system updates.

## Startup and reboot

After an explicitly approved enrollment and successful manual check-in,
persistence can be installed separately from unresolved custom compliance.
It does not repair privileged caller validation, authorize tenant scripts as
root, or imply that full tenant compliance passes.

The startup installers preserve the enrolled runtime, registration, existing
keyring defaults and authentication configuration. They require the existing
reviewed root installation and refuse conflicting activation/unit files.
They do not reinstall PAM or copy user credential state into the root runtime.

From this source checkout, stage the reviewed system activation sources in a
root-controlled directory before executing the root installer:

```bash
sudo install -d -o root -g root -m0755 /opt/intune-arm64/startup
sudo install -o root -g root -m0700 \
  runtime/install-system-startup runtime/device-broker-activation.service \
  runtime/intune-daemon.socket runtime/device-broker-run runtime/daemon-run \
  runtime/intune-daemon.service /opt/intune-arm64/startup/
sudo /opt/intune-arm64/startup/install-system-startup
python3 scripts/install-user-startup "$runtime"
```

If the namespace-only identity test was separately approved, add
`--compat-os ubuntu24.04` to the **user installer**. This persists the opt-in
identity only in the agent service, not the user broker, root services,
global environment or host OS files. The inventory caveat still applies.

Stop only the previously manually launched user broker, then:

```bash
systemctl --user start microsoft-identity-broker.service intune-agent.timer
systemctl --user start intune-agent.service
python3 "$runtime/verify-startup.py" --check-browser-host
```

The guarded root upgrade accepts only the exact reviewed previous launchers
or current versions. It adds a private `/opt` mount layout and bounds daemon
shutdown to 20 seconds, without relaxing root hardening.
The user installer requires the launcher with private journal isolation;
it will not silently run a new logging wrapper against an older launcher.

The installation provides:

- A system D-Bus activation file delegating device-broker startup to the
  existing hardened root unit, with no direct-execution fallback.
- The existing daemon socket enabled under `sockets.target`; the daemon
  remains socket-activated, not a second separately enabled boot service.
- A `Type=dbus` user broker enabled under `graphical-session.target`,
  `PartOf` the session, gated on imported `DISPLAY`, and restarted on failure.
  User D-Bus activation provides an additional recovery path.
- An agent timer five minutes after timer activation, then hourly, with
  up to one minute of randomized delay and 30-second accuracy.

Omarchy/uwsm imports display environment before activating the graphical
target. `After` alone would not prevent a headless/SSH start, hence the
explicit display condition. The Siemens host checks broker availability
before normal requests: D-Bus-only activation is insufficient for ordinary
extension startup. The graphical session must proactively start the broker.

### Private check-in diagnostics

The scheduled wrapper retains an at-most-8-MiB tail of the last agent run in
`$runtime/state/state/intune/checkin-last.log`, mode 0600. Even INFO logs can
contain complete tenant scripts: **never publish this file**.
The agent unit's journal receives only server-confirmation status and aggregate
setting outcomes, not raw agent output. The launcher also masks
`/run/systemd/journal` inside this agent-only namespace: stdout redirection
alone did not prevent Intune's direct journal writes. Broker/daemon journals
remain private diagnostic sources and must not be exported unreviewed.

`checkin-status.json` in the same private directory records the exit status,
both required server-completion markers, aggregate setting outcomes, completion
time and current boot ID. Exit zero without server confirmation is a failure.
Missing retained policy reporting is represented as `null`, not zero errors.
Unsafe log/status symlinks are rejected.

The verifier checks enabled/active units, unlocked collection metadata,
the agent service result, and a recent confirmed check-in from this boot.
`--check-browser-host` additionally acquires a real SSO cookie through native
messaging without printing account/cookie values. This is not proof of
interactive Outlook access or full tenant compliance.

### Actual reboot gate

Save work and approve a reboot explicitly; installation does not reboot.
After graphical login, allow roughly six to seven minutes for the initial
timer, then run:

```bash
python3 "$runtime/verify-startup.py" --check-browser-host
systemctl --user list-timers intune-agent.timer
```

Check Outlook interactively in the existing Chromium work profile. Do not
manually start brokers or recreate credentials before this check: doing so
would hide a startup failure. A previous boot's status cannot pass the
this-boot check. If networking was unavailable during the first run, retry
only `systemctl --user start intune-agent.service`; record that as a manual
retry rather than automatic reboot success.

### Stop persistence without deleting enrollment

```bash
systemctl --user disable --now intune-agent.timer microsoft-identity-broker.service
systemctl --user stop intune-agent.service
sudo systemctl disable --now intune-daemon.socket
```

D-Bus activation files still permit on-demand startup after those commands.
For a full rollback, remove only the two activation files installed by this
runbook (the user `com.microsoft.identity.broker1.service` and system
`com.microsoft.identity.devicebroker1.service`), reload each bus with
`org.freedesktop.DBus.ReloadConfig`, and stop the root broker/daemon.
Do not restart the entire system/user bus or keyring daemon. Preserve
registration, `/etc/microsoft/identity-broker/`, and keyring databases.
