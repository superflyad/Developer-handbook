# Chapter 110 — Consistency, Transactions, and Concurrent Change

Two operators read that one reviewer remains on call. Each independently removes a different reviewer. Both writes succeed because they update different rows, leaving nobody on call. Every row update was atomic; the business invariant still failed.

Correct concurrency begins with the invariant, not the database's isolation-level name.

The central idea is:

> State the histories the business allows, place each invariant inside an enforceable coordination boundary, and use weaker or asynchronous consistency only where stale or conflicting observations have an owned consequence.

## 1. Correctness is a property of histories

A sequential function can be correct for every input and still fail when operations overlap. A concurrent history includes invocations, reads, writes, commits, aborts, and observed results in some partial order.

For task assignment, possible histories include:

```text
A reads task version 17, assignee = Mia
B reads task version 17, assignee = Mia
A assigns Noor and commits version 18
B assigns Luis and commits version 18 from stale state
```

If B overwrites A without detecting the stale version, the system has a lost update. Whether last writer wins is correct depends on the domain. It may be acceptable for a derived presence signal and unacceptable for a task assignment, account balance, or access-policy change.

Model operations from the client's observation boundary. A database commit that the caller never observes creates an unknown outcome and possible retry, as Chapter 107 described.

## 2. Translate invariants into forbidden histories

An invariant is a property that must hold across accepted state transitions. Make its scope and time explicit:

- a task belongs to exactly one project at all times;
- a task version increases for every accepted mutation;
- only an active project member can be assigned at commit time;
- at least one authorized project owner remains after any change;
- an idempotency key identifies at most one request fingerprint in its retention window;
- available inventory never falls below zero for accepted reservations.

Then name the forbidden concurrent history. “At least one owner” forbids two transactions that each observe two owners and remove a different one. “Inventory never below zero” forbids multiple reservations that all approve against the same prior quantity.

The enforcement boundary must include every fact used to decide the invariant. Checking in application code and later issuing unrelated writes does not make the check atomic.

## 3. Distinguish atomicity, isolation, consistency, and durability

In the ACID vocabulary:

- **atomicity** means a transaction's included effects commit together or not at all;
- **consistency** means transactions are intended to preserve declared rules;
- **isolation** constrains how concurrent transactions can observe and affect one another;
- **durability** means committed effects survive the promised failures.

Atomicity does not prevent write skew between facts outside the transaction's conflict detection. Durability does not guarantee a stale replica has observed the commit. “Consistent” in ACID does not name a distributed read model.

Use exact terms: unique constraint, conditional update, serializable transaction, linearizable register, read-your-writes session, or bounded-stale projection.

## 4. Know the common anomalies

Concurrency mechanisms are easier to evaluate through anomalies:

- **dirty read:** observe data from a transaction that may abort;
- **dirty write:** overwrite another uncommitted write;
- **nonrepeatable read:** reread an item and see another committed value;
- **phantom:** repeat a predicate query and see a changed matching set;
- **lost update:** a stale write overwrites a concurrent effect;
- **write skew:** transactions read a shared condition and make disjoint writes that jointly violate it;
- **fractured read:** observe parts of a multi-object update from different points in time;
- **serialization anomaly:** committed results cannot match any serial execution.

Do not choose an isolation level from its reassuring name. Engine implementations differ, and application behavior depends on exact statements, predicates, constraints, and retry logic. Test the anomaly that threatens the invariant.

## 5. Use constraints as concurrency mechanisms

Database constraints are not only input validation. When enforced at commit under the engine's contract, they coordinate concurrent change:

- primary and unique keys prevent duplicate identities;
- foreign keys preserve declared references;
- check constraints preserve row-local predicates;
- exclusion or equivalent constraints can prevent overlapping ranges;
- conditional writes compare expected state atomically;
- atomic increments avoid read-modify-write races for supported counters.

Prefer a declarative constraint when it exactly represents the invariant. It remains active across all writers, including jobs and administrative tools.

Not every cross-row or cross-service rule fits a simple constraint. A unique partial representation, materialized ownership record, explicit lock, or serializable transaction may bring the invariant into an enforceable boundary.

## 6. Make read-modify-write one conditional transition

This unsafe pattern separates decision from effect:

```text
read version 17
compute change
write new state without checking version
```

Use compare-and-swap or optimistic versioning:

