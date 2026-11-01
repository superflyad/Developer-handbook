# Chapter 90 — Cloud Computing, Shared Responsibility, and Service Models

Moving a database from a host you patch to a managed API can remove operating-system work. It does not decide who classifies the data, grants access, chooses failure domains, tests restore, watches quotas, or pays for idle capacity.

The central idea is:

> Cloud services move implementation boundaries; they do not erase engineering ownership. Name every retained responsibility, failure mode, quota, and meter before calling a capability managed.

## 1. Cloud computing is an operating model

NIST describes cloud computing through five essential characteristics:

- on-demand self-service;
- broad network access;
- resource pooling;
- rapid elasticity;
- measured service.

The useful shift is not merely “someone else's computer.” Infrastructure and platforms become programmable, pooled services that can be provisioned, changed, measured, and released through interfaces.

That creates leverage and new failure modes:

- configuration can change globally in seconds;
- capacity can expand without a purchase order and contract without a disposal project;
- credentials can create expensive or public resources;
- API rate limits and quotas become architectural constraints;
- metered usage turns inefficient behavior into a continuing bill;
- provider control planes become dependencies for change and recovery.

Cloud engineering applies software discipline to those interfaces.

## 2. On-demand does not mean unconstrained

An API request to create a resource still depends on:

- authenticated and authorized identity;
- valid configuration and policy;
- service and account quotas;
- regional capacity;
- control-plane availability;
- dependency readiness;
- billing and account state;
- asynchronous workflow completion.

The accepted request and usable resource are different states. Design idempotent automation, wait for explicit conditions, preserve operation identity, and expose terminal failure rather than retrying every error forever.

Part VI's automation and distributed-systems rules apply directly to cloud control planes.

## 3. Resource pooling changes visibility, not accountability

Consumers generally do not select or inspect the provider's individual physical hosts. The provider pools infrastructure and exposes logical resources under an isolation contract.

The consumer still chooses:

- service and deployment model;
- account, tenant, project, and region;
- data placement and access;
- logical network exposure;
- workload identity;
- redundancy and recovery;
- configuration and software above the service boundary;
- evidence needed to verify the provider contract.

Do not build controls that require physical details the service does not promise. Do not infer isolation properties the service has not documented.

## 4. Elasticity is a feedback loop

Elasticity means capacity can expand and contract with demand. It does not mean capacity appears instantly, scales without limits, or makes the application stateless.

A complete scaling loop includes:

```text
demand -> measured signal -> decision -> API request -> provisioning delay
       -> readiness -> traffic or work assignment -> later scale-in
```

The workload must tolerate:

- detection and provisioning lag;
- cold caches and initialization;
- quota or capacity denial;
- concurrent instances;
- duplicate work during ambiguous failure;
- termination and draining;
- a minimum capacity floor;
- cost during overshoot.

Queues, admission control, load shedding, and graceful degradation often matter more than a faster scaling rule.

## 5. Measured service creates a cost data plane

Cloud usage is metered across dimensions such as time, requests, bytes, operations, provisioned capacity, licenses, addresses, logs, or data transfer.

For every service, record:

- unit and price dimensions;
- payer and cost owner;
- expected baseline and peak usage;
- free tier or commitment assumptions;
- minimum billing granularity;
- storage and retention growth;
- ingress, egress, and cross-boundary transfer;
- idle and orphaned-resource behavior;
- budget and anomaly signals;
- delay between usage, billing data, and alert.

Pay-as-you-go is a charging mechanism, not an assurance that every charge reflects useful work.

## 6. Service models move the managed boundary

The IaaS, PaaS, and SaaS categories describe how much of the stack the provider operates.

| Model | Provider supplies | Consumer still controls or owns |
| --- | --- | --- |
| IaaS | Fundamental compute, storage, network, facilities, and virtualization | Guest OS, patches above the hypervisor, application, logical configuration, identity, data, resilience, and cost |
| PaaS | Managed application platform and underlying infrastructure | Deployed code or data, application configuration, identities, integration, scaling policy, recovery objectives, and cost |
| SaaS | Provider-operated application and infrastructure | Tenant configuration, users, data handling, integrations, retention, export, legal use, and business continuity |

