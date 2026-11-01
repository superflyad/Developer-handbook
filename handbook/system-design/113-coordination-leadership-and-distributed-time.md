# Chapter 113 — Coordination, Leadership, and Distributed Time

A worker acquires a 30-second lease, pauses for garbage collection, and resumes after the lease expired. Another worker now holds the lease. Both believe they may write because the first worker did not observe time passing while paused. The lock service behaved correctly; the protected resource still accepted a stale owner.

The central idea is:

> Distributed coordination is safe only when ownership is established by a proven agreement service and every protected effect can reject stale owners; clocks, timeouts, and “I still hold the lock” are observations, not authority.

## 1. Partial failure changes the reasoning model

On one machine, a process can often distinguish a returned call from a crashed process using shared kernel state. Across machines, silence is ambiguous:

- the peer may have crashed;
- the network may have dropped or delayed traffic;
- the peer may be paused;
- the response may be lost;
- the local machine may be partitioned;
- the peer may have completed the effect and moved on.

A timeout is evidence that a deadline passed without an observed response. It does not prove the remote action failed or the peer is dead.

Design every coordination protocol around unknown outcomes and overlapping beliefs. “Node A is down” should mean “the current membership or lease authority no longer grants A ownership,” not “we have not heard from A recently.”

## 2. Coordinate only when an invariant requires it

Coordination orders or excludes concurrent action. It is justified for requirements such as:

- one authoritative writer for a resource epoch;
- a globally unique allocation under one namespace;
- a configuration transition observed in one agreed order;
- membership change without two independent majorities;
- a transaction invariant spanning concurrent actors;
- failover where old and new owners could both cause harm.

Avoid coordination when operations commute, are idempotent, can be partitioned by stable ownership, or can merge safely. A global lock around all task updates destroys availability and throughput when per-task versions already protect the invariant.

Make the invariant and coordination scope explicit. “We need a leader” is incomplete until the leader's unique responsibility is named.

## 3. Separate safety from liveness

**Safety** means something bad never happens: two owners do not both commit for the same epoch, or two logs do not decide different values at one position.

**Liveness** means something good eventually happens: a leader is elected, a lock becomes available, or a command commits.

During a network partition, a system may preserve safety by refusing progress on one side. Weakening safety to remain writable can create split authority and require conflict resolution.

State which property wins for each operation. Access-policy changes and inventory allocation often prefer safety. Presence indicators may prefer availability and convergence.

## 4. Clocks do not provide a universal present

Machine clocks can differ because of oscillator drift, synchronization error, pause, manual adjustment, virtualization, leap handling, or network delay. Wall clocks can move forward or backward.

Use wall time for human timestamps, expiration contracts with stated uncertainty, and externally meaningful deadlines. Do not use it alone to decide which concurrent write is “latest” when losing one is harmful.

Use a monotonic clock for local elapsed durations and timeouts. A monotonic reading on one machine is not directly comparable with another machine's reading.

When a system offers bounded clock uncertainty as part of a formal contract, its algorithms can incorporate that interval. Ordinary synchronized clocks should not be treated as perfectly ordered.

## 5. Separate physical and logical order

Logical clocks describe causal or protocol order without claiming exact wall time.

A Lamport-style counter can ensure that if event A causally precedes B, A's logical timestamp is lower. The converse is not guaranteed: a lower number does not necessarily prove causality.

Vector-style metadata can distinguish some concurrent events from ordered ones at the cost of metadata growth and membership complexity.

Terms, epochs, log positions, entity versions, and fencing tokens are domain-specific logical order. They are often safer than timestamps for rejecting stale work.

Carry both when needed: wall time for observation and an epoch/version for authority.

## 6. A lease grants time-bounded permission

A lease is ownership that expires unless renewed through an authority. It differs from an indefinite lock because failure can release it without the old holder cooperating.

Define:

- lease scope and identity;
- granting authority and consistency guarantee;
- duration and renewal point;
- clock used to evaluate expiry;
- network and pause assumptions;
- behavior when renewal outcome is unknown;
- protected-resource fencing;
- cleanup and handoff.