```text
update task
set assignee = Noor, version = 18
where task_id = T and version = 17
```

Exactly one concurrent writer can match version 17. A zero-row update is a conflict, not success. The caller can fetch current state, merge if the domain supports it, or ask the user to resolve.

DynamoDB condition expressions and relational `WHERE version = ?` updates implement the same principle within their scopes. The version check and write must be one atomic operation.

## 7. Treat optimistic concurrency as conflict detection

Optimistic control assumes conflicts are uncommon enough to detect at commit rather than block early. It works well for short edits, independent aggregates, and interactive workflows where a conflict can be surfaced.

Define:

- version scope and initial value;
- fields included in the comparison;
- server behavior on conflict;
- whether automatic merge is safe;
- retry limit and backoff;
- user-visible resolution;
- idempotency interaction.

Blindly retrying the full business decision against new state can be wrong. A retry may need to recompute price, authorization, inventory, or policy. A user who chose “replace Mia with Noor” may not intend to replace Luis after a concurrent edit.

High contention turns optimistic control into repeated wasted work. Measure conflict rate and retry latency.

## 8. Use pessimistic control when waiting is safer than conflict

Pessimistic locking reserves data or a logical resource before acting. It can simplify highly contended transitions but creates wait, deadlock, failure-recovery, and availability concerns.

Define:

- lock scope and ordering;
- acquisition timeout and cancellation;
- transaction duration;
- deadlock handling;
- owner failure and release;
- lease or fencing behavior if distributed;
- observability and administrative recovery.

Keep database transactions short and avoid holding locks across user input or slow network calls. Calling an external payment provider while holding a row lock couples an unbounded dependency to database progress.

A process mutex coordinates only one process. A distributed lock is safe only under its failure and fencing contract; Chapter 113 develops that boundary.

## 9. Understand isolation through permitted observations

SQL isolation names describe classes of allowed histories, but exact behavior is engine-specific. PostgreSQL, for example, documents:

- Read Committed uses a new committed snapshot per statement;
- Repeatable Read holds a transaction snapshot and can still permit serialization anomalies;
- Serializable rejects a pattern that cannot match a serial execution.

Serializable transactions may abort and require retry. PostgreSQL specifically requires retrying the complete transaction logic after a serialization failure, not only the last SQL statement.

A stronger level is not a substitute for constraints, short transactions, idempotent external effects, or correct retry. It also does not coordinate a separate service or database outside the transaction.

## 10. Recognize write skew

Suppose reviewers A and B are both on call. Two transactions run:

```text
transaction 1: read A and B; set A off call
transaction 2: read A and B; set B off call
```

They write different rows, so simple row-conflict detection may allow both. The final state violates “at least one reviewer remains.” This is write skew.

Possible remedies include:

- serializable isolation with complete-transaction retry;
- lock a common project or schedule row;
- represent the scarce permission through one constrained aggregate;
- use an atomic conditional operation over the invariant scope;
- serialize commands through one owner.

Do not fix it with a post-commit alert if the invariant must never be false. Detection and compensation are appropriate only when temporary violation is explicitly allowed.

## 11. Separate serializability from real-time order

Serializability says committed transactions have an effect equivalent to some serial order. That order need not respect wall-clock completion between separate transactions.

Linearizability is commonly described for operations on an object: each operation appears atomic in an order consistent with real-time precedence. If write A completes before read B begins, B cannot return a value older than A under the same linearizable object contract.

Strict serializability combines transactional serializability with real-time constraints. These are strong guarantees with coordination and availability consequences under network partitions.

Do not claim “strong consistency” when the actual contract is per-item conditional writes, transaction serializability, leader reads, or session stickiness. Name the scope.

## 12. Define replica read behavior

Replication creates multiple observations of state. A read replica may lag the writer, and lag is a distribution rather than one constant.

For each read path, define:

- replica or leader routing;
- consistency option and object scope;
- expected and maximum staleness if bounded;
- behavior after a write;
- failover behavior;
- monitoring and fallback;
- whether authorization may use it.

DynamoDB, for example, documents eventually and strongly consistent reads for tables and local secondary indexes, while global secondary indexes are eventually consistent. The service name alone does not tell a caller which guarantee a particular read used.

Never make a security or uniqueness decision from a replica whose permitted lag can invalidate it unless the system has another enforcing boundary.

## 13. Provide session guarantees where journeys need them

