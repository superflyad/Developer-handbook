# Chapter 124 — Memory, Allocation, and Resource-Leak Diagnosis

A process that uses more memory than expected does not necessarily leak, and a process with a stable managed heap can still approach its memory limit. Live objects, allocation churn, native arenas, mapped files, shared pages, runtime metadata, thread stacks, buffers, allocator fragmentation, file descriptors, sockets, and GPU or device resources all contribute differently.

A leak is **unintended retained ownership that continues after the work requiring it is complete**. Diagnosis therefore needs a workload lifecycle, an ownership model, repeated measurements, and profiles or snapshots that connect growth to allocation and retention paths.

This chapter does not teach allocator implementation, enumerate garbage-collector tuning flags, diagnose kernel leaks, or perform forensic memory recovery.

## 1. Describe the resource symptom precisely

Start with observations:

> Under a repeated cycle of 10,000 attachment previews followed by ten minutes idle, container usage rises about 180 MB per cycle. Managed live heap returns within 20 MB of baseline, resident anonymous memory does not, and open file descriptors rise by exactly 10,000 per cycle. The process reaches its 2 GB limit after nine cycles.

Capture:

- which resource grows: virtual, committed, resident, private, heap, native, descriptor, handle, thread, socket, or mapped file;
- start, peak, post-work, and post-idle values;
- workload units and cycle boundaries;
- process, container, host, and cgroup or job limits;
- artifact, runtime, allocator, operating system, and configuration;
- garbage-collection or cleanup events;
- user impact, OOM evidence, and restart behavior;
- a known-good version or stable cohort.

“Memory is high” has no baseline, ownership, or failure condition.

## 2. Build a layered memory model

Useful categories include:

- **virtual address space:** addresses reserved or mapped, not necessarily backed by physical memory;
- **committed/private memory:** memory for which backing must exist and that cannot simply be shared with another process;
- **resident set or working set:** pages currently resident in physical memory for the process, including private and shared pages;
- **proportional set size:** resident shared pages divided proportionally among mapping participants where supported;
- **managed heap:** objects tracked by a runtime and collector;
- **native heap:** allocations made outside the managed heap by runtime, libraries, or application code;
- **mapped files and shared memory:** file-backed or interprocess mappings;
- **thread stacks, code, runtime metadata, and JIT output**;
- **kernel-accounted resources:** descriptors, sockets, handles, buffers, and objects that may not appear fully in process heap profiles.

No single number answers every question. Resident memory describes current physical footprint, not the identities of retained objects. A managed heap snapshot cannot explain a native image-decoder leak.

## 3. Separate allocation rate from retained size

Allocation rate measures bytes or objects created per unit of work or time. Retained or in-use size measures what remains live at a snapshot.

High allocation rate can cause CPU and garbage-collection cost while retained heap stays flat. A slow leak can have low allocation rate but a growing live set. Profile both:

- allocation bytes and objects by stack;
- current live bytes and objects by allocation stack or type;
- promotion or survivor behavior where relevant;
- collection frequency, pause, and CPU cost;
- bytes per good operation.

Do not interpret an “allocations since process start” profile as current memory. Conversely, a live-heap profile after collection can hide intense temporary churn that drives CPU and latency.

Sampling profilers estimate allocation populations; record sampling rate and minimum object bias.

## 4. Understand garbage collection before declaring a leak

In a managed runtime, unreachable objects may remain until collection. The runtime may keep freed heap pages reserved or committed for future reuse rather than return them immediately to the operating system. Generational collectors move, promote, or compact objects according to policy.

Observe:

- live heap before and after comparable full or completed collection points;
- collection count, duration, CPU share, and pause distribution;
- heap committed, reserved, and used values;
- survivor and promotion rates;
- finalizer or reference queues;
- allocation and mutation rate;
- memory limit awareness.

Forcing collection can be a diagnostic experiment in an isolated environment, not a routine production fix. It changes timing and may create expensive pauses. If live heap drops but resident memory remains, investigate allocator retention, fragmentation, native memory, and working-set policy.

## 5. Trace retention paths, not only allocation sites

An allocation stack tells where an object originated. A retention path explains why it remains reachable. Common owners include:

- unbounded maps and caches;
- global registries and event listeners;
- queues and retry buffers;
- thread-local or task-local state;
- closures and callbacks;
- session or tenant maps;
- orphaned futures and coroutines;
- finalizer queues;
- native handles referenced by wrappers;
- class loaders, modules, plugins, or generated code.

