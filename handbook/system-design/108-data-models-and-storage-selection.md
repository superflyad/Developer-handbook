# Chapter 108 — Data Models and Storage Selection

A database can store nearly any bytes. That does not make it a good model for the questions, invariants, concurrency, retention, and recovery the system owns. A normalized schema can preserve truth while missing a latency objective. A denormalized document can serve one screen quickly while making every update a repair problem. A search index can answer rich text queries while returning stale or incomplete business state.

The central idea is:

> Choose authoritative and derived data models from access patterns, invariants, consistency, lifecycle, scale, and operational ownership; every duplicated representation creates a synchronization obligation.

## 1. Start with meaning and operations

Before choosing a product, carry forward Chapter 106's model:

- entities, relationships, identities, and tenant boundaries;
- commands, queries, and critical journeys;
- invariants and concurrency conflicts;
- object counts, sizes, rates, skew, and growth;
- consistency, freshness, latency, and availability;
- retention, erasure, audit, backup, and recovery;
- security, residency, cost, and team constraints.

Then describe each access pattern:

```text
operation: list open tasks assigned to a member in a project
predicate: tenant, project, assignee, state = OPEN
ordering: priority descending, updated_at descending, task_id tie-breaker
page size: 50; cursor traversal
consistency: committed assignments visible within 2 seconds
peak: 1,200 queries/second; one large tenant is 18% of traffic
payload: task summary only
```

“Store tasks” is not an access pattern. The predicate, order, projection, consistency, rate, and skew determine whether a key lookup, index scan, join, graph traversal, text search, or precomputed view is appropriate.

## 2. Separate the domain model from storage layout

The domain model describes business concepts and rules. A logical data model expresses entities, attributes, relationships, and constraints. A physical model chooses tables, documents, keys, partitions, indexes, compression, and placement.

Do not let a storage engine's vocabulary become the business language. A task is not inherently a row, JSON document, graph node, or key-value item. It can have different physical representations for different access paths while retaining one authoritative meaning.

Conversely, do not pretend physical layout is an invisible implementation detail. A partition key can constrain transactions and scale. Embedding children in one document can constrain growth and concurrent updates. A secondary index adds write work and storage. The logical model and physical design must be reviewed together.

## 3. Define authority before duplication

For every datum, name the system of record—the authority permitted to decide its current business truth. Other forms may be:

- synchronous replicas;
- caches;
- materialized views;
- search indexes;
- analytics tables;
- graph projections;
- event logs;
- exports and archives;
- backups.

A copy needs an owner, source identity, update mechanism, freshness objective, reconciliation path, access policy, retention, and deletion propagation. “Eventually consistent” is incomplete without a bound, measurement point, and behavior when the bound is missed.

Do not create two authorities for the same field. If both a project service and identity service can change a member's display name, conflict is inevitable. One may own the identity while the other stores a labeled snapshot for history; the semantics must say so.

## 4. Choose stable keys from identity semantics

A primary key should identify the business object for its supported lifetime. Good keys have documented scope, uniqueness, immutability, generation authority, opacity, and reuse policy.

Natural keys such as email addresses, names, or external account numbers may change, be recycled, vary in normalization, or belong to another authority. Surrogate identifiers make references stable but do not eliminate uniqueness constraints on meaningful business keys.

Composite keys can encode a useful scope:

```text
(tenant_id, project_id, task_id)
```

They also propagate through indexes and references. Decide whether the tenant is inherent in the object identity or an authorization attribute. Never trust a tenant component supplied by a caller without verifying its relationship to the principal and object.

Time-sortable identifiers can improve locality and operational inspection, but may reveal creation order or rate. Random identifiers distribute writes but can reduce index locality in some engines. Choose from workload and threat evidence.

## 5. Use relational models for constraints and flexible composition

A relational model represents data as relations with declared attributes, keys, and constraints. It is a strong default when:

- several related entities participate in transactions;
- uniqueness and referential integrity matter;
- access patterns include varied filters and joins;
- ad hoc operational queries are valuable;
- schemas and migrations are owned;
- the workload fits the engine's scaling and availability model.

For the task domain:

