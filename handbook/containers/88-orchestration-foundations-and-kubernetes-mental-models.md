# Chapter 88 — Orchestration Foundations and Kubernetes Mental Models

Starting a container is straightforward. Keeping the intended number of healthy, correctly configured instances running across changing hosts—while rolling versions, routing traffic, attaching storage, and enforcing policy—is a different problem.

The central idea is:

> Orchestration is continuous reconciliation of declared workload state against a changing cluster, with scheduling, identity, networking, storage, and rollout handled by cooperating control loops.

## 1. Orchestration begins when one host is not the system

A multi-host platform must answer:

- Which machines are available and what can each run?
- Where should a new workload instance be placed?
- What happens when a process or machine disappears?
- How do clients find changing instances?
- How are updates introduced without replacing everything at once?
- Where do configuration, credentials, and durable data live?
- Which identities may change desired state?
- How are resource contention and policy enforced?
- What evidence explains a controller's decision?

These responsibilities exist regardless of product. Kubernetes gives them a widely used API and vocabulary; it does not make them disappear.

## 2. A cluster has a control plane and nodes

A Kubernetes cluster contains a control plane and worker nodes.

The control plane commonly includes:

- an API server that authenticates, authorizes, validates, and exposes objects;
- a durable data store for API state;
- controllers that compare desired and observed state;
- a scheduler that binds eligible unscheduled Pods to nodes;
- optional cloud integration and admission components.

Each node commonly includes:

- a kubelet that realizes assigned Pod specifications;
- a container runtime;
- networking components;
- host operating-system services;
- storage and device integrations.

Production behavior also depends on DNS, network, storage, ingress, metrics, logging, certificate, policy, and cloud-provider components. Kubernetes defines many interfaces; platform implementations supply many data planes.

## 3. The API is the coordination boundary

Users and automation submit objects through the API rather than directly starting processes on arbitrary nodes. Objects contain desired specification, identity, metadata, and observed status.

Conceptually:

```text
declarative intent -> authenticated API mutation -> stored desired state
                                             |
                     controllers and agents observe
                                             |
                         runtime objects and status
```

The API is a high-impact security and availability boundary. A credential that can create or modify workloads can often cause nodes to run code and mount data. Apply least-privilege authorization, admission policy, audit, and short-lived identity.

## 4. Reconciliation is a loop, not a one-time script

A controller repeatedly:

1. observes relevant desired and actual state;
2. computes a difference;
3. performs one or more safe actions;
4. records status or events;
5. observes again.

The loop must be idempotent because it can restart, repeat, race with other actors, or see stale state. It usually converges over time rather than changing the whole system atomically.

This explains why deleting a managed Pod often creates another: the controller sees fewer replicas than desired and acts to close the gap. Editing the replacement Pod is treating a symptom; change the owning workload object.

## 5. Desired state is not immediate state

After an accepted API update, the system can temporarily contain:

- old and new workload revisions;
- pending Pods with no placement;
- Pods pulling images or attaching volumes;
- running but unready containers;
- terminating Pods still draining traffic;
- stale status from an unavailable node;
- retries after transient infrastructure failure.

Automation should wait for explicit conditions with a time budget and surface the reason for non-convergence. “The manifest applied” means the API accepted intent, not that users can complete a request.

## 6. A Pod is the scheduling and lifecycle unit

A Pod groups one or more tightly coupled containers that share a lifecycle and selected namespaces and resources. Containers in a Pod share a network namespace and can communicate over loopback. They can mount shared Pod volumes.

Put containers in one Pod only when they need tight co-location, shared fate, or shared local resources—for example, an application and a purpose-built helper that must run beside each instance.

Do not put an entire distributed application in one Pod. Independently scaled, deployed, secured, or recovered services belong in separate workload units.

## 7. Pod identity is replaceable

Each Pod receives a unique identity and is scheduled to one node. If it is replaced, the new Pod has a new UID and usually a new IP even when it carries the same workload labels.

Applications should therefore:

- discover stable Services rather than store Pod addresses;
- keep durable state outside the Pod's ephemeral filesystem;
- tolerate connection turnover;
- expose meaningful readiness;
- terminate gracefully when asked;
- make startup and initialization repeatable;
- attach request and workload identity to external effects.

A restarted container inside one Pod and a replacement Pod are different lifecycle events with different retained state.

## 8. Containers in a Pod share a trust boundary

Pod containers can reach each other over `localhost` and may share volumes. A compromised helper can observe or modify those shared resources according to its permissions.

Review:

- which volumes each container mounts;
- whether process namespaces are shared;
- service-account token and secret mounts;
- Linux security context per container;
- resource requests and limits;
- startup and shutdown ordering;
- whether the helper can become an independent service.

The Pod is useful for collaboration, not strong isolation between its containers.

## 9. Workload controllers express different lifecycles

Common workload types include:

| Workload | Primary contract |
| --- | --- |
| Deployment | Interchangeable, replaceable replicas with declarative rollout |
| StatefulSet | Ordered or stable identities associated with persistent state |
| DaemonSet | A Pod on all or selected eligible nodes |
| Job | Bounded work that completes successfully |
| CronJob | Jobs created on a schedule |

Choose from lifecycle semantics, not name familiarity. A StatefulSet does not make an application distributed, replicated, or consistent. A Deployment does not make a stateful process stateless.

Avoid managing long-lived application Pods directly when a controller owns the desired lifecycle.

## 10. Deployments manage interchangeable replicas

A Deployment manages ReplicaSets, which manage Pods created from a Pod template. Changing the Pod template creates a new rollout revision; scaling alone does not change the template revision.

Deployment replicas should be interchangeable under the service contract:

- any ready replica can receive a request;
- local instance state is disposable or reconstructable;
- configuration and artifact identity are explicit;
- termination drains work safely;
- external effects remain retry-safe;
- replicas do not rely on stable individual names.

If those assumptions are false, redesign the service or choose a workload and storage model that represents the real identity.

## 11. Services provide stable network identity

A Kubernetes Service selects a set of backend Pods and provides a stable endpoint. EndpointSlice objects represent current backends, and a service proxy or networking implementation programs the data path.

```text
client -> Service name/address -> ready selected endpoints -> Pod port
```

The Service is not a process and does not make an unready application ready. It maps a stable logical identity onto a changing backend set.

Cluster DNS commonly gives Services names. External exposure can involve a Service type, Gateway API, Ingress, or platform load balancer, each with an implementation and policy boundary.

## 12. Labels and selectors connect objects

Controllers and Services use labels and selectors to identify objects. That makes metadata operational.

A selector that is too broad can route traffic to the wrong Pods or make one controller overlap another. A selector that no longer matches can leave a Service with zero endpoints.

Use a consistent label schema for application, component, instance, version, and ownership. Treat selector changes as topology changes and test them during rollouts.

Names identify individual API objects; labels identify sets. Do not substitute one concept for the other.

## 13. Readiness controls traffic membership

A readiness probe answers whether a Pod should receive new Service traffic now. Failed readiness removes the Pod from eligible endpoints without inherently restarting the container.

A liveness probe answers whether restarting the container is an appropriate recovery action. A startup probe protects slow initialization by delaying liveness and readiness evaluation until startup succeeds.

Bad probe design can amplify an incident:

- a shared dependency failure marks every replica unready;
- CPU pressure makes probes time out and causes restarts;
- a liveness probe performs destructive work;
- a shallow TCP check routes traffic before migrations finish;
- a probe depends on tooling absent from the image.

Reuse Chapter 86's bounded, meaningful probe design and distinguish local health from end-to-end business health.

## 14. Scheduling filters and scores nodes

The scheduler considers an unscheduled Pod and current cluster state. It filters out ineligible nodes and scores remaining candidates according to resource availability and placement policy, then records a binding.

Constraints can include:

- CPU, memory, and other resource requests;
- node selectors and node affinity;
- taints and tolerations;
- inter-Pod affinity or anti-affinity;
- topology spread constraints;
- volume topology and attachment;
- ports, devices, runtime class, and policy;
- priority and preemption rules.

