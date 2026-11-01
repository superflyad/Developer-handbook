# Chapter 115 — Security, Privacy, and Multi-Tenant Boundaries

Security is not a box attached to an otherwise complete architecture. It changes what the system may store, who may act, where data may travel, how administrators recover it, and which failures are acceptable. Privacy adds a second question: even when processing is authorized and protected from attackers, can it still create harm for the people represented by the data?

A useful design connects every control to an asset, actor, action, threat, and owner. “Use encryption” is incomplete. “Encrypt exported task archives with a managed key so storage operators cannot read them; the data platform team owns rotation and a quarterly restore test verifies availability” is reviewable.

This chapter develops that model for a multi-tenant task platform. It does not provide legal advice, prescribe a compliance framework, teach cryptographic implementation, or replace penetration testing.

## 1. Model security before choosing controls

Begin with the system model from Chapter 106. Add the facts an adversarial review needs:

- valuable assets, including identities, credentials, business data, metadata, logs, and availability;
- human and machine actors, their goals, and their allowed authority;
- components and data flows, including administration and recovery paths;
- trust boundaries where identity, ownership, integrity, or confidentiality assumptions change;
- entry points, third parties, and shared infrastructure;
- normal, degraded, migration, support, and deletion workflows.

Then ask what could go wrong. A control selected before this model may protect the wrong boundary. A private subnet does not stop an overprivileged internal service. Encryption at rest does not stop an authorized application from returning another tenant's record.

Security architecture is risk management under uncertainty. It identifies credible harm, reduces likelihood or impact, makes remaining risk explicit, and creates evidence that the controls still work.

## 2. Inventory assets by consequence

An asset is anything whose loss of confidentiality, integrity, availability, or appropriate use would matter. Inventory more than database tables:

| Asset | Security or privacy consequence | Important property |
| --- | --- | --- |
| Authentication session | Account takeover | Confidentiality and freshness |
| Tenant membership | Cross-tenant access | Integrity |
| Task title and attachment | Business or personal disclosure | Confidentiality and purpose limitation |
| Audit event | Hidden abuse or weak investigation | Integrity and availability |
| Encryption key | Bulk disclosure or unrecoverable data | Confidentiality and availability |
| Worker capacity | One tenant blocks others | Availability and fairness |
| Deletion request | Data retained against expectation | Integrity and completion |

Classify data by sensitivity and handling needs. Record its source, purpose, tenant owner, residency constraints, retention, deletion path, and downstream copies. Unknown copies are uncontrolled assets.

Do not confuse value with secrecy. The integrity of a feature flag or authorization rule may be more important than its confidentiality. Availability of identity and recovery mechanisms may determine whether the whole product can operate safely.

## 3. Distinguish actors from identities

An actor is a role in a journey; an identity is a verified subject represented in the system. One person may act as a tenant member, tenant administrator, support engineer, and incident responder at different times. A service may act for itself or on behalf of a user.

For each action, record:

- the actor and verified subject;
- the selected tenant and current membership;
- the requested resource and operation;
- delegated or impersonated authority;
- environmental facts that affect policy;
- who approved elevated access;
- what evidence must remain afterward.

This prevents vague labels such as “admin” from becoming unlimited authority. Separate customer administration, platform operation, support access, and emergency access. Their purposes, approval paths, and audit requirements differ.

## 4. Draw trust boundaries around changed assumptions

A trust boundary is crossed whenever data or execution moves into a context with different guarantees. Common boundaries include:

- browser to public API;
- API to worker queue;
- service to database;
- tenant-scoped path to platform-wide administration;
- production to analytics;
- primary storage to backup and restore tooling;
- first-party service to third-party processor;
- build system to deployment authority.

At each crossing, ask how the receiver establishes identity, tenant, integrity, freshness, confidentiality, and allowed purpose. Do not inherit trust merely because traffic came from an internal network. NIST's zero-trust model focuses authorization on resources and subjects rather than granting implicit trust based on network location.

