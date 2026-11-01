# Chapter 105 — Infrastructure as Code and a Complete AWS Delivery Lifecycle

A template can be syntactically valid and still replace a database. A plan can be approved and become stale before it runs. A deployment can report success while customers cannot complete the business operation. A retained bucket can survive teardown and quietly incur charges for years.

The central idea is:

> Infrastructure delivery is a controlled transition from reviewed intent to observed operation, with state, identity, data, recovery, cost, and eventual removal all included in the contract.

## 1. Infrastructure code creates an operating obligation

Infrastructure as code makes change reproducible, reviewable, and automatable. It does not transfer ownership to CloudFormation, the AWS CDK, Terraform, a CI service, or AWS. The team still owns:

- the business and reliability requirements;
- source, dependencies, modules, and generated artifacts;
- deployment credentials and approval boundaries;
- state, locks, plans, and drift;
- replacement and data-migration consequences;
- quotas, capacity, security, and cost;
- alarms, runbooks, backups, and restore tests;
- upgrades, deprecation, retained resources, and teardown.

Treat infrastructure code like production application code, but recognize its larger mutation authority. An application defect may affect one request path. An infrastructure defect can remove the network, data store, recovery evidence, and observability used to diagnose it.

Every resource needs an owner during creation, steady operation, incident response, replacement, and deletion. “Managed service” describes who operates part of the mechanism, not who owns the outcome.

## 2. Model three states and one proposed transition

Safe delivery compares at least three descriptions:

1. **desired state** in reviewed source and generated configuration;
2. **recorded state** known by the infrastructure tool;
3. **actual state** returned by provider control planes.

A plan or change set describes a proposed transition, not truth and not success:

```text
desired source + recorded state + observed actual state -> proposed operations
proposed operations + authorization + runtime conditions -> attempted transition
attempted transition + post-deploy evidence -> accepted operation or rollback
```

CloudFormation stores stack templates and resource relationships. Terraform state maps configuration addresses to remote objects and retains provider metadata. Neither is a disposable cache. Both can differ from actual infrastructure because of emergency changes, service-side defaults, partial failures, unsupported properties, or an operator using another interface.

Record the source revision, tool and provider versions, dependency lock data, environment identity, observed-state revision, generated template or plan digest, reviewer, approval, expiration, and execution result. Without that chain, “we applied the code” is not useful evidence.

## 3. Choose an ownership boundary before choosing syntax

CloudFormation, the AWS CDK, and Terraform can all produce reliable AWS systems. The important design question is which control plane owns each resource.

### CloudFormation

CloudFormation is AWS-native declarative orchestration. A stack owns resources through a template, parameters, and service-side state. Change sets preview additions, modifications, removals, and replacements before execution. A change set does not guarantee that execution will succeed; permissions, quotas, invalid runtime values, dependencies, and service conditions can still fail.

Use stack boundaries that match ownership, lifecycle, blast radius, and deployment cadence. A shared network, workload runtime, stateful data layer, and organization guardrail usually should not be one enormous stack simply because references are convenient.

### AWS CDK

The AWS CDK expresses constructs in a general-purpose language, synthesizes CloudFormation templates and assets, and deploys them through CloudFormation. It adds composition, abstraction, tests, and asset workflows; it does not remove CloudFormation replacement, rollback, policy, quota, or drift semantics.

Review the synthesized output and resulting change set, not only the compact construct source. Treat CDK bootstrap resources, deployment roles, asset buckets, trusted accounts, and bootstrap template versions as privileged platform infrastructure. Environment-specific synthesis can embed account and Region information, so promotion must deliberately control what is rebuilt and what remains identical.

### Terraform

Terraform providers translate configuration into API operations. Terraform state is required mapping and metadata, and a plan compares configuration, prior state, and refreshed remote objects. Store production state remotely with encryption, access control, version recovery, isolation, audit, and locking supported by the backend.

An S3 backend can use a lock file and should use S3 versioning for recovery. Do not disable locking to make a blocked pipeline proceed. Force-unlock only a confirmed stale lock created by an operation the team owns.

### Do not create two writers

One resource must have one authoritative infrastructure owner. Do not let Terraform manage a security group while CloudFormation also manages its rules, or let a console automation continuously overwrite a property owned by a stack. Cross-tool references should use stable published interfaces such as parameter names, DNS names, event contracts, or deliberately governed remote outputs—not shared mutation.

If ownership moves between tools, design an adoption migration: inventory the live object, protect data, import or adopt it, compare every property, remove the old owner without deleting the object, and prove the new owner can plan a no-op before changing it.

## 4. Separate environments by failure and authority

An `environment = "prod"` variable does not create isolation. Prefer separate AWS accounts for production, pre-production, development, security evidence, and shared services when the organization warrants them. Account boundaries improve identity, quota, billing, policy, and incident containment.

