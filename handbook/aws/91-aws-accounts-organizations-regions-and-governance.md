# Chapter 91 — AWS Accounts, Organizations, Regions, and Governance

A single AWS account can contain a surprising amount of infrastructure. That convenience becomes dangerous when production, experiments, security evidence, organization administration, and unrelated cost owners all share the same credentials, quotas, and failure boundary.

The central idea is:

> Treat accounts and Regions as architectural boundaries. Give each boundary an owner, purpose, policy, budget, recovery path, and lifecycle before placing workloads inside it.

## 1. An AWS account is more than a login

An AWS account is simultaneously:

- a resource container;
- an identity and authorization boundary;
- a default billing and cost-allocation boundary;
- a quota and API-rate boundary for many services;
- an ownership and incident-response boundary;
- a unit that can join an AWS Organization.

Resources in different accounts are logically isolated by default. Cross-account access must be deliberately authorized. This makes accounts useful for containing mistakes and compromise, separating data classes, assigning costs, and allowing teams to operate without sharing one universal administrator role.

An account is not a complete security boundary by itself. Cross-account roles, resource policies, shared networks, organization administrators, external identities, replicated data, and centralized automation can reconnect accounts. Document every connection that crosses the boundary.

## 2. Design boundaries from consequences

Create a separate account when resources need a meaningfully different combination of:

- business owner;
- operational owner;
- data sensitivity or regulatory scope;
- production criticality;
- human or machine access;
- preventive controls;
- network connectivity;
- quota pool;
- budget and payer visibility;
- incident blast radius;
- lifecycle or divestment path.

Do not create accounts merely to make a diagram symmetrical. Every boundary adds provisioning, access, network, observability, and recovery work. The useful question is not “How many accounts should we have?” but “Which consequences must not be shared?”

## 3. Separate production from non-production

Production and non-production commonly differ in:

- who can administer them;
- which data may enter them;
- allowed services and Regions;
- change approval and deployment paths;
- monitoring and retention;
- recovery objectives;
- cost tolerance;
- incident severity.

Separate accounts make those differences enforceable. A development credential or runaway experiment should not consume a production quota, alter a production route, expose production data, or exhaust the same budget.

Environment separation does not justify copying real customer data into development. Use synthetic, minimized, or irreversibly transformed data under an explicit policy.

## 4. Organize around workloads and controls

A practical starting pattern is:

```text
organization root
├── Security OU
│   ├── log-archive
│   └── security-audit
├── Infrastructure OU
│   ├── network
│   └── shared-services
├── Workloads-Prod OU
│   ├── payments-prod
│   └── catalog-prod
├── Workloads-NonProd OU
│   ├── payments-nonprod
│   └── catalog-nonprod
├── Sandbox OU
│   └── engineer-sandboxes
├── Policy-Staging OU
│   └── governance-test
└── Suspended OU
```

The exact names are not important. The control relationships are.

Small organizations can begin with fewer accounts while preserving the same distinctions. Avoid putting ordinary workloads into the management, log archive, security audit, or emergency-access accounts simply because those accounts already exist.

## 5. AWS Organizations provides a governance hierarchy

AWS Organizations can group a management account and member accounts into one organization. With all features enabled, it supports organizational units, organization policies, delegated administration for supported services, and consolidated billing.

An organizational unit, or OU, groups accounts that need common controls. OUs form a tree below the organization root, and an account belongs directly to one parent OU or the root at a time.

Use OUs for stable policy intent, such as:

- production workloads;
- non-production workloads;
- security functions;
- shared infrastructure;
- sandboxes;
- policy staging;
- suspended or quarantined accounts.

Do not mirror a frequently changing reporting chart. Teams reorganize more often than security and operational control sets should.

## 6. Protect the management account

The Organizations management account can perform organization-wide administration and is responsible for the charges of member accounts under consolidated billing. Service control policies do not restrict principals in this account.

Therefore:

- use it only for tasks that require the management account;
- do not run business workloads there;
- minimize and review human access;
- protect and periodically verify root recovery information;
- use delegated administrator accounts where the service supports them;
- centralize evidence without centralizing every powerful credential;
- alert on use of privileged and root paths.

A management-account compromise can alter the guardrails intended to protect every member account. Treat its administrative surface as a critical control system.

## 7. Delegate service administration carefully

Supported AWS services can designate a member account as a delegated administrator. This reduces routine use of the management account and can align administration with the security, infrastructure, or operations team that owns the capability.

