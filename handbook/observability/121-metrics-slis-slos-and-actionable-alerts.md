# Chapter 121 — Metrics, SLIs, SLOs, and Actionable Alerts

Metrics compress many observations into time series. That compression makes trends, rates, distributions, objectives, and alerts affordable—but it also discards individual context. A useful metric begins with a question, has defined units and dimensions, and preserves enough information to make a valid decision.

Service-level indicators and objectives connect those measurements to user outcomes. Error budgets express tolerated imperfection. Alerts notify a human only when timely action is required. Together they create a control loop: observe, compare with an objective, decide, act, and verify.

This chapter does not prescribe a metrics vendor, cover statistical process control in depth, or define organization-wide reliability governance.

## 1. Start with decisions, not available charts

Before adding a metric, state the decision it supports:

- Is the task-update journey meeting its reliability target?
- Which resource is approaching a capacity limit?
- Did release `2026.11.1` change latency or correctness?
- Is queue delay threatening the notification objective?
- Must an on-call engineer act now, or can the issue become planned work?

A dashboard full of CPU, memory, request counts, and colorful percentiles can still omit the user's failed journey. Conversely, one alert derived from a precise SLO may be more valuable than hundreds of component thresholds.

Document name, type, unit, population, dimensions, owner, expected range, reset behavior, and intended use. A metric is an interface: once dashboards and alerts depend on it, silent semantic changes are breaking changes.

## 2. Choose a metric type that preserves meaning

The common models are:

- **counter or monotonic sum:** cumulative occurrences or quantities that only increase until process reset, such as accepted requests, failed updates, or bytes sent;
- **gauge:** a sampled value at a point in time, such as queue depth, current connections, temperature, or configuration generation;
- **histogram:** a distribution represented by count, sum, and buckets or another aggregatable sketch, such as request duration or payload size;
- **up/down or non-monotonic sum:** additive state that can increase or decrease, such as active work items, when the instrumentation model supports it.

Do not record a cumulative request count as a gauge merely because both store numbers. A counter's reset-aware rate has meaning; arbitrary gauge differences may not.

Units belong in the metric identity. Seconds, bytes, and dimensionless ratios must not be mixed. Use base units and stable naming conventions supported by the telemetry system.

## 3. Derive rates from counters

A counter value usually answers “how many since this process started,” not “how fast now.” Compute a rate over a window while accounting for resets:

```text
request rate = increase(requests_total over window) / window duration
error ratio  = increase(failed_requests_total) / increase(valid_requests_total)
```

Sum compatible counter increases across instances before forming the ratio. Averaging instance error percentages can overweight a nearly idle instance.

Choose the window for the decision. A one-minute rate detects sharp changes but is noisy at low traffic; a six-hour rate detects sustained budget consumption but responds slowly. Dashboards can show several windows, but alerts need explicit behavior.

Do not differentiate gauges such as queue depth to infer arrivals unless the state model justifies it. Work can arrive, complete, expire, move, or be corrected between samples.

## 4. Use gauges for state, with staleness semantics

A gauge is the latest observed value, not an event count. Examples include:

- current queue depth;
- in-use database connections;
- bytes of resident memory;
- timestamp of last successful backup;
- current configuration version encoded as labeled metadata where bounded.

Define who updates the gauge and what happens when the source disappears. A last value of `1` for “healthy” may remain visible after the process dies unless the monitoring system marks it stale. Pair critical state with collection freshness or an explicit heartbeat only when that heartbeat represents a real contract.

Avoid using gauges for durations that occur repeatedly; a histogram preserves the population. A gauge may be appropriate for the duration of the last completed batch only if “last batch duration” is the intended state.

## 5. Preserve latency distributions with histograms

An average hides shape. Nine requests at 10 ms and one at 5 seconds average about 509 ms, which describes no user's experience. Percentiles answer distribution questions, but their computation matters.

