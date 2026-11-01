# Chapter 106 — From Requirements to a System Model

“Design a task-management system” is not a requirement. It does not say who manages tasks, what a task means, which operations matter, how many people collaborate, how quickly changes must appear, what may be lost, what must remain private, or what failure the business can tolerate.

Choosing components before answering those questions produces an inventory, not a design.

The central idea is:

> A useful system model turns desired outcomes, actors, workloads, data, quality scenarios, constraints, and uncertainty into statements that can be measured, challenged, and traced to later decisions.

## 1. Design the problem before the solution

Early system design has two jobs:

1. discover what outcome is actually required;
2. construct a model precise enough to evaluate possible solutions.

The model is not the deployed system. It is an intentionally smaller description of the system and its environment. A useful model exposes the facts that change architecture:

- actors and their authority;
- critical user and machine journeys;
- operations and state transitions;
- data identity, ownership, sensitivity, and lifecycle;
- workload volume, distribution, bursts, and growth;
- latency, availability, durability, and recovery objectives;
- external dependencies and failure domains;
- legal, contractual, security, cost, and organizational constraints;
- assumptions, unknowns, and evidence;
- measures that distinguish success from failure.

Do not start with “microservices or monolith,” “SQL or NoSQL,” or “which cloud service.” Those are candidate decisions. Requirements describe the problem against which decisions are judged.

## 2. Write a bounded problem statement

A problem statement should identify the user, need, current pain, desired outcome, and boundary without embedding an implementation.

Weak:

> Build a real-time scalable task platform with Kafka and microservices.

Stronger:

> Distributed product teams need to create, assign, discuss, and track work across web and mobile clients. A committed task change should be visible to active collaborators within two seconds under the expected peak workload. Authorized teams must not see one another's private projects. The first release serves internal teams in one legal jurisdiction and does not replace document editing, source control, or payroll systems.

The stronger statement still contains questions, but it creates testable boundaries. “Real-time,” “scalable,” and “secure” are aspirations. Two seconds, a defined peak, tenant isolation, jurisdiction, and explicit non-goals can drive design and validation.

Keep the problem statement short enough that product, engineering, security, operations, and data stakeholders can correct it together.

## 3. Identify stakeholders, actors, and incentives

An actor is an entity that interacts with the system. A stakeholder is anyone whose outcome, risk, or work is materially affected. They overlap but are not identical.

Actors may include:

- anonymous and authenticated users;
- administrators, support staff, and auditors;
- mobile, web, CLI, and automation clients;
- upstream identity or billing systems;
- downstream notification, analytics, and archive systems;
- scheduled jobs and event consumers;
- attackers and accidental misusers.

Stakeholders also include compliance, finance, legal, privacy, security, operations, accessibility, customer support, and the team that must evolve the system. Record what each needs, controls, and fears.

A product owner may optimize adoption, an operator recovery, finance unit cost, and privacy counsel data minimization. These are not distractions from architecture. They reveal tradeoffs that the architecture must make visible.

Do not use “the user” as a universal actor. An organization owner deleting a project, a member editing a task, an integration reading changes, and an auditor reviewing history have different authority and failure consequences.

## 4. Start from critical journeys

A use case describes an interaction between an actor and the system toward an outcome. A critical journey is a use case whose failure causes material customer, business, safety, legal, or operational harm.

For each journey, record:

- initiating actor and authorization context;
- trigger and preconditions;
- normal sequence and business result;
- data read and changed;
- downstream effects;
- expected volume and time sensitivity;
- duplicate, concurrent, invalid, and partial inputs;
- user-visible failure and recovery;
- evidence that proves success.

Example:

```text
journey: assign a task
actor: project member with task-edit authority
preconditions: project and assignee are active in the same tenant
command: assign task T to member M using expected task version 17
result: assignment becomes version 18 and an audit event is durable
visible propagation: active collaborators observe it within 2 seconds
conflict: a stale version receives a conflict, not silent overwrite
downstream: notification may be delayed without rejecting the assignment
success evidence: authoritative read returns M and the audit event identifies the actor
```

