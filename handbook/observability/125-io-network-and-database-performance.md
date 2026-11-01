# Chapter 125 — I/O, Network, and Database Performance

When CPU is not the limit, latency usually accumulates while work waits: for a socket, connection, lock, queue, device, page, remote response, or durable commit. “I/O is slow” is not a diagnosis. The engineer must follow one workload across layers, decompose elapsed time, identify the first saturated or serialized resource, and verify the fix at the user boundary.

Storage, network, and databases are coupled. A missing index increases reads; reads fill device queues; queueing extends transaction time; long transactions hold locks and connections; pool wait causes API timeouts and retries; retries increase load. Optimizing one local measurement without the chain can amplify the incident.

This chapter does not cover firmware tuning, network benchmark engineering, database-engine internals, or vendor-specific performance recipes.

## 1. Start with an end-to-end latency budget

For one task update, divide the journey into measured phases:

```text
client and edge             24 ms
admission and queue         11 ms
connection acquisition    180 ms
network to database         18 ms
database lock wait         120 ms
query execution             34 ms
commit and durability       42 ms
response network            21 ms
application CPU             36 ms
unattributed                14 ms
total wall time            500 ms
```

The phases need not be perfectly additive when work overlaps, but the accounting exposes the largest waits and unknowns. Define start and end points, clock source, sampling, and concurrency.

Do not optimize the 34 ms query while 300 ms accumulates in pool and lock waits. Do not blame “the network” for all remote time; server processing and remote queues live between send and response.

Use traces, socket and pool metrics, database wait events, device statistics, and profiles to triangulate the budget.

## 2. Relate latency, throughput, concurrency, and queueing

For a stable system, Little's Law gives an intuition:

```text
average concurrency ≈ throughput × average time in system
```

At 1,000 operations per second and 100 ms average time, roughly 100 operations are in flight. If service time or queueing raises the average to 500 ms, in-flight work approaches 500 unless admission control reduces arrivals.

Throughput can plateau while latency and queue depth continue rising. That is saturation: new work waits without increasing useful completions. Observe:

- arrivals, starts, and successful completions;
- concurrency and queue depth;
- oldest age and wait distribution;
- service-time distribution after admission;
- rejection, timeout, cancellation, and retry;
- resource utilization and errors.

An average hides burstiness and tail amplification. Measure distributions and time alignment.

## 3. Find the first queue

Every bounded resource has a queue, explicit or hidden:

- edge and application admission;
- thread or worker pool;
- database connection pool;
- database lock manager;
- database execution workers;
- filesystem and block layer;
- device command queue;
- network interface and transport buffers;
- downstream rate limiter;
- client retry and connection queues.

The earliest sustained queue often identifies the first limit. Downstream queues may then drain because less work reaches them, making them look healthy.

Measure waiting separately from service. A database call span of 250 ms can contain 180 ms waiting for a client-side connection and only 70 ms inside the database. A device “busy” metric can be high without user harm if the queue stays bounded and latency meets the objective.

## 4. Distinguish bandwidth, operations, and latency

I/O capacity has several dimensions:

- bytes per second;
- operations or requests per second;
- latency per operation;
- concurrency or queue depth;
- request size and read/write mix;
- sequential versus random access;
- synchronous versus buffered or asynchronous completion;
- durability semantics.

A device can exhaust IOPS on small random requests while bandwidth remains low, or bandwidth on large sequential transfers while IOPS remains modest. A network can have available link bandwidth while one request suffers round-trip delay.

Normalize by good work: bytes read per returned row, round trips per update, I/O operations per transaction, or network bytes per successful request. Excess work often matters more than device tuning.

Record advertised limits as hypotheses; measure the actual workload and shared environment.

## 5. Understand cache effects

“Disk latency” may actually be page-cache hit time, filesystem metadata, storage-controller cache, remote block cache, or physical device service. A warm benchmark and cold production restart can differ by orders of magnitude.

Identify caches at each layer:

- application and query-result caches;
- database buffer pool;
- operating-system page cache;
- filesystem metadata and directory caches;
- device or controller cache;
- network and CDN caches;
- client and resolver caches.

State whether the experiment is warm, cold, or mixed. Clearing a host cache is destructive to other workloads and rarely represents normal operation; use isolated environments and bounded fixtures.

Measure hit, miss, admission, eviction, bytes, and miss penalty. A high hit ratio can still hide expensive misses in the tail, while a lower ratio for cheap data may be acceptable.

