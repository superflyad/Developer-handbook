# Chapter 126 — Load Testing, Capacity Planning, and Failure Injection

A system is not ready merely because it handles today's average traffic. It must satisfy its user contract during peaks, growth, dependency loss, deployments, cache churn, and the delay before new capacity becomes useful. Load testing turns those expectations into experiments. Capacity planning converts the evidence into operating headroom. Failure injection verifies that the system degrades and recovers as designed.

These are one discipline. A throughput number without an SLO can reward unusable work. A forecast without a measured resource-to-service relationship is arithmetic on an assumption. A fault test without a representative workload may prove only that an idle system survives. The goal is to discover the first limit safely, before users do, and preserve enough evidence to repeat the conclusion after the system changes.

This chapter does not cover internet-scale traffic generators, destructive production chaos, or precise forecasting models.

## 1. Begin with a falsifiable capacity question

“How fast is it?” is too vague. Define one question with a workload, user contract, environment, and decision:

> Can Atlas Task Service sustain 900 representative API operations per second for 30 minutes, keep successful requests within the 300 ms p99 and 0.5% error SLO, retain 30% recoverable headroom, and recover within 120 seconds after one worker group becomes unavailable?

That question identifies what must remain equivalent between trials. Record:

- the application artifact, configuration, schema, and infrastructure shape;
- request mix, payload distribution, tenant skew, session behavior, and think time;
- cache and data state at the beginning of each phase;
- arrivals, completions, rejections, retries, and abandoned work;
- latency distribution, error classification, saturation, queue depth, and cost;
- the injected event, blast radius, abort conditions, and recovery objective.

A test is useful when it can disprove the claim. If every outcome is interpreted as success, the exercise is a demonstration, not an experiment.

## 2. Model demand before generating it

Production traffic is a distribution, not one requests-per-second number. Build a workload model from observed journeys and explicit future assumptions.

For an API, include:

- operation mix, such as 50% reads, 20% searches, 20% updates, and 10% exports;
- payload sizes and result cardinality;
- hot and cold tenants, keys, and partitions;
- authentication, authorization, pagination, and conditional requests;
- new and reused connections;
- background jobs, compaction, backups, and scheduled work;
- valid requests, expected invalid requests, cancellations, and timeouts.

Use production telemetry to form the baseline, but do not copy sensitive records into the test environment. Generate representative cardinality, shape, skew, and relationships. Add known launch traffic and growth separately so an uncertain forecast is not mistaken for an observation.

Keep a versioned workload fingerprint. If the request mix changes between two builds, a throughput difference cannot be assigned to the code change alone.

## 3. Choose an open or closed load model deliberately

A **closed model** keeps a fixed number of workers or users in flight. Each virtual user begins new work after its previous work and optional think time finish. This is appropriate for a bounded population, such as 500 interactive sessions or 20 batch workers.

An **open model** starts work according to an arrival schedule independent of prior response time. This is appropriate when external arrivals do not slow merely because the system does: webhooks, messages, scheduled jobs, and a public request stream.

The distinction changes what overload looks like. In a closed model, slower responses make each worker issue fewer requests. Offered load falls at the moment the service becomes slow. An open model continues the intended arrivals, so queues, rejection, or shedding become visible.

Neither model is universally correct. Model the real feedback loop. For a browser journey, a closed session model may capture user think time, while an open model separately tests an ingress event stream. State the reason in the plan.

## 4. Prevent coordinated omission

Coordinated omission occurs when the load generator waits for a slow response before scheduling work that should have arrived during the wait. The missing requests also remove their waiting time from the latency distribution. A service pauses for five seconds, but the report contains one five-second result instead of the queue of delayed arrivals that users would have experienced.

For arrival-driven traffic:

- schedule arrivals independently of completions;
- record intended arrival time, actual start time, and completion time;
- include generator-side queueing or dropped arrivals;
- ensure the generator has enough local capacity;
- report service time and end-to-end response time separately.

Do not “fix” an overloaded generator by silently reducing demand. If the generator cannot maintain the schedule, that trial does not support a target-rate conclusion.