A holder must stop initiating new work before local uncertainty reaches expiration. But local self-restraint is insufficient: a paused process can resume late, and packets sent before expiry can arrive afterward.

## 7. Fence stale owners at the resource

When granting ownership, issue a monotonically increasing fencing token:

```text
owner A receives token 41
lease expires
owner B receives token 42
protected resource records highest accepted token = 42
late write from A with 41 is rejected
```

The protected storage, API, device, or downstream service must compare the token atomically with the effect. A token checked only by the client is not fencing.

Fencing may be an epoch in a row condition, generation number in object metadata, or term in a replicated protocol. If the resource cannot reject stale owners, the lease cannot guarantee exclusive effects after pause or partition.

## 8. Distributed locks need a complete failure contract

A safe lock service must define:

- mutual exclusion scope;
- acquisition order or fairness if promised;
- lease or session semantics;
- owner identity and reentrancy;
- persistence and replication;
- behavior under partition and failover;
- stale-owner fencing;
- cancellation and timeout;
- lock loss notification;
- administrative recovery.

Do not build a distributed lock from “create a cache key if absent” unless the cache's consistency, failover, expiry, and fencing behavior satisfy the invariant. A best-effort mutex can be useful for duplicate-work reduction and unsafe for financial settlement.

Prefer a transactional constraint or partitioned single writer when that directly protects the rule.

## 9. Leader election chooses a role, not correctness

Leader election selects one participant to perform responsibilities such as sequencing a log, scheduling work, or reconciling desired state. Election alone does not make the leader's decisions durable, current, or accepted by protected resources.

Define:

- what only the leader may do;
- term or epoch identity;
- how followers reject stale terms;
- which state a candidate must have to become leader;
- how commands become committed;
- read consistency under leadership change;
- client redirection and retry;
- handoff and recovery.

Two processes can temporarily believe they are leader due to message delay. Safety comes from quorum/term rules and resource fencing, not the processes' beliefs.

## 10. Understand quorum intersection

For a fixed set of `N` voting members, a strict majority is:

```text
floor(N / 2) + 1
```

Any two strict majorities intersect in at least one member. Consensus protocols use this intersection with durable terms, votes, and log rules to prevent conflicting committed decisions.

Three voters tolerate one unavailable voter for progress; five tolerate two, assuming the protocol and failure model. Adding an even voter can increase quorum size without increasing failure tolerance.

Quorum count alone is not consensus. Voting rules, durable state, candidate freshness, log replication, membership transition, and state-machine application all matter.

## 11. Consensus orders agreed commands

Consensus protocols let a group agree on a sequence despite crash failures and network disruption within their assumptions. A replicated state machine applies the same committed commands in the same order.

Raft, for example, uses terms as logical time, elects at most one leader per term, replicates log entries, and commits through majority rules plus safety constraints. The paper is approachable; implementing it correctly through persistence, snapshots, membership changes, reads, and operational failures remains specialist work.

Use a maintained database, coordination service, or library with a clear consistency and failure contract. Do not implement consensus inside application business code to avoid a managed dependency.

## 12. Split brain is conflicting authority

Split brain occurs when separated participants both act as authoritative for the same scope. It can arise from unsafe failover, independent control planes, stale leases without fencing, or incorrect membership changes.

Detection after both sides accepted writes is not prevention. Recovery may require discarding, merging, compensating, or manually reconciling state.

Prevent it through quorum intersection, one authoritative membership, epochs, fencing, and fail-closed behavior for non-commutative effects. Document which side may progress under each partition shape.

## 13. Membership is part of the safety protocol

Adding or removing voters changes which sets form a quorum. A naive switch from old to new membership can let disjoint groups each form what they consider a majority.

Proven protocols use a safe transition such as joint agreement between old and new configurations or another formally specified approach.

Operators should use the coordination system's membership procedure, one change at a time where required, with backups, health evidence, and rollback guidance. Editing a configuration file on several nodes is not a safe membership protocol.

## 14. Failure detectors are suspicions

