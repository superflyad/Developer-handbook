# Chapter 100 — DynamoDB, Caching, and NoSQL Access Patterns

A DynamoDB table can scale without the application managing servers, yet one celebrity key can still throttle, one filter can still read a whole table, and one cache can still return a value the business can no longer accept. NoSQL removes neither modeling nor correctness; it moves them into access patterns and keys.

The central idea is:

> Model every required read and write before creating the table, then choose keys, indexes, consistency, capacity, and caches that make those exact operations bounded and correct.

## 1. Start with operations, not entities

Relational design often begins with facts and relationships, then uses indexes and queries to support evolving access. DynamoDB design begins with known operations:

```text
operation: list a customer's open orders newest first
key condition: customer_id = ? and status_time begins_with "OPEN#"
maximum result: 50 items per page
consistency: eventual is acceptable
peak: 2,000 requests/second across 200,000 customers
item size: 1–3 KB projected
```

For every pattern, record:

- partition key value source;
- sort key condition and ordering;
- table or index used;
- projected attributes;
- maximum items and bytes per page;
- read consistency;
- peak and per-key request rate;
- write amplification into indexes and streams;
- stale, missing, duplicate, and conflict behavior;
- retention and cache policy.

If an important request cannot name its partition key, the model is incomplete or the request belongs in a different system.

## 2. Tables contain items, not joined rows

A DynamoDB table stores items with attributes. Each item is identified by either:

- a simple primary key containing one partition key; or
- a composite primary key containing a partition key and sort key.

The partition key is hashed to distribute items and traffic. Items sharing a composite partition key form an item collection ordered by sort key. Attributes outside the key can vary between items.

DynamoDB does not join related items at query time. Applications commonly denormalize, duplicate selected facts, or place related item types in one collection so one `Query` returns a complete view. Duplication is intentional only when its update and reconciliation rules are explicit.

## 3. Partition keys distribute both data and heat

A good partition key has enough distinct active values to distribute request load. Cardinality alone is insufficient: a million dormant tenants do not help when one active tenant receives nearly every write.

Estimate for each key value:

```text
requests per second
× capacity units per request based on item size and consistency
= key-range demand
```

Adaptive capacity can help uneven workloads but does not abolish per-partition limits or instantaneously rescue an indefinitely hot key. DynamoDB documents per-partition maximums of 3,000 read units and 1,000 write units per second; item size changes how many operations fit within them.

When one logical key is predictably hot, consider write sharding with a bounded suffix and a read fan-out plan. Random suffixes distribute writes but force readers to query every shard. Time buckets can bound collections but make range reads cross buckets. State those costs before adopting the pattern.

## 4. Sort keys encode range and hierarchy

Within one partition-key value, DynamoDB stores items by sort key. A sort key can support equality, comparison, `BETWEEN`, and `begins_with` key conditions.

Composite values can encode a stable hierarchy:

```text
PK = CUSTOMER#42
SK = ORDER#2026-11-01T15:04:05Z#7f8c
```

Choose a representation whose lexical or numeric order matches the intended query. Use fixed-width or sortable timestamp formats, escape delimiters, and avoid embedding mutable facts that require rewriting identity.

A sort key is not a general predicate. A filter expression runs after DynamoDB reads matching key data, so it does not turn a broad key condition into an efficient query.

## 5. Get, Query, and Scan have different cost shapes

`GetItem` addresses one complete primary key. `BatchGetItem` requests a known set of keys. `Query` requires one partition-key value and can narrow by sort key. These operations make read work proportional to requested key ranges.

`Scan` reads every item in a table or index. Each request reads up to 1 MB before applying a filter; filtered-out items still consume capacity. Pagination continues from `LastEvaluatedKey`.

Scans can be valid for controlled administration, export, backfill, or small bounded tables. They should not hide inside latency-sensitive request paths. Isolate large scans, limit page size, pace them, monitor consumed capacity, and prefer export or a purpose-built projection when repeated analytical access is required.

## 6. Filters reduce responses, not read work

Key conditions decide which items DynamoDB reads for a `Query`. Filter expressions discard items after that read and before returning the page. A page can therefore contain zero returned items and still include a continuation key and consumed capacity.

If a filter rejects most candidates:

- redesign the sort key;
- add a sparse index for items possessing a qualifying attribute;
- materialize a separate projection;
- move exploratory analysis to an export or analytical store.

Measure `ScannedCount`, `Count`, consumed capacity, pages, and returned bytes. A fast test with ten items does not prove a million-item pattern is bounded.