## 5. Separate arrivals, starts, and completions

At every interval, record at least:

```text
offered arrivals = 1,000/s
admitted starts  =   930/s
completions      =   905/s
explicit rejects =    70/s
timeouts         =    20/s
queue growth     =     5/s
```

Throughput alone hides loss. Counting only completions might call this “905 requests per second” while ignoring that nearly 10% of intended work did not complete and the queue still grew.

Reconcile the flow over the complete test:

```text
arrivals ≈ completions + explicit failures + cancellations
         + work still queued or running + generator drops
```

The equation reveals missing instrumentation and work that merely moved outside the measurement window.

## 6. Warm the system without hiding cold behavior

Runtime compilation, connection establishment, lazy initialization, filesystem pages, database buffers, application caches, and autoscaling all change during a test. A warm-up phase keeps startup effects from contaminating a steady-state measurement, but cold behavior may itself be a user requirement.

Use named phases:

1. reset or document initial state;
2. verify the environment at low load;
3. warm until chosen signals stabilize;
4. measure for a fixed interval;
5. inject the bounded event;
6. observe recovery and drain;
7. return to baseline and verify cleanup.

Define “warm” with evidence—stable compilation activity, cache hit ratio, connection count, and latency—not an arbitrary sleep. Run separate cold-start, empty-cache, and scale-from-minimum scenarios when those transitions matter in production.

## 7. Measure distributions and bad outcomes

An average compresses away the experiences most likely to violate an SLO. Report latency percentiles for the same eligible events and time window as the production SLI. Include p50, p90, p95, p99, and a high-tail view when sample volume supports it.

Percentiles need context:

- a p99 from 200 samples describes roughly the two slowest observations;
- combining per-host p99 values does not produce the fleet p99;
- a successful-request percentile excludes failures unless the error SLI reports them;
- a client timeout truncates server latency unless abandoned work remains observable;
- one full-test percentile can hide a five-minute overload interval.

Plot time-windowed latency, errors, arrivals, and saturation together. Retain histograms or raw bounded samples when practical so thresholds can be recomputed consistently.

## 8. Find the knee before the cliff

Increase offered load in controlled steps while observing completions, latency, errors, queue depth, and resource saturation. The useful limit is rarely the last point before a crash.

Near the **knee** of the curve:

- throughput gains begin to flatten;
- latency and queueing rise faster;
- error or rejection probability increases;
- one resource remains persistently busy;
- small bursts take longer to drain.

Beyond the knee, additional arrivals mostly create waiting and retries. Declare a safe capacity below that region, where the complete SLO still holds and the system can absorb expected variation. The breaking point is diagnostic evidence, not an operating target.

## 9. Locate the first constrained resource

Carry forward the cross-layer method from Chapter 125. Correlate the first SLO breach with:

- CPU run queues, throttling, and concurrency;
- allocation, garbage collection, and memory pressure;
- connection, thread, worker, and request pools;
- device latency, operations, bandwidth, and queue depth;
- database plans, locks, buffers, and active sessions;
- dependency latency, quotas, rate limits, and failures;
- queue age and backlog, not merely queue length.

High utilization is not sufficient proof. A database may be 95% busy while an application pool serializes all callers before they reach it. Change one suspected constraint and repeat the same workload. If the knee moves while the contract remains equivalent, the causal claim strengthens.

## 10. Express capacity in service units

Infrastructure units are inputs. Users consume service units: searches per second, active sessions, events per minute, or gigabytes processed within a deadline.

Measure the relationship:

```text
safe service capacity per replica = 240 representative operations/s
peak required service capacity    = 2,400 representative operations/s
minimum healthy replicas          = 10
```

The ratio is conditional on artifact, workload mix, data shape, dependencies, and SLO. Re-measure after code, runtime, schema, instance, or traffic changes. “This machine handled 10,000 QPS last year” is not a durable capacity fact.

For mixed workloads, use weighted service units only when the weights remain calibrated. A search over a large tenant and a cached point lookup are not interchangeable requests.

