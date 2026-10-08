# Troubleshooting without credential resets

## Distinguish the layers

Public metadata loading does not prove the login form renders.
Certificate unlock does not prove credentials were cached.
Credential caching does not prove device enrollment.
Enrollment/check-in does not prove complete compliance.
Compliance does not prove the browser sends a registered-device claim.

## Observed failures

| Symptom | Established finding / response |
|---|---|
| JSC crash/allocator fault | Standalone reproduction; `Malloc=1`, JSC JIT/Wasm disabled |
| Embedded page appears offline | Missing Ubuntu CA path; supply host trust through private paths, never disable verification |
| Sandbox helper SIGSYS | Guest libseccomp BPF applied to native ARM64; use the native syscall-name bridge |
| Post-email modal blank | Broker-parent interpreter mode leaked to renderer; native helper explicitly selects renderer/network modes |
| `4rfhk` | Interactive request already in progress; stop only the exact experimental user broker, preserve caches |
| `4kv4v`, libsecret error 19 | Required `login` collection absent; create it separately without changing default |
| Terms-of-Use HTTP 400 | Rolling-release host supplied empty OS version; approved namespace identity test changed request to 24.04 and HTTP 200 |
| Agent says another instance runs | Native trace showed `mkdirat` failed with EROFS at the hard-coded user runtime path, not a second agent |
| Agent cannot find registration | Portal config/state path mismatch; guard an explicit symlink, never reset registration |
| Password-policy values zero | No effective native pwquality enforcement / no recognized policy-reader path |
| `PeerValidationFailed` | Privileged daemon caller integration unresolved; do not disable checks |
| Custom configuration `Error`, custom compliance `Unknown` | Successful check-in still leaves tenant policy failures |

An unsupported OS subtype remained `None` even after Terms succeeded.
Do not assume that field alone caused the HTTP 400, or that every future 400
has the same cause. Obtain request/error metadata without leaking authorization.

## Browser says "device isn't registered"

This can mean the browser supplied no device identity claim, not that the
Intune enrollment disappeared.
Microsoft's [Linux enrollment instructions](https://learn.microsoft.com/en-us/intune/user-help/enrollment/enroll-linux)
use Microsoft Edge signed into a work/school profile for protected resources.
Chromium being Chromium-based does not provide that supported integration.

Initially, Chromium was the installed/default browser and Outlook reported
an unregistered device. Edge had no available native binary for this setup,
so the native community bridge below was installed instead. An unsupported
ARM64 Edge/emulation path is a separate problem.
Do not promise that merely switching a default browser fixes it.
Broker/native browser integration and tenant compliance still need proof.

Do not fabricate browser/device compliance claims, extract raw keyring tokens,
or delete the enrollment as the first response. The community bridge described
below requests a genuine broker-minted PRT SSO cookie; it does not manufacture
device identity or override Conditional Access.

### Native ARM64 Chromium bridge

The reviewed [Siemens Linux Entra SSO](https://github.com/siemens/linux-entra-sso)
host is Python and works natively on ARM64. Its Chromium extension uses
Manifest V3 and `declarativeNetRequest` on the Microsoft login origin.
It uses the existing user broker's `acquirePrtSsoCookie` method, so no Edge
binary is required by this community integration.

The reviewed revision is pinned by `scripts/install-chromium-sso`. Install
native `python-gobject` and `python-pydbus`, then:

```bash
git clone https://github.com/siemens/linux-entra-sso.git
git -C linux-entra-sso checkout e25c215735b8b365ceb7b5f395480119230970c4
python3 scripts/install-chromium-sso ./linux-entra-sso
python3 runtime/probe-browser-sso.py ./linux-entra-sso/linux-entra-sso.py
python3 runtime/probe-native-messaging.py "${XDG_CONFIG_HOME:-$HOME/.config}/chromium/linux-entra-sso"
```

Install the signed
[Linux Entra SSO extension](https://chromewebstore.google.com/detail/linux-entra-sso/jlnfnnolkbjieggibinobhkjdfbpcohn)
and reload it after installing the native host. The installer grants native
messaging access only to that extension ID and refuses existing artifacts.
It retains the upstream MPL license and uses the native system Python, not
the emulated guest or a version-manager interpreter.

The probe checks that the broker returns nonempty genuine SSO cookie data
without printing/saving accounts or cookies. The installed host's actual
framed native-messaging protocol was also verified against broker 3.0.2.
After the extension was reloaded/enabled with the work account, the user
confirmed Outlook sign-in worked in native ARM64 Chromium.

Cookie acquisition alone would not have established that outcome; use the
real protected resource to verify your own configuration. Keep the
experimental broker running. Its automatic D-Bus activation/reboot
persistence remains unfinished, and other custom policy errors can remain.

This third-party integration uses an undocumented broker protocol and is
not Microsoft's supported Edge workflow. Review upstream permissions/privacy
and test against your organization's policies. Do not globally grant optional
SPA origins unless needed.

## Diagnostics and privacy

Run public probes before tenant sign-in. They create private local logs.
Treat all authenticated logs and cores as sensitive: tokens, account/device
identifiers and tenant scripts may appear even when some fields are redacted.
Never commit them or paste entire HTTP preludes, JWTs, keyrings or core dumps.

For a crash, start with `coredumpctl info <exact-pid>`, correlate timestamps,
check OOM/resource evidence, and inspect all relevant stacks. Extract a core
only to a fresh private temporary path and remove your extracted copy.
Do not reset working keyrings to address an emulator heap-corruption error.

The initial agent shutdown sometimes aborted after its misleading lock error.
Native trace identified the failed runtime-directory creation; fixing that
directory allowed complete check-ins. This does not prove generic Box64 heap
corruption is solved.
