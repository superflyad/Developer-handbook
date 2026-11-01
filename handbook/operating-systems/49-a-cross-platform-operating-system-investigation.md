# Chapter 49 — A Cross-Platform Operating-System Investigation

Operating-system incidents cross layers. A service cannot write a file; the path belongs to an unexpected volume; the process runs under a different identity; memory pressure delays it; and a restart hides the original evidence. This chapter provides one read-mostly investigation structure with platform-specific collection paths.

The central idea is:

> Keep the diagnostic questions portable, but use each operating system's native evidence and terminology.

## 1. The scenario and safety boundary

Investigate one noncritical process or service you are authorized to inspect and one path it uses. The goal is to build an evidence map, not repair or benchmark the system.

Do **not**:

- mount, unmount, format, resize, or repair storage;
- start, stop, restart, enable, or disable services;
- change priority, affinity, memory limits, ownership, modes, or ACLs;
- dump another process's memory or environment;
- collect secrets, command-line credentials, or unrelated user data;
- reboot solely for the exercise.

Some read-only commands still reveal sensitive paths, account names, arguments, or logs. Keep results local and redact them before sharing. If access is denied, record the boundary rather than elevating.

## 2. Start with a testable symptom

Replace “the server is broken” with an observation:

```text
At 14:05 local time, service X failed to create Y at path Z.
Expected: one new file within 2 seconds.
Observed: access-denied error after 20 milliseconds.
Scope: one host and one service instance.
Last known success: 13:57.
```

For a learning exercise without a real failure, use this question:

> Which storage, process context, memory state, service policy, and access rules govern this path right now?

Create a notes file outside the target application's directories. Record timestamps with timezone, host identity, operating-system version, and whether the system is physical, virtual, containerized, or remotely mounted.

## 3. Build the layer map before commands

Fill each line with evidence or “unknown”:

```text
requested operation
└── application/service
    ├── process ID and start time
    ├── executable and launch manager
    ├── runtime identity and containment
    ├── working directory and explicit target path
    ├── CPU state and memory scope
    └── path
        ├── namespace components and links
        ├── object type and metadata
        ├── owner/mode/ACL or security descriptor
        ├── mount or volume and filesystem
        └── backing device, share, or virtual source
```

This prevents a familiar error: collecting hundreds of metrics without knowing which component or path they describe.

## 4. Select one platform track

Do not run all three columns. Choose the operating system being investigated. Replace placeholders such as `PID`, `path`, and `unit-name` with observed values; never paste the placeholders literally into a command that changes state.

### System and time context

| Question | Linux | macOS | Windows PowerShell |
| --- | --- | --- | --- |
| OS and kernel | `uname -a`; `cat /etc/os-release` | `sw_vers`; `uname -a` | `Get-ComputerInfo` selected fields |
| Current time | `date --iso-8601=seconds` | `date -Iseconds` | `Get-Date -Format o` |
| Uptime/boot | `uptime -s`; `uptime` | `sysctl -n kern.boottime`; `uptime` | CIM `Win32_OperatingSystem` boot time |
| Host | `hostnamectl` or `hostname` | `scutil --get ComputerName`; `hostname` | `$env:COMPUTERNAME` |

Tool availability differs among distributions and versions. If a convenience command is absent, record that fact and use the platform's documented equivalent rather than installing tools during an incident.

## 5. Trace the path to storage

First preserve the exact path supplied to the application. Then inspect without following unexpected links blindly.

### Linux

```bash
namei -l /full/path
stat -- /full/path
findmnt -T /full/path
df -hT /full/path
lsblk -o NAME,TYPE,FSTYPE,SIZE,MOUNTPOINTS
```

### macOS

```bash
stat -x /full/path
ls -ldeO@ /full/path
df -h /full/path
diskutil info /full/path
mount
```

### Windows PowerShell

```powershell
$item = Get-Item -LiteralPath 'C:\full\path' -Force
$item | Format-List FullName, PSProvider, Attributes, LinkType, Target, Length, CreationTimeUtc, LastWriteTimeUtc
Get-Volume
Get-Partition
Get-Disk
```