Within every environment, record:

- AWS account ID and organization path;
- Region and required secondary Regions;
- stack, state, workspace, or project identity;
- network and DNS boundaries;
- data classification and residency;
- deployment and break-glass roles;
- quota, budget, and tag ownership;
- recovery destination and dependencies.

Never infer the target from a developer's active CLI profile. Resolve and print the account and Region, compare them with allowlisted metadata, and make production targeting fail closed. A human-readable name is insufficient; use immutable account IDs in policy and validation.

Environment separation does not require duplicating unreviewed source. Reuse versioned modules and constructs, then provide small reviewed environment data. Keep production differences visible. A hidden conditional that grants broad access only in production is more dangerous than a clear production configuration file.

## 5. Protect infrastructure state as production data

State can contain resource identifiers, network topology, policy documents, generated credentials, database values, or values marked sensitive only for display. Terraform's `sensitive` annotation redacts output but does not by itself keep the value out of state or plan files. Where supported, ephemeral values and write-only arguments can omit values; otherwise, avoid placing secret material in configuration and protect state as confidential data.

A production state contract should include:

- remote durable storage rather than a laptop file;
- encryption in transit and at rest;
- least-privilege read and write access;
- per-environment and per-system isolation;
- locking or serialized execution;
- version history and tested recovery;
- access and mutation audit;
- retention and secure deletion;
- no state or plan artifacts in source control or public CI logs.

State versioning makes recovery possible, not automatically safe. Restoring an old state snapshot can cause the next plan to misunderstand newer live objects. Stop writers, preserve current evidence, determine the last consistent state, restore deliberately, refresh, and inspect the complete plan before applying.

CloudFormation service state also needs governance. Protect stack update and execution roles, template and asset locations, termination controls where appropriate, and the ability to modify or delete the stack. A stack policy can prevent accidental updates to protected resources during stack updates; it is a fail-safe for update behavior, not a substitute for IAM authorization.

## 6. Build modules that preserve important decisions

A useful module or construct packages resources that share a purpose and lifecycle while exposing the decisions callers genuinely need. It should establish safe defaults, validation, outputs, ownership tags, telemetry, and data lifecycle without hiding consequential behavior.

Good interfaces might expose:

- workload identity and business owner;
- data class, retention, recovery point, and recovery time;
- public, private, or service-only reachability;
- capacity and scaling bounds;
- availability and failure-domain requirements;
- alarm destination and runbook;
- deletion and replacement policy;
- cost-sensitive features.

Avoid a universal module with dozens of booleans that synthesizes unrelated architectures. Avoid wrappers that prevent access to a necessary native capability and then require manual console changes. Version modules, publish compatibility and migration notes, test synthesized output, and make breaking changes explicit.

A module is a policy product. It needs an owner, consumers, supported versions, deprecation process, and evidence that its defaults still match current service behavior.

## 7. Keep secrets out of source, artifacts, plans, and logs

Infrastructure source should declare a reference and access path, not embed a secret value. Create or select the secret container, grant the runtime identity access, and retrieve the value at runtime according to Chapter 104's cache and rotation contract.

Be wary of:

- command-line variables captured in shell history;
- CI environment variables printed during debug tracing;
- generated templates containing dynamic values;
- plan files uploaded as broadly readable artifacts;
- outputs that reveal credentials;
- database passwords placed into state;
- secret values copied between accounts during promotion.

Pass opaque identifiers where possible. If provisioning must generate sensitive material, define exactly where it is persisted, who can read it, how it rotates, whether it appears in state, and how a failed create is cleaned up.

## 8. Use a validation ladder

Fast checks should reject obvious faults before a privileged plan or deployment:

1. format and parse source;
2. pin and verify dependencies;
3. validate schemas and tool configuration;
4. run unit tests for modules, policies, and naming;
5. synthesize generated templates;
6. inspect security, compliance, and organizational policy;
7. estimate cost and check service quotas;
8. create a read-only plan or CloudFormation change set;
9. test in an isolated disposable environment;
10. run integration, failure, recovery, and teardown checks;
11. promote the reviewed artifact and execute with narrow authority;
12. verify platform and business outcomes.

Static policy is valuable for facts visible before deployment: public exposure, encryption configuration, wildcard permissions, required tags, approved Regions, logging, retention, and deletion policy. It cannot prove that a restore works, an alarm reaches a responder, a dependency meets latency, or a customer can complete checkout.

Keep validation deterministic. A test that queries mutable production state without recording it can pass during review and evaluate a different system during apply.

## 9. Review the operation, not the line count

A small source diff can cause a large replacement. A large generated diff can be a harmless metadata change. Review the proposed resource operations and their consequences.

For every plan or change set, ask:

- Which resources are added, modified, replaced, removed, imported, or orphaned?
- Which stable names, addresses, endpoints, or identifiers change?
- Will replacement copy data, preserve it, snapshot it, or delete it?
- Does an IAM, key, resource, endpoint, or trust policy broaden authority?
- Does any route, security group, load balancer, bucket, or API become public?
- Do encryption, logging, retention, backup, or deletion controls weaken?
- Can the operation exceed quotas or briefly double capacity and cost?
- What fails if execution stops halfway?
- What is the rollback operation, and is it data-compatible?
- What evidence will declare success?

CloudFormation `DeletionPolicy` controls what happens when a resource is removed from a template or its stack is deleted. It does not protect the old physical resource during replacement. `UpdateReplacePolicy` controls that replacement case. `Retain` and `Snapshot` can preserve data, but retained resources and snapshots leave CloudFormation's scope and continue to cost money. They need inventory and eventual disposition.

Do not approve a binary plan file without a trustworthy human-readable rendering and digest. Do not approve a change set whose generated template differs from the reviewed synthesis.

## 10. Bind approval to an immutable plan

The safe unit of approval is not “run the pipeline.” It is a particular plan for a particular source revision, dependency set, artifact digest, account, Region, and observed environment revision.

Between plan and apply, another deployment, emergency repair, provider-side change, expired credential, quota consumption, or service event can invalidate assumptions. Set a plan lifetime. Serialize writers. Immediately before execution, verify target identity, source and artifact digest, state revision, lock ownership, approval, and required health gates.

If the tool must recalculate the plan, the prior approval no longer applies when material operations change. Send the new plan through review. Convenience is not a reason to let an approved `update in place` silently become `replace and delete`.

CloudFormation invalidates other change sets after one changes the stack. Terraform saved plans bind configuration and prior-state assumptions. In both cases, detect staleness rather than pretending the old proposal remains authoritative.

## 11. Separate build, review, and execution identities

A developer or pull-request job can format, test, synthesize, and request a read-only plan without permanent production administrator credentials. A controlled deployment identity can execute the approved operations.

Prefer short-lived federation and workload identity over static access keys. Constrain deployment roles by account, Region, resource, service, permission boundary, session context, and source pipeline where supported. CloudFormation service roles persist for stack operations, so their policy and `iam:PassRole` paths deserve careful review.

Separate these capabilities where risk warrants it:

- author source;
- merge protected branches;
- approve a production plan;
- assume the deployment role;
- change the pipeline or policy checks;
- administer state and locks;
- use break-glass authority;
- alter audit evidence.

Separation of duties does not require a human click for every low-risk change. It requires that no untrusted change can rewrite its own checks, approve itself, and acquire unrestricted production authority without a controlled boundary.

## 12. Treat drift as evidence, not merely noise

Drift is a difference between intended or recorded configuration and actual infrastructure. It can come from emergency repair, an unauthorized change, service behavior, a property the tool does not model, a second writer, or failed reconciliation.

CloudFormation drift detection compares supported, explicitly set properties. Unsupported resource types and properties limit what it can prove. Drift-aware change sets can compare actual state, the previous deployment, and desired state for supported resources, helping reveal when an update would overwrite an out-of-band change. They still do not make every property observable.

Define a response:

1. detect and preserve evidence;
2. determine whether the actual or desired state is correct;
3. contain unauthorized or dangerous change;
4. encode an accepted emergency change in source;
5. plan reconciliation;
6. verify no second writer remains;
7. record the decision and prevention work.

Never “fix drift” by blindly applying old source. The manual change may have stopped an incident. Conversely, importing the manual state into source without review may preserve a temporary broad permission forever.

## 13. Import existing infrastructure as a migration

Import connects a live resource to infrastructure state; it does not prove that the source accurately describes the resource or that future changes are safe.

Before import:

- identify the resource and current owner unambiguously;
- capture configuration, dependencies, tags, data, and policy;
- enable appropriate backup and deletion protection;
- model every important property, including defaults;
- ensure no other tool will continue writing;
- test import in a representative environment;
- prepare a state and ownership rollback.

After import, require a no-op plan or explain every difference. Then make one small reversible change and verify it. For CloudFormation resource import or Terraform import, read the exact resource-type limitations. Some properties, relationships, or lifecycle actions may not be importable.

## 14. Design a small complete AWS system

Consider an order-intake workload with these bounded responsibilities:

```text
client
  -> API Gateway HTTP API
  -> Lambda order function
  -> DynamoDB orders table
       -> DynamoDB stream
       -> event consumer
       -> SQS fulfillment queue -> Lambda worker
                              \-> dead-letter queue
```