This journey separates the committed business effect from a notification side effect and states a concurrency policy. Later chapters can choose interfaces, storage, and messaging to satisfy it.

## 5. Specify functional behavior as observable effects

Functional requirements say what the system must do. Write them from observable inputs, authorization, state changes, outputs, and errors rather than screen layouts or internal classes.

Useful forms include:

- Given an active project member and a valid task title, creating a task returns a stable task identity and persists its initial state.
- Repeating a create command with the same idempotency key and payload returns the original result within the supported retry window.
- A user without project membership cannot read the project's task content.
- Deleting a project prevents new writes immediately and completes the declared retention workflow.
- An export contains the documented snapshot or time range and records who requested it.

State what happens for invalid, unauthorized, duplicate, late, missing, and conflicting inputs. Error behavior is part of the contract, not an implementation afterthought.

Avoid requirements such as “use a REST API,” “store tasks in PostgreSQL,” or “publish to Kafka” unless an external compatibility constraint genuinely requires them. A functional requirement should survive consideration of multiple architectures.

## 6. Turn quality words into scenarios

Availability, performance, security, modifiability, usability, testability, and scalability are too broad to evaluate as single adjectives. The Software Engineering Institute's quality-attribute scenario method makes them operational through six elements:

1. source of stimulus;
2. stimulus;
3. environment;
4. stimulated artifact;
5. required response;
6. response measure.

For example:

```text
source: authenticated project members
stimulus: submit task reads
environment: normal weekday peak at 2,000 requests/second
artifact: task-read path for projects in the primary region
response: authorize and return the current committed task representation
measure: 99% complete within 300 ms and 99.9% succeed over 28 days
```

An availability scenario might instead state that one compute-zone failure during peak traffic must not interrupt more than a bounded percentage of valid requests and must recover without operator data repair.

The environment matters. A response time measured with one warm object in a development environment is not a peak-production requirement. The source and artifact matter because anonymous search, administrative exports, and interactive writes may have different objectives.

Quality scenarios are architectural test cases. They do not dictate a design, but they expose which mechanisms need evidence.

## 7. Define success from the user's boundary

Success measures should describe useful outcomes, not only internal activity. “The API returned 200” is insufficient if the accepted order never becomes fulfillable. “The queue is available” is insufficient if the user journey depends on a failed consumer.

For each critical journey, define:

- a service-level indicator observable at the appropriate boundary;
- a good-event definition;
- a valid-event denominator;
- a threshold and measurement window;
- exclusions narrow enough not to hide real harm;
- a business or user outcome where technical success is ambiguous.

Latency often needs more than an average. A requirement may state that 90% complete under one threshold and 99% under another. Availability should define which requests count and which responses are good. Durability should define the acknowledged event and acceptable loss window. Freshness should define the source commit and observation point.

Google's SRE guidance uses critical user journeys and user-centered service-level objectives for this reason: component health is useful evidence, but the journey is the outcome.

## 8. Model the workload, not one average

Architecture responds to distributions, concurrency, skew, and bursts. Record at least:

- active and total actors;
- requests or operations by type;
- reads-to-writes ratio;
- concurrent connections and sessions;
- payload and object size distributions;
- fan-out per operation;
- hot keys, tenants, projects, or time windows;
- burst magnitude and duration;
- daily, weekly, seasonal, and event-driven cycles;
- background, batch, replay, and migration traffic;
- current, near-term, and longer-horizon growth.

Separate arrival rate from concurrency. One thousand one-second requests per second imply roughly one thousand in flight under stable conditions; one thousand ten-second streams per second imply a different connection and memory model. Separate logical operations from amplified work: one task update may produce ten notifications, index mutations, audit events, and analytics records.

Use ranges and distributions when evidence is incomplete:

```text
ordinary peak: 800–1,200 task reads/second
launch scenario: up to 3,000/second for 15 minutes
largest known tenant: 8% of reads and 22% of writes
task body: median 2 KiB, p99 80 KiB, hard limit 256 KiB
```

Mark the source and date. A capacity number without provenance becomes folklore.

