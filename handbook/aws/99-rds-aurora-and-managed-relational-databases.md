# Chapter 99 — RDS, Aurora, and Managed Relational Databases

A managed database can replace failed infrastructure, take backups, and apply engine maintenance while an application still overwhelms its connections, deploys an incompatible schema, reads stale replicas, or cannot restore within its recovery objective. Management changes who performs work; it does not erase the database contract.

The central idea is:

> Use managed relational services to transfer repeatable infrastructure operations, then keep schema, transactions, queries, connections, recovery, and change sequencing under explicit application ownership.

## 1. Relational requirements come before the service

A relational database is a good fit when the workload needs combinations of:

- declared schemas and constraints;
- transactions across related records;
- joins and flexible indexed queries;
- referential integrity;
- mature SQL tools and drivers;
- established engine compatibility.

Write the workload contract first: transaction boundaries, consistency, query shapes, data volume and growth, latency, concurrency, availability, recovery point and time, retention, engine features, and licensing. “Use RDS” is a deployment choice, not a data model.

## 2. RDS transfers infrastructure work, not data ownership

Amazon RDS supports managed deployments of several relational engines. Depending on engine and configuration, AWS manages work including host provisioning, storage integration, infrastructure replacement, service monitoring, backups, and supported patch workflows.

The customer still owns:

- engine, edition, version, and feature selection;
- schema, constraints, indexes, and migrations;
- queries, transactions, locks, and isolation behavior;
- users, database privileges, secrets, and network access;
- instance, storage, parameter, and availability choices;
- application connection pooling and retry behavior;
- backup retention, restore validation, and disaster recovery;
- maintenance timing and upgrade compatibility;
- data classification, retention, deletion, and cost.

Managed does not mean administrator-free. It means administration occurs through supported service boundaries instead of unrestricted host access.

## 3. Choose an engine by compatibility and ownership

RDS offers engines such as PostgreSQL, MySQL, MariaDB, Oracle, SQL Server, and Db2 in supported combinations. Aurora provides AWS-designed, MySQL-compatible and PostgreSQL-compatible engines with a distinct distributed storage architecture.

Evaluate:

- SQL and wire-protocol compatibility;
- required extensions, collations, data types, and procedural code;
- version lifecycle and upgrade path;
- replication and migration tools;
- licensing and support obligations;
- operational features and limits;
- team expertise and incident tooling;
- ability to leave the service later.

“Compatible” is not “identical.” Run application, migration, query-plan, driver, and operational tests against the exact engine family and version.

## 4. A DB instance is a bounded compute and memory envelope

For ordinary RDS, a DB instance combines managed compute with configured storage. Instance class affects CPU, memory, network, EBS bandwidth, and connection capacity. Storage choices affect capacity, IOPS, throughput, latency, and autoscaling behavior.

Measure:

- CPU saturation and load;
- freeable memory and swap;
- read/write IOPS, throughput, latency, and queue depth;
- connection count and churn;
- transaction rate and lock waits;
- cache hit behavior;
- temporary space;
- replication lag;
- engine-specific waits and top SQL.

Vertical scaling can relieve a bottleneck but may require failover or interruption. It does not repair missing indexes, unbounded queries, lock contention, or a connection storm.

## 5. Storage autoscaling protects capacity, not performance

Supported RDS configurations can increase allocated storage up to a configured maximum when free space becomes low. This helps avoid `storage-full`, but it is not a complete capacity plan.

Autoscaling does not necessarily:

- increase provisioned IOPS or throughput in the needed ratio;
- shrink storage later;
- fix transaction-log, temporary-file, or table-bloat causes;
- guarantee growth finishes before a sudden ingest spike;
- make the resulting monthly cost acceptable.

Alert on growth rate and time to exhaustion before the threshold. Investigate why data grows, define retention and archival, test maximum-storage behavior, and keep infrastructure declarations aligned with runtime changes.

## 6. Single-AZ is one availability boundary

A Single-AZ DB instance can be appropriate for disposable development, rebuildable workloads, or recovery objectives that tolerate replacement and restore. Its lower cost does not make it a production default.

Define what happens when its host, storage path, or Availability Zone is unavailable. Automated backups may preserve a recovery point, but restoring and validating a new instance takes time. Backups provide recovery; they do not provide a ready synchronous failover target.

