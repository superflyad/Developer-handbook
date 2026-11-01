# Chapter 114 — Resilience, Timeouts, Retries, and Failure Containment

A dependency slows from 50 milliseconds to 20 seconds. Callers keep their requests open, exhaust connection and worker pools, fail health checks, and retry through several layers. One slow service becomes a system-wide outage even though no machine originally crashed.

The central idea is:

> Resilience bounds time, concurrency, retries, queues, and blast radius so a local fault becomes an explicit degraded outcome instead of unbounded work that consumes the recovery path.

## 1. Start with failure modes, not patterns

For each critical journey, ask what happens when a component or dependency is:

- unavailable;
- slow;
- intermittently failing;
- returning malformed or stale data;
- overloaded;
- partitioned from some callers;
- out of quota or capacity;
- logically corrupt;
- partially deployed or incompatible;
- recovered but cold or backlogged.

Then trace resource consequences: threads, tasks, connections, memory, queue depth, retries, locks, and downstream requests.

A pattern name is not evidence. A circuit breaker can isolate a slow dependency and can also reject healthy traffic if scoped or tuned incorrectly. The design must connect mechanism to failure mode and business outcome.

## 2. Classify faults by response

Useful classes include:

- **permanent input failure** — correct the request; do not retry;
- **authorization or policy failure** — stop or reauthorize;
- **optimistic conflict** — refresh or resolve under domain rules;
- **transient dependency failure** — a bounded retry may help;
- **overload or throttling** — reduce offered load and respect retry guidance;
- **unknown outcome** — query status or reconcile before repeating effects;
- **persistent component failure** — isolate, fail over, or degrade;
- **data corruption** — stop writes, preserve evidence, and recover deliberately.

Do not map every exception to “transient.” Retrying invalid schema, revoked access, an invariant failure, or a deterministic bug amplifies harm.

## 3. Give every journey an end-to-end deadline

A deadline is the latest useful completion time at the user's boundary. Each hop receives a remaining budget rather than starting an unrelated timeout.

```text
client objective: 2,000 ms
edge and authentication: 150 ms
application queue and work: 250 ms
dependency calls: 1,100 ms
response serialization and network: 200 ms
safety margin: 300 ms
```

Budgets must use latency distributions and parallel/serial structure, not simply divide the deadline by call count. A dependency timeout must leave time to process failure and return a useful response.

Propagate an absolute deadline or remaining duration using a trusted monotonic basis within each process. Reject work that cannot finish before expiry. Continuing after the caller abandoned the result wastes capacity and can create effects the caller retries.

## 4. Timeouts bound waiting, not remote execution

Connection, TLS, request, read-idle, write, queue, and overall deadlines cover different phases. Configure all relevant phases; a request timeout that excludes DNS or connection establishment leaves gaps.

After a timeout, the remote effect may have failed, succeeded, or still be running. Mutations require the idempotency and status-reconciliation contracts from Chapters 107 and 112.

Avoid one universal timeout. A health probe, metadata lookup, large export, and payment authorization have different service-time and consequence distributions.

Observe timeout phase and remaining budget. “Timed out” without boundary is weak evidence.

## 5. Cancel work through the call graph

Cancellation should propagate from disconnected client or expired deadline to queued and running work where safe. Dependencies should receive the reduced deadline.

Cancellation is cooperative. Code must release connections, locks, buffers, temporary files, and permits. A canceled future whose underlying I/O continues can still exhaust the system.

Some effects cannot be canceled after commitment. Return an operation identity and let the caller observe terminal state rather than pretend cancellation reversed it.

Test cancellation during queue wait, dependency call, local transaction, response loss, and cleanup.

## 6. Retry only when another attempt can improve the outcome

A retry is justified when:

- the failure is plausibly transient;
- the operation is safe to repeat or durably idempotent;
- enough deadline remains;
- the attempt will not violate rate or concurrency limits;
- the dependency is likely to have recovered;
- the caller can handle an unknown first outcome.

