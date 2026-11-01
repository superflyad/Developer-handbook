# Chapter 101 — SQS, SNS, EventBridge, and Asynchronous Workflows

An asynchronous boundary can absorb a traffic spike, isolate a failing dependency, and let several consumers react independently. It can also hide a growing backlog, deliver the same work twice, lose an event after retries expire, or serialize an entire workload behind one poisoned message.

The central idea is:

> Choose the service by who owns the next action, then design every consumer for redelivery, bounded retries, quarantine, replay, and observable lag.

## 1. Start with ownership, not “event driven”

“Event driven” is too broad to select a service. Begin with the relationship between producer and consumer:

- A **command** asks one logical worker to perform an action. A queue normally owns this work distribution.
- An **event** states that something happened. A topic or event bus can let zero, one, or many independent consumers react.
- A **workflow** owns a known sequence of steps, choices, waits, and compensations. A state machine makes that coordination explicit.

For every asynchronous boundary, name:

- the producer and authoritative source of the fact;
- the intended consumers and their owners;
- whether one or every consumer should process a message;
- acceptable delivery, ordering, latency, and retention;
- the idempotency key and duplicate behavior;
- retry owner, retry horizon, and terminal failure destination;
- backlog and age limits;
- replay source and replay procedure;
- data classification, schema owner, and compatibility policy.

A component diagram showing arrows is not enough. The contract must explain what happens when an acknowledgment is lost, a target is unavailable for a day, a message is malformed, or an operator replays last week's traffic.

## 2. Choose the primitive by responsibility

| Need | Primary primitive | What it owns | Important boundary |
| --- | --- | --- | --- |
| Competing workers process each job | SQS queue | buffering, visibility, redelivery, and backlog | consumers still need idempotency |
| One publication fans out to independent subscribers | SNS topic | push fan-out and per-subscription delivery | use a queue per durable consumer |
| Events route by content to selected targets | EventBridge event bus | matching rules, routing, target retry, and optional archive | unmatched or exhausted events need an explicit policy |
| A known process coordinates steps and waits | Step Functions state machine | workflow state, transitions, retries, and catches | workflow guarantees do not make external effects atomic |

These services compose. A common durable fan-out is `producer -> SNS -> one SQS queue per consumer`. EventBridge can route an event to queues owned by separate teams. Step Functions can publish a command and wait for a callback. Composition is useful when each boundary has one clear owner; adding every service to every path only adds failure modes.

## 3. Define a stable message envelope

Put routing and operational identity in a small envelope, leaving domain data in `data`:

```json
{
  "id": "01JBP7M4WQ2K6T8GCV9Y5R3N1A",
  "type": "order.accepted.v2",
  "source": "checkout",
  "occurred_at": "2026-11-01T15:04:05Z",
  "subject": "order/48392",
  "correlation_id": "request-7f2c",
  "causation_id": "command-91de",
  "schema_version": 2,
  "data": {
    "order_id": "48392",
    "currency": "USD",
    "total_minor": 12500
  }
}
```

The event `id` identifies the occurrence, not the delivery attempt. Preserve it through retries and routing so consumers can deduplicate. `correlation_id` groups one business journey; `causation_id` identifies the input that produced this message. Do not overload transport-generated identifiers as domain identity.

Version schemas compatibly. Producers should usually add optional fields rather than rename or reinterpret existing ones. Consumers must ignore unknown fields and deliberately handle supported versions. A schema registry can document structure and generate bindings, but it cannot decide the semantic meaning of a field or guarantee that every deployed consumer is compatible.

Do not place secrets, access tokens, or unnecessary personal data in an event merely because the transport is encrypted. Messages are copied into logs, queues, dead-letter queues, archives, and debugging tools. Prefer stable identifiers and let an authorized consumer retrieve sensitive state from its owner when necessary.

## 4. Publishing must survive the database boundary

The classic dual-write bug is:

1. commit an order to a database;
2. publish `order.accepted`;
3. crash between the two operations.