Scheduling decides placement. The kubelet and runtime still have to pull images, mount data, configure networking, and start containers.

## 15. Requests support placement; limits support enforcement

Resource requests inform scheduling and capacity accounting. Limits constrain runtime consumption according to resource and platform semantics.

An understated request can overpack nodes even if a high limit permits bursts. An overstated request can leave capacity unused and Pods pending. A missing memory limit can transfer one workload's growth to node pressure; an overly tight limit causes OOM failure.

Measure real startup, steady, and peak behavior. Track pending reasons, throttling, OOM events, eviction, and node pressure. Requests and limits are both operating and cost decisions.

## 16. Placement policy describes failure assumptions

Replicas on one node do not survive that node's loss. Replicas across two nodes in one zone do not survive a zone loss.

Express desired spread across meaningful topology domains while accounting for:

- number and capacity of eligible nodes;
- hard versus preferred constraints;
- maintenance and autoscaling behavior;
- storage attachment topology;
- network latency and data locality;
- correlated control-plane or provider failures;
- whether the application itself can tolerate partition.

A hard anti-affinity rule can improve separation and also make all new Pods unschedulable when capacity is tight. Every constraint needs a failure and capacity model.

## 17. Node failure is observed, not instantly known

Distributed systems cannot distinguish a failed node from a delayed or partitioned one immediately. Controllers use leases, heartbeats, timeouts, and policy to infer availability.

During uncertainty:

- a Pod may still run while the control plane considers its node unreachable;
- a replacement can create duplicate external actors;
- attached storage may need fencing before reassignment;
- status can lag physical reality;
- clients may retain old connections.

Use operation identities, leader fencing, leases, and storage protocols that tolerate ambiguous failure. Orchestration does not remove the distributed-systems rules from Part VI.

## 18. Rolling updates trade capacity for availability

A Deployment rolling update creates new-revision Pods and removes old-revision Pods within surge and unavailability bounds.

Plan:

- `maxSurge`: temporary extra replica capacity;
- `maxUnavailable`: tolerated reduction in ready replicas;
- readiness and startup timing;
- termination grace and traffic draining;
- old/new protocol and schema compatibility;
- image-pull and scheduling capacity;
- rollout progress deadline;
- rollback trigger and evidence.

“Zero downtime” is not a controller property alone. The application, clients, load-balancing path, database changes, and capacity must support overlap.

## 19. Rollback restores a template, not the world

Deployment rollback can select an earlier Pod template. It does not automatically reverse:

- database migrations;
- messages published by the new version;
- external API calls;
- changed secrets or configuration objects;
- removed data;
- client-side caches or contracts.

Use backward- and forward-compatible change sequences, expand-and-contract schemas, feature controls, and explicit data recovery. Record the digest and configuration version in every rollout.

## 20. Disruption has voluntary and involuntary sources

Pods can disappear through rollout, scaling, node drain, eviction, node failure, preemption, operator deletion, or application failure.

Availability design should include:

- enough ready replicas and failure-domain spread;
- graceful termination and endpoint draining;
- disruption budgets where appropriate;
- realistic maintenance and autoscaling procedures;
- dependency and storage recovery time;
- capacity to place replacements;
- client timeouts and retries.

A disruption budget can constrain some voluntary evictions; it cannot prevent hardware failure or guarantee application availability.

## 21. Configuration objects do not guarantee reload

ConfigMaps store non-confidential configuration; Secrets store sensitive values under a different API contract. Pods can consume them through environment variables, arguments, or mounted files.

Update behavior differs:

- environment values are fixed for the container process;
- projected volume content can update eventually;
- `subPath` mounts do not receive the same automatic updates;
- applications may not watch or atomically reload files;
- controllers do not automatically roll every workload after a referenced object changes.

Use versioned configuration identity, deliberate rollout or reload behavior, and validation before activation.

## 22. A Kubernetes Secret needs surrounding protection