The synchronous path authenticates and validates the request, performs an idempotent conditional write, and returns the stable order identity. The stream publishes the committed change. A consumer places fulfillment work onto SQS. The worker uses bounded concurrency, idempotency, visibility-timeout renewal where necessary, and a DLQ with an owned redrive procedure.

Infrastructure code also defines:

- separate runtime roles with least-privilege table, stream, queue, log, and key access;
- API throttles, Lambda timeout and concurrency bounds, queue retention, and DLQ policy;
- DynamoDB recovery, deletion protection where available, and lifecycle classification;
- encryption, secret references, structured logs, bounded metrics, OpenTelemetry propagation, alarms, and dashboards;
- CloudTrail and AWS Config evidence through organizational infrastructure;
- ownership, system, environment, data class, and cost-allocation tags;
- budgets and quota monitoring;
- retained-data and full-teardown paths.

Do not add a VPC, NAT gateway, custom KMS key, orchestration engine, Kubernetes cluster, cache, or relational database merely to make the diagram look complete. Every component must answer a requirement and accept an owner, failure mode, cost, and removal plan.

## 15. Divide stacks and states by lifecycle

One reasonable ownership graph is:

```text
organization guardrails and audit
  -> account baseline and deployment roles
     -> regional network and shared endpoints
        -> workload data
        -> workload runtime and messaging
        -> workload observability
```

Stable layers should publish small explicit outputs to faster-moving layers. Avoid circular dependencies between stacks or states. Do not let an application deployment own the organization trail, shared network, or production state bucket it depends on.

Separate stateful and stateless resources when their replacement, approval, backup, or deletion requirements differ. A runtime stack can be replaced aggressively; an orders table cannot. Separation also limits the authority of the routine application deployment role.

Cross-stack references create coupling. Prefer stable identifiers when independent deployment and retirement are important. Version interface contracts and validate that providers and consumers agree before removing an old output.

## 16. Promote evidence and immutable artifacts

Build an application artifact once, scan and sign it, identify it by immutable digest, and promote that same artifact across environments. Rebuilding from the same Git commit can select different base images, packages, timestamps, or registries.

Infrastructure often must incorporate environment-specific account IDs, Regions, domains, capacity, or data policy. Separate reusable versioned source from reviewed environment configuration, then record the exact synthesized template or plan for each target. Do not claim that development and production are identical; prove that their intentional differences are understood.

A useful promotion record contains:

- source and module revisions;
- dependency lock and tool versions;
- application image or package digest;
- generated infrastructure digest;
- environment configuration revision;
- plan or change-set identity and digest;
- security and policy results;
- reviewer and approval;
- deployment event and post-deploy evidence.

Promotion is a claim that evidence learned in a lower environment remains relevant. Production still needs its own verification because scale, policy, data, quotas, dependencies, and failure domains differ.

## 17. Choose a deployment strategy from failure behavior

An in-place deployment is simple but can expose all capacity to one defect. Rolling replacement limits simultaneous change but temporarily mixes versions. Blue/green deployment creates a parallel environment and switches traffic, improving rollback speed at additional cost and data complexity. Canary delivery sends a small controlled portion of traffic to the new version and expands only when health remains acceptable.

Define before deployment:

- batch or traffic increments;
- bake time long enough to observe meaningful behavior;
- minimum healthy capacity;
- platform and business success signals;
- automatic stop and rollback thresholds;
- who can continue after a pause;
- how queued, scheduled, and long-lived work behaves;
- maximum old/new coexistence period.

CloudFormation or the runtime scheduler can report resource stabilization while the application is logically broken. Test a representative business operation and its asynchronous completion. Verify alarm delivery, not just alarm configuration.

## 18. Rollback is a forward compatibility problem

Redeploying old application bits is safe only if data, messages, configuration, secrets, and external contracts remain compatible. A database migration that drops a column or rewrites values can make the old application unusable.

Prefer expand-and-contract:

1. add compatible schema or fields;
2. deploy code that handles old and new forms;
3. migrate or backfill with bounded load and checkpoints;
4. switch writers after verification;
5. observe through the rollback window;
6. remove old compatibility in a later deployment.

For queues and events, consumers should tolerate the supported schema window, and rollback must account for messages produced by the new version. For configuration and secrets, preserve version identity and compatible overlap. For infrastructure replacement, know whether endpoints, physical IDs, and stored data can return to the previous arrangement.

If rollback would lose accepted writes, call it recovery or roll-forward and use a rehearsed procedure. Do not hide data loss behind a green pipeline status.

## 19. Backups are inputs to tested recovery

Inventory every authoritative dataset, including state, configuration, registries, object versions, databases, queues when replay matters, audit evidence, and encryption dependencies. Define recovery point objective, recovery time objective, retention, immutability, cross-account or cross-Region copies, and restoration authority.