## 11. Reserve headroom for uncertainty and recovery

Headroom is the space between expected demand and safe capacity. It absorbs forecast error, traffic variation, rebalancing, maintenance, dependency slowdown, and the time required to add usable capacity.

One simple expression is:

```text
headroom ratio = (safe capacity - planned peak demand) / safe capacity
```

If safe capacity is 3,000 operations per second and planned peak is 2,100, headroom is 30%. This is not automatically enough. Test the largest credible concurrent loss and the recovery path.

Distinguish:

- **provisioned headroom** already serving or ready;
- **elastic headroom** that depends on metrics, scheduling, startup, and warm-up;
- **downstream headroom** in databases, queues, APIs, and quotas;
- **operational headroom** needed for rollouts and repair.

Capacity that arrives after the SLO window is not headroom for that event.

## 12. Measure scaling lag end to end

Autoscaling is a delayed control loop. It must observe demand, aggregate a signal, decide, provision, schedule, start, become ready, warm, and receive balanced work. A test that ends when scaling begins proves little.

Record timestamps for:

```text
load increase
metric visibility
scaling decision
resource requested
resource scheduled
process started
readiness accepted
traffic received
SLO restored
```

Test whether the chosen signal leads user pain. CPU can lag behind queue growth; queue age or concurrency may better express pending work. Validate scale-down too: stabilization must prevent oscillation, and removing capacity must not interrupt long work or erase the recovery margin.

Keep enough baseline capacity for bursts that arrive faster than the measured scale-up path.

## 13. Use soak tests to expose accumulation

A short peak test finds immediate saturation. A soak test runs a representative, sustainable workload long enough to expose accumulation:

- memory, descriptor, socket, thread, or connection leaks;
- queue drift and retry amplification;
- cache churn and unbounded metadata;
- storage growth, compaction, checkpoints, and log rotation;
- token refresh, credential expiry, and scheduled jobs;
- gradual thermal or quota throttling;
- performance changes as data volume grows.

Graph rates and totals. A stable error rate can coexist with an ever-growing backlog. Fit no elaborate forecast when a simple monotonic resource count already proves the system cannot reach steady state.

A soak test is successful when workload, queues, resource ownership, and latency converge to bounded behavior and the system returns to baseline afterward.

## 14. Plan failure injection as an experiment

Failure injection is not random breakage. Start with a steady-state hypothesis expressed in user-visible signals:

> During the loss of one worker group, successful task updates continue below 300 ms p99, errors remain below 0.5%, no accepted update is lost, and normal headroom returns within 120 seconds.

Then define:

- the real event represented by the fault;
- a control and an experimental group where possible;
- affected tenants, nodes, region, or percentage of traffic;
- exact start, duration, and restoration action;
- SLO, correctness, durability, and recovery observations;
- automated abort thresholds and a named operator;
- evidence required to declare recovery.

Inject one interpretable event first: latency, connection refusal, process loss, dependency throttling, corrupted response, or capacity removal. Compound failures are valuable only after their individual effects are understood.

## 15. Bound the blast radius

Move through progressively more representative environments and scopes. A sensible path is model or unit test, local integration, dedicated test environment, isolated staging slice, then a narrowly scoped production experiment when the value and safeguards justify it.

Before any shared-environment experiment:

- identify affected users and data;
- cap traffic, duration, and resource consumption;
- protect control-plane and recovery capacity;
- pause conflicting deployments and operations;
- confirm observability and rollback paths;
- establish an immediate stop mechanism;
- communicate ownership and timing.

An abort threshold is a trigger, not a meeting. Automate it when possible. Stop on correctness or durability uncertainty even if latency remains acceptable.

## 16. Verify degradation, not only survival

Healthy overload behavior often means doing less work deliberately. Test admission control, priority, load shedding, bounded queues, timeouts, retry budgets, circuit breaking, and degraded responses.

Ask:

- Does the service reject early or accept work it cannot finish?
- Are high-priority operations isolated from expensive bulk work?
- Do retries decrease total success by amplifying load?
- Does a timeout cancel downstream work?
- Is degradation explicit to clients and operators?
- Does recovery drain old work before admitting a new flood?