Base64 encoding is not encryption. Kubernetes Secrets are stored unencrypted in the API data store by default unless encryption at rest is configured.

Protect them with:

- API-server encryption at rest and key lifecycle;
- least-privilege RBAC;
- namespace and workload separation;
- restricted Pod-creation authority;
- short-lived external identities where possible;
- explicit per-container mounts;
- audit and rotation;
- external secret-store integration when required.

Anyone allowed to create a sufficiently privileged Pod in a namespace can often obtain secrets available in that namespace. Authorization to create workloads is security-sensitive.

## 23. Service accounts are workload API identities

A ServiceAccount identifies workloads to the Kubernetes API and other configured trust systems. Bind only the required RBAC operations.

If a workload does not call the Kubernetes API, disable automatic service-account token mounting. When it does, prefer short-lived, audience-bound projected tokens and validate audience at the receiver.

Do not grant `cluster-admin` to solve a missing permission. Determine the exact API group, resource, namespace, and verbs required, then test denial of everything else.

The workload's external cloud or database identity is a separate authorization system even if a platform bridges the two.

## 24. Persistent storage has an independent control plane

PersistentVolume and claim abstractions connect workload requests to storage supplied by an implementation. Storage classes, topology, access modes, reclaim policy, snapshots, and drivers affect behavior.

Kubernetes can attach a volume to a replacement Pod; it cannot make an application safe for concurrent writers, guarantee a consistent backup, or fence a failed writer unless the storage and application protocols do so.

Use StatefulSet when stable Pod identity and per-replica storage association are part of the application contract. Do not scale a single-writer database merely by increasing replicas.

## 25. Networking APIs depend on data-plane implementations

Kubernetes defines a cluster network model and APIs such as Service and NetworkPolicy, while installed components implement Pod networking, service routing, policy, ingress, and load balancing.

Verify:

- address families and routes;
- CNI and service-proxy implementation;
- whether NetworkPolicy is actually enforced;
- default ingress and egress behavior;
- DNS and EndpointSlice updates;
- source-address preservation;
- external load-balancer health and draining;
- encryption and workload identity.

The presence of a NetworkPolicy object does not prove the selected network implementation enforces it.

## 26. Observability must include control-plane decisions

Application logs and metrics explain only part of a cluster incident. Also collect:

- object spec and status;
- owner references and generation;
- conditions and recent Events;
- scheduler and admission decisions;
- node and kubelet state;
- container runtime lifecycle and OOM evidence;
- Service endpoints and probe status;
- rollout revision and controller status;
- storage and network component evidence;
- API audit records.

Events are useful but not an unlimited durable audit store. Export what the incident and compliance model require.

## 27. Translate Compose concepts carefully

| Compose concept | Kubernetes responsibility | Important difference |
| --- | --- | --- |
| Project | Namespace plus labels and policy | Namespace is a shared API scope, not a full project lifecycle wrapper |
| Service definition | Workload controller plus Pod template | The controller continuously reconciles replicas |
| Compose service name | Service and DNS identity | A Service selects changing ready Pods |
| `depends_on` | Probes, init work, Jobs, and resilient clients | There is no general cross-workload startup-order guarantee |
| Named volume | PersistentVolumeClaim and storage policy | Provisioning, topology, access, and reclaim are independent concerns |
| `ports` | Service, Gateway/Ingress, or load balancer | External routing is implemented by cluster and provider components |
| `environment` / configs | Pod env, ConfigMaps, Secrets, projected volumes | Update and protection behavior varies by consumption mode |
| `restart` | Kubelet and workload-controller reconciliation | Container restart and Pod replacement are separate loops |
| `profiles` | Separate overlays, namespaces, or deployment choices | Optional topology needs its own validation and ownership |

The translation is architectural, not mechanical. First define each responsibility and failure contract; then choose objects.

## 28. Decide whether the platform complexity is justified

Kubernetes can be justified when several of these are real requirements:

- many services or teams need a shared workload API;
- workloads must reschedule across hosts;
- standardized rollout and policy are valuable;
- heterogeneous capacity needs scheduling;
- service discovery spans changing nodes;
- platform integrations provide storage, identity, secrets, and observability;
- autoscaling or batch scheduling has material value;
- a staffed platform team can own lifecycle and incidents.

It can be wasteful when one small system fits on a single recoverable host, deployments are infrequent, the team cannot operate the control plane or data plane, or a managed application platform supplies the needed outcomes more simply.

Choose the smallest platform that satisfies availability, security, scale, and organizational requirements.

## 29. Account for the platform as a product

Cluster adoption adds ongoing work:

- version and API lifecycle management;
- node-image and kernel patching;
- certificate and credential rotation;
- network, storage, DNS, ingress, and policy upgrades;
- capacity, quota, and cost management;
- backup and recovery of control-plane and application state;
- tenant isolation and authorization review;
- observability and incident response;
- developer interfaces, templates, and support.

Managed Kubernetes transfers some component operation to a provider, not application ownership or all cluster configuration.

Measure platform success through safer lead time, recovery, reliability, security, and reduced cognitive load—not by object count.

## 30. Practical simulation: reconcile and roll replicas

The following standard-library model demonstrates three ideas: a controller replaces missing replicas, a scheduler respects node capacity, and a rolling update preserves an availability floor while allowing bounded surge. It is conceptual; it does not reproduce Kubernetes source code, API timing, or every failure mode.

