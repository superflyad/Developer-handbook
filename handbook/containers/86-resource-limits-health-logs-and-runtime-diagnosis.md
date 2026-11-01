# Chapter 86 — Resource Limits, Health, Logs, and Runtime Diagnosis

A container that disappears under load may have crashed, been killed by its memory cgroup, received an operator signal, failed a health policy, lost its host, or been replaced by reconciliation. The last application log line rarely distinguishes those outcomes by itself.

The central idea is:

> Diagnose a container by correlating configured constraints, live resource pressure, runtime lifecycle evidence, and application signals across both the container and host boundaries.

## 1. A container is a constrained process group

On Linux, a runtime commonly uses cgroups to account for and control process resources. Namespaces shape what processes can see; cgroups shape how much they can consume and how that consumption is measured.

A useful operating model includes:

- CPU time, weight, quota, and throttling;
- memory usage, reclaim, swap, pressure, and OOM events;
- process and thread count;
- block I/O and filesystem capacity;
- network traffic and connection state;
- file descriptors and other process limits;
- lifecycle state, exit status, and signals;
- health-check status and history;
- standard output, standard error, and logging-driver behavior.

The runtime configuration is not the observation. Verify what was applied and what the kernel enforced.

## 2. Start with four evidence classes

For every incident, collect:

1. **Desired constraints:** Compose or runtime settings, image identity, restart and health policy.
2. **Effective runtime state:** inspected cgroup limits, mounts, process configuration, and logging driver.
3. **Time-varying evidence:** metrics, pressure, events, health transitions, and logs.
4. **Terminal evidence:** exit code, signal, OOM flag, restart count, timestamps, and retained artifacts.

No single class is sufficient. A configured 512 MiB limit does not prove the container reached it. A memory graph near 512 MiB does not prove the kernel killed the process. Exit code 137 does not identify who sent `SIGKILL`.

## 3. Unset limits are still a capacity decision

Docker containers have no CPU or memory constraint by default beyond what the host scheduler and kernel permit. An unbounded workload can interfere with every other workload and with the runtime itself.

Before setting limits, measure representative behavior:

- steady-state working set;
- startup and deployment peaks;
- cache growth and reclaim behavior;
- request concurrency and queue depth;
- CPU per unit of useful work;
- thread and child-process growth;
- temporary-file, log, and writable-layer growth;
- behavior during dependency latency or failure.

Choose limits with a failure policy. “Prevent noisy neighbors” is incomplete unless the service also behaves predictably when throttled, allocation fails, or a child cannot be created.

## 4. Memory limits bound a cgroup, not an object heap

A memory limit can account for more than language-managed heap:

- process heap and stacks;
- allocator fragmentation;
- memory-mapped files;
- page cache under the controller's rules;
- native libraries and runtime metadata;
- child processes;
- kernel memory charged to the cgroup;
- tmpfs-backed data;
- some shared pages according to accounting rules.

A 256 MiB application heap inside a 256 MiB container is therefore unsafe. Leave headroom for non-heap memory and transient work.

Language runtimes differ in whether they discover cgroup limits and size themselves accordingly. Verify the exact runtime version and effective settings from inside the deployed artifact.

## 5. Distinguish hard limits, soft pressure, and swap

A hard memory limit establishes an enforcement boundary. A reservation or low watermark can influence reclaim or scheduling without guaranteeing a ceiling. Swap configuration controls whether and how anonymous memory can move to slower storage.

Docker's `--memory-swap` represents combined memory and swap, not swap alone. Its behavior depends on whether `--memory` is set and on host support. Tools such as `free` inside a container can report host-wide swap rather than the container's usable allowance.

Document:

- physical-memory limit;
- combined memory-and-swap limit;
- swappiness or equivalent policy;
- host swap availability and encryption;
- latency impact under reclaim;
- application behavior on allocation failure;
- platform differences between cgroup versions.

Do not disable OOM killing on an unbounded container. That can transfer the failure from one workload to the whole host.

## 6. OOM evidence must be correlated

When a cgroup cannot satisfy memory demand, the kernel can reclaim memory, stall tasks, fail allocations, or kill one or more processes according to its policy and configuration.

