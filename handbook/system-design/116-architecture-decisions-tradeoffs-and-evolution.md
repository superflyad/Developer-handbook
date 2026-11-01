# Chapter 116 — Architecture Decisions, Tradeoffs, and Evolution

An architecture is a sequence of decisions made with incomplete information. Requirements change, traffic grows, incidents expose false assumptions, products disappear, regulations shift, and teams learn. A design that cannot evolve safely becomes a constraint even if it was correct when chosen.

The goal is not to predict every future. It is to preserve why important choices were made, identify what evidence could invalidate them, and create seams through which the system can change. Architecture decision records, explicit tradeoffs, migration plans, fitness functions, and maintained diagrams turn change from rediscovery into engineering.

This chapter does not prescribe enterprise governance, portfolio management, or one diagramming notation. It develops a lightweight practice for product teams.

## 1. Identify architecturally significant decisions

Not every choice needs a permanent record. Record a decision when changing it later would be expensive, risky, externally visible, or difficult to understand without its original context. Typical subjects include:

- service and deployment boundaries;
- public interfaces and event contracts;
- source-of-truth and consistency choices;
- identity, tenant isolation, and encryption boundaries;
- availability, recovery, and failure-containment strategies;
- major dependencies, frameworks, protocols, and managed services;
- build-versus-buy decisions;
- organization-wide construction or delivery constraints.

Do not create an ADR for variable names or an easily reversed library used inside one module. Do record why the task platform chose tenant-scoped database rows over separate databases, because that choice shapes authorization, restore, migration, cost, and blast radius.

Significance depends on consequence, not title. A small cache-key decision can be architectural when it controls tenant isolation.

## 2. Preserve context, not meeting minutes

Future readers need the forces that made one option preferable at the time:

- the problem and decision deadline;
- measurable quality requirements;
- technical, product, security, legal, cost, and staffing constraints;
- relevant system state and existing commitments;
- assumptions and their confidence;
- serious alternatives considered;
- evidence available and missing;
- stakeholders and decision owner.

Avoid a chronological transcript. “After three meetings, the team agreed to PostgreSQL” preserves process but not reasoning. “The first release needs relational constraints and tenant-scoped transactions; the team operates PostgreSQL already; expected storage is 200 GB for two years; global active-active writes are not required” allows reevaluation.

Context should be factual and time-bound. Link to requirements, measurements, experiments, and threat models rather than copying artifacts that will diverge.

## 3. State one decision precisely

Write the decision as an affirmative commitment:

> Store authoritative task and membership records in one managed relational database, using tenant-scoped keys and row-level authorization defense in depth.

This is more useful than “Database decision” or “We will use SQL.” State scope and boundaries: what is authoritative, which workloads are included, and what remains undecided.

One ADR should represent one coherent decision. If choosing a database also appears to decide messaging, caching, analytics, and disaster recovery, split the records and link their dependencies. Smaller records are easier to supersede independently.

## 4. Compare credible options against the same forces

Architecture is tradeoff analysis, not a list of technology features. Compare options using the requirements that matter to this system:

| Force | Shared relational database | Database per tenant | Key-value store |
| --- | --- | --- | --- |
| Tenant transaction | Native and familiar | Native within each tenant | Requires data-model constraints |
| Isolation | Strong controls required | Stronger credential and data boundary | Depends on key and policy design |
| Fleet operations | One main fleet | Many databases and migrations | Managed scaling can reduce operations |
| Tenant restore | Requires scoped reconstruction | Easier whole-database restore | Requires explicit export and replay design |
| Cost at small scale | Efficient | Higher baseline | Workload-dependent |
| Team experience | High | Moderate | Low |

Use estimates and experiments where uncertainty matters. Rejecting an option because “it does not scale” is weak unless scale and limit are quantified.

Include the option to defer, simplify, or remove the requirement. The best technical solution may be avoiding the problem.

## 5. Record positive and negative consequences

Every accepted option creates work and constraints. Consequences should include:

- capabilities gained;
- limitations and risks accepted;
- new operational duties;
- cost and staffing effects;
- security and privacy changes;
- migration or exit obligations;
- follow-up decisions and tests;
- conditions that would make the choice unsuitable.