Histograms count observations in configured buckets and preserve total count and sum. Compatible histograms can be aggregated across instances and time before calculating quantiles. Choose boundaries around user and SLO thresholds—for example 100, 300, 500, 1,000, and 2,000 ms—while controlling series cost and approximation error.

Precomputed client-side quantiles often cannot be aggregated correctly. Averaging per-instance p95 values is statistically invalid. If instances expose only quantiles, the global p95 cannot be reconstructed from them.

For a threshold SLO such as “99% under 300 ms,” the most direct SLI is the count at or below the threshold divided by eligible count. It avoids percentile interpolation near the decision boundary.

## 6. Keep metric dimensions bounded

A time series is commonly identified by metric name plus a set of label or attribute values. Adding one label multiplies possible series:

```text
series ≈ routes × methods × outcomes × regions × cells × versions
```

Ten routes, five methods, six outcomes, three regions, four cells, and ten live versions can create 36,000 series before instances or histogram buckets.

Good bounded dimensions include route template, operation, outcome class, region, cell, and a limited deployment version. Dangerous dimensions include user ID, email, request ID, task ID, raw URL, exception message, and arbitrary tenant ID.

Use logs or traces for high-cardinality lookup. Use controlled heavy-hitter, top-N, or separately budgeted per-tenant accounting when tenant visibility is a genuine requirement. Estimate cardinality before deployment and alert on unexpected series growth.

## 7. Use RED to inspect request-driven services

The RED questions are:

- **Rate:** How much work arrives or completes?
- **Errors:** How much work fails according to the contract?
- **Duration:** How long does the work take across its distribution?

Apply them to user operations, RPCs, queue consumers, and scheduled jobs. For asynchronous work, rate may include accepted, started, and completed separately; duration may include queue age plus execution; error includes permanent failure, expiry, or dead-letter disposition.

RED is an investigation and instrumentation checklist, not an SLO definition. A dependency's request rate may explain an incident without representing a direct user outcome.

Avoid one generic `requests_total` whose outcome label changes meaning by endpoint. Define eligibility and success consistently.

## 8. Use USE to inspect resources

For every constrained resource, examine:

- **Utilization:** how busy or consumed the resource is;
- **Saturation:** queued or delayed work it cannot service immediately;
- **Errors:** allocation, device, or operation failures.

Examples:

| Resource | Utilization | Saturation | Errors |
| --- | --- | --- | --- |
| CPU | busy time | runnable queue or scheduler delay | hardware or throttling faults |
| Database pool | in-use connections | acquisition waiters and wait time | acquisition failures |
| Worker pool | busy workers | queued tasks and oldest age | rejected tasks |
| Disk | busy time or bandwidth | I/O queue and wait | device or filesystem errors |
| Memory limit | resident bytes versus limit | reclaim, paging, allocation stalls | allocation or OOM failures |

Utilization below 100% does not prove absence of saturation: averages hide bursts, one shard can be hot, and concurrency or rate limits may bind first. USE helps locate a bottleneck; it does not tell whether users are meeting an objective.

## 9. Define an SLI from a user outcome

A service-level indicator is a quantitative measure of behavior important to a user. Start from the journey:

> An authorized member submits a valid task update and receives confirmation that the durable version committed before the client deadline.

Define **valid events** and **good events**:

```text
availability SLI = good valid task-update attempts / all valid task-update attempts
```

The denominator may exclude malformed requests, explicit client cancellation before processing, load outside a published contract, and authorized maintenance only if the product contract actually excludes them. Do not exclude server failures because they are inconvenient.

The numerator must include correctness and deadline semantics. An HTTP `200` with a stale or uncommitted result is not good. A `412` stale-version response may be a correct success for the concurrency contract, even though the attempted mutation did not apply.

Write inclusion and exclusion rules before implementing the query.

## 10. Choose indicators by service type

Common SLIs include:

- **availability:** valid operations that return a correct usable result;
- **latency:** valid operations completed within a user-relevant threshold;
- **correctness:** results satisfying business invariants;
- **freshness:** derived data no older than an allowed age;
- **durability:** accepted data still retrievable and correct later;
- **throughput:** eligible work completed per unit time under a stated workload;
- **coverage:** expected entities processed or protected;
- **quality:** domain-specific usefulness or accuracy.

Storage can be available yet return corrupt data. A pipeline can process quickly while its output is a day stale. A notification system can accept every message while delivering none. Select a handful of indicators that represent distinct user harms.

Do not turn demand, such as incoming requests per second, into an objective the service controls. Demand is a workload condition; throughput or availability under that condition can be an objective.

## 11. Measure at the boundary closest to experience

Server-side metrics are detailed and reliable but may miss DNS, edge, network, client rendering, or SDK retry effects. Client-side measurements better represent experience but may be sampled, delayed, blocked, untrusted, or unable to distinguish causes.

Use complementary sources:

- black-box probes for externally visible availability and latency;
- edge or load-balancer events for accepted traffic and response outcomes;
- application metrics for correctness and phase detail;
- client telemetry for end-to-end usability where privacy and trust allow it;
- reconciliation for durability, freshness, and completion.

State the measurement point in the SLI definition. “Latency under 300 ms” is ambiguous without start and end boundaries.

Compare sources. If the server SLI is healthy while clients fail, the gap is evidence—not a reason to discard the client view.

## 12. Write a complete SLO

An objective needs more than a target:

> Over each rolling 30-day window, at least 99.9% of valid production task-update attempts measured at the edge will return a contract-correct terminal response within two seconds. The valid population excludes authenticated client cancellations received before the request is admitted and documented load beyond the tenant quota. Missing edge telemetry is not counted as success and triggers a separate measurement-integrity policy.

Specify:

- user journey and population;
- good-event rule;
- measurement point and source;
- target and evaluation window;
- latency threshold or other quality boundary;
- scope by region, tier, or workload class;
- exclusions and maintenance treatment;
- low-traffic and missing-data behavior;
- owner, review cadence, and consequences of budget exhaustion.

SLOs are internal engineering objectives. An SLA is an external agreement with business or legal consequences and requires qualified organizational review.

## 13. Choose an evaluation window deliberately

Common choices are rolling windows and calendar windows.

- A **rolling 30-day** window always reflects the recent 30 days and changes continuously.
- A **calendar month** aligns with reporting or contractual periods but varies in length and resets at boundaries.

Short windows respond quickly but are noisy and make one event dominant at low volume. Long windows are stable but can hide recent deterioration. Use fast burn windows for alerting and the full objective window for compliance.

Request-based objectives weight every eligible event. Time-based objectives classify intervals as good or bad and can better represent continuous availability when traffic is sparse. State which model is used; they produce different budgets.

Never silently switch between rolling and calendar calculations on dashboards and alerts.

## 14. Treat low traffic honestly

If a service handles ten requests in an hour, one failure produces a 90% SLI. That may be genuine severe user impact, but a percentage alone is statistically unstable.

Use:

- raw good and total counts beside ratios;
- longer windows for reporting;
- synthetic or scheduled probes for critical idle journeys;
- per-user or per-tenant impact where appropriate;
- alert minimum-event gates only if they do not hide intolerable single failures;
- time-based indicators for continuously expected service.

Do not report “100% available” when no eligible events occurred. Represent no data separately from perfect success.

For rare durability failures, one event may be unacceptable regardless of percentage. An SLO need not be the only policy.

## 15. Compute an error budget

For a request-based target:

```text
allowed bad fraction = 1 - SLO target
allowed bad events   = eligible events × allowed bad fraction
budget consumed      = observed bad events / allowed bad events
budget remaining     = 1 - budget consumed
```

At 99.9%, the allowed bad fraction is 0.001. Across 10,000,000 valid attempts, the budget permits 10,000 bad events. It does not grant permission to fail 10,000 selected users or violate security and correctness invariants.