Heartbeats and timeouts produce suspicions based on observation. They cannot perfectly distinguish a failed node from a slow or partitioned one in an asynchronous network.

Tune detection from recovery objective and false-positive consequence. Faster suspicion can improve failover time and increase unnecessary elections or ownership churn.

Separate:

- suspected unavailable;
- removed from membership;
- lease expired;
- fenced from effects;
- repaired and eligible again.

Do not let a load balancer health check double as authority to promote a new database writer without the database's own failover protocol.

## 15. Election timeout is not lease duration

An election timeout determines when a participant suspects no current leader and starts an election. A lease duration defines a time-bounded permission. A client request deadline defines how long it waits.

These clocks interact but are not interchangeable. Setting them all to 30 seconds does not create a correct timing proof.

Record measurement source, uncertainty, renewal, and consequence for every timeout. Test pause, delayed packets, asymmetric partition, and clock adjustment.

## 16. Coordinate scheduling without double execution assumptions

Leader-elected schedulers can reduce duplicate scheduling, but failover can still overlap work:

1. old leader dispatches a job;
2. its acknowledgment is lost;
3. new leader takes over and dispatches again.

Jobs require stable execution identity, idempotency, claim/fencing at the target, and reconciliation. Leader election reduces competing decisions; it does not make external effects exactly once.

For long jobs, use a renewable claim with fencing and checkpoints. A worker that loses its claim must stop, and the result store must reject its late token.

## 17. Treat coordination storage as critical infrastructure

A coordination system often controls deployment, scheduling, membership, locks, or configuration. Its availability and integrity can affect the entire platform.

Own:

- authentication and least privilege;
- network isolation;
- odd-sized voter placement across failure domains;
- durable storage and tested backup/restore;
- compaction and quota;
- latency and leader-change monitoring;
- version compatibility and upgrades;
- membership changes;
- client session and retry behavior;
- disaster recovery and bootstrap trust.

Do not place large payloads or high-volume application events in a service intended for small coordination state.

## 18. Avoid making coordination a hot data path

Use coordination to establish ownership or commit small metadata, then perform ordinary work within that boundary. Acquiring a global lock for every request serializes throughput and makes the coordination service part of every latency objective.

Partition coordination by independent invariant scope. Cache read-only discovery cautiously with version/epoch validation. Batch ownership when safe.

If every operation requires consensus across regions, validate that the latency and availability tradeoff is actually required by the business invariant.

## 19. Handle session loss explicitly

Many coordination services tie ephemeral ownership to a session or lease. Connection interruption may leave the client uncertain whether the session remains valid.

On uncertainty:

- stop initiating protected effects;
- attempt only the documented renewal or recovery path;
- reacquire a new epoch rather than assuming continuity;
- make late in-flight effects carry their old fencing token;
- reconcile outcomes before retry.

A reconnect is not proof that the old ownership survived. Watch streams can compact or miss history; perform a fresh authoritative read when the contract requires it.

## 20. Design safe leader reads

A process that believes it is leader may be partitioned from the quorum and stale. Serving reads from it can violate a current-state guarantee.

Options include:

- quorum-confirmed or protocol linearizable reads;
- reads from committed log position with a current leadership check;
- follower reads labeled with bounded or unbounded staleness;
- session tokens requiring a minimum applied index.

Do not infer linearizable reads from “leader-based.” The implementation must prove current authority and applied state under its documented protocol.

## 21. Test pauses and partitions, not only crashes

Exercise:

- one node crash and restart;
- long process pause beyond lease expiry;
- one-way and asymmetric partitions;
- delayed and reordered packets;
- response loss after commit;
- clock step and drift where relevant;
- full disk or persistence failure;
- leader loss during write and read;
- membership change interrupted halfway;
- backup restore with stale identity;
- stale owner writing after a new epoch.

Verify safety invariants and accepted histories, not merely recovery time. A chaos test that only shows “the cluster became green again” can miss conflicting effects.

## 22. Observe coordination health

Monitor:

- current leader and term/epoch changes;
- election frequency and duration;
- commit and apply indexes;
- follower lag;
- quorum health and member reachability;
- lease renewal latency and failures;
- session expiration;
- lock wait and hold duration;
- rejected stale fencing tokens;
- storage quota, compaction, and snapshot age;
- client retry and unknown outcomes.

Alert on user-impacting inability to commit plus safety signals such as stale-owner attempts. Frequent successful elections are still instability.

## 23. Apply coordination to the task platform

Most task edits require no global leader: per-task optimistic versions and database transactions protect their invariants.

Coordination may be justified for:

- one active shard-migration owner per shard epoch;
- one scheduler generation dispatching a recurring job;
- safe search-index alias cutover;
- partition ownership among stream processors;
- membership of the underlying managed database or broker.

Each operation carries an epoch to the protected resource. A scheduler job also carries a stable job occurrence ID, because failover can redispatch even with safe leader election.

Use the database or managed coordination platform's primitives. Do not create a global task-system lock in the shared cache.

## 24. Encode a coordination contract

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class LeaseContract:
    scope: str
    authority: str
    duration_seconds: int
    renew_before_seconds: int
    monotonic_fencing_token: bool
    protected_resource_checks_token: bool

    def validate(self) -> None:
        if not self.scope.strip() or not self.authority.strip():
            raise ValueError("lease needs scope and authority")
        if not 0 < self.renew_before_seconds < self.duration_seconds:
            raise ValueError("lease renewal window is invalid")
        if not self.monotonic_fencing_token or not self.protected_resource_checks_token:
            raise ValueError("lease does not fence stale owners")


@dataclass(frozen=True)
class CoordinationContract:
    lease: LeaseContract
    invariant: str
    managed_consensus_primitive: bool
    quorum_members: int
    failure_tolerance: int
    safe_membership_change: bool
    session_loss_stops_effects: bool
    stale_leader_reads_prevented: bool
    pause_and_partition_tested: bool

    def validate(self) -> None:
        self.lease.validate()
        if not self.invariant.strip():
            raise ValueError("coordination has no named invariant")
        if not self.managed_consensus_primitive:
            raise ValueError("custom consensus is outside the application boundary")
        if self.quorum_members < 3 or self.quorum_members % 2 == 0:
            raise ValueError("voting set needs an appropriate odd size")
        if self.failure_tolerance > (self.quorum_members - 1) // 2:
            raise ValueError("claimed failure tolerance exceeds majority quorum")
        if not self.safe_membership_change:
            raise ValueError("membership transition can split authority")
        if not self.session_loss_stops_effects:
            raise ValueError("uncertain owner continues protected effects")
        if not self.stale_leader_reads_prevented:
            raise ValueError("stale leader can serve current reads")
        if not self.pause_and_partition_tested:
            raise ValueError("coordination lacks pause and partition evidence")
```

Executable tests exercise the contract:

```python
import unittest

from coordination_contract import CoordinationContract, LeaseContract


def valid_contract() -> CoordinationContract:
    lease = LeaseContract("shard migration", "managed coordinator", 30, 10, True, True)
    return CoordinationContract(
        lease, "one migration writer per shard epoch", True, 5, 2,
        True, True, True, True,
    )


