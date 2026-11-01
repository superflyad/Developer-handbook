# Chapter 103 — ECS, EKS, ECR, and Container Platforms on AWS

A container image can run on a laptop, an ECS task, or a Kubernetes Pod. That does not make those environments operationally equivalent. The scheduler, identity model, network attachment, health protocol, rollout controller, node owner, storage, and upgrade burden determine whether the same image becomes a reliable service.

The central idea is:

> Promote one immutable image by digest, then choose the smallest orchestration platform whose ownership and control surface match the workload.

## 1. Separate artifact, workload, and platform

A container system has three distinct layers:

- **Artifact:** image layers, manifest, digest, signatures, provenance, and vulnerability findings.
- **Workload:** command, ports, resources, health, identity, configuration, secrets, storage, replicas, and shutdown behavior.
- **Platform:** scheduler, compute capacity, network integration, rollout, scaling, upgrades, observability, and policy.

Do not describe a deployment as “a Docker container on AWS.” Record:

- source commit, build identity, image digest, and supported architecture;
- repository owner, retention, scan, signing, and replication policy;
- ECS task definition or Kubernetes workload version;
- task, Pod, and node identities;
- compute mode and who patches it;
- subnets, security groups or network policies, ports, and ingress;
- CPU, memory, ephemeral storage, and persistent volume requirements;
- health, graceful termination, rollout, rollback, and disruption budget;
- minimum capacity, scaling signal, quotas, logs, metrics, and cost owner.

Portability comes from an explicit workload contract, not from the image format alone.

## 2. Choose the scheduler before its features

| Platform | Best fit | Customer still owns |
| --- | --- | --- |
| ECS on Fargate | AWS-native services and jobs with minimal host management | image, task, identity, network, rollout, scaling, and cost |
| ECS on EC2 | ECS with instance choice, host control, accelerators, or high sustained utilization | all ECS workload concerns plus instances, AMIs, capacity, patching, and bin packing |
| ECS Managed Instances | ECS needing more instance flexibility with AWS managing more capacity operations | workload design, compatible capacity strategy, identity, rollout, and remaining shared duties |
| EKS Auto Mode or EKS on Fargate | Kubernetes APIs with more managed data-plane responsibility | Kubernetes workloads, policy, identity, networking intent, upgrades within the documented boundary |
| EKS with managed or self-managed nodes | Kubernetes ecosystem and maximum data-plane control | cluster add-ons, workloads, nodes to varying degrees, upgrades, security, and platform operations |

Start with ECS on Fargate when an AWS-hosted application needs ordinary containers but not Kubernetes APIs or host control. Choose ECS on EC2 only for a measured need such as GPU, specialized instance, daemon, privileged or unsupported Fargate behavior, or sustained economics.

Choose EKS when Kubernetes compatibility, APIs, operators, admission controls, ecosystem tooling, or an established Kubernetes platform team create concrete value. “We might be multicloud later” rarely pays for Kubernetes day-two work today.

AWS adds platform modes over time—currently including ECS Managed Instances and EKS Auto Mode. Re-evaluate current responsibility tables rather than assuming only the older EC2-versus-Fargate choice exists.

## 3. ECR stores content-addressed artifacts

Amazon ECR repositories store OCI-compatible container artifacts. An image digest identifies manifest content; a tag is a human-readable pointer. Deploy by digest:

```text
123456789012.dkr.ecr.us-east-1.amazonaws.com/orders@sha256:4b6c...
```

A mutable `production` or `latest` tag can point to different bytes between rollout, scale-out, and incident recovery. Enable tag immutability for release tags or use carefully scoped exclusions only where a workflow truly needs mutation. Record both a useful source tag and the resolved digest.

Repository policies control cross-account pulls and pushes. Registry authentication does not replace IAM authorization, and an ECR login token should not be treated as a long-lived secret. Build systems need push access; runtime execution roles normally need only pull actions for intended repositories.

