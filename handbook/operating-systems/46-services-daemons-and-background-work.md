# Chapter 46 — Services, Daemons, and Background Work

Appending `&` or closing a terminal does not create a reliable service. Long-lived work needs a declared identity, environment, dependencies, restart policy, logs, and shutdown contract. Operating-system service managers provide that lifecycle boundary.

The central idea is:

> A service is a managed execution contract around a process, not merely a process without a window.

## 1. Background and managed are different

A shell background job still belongs to a login session and inherits its terminal, environment, working directory, limits, and credentials unless deliberately changed. It may stop when the session ends, lose output, or continue with no owner able to observe it.

A service manager can:

- start work at boot, login, demand, or dependency readiness;
- assign identity, environment, working directory, and resource limits;
- connect logging and standard streams;
- track the main process or process group;
- stop it through a defined protocol;
- restart according to declared failure policy;
- order or activate dependencies;
- report state to operators and automation.

The manager does not make application behavior healthy by itself. It makes lifecycle policy visible and enforceable.

## 2. Define the execution context completely

Services usually run with a smaller and different environment than an interactive shell. They may have no home directory, login shell profile, terminal, desktop session, or user-mounted network share. Their working directory can be `/`, a system directory, or an explicitly configured path.

Declare:

- an absolute executable path and argument boundaries;
- a dedicated least-privilege identity;
- required environment or secret references;
- working and state directories;
- dependencies and activation conditions;
- resource and security restrictions;
- logging destination;
- startup, readiness, stop, and timeout behavior.

Do not copy an entire interactive environment into a service. It can include secrets, developer paths, proxy settings, and behavior that changes across logins.

## 3. Linux: systemd units describe managed state

Many Linux distributions use systemd. A service unit can declare the executable, user, dependencies, restart behavior, environment, and sandboxing. Read-only inspection includes:

```bash
systemctl status unit-name
systemctl cat unit-name
systemctl show unit-name
journalctl -u unit-name --since today
```

`status` is a summary, not the full configuration. Unit files can have drop-ins and generated or vendor definitions; `systemctl cat` and `show` reveal different views. Journal access depends on permissions and retention.

Do not run `enable`, `disable`, `start`, `stop`, `restart`, or `daemon-reload` while merely investigating. Enabling controls whether a unit participates in configured startup relationships; starting changes current runtime state. They are related but not synonyms.

Modern service managers expect the managed process to remain in the foreground unless the unit type explicitly supports another protocol. Self-daemonizing can cause the manager to track the wrong process.

## 4. macOS: launchd manages daemons and agents

macOS uses `launchd` for system daemons and per-user agents. Property-list configuration declares a label, program arguments, activation and keep-alive behavior, environment, and other policy. System daemons and user agents occupy different domains and identities.

Read-only commands can include:

```bash
launchctl print system
launchctl print gui/$(id -u)
plutil -p /path/to/job.plist
```

The output can be large and domain syntax matters. Prefer inspecting one known label or owned plist. Do not edit files under system-managed locations or use old copied `launchctl` recipes without the documentation for the installed macOS version.

Apple guidance for managed jobs says not to self-daemonize; `launchd` needs to track the process it launched. Long-running app helpers may be better represented as launch agents, XPC services, or platform service-management components.

## 5. Windows: the Service Control Manager owns services

The Windows Service Control Manager (SCM) maintains installed service configuration and sends lifecycle controls. A service runs in a configured account and session, often without an interactive desktop. It reports state transitions and accepts supported controls through the service API.

Read-only PowerShell observations include:

```powershell
Get-Service -Name service-name
Get-CimInstance Win32_Service -Filter "Name='service-name'" |
    Select-Object Name, State, StartMode, StartName, PathName, ProcessId
```

`Get-Service` shows service-controller state; CIM exposes more configuration. The executable command in `PathName` needs careful parsing and quoting. Service account, filesystem ACLs, log-on rights, registry or configuration access, and network identity all influence behavior.

Do not change startup type or account as an experiment. Account changes can break private-key access, profile-dependent state, network authentication, and file ownership.