The diagram should show credentials and control flows as well as business data. A management interface with no customer traffic can still be the most powerful entry point.

## 5. Threat-model concrete flows

Threat modeling is a structured way to examine the design from an adversarial perspective. It should produce testable requirements, not a list of frightening nouns.

For one flow:

1. State the legitimate journey and security properties.
2. Trace components, stores, and trust boundaries.
3. Identify attacker goals and misuse by authorized actors.
4. Use prompts such as spoofing, tampering, repudiation, disclosure, denial of service, and privilege escalation.
5. Describe the precondition, action, affected asset, and consequence.
6. Choose to mitigate, eliminate, transfer, or explicitly accept the risk.
7. Assign the control, verification, residual risk, and owner.

For example: “A member changes a task ID and reads another tenant's task because the handler queries only by task ID.” The control is not “secure the API.” It is a server-side authorization rule binding the verified principal, selected tenant, action, and resource ownership, with negative integration tests.

Repeat the review when trust boundaries, identity providers, data uses, tenant models, or privileged paths change. A threat model is a maintained design artifact.

## 6. Separate authentication from authorization

**Authentication** establishes confidence in the subject. **Authorization** decides whether that subject may perform this action on this resource in this context. A valid session proves neither tenant membership nor permission.

Authentication design includes enrollment, authenticator strength, recovery, revocation, session lifetime, reauthentication, federation, and compromised-credential response. Use maintained identity libraries and providers; do not invent password storage or token protocols. Select assurance proportional to the consequence, especially for privileged and recovery actions.

Authorization should be:

- deny-by-default;
- enforced server-side at every reachable path;
- based on current policy and resource context;
- resistant to identifier substitution;
- consistent for synchronous, asynchronous, bulk, export, and administrative operations;
- tested with allowed and denied cases.

Role-based access control can express stable job functions. Attribute-based rules can include resource, tenant, relationship, and environment. Relationship-based rules can express ownership and sharing. Choose the smallest model that represents the product correctly; scattered role-name conditionals are not a policy architecture.

## 7. Bind tenant context to verified authority

A client-provided tenant ID is a selector, not proof. Establish tenant context early by combining the authenticated subject with current membership or service authority. Propagate the verified context without letting downstream callers replace it.

Every tenant-owned lookup should bind resource identity to tenant scope. Depending on the storage design, that may be a composite key, row-level policy, schema boundary, database credential, or separate store. Parameterized SQL prevents injection; it does not prevent a correctly formed cross-tenant query.

Apply tenant scope to more than the primary database:

- cache and idempotency keys;
- search indexes and vector stores;
- object paths and signed downloads;
- queue messages and scheduled jobs;
- logs, metrics, exports, and analytics;
- rate limits, concurrency, and quotas;
- backups, restores, migrations, and deletion jobs.

A missing tenant dimension in any derived store can bypass an otherwise correct API.

## 8. Choose an isolation model deliberately

Multi-tenancy trades efficiency for correlated risk. Isolation is a spectrum:

| Model | Strength and flexibility | Cost and failure consequence |
| --- | --- | --- |
| Shared tables with tenant predicates | Efficient and simple to operate | One missed predicate can expose many tenants |
| Shared database, separate schemas | Stronger namespace and migration boundaries | More operational objects and connection rules |
| Separate databases or accounts | Strong data and credential boundaries | Higher fleet, migration, and cost overhead |
| Dedicated deployment or cell | Strong compute and blast-radius isolation | Highest operational complexity and fragmentation |

Choose by sensitivity, regulatory or contractual constraints, tenant size, customization, noisy-neighbor risk, restore needs, and operational maturity. Hybrid tiers are reasonable if movement between tiers is designed.

Defense in depth can combine application authorization with data-layer policy. But the second layer must use a role that cannot casually bypass it, and pooled connections must reset tenant state safely. Test the actual production identity and connection behavior.

## 9. Enforce least privilege across every plane

