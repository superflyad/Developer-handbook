# Chapter 112 — Messaging, Events, and Asynchronous Workflows

A producer commits an order and crashes before publishing its event. A worker charges a card, loses its acknowledgment, and receives the message again. An operator replays six months of events into a consumer whose idempotency records last seven days. Every component can behave according to its local contract while the business outcome is missing or duplicated.

The central idea is:

> Asynchronous design moves work across time and ownership boundaries; correctness therefore depends on durable intent, explicit delivery and ordering scope, idempotent effects, bounded backlog, and recoverable partial progress.

## 1. Use asynchrony for a named reason

Messaging can:

- buffer bursts and level load;
- decouple producer availability from consumer availability;
- distribute work among competing consumers;
- fan out facts to independent consumers;
- preserve a replayable history;
- coordinate long-running workflows;
- isolate slow or optional side effects.

It also adds delay, duplicate delivery, reordering, retention limits, schema evolution, backlog, poison messages, and harder end-to-end observation.

Do not insert a broker merely to make a diagram “event driven.” State which synchronous dependency or workload problem it solves and which business result now completes later.

## 2. Separate commands, events, and replies

A **command** asks one logical owner to attempt an action:

```text
ReserveInventory(order_id, items, expected_catalog_version)
```

An **event** reports a fact the publisher considers committed:

```text
InventoryReserved(order_id, reservation_id, inventory_version)
```

A **reply** reports the outcome of an earlier request and correlates to it.

Commands can be rejected, expire, or produce one result. Events may interest zero or many consumers and should not instruct a particular downstream implementation. Naming a command `EmailSentEvent` before the email is sent hides the real state transition.

Every message needs an owner for its meaning, schema, retention, security, and support.

## 3. Choose queue, topic, or log semantics deliberately

A work queue commonly distributes each message to one member of a competing consumer group. It fits tasks where parallel workers share one responsibility.

A publish-subscribe topic delivers a publication to independent subscriptions so each consumer group can react. Failure or slowness in one subscription should not silently discard another's copy.

A partitioned log retains ordered records for a period and lets consumers track positions and replay. It fits state propagation, stream processing, audit-oriented integration, and multiple readers with independent pace.

Products combine these models, but the contract matters more than the label. Record retention, acknowledgment, consumer position, redelivery, ordering scope, and what happens when a consumer falls behind retention.

## 4. Define the acknowledgment boundary

Producer success can mean:

- accepted into a client buffer;
- received by one broker process;
- durably stored under the broker's replication contract;
- committed to a partition and visible to consumers;
- delivered to one or more subscribers.

Consumer acknowledgment can mean:

- bytes were received;
- message parsed;
- local transaction committed;
- external side effect completed;
- downstream publication became durable.

Choose the boundary from the business invariant. A worker should not acknowledge before the durable effect and its deduplication record are safe. If processing exceeds a visibility or lease interval, renew it safely or split the work; otherwise another worker can overlap.

## 5. Assume duplicate delivery

At-least-once systems redeliver after lost acknowledgments, worker failure, lease expiry, broker recovery, and operator replay. Even a transport advertising stronger semantics cannot make an arbitrary external effect exactly once.

A consumer should:

1. validate the envelope and supported schema;
2. authenticate the source and authorize the message path;
3. derive the stable business idempotency key;
4. atomically claim or compare that key with local state;
5. perform the local transition;
6. record result and source position;
7. acknowledge only after the owned durability boundary.

If the key already exists with the same fingerprint, return the recorded outcome. If it exists with a different fingerprint, quarantine the conflict rather than silently treating it as a duplicate.

## 6. Match deduplication lifetime to replay lifetime

Idempotency retention must cover normal retry, delayed delivery, queue retention, dead-letter residence, archive replay, backup restoration, and manual recovery.

If events can replay for one year and deduplication records expire after seven days, side effects are protected for seven days—not one year.

