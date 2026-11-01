# Chapter 76 — Scheduling, Concurrency, and Work Queues

Making a command run every hour is easy. Deciding what happens after downtime, overlap, slow work, clock changes, worker crashes, or duplicate delivery is the engineering work.

The central idea is:

> Separate eligibility, admission, ownership, and effect: schedules create work, queues bound it, leases assign it temporarily, and idempotent handlers make repetition safe.

## 1. A schedule is not an execution guarantee

A scheduler decides when a run becomes eligible. It does not by itself guarantee that the process starts, finishes, runs only once, or observes the intended data.

For every scheduled automation, define:

- schedule expression and named time zone;
- acceptable start delay and completion deadline;
- behavior after missed start times;
- overlap policy;
- retry and recovery ownership;
- maximum concurrent runs and downstream request rate;
- identity, configuration, and artifact version;
- run history and alerting;
- idempotency scope.

“Daily at 02:00” leaves most of this unspecified.

## 2. Choose wall-clock or elapsed-time intent

Wall-clock schedules express calendar intent: every weekday at 09:00 in a named business time zone. Elapsed-time schedules express duration intent: 15 minutes after the previous completion.

They behave differently across:

- daylight-saving transitions;
- time-zone rule updates;
- system clock corrections;
- host suspend and restart;
- long-running jobs;
- manual runs.

Use an IANA time-zone name such as `America/Chicago` when local civil time matters. A fixed UTC offset does not model seasonal or historical changes.

Persist the originally scheduled instant separately from the actual start time. That identity helps deduplicate a run and measure schedule delay.

## 3. Define missed-run behavior

When the scheduler or host is unavailable, several start times may pass. Choose a policy:

- **skip** old occurrences and wait for the next one;
- **coalesce** all missed occurrences into one current run;
- **catch up** each missed occurrence in order;
- **catch up within a deadline** and discard stale work;
- **reconcile desired state** without replaying each interval.

The correct choice follows business semantics. A monitoring snapshot may skip. A billing period may require every partition. A state synchronizer may reconcile current state once.

Bound catch-up. Starting thousands of missed jobs simultaneously can turn recovery into another outage.

## 4. Make overlap policy explicit

If one run is still active when the next becomes eligible, the scheduler can:

- **allow** both runs;
- **forbid** or skip the new run;
- **queue** the new run for later;
- **replace** the old run after cooperative cancellation;
- **coalesce** both intents;
- **partition** them so independent keys run concurrently.

Forbid is not the same as queue. A skipped occurrence may never run. Replace is unsafe if the old process can continue mutating after the new one begins.

Scheduler-level overlap controls are useful but not a complete correctness boundary. Controller failover and network partitions can still produce duplicates. The operation must retain the idempotency and recovery protocol from Chapter 74.

## 5. Use the scheduler as a supervisor

A production scheduler should start a defined executable or task from Chapter 75 and capture its result. Avoid embedding a long shell pipeline directly in a crontab field where quoting, working directory, environment, and failure handling become obscure.

The scheduled unit should declare:

- absolute executable and working directory;
- minimal environment and configuration source;
- service identity and resource limits;
- startup and execution timeout;
- restart policy, if any;
- stdout, stderr, and structured event destination;
- success exit codes;
- cancellation signal and grace period.

Do not assume an interactive shell profile, terminal, current directory, or user `PATH` exists.

## 6. Understand scheduler-specific semantics

Different schedulers expose different contracts. For example, systemd timers can persist the last trigger and run after downtime, and can randomize activation to spread load. Kubernetes CronJobs expose time zones, starting deadlines, and overlap policies while still advising idempotent jobs.

Read the exact platform documentation for:

- clock and time-zone interpretation;
- missed-event limits;
- controller reconciliation interval;
- duplicate-start possibilities;
- whether a restart catches up;
- how cancellation and replacement work;
- retention of completed-run history.

Do not transfer assumptions from one product to another because both accept a cron-like expression.

## 7. Distinguish locks from leases

A **lock** grants exclusive access until release under the lock system's contract. A process-local mutex coordinates only threads in that process. A file lock may coordinate processes on one compatible filesystem. A database or coordination service may provide broader scope.

A **lease** grants ownership until a deadline unless renewed. Leases allow recovery after a worker disappears, but they create a critical rule:

> An expired owner must stop affecting protected state.

A worker can pause, lose its lease, and resume after another worker takes ownership. Merely checking the clock before a write is insufficient.

## 8. Add fencing to expiring ownership

