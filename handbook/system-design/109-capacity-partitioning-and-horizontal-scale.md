# Chapter 109 — Capacity, Partitioning, and Horizontal Scale

A service averaging 20% CPU can still fail every morning because one tenant sends half the writes to one partition. A fleet can add replicas while latency rises because requests wait in a saturated database pool that does not scale with the fleet. An autoscaler can react correctly and still arrive after a three-minute burst is over.

Scale is a workload shape, a bottleneck, and a time-dependent control problem—not a replica count.

The central idea is:

> Estimate work in units that map to resources, find the first constrained queue or shared state, and partition only when the key, skew, movement, and failure consequences are explicit.

## 1. Begin with one journey and one horizon

Capacity planning starts from the requirements model in Chapter 106. Choose a critical journey, a planning horizon, and a workload environment:

```text
journey: list assigned open tasks
horizon: expected peak 12 months after launch
arrival rate: 1,200 requests/second, 2.5x ten-second burst
latency objective: 99% within 300 ms
response: 50 summaries, median 24 KiB
read amplification: one authorization lookup and one indexed task query
skew: largest tenant contributes 18% of peak; hottest project 4%
failure requirement: one compute zone unavailable
```

Capacity statements without a horizon are either already stale or impossible to challenge. Separate observed current load, forecast planning load, and a contingency trigger that demands redesign.

Do not begin with “support a million users.” Registered users do not consume equal capacity. Translate actors into active concurrency, operation rates, data volume, connections, fan-out, and background work.

## 2. Preserve units in every estimate

Dimensional analysis catches errors before benchmarks do. Keep units visible:

```text
requests/s * database operations/request = database operations/s
events/s * average bytes/event = bytes/s
bytes/s * retention seconds = retained bytes before overhead
requests/s * average service seconds = concurrent requests
```

If 1,200 requests/s each cause one authorization read and one task query, the journey creates about 2,400 database operations/s before cache misses, retries, replicas, indexes, or observability.

Use ranges rather than false precision. Document assumptions and calculate lower, expected, and upper cases. The purpose is to expose dominant terms and missing evidence, not to produce a procurement number from guesses.

## 3. Use Little's Law as a consistency check

For a stable system over an observation window, Little's Law relates average items in the system, arrival rate, and average time:

```text
L = lambda * W
```

At 1,200 requests/s with 100 ms average end-to-end time, roughly 120 requests are in flight on average:

```text
1,200 requests/s * 0.1 s = 120 requests
```

This is not a latency guarantee or a complete queueing model. It assumes a meaningful stable window and averages that can hide tails. It is useful for checking connection pools, worker concurrency, queue depth, and memory estimates.

If a queue receives 500 jobs/s and jobs spend an average of 20 seconds waiting and running, about 10,000 jobs are present on average. If dashboards show 100,000, an assumption, measurement boundary, or stability condition is wrong.

## 4. Separate throughput, latency, and concurrency

- **Throughput** is completed work per time.
- **Latency** is time for one operation across waiting and service.
- **Concurrency** is work in progress.
- **Utilization** is the fraction of a constrained resource busy.

They interact but are not interchangeable. Adding concurrency can improve throughput while spare parallel capacity exists. Beyond a bottleneck, it adds waiting, memory, context switching, lock contention, and timeouts.

Record latency distributions, not only averages. A system can meet average throughput while its tail violates the user objective. Break end-to-end latency into queue wait, application service, downstream calls, storage, serialization, and network time. Optimize the dominant and variable terms.

## 5. Account for amplification

One user operation can create many resource operations:

- authentication and authorization reads;
- primary data reads or writes;
- index maintenance;
- replica or cross-region traffic;
- cache fill and invalidation;
- event publication and consumer work;
- logging, metrics, and tracing;
- retries and hedged requests;
- backup, compaction, and migration work.

Define an amplification vector per journey. A task assignment might be one transaction, three index updates, one outbox insert, two projection writes, five notification attempts, and several telemetry records.

Avoid multiplying every worst case together unless those conditions can coincide. But explicitly model correlated failure: a cache outage raises database reads while a retry storm raises request rate and telemetry volume.