Permanent deduplication can be expensive. Alternatives include a durable business state that naturally rejects repetition, monotonic entity versions, replay into a side-effect-disabled rebuild path, or a new replay namespace with explicit transformation.

Document behavior after the supported window. “Exactly once” is not a retention policy.

## 7. Preserve database change and publication together

Writing business state and publishing separately creates two failure gaps:

```text
commit database -> crash -> event missing
publish event -> database rollback -> event describes false state
```

A transactional outbox writes the business change and an outbox record in one local transaction. A relay publishes unprocessed records and records progress.

The relay can publish twice if it crashes after broker acceptance but before marking the outbox row. Consumers still need idempotency. Monitor outbox age, backlog, publication failures, and retention. Do not delete an outbox record until the supported publication evidence exists.

Change data capture can provide a similar bridge when its ordering, schema, filtering, retention, and recovery contract fits.

## 8. Use an inbox for local atomic consumption

When a consumer changes its database, store the received message identity and business transition in one transaction. The inbox record proves whether the message was applied locally.

An inbox does not make an external API call atomic. For that, pass a stable idempotency key to the provider, query status after an unknown outcome, or reconcile later.

Keep inbox retention aligned with replay. Partition and archive it deliberately; an unbounded inbox can become the consumer's largest dataset.

## 9. State ordering scope precisely

Global ordering restricts parallelism and is rarely required. Useful scopes include:

- one aggregate or entity;
- one account or tenant;
- one workflow instance;
- one broker partition;
- one producer session.

Partition by the smallest scope whose operations must be serialized. Include an entity version or sequence number so consumers can detect gaps, duplicates, and older arrivals.

Transport order does not guarantee completion order when workers process concurrently or retry. If entity order matters, route one entity consistently and prevent concurrent application, or make operations commutative and version-aware.

## 10. Decide how to handle gaps and late messages

On receiving version 44 after 42, a consumer can:

- wait briefly for 43;
- query authoritative current state;
- place 44 in a bounded gap buffer;
- rebuild the projection from a retained source;
- reject to a repair path;
- apply 44 if it is a complete replacement and the contract permits skipping.

Do not block an entire partition forever for one missing record. Bound wait, memory, retries, and repair ownership.

Late events may be valid for analytics and invalid for a current-state transition. Separate event time, ingestion time, and processing time.

## 11. Evolve event schemas for stored readers

Event compatibility must account for:

- old consumers reading new messages;
- new consumers reading retained old messages;
- restored backups containing older schemas;
- archives replayed years later;
- intermediaries that may drop unknown fields.

Add optional fields only when absence preserves old meaning. Never reinterpret or reuse an existing field identifier. Handle unknown enum values. Publish a schema identity and compatibility direction.

When semantics change, publish a new event type or major schema and define translation. A schema registry can validate structure; it cannot prove behavioral compatibility or consumer readiness.

## 12. Keep event payloads useful but bounded

An event can carry:

- a notification with identity and version, requiring a source lookup;
- a self-contained state snapshot;
- a domain-specific change;
- a reference to a large immutable object.

Thin notifications reduce duplication but couple consumers to source availability and can observe a later state. Full snapshots improve independent processing but enlarge messages, expose more data, and complicate deletion. Deltas are compact but require ordered history and a known base.

Choose per consumer and lifecycle. Never place secrets, unnecessary personal data, or unbounded attachments in a broad event stream.

## 13. Treat backlog as customer latency

A queue buffers bursts but does not create capacity. If average arrival exceeds completion, backlog and age grow indefinitely.

Monitor:

- arrival, completion, and retry rates;
- oldest unprocessed age;
- ready and in-flight depth;
- service-time and payload distributions;
- per-partition lag and hot keys;
- consumer concurrency and downstream saturation;
- time to drain at current and maximum safe rate;
- dead-letter depth and age.

Scale from work and age, not count alone when job sizes vary. Bound aggregate consumer concurrency so scaling does not overload the database or external provider.

