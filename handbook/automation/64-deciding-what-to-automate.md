# Chapter 64 — Deciding What to Automate

Automation multiplies a procedure. If the procedure is understood and bounded, that multiplication creates consistency and capacity. If it is unstable or wrong, automation spreads ambiguity and damage faster.

The central idea is:

> Automate only after the work has a stable contract, explicit safety boundaries, and a measurable reason to exist.

## 1. Follow the whole improvement sequence

The handbook's sequence is deliberate:

```text
Observe → Understand → Remove Waste → Stabilize → Automate → Measure
```

**Observe** the real work, including inputs, decisions, exceptions, waits, and recovery. **Understand** why each step exists and which system owns it. **Remove Waste** before encoding unnecessary approvals, duplicate entry, and avoidable handoffs. **Stabilize** the remaining interface and expected outcomes. **Automate** a bounded contract. **Measure** whether the result improves safety, time, quality, and human workload.

Skipping ahead preserves defects as software. A script that copies data between two unnecessary spreadsheets is faster waste, not a better system.

The best outcome can be eliminating the task. A product invariant, self-service interface, or system design that no longer requires external repair is often better than a permanent repair bot.

## 2. Observe complete instances of the work

Do not automate from the happy-path runbook alone. Watch several real executions and record:

- trigger and requestor;
- authoritative inputs and their provenance;
- prerequisite checks;
- decisions and judgment calls;
- systems, credentials, and permissions used;
- commands or interface operations;
- expected and unexpected outputs;
- partial failures, retries, and cleanup;
- evidence retained for review;
- completion and handoff criteria.

Measure active human time separately from elapsed wait time. A five-hour task with ten minutes of human work has different opportunities from a repetitive ten-minute interruption that happens twenty times daily.

When operators disagree about the procedure, that is discovery evidence. Resolve the underlying policy or acknowledge multiple supported paths before selecting one for automation.

## 3. Identify toil without dismissing all manual work

Work is a strong automation candidate when it is manual, repetitive, predictable, automatable, tactical, low in enduring value, and grows with service scale. Frequency alone is not enough.

Manual work can be valuable when it creates understanding, handles a novel case, builds a lasting improvement, or requires accountable judgment. A rare migration might justify a disposable tool because it touches a million records; a weekly five-minute judgment call might remain manual.

Ask three elimination questions first:

1. Why must this task exist?
2. Can the producing system emit the needed form directly?
3. Can an invariant, interface, or policy remove the repeated decision?

Do not automate around a broken ownership boundary merely because its symptoms are frequent.

## 4. Evaluate frequency and scale together

Estimate workload using observable units:

```text
annual human load = executions × active time × people per execution
```

Then add interruption and coordination costs that the simple product misses. A two-minute page at night is not equivalent to two planned minutes during business hours.

Consider future scale carefully. Automation can be justified before current manual time exceeds development time when consistency, response speed, security, or error reduction matters. Conversely, speculative volume is not evidence.

Track distributions rather than one average. The slowest and riskiest cases may contain exceptions that invalidate a proposed single path.

## 5. Classify variability

Variation can be structured or open-ended. Structured variation has named cases and machine-observable inputs:

```text
if account is active and request is approved → apply standard change
if account is suspended → stop and report policy conflict
if state is unknown → require human review
```

Open-ended variation relies on context that has not been converted into a policy: interpreting customer intent, resolving contradictory evidence, or choosing among novel mitigations.

Automation does not require every case to be automatic. A safe system can handle known cases and route ambiguous cases to a person with the evidence already assembled. A clear refusal is better than guessing.

If exceptions dominate, stabilize the process or improve the source data before writing the executor.

## 6. Separate judgment from mechanics

Many procedures mix a human decision with mechanical execution. Split them:

- human or policy decides **whether** and **what**;
- automation validates the decision and performs **how**;
- automation records **what happened**;
- human handles conditions outside the contract.

For example, a reviewer can approve a bounded account entitlement while automation validates the account, applies the exact grant, verifies the result, and records an audit event. The tool need not decide the business entitlement.