Collect all available evidence:

- runtime `OOMKilled` state;
- `oom` and `die` events;
- exit code and finish timestamp;
- cgroup `memory.events` counters such as `oom` and `oom_kill` where available;
- host kernel logs;
- memory usage and pressure before termination;
- restart-policy actions;
- application allocation errors or crash reports.

Exit status 137 commonly means the process died from signal 9, but an operator or timeout can also send `SIGKILL`. It is not sufficient OOM proof.

## 7. Host OOM and cgroup OOM have different blast radii

A cgroup-scoped OOM condition can kill work within the constrained group while preserving the host. Global host exhaustion can select processes across the system and destabilize the runtime, monitoring, or remote access.

The container may not be able to observe or report the event that kills it. Retain host-level kernel and runtime evidence outside the affected container.

When several containers fail together, check host memory, swap, pressure, kernel events, and daemon health before assuming identical application bugs.

## 8. CPU quotas cause throttling, not a crash

A CPU quota limits how much CPU time a cgroup can consume during a scheduler period. Docker's `--cpus` is a convenient expression of quota and period.

When demand exceeds quota, runnable work is throttled until more budget becomes available. Symptoms can include:

- request latency spikes;
- missed heartbeats or lease renewals;
- health-check timeouts;
- growing queues;
- longer stop or startup time;
- low apparent throughput despite a busy process.

The service can be “healthy” according to process state while doing too little useful work. Track throttled periods and time, not only CPU percentage.

## 9. CPU weight is relative, quota is a ceiling

CPU weight or shares influences distribution during contention. It does not reserve CPU and usually does not restrict an otherwise idle host.

A quota imposes a ceiling even when spare CPU exists. CPU affinity restricts which processors may run the work and can concentrate contention.

Use the mechanism that matches the objective:

- relative priority among contending workloads: weight;
- maximum sustained CPU consumption: quota;
- locality or licensed-core requirement: affinity, with careful measurement;
- guaranteed capacity: host or scheduler placement plus capacity planning, not a share value alone.

Real-time scheduling requires specialist host configuration and can starve ordinary work. It is not a shortcut around latency engineering.

## 10. Process limits include threads

A PID cgroup limit counts kernel tasks, which includes threads on Linux. A service can reach the limit with one visible process and a large thread pool.

Symptoms include failed `fork`, `clone`, or thread creation; command-execution failures; stalled worker pools; and health checks that cannot start.

Compare:

- runtime PIDS statistics;
- process and thread counts;
- configured PID limit;
- thread-pool and child-process policy;
- host-wide PID availability;
- application errors at creation time.

Leave enough headroom for the health check and bounded diagnostics, or those tools may fail precisely when needed.

## 11. File descriptors and process limits matter too

Per-process and system limits can constrain:

- open files and sockets;
- processes or user tasks;
- locked memory;
- stack size;
- core dump size;
- queued signals.

“Too many open files” can mean a per-process soft limit, hard limit, service-level limit, or host file-table pressure. Inspect effective limits in the process and host context.

Raising a limit without fixing leaked sockets or unbounded concurrency only delays failure and increases the eventual blast radius.

## 12. Filesystem capacity has several owners

Container disk pressure can occur in separate places:

- image and build cache storage;
- the container writable layer;
- named volumes and bind-mounted filesystems;
- tmpfs mounts charged to memory;
- runtime metadata;
- logging-driver storage;
- external storage services.

A free-space check inside one mount does not describe the others. Inode exhaustion can fail writes while byte capacity remains.

Set bounded log retention, classify writable paths as in Chapter 83, and monitor the filesystem that actually owns each path.

## 13. I/O limits need workload-aware tests

Block I/O weights and throttles depend on the host, storage stack, device, scheduler, and access pattern. A database waiting on synchronization has different requirements from a sequential batch reader.

Observe latency and queueing, not only bytes per second. Page cache can make a short read test appear faster than durable storage. Shared network storage adds independent service and network pressure.

Do not benchmark a writable container layer and assume the result applies to a production volume driver.