## 7. Multi-AZ has more than one deployment model

RDS Multi-AZ configurations differ:

- A **Multi-AZ DB instance deployment** maintains one standby for failover. That standby does not serve application read traffic.
- A **Multi-AZ DB cluster deployment** has a writer and two readable instances in three Availability Zones for supported engines and configurations.

Do not infer the model from the phrase “Multi-AZ.” Record the exact topology, endpoints, replication behavior, readable capacity, failover targets, and engine support.

Multi-AZ improves availability; it does not make every transaction immune to interruption. Connections break during failover, in-flight transactions can abort, and clients must reconnect to the service endpoint with safe retry semantics.

## 8. Failover is an application event

RDS can initiate failover after infrastructure failure, maintenance, instance modification, or an explicit reboot with failover. The endpoint name stays the application contract while its resolved destination changes.

Applications must:

- use the managed endpoint rather than a cached instance address;
- bound DNS caching appropriately;
- time out failed connections;
- discard invalid pooled connections;
- reconnect with backoff and jitter;
- retry only transactions known to be safe;
- tolerate an unknown commit result;
- recover session state and temporary tables;
- expose degraded database health without retry storms.

Rehearse failover under traffic. Measure error rate, reconnect time, transaction outcome, pool recovery, and user-visible duration.

## 9. Read replicas are asynchronous read capacity

RDS read replicas use engine replication and are generally asynchronous. They can offload reporting or read-heavy work and can support disaster-recovery strategies. They are not the same as a Multi-AZ standby.

A replica may be stale. Before routing a query to it, ask whether the user must read a just-committed write, whether lag is bounded, and what happens during replication failure. Common policies include:

- read-after-write from the writer for a bounded session window;
- route only stale-tolerant queries to replicas;
- compare a replication position or application version token;
- shed optional replica reads when lag exceeds a threshold;
- never issue writes through a read-only endpoint.

Promotion creates an independent writable database and changes recovery topology. It is not an automatic merge back into the former source.

## 10. Aurora separates compute instances from cluster storage

An Aurora cluster contains a distributed cluster volume and one or more DB instances. One writer performs read/write work. Aurora Replicas attach to the shared cluster volume and serve reads; a replica can be promoted during failover.

The cluster volume spans multiple Availability Zones independently of the number of instances. Storage durability does not mean compute availability: a cluster with no reader still needs to create or recover a writer after failure. For high availability, deploy appropriately sized replicas in different zones and set promotion tiers deliberately.

Aurora's architecture changes storage, replication, failover, and scaling behavior, but applications still use a MySQL- or PostgreSQL-compatible engine contract with version-specific differences.

## 11. Use Aurora endpoints by role

Aurora exposes endpoint types:

- the cluster or writer endpoint follows the current writer;
- the reader endpoint distributes new read-only connections among eligible readers;
- instance endpoints address one specific instance;
- custom endpoints group selected instances for specialized workloads.

Endpoints route connections, not individual SQL statements. A long-lived connection remains on the instance it reached. Reader-endpoint DNS behavior can produce uneven connection distribution, and during topology changes clients must reconnect.

Use instance endpoints for diagnosis or an explicitly pinned operational task, not ordinary high-availability application traffic.

## 12. Connection count is a shared finite resource

Every process, container, function, worker, and deployment generation can create a pool. Fleet size multiplied by pool size can exceed database memory and connection limits even when query volume is modest.

Budget connections:

```text
reserved administration
+ migrations and jobs
+ each service's steady pools
+ autoscaling headroom
+ deployment overlap
+ incident headroom
<= safe database connection capacity
```

Use bounded application pools, acquisition timeouts, idle eviction, connection lifetime, and request deadlines. Monitor checked-out duration and waiters, not only total connections.

RDS Proxy can pool and multiplex compatible workloads, absorb some connection churn, and help clients through topology changes. It does not make transactions stateless, remove database limits, or repair slow SQL. Session state and some operations can pin a client to a backend connection.

## 13. Transactions need uncertainty-aware retries

A connection failure near `COMMIT` can leave the client unsure whether the transaction committed. Blindly rerunning a charge, message, or inventory decrement can duplicate business effects.

Design with:

- idempotency keys and uniqueness constraints;
- transactionally stored operation results;
- outbox records for downstream messages;
- bounded retries only for classified transient errors;
- a lookup path for unknown outcomes;
- deadlock retries around the whole transaction;
- short transactions and deterministic lock order.

High availability increases the chance that service recovers quickly; it does not turn ambiguous outcomes into exactly-once execution.

## 14. Parameter groups are versioned runtime configuration

DB parameter groups and cluster parameter groups expose supported engine settings. Some parameters apply dynamically; others are pending until reboot. Defaults can vary by engine family and service context.

Treat parameter changes as code:

- pin the correct engine family;
- record rationale and expected metric;
- test against production-like workload;
- classify dynamic versus reboot-required behavior;
- review memory interactions among parameters;
- stage and observe change;
- track `pending-reboot` and pending modifications;
- retain rollback procedure.

A maintenance window does not automatically reboot every resource merely because a parameter shows pending reboot. Verify the actual apply state.

## 15. Backups provide a recovery window

RDS automated backups combine snapshots and transaction logs to support point-in-time recovery within a configured retention period. Manual snapshots persist until explicitly deleted. Aurora has related cluster backup and restore mechanisms.

Backup policy must name:

- retention and latest-restorable-time monitoring;
- backup and maintenance windows;
- manual pre-change snapshots where useful;
- cross-Region or cross-account copies;
- KMS keys and grants;
- deletion behavior and final snapshots;
- legal retention and independent governance;
- restore frequency and acceptance tests.

Automated backups can stop advancing when a database is stopped or not in an eligible state. Monitor evidence, not configuration alone.

## 16. Point-in-time recovery creates a new resource

An RDS point-in-time restore creates a new DB instance; Aurora restores a new cluster. The source is not rewound in place. The restored resource needs review of:

- target timestamp and time zone;
- instance class and storage;
- subnet and security groups;
- parameter and option groups;
- encryption key;
- certificates and authentication;
- monitoring and logs;
- endpoints, DNS, and application secrets;
- replication and Multi-AZ topology;
- tags, backups, alarms, and deletion protection.

Then validate schema, row-level business invariants, dependent systems, and missing events before cutover. Restore time includes creation, storage initialization, validation, application reconfiguration, and reconciliation—not just the API reaching `available`.

## 17. Availability is not disaster recovery

Multi-AZ handles selected local failures. Disaster recovery addresses a wider loss or compromise boundary. Define:

- Regional recovery target;
- acceptable data loss and downtime;
- backup or replica independence;
- cross-Region networking, secrets, keys, and certificates;
- infrastructure and application deployment;
- DNS or endpoint cutover;
- write fencing and split-brain prevention;
- return-to-primary procedure.

Cross-Region replicas can reduce recovery point but may reproduce corruption and remain dependent on source administration. Backups can provide history but take longer to restore. Use the combination required by the threat model.

## 18. Maintenance is inevitable change

RDS has preferred maintenance windows for pending modifications and service maintenance. The window controls when work begins, not an absolute completion deadline. Mandatory engine, operating-system, certificate, or hardware changes cannot be deferred forever.

Operate maintenance as a release:

- subscribe to events and review pending actions;
- test engine minor and major versions;
- verify driver and extension compatibility;
- rehearse failover and rollback constraints;
- schedule when owners can observe;
- drain or reduce sensitive workloads;
- validate after change;
- remove obsolete versions before forced deadlines.

Blue/green deployment features can reduce risk for supported engines and changes, but data synchronization, switchover, schema compatibility, and application validation remain real work.

## 19. Schema changes are application releases

AWS does not decide whether a migration is safe for old and new application versions. Use expansion and contraction when deployments overlap:

1. add backward-compatible structures;
2. deploy code that can use both forms;
3. backfill in bounded, restartable batches;
4. verify data and query plans;
5. switch reads and writes;
6. remove old structures only after every consumer leaves.

Control locks, statement timeout, transaction duration, replica lag, write amplification, and rollback. A DDL statement that succeeds in staging can block a large production table.

Keep one migration authority, an applied-migration ledger, immutable migration artifacts, and startup behavior that does not let every replica race to alter production.

## 20. Encrypt transport, storage, and credentials

Enable RDS or Aurora encryption at creation with the intended KMS key. Encrypted storage includes underlying storage, logs, backups, and snapshots according to service behavior. Migrating an unencrypted database generally requires snapshot-copy or data-migration workflows rather than toggling encryption in place.