A process that remains alive while every request times out has not survived in the service sense. Judge the steady-state user contract, not host uptime.

## 17. Test recovery as a separate phase

Removing the fault is not recovery. The system may face a backlog, cold cache, re-election, rebalance, replay, repair, or retry wave.

Measure:

- time until successful service resumes;
- time until latency and errors meet the SLO;
- time until backlog and queue age return to bounds;
- time until redundancy and headroom are restored;
- correctness reconciliation and durable-data checks;
- operator actions required.

Define the recovery objective before the test. Continue observation long enough to detect a second failure caused by drain pressure. If manual intervention is expected, exercise the actual runbook and record decision time, permissions, commands, and verification.

## 18. Include cost in the capacity result

Capacity is not “maximum throughput regardless of price.” Record the cost of the generator, service, data tier, network, observability, and any temporary overprovisioning for the same test window.

Useful comparisons include:

```text
cost per 1 million successful representative operations
cost per active tenant at the target SLO
cost of reserved headroom per month
cost of one recovery rehearsal
```

Do not optimize unit cost by operating at the cliff. The least expensive steady-state configuration can be the most expensive incident configuration. Compare cost at the required SLO, failure tolerance, and recovery objective.

Treat load-test traffic as spend with an owner and ceiling. A runaway generator or autoscaler is itself a failure mode.

## 19. Make trials reproducible and comparable

Store the test plan next to the code. For every trial, retain:

- source revision and immutable artifact identity;
- infrastructure, runtime, schema, flags, and dependency versions;
- generator version, placement, clocks, and resource use;
- workload fingerprint and sanitized data generator version;
- phase timestamps and injected event record;
- raw or loss-preserving metrics and dashboard snapshot;
- result, anomalies, cost, and conclusion.

Repeat trials and report variation. Random noise, noisy neighbors, cache placement, and background work can reverse a small difference. Change one primary variable per comparison. When that is impossible, say what changed and narrow the conclusion.

Never compare a warmed candidate against a cold baseline or a smaller dataset against a production-shaped one.

## 20. Encode the experiment contract

The following model does not generate traffic. It makes the evidence and safety obligations reviewable before a tool runs:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class CapacityPlan:
    question: str
    artifact_and_environment: str
    workload_fingerprint: str
    load_model: str
    load_model_reason: str
    target_arrival_rate: float
    warmup_seconds: int
    measurement_seconds: int
    repetitions: int
    representative_data: bool
    controls_coordinated_omission: bool
    preserves_correctness_and_durability: bool
    slo_p99_ms: float
    slo_error_ratio: float
    required_headroom_ratio: float
    fault: str
    blast_radius_percent: float
    abort_error_ratio: float
    recovery_objective_seconds: float
    cost_ceiling: float
    owner_and_runbook: str

    def validate(self) -> None:
        required = (
            self.question,
            self.artifact_and_environment,
            self.workload_fingerprint,
            self.load_model_reason,
            self.fault,
            self.owner_and_runbook,
        )
        if not all(value.strip() for value in required):
            raise ValueError("plan lacks identity, rationale, fault, or ownership")
        if self.load_model not in {"open", "closed"}:
            raise ValueError("load model must be open or closed")
        if self.target_arrival_rate <= 0 or self.measurement_seconds <= 0:
            raise ValueError("load and measurement duration must be positive")
        if self.warmup_seconds < 0 or self.repetitions < 3:
            raise ValueError("warm-up or repetition plan is insufficient")
        if not self.representative_data:
            raise ValueError("data shape cannot support a capacity conclusion")
        if self.load_model == "open" and not self.controls_coordinated_omission:
            raise ValueError("open workload does not control coordinated omission")
        if not self.preserves_correctness_and_durability:
            raise ValueError("test weakens system semantics")
        if self.slo_p99_ms <= 0 or not 0 <= self.slo_error_ratio < 1:
            raise ValueError("SLO is invalid")
        if not 0 <= self.required_headroom_ratio < 1:
            raise ValueError("headroom ratio is invalid")
        if not 0 < self.blast_radius_percent <= 100:
            raise ValueError("blast radius is invalid")
        if not 0 < self.abort_error_ratio < 1:
            raise ValueError("abort threshold is invalid")
        if self.abort_error_ratio <= self.slo_error_ratio:
            raise ValueError("abort threshold must exceed the SLO error ratio")
        if self.recovery_objective_seconds <= 0 or self.cost_ceiling <= 0:
            raise ValueError("recovery objective and cost ceiling must be positive")