## 9. Estimate to discover sensitivity

Early estimates need not predict the future exactly. They should reveal which variables dominate storage, bandwidth, concurrency, cost, or recovery.

Suppose the first year expects:

```text
2 million tasks
average current representation: 4 KiB
average 12 retained change events per task: 0.8 KiB each
two indexed projections totaling 1.5 times current-state size
```

An order-of-magnitude logical estimate is:

```text
current state = 2,000,000 * 4 KiB           ~= 7.6 GiB
history       = 2,000,000 * 12 * 0.8 KiB    ~= 18.3 GiB
indexes       = 7.6 GiB * 1.5               ~= 11.4 GiB
logical total                                   ~= 37.3 GiB
```

Replication, backups, versions, logs, temporary migration space, and storage-engine overhead add to this. The conclusion is not “allocate exactly 37.3 GiB.” It is that retained history dominates current task bodies and that retention or event size materially changes the design.

Record the equation, units, range, and sensitivity. Recalculate when evidence changes. False precision hides uncertainty.

## 10. Inventory data by meaning and lifecycle

List data domains before choosing a database. For each, record:

- business meaning and authoritative owner;
- stable identity and tenant boundary;
- creation, mutation, and deletion rules;
- relationships and invariants;
- access patterns and required indexes;
- sensitivity and allowed readers;
- residency, retention, legal hold, and erasure;
- version history and audit requirements;
- freshness and consistency needs;
- backup, recovery point, and recovery time;
- export, migration, and archival needs.

For the task system, data may include identities, organizations, projects, memberships, tasks, comments, attachments, audit records, notifications, search projections, and usage records. They should not automatically share one store or one lifecycle. Search is often a derived projection; audit records may need longer retention; notification attempts may be ephemeral; attachments may have different size and malware controls.

Distinguish authoritative state from caches, indexes, replicas, analytics copies, and exports. Every derived copy needs a source, freshness contract, rebuild method, access policy, and deletion propagation path.

## 11. Write invariants before storage schemas

An invariant is a property that must remain true across valid state transitions. Examples include:

- a task belongs to exactly one project;
- an assignee must be an active member of the task's tenant at assignment time;
- a task version increases monotonically for accepted changes;
- an idempotency key cannot identify two different create payloads within its scope;
- deleting a tenant cannot expose its stable names to another tenant;
- an acknowledged audit event is never silently rewritten.

Also record whether an invariant must hold synchronously, may converge within a window, or can be repaired later. “Counts may be stale for 30 seconds” is different from “membership authorization may be stale for 30 seconds.”

Later component selection should show how transactions, constraints, conditional writes, serialization, events, or reconciliation preserve each invariant. If an invariant has no enforcement owner, the system model is incomplete.

## 12. Model state transitions and concurrency

For important entities, describe states, commands, preconditions, transitions, and terminal conditions.

```text
OPEN --complete--> COMPLETED
OPEN --cancel----> CANCELED
COMPLETED --reopen--> OPEN
CANCELED --reopen----> OPEN only with project-admin authority
```

Ask what happens when two actors issue commands from the same prior version. Possible policies include first writer wins, last writer wins, optimistic conflict, field-level merge, commutative operation, or serialized ownership. The correct choice follows business semantics.

Separate command acceptance from propagation. Completing a task might be authoritative immediately while search, notifications, and analytics update asynchronously. The model should say which observations can lag, by how much, and what users see during lag.

This chapter records the contract; Chapters 107, 110, and 112 develop interface evolution, concurrent change, and asynchronous realization.

## 13. Map system context and external dependencies

A context model shows what is inside the proposed system, which external actors and systems interact with it, and what crosses each boundary.

```text
users and clients
       |
       v
task collaboration system
  | identity provider
  | email/push provider
  | object malware scanner
  | analytics destination
  | support and audit tooling
```

For every dependency, record:

- owner and support path;
- interface and authentication;
- data sent and received;
- latency, availability, quota, and rate limits;
- timeout and retry behavior;
- duplicate and ordering semantics;
- degraded behavior and recovery;
- version and deprecation process;
- cost and legal constraints.