Configure encryption, ownership tags, and cross-Region or cross-account replication from recovery and deployment requirements. Replication is not proof that a digest has passed the destination environment's policy checks.

## 4. Build once and attach evidence

A safe image pipeline:

1. builds from a pinned base image and locked dependencies;
2. runs unit, integration, and container-structure tests;
3. produces an SBOM and provenance tied to the digest;
4. scans operating-system and language packages;
5. signs or attests according to policy;
6. pushes once to a controlled repository;
7. promotes the same digest through environments;
8. continuously reevaluates deployed digests as vulnerability data changes.

ECR basic scanning finds operating-system vulnerabilities on push or demand. Enhanced scanning integrates with Amazon Inspector for operating-system and language packages and can update findings continuously. A clean scan is time-bound evidence, not permanent safety.

Define severity policy with exploitability, exposure, fix availability, exceptions, owner, and deadline. Blocking every unfixed low-severity finding encourages bypasses; ignoring a critical reachable vulnerability because it appeared after deployment is equally unsafe.

Never bake credentials, environment configuration, SSH keys, or customer data into layers. Deleting a tag does not immediately prove sensitive bytes disappeared from every cache, replica, export, or base image.

## 5. Retention must preserve rollback

ECR lifecycle policies can expire or archive matching images. Preview a policy before applying it and protect:

- every digest deployed in any active environment;
- the last known good rollback set;
- images required by disaster recovery;
- evidence retained for investigation or compliance;
- base images still used by supported releases.

Tag-based retention can fail when tags move or are absent. Inventory actual task definitions, Kubernetes manifests, aliases, and deployment records by digest before expiration.

Keep enough old artifacts to roll back code while maintaining database and event compatibility. Retaining an image whose runtime, certificate, schema, or secret no longer works is not a tested rollback.

## 6. An ECS task definition is a versioned workload blueprint

An ECS task definition describes one or more containers that should be placed together. It includes image, command, CPU and memory, ports, environment, secrets, logging, health, volumes, network mode, compatibility, task role, and task execution role. Registering a change creates a new numbered revision.

Containers in one task share a lifecycle and, with `awsvpc`, a network namespace through the task interface. Put a sidecar in the same task only when it must scale, deploy, and fail with the application. A log router or local proxy can fit; an independently owned database cannot.

Mark only workload-critical containers as essential. If an essential container exits, ECS stops the task. Define container dependency and startup ordering only where necessary; ordering does not prove readiness.

Use a read-only root filesystem where compatible, drop Linux capabilities, run as a non-root user, and avoid privileged mode. Verify the selected capacity mode supports every task-definition feature.

## 7. Tasks run once; services maintain desired state

An ECS **task** is one instantiation of a task definition. Use standalone tasks for bounded jobs whose completion, retry, uniqueness, and output are owned elsewhere.

An ECS **service** maintains a desired number of tasks and replaces tasks that stop. Use it for long-running stateless applications and workers. A service can integrate with load balancers, service discovery, auto scaling, capacity providers, and rolling deployments.

Replacement is not recovery for state stored only in a container filesystem. Persist authoritative state in a managed data service or explicitly mounted durable volume. Make jobs idempotent because a scheduler, operator, or workflow may start them more than once.

Desired count is not availability. Spread tasks across Availability Zones, verify capacity in each, keep a minimum that tolerates one task or zone loss, and test replacement while a deployment is also consuming surge capacity.

## 8. Capacity providers express where tasks run

Modern ECS designs use capacity-provider strategies to select Fargate, Fargate Spot, Auto Scaling group capacity, or ECS Managed Instances. A strategy can set a base and weighted distribution.

Fargate removes customer node provisioning and patching. It supplies task-sized compute with a supported set of CPU, memory, storage, operating-system, and platform features. It is a strong default when those constraints fit.

EC2 capacity gives instance selection, accelerators, host-level controls, local storage choices, and potentially better economics at stable utilization. The team then owns AMI updates, ECS agent compatibility, instance draining, Auto Scaling groups, capacity reservations, host monitoring, and unused capacity.