@dataclass(frozen=True)
class CapacityResult:
    plan: CapacityPlan
    offered_rate: float
    safe_capacity_rate: float
    p99_ms: float
    error_ratio: float
    recovered_in_seconds: float
    correctness_verified: bool
    cost: float

    def validate(self) -> None:
        self.plan.validate()
        if min(self.offered_rate, self.safe_capacity_rate, self.p99_ms) <= 0:
            raise ValueError("result contains invalid rate or latency")
        if not 0 <= self.error_ratio <= 1 or self.recovered_in_seconds < 0:
            raise ValueError("result contains invalid errors or recovery time")
        if not self.correctness_verified:
            raise ValueError("correctness was not verified after recovery")
        if self.cost < 0:
            raise ValueError("cost is invalid")

    def meets_contract(self) -> bool:
        self.validate()
        usable_rate = self.safe_capacity_rate * (1 - self.plan.required_headroom_ratio)
        return all((
            self.offered_rate <= usable_rate,
            self.p99_ms <= self.plan.slo_p99_ms,
            self.error_ratio <= self.plan.slo_error_ratio,
            self.recovered_in_seconds <= self.plan.recovery_objective_seconds,
            self.cost <= self.plan.cost_ceiling,
        ))
```

Validation prevents a green result from a toy dataset, one lucky run, an unsafe fault, weakened durability, or a hidden cost overrun. `meets_contract()` then evaluates the planned peak against safe capacity after reserving headroom.

## 21. Test the experiment contract

```python
from dataclasses import replace
import unittest

from capacity_experiment import CapacityPlan, CapacityResult


def valid_plan() -> CapacityPlan:
    return CapacityPlan(
        question="Can task updates meet the SLO after one worker group fails?",
        artifact_and_environment="api@sha256:abc; schema=42; staging-prod-shape",
        workload_fingerprint="task-mix-v7; tenant-skew-v3; payloads-v2",
        load_model="open",
        load_model_reason="external API arrivals continue during slow responses",
        target_arrival_rate=900,
        warmup_seconds=600,
        measurement_seconds=1_800,
        repetitions=5,
        representative_data=True,
        controls_coordinated_omission=True,
        preserves_correctness_and_durability=True,
        slo_p99_ms=300,
        slo_error_ratio=0.005,
        required_headroom_ratio=0.30,
        fault="remove one worker group for 90 seconds",
        blast_radius_percent=10,
        abort_error_ratio=0.03,
        recovery_objective_seconds=120,
        cost_ceiling=250,
        owner_and_runbook="performance team; runbook CAP-17",
    )


def valid_result() -> CapacityResult:
    return CapacityResult(
        plan=valid_plan(),
        offered_rate=900,
        safe_capacity_rate=1_400,
        p99_ms=245,
        error_ratio=0.003,
        recovered_in_seconds=88,
        correctness_verified=True,
        cost=180,
    )


