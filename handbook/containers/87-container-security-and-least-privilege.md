# Chapter 87 — Container Security and Least Privilege

An image can be minimal, signed, and free of known vulnerabilities while its container still mounts the host root, controls the runtime socket, runs privileged, or receives broad credentials. Artifact quality and runtime authority are separate security questions.

The central idea is:

> Give a verified image the smallest identity, kernel authority, filesystem access, device access, network reach, credentials, and runtime control needed for one role—and assume every isolation layer can fail.

## 1. Begin with a workload threat model

Identify:

- code and packages inside the image;
- configuration and secrets supplied at runtime;
- data read, created, or modified;
- clients and downstream services;
- host kernel, runtime daemon, and management APIs;
- build system, registry, and deployment controller;
- operators, automation identities, and attackers;
- required availability and forensic evidence.

Then list credible paths:

- a vulnerable application receives hostile input;
- a compromised dependency executes during build or startup;
- a stolen registry credential replaces an artifact;
- a workload reads an over-broad secret or host mount;
- a process abuses a capability, device, syscall, or shared namespace;
- runtime API access creates a more privileged container;
- a kernel or runtime flaw crosses the container boundary;
- unrestricted egress moves data or reaches control planes.

Hardening should break or constrain those paths. A copied checklist without a threat model can preserve the most dangerous authority.

## 2. Containers are not miniature trust zones by default

Linux containers ordinarily share the host kernel. Namespaces isolate views, cgroups constrain resources, capabilities divide root authority, seccomp filters syscalls, and mandatory access controls restrict objects. These mechanisms overlap, but none makes arbitrary hostile code equivalent to a separate physical machine.

The security boundary changes when a workload receives:

- host namespaces;
- privileged mode or powerful capabilities;
- host devices;
- sensitive bind mounts;
- runtime or orchestration control sockets;
- kernel interfaces with write access;
- credentials that control external infrastructure.

For mutually untrusted tenants or high-impact workloads, consider a stronger sandbox or virtual-machine boundary in addition to container controls.

## 3. Separate build trust from runtime trust

The build system answers:

- What source and dependencies produced this image?
- Were build inputs pinned and reviewed?
- Were secrets kept out of layers and attestations?
- Is provenance verifiable?
- What packages and licenses are present?

The runtime answers:

- Which digest is actually running?
- Under which identity and policy?
- What can it read, write, call, mount, or control?
- Which host and kernel enforce the boundary?

A secure design needs both. Chapter 81's provenance gate cannot compensate for `--privileged`; runtime restrictions cannot make an unknown artifact trustworthy.

## 4. Run as a dedicated non-root identity

Set a non-root default in the final image and enforce it at deployment. Prefer a dedicated numeric UID and GID whose ownership is prepared during the build.

```dockerfile
FROM example/runtime@sha256:<verified-digest>

COPY --chown=10001:10001 ./application /opt/application
USER 10001:10001
ENTRYPOINT ["/opt/application/server"]
```

If the application needs a home directory or name lookup, create the account and writable directory using the final stage's distribution-specific account tools. Numeric execution itself does not require a passwd entry.

Names can differ between host and image. Numeric IDs cross filesystem boundaries. Coordinate bind mounts and volumes without recursively changing arbitrary ownership at every startup.

Non-root reduces ordinary authority but does not erase mounted credentials, world-writable files, kernel attack surface, or application permissions.

## 5. Avoid runtime privilege-dropping wrappers where possible

Starting as root and dropping privilege later creates a privileged initialization window. It also depends on wrapper correctness, signal forwarding, environment sanitation, and ownership changes.

Prefer build-time ownership and a process that starts directly as its final identity. When privileged initialization is truly required:

- isolate it as a short, auditable step;
- grant only the required capability or resource;
- make it idempotent and bounded;
- remove privileged credentials before application startup;
- verify the post-drop UID, GID, groups, and capabilities;
- use `exec` so the application becomes PID 1.

Do not ship `sudo` as a general escape hatch in a runtime image.

## 6. Capabilities divide traditional root authority

Linux capabilities split privileged operations into named units. Capability sets can include permitted, effective, inheritable, bounding, and ambient sets.

Examples of sensitive capabilities include:

- `SYS_ADMIN`, which gates many unrelated kernel operations;
- `NET_ADMIN`, which changes network configuration;
- `SYS_PTRACE`, which can inspect processes under applicable rules;
- `DAC_OVERRIDE`, which bypasses file permission checks;
- `SYS_MODULE`, which can affect kernel modules;
- `BPF`, which enables powerful kernel instrumentation;
- `MKNOD`, which creates device nodes;
- `NET_RAW`, which permits raw and packet sockets.

Capability behavior also depends on user namespaces, seccomp, mandatory policy, and kernel version. A capability is not a portable application permission string.

## 7. Drop all capabilities, then add evidence-backed exceptions

A strong starting point is:

```bash
docker run --cap-drop ALL example/application@sha256:<digest>
```

Add one capability only when a traced required operation fails and the threat review accepts the consequence:

```bash
docker run \
  --cap-drop ALL \
  --cap-add NET_BIND_SERVICE \
  example/application@sha256:<digest>
```

Modern Linux configurations can often allow unprivileged binding below port 1024 through host policy, or the application can use a higher container port behind normal publication. Do not add a capability merely to preserve a historical port number.

Test startup, steady operation, shutdown, health checks, backup, restore, and diagnostics under the final set.

## 8. Prevent privilege acquisition after startup

`no_new_privs` tells the kernel that a process and its descendants cannot gain additional privilege through mechanisms such as set-user-ID binaries or file capabilities during `execve`.

```bash
docker run \
  --security-opt no-new-privileges \
  example/application@sha256:<digest>
```

This complements non-root execution and capability reduction. It does not remove existing capabilities, filesystem access, secrets, or runtime API authority.

Some software assumes set-user-ID helpers work. Treat such a failure as a design question, not an automatic reason to disable the control.

## 9. Use seccomp to reduce syscall attack surface

Seccomp filters system calls and, for supported cases, their arguments. Docker applies a default seccomp profile on supported Linux configurations unless it is explicitly disabled or replaced.

Do not use `seccomp=unconfined` as a generic compatibility fix. First identify:

- exact denied syscall and arguments;
- calling executable and feature;
- whether the feature is required;
- kernel and runtime versions;
- whether a narrow reviewed profile change is possible;
- what additional kernel interface the exception exposes.

Seccomp filters calls; it does not decide which filesystem objects a permitted call may access. Combine it with capabilities, namespaces, and mandatory policy.

## 10. Mandatory access control constrains objects

SELinux, AppArmor, and other Linux Security Modules can restrict file, network, signal, capability, and process interactions according to host policy.

These controls can deny an operation even when UID, mode bits, and capabilities appear to allow it. Preserve their enforcement during troubleshooting.

Do not disable labeling or run an unconfined profile merely to make a mount work. Inspect the denial, confirm the intended object and operation, and apply the platform's narrow supported label or profile change.

Custom policy authoring is beyond this chapter, but policy status and denials belong in every incident record.

## 11. Make the root filesystem read-only

A read-only root prevents ordinary runtime modification of image content and many persistence techniques:

```bash
docker run \
  --read-only \
  --tmpfs /tmp:rw,nosuid,nodev,noexec,size=16m \
  example/application@sha256:<digest>
```

Declare every writable path and its purpose:

- bounded temporary state in tmpfs;
- durable state in an owned volume or external service;
- configuration and secrets as read-only mounts;
- runtime sockets in a small writable mount;
- no writable application or executable directories.

Read-only root does not protect writable volumes or bind mounts. Mount options and ownership must constrain each path separately.

## 12. Restrict writable mounts

Every writable mount is authority over its backing data. Review:

- exact host or volume source;
- destination path and content it hides;
- read-only versus read-write mode;
- UID, GID, ACL, and security label;
- `nosuid`, `nodev`, and `noexec` support;
- mount propagation;
- data sensitivity and backup ownership;
- whether another workload shares it;
- behavior after container compromise.

Never mount the host root, `/proc`, `/sys`, boot files, credential directories, or arbitrary application sockets just to simplify an operation. A narrow file mount is safer than a broad parent directory when semantics permit.

## 13. Treat device access as host authority

Devices expose kernel drivers and physical or virtual hardware. Privileged mode commonly grants broad device access and relaxes other controls.

If a workload truly needs a device:

- map only the exact device;
- grant only required read, write, or `mknod` permissions;
- add only required capabilities;
- isolate the host or node pool if compromise impact is high;
- patch the driver and firmware;
- test removal, reset, and concurrent use;
- monitor device and kernel errors.

GPU, accelerator, USB, block, sound, and FUSE access have different threat models. Do not replace that analysis with `--privileged`.