## 14. Apply backpressure at the producer boundary

When consumers cannot meet the business deadline, admitting unlimited work hides failure in a growing queue.

Use bounded retention, producer quotas, per-tenant fairness, admission control, priority lanes, load shedding, and explicit retry guidance. Preserve capacity for critical work and recovery.

Do not let a bulk replay share unbounded capacity with live traffic. Rate-limit by downstream safety margin and pause automatically on latency, error, or lag thresholds.

## 15. Make dead letters an owned state

A dead-letter queue holds messages that exceeded delivery attempts or failed a terminal rule. It is not a trash can.

Define:

- which errors are retryable, terminal, or unknown;
- maximum attempts and total age;
- backoff and visibility behavior;
- redacted failure evidence;
- alert and owner;
- inspection authorization;
- repair, replay, or discard decision;
- retention and deletion;
- proof that redrive will not repeat an unsafe effect.

Fix the cause before redrive. Replaying malformed or incompatible messages unchanged creates another failure loop.

## 16. Use retries only for transient ambiguity

Retryable conditions may include a bounded transport failure, temporary throttling, or dependency unavailability. Invalid schema, forbidden access, impossible state transition, or unsupported version is not fixed by time.

Use exponential backoff with jitter, a total deadline, attempt cap, and downstream-aware concurrency. Propagate the original idempotency and correlation identity.

Record first failure, last failure, attempt count, and next eligibility without logging sensitive payloads. A retry storm is a load-amplification incident.

## 17. Choose orchestration or choreography by ownership

In orchestration, a workflow owner stores state and directs steps. It offers a visible sequence, timeout and compensation policy, and one place to query progress. The orchestrator must be durable, available, and versioned.

In choreography, independent domains react to facts. It reduces central control and fits open-ended fan-out, but workflow dependencies can become implicit and difficult to observe.

Use orchestration when one owner is accountable for a bounded business outcome and sequence. Use choreography for independent reactions to published facts. A system can orchestrate inside a domain and publish events at its boundary.

Do not create a distributed call stack disguised as events where every consumer must respond in sequence for the original request to succeed.

## 18. Treat sagas as forward recovery and compensation

A saga coordinates local transactions across owners. Each step commits independently. Later failure triggers forward recovery, compensation, or explicit intervention.

Compensation is not rollback of history:

- refund differs from erasing a charge;
- release differs from pretending inventory was never reserved;
- cancellation may be impossible after shipment;
- a sent email cannot be unsent.

For every step, define idempotent command, success evidence, timeout, unknown outcome lookup, retry, compensation, compensation failure, and point of no return.

Persist workflow state and decisions. Do not rely on a process call stack for a workflow that outlives the process.

## 19. Version long-running workflows

A workflow started under definition V1 may still be active when V2 deploys. Record the workflow definition version and state schema with each instance.

Decide whether existing instances:

- complete under V1;
- migrate through an explicit compatible transformation;
- pause for operator action;
- compensate and restart.

Workers must support the versions still in flight. Removing an old handler during deployment can strand durable work.

## 20. Make replay a separate operation

Replay may rebuild a projection, recover missed work, test a new consumer, or repeat business side effects. These are different operations.

A replay plan needs:

- source range and immutable identity;
- consumer version and schema support;
- replay namespace or run ID;
- side-effect policy;
- idempotency coverage;
- rate and downstream budget;
- checkpoint, pause, resume, and cancel;
- live-traffic interaction;
- comparison and completion evidence.

Default rebuilding consumers to side-effect suppression. A projection rebuild should not resend notifications or reissue payments.

## 21. Secure asynchronous boundaries

Authenticate producer identity at publication and authorize topic, queue, partition, or message type. Authorize consumers separately. Encrypt transport and storage according to data class.

Validate schema, type, size, tenant, and business identity. Do not trust a tenant field merely because a broker delivered it. Prevent confused-deputy behavior where a broadly privileged consumer acts on a forged resource reference.