Require TLS and validate the server certificate using the current RDS trust bundle. Certificate rotation is an application dependency: inventory clients, trust stores, drivers, and connection settings before the old certificate expires.

Store database credentials in a managed secret workflow, rotate them, and prefer temporary IAM database authentication where supported and appropriate. Database authorization remains necessary after network and IAM admission.

## 21. Network isolation narrows the access path

Place production databases in a DB subnet group spanning the required Availability Zones. Avoid public accessibility unless the use case and controls explicitly require it. Security groups should admit only intended application or administration sources on the engine port.

Network reachability is not database authorization. Combine private routing, security groups, TLS, authenticated database users, least privileges, audit, and secret rotation. Keep break-glass administration separate from application credentials.

## 22. Observe service, engine, and workload together

Use multiple evidence layers:

- RDS events and resource status;
- CloudWatch host and storage metrics;
- Enhanced Monitoring for operating-system detail where enabled;
- Database Insights or supported query-performance tooling;
- engine logs and slow-query evidence;
- replication lag and failover events;
- pool saturation and application traces;
- backup latest-restorable time and snapshot state;
- configuration and maintenance changes;
- cost, reservation, and extended-support signals.

Alert on user symptoms plus exhausted safety margins: latency, error rate, pool wait, storage runway, memory, connections, replica lag, deadlocks, and recovery evidence. A green CPU graph does not prove healthy transactions.

## 23. Rehearse managed-database failures

Test:

- planned Multi-AZ or Aurora failover under load;
- connection pool recovery and DNS refresh;
- unknown transaction outcome at commit;
- replica lag during a read-after-write flow;
- storage growth to the autoscaling boundary;
- a pending-reboot parameter change;
- certificate rotation;
- KMS or secret access failure;
- point-in-time restore and endpoint cutover;
- a schema migration interrupted halfway;
- one Availability Zone and one Region unavailable;
- backup state stops advancing.

For each, capture maximum errors, recovery time, data-loss bound, business validation, authority, and rollback. A managed failover that the client cannot survive is still an application outage.

## 24. Encode the database operating contract

This standard-library lab validates a production relational service contract. It models policy rather than calling AWS.

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RelationalContract:
    engine_family: str
    topology: str
    availability_zones: int
    backup_retention_days: int
    restore_tested: bool
    failover_tested: bool
    tls_required: bool
    encrypted: bool
    private_network: bool
    max_connections: int
    reserved_connections: int
    application_pools: tuple[int, ...]
    replica_reads_stale_tolerant: bool
    migrations_backward_compatible: bool
    maintenance_owner: str

    def validate(self) -> None:
        if self.engine_family not in {"postgres", "mysql", "aurora-postgres", "aurora-mysql"}:
            raise ValueError("engine family must be explicit and supported by this policy")
        if self.topology not in {"rds-multi-az", "rds-multi-az-cluster", "aurora"}:
            raise ValueError("production topology must provide managed failover")
        if self.availability_zones < 2:
            raise ValueError("production database must span at least two AZs")
        if not 7 <= self.backup_retention_days <= 35:
            raise ValueError("backup retention is outside the reviewed recovery window")
        if not self.restore_tested or not self.failover_tested:
            raise ValueError("restore and failover must both be tested")
        if not self.tls_required or not self.encrypted or not self.private_network:
            raise ValueError("transport, storage, and network controls are required")
        if self.max_connections <= 0 or self.reserved_connections < 1:
            raise ValueError("connection capacity must be positive")
        if sum(self.application_pools) + self.reserved_connections > self.max_connections:
            raise ValueError("application pools exceed the connection budget")
        if self.topology in {"rds-multi-az-cluster", "aurora"}:
            if not self.replica_reads_stale_tolerant:
                raise ValueError("replica reads must tolerate asynchronous visibility")
        if not self.migrations_backward_compatible:
            raise ValueError("overlapping releases require compatible migrations")
        if not self.maintenance_owner:
            raise ValueError("maintenance needs an accountable owner")
```

Tests cover recovery, connection, replica, and migration boundaries:

```python
import unittest

from relational_contract import RelationalContract