Reversing the order creates the opposite bug: consumers observe an order that never committed. A network timeout after publishing also leaves the producer uncertain whether retrying will create a duplicate.

Use a transactional outbox when database state and publication must agree. Commit the business change and an outbox row in the same local transaction. A relay then publishes unsent rows, records progress, and can safely retry. The relay may publish twice, so event IDs and consumer idempotency remain necessary. DynamoDB Streams or change-data capture can serve a similar role when their ordering, retention, filtering, and recovery properties fit the design.

An outbox closes the local commit gap; it does not create a distributed transaction with every consumer. Monitor oldest unpublished age, relay failures, and rows that exceed the retry horizon. Reconcile authoritative records against downstream projections.

## 5. SQS Standard queues distribute work

An SQS Standard queue provides durable buffering and very high throughput. Multiple workers compete for messages, so one message is normally processed by one successful worker. Standard queues use at-least-once delivery and can return duplicates or messages out of order.

A safe consumer loop is:

1. long-poll for a bounded batch;
2. validate the envelope and supported schema;
3. claim the idempotency key atomically;
4. perform the effect within a deadline;
5. record the completed result;
6. delete the message only after success.

If the process crashes before deletion, SQS makes the message visible again. That is recovery, not an anomaly. If deletion succeeds but the response is lost, retrying deletion or receiving another copy must also be harmless.

Long polling waits for available work and reduces empty responses and cost. Batch receive and delete improve efficiency, but acknowledge successful messages individually when a batch contains mixed outcomes. Do not make one malformed record force repeated processing of nine successful records.

## 6. Visibility timeout is a lease, not a lock

Receiving an SQS message does not remove it. The visibility timeout temporarily hides it from other consumers. Successful code must delete it before that lease expires.

Choose a timeout longer than normal processing plus network and deletion margin, but shorter than the maximum acceptable recovery delay after a crashed worker. For variable work, extend visibility with a heartbeat while progress is real. Stop extending when the worker is stuck or loses ownership.

Two bad extremes are common:

- A timeout shorter than processing permits concurrent duplicate work.
- A timeout of hours delays retry after an immediate crash.

SQS can still deliver duplicates while a message is invisible under its at-least-once model. A lease reduces concurrency; it does not prove exclusivity. The consumer's datastore must enforce the business invariant.

Track processing duration against visibility, extension failures, receive count, and messages becoming visible again. Set the HTTP client timeout for a long-poll request longer than the polling wait time so the client does not abandon healthy receives.

## 7. Idempotency belongs at the effect

An idempotent consumer produces the same business outcome when it receives the same event more than once. “We check a cache first” is insufficient if two workers race or the cache expires.

Prefer one of these patterns:

- Insert the event ID into a unique processed-events table in the same transaction as the business update.
- Use a conditional write keyed by the domain command or event ID.
- Pass a stable idempotency token to an API that durably enforces it.
- Model the transition so repeating it is a no-op, such as `ship only if status = paid`.

The deduplication retention must cover transport retention, delayed delivery, DLQ residence, archive replay, and manual recovery. If the idempotency record expires in one day but operators can replay seven days, the design is only idempotent for one day.

For an external side effect with no idempotency support, place an owned adapter in front of it, reconcile after unknown outcomes, or accept and document the duplicate risk. An acknowledgment cannot make a non-transactional email, payment, or shipment atomic with queue deletion.

## 8. Backpressure is visible in message age

A queue decouples arrival rate from service rate only while retention and latency budgets can absorb the difference. If producers sustain 1,000 jobs per second and consumers complete 800, the backlog grows by 200 per second.

Measure:

```text
arrival rate - completion rate = backlog growth rate
visible messages / effective completion rate = approximate drain time
```

Queue depth alone can mislead because message cost varies and in-flight work is separate. Alert primarily on age of oldest actionable message, then depth, in-flight count, receive count, completion rate, error rate, and DLQ entries. Partition metrics by workload or tenant when one class can starve another.

Scale consumers against age and downstream capacity, not simply message count. Cap concurrency before the database, partner API, or account quota fails. Use separate queues for distinct priorities or failure domains rather than building an unbounded priority scheduler inside one consumer.

