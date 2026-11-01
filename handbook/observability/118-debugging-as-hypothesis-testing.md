# Chapter 118 — Debugging as Hypothesis Testing

Debugging is the process of turning an unexplained observation into a tested explanation. Random edits sometimes make a symptom disappear, but they destroy evidence, combine variables, and teach nothing about recurrence. A disciplined investigation cycles through **observation, model, hypothesis, prediction, experiment, and revision**.

The goal is not to sound scientific. It is to choose the smallest safe test whose result distinguishes credible explanations. This method works for one function, a build failure, a distributed outage, and a gradual performance regression.

This chapter does not teach a language-specific debugger, performance profiler, or incident-command process. Those tools become more effective after the question is precise.

## 1. Separate the symptom from the explanation

A symptom is observed behavior that differs from an expectation. Write it without causes:

> Between 14:05 and 14:22 UTC, 7.4% of task-update requests for tenants routed to cell B returned `503` after approximately two seconds. Reads and cells A and C remained within their normal ranges.

“The database is overloaded” is not a symptom. It is a hypothesis. “The service is broken” is too broad to test.

A useful symptom statement includes:

- expected and observed behavior;
- affected journey or invariant;
- start, end, and timezone;
- population and denominator;
- failure value, distribution, or message;
- environment, version, and location;
- known unaffected comparisons;
- source and quality of the evidence.

Precision narrows the search before any system changes.

## 2. Verify the report and its measurement

Before diagnosing the system, verify that the observation is real and interpreted correctly. Ask:

- Does the query use the right time range and timezone?
- Did the dashboard, alert, client, or test change?
- Is the denominator complete?
- Is sampling hiding or exaggerating a pattern?
- Does “success” match the user outcome?
- Are delayed events being plotted at ingestion rather than occurrence time?
- Can another independent signal confirm the symptom?

A broken monitor can still reveal a real instrumentation defect, but changing application code will not correct it. Conversely, “only a dashboard issue” is unsafe until user impact is checked independently.

Treat telemetry as evidence with provenance and limitations, not as reality itself.

## 3. Stabilize harm while preserving evidence

Investigation and mitigation are related but distinct. If users, data, security, or recovery objectives are at risk, contain the harm first with the safest known action: shed load, disable a feature, fail over, revoke a credential, or roll back a recent change.

Before volatile evidence disappears, preserve what can be collected safely:

- request and trace identifiers;
- exact timestamps and clock sources;
- error bodies, stack traces, and process state;
- deployment, configuration, schema, and feature-flag versions;
- resource and queue measurements;
- a bounded sample of relevant logs;
- commands and changes already performed.

Do not delay urgent containment for perfect evidence. Do avoid restarting, scaling, clearing caches, rotating everything, and redeploying simultaneously unless safety requires it. That may mitigate the event while making cause unknowable and introducing new faults.

## 4. Establish how the system should work

Troubleshooting needs a model. Trace the failing journey through components, state transitions, dependencies, queues, caches, and trust boundaries. Identify the invariants that should hold at each step.

For a task update:

1. edge routing selects the cell;
2. the API authenticates and authorizes;
3. admission control grants capacity;
4. a database connection is acquired;
5. the conditional update and outbox record commit;
6. the response returns before the deadline;
7. asynchronous consumers project search and notifications.

This model suggests evidence and failure boundaries. If the client receives `503` before any database span exists, storage hypotheses fall in rank. If database acquisition consumes the entire deadline, application serialization is less likely.

System knowledge does not replace testing; it produces better hypotheses.

## 5. Bound scope across useful dimensions

Compare affected and unaffected groups across:

- time: before, during, after;
- version: old, new, canary;
- environment: local, test, production;
- location: region, zone, cell, host, process;
- tenant or user cohort;
- endpoint, method, data shape, and payload size;
- dependency, shard, partition, or queue;
- network path, client type, and protocol;
- cold versus warm state;
- success versus failure traces.