Spot capacity can reduce cost but can disappear. Mix capacity types only when the service has interruption handling, sufficient baseline, distribution across failure domains, and rapid replacement. A capacity strategy cannot make a singleton stateful task interruption-safe.

## 9. Resource reservations make placement predictable

Set CPU and memory from load tests. Requests or reservations inform placement; hard limits protect neighbors but can terminate a container under memory pressure. Monitor working set, throttling, garbage collection, latency, and out-of-memory exits.

Over-reserving wastes capacity and money. Under-reserving creates contention, eviction, failed placement, or performance instability. Include sidecars in the task or Pod budget.

For EC2-backed schedulers, bin packing improves utilization but can concentrate replicas on one host. Placement spread, distinct-instance constraints, topology rules, and capacity headroom trade efficiency for fault isolation. Measure the consequence of losing the fullest node.

Ephemeral disk is bounded and replaceable. Cap logs and temporary files, stream logs out, and alert before disk pressure stops tasks or nodes.

## 10. Give each workload its own AWS identity

ECS separates two roles:

- The **task execution role** lets the ECS agent or Fargate perform startup operations such as pulling an ECR image, fetching referenced secrets, and sending logs.
- The **task role** supplies temporary credentials to application containers for their AWS API calls.

Do not grant application database or S3 access to the execution role, and do not make every task inherit a broad EC2 instance profile. Create narrow task roles by workload and prevent containers from reaching unintended instance credentials on EC2 hosts.

EKS needs the same separation. Node roles allow kubelet, networking, image pull, and node operations. Pods should use EKS Pod Identity or IAM roles for service accounts rather than borrowing the node role. Pod Identity maps an IAM role to a Kubernetes service account but has documented platform restrictions; verify compute compatibility and isolate instance metadata.

Containers share a kernel on ordinary nodes and are not a complete security boundary. Identity, pod security, seccomp, capabilities, node isolation, and runtime controls provide defense in depth.

## 11. Secrets are injected snapshots unless refreshed

Reference Secrets Manager or Parameter Store values through supported task or Pod mechanisms. Do not place secret values directly in an ECS task definition, Kubernetes manifest, image, or ordinary environment file; anyone able to describe those resources may read them.

Environment injection usually captures a value at task or Pod start. Secret rotation does not magically update process memory. Define whether the application fetches and caches dynamically, uses a sidecar or CSI integration, or receives a rolling restart after rotation. Support an overlap in which old and new credentials both work long enough for rollout.

Keep the startup identity that retrieves a secret separate from the runtime identity where the platform requires it. Scope secret ARN and KMS permissions, avoid logging environment dumps, and test a denied or unavailable secret path.

Non-secret configuration should still be versioned. A changed endpoint, feature flag, or log level can alter behavior as much as code.

## 12. `awsvpc` gives each ECS task a network identity

In `awsvpc` mode, each ECS task receives an elastic network interface and private IP with selected security groups. Containers in the task communicate over `localhost`. This aligns network policy with the task rather than a shared host port.

Place tasks in private subnets across Availability Zones. Public ingress normally terminates at an ALB or NLB. Provide outbound AWS service access through VPC endpoints when appropriate and internet egress through a deliberate NAT or proxy path. ECS on EC2 tasks in `awsvpc` mode do not gain internet merely by using a public subnet.

Plan subnet address space, ENI quotas, EC2 ENI density, NAT ports, DNS, and target registration. A service can be unable to scale because no task IPs remain even when CPU capacity is abundant.

For `awsvpc` targets, load-balancer target type is `ip`, not `instance`. Security-group rules must permit the load balancer to reach the container port and permit health checks without exposing the task directly to the internet.

## 13. Health has startup, readiness, and liveness meanings

A process can be running but not ready for traffic. Define:

- **startup:** dependencies loaded and initialization can complete within its allowance;
- **readiness:** this instance should receive new work now;
- **liveness:** the process cannot recover without restart;
- **deep dependency health:** an operator signal, not necessarily a reason to restart every replica.

ECS combines container health and load-balancer or discovery health during deployment. Kubernetes exposes startup, readiness, and liveness probes. Keep liveness local and cheap. If every replica restarts when a shared database is down, recovery becomes harder.

Set grace periods from measured startup. A grace period that hides failure for 20 minutes delays rollback; one shorter than normal initialization creates a restart loop.

Health endpoints must not reveal configuration, secrets, or detailed dependency errors to untrusted callers.

## 14. Graceful termination is a protocol

On termination, the platform stops routing new work, signals the process, waits a bounded grace interval, and eventually kills it. The application should:

1. fail readiness or deregister;
2. stop accepting new work;
3. finish or checkpoint in-flight requests and messages;
4. flush bounded telemetry;
5. close resources;
6. exit before the grace period.

Align load-balancer deregistration delay, container stop timeout, Kubernetes termination grace, application deadline, and queue visibility. A worker that receives a 10-minute job cannot safely use a 30-second termination window without checkpoint or redelivery.

Handle the actual stop signal as PID 1. Shell wrappers that do not forward signals cause forced termination and duplicate work.

## 15. Load balancing and discovery solve different paths

Use an Application Load Balancer for HTTP routing and Layer 7 health, a Network Load Balancer for supported Layer 4 requirements, or service discovery and service-connectivity features for internal service communication. Do not create a public load balancer for every internal call by habit.

For each listener and target group, define protocol, port, TLS termination, health, slow start if used, deregistration, idle timeout, and security groups. Preserve client identity only through documented headers or proxy protocol and establish which proxy is trusted.

Service discovery returns candidates; clients still need timeouts, load balancing, retry limits, and stale-endpoint handling. DNS does not prove that a target is ready.

## 16. Scale on demand, not only CPU

ECS Service Auto Scaling changes desired task count through target tracking, step, scheduled, or predictive policies. CPU and memory can fit compute-bound services. Request rate per target, queue backlog per task, latency, or a domain metric often better represents work.

For a queue worker:

```text
backlog per task = visible actionable messages / running healthy tasks
target backlog per task ≈ acceptable queue delay / average processing time
```

Cap scale from database connections, partner quotas, subnet IPs, cluster capacity, and cost. Configure a minimum for availability and cold-start objectives. Scaling from zero waits for evidence and is not instantaneous.

Scale-out must outrun backlog growth; scale-in should be conservative and honor draining. Test scaling during deployment and dependency slowdown. A pending desired count can indicate insufficient cluster capacity rather than a broken application.

## 17. A rollout needs health and a rollback target

Deploy a new task-definition revision or Kubernetes manifest by immutable digest. Control minimum healthy capacity and maximum surge so the platform can run old and new replicas together without exhausting IP, CPU, memory, ports, or downstream connections.

ECS rolling deployments can use a deployment circuit breaker to detect tasks that fail to reach `RUNNING` or pass container, load-balancer, or discovery health. Automatic rollback requires a previously completed deployment. Alarm on deployment failure events; rollback itself can stall.

Kubernetes Deployments use readiness, progress deadlines, surge and unavailable settings. A rollout becoming “available” proves its probes passed, not that checkout or settlement works. Add synthetic and business-outcome verification.

Keep database and event changes compatible with concurrent old and new versions. Rollback the workload before removing compatibility, and test that the retained image still starts with current secrets and dependencies.

## 18. EKS manages a control plane, not your whole platform

In EKS standard, AWS manages the Kubernetes control plane and its highly available infrastructure. The customer still owns workload manifests, namespaces, RBAC, admission policy, network behavior, node groups, add-ons, storage classes, observability, backup of application state, and upgrades within the documented boundary.