For time-based availability, 99.9% over a 30-day window corresponds to about 43.2 minutes of bad time, subject to the precise interval classification.

Budget policy should define what changes when consumption is high: pause risky launches, prioritize reliability work, reduce experiment scope, or seek an explicit objective decision. An error budget without agreed action is only a report.

## 16. Use burn rate to express urgency

Burn rate compares the current bad-event ratio with the allowed bad fraction:

```text
burn rate = observed bad ratio / (1 - SLO target)
```

For a 99.9% objective:

- 0.1% bad is burn rate 1 and consumes a 30-day budget in 30 days if sustained;
- 1% bad is burn rate 10 and consumes it in about 3 days;
- 10% bad is burn rate 100 and consumes it in about 7.2 hours.

Burn rate normalizes alert urgency across objective targets. A 1% error rate is radically different for a 99% versus 99.99% service.

Use multiple windows. A short window detects acute failures; a longer paired window confirms persistence and reduces noise. Separate slow sustained consumption into a ticket or planned-work channel rather than waking someone who cannot improve the outcome immediately.

Thresholds are starting points to validate against real traffic and page load, not universal constants.

## 17. Alert only when a human must act

A page should answer:

- What user outcome is threatened?
- How quickly will the objective or safety boundary be exhausted?
- Which team owns the response now?
- What immediate action might improve the outcome?
- Which dashboard, traces, deploys, and runbook begin investigation?
- How does the alert resolve and avoid duplicate pages?

Page on fast or material budget burn, critical correctness or security invariants, and inability of automation to contain the issue. Create tickets for slow burn, capacity forecasts, or maintenance. Put informational context on dashboards.

CPU at 85% is not inherently pageable. If latency and errors remain healthy, it may be an efficiency signal. If saturation predicts imminent SLO burn and scaling cannot respond, it may justify action.

Every alert needs an owner, severity, notification path, runbook, tested query, and review date.

## 18. Pair long and short alert windows

A practical multi-window pattern requires both a long and a short window to exceed a burn threshold:

```text
page if:
  (1h burn > fast threshold AND 5m burn > fast threshold)
  OR
  (6h burn > sustained threshold AND 30m burn > sustained threshold)
```

The long window establishes meaningful budget consumption; the short window lets the alert reset soon after recovery. Exact windows depend on traffic, collection interval, SLO period, and response time.

Avoid alerting on the full 30-day SLO alone. It reacts too slowly to a sudden outage and may keep firing long after recovery. Avoid a five-minute error threshold alone; transient low-volume noise will page unnecessarily.

Group related objectives and inhibit derivative component alerts during the same incident, while keeping diagnostic signals visible.

## 19. Define missing-data behavior

No samples can mean:

- zero eligible traffic;
- the service or exporter is down;
- collection cannot reach the source;
- credentials or discovery failed;
- a query label changed;
- the pipeline is delayed;
- the metric was removed;
- the workload moved elsewhere.

Never coerce all missing data to zero or healthy. Pair SLIs with collection freshness, target discovery, expected workload, and black-box evidence. For a request ratio, no numerator and denominator is “no eligible observations,” not 100% success. A numerator without a denominator indicates a broken query or instrumentation invariant.

Decide whether missing measurement burns budget, pauses evaluation, or invokes a separate measurement-integrity response. The choice depends on contract and failure mode, and must not incentivize disabling telemetry.

Test alert behavior when a time series disappears.

## 20. Build dashboards for questions

A service overview should lead from outcome to cause:

1. SLO compliance, remaining budget, and burn by window;
2. good, bad, and total event counts;
3. rate, errors, and duration by bounded workload dimensions;
4. major dependency outcomes and latency;
5. resource utilization, saturation, and errors;
6. deployment, configuration, and feature-change annotations;
7. links to traces, logs, runbooks, and capacity views.

Show distributions or threshold counts, not only averages. Show both ratio and volume. Keep axes, units, window, timezone, aggregation, and missing-data behavior visible.