## 14. Avoid host namespace sharing

Sharing host PID, network, IPC, user, or other namespaces removes an isolation layer.

Examples:

- host PID access can expose process metadata and signal targets under granted permissions;
- host networking shares interfaces, routes, loopback, and port space;
- host IPC can expose shared-memory or message-queue objects;
- disabling user-namespace mapping restores host identity relationships;
- broad mount propagation can carry host mount changes across boundaries.

Require a concrete operational need, a threat review, and a stronger surrounding boundary. Diagnostic convenience is not sufficient justification.

## 15. The runtime socket is a control-plane credential

Access to the Docker daemon API can create containers, mount host paths, access volumes, inspect configuration, and request broad privilege. Membership in the local `docker` group commonly grants root-level host authority through that API.

Do not mount `/var/run/docker.sock` into an ordinary workload. A read-only socket mount does not make API calls read-only; UNIX socket mount mode is not an HTTP authorization policy.

For automation that needs runtime operations:

- separate it from untrusted application code;
- authenticate the client;
- authorize exact operations through a purpose-built control service or policy proxy;
- protect transport with SSH or mutually authenticated TLS where appropriate;
- rotate and audit client credentials;
- restrict network reach to the daemon;
- avoid exposing an unauthenticated TCP endpoint.

Treat a leaked daemon client credential as host compromise until proven otherwise.

## 16. Rootless mode reduces daemon and runtime authority

Docker rootless mode runs the daemon and containers as a non-root user, using user namespaces and supporting components to implement available features. This can reduce the impact of daemon or runtime vulnerabilities.

Rootless mode has platform, networking, storage, cgroup, device, and privileged-port limitations that evolve over time. It also does not make the workload harmless: the rootless user can still lose its files, credentials, sessions, and reachable services.

Verify required features and effective resource enforcement. Rootless is an additional boundary, not a reason to restore broad mounts or credentials.

## 17. User-namespace remapping changes host identity

With user-namespace remapping, container UID 0 maps to an unprivileged subordinate UID on the host. The daemon can still run as host root, unlike rootless mode.

Remapping reduces the host authority of container identities, but introduces filesystem and integration constraints:

- bind-mount ownership must match mapped IDs;
- subordinate UID and GID ranges must not overlap;
- some host namespace and privileged features are incompatible;
- existing engine storage can appear unavailable after enabling it;
- external volume drivers must understand mappings.

Enable it as a planned host architecture decision, preferably on a new installation, and test the complete workload lifecycle.

## 18. Inject secrets at runtime with least scope

Do not store runtime secrets in:

- image layers or build context;
- Dockerfile `ARG` or `ENV`;
- source control;
- image labels;
- command-line arguments visible to process inspection;
- ordinary logs or health output;
- broad shared environment files.

Prefer a platform secret mechanism that grants each service only what it needs, exposes it as a bounded file or short-lived identity, supports rotation, and records access.

Compose file-backed secrets improve service scoping but inherit host-file protection and implementation behavior. Swarm-managed secrets have different encrypted storage and delivery guarantees. Name the platform before making a security claim.

## 19. Make applications reload or rotate credentials safely

Secret injection is incomplete without lifecycle behavior:

- how the application detects a new version;
- whether existing connections continue;
- overlap between old and new credentials;
- atomic file replacement semantics;
- failure behavior during rotation;
- revocation timing;
- audit evidence;
- cleanup from memory, temporary files, and crash dumps.

Prefer workload identity and short-lived credentials over static shared passwords where the platform supports them. Scope external authorization independently of container UID.

## 20. Keep build secrets out of layers

Build arguments and environment variables can persist in image history, metadata, cache, or provenance. Use the builder's secret or SSH mount mechanism for private dependency access.

```dockerfile
# syntax=docker/dockerfile:1
RUN --mount=type=secret,id=package_token \
    PACKAGE_TOKEN_FILE=/run/secrets/package_token \
    /opt/build/fetch-private-dependencies
```

The build step must not copy, print, archive, or embed the mounted secret into its output. Review build logs and attestations as potential disclosure surfaces.

Separate build credentials from deployment credentials and grant them read-only, repository-specific access where possible.

## 21. Enforce artifact identity at deployment

A hardened runtime should consume an approved immutable digest and verify the evidence required by policy:

- trusted registry and repository;
- expected signer or identity;
- provenance and source revision;
- approved builder and build parameters;
- SBOM availability;
- vulnerability and exploitability policy;
- base-image policy;
- license or organizational requirements;
- freshness and revocation state.

Scan results are time-dependent. Re-evaluate stored artifacts as vulnerability intelligence changes, and rebuild from patched inputs rather than modifying running containers.

## 22. Minimize the runtime image

A smaller runtime image can reduce packages, tools, and update obligations. Use multi-stage builds to keep compilers, package managers, source, tests, and build credentials out of the final stage.

Minimalism must remain operable:

- include trusted CA roots if TLS requires them;
- include time-zone or locale data only when needed;
- preserve license notices and required metadata;
- provide an external diagnostic plan;
- retain a supported patch path;
- avoid downloading executables at startup.

Removing a shell does not prevent arbitrary code execution after memory corruption. It removes one convenient tool, not the underlying application authority.

## 23. Patch by replacement

Maintain:

- an owner for each image;
- an upstream release and security-advisory feed;
- regular rebuilds even when application source is unchanged;
- a supported-version policy;
- automated provenance, SBOM, and vulnerability gates;
- compatibility and rollback tests;
- deployment evidence that identifies the actual digest;
- retirement of superseded images and credentials.

Do not patch a running container interactively. That creates an untracked instance whose state disappears on replacement and whose provenance no longer matches the image.

## 24. Constrain network reach and egress

Network access is authority. Apply Chapter 84's scoped networks and publication rules:

- publish only required entry points on intended host addresses;
- attach only to networks required by the service role;
- restrict egress destinations and protocols where the platform supports it;
- protect metadata, credential, and control-plane endpoints;
- authenticate and authorize service calls;
- resolve through approved DNS paths;
- log policy decisions without sensitive payloads.

An attacker who cannot escape the container may still steal data or control cloud resources through an over-broad workload identity.

## 25. Resource limits are security controls too

Memory, CPU, PID, file-descriptor, log, and storage limits constrain denial-of-service and runaway behavior. They do not correct a vulnerability, but they can reduce blast radius.

Set them from measured demand and preserve the evidence model from Chapter 86. A limit so tight that health checks fail under normal load can cause an availability attack through the control plane.

Rate-limit expensive application operations and bound queues, decompression, parsing, and fan-out inside the service as well.

## 26. Do not trust inherited defaults blindly

Runtime defaults improve over time and differ by engine, version, operating system, rootless mode, and deployment platform. Record and test:

- default capability set;
- seccomp profile and enforcement;
- AppArmor or SELinux profile;
- user-namespace mode;
- masked and read-only kernel paths;
- device policy;
- default network and publication behavior;
- logging and resource defaults;
- daemon API exposure.

An upgrade can fix vulnerabilities and also change behavior. Pin supported versions, read release notes, and verify effective policy after upgrades.

## 27. Inspect effective hardening

On Docker, useful evidence includes:

```bash
docker inspect application-api --format '{{.Config.User}}'
docker inspect application-api --format '{{.HostConfig.ReadonlyRootfs}}'
docker inspect application-api --format '{{json .HostConfig.CapDrop}}'
docker inspect application-api --format '{{json .HostConfig.CapAdd}}'
docker inspect application-api --format '{{json .HostConfig.SecurityOpt}}'
docker inspect application-api --format '{{json .HostConfig.Devices}}'
docker inspect application-api --format '{{.HostConfig.Privileged}}'
docker inspect application-api --format '{{.HostConfig.NetworkMode}}'
docker inspect application-api --format '{{json .Mounts}}'
```

Also inspect process credentials and capabilities, LSM enforcement, seccomp state, open descriptors, network paths, and mounted secrets using approved host or workload tools.

Requested settings can be unsupported, translated, or overridden. Admission and deployment policy should reject unsafe models before creation, while runtime verification catches drift and implementation gaps.

## 28. Encode policy around dangerous combinations

High-value denial rules often include:

- privileged mode;
- added broad capabilities;
- host PID, network, IPC, or user namespaces;
- runtime socket mounts;
- writable host-root or control-plane mounts;
- unrestricted host devices;
- root user without an approved exception;
- writable root filesystem without declared need;
- unconfined seccomp or mandatory policy;
- unverified or mutable image identity;
- secrets in environment or image configuration;
- absent resource limits for shared hosts;
- publication on all host interfaces without review.

Exceptions need an owner, threat analysis, exact scope, expiration, compensating controls, and verification. A permanent wildcard exception is policy removal.