## 7. Secondary indexes are maintained projections

A global secondary index (GSI) can use different partition and sort keys from the base table. It has its own capacity and partitions and is maintained asynchronously from base-table writes. GSI reads are eventually consistent.

A local secondary index (LSI) shares the table partition key and uses a different sort key. It is created with the table, consumes base-table capacity, supports strong reads, and imposes item-collection constraints.

For each index, define:

- access pattern it serves;
- key cardinality and hot-key risk;
- projected attributes;
- items that appear—especially sparse-index conditions;
- write amplification and capacity;
- backfill behavior;
- consistency and lag tolerance;
- storage and deletion owner.

Project only attributes needed by the pattern. Fetching missing attributes after an index query adds round trips or is unsupported in the same way across index types. Copying every attribute increases storage and write cost.

## 8. Denormalization needs one source and repair

Suppose an order item duplicates the customer's display name. A later name change does not update old orders automatically. Decide whether the copy is:

- an immutable historical snapshot;
- a derived projection updated asynchronously;
- a value that must change atomically with the source;
- a cache that can expire and reload.

For derived copies, define the authoritative item, update event, idempotency key, retry, failure destination, lag objective, and reconciliation scan or export. “Eventually consistent” describes visibility, not who repairs a permanently missed projection.

## 9. Item size affects capacity and modeling

DynamoDB items have a 400 KB maximum, including attribute names and values. Read units round data in 4 KB blocks; writes round in 1 KB blocks. Long attribute names repeated across millions of items consume storage and capacity.

Keep large immutable blobs in S3 and store a key, version, checksum, and metadata in DynamoDB. Splitting one logical document into items can improve bounded updates but introduces assembly, transaction, ordering, and partial-state concerns.

Estimate sizes with realistic names, indexes, encryption metadata, and future growth. Reject oversized writes before they reach production.

## 10. Choose consistency per access pattern

Eventually consistent reads are the default and can return an older committed value briefly. Strongly consistent reads on a table or LSI reflect successful prior writes, but cost more capacity. GSIs and streams do not support strongly consistent reads.

Choose deliberately:

- product catalog browsing may tolerate staleness;
- a user reading immediately after editing may use the base table strongly or retain the written value;
- authorization revocation may require an authoritative strongly consistent path rather than a cache or GSI;
- a background projection can accept lag if reconciliation exists.

Strong reads do not lock an item against a later write. Use a conditional write when correctness depends on the value not changing between read and update.

## 11. Conditional writes are compare-and-swap

`PutItem`, `UpdateItem`, and `DeleteItem` can include a condition expression evaluated atomically with the write. Conditions support patterns such as:

- create only if the key does not exist;
- decrement inventory only above zero;
- update only if a version equals the value read;
- claim a job only while its lease is expired;
- preserve a state-machine transition.

A failed condition is a business concurrency result, not necessarily an infrastructure error. Decide whether to return conflict, reload and retry, or abandon work. Avoid unbounded retry loops under contention.

Atomic update expressions can increment counters or alter collections without a client read-modify-write. Counters still create a hot key if all traffic targets one item.

## 12. Transactions coordinate bounded item sets

`TransactWriteItems` and `TransactGetItems` provide ACID operations across supported items and tables in one Region. A transaction consumes additional capacity because DynamoDB performs prepare and commit work.

Use transactions when invariants truly span items, such as claiming uniqueness while creating an entity. Do not use them to reproduce arbitrary relational joins or long workflows. Keep external calls outside a database transaction and coordinate them through durable state, idempotency, and events.

Supply client request tokens where supported, handle cancellation reasons carefully, and make retries safe after a timeout with an unknown outcome.

## 13. Capacity mode does not remove key design

On-demand mode bills requests and adapts to traffic without explicit capacity units. It suits variable or uncertain workloads, but retains partition, account, and optional maximum-throughput limits. Sudden traffic far beyond the previous peak still needs a load and prewarming strategy described by current service guidance.

Provisioned mode assigns read and write capacity to tables and GSIs, optionally with auto scaling. It can fit predictable steady workloads and cost controls, but scaling reacts after measurements and cannot instantly repair a spike.

In both modes:

- hot key ranges can throttle;
- GSIs can throttle writes and create backpressure;
- account quotas apply;
- retries need exponential backoff with jitter;
- clients need deadlines and admission control;
- consumed capacity and throttling reasons need monitoring.