## 9. Dead-letter queues are quarantine, not recovery

An SQS redrive policy moves a message after `maxReceiveCount` receives. Set the count high enough for transient recovery but low enough that one poison message does not consume capacity indefinitely. The DLQ retention should exceed the source retention; Standard queue messages retain their original enqueue age when moved.

Every DLQ needs:

- an alarm on visible messages;
- an owner and response objective;
- access controls and encryption matching the source data;
- tools to inspect safely without exposing payloads broadly;
- a repair decision: discard, transform, compensate, or replay;
- a rate-limited redrive plan back through normal validation.

Never redrive the entire DLQ blindly after deploying a fix. Sample and classify failures, preserve evidence, test the corrected consumer, replay a bounded cohort, observe outcomes, and increase gradually. A permanently invalid schema should not cycle forever.

A DLQ can disrupt strict FIFO order by removing a failed message and allowing later work to proceed. If later messages depend on that predecessor, pause the group or model the dependency explicitly instead of treating DLQ movement as harmless.

## 10. FIFO queues narrow ordering scope

An SQS FIFO queue preserves order within each message group. While one message in a group is in flight, later messages from that group wait. Different groups can progress concurrently.

Choose the narrowest correct group key:

```text
customer-42   # preserve one customer's mutations
order-48392   # preserve one order's transitions
account-9     # only if all account operations truly require serialization
```

Using one constant group ID serializes the entire queue. A hot group limits its own throughput even when thousands of workers are idle. Estimate active group cardinality and the hottest group's arrival rate.

FIFO producer deduplication suppresses repeated sends with the same deduplication ID during a five-minute interval. That window does not replace durable consumer idempotency: a message can reappear after visibility expiry, a producer can retry outside the window, and an operator can replay later. “Exactly-once processing” requires more than a queue setting.

Ordering also stops at system boundaries. Two queues, two topics, or a later database replica do not share one total order. Carry entity versions or sequence numbers and define how consumers handle gaps, stale versions, and concurrent sources.

## 11. SNS topics fan out publications

SNS publishes one message to multiple subscriptions, including SQS, Lambda, HTTP/S, email, and other endpoints. Use it when subscribers are known through topic subscriptions and each should receive its own copy.

For durable application-to-application fan-out, subscribe one SQS queue per consumer:

```text
orders topic
├── fulfillment queue -> fulfillment workers
├── analytics queue   -> analytics workers
└── notifications queue -> notification workers
```

Each team then owns backlog, concurrency, retry, DLQ, and deployment independently. Publishing directly to several Lambda functions is simpler for small workloads but provides less buffering control when one subscriber is slow or unavailable.

SNS delivery policy depends on endpoint protocol. When its retries are exhausted, SNS discards the message unless that subscription has a DLQ. The DLQ is attached per subscription because delivery failure belongs to the target, not the topic. Verify permissions and alarm on each failure path.

## 12. Filters reduce fan-out but create contracts

An SNS subscription filter policy can match message attributes or a JSON message body. A subscription without a filter receives every publication. With a filter, nonmatching messages are intentionally not delivered.

Filters are useful for broad shared topics, but they couple routing to field names, types, and missing-value behavior. Treat each filter as code:

- keep routing attributes small and stable;
- test positive, negative, missing, malformed, and new-version cases;
- deploy producer and filter changes compatibly;
- monitor filtered and delivered counts;
- avoid filters that encode business logic owned by the consumer.

Filtering is not a security boundary. Topic and queue policies must still prevent unauthorized publishing or subscription. A producer able to choose routing attributes may be able to reach a subscriber unless IAM and resource policies constrain it.

FIFO SNS topics add ordering and deduplication features, but their exactly-once conditions are specific: compatible FIFO targets, correct permissions, successful processing and deletion, and filtering choices all matter. Continue to make business effects idempotent.

## 13. EventBridge routes facts by content