A fencing token is a monotonically increasing ownership generation. Every protected write carries the token, and the resource rejects tokens older than the latest accepted generation.

```text
worker A receives lease token 41
worker A pauses past expiry
worker B receives lease token 42 and writes
worker A resumes and tries token 41
resource rejects token 41 as stale
```

Without enforcement at the resource being protected, a distributed lock or lease may prevent most overlap but cannot stop a paused stale owner.

Not every external API supports fencing. Use conditional versions, compare-and-swap, idempotent desired-state writes, partitioned ownership, or a single transactional authority where appropriate.

## 9. Use queues to decouple admission from execution

A work queue lets producers admit tasks without requiring a worker to finish immediately. A job message should contain or reference:

- stable job and idempotency identifiers;
- tenant and partition scope;
- schema and workflow version;
- immutable input reference or fingerprint;
- creation and eligibility time;
- attempt and deadline policy;
- trace or correlation context without credentials.

Keep messages small and versioned. Store large payloads in a durable system and include an integrity-protected reference. Never place a long-lived secret in a queue message.

## 10. Acknowledge only after durable completion

A common queue protocol is:

1. receive and temporarily hide or lease a message;
2. process it under an idempotency key;
3. durably record the result;
4. acknowledge or delete the message.

If the worker crashes before acknowledgement, the message can become eligible again. This is at-least-once delivery behavior, so duplicate processing must be safe.

Acknowledging before the effect is durable can lose work. Acknowledging after creates a window in which completed work is redelivered. Idempotency and durable result lookup close that window.

A visibility timeout is a lease, not proof that no other worker can ever receive the same message.

## 11. Renew ownership with bounded heartbeats

When work may outlast its initial lease, renew before expiry. A heartbeat should include the job, worker, and current lease token and should fail closed if ownership has changed.

Choose:

- initial lease longer than normal processing jitter;
- renewal interval with enough margin for transient delay;
- maximum total run time;
- behavior after renewal failure;
- cancellation deadline before ownership expires.

Do not renew forever. A stuck worker can hide work indefinitely. Long or unpredictable jobs may need smaller resumable steps and checkpoints.

## 12. Bound concurrency at the scarce resource

More workers improve throughput only until a bottleneck saturates. Bound concurrency according to:

- CPU and memory per task;
- database connections and lock contention;
- remote API quotas and latency;
- network sockets and bandwidth;
- tenant fairness;
- downstream recovery capacity.

A global worker count may still overload one dependency if each job fans out. Apply a semaphore or rate limit at the actual boundary as well as a total worker limit.

Use threads, processes, asynchronous I/O, or external workers according to the workload and failure model. Python's concurrency documentation distinguishes these mechanisms; a thread pool is not automatically suitable for long-running worker service supervision.

## 13. Apply backpressure before overload

Backpressure makes producers slow, reject, defer, or shed work when consumers cannot keep up. Without it, a queue can convert a throughput problem into unbounded memory, cost, and recovery time.

Observe:

- arrival and completion rate;
- ready and in-flight count;
- age of the oldest ready job;
- processing latency distribution;
- retry and dead-letter rate;
- saturation at downstream boundaries.

Queue depth alone can mislead. A stable depth of 10 may be healthy for millisecond work and an emergency for month-old jobs.

Define an admission limit and response: block briefly, return a retryable rejection, spill to a durable bounded queue, or drop only work whose contract permits loss.

## 14. Preserve fairness and ordering only where needed

Global ordering limits parallelism and is often unnecessary. Identify the smallest key that requires sequence, such as one account, device, or document.

Partitioning by key can provide:

- ordered processing within a key;
- concurrency across independent keys;
- ownership and rate limits per tenant;
- smaller recovery scopes.

Hot keys still serialize and can starve others. Monitor per-partition age and use fair admission rather than allowing one tenant to consume every worker.

Ordering claims need a boundary: enqueue order, delivery order, start order, or committed-effect order are different.

## 15. Retry jobs without creating poison loops

Queue retries should reuse the logical job identity and follow Chapter 74's classification and backoff rules. Persist attempt history outside a worker's memory.

After the permitted attempts or deadline, move the job to a terminal review state or dead-letter queue. Dead-lettering is not resolution. It needs:

- an owner and alert;
- original job identity and safe error evidence;
- retention and access policy;
- a repair and replay procedure;
- replay under the original idempotency contract;
- monitoring for accumulation and age.