Do not create one dashboard per organizational team if a user journey crosses them. Shared views reduce the “my service is green” failure during incidents.

## 21. Avoid common metric traps

- **Averaging averages:** combine sums and counts with their weights.
- **Averaging percentiles:** retain an aggregatable distribution instead.
- **Ratios of mismatched populations:** ensure numerator is a subset of denominator.
- **Success by absence:** missing failures do not prove success if telemetry is broken.
- **Outcome ambiguity:** define whether client errors, conflicts, retries, and cancellations are good, bad, or excluded.
- **Reset blindness:** counters restart; queries must handle it.
- **High-cardinality labels:** move individual lookup to events or traces.
- **Coordinated aggregation:** one-minute averages can hide one-second saturation.
- **Retry inflation:** measure user attempts and backend attempts separately.
- **Observer bias:** server success can miss client failure.

Validate queries with synthetic known counts and during telemetry failure, not only against attractive production graphs.

## 22. Apply objectives to Atlas Tasks

Atlas defines separate indicators:

### Task-update availability

Good: valid authorized update attempts that return a contract-correct terminal response within two seconds. A stale-version `412` is good because it preserves the concurrency contract. A timeout with an unknown outcome is bad even if the commit later appears.

Target: 99.9% over a rolling 30-day window, measured at the edge.

### Task-update latency

Good: valid attempts with a terminal response under 500 ms.

Target: 99% over 30 days. The histogram has a bucket boundary at 500 ms so compliance is a direct count.

### Search freshness

Good: sampled accepted task versions visible in search within 60 seconds.

Target: 99.5% over 30 days, measured by reconciliation probes rather than API response time.

### Tenant deletion completion

Good: authorized deletion workflows reconcile every registered primary and derived store within 30 days.

This low-volume critical workflow uses per-operation tracking and deadline alerts, not only an aggregate percentage.

Dashboards separate user update attempts from internal retries, show cell and bounded tenant-tier dimensions, and link error exemplars to traces without putting request IDs into metric labels.

## 23. Encode an SLO and alert contract

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class SLO:
    name: str
    good_events: int
    valid_events: int
    target: float
    window_days: int
    measurement_point: str
    owner: str

    def validate(self) -> None:
        if not self.name.strip() or not self.measurement_point.strip():
            raise ValueError("SLO lacks a journey or measurement boundary")
        if not 0 <= self.good_events <= self.valid_events:
            raise ValueError("good events must be a subset of valid events")
        if self.valid_events <= 0:
            raise ValueError("SLO has no eligible observations")
        if not 0 < self.target < 1 or self.window_days <= 0:
            raise ValueError("SLO target or window is invalid")
        if not self.owner.strip():
            raise ValueError("SLO has no owner")

    @property
    def indicator(self) -> float:
        return self.good_events / self.valid_events

    @property
    def bad_ratio(self) -> float:
        return 1 - self.indicator

    @property
    def burn_rate(self) -> float:
        return self.bad_ratio / (1 - self.target)

    @property
    def budget_consumed(self) -> float:
        allowed_bad = self.valid_events * (1 - self.target)
        return (self.valid_events - self.good_events) / allowed_bad


@dataclass(frozen=True)
class AlertPolicy:
    slo: SLO
    long_window_minutes: int
    short_window_minutes: int
    burn_threshold: float
    owner: str
    runbook: str
    missing_data_policy: str

    def validate(self) -> None:
        self.slo.validate()
        if self.long_window_minutes <= self.short_window_minutes or self.short_window_minutes <= 0:
            raise ValueError("alert windows do not confirm and reset correctly")
        if self.burn_threshold <= 1:
            raise ValueError("page threshold does not represent accelerated burn")
        if not self.owner.strip() or not self.runbook.strip():
            raise ValueError("alert lacks an owner or response")
        if self.missing_data_policy not in {"measurement_alert", "burn", "pause_with_review"}:
            raise ValueError("missing-data behavior is undefined")