```text
projects(project_id, tenant_id, name, ...)
memberships(project_id, member_id, role, ...)
tasks(task_id, project_id, assignee_id, state, version, ...)
comments(comment_id, task_id, author_id, body, ...)
```

Primary, foreign-key, unique, check, and exclusion constraints can enforce part of the domain close to the writes. Transactions can preserve multi-row invariants. Application authorization and cross-system rules still remain application responsibilities.

Relational does not mean one server, one table, or no JSON. It describes a model and query algebra; product implementations differ in replication, partitioning, indexing, isolation, and operations.

## 6. Normalize to give facts one home

Normalization reduces update anomalies by decomposing data so one fact has one authoritative representation under its dependencies. If every task row repeats the project owner's email, changing the email requires updating many rows and risks disagreement.

Normalization improves integrity and flexibility, but it is not a contest to maximize table count. The useful question is which facts must change together and which dependencies the schema should enforce.

Keep a normalized authoritative model when:

- facts change independently;
- uniqueness or referential rules matter;
- many query shapes need composition;
- duplicated updates would be risky;
- storage and join cost meet objectives.

Measure actual query plans and data. A join between indexed bounded relations can be cheaper and safer than maintaining a large duplicated structure.

## 7. Denormalize for a named read path

Denormalization duplicates or precomputes data to reduce read-time work, serve a different partition, preserve a historical label, or meet a latency and availability objective.

Every denormalized field needs:

- authoritative source;
- update trigger and ordering;
- expected freshness;
- conflict rule;
- backfill and rebuild path;
- reconciliation query;
- deletion and privacy propagation;
- acceptable behavior when stale.

For example, a task summary may copy the assignee display name so a board renders without an identity-service call. Is it the current name or the name when assigned? If current, updates must propagate. If historical, the field should be named and documented as a snapshot.

Denormalization trades read coordination for write and repair coordination. Make the trade explicit.

## 8. Design indexes from complete access patterns

An index is another organized representation of data. It accelerates matching and ordering at the cost of storage, write amplification, maintenance, cache pressure, and migration work.

Index design must include:

- equality and range predicates;
- leading-key order;
- sort direction and stable tie-breaker;
- projected columns or fields;
- selectivity and cardinality;
- null and collation behavior;
- partial or sparse conditions;
- update frequency and write cost;
- tenant and partition scope.

PostgreSQL's documentation states the central tradeoff plainly: indexes can retrieve rows much faster but add system overhead and should be used sensibly. The specific index method must match the operators and ordering involved.

An unused index is not free. Inventory usage, but do not delete solely because a short observation window missed a monthly, recovery, or incident query.

## 9. Use key-value models for bounded key access

A key-value model maps a key to an opaque or structured value. It fits when operations are dominated by known keys and bounded ranges, such as sessions, configuration snapshots, idempotency results, carts, or aggregate state.

Strengths include direct lookup, simple partitioning, and predictable access when keys distribute well. Costs include limited ad hoc querying, careful secondary-index design, application-enforced relationships, and key-driven transaction boundaries.

The key often encodes several dimensions:

```text
PK = TENANT#<tenant_id>#PROJECT#<project_id>
SK = TASK#<task_id>
```

This is a physical access design, not proof of correct domain modeling. Document every query it supports and every query it makes expensive. Model hot partitions, item and transaction limits, pagination, conditional writes, and migrations before committing.

## 10. Use document models around aggregate boundaries

A document model stores a structured value, often JSON-like, under an identity. It fits when data is commonly read and changed as one bounded aggregate with variable optional attributes.

Embedding can provide one-read locality and atomic updates within the document. Referencing avoids unbounded growth and repeated shared data. Choose per relationship:

- Does the child share the parent's lifecycle?
- Is it read with the parent most of the time?
- Can the collection grow without bound?
- Do independent writers update different children?
- Is the child referenced elsewhere?
- Must constraints span multiple documents?

Embedding all comments in a task document may work for small bounded discussions and fail for a task with millions of comments, high write concurrency, or independent retention. “Schema flexible” does not mean schema absent; applications still need version, validation, indexes, and migrations.

## 11. Use graph models when paths are the query

A property graph represents entities as nodes and connections as typed, directed relationships; both can have properties. It is useful when the primary questions traverse variable-depth relationships or discover patterns:

- dependency and blast-radius analysis;
- identity and entitlement relationships;
- fraud rings;
- recommendations;
- network or knowledge graphs;
- supply-chain provenance.

Graph storage is not automatically justified because the domain contains relationships. Relational databases also represent relationships well, particularly bounded joins with strong transactional constraints. A graph model earns its cost when traversal shape, depth, path semantics, and update workload fit it better.

Define path direction, relationship meaning, maximum or bounded traversal, cycles, high-degree nodes, tenant isolation, and consistency. A generic `CONNECTED_TO` edge usually hides the domain. Neo4j's model emphasizes typed directional relationships and properties; constraints and indexes still matter.

## 12. Use search engines for retrieval, not silent authority

Search indexes optimize full-text retrieval, ranking, analyzers, faceting, and combinations of filters that operational stores may not serve efficiently. They are commonly derived from an authoritative database.

Model:

- indexed document identity and source version;
- tokenization, language, normalization, and analyzers;
- searchable versus filterable fields;
- authorization filtering;
- indexing delay and freshness SLI;
- partial update, delete, and tombstone behavior;
- reindex and alias cutover;
- missed-event detection and reconciliation;
- result limit and deep-pagination policy.

Search ranking is not a stable total order unless the contract defines it. A search hit can become stale between retrieval and action, so authoritative operations must reauthorize and revalidate current state.

Never leak a private document through snippets, aggregations, timing, or stale index permissions. Deletion workflows must cover the index and old index generations.

## 13. Use object storage for immutable or large values

Object storage fits blobs and immutable or versioned values addressed by a key: attachments, media, exports, backups, model artifacts, logs, and archives.

It usually does not provide arbitrary field queries or the update semantics of a database row. Store metadata and business relationships in an authoritative model, and treat the object key, version, checksum, size, content type, encryption, and lifecycle as one contract.

For uploads, define reservation, authorization, size and type validation, checksum, malware scanning, publication, orphan cleanup, and abort behavior. A database row pointing to an incomplete object and an object with no owning row are both recoverable states only if modeled.

Avoid overwriting a mutable key when immutable version identity improves caches, audit, and rollback. Lifecycle policies are asynchronous cleanup tools, not application transactions.

## 14. Use time-series models for time-window aggregation

Time-series systems organize timestamped measurements, often by metric identity and indexed dimensions. They fit monitoring, device telemetry, finance observations, and other append-heavy time-window queries.

Define:

- event time versus ingestion time;
- clock precision and synchronization assumptions;
- series identity and bounded tag cardinality;
- late, duplicate, and out-of-order points;
- retention and downsampling;
- rollup functions and units;
- correction and deletion behavior;
- raw versus derived authority.

Putting an unbounded user ID, request ID, or URL in an indexed label can create a series per value and exhaust resources. High-cardinality identifiers often belong in logs or traces with a correlation key rather than metric dimensions.

Time-series storage may answer “what was observed?” without being the authority for “what is true now.”

## 15. Treat caches as disposable derived state

A cache stores a copy chosen for faster or more available reads. It needs:

- key and tenant scope;
- authoritative source and source version;
- TTL and explicit invalidation;
- cache-aside, read-through, write-through, or other update model;
- stale tolerance and negative caching;
- stampede and hot-key control;
- capacity and eviction behavior;
- cold-start and source-protection plan;
- sensitive-data and deletion behavior.

Do not rely on eviction as business deletion or on cache presence as durability. A cache should be rebuildable, and its loss must have a bounded impact on the source. If the source cannot survive a cold cache, the cache is operationally mandatory even if logically derived.

## 16. Distinguish transactions from eventual repair

Group facts in one transaction when the business invariant must hold before acknowledgment and the engine can enforce it at acceptable cost. Use asynchronous projection when stale derived data is acceptable and repairable.

Do not split one invariant across stores merely to use a fashionable service for each query. A cross-store workflow introduces partial completion, idempotency, ordering, compensation, and reconciliation.

A transactional outbox can commit authoritative state and a publication record together; a relay updates derived models and can retry. This still yields duplicates and lag, so projections require source versions and idempotent application.

