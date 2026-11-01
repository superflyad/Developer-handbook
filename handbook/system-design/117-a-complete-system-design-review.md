# Chapter 117 — A Complete System Design Review

A system design review is not a performance in which one engineer presents a finished diagram and senior people approve it. It is a structured attempt to find unsupported assumptions while change is still affordable. The proposal connects user outcomes to interfaces, data, scale, failure behavior, security, operations, cost, and an evidence plan.

This chapter reviews a realistic multi-tenant task platform called **Atlas Tasks**. The design is intentionally incomplete: its purpose is to demonstrate how a team makes uncertainty visible, compares alternatives, and chooses the next validation experiment. It is not a universal reference architecture or a production implementation.

## 1. Begin with a decision brief

A reviewer should understand the decision before studying components.

**Decision requested:** Approve the first production architecture and staged delivery plan for a hosted task-collaboration service.

**Business outcome:** Teams can create, assign, discuss, and track work without losing changes or exposing one organization's data to another.

**Launch scope:** Web and API clients, 10,000 tenant organizations, task and membership management, comments, attachments, search, notifications, audit export, and tenant deletion.

**Explicitly outside launch scope:** Offline-first synchronization, arbitrary workflow automation, customer-managed encryption keys, active-active regional writes, and a public extension marketplace.

**Decision deadline:** Four weeks, because schema and public API implementation begin afterward.

**Owners:** Product owns journeys and adoption; application owns APIs and workflows; data owns storage and restore; security owns identity-control review; platform owns deployment and runtime; the engineering lead owns the integrated decision.

This boundary prevents the review from solving every future product at once.

## 2. State measurable requirements

Functional requirements describe behavior:

1. Members create, read, update, assign, and comment on tasks within authorized tenants.
2. Concurrent edits never silently overwrite one another.
3. Attachments are uploaded and downloaded without passing large bodies through the API service.
4. Search reflects accepted task changes within 60 seconds.
5. Notification delivery may be delayed but cannot block task creation.
6. Tenant administrators export audit events and request tenant deletion.

Quality requirements define useful boundaries:

| Attribute | Launch target |
| --- | --- |
| API availability | 99.9% monthly for task read and write journeys |
| Latency | p95 under 300 ms for reads and 500 ms for writes at expected load |
| Consistency | Read-your-write for authoritative task API; search lag under 60 seconds |
| Durability | RPO at most 5 minutes for task metadata; zero accepted-loss target for audit events |
| Recovery | RTO within 4 hours for regional data-plane loss |
| Isolation | No cross-tenant data access, including cache, queue, search, export, and restore paths |
| Retention | Deleted tenant primary data removed within 30 days; backup expiry documented separately |
| Cost | Normal launch workload within the approved monthly envelope, with per-tenant visibility |

“Fast,” “secure,” and “highly available” would not support a design decision or test.

## 3. Identify actors, journeys, and invariants

Actors include tenant member, tenant administrator, support engineer, application service, background worker, identity provider, object store, notification provider, and platform operator.

The critical journey is **update task**:

1. A member authenticates and selects a tenant.
2. The client reads task version 41.
3. The member changes the assignee and submits version 41.
4. The service authorizes the action against current membership.
5. Storage updates only if version 41 remains current, producing version 42.
6. The transaction records an outbox event.
7. The response returns the committed representation.
8. Workers later update search and send notifications.

Core invariants:

- every tenant-owned object has one immutable tenant identity;
- only currently authorized subjects can act on it;
- a task update either commits with its audit/outbox record or does not commit;
- an update based on a stale version never silently overwrites a newer one;
- asynchronous side effects do not redefine authoritative task state;
- deletion and restore preserve tenant scope;
- retries cannot duplicate externally visible effects.

Invariants are stronger design inputs than component names.

## 4. Build a workload model

Launch planning assumptions:

- 10,000 tenants, 100 active users per tenant at the 95th percentile;
- 100 million tasks and 600 million comments after two years;
- 20 million API requests per day;
- read-to-write ratio of 8:1;
- average request rate about 231 requests per second;
- peak factor of 10, producing about 2,300 requests per second;
- roughly 260 peak writes per second before retry and growth headroom;
- 2 KB average task metadata and 1 KB average comment metadata;
- 20 TB of attachments after two years, with a long-tailed size distribution;
- notification and search events at approximately the accepted write rate.

