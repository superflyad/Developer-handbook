# Chapter 74 — Idempotency, State, Retries, and Recovery

An automation can lose a response after the remote system accepts its request. At that moment, “try again” may recover the run or duplicate the effect. Safe recovery requires more than an exception handler.

The central idea is:

> Give each logical operation a stable identity, persist its transitions, retry only when repetition is safe, and reconcile ambiguity against observed state.

## 1. Failure creates an information problem

Consider this sequence:

```text
client sends create request
service creates the resource
connection closes before the response arrives
client observes a timeout
```

The timeout does not say whether the effect occurred. It says the client did not receive a conclusive response before its deadline.

Treat these as different facts:

- **request outcome**: what response, error, or timeout the caller observed;
- **operation outcome**: what state transition the target system committed.

A transport error can leave the operation outcome unknown. Marking it failed is unjustified; marking it successful is equally unjustified. The recovery design must preserve uncertainty until evidence resolves it.

## 2. Model desired and observed state

Reliable automation converges an observed system toward an explicit desired state:

```text
desired state: account has label "reviewed"
observed state: account lacks label "reviewed"
action: ensure the label exists
```

“Ensure the label exists” is safer to repeat than “append one label.” The first describes a stable postcondition. The second describes an event whose repetition may create duplicates.

Before mutating, identify:

- the resource and version observed;
- the desired postcondition;
- the operation identity;
- the preconditions that must still hold;
- the allowed transition;
- the evidence that confirms completion.

After mutating, observe again when the boundary cannot provide authoritative completion evidence.

## 3. Understand idempotency precisely

An operation is idempotent when repeating the same logical request has the same intended effect as applying it once. The responses, timestamps, audit records, and metrics do not have to be identical.

Examples include:

- setting a field to a specific value;
- ensuring a named resource exists with a specific configuration;
- deleting a resource that is already absent, if absence counts as success;
- recording a payment request under a unique operation key.

These are not inherently idempotent:

- incrementing a counter;
- appending an item without a uniqueness constraint;
- generating a new identifier on every attempt;
- sending an email on every delivery;
- charging an account without a stable payment identity.

HTTP labels methods such as PUT and DELETE idempotent by their defined intent, but an application still has to implement those semantics. A path named `/delete` and a familiar status code do not prove safe repetition.

## 4. Give the logical operation one stable identity

Create the operation identifier outside the retry loop and reuse it for every attempt, restart, and downstream call belonging to the same intent.

A sound idempotency key needs:

- uniqueness within a documented scope;
- enough entropy or coordination to avoid accidental collision;
- association with the authenticated caller or tenant;
- a request fingerprint that detects reuse for different intent;
- a retention period longer than the possible retry and recovery window;
- protection from appearing as a secret or authorization token.

Do not derive a key only from mutable presentation text. Do not generate a new key for each retry. Do not accept the same key with different parameters.

A provider should store the first accepted fingerprint and result under a unique constraint. Later matching requests return or reconstruct that result. A mismatched fingerprint is a conflict, not a fresh operation.

## 5. Define the idempotency scope and lifetime

The statement “this API supports idempotency keys” is incomplete. Ask:

- Is the key unique globally, per account, per endpoint, or per resource?
- When is the key recorded: before validation, after validation, or at commit?
- Are errors cached as well as successes?
- How are simultaneous first requests serialized?
- How long is the key retained?
- Does failover preserve the deduplication record?
- Can a caller query the result by key?

If a key expires after 24 hours, a week-late recovery cannot rely on it. The caller must reconcile using a stable business identifier or require operator review.

## 6. Persist intent before attempting an effect

For an operation that must survive process failure, write a durable intent record before crossing the external boundary:

```text
operation key
request fingerprint and schema version
target and tenant scope
desired postcondition
status and attempt count
timestamps and lease metadata
remote operation identifier
result or error classification
```

The write must complete before the effect is attempted. An in-memory variable or buffered log line is not a checkpoint.