## 6. Estimate storage as a lifecycle

Storage grows from arrivals, sizes, retention, versions, indexes, replicas, and cleanup lag:

```text
new tasks/day * average task bytes * retained days
+ comments and attachments
+ indexes and materialized views
+ history and tombstones
+ replicas
+ backups
+ migration headroom
```

Track object-count limits and metadata work as well as bytes. Ten billion tiny objects can be harder to list, index, delete, and restore than a smaller number of large objects with the same total size.

Measure compression on representative data. Include temporary double storage during backfill, compaction, reindex, replica rebuild, and blue/green migration. Capacity without maintenance headroom is capacity that cannot safely change.

## 7. Find the first bottleneck with a resource model

For each stage, record:

- work per request;
- sustainable throughput under the durability and correctness settings used;
- concurrency or queue limit;
- memory and connection footprint;
- downstream quota;
- saturation and rejection signal;
- scale-up mechanism and lead time;
- failure behavior.

The first bottleneck may be CPU, memory, allocator pressure, connection count, lock contention, disk IOPS, network bandwidth, database partitions, a single ordered consumer, external quota, or a human review step.

Do not infer capacity from one utilization graph. Low aggregate CPU can coexist with one saturated core, partition, lock, disk, or dependency. Validate with profiling, query plans, queue wait, per-key heat, and controlled load.

## 8. Preserve headroom for failure and change

If a service must survive loss of one of three equal failure domains, steady state cannot consume nearly all three. After one fails, the remaining two must absorb traffic, recovery work, and imbalance without entering overload.

Headroom also supports:

- rolling deployment surge;
- autoscaling delay;
- cache loss;
- backup and restore;
- index creation and compaction;
- replica rebuild;
- backfill and replay;
- traffic estimation error;
- dependency slowdown.

State which events may coincide. Reserving separate headroom for every impossible combination wastes money; assuming no failures during deployment is unsafe.

## 9. Scale vertically before distributing by reflex

Vertical scaling gives one node more CPU, memory, storage, or I/O. It can be the simplest safe response when the engine, budget, and recovery model support it.

Benefits include fewer network hops, simpler transactions, less coordination, and easier operations. Limits include finite machine sizes, larger single-node blast radius, restart or migration time, nonlinear price, and recovery duration.

Horizontal scaling adds nodes or instances. It can increase throughput and fault tolerance when work can be divided, but introduces routing, partitioning, replication, rebalancing, partial failure, and distributed coordination.

Choose the least complex step that meets the horizon and preserves a tested next step. “Web scale” is not a reason to shard a workload whose measured database fits comfortably on one managed instance.

## 10. Make stateless compute genuinely replaceable

A stateless request tier keeps durable business state outside a particular process instance. Any healthy compatible replica can serve a request when given its identity and inputs.

Hidden state breaks this model:

- in-memory sessions without shared or signed representation;
- local files required by later requests;
- process-local locks used for global invariants;
- sticky routing assumed for correctness;
- background jobs owned only by the receiving process;
- uncheckpointed streams or uploads.

Local caches and connection pools are still state, but they should be disposable and safely rebuilt. Scale-out capacity must include cold-cache, connection-establishment, JIT, and warm-up behavior.

The downstream systems must also accept the added concurrency. Ten more application replicas can exhaust the same fixed database connection limit faster.

## 11. Partition when one ownership unit is insufficient

Partitioning divides data or work into independently placed subsets. It is useful when one node, transaction boundary, index, queue, or failure domain cannot meet size, throughput, locality, or ownership requirements.

Common strategies include:

- hash by stable key for broad distribution;
- range by ordered value for locality and range scans;
- tenant or account for isolation and movement;
- geography for latency or residency;
- time window for append and retention;
- directory or lookup service for explicit placement;
- composite schemes that combine several dimensions.

The partition key determines which operations are local and which require fan-out or coordination. Choose it from dominant access patterns and invariants, not merely cardinality.

## 12. Evaluate a partition key with more than cardinality

A candidate key needs:

- enough distinct values;
- balanced traffic, storage, and growth;
- stable identity and routing availability;
- locality for common operations and transactions;
- acceptable largest-key size and throughput;
- isolation of noisy neighbors;
- ability to split or move a hot owner;
- bounded scatter-gather for required queries;
- tenant and security semantics;
- recovery and rebalancing behavior.

High cardinality does not guarantee balance. A user-ID key has millions of values, but one celebrity or integration account may dominate. A date key changes every day yet sends today's writes to one place.

Measure the frequency distribution, largest key, and concentration. Average load per partition conceals hotspots.

## 13. Understand hash and range tradeoffs

Hash partitioning tends to distribute unrelated keys broadly. It supports direct key routing but destroys natural range locality and can make range queries scatter across partitions.

Range partitioning keeps nearby values together and makes ordered scans efficient. Monotonically increasing keys can create a moving write hotspot at the newest range. Unequal ranges can produce skew.

Composite designs can hash a tenant and sort by time within the tenant, preserving tenant-local queries while distributing tenants. This fails when one tenant exceeds one partition's capacity unless the model supports sub-sharding.

There is no universally good key. Write the operations made local, the operations made distributed, and the behavior of the largest owner.

## 14. Treat hotspots as a first-class failure mode

A hotspot occurs when one key, partition, node, lock, queue, or cache entry receives disproportionate work. Sources include:

- large tenants and celebrity users;
- monotonically increasing keys;
- global counters or singleton configuration;
- popular content;
- synchronized cron jobs;
- retry storms;
- partition-local secondary indexes;
- skewed routing or failed nodes.

Mitigations include better key distribution, write sharding, hierarchical aggregation, batching, rate fairness, caching reads, isolating large tenants, and changing the business operation.

Write sharding spreads one logical stream across suffixes, but readers must query and merge them, uniqueness may become harder, and shard-count changes require a routing rule. Use it for a measured hot path, not as decorative randomness.

AWS DynamoDB guidance, for example, recommends uniform activity across partition keys and documents write sharding for hot keys. The exact service limits can change; the enduring lesson is to model per-key capacity rather than table totals.

## 15. Distinguish sharding from replication

Sharding divides different data or work among nodes. Replication places copies of the same data or work in multiple locations.

Replication can serve different purposes:

- failover availability;
- read throughput;
- geographic latency;
- disaster recovery;
- offline analytics or backup staging.

Each purpose has different consistency, lag, routing, recovery, and cost requirements. A read replica may scale stale-tolerant queries but cannot increase the authoritative writer's throughput. A disaster-recovery copy may be deliberately isolated and not serve normal traffic.

More replicas add write, network, storage, coordination, and repair work. State which copy may accept writes, how failover avoids divergent authority, and how a recovered node catches up.

## 16. Bound scatter-gather

A query without the partition key may contact many partitions and merge results. Scatter-gather increases work with partition count and makes tail latency depend on the slowest participants.

Use it when fan-out is bounded, infrequent, and measured. For frequent global queries, consider an owned secondary index, materialized view, search projection, aggregation hierarchy, or revised product boundary.

Every secondary distribution creates another write path and failure mode. Define its authority, freshness, rebuild, and deletion contract from Chapter 108.

Pagination across moving partitions needs a stable order, per-partition cursors or snapshot semantics, and a bound on token size and lifetime.

## 17. Route without creating a fragile coordinator

Routing may use a deterministic hash, range map, partition directory, service discovery, or proxy. The router needs a versioned view of placement and behavior during movement.

Ask:

- Can clients route directly or only through a service?
- How are placement changes published and cached?
- What happens with a stale route?
- Can a request be safely retried after redirect?
- Is the directory highly available and recoverable?
- Can authorization be preserved across routing?
- How is a partition fenced during ownership transfer?

A central directory can enable deliberate tenant placement and movement, but it becomes critical state. A pure hash avoids a directory but makes membership changes and heterogeneous capacity harder.

## 18. Plan rebalancing before the first split

Rebalancing moves ownership or data when nodes join, leave, fail, or become uneven. It competes with production for network, disk, CPU, cache, and replica work.

A safe movement protocol usually needs:

1. a source and destination with explicit ownership epochs;
2. a snapshot or copy baseline;
3. capture of concurrent changes;
4. catch-up and integrity comparison;
5. a fenced cutover so only one authority accepts each write;
6. route publication and stale-client handling;
7. rollback before destructive cleanup;
8. delayed source deletion after verification.

Throttle movement by user latency and safety margins. Test interruption and resume. “The database rebalances automatically” does not answer how long it takes, what traffic it disrupts, or what happens when movement fails halfway.

## 19. Autoscaling is delayed feedback control

An autoscaler observes a metric, computes desired capacity, requests new capacity, waits for it to become ready, and later scales down. Every step has delay and error:

```text
detection + metric lag + decision interval + provisioning + startup + warm-up
```

If a burst exceeds spare capacity for less than this total, reactive scaling alone cannot protect it. Keep minimum headroom, pre-scale for known events, queue bounded asynchronous work, shed optional load, or use a faster capacity source.

Scale on a metric that precedes user failure and maps to the resource. CPU may work for CPU-bound stateless tasks. Queue age or backlog per worker may better represent consumers. In-flight requests, concurrency, latency, and custom saturation signals can be more direct than average CPU.

Kubernetes documents its HorizontalPodAutoscaler as an intermittent control loop with readiness handling, stabilization, and configurable scale behavior. Those details illustrate why an autoscaler is not instantaneous capacity.

## 20. Avoid unstable scaling loops

Scaling too eagerly can flap: capacity arrives, utilization falls, replicas disappear, demand rises per replica, and the cycle repeats.

Stabilize with:

- dead bands or tolerance around the target;
- different scale-up and scale-down policies;
- minimum dwell or stabilization windows;
- rate limits on capacity change;
- readiness that reflects usable capacity;
- metrics that exclude initialization distortion;
- a minimum replica and failure-domain floor;
- coordinated application and node scaling.

Do not let infrastructure code continually reset the desired replica count while an autoscaler also owns it. Do not scale down below recovery, deployment, or zone-loss requirements merely because current traffic is low.

## 21. Use queues as buffers, not capacity generators

A queue can absorb a burst and decouple arrival from processing, but if average arrival exceeds average service capacity, backlog grows without bound.

Monitor:

- arrival and completion rates;
- oldest-item age;
- ready and in-flight depth;
- retry and dead-letter rates;
- service-time distribution;
- worker concurrency and downstream saturation;
- time to drain under current and maximum safe capacity.

Scale consumers from backlog age or work units, not message count alone when jobs vary greatly. Bound queue retention and producer admission. A six-hour backlog is not healthy because no messages were dropped if the business objective is ten minutes.

## 22. Apply backpressure before collapse

When a dependency saturates, unlimited concurrency and retries increase waiting and make recovery harder. Backpressure limits admitted or in-flight work so the system fails in a controlled way.

Techniques include bounded queues, connection and worker pools, per-tenant quotas, rate limits, concurrency limits, load shedding, circuit breaking, and explicit retry-after guidance.

Prioritize critical work. Task reads and assignments may outrank search reindexing, analytics export, attachment preview, and bulk migration. Do not bypass authorization or durability to preserve throughput.

Reject early when completing within the deadline is impossible. A fast explicit overload response is often safer than accepting work that will time out after consuming scarce capacity.

## 23. Load-test the model, not an empty endpoint

A representative load test includes:

- operation mix and payload distributions;
- hot tenants and keys;
- realistic dataset, indexes, and cache state;
- authentication and serialization;
- downstream durability settings;
- background and maintenance work;
- ramp, burst, soak, and recovery phases;
- one-node or one-zone capacity loss;
- retry and timeout behavior;
- cost and quota observation.

Measure throughput, latency percentiles, errors, saturation, queue wait, per-key heat, connection pressure, storage, and recovery after load stops.

An open-loop generator preserves offered arrival rate and reveals overload; a closed-loop generator that waits for each response can unintentionally reduce offered load as latency rises. Understand the generator's feedback behavior.

Never run an unbounded test against shared or production systems without explicit authorization, rate limits, stop conditions, and cost ownership.

## 24. Evolve scale in evidence-backed stages

A staged task-system plan might be:

1. one relational writer with replicas for measured stale-tolerant reads;
2. horizontally scaled stateless application tier with bounded pools;
3. object storage and asynchronously rebuilt search projection;
4. isolate high-cost background work and large tenants;
5. partition only when a measured writer, size, locality, or recovery limit approaches;
6. split by tenant directory so large tenants can move independently;
7. add sub-sharding only for tenants that exceed a shard's safe envelope.

Each stage should name trigger metrics, migration path, rollback, and new operational cost. Preserve simplicity until evidence reaches a boundary; preserve options before the boundary becomes an emergency.

## 25. Encode an order-of-magnitude capacity review

This standard-library model checks unit relationships, failure headroom, key skew, and autoscaling delay. It is not a queueing simulator.

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Workload:
    requests_per_second: float
    average_latency_seconds: float
    operations_per_request: float
    burst_multiplier: float

    def expected_concurrency(self) -> float:
        if min(self.requests_per_second, self.average_latency_seconds,
               self.operations_per_request, self.burst_multiplier) <= 0:
            raise ValueError("workload values must be positive")
        return self.requests_per_second * self.average_latency_seconds

    def downstream_operations_per_second(self) -> float:
        return self.requests_per_second * self.operations_per_request


@dataclass(frozen=True)
class PartitionPlan:
    partitions: int
    sustainable_operations_per_partition: float
    hottest_key_fraction: float
    single_key_limit: float
    rebalance_tested: bool

    def validate(self, workload: Workload) -> None:
        if self.partitions <= 0 or self.sustainable_operations_per_partition <= 0:
            raise ValueError("partition capacity must be positive")
        peak = workload.downstream_operations_per_second() * workload.burst_multiplier
        if peak > self.partitions * self.sustainable_operations_per_partition:
            raise ValueError("aggregate partition capacity is insufficient")
        if not 0 < self.hottest_key_fraction <= 1:
            raise ValueError("hottest-key fraction is invalid")
        if peak * self.hottest_key_fraction > self.single_key_limit:
            raise ValueError("hottest key exceeds its capacity")
        if not self.rebalance_tested:
            raise ValueError("partition movement has not been tested")


@dataclass(frozen=True)
class CapacityPlan:
    workload: Workload
    partition: PartitionPlan
    steady_capacity_units: int
    capacity_after_failure: int
    required_peak_units: int
    autoscaling_total_delay_seconds: int
    burst_duration_seconds: int
    overload_control_defined: bool

    def validate(self) -> None:
        self.workload.expected_concurrency()
        self.partition.validate(self.workload)
        if self.steady_capacity_units < self.required_peak_units:
            raise ValueError("steady capacity cannot serve expected peak")
        if self.capacity_after_failure < self.required_peak_units:
            raise ValueError("failure headroom is insufficient")
        if (self.autoscaling_total_delay_seconds >= self.burst_duration_seconds
                and self.steady_capacity_units == self.required_peak_units):
            raise ValueError("autoscaling arrives after burst without spare headroom")
        if not self.overload_control_defined:
            raise ValueError("overload behavior is undefined")
```

Executable tests make the assumptions visible:

```python
import unittest

from capacity_plan import CapacityPlan, PartitionPlan, Workload


def valid_plan() -> CapacityPlan:
    workload = Workload(1200, 0.1, 2, 2.5)
    partition = PartitionPlan(12, 600, 0.04, 300, True)
    return CapacityPlan(workload, partition, 16, 12, 10, 45, 180, True)