Real products can combine models. Classify each capability instead of labeling an entire architecture once.

More abstraction usually reduces low-level operation and increases dependence on provider APIs, service behavior, supported versions, pricing, and migration paths.

## 7. IaaS preserves the broadest consumer control

With infrastructure services, the consumer often controls guest operating systems, runtime software, network configuration, and application data.

That permits specialized workloads and familiar operating models, but retains duties including:

- guest patching and hardening;
- image lifecycle;
- process supervision;
- backup and restore;
- scaling and replacement;
- host-level observability exposed by the service;
- network and identity configuration;
- license compliance;
- capacity and cost optimization.

The provider operating the facilities and virtualization layer does not patch your guest or correct an over-broad security rule.

## 8. PaaS trades host control for platform constraints

A platform service can manage operating systems, runtime patching, placement, replacement, or scaling machinery. The consumer normally remains responsible for:

- secure application code and dependencies;
- supported runtime selection and upgrades;
- environment and secret configuration;
- application identity and authorization;
- data correctness and migration;
- probe and scaling signals;
- performance within service limits;
- backup, export, and recovery contract;
- regional and cost design.

The platform may terminate, relocate, or update instances. Applications must honor its lifecycle instead of depending on undocumented host behavior.

## 9. SaaS shifts operation but retains business ownership

Using a provider-operated application can remove application deployment and infrastructure operation. The customer still decides:

- who receives tenant and administrative access;
- which data is entered and how it is classified;
- retention, deletion, export, and legal hold;
- integration credentials and downstream effects;
- tenant security settings;
- monitoring and audit review;
- provider outage and exit plans;
- user training and acceptable use;
- licensing and cost ownership.

“The vendor secures it” is incomplete when a customer administrator can expose data through a sharing setting or compromised identity.

## 10. Shared responsibility is service-specific

AWS describes security **of** the cloud as its responsibility for infrastructure, facilities, hardware, software, and networking that run AWS services. Security **in** the cloud varies with the service selected and the customer's configuration, data, identities, and software.

The same pattern applies beyond security:

- **reliability:** provider service availability plus customer architecture and recovery;
- **data:** provider storage durability mechanisms plus customer classification, access, versioning, backup, and deletion;
- **cost:** provider meters and pricing plus customer demand, configuration, retention, and ownership;
- **compliance:** provider evidence plus customer use, configuration, scope, and controls;
- **operations:** provider-managed layers plus customer observation, incident response, and change.

Read the exact service documentation. A general diagram cannot assign every control.

## 11. “Shared” needs two named actions

Avoid assigning a row merely to “shared.” Write both sides:

| Concern | Provider obligation | Consumer obligation | Verification |
| --- | --- | --- | --- |
| Physical media | Control facilities and media lifecycle | Select eligible service and region | Provider reports and contractual evidence |
| Stored data | Implement documented storage mechanisms | Classify, authorize, encrypt where required, back up, test restore | Configuration evidence and restore test |
| Identity | Operate authentication and authorization services | Configure federation, roles, conditions, and reviews | Access analysis and denied-path tests |
| Availability | Operate service to its published design | Deploy across required failure domains and remove single points | Failure exercise and objective measurement |
| Metering | Measure usage under documented dimensions | Attribute, budget, alert, and remove waste | Billing data and owner review |

If either action is blank, the control has an ownership gap.

## 12. Managed does not mean self-configuring

A managed service can operate hardware, hosts, replication machinery, or software updates while accepting unsafe customer configuration.

Common retained choices include:

- public versus private reachability;
- identity and resource policy;
- encryption key ownership and rotation;
- deletion protection and retention;
- backup windows and restore destinations;
- maintenance windows and supported versions;
- scaling floors and ceilings;
- logging and audit destinations;
- failure-domain placement;
- quotas and alarms.