These are not capacity promises. They are assumptions with owners and validation dates. The design uses a 3x short-term headroom factor for traffic bursts, backfills, and uneven tenant activity, then relies on measurements rather than permanent overprovisioning.

The distribution matters more than the mean. One large tenant import can dominate writes; a viral notification can dominate reads; attachments dominate bytes while metadata dominates operations.

## 5. Draw the system context

```text
                         +-------------------+
                         | Identity provider |
                         +---------+---------+
                                   |
 +-------------+       HTTPS       v       HTTPS       +------------------+
 | Web/API     +----------------> Atlas Tasks --------->+ Notification     |
 | clients     |                 platform               | provider         |
 +------+------+                    |                   +------------------+
        |                           |
        | direct signed upload      | export and lifecycle
        v                           v
 +-------------+              +-------------+
 | Object      |              | Tenant      |
 | storage     |              | administrators|
 +-------------+              +-------------+
```

The context diagram shows people and external systems, not internal deployment detail. Trust boundaries exist at every external connection. The identity provider authenticates subjects; Atlas still authorizes tenant, resource, and action. The notification provider receives only required delivery data and has a kill switch.

## 6. Choose deployable boundaries

The launch design favors a modular application service plus independently scalable workers:

```text
                         +-----------------------+
                         | Edge / load balancer  |
                         +-----------+-----------+
                                     |
                          +----------v----------+
                          | API application     |
                          | authz, tasks, audit |
                          +---+----------+------+ 
                              |          |
                  transaction |          | signed URL
                              v          v
                     +--------+---+  +---+----------+
                     | Relational |  | Object store |
                     | database   |  +--------------+
                     +-----+------+
                           | outbox relay
                           v
                     +-----+------+      +----------------+
                     | Message    +----->+ Search workers |
                     | broker     +----->+ Notify workers |
                     +-----+------+      +----------------+
                           |
                           v
                     +-----+------+
                     | Search     |
                     | index      |
                     +------------+
```

Why not launch with many domain microservices? The early product needs transactions across task, membership reference, audit, and outbox state; one team owns the domain; and independent deployment does not yet outweigh distributed coordination and operational cost. Modules enforce boundaries inside the application. Search, attachments, and notifications already have different scaling or failure behavior, so their infrastructure is separate.

The design does not claim “monolith forever.” Stable interfaces and outbox events create extraction seams if ownership or scaling later diverges.

## 7. Define the public contract

An update request is conditional and idempotent:

```http
PATCH /v1/tenants/t-7/tasks/task-42 HTTP/1.1
Authorization: Bearer <session>
If-Match: "41"
Idempotency-Key: 01JBN5M4C6Q8...
Content-Type: application/merge-patch+json

{
  "assignee_id": "user-19"
}
```

Possible outcomes:

- `200 OK` with version 42 when committed;
- `412 Precondition Failed` when version 41 is stale;
- `403 Forbidden` when the subject lacks the action;
- `404 Not Found` when the resource is unavailable to the scoped caller;
- `429 Too Many Requests` with bounded retry guidance under admission control;
- a stable problem document for machine-readable failure details.

The idempotency key is scoped to tenant, subject, operation, and request meaning. Reusing it with a different body is rejected. A timeout does not prove failure; the client can safely retrieve the prior result or repeat the same keyed request.

Pagination uses an opaque cursor tied to tenant and stable ordering. Public fields, error meanings, compatibility rules, rate limits, and deprecation policy are part of the contract.

## 8. Define the data model and ownership

The authoritative relational model includes:

```text
tenant(tenant_id, name, status, version)
membership(tenant_id, user_id, role, status, version)
task(tenant_id, task_id, project_id, title, status,
     assignee_id, version, created_at, updated_at)
comment(tenant_id, comment_id, task_id, body, version, created_at)
attachment(tenant_id, attachment_id, task_id, object_key,
           digest, scan_status, created_at)
audit_event(tenant_id, event_id, actor_id, action, resource_id,
            policy_version, occurred_at)
outbox(tenant_id, event_id, aggregate_id, aggregate_version,
       event_type, payload, published_at)
idempotency_record(tenant_id, subject_id, key, request_digest,
                   response_reference, expires_at)
```

