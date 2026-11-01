# Chapter 77 — A Complete CI/CD Automation Lifecycle

A pipeline is not trustworthy because its YAML is long or every stage is green. Trust comes from preserving identity, evidence, authority, and recovery from source review through the deployed artifact.

The central idea is:

> Verify an immutable revision, build one immutable artifact, promote that artifact by digest through protected environments, and keep enough evidence to stop, recover, or roll back safely.

## 1. Define CI, delivery, and deployment

**Continuous integration** gives small source changes fast, repeatable feedback and integrates them into a shared branch under required checks.

**Continuous delivery** keeps a verified release candidate ready for an explicit production decision.

**Continuous deployment** automatically promotes every candidate that satisfies policy into production.

These are different operating models. Automation should not turn delivery into deployment accidentally. The acceptable model depends on product risk, recovery speed, compliance, and the quality of automated verification.

## 2. Automate a stable manual contract

A pipeline should invoke the understood tasks from Chapter 75, not become the only place anyone can discover how the project works.

Before CI/CD, define:

- supported bootstrap and verification commands;
- source and dependency inputs;
- artifact format and digest;
- environment configuration boundaries;
- deployment and health-check procedure;
- failure and rollback behavior;
- required human judgment;
- service ownership and escalation.

Moving an unexplained command sequence into workflow syntax preserves the ambiguity and makes it harder to reproduce locally.

## 3. Model the lifecycle as identities and transitions

A complete path looks like this:

```text
reviewed source revision
        |
        v
unprivileged verification evidence
        |
        v
isolated build -> artifact digest + provenance + dependency evidence
        |
        v
candidate registry
        |
        v
staging promotion -> deployment record -> post-deploy verification
        |
        v
production policy/approval
        |
        v
progressive production promotion -> verification -> completed release
                                      |
                                      v
                            stop / rollback / roll forward
```

Each arrow is a policy-controlled state transition. Record the actor, source revision, artifact digest, evidence, environment, time, and result.

## 4. Treat triggers as trust boundaries

Common triggers carry different authority:

- a pull request from a fork contains untrusted code;
- a branch push identifies integrated code but can still modify the workflow;
- a signed or protected tag may represent release intent;
- a manual dispatch identifies an actor and parameters, not automatic correctness;
- a schedule creates time-based intent under Chapter 76's semantics;
- an API event requires authenticated origin and replay handling.

Untrusted change verification should receive no production secrets and no write authority to trusted caches or releases. A workflow definition in the change is executable input; it can attempt to exfiltrate anything the runner can reach.

Separate the event that requests work from the policy that authorizes a privileged transition.

## 5. Pin the source revision

Build and deploy an immutable source revision, usually a full commit identifier resolved by the trusted checkout step. Record both the requested reference and resolved revision.

Before a privileged build or deployment:

- verify the revision belongs to the expected repository;
- confirm required review and checks apply to that exact revision;
- reject a moving branch lookup performed later in the job;
- fetch only the history and tags the build actually requires;
- avoid executing checkout hooks or repository configuration unexpectedly.

A branch name is convenient user intent. It is not an immutable artifact identity.

## 6. Isolate and harden runners

Pipeline code executes with the runner's filesystem, network, process, and credential authority. Prefer ephemeral workers that start from a controlled image and are destroyed after one job.

Runner policy should define:

- image and toolchain provenance;
- patching and retirement;
- network destinations;
- filesystem and process isolation;
- access to metadata services and control planes;
- workspace cleanup;
- log and artifact collection;
- separation between untrusted and privileged jobs.

Long-lived self-hosted runners can retain malicious processes, modified tools, credentials, and workspace data between jobs. If they are necessary, dedicate them by trust level and rebuild them predictably.

## 7. Minimize workflow permissions

Start every job with no write permission and add the smallest permission it needs. Verification usually needs source read access only. Artifact upload, provenance, package publication, and deployment should be separate jobs with separate identities.

Prefer short-lived workload identity exchanged for narrowly scoped credentials over stored long-lived keys. Bind trust to claims such as repository, revision, workflow, environment, and protected reference.