## 6. Diagnose filesystem and device waits

Useful evidence includes:

- application read, write, open, sync, and metadata-operation rates;
- bytes and request-size distributions;
- completion latency distribution;
- device utilization, queue depth, and service time;
- filesystem dirty data, writeback, and flush behavior;
- page faults and cache misses;
- I/O errors, retries, timeouts, and path failover;
- free space, inode or metadata capacity, and fragmentation where relevant;
- co-tenant and volume-level limits.

Follow application operations to device operations carefully. One logical write can become journal, metadata, data, replication, and flush work. Buffered write completion may not mean durable media completion.

A high I/O wait percentage is not a full diagnosis. Determine which processes and requests wait, which device or remote volume serves them, and what operation pattern created the queue.

## 7. Treat durability as part of performance

Acknowledging a write after memory copy is faster than acknowledging after a durable replicated commit, but the operations promise different outcomes. Never optimize by silently weakening:

- flush or synchronization behavior;
- replication acknowledgment;
- transaction commit semantics;
- ordering or write barriers;
- backup and recovery objectives.

Record where durability begins and when the client is told success. Batch commits can amortize flush cost but increase latency, loss window, and coupling among operations. Asynchronous replication can improve local latency while changing RPO and failover behavior.

Performance comparisons must use equivalent correctness and durability settings. A “faster” test with durability disabled is a different system.

## 8. Decompose network time

Network-facing latency can include:

- name resolution;
- address selection and routing;
- connection queueing and establishment;
- TLS or other security handshake;
- request serialization and transmission;
- propagation and intermediate queues;
- server queue and processing;
- response first byte and transfer;
- retransmission, flow control, and congestion control;
- proxy, load balancer, service mesh, and gateway work;
- connection close or reuse.

Measure phase timing at both endpoints when possible. A ping-like round-trip does not include application protocol, TLS, proxy, or server behavior and may follow different policy.

Use route templates and bounded endpoint classes rather than raw URLs. Record address family, protocol version, connection reuse, region, zone, and proxy path where relevant.

## 9. Count round trips

Even with low processing cost, sequential network round trips add wall time:

```text
minimum sequential latency ≈ round trips × path RTT + server work
```

This is a simplification: connection setup, TLS, congestion windows, multiplexing, loss, and queueing change it. It remains a powerful design check.

Common waste includes:

- one database query per row;
- chatty service calls;
- repeated authentication or metadata lookup;
- small writes each requiring acknowledgment;
- serial requests that could be safely parallel or batched;
- lack of connection reuse;
- redirects and retry layers.

Reduce round trips with set-based queries, batching, projection, local computation, or safe parallelism. Bound batch size and preserve failure attribution; one enormous batch can worsen tail latency and retry cost.

## 10. Inspect retransmission and flow control

TCP provides ordered reliable byte delivery through acknowledgment and retransmission. Loss, reordering, receiver limits, and congestion can reduce throughput or add latency. Observe:

- round-trip estimates and variance;
- retransmissions and timeouts;
- duplicate acknowledgments or loss signals;
- send and receive queue occupancy;
- advertised and congestion windows where available;
- resets and connection failure;
- packet and byte rate;
- interface drops and errors;
- application write and read size.

Retransmission is evidence, not automatically a faulty network. Congestion, overloaded endpoints, buffer pressure, and intentional path policy can contribute.

Do not capture payloads by default. Packet and socket diagnostics can expose credentials and customer data. Use metadata, filters, authorization, bounded duration, and secure retention.

## 11. Analyze connection establishment and reuse

Creating a connection can require DNS, transport, security, authentication, and session setup. Reuse amortizes that cost but introduces pool capacity, stale connection, lifetime, and load-balancing behavior.

Track:

- new versus reused connections;
- establishment time by phase;
- active, idle, closing, and failed connections;
- pool acquisition wait and timeout;
- connection lifetime and rotation;
- per-endpoint and per-instance distribution;
- handshake failures and certificate validation;
- resets, keepalive, and idle timeout;
- credential and DNS changes.

An oversized pool can overwhelm the dependency or consume descriptors. An undersized pool serializes work. A long-lived pool can pin traffic to obsolete endpoints or retain revoked credentials.

Size by measured concurrency, dependency limits, service time, and failure containment—not by the maximum number of application threads.

## 12. Treat the connection pool as a resource boundary

Separate:

- acquisition wait;
- connection validation or setup;
- query or request execution;
- result transfer;
- connection return;
- leak or invalidation paths.

Instrument active, idle, maximum, waiters, acquisition duration, timeouts, creation, destruction, and borrow age. Enforce deadlines while waiting; an operation that spends its entire deadline in the pool should not begin remote work afterward.

The pool is a bulkhead. Separate critical and background work when one can starve the other. Bound queues and shed load before every caller occupies a waiter.

Leaks may be logical—transactions left open, results not consumed, cancellation paths skipping return—even when the underlying socket remains valid.

## 13. Start database diagnosis with wait categories

Database duration can include:

- client-side pool wait;
- parse and network transfer;
- admission and worker scheduling;
- lock or transaction wait;
- buffer or storage I/O;
- CPU execution;
- memory spill or temporary I/O;
- replication or commit wait;
- result serialization and transfer;
- client consumption backpressure.

Use database wait-event and activity views to distinguish them. A “slow query” may spend almost all time waiting on another transaction. A high-CPU plan requires different action from a lock wait or storage read.

Correlate database session and query identity with application trace context through approved, bounded metadata. Do not place user data or unbounded trace IDs into SQL text comments if that breaks plan aggregation or leaks context.

## 14. Read query plans as measured hypotheses

A plan is a tree of scans, joins, sorts, aggregates, and other operations selected from statistics and cost estimates. Inspect:

- estimated versus actual rows per node;
- loops and rows processed, filtered, or removed;
- access path and index condition;
- join order and algorithm;
- sort, hash, or aggregate memory and spill;
- buffers, reads, writes, and temporary I/O;
- parallel workers;
- planning and execution time;
- early termination from limits;
- parameters and prepared-plan behavior.

Large estimate errors can lead to a poor plan. Refresh or improve statistics, understand data correlation and skew, and test representative parameters.

`EXPLAIN ANALYZE` executes the statement and adds measurement overhead. For mutating statements it can change data unless safely wrapped or isolated. It may omit client transfer and representation costs. Use a safe environment, read-only equivalent, or transaction strategy appropriate to the engine.

Toy data does not prove a production-scale plan.

## 15. Design indexes from access paths

An index can reduce scanned work for matching predicates, joins, ordering, or coverage. It also costs:

- write amplification;
- storage and cache footprint;
- maintenance and build time;
- lock or concurrency effects;
- replication and backup bytes;
- planner complexity;
- operational risk during creation.

Choose key order from equality, range, ordering, selectivity, and workload patterns. Include tenant scope where ownership and access require it. Partial, expression, covering, or specialized indexes can help particular predicates but increase coupling.

Do not add an index because one slow query mentions a column. Verify the plan and production-like distribution, then measure read benefit and write cost. Remove unused or redundant indexes through a reviewed lifecycle, not a one-day observation.

Sometimes a sequential scan is correct for a small table or a query returning much of the data.

## 16. Find lock and transaction contention

Measure:

- wait duration and waiters by lock type;
- holder transaction, operation, and age;
- blocked chains and deadlocks;
- transaction duration and idle-in-transaction sessions;
- rows or keys touched;
- retry and abort rates;
- isolation level and predicate or range effects;
- connection occupancy while blocked.

The blocked query is often the victim, not the cause. Find the holder and why its critical transaction remains open. Application think time, remote calls, large batches, and slow clients should not occur inside a transaction without explicit reason.

Fixes include shorter transactions, stable access order, reduced scope, partitioning hot keys, optimistic concurrency, smaller batches, and admission control. Lowering isolation or removing locks changes correctness and requires a new design decision.

Timeouts bound harm but do not remove contention.

## 17. Detect the N+1 and excess-work patterns

An N+1 pattern performs one query to find N items and then one query per item. Evidence includes:

- query count growing linearly with result count;
- many similar statements with different keys;
- low per-query latency but high aggregate wall time;
- excessive round trips and connection occupancy;
- trace fan-out or repeated spans.

Set-based queries, prefetch, batch loaders, or denormalized projections can reduce calls. Preserve authorization, tenant scope, memory bounds, and result-size limits.

Other excess-work patterns include selecting unused columns, scanning then filtering in application code, repeated serialization, full counts for pagination, and rebuilding identical derived data.

Measure rows examined, returned, and consumed. A fast query returning 100 MB to use one row is still wasteful.

## 18. Use batching with bounded tradeoffs