Least privilege gives a subject only the actions, resources, and duration needed. Apply it to:

- users and tenant administrators;
- service identities and deployment automation;
- database roles and object-store policies;
- encryption-key use;
- support and incident tooling;
- build systems and artifact publication;
- backups and recovery systems.

Separate read, write, export, delete, impersonate, and policy-change authority. Prefer short-lived, purpose-bound credentials over shared long-lived secrets. Make temporary elevation expire automatically.

Privilege also includes capacity. One tenant with unlimited queue depth or connection use can violate every other tenant's availability. Quotas, fair scheduling, and bulkheads are tenant-isolation controls as well as resilience controls.

## 10. Encrypt data with a key lifecycle

Encrypt data in transit across untrusted or independently administered boundaries and encrypt sensitive stored data according to its threat model. Then answer the harder questions:

- Who may request decryption?
- Which service identity can use which key?
- Are keys separated by environment, purpose, or tenant?
- How are keys generated, stored, rotated, revoked, backed up, and destroyed?
- Can encrypted backups still be restored after rotation?
- What telemetry detects unusual decrypt activity?

Encryption relocates trust into key management; it does not erase it. Application-level encryption can narrow exposure to storage operators but complicates search, indexing, rotation, and recovery. Per-tenant keys can support cryptographic separation and targeted revocation but increase lifecycle complexity.

Use established algorithms and managed key systems. Cryptographic engineering is outside this chapter's scope; architecture should state the required property and ownership without inventing a primitive.

## 11. Manage secrets as expiring capabilities

Passwords, API tokens, signing keys, certificates, and database credentials grant authority. A secret lifecycle includes generation, distribution, storage, use, rotation, revocation, observation, and disposal.

Keep secrets out of source, images, logs, error messages, and general configuration. Workloads should retrieve a secret reference or receive a short-lived credential through an authenticated channel. Scope it to one environment and purpose. Automate rotation without requiring a synchronized flag day; systems often need a bounded overlap while old credentials drain.

Inventory secret consumers before rotation. A forgotten batch worker can turn a security improvement into an outage. Test both successful rollover and prompt revocation after compromise.

## 12. Design audit evidence, not verbose logs

Security audit events answer who attempted what, against which tenant and resource, through which authority, with what result, and under which policy version. Record high-consequence events such as:

- sign-in, recovery, factor, and session changes;
- membership and permission changes;
- export, deletion, key, and secret operations;
- administrative access and impersonation;
- denied cross-tenant attempts;
- configuration, deployment, and policy changes;
- restore and emergency-access activity.

Protect audit integrity and restrict access. Use reliable time, correlation identifiers, and retention that supports investigation. Avoid copying tokens, passwords, raw personal data, or full request bodies merely because storage is cheap.

Logging is not authorization. An event recorded after unauthorized access is evidence of failure, not prevention.

## 13. Treat privacy as a data-processing risk

Security asks whether an unauthorized party can access or change data. Privacy also asks whether authorized processing creates unwanted observation, inference, loss of autonomy, exclusion, or other harm.

For each personal-data element, document:

- the product purpose and accountable owner;
- how it is collected or inferred;
- who receives it and why;
- transformations and derived attributes;
- retention and deletion behavior;
- individual controls and communications;
- secondary uses, model training, or analytics;
- the harm if processing is inaccurate, excessive, unexpected, or permanent.

Data minimization is an architectural control. Data never collected, copied, or retained cannot be exposed later. Prefer purpose-specific fields and aggregated measures over convenient raw-event accumulation.

The NIST Privacy Framework provides a risk-management vocabulary rather than a universal legal checklist. Product teams still need qualified legal and privacy guidance for applicable obligations.

## 14. Make retention and deletion executable

“Retain for 30 days” must map to data states and jobs. Identify primary records, replicas, caches, indexes, object versions, analytics, audit exceptions, backups, and downstream processors. Define when the clock starts and what deletion means in each store.