Do not hide disadvantages to make approval easier. A credible ADR might say the shared database lowers early cost but increases the consequence of a missed tenant predicate and makes tenant-scoped restore harder. That consequence should produce data-layer defenses, negative tests, and a restore experiment.

Consequences are not implementation tasks alone. They explain the architectural shape the team accepts.

## 6. Track assumptions as expiring claims

An assumption is a claim used before complete evidence exists. Write it so observation can prove it wrong:

- “Peak writes remain below 2,000 per second through 2027.”
- “Ninety-nine percent of tenant restores can complete within four hours.”
- “No customer requires a dedicated regional data plane in the first two releases.”
- “The identity provider supports revocation within five minutes.”

Give important assumptions an owner, evidence source, review date, and invalidation threshold. An assumption without a trigger quietly becomes dogma.

Link assumptions to the capacity model, SLO, security review, vendor commitment, or product discovery that measures them. Chapter 117 will expose the weakest assumption as a validation target.

## 7. Distinguish reversible from costly decisions

Reversibility determines how much evidence to gather before committing.

**Easily reversible** decisions are local, hidden behind an interface, carry no durable data, and have limited operational coupling. Use a short experiment and decide quickly.

**Costly-to-reverse** decisions create public contracts, durable data, organizational dependencies, vendor-specific workflows, or large migrations. Spend more effort on alternatives, exit paths, compatibility, and validation.

Reversibility is designed, not inherent. A vendor service behind a narrow port with exportable data may be more reversible than a self-hosted platform whose assumptions leak into every component. A programming language can become irreversible when it determines hiring, build systems, observability, and shared libraries.

Do not use “reversible” to excuse careless choices. Reversal still consumes time and can harm users.

## 8. Create migration seams

A migration seam is a boundary that permits old and new implementations to coexist or be exchanged. Useful seams include:

- a stable interface around a vendor or storage engine;
- versioned schemas and event envelopes;
- an adapter that translates old and new contracts;
- partition routing that can move tenants gradually;
- change-data capture or an outbox for controlled replication;
- feature flags that select behavior by cohort;
- export formats independent of internal storage;
- observability that compares both paths.

Do not build speculative abstraction around every component. Create seams where replacement is plausible and consequence is high. The seam must preserve semantics, not merely method names.

A database repository that exposes vendor-specific transactions, query syntax, and ordering assumptions throughout the application is not a useful seam. Neither is a “generic” interface so weak that callers reconstruct the vendor model themselves.

## 9. Plan migrations as state transitions

A migration is a temporary distributed system. It has old state, intermediate states, new state, concurrency, partial failure, reconciliation, and rollback limits.

A safe staged migration often follows:

1. Define invariants and success measures.
2. Make the old system accept the future shape where necessary.
3. Backfill with checkpoints and bounded load.
4. Capture or dual-write new changes with an explicit consistency strategy.
5. Compare records and behavior.
6. Read from the new path for a small cohort.
7. Expand while monitoring errors, latency, and business outcomes.
8. Stop old writes.
9. Observe through a defined confidence window.
10. Remove old state only after rollback is no longer required.

“Rollback” is not always reversing a deployment. Once new-format data or external effects exist, the safe response may be roll-forward, compatibility, or restoration from a verified checkpoint. State the point of no return.

## 10. Evaluate build versus buy across the lifecycle

Build-versus-buy is not “license cost versus engineer salary.” Compare total responsibility:

- fitness for required behavior and quality attributes;
- integration and migration effort;
- operation, upgrades, security response, and support;
- customization pressure and roadmap control;
- pricing shape and cost at expected scale;
- data portability and exit time;
- vendor stability and dependency concentration;
- compliance, residency, and audit evidence;
- internal expertise and opportunity cost.

Buying transfers implementation and some operational work, not accountability for system outcomes. Building provides control but creates a long-lived product the team must staff.

Run a proof for the highest-risk assumption, not the easiest demo. Test tenant isolation, failure behavior, export, rate limits, recovery, and cost at representative scale. Record contractual claims separately from observed behavior.

