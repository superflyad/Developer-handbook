# Chapter 129 — A Complete Cross-Layer Engineering Investigation

This chapter completes the first-edition curriculum by applying its methods to one failure. The goal is not to demonstrate every command. It is to show how an engineer moves from a user symptom to a defensible cross-layer explanation while controlling changes, preserving security boundaries, restoring service, and verifying the design revision.

The scenario is synthetic but realistic. Atlas Task Service deploys a new search implementation. Search latency and errors rise for large tenants, scaling does not help, and one response appears to contain a project name from another tenant. The investigation must treat availability and authorization as simultaneous concerns. It cannot assume the deployment is the entire cause, blame “the database,” or optimize away a security check.

All identifiers, tenants, traces, and measurements in this lab are invented. Run experiments only in an isolated disposable environment with synthetic data. The chapter does not authorize live production intervention.

## 1. State the incident and safety boundary

The initial incident record says:

```text
incident: INC-2047
declared: 2026-11-01T14:12:00Z
impact: search p99 above 8 s; 17% HTTP 504 for large EU tenants
security concern: one error detail named project "northstar" for the wrong tenant
healthy: task create/update and US traffic
candidate: api@sha256:d91, rollout at 40%
objective: stop possible cross-tenant disclosure and restore search below 500 ms p99
constraints: preserve accepted writes and security evidence; one controlled change at a time
```

The team immediately activates the security boundary because the wrong-tenant report is credible enough to investigate. It restricts sensitive evidence, retains affected response and audit identifiers, names a security lead, freezes unrelated change, and avoids broad cache clearing or process destruction until evidence requirements are understood.

The service objective is not “make the graph green.” It is:

- no cross-tenant search result, metadata, or authorization decision;
- deny protected work when authorization is unavailable or ambiguous;
- successful search below 500 ms p99 and below 0.5% errors;
- no unbounded queue or retry amplification;
- known artifact, configuration, data, and policy revision;
- recovery sustained with required capacity and redundancy.

## 2. Draw the request path before choosing a cause

The affected journey crosses several boundaries:

```text
browser
  -> DNS and TLS
  -> cloud load balancer
  -> Atlas API container
       -> task database
       -> policy service container
            -> policy database
       -> decision cache
  -> response
```

The cloud platform schedules containers and scales API replicas. Each API replica has CPU and memory limits plus a database and HTTP connection pool. Trace context should cross the API-to-policy call. Task and project identifiers are tenant-scoped; the same project ID may exist in two tenants. Policy decisions depend on tenant, subject, action, resource, and policy revision.

Write the invariants at the boundary:

```text
result.tenant_id == authenticated_tenant_id
authorization key includes every input that can change the decision
missing or stale required policy input never becomes allow
one user search produces bounded downstream work
retry and concurrency cannot exceed downstream safe capacity
```

These invariants prevent the performance investigation from “fixing” latency by bypassing policy checks or sharing an unsafe cache entry.

## 3. Create an evidence workspace

Use a case-specific, access-controlled workspace. Preserve originals and analyze copies:

```text
INC-2047/
  manifest.md
  timeline.csv
  impact/
  releases/
  traces/
  profiles/
  runtime/
  network/
  database/
  authorization/
  experiments/
  decisions/
```

The manifest records collector, source, UTC time range, command or query, artifact and environment identity, integrity reference where required, access classification, and any transformation. Never paste secrets, bearer tokens, raw customer content, or unrestricted production dumps into an ordinary issue.

Synchronize clocks or record their offsets. A trace timestamp, load-balancer access log, container event, and database sample cannot form a causal timeline when their time bases are unknown.

The evidence packet is append-only during active response. Correct the index with an annotation; do not silently replace inconvenient observations.

## 4. Quantify the user symptom

Start from the same SLI contract used for normal operation:

```text
eligible event: completed authenticated POST /tasks/search
success: correct tenant-scoped response before 2 s client deadline
latency: client-observed duration for successful eligible events
dimensions: region, route, tenant size class, artifact digest
```

The incident window shows:

| Signal | Baseline | Incident | Scope |
| --- | ---: | ---: | --- |
| search p50 | 82 ms | 410 ms | EU candidate and stable |
| search p99 | 310 ms | 8.4 s | large EU tenants |
| HTTP 504 | 0.08% | 17% | large EU tenants |
| task-write success | 99.97% | 99.96% | unchanged |
| cross-tenant report | 0 | 1 credible | candidate response detail |