Where local state and an outgoing message must be committed together, use a transactional outbox or another mechanism with equivalent atomicity. “Update the database, then publish” contains a crash gap between those actions.

## 7. Use an explicit state machine

A small state machine makes legal recovery paths reviewable:

```text
pending -> running -> succeeded
                |       ^
                v       |
             unknown -> reconcile
                |
                v
              failed
```

Possible meanings are:

- `pending`: durable intent exists; no attempt is known to have started;
- `running`: a worker owns an unexpired lease and may be attempting the effect;
- `succeeded`: authoritative evidence confirms the postcondition;
- `unknown`: the attempt may have committed, but evidence is inconclusive;
- `failed`: a terminal policy or validation error prevents automatic progress.

Status names are a contract. Define which actor can make each transition, what transaction protects it, what evidence is required, and what happens after a crash during the transition.

Never convert `unknown` to `failed` merely because time passed. Expiration may make automatic recovery impossible, but it does not rewrite history.

## 8. Make checkpoints truthful and durable

A checkpoint should describe facts that are safe to act on after restart. Record “attempt started” before the attempt and “effect confirmed” only after authoritative confirmation.

Avoid these patterns:

- updating a checkpoint only in process memory;
- marking an entire batch complete before every item is confirmed;
- writing success before a buffered output is durable;
- using a log message as the sole recovery state;
- overwriting the last useful error with a generic final exception;
- resuming by numeric position when the input can reorder.

Prefer stable item identities and per-item state. Include a schema version so newer code can reject or migrate checkpoints it does not understand.

Durability depends on the storage contract. A successful library call may still mean data is buffered above the device or replicated asynchronously. Match the guarantee to the consequence of replay.

## 9. Classify errors before retrying

Retries should follow semantics, not a blanket list of exceptions. Useful classes are:

| Class | Example | Default action |
| --- | --- | --- |
| Permanent | Invalid input, unsupported operation | Stop and report |
| Authorization | Missing permission, wrong tenant | Stop; repair authority deliberately |
| Conflict | Version or precondition mismatch | Re-observe and re-plan |
| Transient | Throttling, temporary unavailability | Retry within budget if idempotent |
| Ambiguous | Timeout after request may have arrived | Reconcile or retry with the same key |
| Local capacity | Disk full, process limit | Stabilize local system before retry |

An HTTP status is context, not a complete policy. A `409` might require re-planning, and a `429` might include a server-directed delay. A timeout on a non-idempotent request is ambiguous even when the client library labels it transient.

Authentication failures should not spin. Refreshing an expired credential once can be reasonable if the identity and scope remain the same; changing credentials silently can cross an authority boundary.

## 10. Bound retries by attempts and time

A retry policy should specify:

- which operation and error classes qualify;
- idempotency or reconciliation requirements;
- maximum attempts, including the first call;
- per-attempt timeout;
- total elapsed deadline;
- backoff formula and maximum delay;
- server retry guidance handling;
- cancellation behavior;
- terminal evidence and escalation.

An attempt limit alone can exceed an operator's deadline when individual calls hang. A time limit alone can create an excessive request rate when calls fail immediately. Use both.

Place retries at one deliberate layer. Three retries in a client, three in a helper, and three in a job runner can multiply into 27 downstream calls for one logical operation.

## 11. Back off and add jitter

Immediate retries amplify an outage. Exponential backoff grows the delay after repeated failures:

```text
cap_n = min(maximum_delay, base_delay * 2^n)
```

Full jitter chooses a random delay between zero and that cap:

```text
delay_n = random(0, cap_n)
```

Jitter prevents many clients from synchronizing on identical retry times. The exact strategy is a system choice; document it and use the supported SDK behavior when available.

Honor trustworthy server guidance such as `Retry-After` within the caller's total deadline and safety policy. Do not sleep past cancellation or hold scarce resources unnecessarily while waiting.

Backoff reduces pressure; it does not make an unsafe operation safe to repeat.

## 12. Treat timeouts as resource budgets

