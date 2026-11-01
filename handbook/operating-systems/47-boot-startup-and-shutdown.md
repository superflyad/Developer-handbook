# Chapter 47 — Boot, Startup, and Shutdown

An operating system does not appear all at once. Firmware initializes enough hardware to select a boot path, a loader places a kernel into memory, the kernel builds core abstractions, and user-space managers start services and login environments. Each phase depends on earlier evidence.

The central idea is:

> Locate startup failures by the last completed handoff; do not repair a later layer that never received control.

## 1. Startup is a chain of authority and state

A generalized sequence is:

```text
power or reset
→ firmware initialization and boot selection
→ boot manager or loader
→ kernel and early drivers
→ root/system storage and core user space
→ service manager and dependencies
→ login/session manager
→ user applications
```

Platforms combine or subdivide these phases differently. Sleep resume, hibernation restore, container start, and virtual-machine start also follow different paths from a cold boot. Record which event actually occurred before comparing timing or logs.

## 2. Firmware discovers a boot path

Modern PCs commonly use UEFI firmware. It performs early platform initialization, consults configuration, and loads a selected EFI application such as an operating-system boot manager. Secure Boot can validate components against configured trust policy. Older BIOS and MBR paths still exist but are not interchangeable with UEFI.

Apple hardware integrates firmware and platform security with its own boot policy, with important differences between Apple silicon and Intel systems. Windows and Linux can both boot through UEFI but use different loaders and trust chains.

If the system never displays loader or operating-system evidence, changing a service unit cannot help. First identify power, firmware, device discovery, display, and boot-selection state. Firmware updates and key changes are high-risk administrative actions and are outside this chapter.

## 3. The loader prepares the kernel handoff

A boot loader selects and loads the kernel and often an initial RAM filesystem or equivalent early environment. It supplies configuration such as a kernel command line. The early environment can load drivers, unlock encrypted storage, assemble logical volumes, and locate the real root filesystem.

Failure here can look like a missing kernel, invalid signature, inaccessible boot volume, or inability to find the system root. A boot menu entry, filesystem mount, and service startup are three different layers even if all mention the same disk.

Do not edit boot configuration from an unverified online recipe. Capture the exact firmware mode, loader, operating-system version, disk layout, encryption state, and recovery path first.

## 4. The kernel establishes operating-system primitives

The kernel initializes memory management, scheduling, device drivers, filesystems, networking foundations, and process creation. It eventually starts the first user-space process or the platform's equivalent system initialization path.

Early kernel logs can reveal driver, storage, memory, and root-mount problems. Later service logs cannot exist if the kernel never created the relevant user-space environment. Conversely, one alarming driver warning does not prove it caused a later application failure; align timestamps and dependency evidence.

Linux commonly exposes the current boot's kernel messages through `journalctl -k -b` when systemd journal access is available. macOS unified logging and Windows Event Viewer provide platform-specific records, but collection and retention policies vary.

## 5. User-space managers start dependency graphs

Linux systemd, macOS `launchd`, and Windows system processes plus the Service Control Manager coordinate managed user-space work. Startup is not merely one fixed serial script: managers can activate independent work in parallel, wait on dependencies, and start on demand.

Linux observations can include:

```bash
systemd-analyze time
systemd-analyze critical-chain
systemctl --failed
journalctl -b
```

These commands describe a systemd-based system and require appropriate access. The critical chain identifies timing relationships, not necessarily the only cause of slow user experience.

On Windows, Event Viewer and Windows Performance Recorder/Analyzer can provide boot evidence. PowerShell can inspect service states, but a stopped automatic service after boot needs its event history before diagnosis. On macOS, `log show --last 1h` and targeted `launchctl print` queries can help, with predicates and permissions chosen to avoid collecting unrelated sensitive logs.

## 6. Login startup is another layer

After the system is usable, a login starts user-specific sessions, shells, desktop agents, profiles, and applications. A slow shell profile is not a slow kernel boot. An application configured to start at login is not a system daemon.

Separate these timestamps:

- power to loader;
- loader to kernel handoff;
- kernel to system-ready state;
- authentication to user session;
- session to application readiness.

