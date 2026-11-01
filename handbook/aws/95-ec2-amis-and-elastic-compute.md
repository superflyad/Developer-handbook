# Chapter 95 — EC2, AMIs, and Elastic Compute

A virtual machine can run for years while operators patch it, copy files into it, and forget which changes were made. It appears stable until replacement is urgent and nobody can reproduce it. EC2 provides elastic virtual servers; the customer still owns the operating system and the path from image to replaceable capacity.

The central idea is:

> Define an instance as a versioned launch contract plus disposable runtime state. If replacement cannot recreate service safely, the server is not yet elastic.

## 1. EC2 is infrastructure as a service

An EC2 instance is a virtual server. AWS operates the facilities, physical hosts, hypervisor, and EC2 control plane. The customer still owns responsibilities including:

- AMI and operating-system selection;
- guest patching and hardening;
- instance role and application credentials;
- VPC placement and network policy;
- EBS configuration, encryption, backup, and deletion;
- application installation and startup;
- health, logs, metrics, and recovery;
- capacity, purchase model, and cost;
- replacement and retirement.

Root access inside the guest is powerful but does not administer the AWS host. Conversely, AWS control-plane permission can replace or terminate the guest without logging into it.

## 2. An instance is one realization of a contract

A complete launch contract names:

- AMI ID, owner, architecture, and provenance;
- allowed instance types;
- subnet and Availability Zone choices;
- security groups;
- instance profile;
- metadata-service options;
- block-device mappings;
- user data or bootstrap artifact;
- tags and ownership;
- purchase model and capacity assumptions;
- monitoring and health checks;
- termination and replacement behavior.

Store these settings in reviewed infrastructure code and a numbered launch-template version. An instance ID is runtime evidence, not the durable definition of the service.

## 3. Instance types are resource envelopes

An instance type selects a combination of:

- vCPUs and processor architecture;
- memory;
- network performance and packet capacity;
- EBS bandwidth and IOPS limits;
- local instance-store devices where offered;
- accelerators and specialized features;
- supported ENI and address density.

Family labels suggest a workload shape, but benchmarks decide fit. Measure application throughput, tail latency, memory pressure, disk queueing, network behavior, and cost under representative load.

Identify several compatible types when the workload permits. Flexibility can improve capacity availability and Spot diversification. Verify AMI architecture, kernel, drivers, virtualization, storage, and application licensing for every allowed type.

## 4. Vertical size is not an availability design

A larger instance can improve single-node capacity but also enlarges one failure unit. Compare:

- scale up versus scale out;
- per-node state and recovery time;
- load-balancing behavior;
- software licensing;
- quota and Regional supply;
- deployment and rollback granularity;
- cost at steady and peak demand.

Some workloads require large memory or specialized accelerators. Even then, define failure behavior and capacity replacement rather than assuming an expensive instance cannot fail.

## 5. AMIs are versioned boot artifacts

An Amazon Machine Image contains the information needed to boot an instance, including a root-volume template, launch permissions, and block-device mapping. AMI IDs are Regional.

Treat an AMI like a release artifact:

- build from declared inputs;
- patch and harden during a controlled pipeline;
- remove build credentials and temporary data;
- run security and functional tests;
- record source revision, build time, owner, and dependencies;
- copy deliberately to required Regions and accounts;
- promote an exact ID;
- deprecate and deregister through retention policy;
- retain or delete backing snapshots deliberately.

An image name is mutable human metadata. Pin the exact AMI ID and expected owner in each environment.

## 6. Image creation needs consistency

Creating an EBS-backed AMI produces snapshots of mapped EBS volumes. An application writing during snapshot creation can leave crash-consistent or application-inconsistent state unless the build process stops writes, flushes buffers, or uses application-aware procedures.

Golden images should usually contain operating-system and stable runtime dependencies, not mutable customer data. Test the image by launching a fresh instance, not by declaring the builder healthy.

Deregistering an AMI prevents new launches but does not terminate existing instances. Snapshot deletion and retention are separate lifecycle actions.

## 7. Launch templates preserve versioned parameters

An EC2 launch template stores launch parameters and supports numbered versions. Existing versions are immutable; changes produce a new version.