## 14. Pressure explains work that is runnable but stalled

Linux Pressure Stall Information can quantify time lost to CPU, memory, and I/O contention. System-level files under `/proc/pressure` and, where supported, per-cgroup pressure files provide recent averages and cumulative stall time.

Pressure can reveal degradation before a hard limit or OOM event:

- memory reclaim stalls requests;
- I/O contention blocks all non-idle work;
- CPU contention leaves tasks waiting to run.

Interpret pressure with workload latency, throughput, and queue metrics. A high resource-use percentage is not itself evidence of harmful contention; stall time connects saturation to lost progress.

## 15. `docker stats` is a sample, not a history

`docker stats` reports live CPU, memory, network, block I/O, and process information. On Linux, the CLI's displayed memory can subtract cache in ways that differ from the Engine API's raw value.

```bash
docker stats --no-stream application-api
docker stats --no-stream --format '{{json .}}' application-api
```

Use it for immediate orientation and verify metric definitions. A single sample can miss a spike that already killed and restarted the container.

For incident reconstruction, export time-series metrics outside the workload with timestamps, instance identity, image digest, host identity, and effective limits.

## 16. Runtime events supply lifecycle context

Docker events can include container creation, start, health transitions, exec operations, OOM, death, stop, kill, restart, and destroy events.

```bash
docker events \
  --filter type=container \
  --filter container=application-api
```

Events are not an unlimited durable audit log. Docker returns only a bounded recent history, and events are scoped to the daemon. Subscribe or export them if they are needed for forensic retention.

Correlate event timestamps with application logs, metrics, deployment actions, and host events. Clock synchronization and explicit time zones matter.

## 17. Inspect terminal state before removing the container

A stopped container can retain valuable metadata:

```bash
docker inspect --type container application-api \
  --format '{{json .State}}'
docker inspect --type container application-api \
  --format '{{json .HostConfig}}'
docker inspect --type container application-api \
  --format '{{json .Config.Healthcheck}}'
```

Relevant state can include running, paused, restarting, exit code, error, start and finish times, OOM status, PID, and health history.

Automatic removal and aggressive pruning can destroy this evidence. Decide whether failed containers should be retained briefly, copied into incident storage, or represented by externally captured events and metadata.

## 18. Exit codes require signal and runtime context

An application-selected nonzero exit code can indicate a controlled failure. Shell conventions often encode signal termination as 128 plus the signal number, but that convention is not a complete provenance record.

Ask:

- Did the application exit itself?
- Did the runtime send the configured stop signal?
- Did graceful timeout escalate to `SIGKILL`?
- Did an operator issue `kill` or remove the container forcibly?
- Did the kernel OOM killer act?
- Did the runtime or host disappear without preserving state?
- Did a wrapper translate or mask the child status?

Use Chapter 82's PID 1 and signal-forwarding model when interpreting termination.

## 19. Health, liveness, readiness, and startup are different

A process can be alive but unable to serve. A service can serve one local probe while unable to accept real traffic. A slow-starting service can be correct but not ready yet.

Define separate contracts:

- **startup:** has initialization completed within its allowed window?
- **liveness:** is the process making progress, or must it be restarted?
- **readiness:** should new work be routed here now?
- **dependency health:** can a required downstream operation succeed?
- **business health:** can the user-visible workflow complete?

Docker container health is one status channel, not a complete orchestration policy. Docker Engine records health state but does not inherently restart an unhealthy standalone container merely because the check failed.

## 20. Design health checks to avoid causing incidents

A health check should be bounded, cheap, safe, and meaningful. Avoid probes that:

- allocate large memory or spawn many processes;
- contend on the same exhausted pool as user traffic without a plan;
- mutate durable state;
- require every optional external dependency;
- perform expensive authentication or database scans;
- hang beyond the configured timeout;
- depend on a tool absent from the image;
- leak credentials into command inspection or logs.

Set interval, timeout, retries, and startup grace from measured behavior. Tight checks under CPU throttling can declare failure because the probe could not be scheduled, not because the application logic is dead.

## 21. Health output is bounded diagnostic evidence

Inspect the current status and recent check results:

```bash
docker inspect application-api \
  --format '{{json .State.Health}}'
```

Capture probe exit code, output, start time, and end time where the runtime provides them. Keep probe output concise and non-sensitive because the history is bounded and can appear in inspection APIs.

If the check calls `localhost`, remember that it tests from the container namespace. It does not verify host publication, external DNS, load balancers, or client authorization.

## 22. Write primary logs to standard streams

Container applications commonly write operational events to standard output and standard error. The runtime's logging driver then routes or stores those streams.

Prefer structured events with:

- timestamp and time zone;
- severity;
- service and instance identity;
- request or trace correlation;
- stable event name;
- outcome and duration;
- bounded diagnostic fields;
- no secrets or unnecessary personal data.

Do not rely on a file inside the writable layer unless a deliberate collector and retention lifecycle owns it. Container replacement can remove it.

## 23. Logging has backpressure and loss semantics

Docker logging drivers can deliver synchronously or through a non-blocking buffer. Blocking delivery can slow or stall an application when the logging destination is unavailable. Non-blocking delivery can drop new records when its buffer fills.

Choose explicitly:

- which events must never be dropped;
- what the application should do if audit logging fails;
- maximum tolerable application backpressure;
- buffer capacity and memory cost;
- rotation and disk limits;
- remote destination failure behavior;
- duplicate behavior during retries;
- retention and access policy.

The default `json-file` driver can consume unbounded disk without rotation. Inspect the daemon and per-container logging configuration; changes usually require container recreation to take effect.

## 24. `docker logs` is not universally authoritative

`docker logs` reads through the configured logging mechanism when supported. Some remote drivers or dual-logging configurations can make its output incomplete or unavailable.

```bash
docker logs --timestamps --since 15m application-api
docker inspect application-api \
  --format '{{json .HostConfig.LogConfig}}'
```

Absence of output can mean the application wrote elsewhere, the driver does not support local reads, logs rotated, the process failed before emitting, or collection failed.

Confirm the logging path and test it during normal operation and collector failure.

## 25. `exec` creates a new process and changes the system

`docker exec` starts another process in a running container while its primary process remains alive. That diagnostic process consumes the container's CPU, memory, PID, file-descriptor, and I/O budgets.

It can also:

- alter files and caches;
- acquire locks;
- change application behavior;
- expose secrets to the operator terminal;
- fail because the container is paused or exhausted;
- run under a different user or privilege if requested;
- disappear when the primary container process exits.

Use the least-privileged, read-only command possible and record what was executed. Never use `--privileged` merely to make diagnosis convenient.

## 26. Minimal images need an external diagnostic plan

A production image may intentionally omit shells, package managers, `ps`, `ss`, and debuggers. Preserve that reduction.

Prepare approved alternatives:

- runtime and host inspection APIs;
- application diagnostic endpoints;
- an ephemeral toolbox image with pinned provenance;
- namespace entry from the host under audited privilege;
- exported metrics, traces, profiles, and crash reports;
- a reproducible staging environment.

A toolbox that joins another container's namespaces can observe sensitive state and affect resource usage. Treat it as privileged incident access, not an ordinary sidecar.

## 27. Restart loops can erase the first failure

A restart policy can turn one failure into a rapid sequence:

```text
bad configuration -> exit -> restart -> repeated initialization
                  -> log churn -> dependency load -> evidence rotation
```

Track restart count and the first transition, not only the latest running state. Set backoff and an escalation threshold in the surrounding platform. Make initialization safe to repeat and avoid destructive startup actions.

When debugging, pause automated reconciliation only under an approved incident procedure; changing the desired state can itself affect evidence and availability.

## 28. Diagnose from host and container perspectives

Inside-container evidence can answer:

- what interfaces, mounts, processes, and limits are visible;
- what the application reports;
- whether local files and endpoints work.

Host or runtime evidence can answer:

- what cgroup was applied;
- whether the kernel reported OOM or pressure;
- what signal or lifecycle action the runtime recorded;
- whether storage, networking, or the daemon failed;
- what other workloads contended at the same time.