Managed node groups automate node provisioning and replacement but do not automatically update when the control plane changes. EKS Auto Mode extends AWS management into compute, scaling, networking, and storage capabilities. EKS on Fargate removes node management for eligible Pods but has feature and identity limitations. These modes reduce tasks; none eliminates workload governance.

The cost of EKS is not only the cluster fee. Count platform engineering, controllers, add-ons, upgrades, incident skill, unused node capacity, cross-zone traffic, logs, and policy maintenance.

## 19. Kubernetes adds a declarative API and controllers

A minimal service commonly includes:

- a `Deployment` or another controller describing Pods and rollout;
- a `Service` providing stable discovery and virtual addressing;
- an `Ingress` or Gateway integration for external routing;
- `ConfigMap` and secret references;
- service account and AWS workload identity;
- resource requests and limits;
- probes and a disruption budget;
- auto-scaling and topology policy;
- logs, metrics, and alert ownership.

The API stores desired state; controllers continuously reconcile actual state. Manual changes made directly to live objects drift from Git or infrastructure code and may be overwritten. Use server-side validation, policy checks, diff or plan review, controlled apply, and post-deployment verification.

Namespaces help organization and policy scope but are not complete tenant isolation by themselves. RBAC, network policy, pod security, quotas, node isolation, and separate clusters may be required based on threat model.

## 20. EKS networking consumes real VPC capacity

With the Amazon VPC CNI, Pods commonly receive VPC addresses. This simplifies routing and security integration but makes subnet IP capacity and ENI density scheduling constraints. Plan pod density, prefix delegation where appropriate, secondary address space, dual-stack decisions, and failure-zone headroom before a cluster is full.

Security groups, Kubernetes network policies, load-balancer controllers, service meshes, and application TLS act at different layers. Draw the permitted path from client through load balancer, node or Pod interface, sidecar, and application. “The cluster is private” does not define east-west authorization.

Restrict the Kubernetes API endpoint and administrative access. Separate AWS IAM authentication, Kubernetes RBAC authorization, and workload identity. Audit cluster API activity and high-risk changes.

## 21. Upgrades are recurring product work

Kubernetes releases regularly, and EKS versions have standard and extended support windows. Plan upgrades continuously:

1. inventory deprecated APIs and incompatible add-ons;
2. test workloads and policy in a representative cluster;
3. verify backups and rollback or replacement strategy;
4. update the control plane one supported step at a time;
5. update nodes or recreate Fargate Pods as required;
6. update VPC CNI, CoreDNS, `kube-proxy`, CSI drivers, controllers, and clients;
7. run workload, network, storage, and security verification.

Managed node groups are not silently upgraded with the control plane. Pod disruption budgets can protect availability but also block a node drain. Test capacity to run replacements before starting.

Assign an owner and calendar for every add-on. An abandoned ingress controller or autoscaler has cluster-wide privileges and can outlive the application that introduced it.

## 22. Observe scheduler, workload, and business outcome

Container stdout and stderr should be structured and shipped to durable storage with explicit retention. Include service, environment, image digest, task or Pod identity, trace ID, safe request identity, and outcome. Do not depend on files inside a stopped container.

Monitor:

- image findings, signature or policy failures, and pull errors;
- desired, pending, running, stopped, unavailable, and restarting replicas;
- stopped reasons, exit codes, OOM kills, and probe failures;
- deployment progress, circuit-breaker or rollout failure, and rollback;
- CPU, memory, throttling, disk, network, open connections, and file descriptors;
- load-balancer healthy targets, latency, response codes, and rejected connections;
- queue age or request rate per replica and scaling activity;
- node readiness, pressure, version, capacity, and daemon health;
- Kubernetes API audit, policy denial, and privileged changes;
- domain success, error, saturation, and cost per successful operation.

Keep a read-only diagnostic path for task definition, events, stopped tasks, Pod status, events, and logs. Avoid incident procedures that begin by opening a shell in production; ephemeral debugging changes evidence and may require dangerous privileges.

## 23. Build a container-platform contract checker