## 29. Plan for an isolation failure

Assume a process obtains code execution and ask what remains protected:

- Does it run as non-root with no capabilities?
- Can it modify executables or startup files?
- Which secrets and data can it read?
- Which networks and control planes can it reach?
- Can it access devices or host namespaces?
- Can it call the runtime API?
- Can it persist beyond container replacement?
- Can it erase logs or detection evidence?
- Does user-namespace or rootless mapping reduce host authority?
- Would a sandbox or VM contain a kernel exploit?

This exercise reveals which layers are independent and which collapse together.

## 30. Safe engine lab: verify a least-authority container

On an approved disposable Linux Docker-compatible engine, this Bash lab creates a container with a numeric non-root identity, read-only root, one bounded tmpfs, no network, no Linux capabilities, `no_new_privs`, and resource limits. It verifies that only the declared temporary path is writable and that device-node creation fails.

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

suffix="$RANDOM-$$"
container="handbook-hardened-$suffix"
image="alpine:3.21"

cleanup() {
  docker rm --force "$container" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker create \
  --name "$container" \
  --user 65532:65532 \
  --read-only \
  --tmpfs /tmp:rw,nosuid,nodev,noexec,size=1m \
  --network none \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --memory 32m \
  --memory-swap 32m \
  --cpus 0.25 \
  --pids-limit 32 \
  "$image" sh -c '
    test "$(id -u)" = "65532"
    test "$(id -g)" = "65532"
    printf "writable-only-here\n" > /tmp/probe
    test "$(cat /tmp/probe)" = "writable-only-here"

    if touch /etc/should-not-exist 2>/dev/null; then
      printf "root filesystem unexpectedly writable\n" >&2
      exit 1
    fi

    if mknod /tmp/should-not-exist c 1 3 2>/dev/null; then
      printf "device creation unexpectedly succeeded\n" >&2
      exit 1
    fi

    test ! -e /etc/should-not-exist
    test ! -e /tmp/should-not-exist
  ' >/dev/null

test "$(
  docker inspect "$container" --format '{{.Config.User}}'
)" = "65532:65532"

test "$(
  docker inspect "$container" --format '{{.HostConfig.ReadonlyRootfs}}'
)" = "true"

test "$(
  docker inspect "$container" --format '{{.HostConfig.Privileged}}'
)" = "false"

test "$(
  docker inspect "$container" --format '{{.HostConfig.NetworkMode}}'
)" = "none"

test "$(
  docker inspect "$container" --format '{{json .HostConfig.CapDrop}}'
)" = '["ALL"]'

