# Chapter 123 — CPU Profiling and Concurrency Bottlenecks

Performance work begins with a user-visible outcome and a resource hypothesis, not a hot-looking function. A slow request may be waiting on a database, a lock, a thread pool, the scheduler, or CPU. CPU profiling locates where execution samples accumulate while code is on a processor. Concurrency evidence explains why runnable work cannot make progress or why added parallelism stops helping.

The objective is to demonstrate an improvement in workload terms—throughput, latency distribution, resource cost, or capacity—while preserving correctness. Reducing a function's benchmark time is not enough if the end-to-end limit lies elsewhere.

This chapter does not teach assembly optimization, compiler internals, real-time scheduling, or a catalog of language-specific profilers.

## 1. Define the performance claim

Write the observed problem and target before collecting a profile:

> At 2,300 task-update requests per second, p95 server latency is 480 ms against a 300 ms target. API CPU is 92%, runnable queue averages 1.8 tasks per logical CPU, and database latency remains below 40 ms. Determine whether CPU execution or concurrency control is the first limit and improve p95 without increasing error rate or cost per request.

Capture:

- user journey and workload shape;
- rate, concurrency, data, and cache state;
- latency distribution and throughput;
- CPU count, quota, utilization, throttling, and scheduler delay;
- service, artifact, runtime, configuration, and dependency versions;
- correctness and error measures;
- cost or resource envelope;
- target and stopping criteria.

“The service uses too much CPU” lacks a denominator and outcome. High utilization can be efficient when throughput and latency meet requirements.

## 2. Separate wall time from CPU time

Wall time is elapsed duration from start to finish. CPU time accumulates only while execution runs on a processor. With parallel threads, total CPU time can exceed wall time; with I/O or lock waits, wall time can greatly exceed CPU time.

For one request:

```text
wall duration = on-CPU + runnable delay + lock wait + I/O wait + sleep + other delay
```

This is a conceptual decomposition; categories may overlap or be measured differently by the runtime.

A CPU profile samples only on-CPU execution unless the tool explicitly provides wall or off-CPU modes. If latency is 500 ms and attributed CPU is 20 ms, optimizing the widest CPU stack cannot recover 480 ms.

Start with traces, thread states, scheduler and resource metrics. Select CPU profiling when CPU is saturated, throttled, costly per operation, or suspected by evidence.

## 3. Characterize the workload before profiling

Profiles describe the workload that generated them. Record:

- operation mix and arrival pattern;
- request and payload distributions;
- tenant or key skew;
- read/write ratio;
- concurrency and connection reuse;
- warm-up, cache, just-in-time, and runtime state;
- background jobs and telemetry;
- dependency behavior;
- duration and steady-state window;
- hardware, CPU quota, topology, and co-tenancy.

A profile from one synthetic request may emphasize startup and parsing while production spends CPU on serialization under mixed traffic. A profile captured during cache warm-up may not represent steady state. A system-wide profile can reveal kernel, sidecar, or neighbor cost that a process-only profile misses.

Use a reproducible workload from Chapter 119 and retain the exact artifact plus profile command.

## 4. Choose sampling or instrumentation

**Sampling profilers** interrupt or inspect execution periodically and record the current stack. They have bounded overhead proportional to sample frequency and stack collection cost. They estimate where time accumulates but do not count every call.

**Instrumentation or tracing profilers** record function entry and exit or selected events. They can provide exact call counts and timing relationships but add overhead on every observed event, disproportionately affecting small frequent functions and concurrency.

Use sampling for production-like CPU hot-path discovery. Use instrumentation when exact call count or short operation timing is essential and measured overhead is acceptable. Hardware performance counters and scheduler tracepoints answer lower-level questions after ordinary profiles localize the area.

Never compare instrumented and uninstrumented timings without quantifying the observer effect.

## 5. Select a representative sampling frequency

At a nominal 99 Hz for 60 seconds, one fully busy CPU yields roughly 5,940 opportunities for samples before tool loss and scheduling effects. Across many CPUs the count grows. Higher frequency improves resolution but raises interrupt, unwind, storage, and application overhead.

Avoid frequencies synchronized with periodic application work; a non-round value can reduce simple aliasing. The actual profiler may sample CPU cycles, wall time, runtime safepoints, or another event, each with different bias.

Short profiles can miss low-frequency paths. Very long profiles average several system states together. Capture a window matching the problem and annotate phase changes.