If the container cannot see a cause, that may be correct isolation—not missing application instrumentation.

## 29. Safe engine lab: observe health and a bounded OOM

On an approved disposable Linux Docker-compatible engine, this Bash lab starts one constrained healthy service and one disposable memory worker. The worker is limited to 64 MiB with swap disabled for the cgroup, so its deliberate allocation loop cannot consume unbounded host memory.

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

suffix="$RANDOM-$$"
service="handbook-health-$suffix"
worker="handbook-oom-$suffix"
service_image="alpine:3.21"
worker_image="python:3.13-alpine"

cleanup() {
  docker rm --force "$service" "$worker" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker run --detach \
  --name "$service" \
  --memory 64m \
  --memory-swap 64m \
  --cpus 0.50 \
  --pids-limit 64 \
  --read-only \
  --tmpfs /run:rw,nosuid,nodev,noexec,size=1m \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --health-cmd 'test -f /run/ready' \
  --health-interval 1s \
  --health-timeout 1s \
  --health-retries 5 \
  --health-start-period 1s \
  "$service_image" sh -c '
    trap "rm -f /run/ready; exit 0" TERM INT
    printf "service-started\n"
    : > /run/ready
    while :; do sleep 1; done
  ' >/dev/null

health=""
for attempt in $(seq 1 20); do
  health="$(
    docker inspect "$service" --format '{{.State.Health.Status}}'
  )"
  test "$health" = "healthy" && break
  sleep 0.25
done
test "$health" = "healthy"

docker stats --no-stream "$service"
docker logs "$service"
docker inspect "$service" --format \
  'memory={{.HostConfig.Memory}} memory_swap={{.HostConfig.MemorySwap}} nano_cpus={{.HostConfig.NanoCpus}} pids={{.HostConfig.PidsLimit}}'
docker inspect "$service" --format '{{json .State.Health}}'

docker run --detach \
  --name "$worker" \
  --memory 64m \
  --memory-swap 64m \
  --cpus 0.50 \
  --pids-limit 64 \
  --read-only \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  "$worker_image" python -c '
chunks = []
while True:
    chunks.append(bytearray(8 * 1024 * 1024))
  ' >/dev/null

set +e
exit_code="$(docker wait "$worker")"
wait_status=$?
set -e
test "$wait_status" -eq 0

oom_killed="$(
  docker inspect "$worker" --format '{{.State.OOMKilled}}'
)"
test "$oom_killed" = "true"