An EventBridge event bus compares events with rule patterns and sends matches to rule targets. A pattern can use event metadata and detail fields. Unlike a queue, a bus is not itself a competing-worker backlog for consumers.

Use EventBridge when producers should publish facts without knowing which targets exist and platform owners need content-based routing, cross-account boundaries, SaaS integration, archive/replay, or centralized rule management. Keep patterns precise; a broad or recursive rule can produce unexpected traffic, cost, or loops.

For each rule, define:

- accepted source, detail type, and schema versions;
- target owner and target resource policy;
- input transformation and what information it discards;
- retry policy and DLQ;
- expected match rate and alarm thresholds;
- recursion guard;
- test fixtures for matching and nonmatching events.

An event that matches no rule causes no target action. That may be correct, but it is not durable pending work. If every command must be handled, address a queue owned by that consumer rather than hoping a future rule matches it.

## 14. EventBridge retry, DLQ, archive, and replay differ

By default, EventBridge retries retriable target-delivery failures for up to 24 hours and up to 185 attempts with exponential backoff and jitter. After the configured attempts or event age is exhausted, it drops the event unless the target has a DLQ.

These mechanisms solve different problems:

- A **target DLQ** retains events EventBridge could not deliver to that target.
- An **archive** retains events accepted by an event bus according to its pattern and retention.
- A **replay** sends archived events again to the source bus and selected rules for a time range.

A replay is new delivery, not time travel. Current rules, targets, permissions, code, and external state may differ from the original run. Consumers must remain idempotent and replay-safe, and operators should replay a bounded interval at a controlled rate where downstream capacity permits.

Archive does not replace domain data retention or an audit ledger. Store authoritative business facts in their owning system. Record replay initiator, scope, reason, expected count, observed count, and reconciliation result.

## 15. Schema ownership is an operational responsibility

EventBridge Schemas can store AWS and custom schemas, discover schemas from events, and generate code bindings. Discovery is useful inventory, not governance: sampling traffic after deployment is too late to prevent an incompatible producer change.

Assign a producer team to each event type. Keep representative examples and compatibility tests in source control. Validate required fields at ingress and route unsupported versions to observable quarantine rather than retrying them as transient failures.

Separate three changes:

- **additive**: a new optional field that old consumers ignore;
- **behavioral**: an existing field gains a new meaning or value;
- **breaking**: a required field is removed, renamed, or retyped.

Behavioral changes can be breaking even when JSON validation passes. Publish a new event type or version when consumers need an explicit migration. Run old and new forms in parallel only with an end date and measured consumer adoption.

## 16. Step Functions makes coordination explicit

Use Step Functions when the application owns a known process: invoke a service, wait for a job, branch on a result, request approval, run tasks in parallel, retry selected failures, and compensate completed work. The state machine becomes a durable execution model rather than orchestration scattered across callbacks and queue consumers.

Step Functions supports three broad integration patterns:

- **Request Response** continues after the service API responds; that response may only mean a job was accepted.
- **Run a Job (`.sync`)** waits for a supported job to complete.
- **Callback with task token** waits for an external actor to return success or failure.

Express workflows support Request Response integrations, not `.sync` or callback patterns. Choose the workflow type before creation because it is immutable.

Orchestration is appropriate when one owner controls sequence and outcome. Choreography is appropriate when independent domains react to facts without one central process deciding every step. A useful system often orchestrates inside a domain and publishes events at domain boundaries.

## 17. Standard and Express guarantees are scoped

Standard workflows provide durable, auditable execution for up to one year and an exactly-once **workflow execution** model unless retries are defined. Asynchronous Express workflows are at least once; Synchronous Express workflows are at most once and both have a five-minute maximum duration.

Do not translate “exactly-once workflow execution” into “every external effect happens exactly once.” A task can call an external service, lose the response, time out, and be retried according to the state-machine policy. A stopped `.sync` task is cancelled on a best-effort basis and may continue externally. Redrive also resets retry counts for rerun states.

Therefore:

- pass stable idempotency keys to tasks;
- distinguish retryable technical errors from business rejection;
- set task, heartbeat, and whole-workflow timeouts;
- define compensation for completed irreversible steps;
- reconcile unknown external outcomes before retrying them;
- enable the execution history or logs needed by the workflow type.

Use Standard for long-running, auditable, callback, or job-waiting workflows. Use Express for short, high-volume processing whose tasks are idempotent and whose logging and execution semantics fit the workload.

## 18. Retry only errors that can recover

Step Functions `Retry` policies select error names and define interval, attempt count, backoff, maximum delay, and optional jitter. `Catch` routes terminal failures to explicit handling states. Without handling, an error fails the execution.

Classify failures:

- throttle, temporary unavailability, and selected network errors can be retried with backoff and jitter;
- invalid input, unsupported schema, failed authorization, and violated business rules normally should not be retried unchanged;
- timeout after an external request may have an unknown outcome and requires lookup or reconciliation;
- exhausted retry should enter compensation, manual review, or terminal failure—not restart forever.

Retries multiply. An SDK, Lambda runtime, state machine, EventBridge target, and SQS consumer can all retry the same request. Assign one layer as the primary retry owner, bound every other layer, and calculate the worst-case attempts and elapsed time. Respect the caller's deadline and the downstream recovery objective.

## 19. Large payloads need an owned reference

Transport limits and repeated copies make messages a poor place for large documents. Store the payload in S3 and send a reference containing bucket, key, immutable version, checksum, size, media type, encryption context, and expiry.

The reference creates lifecycle obligations:

- the object must outlive queue retention, DLQ analysis, and replay;
- consumers need least-privilege access without a long-lived public URL;
- the checksum must detect wrong or changed content;
- deletion and privacy requests must include archives and quarantines;
- producers must clean up objects whose publication never completes.

Avoid mutable “latest” keys. A replay must resolve the same payload that the original event described, or it is a different operation.

## 20. Secure every hop

Grant producers permission only to send or publish to intended resources. Grant consumers receive, visibility-change, and delete permissions only for their queues. Scope Step Functions execution roles to the exact integrated actions and resources.

Resource policies matter for SNS-to-SQS, EventBridge targets, and cross-account event buses. Constrain service principals with source ARNs or accounts where supported to prevent a confused deputy. For encrypted queues, topics, buses, archives, and DLQs, verify both data-service permissions and KMS key policy grants.

Separate application permissions from operator permissions. Reading arbitrary payloads, redriving DLQs, starting replays, and manually starting workflows can expose data or repeat costly effects. Log those operations and require narrower production roles or approval for high-impact recovery.

## 21. Observe the whole asynchronous path

Propagate event ID, correlation ID, causation ID, event type, schema version, and entity key into structured logs and traces. Do not use high-cardinality identifiers as unbounded metric dimensions.

Build dashboards around outcomes:

- publish accepted, rejected, and latency;
- oldest unpublished outbox record;
- queue oldest age, visible and in-flight count, receives, deletes, and DLQ count;
- topic delivery success and failure by subscription;
- rule matches, target delivery failures, throttling, and DLQ count;
- workflow started, succeeded, failed, timed out, aborted, duration, and redrive;
- consumer processed, duplicate, invalid, retryable failure, permanent failure, and end-to-end lag.

Trace breaks are expected across asynchronous time and service boundaries. Link spans using message metadata and preserve original timestamps. A healthy producer latency chart says nothing about a two-hour consumer backlog.

## 22. Test failure, not only delivery

Before launch, exercise:

- duplicate delivery before and after the deduplication retention window;
- worker crash before the side effect, after the side effect, and before delete;
- visibility timeout shorter than work and heartbeat failure;
- one poison message and a full DLQ;
- downstream throttle and outage beyond the retry horizon;
- malformed and unsupported schema versions;
- FIFO hot group, missing sequence, and out-of-order external events;
- SNS subscription permission failure;
- EventBridge nonmatch, target failure, archive, and bounded replay;
- workflow task timeout, catch, compensation, stop, and redrive;
- KMS, IAM, and cross-account policy denial;
- consumer capacity below producer rate.