Tenant identity participates in every tenant-owned key and relationship. The ordinary application role cannot bypass the data-layer tenant policy. Cross-tenant administration uses a separate, audited path and identity.

Attachments live in object storage because their access pattern, size, lifecycle, and serving path differ from metadata. The database stores ownership, expected digest, scan state, and object reference. Search is a derived projection, never the source of task truth.

## 9. Make consistency choices per journey

Task mutation uses a local transaction and optimistic concurrency:

1. Verify tenant context and authorization.
2. Update the task with `WHERE tenant_id = ? AND task_id = ? AND version = 41`.
3. Insert audit and outbox records in the same transaction.
4. Commit once.

If zero rows update, the service returns a conflict instead of overwriting. Readers of the authoritative API observe committed state. Search and notifications are eventually consistent.

The outbox relay may deliver an event more than once. Consumers deduplicate by event identity or apply monotonic aggregate versions. They do not assume broker delivery equals business uniqueness. Ordering is required only per task aggregate, not globally.

An alternative synchronous search update was rejected because search failure would make task creation unavailable and create a distributed transaction problem. Its consequence is visible search lag, measured against the 60-second requirement.

## 10. Partition for growth without premature distribution

The initial database scales vertically with read replicas used only for explicitly stale-tolerant queries. Tenant identity is included in primary and secondary access paths so future partition routing can use it.

Growth stages:

1. Tune queries, indexes, connection limits, and retention.
2. Move analytical and search workloads away from the primary.
3. Partition large history tables and archive expired data.
4. Route large tenants or tenant ranges into database cells when measured limits require it.

Tenant-based cells bound blast radius and make movement understandable, but a single very large tenant may need further partitioning. The design avoids a global sequence and cross-tenant transactions so those future splits remain possible.

Hot-key telemetry measures request, write, storage, queue, and connection use per tenant. Global averages cannot expose a noisy neighbor.

## 11. Design overload and dependency failure

Each interactive request carries a two-second end-to-end deadline. Internal timeouts leave time for serialization and response. Cancellation propagates when the client disconnects or deadline expires.

The API has separate concurrency pools for database work, identity checks, and object-signing calls. Queues are bounded. Admission control rejects low-priority or excessive work before pools saturate. Tenant and global limits protect fairness and the platform.

Retries occur only for transient, idempotent operations, at one owning layer, with exponential backoff, jitter, attempt limits, and a retry budget. Circuit breakers stop repeated calls to an unhealthy notification provider; notification work remains queued without blocking task writes.

Degraded modes are explicit:

- search unavailable: authoritative task reads and writes continue; search reports unavailable rather than stale completeness;
- notification provider unavailable: accepted notifications remain queued within retention and capacity bounds;
- object scanner unavailable: new attachments remain quarantined and cannot be downloaded;
- policy dependency unavailable: use a bounded, versioned cache only within its safe lifetime, then fail closed for writes;
- database unavailable: reject writes quickly; do not accept work that cannot meet durability semantics.

## 12. Place workloads across failure domains

API and worker instances run across at least three independent zones behind health-aware routing. Stateless instances can be replaced without losing accepted state. The relational database uses synchronous multi-zone durability within the primary region and tested backup or replicated recovery to a second region according to the stated RPO.

The message broker, object store, secret system, and key system use managed multi-zone configurations. Redundancy is checked for shared dependencies: three API zones do not help if all require one exhausted connection pool or one unavailable identity path.

The control plane and recovery credentials are protected from the same failure that affects the data plane. Regional failover is an operator-controlled process at launch, because automatic failover without tested data and dependency readiness could choose availability while violating consistency or tenant controls.

## 13. Specify recovery, not merely backups

For regional database loss:

1. Declare and communicate the recovery event.
2. Stop or fence writers to avoid two primaries.
3. Establish the newest verified recovery point within the five-minute RPO.
4. Restore or promote data and verify schema, keys, tenant policy, and audit continuity.
5. Reconfigure dependent workers and routing.
6. Run read-only integrity probes before opening writes.
7. Increase traffic gradually while bounding replay and cache-warm load.
8. Reconcile outbox, search, notifications, and idempotency records.
9. Verify business journeys and record actual recovery measures.

Quarterly exercises use representative data volume and a defined stop condition. A restore that completes in a test account but cannot reattach keys, secrets, DNS, queues, or consumers does not meet the RTO.

Tenant-scoped recovery is a separate workflow: reconstruct into an isolated location, filter and verify tenant ownership, compare counts and digests, authorize import, and never restore a shared snapshot directly over live shared data.

## 14. Threat-model the design

High-consequence threats include:

| Threat | Boundary and consequence | Primary controls | Evidence |
| --- | --- | --- | --- |
| Task ID substitution | Public API exposes another tenant's task | Verified tenant context, resource authorization, scoped query | Cross-tenant negative tests |
| Stale membership cache | Removed user retains access | Short safe cache, invalidation event, policy version | Revocation-latency test |
| Cache key omits tenant | Derived response leaks data | Tenant in key, auth before reuse | Collision and property tests |
| Forged queue message | Worker writes into chosen tenant | Authenticated producer, consumer authorization, scoped service identity | Rejected-message integration test |
| Support impersonation abuse | Privileged path reads customer data | Separate role, time-bound approval, visible state, audit | Quarterly access review and alert |
| Attachment malware | Download harms recipient | Quarantine, digest, scan state, content controls | Known-test-file and bypass tests |
| Tenant resource exhaustion | Shared capacity denied to others | Quotas, fair queues, concurrency limits | Noisy-neighbor load test |
| Overbroad export | Personal or business disclosure | Field allowlist, authorization, encrypted delivery, expiry | Export fixture and access tests |

Secrets are short-lived where possible and scoped by service and environment. Data is encrypted in transit and at rest with owned key rotation. Audit records avoid tokens and task bodies while preserving actor, tenant, action, resource, result, and policy version.

## 15. Define privacy and deletion behavior

Atlas collects account identity, membership, task content, comments, attachments, operational metadata, and necessary security events. Each category has a documented purpose and owner. Product analytics uses minimized events rather than arbitrary task content.

Tenant deletion creates a durable, idempotent workflow:

1. Reauthenticate and authorize the tenant administrator.
2. Enter a reversible waiting state and notify required owners.
3. Disable new tenant writes.
4. Delete or tombstone primary rows and objects.
5. remove search, cache, analytics, and queued representations;
6. request deletion from processors;
7. reconcile every registered store;
8. retain only authorized minimal evidence;
9. let protected backups expire, with restore-time tombstone replay.

The 30-day target applies to declared primary and derived stores. Backup retention is documented separately so the promise is not misleading. New data stores cannot launch without joining the data inventory and deletion workflow.

## 16. Design observability from user journeys

The primary service-level indicators are:

- successful authorized task reads and writes divided by valid attempts;
- latency distribution for those journeys;
- stale-version conflict rate, separated from server failures;
- search projection lag;
- notification queue age;
- tenant deletion age and reconciliation failures;
- denied cross-tenant attempts and authorization anomalies;
- recovery-point age and last successful recovery exercise.

Structured events carry request, trace, tenant, subject, operation, result, dependency, version, and deployment identifiers, with sensitive fields redacted. Metrics retain bounded tenant dimensions through controlled heavy-hitter or per-tenant accounting mechanisms rather than unbounded labels.

Traces follow API, database, outbox, broker, and consumer work through correlation identifiers. Alerts fire on user-impacting symptoms and exhaustion trends with owners and runbooks. A page for every single failed notification would be noise; sustained queue age threatening the delivery objective is actionable.

## 17. Estimate cost and ownership

The cost model includes more than instance count:

- API and worker compute at baseline, peak, and recovery load;
- database compute, storage, replicas, backups, I/O, and connections;
- object storage, requests, lifecycle transitions, and egress;
- broker throughput and retention;
- search nodes, replicas, and index growth;
- observability ingestion, retention, and query;
- identity, key, secret, and security services;
- cross-zone and cross-region transfer;
- engineering and on-call ownership.