The aggregate fleet p99 is only 720 ms because small tenants dominate request count. Per-tenant and per-artifact dimensions reveal the severe cohort. This explains why the rollout automation did not stop, but it does not yet explain the failure mechanism.

Preserve the affected response under restricted handling. Verify that the project name came from service output rather than browser state, an extension, or a support transcription.

## 5. Reproduce with synthetic tenant skew

Build an isolated environment from the same immutable candidate and stable digests. Use generated tenants:

- 9,900 small tenants with 20 projects each;
- 99 medium tenants with 2,000 projects each;
- one large tenant with 100,000 projects;
- repeated project IDs across tenants;
- policy allow, deny, missing, stale, and unavailable cases;
- production-shaped search result counts and concurrency.

Run a stable-versus-candidate matrix with the same runtime, schema, policy revision, and cache state. Use an open arrival model because requests continue arriving while search slows. Capture intended arrivals, generator queueing, completions, failures, and end-to-end latency so coordinated omission cannot hide the stall.

The candidate reproduces the large-tenant tail and wrong-tenant project name when two tenants share project ID `p-17`. The stable build does not. Repetition makes the failure a controlled starting point, not a production anecdote.

Keep the reproducer minimal enough to inspect but preserve the necessary tenant skew, duplicate ID, concurrency, and policy behavior. Removing those facts would remove the failure.

## 6. Maintain competing hypotheses

The team begins with multiple explanations:

| ID | Hypothesis | Prediction | Cheapest discriminating evidence | Status |
| --- | --- | --- | --- | --- |
| H1 | API CPU throttling causes queueing | candidate has high throttled time and on-CPU samples | cgroup counters plus CPU profile by digest | contradicted |
| H2 | memory leak creates long GC pauses | live retained set and pause time grow with requests | heap profile and soak trend | contradicted |
| H3 | network loss delays policy calls | retransmission aligns with long spans | connection, RTT, retransmission evidence | weak |
| H4 | search performs per-result policy calls | child-span count grows with result count | representative traces and code diff | supported |
| H5 | decision cache omits tenant context | same resource ID reuses another tenant's entry | cache-key code and two-tenant test | supported |
| H6 | policy database access path saturates | scans and pool wait rise with H4 fan-out | actual plan, waits, and buffers | supported |
| H7 | autoscaling will restore capacity | added replicas increase completions without downstream saturation | replicas, pool pressure, SLI | contradicted |

Every branch has an owner and time box. Contradicted hypotheses remain in the record. They are evidence that the team checked plausible layers rather than jumping from deployment time to source-code blame.

## 7. Establish source and release identity

Use Git to map the running digest to a reviewed source revision and pipeline record:

```powershell
git show --stat --oneline 4f8c2d1
git diff 4f8c2d1^ 4f8c2d1 -- src/search src/policy tests
git log --first-parent --decorate --since="2026-10-20" -- src/search
git blame -L 80,145 -- src/search/authorize.py
```

The release evidence says:

```text
source revision: 4f8c2d1
image digest: sha256:d91
SBOM and provenance subject: sha256:d91
deployment revision: atlas-api-eu-1842
schema revision: 42
policy revision: pol-771
feature flag: batched_search_authz=true for candidate cohort
```

Verify that the runtime reports the same digest and configuration. A tag such as `v7` is not enough; it can move. If the running artifact cannot be connected to source and delivery evidence, fix that uncertainty before making a line-level causal claim.

The diff shows candidate code changed one batch authorization call into an enrichment loop and introduced a local decision cache keyed only by `project_id`. History explains when and why, not whether the change caused observed harm.

## 8. Audit the delivery and configuration path

Review the pipeline rather than assuming the code diff is the only change:

- required checks ran on revision `4f8c2d1`;
- one image was built and promoted by digest;
- the deployment plan changed only candidate replicas and the feature flag;
- no schema migration or policy bundle changed in the incident window;
- secrets and service identity match the stable cohort;
- rollout analysis aggregated route latency across all tenant sizes;
- the load suite used unique project IDs and uniform 20-project tenants.

This identifies two prevention gaps: the test dataset removed tenant-key collision and skew, while the rollout gate hid the affected population. It also rules out rebuild drift and simultaneous schema or policy changes.

Do not infer safety from a green pipeline. Ask what the checks proved and which production conditions they omitted.

## 9. Check cloud routing and failure-domain scope

Cloud evidence shows the load balancer routed correctly by region and target health. TLS negotiation, DNS resolution, and edge connection time remain near baseline. The 504 occurs after the request reaches the API and exceeds the upstream response deadline.