Do not infer the path-to-volume relationship from matching sizes alone. On Windows, use the item's resolved drive or documented volume APIs; on Unix-like systems, use the mount containing that exact path. For UNC, NFS, SMB, or other remote paths, record the server and share/export as a dependency instead of looking for a local physical disk.

Answer:

1. Is the object a regular file, directory, link, reparse point, or special type?
2. Which filesystem or volume contains it?
3. Is the source local, virtual, removable, or remote?
4. Is the filesystem read-only, full, quota-constrained, or unexpectedly mounted?
5. Could a mount or link redirect resolution across a trust boundary?

## 6. Identify the exact process instance

A PID alone is insufficient because IDs can be reused. Pair it with start time, executable, owner, and service association.

### Linux

```bash
ps -o pid,ppid,user,group,lstart,stat,etime,time,command -p PID
readlink /proc/PID/exe
readlink /proc/PID/cwd
cat /proc/PID/status
```

Access to `/proc` details may be restricted. Do not read `/proc/PID/environ` for this exercise; it may expose secrets.

### macOS

```bash
ps -o pid,ppid,user,group,lstart,state,etime,time,command -p PID
lsof -a -p PID -d cwd
```

`lsof` output can expose unrelated paths. Limit and protect the result.

### Windows PowerShell

```powershell
Get-Process -Id PID | Select-Object Id, ProcessName, StartTime, Path, CPU, WorkingSet64, PrivateMemorySize64
Get-CimInstance Win32_Process -Filter 'ProcessId = PID' |
    Select-Object ProcessId, ParentProcessId, ExecutablePath, CreationDate
```

Some fields require additional access. Avoid collecting full command lines unless needed and safe; they may contain credentials.

Answer:

- Who launched and manages the process?
- What identity and containment does it actually use?
- What working directory and namespace view does it have?
- Is this the same instance that produced the error?
- Are open handles or current directories retaining storage?

## 7. Interpret CPU and memory without one-number conclusions

Capture a short, timestamped observation rather than an unbounded trace.

| Evidence | Linux | macOS | Windows |
| --- | --- | --- | --- |
| System pressure | `uptime`, `free -h`, PSI files | Activity Monitor, `vm_stat` | Task Manager or approved counters |
| Process CPU/memory | `ps`, `/proc/PID/status` | `ps`, Activity Monitor, `vmmap PID` | `Get-Process`, approved counters |
| Limits | `/proc/PID/limits`, cgroup files | manager/sandbox policy | service, job, container, or VM policy |

Record wall-clock symptom, process CPU time, runnable versus blocked evidence when available, resident or working-set value, private or proportional value when supported, and the enforcing container or service limit.

Do not sum resident values across processes as physical usage. Do not call high virtual size a leak. Do not raise priority because latency is high. The next safe step may be an application profiler or trace, but that requires a separate scope and data-handling plan.

## 8. Inspect the service-manager contract

If the process is managed, correlate its current PID with its manager definition.

### Linux systemd

```bash
systemctl status unit-name
systemctl cat unit-name
systemctl show unit-name
journalctl -u unit-name --since today
```

### macOS launchd

```bash
launchctl print system/label
launchctl print gui/$(id -u)/label
plutil -p /path/to/owned-job.plist
```

Choose the correct domain; do not assume both labels exist.

### Windows

```powershell
Get-Service -Name service-name
Get-CimInstance Win32_Service -Filter "Name='service-name'" |
    Select-Object Name, State, StartMode, StartName, PathName, ProcessId
```

Record executable and arguments, runtime identity, working directory if declared, environment source, dependencies, startup policy, resource restrictions, restart policy, last transition, and manager logs. “Running” establishes neither readiness nor access to the target path.

## 9. Trace the access decision

State the exact operation: traverse, list, read, create, append, replace, delete, or execute. Different rights apply.

### Linux

```bash
id
namei -l /full/path
getfacl -- /full/path
```

### macOS

```bash
id
ls -ldeO@ /full/path
```

### Windows PowerShell

```powershell
whoami /all
Get-Acl -LiteralPath 'C:\full\path' | Format-List Owner, AccessToString, AreAccessRulesProtected
```

These inspect the current shell identity, which may differ from a service identity. Do not impersonate the service merely for the exercise. Instead, compare documented runtime identity with applicable path traversal, mode, ACL/DACL, inheritance, share/export, attribute, mount, mandatory policy, and application rules.