class CapacityExperimentTests(unittest.TestCase):
    def test_complete_result_meets_contract(self):
        self.assertTrue(valid_result().meets_contract())

    def test_toy_data_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "data shape"):
            replace(valid_plan(), representative_data=False).validate()

    def test_open_model_must_control_coordinated_omission(self):
        plan = replace(valid_plan(), controls_coordinated_omission=False)
        with self.assertRaisesRegex(ValueError, "coordinated omission"):
            plan.validate()

    def test_single_trial_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "repetition"):
            replace(valid_plan(), repetitions=1).validate()

    def test_unsafe_blast_radius_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "blast radius"):
            replace(valid_plan(), blast_radius_percent=0).validate()

    def test_weakened_semantics_are_rejected(self):
        plan = replace(valid_plan(), preserves_correctness_and_durability=False)
        with self.assertRaisesRegex(ValueError, "semantics"):
            plan.validate()

    def test_insufficient_headroom_fails_contract(self):
        result = replace(valid_result(), safe_capacity_rate=1_200)
        self.assertFalse(result.meets_contract())

    def test_slow_recovery_fails_contract(self):
        result = replace(valid_result(), recovered_in_seconds=180)
        self.assertFalse(result.meets_contract())

    def test_unverified_correctness_is_rejected(self):
        result = replace(valid_result(), correctness_verified=False)
        with self.assertRaisesRegex(ValueError, "correctness"):
            result.meets_contract()

    def test_cost_overrun_fails_contract(self):
        result = replace(valid_result(), cost=300)
        self.assertFalse(result.meets_contract())


if __name__ == "__main__":
    unittest.main()