Batching amortizes per-operation overhead, network round trips, commits, and compression. Larger batches also:

- wait longer to fill;
- consume more memory;
- create bursty downstream load;
- increase lock scope and transaction duration;
- make retries repeat more work;
- complicate partial failure;
- worsen one slow item's impact;
- create larger tail latency.

Tune by item count, bytes, and maximum age. Flush on deadline or lifecycle boundaries. Preserve item identity and idempotency so partial outcomes can be reconciled.

Plot throughput, p50/p95/p99 latency, error rate, memory, lock time, and recovery cost across batch sizes. Select the knee, not the largest batch.

## 19. Validate cache changes end to end

A cache can hide database or network cost but introduces staleness, invalidation, stampede, serialization, and another network hop. Measure:

- hit rate by operation and value cost;
- hit and miss latency distributions;
- backend work avoided;
- key cardinality, size, and eviction;
- invalidation lag and correctness;
- cold-start and failure behavior;
- stampede or single-flight effectiveness;
- total cost.

A 95% hit rate is poor if the remaining 5% are expensive correlated misses that overload the database. A local cache may improve latency while increasing stale authorization risk.

Compare the complete user journey and failure modes, not the cache lookup alone. Chapter 111's consistency tradeoffs still apply.

## 20. Avoid unsafe benchmark shortcuts

Performance tests can mislead when they use:

- local loopback instead of realistic network distance;
- one connection instead of production concurrency;
- tiny uniform tables instead of skewed data;
- warm cache only;
- durability, TLS, authorization, or replication disabled;
- a single query parameter;
- no background maintenance or co-tenancy;
- averages without tail and queue measures;
- a closed workload that slows arrivals when latency rises;
- client generation that becomes the bottleneck.

Use isolated representative environments and protect shared systems. Record workload, artifact, schema, statistics, cache state, plan, network path, and resource limits.

The test should preserve correctness and failure semantics. A faster result achieved by returning partial data, relaxing durability, or rejecting work is not equivalent.

## 21. Apply the method to task search

Atlas task-search p95 rises from 180 ms to 1.4 seconds for large tenants. CPU in the API is modest. The trace budget shows:

- connection acquisition: 15 ms;
- database execution: 1,120 ms;
- result transfer: 180 ms;
- response encoding: 55 ms.

Database evidence shows a sequential scan, 4.8 million rows examined, 60 returned, and a temporary sort spill. Estimated rows are 900 because statistics do not represent tenant and status correlation. The query filters tenant and status, orders by updated time, and retrieves a bounded page.

The team tests a tenant/status/updated-time access path on production-like skew after refreshing statistics. It also narrows selected columns. Matched trials show:

- rows examined fall from 4.8 million to 74;
- database p95 falls to 62 ms;
- result bytes fall 68%;
- end-to-end p95 falls to 145 ms;
- write CPU rises 3% and index storage rises by the measured amount;
- no change to tenant scope or result correctness.

The index is accepted with storage, write, and maintenance consequences recorded. Adding API instances would not have fixed the database work.

## 22. Encode a cross-layer latency experiment

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class LatencyBudget:
    total_ms: float
    cpu_ms: float
    queue_ms: float
    connection_ms: float
    network_ms: float
    lock_ms: float
    database_ms: float
    storage_ms: float
    unattributed_ms: float

    def validate(self) -> None:
        values = (
            self.total_ms,
            self.cpu_ms,
            self.queue_ms,
            self.connection_ms,
            self.network_ms,
            self.lock_ms,
            self.database_ms,
            self.storage_ms,
            self.unattributed_ms,
        )
        if self.total_ms <= 0 or any(value < 0 for value in values[1:]):
            raise ValueError("latency budget contains invalid time")
        explained = sum(values[1:])
        if abs(explained - self.total_ms) > self.total_ms * 0.10:
            raise ValueError("latency phases do not reconcile within ten percent")