Users often need guarantees weaker than global linearizability but stronger than arbitrary eventual reads:

- **read-your-writes:** a session observes its completed writes;
- **monotonic reads:** later reads do not go backward;
- **monotonic writes:** one actor's writes apply in order;
- **writes-follow-reads:** a write is ordered after state the actor observed.

Implementations may use leader routing, sticky replica choice, commit tokens, version-aware reads, causal metadata, or waiting until a replica reaches a required position.

State token scope and expiration. A token from one partition may not order another. If waiting would exceed the deadline, return an explicit unavailable or stale result rather than silently violating the promised journey.

## 14. Use staleness only with a consequence model

Eventual consistency means replicas or projections converge when updates stop and delivery continues. It does not specify how stale a read can be, whether reads go backward, or how conflicts resolve.

For a stale-tolerant path, record:

- authoritative source and projection;
- lag SLI and objective;
- source version carried with the result;
- behavior when lag exceeds the objective;
- user-visible freshness indication where relevant;
- rebuild and reconciliation;
- decisions forbidden on stale data.

Search results may be five seconds stale, but opening a task should reauthorize against current state. Analytics may lag an hour, but billing finalization might require an authoritative cutoff snapshot.

## 15. Make conflict resolution domain-specific

Multi-writer or disconnected systems can produce concurrent versions. Resolution policies include:

- reject and require explicit merge;
- last writer wins under a trusted ordering;
- field-level merge;
- set union or intersection;
- maximum or minimum;
- additive counter;
- domain-specific compensation;
- conflict-free replicated data type where its algebra fits.

Last writer wins discards data and depends on ordering. Wall clocks can be wrong, equal, or manipulated. It may fit an ephemeral presence indicator and not a payment, access grant, or task assignment.

Automatic merge is safe only when operations commute or the merged state preserves invariants. Merging two individually valid policy documents can create excessive permission.

## 16. Distinguish commutativity from idempotency

An operation is idempotent if repeating it has the same effect as applying it once. Two operations commute if applying them in either order produces the same result.

```text
set status = CLOSED       idempotent, may not commute with reopen
add member X to a set     idempotent and often commutative
increment count by 1      not idempotent, increments commute with each other
replace assignee          idempotent per value, competing replacements do not commute
```

These properties inform retry, reordering, batching, and merge, but business preconditions still matter. Replaying “close task” after it was reopened may be technically idempotent and semantically wrong without an expected version.

## 17. Keep external effects outside transaction illusions

A local database transaction cannot atomically commit an arbitrary email, shipment, payment provider call, and message broker effect.

Use patterns with explicit recovery:

- transactional outbox for local state plus publication intent;
- idempotency key at the external provider;
- operation-status lookup after timeout;
- inbox or deduplication at consumers;
- compensation when the business effect can be reversed;
- reconciliation when outcome remains uncertain.

Do not hold a database transaction open while waiting for an external system to simulate atomicity. A process crash can still occur between the external effect and local commit.

## 18. Put authorization in the commit decision

Authorization can change concurrently. Checking membership, waiting, and then writing may allow a removed member to commit after revocation.

Determine the required semantics:

- authorization at request start;
- authorization at commit;
- revocation effective for new operations only;
- cancellation of in-flight work;
- lease or capability valid until expiry.

For high-consequence operations, bring the authorization version or membership predicate into the conditional write or transaction. For long workflows, record the authorized intent and reauthorize later steps according to policy.

Stale caches and replicas must not silently weaken the stated revocation objective.

## 19. Design counters and quotas carefully

A single atomic counter gives a clear total but can become a hotspot. Sharded counters improve write throughput but produce approximate or delayed totals unless coordinated on read.

Quotas and inventory often require more than a counter:

- scope and reset period;
- reservation versus consumption;
- atomic admission threshold;
- expiration and release;
- retries and duplicate identity;
- transfer between partitions;
- negative and overflow prevention;
- reconciliation with authoritative events.

Approximation is suitable for dashboards and autoscaling hints. Admission, billing, and scarce inventory need a contract that prevents or deliberately bounds oversubscription.

## 20. Handle transaction retries as new executions

Serialization failures, deadlocks, conditional conflicts, and transient transport failures may be retryable. A retry reruns logic against potentially changed state.

Define:

- which errors are retryable;
- complete transaction boundary;
- maximum attempts and total deadline;
- randomized backoff;
- idempotency for external effects;
- recomputation of authorization and derived values;
- conflict and exhaustion response;
- metrics by operation and cause.

Never retry an arbitrary transaction closure that sends email, mutates process-global state, or consumes a one-time token unless those effects are outside or independently idempotent.

High retry rate is contention evidence, not success. Reduce invariant scope, improve access order, serialize a hotspot, or change the product operation.

## 21. Test histories, not only final happy paths

Concurrency tests should coordinate operations to exercise dangerous interleavings:

- two stale updates to one version;
- insert races against uniqueness;
- predicate reads followed by disjoint writes;
- lock acquisition in opposite orders;
- commit success with lost response and retry;
- writer followed by replica read;
- failover during transaction outcome;
- duplicate and out-of-order event application;
- authorization revocation during an operation.

Check invariant preservation and returned results, not merely that calls completed. Run against the exact engine, isolation, schema, driver, and topology used in production.

Distributed consistency claims require fault testing with partitions, pauses, clock disturbance where relevant, and history analysis. A unit test cannot prove a deployed database's consistency model.

## 22. Observe correctness signals

Monitor:

- conditional and serialization conflict rate;
- complete-transaction retry rate and exhaustion;
- lock wait and deadlock;
- transaction duration;
- replica and projection lag distributions;
- read routing and consistency mode;
- invariant-check and reconciliation findings;
- duplicate suppression and idempotency expiry;
- compensation and unknown outcomes;
- user-visible stale or conflict responses.

An invariant violation requires incident treatment even if automatic repair succeeds. Repair reduces harm but does not explain how invalid state was accepted.

Avoid high-cardinality metric labels for object IDs. Preserve bounded aggregates and correlated structured evidence for investigation.

## 23. Map consistency to the task system

One defensible contract is:

- task edits use an expected task version and reject stale writes;
- project membership and owner-count changes use one serializable or explicitly locked invariant boundary;
- membership authorization is current at the protected commit point;
- task search is a versioned projection allowed to lag five seconds;
- opening a search hit reauthorizes and reads authoritative task state;
- notifications are at-least-once side effects deduplicated by event identity;
- analytics is eventually consistent and forbidden for authorization or billing finality;
- interactive sessions get read-your-writes through writer routing or commit tokens.

These choices are not one global consistency level. They are operation-specific guarantees derived from consequences.

## 24. Encode an invariant-to-mechanism review

The following model requires every invariant to have a scope, mechanism, and concurrency test.

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class InvariantContract:
    name: str
    scope: str
    mechanism: str
    stale_reads_allowed: bool
    stale_read_consequence: str
    concurrent_history_tested: bool

    def validate(self) -> None:
        if not all((self.name.strip(), self.scope.strip(), self.mechanism.strip())):
            raise ValueError("invariant needs name, scope, and mechanism")
        if self.stale_reads_allowed and not self.stale_read_consequence.strip():
            raise ValueError("stale reads need a consequence model")
        if not self.concurrent_history_tested:
            raise ValueError("invariant lacks a concurrent-history test")


@dataclass(frozen=True)
class ConcurrencyPlan:
    invariants: tuple[InvariantContract, ...]
    expected_version_required: bool
    complete_transaction_retry: bool
    retry_side_effects_idempotent: bool
    replica_read_contract: str
    read_your_writes: bool
    reconciliation_defined: bool
    authorization_checked_at_commit: bool

    def validate(self) -> None:
        if not self.invariants:
            raise ValueError("concurrency plan needs invariants")
        for invariant in self.invariants:
            invariant.validate()
        if not self.expected_version_required:
            raise ValueError("mutable aggregate needs stale-write detection")
        if self.complete_transaction_retry and not self.retry_side_effects_idempotent:
            raise ValueError("transaction retry can duplicate side effects")
        if not self.replica_read_contract.strip():
            raise ValueError("replica read consistency is undefined")
        if not self.read_your_writes:
            raise ValueError("interactive journey lacks read-your-writes")
        if not self.reconciliation_defined:
            raise ValueError("derived state needs reconciliation")
        if not self.authorization_checked_at_commit:
            raise ValueError("authorization can become stale before commit")
```

Executable tests exercise the review:

```python
import unittest

from concurrency_plan import ConcurrencyPlan, InvariantContract