Use dominator trees, reference graphs, roots, retained size, and object-count diffs where the runtime provides them. A large object can be retained by one tiny registry entry; optimize the owner, not merely the leaf type.

Allocation sites can be widespread while one lifecycle omission causes retention. Connect type and stack evidence to the business operation that should release ownership.

## 6. Compare snapshots at equivalent lifecycle points

One snapshot shows state, not growth. Capture at controlled points:

1. after startup and warm-up;
2. after baseline collection or idle stabilization;
3. after one workload cycle;
4. after work is expected to release;
5. after repeated cycles;
6. after a comparable collection and idle period.

Diff by live bytes, object count, allocation site, type, and retaining root. Normalize by completed work.

Equivalent state matters. Comparing a cold baseline with a warmed cache will label intentional initialization as a leak. Comparing just before collection with just after collection exaggerates growth. Record cache population, active requests, queue depth, and runtime phase beside each snapshot.

Snapshot collection can pause or perturb the process and may contain sensitive object content. Use isolated replicas, access controls, encryption, and minimal retention.

## 7. Diagnose native memory separately

Native growth can originate from:

- compression, image, database, cryptographic, or networking libraries;
- runtime and just-in-time compiler metadata;
- direct or off-heap buffers;
- foreign-function interfaces;
- thread stacks;
- memory-mapped files;
- allocator arenas and caches;
- graphics or accelerator resources;
- leaked native handles.

A managed heap that returns to baseline does not clear these candidates. Use process mapping breakdowns, native allocation tracing, library-specific diagnostics, and controlled feature disablement.

Map regions by anonymous versus file-backed, private versus shared, resident versus merely virtual, and growth over cycles. Preserve build IDs and symbols for native stacks.

Ensure the profiler covers child processes and sidecars if the product resource limit aggregates them.

## 8. Distinguish fragmentation and allocator retention

An allocator can hold free blocks that are not reusable for the next allocation size or not returned to the operating system. Multiple arenas, thread caches, page granularity, long-lived objects interleaved with short-lived objects, and size-class behavior can keep resident memory high.

Evidence includes:

- application live bytes stable while allocator committed or resident bytes remain high;
- free space present inside arenas;
- different allocation-size distributions across workload versions;
- resident memory drops after an allocator purge or process quiescence experiment;
- repeated peak workload establishes a high-water mark that later cycles reuse without continued growth.

Fragmentation is not a true ownership leak, but it can still cause OOM under a hard limit. Remedies may include reducing churn, changing object lifetimes or buffer sizes, bounding arenas, selecting an appropriate allocator, or isolating bursty work.

Do not switch allocators or force purges before measuring CPU, latency, and reuse consequences.

## 9. Treat caches as bounded retained state

A cache intentionally retains data, so its growth is not automatically a leak. It becomes unsafe when size, ownership, admission, eviction, or invalidation is undefined.

Measure:

- entries, bytes, and per-entry distribution;
- hit, miss, admission, eviction, and expiration rates;
- maximum and target size;
- tenant fairness and key cardinality;
- stale or invalid entries;
- pinned or in-use entries;
- value cost versus saved work;
- behavior under memory pressure.

An unbounded cache is a leak by policy even if every entry is reachable. A bounded cache can still hold objects that retain a much larger graph than its nominal value-size estimate.

Test steady state under a workload whose unique-key space exceeds capacity. The cache should plateau and evict without violating correctness.

## 10. Interpret resident memory carefully

On Linux, resident set size includes resident anonymous, file-backed, and shared memory. `/proc/<pid>/smaps` or `smaps_rollup` can provide detailed or rolled-up mappings, including RSS and proportional share, though reading mappings has cost and races with change. Fast summary fields may trade precision for scalability.

On Windows, a working set is the pageable memory currently resident for a process and includes shared and private pages. It changes with system pressure and trimming, so it is not equivalent to private committed memory or total ownership.

Across platforms, document the exact metric source. “RSS,” “working set,” “private bytes,” “commit,” and “heap used” are not synonyms.

Compare process view with container or job accounting. Shared pages may be charged differently; kernel and page-cache memory may appear outside the application heap.

## 11. Measure virtual memory without panic

Large virtual size may represent sparse reservations, mapped files, guard regions, runtime heaps, or address-space techniques with little resident or committed cost. On 64-bit systems, reserving a large range can be normal.