Reconcile expected business records after each test. “The event eventually disappeared” is not a success criterion.

## 23. Build a delivery contract checker

The following standard-library model rejects several unsafe combinations before infrastructure exists:

```python
from dataclasses import dataclass


AT_LEAST_ONCE = {"sqs-standard", "sqs-fifo", "sns", "eventbridge", "express-async"}


@dataclass(frozen=True)
class Consumer:
    name: str
    idempotent: bool
    replay_safe: bool
    dedupe_days: int
    max_handler_seconds: int
    max_concurrency: int


@dataclass(frozen=True)
class Route:
    service: str
    ordering: str
    retention_days: int
    has_dlq: bool
    visibility_seconds: int = 0
    message_groups: int = 0
    archive_days: int = 0


@dataclass(frozen=True)
class DeliveryContract:
    route: Route
    consumer: Consumer
    replay_required: bool

    def validate(self) -> None:
        route = self.route
        consumer = self.consumer
        if route.service in AT_LEAST_ONCE and not consumer.idempotent:
            raise ValueError("at-least-once delivery requires an idempotent consumer")
        if route.service in AT_LEAST_ONCE and not route.has_dlq:
            raise ValueError("at-least-once delivery requires terminal quarantine")
        if route.service.startswith("sqs"):
            required = consumer.max_handler_seconds + 10
            if route.visibility_seconds < required:
                raise ValueError("visibility must exceed handler time plus delete margin")
        if route.service == "sqs-fifo":
            if route.ordering != "message-group":
                raise ValueError("FIFO ordering scope must be message-group")
            if consumer.max_concurrency > 1 and route.message_groups < 2:
                raise ValueError("concurrent FIFO work requires multiple message groups")
        if self.replay_required:
            if not consumer.replay_safe:
                raise ValueError("replay requires a replay-safe consumer")
            replay_window = max(route.retention_days, route.archive_days)
            if consumer.dedupe_days < replay_window:
                raise ValueError("dedupe retention must cover the replay window")
        if route.service == "eventbridge" and self.replay_required and route.archive_days == 0:
            raise ValueError("EventBridge replay requires an archive")
        if route.service == "express-async" and not consumer.idempotent:
            raise ValueError("asynchronous Express tasks must be idempotent")
```

Tests make the intended guarantees executable:

```python
import unittest

from delivery_contract import Consumer, DeliveryContract, Route


def valid_contract() -> DeliveryContract:
    return DeliveryContract(
        Route("sqs-standard", "none", 4, True, visibility_seconds=70),
        Consumer("fulfillment", True, True, 14, 45, 20),
        replay_required=True,
    )


class DeliveryContractTests(unittest.TestCase):
    def test_complete_contract_is_accepted(self) -> None:
        valid_contract().validate()

    def test_non_idempotent_consumer_is_rejected(self) -> None:
        contract = valid_contract()
        consumer = Consumer("fulfillment", False, True, 14, 45, 20)
        with self.assertRaisesRegex(ValueError, "idempotent"):
            DeliveryContract(contract.route, consumer, True).validate()

    def test_short_visibility_is_rejected(self) -> None:
        contract = valid_contract()
        route = Route("sqs-standard", "none", 4, True, visibility_seconds=45)
        with self.assertRaisesRegex(ValueError, "visibility"):
            DeliveryContract(route, contract.consumer, True).validate()

    def test_one_fifo_group_cannot_supply_concurrency(self) -> None:
        contract = valid_contract()
        route = Route("sqs-fifo", "message-group", 4, True, 70, message_groups=1)
        with self.assertRaisesRegex(ValueError, "multiple message groups"):
            DeliveryContract(route, contract.consumer, True).validate()

    def test_replay_requires_dedupe_retention(self) -> None:
        route = Route("eventbridge", "none", 0, True, archive_days=30)
        consumer = Consumer("projection", True, True, 7, 20, 10)
        with self.assertRaisesRegex(ValueError, "dedupe retention"):
            DeliveryContract(route, consumer, True).validate()

    def test_eventbridge_replay_requires_archive(self) -> None:
        route = Route("eventbridge", "none", 0, True)
        consumer = Consumer("projection", True, True, 30, 20, 10)
        with self.assertRaisesRegex(ValueError, "requires an archive"):
            DeliveryContract(route, consumer, True).validate()


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

Save the blocks as `delivery_contract.py` and `test_delivery_contract.py`, then run:

```bash
python -m unittest -v test_delivery_contract.py
```

A production checker should inspect authorized read-only inventory for queue retention, visibility, redrive policies, SNS subscription DLQs and filters, EventBridge rule targets and archives, Step Functions type and logging, KMS keys, IAM policies, alarms, and quotas. It must not redrive, replay, publish, purge, start executions, or change infrastructure during validation.

## 24. Review an asynchronous design

```text
command, event, or workflow; producer; authority; and owning teams:
service choice and why queue, topic, bus, or state machine fits:
envelope, event identity, correlation, schema owner, and compatibility:
database-to-publication atomicity, outbox relay, and reconciliation:
delivery guarantee, idempotency key, atomic claim, and retention:
ordering scope, message groups, versions, gaps, and stale handling:
visibility, heartbeat, handler deadline, deletion, and unknown outcome:
arrival/completion rates, oldest-age objective, concurrency, and quotas:
retry owner, retryable errors, backoff, jitter, attempts, and horizon:
DLQ owner, alarm, retention, inspection, repair, and bounded redrive:
SNS subscriptions, filters, delivery policy, and per-target isolation:
EventBridge patterns, nonmatches, loop guards, DLQ, archive, and replay:
Step Functions type, integration pattern, timeout, catch, and compensation:
payload limits, immutable object reference, checksum, and lifecycle:
IAM and resource policies, KMS, cross-account trust, and operator access:
logs, traces, metrics, dashboards, runbooks, and failure drills:
```

## Common Misconceptions

- “A queue delivers every message exactly once.” SQS consumers must tolerate duplicate delivery and unknown outcomes.
- “Visibility locks the message.” It is a temporary lease, and at-least-once delivery still applies.
- “FIFO orders the system.” It orders one message group, not every downstream effect or separate channel.
- “A DLQ handles failures.” It retains terminal failures; people and procedures still need to diagnose and recover them.
- “SNS is a durable queue for every subscriber.” Durable application consumers usually need their own SQS subscription.
- “EventBridge stores unmatched work until a consumer appears.” Unmatched events cause no target action unless another retention design exists.
- “Archive and DLQ are interchangeable.” An archive supports bus replay; a target DLQ captures failed target delivery.
- “Step Functions exactly once means side effects exactly once.” Workflow execution semantics do not make remote effects transactional.
- “More retries improve reliability.” Nested, unbounded retries can amplify an outage and exceed the business deadline.
- “Schema-valid means compatible.” Meaning and business behavior can break while structure still validates.

## Core Computer Science Concept

Asynchronous systems apply **queues, leases, replicated logs, finite-state machines, and idempotent operations**. Acknowledgment separates delivery from completion, a visibility lease allows failure recovery, sequence scope constrains ordering, and a durable state machine records progress. Exactly-once business effect is usually constructed from stable identity and atomic state transition rather than provided by the transport alone.

## Engineering Connections

- Outboxes extend Chapter 99's transaction boundary into reliable publication.
- Idempotent consumers and bounded retries apply Chapters 74 and 76.
- Message groups are per-key serialization like DynamoDB partition-key coordination in Chapter 100.
- Queue age is congestion evidence like TCP flow and backpressure from Chapter 58.
- Resource policies and KMS reuse Chapters 92 and 94's identity and network boundaries.
- Replay is a migration and recovery operation requiring Chapter 77's comparison and rollback discipline.

## From the Field

A payment consumer charges a card and then crashes before deleting the SQS message. The visibility timeout expires, a second worker receives the same message, and the card is charged again. Raising the visibility timeout only delays the duplicate. A stable payment idempotency key enforced by the payment adapter, an atomic local record of the outcome, and reconciliation after ambiguous timeouts convert redelivery from financial damage into a harmless repeat.

## Engineering Review

### What problem does this solve?

It turns asynchronous AWS service choices into explicit ownership, delivery, ordering, retry, failure, replay, security, and observability contracts.

### Why was it designed this way?

Distributed delivery crosses independent failure boundaries. Durable messages and workflow state permit recovery, but applications must define duplicate-safe effects and terminal outcomes.

### When should I use it?

Use this model for background jobs, buffering, fan-out, domain events, content routing, cross-account integration, event replay, and multi-step AWS workflows.

### When should I avoid it?

Avoid asynchronous boundaries when the caller requires one immediate atomic result, the operation cannot tolerate delayed or duplicate execution, or the team cannot own backlog and recovery. A direct bounded call or local transaction may be clearer.

### How does this make me a better engineer?

It teaches you to distinguish transport claims from business outcomes, narrow ordering, quantify backlog, assign retry ownership, and design recovery before failure.

### How does this reduce waste?

It reduces duplicate effects, idle polling, retry storms, hot FIFO groups, abandoned DLQs, accidental fan-out, oversized payload copies, central orchestration, and manual recovery without evidence.

## Handbook Principle #101

> Reliable asynchronous work comes from explicit ownership and duplicate-safe effects, not from assuming the transport will deliver once.

## Practical Observation

Select one production queue, topic, rule, or workflow. Trace one message from authoritative commit through every retry layer to its final effect. Record its stable ID, maximum attempts, maximum elapsed time, deduplication retention, terminal destination, oldest-age alarm, and replay path. If any value is unknown, the system's delivery guarantee is unknown too.

## Looking Ahead

Queues and event routes need compute that scales, times out, handles batches, and exposes synchronous APIs safely. Chapter 102 examines Lambda, API Gateway, concurrency controls, cold starts, event-source mappings, and serverless execution boundaries.

## References

- [Amazon SQS — Developer Guide](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/)
- [Amazon SQS — Standard queues](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/standard-queues.html)
- [Amazon SQS — Visibility timeout](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html)
- [Amazon SQS — FIFO delivery logic](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/FIFO-queues-understanding-logic.html)
- [Amazon SQS — Dead-letter queues](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html)
- [Amazon SQS — Short and long polling](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-short-and-long-polling.html)
- [Amazon SNS — What is Amazon SNS?](https://docs.aws.amazon.com/sns/latest/dg/welcome.html)
- [Amazon SNS — Message filtering](https://docs.aws.amazon.com/sns/latest/dg/sns-message-filtering.html)
- [Amazon SNS — Message delivery retries](https://docs.aws.amazon.com/sns/latest/dg/sns-message-delivery-retries.html)
- [Amazon SNS — Dead-letter queues](https://docs.aws.amazon.com/sns/latest/dg/sns-dead-letter-queues.html)
- [Amazon SNS — FIFO message deduplication](https://docs.aws.amazon.com/sns/latest/dg/fifo-message-dedup.html)
- [Amazon EventBridge — Event buses](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-event-bus.html)
- [Amazon EventBridge — Event patterns](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-event-patterns.html)
- [Amazon EventBridge — Schemas](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-schema.html)
- [Amazon EventBridge — Target retry policy](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-rule-retry-policy.html)
- [Amazon EventBridge — Replaying archived events](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-replay-archived-event.html)
- [AWS Step Functions — Choosing a workflow type](https://docs.aws.amazon.com/step-functions/latest/dg/choosing-workflow-type.html)
- [AWS Step Functions — Service integration patterns](https://docs.aws.amazon.com/step-functions/latest/dg/connect-to-resource.html)
- [AWS Step Functions — Error handling](https://docs.aws.amazon.com/step-functions/latest/dg/concepts-error-handling.html)
- [Chapter 100 — DynamoDB, Caching, and NoSQL Access Patterns](100-dynamodb-caching-and-nosql-access-patterns.md)