Environment credentials should become available only after environment policy passes. Do not pass production credentials through earlier build or test jobs.

Masking a secret in logs does not reduce its authority or remove it from a compromised process.

## 8. Control workflow dependencies

Third-party actions, plugins, container images, runner images, package installers, and reusable workflows are executable dependencies.

Use immutable references or the platform's verified dependency-lock mechanism. Review updates and retain origin information. A movable tag can resolve to different code after review.

Limit dependency count and inspect what each component can access. A convenient formatting action does not need a production token. Verify downloaded tools before execution and constrain package indexes or registries according to the project's supply-chain policy.

Pinning prevents unexpected movement; it does not prove that the pinned code is safe.

## 9. Keep caches outside the trust chain

Caches accelerate work but should not decide what is released. Apply Chapter 75's complete cache keys and separate them by trust level.

Do not let untrusted changes populate an executable cache later consumed by a privileged release job unless the content is independently verified. Validate restored content, and rebuild on a miss or integrity failure.

Artifacts differ from caches:

- a cache is disposable acceleration;
- an artifact is an identified output with retention and integrity policy;
- a release candidate is an artifact that has satisfied named evidence;
- a deployed release is a candidate recorded in an environment history.

## 10. Make required checks revision-specific

Required checks should cover the project's actual release risks:

- formatting, linting, and type checks;
- unit, component, and integration tests;
- dependency and vulnerability policy;
- generated-file consistency;
- packaging and installation smoke tests;
- platform or architecture matrix where supported;
- migration and compatibility checks;
- policy validation for workflow and infrastructure changes.

Report results against the exact revision. Avoid a gate whose name can be produced by a weaker alternate workflow. Keep failures actionable and distinguish infrastructure errors from product failures without automatically treating either as success.

Reruns create new evidence. Record which attempt satisfied policy and whether code, configuration, dependencies, or runner image changed.

## 11. Build once in a controlled job

After integration policy passes, build the release candidate once:

1. resolve the immutable source and locked dependencies;
2. run the versioned project build task;
3. produce the artifact in an isolated environment;
4. calculate its cryptographic digest;
5. create provenance and dependency evidence;
6. store it in immutable artifact storage;
7. verify it can be retrieved and installed;
8. identify every later transition by digest.

Do not rebuild separately for staging and production. A rebuild can resolve different inputs or embed different state, so production would receive an object that staging did not verify.

Environment-specific configuration should be supplied at runtime or represented as a separately versioned input, not baked through hidden rebuilds.

## 12. Attach evidence to the artifact

Useful release evidence can include:

- source revision and repository identity;
- build definition and trusted builder identity;
- artifact name, media type, size, and digest;
- dependency lock and software bill of materials;
- test and scan results tied to the same subject;
- signatures or attestations;
- creation and retention policy.

Provenance states where and how an artifact was built. It does not by itself prove the artifact is secure. Consumers must verify authenticity and compare claims with policy.

Store evidence where an artifact substitution cannot silently preserve a green status. A test report for digest A does not authorize digest B.

## 13. Promote by digest through environments

Promotion changes the status or availability of an existing artifact; it does not create a new artifact.

For each environment, define:

- permitted source branches, tags, or release channels;
- required evidence and approvals;
- credential identity and scope;
- concurrency and cancellation policy;
- configuration and secret source;
- deployment window and freeze policy;
- post-deployment verification;
- history and retention.

Approvals should present the artifact digest, source revision, evidence summary, proposed change, current environment state, deployment strategy, and recovery plan. “Approve run 1842” is too little context.

Separate request from approval when risk requires it, and prevent the initiator from satisfying independent review alone.

## 14. Plan before changing an environment

A deployment plan should compare desired and observed state and show:

- current and target artifact digests;
- configuration and migration changes;
- resources or instances affected;
- order, batch size, and health gates;
- expected availability impact;
- rollback candidate and compatibility limits;
- credentials and environment scope;
- operations that are irreversible.