@dataclass(frozen=True)
class CrossLayerExperiment:
    question: str
    workload_fingerprint: str
    artifact_and_schema: str
    durability_equivalent: bool
    correctness_equivalent: bool
    representative_data: bool
    repeated_trials: int
    before: LatencyBudget
    after: LatencyBudget
    throughput_before: float
    throughput_after: float
    errors_before: float
    errors_after: float
    changed_resource_cost_recorded: bool

    def validate(self) -> None:
        if not all((self.question.strip(), self.workload_fingerprint.strip(), self.artifact_and_schema.strip())):
            raise ValueError("experiment lacks question, workload, artifact, or schema")
        if not self.durability_equivalent or not self.correctness_equivalent:
            raise ValueError("performance comparison changes system semantics")
        if not self.representative_data or self.repeated_trials < 3:
            raise ValueError("data or repetition cannot support the conclusion")
        self.before.validate()
        self.after.validate()
        if self.throughput_before <= 0 or self.throughput_after <= 0:
            raise ValueError("throughput is invalid")
        if not 0 <= self.errors_before <= 1 or not 0 <= self.errors_after <= 1:
            raise ValueError("error ratio is invalid")
        if not self.changed_resource_cost_recorded:
            raise ValueError("optimization hides index, cache, or capacity cost")
```

The tests preserve the cross-layer comparison:

```python
from dataclasses import replace
import unittest

from latency_experiment import CrossLayerExperiment, LatencyBudget


def budget(total: float, database: float, network: float, cpu: float) -> LatencyBudget:
    return LatencyBudget(total, cpu, 5, 10, network, 5, database, 0, total - cpu - 20 - network - database)


def valid_experiment() -> CrossLayerExperiment:
    return CrossLayerExperiment(
        question="Does the tenant search index reduce end-to-end search latency?",
        workload_fingerprint="search-v4; large-tenant-skew; warm-mixed-cache",
        artifact_and_schema="api@sha256:abc; schema=42; stats=2026-11-01",
        durability_equivalent=True,
        correctness_equivalent=True,
        representative_data=True,
        repeated_trials=5,
        before=budget(1_400, 1_120, 180, 55),
        after=budget(145, 62, 22, 36),
        throughput_before=80,
        throughput_after=760,
        errors_before=0.002,
        errors_after=0.002,
        changed_resource_cost_recorded=True,
    )


class CrossLayerExperimentTests(unittest.TestCase):
    def test_complete_experiment_is_accepted(self):
        valid_experiment().validate()

    def test_unreconciled_latency_is_rejected(self):
        experiment = valid_experiment()
        broken = replace(experiment.before, database_ms=700)
        with self.assertRaisesRegex(ValueError, "reconcile"):
            replace(experiment, before=broken).validate()

    def test_weakened_durability_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "semantics"):
            replace(valid_experiment(), durability_equivalent=False).validate()

    def test_changed_correctness_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "semantics"):
            replace(valid_experiment(), correctness_equivalent=False).validate()

    def test_toy_data_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "data"):
            replace(valid_experiment(), representative_data=False).validate()

    def test_single_trial_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "repetition"):
            replace(valid_experiment(), repeated_trials=1).validate()

    def test_invalid_error_ratio_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "error ratio"):
            replace(valid_experiment(), errors_after=1.2).validate()

    def test_hidden_index_cost_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "hides"):
            replace(valid_experiment(), changed_resource_cost_recorded=False).validate()


if __name__ == "__main__":
    unittest.main()