## 14. Retry throttling without amplifying it

Throttling is flow control, not permission to retry immediately forever. Use current SDK retry behavior as a baseline, then bound total attempt time by the caller's deadline.

Good clients:

- inspect the throttling reason and affected resource;
- use exponential backoff with jitter;
- cap attempts and elapsed time;
- preserve idempotency;
- reduce concurrency when overload persists;
- expose retry and throttle metrics;
- avoid retry multiplication across service layers.

Fix the cause: key heat, insufficient table or index capacity, configured maximums, account quota, oversized operations, or an uncontrolled scan.

## 15. TTL is asynchronous cleanup

Time to Live uses a numeric Unix-epoch-seconds attribute to mark items for expiration. DynamoDB deletes eligible items asynchronously, typically within days, without consuming table write capacity for the initial deletion.

Expired items can remain readable until deletion. Therefore TTL is not:

- an authorization expiry check;
- a precise scheduler;
- a legal deletion deadline;
- immediate cache invalidation.

Applications must enforce business expiration during reads and writes. TTL deletions can appear in Streams, and replicated TTL deletes in global tables can incur replicated write cost. Restored tables need TTL configuration verified.

## 16. Streams expose item changes, not a global transaction log

DynamoDB Streams retains item-level change records for 24 hours and can include keys, old images, new images, or both. It preserves modification order for a given item, not one total order across the table.

Consumers must be idempotent because the delivery system invoking them can retry batches. They must handle poison records, partial batch failures, lag approaching retention, shard lineage, resharding, and replay limits.

Use Streams for projections, search indexing, notifications, audit enrichment, and integration—not as proof that an external side effect happened exactly once. Store business events transactionally when omission would violate an invariant, then reconcile downstream state.

## 17. Global tables add multi-Region conflict semantics

Global tables replicate DynamoDB data among Regions. Current service modes include multi-Region eventual consistency and supported multi-Region strong-consistency configurations with distinct requirements.

Before multi-active writes, define:

- home Region or write-anywhere behavior;
- conflicting concurrent updates;
- conditional-write and optimistic-lock expectations;
- TTL and stream processing per Region;
- routing and failback;
- replicated capacity and cost;
- Regional isolation behavior.

In last-writer-wins eventual configurations, an application version attribute does not by itself prevent another Region's concurrent write from winning later. Model conflict at the business level or constrain write ownership.

## 18. Caching changes the consistency contract

A cache can reduce table reads and latency for hot, repeatedly accessed data. It also introduces another copy with eviction, expiration, availability, and invalidation behavior.

For every cached pattern, define:

- exact cache key and tenant boundary;
- positive and negative TTL;
- acceptable staleness;
- maximum object size;
- write-through, write-around, or explicit invalidation;
- stampede control;
- behavior when cache or table is unavailable;
- authorization and sensitive-data handling;
- hit-rate and total-cost target.

Never cache a mutable authorization decision longer than its revocation contract.

## 19. DAX accelerates eventual DynamoDB reads

DynamoDB Accelerator is a managed, in-memory, API-compatible cache for supported DynamoDB operations. DAX uses write-through behavior for writes sent through DAX and has separate item and query caches.

Important boundaries:

- cache misses use eventually consistent table reads;
- strongly consistent reads pass through and are not cached;
- DAX-node replication is eventually consistent;
- direct writes that bypass DAX can leave cached items stale until expiry;
- item updates do not invalidate cached `Query` results;
- negative results can be cached;
- a cluster adds nodes, networking, failure modes, and cost.

Use DAX when measured repeated-read latency and table-read cost justify it and the access pattern tolerates these semantics. Do not add it to repair poor keys, scans, or write bottlenecks.

## 20. Backups and point-in-time recovery still matter

DynamoDB durability and Multi-AZ replication do not protect against every destructive write or operator action. Configure point-in-time recovery and backups according to recovery objectives, and test restore to a new table.

Restore validation includes table name and ARN changes, indexes, capacity mode, encryption, TTL, Streams, resource policies, tags, alarms, application configuration, and dependent event consumers. A restored table does not automatically replace the original in every client.

Use exports for analytics and reconciliation without consuming table read capacity where supported. Keep recovery copies and keys under the independence required by the threat model.

## 21. Observe access-pattern health

Monitor:

- consumed and provisioned read/write capacity;
- throttled requests and detailed throttling reasons;
- successful-request latency and system errors;
- per-key contribution through Contributor Insights where enabled;
- GSI capacity and propagation symptoms;
- conditional-check and transaction cancellations;
- item size and collection growth;
- stream iterator age and consumer failures;
- TTL deletion behavior;
- DAX hit rate, evictions, errors, and node health;
- backup and restore evidence;
- cost by table, index, backup, stream, and replica.

Instrument operations by named access pattern. A table-wide average hides the one pattern or key range causing user failures.

## 22. Evolve the model through dual projections

Changing a key schema requires a new table or projection rather than an in-place primary-key edit. A safe migration can:

1. define the new access patterns and invariants;
2. create the destination table and indexes;
3. establish change capture;
4. backfill with bounded, restartable workers;
5. reconcile counts, checksums, and business samples;
6. dual-read or shadow-read and compare;
7. switch writes and reads through controlled flags;
8. retain rollback until lag is zero and confidence is sufficient;
9. retire old consumers before deleting data.

Dual writes can partially fail. Prefer a transactional outbox or stream projection plus reconciliation over pretending two independent writes are atomic.

## 23. Rehearse NoSQL failures

Test:

- one partition-key value receives a traffic spike;
- a GSI has lower capacity than the base table;
- a paginated query returns an empty filtered page with a continuation key;
- a conditional update loses a race;
- a transaction times out with unknown outcome;
- an expired TTL item remains visible;
- a stream batch contains one poison record;
- a cache returns stale or negative data after a direct write;
- a Region accepts a conflicting global-table write;
- restore produces a table without an expected integration;
- a scan competes with request traffic;
- item growth approaches 400 KB.

Record expected response, bounded retry, reconciliation, data-loss tolerance, recovery owner, and evidence.

## 24. Validate an access-pattern catalog

This standard-library lab rejects unbounded and inconsistent production patterns before they become infrastructure.

```python
from __future__ import annotations

from dataclasses import dataclass
from math import ceil


@dataclass(frozen=True)
class AccessPattern:
    name: str
    operation: str
    index: str
    partition_key_known: bool
    consistency: str
    average_item_bytes: int
    max_items_per_request: int
    peak_requests_per_key_second: int
    cache: str = "none"

    def validate(self) -> None:
        if self.operation not in {"get", "query", "put", "update", "transaction"}:
            raise ValueError(f"{self.name}: production pattern cannot depend on scan")
        if self.operation in {"get", "query"} and not self.partition_key_known:
            raise ValueError(f"{self.name}: read must identify a partition key")
        if not 1 <= self.average_item_bytes <= 400 * 1024:
            raise ValueError(f"{self.name}: item size is outside DynamoDB limits")
        if self.max_items_per_request < 1:
            raise ValueError(f"{self.name}: request bound must be positive")
        if self.index.startswith("gsi:") and self.consistency == "strong":
            raise ValueError(f"{self.name}: GSI reads cannot be strongly consistent")
        if self.cache == "dax" and self.consistency != "eventual":
            raise ValueError(f"{self.name}: DAX cache requires eventual consistency")
        if self.operation in {"put", "update"}:
            write_units = ceil(self.average_item_bytes / 1024)
            if write_units * self.peak_requests_per_key_second > 1000:
                raise ValueError(f"{self.name}: one key can exceed partition write capacity")


@dataclass(frozen=True)
class TableContract:
    capacity_mode: str
    point_in_time_recovery: bool
    ttl_is_only_cleanup: bool
    stream_consumers_idempotent: bool
    patterns: tuple[AccessPattern, ...]

    def validate(self) -> None:
        if self.capacity_mode not in {"on-demand", "provisioned"}:
            raise ValueError("capacity mode must be explicit")
        if not self.point_in_time_recovery:
            raise ValueError("point-in-time recovery is required")
        if not self.ttl_is_only_cleanup:
            raise ValueError("TTL cannot enforce precise business expiry")
        if not self.stream_consumers_idempotent:
            raise ValueError("stream consumers must tolerate retries")
        if not self.patterns:
            raise ValueError("at least one access pattern is required")
        names = [pattern.name for pattern in self.patterns]
        if len(names) != len(set(names)):
            raise ValueError("access pattern names must be unique")
        for pattern in self.patterns:
            pattern.validate()
```

Tests exercise the principal modeling failures:

```python
import unittest

from dynamodb_contract import AccessPattern, TableContract


def valid_contract() -> TableContract:
    return TableContract(
        capacity_mode="on-demand",
        point_in_time_recovery=True,
        ttl_is_only_cleanup=True,
        stream_consumers_idempotent=True,
        patterns=(
            AccessPattern("get-order", "get", "table", True, "strong", 2048, 1, 20),
            AccessPattern(
                "list-customer-orders", "query", "gsi:customer-time",
                True, "eventual", 1024, 50, 40, "dax"
            ),
            AccessPattern("create-order", "put", "table", True, "none", 3072, 1, 50),
        ),
    )


class TableContractTests(unittest.TestCase):
    def test_complete_contract_is_accepted(self) -> None:
        valid_contract().validate()

    def test_scan_request_path_is_rejected(self) -> None:
        contract = valid_contract()
        pattern = AccessPattern("find", "scan", "table", False, "eventual", 1000, 10, 1)
        broken = TableContract(**{**contract.__dict__, "patterns": (pattern,)})
        with self.assertRaisesRegex(ValueError, "cannot depend on scan"):
            broken.validate()

    def test_strong_gsi_read_is_rejected(self) -> None:
        contract = valid_contract()
        pattern = AccessPattern("recent", "query", "gsi:recent", True, "strong", 1000, 20, 2)
        broken = TableContract(**{**contract.__dict__, "patterns": (pattern,)})
        with self.assertRaisesRegex(ValueError, "cannot be strongly consistent"):
            broken.validate()

    def test_hot_write_key_is_rejected(self) -> None:
        contract = valid_contract()
        pattern = AccessPattern("counter", "update", "table", True, "none", 2048, 1, 600)
        broken = TableContract(**{**contract.__dict__, "patterns": (pattern,)})
        with self.assertRaisesRegex(ValueError, "exceed partition write"):
            broken.validate()

    def test_dax_strong_read_is_rejected(self) -> None:
        contract = valid_contract()
        pattern = AccessPattern("session", "get", "table", True, "strong", 800, 1, 50, "dax")
        broken = TableContract(**{**contract.__dict__, "patterns": (pattern,)})
        with self.assertRaisesRegex(ValueError, "DAX cache requires eventual"):
            broken.validate()

    def test_ttl_as_authorization_is_rejected(self) -> None:
        contract = valid_contract()
        broken = TableContract(**{**contract.__dict__, "ttl_is_only_cleanup": False})
        with self.assertRaisesRegex(ValueError, "precise business expiry"):
            broken.validate()


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

Save the blocks as `dynamodb_contract.py` and `test_dynamodb_contract.py`, then run:

```bash
python -m unittest -v test_dynamodb_contract.py
```

A production verifier should inspect authorized read-only inventory for keys, indexes, projections, capacity, limits, encryption, backups, TTL, Streams, global replicas, Contributor Insights, alarms, and DAX. It must not create indexes, change capacity, enable Streams, restore tables, or modify items during validation.

## 25. Review a DynamoDB design

```text
business invariants, owner, data class, Regions, and recovery objectives:
each access pattern, key condition, index, ordering, page bound, and consistency:
partition-key cardinality, hottest values, sharding, and fan-out:
sort-key encoding, hierarchy, ranges, and mutable fields:
item types, average/maximum sizes, large-object references, and growth:
GSIs/LSIs, projections, sparsity, write amplification, and lag tolerance:
conditional writes, versions, counters, transactions, and unknown outcomes:
on-demand/provisioned mode, peaks, previous peak, quotas, and maximums:
throttle reason handling, deadlines, backoff, jitter, and admission control:
TTL cleanup, application expiry, Streams, idempotency, and reconciliation:
global-table write ownership, conflict, routing, and failback:
cache keys, TTLs, invalidation, negative entries, stampede, and bypass:
PITR, backups, restore test, indexes, integrations, and cutover:
metrics by access pattern, hot-key evidence, alarms, cost, and owners:
model migration, backfill, change capture, comparison, rollback, and retirement:
```

## Common Misconceptions

- “DynamoDB is schemaless, so modeling comes later.” Key and index schema must serve known operations before launch.
- “On-demand means unlimited.” Partition heat, previous peaks, configured maximums, and quotas still matter.
- “A filter makes a scan efficient.” Filtering happens after read capacity is consumed.
- “A GSI is immediately consistent.” GSI propagation and reads are eventual.
- “Strong reads prevent concurrent writes.” Conditions protect read-modify-write invariants.
- “TTL deletes at the timestamp.” Deletion is asynchronous; applications enforce expiry.
- “Streams deliver one global order.” Ordering is per item, and consumers must tolerate delivery retries.
- “Transactions make DynamoDB relational.” They coordinate bounded item operations, not arbitrary queries or joins.
- “DAX always returns the table's latest value.” Cache, direct writes, query TTL, and node propagation affect visibility.
- “Denormalization eliminates consistency work.” It creates copies that need ownership and repair.

## Core Computer Science Concept

DynamoDB applies **hash partitioning, ordered local indexes, optimistic concurrency, and materialized views**. Partition keys distribute work, sort keys organize bounded ranges, conditions provide compare-and-swap, and indexes or stream consumers maintain derived projections. Performance and correctness follow directly from those structures.

## Engineering Connections

- Partitioning extends Chapter 99's read-scaling discussion without relational joins.
- Conditional writes implement the same compare-and-swap used in Chapter 97.
- Streams and projections use Part VI's idempotent consumer model.
- Capacity throttling is admission control and queue stability.
- DAX and TTL apply Chapter 29's cache identity and invalidation principles.
- Global tables expose distributed conflict and consistency tradeoffs.
- Model migration follows Chapter 77's dual-run and reconciliation pattern.

## From the Field

A leaderboard stores every score under `PK = GAME#final`. Launch traffic sends thousands of writes per second to that one key range. On-demand capacity and a large account quota do not help: the partition is hot. Bounded write shards, per-shard leaders, a merge query or asynchronous projection, and a load test focused on the hottest logical key would have revealed the limit before the event.