def valid_contract() -> RelationalContract:
    return RelationalContract(
        engine_family="aurora-postgres",
        topology="aurora",
        availability_zones=3,
        backup_retention_days=14,
        restore_tested=True,
        failover_tested=True,
        tls_required=True,
        encrypted=True,
        private_network=True,
        max_connections=500,
        reserved_connections=50,
        application_pools=(80, 80, 40),
        replica_reads_stale_tolerant=True,
        migrations_backward_compatible=True,
        maintenance_owner="database-platform",
    )


class RelationalContractTests(unittest.TestCase):
    def test_complete_contract_is_accepted(self) -> None:
        valid_contract().validate()

    def test_single_az_is_rejected(self) -> None:
        contract = valid_contract()
        broken = RelationalContract(**{**contract.__dict__, "availability_zones": 1})
        with self.assertRaisesRegex(ValueError, "at least two AZs"):
            broken.validate()

    def test_connection_overcommit_is_rejected(self) -> None:
        contract = valid_contract()
        broken = RelationalContract(**{
            **contract.__dict__, "application_pools": (240, 240)
        })
        with self.assertRaisesRegex(ValueError, "exceed the connection budget"):
            broken.validate()

    def test_unrehearsed_restore_is_rejected(self) -> None:
        contract = valid_contract()
        broken = RelationalContract(**{**contract.__dict__, "restore_tested": False})
        with self.assertRaisesRegex(ValueError, "restore and failover"):
            broken.validate()

    def test_strong_read_assumption_on_replica_is_rejected(self) -> None:
        contract = valid_contract()
        broken = RelationalContract(**{
            **contract.__dict__, "replica_reads_stale_tolerant": False
        })
        with self.assertRaisesRegex(ValueError, "asynchronous visibility"):
            broken.validate()

    def test_breaking_migration_is_rejected(self) -> None:
        contract = valid_contract()
        broken = RelationalContract(**{
            **contract.__dict__, "migrations_backward_compatible": False
        })
        with self.assertRaisesRegex(ValueError, "compatible migrations"):
            broken.validate()


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

Save the blocks as `relational_contract.py` and `test_relational_contract.py`, then run:

```bash
python -m unittest -v test_relational_contract.py
```

A production verifier should inspect authorized read-only inventory for engine version, topology, zones, endpoints, storage, encryption, subnet and security groups, parameters, backups, maintenance, certificates, logs, metrics, proxy, and replicas. It must not reboot, fail over, restore, modify, or delete a database during validation.

## 25. Review a managed relational service

```text
data owner, classification, engine, version, edition, and compatibility tests:
schema authority, migration ledger, expansion/contraction, and rollback:
instance classes, storage, IOPS, growth, and autoscaling maximum:
Single-AZ, Multi-AZ instance, Multi-AZ cluster, or Aurora topology:
writer, reader, instance, proxy, and administration endpoints:
connection budget, pools, timeouts, lifetime, and deployment overlap:
transactions, isolation, deadlocks, idempotency, and unknown outcomes:
replica query classes, lag limits, read-after-write, and promotion:
backup retention, latest restorable time, snapshots, copies, and deletion:
measured restore time, target configuration, validation, and cutover:
Regional recovery, fencing, reconciliation, and return procedure:
parameters, pending reboot, maintenance, upgrades, and certificates:
subnets, security groups, TLS, users, secrets, KMS keys, and audit:
metrics, engine logs, top SQL, pool signals, events, alarms, and owners:
cost, licenses, reservations, extended support, quotas, and retirement:
```

## Common Misconceptions

- “Managed means AWS owns the schema.” The application team owns relational correctness and change.
- “Multi-AZ doubles read capacity.” A Multi-AZ DB instance standby does not serve reads.
- “A read replica is current.” Asynchronous replication permits lag.
- “Failover is transparent.” Connections and transactions can fail and must recover.
- “Aurora storage means one instance is highly available.” Compute failover still needs a ready replica or recovery.
- “A reader endpoint balances every query.” It selects an instance when a connection is established.
- “RDS Proxy removes connection limits.” It helps pool compatible traffic; the database remains finite.
- “Automated backups prove recovery.” Restore, configure, validate, and cut over must be rehearsed.
- “Point-in-time recovery rewinds production.” It creates a new resource.
- “The maintenance window bounds all maintenance.” Work can continue beyond the window and mandatory upgrades cannot be deferred forever.

## Core Computer Science Concept