Pin a numbered version for controlled deployment. `$Latest` and `$Default` are convenient aliases but can change which configuration a later scale-out receives without changing the consuming declaration.

Review a new version as a unit. An AMI update can interact with instance type, user data, metadata options, role, storage, and health timing. A syntactically valid version is not a proven boot contract.

## 8. User data is bootstrap input, not a secret store

EC2 user data can supply shell scripts, cloud-init directives, or platform-specific startup instructions. On common Linux configurations it runs during the first launch boot by default, although behavior depends on the image and agent configuration.

Bootstrap should be:

- small and deterministic;
- idempotent where rerun is possible;
- bounded by timeouts and retries;
- observable through protected logs;
- explicit about failure;
- independent of one mutable external URL;
- safe when dependencies are temporarily unavailable.

Do not place passwords, access keys, private certificates, or bearer tokens in user data. Authorized APIs can expose user data, and it can be retained in instance or cloud-init state. Fetch secrets at runtime using the instance role and a dedicated secret service.

## 9. Separate baking from bootstrapping

Two extremes create problems:

- baking every environment value into an AMI produces many nearly identical images;
- installing the whole operating system and application at boot makes launches slow and dependent on external repositories.

A practical boundary is:

- **image:** patched OS, agents, runtime, application artifact or stable base;
- **launch template:** infrastructure-facing parameters;
- **bootstrap:** small environment binding and service registration;
- **runtime configuration:** versioned non-secret settings;
- **secret store:** current sensitive values retrieved by workload identity.

Measure launch-to-ready time and test repository, DNS, identity, and configuration failures.

## 10. Instance profiles deliver role credentials

An IAM role associated through an instance profile lets applications obtain temporary credentials from the Instance Metadata Service. AWS SDK provider chains retrieve and refresh them automatically.

Use one role per meaningful workload authority boundary. Do not place permanent access keys on disk or in the AMI. Avoid calling `AssumeRole` merely to re-assume the same role unless session tags or a narrowing session policy are actually required.

Anyone who can execute code as the workload may be able to use its role. Least privilege, application isolation, metadata protection, and egress controls remain necessary.

## 11. Protect the Instance Metadata Service

IMDS exposes instance metadata and, when a role is attached, renewable temporary credentials at a link-local endpoint. Require IMDSv2 unless a documented compatibility constraint prevents it.

IMDSv2 requires a token obtained through an HTTP `PUT`, then sends that token with metadata requests. Configure:

- `HttpTokens=required`;
- the smallest response hop limit compatible with the runtime;
- metadata endpoint enablement only when needed;
- instance-tag access disabled unless justified;
- account and AMI defaults plus launch-time enforcement.

Containers can affect the necessary hop limit. Do not raise it blindly; understand which network namespace needs metadata and prevent unrelated workloads from inheriting the node role.

IMDSv2 adds defense in depth against several proxy and SSRF paths. It does not make vulnerable code safe or prevent local privileged processes from using credentials.

## 12. EBS has an independent lifecycle

Amazon EBS provides zonal block volumes. A volume attaches to instances in the same Availability Zone, subject to type and attachment constraints.

For every volume define:

- purpose and data classification;
- AZ and attachment owner;
- volume type, size, IOPS, and throughput;
- encryption key and recovery authority;
- filesystem and mount behavior;
- snapshot consistency and schedule;
- restore test and objective;
- `DeleteOnTermination` behavior;
- monitoring, expansion, and retirement.

Stopping an instance does not stop EBS storage charges. Terminating an instance deletes only volumes whose mapping says to delete them.

## 13. Root and data volumes serve different lifecycles

An EBS-backed root volume commonly has `DeleteOnTermination=true` so replacement does not leave orphaned boot disks. Durable business data should normally live in a managed data service or a separately governed data volume with tested backup and recovery.

Persisting a root volume can help forensics or specialized recovery but also creates sensitive orphaned storage and continuing cost. Make persistence a reviewed exception with expiration.

Device names in the EC2 mapping do not always equal Linux device names under NVMe. Discover devices by stable identifiers, labels, or filesystem UUIDs rather than assuming enumeration order.

## 14. Instance store is local ephemeral capacity