Human approval adds value only when the reviewer has relevant information, time, authority, and a meaningful ability to reject. A habitual click inserted after an opaque automation creates latency without control.

## 7. Assess blast radius and reversibility

Classify each effect by scope, sensitivity, and recoverability:

| Dimension | Lower risk | Higher risk |
| --- | --- | --- |
| Scope | one disposable object | fleet, account, or shared control plane |
| Data | derived and reproducible | unique, regulated, or customer-owned |
| Permission | read-only | privileged mutation or credential issuance |
| Reversal | direct and tested | compensating action or irreversible effect |
| Detection | immediate and specific | delayed, silent, or externally reported |
| Rate | naturally bounded | fast fan-out or feedback loop |

“Reversible” must name a tested operation and time window. Restoring a backup can be slow, incomplete, or disruptive; it is not the same as undoing a transaction.

High-blast-radius automation needs stronger validation, staged rollout, rate and concurrency limits, canaries, independent stop controls, narrow credentials, and observable outcomes. Some effects should remain human initiated even when execution is automated.

## 8. Require a stable interface

Automation needs an interface more durable than screen position, prose formatting, or a person's memory. Prefer documented APIs, structured command output, versioned files, database contracts, or purpose-built service operations.

For each dependency, ask:

- Is the interface documented and supported?
- Is output machine-readable and versioned?
- Are timeouts, rate limits, and error categories defined?
- Can requests be safely retried or deduplicated?
- Does the caller receive an operation identifier?
- How are authentication and authorization scoped?
- How will changes be announced and tested?

If the only interface is unstable, isolate it behind a small adapter and budget for maintenance. Do not let scraped presentation text become an invisible organization-wide API.

## 9. Write the automation contract before code

A useful contract states:

```text
Trigger:
Authorized caller:
Inputs and schema:
Preconditions:
Planned effects:
Invariant safety limits:
Success condition:
Failure categories:
Retry and duplicate behavior:
Partial-progress record:
Rollback or compensation:
Evidence and retention:
Human escalation boundary:
```

Define input provenance and validation, not just field names. “Project ID” differs from “project ID selected from the authenticated caller's approved projects.”

Success must be observable after the action. An API returning `202 Accepted` proves acceptance, not completion. State the verification query and how long the automation waits before returning an inconclusive result.

If the team cannot agree on this contract, implementation is premature.

## 10. Start with a runbook and preview

A runbook is an executable design aid even when a human still follows it. It should identify prerequisites, inputs, normal steps, decision points, evidence, stopping conditions, recovery, and escalation.

Before automatic mutation, build the narrowest useful capability:

1. collect and normalize evidence;
2. validate inputs and preconditions;
3. calculate a proposed plan;
4. present a dry-run or preview;
5. execute one bounded case;
6. verify and record the result;
7. expand scope only from measured evidence.

A preview must use the same decision logic as execution and disclose assumptions. It cannot promise that external state will remain unchanged between preview and action. Revalidate critical preconditions immediately before mutation.

## 11. Price creation and ownership

Automation cost includes more than initial coding:

- discovery and policy clarification;
- implementation and review;
- test environments and fixtures;
- credentials and security review;
- deployment and monitoring;
- documentation and training;
- dependency and interface upgrades;
- incident response and recovery testing;
- eventual migration or retirement.

Name an owner, support boundary, and retirement condition. An unowned script becomes a hidden production dependency whose failures return the toil with less understanding.

Reuse a maintained platform or improve the product when that reduces lifecycle cost. Avoid building a general framework before one stable concrete case proves the abstraction.

## 12. Define measurements before implementation

Choose a baseline and measures tied to the original reason for automation:

- active human minutes and interruptions;
- end-to-end completion time;
- success, refusal, and ambiguous-result rates;
- manual correction and rollback frequency;
- policy or validation defects prevented;
- queue depth and oldest-item age;
- affected scope per failure;
- maintenance time spent on the automation;
- user or operator satisfaction.

A high execution count is not success. The tool may be automating demand that should disappear. Measure the system outcome and residual human work.