def valid_plan() -> ConcurrencyPlan:
    invariant = InvariantContract(
        "at least one project owner", "project membership",
        "serializable transaction with complete retry", False, "", True,
    )
    return ConcurrencyPlan(
        (invariant,), True, True, True,
        "authoritative reads current; search may lag five seconds",
        True, True, True,
    )


class ConcurrencyPlanTests(unittest.TestCase):
    def test_complete_plan_is_accepted(self) -> None:
        valid_plan().validate()

    def test_unscoped_invariant_is_rejected(self) -> None:
        plan = valid_plan()
        bad = InvariantContract("owner remains", "", "serializable", False, "", True)
        fields = {**plan.__dict__, "invariants": (bad,)}
        with self.assertRaisesRegex(ValueError, "scope"):
            ConcurrencyPlan(**fields).validate()

    def test_untested_history_is_rejected(self) -> None:
        plan = valid_plan()
        fields = {**plan.invariants[0].__dict__, "concurrent_history_tested": False}
        with self.assertRaisesRegex(ValueError, "history"):
            ConcurrencyPlan((InvariantContract(**fields),), True, True, True,
                            plan.replica_read_contract, True, True, True).validate()

    def test_stale_read_without_consequence_is_rejected(self) -> None:
        plan = valid_plan()
        fields = {**plan.invariants[0].__dict__, "stale_reads_allowed": True}
        with self.assertRaisesRegex(ValueError, "consequence"):
            ConcurrencyPlan((InvariantContract(**fields),), True, True, True,
                            plan.replica_read_contract, True, True, True).validate()

    def test_blind_aggregate_write_is_rejected(self) -> None:
        plan = valid_plan()
        fields = {**plan.__dict__, "expected_version_required": False}
        with self.assertRaisesRegex(ValueError, "stale-write"):
            ConcurrencyPlan(**fields).validate()

    def test_nonidempotent_retry_effect_is_rejected(self) -> None:
        plan = valid_plan()
        fields = {**plan.__dict__, "retry_side_effects_idempotent": False}
        with self.assertRaisesRegex(ValueError, "duplicate"):
            ConcurrencyPlan(**fields).validate()

    def test_missing_replica_contract_is_rejected(self) -> None:
        plan = valid_plan()
        fields = {**plan.__dict__, "replica_read_contract": ""}
        with self.assertRaisesRegex(ValueError, "replica"):
            ConcurrencyPlan(**fields).validate()

    def test_stale_authorization_is_rejected(self) -> None:
        plan = valid_plan()
        fields = {**plan.__dict__, "authorization_checked_at_commit": False}
        with self.assertRaisesRegex(ValueError, "authorization"):
            ConcurrencyPlan(**fields).validate()


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

Save the blocks as `concurrency_plan.py` and `test_concurrency_plan.py`, then run:

```bash
python -m unittest -v test_concurrency_plan.py
```

A production review should test the actual engine and isolation behavior, inspect constraints and conditional statements, inject dangerous interleavings, measure conflicts and lag, rehearse failover, and verify every external effect's idempotency or reconciliation path.

## 25. Review consistency and concurrent change

```text
business invariant, fact set, time boundary, and forbidden histories:
atomicity, isolation, durability, read consistency, and exact scope:
dirty read/write, nonrepeatable, phantom, lost update, skew, and fracture:
primary, unique, foreign, check, exclusion, condition, and counter constraints:
expected version, comparison scope, conflict, merge, user resolution, and retry:
lock scope, order, wait, timeout, deadlock, owner failure, lease, and fencing:
engine, isolation, statements, predicates, serialization failure, and full retry:
linearizable object, serializable transaction, strict order, and real-time need:
leader/replica routing, lag distribution, stale bound, failover, and fallback:
read-your-writes, monotonic reads/writes, causal token, scope, and expiration:
projection authority, source version, lag SLI, exceeded behavior, and rebuild:
conflict policy, commutativity, idempotency, discarded data, and invariants:
outbox, provider key, status lookup, inbox, compensation, and reconciliation:
authorization observation, commit check, revocation objective, and stale caches:
counter or quota scope, reservation, threshold, expiry, sharding, and reconcile:
retryable errors, complete boundary, attempts, deadline, backoff, and effects:
history tests, engine topology, partitions, failover, response loss, and replay:
conflicts, retries, lock waits, lag, invariant findings, and incident ownership:
```