This boundary also changes identity and environment. User-mounted drives, credential stores, and desktop services may not exist for system services before login.

## 7. Shutdown is ordered dependency reversal

Orderly shutdown stops accepting new work, asks services to terminate, flushes application and filesystem state, unmounts storage, and powers off or restarts. A forced power loss bypasses these contracts. Journaling filesystems improve recovery but do not guarantee every application's last acknowledged operation survives.

Services should handle the platform's stop request, reject or drain new work as appropriate, persist required state, close resources, and exit within a declared timeout. Managers may force termination after that timeout. A service that ignores shutdown can delay the whole host or lose state.

Do not use a hard power-off as routine service management. If shutdown hangs, collect the blocking unit, process, mount, or driver evidence and use the documented escalation procedure for that platform.

## 8. Diagnose by last confirmed boundary

1. Define cold boot, restart, resume, or login and record the time.
2. Identify the last phase with trustworthy output or logs.
3. Inspect that phase's attempted handoff and the next phase's earliest evidence.
4. Correlate storage, encryption, driver, dependency, and service state.
5. Make one reversible change at the responsible layer.
6. Reboot only when required and compare the same timing boundaries.

Recovery environments are separate operating contexts. Their drive letters, mount paths, credentials, and available tools can differ from the installed system. Confirm targets before changing anything.

## Common Misconceptions

- “Boot is one program running a list.” It is a series of handoffs and dependency graphs.
- “The first error in a log is the cause.” It may be tolerated or unrelated.
- “System startup ends at the login screen.” User-session startup continues afterward.
- “Journaling makes hard shutdown safe.” It protects selected filesystem consistency properties, not every application transaction.

## Core Computer Science Concept

Boot is **layered bootstrap**: each stage creates enough capability and trust to load the next. Because later tools depend on earlier stages, diagnosis must use the evidence available at the last successful boundary.

## Engineering Connections

- Secure Boot establishes a chain of trust before ordinary application authorization.
- Service dependency graphs resemble build systems and deployment orchestration.
- Readiness should be measured at user-facing boundaries, not merely kernel start.
- Graceful shutdown is a distributed coordination problem across local dependencies.

## From the Field

A machine reaches the desktop quickly, but the user's terminal takes 40 seconds to open. Firmware and kernel teams are initially blamed because the symptom is called “slow boot.” Timestamped evidence shows the delay is a network lookup in the shell profile after login. Separating phase boundaries directs the fix to user startup configuration.

## Engineering Review

### What problem does this solve?

It explains how a powered machine establishes trusted code, kernel services, managed processes, and user sessions in stages.

### Why was it designed this way?

No full operating-system environment exists initially, so each small stage must construct the capabilities needed by the next.

### When should I use it?

Use the model for boot failure, slow startup, service ordering, login delay, shutdown hang, and recovery planning.

### When should I avoid it?

Avoid changing firmware, loader, or recovery configuration when evidence places the fault in a later service or user-session layer.

### How does this make me a better engineer?

It teaches causal diagnosis through handoff boundaries and prevents layer-crossing guesses.

### How does this reduce waste?

It narrows logs and ownership to the failed phase and avoids risky changes to healthy earlier components.

## Handbook Principle #47

> Find the last successful startup handoff, then investigate the next dependency with evidence from both sides.

## Practical Observation

Without rebooting, use existing logs to sketch the most recent startup timeline for your system: firmware or loader evidence if available, kernel start, service-manager readiness, login, and one user application. Record missing evidence rather than inventing timestamps. Make no boot or startup configuration changes.

## Looking Ahead

Startup creates processes under specific identities and policies. Chapter 48 follows an access request through process credentials, directory traversal, object permissions, ACLs, and elevated privilege.

## References

- [systemd: Bootup Process](https://www.freedesktop.org/software/systemd/man/latest/bootup.html)
- [Microsoft: Advanced Troubleshooting for Windows Startup Issues](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/windows-boot-issues-troubleshooting)
- [Apple Platform Security: Boot Process](https://support.apple.com/guide/security/boot-process-secac71d5623/web)
- [UEFI Forum Specifications](https://uefi.org/specifications)