Retry at one owned layer when possible. If a client, gateway, service, SDK, and database driver each retry three times, one request can become hundreds of downstream attempts.

Record attempt number, total elapsed time, original operation identity, and final cause. Do not reset the end-to-end deadline for each attempt.

## 7. Use exponential backoff with jitter

Immediate synchronized retries recreate the same overload. Exponential backoff spaces attempts; jitter spreads callers across the window.

One full-jitter form is:

```text
cap_n = min(maximum_delay, base_delay * 2^attempt)
delay_n = random(0, cap_n)
```

Bound attempts, maximum delay, and total elapsed time. Respect a trustworthy server retry-after signal within the caller's deadline and policy.

Jitter is not a cure for persistent overload. Admission control and load shedding must reduce total offered work.

## 8. Use retry budgets

A retry budget caps retry traffic relative to useful original traffic or available capacity. It prevents a high error rate from converting into unlimited additional load.

Define budget scope by service, dependency, tenant, and priority. Critical recovery operations may have a reserved pool, but must remain bounded.

When the budget is exhausted, fail explicitly or queue under a business deadline. Do not hide retries as SDK internals; inventory and configure every layer.

## 9. Open circuits around failing dependencies

A circuit breaker normally has:

- **closed** — requests flow while recent outcomes are measured;
- **open** — calls fail fast or degrade for a cooldown;
- **half-open** — a limited number of probes test recovery.

Scope a breaker to an independently failing resource: shard, region, endpoint, or dependency. One global breaker can block healthy partitions because another failed.

Classify outcomes. Client validation errors should not open a dependency breaker. Slow successes can still consume capacity and may need to count toward a latency-based trigger.

Limit half-open probes so recovery is not overwhelmed. Observe transitions and provide safe operational override.

## 10. Bulkhead shared resources

Bulkheads isolate resource pools so one dependency, tenant, feature, or priority cannot consume everything:

- separate connection pools;
- bounded worker and thread pools;
- per-tenant concurrency;
- dedicated queues;
- process or cell isolation;
- separate capacity for interactive and batch work.

Isolation costs utilization and complexity. Choose boundaries from blast radius and business criticality.

A semaphore around calls is a bulkhead only if waiting is bounded and cancellation releases permits. An unbounded queue before a bounded pool merely moves exhaustion into memory and latency.

## 11. Keep queues short and explicit

For synchronous work, a long queue often converts overload into timeouts. Bound queue length or waiting time from the deadline and service rate.

When capacity is full, reject early with a clear overload response rather than accept work that cannot finish. For asynchronous work, queue age is customer latency; admission must stop when retention or objective cannot be met.

Use Little's Law from Chapter 109 to compare expected in-flight work with pool and queue size. Monitor time in queue separately from service time.

## 12. Shed load before the service collapses

Load shedding rejects lower-value or excess work to preserve useful capacity. Possible policies include:

- reject requests beyond in-flight limits;
- enforce per-tenant fairness;
- drop optional fan-out or enrichment;
- sample nonessential telemetry;
- disable expensive ranking or recommendations;
- serve a bounded stale response;
- defer batch work;
- preserve capacity for recovery and administrative access.

Choose priorities before an incident. Shedding based on arrival order alone can let one noisy tenant dominate.

Return retry guidance only when retrying later is meaningful. A client that instantly retries every shed request defeats the control.

## 13. Design graceful degradation as a product state

Degradation should preserve core invariants and expose reduced capability honestly:

- read-only mode when writes are unsafe;
- task board without search ranking;
- cached public data with visible age;
- accept durable work for later completion;
- omit optional analytics or previews;
- restrict operations to one healthy region.

Never degrade by bypassing authorization, durability, tenant isolation, or data validation. A fallback that returns plausible fabricated data may be worse than an explicit failure.

Exercise degraded paths regularly. Rare emergency code often fails when first needed.

## 14. Define dependency fallbacks carefully

A fallback can be cached data, alternate provider, default value, reduced query, or manual process. It needs:

- trigger and scope;
- correctness and freshness consequence;
- security equivalence;
- capacity and independent failure mode;
- switch and switchback behavior;
- observability;
- testing and owner.

Two providers are not independent if they share DNS, identity, network, control plane, data source, or quota. Switching to an untested backup during an incident can expand the blast radius.

Avoid fallback loops where A calls B and B falls back to A.

## 15. Treat health signals as routing contracts

**Liveness** asks whether a process should be restarted. **Readiness** asks whether it should receive new traffic. **Startup** protects slow initialization from premature liveness failure.

Health checks should be cheap, bounded, and meaningful. A liveness check that fails because an external dependency is down can restart every otherwise healthy caller and worsen the outage.

Readiness may consider essential local dependencies, warm-up, and ability to meet request bounds. It should not flap on one transient sample. Use hysteresis and removal/drain behavior.

An HTTP 200 from a health endpoint does not prove the business journey works. Use synthetic transactions and SLOs separately.

## 16. Redundancy must cross the failed boundary

Extra instances help only if they do not share the same cause of failure. Examine:

- process, host, rack, zone, region, account, and provider;
- network, DNS, identity, key, certificate, and control plane;
- software version and configuration;
- data corruption and operator action;
- capacity and quota.

Active-active capacity can provide fast failover but adds consistency and routing complexity. Active-passive can simplify authority but requires tested promotion and sufficient warm capacity.

Redundancy is not recovery from logical corruption; all replicas can faithfully copy bad state.

## 17. Define recovery objectives per journey

Recovery point objective bounds acceptable data loss. Recovery time objective bounds restoration time. Service-level objectives bound normal user experience. They inform one another but are not synonyms.

For each critical journey, define:

- failed scope;
- detection objective;
- containment action;
- degraded capability;
- failover or restore path;
- RPO and RTO;
- dependency and identity recovery;
- business verification;
- return-to-normal and backlog drain.

Restore tests must include application integrity, keys, policy, network, DNS, and capacity. A database restored without its identity and encryption dependencies is not recovered.

## 18. Prevent recovery from causing a second outage

Recovery introduces load:

- cold caches and connection pools;
- replica catch-up;
- queue replay;
- customer retries;
- data backfill;
- traffic rebalancing;
- autoscaling and warm-up.

Ramp traffic gradually, limit retries and replay, preserve headroom, and monitor the recovering dependency. Do not close every circuit simultaneously and release a synchronized backlog.

Switchback deserves the same care as failover. Confirm state convergence and authority before returning traffic.

## 19. Use cells to bound blast radius

A cell contains a subset of tenants or traffic with separate compute and, where justified, data and dependencies. Failure affects that cell rather than the entire fleet.

Cells require placement, routing, capacity, migration, per-cell observability, and control-plane resilience. Shared global dependencies can defeat isolation.

Choose cell size from tenant distribution, operational cost, recovery, and acceptable blast radius. Keep cross-cell operations rare or explicitly coordinated.

## 20. Protect control and recovery planes

During overload, operators still need deployment, configuration, status, and recovery access. Reserve capacity and separate permissions for control-plane operations.

Do not let customer traffic exhaust the same pool used for health, scaling, or incident mitigation. Conversely, a faulty control loop should not rewrite all cells simultaneously.

Use staged rollout, rate limits, circuit breakers, and manual stops for automation that can amplify failure.

## 21. Run failure experiments as hypotheses

A controlled resilience experiment should:

1. define a measurable steady state at the user boundary;
2. state the expected behavior under a realistic fault;
3. limit blast radius and duration;
4. define automatic and manual stop conditions;
5. verify observability and on-call awareness;
6. introduce one understood variable;
7. compare outcomes with the hypothesis;
8. restore state and capture follow-up.

Start in a disposable or isolated environment, then increase realism only with authorization and evidence. Never improvise destructive production faults.

The Principles of Chaos Engineering emphasizes attempts to disprove a steady-state hypothesis. A successful experiment produces evidence, not merely injected failure.