Managed reduces work only when the team understands and accepts the service contract.

## 13. Control planes change resources

AWS commonly distinguishes a control plane from a data plane. Control-plane APIs create, describe, update, delete, and list resources. They can coordinate several underlying systems and asynchronous workflows.

Examples of control-plane work include:

- creating compute capacity;
- changing network or access policy;
- defining a data store;
- rotating configuration;
- updating service metadata;
- listing inventory.

Control-plane access is high authority. Protect it with federation, temporary credentials, least privilege, change review, audit, and bounded automation.

## 14. Data planes deliver the service's primary function

The data plane handles normal workload operations: processing requests, reading or writing data, moving packets, or serving names.

A running workload can sometimes continue while a control plane is impaired. Design critical paths for **static stability** where practical:

- pre-provision capacity needed to survive expected failure;
- avoid creating resources during every user request;
- cache stable configuration under a safe expiry policy;
- keep data-plane credentials valid through the recovery window;
- exercise operation when change APIs are unavailable;
- avoid deleting healthy capacity during ambiguous control-plane state.

Do not assume all services or operations separate these planes identically. Use service-specific documentation.

## 15. Recovery can depend on the control plane

Even if normal data-plane work continues, repair may require control-plane operations. Ask:

- Can traffic fail over without creating new resources?
- Is spare capacity already present in another failure domain?
- Can credentials remain valid without a refresh API?
- Can operators inspect enough state during impairment?
- Does autoscaling depend on the impaired plane?
- Will automation retry safely when the plane returns?
- Which emergency changes are impossible?

High availability requires both continued service and a viable recovery path.

## 16. Regions are explicit placement boundaries

An AWS Region is a separate geographic area. Many resources are regional and visible only when the client addresses the correct Region. Services, features, prices, quotas, and legal suitability can differ by Region.

Region selection should consider:

- users and latency;
- data residency and legal requirements;
- service and feature availability;
- failure and disaster-recovery objectives;
- price and transfer cost;
- quota readiness;
- support and operational coverage;
- dependency locations;
- carbon and organizational requirements where relevant.

AWS does not automatically replicate every regional resource to another Region. Replication and failover are workload decisions unless the service explicitly promises otherwise.

## 17. Availability Zones are fault-isolation locations

AWS Regions contain multiple Availability Zones. An AZ consists of one or more discrete data centers and is designed as an isolated location connected to other AZs in the Region through redundant low-latency networking.

Using an AZ is not the same as surviving its loss. A workload must place sufficient independent capacity, data, and dependencies across AZs and route around failure.

Check every component:

- compute and load balancing;
- databases and storage;
- caches and queues;
- NAT or egress paths;
- secrets and identity dependencies;
- observability and deployment systems;
- capacity to absorb failed-zone load.

One zonal dependency can reduce a nominally multi-AZ workload to one failure domain.

## 18. Multi-AZ is not automatically multi-Region

AZs in one Region address a different failure scope from Regions. Multi-Region design adds:

- data replication and consistency choices;
- global routing and failover detection;
- independent quotas and capacity;
- credential and configuration replication;
- deployment coordination;
- higher network and storage cost;
- legal and residency constraints;
- split-brain and recovery reconciliation;
- regular failover and failback testing.

Choose it from recovery objectives and business impact, not as a reflexive label of maturity.

## 19. Quotas are architectural limits

AWS quotas can apply per account, Region, resource, or API rate. Some are adjustable; others are fixed. Increase requests can require review and time.

Inventory before deployment:

- resource-count quotas;
- concurrent-execution quotas;
- request-rate and burst quotas;
- storage, address, rule, and policy-size quotas;
- quotas in every failover Region and account;
- adjustable maximum and approval lead time;
- current usage and forecast;
- monitoring threshold and owner.

A disaster plan that needs double capacity fails if the recovery account or Region has only steady-state quota.

## 20. Throttling is a normal control-plane response

Rate limits protect shared services. Clients must distinguish throttling from authorization, validation, conflict, capacity, and permanent quota errors.