Then restore. AWS Well-Architected guidance calls for periodic recovery to verify backup integrity and process against RPO and RTO. AWS Backup restore testing can schedule restores, measure duration, support validation, and remove test resources afterward for supported services. Restoration still needs application-level checks: row counts alone do not prove referential, cryptographic, or business integrity.

A useful restore exercise verifies:

- the recovery point exists and is readable;
- keys, roles, network, DNS, and quotas exist in the target;
- infrastructure can be rebuilt without the failed environment;
- data can be restored within objectives;
- the application can read and write safely;
- asynchronous work can resume without duplication or loss;
- evidence and decisions are preserved;
- temporary restored resources are removed and cost checked.

Keep restore control outside the failure boundary it must recover. A backup encrypted by a deleted key or administered only through a failed identity system is not recoverable.

## 20. Accept deployments through SLO and business evidence

An apply ending with exit code zero means the control-plane operation completed. Acceptance requires evidence from the running system.

Check at least:

- expected resource inventory and configuration;
- healthy capacity in intended failure domains;
- authentication, authorization, encryption, and network denial tests;
- a synthetic or canary business transaction;
- downstream event and queue completion;
- latency, error, saturation, backlog, and throttling signals;
- logs and traces with correlation and no secret leakage;
- alarms, notification paths, and runbook links;
- error-budget impact and comparison with baseline;
- unexpected cost or quota movement.

Choose a bake period from request volume and failure latency. Five minutes may reveal a broken route but not a daily batch, credential rotation, cache expiry, autoscaling limit, backup, or retention defect. Keep long-horizon validation as continuing operations rather than pretending deployment completes all proof.

## 21. Preserve an audit chain without leaking secrets

Evidence should allow an investigator to answer who proposed, reviewed, approved, executed, and observed a change; which source and artifacts were used; what the plan contained; which identity acted; and what the outcome was.

Preserve:

- protected source review and merge records;
- dependency and artifact attestations;
- policy and security results;
- redacted plan or change-set rendering and digest;
- approval bound to target and plan;
- deployment identity and CloudTrail events;
- tool events, stack events, and state revision;
- post-deploy checks and operational signals;
- rollback, exception, and break-glass records.

Evidence stores need separate access, retention, integrity, and deletion controls. Plans and logs can contain confidential resource attributes, so broadly publishing them to satisfy audit creates another security failure.

## 22. Make cost and quota part of design review

Infrastructure code makes resources easy to create, not free to operate. Estimate fixed and usage-sensitive cost before deployment. Review data transfer, NAT processing, logs, metrics, traces, backups, snapshots, idle replicas, provisioned capacity, build minutes, restore tests, cross-Region copies, and retained resources.

Tag resources consistently, activate appropriate cost-allocation tags, and map shared cost intentionally. Set budgets for actual and forecast spend with notification and, where suitable, guarded actions. AWS Budgets data is delayed and is not a real-time circuit breaker. Pair it with service quotas, capacity bounds, anomaly detection, per-request economics, and workload alarms.

Cost controls must preserve reliability and evidence. Automatically deleting an unknown production resource or disabling logs at a threshold can turn a budget issue into an outage or an uninvestigable incident. Prefer bounded scaling, admission control, retention limits, approved service catalogs, and human-owned response.

Review cost after deployment against the estimate. Feed the difference back into module defaults and capacity models.

## 23. Design teardown before creation

Every environment needs a disposition for each resource:

- **delete** because it is reproducible and contains no required data;
- **empty then delete** because the service requires content removal;
- **snapshot then delete** with a named retention and owner;
- **retain and transfer** to another owner or stack;
- **archive** under a defined legal or business policy.

CloudFormation's default is deletion for most resources, with documented exceptions. `Retain`, `RetainExceptOnCreate`, and `Snapshot` alter behavior where supported. Terraform lifecycle controls and provider behavior likewise require explicit review. Neither tool automatically empties every bucket, removes every dependent interface, revokes every external trust, or cleans every retained object.

A teardown runbook should discover resources by authoritative inventory and tags, stop traffic and writers, preserve required data and evidence, revoke integrations and credentials, drain or disposition queues, delete in dependency order, verify retained items, inspect DNS and certificates, check state and locks, and monitor cost afterward.

Test teardown in disposable environments. A test environment that cannot be deleted predictably is warning that production retirement will become archaeology.

## 24. Use disposable laboratories safely

Learn infrastructure delivery in an isolated account with no production trust, synthetic data, a restrictive budget, explicit Region allowlist, bounded quotas, short retention, and a teardown deadline. Prefer local syntax and unit validation first, then a faithful service emulator where it tests the intended behavior, then a small real AWS deployment where service semantics matter.

Before creating resources, record expected inventory and cost-sensitive services. After the lab:

1. run the documented destroy or stack deletion;
2. inspect failures rather than bypassing protection blindly;
3. enumerate retained resources, snapshots, logs, artifacts, keys, addresses, endpoints, and DNS;
4. verify state and lock cleanup;
5. review the next cost report because billing data lags;
6. preserve only intentionally retained evidence.

Never test destructive production behavior from a personal default profile. Disposable means the environment is designed for loss, not that its guardrails are disposable.

## 25. Drill failures across the lifecycle

Exercise failures that happy-path deployments hide:

- state lock held by an interrupted operation;
- state version restored incorrectly;
- plan becomes stale before approval;
- replacement exceeds quota or available IP space;
- deployment role loses a required permission halfway through;
- CloudFormation rollback also fails;
- module upgrade changes a generated logical identity;
- emergency console repair creates drift;
- canary passes platform health but fails the business transaction;
- old code cannot read the new data shape;
- restore lacks a KMS key or network dependency;
- retained resource continues billing after teardown.

For each drill, observe detection, containment, decision authority, recovery, evidence, and follow-up. The goal is not to prove that failures never occur. It is to make partial change understandable and recoverable.

## 26. Encode the minimum delivery contract

The following Python model is intentionally smaller than a real deployment system. It makes high-risk assumptions executable.

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class StateContract:
    remote: bool
    encrypted: bool
    versioned: bool
    locked: bool
    isolated_per_environment: bool

    def validate(self) -> None:
        if not all((self.remote, self.encrypted, self.versioned, self.locked)):
            raise ValueError("state must be remote, encrypted, versioned, and locked")
        if not self.isolated_per_environment:
            raise ValueError("state must be isolated per environment")


@dataclass(frozen=True)
class ChangeContract:
    source_revision: str
    planned_source_revision: str
    environment_revision: str
    planned_environment_revision: str
    artifact_digest: str
    deployed_artifact_digest: str
    destructive_changes_reviewed: bool
    replacements_reviewed: bool
    policy_checks_passed: bool
    cost_reviewed: bool
    backup_verified: bool
    restore_test_age_days: int
    post_deploy_business_check: bool
    post_deploy_platform_check: bool
    data_disposition_classified: bool

    def validate(self, maximum_restore_age_days: int = 90) -> None:
        if self.source_revision != self.planned_source_revision:
            raise ValueError("plan does not match source revision")
        if self.environment_revision != self.planned_environment_revision:
            raise ValueError("plan is stale for the environment")
        if self.artifact_digest != self.deployed_artifact_digest:
            raise ValueError("deployment rebuilt or substituted the artifact")
        if not self.destructive_changes_reviewed or not self.replacements_reviewed:
            raise ValueError("destructive and replacement operations require review")
        if not self.policy_checks_passed or not self.cost_reviewed:
            raise ValueError("policy and cost checks are required")
        if not self.backup_verified:
            raise ValueError("backup must be verified before risky change")
        if not 0 <= self.restore_test_age_days <= maximum_restore_age_days:
            raise ValueError("restore test evidence is missing or stale")
        if not self.post_deploy_business_check:
            raise ValueError("business outcome was not verified")
        if not self.post_deploy_platform_check:
            raise ValueError("platform outcome was not verified")
        if not self.data_disposition_classified:
            raise ValueError("teardown data disposition is unclassified")


@dataclass(frozen=True)
class DeliveryContract:
    state: StateContract
    change: ChangeContract

    def validate(self) -> None:
        self.state.validate()
        self.change.validate()
```

Executable tests turn the review claims into regression checks:

```python
import unittest

from delivery_contract import ChangeContract, DeliveryContract, StateContract


def valid_contract() -> DeliveryContract:
    state = StateContract(True, True, True, True, True)
    change = ChangeContract(
        "git:abc", "git:abc", "state:42", "state:42",
        "sha256:image", "sha256:image", True, True, True, True,
        True, 21, True, True, True,
    )
    return DeliveryContract(state, change)