Compare:

- request IDs across load balancer and application logs;
- target group, availability zone, artifact digest, and response time;
- healthy-host count and deregistration events;
- scaling decisions, desired versus ready capacity, and warm-up time;
- network and database quotas;
- stable and candidate traffic weights.

Impact spans all EU availability zones but only large-tenant searches. That weakens a zone-local network or host hypothesis. The cloud layer still matters: autoscaling adds API replicas, which increases simultaneous downstream connections and policy calls. It amplifies rather than creates the bottleneck.

Containment can therefore use routing: set candidate traffic to zero by immutable digest while leaving the stable cohort and other journeys available.

## 10. Inspect container and operating-system limits

For stable and candidate containers under the same workload, collect runtime identity and bounded resource evidence:

```text
image digest
command and environment fingerprint
CPU quota, usage, throttled periods, run queue
memory current, limit, events, working set, major faults
open descriptors and sockets
network bytes, connections, retransmission indicators
block I/O and pressure
restart, OOM, and readiness history
```

The candidate uses 1.4 of 2 CPU cores, has negligible throttling, stable memory, no OOM events, no descriptor growth, and low block I/O. API thread count rises because many requests wait on downstream calls. This contradicts CPU quota and memory leak as dominant mechanisms.

Do not conclude “resources are fine” from `docker stats` alone. Container summaries can hide host contention, throttling windows, page-cache behavior, and thread waits. Cross-check cgroup counters, scheduler or pressure evidence, and profiles over the incident window.

The negative result matters: adding CPU or memory will not remove a remote wait or unsafe cache key.

## 11. Profile CPU, memory, and waiting separately

An on-CPU profile shows JSON encoding and ordinary request work, but no function accounts for enough wall time to explain eight-second latency. An allocation profile is stable across repeated trials, and retained heap returns to baseline after load.

A wall-time or concurrency view tells a different story:

```text
search request
  6.8 s waiting for policy HTTP futures
  0.9 s waiting for database connection
  0.2 s task query and result mapping
  0.1 s CPU and serialization
```

There are hundreds of policy futures per large result set. The pool queue grows while CPU retains headroom. This supports H4 and redirects effort from local optimization to fan-out and downstream capacity.

Keep profile scope and sampling bias explicit. A CPU profile answers where CPU time ran; it does not directly show wall-clock waiting. A heap snapshot can perturb the process and may expose sensitive values, so capture it only in the disposable lab for this case.

## 12. Follow causal context across the network

Representative traces use the same trace context across API and policy boundaries. One large-tenant search contains:

```text
POST /tasks/search                         8.21 s
  task database query                     0.18 s
  authorize project p-1                  0.03 s
  authorize project p-2                  0.04 s
  ... 238 more policy client spans ...
  connection-pool wait                    5.92 s aggregate critical path
  response serialization                  0.07 s
```

Span count grows with result cardinality. Many calls reuse connections, so TLS and DNS are not repeated for every result. RTT is normal, and retransmission does not correlate with the long spans. Network evidence weakens H3 and reveals an application-level round-trip problem.

Check the client boundary too. The eight-second service trace plus load-balancer deadline explains the 504. Server work continues briefly after some clients abandon requests, consuming downstream capacity. Cancellation propagation is another design gap.

Trace IDs in structured logs connect timeout, retry, tenant-size class, artifact digest, and policy call count without placing raw tenant or token data in metric labels.

## 13. Diagnose policy service and database queues

The policy service completes more calls after the candidate rollout but reaches the same completion plateau. Pool acquisition time and database active sessions rise; API scale-out increases arrivals without increasing useful policy throughput.

Database evidence separates wait and execution:

```text
policy connection acquisition p99     1.9 s
query execution p99                    34 ms
rows estimated                         1
rows observed                          420 for hot tenant pattern
buffer reads                           elevated
lock wait                              not dominant
```

The actual plan on representative synthetic data shows an index on `project_id` but the query filters `(tenant_id, project_id, subject_id, action, revision)`. Tenant skew and repeated project IDs make the access path more expensive than the uniform test predicted.

The query still takes tens, not thousands, of milliseconds. The primary mechanism is hundreds of calls competing for a finite pool; the suboptimal access path amplifies it. One composite access-path improvement helps, but batching removes far more work.

Do not run an unbounded `EXPLAIN ANALYZE` on an expensive production statement during the incident. The lab uses sanitized representative data and records that the tool executes the query and adds overhead.