## 22. Model dependency failure for the task platform

For interactive task reads:

- one 2-second end-to-end deadline is divided across authentication, task storage, and response;
- the search dependency has a separate short timeout and breaker;
- search failure degrades to direct task access, not authorization bypass;
- per-tenant and per-dependency bulkheads preserve fairness;
- stale board summaries are allowed only within their cache contract;
- overload sheds optional previews before task reads and assignments.

For writes, a lost response uses the idempotency key and status lookup. Notification failure remains asynchronous and does not retry in the interactive call. Recovery drains notification backlog under provider rate limits.

## 23. Encode a resilience contract

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class DependencyPolicy:
    name: str
    timeout_ms: int
    maximum_attempts: int
    retry_budget_percent: int
    idempotent: bool
    circuit_breaker: bool
    concurrency_limit: int

    def validate(self, remaining_deadline_ms: int) -> None:
        if not self.name.strip() or self.timeout_ms <= 0:
            raise ValueError("dependency needs a name and timeout")
        if self.timeout_ms >= remaining_deadline_ms:
            raise ValueError("dependency consumes the entire remaining deadline")
        if self.maximum_attempts > 1 and not self.idempotent:
            raise ValueError("retry can repeat a non-idempotent effect")
        if not 0 <= self.retry_budget_percent <= 100:
            raise ValueError("retry budget is invalid")
        if not self.circuit_breaker or self.concurrency_limit <= 0:
            raise ValueError("dependency lacks failure containment")


@dataclass(frozen=True)
class ResilienceContract:
    end_to_end_deadline_ms: int
    dependency: DependencyPolicy
    queue_wait_bounded: bool
    load_shedding_defined: bool
    degradation_preserves_security: bool
    failure_domains_independent: bool
    rpo_defined: bool
    rto_defined: bool
    recovery_load_bounded: bool
    experiment_stop_conditions: bool

    def validate(self) -> None:
        if self.end_to_end_deadline_ms <= 0:
            raise ValueError("journey needs an end-to-end deadline")
        self.dependency.validate(self.end_to_end_deadline_ms)
        if not self.queue_wait_bounded or not self.load_shedding_defined:
            raise ValueError("overload has no bounded response")
        if not self.degradation_preserves_security:
            raise ValueError("degradation weakens security invariants")
        if not self.failure_domains_independent:
            raise ValueError("redundancy shares the failed boundary")
        if not self.rpo_defined or not self.rto_defined:
            raise ValueError("recovery objectives are incomplete")
        if not self.recovery_load_bounded:
            raise ValueError("recovery can cause a second overload")
        if not self.experiment_stop_conditions:
            raise ValueError("failure experiment lacks stop conditions")
```

Executable tests exercise the contract:

```python
import unittest

from resilience_contract import DependencyPolicy, ResilienceContract


def valid_contract() -> ResilienceContract:
    dependency = DependencyPolicy("task store", 800, 2, 15, True, True, 80)
    return ResilienceContract(
        2000, dependency, True, True, True, True,
        True, True, True, True,
    )