The most informative statement is often a difference: “only cell B writes fail; cell B reads succeed.” That comparison eliminates theories that should affect all cells or all database operations.

Beware hidden correlation. Two “independent” cells may share one identity provider, control plane, certificate, or deployment artifact.

## 6. Construct a timeline

A timeline aligns symptoms with changes and system transitions:

```text
13:42  release 2026.11.1 begins in cell B
13:51  database connection limit changed from 400 to 250
13:58  release completes; synthetic writes pass
14:05  p95 connection wait rises
14:07  write 503 rate crosses alert threshold
14:09  autoscaler adds API instances
14:10  wait rises faster; each instance opens its minimum pool
14:22  pool minimum reduced; errors recover
```

Use event time and state how clocks are aligned. Correlation in the timeline does not prove causation, but it supplies candidates and predictions. The release began before the connection change; the error began after both. A valid hypothesis must explain the delay, cell specificity, read behavior, and counterintuitive worsening after scaling.

Include mitigations and observations, not just deployments. Human actions become experimental inputs.

## 7. Find a known-good comparison

A known-good case provides a controlled contrast:

- the last version where the same test passed;
- an unaffected cell with comparable traffic;
- a successful request adjacent to a failure;
- a smaller input that avoids the defect;
- an earlier time with the same configuration;
- a healthy dependency endpoint.

Verify that it is actually comparable. Cell A may have half the tenant skew; yesterday may have used a different certificate; a successful request may have hit cache.

List the differences between good and bad, then rank them by their ability to explain every observation. This is more efficient than enumerating every component that could theoretically fail.

## 8. Write hypotheses that can be false

A useful hypothesis names a mechanism and connects it to the symptom:

> Cell B's lowered database connection limit, combined with the API's per-instance minimum pool, causes connection acquisition to exceed the two-second deadline; autoscaling adds minimum connections and amplifies contention.

Weak versions include “database issue,” “network flakiness,” and “bad deploy.” They do not predict evidence.

For each hypothesis, record:

- mechanism;
- observations it explains;
- observations it does not yet explain;
- predicted evidence if true;
- predicted evidence if false or an alternative is true;
- smallest distinguishing test;
- risk and cost of that test;
- current confidence and why.

A hypothesis may be partially correct. The connection limit can be a trigger while the unbounded pool policy is the amplification mechanism.

## 9. Maintain several credible alternatives

Prematurely choosing one explanation creates confirmation bias. Keep a small ranked set, for example:

1. connection acquisition exhaustion from the new limit and pool behavior;
2. a cell-B network path adding two-second connection stalls;
3. lock contention from one large tenant import;
4. the release leaking connections on an exception path;
5. telemetry attributing errors to the wrong cell.

Rank by explanatory coverage, prior evidence, recency of relevant change, and experiment cost—not by who proposed it. Add an “unknown mechanism” category when the model may be incomplete.

Do not keep dozens of vague possibilities. Merge equivalent mechanisms and remove hypotheses contradicted by reliable evidence, recording why.

## 10. Derive predictions before running a test

Predictions protect against explaining every result after the fact. For the pool-exhaustion hypothesis:

- failed requests should spend most of their time awaiting a connection;
- total requested minimum connections should approach or exceed the database limit;
- adding API instances should worsen acquisition wait;
- reducing per-instance pool minimum should improve the symptom without changing query time;
- read traffic using the same pool should also show wait unless it follows a different path.

The last prediction exposes a gap: observed reads are healthy. Investigation may reveal reads use a replica pool, strengthening rather than weakening the model.

Write predictions with thresholds where possible. “Latency will improve” is weaker than “p95 acquisition wait falls below 200 ms while query execution remains within 50 ms.”

## 11. Choose experiments by information gained

The best next experiment is not always the one most likely to fix the issue. It is the safest, cheapest test that separates high-ranked alternatives.