## 14. Prove the authorization failure independently

Performance evidence cannot establish a tenant-boundary violation. Build a two-tenant security test:

```text
tenant red:  project p-17, subject alice, action read -> allow
tenant blue: project p-17, subject bob,   action read -> deny
```

The candidate cache stores:

```python
decision_cache[project_id] = decision
```

After red warms `p-17`, blue reuses red's entry. The under-scoped key omits tenant, subject, action, and policy revision. Depending on request order, it can incorrectly allow, incorrectly deny, or attach the wrong project display metadata.

This is a causal reproduction of H5. Treat it as a security defect even if the observed production response exposed only a project name. Search logs and affected cache windows through the approved security process; do not speculate publicly about broader access until evidence establishes it.

The safe behavior is deny by default when required context is missing or the policy service is unavailable. Performance work must never translate an undefined authorization decision into allow.

## 15. Build the cross-layer causal account

The supported chain is:

```text
candidate source change
  -> per-result authorization loop
  -> downstream calls grow with search cardinality
  -> policy HTTP and database pools queue
  -> client deadlines expire; abandoned work briefly continues
  -> retries and API autoscaling add more arrivals
  -> policy throughput plateaus while latency and errors rise

under-scoped cache key
  -> decision reused across tenant, subject, action, and revision
  -> incorrect allow/deny or metadata possible for repeated project IDs

uniform test data + aggregate rollout gate + missing pool spans
  -> defects escape prevention and early detection
```

The deployment is the trigger. N+1 policy evaluation and incomplete cache identity are mechanisms. Tenant skew, database access path, retry behavior, cancellation gap, rollout aggregation, and test-data assumptions are contributing conditions.

CPU, memory, zone-local routing, TLS, and lock waits were plausible but not dominant. State these negative findings so future readers understand the boundaries of the conclusion.

## 16. Choose a reversible mitigation

The incident commander approves one change: route candidate digest `sha256:d91` to zero and restore the previously verified stable digest. This action:

- removes both the suspected disclosure and load mechanism;
- preserves task writes and the task database;
- has a known delivery and rollback path;
- changes one primary variable;
- can be verified by artifact, traffic, SLI, pool, and authorization evidence.

Before the change, the recorder captures traffic weights, cache state metadata, relevant restricted evidence, pool and query samples, and user SLIs. The security lead approves preservation and containment sequencing. The team does not merely flush the cache while leaving unsafe code live; that would erase useful state and allow immediate recurrence.

Success signals are zero candidate traffic, no new cross-tenant test failure, search below 500 ms p99, errors below 0.5%, and shrinking queues. Abort signals include task-write regression, reconciliation failure, or stable-capacity overload.

## 17. Verify recovery rather than declaring victory

Five minutes after rollback, error rate falls, but policy queue age remains elevated. The team stays in monitoring while retries and abandoned work drain.

Recovery evidence includes:

- running digest and traffic weights match the approved stable release;
- search SLI meets objective across tenant-size and region cohorts;
- policy arrival and completion rates converge;
- pool wait, active sessions, and queue age return to baseline;
- two-tenant authorization replay consistently denies blue;
- restricted log review finds no additional confirmed cross-tenant result;
- task writes and accepted search requests reconcile;
- desired redundancy and headroom return;
- temporary evidence access and diagnostic settings have owners.

The incident resolves only after a representative observation window. The candidate remains quarantined; nobody retags or silently rebuilds it.

## 18. Design the durable correction

The corrected design changes several boundaries:

1. the API sends one bounded batch authorization request per page, not one request per result;
2. the policy enforcement point passes verified tenant, subject, action, resource IDs, and required policy revision;
3. the decision cache key contains every security-relevant input;
4. missing, stale, ambiguous, or unavailable policy input fails closed;
5. result count and batch size are bounded;
6. connection concurrency and retries fit downstream safe capacity;
7. cancellation and deadlines propagate to downstream work;
8. the policy database has a representative composite access path;
9. traces expose batch size, pool acquisition, policy revision, and decision outcome using safe attributes;
10. rollout gates evaluate tenant-size cohorts and authorization invariants.

Do not treat the cache-key correction as sufficient. It repairs isolation but leaves the N+1 capacity mechanism. Do not treat batching as sufficient. It repairs work amplification but can still share an unsafe decision if identity remains incomplete.

## 19. Implement bounded tenant-scoped authorization

This simplified module models the corrected application boundary. Production code would also define expiry, invalidation, encrypted transport, authenticated service identity, policy freshness, audit handling, and persistent-cache behavior.