docker inspect "$container" --format '{{json .HostConfig.SecurityOpt}}'
docker inspect "$container" --format '{{json .HostConfig.Tmpfs}}'
docker start --attach "$container"
```

The lab verifies selected controls, not the absence of every escape path. It does not test the host's seccomp or mandatory-policy profile, user-namespace mapping, kernel patch level, image provenance, or remote authorization.

The cleanup trap targets only the unique container. Pulling the image can leave a cache entry. Pin an approved digest when using the result as security evidence.

## 31. Produce a hardening plan with evidence

For each service, record:

```text
service role and data classification:
approved image digest and provenance policy:
runtime UID, GID, groups, and user-namespace mapping:
capabilities dropped and narrowly added:
no_new_privs, seccomp, and mandatory-policy state:
read-only root and exact writable mounts:
devices and shared namespaces:
runtime or control-plane API access:
ingress, network memberships, egress, and DNS:
secret sources, grants, rotation, and revocation:
CPU, memory, PID, descriptor, log, and storage limits:
rootless or stronger sandbox boundary:
patch and rebuild owner:
exception owner, scope, expiration, and compensating controls:
verification commands and last observed result:
incident evidence and containment plan:
```

Review the plan whenever the image, platform, host kernel, service role, mount, device, credential, or network dependency changes.

## Common Misconceptions

- “Non-root means safe.” A non-root process can still read mounted secrets, exploit the kernel, call broad APIs, and misuse application permissions.
- “A read-only root makes the container immutable.” Writable volumes, tmpfs, external services, and kernel state remain mutable.
- “`--privileged` is one capability shortcut.” It grants broad capabilities, devices, and relaxed security policy.
- “The Docker socket is harmless if mounted read-only.” API authorization is not enforced by the mount's file-write flag.
- “Rootless means no host impact.” The rootless user and every resource reachable by that identity remain at risk.
- “A clean vulnerability scan proves the image is trusted.” It does not establish provenance, runtime authority, exploitability, or future vulnerability state.
- “Removing the shell prevents code execution.” It removes a tool, not the permissions of compromised application code.

## Core Computer Science Concept

Container security is **least authority through independent reference monitors**. Identity, capabilities, syscall filtering, mandatory policy, mounts, devices, networks, credentials, and artifact admission each mediate a different operation; defense in depth requires that compromise of one monitor does not silently bypass all others.

## Engineering Connections

- Kernel isolation boundaries extend Chapter 78's namespace model.
- Provenance and digest admission reuse Chapter 81's artifact identity chain.
- Read-only roots and mount ownership apply Chapter 83's storage classification.
- Network reach is constrained using Chapter 84's path model.
- Compose secret grants and project resources inherit Chapter 85's ownership model.
- Resource limits and forensic evidence come from Chapter 86.

## From the Field

A deployment runs its web service as non-root and passes an image scan, so the team labels it hardened. The service also mounts the Docker socket to discover neighboring containers. An application compromise uses that API to start a privileged container with the host root mounted. The decisive authority was the runtime socket, not the UID or scan result; removing it and replacing discovery with a narrow service API restores an actual boundary.

## Engineering Review

### What problem does this solve?

It limits what compromised or defective container code can do to the host, data, credentials, neighboring workloads, control planes, and software supply chain.

### Why was it designed this way?

Containers share host infrastructure, so security depends on several kernel and platform monitors restricting different operations rather than on one opaque container boundary.

### When should I use it?

Use this threat-informed review for every production workload, build job, diagnostic container, third-party image, and automation service that can control a container runtime.

### When should I avoid it?

Avoid assuming these controls alone are sufficient for hostile multi-tenancy or high-impact kernel-exploit scenarios; add a stronger sandbox, VM, dedicated host, or separate account according to the threat model.

### How does this make me a better engineer?

It teaches you to measure authority across artifacts, kernel mechanisms, data, networks, credentials, and control planes instead of equating a non-root UID or vulnerability scan with security.

### How does this reduce waste?

It prevents blanket privilege, emergency host rebuilds, leaked credentials, unreviewed exceptions, runtime snowflakes, oversized images, and controls that look strong but protect the wrong boundary.

## Handbook Principle #87

> Harden the authority around the process, not the label on the container—and preserve a stronger boundary for what you cannot safely grant.

## Practical Observation

Run the disposable hardening lab on an approved Linux engine and save the inspected user, root-filesystem, capability, security-option, network, and tmpfs fields. Then compare one real service against the hardening-plan worksheet. Any exception should identify the exact failed operation and the narrower alternative that was tested.

## Looking Ahead

A single host can apply these controls directly. Across hosts, a system must continuously choose placement, reconcile desired state, route to changing replicas, coordinate rollouts, and attach policy to workload identity. Chapter 88 explains why orchestration introduces controllers, pods, services, probes, and scheduling—and when that complexity is justified.

## References

- [Docker Engine security](https://docs.docker.com/engine/security/)
- [Docker Engine runtime privilege and Linux capabilities](https://docs.docker.com/engine/containers/run/#runtime-privilege-and-linux-capabilities)
- [Docker Engine seccomp profiles](https://docs.docker.com/engine/security/seccomp/)
- [Docker Engine AppArmor profiles](https://docs.docker.com/engine/security/apparmor/)
- [Docker Engine rootless mode](https://docs.docker.com/engine/security/rootless/)
- [Docker Engine user-namespace remapping](https://docs.docker.com/engine/security/userns-remap/)
- [Docker Engine daemon socket protection](https://docs.docker.com/engine/security/protect-access/)
- [Docker build secrets](https://docs.docker.com/build/building/secrets/)
- [Docker Compose secrets reference](https://docs.docker.com/reference/compose-file/secrets/)
- [OCI Runtime Specification — Linux process capabilities](https://specs.opencontainers.org/runtime-spec/config-linux/#process)
- [Linux `capabilities(7)` manual page](https://man7.org/linux/man-pages/man7/capabilities.7.html)
- [Linux `seccomp(2)` manual page](https://man7.org/linux/man-pages/man2/seccomp.2.html)
- [Linux kernel `no_new_privs` documentation](https://docs.kernel.org/userspace-api/no_new_privs.html)