| Experiment | Distinguishes | Risk |
| --- | --- | --- |
| Compare acquisition and execution spans | Pool wait versus slow queries | Read-only |
| Compare cell B with cell A pool totals | Cell-local capacity versus shared dependency | Read-only |
| Route a synthetic write through both paths | Request path or data dependence | Low, controlled |
| Lower one canary's minimum pool | Pool mechanism versus network stall | Bounded change |
| Restart all API instances | Few alternatives; destroys process evidence | High and weak |

Prefer observation when it can refute a theory. Use active changes when passive evidence cannot distinguish alternatives. Run dangerous tests in disposable or canary environments unless urgent mitigation justifies production action.

An experiment must have a prediction, measurement, duration, stop condition, and rollback or containment plan.

## 12. Change one causal variable at a time

If a test changes the release, instance count, pool size, and database limit together, improvement cannot identify which variable mattered. Keep other conditions stable where feasible.

Distributed systems make perfect control impossible. Traffic, cache state, background work, and dependency health continue changing. Record those covariates and use comparison groups:

- one canary versus unchanged instances;
- matched tenants or requests;
- repeated trials at similar load;
- before-and-after with a stable control cell.

“One variable” refers to the causal question, not literal immobility. A configuration change may necessarily restart a process; the restart is a confounder that needs a control or acknowledgment.

## 13. Use binary search over ordered spaces

When candidates have an order and a reliable pass/fail test, divide the space:

- commits between known-good and known-bad revisions;
- configuration history;
- input length or record count;
- time intervals;
- layers in a request path;
- feature sets that can be enabled independently.

Git's `bisect` implements binary search over revision history. It requires trustworthy endpoints and a test that classifies each revision. `git bisect run` can automate the test; untestable revisions must be skipped, which may leave ambiguity near the boundary.

Binary search assumes the property changes consistently enough to classify. A flaky test, multiple independent regressions, incompatible historical environments, or a non-monotonic performance threshold can mislead. Stabilize the test and capture environment before trusting the result.

## 14. Test invariants at boundaries

An invariant localizes failure without requiring the full root cause. If an API promises every committed task update has one durable outbox identity, compare:

- requests accepted by the API;
- committed task versions;
- outbox records;
- broker publications;
- consumer-applied versions.

The first boundary where counts or identities diverge narrows the mechanism. Avoid relying only on error logs: absence of a log may mean the code path never ran, logging failed, sampling dropped it, or the query is wrong.

Checksums, sequence numbers, version counters, queue offsets, and conservation relationships are powerful because they express what must remain true across transformations.

## 15. Interpret negative evidence carefully

Not seeing evidence is useful only when the evidence would reliably appear:

- no error log is weak if errors are sampled;
- no trace is weak if head sampling excluded failed requests;
- no CPU spike is strong against CPU saturation only if the metric resolution captures it;
- no database span is strong against query execution only if instrumentation starts before the call;
- no reproduction in test is weak if data scale and scheduling differ.

Ask the counterfactual: **If this hypothesis were true, how likely is this measurement to observe it?** A low-sensitivity instrument cannot refute much.

Record missing evidence and telemetry limitations as findings. Observability gaps are often part of the corrective work.

## 16. Update confidence without fake precision

Confidence should change with evidence. A practical ledger can use ordinal levels:

- **low:** plausible mechanism, little direct evidence;
- **medium:** explains scope and timeline; some predictions confirmed;
- **high:** distinguishing predictions confirmed and alternatives contradicted;
- **demonstrated:** controlled reproduction and corrective reversal establish the mechanism.

Do not assign arbitrary percentages to look quantitative. Explain why confidence changed:

> Raised from medium to high: failed traces spend 1.8–2.0 seconds in pool acquisition, query execution remains below 40 ms, and lowering the canary pool minimum removes failures at matched load. Network handshake latency is unchanged.

A successful mitigation raises confidence but does not always prove cause. Restarting can clear leaks, locks, corrupted caches, and bad connections simultaneously.