```python
from collections.abc import Iterable


class AuthorizationUnavailable(RuntimeError):
    pass


class PolicyBackend:
    def __init__(self, rules: dict[tuple[str, str, str, str, str], bool]):
        self.rules = rules
        self.available = True
        self.calls: list[tuple[str, ...]] = []

    def check_many(
        self,
        tenant_id: str,
        subject_id: str,
        action: str,
        project_ids: tuple[str, ...],
        policy_revision: str,
    ) -> dict[str, bool]:
        if not self.available:
            raise AuthorizationUnavailable("policy backend is unavailable")
        self.calls.append(project_ids)
        return {
            project_id: self.rules.get(
                (tenant_id, subject_id, action, project_id, policy_revision),
                False,
            )
            for project_id in project_ids
        }


class SearchAuthorizer:
    def __init__(
        self,
        backend: PolicyBackend,
        *,
        batch_size: int = 50,
        max_projects: int = 500,
    ):
        if batch_size <= 0 or max_projects <= 0 or batch_size > max_projects:
            raise ValueError("authorization bounds are invalid")
        self.backend = backend
        self.batch_size = batch_size
        self.max_projects = max_projects
        self.cache: dict[tuple[str, str, str, str, str], bool] = {}

    def authorize(
        self,
        tenant_id: str,
        subject_id: str,
        action: str,
        project_ids: Iterable[str],
        policy_revision: str,
    ) -> tuple[str, ...]:
        identity = (tenant_id, subject_id, action, policy_revision)
        if not all(value.strip() for value in identity):
            raise ValueError("authorization context is incomplete")

        unique_ids = tuple(dict.fromkeys(project_ids))
        if not unique_ids or any(not value.strip() for value in unique_ids):
            raise ValueError("project set is empty or invalid")
        if len(unique_ids) > self.max_projects:
            raise ValueError("project set exceeds the authorized bound")

        missing = tuple(
            project_id
            for project_id in unique_ids
            if (tenant_id, subject_id, action, project_id, policy_revision)
            not in self.cache
        )

        pending: dict[tuple[str, str, str, str, str], bool] = {}
        for start in range(0, len(missing), self.batch_size):
            batch = missing[start : start + self.batch_size]
            decisions = self.backend.check_many(
                tenant_id,
                subject_id,
                action,
                batch,
                policy_revision,
            )
            for project_id in batch:
                key = (tenant_id, subject_id, action, project_id, policy_revision)
                pending[key] = decisions.get(project_id, False)

        self.cache.update(pending)
        return tuple(
            project_id
            for project_id in unique_ids
            if self.cache[
                (tenant_id, subject_id, action, project_id, policy_revision)
            ]
        )
```

The backend defaults missing rules to deny. The authorizer updates its cache only after each successful batch response. If a backend call fails, the protected request fails instead of using a fabricated allow. A real implementation should decide whether earlier successful batches may enter the cache after a later failure and test that atomicity contract explicitly.

## 20. Test isolation, failure, and work bounds