## 11. Make technical debt specific

Technical debt is a present design compromise that increases the cost or risk of future change. Use the term only when the principal and likely interest can be described.

Good debt record:

> Task search shares the primary database for the first release. This avoids operating a search index, but wildcard queries approach the 200 ms budget at 500 GB. Reevaluate at 300 GB or when p95 exceeds 150 ms for seven days. The data team owns the decision; an outbox preserves an index migration seam.

Poor debt record:

> The database is technical debt.

Some debt is intentional and rational. Other debt is accidental drift, missing maintenance, or a defect. Classify it so the response matches: repay, contain, monitor, accept, or remove the requirement. A backlog item with no trigger or owner is not managed debt.

## 12. Deprecate before removing

Public contracts need an explicit lifecycle. Deprecation means the contract remains usable but should no longer be adopted. Removal or sunset ends support. Communicate:

- what is deprecated and why;
- the supported replacement;
- the date and conditions for removal;
- compatibility and migration guidance;
- usage telemetry and affected owners;
- support and exception path.

For HTTP resources, standards define `Deprecation` and `Sunset` response fields that can complement documentation and direct communication. Headers alone are insufficient: many consumers will not inspect them.

Do not remove by calendar alone. Track remaining use, identify critical consumers, prove the replacement, and handle clients that cannot migrate. Conversely, indefinite compatibility carries security, test, and operational cost. Make exceptions explicit and expiring.

## 13. Use fitness functions to guard architecture

A fitness function is an objective check of an architectural property. It turns a desired characteristic into continuous or periodic feedback. Examples:

- dependency rules prevent domain code from importing infrastructure adapters;
- contract tests prove old clients can read the new event schema;
- latency tests enforce a p95 budget under a representative workload;
- policy tests deny cross-tenant access combinations;
- recovery drills prove the stated RTO and RPO;
- cost checks flag per-tenant spend above a threshold;
- static analysis rejects unencrypted public endpoints;
- runtime checks detect cyclic service dependencies or forbidden calls.

Fitness functions may be tests, metrics, policy rules, architecture analysis, or scheduled exercises. Choose the cheapest evidence that detects meaningful drift. A unit test cannot prove regional recovery; a yearly manual review is too slow for import boundaries.

Avoid vanity functions. Counting services or test lines does not prove modularity or reliability unless tied to a specific risk.

## 14. Balance competing fitness functions

Architecture has multiple dimensions: delivery speed, latency, availability, security, operability, cost, privacy, and evolvability. Improving one can degrade another. A cache reduces latency but increases staleness and privacy surface. Database-per-tenant improves isolation but increases fleet cost and migration work.

State priority and acceptable ranges rather than seeking a single optimum. For example:

- tenant isolation is a hard invariant;
- p95 latency must remain below 300 ms at expected load;
- monthly infrastructure cost should remain within the approved range;
- recovery must meet the four-hour RTO;
- a normal schema change must deploy without coordinated downtime.

When constraints conflict, update the ADR or requirements. Do not quietly weaken the test until it passes.

## 15. Maintain diagrams as queryable models

Diagrams answer specific questions. Keep a small set with declared scope:

- system context: people, external systems, and ownership;
- containers or deployable units: responsibilities and major communication;
- data flow and trust boundaries: sensitive movement and controls;
- deployment: runtime instances, networks, regions, and failure domains;
- sequence: ordering, retries, asynchronous boundaries, and failure paths;
- data model: identity, ownership, and invariants.

Label title, scope, environment, date or version, and legend. Show protocol and direction where relevant. Store diagrams near the decisions and code they describe. Prefer text-based or generated representations when they improve review and version history, but clarity matters more than format.

A diagram is stale when it makes a false claim, not merely when its colors are old. Assign ownership and update triggers such as a new service, data flow, trust boundary, or deployment region.

## 16. Keep code, records, and diagrams connected

No artifact is the sole source of architecture. Code shows implementation but rarely preserves rejected options. ADRs preserve reasoning but can drift from implementation. Diagrams explain relationships but omit detail.