printf 'worker exit code: %s\n' "$exit_code"
docker inspect "$worker" --format '{{json .State}}'
```

The worker intentionally fails; never substitute an unlimited host process. The exact exit code can vary by runtime and platform, so the lab asserts the runtime's OOM flag instead of assuming that 137 proves the cause.

This lab is Linux-cgroup specific. Docker Desktop adds a virtual-machine resource boundary, and Windows containers use different enforcement and metrics. Pin approved image digests when using the lab as evidence.

## 30. Use an incident evidence worksheet

Capture before removal:

```text
incident start/end and time zone:
container ID, name, service, project, host:
image reference and verified digest:
created/started/finished timestamps:
effective memory, swap, CPU, PID, and ulimit settings:
restart and health policy:
current and recent health results:
exit code, OOM flag, runtime error, restart count:
runtime lifecycle events:
host kernel OOM and pressure evidence:
CPU throttle, memory, PID, I/O, network, and disk metrics:
logging driver and retention state:
application logs/traces/request correlation:
deployment or operator actions:
diagnostic commands that changed state:
retained artifacts and access controls:
```

Then write hypotheses that explain all evidence, list contradicting facts, and design the smallest safe test. Do not turn temporal correlation into causation without a mechanism.

## Common Misconceptions

- “Exit 137 means OOM.” It indicates `SIGKILL` under a common convention; runtime and kernel evidence must identify the sender and reason.
- “CPU limit violations kill the container.” Quota normally throttles runnable work and increases latency.
- “The heap limit equals container memory.” Native memory, stacks, cache, tmpfs, and child processes also consume the cgroup budget.
- “Unhealthy containers automatically restart.” Docker Engine health status alone does not inherently restart a standalone container.
- “`docker stats` is monitoring.” It is a live sample whose definitions and retention differ from a time-series system.
- “No `docker logs` output means the app logged nothing.” Driver, dual-logging, rotation, or collection behavior can hide output.
- “`docker exec` is passive observation.” It creates a resource-consuming process that can mutate the container.

## Core Computer Science Concept

Container operation is **feedback control over shared resources with partial observability**. Limits define enforcement boundaries, metrics sample state, pressure measures lost progress, events describe transitions, and health checks approximate application state; diagnosis requires correlating these imperfect signals over time.

## Engineering Connections

- Cgroups complement Chapter 78's namespace isolation.
- PID 1, signals, and terminal status extend Chapter 82's lifecycle model.
- Writable-layer and log growth apply Chapter 83's state ownership model.
- Health-gated Compose dependencies from Chapter 85 remain vulnerable to later turnover.
- Layered evidence collection reuses the packet and system diagnosis method from Part V.

## From the Field

An API restarts during a traffic spike and its last log line shows an ordinary request. The team first blames that request. Runtime inspection shows `OOMKilled=true`; cgroup events show an OOM kill; host pressure rose during a cache expansion; the configured heap left no room for native buffers. Correlating the four evidence classes turns a coincidental last request into the real capacity and memory-accounting defect.

## Engineering Review

### What problem does this solve?

It separates application failure from cgroup enforcement, host contention, health-check design, logging behavior, operator action, and runtime reconciliation.

### Why was it designed this way?

Containers share a kernel and host resources, so cgroups enforce group policy while runtime and application channels expose different parts of the resulting state.

### When should I use it?

Use this model for sizing, alert design, health checks, restart policy, incident response, performance diagnosis, and every unexplained container exit or slowdown.

### When should I avoid it?

Avoid applying Linux cgroup file names or Docker metric definitions unchanged to Windows containers, non-Docker runtimes, managed platforms, or cgroup v1 systems; preserve the evidence model and map it to that platform.

### How does this make me a better engineer?

It teaches you to distinguish configured policy from effective enforcement, saturation from pressure, signal status from cause, and convenient runtime output from durable evidence.

### How does this reduce waste?

It prevents blind limit increases, noisy restart loops, oversized diagnostic images, lost incident evidence, unbounded logs, and application rewrites for host-level failures.

## Handbook Principle #86

> A container failure has a resource path and a lifecycle path—preserve both before changing the system.

## Practical Observation

Run the bounded engine lab on an approved Linux engine. Record the healthy service's effective limits, stats, logs, and health history, then compare the worker's exit code with its OOM flag and state timestamps. On a real service, add host pressure and runtime events to the same timeline before proposing a cause.

## Looking Ahead

Resource controls limit consumption, but they do not establish least privilege or defend the runtime boundary. Chapter 87 hardens identity, capabilities, filesystems, devices, system calls, credentials, daemon access, and supply-chain policy as one layered container security model.

## References

- [Docker Engine resource constraints](https://docs.docker.com/engine/containers/resource_constraints/)
- [Docker CLI `docker container stats`](https://docs.docker.com/reference/cli/docker/container/stats/)
- [Docker CLI `docker system events`](https://docs.docker.com/reference/cli/docker/system/events/)
- [Docker CLI `docker inspect`](https://docs.docker.com/reference/cli/docker/inspect/)
- [Docker CLI `docker container logs`](https://docs.docker.com/reference/cli/docker/container/logs/)
- [Docker CLI `docker container exec`](https://docs.docker.com/reference/cli/docker/container/exec/)
- [Docker Engine logging overview](https://docs.docker.com/engine/logging/)
- [Docker Engine logging-driver configuration](https://docs.docker.com/engine/logging/configure/)
- [Linux kernel cgroup v2 documentation](https://docs.kernel.org/admin-guide/cgroup-v2.html)
- [Linux kernel Pressure Stall Information](https://docs.kernel.org/accounting/psi.html)
- [OCI Runtime Specification — Linux control groups](https://specs.opencontainers.org/runtime-spec/config-linux/#control-groups)
