# Chapter 78 — Why Containers Work: Isolation, Not Tiny Virtual Machines

A container can look like a small machine: it has a root filesystem, hostname, network interfaces, users, and process IDs. On Linux, those views are primarily created around ordinary host processes. There is no separate guest kernel inside a typical container.

The central idea is:

> A container is a host process placed inside selected kernel isolation, resource, and security boundaries and started with a prepared filesystem view.

## 1. Begin with the process

When a Linux container is running, the kernel schedules threads, allocates memory, resolves filesystem operations, and handles system calls just as it does for other processes. The runtime configures the process before starting the requested program.

A useful model is:

```text
image content + runtime configuration
                 |
                 v
runtime prepares root filesystem, namespaces, cgroup, credentials,
capabilities, mounts, devices, and security policy
                 |
                 v
kernel starts the container's initial process
```

The container is not the image. It is not the command-line client. It is not necessarily the long-running daemon. It is the runtime instance and boundaries associated with one or more processes.

## 2. The host kernel remains in control

Processes in Linux containers normally use the host's running kernel. They make system calls into that kernel and depend on its:

- system-call implementation;
- configured features and modules;
- security fixes and vulnerabilities;
- namespace and cgroup support;
- filesystem and networking behavior;
- CPU architecture and exposed hardware.

An image can carry user-space programs and libraries. It cannot carry a Linux kernel that replaces the host kernel merely by being run as a normal container.

On Docker Desktop and similar products, Linux containers run inside a managed Linux virtual machine. They share that VM's Linux kernel, not the Windows or macOS host kernel directly. The process model still applies one layer inside the VM.

## 3. Namespaces change what a process can see

A Linux namespace wraps a global resource in a process-specific view. Processes that belong to different namespace instances can see different resource names or memberships.

Common namespace types include:

| Namespace | Isolated view |
| --- | --- |
| Mount | Mount points and propagation |
| PID | Process identifier hierarchy |
| Network | Interfaces, routes, ports, and network stack state |
| UTS | Hostname and domain name |
| IPC | System V IPC and POSIX message queues |
| User | User and group ID mappings and capabilities |
| Cgroup | Cgroup paths exposed to the process |
| Time | Selected boot and monotonic clock offsets |

A runtime may create some namespaces and join existing instances for others. “Runs in a container” does not identify the actual isolation. Inspect the configuration.

Namespaces primarily control visibility and naming. They do not automatically set CPU or memory limits, remove capabilities, filter system calls, or prevent access through a deliberately shared mount.

## 4. Namespace membership has identity

On Linux, namespace handles appear under `/proc/<pid>/ns/`. A symbolic link such as:

```text
/proc/1234/ns/net -> net:[4026533102]
```

names the namespace type and an inode-like identifier. Processes whose links identify the same namespace instance share that view.

Inspecting these links is more reliable than guessing from a process name. The container's network namespace can be distinct while its user namespace is the host's initial user namespace, for example.

Namespace membership can also be held by an open file descriptor or bind mount after the last process exits. Process lists alone do not always describe namespace lifetime.

## 5. PID namespaces create a process hierarchy view

A process can have one PID as seen inside its PID namespace and another as seen by an ancestor namespace. The first process in a PID namespace appears as PID 1 inside it and has special responsibilities.

An ancestor PID namespace can see processes in descendant PID namespaces. A descendant cannot use its PID view to enumerate processes that exist only in an ancestor or sibling namespace.

PID namespaces change identifiers and visibility; they do not create a separate scheduler. The host kernel still schedules the same underlying tasks.

PID 1 signal and child-reaping behavior matters for container shutdown and zombie processes. Chapter 82 develops that lifecycle in detail.

## 6. Mount namespaces create a filesystem view

A mount namespace gives a process its own mount table. The runtime can arrange an image root filesystem, mount `/proc`, add temporary filesystems, bind host paths, mask sensitive paths, and mark paths read-only.

Changing the apparent root does not by itself create a security boundary. `chroot` changes pathname resolution but does not supply the namespace, credential, capability, device, and system-call controls expected from a container runtime.

Mount propagation determines whether later mount events cross namespace relationships. A careless shared mount can expose host changes or let container-created mounts propagate unexpectedly.

Every bind mount is an intentional hole in filesystem separation. Mounting the host root, runtime socket, device tree, or sensitive configuration can give a container authority far beyond its image.

## 7. Network namespaces isolate network stack state

A network namespace can have its own:

- interfaces and addresses;
- routing tables;
- firewall rules;
- listening ports;
- connection-tracking state;
- `/proc` and `/sys` network views.