Delegation is not harmless. A delegated administrator may affect many accounts. For each delegated service, record:

- the member account;
- the owning team and on-call path;
- exact organization-wide authority;
- roles allowed to use it;
- audit events and alerts;
- change and rollback procedure;
- behavior if the delegated account is unavailable or compromised.

Do not accumulate unrelated organization-wide powers in one “tools” account without considering the resulting blast radius.

## 8. Service control policies are ceilings, not grants

A service control policy, or SCP, limits the maximum permissions available to principals in affected member accounts. It does not grant permission. An IAM identity or resource policy must still allow an action, and an applicable explicit deny still wins.

A useful simplified model is:

```text
effective permission
    = identity or resource permission
    intersected with every applicable organization guardrail
    intersected with other permission boundaries
    minus any applicable explicit deny
```

The complete IAM evaluation model has important exceptions and resource-policy details, which Chapter 92 addresses. For governance design, remember:

- SCPs affect member accounts, including their root users;
- SCPs do not affect principals in the management account;
- an SCP that allows an action does not authorize anyone to perform it;
- policies inherited from the root and parent OUs contribute to the effective ceiling;
- moving an account to another OU can change its permissions immediately.

## 9. Prefer guardrails with testable intent

Good organization guardrails protect invariants that account administrators must not override. Examples include preventing:

- disabling required audit controls;
- leaving approved Regions without an exception;
- changing protected security resources;
- creating prohibited public exposure;
- using services disallowed by policy;
- deleting required recovery evidence.

Avoid copying a policy from an example and attaching it at the root. First define:

- the invariant and threat it addresses;
- affected accounts and principals;
- services and API behavior involved;
- automation roles that require exceptions;
- recovery and break-glass behavior;
- test cases for allowed and denied actions;
- staged rollout and rollback.

An incorrect root-level deny can interrupt every workload at once.

## 10. Stage organization policy changes

Treat SCPs and other organization policies as code:

1. review the policy and its assumptions;
2. evaluate service last-accessed and workload evidence;
3. test it in a policy-staging account or separate test organization;
4. test expected allows as well as expected denies;
5. attach it to a narrow non-production OU;
6. observe audit events and workload behavior;
7. expand gradually;
8. retain a tested rollback path.

Policy syntax validation is necessary but insufficient. The important test is whether real principals can still perform required operations while prohibited operations fail for the intended reason.

## 11. Choose Regions through explicit constraints

A Region decision should consider:

- legal and contractual data-location requirements;
- service and feature availability;
- user and dependency latency;
- price and inter-Region transfer cost;
- carbon and sustainability objectives;
- quota availability and increase lead time;
- support for required instance types or capacity;
- recovery objectives and correlated risks;
- identity, logging, key, artifact, and deployment dependencies;
- the team's ability to operate the Region.

Record why a Region is approved, not just its short name. Revisit the decision as requirements and AWS capabilities change.

The cheapest compute price does not prove the lowest system cost. Data transfer, duplicated controls, operational complexity, support, and recovery exercises also consume money and attention.

## 12. Region enablement is a control

Some AWS Regions are enabled by default; opt-in Regions must be enabled before use. Enabling or disabling a Region is an asynchronous account operation and can take time while AWS prepares underlying services and distributes identity resources.

Maintain an approved-Region set and reconcile actual account status against it. Region restriction can reduce accidental deployment and monitoring gaps, but it must account for:

- global services and their control endpoints;
- services whose resources are not Regional;
- disaster-recovery Regions;
- audit and security tooling;
- organization policy exceptions;
- existing resources before a Region is disabled.

Disabling a Region is not a substitute for inventory, data migration, backup validation, and teardown.

## 13. Availability Zones are not accounts or Regions

An Availability Zone is an isolated location within a Region. An account is an administrative boundary. A Region is a geographic and service boundary. These dimensions solve different problems.

A production account can deploy a workload across multiple AZs to tolerate a zonal failure while retaining one account-level security and billing boundary. Separate accounts do not create zonal redundancy. Multiple AZs do not protect against an account-wide destructive action or every Regional failure.

For each production workload, state:

- required number of AZs;
- capacity needed after losing one AZ;
- which state is synchronously or asynchronously replicated;
- whether any dependency remains single-AZ;
- whether Region-level recovery is required;
- who can invoke and validate recovery.

## 14. Multi-Region is a business decision