Tagging or equivalent allocation records environment, component, and tenant class. Unit measures include cost per active tenant, per million API operations, per stored gigabyte, and per attachment gigabyte served.

The design reserves cost headroom for multi-zone resilience and recovery exercises. Removing redundancy may lower a bill while violating the approved availability and recovery requirements; optimization must preserve the outcome.

## 18. Compare major alternatives

### Modular application versus microservices

The modular application wins at launch because ownership is unified, transactional boundaries are close, throughput is modest, and operational maturity is limited. Microservices could improve independent ownership and scaling later but introduce network failure, contract evolution, distributed observability, and data ownership work now.

### Relational source of truth versus key-value storage

Relational storage fits conditional updates, relationships, audit/outbox atomicity, and team expertise. Key-value storage offers attractive horizontal scaling but would move more invariant and access-path work into the application before scale demands it.

### Outbox events versus synchronous side effects

Outbox events keep task availability independent of search and notification dependencies and preserve transaction-to-message continuity. They accept eventual consistency, duplicate delivery, queue operation, and consumer idempotency.

### Shared database versus database per tenant

Shared storage is efficient for launch and fleet operation. It increases cross-tenant consequence and complicates scoped restore. Tenant-aware keys, data policy, negative tests, exports, and future cell routing mitigate but do not erase those costs.

The review approves tradeoffs, not technology in isolation.

## 19. Record the load-bearing decisions

The initial ADR index contains:

- ADR-001: Launch as a modular application with separate asynchronous workers.
- ADR-002: Use a shared relational source of truth with tenant-scoped keys.
- ADR-003: Use optimistic concurrency and explicit task versions.
- ADR-004: Commit audit and outbox state in the mutation transaction.
- ADR-005: Treat search and notifications as rebuildable projections.
- ADR-006: Use direct signed attachment transfer with quarantine and scanning.
- ADR-007: Launch in one write region with multi-zone availability and tested regional recovery.
- ADR-008: Use tenant identity as the future cell-routing dimension.

Each record includes context, serious options, consequences, assumptions, fitness functions, owner, review trigger, and migration seam. For example, ADR-002 is reviewed when primary storage reaches 300 GB, p95 write latency exceeds its threshold for seven days, tenant restore misses four hours, or a contract requires dedicated storage.

## 20. Maintain a ranked risk register

| Risk or assumption | Consequence if wrong | Evidence or mitigation | Owner and trigger |
| --- | --- | --- | --- |
| Tenant-scoped restore meets four hours | Contract and recovery failure | Full-volume restore prototype | Data; before first enterprise contract |
| Shared database handles hot tenants | Cross-tenant latency and availability | Skewed load test and tenant quotas | Data; before beta |
| Identity revocation propagates in five minutes | Removed member retains access | Revocation experiment under outage | Security; before launch |
| Search indexing stays under 60 seconds | Users act on incomplete results | Burst and replay test | Search; before beta |
| Notification provider export and failover are adequate | Delivery outage and lock-in | Provider failure exercise, secondary path decision | Application; at volume threshold |
| Deletion inventory is complete | Retention promise fails | Reconciliation test for every registered store | Privacy owner; each new store |
| Regional recovery meets RPO/RTO | Extended outage or data loss | Game day at representative volume | Platform; quarterly |

Rank by consequence and uncertainty, not numerical precision alone. An untested tenant restore is a higher-priority experiment than polishing a low-risk deployment diagram.

## 21. Stage delivery and learning

### Stage 0 — Prove dangerous assumptions

- prototype optimistic updates and atomic outbox behavior;
- test tenant-scoped restore at projected two-year data volume;
- run skewed workload and connection-pool tests;
- verify identity revocation and queue authentication;
- price representative attachment, search, and observability volume.

### Stage 1 — Internal and design-partner release

- one region, multi-zone runtime;
- task, membership, attachment, and audit fundamentals;
- small controlled tenant set;
- synthetic journeys, security tests, and manual recovery exercise;
- feature flags for search and notifications.

### Stage 2 — Public launch