Protect archives and dead letters: they often contain old sensitive payloads and failure detail. Audit replay, purge, subscription, and permission changes.

## 22. Trace causation across time

Carry distinct identities:

- message or event ID;
- business aggregate and version;
- workflow instance;
- correlation ID for the user journey;
- causation ID for the immediate predecessor;
- idempotency key for the effect;
- trace context where sampling permits.

Do not use one ID for every meaning. Preserve timestamps for occurrence, recording, publication, receipt, and completion when lag analysis requires them.

End-to-end success must include the business outcome, not only broker publication or consumer acknowledgment.

## 23. Apply the model to task assignment

The authoritative task transaction updates the assignee and version and writes an outbox event. A relay publishes `task.assigned/v1` with task version, event ID, tenant, correlation, and causation.

Independent consumers update search, analytics, and notifications. Search applies only a newer task version and can rebuild with side effects disabled. Notification claims `(event_id, channel, recipient)` before sending and uses provider idempotency where available.

If notification fails permanently, task assignment remains committed; the DLQ has an owner and user-visible delivery status if the product requires it. Membership authorization was enforced at the task commit, not delegated to an eventually consistent consumer.

## 24. Encode an asynchronous workflow contract

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class MessageContract:
    owner: str
    schema: str
    ordering_scope: str
    retention_hours: int
    deduplication_hours: int
    idempotency_key: str
    maximum_attempts: int
    dead_letter_owner: str

    def validate(self) -> None:
        if not all((self.owner, self.schema, self.ordering_scope, self.idempotency_key)):
            raise ValueError("message contract is incomplete")
        if self.deduplication_hours < self.retention_hours:
            raise ValueError("deduplication expires before retained replay")
        if self.maximum_attempts <= 0 or not self.dead_letter_owner:
            raise ValueError("failed delivery needs bounded attempts and an owner")


@dataclass(frozen=True)
class WorkflowContract:
    message: MessageContract
    publication_atomic_with_state: bool
    consumer_effect_atomic_with_inbox: bool
    compensation_defined: bool
    compensation_failure_defined: bool
    backlog_age_objective_seconds: int
    downstream_concurrency_bounded: bool
    replay_side_effects_suppressed: bool
    workflow_version_recorded: bool

    def validate(self) -> None:
        self.message.validate()
        if not self.publication_atomic_with_state:
            raise ValueError("business state and publication can diverge")
        if not self.consumer_effect_atomic_with_inbox:
            raise ValueError("consumer effect can diverge from acknowledgment state")
        if not self.compensation_defined or not self.compensation_failure_defined:
            raise ValueError("workflow has no complete compensation contract")
        if self.backlog_age_objective_seconds <= 0:
            raise ValueError("backlog has no age objective")
        if not self.downstream_concurrency_bounded:
            raise ValueError("consumers can overload the downstream system")
        if not self.replay_side_effects_suppressed:
            raise ValueError("replay can repeat external side effects")
        if not self.workflow_version_recorded:
            raise ValueError("long-running workflow definition is unversioned")
```

Executable tests exercise the boundary:

```python
import unittest

from workflow_contract import MessageContract, WorkflowContract


def valid_contract() -> WorkflowContract:
    message = MessageContract(
        "task team", "task.assigned/v1", "task_id", 168, 240,
        "event_id + channel + recipient", 8, "task operations",
    )
    return WorkflowContract(message, True, True, True, True, 120, True, True, True)