## 17. Distinguish trigger, mechanism, and systemic cause

A complete explanation may have layers:

- **trigger:** the database connection limit was lowered;
- **failure mechanism:** aggregate minimum pools exceeded available connections;
- **amplifier:** autoscaling added more pools during timeouts;
- **detection gap:** alerts measured total latency but not acquisition wait;
- **systemic cause:** capacity relationships were not encoded or tested during configuration review.

Fixing only the trigger restores service but leaves recurrence likely. Blaming only the systemic process can obscure the concrete technical repair. Preserve both.

Avoid “root cause” when it implies one final cause. Complex failures often require several necessary conditions.

## 18. Keep mitigation separate from corrective action

Mitigation reduces current impact: restore the connection limit, cap instance scale, or shed low-priority writes. Corrective action prevents or limits recurrence:

- compute aggregate pool bounds from database capacity;
- validate configuration relationships before deployment;
- expose acquisition wait and pool saturation;
- make autoscaling aware of the constrained dependency;
- load-test the failure mode;
- update the runbook and decision record.

Do not postpone mitigation until every mechanism is proven. Do not close the investigation because mitigation worked.

## 19. Maintain an investigation log

Record the reasoning in chronological, append-oriented form:

```text
14:14Z OBSERVATION  Cell B write p95=2.03s; DB execution p95=37ms.
14:16Z HYPOTHESIS   H1 pool acquisition exceeds deadline after limit change.
14:17Z PREDICTION   Failed traces spend >1.5s before query; canary pool=2 recovers.
14:21Z EXPERIMENT   Set one canary pool minimum 10 -> 2 for 10 min; stop at 2% errors.
14:33Z RESULT       Canary errors 0.1%, control 7.1%; handshake unchanged.
14:34Z REVISION     H1 high confidence; H2 network stall reduced to low.
```

Separate observations, inferences, actions, and decisions. Include query links or captured artifacts when access controls permit. This allows handoff, prevents repeated tests, and preserves the path when an early assumption is later found wrong.

## 20. Define stopping criteria

An investigation should state when it can stop or change mode. Reasonable criteria include:

- user impact is contained and the responsible mechanism is demonstrated;
- corrective action has a regression test or operational verification;
- residual uncertainty has an owner and acceptable consequence;
- further experiments are riskier than the remaining problem;
- the evidence cannot distinguish alternatives without new instrumentation;
- the symptom cannot be reproduced after a defined observation window.

“Could not reproduce” is not “fixed.” State the attempts, environments, evidence retained, monitoring added, and trigger for reopening.

During an incident, stop deep causal work when it interferes with safe stabilization. Resume afterward with preserved evidence.

## 21. Apply the loop to the task platform

Symptom: cell B task writes return `503` at 7%, beginning after a release and database configuration change; reads are healthy.

Ranked hypotheses:

1. write-pool acquisition exhaustion;
2. cell-B network connection stalls;
3. lock contention from tenant import;
4. release-specific connection leak.

Evidence shows failures wait before query execution, while successful and failed query execution time is similar. Reads use a replica pool. The aggregate write-pool minimum across autoscaled instances exceeds the new primary connection limit. A canary with a lower minimum recovers at matched load; network handshake time and lock wait remain unchanged.

Mitigation restores the limit and caps scaling. Corrective work adds a configuration invariant, pool-wait SLI, dependency-aware scaling test, and load experiment. The release did not introduce a leak, so rolling it back would have added risk without addressing the mechanism.

The investigation succeeded because each result changed the ranked explanation.

## 22. Encode a hypothesis ledger

The following model enforces a minimal reasoning contract:

```python
from dataclasses import dataclass, field


@dataclass
class Hypothesis:
    name: str
    mechanism: str
    predictions: list[str]
    distinguishing_test: str
    confidence: str = "low"
    evidence_for: list[str] = field(default_factory=list)
    evidence_against: list[str] = field(default_factory=list)

    def validate(self) -> None:
        if not self.name.strip() or not self.mechanism.strip():
            raise ValueError("hypothesis needs a named mechanism")
        if not self.predictions:
            raise ValueError("hypothesis makes no falsifiable prediction")
        if not self.distinguishing_test.strip():
            raise ValueError("hypothesis has no distinguishing test")
        if self.confidence not in {"low", "medium", "high", "demonstrated"}:
            raise ValueError("confidence level is invalid")


@dataclass
class Investigation:
    symptom: str
    expected_behavior: str
    evidence_preserved: bool
    known_good_comparison: str
    hypotheses: list[Hypothesis]
    controlled_variable: str
    stop_condition: str

    def validate(self) -> None:
        if not self.symptom.strip() or not self.expected_behavior.strip():
            raise ValueError("investigation lacks observed and expected behavior")
        if not self.evidence_preserved:
            raise ValueError("volatile evidence was not preserved")
        if not self.known_good_comparison.strip():
            raise ValueError("investigation lacks a known-good comparison")
        if len(self.hypotheses) < 2:
            raise ValueError("investigation has no credible alternative")
        for hypothesis in self.hypotheses:
            hypothesis.validate()
        if not self.controlled_variable.strip():
            raise ValueError("experiment changes no explicit causal variable")
        if not self.stop_condition.strip():
            raise ValueError("investigation has no stopping criterion")
```

The tests reject common reasoning shortcuts:

```python
from dataclasses import replace
import unittest

from hypothesis_ledger import Hypothesis, Investigation


def candidate(name: str) -> Hypothesis:
    return Hypothesis(
        name=name,
        mechanism=f"{name} explains connection acquisition delay",
        predictions=["failed requests wait before query execution"],
        distinguishing_test="compare acquisition and execution spans",
    )


def valid_investigation() -> Investigation:
    return Investigation(
        symptom="Cell B writes return 503 after two seconds.",
        expected_behavior="Writes complete within 500 ms at expected load.",
        evidence_preserved=True,
        known_good_comparison="Cell A at matched traffic",
        hypotheses=[candidate("pool exhaustion"), candidate("network stall")],
        controlled_variable="per-instance pool minimum",
        stop_condition="mechanism reproduced and regression check passes",
    )


class InvestigationTests(unittest.TestCase):
    def test_complete_investigation_is_accepted(self):
        valid_investigation().validate()

    def test_explanation_is_not_a_symptom(self):
        with self.assertRaisesRegex(ValueError, "observed and expected"):
            replace(valid_investigation(), symptom="").validate()

    def test_destroyed_evidence_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "evidence"):
            replace(valid_investigation(), evidence_preserved=False).validate()

    def test_missing_comparison_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "known-good"):
            replace(valid_investigation(), known_good_comparison="").validate()

    def test_single_story_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "alternative"):
            replace(valid_investigation(), hypotheses=[candidate("pool")]).validate()

    def test_prediction_free_hypothesis_is_rejected(self):
        investigation = valid_investigation()
        investigation.hypotheses[0].predictions = []
        with self.assertRaisesRegex(ValueError, "falsifiable"):
            investigation.validate()

    def test_uncontrolled_experiment_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "causal variable"):
            replace(valid_investigation(), controlled_variable="").validate()

    def test_missing_stop_condition_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "stopping"):
            replace(valid_investigation(), stop_condition="").validate()


if __name__ == "__main__":
    unittest.main()
```

The ledger does not choose the correct hypothesis. It makes the reasoning inspectable and forces each candidate to risk being wrong.

## 23. Review a debugging investigation

Before changing the system, ask:

### Observation and scope

- Is the symptom stated separately from its suspected cause?
- Are time, population, denominator, version, environment, and evidence source precise?
- Which comparable cases are unaffected?
- Has volatile evidence been preserved before disruptive action?

### Hypotheses and experiments