- verified SLOs, on-call ownership, runbooks, deletion, export, quotas, and cost allocation;
- capacity headroom demonstrated at peak model;
- threat mitigations and dependency failure modes tested;
- regional backup recovery demonstrated within objectives.

### Stage 3 — Evidence-driven evolution

- add tenant cells only when scale, isolation, or restore evidence justifies them;
- extract services only with clear ownership or scaling benefit;
- add regional write strategies only when product requirements justify their consistency cost;
- supersede ADRs and migrate by cohort with reconciliation.

Each stage has an exit criterion, not merely a date.

## 22. Conduct the review as a working session

Distribute the brief, requirements, diagrams, estimates, ADRs, and risk register before the meeting. Reviewers annotate questions asynchronously. The live session focuses on disputed assumptions and cross-domain effects.

Invite people who can challenge product journeys, application contracts, data semantics, security and privacy, operations, and cost. Use one shared model; do not let each specialty review a different architecture.

For every issue, classify the outcome:

- **approve:** evidence is sufficient;
- **approve with action:** risk is bounded and an owned action has a deadline;
- **experiment required:** evidence can resolve a consequential uncertainty;
- **decision required:** tradeoff needs an accountable owner;
- **block:** an invariant or launch requirement is knowingly unmet.

The output is not “review held.” It is an updated proposal, decision log, ranked risks, experiments, owners, and explicit approval boundary.

## 23. Ask questions that expose weak reasoning

Product and scope:

- Which user outcome fails if this component is removed?
- Which launch requirement caused each major piece of complexity?
- What is intentionally deferred?

Data and correctness:

- Where is each fact authoritative?
- Which concurrent histories are legal?
- What happens after an unknown write outcome?
- Can every derived view be rebuilt or reconciled?

Scale and failure:

- Which distribution or tenant becomes hot first?
- What is the first saturated resource?
- How many attempts can one user action create?
- Does recovery load reproduce the outage?

Security and privacy:

- How is tenant context established on every path?
- Which administrator can cross the boundary, and what evidence remains?
- Where do data copies outlive their purpose?
- Does degraded mode weaken authorization?

Evolution and ownership:

- Which assumption would reverse this decision?
- What is the migration seam and point of no return?
- Who is paged, who decides, and who pays?
- Which test proves the architecture still has its claimed property?

## 24. Encode review completeness

A checklist cannot prove a design is correct, but it can stop an incomplete proposal from masquerading as a complete one:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class DesignReview:
    decision_requested: str
    measurable_requirements: int
    critical_invariants: int
    workload_model: bool
    context_and_deployment_views: bool
    api_and_data_contracts: bool
    consistency_model: bool
    failure_and_recovery_model: bool
    threat_and_privacy_model: bool
    observability_and_cost_model: bool
    alternatives_compared: int
    decision_records: int
    ranked_risks: int
    staged_experiments: int
    owners_assigned: bool
    weakest_assumption: str

    def validate(self) -> None:
        if not self.decision_requested.strip():
            raise ValueError("review has no decision boundary")
        if self.measurable_requirements < 3 or self.critical_invariants < 3:
            raise ValueError("requirements or invariants are too vague")
        required_models = (
            self.workload_model,
            self.context_and_deployment_views,
            self.api_and_data_contracts,
            self.consistency_model,
            self.failure_and_recovery_model,
            self.threat_and_privacy_model,
            self.observability_and_cost_model,
        )
        if not all(required_models):
            raise ValueError("cross-functional design model is incomplete")
        if self.alternatives_compared < 2:
            raise ValueError("review does not expose meaningful tradeoffs")
        if self.decision_records < 1 or self.ranked_risks < 1:
            raise ValueError("decisions or residual risks are unrecorded")
        if self.staged_experiments < 1:
            raise ValueError("uncertainty has no validation experiment")
        if not self.owners_assigned:
            raise ValueError("actions and risks have no owners")
        if not self.weakest_assumption.strip():
            raise ValueError("review hides its weakest assumption")
```

The tests remove one dimension at a time:

```python
from dataclasses import replace
import unittest

from design_review import DesignReview