## Common Misconceptions

- “Atomic row updates preserve the business invariant.” Cross-row predicates can still suffer write skew.
- “Repeatable Read is always stronger than Snapshot Isolation.” Model names and allowed histories are not always totally ordered.
- “Serializable means no transaction fails.” Correct implementations may abort a transaction that must be retried completely.
- “Linearizable and serializable are synonyms.” One concerns real-time object operations; the other concerns transaction-equivalent order.
- “A committed write is immediately visible everywhere.” Replica and index read paths can have different guarantees.
- “Eventual consistency means a few seconds stale.” It gives no universal time bound by itself.
- “Last writer wins merges conflicts.” It chooses one value and discards another.
- “A distributed lock makes the operation safe.” Scope, expiry, owner failure, and fencing determine safety.
- “Retrying a transaction is harmless.” Application and external effects may repeat.
- “Authorization at request start is always sufficient.” Revocation may need to participate in commit.

## Core Computer Science Concept

This chapter applies **concurrent histories, serial equivalence, atomic compare-and-swap, mutual exclusion, optimistic validation, partial orders, consistency models, and commutative operations**. Correctness depends on which interleavings are admitted and observed, not on whether individual functions look sequentially correct.

## Engineering Connections

- Process races and locks extend Chapters 4, 42, 43, 74, and 76.
- Transactions and constraints build on Chapters 15, 99, 100, and 108.
- Retry and unknown outcomes extend Chapters 70, 74, 101, and 107.
- Replication and partitions follow Chapter 109's scale model.
- Chapter 111 applies these guarantees specifically to cached copies.

## From the Field

Two administrators each see two project owners and remove the other owner. The updates touch different membership rows, so both commit under a snapshot-style isolation level. The project has no owner and no one can repair permissions through the normal interface. A shared project lock, constrained ownership aggregate, or serializable transaction with complete retry would have made the cross-row invariant visible to concurrency control.

## Engineering Review

### What problem does this solve?

It maps each business invariant to an enforceable transaction, constraint, conditional update, lock, consistency guarantee, or explicit asynchronous repair boundary.

### Why was it designed this way?

Isolation names and “strong consistency” labels hide scope. Forbidden histories reveal whether a mechanism actually protects the business rule.

### When should I use it?

Use it for concurrent writes, replicas, caches, projections, multi-region operation, retries, quotas, authorization changes, and any workflow spanning more than one atomic boundary.

### When should I avoid it?

Do not require global coordination for data whose stale or conflicting states are harmless and repairable. Document that consequence and use the weakest sufficient guarantee.

### How does this make me a better engineer?

It teaches you to reason in histories, distinguish consistency scopes, detect write skew, and treat retries and authorization as part of the transaction contract.

### How does this reduce waste?

It avoids unnecessary global coordination, silent lost updates, retry storms, stale authorization, invalid quota admission, inappropriate last-writer-wins, and repairs that mask recurring invariant violations.

## Handbook Principle #110

> Protect each invariant at the smallest boundary that contains all facts needed to decide it, and weaken consistency only with an explicit stale or conflict consequence.

## Practical Observation

Choose one rule currently “checked in code.” Run two copies of the operation from the same initial state and make them commit in both orders or concurrently. If both can succeed while the rule becomes false, the check is not an invariant mechanism.

## Looking Ahead

Caches are intentionally stale replicas with eviction and failure behavior. Chapter 111 treats cache keys, invalidation, stampedes, negative entries, write strategies, and bypass as consistency decisions rather than free performance.

## References

- [PostgreSQL — Transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html)
- [PostgreSQL — Serialization failure handling](https://www.postgresql.org/docs/current/mvcc-serialization-failure-handling.html)
- [Jepsen — Consistency models](https://jepsen.io/consistency/models)
- [Jepsen — Linearizability](https://jepsen.io/consistency/models/linearizable)
- [Amazon DynamoDB — Read consistency](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.ReadConsistency.html)
- [Amazon DynamoDB — Optimistic locking](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/BestPractices_OptimisticLocking.html)
- [Amazon DynamoDB — Transactions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transactions.html)
- [Chapter 107 — Interfaces, Contracts, and Evolution](107-interfaces-contracts-and-evolution.md)
- [Chapter 109 — Capacity, Partitioning, and Horizontal Scale](109-capacity-partitioning-and-horizontal-scale.md)