class DeliveryContractTests(unittest.TestCase):
    def test_complete_delivery_is_accepted(self) -> None:
        valid_contract().validate()

    def test_local_unlocked_state_is_rejected(self) -> None:
        contract = valid_contract()
        bad_state = StateContract(False, True, True, False, True)
        with self.assertRaisesRegex(ValueError, "remote, encrypted, versioned, and locked"):
            DeliveryContract(bad_state, contract.change).validate()

    def test_stale_plan_is_rejected(self) -> None:
        contract = valid_contract()
        fields = {**contract.change.__dict__, "environment_revision": "state:43"}
        with self.assertRaisesRegex(ValueError, "stale"):
            DeliveryContract(contract.state, ChangeContract(**fields)).validate()

    def test_unreviewed_replacement_is_rejected(self) -> None:
        contract = valid_contract()
        fields = {**contract.change.__dict__, "replacements_reviewed": False}
        with self.assertRaisesRegex(ValueError, "replacement"):
            DeliveryContract(contract.state, ChangeContract(**fields)).validate()

    def test_stale_restore_evidence_is_rejected(self) -> None:
        contract = valid_contract()
        fields = {**contract.change.__dict__, "restore_test_age_days": 180}
        with self.assertRaisesRegex(ValueError, "restore test"):
            DeliveryContract(contract.state, ChangeContract(**fields)).validate()

    def test_rebuilt_artifact_is_rejected(self) -> None:
        contract = valid_contract()
        fields = {**contract.change.__dict__, "deployed_artifact_digest": "sha256:other"}
        with self.assertRaisesRegex(ValueError, "substituted"):
            DeliveryContract(contract.state, ChangeContract(**fields)).validate()

    def test_missing_business_check_is_rejected(self) -> None:
        contract = valid_contract()
        fields = {**contract.change.__dict__, "post_deploy_business_check": False}
        with self.assertRaisesRegex(ValueError, "business outcome"):
            DeliveryContract(contract.state, ChangeContract(**fields)).validate()

    def test_unclassified_teardown_is_rejected(self) -> None:
        contract = valid_contract()
        fields = {**contract.change.__dict__, "data_disposition_classified": False}
        with self.assertRaisesRegex(ValueError, "disposition"):
            DeliveryContract(contract.state, ChangeContract(**fields)).validate()


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

Save the blocks as `delivery_contract.py` and `test_delivery_contract.py`, then run:

```bash
python -m unittest -v test_delivery_contract.py
```

A production implementation should derive these claims from signed source and artifact metadata, state backend revisions and locks, CloudFormation change sets or Terraform plans, policy results, backup and restore systems, deployment events, telemetry, synthetic business checks, and resource inventory. The validator should use read-only access wherever possible and must never apply a plan merely to determine whether the plan is safe.

## 27. Review a complete delivery

```text
business outcome, owner, data class, SLO, RPO, RTO, and cost model:
account IDs, Regions, stack/state boundaries, and authoritative owners:
tool, version, provider, modules, locks, synthesis, and bootstrap trust:
state location, encryption, readers, writers, lock, versions, and recovery:
source, environment data, artifact, template, and plan identities:
policy, security, quota, cost, and destructive-operation results:
adds, updates, replacements, removals, imports, and retained resources:
IAM, KMS, network, public access, logging, backup, and deletion changes:
approval identity, expiry, target, plan digest, and execution role:
deployment increments, bake time, stop signals, and rollback authority:
schema, message, secret, configuration, and old-version compatibility:
post-deploy platform, security, business, async, alarm, and SLO checks:
backup inventory, restore evidence, dependency recovery, RPO, and RTO:
drift detection, emergency reconciliation, and second-writer prevention:
budgets, tags, anomaly response, quotas, retained cost, and cost review:
delete, empty, snapshot, retain, transfer, archive, and teardown proof:
audit evidence, exception, break-glass, incident, and review date:
```

## Common Misconceptions

- “Declarative means idempotent and safe.” A declaration can still replace, delete, or repeatedly fail on a live dependency.
- “The plan is the deployment.” It is a proposal based on observations that can become stale.
- “CDK hides CloudFormation details.” It generates CloudFormation, whose resource and replacement semantics still apply.
- “State can be regenerated from AWS.” State contains ownership mapping and metadata that remote APIs may not reconstruct safely.
- “Sensitive output means the value is absent from state.” Redaction and storage omission are different controls.
- “A retained resource is protected.” It leaves tool ownership, keeps costing money, and still needs security and deletion ownership.
- “A successful apply proves the release works.” Control-plane completion does not prove the business outcome.
- “Rollback means deploy the old image.” New data and messages may no longer be compatible with old code.
- “A backup job succeeded, so recovery works.” Only a validated restore tests recoverability.
- “A budget stops runaway spend immediately.” Cost data and budget evaluation lag; design bounded consumption too.

## Core Computer Science Concept

This chapter applies **state-machine transitions, optimistic concurrency, serialization, immutable identity, graph dependency ordering, invariant checking, and feedback control**. A deployment is a concurrent transition over a dependency graph. Plans describe expected operations, locks serialize writers, digests bind identity, policies enforce preconditions, and telemetry determines whether the resulting state satisfies the system's invariants.

## Engineering Connections

- State and plan identity extend Chapters 28 and 41's versioning and delivery evidence.
- Environment and role boundaries apply Chapters 91 and 92's governance and authorization.
- Stack topology uses Chapters 93 and 94's regional, network, and compute failure domains.
- Data disposition and restore testing integrate Chapters 97 through 100.
- Async verification applies Chapter 101's delivery and idempotency contracts.
- Deployment strategies extend Chapters 102 and 103's runtime rollout controls.
- Post-deploy evidence uses Chapter 104's telemetry, audit, and configuration model.