Write a one-sentence conclusion:

```text
Process identity A requested operation B on object C through namespace D;
policy evidence E allows/denies/does not yet explain the result.
```

“Does not yet explain” is a valid outcome and is safer than an unsupported permission change.

## 10. Build a timeline and causal claim

Align evidence by timestamp and source:

| Time | Layer | Evidence | Interpretation | Confidence |
| --- | --- | --- | --- | --- |
| 14:04:58 | service manager | process started as identity A | new instance created | high |
| 14:05:01 | application | create path Z denied | requested write failed | high |
| 14:05:01 | filesystem | parent lacks required grant for A | explains denial | medium/high |

Separate observations from interpretations. A causal claim should predict a safe test: granting one missing right on a disposable equivalent should change only the denied operation. A production remediation still needs owner approval, impact analysis, rollback, and post-change verification.

## 11. Produce the handoff

End with:

- symptom and scope;
- system and time context;
- path-to-storage map;
- process instance and manager context;
- CPU/memory interpretation;
- authorization trace;
- evidence-supported hypothesis and alternatives;
- next read-only diagnostic step;
- proposed change, risk, rollback, and verification—if remediation is authorized later.

Do not attach raw dumps containing secrets. Include exact commands only after redacting identifiers that should remain private.

## Common Misconceptions

- “Cross-platform means identical commands and metrics.” It means comparable questions with platform-native evidence.
- “Read-only output is harmless.” Logs, tokens, paths, and arguments can be sensitive.
- “The current shell represents the service.” Runtime identity and namespace can differ.
- “A complete inventory is a diagnosis.” Evidence needs a causal relationship to the symptom.

## Core Computer Science Concept

This investigation uses **model-based diagnosis**. The layer map predicts which evidence should exist and how state flows. Contradictions refine the model; they are more useful than collecting unrelated output until something looks unusual.

## Engineering Connections

- Incident handoffs improve when observations, interpretations, and proposed changes are separate.
- Security review benefits from the same path, identity, and trust-boundary map.
- Performance work begins by locating wait and enforcement scope, not tuning everything.
- Automation should encode this evidence plan only after the manual questions are stable.

## From the Field

A team restarts a failing service, opens directory permissions, and expands memory in one response. The issue disappears, but no one knows which action mattered and the system now has excess authority. A layered investigation would have shown that the restarted process received a different service account token; the durable repair is the correct narrow grant and a corrected deployment identity.

## Engineering Review

### What problem does this solve?

It provides a repeatable way to connect filesystem, storage, process, memory, service, startup, and authorization evidence.

### Why was it designed this way?

Operating systems expose similar responsibilities through different abstractions, so stable questions are more portable than command names.

### When should I use it?

Use it for initial triage, learning, incident handoff, and deciding which specialist or deeper tool is needed next.

### When should I avoid it?

Avoid running broad collection against sensitive systems without authorization or treating this read-mostly workflow as production remediation.

### How does this make me a better engineer?

It trains you to build causal system models, preserve evidence, and state uncertainty precisely.

### How does this reduce waste?

It narrows investigation before changes, prevents multi-variable guessing, and creates reusable evidence for handoff.

## Handbook Principle #49

> Keep the questions stable across platforms, collect native evidence by layer, and change nothing until one causal model fits.

## Practical Observation

Complete the investigation for one noncritical process or service and one path without elevating or changing state. Produce a one-page handoff containing the layer map, five timestamped observations, one supported conclusion, one uncertainty, and the next safe step. Delete or secure raw output that contains sensitive identifiers.

## Looking Ahead

Part IV established local namespaces, execution, resources, supervision, and authorization. Part V follows data beyond one host: addressing, routing, DNS, transport, HTTP, TLS, SSH, firewalls, and network troubleshooting.

## References

- [Linux `/proc` Filesystem](https://docs.kernel.org/filesystems/proc.html)
- [Apple: Creating Launch Daemons and Agents](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html)
- [Microsoft PowerShell: `Get-Process`](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/get-process)
- [Microsoft PowerShell: `Get-Acl`](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.security/get-acl)