Multi-Region designs may improve recovery from a Regional disruption or meet latency and sovereignty needs. They also introduce:

- replication lag and conflict handling;
- key and secret distribution;
- global traffic steering;
- duplicate quotas and capacity;
- additional cost;
- more complicated deployments and schema changes;
- failover and failback procedures;
- a larger policy and observability surface.

Do not add a second Region as a diagram label. Define the recovery point objective, recovery time objective, data authority, activation trigger, capacity model, and test schedule.

## 15. Maintain an account inventory

Every account should have authoritative metadata outside the account itself:

- account ID and durable internal name;
- lifecycle state;
- parent OU;
- purpose and environment;
- business, technical, security, and cost owners;
- workload and data classifications;
- approved and enabled Regions;
- identity and emergency-access paths;
- network and shared-service connections;
- delegated administration roles;
- baseline version and exceptions;
- budgets, quotas, and alert destinations;
- creation, review, suspension, and closure dates.

Names help humans; account IDs identify AWS principals and resources. Never infer authority from a display name alone.

## 16. Tags add metadata, not isolation

Tags are case-sensitive key-value metadata supported by many AWS resources. They can help with:

- cost allocation;
- ownership and inventory;
- automation selection;
- access-control conditions where the service supports them;
- compliance and lifecycle reporting.

A starting tag vocabulary might include:

```text
org:workload-id
org:environment
org:cost-center
org:technical-owner
org:data-classification
org:lifecycle
```

Use stable identifiers instead of a person's name. Do not put credentials, personal data, customer data, or other secrets in tags; tags are visible to multiple services and billing systems.

Tags do not replace account boundaries. A mistyped or mutable `environment=prod` tag cannot provide the same containment as a separate production account.

## 17. Govern tags as a schema

Define for each required tag:

- canonical spelling and case;
- allowed values or identifier source;
- which resource types support it;
- whether it is inherited or propagated;
- who can set or change it;
- whether it participates in authorization;
- whether it must be activated for cost allocation;
- how missing or invalid values are detected and remediated.

AWS Organizations tag policies can standardize supported tag keys and values and report or enforce compliance for supported resource types. They do not retroactively invent correct ownership, and enforcement coverage must be verified per service.

If tags drive access control, protect tag mutation with the same care as permission changes.

## 18. Quotas belong in governance

Many AWS quotas are scoped per account, per Region, per resource, or some combination. A multi-account structure can isolate quota consumption, but it also creates more quota sets to inventory and raise.

For every workload account and active Region:

- identify limiting quotas;
- calculate steady-state, burst, deployment, and recovery demand;
- inspect the applied value, not only the default;
- request increases before they are needed;
- alarm below exhaustion with enough response time;
- test degraded behavior when throttled;
- assign an owner and review date.

Recovery capacity that requires an unapproved quota increase does not yet exist.

## 19. Budgets are ownership signals

Assign each account a cost owner and expected operating range. Create budgets and alerts before workload spend begins. Useful layers include:

- an organization-level total;
- an account or workload budget;
- environment and project views;
- anomaly detection;
- service- or usage-specific thresholds;
- forecasted as well as actual spend.

Budget data is delayed and alerts are not hard real-time circuit breakers. Automatic budget actions can also interrupt legitimate workloads. Use them only with reviewed thresholds, exemptions, and recovery procedures.

A budget without a recipient who can investigate and act is merely a report.

## 20. Understand consolidated billing

Under AWS Organizations consolidated billing, the management account is responsible for member-account charges. The organization can receive combined usage benefits and centralized cost data, but consolidated billing does not make spend ownership self-explanatory.

Important consequences include:

- the payer needs organization-wide cost controls and visibility;
- account ownership should map to internal allocation;
- cost allocation tags or categories require governance;
- discounts and shared commitments can complicate chargeback;
- the bill does not automatically mirror the OU hierarchy;
- member-account lifecycle changes can affect access to historical cost data.

Separate payer responsibility from workload cost accountability. Central payment must not become anonymous consumption.

## 21. Design emergency access before the emergency

Normal workforce access may depend on IAM Identity Center, an external identity provider, a Region, networking, and several administrative services. A failure in that path can occur while urgent workload changes are still required.

An emergency-access design should define:

- the failure conditions that justify activation;
- a path independent of the failed component;
- a dedicated emergency operations account or equivalent boundary;
- narrowly scoped roles in target accounts;
- strong authentication and protected credentials;
- two-person or similarly controlled activation where appropriate;
- short sessions and explicit expiration;
- immediate logging and alerting;
- a command and communication procedure;
- periodic tests;
- revocation, credential rotation, and post-use review.

AWS documents a direct federation pattern for IAM Identity Center disruptions. Its dependencies must match your actual threat model. A path that uses the same unavailable identity provider is not independent of an identity-provider outage.

“Break glass” means controlled exceptional access, not a permanently shared administrator password.

## 22. Preserve root recovery without using root routinely

Some account operations require the root user. Routine administration should use federated roles and temporary credentials, but every account still needs a controlled root-recovery process.

For each account:

- use an organization-controlled email address and phone process;
- protect root authentication according to current AWS guidance;
- prevent dependence on one employee;
- alert on root use;
- document required root-only tasks;
- review recovery contacts periodically;
- test the organizational process without unnecessarily using root in production.

Centralized root credential management, when applicable to the organization, changes implementation details but not the need for explicit ownership and recovery evidence.

## 23. Govern the complete account lifecycle

Account governance begins before creation and continues after workloads stop:

1. request with purpose, owners, data class, environment, Regions, and budget;
2. approve the boundary and connections;
3. provision through a repeatable account-vending workflow;
4. apply identity, logging, security, network, tag, quota, and cost baselines;
5. verify the baseline before workload access;
6. monitor drift, contacts, owners, exceptions, spend, and findings;
7. quarantine or suspend safely during incidents or abandonment;
8. retain and export required evidence and data;
9. remove cross-account dependencies;
10. close through the provider's documented process;
11. track the post-closure and retention period.

An unused account with valid credentials and forgotten resources is an attack surface and a continuing bill.

## 24. Make exceptions expire

Governance must support justified exceptions without turning them into permanent invisible policy.

Every exception should record:

- the exact control and affected accounts;
- business and technical reason;
- risk owner;
- compensating controls;
- approval evidence;
- start and expiration dates;
- monitoring requirements;
- removal or renewal test.

Place exceptional accounts in a deliberate OU only when they share a real control model. Do not create an ungoverned “miscellaneous” OU.

## 25. Practical model: validate a governance plan

This standard-library model checks a proposed organization without contacting AWS. It catches structural omissions; it does not prove that deployed accounts match the proposal.