Record dropped samples, buffer overruns, profiler frequency, event source, CPU scope, and whether child processes or threads are included. A beautiful graph from a lossy or partial capture is weak evidence.

## 6. Define collection scope

Choose among:

- one process or container;
- all threads of a service replica;
- one CPU or CPU set;
- all processes system-wide;
- a request cohort or trace-linked subset;
- a canary version and matched control;
- user-space only or user plus kernel;
- runtime-managed code plus native libraries.

Process-only data may blame application code while missing proxy, kernel, encryption, or storage work. System-wide data may include unrelated neighbors and require filtering. Container quotas can make a process “100% CPU” relative to its allocation while host CPUs remain idle.

Capture resource identity, CPU topology, quotas, affinity, and virtualization context. Verify the profiler can see every relevant thread and namespace.

## 7. Preserve correct stacks and symbols

CPU attribution depends on unwinding stack frames and resolving instruction addresses. Common failure modes include:

- missing symbols or wrong build ID;
- stripped or expired artifacts;
- optimized inline and tail-called functions;
- omitted frame pointers without working unwind metadata;
- just-in-time code absent from symbol maps;
- native/runtime transitions;
- kernel restrictions or permissions;
- truncated stacks;
- an `unknown` frame wider than the supposed hotspot.

Validate with known call paths and inspect the unknown proportion. Store the exact artifact, symbols, source revision, compiler settings, runtime, and mapping metadata.

Do not interpret an unresolved 40% of samples as harmless. The missing region may contain the true bottleneck.

## 8. Read top tables correctly

Profiler reports commonly show:

- **exclusive or self samples:** execution observed directly in a function;
- **inclusive or cumulative samples:** execution in that function or any descendant;
- caller and callee relationships;
- sample count and estimated share.

A dispatcher can have high inclusive cost because it calls all work while having low exclusive cost. An encoding loop can have high exclusive cost and be a direct hot path. A frequently present function may be called often, be expensive per call, or both; sampling alone does not provide exact call count.

Sort by exclusive value to find leaf work and by inclusive value to find expensive subtrees or ownership paths. Follow callers to determine which workload reaches the code.

Do not optimize generic runtime or allocation frames without identifying the application call sites responsible.

## 9. Interpret call trees and flame graphs

A CPU flame graph aggregates sampled stacks:

- each rectangle is a stack frame;
- width represents the fraction of samples containing that frame;
- the top edge is code observed on CPU;
- frames below show ancestry;
- vertical height is stack depth, not elapsed time;
- horizontal order usually groups similar stacks and is not a timeline;
- color often has no performance meaning unless the legend defines one.

Wide plateaus at the top are candidates for direct CPU work. Wide lower frames identify expensive call paths but may delegate the actual work upward.

Zoom, search, and compare with top tables. Check sample totals before reading tiny width differences. A flame graph visualizes the profile; it does not validate workload, symbolization, or causality.

Use off-CPU or memory flame graphs only with their corresponding units and interpretation.

## 10. Compare matched profiles

Before/after profiles need matched:

- workload and rate;
- duration and steady-state phase;
- artifact except for the intended change;
- hardware, CPU quota, and instance type;
- runtime and dependencies;
- sampling event, frequency, and scope;
- success and correctness rates.

A differential profile can show stacks whose sample share grew or shrank. Sample share is relative: a function can become a larger percentage even when its absolute CPU remains constant because another path improved.

Compare total CPU seconds, completed operations, and samples per operation as well as percentages. Repeat trials and report variability.

If throughput is unconstrained, a faster version may use the same CPU while completing more work. That is an improvement visible in CPU per good operation, not necessarily lower utilization.

## 11. Confirm CPU saturation

High CPU utilization alone is not proof of a CPU bottleneck. Look for:

- sustained utilization near the effective quota or core capacity;
- runnable queue or scheduler delay;
- CPU throttling under container quotas;
- throughput scaling with added CPU;
- latency rising as utilization and queueing rise;
- little time in blocking states;
- on-CPU profiles covering the slow workload;
- stable downstream latency and capacity.

One hot thread can limit a service while total machine utilization is low. Inspect per-thread and per-core distribution. Conversely, many runnable threads can create contention and context switches without useful throughput.

Use a controlled CPU allocation experiment: if doubling effective CPU materially improves the outcome at matched workload, CPU capacity is implicated. If not, another serialized or waiting resource may dominate.