- Does each hypothesis name a mechanism and explain the observations?
- Are there credible alternatives, including measurement error?
- Were predictions written before the test?
- Does the next experiment distinguish leading alternatives safely?
- Are causal variables, comparisons, duration, and stop conditions explicit?

### Conclusion and learning

- Which evidence confirmed and contradicted each candidate?
- Are trigger, failure mechanism, amplifier, and detection gap distinguished?
- Did mitigation merely change the symptom, or demonstrate the mechanism?
- Is there a regression check, monitoring improvement, owner, and reopening trigger?

## Common Misconceptions

- **“Experienced engineers debug by intuition.”** Experience proposes higher-quality hypotheses; evidence still tests them.
- **“The most recent change caused it.”** Recency raises a candidate's rank but does not establish mechanism.
- **“Restarting fixed it, so the cause is known.”** A restart changes many states simultaneously.
- **“No errors in the logs means that component is healthy.”** Logging coverage and sampling determine what absence means.
- **“Binary search always finds the bad change.”** It needs ordered candidates and a stable classification test.
- **“One root cause explains the incident.”** Trigger, mechanism, amplifier, and systemic conditions may all be necessary.
- **“Mitigation should wait for proof.”** Protect users first when harm is active, while preserving evidence proportionally.

## Core Computer Science Concept

This chapter applies **the hypothetico-deductive method, falsifiability, binary search, invariants, controlled experiments, causal inference, information gain, and state observation**. Debugging is a search problem made tractable by predictions that divide the candidate space.

## Engineering Connections

- Process, network, and system boundaries build on Chapters 43, 54, 61, and 86.
- Git history bisection extends Chapters 29, 33, and 36.
- Failure mechanisms and recovery use Chapters 110 through 114.
- Chapter 117's weakest-assumption experiment becomes the investigation loop here.
- Chapters 119–126 add reproduction, telemetry, profiles, and load evidence to the method.

## From the Field

A team sees rising API latency immediately after a release and rolls it back. Latency remains high, so it restarts the database, clears caches, and doubles instances. Service recovers, but no explanation survives. The actual trigger was a lowered database connection limit; scaling amplified pool contention. A timeline, acquisition spans, matched cell comparison, and one canary pool change would have isolated the mechanism with less risk.

## Engineering Review

### What problem does this solve?

It replaces untracked guesses and multi-variable changes with a reasoning process that can eliminate alternatives and preserve learning.

### Why was it designed this way?

Explicit predictions and distinguishing tests maximize information while bounded experiments limit the risk of investigation itself.

### When should I use it?

Use it whenever observed behavior violates an expectation, from a unit-test failure to a distributed production regression.

### When should I avoid it?

Do not let formal investigation delay urgent safety or security containment; mitigate first and resume causal work with the evidence available.

### How does this make me a better engineer?

You learn to distinguish observation from inference, challenge favored explanations, and choose tests that teach rather than merely change the symptom.

### How does this reduce waste?

It avoids shotgun changes, repeated experiments, unnecessary rollback, misleading fixes, and telemetry added without a specific question.

## Handbook Principle #118

> State the symptom without its cause, rank mechanisms that make different predictions, and run the smallest safe experiment that can prove a favored explanation wrong.

## Practical Observation

Before your next debugging command, write two hypotheses and one result that would distinguish them. If the command produces the same expected result under both explanations, it may collect context, but it is not yet the decisive experiment.

## Looking Ahead

Chapter 119 turns an observed failure into a deterministic, minimized, shareable case—or documents exactly which production-only dimensions still resist reproduction.

## References

- [Google SRE Book — Effective Troubleshooting](https://sre.google/sre-book/effective-troubleshooting/)
- [Git documentation — git-bisect](https://git-scm.com/docs/git-bisect)
- [Python documentation — pdb](https://docs.python.org/3/library/pdb.html)
- [Chapter 117 — A Complete System Design Review](../system-design/117-a-complete-system-design-review.md)