Some instance types include physically attached instance-store volumes. They can provide high local performance, but their data does not survive instance termination and is lost on stop/start that moves the instance to another host.

Use instance store for reconstructible caches, scratch space, replicas, or checkpoints copied elsewhere. Never call data durable merely because it survived a reboot on the same host.

## 15. Placement changes correlated risk and performance

Placement groups influence physical placement:

- **cluster:** packs instances within one AZ for low-latency, high-throughput communication;
- **partition:** separates groups of distributed nodes across hardware partitions;
- **spread:** places a small number of critical instances on distinct hardware;
- other specialized strategies exist for supported needs.

Cluster placement improves proximity but concentrates zonal scope. Spread and partition strategies trade density and capacity flexibility for fault separation. Placement requests can fail when compatible capacity is unavailable.

Use placement only for a measured requirement and include restart and capacity behavior in recovery tests.

## 16. Purchase models separate capacity from discount

Common EC2 options include:

- **On-Demand:** usage pricing without a term commitment;
- **Savings Plans:** a usage-spend commitment that discounts eligible use;
- **Reserved Instances:** a term-based billing discount with scope and attributes;
- **Spot:** spare capacity that EC2 can interrupt;
- **Capacity Reservations:** reserved capacity in a specific AZ;
- **Dedicated options:** isolation or licensing-oriented host choices.

A discount is not always a capacity guarantee, and a capacity reservation is not automatically the cheapest billing model. Match financial commitment to measured baseline demand and capacity reservation to recovery or launch requirements.

## 17. Spot is an interruption contract

Spot Instances can be reclaimed. A two-minute interruption notice can occur, and a rebalance recommendation may arrive earlier but is not guaranteed to precede it.

Use Spot only when the workload can:

- retry or resume work;
- checkpoint outside the instance;
- drain traffic quickly;
- tolerate loss before any notice;
- diversify across compatible types and AZs;
- replace capacity through a fleet controller;
- preserve logs and progress externally.

Test interruption. A shutdown handler that has never run under a two-minute deadline is not recovery evidence.

## 18. Auto Scaling maintains declared capacity

An Auto Scaling group combines a launch definition with:

- minimum, desired, and maximum capacity;
- VPC subnets and AZs;
- health checks and grace periods;
- scaling policies or schedules;
- instance maintenance and termination behavior;
- optional mixed instance and purchase policies.

The group attempts to converge on desired capacity and replaces instances it considers unhealthy. It does not know whether business state was externalized correctly or whether a health endpoint represents real readiness.

Scale on a signal related to demand and saturation, not habit. CPU may be useful, irrelevant, or too late depending on the workload.

## 19. Health needs layers

Distinguish:

- EC2 system status;
- EC2 instance status;
- attached-volume status;
- process liveness;
- application readiness;
- dependency health;
- load-balancer target health;
- user and business outcomes.

An instance can be `running` while bootstrap failed. A process can be alive while it cannot serve requests. Configure warmup and grace periods from observed startup behavior, then alarm separately on startup failures so a replacement loop does not hide a broken image.

## 20. Replace instead of repairing drift

Immutable operation builds a new AMI or launch-template version, launches replacements, verifies them, drains old instances, and terminates them. Benefits include reproducibility, clean rollback inputs, and removal of hidden drift.

In-place patching can be appropriate for long-lived, stateful, licensed, or hard-to-replace systems. It requires:

- an approved patch baseline;
- staged rollout and maintenance windows;
- backup and restore evidence;
- reboot policy;
- application validation;
- failure and rollback procedure;
- compliance reporting.

Systems Manager Patch Manager automates parts of scanning and installation, but AWS does not test third-party patches for the workload. The application owner still validates outcomes.

## 21. Roll out with instance refresh

An Auto Scaling instance refresh can replace instances using a new desired configuration. Control:

- minimum and maximum healthy percentages;
- launch-before-terminate capacity;
- warmup;
- checkpoints and bake time;
- skip matching;
- alarms and automatic rollback;
- behavior for protected, standby, or unhealthy instances.

Rollback must refer to a known prior AMI and launch-template version. If schema or external state changed incompatibly, reverting compute alone may not restore service.