```

The tests verify arithmetic and operational completeness:

```python
from dataclasses import replace
import unittest

from slo_contract import AlertPolicy, SLO


def valid_slo() -> SLO:
    return SLO(
        name="task update availability",
        good_events=999_000,
        valid_events=1_000_000,
        target=0.999,
        window_days=30,
        measurement_point="edge terminal response",
        owner="task platform",
    )


def valid_policy() -> AlertPolicy:
    return AlertPolicy(
        slo=valid_slo(),
        long_window_minutes=60,
        short_window_minutes=5,
        burn_threshold=14.4,
        owner="task platform on-call",
        runbook="runbooks/task-update-slo.md",
        missing_data_policy="measurement_alert",
    )


class SLOContractTests(unittest.TestCase):
    def test_indicator_and_burn_are_computed(self):
        slo = valid_slo()
        slo.validate()
        self.assertAlmostEqual(0.999, slo.indicator)
        self.assertAlmostEqual(1.0, slo.burn_rate)
        self.assertAlmostEqual(1.0, slo.budget_consumed)

    def test_good_events_cannot_exceed_population(self):
        with self.assertRaisesRegex(ValueError, "subset"):
            replace(valid_slo(), good_events=1_000_001).validate()

    def test_empty_population_is_not_perfect(self):
        with self.assertRaisesRegex(ValueError, "eligible"):
            replace(valid_slo(), good_events=0, valid_events=0).validate()

    def test_perfect_target_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "target"):
            replace(valid_slo(), target=1.0).validate()

    def test_unowned_objective_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "owner"):
            replace(valid_slo(), owner="").validate()

    def test_short_window_must_be_shorter(self):
        with self.assertRaisesRegex(ValueError, "windows"):
            replace(valid_policy(), short_window_minutes=60).validate()

    def test_page_requires_accelerated_burn(self):
        with self.assertRaisesRegex(ValueError, "accelerated"):
            replace(valid_policy(), burn_threshold=1.0).validate()

    def test_alert_needs_a_runbook(self):
        with self.assertRaisesRegex(ValueError, "response"):
            replace(valid_policy(), runbook="").validate()

    def test_missing_data_must_have_policy(self):
        with self.assertRaisesRegex(ValueError, "missing-data"):
            replace(valid_policy(), missing_data_policy="assume_healthy").validate()


if __name__ == "__main__":
    unittest.main()