Set timeouts for connection establishment, request or read progress, and total operation time according to the boundary. One broad timeout may omit DNS, TLS negotiation, connection-pool waiting, or response streaming.

A timeout should be:

- long enough for normal tail latency;
- short enough to preserve the total recovery budget;
- distinct from cancellation by an operator or parent workflow;
- observable with attempt and elapsed-time context;
- tested against slow and stalled boundaries.

Extremely short timeouts manufacture retries. Infinite timeouts turn a partial outage into resource exhaustion.

## 13. Reconcile ambiguous outcomes

Reconciliation compares desired state, durable intent, and current observed state. It can resolve an `unknown` operation by:

1. querying the provider by idempotency key or remote operation ID;
2. reading the target through a strongly appropriate consistency path;
3. validating the expected postcondition and request fingerprint;
4. marking success when authoritative evidence agrees;
5. safely reissuing the same logical operation when it does not;
6. escalating when evidence conflicts or has expired.

Absence from an eventually consistent listing may not prove the effect did not occur. Use the provider's documented read semantics.

Reconciliation is also routine maintenance. A periodic controller can repair drift even when no exception was observed.

## 14. Resume work by identity, not position

Batch recovery often fails when it records “completed row 812.” If the source is edited, resorted, or regenerated, row 813 may represent a different item.

Persist stable item keys, input fingerprints, and individual outcomes. On restart:

- verify the job definition and input version;
- skip authoritatively succeeded items;
- reconcile unknown items;
- retry eligible pending items;
- stop on incompatible input or policy changes;
- produce a final manifest of every item state.

A resumable batch is a collection of named state machines, not a loop counter saved to disk.

## 15. Design partial failure explicitly

When one workflow changes several independent systems, a single all-or-nothing transaction may not exist. Define the possible stable outcomes before implementation.

For each step, decide whether it is:

- retryable to the desired state;
- compensable with a business action;
- irreversible and therefore a pivot point;
- safe to perform in parallel;
- dependent on a version or lease;
- eligible for automatic versus human recovery.

Sequence reversible preparation before irreversible effects where the domain permits. Do not claim rollback across systems that have already committed visible changes.

## 16. Compensation is another operation

A compensating action restores an acceptable business state; it may not restore the exact historical state. Canceling a reservation, issuing a refund, and revoking access all have their own identities, permissions, side effects, and failure modes.

Therefore compensation must be:

- idempotent or deduplicated;
- durably tracked;
- conditional on the state it intends to compensate;
- observable and retryable where safe;
- allowed to stop for human judgment;
- tested for partial completion.

Concurrent work may have changed the resource after the original action. Blindly writing the old value can destroy legitimate updates. Use versions, conditional requests, or domain-specific reversal.

## 17. “Exactly once” needs a named boundary

Networks can duplicate delivery, workers can crash, and acknowledgements can be lost. A queue advertising exactly-once behavior does not automatically make every downstream side effect occur exactly once.

State a narrower guarantee:

```text
Within one tenant and the 30-day key-retention window,
requests with the same operation key and fingerprint
produce at most one accepted invoice record.
```

Delivery may still be at least once, while the consumer uses a durable uniqueness constraint to make the business effect effectively once within that scope.

Name the storage system, transaction boundary, deduplication key, retention window, and behavior after expiration. Without those details, “exactly once” is a slogan rather than a contract.

## 18. Complete example: recover an ambiguous effect

This standard-library lab uses SQLite as a durable operation store and an in-memory remote service that deduplicates by operation key. The service can apply an effect and then lose the response:

```python
from __future__ import annotations

import hashlib
import json
import random
import sqlite3
import time
import unittest
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable, Protocol


class TransientError(RuntimeError):
    pass


class PermanentError(RuntimeError):
    pass


class RetryExhausted(RuntimeError):
    pass


class KeyReuseError(RuntimeError):
    pass


@dataclass(frozen=True)
class OperationRecord:
    key: str
    fingerprint: str
    status: str
    result: str | None


def request_fingerprint(*, target: str, label: str) -> str:
    document = {
        "operation": "ensure-label-v1",
        "target": target,
        "label": label,
    }
    encoded = json.dumps(
        document,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class OperationStore:
    def __init__(self, path: Path) -> None:
        self.connection = sqlite3.connect(path)
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS operations (
                operation_key TEXT PRIMARY KEY,
                fingerprint TEXT NOT NULL,
                status TEXT NOT NULL,
                result TEXT
            )
            """
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def reserve(self, key: str, fingerprint: str) -> OperationRecord:
        self.connection.execute(
            """
            INSERT OR IGNORE INTO operations
                (operation_key, fingerprint, status, result)
            VALUES (?, ?, 'pending', NULL)
            """,
            (key, fingerprint),
        )
        self.connection.commit()
        record = self.get(key)
        if record.fingerprint != fingerprint:
            raise KeyReuseError("operation key reused for different intent")
        return record

    def get(self, key: str) -> OperationRecord:
        row = self.connection.execute(
            """
            SELECT operation_key, fingerprint, status, result
            FROM operations
            WHERE operation_key = ?
            """,
            (key,),
        ).fetchone()
        if row is None:
            raise KeyError(key)
        return OperationRecord(*row)

    def mark(self, key: str, status: str, result: str | None = None) -> None:
        if status not in {"running", "succeeded", "unknown", "failed"}:
            raise ValueError(f"unsupported status: {status}")
        cursor = self.connection.execute(
            """
            UPDATE operations
            SET status = ?, result = ?
            WHERE operation_key = ?
            """,
            (status, result, key),
        )
        if cursor.rowcount != 1:
            raise KeyError(key)
        self.connection.commit()


class LabelService(Protocol):
    def ensure_label(
        self,
        *,
        target: str,
        label: str,
        operation_key: str,
    ) -> str: ...


class FakeLabelService:
    def __init__(self) -> None:
        self.results: dict[str, tuple[str, str, str]] = {}
        self.effects: list[tuple[str, str]] = []
        self.lose_next_response = False

    def ensure_label(
        self,
        *,
        target: str,
        label: str,
        operation_key: str,
    ) -> str:
        previous = self.results.get(operation_key)
        if previous is not None:
            old_target, old_label, result = previous
            if (old_target, old_label) != (target, label):
                raise PermanentError("remote key reused for different intent")
            return result

        result = f"effect-{len(self.effects) + 1}"
        self.effects.append((target, label))
        self.results[operation_key] = (target, label, result)

        if self.lose_next_response:
            self.lose_next_response = False
            raise TransientError("response lost after effect committed")
        return result


def retry_transient(
    action: Callable[[], str],
    *,
    maximum_attempts: int,
    base_delay: float = 0.1,
    maximum_delay: float = 2.0,
    random_value: Callable[[], float] = random.random,
    sleep: Callable[[float], None] = time.sleep,
) -> str:
    if maximum_attempts < 1:
        raise ValueError("maximum_attempts must be positive")

    for attempt in range(1, maximum_attempts + 1):
        try:
            return action()
        except TransientError as error:
            if attempt == maximum_attempts:
                raise RetryExhausted(
                    f"transient failure after {attempt} attempts"
                ) from error
            cap = min(maximum_delay, base_delay * (2 ** (attempt - 1)))
            sleep(random_value() * cap)
    raise AssertionError("attempt loop did not return or raise")


def ensure_label_operation(
    store: OperationStore,
    service: LabelService,
    *,
    operation_key: str,
    target: str,
    label: str,
    maximum_attempts: int,
    retry_sleep: Callable[[float], None] = time.sleep,
) -> str:
    fingerprint = request_fingerprint(target=target, label=label)
    record = store.reserve(operation_key, fingerprint)

    if record.status == "succeeded":
        if record.result is None:
            raise RuntimeError("succeeded operation has no result")
        return record.result
    if record.status == "failed":
        raise PermanentError("operation requires explicit repair")

    store.mark(operation_key, "running")
    try:
        result = retry_transient(
            lambda: service.ensure_label(
                target=target,
                label=label,
                operation_key=operation_key,
            ),
            maximum_attempts=maximum_attempts,
            sleep=retry_sleep,
        )
    except RetryExhausted:
        store.mark(operation_key, "unknown")
        raise
    except PermanentError:
        store.mark(operation_key, "failed")
        raise
    else:
        store.mark(operation_key, "succeeded", result)
        return result


class RecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.database = Path(self.temporary_directory.name) / "operations.db"
        self.store = OperationStore(self.database)
        self.service = FakeLabelService()

    def tearDown(self) -> None:
        self.store.close()
        self.temporary_directory.cleanup()

    def test_lost_response_is_resumed_without_duplicate_effect(self) -> None:
        self.service.lose_next_response = True

        with self.assertRaises(RetryExhausted):
            ensure_label_operation(
                self.store,
                self.service,
                operation_key="tenant-a:run-42",
                target="account-7",
                label="reviewed",
                maximum_attempts=1,
            )

        self.assertEqual(
            self.store.get("tenant-a:run-42").status,
            "unknown",
        )
        self.assertEqual(
            self.service.effects,
            [("account-7", "reviewed")],
        )

        self.store.close()
        self.store = OperationStore(self.database)

        result = ensure_label_operation(
            self.store,
            self.service,
            operation_key="tenant-a:run-42",
            target="account-7",
            label="reviewed",
            maximum_attempts=2,
        )

        self.assertEqual(result, "effect-1")
        self.assertEqual(
            self.store.get("tenant-a:run-42").status,
            "succeeded",
        )
        self.assertEqual(
            self.service.effects,
            [("account-7", "reviewed")],
        )

    def test_key_reuse_with_different_intent_is_rejected(self) -> None:
        ensure_label_operation(
            self.store,
            self.service,
            operation_key="tenant-a:run-43",
            target="account-7",
            label="reviewed",
            maximum_attempts=1,
        )

        with self.assertRaises(KeyReuseError):
            ensure_label_operation(
                self.store,
                self.service,
                operation_key="tenant-a:run-43",
                target="account-8",
                label="reviewed",
                maximum_attempts=1,
            )

    def test_full_jitter_is_bounded_and_deterministic_in_test(self) -> None:
        delays: list[float] = []
        calls = 0

        def eventually_succeeds() -> str:
            nonlocal calls
            calls += 1
            if calls < 3:
                raise TransientError("try again")
            return "done"

        result = retry_transient(
            eventually_succeeds,
            maximum_attempts=3,
            base_delay=0.2,
            maximum_delay=1.0,
            random_value=lambda: 0.5,
            sleep=delays.append,
        )

        self.assertEqual(result, "done")
        self.assertEqual(delays, [0.1, 0.2])


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

Run it in a disposable directory:

```bash
python -m unittest -v test_recovery.py
```

The first call deliberately permits only one attempt. The fake service commits the effect and loses the response, so the local record becomes `unknown`. The restarted call uses the same key; the service returns the first result, and the local store records success without a second effect.

This lab is intentionally single-worker. A production store also needs transactional state transitions, leases or compare-and-swap, timestamps, attempt history, migrations, retention, access control, and backup behavior. Chapter 76 develops coordination between workers.

## 19. Test the recovery protocol

Exercise a crash or injected failure at every boundary:

- before intent is stored;
- after intent is stored but before the request;
- after the remote effect but before its response;
- after the response but before local success is stored;
- while renewing a lease;
- during compensation;
- after a key or remote result has expired.

Assert durable state after reopening the store in a new process, not only through the original connection. Run simultaneous attempts with the same key against the real uniqueness and isolation mechanism. Verify that changed input, stale versions, and expired authority stop rather than silently resume.

Record the test's fault point and operation key so failures remain reproducible.

## 20. Prepare an operational recovery procedure

Operators need a queryable view of:

- operations by state, age, tenant, and workflow version;
- current lease owner and expiration;
- attempt history and last classified error;
- desired and last observed state;
- remote identifiers and idempotency retention deadline;
- available reconcile, retry, compensate, abandon, and escalate actions.

Every manual action should itself be authenticated, authorized, bounded, auditable, and safe to repeat. A dashboard button must not bypass the protocol the automated worker follows.

Practice recovery with synthetic operations before an incident. A runbook that depends on expired keys or unavailable evidence is not a recovery mechanism.

## Common Misconceptions

- “A timeout means nothing happened.” The effect may have committed before the response was lost.
- “Exponential backoff makes retries safe.” It reduces load but does not prevent duplicate effects.
- “DELETE is always safe to repeat.” Application semantics, preconditions, and secondary effects still matter.
- “A checkpoint log is enough.” Recovery state needs an explicit durability and consistency contract.
- “Compensation is rollback.” It is a new business operation in a changed world.
- “Exactly once is a property of the queue.” End-to-end effects cross additional storage and service boundaries.

## Core Computer Science Concept

Recovery is a **durable state machine under partial knowledge**. A process advances only from persisted facts, and ambiguous observations remain explicit until reconciliation supplies stronger evidence.

## Engineering Connections

- Request fingerprints apply canonical serialization and hashing from Chapter 67.
- Durable intent extends the observability contract from Chapter 72 into executable recovery state.
- Fault injection turns the failure-path testing strategy from Chapter 73 into protocol evidence.
- Conditional requests and versions provide optimistic concurrency control at external boundaries.
- Leases, queues, and compare-and-swap lead into the concurrency model in Chapter 76.

## From the Field

A scheduler times out while creating an invoice and marks the job failed. An operator reruns it with a new request identifier, producing a second invoice. The original timeout was only a missing response; the first invoice already existed. A stable business operation key, fingerprint conflict check, and lookup-by-key recovery path would have converted the rerun into retrieval of the original result.

## Engineering Review

### What problem does this solve?

It lets automation continue safely when requests, responses, processes, and multi-step workflows fail at uncertain points.

### Why was it designed this way?

Stable operation identity prevents accidental duplication, durable states survive process loss, bounded retries handle transient faults, and reconciliation resolves outcomes that transport evidence cannot.

### When should I use it?

Use these patterns whenever automation mutates external state, runs unattended, processes batches, or must recover across restarts.

### When should I avoid it?

Avoid automatic retry or compensation when repetition semantics, current state, authority, or business acceptability cannot be established; require explicit review instead.

### How does this make me a better engineer?

It trains you to reason about facts versus observations, name uncertainty, define legal transitions, and design recovery before failure.

### How does this reduce waste?

It prevents duplicate effects, retry storms, abandoned partial work, repeated manual investigation, and destructive guesses after ambiguous failures.

## Handbook Principle #74

> Persist intent before effect, keep ambiguity explicit, and repeat work only under a stable identity with a bounded path to reconciliation.

## Practical Observation

Save the example as `test_recovery.py` in a disposable directory and run it. Inspect the SQLite row after the injected lost response and again after recovery. Then change the resumed label while reusing the key and confirm that fingerprint validation rejects the request before a second effect occurs.

## Looking Ahead

Idempotent operations and durable recovery still need one consistent way to build, check, package, and invoke the project. Chapter 75 creates task-runner and build interfaces that make those environments and commands repeatable locally and in CI.

## References

- [RFC 9110: HTTP Semantics — Idempotent Methods](https://www.rfc-editor.org/rfc/rfc9110.html#name-idempotent-methods)
- [Amazon Builders' Library — Timeouts, retries, and backoff with jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/)
- [AWS Well-Architected Framework — Control and limit retry calls](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_mitigate_interaction_failure_limit_retries.html)
- [Google Cloud Storage retry strategy](https://cloud.google.com/storage/docs/retry-strategy)
- [Microsoft Azure Architecture Center — Saga pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/saga)
- [Microsoft Azure Architecture Center — Compensating Transaction pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction)
- [SQLite transaction documentation](https://www.sqlite.org/lang_transaction.html)