## From the Field

A routine module upgrade changes the generated logical identity of a database. The source diff shows one construct name; the change set shows a replacement. The team approves by pull-request size, not resource operation. Deployment creates a new empty database, shifts the application, and deletes the old physical instance because replacement policy was not set. A synthesized-template test, replacement review, explicit `UpdateReplacePolicy`, current backup, restore rehearsal, and business transaction check would turn the hidden rename into a rejected plan.

## Engineering Review

### What problem does this solve?

It turns infrastructure creation, application release, verification, recovery, cost, and eventual teardown into one reviewable lifecycle instead of independent automation fragments.

### Why was it designed this way?

Infrastructure failures occur between representations and owners: source versus generated template, plan versus actual state, deployment success versus business health, retained data versus cost, and backup existence versus recoverability. Binding identity and evidence across those boundaries makes change governable.

### When should I use it?

Use this lifecycle for every shared or production AWS system and scale the controls to blast radius. Even a small service needs target validation, reviewed changes, recovery, observability, cost ownership, and deletion intent.

### When should I avoid it?

Avoid copying enterprise ceremony into a disposable individual lab. Keep the same invariants—isolated target, bounded cost, no sensitive data, visible plan, and verified teardown—using lighter mechanisms.

### How does this make me a better engineer?

It teaches you to reason about change as a state transition, review generated consequences, bind approval to immutable evidence, and treat recovery and removal as design work.

### How does this reduce waste?

It prevents abandoned environments, duplicate owners, stale plans, accidental replacement, untested backups, rebuilt artifacts, manual drift, idle capacity, indefinite retention, and release pipelines that optimize for green status rather than useful outcomes.

## Handbook Principle #105

> Infrastructure is delivered only when reviewed intent becomes a verified, recoverable, affordable operating system with an owned path to change and removal.

## Practical Observation

Take the most recent production infrastructure change and try to connect, without inference, its source revision, synthesized output, plan, state revision, approval, execution identity, application artifact, business verification, restore evidence, cost effect, and teardown classification. Every missing link is a place where the organization currently relies on memory or luck.

## Part VIII Complete

The AWS chapters began with governance, identity, Regions, networks, compute, storage, data, messaging, runtimes, and operational evidence. This chapter joins them through infrastructure code and a delivery lifecycle. The result is not a catalog of AWS services. It is a method for turning requirements into owned cloud systems whose authority, failure, recovery, cost, and removal can be reviewed.

## Looking Ahead

Part IX steps back from one cloud and develops system design as a disciplined reasoning process. Chapter 106 starts by turning ambiguous requirements into an explicit system model of actors, operations, data, constraints, failure domains, and measurable outcomes.

## References

- [AWS CloudFormation — Change sets](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-changesets.html)
- [AWS CloudFormation — Drift detection](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-stack-drift.html)
- [AWS CloudFormation — Drift-aware change sets](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/drift-aware-change-sets.html)
- [AWS CloudFormation — Stack policies](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/protect-stack-resources.html)
- [AWS CloudFormation — Resource import](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/resource-import.html)
- [AWS CloudFormation — `DeletionPolicy`](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-attribute-deletionpolicy.html)
- [AWS CloudFormation — `UpdateReplacePolicy`](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-attribute-updatereplacepolicy.html)
- [AWS CDK — Deploy applications](https://docs.aws.amazon.com/cdk/v2/guide/deploy.html)
- [AWS CDK — Configure environments](https://docs.aws.amazon.com/cdk/v2/guide/configure-env.html)
- [AWS CDK — Bootstrap environments](https://docs.aws.amazon.com/cdk/v2/guide/bootstrapping-env.html)
- [Terraform — Purpose of state](https://developer.hashicorp.com/terraform/language/state/purpose)
- [Terraform — Create a plan](https://developer.hashicorp.com/terraform/cli/commands/plan)
- [Terraform — State locking](https://developer.hashicorp.com/terraform/language/state/locking)
- [Terraform — S3 backend](https://developer.hashicorp.com/terraform/language/backend/s3)
- [Terraform — Manage sensitive data](https://developer.hashicorp.com/terraform/language/manage-sensitive-data)
- [Terraform — Module development](https://developer.hashicorp.com/terraform/language/modules/develop)
- [AWS Well-Architected — Back up data](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/back-up-data.html)
- [AWS Backup — Restore testing](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing.html)
- [AWS Budgets — Managing costs](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html)
- [Chapter 104 — Encryption, Secrets, Configuration, and Cloud Observability](104-encryption-secrets-configuration-and-cloud-observability.md)