A deletion workflow needs:

- an authenticated and authorized request;
- a durable work record;
- discovery of all scoped copies;
- idempotent deletion or tombstoning;
- handling for legal or operational holds by authorized owners;
- retry and reconciliation;
- completion evidence that does not recreate deleted content;
- a documented backup-expiration or restore-time deletion strategy.

Test deletion after schema changes and new integrations. If the team cannot enumerate copies, it cannot prove completion.

## 15. Model abuse of valid features

Not every harmful action exploits a technical vulnerability. An authenticated user may automate invitations, scrape shared content, spam notifications, enumerate organizations, or use exports to harass people. Abuse cases examine valid functions used at unintended scale, sequence, target, or purpose.

Controls may include rate and value limits, friction for high-risk actions, recipient controls, anomaly detection, moderation, delayed execution, approval, and reversible suspension. Evaluate false positives and appeal paths. An abuse defense that silently locks legitimate users out is itself a product and availability risk.

Keep abuse signals scoped and access-controlled; a broad surveillance system can create a new privacy asset and threat.

## 16. Isolate caches, queues, and asynchronous work

Cross-tenant bugs often appear outside request handlers. Cache keys must include every dimension that changes the result, including tenant, subject, authorization state, locale, and policy version where relevant. Invalidate when membership or permission changes.

Messages should carry a server-established tenant context and immutable identifiers, but consumers must authenticate the producer path and authorize the operation they perform. A tenant field inside a message is still data, not proof. Dead-letter queues, replay tools, and manual repair interfaces require the same isolation.

Partition capacity or apply tenant-aware admission control so one tenant cannot monopolize shared workers. Re-establish context at each asynchronous boundary; ambient request state does not survive a queue.

## 17. Secure administrative and support paths

Platform-wide operations intentionally cross tenant boundaries, so they deserve stronger separation:

- distinct identities and roles;
- phishing-resistant authentication appropriate to risk;
- explicit reason and ticket or approval context;
- just-in-time, time-limited elevation;
- visible impersonation state;
- customer or second-person approval where appropriate;
- detailed tamper-resistant audit;
- rapid revocation and periodic access review.

Do not hide administration behind an obscure URL and call it protected. Avoid using ordinary tenant code with a boolean that disables all scoping. Make the cross-tenant path structurally explicit and narrow.

Emergency access should be usable during identity or network failure, but highly protected, tested, monitored, and reviewed after every use. An untested break-glass path is either unavailable or an unnoticed backdoor.

## 18. Preserve boundaries during migration and recovery

Backups contain the same sensitive data as production, often with broader historical coverage. Restrict backup access, encrypt it independently, test restoration, and expire it according to policy. A tenant-scoped restore from a shared snapshot must not overwrite live shared data or expose other tenants through temporary storage.

Migrations, reindexing, and repair jobs often run with broad authority. Limit their scope, make dry runs possible, record counts by tenant, use checkpoints, and verify postconditions. Temporary export files need owners and deletion deadlines.

Degraded modes must preserve authorization and tenant isolation. If the policy service is unavailable, “allow everything” is not graceful degradation. Choose a bounded cached policy, a safe read-only mode, or fail closed according to consequence.

## 19. Make third-party boundaries explicit

A vendor integration changes the data-processing ecosystem. Record what data leaves, the purpose, region, retention, sub-processors, deletion interface, identity model, availability dependency, and incident responsibilities. Give the integration its own credential and least-privileged scope.

Validate webhook authenticity and replay resistance. Treat third-party output as untrusted input. Prevent a compromised vendor from selecting arbitrary tenants or actions. Provide a kill switch that disables the integration without disabling unrelated service.

Contracts may allocate responsibility, but they do not technically reduce exposure. Verify the controls and preserve evidence appropriate to the risk.

## 20. Test negative space

Happy-path tests prove that allowed users can work. Security tests must prove that forbidden combinations cannot:

- member A cannot read tenant B's resource by ID;
- a removed member loses access in APIs, caches, and queued work;
- a worker cannot replace verified tenant context;
- an export contains only authorized fields and rows;
- a support role cannot invoke emergency authority;
- rotated credentials stop working after the overlap window;
- deletion reconciles every declared store;
- restoring one tenant does not expose or alter another;
- degraded mode preserves authorization and privacy rules;
- one tenant cannot consume unbounded shared capacity.

Generate combinations of subject, tenant, resource, action, and state. Keep a small set of end-to-end isolation canaries because unit tests cannot detect a bypass around the policy layer.

## 21. Assign ownership and residual risk

Every accepted threat needs a decision owner and review trigger. Every mitigation needs an implementation owner, verification method, and operational signal. “The security team owns security” leaves application and data boundaries ownerless.

A useful risk record contains:

| Field | Question |
| --- | --- |
| Threat | What action produces what consequence? |
| Asset and boundary | What is affected and where? |
| Control | How is likelihood or impact reduced? |
| Verification | Which test or observation proves it? |
| Residual risk | What remains after the control? |
| Owner | Who accepts and maintains it? |
| Trigger | What change requires review? |

Security exceptions should expire or be reviewed. Permanent undocumented exceptions become architecture.

## 22. Apply the model to the task platform

Consider `GET /tenants/{tenant_id}/tasks/{task_id}`:

1. The gateway validates the session but does not accept its tenant claim as sufficient.
2. The authorization layer verifies current membership and the `task:read` action.
3. The repository queries by both tenant and task identity using a tenant-scoped database role.
4. The cache key includes tenant, task, representation, and relevant policy version.
5. The response exposes only fields allowed for the actor.
6. An audit event records unusual denied cross-tenant attempts without logging task content.

Now follow an attachment preview job. The API places verified tenant and object identities into a signed or authenticated message. The worker authorizes its service action, reads from a tenant-scoped object path, writes the preview under the same scope, and cannot choose a different tenant from attachment metadata. Its queue quota prevents one tenant from exhausting every preview worker.

Finally, follow deletion and restore. Both must preserve the same tenant association across primary storage, objects, search, cache, analytics, and backups. Security is the property across the whole lifecycle, not just the public endpoint.

## 23. Encode a security architecture contract

The following small model turns important review claims into executable invariants. It is not an authorization engine; it demonstrates how architecture statements can become tests.

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class DataAsset:
    name: str
    purpose: str
    tenant_scoped: bool
    retention_days: int

    def validate(self) -> None:
        if not self.name.strip() or not self.purpose.strip():
            raise ValueError("asset needs a name and purpose")
        if self.retention_days <= 0:
            raise ValueError("asset needs bounded retention")


@dataclass(frozen=True)
class SecurityContract:
    asset: DataAsset
    authentication_defined: bool
    authorization_server_side: bool
    least_privilege_defined: bool
    encryption_key_owner: str
    secret_rotation_tested: bool
    audit_minimized_and_protected: bool
    deletion_verified: bool
    tenant_context_verified: bool
    derived_stores_tenant_scoped: bool
    admin_path_separate: bool
    recovery_preserves_isolation: bool
    residual_risk_owner: str

    def validate(self) -> None:
        self.asset.validate()
        if not self.authentication_defined or not self.authorization_server_side:
            raise ValueError("identity or authorization boundary is incomplete")
        if not self.least_privilege_defined:
            raise ValueError("authority is not least privileged")
        if not self.encryption_key_owner.strip() or not self.secret_rotation_tested:
            raise ValueError("credential lifecycle lacks ownership or proof")
        if not self.audit_minimized_and_protected:
            raise ValueError("audit evidence creates or permits disclosure")
        if not self.deletion_verified:
            raise ValueError("retention has no verified deletion path")
        if self.asset.tenant_scoped:
            if not self.tenant_context_verified:
                raise ValueError("tenant selector is not verified authority")
            if not self.derived_stores_tenant_scoped:
                raise ValueError("derived store can cross tenant boundaries")
            if not self.recovery_preserves_isolation:
                raise ValueError("recovery can violate tenant isolation")
        if not self.admin_path_separate:
            raise ValueError("cross-tenant administration is implicit")
        if not self.residual_risk_owner.strip():
            raise ValueError("residual risk has no owner")