The runtime or network plugin connects namespaces with virtual interfaces, bridges, routing, or user-space forwarding. Publishing a port configures a path into the namespace; it does not cause the process to own the host's identically numbered port directly.

Host networking, shared network namespaces, and privileged network capabilities weaken or remove parts of this separation. Chapter 84 follows packets through these paths.

## 8. User namespaces remap identity

A user namespace can map user and group IDs inside the namespace to different IDs outside it. UID 0 inside can map to an unprivileged host UID.

Capabilities are evaluated relative to a user namespace and the object being accessed. Having `CAP_SYS_ADMIN` inside a child user namespace does not grant that capability over every host resource.

Mappings require a defined subordinate-ID range and filesystem support. Host-mounted files still have host ownership, and an unmapped or surprising ID can cause permission failures.

User namespaces reduce the consequences of container-root compromise, but they do not make a shared-kernel boundary equivalent to a virtual machine.

## 9. Cgroups account for and control resources

Control groups organize processes hierarchically and expose controllers for resources such as:

- CPU time and weight;
- memory and swap;
- process count;
- block I/O;
- CPU and memory placement;
- selected device and accelerator resources.

Namespaces answer “which view does this process have?” Cgroups answer “which resource group does this process belong to, and what accounting or controls apply?”

A memory limit does not reserve that amount of memory. A CPU quota does not guarantee low latency. Limits interact with contention, reclaim, throttling, the out-of-memory policy, parent cgroups, and host capacity.

Leaving limits unset lets one workload compete for host-wide resources. Setting limits without measuring normal and peak behavior can create throttling or termination under legitimate load.

## 10. Capabilities divide root authority

Traditional Unix privilege treats effective UID 0 specially. Linux capabilities divide many privileged operations into named units such as changing file ownership, binding privileged ports, administering network state, or loading kernel modules.

Container runtimes usually start with a reduced capability set. Applications should drop every capability they do not require and run as a non-root user where possible.

Adding a broad capability because one operation failed is not diagnosis. Determine:

- which system call failed;
- which object and namespace it targeted;
- which capability or ordinary permission was checked;
- whether the application should perform that operation at all;
- whether the operation can move to a narrower helper or the host.

`CAP_SYS_ADMIN` covers many unrelated operations and is especially powerful. Treat a request for it as an architectural review point.

## 11. Layer additional kernel controls

Namespaces, cgroups, and capabilities are only part of the boundary. A runtime can also apply:

- a seccomp system-call filter;
- Linux Security Module policy such as SELinux or AppArmor;
- `no_new_privs` to prevent gaining privilege through execution;
- read-only and masked paths;
- device allowlists;
- immutable or read-only root filesystems;
- process, file-descriptor, and other resource limits.

These mechanisms overlap intentionally. An exploit that bypasses an application check should still face minimal credentials, filtered system calls, restricted filesystem access, and host policy.

Defaults vary by runtime, platform, version, and configuration. Document the effective profile rather than claiming “containers are sandboxed” without evidence.

## 12. Rootless mode changes the daemon boundary

In rootless operation, the container engine and containers run without host-root privilege, commonly inside a user namespace. This can reduce the impact of a daemon or runtime compromise.

Rootless operation has real constraints. Networking may use user-space forwarding, privileged ports need another mechanism, filesystem drivers vary, and cgroup delegation depends on the host setup.

Do not confuse:

- running the application as non-root inside a container;
- mapping container IDs through a user namespace;
- remapping containers while the daemon remains privileged;
- running the engine itself rootless.

They protect different boundaries and can be combined.

## 13. Privileged and host-sharing modes collapse boundaries

Flags and configuration that deserve explicit review include:

- privileged mode;
- host PID, network, IPC, or user namespaces;
- broad device access;
- all capabilities or powerful individual capabilities;
- writable host bind mounts;
- the container-engine socket;
- host process or kernel filesystems;
- disabled seccomp or security-module confinement.

Access to a container-engine control socket can often create a new highly privileged container or mount host paths. Treat it as administrative authority, not an ordinary application socket.

One weakened boundary can undermine several others. A read-only image does not help if the process can write the host root through a bind mount.

## 14. An image is packaged input, not a running boundary

An image supplies filesystem content and configuration defaults. It may declare a command, environment values, working directory, user, and exposed-port metadata.

The runtime adds or overrides:

- writable container state;
- namespaces and cgroups;
- mounts and secrets;
- network connections and published ports;
- effective user and capabilities;
- security profiles;
- resource limits.