Create links among them:

- ADRs link to requirements, diagrams, experiments, and follow-up work;
- code or configuration references the governing ADR where a surprising constraint appears;
- fitness functions name the decision or quality attribute they enforce;
- diagrams link to the ADR that changed a boundary;
- pull requests identify affected decisions and diagrams;
- the decision index shows current, proposed, deprecated, and superseded records.

Do not paste the same explanation into every location. Link to one maintained record and put implementation detail beside the implementation.

## 17. Review decisions on evidence, not age

An accepted ADR remains valid until new evidence, changed forces, or a deliberate review says otherwise. Useful triggers include:

- an assumption crosses its threshold;
- an SLO or cost boundary is repeatedly missed;
- a security threat or privacy use changes;
- the vendor changes price, capability, ownership, or support;
- a dependency approaches end of life;
- a migration seam proves inadequate;
- organizational ownership changes;
- a major incident contradicts the failure model.

A calendar review can catch neglected records, but age alone does not invalidate a decision. Focus attention on high-consequence assumptions and changing dependencies.

If the decision changes, create a new ADR that supersedes the old one. Preserve the old record so readers can reconstruct why both states existed.

## 18. Avoid architecture review as a gate ceremony

Review should improve a proposal while change is still affordable. Include product, application, data, security, operations, and cost perspectives appropriate to the decision. Circulate context and options before the meeting. Resolve factual questions asynchronously where possible.

During review, ask:

- Which requirement or constraint drives this choice?
- What evidence distinguishes the options?
- Which assumption has the largest consequence if wrong?
- What new failure mode or operational duty appears?
- How will we know the decision is working?
- How can the system migrate if it stops working?
- Who owns follow-up and residual risk?

Record the decision and unresolved experiments. Do not require consensus from everyone for every decision; define who advises, who decides, and who owns the outcome.

## 19. Use a lightweight ADR lifecycle

A practical lifecycle is:

- **Proposed:** context and options are under review.
- **Accepted:** the decision governs new work.
- **Deprecated:** still present but not recommended for new use.
- **Superseded:** replaced by a linked accepted decision.
- **Rejected:** considered and deliberately not chosen, when preserving that fact has value.

Once accepted and implemented, avoid rewriting its reasoning to match current understanding. Correct trivial errors transparently, but use a superseding ADR for a changed decision.

Keep records short enough to read. A concise record linked to evidence is more likely to remain useful than a comprehensive document nobody revisits.

## 20. Write an example decision record

```markdown
# ADR-0017: Use a shared relational store for task metadata

- Status: Accepted
- Date: 2026-11-01
- Owner: Data platform lead
- Review triggers: 300 GB, p95 write latency above 150 ms for 7 days,
  or a contractual dedicated-storage requirement

## Context

The first release needs tenant-scoped transactions across tasks, membership,
and audit references. Forecast peak load is 2,000 writes/second. The team
operates PostgreSQL. Tenant-scoped restore is required within four hours.

## Options

1. Shared relational database with tenant-scoped keys and row policies.
2. Separate database per tenant.
3. Managed key-value store with application-enforced invariants.

## Decision

Use option 1 for authoritative task metadata. Require tenant scope in keys,
queries, cache keys, and authorization tests. Keep attachments in object storage.

## Consequences

- Lower initial fleet cost and familiar transactional behavior.
- A missed scope check has multi-tenant consequence.
- Tenant restore requires a tested scoped reconstruction workflow.
- An outbox and portable export format preserve migration seams.

## Verification

- Cross-tenant negative tests run on every change.
- Capacity and restore exercises run quarterly.
- Storage, latency, denied access, and per-tenant cost are monitored.
```

The record is specific enough to challenge. If tenant restore takes eight hours or a dedicated-storage contract appears, the trigger causes reevaluation; it does not prove that the original team failed.

## 21. Encode a decision-quality contract