Investigate virtual growth when:

- mappings increase without bound;
- the platform has a practical address-space limit;
- commit or resident memory follows it;
- map count or fragmentation prevents new mappings;
- a library reserves per-operation regions and never unmaps them;
- the resource limit includes virtual or committed space.

Record mapping count, types, sizes, permissions, backing, and lifecycle. Do not treat a 20 GB virtual reservation as a 20 GB physical leak without evidence.

## 12. Run a repeated growth experiment

Use a workload cycle with explicit acquire and release phases:

```text
warm up -> stabilize -> snapshot A
run N operations -> wait for completion -> close resources -> stabilize -> snapshot B
repeat K cycles with identical N -> snapshots C...K
```

Plot post-release resource value against cumulative completed work and cycle number. Interpret patterns:

- returns to baseline: temporary peak;
- grows once then plateaus: warm-up or bounded cache;
- grows with active concurrency then falls: expected in-flight state;
- grows linearly after release: likely per-operation retention;
- grows in steps: capacity expansion, arenas, chunking, or periodic leak;
- sawtooth with collection: managed allocation and reclaim;
- managed heap flat but RSS and descriptors grow: native or handle path.

Repeat enough cycles to distinguish a high-water mark from continuing slope. Preserve the same input and lifecycle point.

## 13. Track file descriptors and handles as memory-adjacent resources

Files, sockets, pipes, event objects, processes, threads, registry keys, and runtime handles have independent limits and often retain kernel plus user-space state. Symptoms include connection failures, inability to open files, memory growth, or stalled cleanup.

Measure:

- total open count and soft/hard limit;
- type and target distribution;
- creation and close rate;
- age and ownership stack where possible;
- state such as established, idle, closing, or deleted-but-open;
- counts per operation, tenant, pool, or dependency;
- cleanup on success, error, cancellation, timeout, and retry.

Use structured ownership constructs—context managers, `defer`, `finally`, RAII, or equivalent—but test exceptional paths. A wrapper collected by a runtime may still leave a native resource open until delayed finalization.

An increasing descriptor count can be the clearest evidence even when heap profiles are inconclusive.

## 14. Diagnose thread, task, and connection leaks

Execution units and connections consume stacks, runtime metadata, buffers, descriptors, and downstream capacity. Track:

- live and peak threads, tasks, goroutines, or fibers;
- creation stack or owner;
- running, runnable, waiting, and terminated states;
- pools versus ad hoc creation;
- queue and cancellation behavior;
- database and network connections by state and age;
- work completion compared with unit termination;
- orphaned timers and scheduled callbacks.

A thousand waiting tasks may be correct if bounded and completing; ten new stuck tasks per request is not. Thread count can plateau while task or future count grows inside a pool.

Use lifecycle invariants: every accepted preview reaches completed, cancelled, expired, or dead-lettered; every borrowed connection returns or is invalidated; every registered listener unregisters with its owner.

## 15. Preserve OOM evidence

An out-of-memory termination may come from:

- container or job memory limit;
- host pressure and victim selection;
- runtime heap limit;
- commit or address-space exhaustion;
- native allocation failure;
- descriptor or mapping exhaustion misreported as memory;
- sudden peak rather than gradual leak.

Collect before restart where safe:

- limit, current, peak, pressure, throttling, and OOM counters;
- kernel, orchestrator, runtime, and application termination evidence;
- recent allocation and resident trends;
- heap/native snapshots or low-overhead profiles;
- descriptor, thread, queue, and connection counts;
- workload and deployment changes;
- exit reason and restart count.

Exit code alone may be ambiguous. A process can be killed externally without producing an application exception.

Reserve enough operational capacity for diagnostics, but do not depend on creating a huge dump at the moment memory is exhausted.

## 16. Use limits for containment, not diagnosis

Memory, descriptor, thread, connection, and queue limits prevent one process from consuming an entire host or dependency. Set them with workload measurements and recovery behavior.

Raising a limit can postpone failure while increasing blast radius and recovery time. Lowering it can expose growth earlier but cause avoidable restart loops. Pair limits with:

- headroom and saturation indicators;
- graceful shedding or backpressure;
- bounded caches and queues;
- restart rate limits and recovery warm-up;
- dump or profile policy;
- alerts on trend and failure, not only the final OOM;
- capacity for telemetry and runtime overhead.