This standard-library model catches artifact, capacity, identity, rollout, and ownership gaps:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class ImageContract:
    pinned_by_digest: bool
    immutable_release_tags: bool
    scanned: bool
    sbom_attached: bool


@dataclass(frozen=True)
class WorkloadContract:
    platform: str
    replicas: int
    availability_zones: int
    health_check: bool
    rollback_enabled: bool
    graceful_shutdown_seconds: int
    maximum_request_seconds: int
    secret_references_only: bool
    workload_identity: bool
    separate_startup_identity: bool
    resource_budget_declared: bool
    upgrade_owner: str


@dataclass(frozen=True)
class ContainerContract:
    image: ImageContract
    workload: WorkloadContract

    def validate(self) -> None:
        image = self.image
        workload = self.workload
        if not image.pinned_by_digest:
            raise ValueError("deployment must pin the image digest")
        if not image.immutable_release_tags:
            raise ValueError("release tags must be immutable")
        if not image.scanned or not image.sbom_attached:
            raise ValueError("image requires scan results and an SBOM")
        if workload.replicas < 2 or workload.availability_zones < 2:
            raise ValueError("available service requires replicas across zones")
        if not workload.health_check or not workload.rollback_enabled:
            raise ValueError("rollout requires health checks and rollback")
        if workload.graceful_shutdown_seconds <= workload.maximum_request_seconds:
            raise ValueError("shutdown grace must exceed in-flight work")
        if not workload.secret_references_only:
            raise ValueError("secrets must be references, not manifest values")
        if not workload.workload_identity:
            raise ValueError("application requires workload-scoped identity")
        if workload.platform.startswith("ecs") and not workload.separate_startup_identity:
            raise ValueError("ECS requires separate task and execution roles")
        if workload.platform == "eks" and not workload.resource_budget_declared:
            raise ValueError("EKS Pods require an explicit resource budget")
        if not workload.upgrade_owner.strip():
            raise ValueError("platform and add-ons require an upgrade owner")
```

The tests express the review policy:

```python
import unittest

from container_contract import ContainerContract, ImageContract, WorkloadContract


def valid_contract(platform: str = "ecs-fargate") -> ContainerContract:
    image = ImageContract(True, True, True, True)
    workload = WorkloadContract(
        platform, 3, 3, True, True, 45, 20, True, True, True, True, "platform"
    )
    return ContainerContract(image, workload)


class ContainerContractTests(unittest.TestCase):
    def test_complete_ecs_contract_is_accepted(self) -> None:
        valid_contract().validate()

    def test_mutable_image_reference_is_rejected(self) -> None:
        contract = valid_contract()
        image = ImageContract(False, True, True, True)
        with self.assertRaisesRegex(ValueError, "image digest"):
            ContainerContract(image, contract.workload).validate()

    def test_single_zone_service_is_rejected(self) -> None:
        contract = valid_contract()
        workload = WorkloadContract(
            "ecs-fargate", 3, 1, True, True, 45, 20, True, True, True, True, "platform"
        )
        with self.assertRaisesRegex(ValueError, "across zones"):
            ContainerContract(contract.image, workload).validate()

    def test_short_shutdown_grace_is_rejected(self) -> None:
        contract = valid_contract()
        fields = {**contract.workload.__dict__, "graceful_shutdown_seconds": 20}
        with self.assertRaisesRegex(ValueError, "in-flight work"):
            ContainerContract(contract.image, WorkloadContract(**fields)).validate()

    def test_shared_ecs_role_is_rejected(self) -> None:
        contract = valid_contract()
        fields = {**contract.workload.__dict__, "separate_startup_identity": False}
        with self.assertRaisesRegex(ValueError, "task and execution roles"):
            ContainerContract(contract.image, WorkloadContract(**fields)).validate()

    def test_eks_without_resource_budget_is_rejected(self) -> None:
        contract = valid_contract("eks")
        fields = {**contract.workload.__dict__, "resource_budget_declared": False}
        with self.assertRaisesRegex(ValueError, "resource budget"):
            ContainerContract(contract.image, WorkloadContract(**fields)).validate()

    def test_missing_upgrade_owner_is_rejected(self) -> None:
        contract = valid_contract("eks")
        fields = {**contract.workload.__dict__, "upgrade_owner": ""}
        with self.assertRaisesRegex(ValueError, "upgrade owner"):
            ContainerContract(contract.image, WorkloadContract(**fields)).validate()


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