Save as `test_reconciliation.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
import unittest


@dataclass
class Node:
    name: str
    capacity: int
    pods: set[str] = field(default_factory=set)


@dataclass
class Pod:
    uid: str
    revision: str
    node: str | None = None
    ready: bool = False
    age: int = 0


class Cluster:
    def __init__(
        self,
        replicas: int,
        revision: str,
        nodes: list[Node],
        max_surge: int = 1,
        max_unavailable: int = 1,
    ) -> None:
        self.replicas = replicas
        self.revision = revision
        self.nodes = {node.name: node for node in nodes}
        self.max_surge = max_surge
        self.max_unavailable = max_unavailable
        self.pods: dict[str, Pod] = {}
        self.sequence = 0

    def create(self, revision: str) -> Pod:
        self.sequence += 1
        pod = Pod(uid=f"pod-{self.sequence}", revision=revision)
        self.pods[pod.uid] = pod
        return pod

    def delete(self, uid: str) -> None:
        pod = self.pods.pop(uid)
        if pod.node is not None:
            self.nodes[pod.node].pods.remove(uid)

    def schedule(self) -> None:
        for pod in self.pods.values():
            if pod.node is not None:
                continue
            candidates = [
                node
                for node in self.nodes.values()
                if len(node.pods) < node.capacity
            ]
            if not candidates:
                continue
            node = min(candidates, key=lambda item: (len(item.pods), item.name))
            node.pods.add(pod.uid)
            pod.node = node.name

    def advance_readiness(self) -> None:
        for pod in self.pods.values():
            if pod.node is None:
                continue
            pod.age += 1
            if pod.age >= 2:
                pod.ready = True

    def reconcile(self) -> None:
        self.schedule()
        self.advance_readiness()

        current = [
            pod for pod in self.pods.values() if pod.revision == self.revision
        ]
        old = [
            pod for pod in self.pods.values() if pod.revision != self.revision
        ]
        total = len(self.pods)

        if len(current) < self.replicas and total < self.replicas + self.max_surge:
            self.create(self.revision)

        ready = sum(pod.ready for pod in self.pods.values())
        ready_current = sum(pod.ready for pod in current)
        availability_floor = self.replicas - self.max_unavailable

        if old and ready_current > 0 and ready > availability_floor:
            victim = sorted(old, key=lambda pod: pod.uid)[0]
            self.delete(victim.uid)

    def converge(self, limit: int = 100) -> None:
        for _ in range(limit):
            self.reconcile()
            if (
                len(self.pods) == self.replicas
                and all(pod.revision == self.revision for pod in self.pods.values())
                and all(pod.ready for pod in self.pods.values())
            ):
                return
        raise TimeoutError("cluster did not converge")

    def endpoints(self) -> set[str]:
        return {pod.uid for pod in self.pods.values() if pod.ready}

    def assert_capacity(self) -> None:
        for node in self.nodes.values():
            if len(node.pods) > node.capacity:
                raise AssertionError(f"node {node.name} is over capacity")


class ReconciliationTests(unittest.TestCase):
    def new_cluster(self) -> Cluster:
        return Cluster(
            replicas=3,
            revision="v1",
            nodes=[Node("node-a", 2), Node("node-b", 2)],
        )

    def test_controller_replaces_a_missing_pod(self) -> None:
        cluster = self.new_cluster()
        cluster.converge()
        removed = sorted(cluster.pods)[0]

        cluster.delete(removed)
        cluster.converge()

        self.assertNotIn(removed, cluster.pods)
        self.assertEqual(len(cluster.pods), 3)
        self.assertEqual(len(cluster.endpoints()), 3)
        cluster.assert_capacity()

    def test_rollout_preserves_bounds_and_converges(self) -> None:
        cluster = self.new_cluster()
        cluster.converge()
        cluster.revision = "v2"

        for _ in range(100):
            cluster.reconcile()
            cluster.assert_capacity()
            self.assertLessEqual(
                len(cluster.pods),
                cluster.replicas + cluster.max_surge,
            )
            self.assertGreaterEqual(
                len(cluster.endpoints()),
                cluster.replicas - cluster.max_unavailable,
            )
            if (
                len(cluster.pods) == cluster.replicas
                and all(pod.revision == "v2" for pod in cluster.pods.values())
                and all(pod.ready for pod in cluster.pods.values())
            ):
                break
        else:
            self.fail("rollout did not converge")


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

Run it:

```bash
python -m unittest -v test_reconciliation.py
```

The Service analogue returns only ready Pod UIDs. The scheduler analogue refuses to exceed per-node capacity. The controller permits one surge Pod and deletes an old Pod only above the availability floor.

The simulation omits API conflicts, asynchronous watches, admission, kubelet restart behavior, image pulls, taints, volumes, real resource dimensions, partitions, graceful termination, and controller-manager leadership. Use it to understand feedback loops, not to predict a cluster implementation.

## 31. Create an orchestration responsibility map

Before writing manifests, fill in:

```text
workload roles and owning teams:
replica and availability objectives:
Pod composition and shared trust:
artifact digest and admission policy:
requests, limits, and growth model:
required and preferred placement constraints:
startup, readiness, and liveness contracts:
Service selectors and client discovery:
external ingress and egress paths:
configuration version and reload behavior:
secret storage, grant, identity, and rotation:
persistent data, access mode, topology, fencing, backup, restore:
rollout surge, unavailable budget, compatibility, and rollback:
node, zone, control-plane, and dependency failure behavior:
service account and RBAC:
network and Pod security policy enforcement:
application, controller, node, runtime, network, and storage evidence:
platform owner, version lifecycle, capacity, and incident on-call:
reason orchestration complexity is justified:
```

An object should exist because it owns one of these responsibilities, not because a template happened to include it.

## Common Misconceptions

- “A Pod is a lightweight VM.” It is a replaceable scheduling unit whose containers share selected namespaces and fate.
- “Applied means deployed.” API acceptance precedes asynchronous scheduling, startup, readiness, and rollout convergence.
- “A Service keeps Pods alive.” Workload controllers manage Pods; a Service supplies stable network identity and backend selection.
- “Liveness means ready for traffic.” Liveness governs restart; readiness governs endpoint membership.
- “Three replicas mean high availability.” Placement, failure domains, dependencies, capacity, and application behavior determine availability.
- “StatefulSet makes a database highly available.” It supplies identity and storage association, not database replication or consensus.
- “Kubernetes Secrets are encrypted by default.” API data-store encryption at rest must be configured and access must be restricted.
- “A NetworkPolicy object blocks traffic.” Enforcement depends on the installed network implementation and policy coverage.

## Core Computer Science Concept

Orchestration is **distributed feedback control over eventually observed state**. Independent reconcilers act on durable desired objects, schedulers solve constrained placement, and stable virtual identities route around ephemeral instances; correctness depends on idempotency, convergence, and explicit behavior under partial failure.

## Engineering Connections

- Pod containers retain the process, storage, networking, and security models from Chapters 82–87.
- Reconciliation is an idempotent distributed operation under Chapter 74's retry rules.
- Node uncertainty and storage fencing reuse the leases and partial-failure model from Part VI.
- Services extend Chapter 84's discovery model across changing nodes.
- Rollout overlap makes schema and protocol compatibility an API-evolution problem.
- Control-plane evidence extends Chapter 86 beyond one runtime daemon.

## From the Field

A team deploys three API replicas and assumes node-failure tolerance. All three land on one large node because no spread policy expresses the failure domain. The node fails, every endpoint disappears, and replacements remain pending because the remaining nodes lack requested capacity. Replica count described quantity; scheduling, topology, and spare capacity determined availability.

## Engineering Review

### What problem does this solve?

It explains how a platform places, replaces, discovers, updates, secures, and observes container workloads across changing hosts without relying on permanent instance identity.

### Why was it designed this way?

Multi-host systems experience partial failure and concurrent change, so durable desired objects plus independent idempotent control loops can continuously converge rather than depend on one fragile procedure.

### When should I use it?

Use orchestration when multi-host recovery, shared platform policy, standardized rollouts, changing service endpoints, heterogeneous scheduling, or organizational scale justify a continuously operated control plane.

### When should I avoid it?

Avoid adopting Kubernetes when a simpler managed platform or recoverable single-host system meets the real requirements and the organization cannot own the cluster's lifecycle and incident surface.

### How does this make me a better engineer?

It teaches you to separate intent from observation, scheduling from execution, Pod identity from service identity, readiness from liveness, and controller rollback from data recovery.

### How does this reduce waste?

It prevents direct Pod repair, accidental selector gaps, unschedulable hard constraints, meaningless replica counts, unsafe rollouts, unnecessary clusters, and platform work without an owned outcome.

## Handbook Principle #88

> Orchestrate responsibilities, not YAML: declare intent, observe convergence, and design every controller action for replacement and partial failure.

## Practical Observation

Run the reconciliation simulation and watch the stable endpoint count during the revision change. Then complete the responsibility map for one Compose project from Chapter 85. If no requirement needs multi-host reconciliation, record that conclusion rather than manufacturing a cluster migration.

## Looking Ahead

The individual mechanisms are now in place: reproducible images, verified distribution, process and storage lifecycle, networking, Compose, runtime diagnosis, least privilege, and orchestration. Chapter 89 joins them into one container delivery workflow with policy gates, deployment evidence, failure injection, rollback, cleanup, and an operated supply-chain boundary.

## References

- [Kubernetes components](https://kubernetes.io/docs/concepts/overview/components/)
- [Kubernetes objects](https://kubernetes.io/docs/concepts/overview/working-with-objects/)
- [Kubernetes controllers](https://kubernetes.io/docs/concepts/architecture/controller/)
- [Kubernetes Pods](https://kubernetes.io/docs/concepts/workloads/pods/)
- [Kubernetes Pod lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)
- [Kubernetes workload management](https://kubernetes.io/docs/concepts/workloads/controllers/)
- [Kubernetes Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
- [Kubernetes Services, Load Balancing, and Networking](https://kubernetes.io/docs/concepts/services-networking/)
- [Kubernetes resource management for Pods and containers](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [Kubernetes assigning Pods to nodes](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/)
- [Kubernetes liveness, readiness, and startup probes](https://kubernetes.io/docs/concepts/workloads/pods/probes/)
- [Kubernetes configuration](https://kubernetes.io/docs/concepts/configuration/)
- [Kubernetes Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Kubernetes ServiceAccounts](https://kubernetes.io/docs/concepts/security/service-accounts/)
- [Kubernetes StatefulSets](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/)