def complete_review() -> DesignReview:
    return DesignReview(
        decision_requested="Approve Atlas Tasks launch architecture and stages.",
        measurable_requirements=8,
        critical_invariants=7,
        workload_model=True,
        context_and_deployment_views=True,
        api_and_data_contracts=True,
        consistency_model=True,
        failure_and_recovery_model=True,
        threat_and_privacy_model=True,
        observability_and_cost_model=True,
        alternatives_compared=4,
        decision_records=8,
        ranked_risks=7,
        staged_experiments=5,
        owners_assigned=True,
        weakest_assumption="tenant restore meets four hours at two-year volume",
    )


class DesignReviewTests(unittest.TestCase):
    def test_complete_review_is_accepted(self):
        complete_review().validate()

    def test_missing_decision_boundary_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "decision boundary"):
            replace(complete_review(), decision_requested="").validate()

    def test_vague_requirements_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "too vague"):
            replace(complete_review(), measurable_requirements=2).validate()

    def test_missing_workload_model_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "incomplete"):
            replace(complete_review(), workload_model=False).validate()

    def test_missing_recovery_model_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "incomplete"):
            replace(complete_review(), failure_and_recovery_model=False).validate()

    def test_missing_privacy_model_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "incomplete"):
            replace(complete_review(), threat_and_privacy_model=False).validate()

    def test_single_option_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "tradeoffs"):
            replace(complete_review(), alternatives_compared=1).validate()

    def test_unrecorded_risk_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "residual risks"):
            replace(complete_review(), ranked_risks=0).validate()

    def test_uncertainty_without_experiment_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "validation experiment"):
            replace(complete_review(), staged_experiments=0).validate()

    def test_hidden_weakness_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "weakest assumption"):
            replace(complete_review(), weakest_assumption="").validate()


if __name__ == "__main__":
    unittest.main()