```

The tests exercise the forbidden combinations, not merely the complete case:

```python
from dataclasses import replace
import unittest

from security_contract import DataAsset, SecurityContract


def valid_contract() -> SecurityContract:
    return SecurityContract(
        asset=DataAsset("task attachment", "team collaboration", True, 30),
        authentication_defined=True,
        authorization_server_side=True,
        least_privilege_defined=True,
        encryption_key_owner="security platform",
        secret_rotation_tested=True,
        audit_minimized_and_protected=True,
        deletion_verified=True,
        tenant_context_verified=True,
        derived_stores_tenant_scoped=True,
        admin_path_separate=True,
        recovery_preserves_isolation=True,
        residual_risk_owner="task product owner",
    )


class SecurityContractTests(unittest.TestCase):
    def test_complete_contract_is_accepted(self):
        valid_contract().validate()

    def test_unbounded_retention_is_rejected(self):
        contract = valid_contract()
        contract = replace(contract, asset=replace(contract.asset, retention_days=0))
        with self.assertRaisesRegex(ValueError, "bounded retention"):
            contract.validate()

    def test_client_only_authorization_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "authorization boundary"):
            replace(valid_contract(), authorization_server_side=False).validate()

    def test_unowned_key_lifecycle_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "credential lifecycle"):
            replace(valid_contract(), encryption_key_owner="").validate()

    def test_unverified_deletion_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "deletion path"):
            replace(valid_contract(), deletion_verified=False).validate()

    def test_unverified_tenant_selector_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "verified authority"):
            replace(valid_contract(), tenant_context_verified=False).validate()

    def test_unscoped_cache_or_index_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "derived store"):
            replace(valid_contract(), derived_stores_tenant_scoped=False).validate()

    def test_implicit_admin_path_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "administration"):
            replace(valid_contract(), admin_path_separate=False).validate()

    def test_cross_tenant_recovery_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "recovery"):
            replace(valid_contract(), recovery_preserves_isolation=False).validate()

    def test_unowned_residual_risk_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "risk has no owner"):
            replace(valid_contract(), residual_risk_owner="").validate()


if __name__ == "__main__":
    unittest.main()