If restart is an accepted temporary containment for an unavoidable third-party leak, make it observable, rate-limited, drained, and owned. It is not a root fix.

## 17. Quantify growth per unit of work

Normalize retained growth:

```text
retained bytes per operation =
    (post-release bytes at cycle K - stable baseline bytes) /
    cumulative completed operations
```

Do the same for descriptors, tasks, connections, and mapped regions. Fit is not proof, but a stable linear relationship suggests per-operation ownership.

Control for cache keys, active concurrency, tenant cardinality, and input size. A cache can grow per unique key while remaining bounded; an apparent per-request slope may actually track unique tenants.

Report uncertainty and repeated trials. Memory measurements are noisy due to collection, paging, allocator arenas, and unrelated background activity. Use matched controls and lifecycle-aligned snapshots.

## 18. Bound profiler and snapshot effects

Memory tools can:

- retain allocation metadata and stacks;
- increase allocation cost;
- change object lifetime and collection timing;
- pause all threads for a snapshot;
- fault pages into the resident set;
- write large files and consume disk;
- expose secrets from heap content;
- prevent optimization or alter allocator paths.

Measure overhead and use the lightest tool that answers the question. Start with time-series and sampled allocation profiles; escalate to precise snapshots in isolated or canary processes.

Do not collect CPU, precise allocation, execution trace, and full heap dump simultaneously unless the interaction is understood. Tool interference can create the behavior being diagnosed.

Secure dumps, symbols, and snapshots as highly sensitive production data and delete them on schedule.

## 19. Match remediation to ownership

Common fixes include:

- remove collection entries and listeners when owners end;
- cancel and join tasks;
- close resources on every outcome;
- bound caches, queues, registries, and retry histories;
- use weak references only when their semantics are correct;
- reuse buffers with measured caps and concurrency safety;
- reduce allocation rate or object lifetime;
- partition long-lived from short-lived state;
- release native resources explicitly;
- upgrade or isolate a leaking dependency;
- change workload batching or backpressure;
- tune runtime or allocator only after application ownership is understood.

Verify with the repeated growth experiment. The post-release slope should disappear or fall within the defined bound, while throughput, latency, correctness, CPU, and peak memory remain acceptable.

Add a regression test at the lifecycle boundary rather than asserting an exact platform-specific RSS value.

## 20. Apply the method to attachment previews

Atlas attachment previews grow until OOM. Managed heap snapshots after each cycle remain nearly flat, so the team initially blames allocator fragmentation.

Resource inventory shows:

- RSS grows about 180 MB per 10,000 previews;
- managed live heap grows under 20 MB then returns;
- open descriptors grow exactly one per preview;
- deleted temporary files remain open;
- descriptor creation stacks point to the image-decoder error path;
- successful previews close correctly, malformed images do not.

The retained resource is a native file handle, not a managed object graph. The exception path bypasses close. A structured cleanup scope fixes it.

Across ten matched cycles, post-release descriptors return within two of baseline and RSS plateaus after allocator warm-up. Malformed-image correctness, quarantine behavior, throughput, and CPU remain unchanged. The regression fixture repeats failing decodes under a low descriptor limit and asserts bounded post-cycle handle count.

## 21. Encode a resource-growth experiment

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceSnapshot:
    cycle: int
    completed_operations: int
    managed_live_bytes: int
    resident_bytes: int
    open_handles: int
    active_tasks: int

    def validate(self) -> None:
        values = (
            self.cycle,
            self.completed_operations,
            self.managed_live_bytes,
            self.resident_bytes,
            self.open_handles,
            self.active_tasks,
        )
        if any(value < 0 for value in values):
            raise ValueError("resource snapshot contains a negative value")