class CapacityPlanTests(unittest.TestCase):
    def test_complete_plan_is_accepted(self) -> None:
        plan = valid_plan()
        plan.validate()
        self.assertEqual(plan.workload.expected_concurrency(), 120)
        self.assertEqual(plan.workload.downstream_operations_per_second(), 2400)

    def test_nonpositive_workload_is_rejected(self) -> None:
        plan = valid_plan()
        bad = Workload(0, 0.1, 2, 2.5)
        with self.assertRaisesRegex(ValueError, "positive"):
            CapacityPlan(bad, plan.partition, 16, 12, 10, 45, 180, True).validate()

    def test_aggregate_capacity_is_checked(self) -> None:
        plan = valid_plan()
        bad = PartitionPlan(4, 600, 0.04, 300, True)
        with self.assertRaisesRegex(ValueError, "aggregate"):
            CapacityPlan(plan.workload, bad, 16, 12, 10, 45, 180, True).validate()

    def test_hot_key_is_checked_separately(self) -> None:
        plan = valid_plan()
        bad = PartitionPlan(12, 600, 0.20, 300, True)
        with self.assertRaisesRegex(ValueError, "hottest key"):
            CapacityPlan(plan.workload, bad, 16, 12, 10, 45, 180, True).validate()

    def test_failure_headroom_is_required(self) -> None:
        plan = valid_plan()
        fields = {**plan.__dict__, "capacity_after_failure": 8}
        with self.assertRaisesRegex(ValueError, "failure headroom"):
            CapacityPlan(**fields).validate()

    def test_autoscaling_delay_requires_spare_capacity(self) -> None:
        plan = valid_plan()
        fields = {
            **plan.__dict__, "steady_capacity_units": 10,
            "autoscaling_total_delay_seconds": 240,
        }
        with self.assertRaisesRegex(ValueError, "after burst"):
            CapacityPlan(**fields).validate()

    def test_rebalance_evidence_is_required(self) -> None:
        plan = valid_plan()
        fields = {**plan.partition.__dict__, "rebalance_tested": False}
        with self.assertRaisesRegex(ValueError, "movement"):
            CapacityPlan(plan.workload, PartitionPlan(**fields), 16, 12, 10,
                         45, 180, True).validate()

    def test_overload_control_is_required(self) -> None:
        plan = valid_plan()
        fields = {**plan.__dict__, "overload_control_defined": False}
        with self.assertRaisesRegex(ValueError, "overload"):
            CapacityPlan(**fields).validate()


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

Save the blocks as `capacity_plan.py` and `test_capacity_plan.py`, then run:

```bash
python -m unittest -v test_capacity_plan.py
```

A production model should use measured service demands and distributions, calibrated load tests, per-key histograms, dependency quotas, failure-domain capacity, startup time, and cost. It should preserve raw inputs so reviewers can reproduce every estimate.

## 26. Review capacity and partitioning

```text
journey, horizon, observations, forecast, range, and contingency trigger:
arrival, throughput, latency distribution, concurrency, and stable window:
operation, byte, connection, index, replica, event, and telemetry amplification:
data arrival, retention, history, indexes, replicas, backup, and headroom:
per-stage demand, capacity, queues, pools, quotas, saturation, and lead time:
first bottleneck evidence, profiler, query plan, wait, heat, and load result:
steady, burst, zone-loss, cache-loss, deployment, migration, and restore headroom:
vertical limit, price, restart, recovery, and next horizontal step:
stateless process, session, local files, locks, stickiness, jobs, and warm-up:
partition purpose, key, locality, distribution, largest owner, and transactions:
hash, range, tenant, geography, time, directory, and composite tradeoffs:
hot keys, counters, cron, retries, indexes, fairness, and write sharding:
shard versus replica purpose, writer authority, lag, failover, and catch-up:
scatter-gather fan-out, tail latency, pagination, and projection alternative:
routing version, stale route, retry, directory recovery, and authorization:
movement epoch, copy, catch-up, fence, cutover, route, rollback, and cleanup:
autoscaling signal, lag, interval, provision, startup, warm-up, and headroom:
tolerance, stabilization, rate policy, readiness, floors, and owner conflicts:
queue arrivals, completions, age, work size, drain time, DLQ, and retention:
backpressure, quotas, shedding, rejection, retry guidance, and priorities:
load mix, skew, dataset, caches, maintenance, failure, stop, and cost controls:
```

## Common Misconceptions

- “A million users means a million concurrent requests.” Activity and operation rates matter.
- “Average utilization proves spare capacity.” One key, core, lock, queue, or dependency may be saturated.
- “More concurrency always raises throughput.” Beyond the bottleneck it raises waiting and failure.
- “Horizontal scale means stateless.” Hidden sessions, files, locks, and jobs can bind requests to instances.
- “High-cardinality keys distribute evenly.” Traffic and size can remain severely skewed.
- “Replication scales writes.” Read replicas do not increase one authoritative writer's capacity.
- “Scatter-gather is parallel, therefore fast.” Tail latency and work grow with participants.
- “Autoscaling handles bursts.” Observation, provisioning, startup, and warm-up take time.
- “A queue absorbs any overload.” Persistent arrival above service rate creates unbounded backlog.
- “Automatic rebalancing needs no design.” Movement consumes resources and changes authority.