```

The tests distinguish an invalid experiment from a valid experiment whose system failed the contract. That distinction matters: bad evidence must be rejected, while an honest red result is useful learning.

## 22. Run the Atlas capacity investigation

Suppose Atlas expects a launch peak of 900 operations per second. The team first replays a production-shaped mix with tenant skew and background exports. An open arrival model records intended arrivals even during slow responses.

At 1,050 operations per second, completion rate flattens, pool wait rises, and p99 crosses the SLO. CPU still has room. Traces and pool metrics identify the database connection pool as the first queue; increasing it merely moves saturation to database sessions. A query and index change moves safe capacity to 1,400 operations per second without weakening durability.

The planned 900 rate uses about 64% of safe capacity, retaining roughly 36% measured headroom. The team then removes one worker group from 10% of traffic. Errors remain within the SLO, but recovery takes 170 seconds because new workers spend 80 seconds starting and warming. The system fails its 120-second recovery objective.

That is a successful experiment and an unsuccessful design result. The team keeps more provisioned baseline capacity, improves startup, and repeats. The second trial recovers in 88 seconds, preserves accepted updates, drains the backlog, and stays within the cost ceiling. The evidence now supports the launch decision.

## 23. Review the complete evidence

### Workload

- Does the request mix represent journeys, payloads, data cardinality, skew, and background work?
- Does the open or closed model match the real feedback loop?
- Are arrivals scheduled and measured without coordinated omission?
- Are warm, cold, peak, and soak phases distinct where needed?

### Capacity

- Are arrivals, admissions, completions, failures, and queued work reconciled?
- Does the full SLO hold at the declared safe capacity?
- Is the first constraint supported by cross-layer evidence and a repeated intervention?
- Does planned demand leave measured headroom after credible loss?

### Failure and recovery

- Is the steady-state hypothesis user-visible and falsifiable?
- Are blast radius, abort conditions, owner, and rollback explicit?
- Does the test verify correctness, durability, degradation, and backlog drain?
- Is redundancy and headroom restored within the recovery objective?

### Reproducibility and cost

- Are artifacts, configuration, environment, workload, phases, and raw evidence retained?
- Are repeated trials comparable, with variation reported?
- Does cost include service, dependencies, generator, telemetry, and headroom?
- Can another engineer reproduce the conclusion after a system change?

## Common Misconceptions

**“The test reached the target throughput, so capacity is sufficient.”** Only if latency, errors, correctness, queue stability, headroom, recovery, and cost also meet the contract.

**“A fixed number of virtual users is always realistic.”** It is realistic for bounded populations. It can hide overload for independently arriving work.

**“Autoscaling eliminates capacity planning.”** Autoscaling has observation, provisioning, startup, warm-up, and downstream limits. Those delays require measured baseline capacity and headroom.

**“Chaos means introducing surprising production failures.”** Useful failure injection begins with a hypothesis, limited blast radius, abort conditions, observability, and recovery verification.

**“The breaking point is the capacity number.”** Safe capacity is below the knee, where the complete service contract holds with uncertainty and failure margin.

**“Once the fault stops, the test is over.”** Recovery includes SLO restoration, backlog drain, correctness checks, and renewed redundancy.

## Core Computer Science Concept

This chapter applies queueing and feedback control. Arrival rate, service time, concurrency, and finite capacity determine whether queues converge. Autoscaling, retry, admission, and shedding are control loops with delay. Delayed or positive feedback can create oscillation and cascading failure; measured headroom and bounded negative feedback keep the system stable.

## Engineering Connections

- SLOs and error classification come from Chapter 121.
- CPU, memory, I/O, network, and database evidence come from Chapters 123 through 125.
- Capacity, overload, resilience, degradation, and recovery extend Chapters 113 and 114.
- Deployment safety and rollback connect to Chapters 95 through 97.
- Chapter 127 uses these limits and recovery signals during live incidents.

## From the Field

A team tests 200 closed-loop workers and reports stable latency. In production, webhooks arrive independently. When the database pauses, the test workers wait and offered load drops; production arrivals instead accumulate, time out, and retry. An open model exposes the queue, a bounded fault test reveals the retry amplification, and admission control plus measured headroom turns a cliff into explicit degradation.

## Engineering Review

### What problem does this solve?

It discovers service limits, unsafe feedback, insufficient headroom, and failed recovery paths before real demand or component loss exposes them.

### Why was it designed this way?

Workload, SLO, capacity, failure, recovery, reproducibility, and cost are one contract because optimizing any one in isolation can produce a misleading green result.

### When should I use it?

Use it before launches and major changes, during recurring capacity reviews, after workload shifts, when validating overload controls, and when rehearsing credible dependency or capacity loss.

### When should I avoid it?

Do not inject uncontrolled faults into shared or production systems without a justified hypothesis, bounded scope, reliable abort mechanism, ownership, observability, and explicit authority.

### How does this make me a better engineer?

You learn to model demand, recognize measurement bias, find the first constraint, reason about delayed control loops, and treat a red experiment as evidence rather than failure of the exercise.

### How does this reduce waste?

It prevents premature fleet growth, false benchmark wins, unused elastic capacity, repeated incidents, unsafe chaos demonstrations, and tuning resources that are not constraining the service.

## Handbook Principle #126

> Test the workload users actually create, measure arrivals through recovery, reserve capacity below the knee, and inject failure only with a falsifiable steady-state hypothesis, bounded blast radius, automatic aborts, and proof that correctness and headroom return.

## Practical Observation

On the next performance dashboard, place offered arrivals, successful completions, p99 latency, error ratio, queue age, the suspected limiting resource, and instance count on the same time axis. If the test report cannot show when demand, saturation, scaling, and recovery happened, it cannot support a capacity decision.

## Looking Ahead

Chapter 127 turns the SLO, capacity, failure, and recovery signals into incident roles, severity, command, communication, mitigation, evidence preservation, and safe restoration under time pressure.

## References

- [Grafana k6 documentation — Open and closed models](https://grafana.com/docs/k6/latest/using-k6/scenarios/concepts/open-vs-closed/)
- [Google SRE — Production Services Best Practices](https://sre.google/sre-book/service-best-practices/)
- [Google SRE — Addressing Cascading Failures](https://sre.google/sre-book/addressing-cascading-failures/)
- [Google SRE — Launch Coordination Checklist](https://sre.google/sre-book/launch-checklist/)
- [Kubernetes documentation — Horizontal Pod Autoscaling](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/)
- [Principles of Chaos Engineering](https://principlesofchaos.org/)
- [Chapter 114 — Resilience, Timeouts, Retries, and Failure Containment](../system-design/114-resilience-timeouts-retries-and-failure-containment.md)
- [Chapter 121 — Metrics, SLIs, SLOs, and Actionable Alerts](121-metrics-slis-slos-and-actionable-alerts.md)
- [Chapter 125 — I/O, Network, and Database Performance](125-io-network-and-database-performance.md)