@dataclass(frozen=True)
class GrowthExperiment:
    workload_fingerprint: str
    artifact_digest: str
    resource_limit_bytes: int
    snapshots_at_post_release: tuple[ResourceSnapshot, ...]
    same_lifecycle_point: bool
    allocation_profile_captured: bool
    retention_or_native_owner_identified: bool
    sensitive_artifacts_protected: bool
    containment_defined: bool

    def validate(self) -> None:
        if not self.workload_fingerprint.strip() or not self.artifact_digest.strip():
            raise ValueError("experiment lacks workload or artifact identity")
        if self.resource_limit_bytes <= 0:
            raise ValueError("experiment lacks the containment limit")
        if len(self.snapshots_at_post_release) < 3:
            raise ValueError("growth needs repeated lifecycle-aligned snapshots")
        for snapshot in self.snapshots_at_post_release:
            snapshot.validate()
        if not self.same_lifecycle_point:
            raise ValueError("snapshots compare different lifecycle states")
        if not self.allocation_profile_captured:
            raise ValueError("allocation rate and live retention are not separated")
        if not self.retention_or_native_owner_identified:
            raise ValueError("growth has no object, handle, or mapping owner")
        if not self.sensitive_artifacts_protected:
            raise ValueError("heap or profile artifacts are exposed")
        if not self.containment_defined:
            raise ValueError("resource exhaustion has no bounded response")

    @property
    def handle_growth_per_operation(self) -> float:
        first, last = self.snapshots_at_post_release[0], self.snapshots_at_post_release[-1]
        operations = last.completed_operations - first.completed_operations
        if operations <= 0:
            raise ValueError("completed work did not increase")
        return (last.open_handles - first.open_handles) / operations
```

Tests reject comparisons that cannot establish ownership or safety:

```python
from dataclasses import replace
import unittest

from growth_experiment import GrowthExperiment, ResourceSnapshot


def snapshots() -> tuple[ResourceSnapshot, ...]:
    return (
        ResourceSnapshot(0, 0, 120_000_000, 220_000_000, 80, 10),
        ResourceSnapshot(1, 10_000, 125_000_000, 400_000_000, 10_080, 10),
        ResourceSnapshot(2, 20_000, 126_000_000, 580_000_000, 20_080, 10),
    )


def valid_experiment() -> GrowthExperiment:
    return GrowthExperiment(
        workload_fingerprint="preview-v2; malformed-images; 10000-per-cycle",
        artifact_digest="sha256:preview-worker",
        resource_limit_bytes=2_000_000_000,
        snapshots_at_post_release=snapshots(),
        same_lifecycle_point=True,
        allocation_profile_captured=True,
        retention_or_native_owner_identified=True,
        sensitive_artifacts_protected=True,
        containment_defined=True,
    )


class GrowthExperimentTests(unittest.TestCase):
    def test_complete_experiment_is_accepted(self):
        experiment = valid_experiment()
        experiment.validate()
        self.assertAlmostEqual(1.0, experiment.handle_growth_per_operation)

    def test_missing_artifact_identity_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "identity"):
            replace(valid_experiment(), artifact_digest="").validate()

    def test_two_snapshots_are_not_a_growth_series(self):
        with self.assertRaisesRegex(ValueError, "repeated"):
            replace(valid_experiment(), snapshots_at_post_release=snapshots()[:2]).validate()

    def test_mismatched_lifecycle_points_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "lifecycle"):
            replace(valid_experiment(), same_lifecycle_point=False).validate()

    def test_missing_allocation_view_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "allocation rate"):
            replace(valid_experiment(), allocation_profile_captured=False).validate()

    def test_unowned_growth_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "owner"):
            replace(valid_experiment(), retention_or_native_owner_identified=False).validate()

    def test_exposed_heap_artifacts_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "exposed"):
            replace(valid_experiment(), sensitive_artifacts_protected=False).validate()

    def test_uncontained_exhaustion_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "bounded"):
            replace(valid_experiment(), containment_defined=False).validate()


if __name__ == "__main__":
    unittest.main()