class WorkflowContractTests(unittest.TestCase):
    def test_complete_contract_is_accepted(self) -> None:
        valid_contract().validate()

    def test_short_deduplication_is_rejected(self) -> None:
        contract = valid_contract()
        fields = {**contract.message.__dict__, "deduplication_hours": 24}
        with self.assertRaisesRegex(ValueError, "replay"):
            WorkflowContract(MessageContract(**fields), True, True, True, True,
                             120, True, True, True).validate()

    def test_dual_write_gap_is_rejected(self) -> None:
        contract = valid_contract()
        fields = {**contract.__dict__, "publication_atomic_with_state": False}
        with self.assertRaisesRegex(ValueError, "diverge"):
            WorkflowContract(**fields).validate()

    def test_unowned_dead_letters_are_rejected(self) -> None:
        contract = valid_contract()
        fields = {**contract.message.__dict__, "dead_letter_owner": ""}
        with self.assertRaisesRegex(ValueError, "owner"):
            WorkflowContract(MessageContract(**fields), True, True, True, True,
                             120, True, True, True).validate()

    def test_incomplete_compensation_is_rejected(self) -> None:
        contract = valid_contract()
        fields = {**contract.__dict__, "compensation_failure_defined": False}
        with self.assertRaisesRegex(ValueError, "compensation"):
            WorkflowContract(**fields).validate()

    def test_unbounded_consumers_are_rejected(self) -> None:
        contract = valid_contract()
        fields = {**contract.__dict__, "downstream_concurrency_bounded": False}
        with self.assertRaisesRegex(ValueError, "overload"):
            WorkflowContract(**fields).validate()

    def test_unsafe_replay_is_rejected(self) -> None:
        contract = valid_contract()
        fields = {**contract.__dict__, "replay_side_effects_suppressed": False}
        with self.assertRaisesRegex(ValueError, "side effects"):
            WorkflowContract(**fields).validate()

    def test_unversioned_workflow_is_rejected(self) -> None:
        contract = valid_contract()
        fields = {**contract.__dict__, "workflow_version_recorded": False}
        with self.assertRaisesRegex(ValueError, "unversioned"):
            WorkflowContract(**fields).validate()


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

Save the blocks as `workflow_contract.py` and `test_workflow_contract.py`, then run:

```bash
python -m unittest -v test_workflow_contract.py
```

A production review should inspect broker configuration, producer acknowledgment, outbox transaction, consumer inbox, idempotency persistence, schema registry, lag, DLQ, replay tooling, workflow history, compensation evidence, access policy, and end-to-end business probes.

## 25. Review asynchronous work

```text
reason for asynchrony, business outcome, owner, and delayed user contract:
command, event, reply, producer, consumer, authority, and semantic name:
queue, subscription, log, retention, position, acknowledgment, and fall-behind:
producer durable acceptance and consumer effect-before-ack boundary:
message identity, fingerprint, idempotency scope, result, and retention:
state/outbox transaction, relay retry, duplicate publication, and monitoring:
inbox/effect transaction, external provider key, status lookup, and reconcile:
partition key, ordering scope, version, gap, late arrival, and concurrency:
schema identity, old/new readers, archive, defaults, enums, and migration:
payload style, source lookup, snapshot, delta, size, privacy, and deletion:
arrival, completion, oldest age, lag, service time, drain, and downstream cap:
admission, fairness, priority, live/replay separation, and load shedding:
retryable/terminal errors, attempts, deadline, jitter, DLQ, owner, and redrive:
orchestration/choreography owner, state, visibility, timeout, and recovery:
saga step, success, unknown outcome, retry, compensation, failure, and no-return:
workflow definition version, in-flight support, migration, and retirement:
replay source, run ID, version, side effects, rate, checkpoint, and evidence:
producer/consumer identity, tenant, schema, archive, DLQ, replay, and audit policy:
event, aggregate, workflow, correlation, causation, idempotency, and trace IDs:
```

## Common Misconceptions