An executable contract can detect incomplete records before acceptance:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class DecisionRecord:
    title: str
    status: str
    context: str
    decision: str
    options: tuple[str, ...]
    positive_consequences: tuple[str, ...]
    negative_consequences: tuple[str, ...]
    assumptions: tuple[str, ...]
    review_triggers: tuple[str, ...]
    verification: tuple[str, ...]
    owner: str
    migration_seam: str
    supersedes: str | None = None

    def validate(self) -> None:
        allowed = {"proposed", "accepted", "deprecated", "superseded", "rejected"}
        if self.status not in allowed:
            raise ValueError("decision status is invalid")
        if not all((self.title.strip(), self.context.strip(), self.decision.strip())):
            raise ValueError("decision lacks title, context, or commitment")
        if len(self.options) < 2:
            raise ValueError("decision does not compare credible options")
        if not self.positive_consequences or not self.negative_consequences:
            raise ValueError("tradeoffs omit positive or negative consequences")
        if not self.assumptions or not self.review_triggers:
            raise ValueError("assumptions cannot be invalidated")
        if not self.verification:
            raise ValueError("decision has no fitness function or evidence")
        if not self.owner.strip():
            raise ValueError("decision has no owner")
        if not self.migration_seam.strip():
            raise ValueError("costly choice has no migration seam")
        if self.status == "superseded" and not self.supersedes:
            raise ValueError("superseded decision lacks a successor link")
```

Tests emphasize omissions that make future revision unsafe:

```python
from dataclasses import replace
import unittest

from decision_record import DecisionRecord


def valid_record() -> DecisionRecord:
    return DecisionRecord(
        title="Use shared relational task storage",
        status="accepted",
        context="Tenant transactions and four-hour restores are required.",
        decision="Use managed PostgreSQL for authoritative task metadata.",
        options=("shared relational", "database per tenant", "key-value"),
        positive_consequences=("familiar transactions",),
        negative_consequences=("scoped restore is more complex",),
        assumptions=("peak writes remain below 2,000 per second",),
        review_triggers=("p95 write latency exceeds 150 ms for seven days",),
        verification=("quarterly restore exercise", "cross-tenant denial tests"),
        owner="data platform lead",
        migration_seam="outbox and portable tenant export",
    )


class DecisionRecordTests(unittest.TestCase):
    def test_complete_record_is_accepted(self):
        valid_record().validate()

    def test_unknown_status_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "status"):
            replace(valid_record(), status="done").validate()

    def test_single_option_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "credible options"):
            replace(valid_record(), options=("shared relational",)).validate()

    def test_hidden_disadvantage_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "negative"):
            replace(valid_record(), negative_consequences=()).validate()

    def test_assumption_without_trigger_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalidated"):
            replace(valid_record(), review_triggers=()).validate()

    def test_decision_without_evidence_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "fitness"):
            replace(valid_record(), verification=()).validate()

    def test_unowned_decision_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "owner"):
            replace(valid_record(), owner="").validate()

    def test_irreversible_choice_without_seam_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "migration seam"):
            replace(valid_record(), migration_seam="").validate()

    def test_superseded_record_needs_successor(self):
        with self.assertRaisesRegex(ValueError, "successor"):
            replace(valid_record(), status="superseded").validate()


if __name__ == "__main__":
    unittest.main()