```

The model forces repeated post-release observations, separates allocation from retention, and recognizes handles and native mappings as owners rather than equating every rise with managed heap.

## 22. Review memory and resource growth

Before diagnosing a leak or accepting a fix, ask:

### Measurement model

- Which exact quantity grows: virtual, committed, resident, private, managed, native, mapped, descriptor, handle, thread, or task?
- How does the operating system, container, runtime, and profiler define it?
- Are allocation rate, live retention, and resident footprint measured separately?
- Are snapshots taken at equivalent post-work and post-cleanup lifecycle points?

### Ownership and mechanism

- Which stack allocates the resource and which root or owner retains it?
- Does growth follow operations, unique keys, concurrency, time, or workload phase?
- Is the pattern warm-up, a bounded cache, fragmentation, allocator retention, or unbounded ownership?
- Are native libraries, mappings, handles, connections, tasks, and thread stacks included?

### Safety and proof

- Are OOM and limit evidence preserved before restart?
- Are dumps and snapshots protected as sensitive data?
- Does the repeated experiment show that the post-release slope is removed?
- Did the fix preserve correctness, throughput, latency, CPU, peak use, and failure containment?
- Does a lifecycle regression test cover success, error, cancellation, timeout, and retry paths?

## Common Misconceptions

- **“Rising RSS proves a heap leak.”** Resident memory includes several mapping types and allocator or runtime behavior.
- **“The garbage collector will close every resource.”** Native handles need explicit lifecycle ownership; finalization is delayed and unreliable for prompt release.
- **“High allocation means high retained memory.”** Churn can be reclaimed while consuming substantial CPU.
- **“A flat managed heap proves memory is healthy.”** Native memory, mappings, threads, handles, and kernel buffers can grow.
- **“A cache is not a leak because entries are reachable.”** An unbounded cache is uncontrolled retained ownership.
- **“A large virtual size consumes that much RAM.”** Reservations and sparse mappings may have little resident or committed cost.
- **“Restarting fixes leaks.”** It reclaims resources while preserving the defect and may create an outage loop.
- **“Raise the memory limit.”** It changes time to failure and blast radius, not ownership.

## Core Computer Science Concept

This chapter applies **reachability, ownership, object lifetimes, resource acquisition and release, virtual memory, paging, allocation, fragmentation, sampling, queues, and repeated-measures experiments**. A leak is a lifecycle invariant failure, not merely a large number.

## Engineering Connections

- Virtual memory, files, processes, and handles build on Chapters 40 through 47.
- Container limits and runtime diagnosis extend Chapters 83 and 86.
- Capacity and containment connect Chapters 109 and 114.
- Reproduction, metrics, and profiling use Chapters 119, 121, 122, and 123.
- Chapter 125 follows waits beyond CPU and memory into storage, networks, pools, queries, and locks.

## From the Field

A preview worker's RSS grows while managed heap snapshots look stable. Engineers tune garbage collection and double the memory limit; failure simply arrives later. Descriptor counts reveal one leaked temporary-file handle per malformed image, retaining deleted mappings and native decoder state. Closing the error path removes the per-operation slope; no collector tuning was relevant.

## Engineering Review

### What problem does this solve?

It attributes resource growth to the correct memory layer or lifecycle owner instead of labeling every high-water mark a managed heap leak.

### Why was it designed this way?

Repeated post-release snapshots distinguish transient peaks and bounded warm-up from continuing retention, while cross-layer resource inventories expose native and kernel ownership.

### When should I use it?

Use it for resident or committed growth, frequent collection, allocation cost, OOM termination, descriptor exhaustion, stuck tasks, connection growth, and cache expansion.

### When should I avoid it?

Do not capture invasive production heap dumps containing sensitive data when time series, sampled profiles, or an isolated reproduction can answer the question safely.

### How does this make me a better engineer?

You learn to ask which resource, owner, lifecycle, and measurement definition explain growth rather than tuning the first runtime setting available.

### How does this reduce waste?

It prevents pointless garbage-collector tuning, unsafe limit increases, restarts as fixes, dump collection without a question, and optimization of allocation sites that do not retain the resource.

## Handbook Principle #124

> Diagnose growth at equivalent lifecycle points, separate allocation from retention and residency, include native and kernel resources, and call it a leak only when ownership survives the work that justified it.

## Practical Observation

For one memory alert, place managed live heap, native or private committed memory, RSS or working set, open handles, active tasks, and workload units on the same timeline. The series that tracks completed work after cleanup points to a more useful owner than the largest instantaneous number.

## Looking Ahead

Chapter 125 follows latency through I/O queues, network round trips, connection pools, query plans, indexes, lock waits, and downstream capacity before changing code or hardware.

## References

- [Linux kernel documentation — The `/proc` filesystem](https://kernel.org/doc/html/latest/filesystems/proc.html)
- [Microsoft Learn — Working Set](https://learn.microsoft.com/en-us/windows/win32/memory/working-set)
- [Microsoft Learn — Memory Performance Information](https://learn.microsoft.com/en-us/windows/win32/memory/memory-performance-information)
- [Go documentation — Diagnostics](https://go.dev/doc/diagnostics)
- [Go runtime pprof package](https://pkg.go.dev/runtime/pprof)
- [Python documentation — `tracemalloc`](https://docs.python.org/3/library/tracemalloc.html)
- [Chapter 123 — CPU Profiling and Concurrency Bottlenecks](123-cpu-profiling-and-concurrency-bottlenecks.md)