The same image can run with radically different authority. Security review must cover both image content and runtime configuration.

Chapter 79 develops the image's content-addressed layers and the boundary between image and container state.

## 15. Containers and virtual machines isolate differently

A traditional virtual machine presents virtual hardware to a guest operating system with its own kernel. A typical Linux container uses the already-running Linux kernel and isolates processes within it.

| Property | Typical container | Typical virtual machine |
| --- | --- | --- |
| Kernel | Shared host or VM-host kernel | Separate guest kernel |
| Packaged unit | User space plus metadata | Guest OS and virtual disks |
| Startup | Start isolated processes | Boot guest operating system |
| Isolation boundary | Kernel process controls | Hypervisor and guest boundary |
| Kernel choice | Compatible with hosting kernel | Chosen per guest architecture support |
| Density | Usually higher | Usually lower |

This comparison is not a verdict that one is always safer or faster. Hypervisors, microVMs, sandboxed runtimes, Windows process isolation, and nested configurations create additional models. Choose from the actual threat and compatibility requirements.

## 16. Portability has a boundary

An image is portable only across compatible runtime and platform contracts. Important dimensions include:

- operating-system family;
- CPU architecture and instruction set;
- kernel system calls and features;
- libc and dynamic-linker expectations;
- device and accelerator availability;
- filesystem semantics;
- security policy;
- runtime specification and implementation support.

A Linux image does not run as ordinary Windows processes merely because both hosts have a container CLI. A multi-platform image can point to different platform-specific manifests, but each selected image still needs a compatible execution environment.

“Works in a container” narrows some user-space variation. It does not erase the host kernel, hardware, runtime, or external-service contracts.

## 17. Choose isolation from a threat model

For trusted services from one organization, hardened shared-kernel containers may provide the needed efficiency and isolation. For hostile multi-tenant code, kernel-exploit exposure may justify a stronger boundary such as a dedicated virtual machine, microVM, or sandboxed runtime.

Ask:

- Who controls the image and runtime arguments?
- What host data and devices are exposed?
- Are tenants mutually trusted?
- What is the consequence of kernel compromise?
- Which security mechanisms are enforced outside the workload's control?
- How are the host kernel and runtime patched?
- Can the workload exhaust shared resources?
- Is escape detection and response available?

Isolation is a system property. No single flag can substitute for this analysis.

## 18. Safe lab: inspect an isolated process

This lab requires a disposable Docker-compatible Linux container environment and a locally approved image. The example uses an Alpine version tag for readability; for controlled or repeatable use, resolve and record an approved digest first.

The script creates one bounded container, inspects it, and removes it through an exit trap:

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

name="handbook-isolation-$RANDOM"
image="alpine:3.21"