```

Real systems calculate each alert window from time-series data rather than one aggregate object. The model demonstrates the invariants: valid populations, non-perfect objectives, explicit measurement, normalized burn, paired windows, ownership, response, and missing-data policy.

## 24. Review metrics, objectives, and alerts

Before approving monitoring, ask:

### Metric semantics

- Does each metric have a question, type, unit, owner, reset behavior, and bounded dimensions?
- Can counters be aggregated before rates and ratios are formed?
- Do histogram boundaries preserve the SLO threshold and required quantiles?
- Are high-cardinality identities kept out of time-series labels?

### SLI and SLO validity

- Does the SLI represent a user outcome rather than a convenient component signal?
- Are good events a precise subset of valid events?
- Are measurement point, scope, exclusions, target, window, and low-volume behavior explicit?
- Are correctness, freshness, durability, or completion missing from an availability-only view?
- Does error-budget policy lead to an owned decision?

### Alert actionability

- Does a page correspond to material budget burn or a critical invariant?
- Do long and short windows balance precision, detection, and reset time?
- Is missing telemetry distinguishable from health and from no traffic?
- Is there a named owner, immediate action, runbook, dashboard, and resolution condition?
- Have the query and notification path been tested?

## Common Misconceptions

- **“Every numeric value is a gauge.”** Counters, gauges, and distributions have different aggregation semantics.
- **“Average latency represents typical users.”** It can hide both the median and a severe tail.
- **“Average the instance p95 values.”** Quantiles generally cannot be averaged or aggregated that way.
- **“No traffic means 100% availability.”** It means no eligible evidence unless another indicator supplies it.
- **“A 99.9% SLO permits any failures inside the budget.”** Security, correctness, durability, and concentrated harm can remain hard constraints.
- **“Alert on every error.”** Alerts should map to user impact, urgency, ownership, and a possible action.
- **“Infrastructure thresholds are SLOs.”** Resources explain behavior; user journeys define service outcomes.
- **“Missing data is zero.”** It may mean exporter, discovery, collection, or query failure.

## Core Computer Science Concept

This chapter applies **measurement theory, aggregation algebra, probability distributions, dimensional analysis, sampling, control loops, finite budgets, and queue/resource models**. Metrics are compressed observations; valid decisions depend on preserving the algebra and population behind that compression.

## Engineering Connections

- Counters, distributions, resource limits, and queueing build on Chapters 43, 76, 86, 109, and 114.
- SLI contracts extend Chapters 106, 107, and 117.
- Event schemas and correlation from Chapter 120 supply exemplars and detailed evidence.
- Chapters 122–126 provide traces, profiles, and load experiments behind metric changes.
- Chapters 127–128 use alerts, budget impact, and missing evidence during incidents and learning.

## From the Field

A team pages whenever any instance exceeds 80% CPU. A traffic increase wakes on-call repeatedly even though latency and errors remain healthy; eventually the alert is muted. Later, one overloaded shard queues requests while fleet-average CPU is 45%, and no one is paged until customers complain. A user-journey SLO burn alert plus per-shard utilization, saturation, and error diagnostics would have reduced noise and detected the real harm.

## Engineering Review

### What problem does this solve?

It connects telemetry to user expectations and reserves urgent notification for conditions where timely human action protects an objective.

### Why was it designed this way?

Typed metric algebra preserves valid aggregation, while SLIs, error budgets, and burn rates translate measurements into consistent decisions.

### When should I use it?

Use it for operated services, pipelines, storage systems, scheduled workflows, and any product that makes reliability or performance expectations.

### When should I avoid it?

Do not force rare safety, security, or durability invariants into percentages that normalize unacceptable events; monitor and respond to them directly.

### How does this make me a better engineer?

You learn to distinguish demand from outcome, distributions from averages, resource signals from user impact, and information from actionable notification.

### How does this reduce waste?

It reduces useless time series, cardinality explosions, invalid percentile math, noisy pages, status meetings without shared objectives, and reliability work disconnected from measured harm.

## Handbook Principle #121

> Measure the user's valid journey, preserve the metric's aggregation semantics, define tolerated imperfection explicitly, and page only when budget burn or a critical invariant demands an owned action now.

## Practical Observation

Take one existing percentage dashboard. Write its numerator, denominator, measurement point, exclusion rules, no-traffic result, missing-data result, and aggregation order. If any answer is unknown, the percentage is not yet an indicator you can safely operate from.

## Looking Ahead

Chapter 122 connects a metric anomaly to causal request paths and sampled stack behavior, while separating distributed tracing from resource profiling.

## References

- [OpenTelemetry — Metrics Data Model](https://opentelemetry.io/docs/specs/otel/metrics/data-model/)
- [Prometheus — Instrumentation practices](https://prometheus.io/docs/practices/instrumentation/)
- [Prometheus — Histograms and summaries](https://prometheus.io/docs/practices/histograms/)
- [Prometheus — Metric and label naming](https://prometheus.io/docs/practices/naming/)
- [Google SRE Book — Service Level Objectives](https://sre.google/sre-book/service-level-objectives/)
- [Google SRE Workbook — Alerting on SLOs](https://sre.google/workbook/alerting-on-slos/)
- [Google SRE Book — Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/)
- [Brendan Gregg — The USE Method](https://www.brendangregg.com/usemethod.html)
- [Chapter 120 — Logs and Structured Events](120-logs-and-structured-events.md)