```

Production controls need implementation-specific verification, adversarial review, dependency assessment, and operational monitoring. The value of this model is traceability: an asset and threat lead to an invariant, an owner, and a failing test.

## 24. Review security, privacy, and tenancy

Before approving a design, ask:

### Assets and processing

- Are sensitive assets, metadata, credentials, logs, and availability needs inventoried?
- Does each personal-data element have a purpose, owner, retention, and deletion path?
- Are secondary uses and downstream processors visible?

### Identity and authority

- Are authentication, authorization, delegation, recovery, and revocation distinct?
- Is policy enforced server-side on every synchronous, asynchronous, bulk, and admin path?
- Does least privilege cover people, services, data, keys, pipelines, and capacity?

### Tenant isolation

- Is tenant context derived from verified authority rather than client input?
- Do database, cache, search, object, queue, analytics, backup, and restore paths preserve scope?
- Can one tenant affect another's confidentiality, integrity, or availability?

### Operations and evidence

- Are secrets and keys owned through rotation, revocation, backup, and destruction?
- Are audit events useful, protected, minimized, and reviewed?
- Do degraded, migration, support, deletion, and recovery modes preserve the controls?
- Does every mitigation and accepted residual risk have an owner and review trigger?

## Common Misconceptions

- **“The user is authenticated, so access is safe.”** Authentication does not authorize a tenant, resource, or action.
- **“Random IDs provide isolation.”** They reduce guessing; they do not prove ownership or permission.
- **“Encryption solves confidentiality.”** Decryption authority, key lifecycle, application access, and copies still determine exposure.
- **“Internal services are trusted.”** Internal identity and network location do not replace resource authorization.
- **“A `tenant_id` column makes a system multi-tenant safe.”** Every access and derived store must enforce its meaning.
- **“Privacy means keeping data secret.”** Authorized collection, inference, sharing, and retention can still harm people.
- **“More logs always improve security.”** Excessive logging can leak credentials and personal data while obscuring useful events.

## Core Computer Science Concept

This chapter applies **reference monitors, complete mediation, capabilities, least privilege, information-flow boundaries, isolation, data lifecycle state machines, and adversarial modeling**. A security property must hold on every path that reaches the asset, including maintenance and recovery paths.

## Engineering Connections

- Identity and OS authority extend Chapters 20, 46, 48, 60, 87, and 92.
- Interface and data contracts apply Chapters 59, 69, 99, 107, and 108.
- Asynchronous scope and capacity isolation build on Chapters 109, 112, and 114.
- Audit and verification connect Chapters 72, 73, 93, and 100.
- Chapter 116 records why these boundaries and residual risks were accepted.

## From the Field

A SaaS API correctly filters database rows by tenant, but a new response cache uses only `task_id`. The first tenant warms the entry; the second requests a colliding identifier and receives the first tenant's task. Database isolation remained intact while a derived store violated the boundary. Tenant-aware cache keys, authorization before reuse, negative cross-tenant tests, and inventorying every derived copy would have exposed the flaw before release.

## Engineering Review

### What problem does this solve?

It prevents architecture from treating threats, personal-data use, privileged access, and tenant isolation as late implementation details.

### Why was it designed this way?

Asset-to-threat-to-control traceability makes vague assurances testable and gives each residual risk an accountable owner.

### When should I use it?

Use it for any system that processes valuable data, delegates authority, exposes administrative paths, or shares infrastructure among customers or trust domains.

### When should I avoid it?

Do not use this chapter as a substitute for applicable legal advice, specialist cryptographic design, independent security testing, or an organization's risk-acceptance process.

### How does this make me a better engineer?

You learn to trace authority and data across the full lifecycle, find bypass paths, and express security claims as falsifiable invariants.

### How does this reduce waste?

Early boundary decisions prevent costly data migrations, retrofitted access control, uncontrolled retention, duplicated security products, and incident-driven redesign.

## Handbook Principle #115

> Protect an asset on every path that can reach it: establish identity, authorize the exact action, minimize data and authority, preserve tenant scope through derived and recovery systems, and assign ownership for what remains.

## Practical Observation

Choose one tenant-owned record and search for every representation of its identifier: primary rows, caches, indexes, objects, messages, logs, analytics, exports, and backups. For each copy, identify how tenant scope is established and how deletion occurs. The first unexplained copy is the next design task.

## Looking Ahead

Chapter 116 turns choices such as isolation tier, authorization model, encryption boundary, and accepted residual risk into decision records that preserve context while allowing the architecture to evolve.

## References

- [OWASP — Threat Modeling Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html)
- [OWASP — Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)
- [OWASP — Multi-Tenant Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Multi_Tenant_Security_Cheat_Sheet.html)
- [OWASP — Application Security Verification Standard 5.0](https://asvs.owasp.org/)
- [NIST SP 800-207 — Zero Trust Architecture](https://csrc.nist.gov/pubs/sp/800/207/final)
- [NIST SP 800-63B-4 — Authentication and Authenticator Management](https://csrc.nist.gov/pubs/sp/800/63/B/4/final)
- [NIST — Privacy Framework](https://www.nist.gov/privacy-framework)
- [NIST SP 1800-28 — Data Confidentiality: Identifying and Protecting Assets Against Data Breaches](https://csrc.nist.gov/pubs/sp/1800/28/final)