cleanup() {
  docker rm --force "$name" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker run --detach \
  --name "$name" \
  --network none \
  --read-only \
  --tmpfs /tmp:rw,nosuid,nodev,noexec,size=16m \
  --memory 128m \
  --cpus 0.50 \
  --pids-limit 64 \
  --user 65532:65532 \
  --cap-drop ALL \
  --security-opt no-new-privileges:true \
  "$image" sleep 300 >/dev/null

docker inspect --format \
  'host-visible-pid={{.State.Pid}} image={{.Image}}' \
  "$name"

docker exec "$name" sh -c '
  set -eu
  echo "identity:"
  id
  echo "kernel:"
  uname -sr
  echo "process view:"
  ps
  echo "namespace identities:"
  for namespace in mnt pid net uts ipc user cgroup; do
    printf "%s " "$namespace"
    readlink "/proc/self/ns/$namespace"
  done
  echo "cgroup membership:"
  cat /proc/self/cgroup
  if test -r /sys/fs/cgroup/memory.max; then
    printf "memory.max="
    cat /sys/fs/cgroup/memory.max
  fi
  if touch /etc/should-fail 2>/dev/null; then
    echo "unexpected: root filesystem was writable" >&2
    exit 1
  fi
  touch /tmp/works
  echo "read-only root rejected a write; tmpfs accepted one"
'

docker rm --force "$name" >/dev/null
trap - EXIT
```

Observe that `ps` shows the container's PID namespace view while `docker inspect` reports the process ID visible to the Linux engine host. On Docker Desktop, that host-visible PID belongs to the managed Linux VM, not directly to Windows or macOS.

Run `docker inspect "$name"` before cleanup in a second experiment and locate the effective user, cgroup limits, capability drops, namespaces, mounts, and security options. Do not run the lab with `--privileged` merely to compare output.

## 19. Interpret absence carefully

If a process cannot see a host object, determine which mechanism caused that result. It might be:

- outside the namespace view;
- absent from the mounted filesystem;
- blocked by ordinary permissions;
- rejected by a capability check;
- denied by seccomp or a security module;
- unavailable through device policy;
- constrained by a parent cgroup;
- omitted by the runtime implementation.

“Permission denied,” “operation not permitted,” and “file not found” can each result from several boundaries. Diagnose with the process identity, effective capabilities, namespace membership, mounts, security-policy audit events, and cgroup configuration.

## Common Misconceptions

- “A container is a lightweight VM.” Typical Linux containers do not boot a guest kernel.
- “Namespaces limit memory.” Cgroups and host policy provide resource accounting and controls.
- “Root in a container is harmless.” Its authority depends on user mapping, capabilities, mounts, devices, and runtime configuration.
- “A read-only image makes the container read-only.” Runtime writable layers and mounts can still provide writable state.
- “Rootless means no security risk.” The process still reaches a shared kernel and whatever resources its user can access.
- “The same image behaves identically everywhere.” Kernel, architecture, runtime, policy, configuration, and external systems remain inputs.

## Core Computer Science Concept

Containers apply **virtualized names and constrained resource membership to processes**. Namespaces create contextual views, cgroups organize resource control, and credential and security mechanisms constrain operations against shared kernel objects.

## Engineering Connections

- PID and mount views extend the process and filesystem models from Parts I and II.
- Network namespaces reuse interfaces, routes, ports, and sockets from Part V.
- Cgroup limits are feedback controls, not performance guarantees.
- Capability and user-namespace checks apply least authority to kernel operations.
- Runtime configuration is another external boundary that needs the evidence and recovery practices from Part VI.

## From the Field

A build container mounts the engine socket to start sibling containers. Compromised build code asks the daemon to mount the host root into a new privileged container and modifies the worker. The original build container's restricted capabilities did not matter because the socket granted control over a more powerful authority boundary.

## Engineering Review

### What problem does this solve?

It replaces the “tiny virtual machine” analogy with a model that predicts visibility, resource use, privilege, portability, and failure.

### Why was it designed this way?

Linux can isolate selected process views and resources without booting another kernel, while layered controls constrain what those processes can do to shared objects.

### When should I use it?

Use this model whenever designing, running, debugging, or securing containers and whenever comparing them with virtual machines or sandboxed runtimes.

### When should I avoid it?

Avoid treating shared-kernel containers as the sole boundary for hostile code when the consequence of kernel compromise requires stronger isolation.

### How does this make me a better engineer?

It lets you inspect the exact boundary that failed instead of attributing behavior to a vague container abstraction.

### How does this reduce waste?

It prevents unnecessary guest-style administration, unsafe privilege escalation, incorrect resource assumptions, incompatible images, and misdiagnosed namespace behavior.

## Handbook Principle #78

> Start with the process, identify every shared kernel boundary, and claim only the isolation that the effective runtime configuration enforces.

## Practical Observation

Run the bounded lab on an approved disposable engine. Record the namespace links, container-visible PID 1, engine-host PID, capability mask, cgroup membership, root mount mode, and tmpfs behavior. Change exactly one safe boundary—such as the PID limit—and explain the observed difference before cleanup.

## Looking Ahead

The runtime needs a filesystem and configuration to start that isolated process. Chapter 79 explains how image manifests, content-addressed layers, build contexts, copy-on-write snapshots, and cache keys provide that input—and how unexpected content enters it.

## References

- [Linux `namespaces(7)` manual page](https://man7.org/linux/man-pages/man7/namespaces.7.html)
- [Linux `user_namespaces(7)` manual page](https://man7.org/linux/man-pages/man7/user_namespaces.7.html)
- [Linux `capabilities(7)` manual page](https://man7.org/linux/man-pages/man7/capabilities.7.html)
- [Linux kernel documentation — Control Group v2](https://docs.kernel.org/admin-guide/cgroup-v2.html)
- [Open Container Initiative Runtime Specification — Bundle](https://specs.opencontainers.org/runtime-spec/bundle/)
- [Open Container Initiative Runtime Specification — Linux configuration](https://specs.opencontainers.org/runtime-spec/config-linux/)
- [Docker Engine security](https://docs.docker.com/engine/security/)
- [Docker Engine rootless mode](https://docs.docker.com/engine/security/rootless/)
- [Microsoft — Windows and containers](https://learn.microsoft.com/en-us/virtualization/windowscontainers/about/)
