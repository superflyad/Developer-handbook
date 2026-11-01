# Chapter 43 — Scheduling, Priorities, and Resource Accounting

A slow process is not necessarily waiting for CPU. It may be sleeping for disk, a network response, a lock, a timer, or another process. Scheduler reasoning begins by distinguishing runnable work from blocked work and CPU time from elapsed time.

The central idea is:

> Measure what a thread is waiting for before changing how urgently the scheduler treats it.

## 1. The scheduler allocates processor time to threads

Operating systems schedule runnable threads onto logical processors. A thread can broadly be:

- running on a processor;
- runnable and waiting for a processor;
- blocked waiting for I/O, a lock, timer, event, or other condition;
- stopped or terminated.

Only runnable competition is directly improved by receiving more CPU opportunity. Raising the priority of a thread blocked on a database does not make the database answer sooner. Adding CPUs does not fix a single serialized lock bottleneck.

Schedulers are preemptive: the operating system can stop one runnable thread and run another. Context switching enables responsiveness and sharing, but consumes overhead and disrupts caches. More threads are not automatically more throughput.

## 2. Wall time and CPU time answer different questions

**Wall-clock time** is elapsed real time between start and finish. **CPU time** is time the process or thread actually executed, often separated into user and kernel/system time.

```text
wall time ≈ running + runnable wait + blocked wait + scheduling and measurement effects
```

If a task takes ten seconds of wall time but only 100 milliseconds of CPU time, it mostly waited. If it consumes nearly ten CPU-seconds on one core over ten wall-seconds, it is CPU-intensive. On multicore systems, aggregate CPU time can exceed wall time because threads run simultaneously.

Use the shell or operating-system measurement tools against a known command:

```bash
time command arguments        # shell or external utility, Unix-like systems
```

```powershell
Measure-Command { command arguments }
Get-Process -Id PID | Select-Object CPU, StartTime
```

PowerShell `Measure-Command` reports elapsed duration, not detailed CPU accounting. Match the tool to the question.

## 3. Utilization needs a denominator

“CPU is at 100 percent” is ambiguous without scope. It may mean one logical processor is saturated, all processors are saturated, one process is consuming its quota, or a monitoring system normalized usage differently. Containers and virtual machines add quotas and host scheduling below the guest.

Record:

- measurement interval;
- number of logical processors visible and allowed;
- per-process and system totals;
- quota, affinity, or containment limits;
- runnable queue or pressure evidence;
- workload throughput and latency.

High utilization with acceptable latency can be efficient. Low utilization with high latency can indicate lock or I/O waits. A threshold without workload context is not a diagnosis.

## 4. Load average is not CPU percentage

On Linux, load average represents an averaged count of runnable tasks plus tasks in certain uninterruptible wait states. Values should be interpreted with CPU count, workload type, and pressure evidence. A load of four is not inherently high or low, and it is not “400 percent CPU.”

macOS also reports load averages, but kernel accounting details and tools differ. Windows uses other queue and performance-counter concepts rather than the Unix load-average interface. Do not translate one metric by name alone.

Linux pressure stall information, when available, can show time in which tasks were delayed for CPU, memory, or I/O resources. It complements rather than replaces process-level profiling.

## 5. Priority influences order; it does not create capacity

Unix nice values influence normal scheduling priority; a larger nice value conventionally gives work lower priority. Policies and privileges affect the exact result. macOS also uses quality-of-service classes in frameworks to express workload intent.

Windows combines process priority class and thread priority to calculate scheduling priority, with dynamic behavior for responsiveness. Microsoft explicitly warns that high and real-time priorities can starve system work, including input and disk flushing.

Priority changes can make the system less stable and can hide the actual bottleneck. Raising a consumer above the producer it waits on can create priority inversion. Prefer fixing blocking, bounding work, or isolating workloads. Change priority only with an explicit latency objective, a narrow scope, measurement, and rollback.

## 6. Affinity is a constraint, not a speed switch

CPU affinity restricts where a thread or process may run. It can support specialized latency or licensing needs, but it reduces scheduler flexibility and can concentrate work on an already busy processor. Modern systems also have topology, heterogeneous cores, and NUMA effects beyond a simple processor number.