## 12. Distinguish runnable from blocked

Thread states matter:

- **running:** executing on a CPU;
- **runnable:** ready but waiting for a CPU;
- **blocked:** waiting for a lock, I/O, timer, condition, or runtime event;
- **parked/idle:** no assigned work.

CPU profiles observe running stacks. Scheduler or runtime traces can quantify runnable delay and context switches. Blocking or mutex profiles attribute wait to synchronization owners or call sites, subject to tool semantics.

A large thread pool with many runnable workers can increase scheduler delay. A pool with idle workers and queued tasks may be blocked on another limit. A queue with no available workers can indicate long tasks, blocked workers, or a pool-size policy.

Measure queue age, active workers, task duration, runnable delay, and blocked states together.

## 13. Diagnose lock contention

Lock contention appears when multiple execution units serialize on shared state. Evidence can include:

- lock wait duration and waiter counts;
- mutex or blocking profiles;
- long critical-section hold time;
- owner stack and waiter stack;
- throughput flattening as concurrency rises;
- context switches and cache-coherence cost;
- low aggregate CPU with high latency, or high CPU spent spinning.

Do not assume the lock function is the cause. Identify the protected invariant, owner, call site, hold work, and access pattern. The fix may be:

- shorten the critical section;
- move I/O outside it;
- partition state or use per-key locks;
- replace global coordination with immutable snapshots;
- batch updates;
- reduce unnecessary parallelism;
- change ownership rather than select a “faster lock.”

Preserve correctness and memory-ordering requirements. Removing synchronization because a benchmark improves can create rare corruption.

## 14. Inspect thread and worker pools as queues

A pool has arrivals, workers, service time, waiting, capacity, rejection, and downstream dependencies. Monitor:

- submitted, started, completed, rejected, and cancelled work;
- active and idle workers;
- queue depth and oldest age;
- task duration distribution;
- worker blocked/runnable/running states;
- downstream connection or rate limits;
- pool resizing and thread creation;
- priority and tenant fairness.

Increasing the pool helps only when work can run in parallel and downstream resources can absorb it. If a database pool has 50 connections, 500 request threads can create 450 waiters, memory overhead, timeouts, and context switches.

Bound queues and make overload visible. An unbounded pool or queue converts a capacity limit into latency and memory failure.

Use separate pools or concurrency limits for workloads with different priority and blocking behavior when shared capacity would cause head-of-line blocking.

## 15. Understand parallel speedup limits

If fraction `s` of work is inherently serial and the rest parallelizes perfectly across `n` workers, the ideal speedup is bounded by:

```text
speedup <= 1 / (s + (1 - s) / n)
```

With 10% serial work, infinite workers cannot exceed 10x speedup, and real overhead lowers it. Coordination, partition imbalance, memory bandwidth, cache coherence, I/O, and scheduling add limits.

Measure throughput and latency as concurrency increases. A scaling curve commonly shows:

1. near-linear improvement;
2. diminishing returns;
3. plateau at a bottleneck;
4. regression from contention and queueing.

Choose concurrency near the useful region with recovery headroom, not the maximum thread count the runtime permits.

Parallelism is simultaneous execution; concurrency is overlapping work. Increasing concurrency can improve I/O utilization without increasing CPU parallelism, or overwhelm the system without improving either.

## 16. Account for context switches and migration

Context switching saves and restores execution state and may disturb caches, translation lookaside buffers, and branch prediction. High switch rates can result from:

- too many runnable threads;
- very short tasks;
- lock contention and wake-up storms;
- frequent yielding or timers;
- blocking I/O with large pools;
- scheduler or affinity policy;
- telemetry and profiling themselves.

Count voluntary and involuntary switches, migrations, runnable delay, and useful completed work. A high number is not automatically bad; network servers naturally switch often. The question is whether switching grows while throughput flattens and latency worsens.

Thread affinity can reduce migration but also create imbalance and operational complexity. Apply it only after evidence and test across the actual topology.

## 17. Consider cache and memory effects

CPU time can rise because data access stalls on caches or memory, even when source code executes the same instructions. Candidates include:

- poor locality and pointer-heavy structures;
- false sharing of writable data on one cache line;
- large working sets exceeding cache;
- random access and partition skew;
- memory bandwidth saturation;
- allocation and garbage-collection work;
- cross-socket access on non-uniform memory systems.