class CoordinationContractTests(unittest.TestCase):
    def test_complete_contract_is_accepted(self) -> None:
        valid_contract().validate()

    def test_invalid_renewal_window_is_rejected(self) -> None:
        contract = valid_contract()
        bad = LeaseContract("shard", "coordinator", 30, 30, True, True)
        with self.assertRaisesRegex(ValueError, "renewal"):
            CoordinationContract(bad, contract.invariant, True, 5, 2,
                                 True, True, True, True).validate()

    def test_unfenced_lease_is_rejected(self) -> None:
        contract = valid_contract()
        fields = {**contract.lease.__dict__, "protected_resource_checks_token": False}
        with self.assertRaisesRegex(ValueError, "fence"):
            CoordinationContract(LeaseContract(**fields), contract.invariant, True,
                                 5, 2, True, True, True, True).validate()

    def test_custom_consensus_is_rejected(self) -> None:
        contract = valid_contract()
        fields = {**contract.__dict__, "managed_consensus_primitive": False}
        with self.assertRaisesRegex(ValueError, "custom consensus"):
            CoordinationContract(**fields).validate()

    def test_even_voting_set_is_rejected(self) -> None:
        contract = valid_contract()
        fields = {**contract.__dict__, "quorum_members": 4, "failure_tolerance": 1}
        with self.assertRaisesRegex(ValueError, "odd"):
            CoordinationContract(**fields).validate()

    def test_impossible_failure_tolerance_is_rejected(self) -> None:
        contract = valid_contract()
        fields = {**contract.__dict__, "failure_tolerance": 3}
        with self.assertRaisesRegex(ValueError, "exceeds"):
            CoordinationContract(**fields).validate()

    def test_unsafe_membership_change_is_rejected(self) -> None:
        contract = valid_contract()
        fields = {**contract.__dict__, "safe_membership_change": False}
        with self.assertRaisesRegex(ValueError, "split authority"):
            CoordinationContract(**fields).validate()

    def test_session_loss_must_stop_effects(self) -> None:
        contract = valid_contract()
        fields = {**contract.__dict__, "session_loss_stops_effects": False}
        with self.assertRaisesRegex(ValueError, "uncertain owner"):
            CoordinationContract(**fields).validate()

    def test_partition_evidence_is_required(self) -> None:
        contract = valid_contract()
        fields = {**contract.__dict__, "pause_and_partition_tested": False}
        with self.assertRaisesRegex(ValueError, "partition evidence"):
            CoordinationContract(**fields).validate()


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

Save the blocks as `coordination_contract.py` and `test_coordination_contract.py`, then run:

```bash
python -m unittest -v test_coordination_contract.py
```

A production review should use the managed system's documented guarantees, inspect lease and transaction code, prove fencing at the protected resource, exercise session loss and partitions, rehearse membership changes and restore, and verify histories rather than relying on role labels.

## 25. Review distributed coordination

```text
invariant, coordination scope, alternatives, safety, liveness, and consequence:
partial failures, unknown outcomes, retries, pause, and overlapping beliefs:
wall clock, monotonic clock, uncertainty, drift, step, and comparison scope:
logical term, epoch, position, version, causality, and authority meaning:
lease grant, duration, renewal, uncertainty, expiration, handoff, and cleanup:
fencing token generation, monotonicity, atomic resource check, and rejection:
lock exclusion, owner, session, persistence, partition, failover, and recovery:
leader responsibility, term, candidate state, commit, reads, redirect, and handoff:
voter count, majority, tolerated failures, placement, and quorum availability:
consensus implementation, persistence, replication, snapshots, and application:
split-brain prevention, conflict consequence, and fail-closed partition behavior:
old/new membership transition, procedure, interruption, rollback, and evidence:
heartbeat, suspicion, removal, lease expiry, fencing, and rejoin distinction:
scheduler generation, occurrence identity, idempotency, claim, and reconcile:
coordination security, storage, backup, restore, compaction, quota, and upgrade:
session loss, watch gap, authoritative reread, reacquisition, and late effects:
read authority, quorum confirmation, applied index, token, and stale labeling:
crash, pause, asymmetric partition, delay, clock, disk, election, and membership tests:
leader churn, term, commit/apply lag, quorum, leases, locks, fences, and incidents:
```

## Common Misconceptions

- “A timeout proves the other node failed.” It proves only that no response was observed by a deadline.
- “Synchronized clocks totally order writes.” Clock error and concurrency make that unsafe without a stronger contract.
- “A lease prevents two workers from acting.” A paused stale holder can resume unless effects are fenced.
- “The lock service guarantees safety.” The protected resource must reject stale tokens.
- “Leader election means exactly one process believes it is leader.” Beliefs can overlap; terms and commit rules protect effects.
- “A majority vote is consensus.” Durable terms, log rules, membership, and state application are also required.
- “Five voters are always better than three.” They cost more coordination and tolerate two failures instead of one.
- “Split brain can be repaired automatically.” Conflicting non-commutative effects may require loss or manual reconciliation.
- “Health checks can promote a writer.” Promotion needs the data system's authority protocol.
- “Implementing Raft from the paper is straightforward.” Production persistence, reads, snapshots, membership, and operations are specialist work.