Instrument refusal and escalation as first-class outcomes. Rising unknown cases can signal an interface or policy change before incorrect actions occur.

## 13. Make a decision, not a slogan

Use a decision record with four possible outcomes:

- **eliminate:** redesign so the task is unnecessary;
- **stabilize:** clarify ownership, policy, or interface before automation;
- **assist:** automate evidence and mechanics while retaining a judgment gate;
- **automate:** execute the bounded contract and measure it.

A practical readiness review asks:

| Question | Ready evidence |
| --- | --- |
| Is the task understood? | several observed executions and named exceptions |
| Is the procedure stable? | versioned runbook and consistent policy |
| Are inputs trustworthy? | schema, provenance, and validation rules |
| Are effects bounded? | scope, rate, permissions, and stop controls |
| Is recovery credible? | tested rollback, compensation, or safe halt |
| Is success measurable? | baseline, verification, and target outcome |
| Is ownership durable? | maintainer, support path, and retirement trigger |

Any “no” can change the next engineering task without permanently rejecting automation.

## Common Misconceptions

- “If it repeats, automate it.” Repetition is one input; instability and risk can make stabilization the next step.
- “Automation removes human error.” It centralizes decisions and can multiply one software error across a larger scope.
- “A dry run proves execution is safe.” External state can change, and preview logic can diverge unless deliberately shared.
- “Human approval always adds safety.” A reviewer without context or a real choice is not a control.
- “Time saved is the only benefit.” Consistency, speed, security, auditability, and reduced interruption can dominate.

## Core Computer Science Concept

Automation is **policy encoded as a repeatable state transition**. A sound design defines accepted state, permitted transition, invariants, observable result, and behavior when reality falls outside the model.

## Engineering Connections

- Network and operating-system workflows become automatable only after endpoint, ownership, and failure evidence are explicit.
- Stable structured interfaces reduce parsing ambiguity and compatibility risk.
- Least-privilege identities constrain the automation's blast radius.
- Idempotency and recovery determine whether interruption and retry converge safely.

## From the Field

A team automates deletion of “unused” cloud volumes using age alone. The script removes dormant disaster-recovery data because the manual operator had always checked backup inventory and legal holds—an undocumented judgment step. Replacing deletion with evidence collection and a reviewed candidate plan reveals the missing policy; only then can tightly scoped deletion cases be automated.

## Engineering Review

### What problem does this solve?

It determines whether repeated work should be eliminated, stabilized, assisted, or automated and defines the contract required to do so safely.

### Why was it designed this way?

Automation magnifies both consistency and error, so understanding, bounded interfaces, recovery, and measurement must precede scale.

### When should I use it?

Use this decision process before turning any manual operational, development, or administrative workflow into software.

### When should I avoid it?

Do not use a score or time calculation to override unresolved policy, essential human judgment, or irreversible high-consequence uncertainty.

### How does this make me a better engineer?

It makes you design the state transition and ownership model before choosing a language or tool.

### How does this reduce waste?

It avoids automating unnecessary work, building unused frameworks, scaling unstable procedures, and maintaining ownerless scripts.

## Handbook Principle #64

> Eliminate what should not exist, stabilize what is unclear, assist what needs judgment, and automate only a bounded measurable contract.

## Practical Observation

Choose one repeated task you know well and observe three recent executions or records. Complete the automation contract and readiness review without writing code. Classify the next step as eliminate, stabilize, assist, or automate, and name one metric that could prove the decision improved the system.

## Looking Ahead

Once a bounded task is worth automating, execution details become part of its contract. Chapter 65 turns a command sequence into a shell program with explicit interpreter, arguments, streams, environment, temporary state, cleanup, and exit status.

## References

- [Google SRE Book — Eliminating Toil](https://sre.google/sre-book/eliminating-toil/)
- [Google SRE Book — The Evolution of Automation at Google](https://sre.google/sre-book/automation-at-google/)
- [Google SRE Workbook — Eliminating Toil](https://sre.google/workbook/eliminating-toil/)