## 6. Running, ready, and healthy are not synonyms

A manager may report a process as running as soon as creation succeeds. The application may still be loading, migrating data, or unable to reach a dependency. Define:

- **liveness:** the process exists or responds enough to avoid restart;
- **readiness:** it can serve new work correctly;
- **health:** its important dependencies and internal invariants meet policy.

Restart-on-failure is useful for transient faults but can create a crash loop that floods logs or damages a dependency. Backoff, retry limits, and failure visibility are part of the policy. Permanent configuration errors should become actionable failures, not infinite restarts.

## 7. Logs must preserve service context

Service logs should include startup configuration identifiers, version, process ID, effective identity where safe, dependency failures, and exit reason. Never log secret values. Platform journals and event systems add manager messages that application log files may omit.

Correlate:

```text
service-manager decision
→ process creation and context
→ application startup
→ readiness transition
→ runtime failure or stop request
→ exit status and restart policy
```

A process that vanishes can have been killed by memory policy, stopped by the manager, crashed, or exited successfully. The last application line alone may not distinguish them.

## 8. Safe change sequence

For a service configuration change:

1. capture current effective configuration and ownership;
2. identify the supported configuration source, not a generated file;
3. validate syntax with platform tools where available;
4. define expected impact, rollback, and maintenance window;
5. apply the narrow change;
6. reload only the required manager configuration;
7. restart or activate only when authorized;
8. verify process context, readiness, logs, and downstream behavior.

This chapter intentionally does not provide a one-size-fits-all install recipe. Service creation changes persistent system state and authority.

## Common Misconceptions

- “A background job is a service.” It lacks a declared manager-owned lifecycle.
- “Enabled means running.” Startup participation and current state are separate.
- “Running means ready.” Process existence does not prove useful service.
- “Restart fixes the service.” It may only erase evidence or repeat a permanent fault.

## Core Computer Science Concept

A service manager is a **supervisor and policy engine**. It converts process exit and dependency events into controlled state transitions, making lifecycle behavior declarative rather than hidden in shell sessions.

## Engineering Connections

- Containers need an orchestrator or supervisor for restart and readiness policy at another layer.
- Least-privilege service accounts contain compromise and clarify filesystem ownership.
- Socket activation can separate endpoint ownership from process lifetime.
- Structured service logs connect operating-system lifecycle with application observability.

## From the Field

A program succeeds from an administrator's terminal but fails as a service. It depended on a mapped network drive, interactive profile, and relative path. Repeated account elevation makes it work but expands authority. The correct fix uses an explicit UNC or supported storage path, absolute configuration, a dedicated service identity, and narrowly granted access.

## Engineering Review

### What problem does this solve?

It provides durable lifecycle, context, dependency, logging, and restart management for noninteractive work.

### Why was it designed this way?

Central supervision makes process policy observable and lets the operating system coordinate startup, shutdown, authority, and failure.

### When should I use it?

Use a service manager for long-lived, boot-time, on-demand, or independently supervised background work.

### When should I avoid it?

Avoid installing a service for a one-off command or using restart policy to conceal deterministic configuration failures.

### How does this make me a better engineer?

It makes runtime context, readiness, and failure response explicit design decisions.

### How does this reduce waste?

It eliminates fragile login-session processes and shortens diagnosis by preserving manager and application evidence.

## Handbook Principle #46

> Manage persistent work through an explicit supervisor contract, with identity, readiness, failure, and shutdown defined.

## Practical Observation

Choose one noncritical installed service and use only read-only tools for your platform to record its manager, startup policy, current state, executable, identity, dependencies, and recent manager logs. Do not start, stop, enable, disable, or reconfigure it.

## Looking Ahead

Service managers participate in a larger startup sequence. Chapter 47 traces the handoff from firmware through kernel initialization, managed services, login, and shutdown.

## References

- [systemd.service](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html)
- [Apple: Creating Launch Daemons and Agents](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html)
- [Microsoft: Service Control Manager](https://learn.microsoft.com/en-us/windows/win32/services/service-control-manager)
- [Microsoft PowerShell: `Get-Service`](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/get-service)