Save the blocks as `container_contract.py` and `test_container_contract.py`, then run:

```bash
python -m unittest -v test_container_contract.py
```

A production checker should inspect authorized read-only inventory for repository mutation, scanning, lifecycle and policy; deployed digests; task definitions or manifests; roles; resources; capacity providers; networks; load balancers; health; scaling; deployments; EKS versions, nodes and add-ons; logs; alarms; and tags. It must not pull untrusted images, start tasks, change desired count, roll deployments, drain nodes, or modify cluster resources during validation.

## 24. Review a container-platform design

```text
source commit, build identity, image digest, SBOM, scan, signature, and owner:
ECR policy, immutability, encryption, replication, retention, and rollback set:
platform choice and concrete need for Fargate, EC2, Managed Instances, or EKS:
task/Pod containers, essential lifecycle, command, ports, and sidecars:
CPU, memory, storage, maximum payload, requests/limits, and quotas:
task execution/node identity versus application task/Pod identity:
configuration, secret reference, retrieval, refresh, rotation, and redaction:
subnets, zones, addresses, ENIs, security groups, network policy, and egress:
load balancer/discovery, TLS, health, registration, and deregistration:
startup, readiness, liveness, dependency health, and failure behavior:
signal handling, termination grace, in-flight work, and forced-stop behavior:
minimum replicas, placement, disruption, Spot interruption, and zone failure:
scaling metric, target, cooldown, maximum, downstream cap, and pending capacity:
rollout surge, healthy minimum, compatibility, verification, and rollback:
EKS control/data plane owners, versions, add-ons, nodes, and upgrade calendar:
logs, metrics, traces, audit, retention, alarms, runbooks, and cost per outcome:
```

## Common Misconceptions

- “The same image means the same runtime behavior.” Identity, network, resources, kernel, and scheduler still differ.
- “A tag identifies a release.” A mutable tag is a pointer; the digest identifies content.
- “A passing image scan means the image stays secure.” New vulnerability data can change findings after deployment.
- “Fargate removes infrastructure responsibility.” It removes node management, not workload, network, identity, rollout, or cost design.
- “An ECS service makes a singleton highly available.” Desired replacement does not preserve in-memory state or eliminate downtime.
- “The task execution role is the application role.” It serves platform startup; the task role serves application API calls.
- “A running container is ready.” Readiness and business verification require separate evidence.
- “EKS means AWS runs Kubernetes for us.” AWS manages the control plane; the customer's platform responsibilities remain substantial.
- “Managed node groups update with the control plane.” Node, add-on, and workload upgrades remain explicit work.
- “Kubernetes guarantees portability.” Manifests depend on storage, networking, identity, controllers, and provider integrations.

## Core Computer Science Concept

Container platforms apply **content-addressed storage, declarative reconciliation, bin packing, health-based replacement, and feedback control**. A digest names immutable content, a scheduler maps resource demands onto capacity, controllers reconcile desired replicas, and auto scaling adjusts that desired state from delayed signals.

## Engineering Connections

- Image digests apply Git's content-identity idea from Chapter 24 to deployable artifacts.
- Task and Pod identity extend Chapter 92's temporary-role model.
- `awsvpc` and VPC CNI make Chapters 93 and 94's address and policy constraints scheduling concerns.
- Health and graceful shutdown connect to Chapter 46's service lifecycle.
- Queue backlog scaling applies Chapters 76 and 101's work and backpressure model.
- Immutable rollout and compatible rollback apply Chapter 77's delivery lifecycle.