```

Passing means the proposal is reviewable. The actual approval still depends on whether its evidence, tradeoffs, and risks are acceptable.

## 25. Decide the Atlas proposal

The review outcome is **experiment required before launch approval**, with conditional approval of the broad architecture.

The shared relational source of truth, modular application boundary, optimistic concurrency, outbox workflow, derived search, direct attachment transfer, and multi-zone deployment fit the stated launch requirements. They preserve clear future seams without paying distributed-system cost prematurely.

The weakest assumption is tenant-scoped restoration within four hours at projected two-year data volume. It affects the storage choice, multi-tenant model, contractual recovery claim, and operational procedure. The next experiment must:

- generate representative task, comment, audit, and object metadata volume;
- restore one tenant from shared protected backups into isolation;
- apply subsequent changes without crossing tenant boundaries;
- verify row counts, ownership, versions, audit continuity, and deletion tombstones;
- measure operator time, compute, I/O, and recovery load;
- produce an ADR update or alternative if the four-hour target fails.

This is a better outcome than approving a polished diagram whose most consequential recovery claim remains untested.

## 26. Review a complete system design

Before concluding a review, ask:

### Purpose and model

- Is the requested decision, scope, deadline, owner, and business outcome clear?
- Are journeys, measurable quality requirements, invariants, and workload distributions explicit?
- Do context, deployment, sequence, data, and trust views answer distinct questions?

### Correctness and scale

- Are API, data, consistency, concurrency, messaging, caching, and partition choices connected?
- Are estimates dimensional, assumptions owned, and hot distributions considered?
- Are alternatives compared against the same forces?

### Failure and protection

- Are deadlines, overload, dependency failure, redundancy, RPO, RTO, and recovery load designed?
- Do identity, authorization, tenant scope, privacy, deletion, administration, and recovery preserve boundaries?
- Are degraded modes explicit and safe?

### Operation and evolution

- Do SLIs, alerts, traces, cost units, runbooks, and ownership follow user journeys?
- Are decisions, residual risks, review triggers, migration seams, and deprecation paths recorded?
- Is the weakest assumption paired with the next bounded experiment?

## Common Misconceptions

- **“A design review chooses technologies.”** It evaluates whether decisions satisfy outcomes, constraints, and risks.
- **“More boxes mean more complete architecture.”** Completeness comes from connected behavior, data, failure, security, operation, and evidence.
- **“The review should eliminate uncertainty.”** It should expose and rank uncertainty, then choose efficient experiments.
- **“A reference architecture is universally correct.”** Context, workload, team, and constraints determine tradeoffs.
- **“Approval means the design will not change.”** Approval establishes a current decision and an evidence-driven evolution path.
- **“Operations can be added before launch.”** Recovery, observability, deployment, ownership, and cost shape the architecture itself.
- **“Every risk blocks delivery.”** Risks can be mitigated, accepted by the right owner, staged, or tested; hidden risks are the danger.

## Core Computer Science Concept

This chapter integrates **abstraction, contracts, data modeling, asymptotic and dimensional estimation, concurrency control, distributed state, fault containment, access control, feedback systems, and decision theory**. System design is the disciplined composition of these ideas under real constraints.

## Engineering Connections

- Chapters 106–108 establish requirements, interfaces, data identity, and storage.
- Chapters 109–113 cover capacity, partitioning, consistency, caching, messaging, coordination, and time.
- Chapters 114–115 bound failure and preserve security, privacy, and tenant isolation.
- Chapter 116 preserves decisions and makes evolution testable.
- Part X will deepen debugging, telemetry, performance, recovery, and incident evidence needed to operate this proposal.

## From the Field

A review spends ninety minutes debating whether search should use one engine or another. No one notices that the stated four-hour tenant restore has never been attempted and the shared backup contains every customer. The selected search engine performs well; the first enterprise recovery takes two days and requires unsafe manual filtering. Review quality is determined by the consequential assumption it exposes, not the technology detail it exhausts.

## Engineering Review

### What problem does this solve?

It creates one reviewable model that connects product outcomes with technical behavior, failure, protection, operation, cost, ownership, and change.

### Why was it designed this way?

Cross-functional evidence prevents local optimizations from violating another domain's invariants and turns unresolved uncertainty into owned experiments.

### When should I use it?

Use it before major implementation commitments, risky migrations, significant scale changes, new trust boundaries, and launch-readiness decisions.

### When should I avoid it?

Do not require the full ceremony for small reversible changes; scale the depth to consequence while preserving explicit reasoning.

### How does this make me a better engineer?

You learn to move from requirements to estimates and contracts, challenge assumptions across disciplines, and defend decisions with evidence rather than familiarity.

### How does this reduce waste?

It finds expensive mismatches before implementation, directs prototypes toward the highest-risk unknowns, prevents duplicate specialist models, and stages complexity only when evidence justifies it.

## Handbook Principle #117

> A complete design is not the one with the most components; it is the one that connects outcomes, invariants, estimates, contracts, failure, protection, operation, cost, ownership, alternatives, and the next experiment in one falsifiable model.

## Practical Observation

Read a design proposal and underline every adjective: scalable, secure, resilient, real-time, simple, cheap, reliable. For each, find its measure, boundary, owner, failure consequence, and test. Any adjective without those is an assumption wearing the shape of a requirement.

## Looking Ahead

Part X begins with debugging as hypothesis testing. The same discipline used here—state a claim, predict evidence, run a bounded experiment, and revise the model—will guide investigation from logs and metrics through profiles, incidents, and post-incident learning.

## References

- [AWS — Well-Architected Framework](https://docs.aws.amazon.com/wellarchitected/latest/framework/)
- [AWS Well-Architected — Preparing for a framework review](https://docs.aws.amazon.com/wellarchitected/latest/userguide/preparing-for-a-wafr.html)
- [Google Cloud — Well-Architected Framework](https://docs.cloud.google.com/architecture/framework)
- [C4 Model — Visualising software architecture](https://c4model.com/)
- [Google SRE Book — Service Best Practices](https://sre.google/sre-book/service-best-practices/)
- [Google SRE Workbook — Non-Abstract Large System Design](https://sre.google/workbook/non-abstract-design/)
- [Chapter 106 — From Requirements to a System Model](106-from-requirements-to-a-system-model.md)
- [Chapter 116 — Architecture Decisions, Tradeoffs, and Evolution](116-architecture-decisions-tradeoffs-and-evolution.md)