Start with ordinary profiles and scaling evidence. Use hardware counters or cache-to-cache tools after a hot path and hypothesis are identified; counter interpretation depends on processor and workload.

False sharing is a specific coherence mechanism, not a synonym for contention. Demonstrate shared cache-line traffic and writers before padding structures. Padding can waste memory and move the bottleneck.

Chapter 124 will separate allocation rate, retained heap, resident memory, and leaks.

## 18. Avoid benchmark distortion

A benchmark can measure setup, optimizer artifacts, caches, or the harness instead of the target. Control:

- warm-up and just-in-time compilation;
- dead-code elimination and constant folding;
- fixture creation outside the measured region;
- CPU frequency and power state where material;
- background load and co-tenancy;
- input distribution and data size;
- cache warm/cold intent;
- garbage collection and runtime phase;
- timer resolution;
- profiler overhead;
- sufficient repetitions and ordering randomization.

Microbenchmarks isolate mechanisms but do not predict service impact by themselves. Load benchmarks capture queueing and dependencies but are harder to control. Use both: microbenchmarks for the proposed hot-path change, then representative workload validation.

Never tune to one benchmark input while real workloads vary. Keep correctness assertions inside or beside the test.

## 19. Optimize the bottleneck, not the most interesting code

Rank candidates by:

```text
potential gain × affected workload share × confidence / change risk
```

A function using 2% of CPU cannot deliver a 30% end-to-end CPU reduction even if made free, unless it unlocks another mechanism. A wide stack may be framework code you cannot change directly; reduce how often the application invokes it or the data it processes.

Prefer algorithmic and work-elimination improvements:

- avoid unnecessary serialization or parsing;
- batch repeated operations;
- cache only with correct invalidation and measured value;
- choose a better data structure;
- reduce allocations in a proven hot path;
- move invariant computation out of loops;
- partition shared state;
- remove duplicate retries or transformations.

Low-level changes come after the profile shows that they matter and higher-level semantics are preserved.

## 20. Validate before and after at workload level

An improvement claim should report:

- exact before and after artifacts;
- matched environment and workload;
- repeated trial count and variability;
- throughput and latency distribution;
- CPU seconds and CPU per good operation;
- errors and correctness checks;
- saturation, queueing, and dependency behavior;
- memory, I/O, and cost changes;
- before/after profiles;
- profiler and benchmark overhead;
- regression fixture and monitoring.

If CPU falls but memory doubles and garbage collection later increases tail latency, the change may not be an improvement. If latency falls only because requests are rejected earlier, success population changed.

Test at normal, peak, and overload boundaries. Optimization can alter failure behavior even when steady-state averages improve.

## 21. Apply the method to Atlas Tasks

After fixing database pool exhaustion, Atlas reaches a new limit at 3,000 updates per second. CPU is 94%, runnable delay rises, and database wait remains low.

A 60-second 99 Hz CPU profile on a representative canary shows:

- 38% inclusive samples under JSON response serialization;
- 21% under repeated authorization-policy decoding;
- 14% in allocation and garbage-collection runtime paths;
- 9% in cryptographic digest work;
- the remainder distributed.

Call-site analysis reveals the same policy document is decoded three times per request by independent layers. A request-scoped immutable parsed policy removes duplicate work without expanding authorization lifetime. A microbenchmark demonstrates decoding reduction; the service test at matched accepted throughput shows:

- CPU per good update down 17%;
- p95 latency from 410 ms to 285 ms;
- runnable delay down 42%;
- no change in denial decisions, errors, memory limit, or database latency;
- profile share for policy decoding down from 21% to 3%.

Increasing worker threads had previously worsened latency because CPU was already saturated. The profile and scaling experiment selected work elimination instead of more concurrency.

## 22. Encode a performance experiment

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Measurement:
    good_operations: int
    wall_seconds: float
    cpu_seconds: float
    p95_ms: float
    error_ratio: float

    def validate(self) -> None:
        if self.good_operations <= 0 or self.wall_seconds <= 0 or self.cpu_seconds < 0:
            raise ValueError("measurement has invalid work or time")
        if self.p95_ms <= 0 or not 0 <= self.error_ratio <= 1:
            raise ValueError("measurement has invalid latency or errors")

    @property
    def throughput(self) -> float:
        return self.good_operations / self.wall_seconds

    @property
    def cpu_ms_per_good_operation(self) -> float:
        return self.cpu_seconds * 1000 / self.good_operations