## Core Computer Science Concept

This chapter applies **partial failure, logical clocks, leases, fencing, quorum intersection, leader epochs, replicated state machines, and consensus**. Safety comes from intersecting durable knowledge and monotonic authority, not from synchronized beliefs or absence of recent messages.

## Engineering Connections

- Time and scheduling build on Chapters 43, 44, 61, 74, and 76.
- Consistency and ownership extend Chapters 100, 109, 110, and 112.
- Kubernetes leases connect to Chapter 88's controller model.
- Infrastructure and recovery apply Chapters 91, 103, and 105.
- Chapter 114 uses these failure boundaries to contain retries and cascading failure.

## From the Field

A batch worker holds a cache-based lock with a 60-second TTL. It pauses for two minutes, another worker acquires the key, and both write an export under the same name. The last completion wins and the manifest references mixed data. A monotonically increasing export epoch checked by the manifest store would reject the stale worker even after its pause.

## Engineering Review

### What problem does this solve?

It provides safe exclusive ownership and agreed ordering when independent machines can pause, partition, fail, recover, and hold conflicting beliefs.

### Why was it designed this way?

Coordination safety must survive late actors, not merely elect a current actor. Fencing connects the coordinator's order to the resource that can cause harm.

### When should I use it?

Use coordination for non-commutative shared invariants, writer failover, partition ownership, schedulers, membership, and ordered configuration transitions.

### When should I avoid it?

Avoid global coordination when stable partitioning, idempotency, commutative operations, or explicit conflict resolution satisfies the requirement.

### How does this make me a better engineer?

It teaches you to treat timeouts as suspicion, separate clocks from authority, require fencing, and recognize consensus as a managed infrastructure boundary.

### How does this reduce waste?

It avoids unsafe cache locks, global serialization, clock-based lost writes, duplicate schedulers, split-brain recovery, homegrown consensus, oversized voting groups, and leader churn mistaken for health.

## Handbook Principle #113

> Distributed ownership is real only when a quorum-backed epoch is enforced by the resource that receives the effect; every unfenced lease is a stale writer waiting to happen.

## Practical Observation

Find one distributed lock or leader election in your system. Pause the holder beyond expiration, let another owner acquire, then resume the first. If the protected resource accepts the first holder's next write, the system has coordination theater rather than exclusion.

## Phase 2 Complete

Chapters 109–113 connect capacity, partitioning, consistency, caching, messaging, and coordination. The design method can now scale work and state without losing sight of the invariants, stale copies, delayed effects, and authority transitions introduced by distribution.

## Looking Ahead

Chapter 114 turns these failure mechanisms into containment design: deadlines, bounded retries, circuit breakers, bulkheads, load shedding, graceful degradation, redundancy, recovery objectives, and controlled failure experiments.

## References

- [Ongaro and Ousterhout — In Search of an Understandable Consensus Algorithm](https://raft.github.io/raft.pdf)
- [Raft project — Publications and implementations](https://raft.github.io/)
- [Apache ZooKeeper — Recipes and Solutions](https://zookeeper.apache.org/doc/current/recipes.html)
- [etcd — Concurrency API](https://etcd.io/docs/latest/dev-guide/api_concurrency_reference_v3/)
- [Kubernetes — Leases](https://kubernetes.io/docs/concepts/architecture/leases/)
- [Kubernetes — Coordinated leader election](https://kubernetes.io/docs/concepts/cluster-administration/coordinated-leader-election/)
- [Google Research — Spanner: Google's Globally-Distributed Database](https://research.google/pubs/spanner-googles-globally-distributed-database/)
- [Chapter 110 — Consistency, Transactions, and Concurrent Change](110-consistency-transactions-and-concurrent-change.md)
- [Chapter 112 — Messaging, Events, and Asynchronous Workflows](112-messaging-events-and-asynchronous-workflows.md)