## 22. Keep state outside replaceable instances

Externalize:

- customer and transactional data;
- sessions that must survive replacement;
- durable job progress;
- configuration source of truth;
- logs and metrics;
- deploy and audit evidence;
- secrets;
- artifacts.

Local caches and temporary files may remain, but the service must define behavior when they disappear. Replacement testing reveals accidental state more reliably than documentation.

## 23. Observe boot and retirement

Collect enough evidence to answer:

- which AMI and launch-template version booted;
- which user-data or cloud-init stage failed;
- whether IMDS and role delivery work;
- when the application became ready;
- which health check triggered replacement;
- whether traffic drained;
- whether logs flushed;
- which volumes and interfaces remained;
- whether desired capacity recovered;
- which resources still incur cost.

Send critical logs off-instance continuously. A terminated root volume cannot be the only incident record.

## 24. Practical model: validate a launch contract

This standard-library model validates declared EC2 intent without contacting AWS. It catches missing identity, mutable version aliases, unsafe metadata, secret-bearing bootstrap, unencrypted volumes, weak replacement design, and incompatible Spot assumptions.

Save as `test_ec2_contract.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
import re
import unittest


AMI_PATTERN = re.compile(r"^ami-[0-9a-f]{17}$")
ACCOUNT_PATTERN = re.compile(r"^[0-9]{12}$")


@dataclass(frozen=True)
class Volume:
    name: str
    purpose: str
    encrypted: bool
    delete_on_termination: bool
    backup_policy: str

    def validate(self) -> None:
        if not self.encrypted:
            raise ValueError(f"{self.name} is not encrypted")
        if self.purpose == "root" and not self.delete_on_termination:
            raise ValueError("root volume would be orphaned")
        if self.purpose == "durable-data":
            if self.delete_on_termination:
                raise ValueError("durable data deletes with the instance")
            if not self.backup_policy.strip():
                raise ValueError("durable data lacks backup policy")


@dataclass(frozen=True)
class Ec2Contract:
    ami_id: str
    ami_owner: str
    launch_template_version: str
    instance_types: tuple[str, ...]
    availability_zones: tuple[str, ...]
    instance_profile: str
    imds_tokens: str
    imds_hop_limit: int
    user_data_contains_secret: bool
    bootstrap_idempotent: bool
    volumes: tuple[Volume, ...]
    minimum: int
    desired: int
    maximum: int
    health_check: str
    replacement_strategy: str
    purchase_model: str
    interruption_tolerant: bool
    state_externalized: bool

    def validate(self) -> None:
        if not AMI_PATTERN.fullmatch(self.ami_id):
            raise ValueError("AMI must be pinned to an exact ID")
        if not ACCOUNT_PATTERN.fullmatch(self.ami_owner):
            raise ValueError("AMI owner must be pinned")
        if not self.launch_template_version.isdecimal():
            raise ValueError("launch template must use a numbered version")
        if not self.instance_types:
            raise ValueError("at least one compatible instance type is required")
        if len(set(self.availability_zones)) < 2:
            raise ValueError("production capacity needs multiple AZs")
        if not self.instance_profile.strip():
            raise ValueError("instance profile is missing")
        if self.imds_tokens != "required":
            raise ValueError("IMDSv2 tokens must be required")
        if self.imds_hop_limit not in {1, 2}:
            raise ValueError("metadata hop limit needs explicit 1 or 2")
        if self.user_data_contains_secret:
            raise ValueError("user data contains a secret")
        if not self.bootstrap_idempotent:
            raise ValueError("bootstrap is not idempotent")
        if not self.volumes:
            raise ValueError("block-device lifecycle is missing")
        for volume in self.volumes:
            volume.validate()
        if not 0 <= self.minimum <= self.desired <= self.maximum:
            raise ValueError("Auto Scaling capacity bounds are invalid")
        if not self.health_check.strip():
            raise ValueError("application health check is missing")
        if self.replacement_strategy not in {"immutable-refresh", "staged-patch"}:
            raise ValueError("replacement or patch strategy is missing")
        if self.purchase_model == "spot" and not self.interruption_tolerant:
            raise ValueError("Spot workload is not interruption tolerant")
        if not self.state_externalized:
            raise ValueError("instance retains irreplaceable state")


def complete_contract() -> Ec2Contract:
    return Ec2Contract(
        ami_id="ami-0123456789abcdef0",
        ami_owner="123456789012",
        launch_template_version="7",
        instance_types=("m7g.large", "m8g.large"),
        availability_zones=("use2-az1", "use2-az2"),
        instance_profile="orders-web-role",
        imds_tokens="required",
        imds_hop_limit=1,
        user_data_contains_secret=False,
        bootstrap_idempotent=True,
        volumes=(Volume("root", "root", True, True, "rebuild from AMI"),),
        minimum=2,
        desired=4,
        maximum=12,
        health_check="HTTPS /ready plus dependency-safe startup",
        replacement_strategy="immutable-refresh",
        purchase_model="on-demand",
        interruption_tolerant=False,
        state_externalized=True,
    )


class Ec2ContractTests(unittest.TestCase):
    def test_complete_contract_is_accepted(self) -> None:
        complete_contract().validate()

    def test_mutable_launch_template_alias_is_rejected(self) -> None:
        contract = complete_contract()
        broken = Ec2Contract(
            **{**contract.__dict__, "launch_template_version": "$Latest"}
        )
        with self.assertRaisesRegex(ValueError, "numbered"):
            broken.validate()

    def test_secret_in_user_data_is_rejected(self) -> None:
        contract = complete_contract()
        broken = Ec2Contract(
            **{**contract.__dict__, "user_data_contains_secret": True}
        )
        with self.assertRaisesRegex(ValueError, "secret"):
            broken.validate()

    def test_unencrypted_volume_is_rejected(self) -> None:
        contract = complete_contract()
        broken = Ec2Contract(
            **{
                **contract.__dict__,
                "volumes": (Volume("root", "root", False, True, ""),),
            }
        )
        with self.assertRaisesRegex(ValueError, "not encrypted"):
            broken.validate()

    def test_spot_requires_interruption_tolerance(self) -> None:
        contract = complete_contract()
        broken = Ec2Contract(
            **{**contract.__dict__, "purchase_model": "spot"}
        )
        with self.assertRaisesRegex(ValueError, "interruption tolerant"):
            broken.validate()


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

Run it:

```bash
python -m unittest -v test_ec2_contract.py
```

The IDs are syntactically plausible examples only. A real verifier should obtain AMI owner and state, launch-template content, encryption, metadata options, group capacity, and current instances through authorized read-only inventory. It must not launch or terminate resources during validation.

## 25. Review an EC2 service

```text
workload, owners, account, Region, and data class:
AMI ID, owner, provenance, tests, age, and Regional copies:
numbered launch-template version and reviewed diff:
compatible instance types and measured bottlenecks:
subnets, AZ IDs, security groups, and placement strategy:
instance profile and exact permissions:
IMDS endpoint, token requirement, hop limit, and container boundary:
user data, external dependencies, timeout, retry, and failure evidence:
EBS and instance-store purpose, encryption, performance, backup, and deletion:
minimum, desired, maximum, warmup, and health semantics:
purchase mix, capacity assumptions, commitments, and interruption behavior:
immutable refresh or staged-patch workflow:
checkpoint, drain, rollback, and one-AZ-loss behavior:
external state, logs, metrics, and retirement evidence:
unit cost, idle policy, quotas, and orphan detection:
```

## Common Misconceptions

- “EC2 is just a server AWS patches.” The customer owns the guest OS and workload stack.
- “A running instance is ready.” EC2 state does not prove bootstrap or application health.
- “An AMI name pins a release.” Pin the Regional AMI ID and expected owner.
- “User data is secret.” It is bootstrap input and must not contain credentials.
- “IMDSv2 prevents all credential theft.” It is defense in depth, not application isolation.
- “Stopping an instance stops all charges.” EBS and other attached resources can continue billing.
- “Termination deletes every disk.” `DeleteOnTermination` controls each EBS mapping.
- “A Savings Plan reserves capacity.” Discount and capacity are different contracts.
- “Spot always gives two minutes.” Design for interruption and loss, not guaranteed cleanup time.
- “Auto Scaling makes an application stateless.” It replaces compute; the application must externalize state.

## Core Computer Science Concept

EC2 operation applies **declarative replication and leases over replaceable state**. A launch template and AMI describe the desired replica. Auto Scaling reconciles actual replicas toward capacity bounds. Temporary credentials and Spot capacity are leases with expiration or revocation behavior. Durable correctness depends on keeping authoritative state outside any one replica.

## Engineering Connections

- AMIs extend Part VII's immutable image model to virtual machines.
- User data follows Part VI's idempotency and bounded-retry rules.
- IMDS credentials apply Chapter 92's temporary-role model.
- ENI and EBS placement inherit Chapter 93's zonal boundaries.
- Auto Scaling is a desired-state controller like Chapter 88's orchestration model.
- Instance refresh applies Chapter 77's staged promotion, health gate, and rollback principles.
- Externalized state separates compute lifecycle from data lifecycle.

## From the Field

A team patches one production instance manually after an incident and never updates its AMI. Months later Auto Scaling replaces it from the old launch template. The replacement passes the EC2 status check but lacks the fix and serves bad responses. Versioned image creation, application readiness, immutable instance refresh, and a test that terminates any replica would have turned the emergency change into a reproducible release.

## Engineering Review

### What problem does this solve?

It defines how to select, launch, identify, store, patch, scale, replace, and pay for EC2 capacity without depending on manually curated machines or embedded credentials.

### Why was it designed this way?

EC2 separates reusable image and launch configuration from disposable runtime instances, allowing infrastructure controllers to replace capacity while storage and identity follow explicit lifecycles.

### When should I use it?

Use this model for every EC2 workload, image release, launch-template change, scaling policy, patch decision, purchase-model review, and instance retirement.

### When should I avoid it?

Avoid EC2 when a managed service meets the workload contract with materially less guest, scaling, patch, and recovery ownership. Abstraction is valuable when its retained responsibilities are understood.

### How does this make me a better engineer?

It teaches you to design a machine from reproducible inputs, bounded identity, explicit storage, measurable health, and replacement behavior rather than from its current in-place condition.

### How does this reduce waste?

It reduces snowflake repair, idle over-sizing, orphaned volumes, permanent keys, slow bootstrap, unused commitments, fragile Spot adoption, and rollouts that replace healthy capacity without proof.

## Handbook Principle #95

> A virtual machine becomes elastic only when its identity, data, health, and replacement are designed before it boots.

## Practical Observation

Run the launch-contract tests, then model one existing server. Mark every file that cannot disappear, every boot dependency, every credential source, and every resource that still bills after stop or termination. If terminating a test replica changes business truth or destroys the only diagnostic evidence, move that state or redesign its recovery before calling the service replaceable.

## Looking Ahead

Replaceable instances still need stable ingress, health-aware distribution, global naming, and edge delivery. Chapter 96 connects Elastic Load Balancing, Route 53 routing and health, and CloudFront caching into one request path with explicit origin, failure, TLS, and cache boundaries.

## References

- [Amazon EC2 — Instances and instance types](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Instances.html)
- [Amazon EC2 — Instance state changes](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-lifecycle.html)
- [Amazon EC2 — AMI lifecycle](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ami-lifecycle.html)
- [Amazon EC2 — Launch templates](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-launch-templates.html)
- [Amazon EC2 — User data](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/user-data.html)
- [Amazon EC2 — Configure instance metadata options](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-options.html)
- [Amazon EC2 — Retrieve role credentials from instance metadata](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-metadata-security-credentials.html)
- [Amazon EBS — EBS volume lifecycle](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-volume-lifecycle.html)
- [Amazon EC2 — Placement groups](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/placement-groups.html)
- [Amazon EC2 — Billing and purchasing options](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-purchasing-options.html)
- [Amazon EC2 — Spot best practices](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/spot-best-practices.html)
- [Amazon EC2 Auto Scaling — Replace instances](https://docs.aws.amazon.com/autoscaling/ec2/userguide/ec2-auto-scaling-group-replacing-instances.html)
- [AWS Systems Manager — Patch Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/patch-manager.html)