@dataclass(frozen=True)
class PerformanceExperiment:
    question: str
    workload_fingerprint: str
    before_artifact: str
    after_artifact: str
    profile_type: str
    sampling_hz: int
    trial_count: int
    correctness_verified: bool
    profiler_overhead_percent: float
    before: Measurement
    after: Measurement

    def validate(self) -> None:
        if not self.question.strip() or not self.workload_fingerprint.strip():
            raise ValueError("experiment lacks a question or workload identity")
        if not self.before_artifact.strip() or not self.after_artifact.strip():
            raise ValueError("experiment lacks exact artifact identity")
        if self.profile_type not in {"cpu", "wall", "blocking", "lock"}:
            raise ValueError("profile does not match a defined resource")
        if self.sampling_hz <= 0 or self.trial_count < 3:
            raise ValueError("sampling or repetition is insufficient")
        if not self.correctness_verified:
            raise ValueError("performance result changes an unverified outcome")
        if not 0 <= self.profiler_overhead_percent <= 5:
            raise ValueError("profiler observer effect is unbounded")
        self.before.validate()
        self.after.validate()

    @property
    def cpu_efficiency_gain(self) -> float:
        before = self.before.cpu_ms_per_good_operation
        return (before - self.after.cpu_ms_per_good_operation) / before
```

Tests require repeatable workload-level evidence:

```python
from dataclasses import replace
import unittest

from performance_experiment import Measurement, PerformanceExperiment


def valid_experiment() -> PerformanceExperiment:
    return PerformanceExperiment(
        question="Does request-scoped policy decoding reduce CPU per good update?",
        workload_fingerprint="task-update-v3; 3000rps; skew-20pct; warm-cache",
        before_artifact="sha256:before",
        after_artifact="sha256:after",
        profile_type="cpu",
        sampling_hz=99,
        trial_count=5,
        correctness_verified=True,
        profiler_overhead_percent=1.8,
        before=Measurement(180_000, 60, 54, 410, 0.001),
        after=Measurement(180_000, 60, 44.8, 285, 0.001),
    )


class PerformanceExperimentTests(unittest.TestCase):
    def test_complete_experiment_is_accepted(self):
        experiment = valid_experiment()
        experiment.validate()
        self.assertGreater(experiment.cpu_efficiency_gain, 0.17)

    def test_unidentified_workload_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "workload"):
            replace(valid_experiment(), workload_fingerprint="").validate()

    def test_unidentified_artifact_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "artifact"):
            replace(valid_experiment(), after_artifact="").validate()

    def test_unknown_profile_resource_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "resource"):
            replace(valid_experiment(), profile_type="fast").validate()

    def test_single_trial_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "repetition"):
            replace(valid_experiment(), trial_count=1).validate()

    def test_unverified_correctness_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unverified"):
            replace(valid_experiment(), correctness_verified=False).validate()

    def test_excessive_profiler_overhead_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "observer"):
            replace(valid_experiment(), profiler_overhead_percent=8).validate()

    def test_zero_good_operations_are_rejected(self):
        experiment = valid_experiment()
        with self.assertRaisesRegex(ValueError, "work or time"):
            replace(experiment, after=replace(experiment.after, good_operations=0)).validate()


if __name__ == "__main__":
    unittest.main()