Do not inherit a dependency's advertised availability as the user's availability. Model how the dependency participates in the journey. Task creation may remain available while email is delayed; login may not remain available when the identity provider fails unless an existing session path is intentionally supported.

## 14. Draw trust and authority boundaries early

Record who authenticates each actor, who authorizes each operation, what tenant or ownership context applies, and where untrusted data enters. Include administrators, support tools, background jobs, deployment identities, and data pipelines—not only end users.

For each boundary, ask:

- which principal acts and how identity is proven;
- which resource and action are requested;
- which policy and business relationship authorize it;
- which data crosses, at what sensitivity;
- where input is validated and output encoded;
- which action requires step-up approval or separation of duties;
- what is audited and who may read the evidence;
- how access is revoked and stale sessions expire.

Security requirements should be tied to risks and abuse cases: cross-tenant reads, identifier guessing, malicious attachments, bulk export, privilege escalation, support impersonation, event forgery, and deletion bypass. “Use encryption” names a mechanism without defining the threat, plaintext path, key authority, or recovery dependency.

## 15. Treat privacy and compliance as data behavior

Compliance is not a checkbox appended to a diagram. Translate obligations into data and operational requirements:

- approved collection purpose and minimization;
- consent or other processing basis where applicable;
- residency and cross-border transfer boundaries;
- access, correction, export, erasure, and objection workflows;
- retention schedules and legal holds;
- audit evidence and administrator accountability;
- incident detection and notification timelines;
- vendor and subprocessor constraints;
- accessibility and records requirements.

Distinguish legal fact from team assumption and obtain qualified review for applicable obligations. The architecture should trace personal or regulated data through primary stores, logs, search indexes, caches, backups, events, analytics, support tools, and exports.

A deletion objective must state what is deleted immediately, what becomes inaccessible, what ages out of immutable backups, which holds override deletion, and what proof is retained.

## 16. Define availability, durability, and recovery separately

These qualities are related but not interchangeable:

- **availability** asks whether a valid operation can complete now;
- **durability** asks whether an acknowledged effect survives defined failures;
- **recovery point objective** bounds acceptable lost history after disaster;
- **recovery time objective** bounds restoration time;
- **freshness** bounds observation lag;
- **continuity** describes useful degraded operation during disruption.

Name the operation and boundary. The system might allow task reads during a regional dependency failure while rejecting writes, preserve acknowledged writes but miss its recovery-time goal, or serve a stale project list while task detail remains current.

Define failure environments: one process, node, zone, region, dependency, credential, bad deployment, corrupted dataset, or administrative error. “Highly available” without a failure model and measurement window cannot be tested.

## 17. Include degraded modes and overload

Capacity is not only the largest expected number. The model needs behavior when demand, dependency latency, or background work exceeds capacity.

Decide which work is:

- essential and admitted first;
- optional and shed;
- delayed into a bounded queue;
- rejected with a retry contract;
- served from stale or reduced data;
- limited per actor or tenant;
- suspended during recovery.

For the task system, authenticated task reads and writes may outrank search indexing, notification fan-out, analytics export, and attachment previews. A degraded mode should preserve security and core invariants. It is not acceptable to bypass authorization because the membership service is slow.

State recovery conditions and backlog limits. A queue can convert an outage into a growing recovery problem if its arrival rate continues to exceed drain capacity.

## 18. Bound growth by horizon

Separate at least three horizons:

- **launch:** what must be true for the first safe release;
- **planning:** what evidence supports the next 6–18 months;
- **contingency:** which plausible change would invalidate the architecture.

Examples of contingency triggers include a tenfold traffic increase, entry into a new jurisdiction, enterprise tenant isolation, real-time offline collaboration, a new file-size class, or a recovery objective tighter than the chosen data platform supports.

Do not build every contingency now. Preserve options where cheap, define signals, and record migration paths for expensive later changes. Premature distribution creates current complexity; ignoring a known hard boundary creates a future emergency.

## 19. Record cost and organizational constraints

A technically possible design may be unaffordable or unownable. Record:

- launch and steady-state budget ranges;
- dominant unit economics such as cost per active tenant, operation, or GiB-month;
- traffic, storage, observability, egress, support, and recovery costs;
- team size, skills, on-call coverage, and delivery date;
- approved technologies, regions, vendors, and procurement lead times;
- migration, training, and operational capacity;
- portability or exit obligations.

Time and team skill are architecture inputs. A design requiring three new distributed data systems, 24-hour operations, and specialist tuning does not satisfy a six-person team's requirement merely because it scales on paper.

Do not turn a budget into an arbitrary component ban. State the outcome and tradeoff: perhaps archival search may take minutes to keep interactive-path cost bounded, or attachment retention must be tiered after 90 days.

## 20. Separate facts, constraints, assumptions, and decisions

These categories require different handling:

- **fact:** supported by current evidence, such as measured peak traffic;
- **constraint:** a boundary the design must satisfy, such as an approved jurisdiction;
- **assumption:** believed for now but capable of being false;
- **decision:** a chosen response among alternatives;
- **unknown:** important information not yet established.

Maintain an assumption register:

```text
ID: A-07
assumption: 99% of projects have fewer than 200 active members
why it matters: notification fan-out and membership-cache size
evidence: 60-day sample from the current tool; enterprise migration excluded
owner: product analytics
validate by: enterprise cohort analysis before beta
if false: batch fan-out and isolate very large projects
```

An assumption needs an owner, evidence, validation date, architectural impact, and response if false. Otherwise it becomes an invisible dependency.

## 21. Prioritize conflicts instead of collecting wishes

Requirements compete. Stronger consistency may increase coordination latency. Longer retention increases cost and privacy exposure. Tighter availability can increase operational complexity. More configurability can reduce testability.

Prioritize with stakeholders using consequence and business value, not volume of adjectives. One useful classification is:

- required for launch or legal/safety correctness;
- important with an agreed degradation or later milestone;
- desirable if evidence justifies cost;
- explicitly out of scope.

For high-impact quality scenarios, rank business importance and technical risk. A scenario that is both essential and uncertain deserves early validation. Record whose priority it is and what tradeoff was accepted.

Do not assign everything “must.” BCP 14 terms such as MUST, SHOULD, and MAY are useful only when the document defines them and uses them deliberately. Priority still needs rationale and consequence.

## 22. Define scope and non-goals

A boundary says which responsibilities the system accepts. Non-goals prevent adjacent needs from silently entering the architecture.

For the first task-system release, non-goals might include:

- simultaneous character-level document editing;
- public anonymous projects;
- arbitrary customer code execution;
- payroll or time-sheet calculation;
- permanent offline writes from disconnected devices;
- cross-region active-active writes;
- legal-record archival beyond the stated audit retention.

Non-goals do not mean “never.” They say the current model does not promise these outcomes. If one becomes required, revisit the assumptions and decisions it invalidates.

Also identify system-of-record boundaries. The task system may reference identity from an enterprise directory without becoming the authoritative employee record.

## 23. Turn unknowns into validation experiments

An architecture review should expose uncertainty, not disguise it. Rank unknowns by probability, consequence, and the cost of learning later.

Possible experiments include:

- measure actual operation and object-size distributions;
- trace a critical journey through current dependencies;
- prototype the highest-risk integration;
- load-test a representative access pattern with skew;
- simulate a dependency timeout and backlog recovery;
- restore a realistic dataset into an isolated environment;
- test tenant authorization with adversarial cases;
- review data flows with privacy and security stakeholders;
- price the dominant workload with upper and lower bounds.

Define the decision each experiment informs and its acceptance threshold. “Build a proof of concept” is not useful unless it can change a decision.

Retire assumptions when evidence arrives, and version the system model. Discovery continues after launch.

## 24. Produce one shared model

A concise first design packet can contain:

1. problem statement, outcomes, scope, and non-goals;
2. stakeholders, actors, and critical journeys;
3. functional requirements and important error behavior;
4. ranked quality-attribute scenarios;
5. workload and growth model with source dates;
6. data inventory, invariants, and lifecycle;
7. system context, dependencies, trust, and failure boundaries;
8. security, privacy, recovery, cost, and organizational constraints;
9. assumptions, unknowns, risks, and validation experiments;
10. success measures and review ownership.

Use diagrams where relationships are difficult to express linearly, but keep the underlying statements in text or structured data that can be reviewed and tested. A polished diagram with unnamed arrows, no workload, and no failure behavior is decoration.

Trace later decisions back to this model. If a component cannot be connected to a requirement, it may be unnecessary. If a requirement has no mechanism or validation, the design is incomplete.

## 25. Encode a minimum system-model contract

The following standard-library model rejects vague requirements and unowned uncertainty. It does not select an architecture.

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class QualityScenario:
    name: str
    source: str
    stimulus: str
    environment: str
    artifact: str
    response: str
    measure: str

    def validate(self) -> None:
        values = (
            self.name, self.source, self.stimulus, self.environment,
            self.artifact, self.response, self.measure,
        )
        if not all(value.strip() for value in values):
            raise ValueError("quality scenario requires all six parts and a name")


@dataclass(frozen=True)
class Assumption:
    statement: str
    owner: str
    evidence: str
    validation: str
    consequence_if_false: str

    def validate(self) -> None:
        if not all(value.strip() for value in self.__dict__.values()):
            raise ValueError("assumption needs owner, evidence, validation, and consequence")


@dataclass(frozen=True)
class SystemModel:
    problem: str
    actors: tuple[str, ...]
    critical_journeys: tuple[str, ...]
    data_domains: tuple[str, ...]
    invariants: tuple[str, ...]
    workload_source: str
    success_measures: tuple[str, ...]
    non_goals: tuple[str, ...]
    quality_scenarios: tuple[QualityScenario, ...]
    assumptions: tuple[Assumption, ...]

    def validate(self) -> None:
        if len(self.problem.strip()) < 40:
            raise ValueError("problem statement is not sufficiently bounded")
        required_collections = {
            "actors": self.actors,
            "critical journeys": self.critical_journeys,
            "data domains": self.data_domains,
            "invariants": self.invariants,
            "success measures": self.success_measures,
            "non-goals": self.non_goals,
            "quality scenarios": self.quality_scenarios,
        }
        for name, values in required_collections.items():
            if not values:
                raise ValueError(f"system model requires {name}")
        if not self.workload_source.strip():
            raise ValueError("workload numbers require provenance")
        for scenario in self.quality_scenarios:
            scenario.validate()
        for assumption in self.assumptions:
            assumption.validate()
```

Executable tests demonstrate the boundary:

```python
import unittest

from system_model import Assumption, QualityScenario, SystemModel


def valid_model() -> SystemModel:
    scenario = QualityScenario(
        "peak task reads", "authenticated members", "read tasks",
        "weekday peak at 2,000 requests/second", "task-read path",
        "authorize and return committed state", "99% within 300 ms",
    )
    assumption = Assumption(
        "99% of projects have fewer than 200 active members",
        "product analytics", "60-day sample", "analyze enterprise cohort",
        "introduce batched fan-out for large projects",
    )
    return SystemModel(
        "Distributed teams need authorized task collaboration with bounded propagation.",
        ("member", "project administrator", "automation client"),
        ("create task", "assign task", "recover project"),
        ("projects", "tasks", "audit events"),
        ("a task belongs to exactly one project",),
        "measured production sample ending 2026-10-01",
        ("accepted task changes are visible within two seconds",),
        ("character-level document editing",),
        (scenario,), (assumption,),
    )