Save as `test_governance_plan.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import unittest


REQUIRED_TAGS = {
    "org:cost-center",
    "org:data-classification",
    "org:environment",
    "org:technical-owner",
    "org:workload-id",
}


@dataclass(frozen=True)
class Workload:
    name: str
    environment: str
    minimum_azs: int


@dataclass(frozen=True)
class Account:
    name: str
    kind: str
    ou: str
    owner: str
    cost_owner: str
    enabled_regions: frozenset[str]
    quota_reviewed_regions: frozenset[str]
    monthly_budget: int
    workloads: tuple[Workload, ...] = ()

    def validate(self, approved_regions: frozenset[str]) -> None:
        if not self.owner.strip() or not self.cost_owner.strip():
            raise ValueError(f"{self.name} lacks accountable owners")
        if self.monthly_budget <= 0:
            raise ValueError(f"{self.name} lacks a positive budget")
        unapproved = self.enabled_regions - approved_regions
        if unapproved:
            raise ValueError(f"{self.name} enables unapproved Regions: {unapproved}")
        missing_reviews = self.enabled_regions - self.quota_reviewed_regions
        if missing_reviews:
            raise ValueError(f"{self.name} lacks quota review: {missing_reviews}")
        environments = {workload.environment for workload in self.workloads}
        if "production" in environments and len(environments) > 1:
            raise ValueError(f"{self.name} mixes production and non-production")
        for workload in self.workloads:
            if workload.environment == "production" and workload.minimum_azs < 2:
                raise ValueError(f"{workload.name} lacks multi-AZ intent")


@dataclass(frozen=True)
class RegionDecision:
    name: str
    service_fit: str
    data_location: str
    latency: str
    recovery_role: str
    cost_owner: str

    def validate(self) -> None:
        evidence = (
            self.service_fit,
            self.data_location,
            self.latency,
            self.recovery_role,
            self.cost_owner,
        )
        if any(not value.strip() for value in evidence):
            raise ValueError(f"Region {self.name} lacks decision evidence")


@dataclass(frozen=True)
class EmergencyPath:
    account: str
    independent_failure: str
    activation_owner: str
    target_role: str
    last_tested: date

    def validate(self, today: date) -> None:
        required = (
            self.account,
            self.independent_failure,
            self.activation_owner,
            self.target_role,
        )
        if any(not value.strip() for value in required):
            raise ValueError("emergency path is incomplete")
        if today - self.last_tested > timedelta(days=90):
            raise ValueError("emergency path test is stale")


@dataclass(frozen=True)
class GovernancePlan:
    accounts: tuple[Account, ...]
    region_decisions: tuple[RegionDecision, ...]
    required_tags: frozenset[str]
    management_account: str
    emergency_path: EmergencyPath

    def validate(self, today: date) -> None:
        names = [account.name for account in self.accounts]
        if len(names) != len(set(names)):
            raise ValueError("account names must be unique")
        by_name = {account.name: account for account in self.accounts}
        if self.management_account not in by_name:
            raise ValueError("management account is not inventoried")
        management = by_name[self.management_account]
        if management.kind != "management":
            raise ValueError("declared management account has wrong kind")
        if management.workloads:
            raise ValueError("management account contains workloads")
        if not any(account.kind == "policy-staging" for account in self.accounts):
            raise ValueError("plan lacks a policy-staging account")
        missing_tags = REQUIRED_TAGS - self.required_tags
        if missing_tags:
            raise ValueError(f"tag schema is incomplete: {missing_tags}")

        approved_regions = frozenset(
            decision.name for decision in self.region_decisions
        )
        if not approved_regions:
            raise ValueError("plan has no approved Regions")
        for decision in self.region_decisions:
            decision.validate()
        for account in self.accounts:
            account.validate(approved_regions)

        if self.emergency_path.account not in by_name:
            raise ValueError("emergency account is not inventoried")
        if by_name[self.emergency_path.account].kind != "emergency":
            raise ValueError("emergency path does not use emergency account")
        self.emergency_path.validate(today)


TODAY = date(2026, 11, 1)


def complete_plan() -> GovernancePlan:
    regions = frozenset({"us-east-2", "us-west-2"})
    return GovernancePlan(
        accounts=(
            Account(
                name="org-management",
                kind="management",
                ou="root",
                owner="cloud-governance",
                cost_owner="finance-platform",
                enabled_regions=regions,
                quota_reviewed_regions=regions,
                monthly_budget=500,
            ),
            Account(
                name="policy-test",
                kind="policy-staging",
                ou="Policy-Staging",
                owner="cloud-governance",
                cost_owner="platform-engineering",
                enabled_regions=regions,
                quota_reviewed_regions=regions,
                monthly_budget=100,
            ),
            Account(
                name="payments-prod",
                kind="workload",
                ou="Workloads-Prod",
                owner="payments-on-call",
                cost_owner="payments-product",
                enabled_regions=regions,
                quota_reviewed_regions=regions,
                monthly_budget=10000,
                workloads=(Workload("payments", "production", 3),),
            ),
            Account(
                name="emergency-operations",
                kind="emergency",
                ou="Security",
                owner="security-operations",
                cost_owner="security-platform",
                enabled_regions=frozenset({"us-east-2"}),
                quota_reviewed_regions=frozenset({"us-east-2"}),
                monthly_budget=100,
            ),
        ),
        region_decisions=(
            RegionDecision(
                name="us-east-2",
                service_fit="all required services and instance types verified",
                data_location="approved for workload data",
                latency="meets customer objective",
                recovery_role="primary",
                cost_owner="payments-product",
            ),
            RegionDecision(
                name="us-west-2",
                service_fit="recovery service parity verified",
                data_location="approved for encrypted replica",
                latency="recovery objective accepts added latency",
                recovery_role="recovery",
                cost_owner="payments-product",
            ),
        ),
        required_tags=frozenset(REQUIRED_TAGS),
        management_account="org-management",
        emergency_path=EmergencyPath(
            account="emergency-operations",
            independent_failure="IAM Identity Center unavailable",
            activation_owner="security-incident-commander",
            target_role="EmergencyOperationsRole",
            last_tested=TODAY - timedelta(days=30),
        ),
    )


class GovernancePlanTests(unittest.TestCase):
    def test_complete_plan_is_accepted(self) -> None:
        complete_plan().validate(TODAY)

    def test_management_account_rejects_workloads(self) -> None:
        plan = complete_plan()
        accounts = list(plan.accounts)
        account = accounts[0]
        accounts[0] = Account(
            name=account.name,
            kind=account.kind,
            ou=account.ou,
            owner=account.owner,
            cost_owner=account.cost_owner,
            enabled_regions=account.enabled_regions,
            quota_reviewed_regions=account.quota_reviewed_regions,
            monthly_budget=account.monthly_budget,
            workloads=(Workload("convenient-app", "production", 2),),
        )
        broken = GovernancePlan(
            accounts=tuple(accounts),
            region_decisions=plan.region_decisions,
            required_tags=plan.required_tags,
            management_account=plan.management_account,
            emergency_path=plan.emergency_path,
        )
        with self.assertRaisesRegex(ValueError, "contains workloads"):
            broken.validate(TODAY)

    def test_unapproved_region_is_rejected(self) -> None:
        plan = complete_plan()
        accounts = list(plan.accounts)
        account = accounts[2]
        accounts[2] = Account(
            name=account.name,
            kind=account.kind,
            ou=account.ou,
            owner=account.owner,
            cost_owner=account.cost_owner,
            enabled_regions=account.enabled_regions | {"eu-west-1"},
            quota_reviewed_regions=account.quota_reviewed_regions | {"eu-west-1"},
            monthly_budget=account.monthly_budget,
            workloads=account.workloads,
        )
        broken = GovernancePlan(
            accounts=tuple(accounts),
            region_decisions=plan.region_decisions,
            required_tags=plan.required_tags,
            management_account=plan.management_account,
            emergency_path=plan.emergency_path,
        )
        with self.assertRaisesRegex(ValueError, "unapproved Regions"):
            broken.validate(TODAY)

    def test_stale_emergency_test_is_rejected(self) -> None:
        plan = complete_plan()
        broken = GovernancePlan(
            accounts=plan.accounts,
            region_decisions=plan.region_decisions,
            required_tags=plan.required_tags,
            management_account=plan.management_account,
            emergency_path=EmergencyPath(
                account=plan.emergency_path.account,
                independent_failure=plan.emergency_path.independent_failure,
                activation_owner=plan.emergency_path.activation_owner,
                target_role=plan.emergency_path.target_role,
                last_tested=TODAY - timedelta(days=120),
            ),
        )
        with self.assertRaisesRegex(ValueError, "stale"):
            broken.validate(TODAY)


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

Run it:

```bash
python -m unittest -v test_governance_plan.py
```

The fixed date makes the example deterministic. In a real control, inject the current date, load account and Region state from read-only inventory, and compare the declared plan with deployed evidence. Do not let the validator modify an organization.

## 26. Review an account and Region proposal

Require a proposal to answer:

```text
account purpose and lifecycle:
workloads, environments, and data classes:
business, technical, security, and cost owners:
OU and inherited controls:
human, machine, and cross-account access:
approved and enabled Regions with decision evidence:
Availability Zone and Region recovery intent:
network and shared-service connections:
limiting quotas for steady state, deployment, and recovery:
budget, anomaly alerts, and response owner:
required tags and enforcement coverage:
logging, security evidence, and retention:
root recovery and emergency-access path:
baseline version, exceptions, expiration, and review date:
provisioning, quarantine, and closure workflow:
```

A proposed boundary is incomplete when its owner, cost, recovery, or retirement is “to be decided later.”

## Common Misconceptions

- “An OU contains resources.” OUs contain accounts; resources live in accounts.
- “An SCP grants approved services.” SCPs limit maximum permissions and never grant access.
- “AdministratorAccess bypasses an SCP.” An applicable SCP deny still limits a member-account principal.
- “SCPs protect the management account.” They do not restrict principals in the management account.
- “One account per team is always correct.” Boundaries should follow workload, control, data, cost, and consequence requirements, not only reporting lines.
- “Tags isolate production.” Tags provide metadata; separate accounts provide a stronger administrative boundary.
- “A second account is a disaster-recovery Region.” Accounts and Regions are independent design dimensions.
- “Consolidated billing assigns costs automatically.” It centralizes payment and data; internal allocation still needs owners and metadata.
- “A budget prevents overspend.” Budget information and notifications can lag and do not universally stop usage.
- “Break-glass access is an unmonitored admin user.” Emergency access should be narrow, protected, alerted, tested, temporary, and reviewed.

## Core Computer Science Concept

This design applies **hierarchical policy composition and fault containment**. An account inherits constraints from a tree of organization policies while remaining a separate resource and identity namespace. The effective behavior is the composition of local permission and inherited ceilings. Boundaries reduce the set of state one failure or authority can affect, but connections between boundaries reintroduce coupling.

## Engineering Connections

- Account separation extends process isolation from Part V to cloud administration.
- OU policy inheritance resembles configuration layering: broad defaults flow downward, while an explicit deny remains decisive.
- Policy staging applies Part VI's test-before-rollout discipline to governance code.
- Region and AZ planning extends Part VII's failure-domain reasoning beyond one container host or cluster.
- Quota inventories apply Chapter 90's capacity contracts to each account and Region.
- Account vending and closure are resource lifecycles, not one-time tickets.
- Budgets turn measured service into assigned operational feedback.

## From the Field

A company runs production, development, audit logs, and organization automation in one account. A developer's broad role is intended only for test resources, but a cleanup script selects instances using an inconsistent environment tag and deletes production capacity. The same account's API rate limit delays recovery, and the log destination is writable by the compromised role. Separate workload accounts, protected evidence, quota ownership, and tested cross-account deployment would not prevent every mistake, but they would sharply reduce the reachable state and preserve recovery evidence.

## Engineering Review

### What problem does this solve?

It turns AWS accounts, OUs, Regions, tags, quotas, budgets, billing, and emergency access into explicit boundaries with accountable owners and testable controls.

### Why was it designed this way?

Cloud resources are easy to create and connect. Hierarchical governance supplies consistent limits, while separate accounts and Regions contain distinct security, cost, quota, and failure consequences.

### When should I use it?

Use this model before the first production workload, whenever a new account or Region is proposed, and during recurring governance, cost, recovery, and access reviews.

### When should I avoid it?

Avoid copying a large enterprise OU diagram into a small environment without corresponding control needs. Preserve the important boundaries, then add accounts and OUs as consequences diverge.

### How does this make me a better engineer?

It teaches you to design administrative topology from authority, blast radius, failure, lifecycle, and cost instead of accepting a collection of accounts as accidental structure.

### How does this reduce waste?

It prevents abandoned accounts, duplicated controls, anonymous spend, unused Regions, surprise quotas, unsafe organization-wide policy changes, and recovery paths that exist only on paper.

## Handbook Principle #91

> A cloud boundary is useful only when its authority, blast radius, cost, and recovery path are explicit.

## Practical Observation

Run the governance-plan tests, then model a small organization with one production workload. Draw every cross-account role, network, log flow, payer relationship, and recovery dependency. Attempt to explain the blast radius of a compromised workload administrator, a mistaken root-level SCP, a failed identity provider, a quota exhausted during recovery, and an abandoned account. Any answer that crosses an unnamed boundary reveals missing governance.

## Looking Ahead

Accounts and SCPs establish coarse boundaries, but applications and operators still need precise authorization inside them. Chapter 92 builds the IAM model from principals, policies, roles, sessions, evaluation logic, temporary credentials, and auditable least privilege.

## References

- [AWS Account Management — What is an AWS account?](https://docs.aws.amazon.com/accounts/latest/reference/)
- [AWS Organizations — Best practices for a multi-account environment](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_best-practices.html)
- [AWS Whitepaper — Organizing Your AWS Environment Using Multiple Accounts](https://docs.aws.amazon.com/whitepapers/latest/organizing-your-aws-environment/organizing-your-aws-environment.html)
- [AWS Organizations — Service control policies](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html)
- [AWS Organizations — Best practices for the management account](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_best-practices_mgmt-acct.html)
- [AWS Account Management — Enable or disable AWS Regions](https://docs.aws.amazon.com/accounts/latest/reference/manage-acct-regions.html)
- [AWS Regions and Availability Zones](https://docs.aws.amazon.com/global-infrastructure/latest/regions/aws-regions-availability-zones.html)
- [AWS Tagging — Best practices and strategies](https://docs.aws.amazon.com/tag-editor/latest/userguide/best-practices-and-strats.html)
- [AWS Billing — Consolidating billing for AWS Organizations](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/consolidated-billing.html)
- [AWS Cost Management — Managing your costs with AWS Budgets](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html)
- [AWS IAM Identity Center — Set up emergency access to the AWS Management Console](https://docs.aws.amazon.com/singlesignon/latest/userguide/emergency-access.html)