```

The experiment does not require latency to improve in every optimization, but it prevents CPU percentages from replacing good-operation efficiency, correctness, artifact identity, repetition, and observer-effect evidence.

## 23. Review CPU and concurrency evidence

Before accepting an optimization, ask:

### Problem and workload

- Is the user outcome, workload, environment, target, and artifact identity precise?
- Do wall time, CPU time, runnable delay, blocking, and dependency waits point toward the selected resource?
- Is the profile window representative and repeatable?

### Profile validity

- Does sampling or instrumentation fit the question?
- Are frequency, scope, duration, dropped samples, and overhead recorded?
- Are stacks complete and correctly symbolized?
- Are inclusive, exclusive, call-tree, and flame-graph meanings interpreted correctly?
- Are absolute CPU and completed work compared, not only relative share?

### Concurrency

- Are worker queues, runnable tasks, lock waiters, critical-section owners, and downstream limits visible?
- Does added concurrency improve, plateau, or reduce throughput?
- Are context switches, migration, cache effects, runtime work, and CPU quotas considered?
- Does the proposed change preserve synchronization and fairness invariants?

### Validation

- Are before and after trials matched and repeated?
- Do good-operation throughput, latency distribution, CPU efficiency, errors, memory, I/O, and cost support the claim?
- Does the regression test reproduce the old limit and verify the new behavior?

## Common Misconceptions

- **“High CPU means inefficient code.”** It may mean useful work at capacity; efficiency needs work and outcome denominators.
- **“A slow request will dominate the CPU profile.”** Waiting consumes wall time but little or no CPU.
- **“The widest flame-graph frame is the bug.”** Width represents sample share and includes ancestry; mechanism and workload still matter.
- **“Horizontal order in a flame graph is time.”** It normally groups stacks and has no timeline meaning.
- **“More threads increase throughput.”** Serialized work, downstream limits, scheduling, and contention bound useful parallelism.
- **“Lock code is expensive, so replace the lock.”** The protected state, hold work, and access pattern determine contention.
- **“Lower CPU utilization proves improvement.”** The version may simply complete or accept less work.
- **“A microbenchmark proves service performance.”** Queueing, data, dependencies, runtime, and concurrency can reverse its effect.

## Core Computer Science Concept

This chapter applies **statistical sampling, call graphs, queueing, scheduler states, mutual exclusion, Amdahl's law, locality, cache coherence, controlled experiments, and dimensional efficiency**. CPU optimization is resource attribution under a representative workload, not code aesthetics.

## Engineering Connections

- Processes, scheduling, memory hierarchy, and concurrency build on Chapters 43, 44, 45, and 76.
- Capacity and queue behavior extend Chapters 109 and 114.
- Reproduction and hypothesis testing use Chapters 118 and 119.
- Metrics, traces, and profile interpretation begin in Chapters 121 and 122.
- Chapter 124 follows allocation, retention, handles, and resident growth that CPU profiles may expose indirectly.

## From the Field

A service's p95 latency rises, so a team adds 4x more request threads. CPU was already quota-saturated; runnable delay and context switches increase, p95 worsens, and downstream connection wait grows. A CPU profile shows duplicate policy decoding, while the scaling curve shows no useful throughput after the original pool size. Removing repeated work improves CPU per operation and latency; adding concurrency only amplified the queue.

## Engineering Review

### What problem does this solve?

It identifies where CPU execution and concurrency constraints limit a representative workload and proves whether a change improves the user-level outcome.

### Why was it designed this way?

Sampling provides low-overhead attribution, scheduler and lock evidence separates running from waiting, and matched before/after trials prevent relative graphs from substituting for results.

### When should I use it?

Use it when CPU capacity, runnable delay, contention, thread pools, or poor parallel scaling plausibly limits throughput, latency, or cost.

### When should I avoid it?

Do not begin with CPU profiling when traces and resource metrics show that the workload is primarily waiting on I/O or an external dependency.

### How does this make me a better engineer?

You learn to read sampled stacks statistically, distinguish execution from waiting, and optimize the constrained resource rather than the most visible code.

### How does this reduce waste?

It prevents speculative rewrites, meaningless flame-graph interpretation, excess threads, invalid percentile claims, unrepeatable benchmarks, and changes that lower CPU by doing less useful work.

## Handbook Principle #123

> Profile the representative workload on the resource it actually consumes, distinguish running from runnable and blocked time, and accept an optimization only when matched trials improve good-operation outcomes without moving the bottleneck into an unmeasured cost.

## Practical Observation

For one slow operation, place wall duration, CPU time, runnable delay, lock wait, and I/O wait in a table—even if some values are initially unknown. The largest unknown is usually a better next measurement than the most interesting function in the first profile.

## Looking Ahead

Chapter 124 separates allocation rate, retained heap, resident memory, fragmentation, caches, file descriptors, handles, and true leaks before changing limits or garbage-collector settings.

## References

- [Linux kernel documentation — Workload tracing with perf](https://kernel.org/doc/html/latest/admin-guide/workload-tracing.html)
- [Go documentation — Diagnostics](https://go.dev/doc/diagnostics)
- [Python documentation — Profiling](https://docs.python.org/3/library/profiling.html)
- [Brendan Gregg — CPU Flame Graphs](https://www.brendangregg.com/FlameGraphs/cpuflamegraphs.html)
- [Linux kernel documentation — False sharing](https://kernel.org/doc/html/latest/kernel-hacking/false-sharing.html)
- [Chapter 122 — Traces, Profiles, and Causal Context](122-traces-profiles-and-causal-context.md)