class ResilienceContractTests(unittest.TestCase):
    def test_complete_contract_is_accepted(self) -> None:
        valid_contract().validate()

    def test_dependency_cannot_consume_deadline(self) -> None:
        contract = valid_contract()
        fields = {**contract.dependency.__dict__, "timeout_ms": 2000}
        with self.assertRaisesRegex(ValueError, "entire"):
            ResilienceContract(2000, DependencyPolicy(**fields), True, True,
                               True, True, True, True, True, True).validate()

    def test_nonidempotent_retry_is_rejected(self) -> None:
        contract = valid_contract()
        fields = {**contract.dependency.__dict__, "idempotent": False}
        with self.assertRaisesRegex(ValueError, "non-idempotent"):
            ResilienceContract(2000, DependencyPolicy(**fields), True, True,
                               True, True, True, True, True, True).validate()

    def test_missing_containment_is_rejected(self) -> None:
        contract = valid_contract()
        fields = {**contract.dependency.__dict__, "concurrency_limit": 0}
        with self.assertRaisesRegex(ValueError, "containment"):
            ResilienceContract(2000, DependencyPolicy(**fields), True, True,
                               True, True, True, True, True, True).validate()

    def test_unbounded_overload_is_rejected(self) -> None:
        contract = valid_contract()
        fields = {**contract.__dict__, "load_shedding_defined": False}
        with self.assertRaisesRegex(ValueError, "overload"):
            ResilienceContract(**fields).validate()

    def test_insecure_degradation_is_rejected(self) -> None:
        contract = valid_contract()
        fields = {**contract.__dict__, "degradation_preserves_security": False}
        with self.assertRaisesRegex(ValueError, "security"):
            ResilienceContract(**fields).validate()

    def test_correlated_redundancy_is_rejected(self) -> None:
        contract = valid_contract()
        fields = {**contract.__dict__, "failure_domains_independent": False}
        with self.assertRaisesRegex(ValueError, "failed boundary"):
            ResilienceContract(**fields).validate()

    def test_unbounded_recovery_is_rejected(self) -> None:
        contract = valid_contract()
        fields = {**contract.__dict__, "recovery_load_bounded": False}
        with self.assertRaisesRegex(ValueError, "second overload"):
            ResilienceContract(**fields).validate()

    def test_experiment_needs_stop_conditions(self) -> None:
        contract = valid_contract()
        fields = {**contract.__dict__, "experiment_stop_conditions": False}
        with self.assertRaisesRegex(ValueError, "stop conditions"):
            ResilienceContract(**fields).validate()


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

Save the blocks as `resilience_contract.py` and `test_resilience_contract.py`, then run:

```bash
python -m unittest -v test_resilience_contract.py
```

A production review should derive deadlines from user objectives, inspect every retrying layer, measure timeout phases, test pool and queue saturation, verify breaker scope, exercise degraded modes, restore data, control recovery traffic, and run authorized failure experiments with business-level steady-state checks.

## 24. Review resilience and containment

```text
critical journey, failure modes, business consequence, and degraded outcome:
invalid, policy, conflict, transient, overload, unknown, persistent, and corrupt classes:
end-to-end deadline, hop budgets, safety margin, propagation, and expiry behavior:
DNS, connect, TLS, queue, request, read, write, overall, and cleanup timeouts:
cancellation propagation, resource release, commit point, status, and late effect:
retryable errors, safe repetition, owner layer, attempts, deadline, and evidence:
backoff base, cap, jitter, retry-after, retry budget, and amplification:
breaker scope, signals, window, open, half-open probes, fallback, and override:
bulkhead tenant, dependency, priority, pools, queues, permits, and cancellation:
queue capacity, wait bound, admission, rejection, age, and source envelope:
load-shedding priority, fairness, optional work, retry guidance, and observability:
degraded mode, product semantics, security, durability, freshness, and exercise:
fallback trigger, correctness, independence, capacity, switchback, and loops:
liveness, readiness, startup, dependency scope, hysteresis, drain, and synthetic test:
redundancy failure domains, authority, capacity, corruption, and promotion:
detection, containment, RPO, RTO, restore, validation, backlog, and normal return:
cold cache, retries, replay, catch-up, ramp, headroom, and second-outage prevention:
cell placement, routing, shared dependencies, migration, blast radius, and cost:
steady-state hypothesis, realistic fault, scope, stop, restore, and findings:
```

## Common Misconceptions

- “Retries improve reliability.” They improve some transient outcomes and can amplify overload into collapse.
- “A timeout means the operation failed.” The remote outcome may be unknown.
- “Each service should use its own full timeout.” Hop budgets must fit one end-to-end deadline.
- “Exponential backoff prevents retry storms.” Without jitter and budgets, callers can remain synchronized or excessive.
- “Circuit breakers replace retries.” They stop calls likely to fail; bounded retries address transient failures.
- “A bounded worker pool prevents overload.” An unbounded queue in front still accumulates work and latency.
- “Fail open is more available.” It can overload the source or violate security.
- “More replicas mean independent redundancy.” Shared control planes, configurations, and data can fail together.
- “A green health endpoint proves the service works.” It does not prove a business journey.
- “Chaos engineering means randomly breaking production.” It is a bounded hypothesis-driven experiment with stop conditions.