## Engineering Review

### What problem does this solve?

It turns NoSQL requirements into bounded key operations with explicit distribution, consistency, concurrency, capacity, expiration, events, caching, recovery, and migration behavior.

### Why was it designed this way?

DynamoDB scales by distributing keys and precomputing access paths rather than planning arbitrary joins at request time. Predictable performance requires the application to declare those paths.

### When should I use it?

Use this model for workloads with known high-scale key access, DynamoDB table or index design, conditional state transitions, event projections, TTL cleanup, global tables, or read caching.

### When should I avoid it?

Avoid DynamoDB when essential requests are exploratory, join-heavy, unbounded, or cannot identify stable distribution keys, unless a separate analytical or search projection owns those needs.

### How does this make me a better engineer?

It teaches you to quantify access before storage, recognize heat hidden by averages, encode invariants atomically, and separate authoritative state from asynchronous projections and caches.

### How does this reduce waste?

It reduces scans, overprovisioning, unused indexes, oversized items, retry storms, stale cache bugs, duplicate stream work, unnecessary transactions, hot-key incidents, and migrations without reconciliation.

## Handbook Principle #100

> A scalable NoSQL table is a catalog of bounded access patterns whose keys distribute both data and demand.

## Practical Observation

Take the ten busiest operations against one existing table. For each, write its complete key condition, index, page bound, average item bytes, consistency, and peak demand for the hottest key—not the average key. Compare that catalog with consumed capacity, throttling reasons, and Contributor Insights. Any operation labeled “filter,” “search,” or “list all” without a bounded key path is the next modeling task.

## Looking Ahead

Streams can announce state changes, but applications also need queues, fan-out topics, routed event buses, backpressure, redelivery, and workflow state. Chapter 101 compares SQS, SNS, EventBridge, and Step Functions through their delivery and ownership contracts.

## References

- [DynamoDB — Core components](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.CoreComponents.html)
- [DynamoDB — Partitions and data distribution](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.Partitions.html)
- [DynamoDB — Partition-key design](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-partition-key-design.html)
- [DynamoDB — Query](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Query.html)
- [DynamoDB — Scan](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Scan.html)
- [DynamoDB — Read consistency](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.ReadConsistency.html)
- [DynamoDB — Secondary-index guidelines](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-indexes-general.html)
- [DynamoDB — Read and write capacity consumption](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/read-write-operations.html)
- [DynamoDB — Concurrent-update strategies](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/BestPractices_ImplementingVersionControl.html)
- [DynamoDB — Transactions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transactions.html)
- [DynamoDB — Capacity-mode selection](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/CostOptimization_TableCapacityMode.html)
- [DynamoDB — Throttling diagnosis](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/TroubleshootingThrottling.html)
- [DynamoDB — Time to Live](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/TTL.html)
- [DynamoDB — Streams](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Streams.html)
- [DynamoDB — DAX consistency](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DAX.consistency.html)
- [Chapter 99 — RDS, Aurora, and Managed Relational Databases](99-rds-aurora-and-managed-relational-databases.md)