```python
import unittest

from search_authorization import (
    AuthorizationUnavailable,
    PolicyBackend,
    SearchAuthorizer,
)


class SearchAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.backend = PolicyBackend({
            ("red", "alice", "read", "p-17", "r1"): True,
            ("blue", "bob", "read", "p-17", "r1"): False,
            ("red", "alice", "read", "p-18", "r1"): True,
            ("red", "alice", "write", "p-18", "r1"): False,
            ("red", "alice", "read", "p-18", "r2"): False,
        })
        self.authorizer = SearchAuthorizer(
            self.backend,
            batch_size=2,
            max_projects=5,
        )

    def test_same_project_id_is_isolated_by_tenant_and_subject(self):
        self.assertEqual(
            self.authorizer.authorize("red", "alice", "read", ["p-17"], "r1"),
            ("p-17",),
        )
        self.assertEqual(
            self.authorizer.authorize("blue", "bob", "read", ["p-17"], "r1"),
            (),
        )

    def test_action_is_part_of_the_decision_identity(self):
        self.assertEqual(
            self.authorizer.authorize("red", "alice", "read", ["p-18"], "r1"),
            ("p-18",),
        )
        self.assertEqual(
            self.authorizer.authorize("red", "alice", "write", ["p-18"], "r1"),
            (),
        )

    def test_policy_revision_is_part_of_the_decision_identity(self):
        self.assertEqual(
            self.authorizer.authorize("red", "alice", "read", ["p-18"], "r1"),
            ("p-18",),
        )
        self.assertEqual(
            self.authorizer.authorize("red", "alice", "read", ["p-18"], "r2"),
            (),
        )

    def test_missing_rule_denies_by_default(self):
        self.assertEqual(
            self.authorizer.authorize("red", "alice", "read", ["missing"], "r1"),
            (),
        )

    def test_duplicate_projects_are_checked_once(self):
        allowed = self.authorizer.authorize(
            "red", "alice", "read", ["p-17", "p-17", "p-18"], "r1"
        )
        self.assertEqual(allowed, ("p-17", "p-18"))
        self.assertEqual(self.backend.calls, [("p-17", "p-18")])

    def test_batch_size_bounds_downstream_work(self):
        projects = ["p-17", "p-18", "x-1", "x-2", "x-3"]
        self.authorizer.authorize("red", "alice", "read", projects, "r1")
        self.assertEqual([len(batch) for batch in self.backend.calls], [2, 2, 1])

    def test_cache_reuse_does_not_call_backend_again(self):
        self.authorizer.authorize("red", "alice", "read", ["p-17"], "r1")
        self.authorizer.authorize("red", "alice", "read", ["p-17"], "r1")
        self.assertEqual(len(self.backend.calls), 1)

    def test_unavailable_backend_does_not_become_allow(self):
        self.backend.available = False
        with self.assertRaisesRegex(AuthorizationUnavailable, "unavailable"):
            self.authorizer.authorize("red", "alice", "read", ["p-17"], "r1")

    def test_incomplete_context_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "context"):
            self.authorizer.authorize("", "alice", "read", ["p-17"], "r1")

    def test_oversized_request_is_rejected_before_backend_call(self):
        with self.assertRaisesRegex(ValueError, "bound"):
            self.authorizer.authorize(
                "red", "alice", "read", [f"p-{n}" for n in range(6)], "r1"
            )
        self.assertEqual(self.backend.calls, [])


if __name__ == "__main__":
    unittest.main()
```

These tests prove properties the original suite omitted: repeated resource IDs cannot cross tenant or subject boundaries; action and policy revision change cache identity; missing policy denies; backend loss does not permit; duplicate work collapses; and batch and request limits bound amplification.

## 21. Re-run the representative performance experiment

Build one candidate artifact from the corrected revision, attach provenance and test evidence, and deploy it only to the disposable environment. Repeat the original matrix with identical workload fingerprint, data, policy, cache phases, and resource limits.

| Result | Faulty candidate | Corrected candidate |
| --- | ---: | ---: |
| policy calls per 240-result search | 240 | 5 batches of at most 50 |
| search p99 at 900 arrivals/s | 8.4 s | 286 ms |
| error ratio | 17% | 0.18% |
| policy pool-wait p99 | 1.9 s | 21 ms |
| cross-tenant two-ID test | fails | passes |
| safe capacity with 30% headroom | below target | 1,350 arrivals/s |
| recovery after one policy replica loss | not bounded | 74 s |

Run warm, cold, peak, soak, and bounded policy-replica-loss phases. Verify cancellation, retries, queue drain, correctness, and cost. Do not compare a warmed corrected build with a cold faulty build.

The composite index improves per-batch query time, but the experiment separately proves that batching changes call count. This prevents assigning the full improvement to whichever change the reviewer prefers.

## 22. Deliver through controlled rollout

The production correction follows the ordinary trusted delivery path, not an incident side door:

1. merge reviewed code and tests;
2. build once and identify the artifact by digest;
3. attach dependency, SBOM, provenance, and scan evidence;
4. verify configuration and policy compatibility;
5. deploy to an isolated cohort containing synthetic collision probes and representative large tenants;
6. gate on tenant-size search SLI, policy batch count, pool wait, queue age, and authorization invariants;
7. expand gradually while preserving the stable digest;
8. stop automatically on correctness, isolation, latency, error, or capacity breach;
9. retain the same digest through promotion;
10. verify the effective runtime and policy decision at each stage.

Monitor downstream capacity while the API cohort grows. A locally healthy canary can still overload a shared policy or database tier when expanded.

## 23. Convert the incident into verified actions

The learning review creates a small outcome-based portfolio:

| Condition | Action | Verification |
| --- | --- | --- |
| uniform IDs hid cache collision | add repeated tenant-local IDs to authorization property tests | faulty key fails; corrected identity passes |
| small tenants hid fan-out | version a skewed workload corpus | CI and load lab reproduce call growth |
| aggregate gate hid affected cohort | gate rollout by tenant-size SLI and invariant probes | synthetic large-tenant failure stops canary |
| pool wait absent from traces | add acquisition spans and safe batch attributes | on-call locates dominant wait in replay |
| retry and autoscale amplified load | enforce retry budget and downstream admission limit | overload test plateaus safely without queue divergence |
| cancellation did not stop work | propagate deadline and cancel pending calls | abandoned-request test releases pool capacity |
| rollback access was fragile | provide reviewed secondary role and rehearsal | second on-call restores stable digest within objective |

Each action has a tracking ID, owner, priority, target date, verification owner, and evidence. A merged telemetry change remains implemented—not verified—until the replay demonstrates the intended diagnostic outcome.

Search prior incidents for the same N+1, cache identity, cohort aggregation, and downstream amplification patterns. Generalize only where the mechanism is shared.

## 24. Assemble the defensible evidence packet

The completed investigation contains:

- incident impact, severity, security boundary, roles, and decision timeline;
- immutable source, artifact, configuration, schema, and policy identities;
- stable-versus-candidate reproduction with workload fingerprint;
- hypothesis log including supporting, contradicting, and inconclusive evidence;
- cloud routing, container, cgroup, profile, network, trace, pool, query-plan, and authorization evidence;
- exact mitigation approval, change, before/after signals, and rollback path;
- recovery proof across SLI, correctness, queue, capacity, redundancy, and security review;
- causal graph with trigger, mechanisms, conditions, and negative findings;
- corrected code, tests, load and failure experiment, and controlled rollout record;
- post-incident actions with verification evidence and residual risks.

Another engineer should be able to trace every material claim to evidence, reproduce the safe lab, identify where uncertainty remains, and explain why the design revision addresses both security and performance mechanisms.

## 25. Know what the investigation does not prove

This case does not prove that:

- every slow search has the same cause;
- all authorization-cache designs should be local;
- batching is always faster or safer;
- one synthetic workload represents every tenant;
- rollback is always the correct first mitigation;
- the absence of another observed disclosure proves none occurred;
- one successful fault test guarantees future recovery;
- a post-incident action remains effective after the system evolves.

Claims remain bounded by workload, evidence, time window, tool behavior, and tested scope. Security notification and forensic conclusions stay with authorized organizational processes.

Engineering maturity is not confidence without limits. It is the ability to state what the evidence supports, what it contradicts, what it leaves unknown, and which next experiment is worth its risk and cost.

## 26. Review the complete investigation

### Problem and reproduction

- Is user impact defined with scope, timing, correctness, and SLO evidence?
- Are security, privacy, and data-integrity concerns routed correctly?
- Does the disposable reproducer preserve the conditions necessary for failure?
- Are workload, artifact, configuration, schema, data, and policy identities fixed?

### Cross-layer diagnosis

- Are multiple hypotheses tested with predictions and discriminating evidence?
- Do source history and release provenance match the running artifact?
- Are cloud, container, OS, CPU, memory, network, database, and dependency layers checked proportionately?
- Are authorization and tenant isolation proven independently of latency?
- Are negative findings and tool limitations recorded?

### Control and recovery

- Is mitigation reversible, scoped, approved, observable, and security-aware?
- Are unrelated changes frozen and emergency actions serialized?
- Does recovery include users, data, queues, capacity, redundancy, and temporary state?
- Is the candidate quarantined without losing the evidence trail?

### Revision and learning

- Does the correction address every supported mechanism without weakening invariants?
- Do tests cover isolation, fail-closed behavior, bounds, and representative load?
- Does controlled rollout observe shared downstream capacity?
- Are learning actions owned, prioritized, and verified through outcomes?

## Common Misconceptions

**“The deployment started the incident, so the diff is the root cause.”** The deployment is a trigger. The mechanism and impact require runtime, workload, dependency, control, and recovery evidence.

**“High latency means CPU needs scaling.”** Wall time can accumulate in pools, networks, locks, or remote services while CPU has headroom. Scaling callers can amplify the first constrained downstream resource.

**“A cache is safe when it returns the right data most of the time.”** A security decision cache is correct only when its identity, freshness, invalidation, default, and enforcement preserve every authorization input.

**“The rollback proves the candidate caused everything.”** Rollback is strong causal evidence, but simultaneous queue drain and state change still require a bounded account and follow-up experiment.

**“One fixed test closes the incident action.”** The fix must pass isolation, failure, load, recovery, and rollout verification in the relevant scope.