Saga-style compensation is a new business action, not rollback of time. It may be impossible to undo an email, external payment, or observed disclosure.

## 17. Choose consistency per operation

Avoid labeling an entire system “strongly consistent” or “eventually consistent.” State what each operation needs:

- read-your-write;
- monotonic reads;
- consistent prefix;
- bounded staleness;
- linearizable conditional update;
- snapshot for a multi-item report;
- causal ordering;
- convergent asynchronous projection.

Authorization and money invariants often require current authoritative state. Search and analytics may tolerate seconds or minutes of lag. A user who just edited a task may require read-your-write even if other viewers can tolerate bounded delay.

Consistency modes affect latency, availability, cost, and failure behavior. The API contract from Chapter 107 must expose the behavior consumers need without leaking irrelevant storage details.

## 18. Design retention and deletion across copies

Retention applies to authoritative records, indexes, caches, events, logs, analytics, exports, object versions, backups, and temporary migration data.

For every class, define:

- creation purpose and legal basis where applicable;
- active retention and archive transition;
- deletion trigger and maximum completion time;
- hold and exception behavior;
- physical versus logical deletion;
- encryption-key dependency;
- deletion evidence without retaining the deleted content;
- behavior in immutable backups and replay.

Time-to-live features are asynchronous and may not meet an immediate access-revocation objective. Remove authorization and query visibility first where required, then complete physical lifecycle under the declared contract.

## 19. Include recovery in storage selection

A storage choice is incomplete without backup, restore, replication, corruption detection, and dependency recovery.

Ask:

- What acknowledged data can be lost under the RPO?
- How long can the journey remain unavailable under the RTO?
- Can backups restore to a separate failure boundary?
- Are keys, schemas, object versions, and external identities included?
- Can a derived model rebuild from retained authoritative history?
- How long does rebuild take at projected scale?
- Can operators identify a clean recovery point after logical corruption?
- Has application integrity been validated after restore?

Replication improves availability and may replicate corruption or deletion immediately. Backups preserve recoverable history but do not serve live traffic. Both may be required.

## 20. Model storage amplification and cost

Logical data size is only the start. Include:

```text
primary records
+ indexes
+ replicas
+ versions and history
+ write-ahead or transaction logs
+ backups and snapshots
+ search and analytics projections
+ cache capacity
+ migration headroom
+ observability
```

Also price requests, transactions, scans, compaction, provisioned capacity, I/O, egress, cross-zone or cross-region transfer, backup retrieval, licenses, and operator time.

An index that doubles write work may be justified for a critical read. A separate database for a minor feature may cost more in ownership than it saves in queries. Measure unit economics against workload ranges.

## 21. Resist accidental polyglot persistence

Using multiple storage models can isolate workloads and fit specialized access patterns. It also creates:

- more identities, networks, backups, and upgrades;
- cross-store consistency and deletion work;
- more failure and incident paths;
- scarce expertise and on-call burden;
- migration and vendor lifecycle dependencies;
- duplicated sensitive data.

Start with the smallest set that satisfies critical requirements. Many systems can use one relational authority plus object storage and add a search projection only when evidence justifies it. Other systems genuinely need a high-scale key-value authority or graph traversal engine.

Require every new store to name the unsupported requirement, benchmark or experiment, owner, data-flow contract, recovery plan, cost, and exit path.

## 22. Plan migrations as online compatibility changes

Schema and storage migrations occur while old and new code may run, retries arrive, queues replay, and backups retain prior representations.

A safe sequence is:

1. add compatible schema and capacity;
2. deploy readers tolerant of old and new forms;
3. capture new writes through one authoritative path;
4. backfill in bounded batches with checkpoints;
5. compare counts, checksums, invariants, and sampled business results;
6. switch reads gradually with shadow comparison where safe;
7. stop old writes and reconcile the remaining gap;
8. wait through rollback and replay windows;
9. remove old representation in a later change;
10. delete migration copies and verify cost.

Throttle backfills by source health, replica lag, lock impact, queue growth, and business latency. A fast migration that causes an outage is not efficient.

## 23. Match the task system to a small storage portfolio

For the task system, one defensible initial model is:

- relational authority for tenants, projects, memberships, tasks, comments, and audit references;
- object storage for immutable attachment versions;
- an asynchronously built search index for text retrieval;
- a bounded cache only for measured hot reads;
- an analytics destination fed from owned change capture.

This is not universal. A workload dominated by enormous predictable key access may choose a key-value authority. Deep dependency traversal may justify a graph projection. Very large telemetry streams may require time-series storage.

The important model is the arrows:

```text
relational authority -> outbox/change capture -> search projection
                     \-> analytics projection
relational attachment metadata <-> immutable object version
cache <- versioned reads from authority
```

Each arrow needs delivery, ordering, freshness, retry, deletion, replay, and reconciliation. The diagram is not complete until those contracts exist.

## 24. Encode a storage-selection review

The following model checks that a candidate has evidence for each access path and that derived stores have lifecycle contracts.

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class AccessPattern:
    name: str
    predicate: str
    ordering: str
    peak_per_second: int
    consistency: str
    maximum_latency_ms: int

    def validate(self) -> None:
        if not all((self.name.strip(), self.predicate.strip(), self.consistency.strip())):
            raise ValueError("access pattern needs name, predicate, and consistency")
        if self.peak_per_second <= 0 or self.maximum_latency_ms <= 0:
            raise ValueError("access pattern needs positive workload bounds")


@dataclass(frozen=True)
class DerivedModel:
    name: str
    authority: str
    freshness_seconds: int
    rebuild_tested: bool
    reconciliation_defined: bool
    deletion_propagates: bool

    def validate(self) -> None:
        if not self.name.strip() or not self.authority.strip():
            raise ValueError("derived model needs a named authority")
        if self.freshness_seconds < 0:
            raise ValueError("freshness bound cannot be negative")
        if not self.rebuild_tested or not self.reconciliation_defined:
            raise ValueError("derived model needs tested rebuild and reconciliation")
        if not self.deletion_propagates:
            raise ValueError("derived model does not honor deletion")


@dataclass(frozen=True)
class StorageDecision:
    authority: str
    invariants_enforced: bool
    access_patterns: tuple[AccessPattern, ...]
    measured_plans: tuple[str, ...]
    backup_restore_tested: bool
    migration_defined: bool
    cost_modeled: bool
    derived_models: tuple[DerivedModel, ...]

    def validate(self) -> None:
        if not self.authority.strip() or not self.invariants_enforced:
            raise ValueError("authoritative model must preserve invariants")
        if not self.access_patterns:
            raise ValueError("storage decision needs access patterns")
        for pattern in self.access_patterns:
            pattern.validate()
        if len(self.measured_plans) != len(self.access_patterns):
            raise ValueError("every access pattern needs measured evidence")
        if not self.backup_restore_tested:
            raise ValueError("storage requires tested restore evidence")
        if not self.migration_defined or not self.cost_modeled:
            raise ValueError("migration and cost are part of storage selection")
        for model in self.derived_models:
            model.validate()
```

Executable tests exercise the contract:

```python
import unittest

from storage_decision import AccessPattern, DerivedModel, StorageDecision


def valid_decision() -> StorageDecision:
    access = AccessPattern(
        "assigned open tasks", "tenant + project + assignee + OPEN",
        "priority desc, updated_at desc, task_id", 1200,
        "visible within two seconds", 300,
    )
    search = DerivedModel("task search", "task database", 5, True, True, True)
    return StorageDecision(
        "task database", True, (access,), ("representative query plan",),
        True, True, True, (search,),
    )