class SystemModelTests(unittest.TestCase):
    def test_complete_model_is_accepted(self) -> None:
        valid_model().validate()

    def test_vague_problem_is_rejected(self) -> None:
        model = valid_model()
        fields = {**model.__dict__, "problem": "Build task software"}
        with self.assertRaisesRegex(ValueError, "bounded"):
            SystemModel(**fields).validate()

    def test_missing_journeys_are_rejected(self) -> None:
        model = valid_model()
        fields = {**model.__dict__, "critical_journeys": ()}
        with self.assertRaisesRegex(ValueError, "critical journeys"):
            SystemModel(**fields).validate()

    def test_unmeasured_quality_is_rejected(self) -> None:
        model = valid_model()
        bad = QualityScenario("availability", "users", "request", "peak",
                              "API", "respond", "")
        fields = {**model.__dict__, "quality_scenarios": (bad,)}
        with self.assertRaisesRegex(ValueError, "six parts"):
            SystemModel(**fields).validate()

    def test_workload_without_source_is_rejected(self) -> None:
        model = valid_model()
        fields = {**model.__dict__, "workload_source": ""}
        with self.assertRaisesRegex(ValueError, "provenance"):
            SystemModel(**fields).validate()

    def test_unowned_assumption_is_rejected(self) -> None:
        model = valid_model()
        bad = Assumption("Traffic doubles yearly", "", "forecast", "measure", "replan")
        fields = {**model.__dict__, "assumptions": (bad,)}
        with self.assertRaisesRegex(ValueError, "owner"):
            SystemModel(**fields).validate()

    def test_missing_non_goals_are_rejected(self) -> None:
        model = valid_model()
        fields = {**model.__dict__, "non_goals": ()}
        with self.assertRaisesRegex(ValueError, "non-goals"):
            SystemModel(**fields).validate()


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

Save the blocks as `system_model.py` and `test_system_model.py`, then run:

```bash
python -m unittest -v test_system_model.py
```

A production design repository should connect requirement identifiers to evidence, decisions, tests, telemetry, risk owners, and review dates. A Boolean field should not replace stakeholder agreement or measurement.

## 26. Review the requirements model

```text
problem, affected users, current pain, desired outcome, and boundary:
stakeholders, actors, authority, incentives, and support responsibilities:
critical journeys, preconditions, normal result, errors, and recovery:
functional effects, invalid inputs, duplicates, conflicts, and idempotency:
quality scenario source, stimulus, environment, artifact, response, measure:
user-centered success indicators, thresholds, windows, and exclusions:
operation rates, concurrency, sizes, fan-out, skew, bursts, and growth:
data meaning, authority, identity, invariants, sensitivity, and lifecycle:
primary, derived, cached, exported, backed-up, and audit copies:
context, dependencies, contracts, quotas, failures, and degraded behavior:
trust boundaries, principals, authorization, abuse cases, and evidence:
privacy, residency, retention, erasure, legal hold, and qualified review:
availability, durability, freshness, RPO, RTO, and failure environments:
launch, planning, and contingency horizons with invalidation triggers:
budget, unit economics, team skill, on-call, delivery, and vendor limits:
facts, constraints, assumptions, unknowns, owners, and validation dates:
priorities, conflicts, accepted tradeoffs, scope, and explicit non-goals:
risks, experiments, thresholds, decisions informed, and review date:
```

## Common Misconceptions

- “The product request is the requirement.” A request must be decomposed into actors, effects, measures, and constraints.
- “Nonfunctional requirements are secondary.” Quality requirements often determine the architecture more than the feature list.
- “Scalable means we can add servers.” Scale must name workload, distribution, horizon, and bottleneck.
- “Five nines is clearer than a failure model.” A percentage without operation, denominator, window, and dependencies is ambiguous.
- “Averages describe capacity.” Bursts, tails, concurrency, skew, and amplification drive failure.
- “Compliance requires a particular database.” Obligations first become data, access, evidence, retention, and operational behavior.
- “An estimate must be exact to be useful.” Ranges and sensitivity can eliminate unsuitable designs early.
- “Assumptions are harmless until disproved.” High-impact assumptions are architectural risks that need owners and experiments.
- “Everything important should be a must.” Unprioritized absolutes hide real tradeoffs.
- “The diagram is the system model.” A diagram without semantics, measures, failure, and uncertainty is incomplete.

## Core Computer Science Concept