Do not pin production work based on one short benchmark. Measure cache locality, contention, interrupt placement, and end-to-end latency under representative load. Managed runtimes and container orchestrators may impose their own CPU sets or quotas.

## 7. Resource limits define failure boundaries

Operating systems and service managers can limit CPU time, process count, open files, memory, and other resources. Linux control groups and container limits add hierarchical accounting. Windows job objects can group and constrain processes. Unix per-process resource limits supply another layer.

A failure such as “cannot open file,” “cannot create thread,” or throttled CPU can be caused by a scoped limit even when the host has capacity. Inspect the process's actual containment and service configuration. Raising the host-wide limit may expand blast radius instead of correcting the scoped policy.

## 8. Investigate scheduling claims methodically

1. Define the symptom in workload terms: latency, throughput, deadline miss, or responsiveness.
2. Capture wall time, CPU time, utilization scope, and processor availability.
3. Determine whether important threads are running, runnable, or blocked.
4. Identify the wait source with profiler, trace, or application evidence.
5. Change code, concurrency, limits, or priority only at the proven boundary.
6. Re-measure the workload and system side effects.

Sampling profilers usually impose less distortion than logging every operation. One snapshot from `top`, Task Manager, or Activity Monitor is a clue, not a causal explanation.

## Common Misconceptions

- “A slow process needs higher priority.” It may be blocked and receive little benefit.
- “Load average is CPU utilization.” It counts task states under platform-specific rules.
- “One hundred percent has a universal meaning.” Normalization depends on processor and quota scope.
- “Affinity guarantees better cache performance.” It can also create imbalance and reduce scheduler choice.

## Core Computer Science Concept

Scheduling is **resource arbitration under competing objectives**. Throughput, latency, fairness, energy use, and deadline behavior cannot all be maximized independently. Priority expresses policy; measurement determines whether the policy addresses the actual constraint.

## Engineering Connections

- Web latency can rise from runnable queues even before average utilization appears alarming.
- Background compaction should yield to interactive work without risking starvation.
- Container CPU quotas can throttle an application on an otherwise idle host.
- Lock contention turns available CPU into waiting and requires synchronization analysis, not more priority.

## From the Field

A batch worker misses its deadline, so an operator raises it to the highest priority. Interactive services become unresponsive while the worker remains slow because its threads wait on one saturated storage queue. The correct response measures I/O wait and queue behavior, then changes batching and storage concurrency while restoring normal scheduler policy.

## Engineering Review

### What problem does this solve?

It explains why runnable threads wait for CPU and how to distinguish that delay from other waiting.

### Why was it designed this way?

Preemptive scheduling shares finite processors while balancing fairness, responsiveness, throughput, and system work.

### When should I use it?

Use the model for latency, CPU saturation, concurrency, throttling, priority, and capacity investigations.

### When should I avoid it?

Avoid changing priority or affinity before identifying thread state, limits, and the actual bottleneck.

### How does this make me a better engineer?

It turns “the machine is slow” into measurable running, runnable, and blocked time.

### How does this reduce waste?

It prevents capacity purchases and risky priority changes that cannot improve the constrained resource.

## Handbook Principle #43

> Classify time as running, runnable, or blocked before tuning the scheduler.

## Practical Observation

Run one harmless CPU-oriented command and one command that waits briefly, then compare elapsed and CPU time with native tools. Record processor count and measurement interval. Do not change system priority, affinity, or limits for this observation.

## Looking Ahead

The scheduler decides when threads run; virtual memory determines what address space and resident data they can use. Chapter 44 separates virtual size, resident memory, sharing, and pressure.

## References

- [Linux `sched(7)`](https://man7.org/linux/man-pages/man7/sched.7.html)
- [Linux `/proc/loadavg`](https://docs.kernel.org/filesystems/proc.html#loadavg)
- [Linux Pressure Stall Information](https://docs.kernel.org/accounting/psi.html)
- [Microsoft: Scheduling Priorities](https://learn.microsoft.com/en-us/windows/win32/procthread/scheduling-priorities)