```

The budget model is intentionally simplified; some phases overlap. Its purpose is to prevent “database,” “network,” or “I/O” from remaining one unexplained span and to keep semantic plus resource costs in the comparison.

## 23. Review I/O, network, and database evidence

Before accepting a diagnosis or optimization, ask:

### End-to-end accounting

- Are wall latency, throughput, concurrency, queue depth, and errors measured on the same workload?
- Which phase is waiting, serving, or unattributed?
- Where is the first sustained queue or serialized resource?
- Are averages hiding burst and tail behavior?

### Storage and network

- Are operation size, IOPS, bytes, access pattern, cache state, durability, and queueing explicit?
- Are DNS, connection, security handshake, round trips, retransmission, flow control, server work, and transfer separated?
- Is connection creation versus reuse visible?
- Are capture and diagnostic artifacts protected?

### Database

- Is client pool wait separated from database execution?
- Which wait category, lock holder, transaction, or plan node owns time?
- Are estimated and actual rows, loops, buffers, spills, and transfer bytes compared?
- Does representative data include skew, cardinality, statistics, and parameters?
- Are index write, storage, maintenance, and concurrency costs recorded?

### Proof

- Are correctness, tenant scope, isolation, and durability equivalent?
- Do repeated end-to-end trials improve user latency or throughput without moving the limit?
- Are cost, resource use, recovery behavior, and overload response still acceptable?

## Common Misconceptions

- **“High device utilization means the disk is the bottleneck.”** Queueing and user latency determine whether capacity is harmful.
- **“A fast ping proves the network is healthy.”** It omits application protocol, security, proxies, server queues, and payload transfer.
- **“The database query took 500 ms.”** That span may include client pool acquisition, transfer, lock wait, and result consumption.
- **“Indexes always make reads faster.”** Plans, selectivity, table size, cache, ordering, and returned fraction determine value; writes and storage pay the cost.
- **“The blocked query causes the lock problem.”** The long-lived holder or transaction is often responsible.
- **“Batch larger for more throughput.”** Fill delay, memory, locks, retries, and tail latency eventually dominate.
- **“Disable durability for performance.”** That changes the promised system rather than optimizing it.
- **“More connections increase database capacity.”** Beyond a useful point they create queues, memory use, contention, and failure amplification.

## Core Computer Science Concept

This chapter applies **queueing theory, Little's Law, latency decomposition, caching, reliable transport, flow control, batching, B-tree access paths, cost-based planning, transactions, locks, and controlled experiments**. End-to-end performance emerges from coupled queues and work amplification across layers.

## Engineering Connections

- Filesystems, virtual memory, and device boundaries build on Chapters 40 through 44.
- DNS, transport, TLS, HTTP, and troubleshooting extend Chapters 56 through 63.
- Data models, caching, transactions, capacity, and resilience connect Chapters 108 through 114.
- Metrics, traces, CPU, and memory evidence use Chapters 121 through 124.
- Chapter 126 will test these limits under representative open and closed workloads plus controlled failure.

## From the Field

A search endpoint slows, so the team doubles API instances and database connections. The query scans millions of tenant rows and spills a sort; more clients increase concurrent scans, evict useful pages, and worsen the tail. A trace budget, actual plan, row estimates, buffer evidence, and production-like skew reveal the access-path problem. One measured index and narrower projection improve the journey; scaling callers had only amplified the queue.

## Engineering Review

### What problem does this solve?

It locates where latency and excess work accumulate across application queues, connections, networks, storage, and database execution before selecting a fix.

### Why was it designed this way?

Phase and queue decomposition separates waiting from service, while representative plans and end-to-end trials prevent local improvements from weakening semantics or moving the bottleneck.

### When should I use it?

Use it for latency, throughput plateaus, connection exhaustion, I/O waits, network variability, query regressions, lock contention, cache misses, and batch tuning.

### When should I avoid it?

Do not reach for database or network tuning when CPU profiles and scheduler evidence already show that local execution is the limiting resource.

### How does this make me a better engineer?

You learn to follow coupled queues across layers, read plans as hypotheses, and preserve correctness and durability in performance comparisons.

### How does this reduce waste?

It prevents scaling the wrong tier, adding unused indexes, oversized pools, unsafe cache clearing, packet captures without a question, and benchmarks that omit the expensive contract.

## Handbook Principle #125

> Decompose end-to-end latency into waiting and service at every boundary, find the first queue and excess work, and accept a faster design only when representative trials preserve correctness, durability, isolation, and the full resource cost.

## Practical Observation

Choose one slow database span and split it into connection acquisition, network, lock wait, execution, result transfer, and client consumption. If the tooling cannot separate them, that observability gap is a better first fix than guessing which SQL clause is slow.

## Looking Ahead

Chapter 126 builds representative open and closed load models, exposes saturation and scaling lag, corrects coordinated omission, runs soak and failure-injection tests, and connects the first limit to SLO, recovery, and cost.

## References

- [RFC 9293 — Transmission Control Protocol](https://www.rfc-editor.org/rfc/rfc9293.html)
- [PostgreSQL documentation — Using `EXPLAIN`](https://www.postgresql.org/docs/current/using-explain.html)
- [PostgreSQL documentation — Indexes](https://www.postgresql.org/docs/current/indexes.html)
- [PostgreSQL documentation — Viewing Locks](https://www.postgresql.org/docs/current/monitoring-locks.html)
- [PostgreSQL documentation — Monitoring Database Activity](https://www.postgresql.org/docs/current/monitoring.html)
- [Chapter 111 — Caching as a Consistency Tradeoff](../system-design/111-caching-as-a-consistency-tradeoff.md)
- [Chapter 124 — Memory, Allocation, and Resource-Leak Diagnosis](124-memory-allocation-and-resource-leak-diagnosis.md)