This chapter applies **abstraction, state-machine modeling, invariants, dimensional analysis, queueing intuition, probability distributions, and empirical falsification**. A system model deliberately omits detail while preserving properties relevant to a decision. Its quality is judged not by realism alone, but by whether observations can falsify its assumptions and whether its invariants constrain valid designs.

## Engineering Connections

- Actors and authority extend Chapters 20, 60, 87, and 92's identity boundaries.
- Workload distributions apply Chapters 43, 51, 76, 86, and 100's capacity reasoning.
- Data identity and invariants build on Chapters 15, 41, 69, 74, and 99.
- Failure environments connect Chapters 48, 54, 61, 88, and 91.
- Success measures prepare Chapter 121's SLIs, SLOs, and alerts.
- The model becomes input to Chapter 107's interface contracts and Chapter 117's complete review.

## From the Field

A team hears “updates must be real-time” and adds a streaming platform, WebSockets, and a distributed cache. User interviews later reveal that project boards are checked a few times per hour and two-second propagation is acceptable; the actual hard requirement is that concurrent edits never silently overwrite an assignment. The early adjective optimized the wrong quality. A measured journey and concurrency invariant would have focused the design on correct change handling before delivery machinery.

## Engineering Review

### What problem does this solve?

It converts ambiguous product intent into a bounded, measurable model that later architecture options can be tested against.

### Why was it designed this way?

Architecture is shaped by interactions among workload, data, quality, failure, authority, cost, and organizational ownership. Treating each as explicit evidence exposes conflicts and uncertainty before components make them expensive.

### When should I use it?

Use it for new systems, substantial features, migrations, reliability changes, vendor selection, and any proposal whose consequences cross one component or team.

### When should I avoid it?

Do not create a large requirements packet for a tiny reversible change with obvious local effects. Still state the user outcome, constraints, risk, and verification at a scale proportional to consequence.

### How does this make me a better engineer?

It teaches you to ask measurable questions, separate facts from assumptions, model state and failure before products, and make uncertainty actionable.

### How does this reduce waste?

It prevents premature services, invented scale, unused features, unowned data copies, impossible SLOs, hidden compliance work, capacity surprises, and prototypes that cannot inform a decision.

## Handbook Principle #106

> Design begins when ambiguous intent becomes a falsifiable model of actors, state, workload, quality, constraints, and uncertainty—not when the first component is chosen.

## Practical Observation

Take one proposed feature and remove every technology name. Can the remaining statement identify the actor, authorized operation, state change, critical data, workload environment, success measure, failure behavior, and assumption most likely to invalidate the design? If not, component debate is premature.

## Looking Ahead

The system model defines observable behavior and constraints. Chapter 107 turns that behavior into explicit interfaces and contracts that can evolve without forcing every producer and consumer to change at once.

## References

- [Software Engineering Institute — Deriving Architectural Tactics: A Step Toward Methodical Architectural Design](https://www.sei.cmu.edu/documents/704/2003_005_001_14213.pdf)
- [Software Engineering Institute — Robustness Scenarios](https://resources.sei.cmu.edu/asset_files/TechnicalReport/2022_005_001_875746.pdf)
- [Software Engineering Institute — Scenario-Based Analysis of Software Architecture](https://insights.sei.cmu.edu/library/scenario-based-analysis-of-software-architecture/)
- [Software Engineering Institute — Architecture Tradeoff Analysis Method collection](https://www.sei.cmu.edu/library/architecture-tradeoff-analysis-method-collection/)
- [Google SRE Workbook — Implementing SLOs](https://sre.google/workbook/implementing-slos/)
- [Google SRE Workbook — Example SLO document](https://sre.google/workbook/slo-document/)
- [NIST NCCoE — Secure software requirements and risk modeling](https://pages.nist.gov/nccoe-devsecops/example-implementation-1-2/appendix-c.html)
- [IETF BCP 14 — Key words for use in RFCs](https://www.rfc-editor.org/rfc/rfc2119.html)
- [Chapter 105 — Infrastructure as Code and a Complete AWS Delivery Lifecycle](../aws/105-infrastructure-as-code-and-a-complete-aws-delivery-lifecycle.md)