class StorageDecisionTests(unittest.TestCase):
    def test_complete_decision_is_accepted(self) -> None:
        valid_decision().validate()

    def test_missing_access_pattern_is_rejected(self) -> None:
        decision = valid_decision()
        fields = {**decision.__dict__, "access_patterns": (), "measured_plans": ()}
        with self.assertRaisesRegex(ValueError, "access patterns"):
            StorageDecision(**fields).validate()

    def test_unmeasured_access_path_is_rejected(self) -> None:
        decision = valid_decision()
        fields = {**decision.__dict__, "measured_plans": ()}
        with self.assertRaisesRegex(ValueError, "measured evidence"):
            StorageDecision(**fields).validate()

    def test_unbounded_workload_is_rejected(self) -> None:
        decision = valid_decision()
        bad = AccessPattern("tasks", "tenant", "", 0, "current", 300)
        fields = {**decision.__dict__, "access_patterns": (bad,)}
        with self.assertRaisesRegex(ValueError, "positive workload"):
            StorageDecision(**fields).validate()

    def test_untested_rebuild_is_rejected(self) -> None:
        decision = valid_decision()
        bad = DerivedModel("search", "task database", 5, False, True, True)
        fields = {**decision.__dict__, "derived_models": (bad,)}
        with self.assertRaisesRegex(ValueError, "rebuild"):
            StorageDecision(**fields).validate()

    def test_missing_deletion_propagation_is_rejected(self) -> None:
        decision = valid_decision()
        bad = DerivedModel("search", "task database", 5, True, True, False)
        fields = {**decision.__dict__, "derived_models": (bad,)}
        with self.assertRaisesRegex(ValueError, "deletion"):
            StorageDecision(**fields).validate()

    def test_untested_restore_is_rejected(self) -> None:
        decision = valid_decision()
        fields = {**decision.__dict__, "backup_restore_tested": False}
        with self.assertRaisesRegex(ValueError, "restore"):
            StorageDecision(**fields).validate()

    def test_missing_cost_model_is_rejected(self) -> None:
        decision = valid_decision()
        fields = {**decision.__dict__, "cost_modeled": False}
        with self.assertRaisesRegex(ValueError, "cost"):
            StorageDecision(**fields).validate()


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

Save the blocks as `storage_decision.py` and `test_storage_decision.py`, then run:

```bash
python -m unittest -v test_storage_decision.py
```

A production review should add representative datasets, query plans, benchmarks, concurrency tests, failure tests, backup restoration, backfill rehearsal, reconciliation, privacy deletion, and cost evidence. A benchmark without realistic cardinality, skew, indexes, and durability settings is not selection evidence.

## 25. Review a data and storage model

```text
domain entities, relationships, identity, tenants, and business meaning:
commands, queries, predicates, ordering, projection, consistency, and latency:
rates, concurrency, sizes, skew, amplification, retention, and growth:
authority for every fact and enforcement owner for every invariant:
relational constraints, normalization, transaction, join, and query needs:
key-value keys, partitions, range access, conditions, and hot-key behavior:
document aggregate, embedding, references, growth, and concurrent updates:
graph nodes, typed relationships, paths, degree, cycles, and traversals:
search analyzers, ranking, authorization, freshness, reindex, and deletes:
object identity, version, checksum, metadata, scan, lifecycle, and orphans:
time basis, series identity, cardinality, late points, rollup, and retention:
cache source, key, version, TTL, invalidation, stampede, and cold start:
derived source, delivery, order, freshness, rebuild, reconcile, and erase:
read/write consistency, conflict, session behavior, and partial failure:
indexes, query plans, write amplification, storage, and migration impact:
backup, restore, corruption, keys, RPO, RTO, and rebuild duration:
logical size, replicas, indexes, history, projections, egress, and labor:
online migration, backfill, checkpoints, comparison, rollback, and cleanup:
owners, on-call, security, compliance, cost, exit, and review date:
```

## Common Misconceptions

- “The database is the data model.” Domain, logical, and physical models are related but distinct.
- “NoSQL means no schema.” Every reader assumes structure and meaning, whether or not the engine enforces it.
- “Normalization is slow.” Query shape, indexes, cardinality, plans, and hardware determine cost.
- “Denormalization removes joins.” It moves coordination into writes, propagation, and repair.
- “An index is free after creation.” It consumes storage, cache, write work, migration time, and operations.
- “Graph databases are for any connected data.” They earn their place when path traversal is a primary workload.
- “Search can be the source of truth.” Ranking and retrieval indexes are often stale derived representations.
- “A cache is optional because data is durable elsewhere.” Cold-cache load can make it operationally essential.
- “Replication is backup.” It can reproduce corruption and deletion quickly.
- “Purpose-built databases always reduce complexity.” Every added store creates cross-store lifecycle and ownership.

## Core Computer Science Concept