```

This validation cannot judge whether PostgreSQL is the right choice. It can ensure that the choice exposes alternatives, disadvantages, assumptions, evidence, ownership, and a path to change.

## 22. Review decisions and evolution

Before accepting an architectural decision, ask:

### Decision quality

- Is the decision significant, scoped, and stated as a commitment?
- Are the driving requirements, constraints, and deadline explicit?
- Were credible options compared using the same forces?
- Are positive and negative consequences honest?

### Evidence and ownership

- Which assumptions are uncertain, measurable, and consequential?
- What experiment or fitness function will test them?
- Who decides, implements, operates, and accepts residual risk?
- Which threshold or event triggers reevaluation?

### Evolution

- Is the choice reversible, and what makes reversal expensive?
- Which interface, export, compatibility layer, or routing seam supports migration?
- Does the migration plan include intermediate states, reconciliation, and a point of no return?
- How will consumers learn about deprecation and sunset?

### Artifact integrity

- Are code, records, tests, and diagrams linked without duplicating truth?
- Is the current decision discoverable in an index?
- Will a new record supersede rather than erase historical context?

## Common Misconceptions

- **“An ADR documents the architecture.”** It documents one significant decision and its reasoning.
- **“Accepted decisions are permanent.”** Their historical record is stable; their applicability can be superseded.
- **“More options make analysis rigorous.”** Only credible options evaluated against real forces add value.
- **“Abstraction makes every choice reversible.”** Leaked semantics, data gravity, operations, and organization can defeat an interface.
- **“Technical debt means bad code.”** Managed debt is a known tradeoff with consequence, trigger, and owner.
- **“A diagram is documentation once exported.”** A false diagram is worse than no diagram and needs an update trigger.
- **“Architecture review is approval by seniority.”** Useful review challenges evidence, assumptions, consequences, and evolution paths.

## Core Computer Science Concept

This chapter applies **decision theory under uncertainty, option value, modularity, information hiding, compatibility, state-machine migration, feedback control, and executable invariants**. Good architecture preserves high-value future choices while continuously testing present assumptions.

## Engineering Connections

- Requirements and quality forces originate in Chapter 106.
- Interface, data, and migration seams build on Chapters 107 and 108.
- Capacity, consistency, messaging, and resilience evidence use Chapters 109 through 114.
- Security decisions and residual risk connect directly to Chapter 115.
- Chapter 117 assembles the records, diagrams, estimates, and experiments into a complete review.

## From the Field

A team chooses a hosted search service after a successful demo but records no export path, cost threshold, or query boundary. Three years later, vendor-specific ranking expressions appear in every service, traffic makes pricing unsustainable, and no one remembers which relevance behavior was essential. A short ADR, representative cost experiment, stable search interface, raw-index export, and spend fitness function would not make migration free, but would turn surprise into a planned decision.

## Engineering Review

### What problem does this solve?

It prevents important reasoning from disappearing and prevents old decisions from becoming permanent merely because change is poorly prepared.

### Why was it designed this way?

Short immutable records preserve historical truth, while measurable triggers, fitness functions, and migration seams let the implementation evolve as evidence changes.

### When should I use it?

Use it for choices with durable data, public contracts, cross-team coupling, operational consequence, significant cost, or difficult reversal.

### When should I avoid it?

Do not create governance overhead for trivial local choices, and do not use records as a substitute for experiments, prototypes, or working software.

### How does this make me a better engineer?

You learn to compare options through explicit forces, admit uncertainty, preserve rationale, and design change paths before urgency removes them.

### How does this reduce waste?

It reduces repeated debates, speculative abstraction, accidental lock-in, stale diagrams, indefinite compatibility, and migrations started without invariants or evidence.

## Handbook Principle #116

> Record significant decisions with their forces, rejected options, consequences, assumptions, evidence, owner, and exit path; preserve the history, test the present, and supersede when reality changes.

## Practical Observation

Select one dependency that would be painful to replace. Find the accepted decision, cost and reliability assumptions, owner, export mechanism, compatibility boundary, and test proving the replacement path. Every missing item is part of the real lock-in.

## Looking Ahead

Chapter 117 integrates the complete Part IX method into one system design review: requirements, estimates, interfaces, data, consistency, asynchronous work, resilience, security, operations, cost, decisions, risks, and staged validation.

## References

- [AWS Prescriptive Guidance — Architectural decision record process](https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/adr-process.html)
- [AWS Prescriptive Guidance — Best practices for architectural decision records](https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/best-practices.html)
- [The GDS Way — Documenting architecture decisions](https://gds-way.digital.cabinet-office.gov.uk/standards/architecture-decisions.html)
- [Architectural Decision Records organization](https://adr.github.io/)
- [Thoughtworks — Fitness function-driven development](https://www.thoughtworks.com/insights/articles/fitness-function-driven-development)
- [RFC 9745 — The Deprecation HTTP Response Header Field](https://www.rfc-editor.org/rfc/rfc9745.html)
- [RFC 8594 — The Sunset HTTP Header Field](https://www.rfc-editor.org/rfc/rfc8594.html)