Bind approval to a digest of the plan. Re-plan if environment state, target artifact, or configuration changes before apply.

Dry-run output is evidence, not authorization and not a guarantee that state will remain unchanged.

## 15. Choose a deployment strategy deliberately

Common strategies include:

- **recreate**: stop the old version, then start the new one;
- **rolling**: replace bounded groups while maintaining service;
- **blue-green**: prepare a parallel environment and switch traffic;
- **canary**: expose a small population, evaluate, then expand;
- **feature control**: deploy code separately from enabling behavior.

The platform name does not guarantee safety. Define capacity during transition, connection draining, session behavior, health criteria, observation duration, stop conditions, and rollback mechanics.

Progressive delivery reduces blast radius only when the first cohort is representative enough and the system can detect harm before expansion.

## 16. Treat data changes as compatibility work

Application rollback does not automatically reverse a schema or data migration. Prefer changes that support mixed versions during rollout:

1. expand the schema or interface compatibly;
2. deploy code that can use old and new forms;
3. migrate or backfill with resumable automation;
4. verify adoption and correctness;
5. remove the old form in a later release.

Record irreversible steps and backup or restore requirements in the plan. Test rollback while both versions and data shapes coexist.

Never assume a successful migration command means every application instance can safely roll back.

## 17. Verify after deployment

Deployment success means the platform accepted a change. Release success requires product and operational evidence.

Post-deployment checks can include:

- expected artifact digest on the intended instances;
- readiness and representative synthetic transactions;
- error rate, latency, saturation, and dependency health;
- queue age and background-worker progress;
- migration completion and data invariants;
- business outcomes appropriate to the change;
- absence of security or authorization regressions.

Use a bounded observation window and compare with a meaningful baseline. A single successful `/health` request may prove only that one process can answer one path.

Keep monitoring after the pipeline completes because slow failures may appear later.

## 18. Stop, roll back, or roll forward

Define automatic stop conditions before rollout. On failure:

- stop further promotion;
- preserve the artifact, plan, logs, and environment evidence;
- prevent concurrent deployment from obscuring state;
- decide whether rollback is safe under current data and dependencies;
- otherwise roll forward with a reviewed repair;
- reconcile partial instances and background work;
- communicate ownership and status.

Rollback should redeploy a previously known digest, not rebuild an old branch. Verify the rollback artifact remains available and compatible with current state.

A rollback is another deployment with authority, failure modes, and post-deployment verification. Test it regularly.

## 19. Control pipeline concurrency and cancellation

Apply Chapter 76's ownership model to pipeline runs. Decide whether a newer revision cancels, queues behind, or runs beside an older one.

Canceling obsolete pull-request verification can save capacity. Canceling a production deployment midway may leave partial state. Deployment jobs need cooperative stop points and environment-scoped exclusivity.

Do not use one global lock when independent environments or services can progress safely. Do not use per-run locks when all runs mutate one shared environment.

Record which run owns the environment transition and reject stale apply attempts through expected-current-digest checks or platform equivalents.

## 20. Preserve an auditable release record

For every release, retain:

- trigger and requesting actor;
- resolved source revision;
- reviewed workflow and dependency identities;
- builder and runner identity;
- artifact digest and storage location;
- provenance, dependency, test, and scan evidence;
- plan digest and approvals;
- environment transitions and credentials used;
- post-deployment results;
- rollback or repair actions;
- final disposition.

Apply access, retention, and minimization policies. Logs should not contain secrets or unrestricted customer data.

Auditability is not collecting every byte forever. It is preserving enough trustworthy evidence to reconstruct why a specific artifact reached a specific environment.

## 21. Complete example: promote one verified artifact

This standard-library simulation binds evidence and deployment plans to artifact digests. It rejects artifact substitution, self-approval for production, changed environment state, corrupted storage, and stale rollback:

```python
from __future__ import annotations

import hashlib
import re
import unittest
from dataclasses import dataclass, replace
from typing import Callable, Mapping


DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
REVISION_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class PolicyError(RuntimeError):
    pass


@dataclass(frozen=True)
class Evidence:
    name: str
    subject_digest: str
    passed: bool


@dataclass(frozen=True)
class ReleaseCandidate:
    source_revision: str
    artifact_digest: str
    build_run_id: str
    evidence: tuple[Evidence, ...]
    staging_verified: bool = False


@dataclass(frozen=True)
class DeploymentPlan:
    environment: str
    expected_current_digest: str | None
    target_digest: str
    rollback_digest: str | None
    initiator: str
    approver: str | None


@dataclass
class Environment:
    name: str
    current_digest: str | None
    history: list[str]


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def verify_candidate(candidate: ReleaseCandidate) -> None:
    if not REVISION_PATTERN.fullmatch(candidate.source_revision):
        raise PolicyError("source revision must be a full 40-character hash")
    if not DIGEST_PATTERN.fullmatch(candidate.artifact_digest):
        raise PolicyError("artifact digest must be lowercase SHA-256")
    if not candidate.build_run_id:
        raise PolicyError("build run identity is required")

    required = {"tests", "static-analysis", "artifact-integrity"}
    valid = {
        item.name
        for item in candidate.evidence
        if item.passed and item.subject_digest == candidate.artifact_digest
    }
    missing = required - valid
    if missing:
        raise PolicyError(f"missing artifact evidence: {sorted(missing)}")


def plan_deployment(
    candidate: ReleaseCandidate,
    environment: Environment,
    *,
    initiator: str,
    approver: str | None = None,
) -> DeploymentPlan:
    verify_candidate(candidate)
    if environment.name == "production":
        if not candidate.staging_verified:
            raise PolicyError("production requires staging verification")
        if approver is None:
            raise PolicyError("production requires approval")
        if approver == initiator:
            raise PolicyError("production approval must be independent")

    return DeploymentPlan(
        environment=environment.name,
        expected_current_digest=environment.current_digest,
        target_digest=candidate.artifact_digest,
        rollback_digest=environment.current_digest,
        initiator=initiator,
        approver=approver,
    )


def apply_deployment(
    plan: DeploymentPlan,
    environment: Environment,
    artifacts: Mapping[str, bytes],
) -> None:
    if environment.name != plan.environment:
        raise PolicyError("plan names a different environment")
    if environment.current_digest != plan.expected_current_digest:
        raise PolicyError("environment changed after planning")

    try:
        content = artifacts[plan.target_digest]
    except KeyError as error:
        raise PolicyError("target artifact is unavailable") from error
    if digest(content) != plan.target_digest:
        raise PolicyError("stored artifact failed integrity verification")

    environment.current_digest = plan.target_digest
    environment.history.append(plan.target_digest)


def verify_deployment(
    plan: DeploymentPlan,
    environment: Environment,
    health_check: Callable[[], bool],
) -> None:
    if environment.current_digest != plan.target_digest:
        raise PolicyError("target digest is not currently deployed")
    if not health_check():
        raise PolicyError("post-deployment verification failed")


def rollback(
    plan: DeploymentPlan,
    environment: Environment,
    artifacts: Mapping[str, bytes],
) -> None:
    if environment.current_digest != plan.target_digest:
        raise PolicyError("refusing rollback from unexpected state")
    if plan.rollback_digest is None:
        raise PolicyError("no rollback artifact was recorded")
    content = artifacts.get(plan.rollback_digest)
    if content is None or digest(content) != plan.rollback_digest:
        raise PolicyError("rollback artifact is unavailable or corrupt")

    environment.current_digest = plan.rollback_digest
    environment.history.append(plan.rollback_digest)


class PipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.previous_content = b"application version 1\n"
        self.candidate_content = b"application version 2\n"
        self.previous_digest = digest(self.previous_content)
        self.candidate_digest = digest(self.candidate_content)
        self.artifacts = {
            self.previous_digest: self.previous_content,
            self.candidate_digest: self.candidate_content,
        }
        self.candidate = ReleaseCandidate(
            source_revision="a" * 40,
            artifact_digest=self.candidate_digest,
            build_run_id="build-1842",
            evidence=tuple(
                Evidence(name, self.candidate_digest, True)
                for name in (
                    "tests",
                    "static-analysis",
                    "artifact-integrity",
                )
            ),
        )

    def test_same_digest_moves_through_staging_and_production(self) -> None:
        staging = Environment("staging", self.previous_digest, [])
        staging_plan = plan_deployment(
            self.candidate,
            staging,
            initiator="release-bot",
        )
        apply_deployment(staging_plan, staging, self.artifacts)
        verify_deployment(staging_plan, staging, lambda: True)

        approved = replace(self.candidate, staging_verified=True)
        production = Environment("production", self.previous_digest, [])
        production_plan = plan_deployment(
            approved,
            production,
            initiator="release-bot",
            approver="operator-a",
        )
        apply_deployment(production_plan, production, self.artifacts)
        verify_deployment(production_plan, production, lambda: True)

        self.assertEqual(staging.current_digest, self.candidate_digest)
        self.assertEqual(production.current_digest, self.candidate_digest)

    def test_evidence_for_another_artifact_is_rejected(self) -> None:
        substituted = replace(
            self.candidate,
            evidence=(
                Evidence("tests", self.previous_digest, True),
                *self.candidate.evidence[1:],
            ),
        )
        with self.assertRaisesRegex(PolicyError, "tests"):
            verify_candidate(substituted)

    def test_production_rejects_self_approval(self) -> None:
        approved = replace(self.candidate, staging_verified=True)
        production = Environment("production", self.previous_digest, [])
        with self.assertRaisesRegex(PolicyError, "independent"):
            plan_deployment(
                approved,
                production,
                initiator="operator-a",
                approver="operator-a",
            )

    def test_apply_rejects_state_changed_after_plan(self) -> None:
        staging = Environment("staging", self.previous_digest, [])
        plan = plan_deployment(
            self.candidate,
            staging,
            initiator="release-bot",
        )
        staging.current_digest = digest(b"unexpected concurrent release\n")
        with self.assertRaisesRegex(PolicyError, "changed after planning"):
            apply_deployment(plan, staging, self.artifacts)

    def test_failed_health_check_rolls_back_recorded_digest(self) -> None:
        production = Environment("production", self.previous_digest, [])
        approved = replace(self.candidate, staging_verified=True)
        plan = plan_deployment(
            approved,
            production,
            initiator="release-bot",
            approver="operator-a",
        )
        apply_deployment(plan, production, self.artifacts)

        with self.assertRaisesRegex(PolicyError, "verification failed"):
            verify_deployment(plan, production, lambda: False)
        rollback(plan, production, self.artifacts)

        self.assertEqual(production.current_digest, self.previous_digest)
        self.assertEqual(
            production.history,
            [self.candidate_digest, self.previous_digest],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

Save it as `test_pipeline.py` in a disposable directory and run:

```bash
python -m unittest -v test_pipeline.py
```

The simulation never rebuilds during promotion. Every evidence item, plan, integrity check, deployment, and rollback names a digest. The expected-current-digest check prevents a stale plan from overwriting an environment changed by another run.

Real systems need durable, transactional release records and platform-specific deployment adapters. The example isolates the lifecycle invariants those adapters must preserve.

## 22. Build the pipeline in safe increments

Adopt the lifecycle gradually:

1. make local `verify` deterministic and required for review;
2. run untrusted change checks without secrets;
3. build one artifact from the integrated immutable revision;
4. store and verify its digest and provenance;
5. deploy that digest to an isolated staging environment;
6. automate bounded post-deployment evidence;
7. add protected production promotion and tested rollback;
8. introduce progressive rollout and automatic stop conditions;
9. measure lead time, failure rate, recovery time, and toil;
10. remove obsolete manual paths and credentials.

At each step, retain a working recovery path. Do not add automatic production authority before the artifact identity, evidence, and rollback boundaries are trustworthy.

## 23. Audit the whole path

Periodically trace one deployed instance backward:

```text
running digest
-> deployment record
-> approved plan
-> stored artifact
-> verified provenance
-> build run
-> immutable source revision
-> review and required checks
```

Then trace recovery forward: detect failure, stop rollout, identify prior compatible artifact, authorize rollback, deploy, verify, and reconcile.

The audit fails if any link relies on a mutable name, expired evidence, inaccessible artifact, undocumented credential, or manual step no one can reproduce.

## Common Misconceptions

- “CI passing means the release is safe.” CI samples behavior; deployment adds environment and operational risk.
- “A tag is immutable.” Many systems allow tags to move unless policy prevents it.
- “Staging tested the source.” Production must receive the same artifact digest, not a rebuild.
- “Provenance proves secure software.” It supports origin and process verification, not absence of defects.
- “Rollback means deploy the old code.” Data, dependencies, and external contracts may no longer be compatible.
- “Secrets are safe because logs mask them.” The job process still has their authority.

## Core Computer Science Concept

A CI/CD lifecycle is a **chain of custody over immutable identities**. Each state transition consumes named evidence and authority, then emits a new durable record without changing the artifact being promoted.

## Engineering Connections

- Required checks compose the test and static-analysis evidence from Chapter 73.
- Operation identity, expected state, and rollback reuse Chapter 74's recovery protocol.
- Build-once promotion depends on Chapter 75's reproducible task and artifact model.
- Environment concurrency and stale-plan rejection apply Chapter 76's ownership principles.
- Artifact provenance creates the supply-chain foundation for container images in Part VII.

## From the Field

A team tests a package in staging, then rebuilds from the release branch for production. The rebuild downloads a compromised dependency version published minutes later. Every staging check is green, but none applies to the production digest. Building once with locked inputs and promoting the verified digest would have preserved the evidence chain.

## Engineering Review

### What problem does this solve?

It moves a source change into an environment while preserving exactly which revision, artifact, evidence, authority, and recovery decision applied.

### Why was it designed this way?

Immutable identities prevent substitution, separated trust zones limit compromise, protected promotion binds authority to evidence, and post-deployment checks close the loop.

### When should I use it?

Use this lifecycle for every maintained software or infrastructure artifact that is built, published, or deployed through automation.

### When should I avoid it?

Avoid automatic production promotion until checks, identity, observability, stop conditions, and recovery meet the consequence of failure.

### How does this make me a better engineer?

It teaches you to design delivery as a stateful, security-sensitive system rather than a list of commands in YAML.

### How does this reduce waste?

It removes rebuild drift, manual release reconstruction, overprivileged jobs, duplicated workflows, slow incident attribution, and untested rollback procedures.

## Handbook Principle #77

> Build once from reviewed source, attach evidence to the digest, promote through explicit trust boundaries, and recover using artifacts already known by identity.

## Practical Observation

Run the example and print the staging and production histories. Then substitute one evidence digest, change the environment after planning, corrupt the artifact bytes, and reuse the initiator as approver. Confirm each defect is rejected before or during the exact transition it violates.

## Looking Ahead

Part VI has moved stable work from manual commands into tested, observable, recoverable automation and a complete delivery lifecycle. Part VII begins by explaining what container isolation actually provides—and what an image, runtime, and host kernel still share.

## References

- [SLSA v1.2 specification](https://slsa.dev/spec/v1.2/)
- [SLSA v1.2 — Verifying artifacts](https://slsa.dev/spec/v1.2/verifying-artifacts)
- [NIST SP 800-218 — Secure Software Development Framework](https://csrc.nist.gov/pubs/sp/800/218/final)
- [NIST SP 800-204D — Software Supply Chain Security in CI/CD Pipelines](https://csrc.nist.gov/pubs/sp/800/204/d/final)
- [GitHub Actions — Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use)
- [GitHub Actions — Artifact attestations](https://docs.github.com/en/actions/concepts/security/artifact-attestations)
- [GitHub Actions — Deployments and environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments)
- [OpenID Connect Core 1.0](https://openid.net/specs/openid-connect-core-1_0.html)