**“Cross-layer means collecting every metric.”** It means following the user journey and testing the cheapest evidence that can discriminate material hypotheses across boundaries.

## Core Computer Science Concept

This investigation combines abstraction, causality, and invariants. Each layer exposes a partial model; correlation identifiers connect events; experiments change one variable to test causal predictions; queues explain amplification; complete cache keys preserve equivalence classes; authorization invariants constrain acceptable optimization; and versioned artifacts make state transitions reproducible.

## Engineering Connections

- Command-line, operating-system, process, memory, storage, and network foundations come from Parts I, II, and V.
- Git history and safe recovery come from Part III.
- automation, build identity, deployment, and evidence come from Parts VI and VII.
- cloud routing, identity, managed data, observability, and cost come from Part VIII.
- architecture, data, caching, consistency, capacity, security, and delivery decisions come from Part IX.
- hypothesis testing, signals, profiles, cross-layer performance, incidents, and learning come from Chapters 118 through 128.

## From the Field

Teams often find the first plausible bottleneck and stop. In this case, a composite index could improve a graph while leaving 240 calls, retry amplification, and cross-tenant cache reuse intact. A cross-layer investigation asks which work should exist, which identity makes it safe, which queue fails first, and which evidence proves the user contract—not merely which knob makes one chart smaller.

## Engineering Review

### What problem does this solve?

It provides a complete method for moving from ambiguous user harm through reproducible evidence, safe mitigation, causal explanation, corrected design, verified delivery, and durable learning.

### Why was it designed this way?

Real failures cross abstractions. A linear tool checklist misses interactions, while a hypothesis-driven journey preserves both efficiency and the security, correctness, and operational constraints that local optimization can violate.

### When should I use it?

Use it for incidents, stubborn defects, performance regressions, security-boundary failures, and architecture decisions whose explanation crosses source, runtime, infrastructure, data, and human coordination.

### When should I avoid it?

Do not turn every small defect into a full major-incident exercise. Scale the evidence and coordination to risk, but never omit a material correctness, security, or reproducibility boundary for convenience.

### How does this make me a better engineer?

You learn to move between layers without losing the user journey, test causes rather than collect trivia, preserve invariants during optimization, and express conclusions at the strength the evidence permits.

### How does this reduce waste?

It prevents random scaling, premature rewrites, duplicate investigation, unsafe cache fixes, destroyed evidence, unverified action items, and repeated incidents caused by treating one symptom as the whole system.

## Handbook Principle #129

> Follow one user-visible failure across every boundary it actually crosses; preserve identity, evidence, and invariants; test competing explanations with the smallest safe experiment; mitigate through controlled reversible change; and call the investigation complete only when recovery, corrected design, delivery, and learning are independently verified.

## Practical Observation

For the next difficult failure, draw two lines on one page: the request path from user to durable state, and the evidence path from claim to source. Every hypothesis should name where it lives on the first line and what could support or contradict it on the second. Unlocated guesses and unsupported conclusions become visible immediately.

## Looking Ahead

The first-edition chapter sequence is complete. The Engineering Patterns appendix turns recurring reasoning structures—identity, boundaries, invariants, queues, idempotency, evidence, reversibility, and feedback—into a compact cross-reference for continued practice. The handbook itself must keep evolving as tools, platforms, standards, threats, and operating experience change.

## References

- [OpenTelemetry documentation — Context Propagation](https://opentelemetry.io/docs/concepts/context-propagation/)
- [Docker documentation — Runtime Metrics](https://docs.docker.com/engine/containers/runmetrics/)
- [PostgreSQL documentation — Using `EXPLAIN`](https://www.postgresql.org/docs/current/using-explain.html)
- [PostgreSQL documentation — Monitoring Database Activity](https://www.postgresql.org/docs/current/monitoring.html)
- [OWASP Cheat Sheet Series — Authorization](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)
- [Google SRE Book — Effective Troubleshooting](https://sre.google/sre-book/effective-troubleshooting/)
- [Chapter 115 — Security, Privacy, and Multi-Tenant Boundaries](../system-design/115-security-privacy-and-multi-tenant-boundaries.md)
- [Chapter 118 — Debugging as Hypothesis Testing](118-debugging-as-hypothesis-testing.md)
- [Chapter 127 — Incident Response and Operational Coordination](127-incident-response-and-operational-coordination.md)
- [Chapter 128 — Post-Incident Learning and Continuous Improvement](128-post-incident-learning-and-continuous-improvement.md)