## From the Field

An ECS service deploys `orders:latest`. Two tasks start before the tag moves and two scale out afterward, so one service now runs two unrecorded images. A later rollback moves the tag again, but cached and newly pulled bytes still differ. Immutable release tags, task definitions pinned to digests, recorded provenance, and promotion of one tested digest would make every replica and rollback target knowable.

## Engineering Review

### What problem does this solve?

It maps a container from registry artifact through ECS or EKS scheduling into identity, network, health, scaling, rollout, upgrades, and operations.

### Why was it designed this way?

Containers standardize packaging, while orchestrators reconcile many short-lived processes over shared capacity. Reliability depends on immutable identity and explicit platform contracts.

### When should I use it?

Use this model for long-running services, workers, scheduled jobs, portable runtime packages, sidecar-based workloads, or systems needing more control than a standard Event Function.

### When should I avoid it?

Avoid containers when a managed service or bounded function meets the requirement with less operational surface. Avoid EKS specifically when the team lacks a concrete Kubernetes need and day-two ownership.

### How does this make me a better engineer?

It teaches you to distinguish packaging from orchestration, identify scheduler constraints, separate platform and workload identity, and price control against ownership.

### How does this reduce waste?

It reduces mutable releases, duplicate builds, unused nodes, oversized reservations, hidden secrets, broad roles, unbounded logs, stalled rollouts, abandoned add-ons, and Kubernetes adopted for fashion.

## Handbook Principle #103

> A container becomes a reliable service only when immutable artifact identity meets explicit scheduling, identity, network, health, and upgrade ownership.

## Practical Observation

Select one running service and resolve every replica to an image digest. Then identify its source commit, scan and SBOM, task or Pod identity, node or startup identity, private address, health decision, shutdown grace, scaling cap, rollback digest, and upgrade owner. Any answer derived only from a mutable tag or console label is not reproducible evidence.

## Looking Ahead

Every compute platform depends on keys, configuration, secrets, logs, metrics, traces, and control-plane evidence. Chapter 104 connects KMS and secret rotation to CloudWatch, CloudTrail, AWS Config, correlation, retention, and safe operational visibility.

## References

- [Amazon ECR — Tag immutability](https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-tag-mutability.html)
- [Amazon ECR — Image scanning](https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-scanning.html)
- [Amazon ECR — Lifecycle policies](https://docs.aws.amazon.com/AmazonECR/latest/userguide/LifecyclePolicies.html)
- [Amazon ECS — Task definitions](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definitions.html)
- [Amazon ECS — Services](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs_services.html)
- [Amazon ECS — Launch types and capacity providers](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/capacity-launch-type-comparison.html)
- [Amazon ECS — Fargate task-definition differences](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/fargate-tasks-services.html)
- [Amazon ECS — IAM role best practices](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/security-iam-roles.html)
- [Amazon ECS — `awsvpc` task networking](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-networking-awsvpc.html)
- [Amazon ECS — Service Auto Scaling](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service-auto-scaling.html)
- [Amazon ECS — Deployment circuit breaker](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/deployment-circuit-breaker.html)
- [Amazon ECS — Environment variables and sensitive values](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/taskdef-envfiles.html)
- [Amazon EKS — What is Amazon EKS?](https://docs.aws.amazon.com/eks/latest/userguide/)
- [Amazon EKS — EKS on Fargate](https://docs.aws.amazon.com/eks/latest/userguide/fargate.html)
- [Amazon EKS — Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [Amazon EKS — Kubernetes version lifecycle](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [Amazon EKS — Updating a cluster](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html)
- [Amazon EKS — Updating managed node groups](https://docs.aws.amazon.com/eks/latest/userguide/update-managed-node-group.html)
- [Chapter 102 — Lambda, API Gateway, and Serverless Execution](102-lambda-api-gateway-and-serverless-execution.md)