Use:

- service-recommended exponential backoff with jitter;
- bounded attempts and elapsed time;
- SDK retry modes appropriate to the operation;
- idempotency tokens where supported;
- concurrency limits and work queues;
- metrics for attempts, throttle rate, latency, and final outcomes;
- quota increases only after demand and client behavior are understood.

Unbounded parallel retry can turn a brief throttle into a sustained outage and a larger bill.

## 21. Capacity is not guaranteed by an adjustable quota

A quota grants permission to request up to a value; it does not necessarily reserve physical capacity at the moment of need.

Separate:

- **quota:** administrative maximum;
- **reservation or commitment:** commercial or capacity construct under its service contract;
- **current supply:** what the provider can allocate now;
- **application headroom:** capacity already healthy and ready;
- **recovery capacity:** what remains after a failure domain is lost.

Critical workloads may need pre-provisioned headroom, reservations, diversified shapes, graceful degradation, or queued demand.

## 22. Metering requires ownership at creation time

Every provisioned resource should answer:

- Who owns it?
- Which workload, environment, and cost center use it?
- When can it be deleted?
- What is the expected spend?
- Which budget and anomaly monitor covers it?
- Who receives and acts on alerts?
- Which resources cannot be tagged and how are they allocated?

Tags can help allocation, automation, and access control, but support varies by service and billing dimension. Account boundaries and cost categories can cover charges that resource tags cannot.

Budget data and alerts can lag usage. Prevent expensive mistakes with quotas, policy, safe defaults, expiration automation, and pre-deployment estimation—not budgets alone.

## 23. Unit economics connect architecture to cost

Track cost per useful outcome, not only the monthly total:

```text
cost per request
cost per active tenant
cost per processed record
cost per retained gigabyte-month
cost per successful build
cost per recovery test
```

A lower bill caused by lost traffic is not optimization. Pair cost with availability, latency, throughput, durability, and quality.

Allocation has uncertainty. Document shared costs, discounts, taxes, support, marketplace charges, and delayed adjustments before comparing teams or architectures.

## 24. Managed services trade operational work for constraints

Potential benefits include:

- provider-operated hosts and software layers;
- built-in replication or backup mechanisms;
- standardized monitoring and APIs;
- faster provisioning;
- elastic capacity;
- reduced specialist on-call burden.

Potential costs include:

- service-specific limits and semantics;
- version and feature constraints;
- migration and data-egress work;
- less low-level visibility;
- provider control-plane dependency;
- pricing dimensions that reward a different access pattern;
- asynchronous or eventually consistent administration;
- portability and exit complexity.

Compare total ownership and risk for the actual workload, not feature-count parity with a self-managed product.

## 25. Reliability remains an end-to-end property

A provider service-level commitment does not equal workload availability. The workload can fail through:

- customer misconfiguration;
- one-AZ placement;
- exhausted quota;
- bad deployment or schema change;
- expired identity or certificate;
- downstream dependency failure;
- data corruption or deletion;
- DNS and network errors;
- control-plane dependence during recovery;
- application overload.

Define user-facing objectives, instrument them, and test failure and recovery across every owned layer.

## 26. Data ownership survives abstraction

For each data class, define:

- authoritative owner and steward;
- allowed accounts, Regions, and services;
- identity and network access;
- encryption and key ownership;
- retention, legal hold, and deletion;
- backup consistency and isolation;
- restore objective and test;
- replication and consistency;
- export format and provider exit;
- audit evidence;
- incident notification and response.

Provider durability protects against some media failures. It does not automatically protect against authorized deletion, logical corruption, compromised credentials, or an application writing bad data.

## 27. Observability must cross the service boundary

The provider can expose metrics, logs, events, audit records, health, status, and billing data. The consumer decides what to enable, retain, protect, correlate, and alert on.

Collect enough evidence to distinguish:

- application error;
- customer policy or configuration;
- quota or throttling;
- zonal or regional impairment;
- provider service event;
- identity denial;
- exhausted capacity;
- cost anomaly;
- control-plane versus data-plane failure.