## Core Computer Science Concept

This chapter applies **deadlines, feedback control, queue bounds, randomized backoff, finite-state circuit breakers, resource partitioning, admission control, and fault containment**. Reliability comes from limiting work and dependency propagation under abnormal conditions, not from assuming failures disappear through repetition.

## Engineering Connections

- Timeouts and transport failures build on Chapters 57, 58, 59, 70, and 74.
- Capacity and queues apply Chapters 76, 109, and 112.
- Consistency and unknown outcomes use Chapters 107 and 110.
- Failure domains and orchestration extend Chapters 88, 91, 103, and 113.
- Chapter 115 ensures resilience modes preserve security, privacy, and tenant boundaries.

## From the Field

A shared identity service slows. Every frontend waits 30 seconds, then retries twice. Worker pools fill, readiness fails, orchestrators restart healthy instances, cold caches increase identity traffic, and the entire product fails. A two-second propagated deadline, separate identity bulkhead, bounded retry budget, breaker, cached session contract, and liveness check independent of the remote service would contain the original fault.

## Engineering Review

### What problem does this solve?

It prevents one slow, failed, or overloaded dependency from consuming every caller and turning local impairment into a cascading outage.

### Why was it designed this way?

Cascades are work amplification and resource exhaustion. Deadlines, budgets, bulkheads, breakers, and shedding bound that amplification.

### When should I use it?

Use it for every remote call, shared resource, queue, critical journey, failover path, and recovery procedure in a production system.

### When should I avoid it?

Avoid adding complex breakers or fallbacks to simple local operations with no shared failure surface. Use the smallest mechanism that bounds the real risk.

### How does this make me a better engineer?

It teaches you to budget time end to end, inventory hidden retries, design overload behavior, distinguish health signals, and treat recovery as load.

### How does this reduce waste?

It reduces zombie work, retry amplification, oversized queues, restart loops, correlated redundancy, unused failovers, insecure degradation, and recovery procedures that cause second incidents.

## Handbook Principle #114

> A resilient system spends bounded time and capacity on failure, preserves its critical invariants while degrading, and recovers slowly enough not to recreate the incident.

## Practical Observation

Trace one request through every timeout and retrying layer. Multiply maximum attempts across layers, add worst-case waiting, and compare with the user deadline and dependency capacity. If the arithmetic surprises you, the current resilience behavior is accidental.

## Looking Ahead

Chapter 115 treats assets, identities, trust boundaries, privacy, abuse, and tenant isolation as architecture inputs—and verifies that normal, degraded, administrative, and recovery paths preserve them.

## References

- [Google SRE Book — Addressing Cascading Failures](https://sre.google/sre-book/addressing-cascading-failures/)
- [Google SRE Book — Handling Overload](https://sre.google/sre-book/handling-overload/)
- [AWS Builders' Library — Timeouts, retries, and backoff with jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/)
- [AWS Well-Architected — Control and limit retry calls](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_mitigate_interaction_failure_limit_retries.html)
- [Microsoft Azure Architecture Center — Circuit Breaker](https://learn.microsoft.com/en-us/azure/architecture/patterns/circuit-breaker)
- [Microsoft Azure Architecture Center — Bulkhead](https://learn.microsoft.com/en-us/azure/architecture/patterns/bulkhead)
- [Principles of Chaos Engineering](https://principlesofchaos.org/)
- [Chapter 109 — Capacity, Partitioning, and Horizontal Scale](109-capacity-partitioning-and-horizontal-scale.md)
- [Chapter 113 — Coordination, Leadership, and Distributed Time](113-coordination-leadership-and-distributed-time.md)