## Core Computer Science Concept

This chapter applies **dimensional analysis, Little's Law, queueing, load distribution, partition functions, replication, feedback control, and conservation of work**. Parallelism redistributes work but does not remove it; every partition and replica changes locality, coordination, and movement costs.

## Engineering Connections

- Process and resource limits build on Chapters 4, 43, 76, and 86.
- Network and storage throughput extend Chapters 51, 54, 83, and 98.
- Access patterns and keys come from Chapters 100, 106, and 108.
- Asynchronous buffers apply Chapters 74, 76, and 101.
- Autoscaling and placement extend Chapters 88, 95, and 103.
- Chapter 110 next defines the correctness cost of distributing reads and writes.

## From the Field

A team sees 40% average database utilization and doubles application replicas for a launch. One enterprise tenant writes every event under its tenant key, saturating a single partition. Requests time out, clients retry, and the new replicas accelerate pressure on the same key. Per-key heat, a largest-tenant estimate, fair admission, and a tested sub-sharding plan would have revealed that aggregate capacity was irrelevant.

## Engineering Review

### What problem does this solve?

It turns workload estimates into a resource and partition model that identifies the first bottleneck and safe next scaling step.

### Why was it designed this way?

Scale failures hide in amplification, skew, queues, and delayed feedback. Aggregate user counts and utilization averages omit those mechanisms.

### When should I use it?

Use it before launches, architecture changes, partitioning, autoscaling, large migrations, reliability reviews, and whenever latency or saturation trends toward an objective.

### When should I avoid it?

Do not shard a small workload merely to demonstrate sophistication. Estimate and load-test the simple design first, then preserve an evidence-backed migration trigger.

### How does this make me a better engineer?

It teaches you to preserve units, distinguish concurrency from throughput, look for skew, model time-to-capacity, and treat movement as a correctness event.

### How does this reduce waste?

It avoids premature sharding, unused replicas, oversized fleets, unstable autoscaling, overloaded dependencies, unbounded queues, ineffective caches, and migrations that discover hotspots in production.

## Handbook Principle #109

> Scale the measured bottleneck for the observed workload shape, preserve failure headroom, and partition only with an owned key, skew model, routing contract, and movement protocol.

## Practical Observation

For one production journey, multiply arrival rate by average latency and compare the implied concurrency with live in-flight work. Then multiply requests by downstream operations and rank keys by traffic. Any large disagreement is more valuable than another generic “scalability” discussion because it points to a missing measurement or false model.

## Looking Ahead

Partitioning and replication create concurrent observations and writes. Chapter 110 defines invariants, isolation anomalies, optimistic and pessimistic control, replica consistency, conflict resolution, and session guarantees so scale does not silently weaken correctness.

## References

- [Google SRE Workbook — Data processing pipelines and capacity](https://sre.google/workbook/data-processing/)
- [Kubernetes — Horizontal Pod Autoscaling](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/)
- [Kubernetes — Node autoscaling](https://kubernetes.io/docs/concepts/cluster-administration/node-autoscaling/)
- [Amazon DynamoDB — Partition-key design](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-partition-key-design.html)
- [Amazon DynamoDB — Write sharding](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-partition-key-sharding.html)
- [Apache Kafka — Introduction and partition model](https://kafka.apache.org/documentation/#intro_concepts_and_terms)
- [Chapter 76 — Scheduling, Concurrency, and Work Queues](../automation/76-scheduling-concurrency-and-work-queues.md)
- [Chapter 103 — ECS, EKS, ECR, and Container Platforms on AWS](../aws/103-ecs-eks-ecr-and-container-platforms-on-aws.md)
- [Chapter 108 — Data Models and Storage Selection](108-data-models-and-storage-selection.md)