- “A queue makes the workflow reliable.” It provides a transport boundary; application effects still need idempotency and recovery.
- “Exactly-once delivery means exactly-once business effect.” External effects and replay boundaries remain.
- “FIFO means every message is globally ordered.” Ordering normally has a key, partition, or session scope.
- “The outbox removes duplicates.” It closes the missing-event gap but the relay can republish.
- “A DLQ prevents failure.” It preserves failed work only when monitored and owned.
- “A saga rolls back.” Compensation is a new forward action and may be incomplete or impossible.
- “Choreography has no coordinator.” Dependencies still exist; they are distributed across consumers.
- “Backlog depth is enough.” Age and work size determine customer delay.
- “Replay is just resetting a cursor.” It can repeat side effects and exceed present capacity.
- “An event schema registry guarantees compatibility.” Meaning and consumer behavior require separate evidence.

## Core Computer Science Concept

This chapter applies **durable logs, producer-consumer queues, at-least-once delivery, idempotent state machines, partial orders, flow control, and compensating transactions**. The broker persists communication; the application must make repeated and delayed communication safe for business state.

## Engineering Connections

- Delivery and retry build on Chapters 57, 70, 74, 76, and 101.
- Interface evolution applies Chapter 107's compatibility model.
- Invariants and idempotency come from Chapter 110.
- Backpressure and partitioning use Chapter 109.
- Chapter 113 explains the coordination primitives beneath ownership, leases, and leaders.

## From the Field

A consumer charges a payment and crashes before acknowledging. Redelivery charges it again because the transport message ID changed during redrive and the provider received no stable business idempotency key. Binding the effect to `order_id + payment_attempt`, storing the result, and querying provider status after ambiguous failure makes transport redelivery ordinary instead of financial duplication.

## Engineering Review

### What problem does this solve?

It makes delayed and distributed work preserve business invariants despite duplicates, reordering, backlog, partial failure, and replay.

### Why was it designed this way?

Asynchronous boundaries remove one call stack and transaction. Durable intent, identities, owned state machines, and reconciliation replace those implicit guarantees.

### When should I use it?

Use it for burst buffering, independent fan-out, long-running workflows, resilient side effects, state propagation, and replayable processing.

### When should I avoid it?

Avoid it when the caller requires an immediate atomic result and the work fits one owned transaction or simple synchronous boundary.

### How does this make me a better engineer?

It teaches you to reason across time, distinguish facts from requests, align deduplication with replay, and make compensation and backlog visible.

### How does this reduce waste?

It avoids missing events, duplicate effects, unbounded retries, orphaned workflows, silent DLQs, unsafe replays, excessive payloads, and brokers added without a requirement.

## Handbook Principle #112

> Asynchronous work is reliable only when durable intent, repeatable effects, ordering scope, backlog limits, compensation, and replay are all owned beyond the message's delivery.

## Practical Observation

Pick one production message and trace it from business commit through publication, delivery, effect, acknowledgment, retry, DLQ, and replay. At every boundary, simulate a crash after the effect but before the next record. Any step that cannot identify the prior outcome is a duplicate or loss risk.

## Looking Ahead

Queues and workflows rely on time, ownership, membership, and exclusive action. Chapter 113 explains why clocks, leases, locks, fencing tokens, leaders, quorums, and consensus boundaries become difficult across machines.

## References

- [Apache Kafka — Design and delivery semantics](https://kafka.apache.org/documentation/#design)
- [CloudEvents — Specification](https://github.com/cloudevents/spec)
- [AWS Prescriptive Guidance — Transactional outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)
- [AWS Prescriptive Guidance — Saga patterns](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-patterns.html)
- [Microsoft Azure Architecture Center — Competing Consumers](https://learn.microsoft.com/en-us/azure/architecture/patterns/competing-consumers)
- [Microsoft Azure Architecture Center — Queue-Based Load Leveling](https://learn.microsoft.com/en-us/azure/architecture/patterns/queue-based-load-leveling)
- [Chapter 101 — SQS, SNS, EventBridge, and Asynchronous Workflows](../aws/101-sqs-sns-eventbridge-and-asynchronous-workflows.md)
- [Chapter 110 — Consistency, Transactions, and Concurrent Change](110-consistency-transactions-and-concurrent-change.md)