Do not place the only logs for a failed service inside that service's failure domain.

## 28. Practical model: validate a responsibility register

This standard-library example rejects vague ownership and missing operational controls. It does not decide whether a provider's real contract satisfies your requirements.

Save as `test_cloud_contract.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
import unittest


REQUIRED_DOMAINS = {
    "access",
    "availability",
    "cost",
    "data",
    "incident",
    "patching",
    "recovery",
    "telemetry",
}
VAGUE_OWNERS = {"cloud", "managed", "provider", "shared", "someone"}


@dataclass(frozen=True)
class Responsibility:
    domain: str
    provider_action: str
    consumer_owner: str
    consumer_action: str
    verification: str

    def validate(self) -> None:
        if self.domain not in REQUIRED_DOMAINS:
            raise ValueError(f"unknown responsibility domain: {self.domain}")
        if not self.provider_action.strip():
            raise ValueError(f"{self.domain} lacks provider action")
        if self.consumer_owner.strip().lower() in VAGUE_OWNERS:
            raise ValueError(f"{self.domain} has vague consumer owner")
        if not self.consumer_action.strip():
            raise ValueError(f"{self.domain} lacks consumer action")
        if not self.verification.strip():
            raise ValueError(f"{self.domain} lacks verification")


@dataclass(frozen=True)
class Quota:
    name: str
    scope: str
    required_peak: int
    applied_value: int
    alarm_threshold: int
    owner: str

    def validate(self) -> None:
        if self.scope not in {"account", "global", "region", "resource"}:
            raise ValueError(f"invalid quota scope: {self.scope}")
        if self.applied_value < self.required_peak:
            raise ValueError(f"quota {self.name} cannot support required peak")
        if not 0 < self.alarm_threshold < self.applied_value:
            raise ValueError(f"quota {self.name} has invalid alarm threshold")
        if not self.owner.strip() or self.owner.lower() in VAGUE_OWNERS:
            raise ValueError(f"quota {self.name} lacks accountable owner")


@dataclass(frozen=True)
class CloudContract:
    service_model: str
    responsibilities: tuple[Responsibility, ...]
    quotas: tuple[Quota, ...]
    meter_owner: str
    critical_runtime_control_plane_dependency: bool
    control_plane_fallback: str

    def validate(self) -> None:
        if self.service_model not in {"IaaS", "PaaS", "SaaS"}:
            raise ValueError("service model must be IaaS, PaaS, or SaaS")
        seen = {item.domain for item in self.responsibilities}
        missing = sorted(REQUIRED_DOMAINS - seen)
        if missing:
            raise ValueError(f"missing responsibility domains: {', '.join(missing)}")
        if len(seen) != len(self.responsibilities):
            raise ValueError("responsibility domains must be unique")
        for item in self.responsibilities:
            item.validate()
        if not self.quotas:
            raise ValueError("at least one limiting quota must be recorded")
        for quota in self.quotas:
            quota.validate()
        if not self.meter_owner.strip() or self.meter_owner.lower() in VAGUE_OWNERS:
            raise ValueError("metering lacks accountable owner")
        if (
            self.critical_runtime_control_plane_dependency
            and not self.control_plane_fallback.strip()
        ):
            raise ValueError("critical control-plane dependency lacks fallback")


def complete_contract() -> CloudContract:
    responsibilities = tuple(
        Responsibility(
            domain=domain,
            provider_action=f"document and operate provider {domain} control",
            consumer_owner="workload-team",
            consumer_action=f"configure and test workload {domain} behavior",
            verification=f"quarterly {domain} evidence review",
        )
        for domain in sorted(REQUIRED_DOMAINS)
    )
    return CloudContract(
        service_model="PaaS",
        responsibilities=responsibilities,
        quotas=(
            Quota(
                name="regional-concurrency",
                scope="region",
                required_peak=80,
                applied_value=100,
                alarm_threshold=70,
                owner="platform-capacity",
            ),
        ),
        meter_owner="finops-owner",
        critical_runtime_control_plane_dependency=False,
        control_plane_fallback="pre-provisioned multi-zone capacity",
    )


class CloudContractTests(unittest.TestCase):
    def test_complete_contract_is_accepted(self) -> None:
        complete_contract().validate()

    def test_vague_managed_owner_is_rejected(self) -> None:
        contract = complete_contract()
        rows = list(contract.responsibilities)
        rows[0] = Responsibility(
            domain=rows[0].domain,
            provider_action=rows[0].provider_action,
            consumer_owner="managed",
            consumer_action=rows[0].consumer_action,
            verification=rows[0].verification,
        )
        broken = CloudContract(
            service_model=contract.service_model,
            responsibilities=tuple(rows),
            quotas=contract.quotas,
            meter_owner=contract.meter_owner,
            critical_runtime_control_plane_dependency=False,
            control_plane_fallback=contract.control_plane_fallback,
        )
        with self.assertRaisesRegex(ValueError, "vague"):
            broken.validate()

    def test_quota_below_recovery_peak_is_rejected(self) -> None:
        contract = complete_contract()
        broken_quota = Quota(
            name="regional-concurrency",
            scope="region",
            required_peak=120,
            applied_value=100,
            alarm_threshold=70,
            owner="platform-capacity",
        )
        broken = CloudContract(
            service_model=contract.service_model,
            responsibilities=contract.responsibilities,
            quotas=(broken_quota,),
            meter_owner=contract.meter_owner,
            critical_runtime_control_plane_dependency=False,
            control_plane_fallback=contract.control_plane_fallback,
        )
        with self.assertRaisesRegex(ValueError, "required peak"):
            broken.validate()

    def test_critical_control_plane_dependency_needs_fallback(self) -> None:
        contract = complete_contract()
        broken = CloudContract(
            service_model=contract.service_model,
            responsibilities=contract.responsibilities,
            quotas=contract.quotas,
            meter_owner=contract.meter_owner,
            critical_runtime_control_plane_dependency=True,
            control_plane_fallback="",
        )
        with self.assertRaisesRegex(ValueError, "lacks fallback"):
            broken.validate()


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

Run it:

```bash
python -m unittest -v test_cloud_contract.py
```

Replace the generic actions with exact service commitments, internal owners, evidence locations, regional quotas, recovery peaks, and metering dimensions. A passing schema proves completeness of the register, not correctness of its claims.

## 29. Review a cloud service before adoption

Produce this service card:

```text
capability and service model:
provider-managed layers:
consumer-managed layers:
security and compliance actions on both sides:
data ownership, location, encryption, backup, restore, export, deletion:
control-plane and data-plane operations:
runtime behavior during control-plane impairment:
regional, zonal, and global scope:
quotas, rates, capacity, and increase lead time:
elasticity signal, lag, floor, ceiling, and scale-in safety:
metering dimensions, baseline, peak, owner, budget, anomaly alert:
availability commitment and workload objective:
observability and audit evidence:
version, deprecation, migration, and exit path:
residual risks and accepted exceptions:
```

Review it again when the provider contract, service tier, region, workload, data class, price, or regulation changes.

## Common Misconceptions

- “Cloud means unlimited capacity.” Quotas, regional supply, rate limits, and provisioning time still constrain demand.
- “Managed means the provider owns security.” The provider owns defined layers; the consumer still owns identity, configuration, data, and application behavior.
- “Multi-AZ is automatic.” The workload must place every critical dependency and enough capacity across failure domains.
- “A service SLA is my application availability.” Customer architecture and dependencies can fail inside the provider commitment.
- “Pay-as-you-go eliminates waste.” Idle, orphaned, over-retained, and inefficient resources are still billed.
- “A quota increase reserves capacity.” Administrative permission and physical supply are different contracts.
- “Control-plane failure stops all data-plane work.” Some provisioned resources can continue; recovery and change paths may still be impaired.
- “SaaS removes data ownership.” Tenant access, retention, integration, export, deletion, and legal use remain customer decisions.

## Core Computer Science Concept

Cloud computing is **resource virtualization plus programmable control under contractual abstraction**. The provider implements hidden lower layers; the consumer composes exposed capabilities. Correctness depends on the interface contract, explicit ownership at the abstraction boundary, and feedback loops for capacity, reliability, security, and cost.

## Engineering Connections

- API-driven provisioning inherits Part VI's idempotency and retry rules.
- Regions and AZs extend Part VI's failure-domain and partial-failure models.
- Control and data planes mirror Chapter 88's separation of desired-state APIs from running workloads.
- Quotas and metering add administrative and economic limits to Chapter 86's resource model.
- Managed-service identity and network configuration retain Chapter 87's least-authority principle.
- Cost per useful outcome is another workload-level performance measure.

## From the Field

A team moves a database to a managed service and removes operating-system patching from its runbook. It also assumes backups, cross-zone recovery, and deletion protection are now automatic. An authorized migration deletes records, and the only retained backup shares the same account and credentials. The provider operated the database hosts correctly; the unassigned customer recovery controls caused the loss.

## Engineering Review

### What problem does this solve?

It identifies who owns security, reliability, data, quotas, recovery, observability, and cost when infrastructure and software layers are provided through managed APIs.

### Why was it designed this way?

Cloud providers can pool and automate lower layers efficiently, while consumers retain workload intent, configuration, data, identity, and business outcomes above the service contract.

### When should I use it?

Use this ownership model before adopting any IaaS, PaaS, SaaS, or managed service and during every architecture, incident, compliance, and cost review.

### When should I avoid it?

Avoid treating the three service-model labels as precise product specifications; inspect the actual service, Region, tier, and contract because real responsibility boundaries vary.

### How does this make me a better engineer?

It teaches you to reason from interfaces, failure domains, quotas, meters, and retained duties instead of treating abstraction as the disappearance of responsibility.

### How does this reduce waste?

It prevents duplicated operation, ownership gaps, unplanned quota failure, idle spend, fragile control-plane dependencies, unnecessary self-management, and managed services chosen without an exit path.

## Handbook Principle #90

> Every managed layer removes some work and exposes a new contract—write down both before depending on it.

## Practical Observation

Run the responsibility-register tests, then replace the generic PaaS row with one cloud service your team uses. Record exact provider and consumer actions, one limiting quota in every recovery Region, the data-plane behavior during control-plane impairment, and the metering owner. Reject “AWS,” “cloud,” or “shared” as an accountable internal owner.

## Looking Ahead

Cloud responsibility needs enforceable organizational boundaries. Chapter 91 treats AWS accounts, Organizations, organizational units, Regions, tags, quotas, budgets, and break-glass access as deliberate units of blast radius, authority, and cost ownership.

## References

- [NIST SP 800-145 — The NIST Definition of Cloud Computing](https://csrc.nist.gov/pubs/sp/800/145/final)
- [AWS Shared Responsibility Model](https://aws.amazon.com/compliance/shared-responsibility-model/)
- [AWS Regions and Availability Zones](https://docs.aws.amazon.com/global-infrastructure/latest/regions/aws-regions-availability-zones.html)
- [AWS Fault Isolation Boundaries — Control planes and data planes](https://docs.aws.amazon.com/whitepapers/latest/aws-fault-isolation-boundaries/control-planes-and-data-planes.html)
- [AWS Well-Architected Reliability Pillar — Understanding availability needs](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/understanding-availability-needs.html)
- [AWS Service Quotas User Guide](https://docs.aws.amazon.com/servicequotas/latest/userguide/intro.html)
- [AWS Well-Architected Framework — Manage demand and supply resources](https://docs.aws.amazon.com/wellarchitected/latest/framework/cost-mandem.html)
- [AWS Cost Management — Cost Anomaly Detection](https://docs.aws.amazon.com/cost-management/latest/userguide/getting-started-ad.html)
- [AWS Cost Management — Budgets](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html)