Separate a malformed poison job from a temporary dependency outage. Retrying malformed input wastes capacity; dead-lettering an entire transient outage may overwhelm operators.

## 16. Shut workers down cooperatively

On shutdown:

1. stop admitting or claiming new work;
2. signal active handlers to finish or checkpoint;
3. continue lease renewal only while safe progress is possible;
4. acknowledge completed work;
5. release or shorten leases for work not completed;
6. exit nonzero if required state could not be preserved.

Set a grace period consistent with the scheduler or platform's termination deadline. A forced kill can occur at any point, so graceful shutdown improves efficiency but does not replace durable recovery.

Propagate cancellation through subprocesses and network calls. An abandoned child process can outlive its lease and continue mutating.

## 17. Keep a run and job history

For each scheduled occurrence, record:

- schedule identity and originally scheduled instant;
- actual start and completion times;
- artifact, configuration, and workflow versions;
- worker identity and lease generations;
- admitted, completed, retried, skipped, and dead-lettered counts;
- final status and classified error;
- links to bounded logs, metrics, and operation records.

Alert on missing expected success, not only explicit failure. A scheduler that never started the process cannot produce an application error log.

Retain history long enough to cover business reconciliation and incident discovery while applying data minimization and access controls.

## 18. Complete example: a bounded leased queue

This deterministic standard-library model uses an injected clock. It demonstrates capacity limits, lease tokens, stale-owner rejection, delayed retries, and terminal dead-letter state without real threads or sleeps:

```python
from __future__ import annotations

import unittest
from dataclasses import dataclass, replace
from typing import Callable


class QueueFull(RuntimeError):
    pass


class LeaseLost(RuntimeError):
    pass


@dataclass(frozen=True)
class Job:
    identifier: str
    payload: str
    status: str
    sequence: int
    attempts: int = 0
    available_at: float = 0.0
    owner: str | None = None
    lease_token: int | None = None
    lease_until: float | None = None
    last_error: str | None = None


@dataclass(frozen=True)
class Lease:
    job_id: str
    payload: str
    owner: str
    token: int
    attempt: int
    deadline: float


class ManualClock:
    def __init__(self) -> None:
        self.value = 0.0

    def now(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("time cannot move backward")
        self.value += seconds


class LeasedQueue:
    def __init__(
        self,
        *,
        now: Callable[[], float],
        maximum_active: int,
        maximum_attempts: int,
    ) -> None:
        if maximum_active < 1 or maximum_attempts < 1:
            raise ValueError("limits must be positive")
        self.now = now
        self.maximum_active = maximum_active
        self.maximum_attempts = maximum_attempts
        self.jobs: dict[str, Job] = {}
        self.next_sequence = 1
        self.next_token = 1

    def enqueue(self, identifier: str, payload: str) -> None:
        if not identifier:
            raise ValueError("identifier must not be empty")
        if identifier in self.jobs:
            raise ValueError("job identifier already exists")
        active = sum(
            job.status in {"ready", "in_flight"}
            for job in self.jobs.values()
        )
        if active >= self.maximum_active:
            raise QueueFull("active queue capacity reached")

        self.jobs[identifier] = Job(
            identifier=identifier,
            payload=payload,
            status="ready",
            sequence=self.next_sequence,
            available_at=self.now(),
        )
        self.next_sequence += 1

    def _expire_leases(self) -> None:
        current = self.now()
        for identifier, job in tuple(self.jobs.items()):
            if (
                job.status == "in_flight"
                and job.lease_until is not None
                and job.lease_until <= current
            ):
                self.jobs[identifier] = replace(
                    job,
                    status="ready",
                    available_at=current,
                    owner=None,
                    lease_token=None,
                    lease_until=None,
                    last_error="lease expired",
                )

    def claim(self, worker: str, *, lease_seconds: float) -> Lease | None:
        if not worker or lease_seconds <= 0:
            raise ValueError("worker and positive lease_seconds are required")
        self._expire_leases()
        current = self.now()
        eligible = sorted(
            (
                job
                for job in self.jobs.values()
                if job.status == "ready" and job.available_at <= current
            ),
            key=lambda job: job.sequence,
        )
        if not eligible:
            return None

        job = eligible[0]
        token = self.next_token
        self.next_token += 1
        updated = replace(
            job,
            status="in_flight",
            attempts=job.attempts + 1,
            owner=worker,
            lease_token=token,
            lease_until=current + lease_seconds,
            last_error=None,
        )
        self.jobs[job.identifier] = updated
        return Lease(
            job_id=updated.identifier,
            payload=updated.payload,
            owner=worker,
            token=token,
            attempt=updated.attempts,
            deadline=updated.lease_until,
        )

    def _owned_job(self, lease: Lease) -> Job:
        self._expire_leases()
        job = self.jobs[lease.job_id]
        if (
            job.status != "in_flight"
            or job.owner != lease.owner
            or job.lease_token != lease.token
        ):
            raise LeaseLost(f"lease is no longer current: {lease.job_id}")
        return job

    def heartbeat(self, lease: Lease, *, lease_seconds: float) -> Lease:
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")
        job = self._owned_job(lease)
        deadline = self.now() + lease_seconds
        self.jobs[job.identifier] = replace(job, lease_until=deadline)
        return replace(lease, deadline=deadline)

    def acknowledge(self, lease: Lease) -> None:
        job = self._owned_job(lease)
        self.jobs[job.identifier] = replace(
            job,
            status="succeeded",
            owner=None,
            lease_token=None,
            lease_until=None,
        )

    def fail(self, lease: Lease, error: str, *, retry_delay: float) -> None:
        if retry_delay < 0:
            raise ValueError("retry_delay must be nonnegative")
        job = self._owned_job(lease)
        terminal = job.attempts >= self.maximum_attempts
        self.jobs[job.identifier] = replace(
            job,
            status="dead" if terminal else "ready",
            available_at=self.now() + retry_delay,
            owner=None,
            lease_token=None,
            lease_until=None,
            last_error=error,
        )


class QueueTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = ManualClock()
        self.queue = LeasedQueue(
            now=self.clock.now,
            maximum_active=2,
            maximum_attempts=3,
        )

    def test_expired_owner_cannot_acknowledge_reclaimed_job(self) -> None:
        self.queue.enqueue("job-1", "payload")
        first = self.queue.claim("worker-a", lease_seconds=10)
        assert first is not None

        self.clock.advance(10)
        second = self.queue.claim("worker-b", lease_seconds=10)
        assert second is not None

        self.assertGreater(second.token, first.token)
        with self.assertRaises(LeaseLost):
            self.queue.acknowledge(first)

        self.queue.acknowledge(second)
        self.assertEqual(self.queue.jobs["job-1"].status, "succeeded")

    def test_capacity_applies_backpressure_to_active_work(self) -> None:
        self.queue.enqueue("job-1", "one")
        self.queue.enqueue("job-2", "two")
        with self.assertRaises(QueueFull):
            self.queue.enqueue("job-3", "three")

        lease = self.queue.claim("worker-a", lease_seconds=10)
        assert lease is not None
        self.queue.acknowledge(lease)
        self.queue.enqueue("job-3", "three")

    def test_retry_delay_and_dead_letter_limit(self) -> None:
        self.queue.enqueue("poison", "bad input")

        for attempt in range(1, 4):
            lease = self.queue.claim("worker-a", lease_seconds=10)
            assert lease is not None
            self.assertEqual(lease.attempt, attempt)
            self.queue.fail(lease, "synthetic error", retry_delay=5)

            if attempt < 3:
                self.assertIsNone(
                    self.queue.claim("worker-b", lease_seconds=10)
                )
                self.clock.advance(5)

        job = self.queue.jobs["poison"]
        self.assertEqual(job.status, "dead")
        self.assertEqual(job.attempts, 3)
        self.assertEqual(job.last_error, "synthetic error")

    def test_heartbeat_extends_only_current_lease(self) -> None:
        self.queue.enqueue("job-1", "payload")
        lease = self.queue.claim("worker-a", lease_seconds=5)
        assert lease is not None
        self.clock.advance(3)

        renewed = self.queue.heartbeat(lease, lease_seconds=5)

        self.assertEqual(renewed.deadline, 8)
        self.clock.advance(3)
        self.assertIsNone(self.queue.claim("worker-b", lease_seconds=5))


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

Save it as `test_queue.py` in a disposable directory and run:

```bash
python -m unittest -v test_queue.py
```

The queue rejects a stale acknowledgement after lease expiry because the reclaimed job has a newer token. In a real distributed system, the protected resource—not only the queue—must also enforce a fencing token or equivalent conditional write.

The model is deliberately single-process and not thread-safe. Production claiming, acknowledgement, and token generation require transactional atomicity in a durable queue or database. Its purpose is to make the state transitions testable before introducing product syntax.

## 19. Verify the unattended system

Test more than the handler:

- start at a daylight-saving transition in the configured zone;
- simulate scheduler downtime and each missed-run policy;
- run longer than one interval under every overlap policy;
- kill a worker before and after the effect and acknowledgement;
- pause a worker past lease expiry and attempt a stale write;
- saturate workers, the queue, and downstream limits;
- deliver the same job concurrently;
- expire and renew leases near their deadlines;
- fill the dead-letter path and replay one repaired item;
- terminate the service during graceful shutdown.

Use injected clocks for state-machine tests and a smaller set of real platform integration tests. Real clock tests alone are slow and flaky; simulated clocks alone cannot prove scheduler configuration.

## 20. Operate capacity as a feedback loop

Changing worker count is an operational decision. Before scaling, determine whether the bottleneck is worker capacity, a hot partition, an external quota, lock contention, or failing work being retried.

Increase capacity gradually and observe completion rate, oldest age, error rate, and downstream saturation. Decrease admission when completion cannot keep pace. Capacity that works during steady state may be unsafe during catch-up after an outage.

Document who can pause producers, drain workers, quarantine a partition, replay dead letters, and change concurrency. Each control needs audit evidence and bounded authority.

## Common Misconceptions

- “Cron runs a job exactly once.” Schedulers can miss or duplicate starts, and processes can fail independently.
- “Forbid overlap means no concurrent effects.” A stale or partitioned worker may continue after ownership changes.
- “A visibility timeout is a lock.” It is temporary delivery ownership and may not prevent duplicates.
- “More workers always reduce queue depth.” They can saturate a dependency and increase retries.
- “A dead-letter queue handles failed jobs.” It stores them; ownership and repair still need design.
- “Ordered delivery means ordered effects.” Parallel handlers and external commits can reorder completion.

## Core Computer Science Concept

Work processing is a **bounded producer-consumer system with temporary ownership**. Stability requires average admitted work not to exceed sustainable completion capacity, while leases and acknowledgements preserve progress across worker failure.

## Engineering Connections

- Scheduled jobs invoke the repeatable task interface from Chapter 75.
- Leases extend the durable state machine and unknown-outcome handling from Chapter 74.
- Bounded queues apply flow control concepts from networking to application work.
- Partition keys combine concurrency control with tenant and ordering boundaries.
- Run history applies the structured evidence model from Chapter 72.

## From the Field

A five-minute job receives a two-minute visibility timeout. After two minutes, a second worker receives the same message while the first still runs. Both call a non-idempotent billing endpoint. Extending visibility would reduce the overlap window, but only a stable billing operation key and deduplicated effect would make the duplicate delivery safe.

## Engineering Review

### What problem does this solve?

It runs work unattended without leaving time, overlap, ownership, capacity, duplicate delivery, or worker loss as implicit behavior.

### Why was it designed this way?

Separating schedules, queues, leases, and effects gives each mechanism one enforceable contract and makes failure recovery observable.

### When should I use it?

Use these patterns for recurring jobs, asynchronous work, batch processing, and any automation with multiple workers or variable arrival rate.

### When should I avoid it?

Avoid distributed queues and leases when one supervised local process with bounded work meets the reliability and scale requirement.

### How does this make me a better engineer?

It teaches you to reason about time, ownership generations, saturation, fairness, and duplicates as normal system states.

### How does this reduce waste?

It prevents overlapping damage, unbounded backlogs, retry amplification, stranded work, hot-tenant starvation, and manual recovery from invisible schedules.

## Handbook Principle #76

> Schedule intent, bound admission, lease ownership, fence stale workers, and assume every job can arrive again.

## Practical Observation

Run the queue example and change the lease from ten seconds to two while advancing the clock by three. Observe the new token and stale-owner rejection. Then reduce capacity to one and confirm that admission resumes only after the active job reaches a terminal state.

## Looking Ahead

Part VI now has stable code, evidence, recovery, build, schedule, and ownership boundaries. Chapter 77 integrates them into a complete CI/CD lifecycle that builds once, promotes immutable artifacts, constrains credentials and environments, and preserves rollback evidence.

## References

- [POSIX `crontab` specification](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/crontab.html)
- [systemd.timer documentation](https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html)
- [Kubernetes CronJob documentation](https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/)
- [Python concurrent execution documentation](https://docs.python.org/3.14/library/concurrency.html)
- [Python `queue` documentation](https://docs.python.org/3.14/library/queue.html)
- [Amazon SQS visibility timeout](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html)
- [Amazon SQS at-least-once delivery](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/standard-queues-at-least-once-delivery.html)