Managed relational databases combine **serializable state machines, replicated logs, and indirection**. Transactions order state changes under an isolation contract. Replication projects that log to standby or reader nodes with different visibility guarantees. Stable endpoints redirect new connections after role changes. Correct clients must handle partial knowledge at every boundary.

## Engineering Connections

- Transactions and constraints implement Chapter 15's state invariants.
- Connection pools are bounded queues and admission control.
- Replica reads expose consistency tradeoffs that Chapter 100 generalizes.
- Failover follows Chapter 96's DNS and endpoint convergence model.
- Storage, snapshot initialization, and KMS build on Chapter 98.
- Schema expansion and contraction extend Chapter 77's compatible deployment pattern.
- Unknown commit results require Part VI's idempotency and reconciliation techniques.

## From the Field

A service scales from ten containers to two hundred during a promotion. Each container opens a twenty-connection pool, exhausting the database before CPU rises. Health checks retry, replacements add more pools, and the incident looks like database failure. A fleet-wide connection budget, acquisition timeout, scaling headroom, proxy where appropriate, and pool-wait alert would have turned connections into controlled capacity rather than an amplifier.

## Engineering Review

### What problem does this solve?

It defines the boundary between managed database infrastructure and application-owned relational correctness, then makes availability, replicas, connections, backup, restore, maintenance, and schema change operationally testable.

### Why was it designed this way?

Database infrastructure work is repeatable and automatable, while schemas, transactions, query semantics, and business recovery remain workload-specific. RDS and Aurora separate those concerns through supported service controls.

### When should I use it?

Use this model when selecting RDS or Aurora, sizing a database, adding replicas or a proxy, enabling Multi-AZ, changing parameters, planning maintenance, releasing schema, or defining recovery.

### When should I avoid it?

Avoid a relational engine when the workload does not need its transaction and query model, or when required host access, unsupported extensions, specialized hardware, or licensing cannot fit the managed boundary.

### How does this make me a better engineer?

It teaches you to distinguish infrastructure availability from transaction correctness, budget connections across a fleet, reason about replica visibility, and prove recovery by restoring a usable application.

### How does this reduce waste?

It reduces idle over-sizing, connection storms, unnecessary replicas, manual host administration, untested snapshots, blocking migrations, stale reads, forced-upgrade emergencies, and incidents misdiagnosed from one metric.

## Handbook Principle #99

> A database becomes managed when infrastructure work is delegated without delegating ownership of transactions, schema evolution, client behavior, or recovery proof.

## Practical Observation

Choose one production database and compute its total possible connection demand across steady replicas, maximum autoscaling, deployment overlap, jobs, migrations, and administrators. Then restore it to an isolated environment at a chosen timestamp and measure until one real business query passes. Compare both results with the documented budget and recovery objective. Configuration without those two proofs is only intent.

## Looking Ahead

Relational modeling starts from normalized relationships and flexible queries. Chapter 100 starts from known access patterns and examines DynamoDB partition and sort keys, indexes, conditional writes, consistency, capacity, transactions, TTL, streams, and cache boundaries.

## References

- [Amazon RDS — What is Amazon RDS?](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Welcome.html)
- [Amazon RDS — Multi-AZ deployments](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZ.html)
- [Amazon RDS — Read replicas](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_ReadRepl.html)
- [Amazon RDS — Automated backups](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithAutomatedBackups.html)
- [Amazon RDS — Point-in-time recovery](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_PIT.html)
- [Amazon RDS — Parameter groups](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/parameter-groups-overview.html)
- [Amazon RDS — Maintaining a DB instance](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_UpgradeDBInstance.Maintenance.html)
- [Amazon RDS — Database authentication](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/database-authentication.html)
- [Amazon RDS — Monitoring](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_Monitoring.html)
- [Amazon RDS Proxy — Connection and failover use cases](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-proxy-best-practices.usage-scenarios.html)
- [Amazon Aurora — Cluster architecture](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Overview.html)
- [Amazon Aurora — Storage reliability](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Overview.StorageReliability.html)
- [Amazon Aurora — Replication and replicas](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Replication.html)
- [Amazon Aurora — Endpoints](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Overview.Endpoints.html)
- [Chapter 98 — EBS, EFS, and Choosing Cloud Storage](98-ebs-efs-and-choosing-cloud-storage.md)