This chapter applies **data independence, functional dependencies, normalization, indexing, materialized views, locality, replication, and consistency models**. Physical representations optimize selected operations, while constraints preserve valid states. Duplication converts read-time computation into write-time propagation plus reconciliation.

## Engineering Connections

- Files, blocks, objects, and durability build on Chapters 3, 41, 83, 97, and 98.
- Keys, indexes, constraints, and transactions extend Chapters 15, 99, and 100.
- Derived-state delivery applies Chapters 74, 76, 101, and 107.
- Data protection and deletion use Chapters 87, 92, 97, and 104.
- Workload evidence comes from Chapter 106 and prepares Chapter 109's partitioning model.

## From the Field

A team copies current member names into every task document for fast board reads. Years later, privacy erasure updates the identity record but misses old tasks, search indexes, exports, and backups because nobody defined whether the copied name was current truth or historical snapshot. A named authoritative source, explicit snapshot semantics, propagation inventory, and deletion contract would have made the duplication reviewable.

## Engineering Review

### What problem does this solve?

It maps business truth and critical access paths to a small owned set of storage representations with explicit consistency, repair, recovery, and lifecycle.

### Why was it designed this way?

Storage engines optimize different operations. Starting from products hides invariants and copy costs; starting from access patterns and lifecycle makes tradeoffs observable.

### When should I use it?

Use it when introducing or changing authoritative data, indexes, caches, search, analytics, object storage, or any derived copy.

### When should I avoid it?

Do not add a specialized store for a hypothetical query. Use the simplest owned model that meets measured requirements and preserve a migration path.

### How does this make me a better engineer?

It teaches you to distinguish meaning from layout, trace every copy to an authority, choose indexes from operations, and include deletion and restore in data design.

### How does this reduce waste?

It reduces accidental polyglot persistence, redundant indexes, unbounded documents, stale permissions, unrebuildable projections, orphaned objects, missed erasure, and migrations without evidence.

## Handbook Principle #108

> Store each business fact under one declared authority, derive other representations for named access paths, and own every copy's consistency, repair, recovery, cost, and deletion.

## Practical Observation

Choose one field visible in your product and enumerate every place it exists: authority, replicas, caches, search, events, analytics, logs, exports, and backups. For each copy, name freshness, reconciliation, access, retention, and deletion. The first unknown answer is a data-model risk, not merely documentation debt.

## Phase 1 Complete

Chapters 106–108 turn an ambiguous request into a measurable system model, stable behavioral contracts, and an owned data model. Part IX can now reason about scale and coordination without inventing requirements or treating storage as a product checklist.

## Looking Ahead

Chapter 109 derives capacity and partitioning decisions from workload estimates, queueing relationships, bottleneck evidence, hotspot behavior, replication purpose, autoscaling delay, and rebalancing cost.

## References

- [PostgreSQL — Constraints](https://www.postgresql.org/docs/current/ddl-constraints.html)
- [PostgreSQL — Indexes](https://www.postgresql.org/docs/current/indexes.html)
- [AWS Decision Guide — Choosing a database service](https://docs.aws.amazon.com/pdfs/decision-guides/latest/databases-on-aws-how-to-choose/databases-on-aws-how-to-choose.pdf)
- [Amazon DynamoDB — Data modeling foundations](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/data-modeling-foundations.html)
- [MongoDB — Data modeling introduction](https://www.mongodb.com/docs/manual/data-modeling/)
- [Neo4j — Graph database concepts](https://neo4j.com/docs/getting-started/appendix/graphdb-concepts/)
- [Elasticsearch — Mapping and field data types](https://www.elastic.co/guide/en/elasticsearch/reference/current/mapping.html)
- [InfluxDB — Schema design](https://docs.influxdata.com/influxdb3/core/write-data/best-practices/schema-design/)
- [Amazon S3 — Data protection and lifecycle](https://docs.aws.amazon.com/AmazonS3/latest/userguide/data-protection.html)
- [Chapter 100 — DynamoDB, Caching, and NoSQL Access Patterns](../aws/100-dynamodb-caching-and-nosql-access-patterns.md)
- [Chapter 107 — Interfaces, Contracts, and Evolution](107-interfaces-contracts-and-evolution.md)
