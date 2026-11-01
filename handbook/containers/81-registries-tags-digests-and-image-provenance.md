# Chapter 81 — Registries, Tags, Digests, and Image Provenance

A registry reference can look like a stable image identity while naming a mutable tag. A scanner can report no known critical vulnerabilities while describing yesterday's tag, an incomplete package inventory, or an artifact built by an untrusted workflow.

The central idea is:

> Use tags for human navigation, digests for immutable identity, and verified subject-bound evidence for trust and promotion decisions.

## 1. Parse the distribution name

A full image reference can contain:

```text
registry.example.com/team/service:release
|__________________| |__________| |_____|
      registry        repository    tag
```

or an immutable digest:

```text
registry.example.com/team/service@sha256:<manifest-digest>
```

The **registry** provides the distribution service. A **repository** is a named collection within it. A **tag** is a repository-scoped label. A **digest** is a content identity.

Client defaults can fill an omitted registry, namespace, or tag. In production policy and audit evidence, write the full registry and repository and avoid implicit `latest` resolution.

## 2. Tags are mutable references

A tag maps a name to a manifest digest. Publishing a new manifest under the same tag changes what later pulls resolve.

Useful tag conventions include:

- release version, such as `2.4.1`;
- update channel, such as `stable`;
- source abbreviation, such as `git-a1b2c3d`;
- environment pointer, such as `staging-approved`.

None is immutable merely because the name looks precise. Registry policy may prohibit movement for selected tags, but that is an enforced repository rule, not a property of tag syntax.

Record the digest immediately after resolving a tag. Logs that contain only `service:stable` cannot prove which bytes ran after the tag moves.

## 3. Digests identify exact manifest bytes

A digest has an algorithm and encoded value:

```text
sha256:4f7c...e921
```

When a client requests a manifest by digest, it should verify that the returned bytes hash to that digest. The manifest then supplies verified descriptors for its configuration and layers.

A digest-pinned reference protects against tag movement and in-transit substitution when verification is performed. It does not establish:

- repository ownership;
- builder identity;
- source revision;
- vulnerability status;
- license acceptability;
- runtime safety.

Those are separate evidence and policy questions.

## 4. Pull an object graph, not one archive

An OCI Distribution pull commonly retrieves:

1. a manifest or index by tag or digest;
2. the selected platform manifest when an index is returned;
3. the image configuration;
4. each referenced layer blob;
5. optional related artifacts such as signatures, provenance, or SBOMs.

Clients advertise supported manifest media types. They must validate returned content types and descriptors rather than guessing from a filename.

Registries can redirect blob downloads to object storage. Authentication and TLS policy must cover the complete redirect path without forwarding credentials to an unintended host.

## 5. Push content before its manifest

Distribution protocols typically upload missing blobs first and the manifest last. The manifest becomes the graph root only after every referenced blob is available.

Content-addressed blob upload supports safe retry and deduplication: if the registry already has the exact digest, another upload may be unnecessary. The client must still verify server responses and handle interrupted upload sessions under the registry contract.

Publishing a manifest is a state transition. Confirm the returned digest matches the uploaded bytes, then attach intended tags. Do not infer success from the absence of a client exception alone.

## 6. Separate authentication from authorization

Registry authentication establishes a client identity. Authorization decides which actions that identity may perform against which repositories.

Useful scopes are narrow:

- pull a defined repository;
- push blobs and manifests to a build repository;
- create selected release tags;
- attach referrer artifacts;
- delete tags or manifests under retention policy;
- administer repository policy.

A build job that pushes candidates does not need delete or registry-administration authority. A production node that only pulls one repository does not need a general registry credential.

Prefer short-lived workload identity over long-lived passwords copied into CI variables or node files. Rotate and revoke credentials independently of image tags.

## 7. Keep credential paths out of artifacts

Registry clients can read credentials from helpers, platform identity, or configuration files. Protect these paths and prevent them from entering:

- build contexts;
- image layers and configuration;
- command-line arguments visible to other processes;
- shell history;
- CI logs and debug bundles;
- published cache records.

Logging out may remove one local token but not copies already exposed elsewhere. Incident response must revoke the credential at its issuer and investigate use.

Trusting a registry's TLS certificate authenticates the service endpoint. It does not authorize every repository publisher or every artifact stored there.

## 8. Record index and platform-manifest identity

A multi-platform reference can resolve to an image index digest. The client selects a platform-specific manifest with its own digest.

Record both when diagnosing or auditing:

```text
index digest: identifies the published platform set
platform: linux/amd64
manifest digest: identifies the selected runnable image
```

Updating one platform changes the index digest even when another platform's manifest remains identical. Conversely, two hosts pulling the same index can run different manifest digests by design.

Policy should state whether it approves the complete index, individual platform manifests, or both.

## 9. Promote content; do not rebuild it

Promotion should make an already verified digest available under a release repository, environment tag, or policy record. It must not invoke the build again.

A safe flow is:

```text
build candidate -> verify digest and evidence
-> deploy same digest to staging
-> record staging result
-> authorize production
-> copy/mount/tag same digest for production
```

Cross-repository promotion may copy manifest and blobs, mount shared blobs, or update a registry-side reference. Verify the destination digest after the operation.

An environment tag can remain useful for humans, but the deployment record and runtime specification should retain the approved digest.

## 10. Retention follows references and policy

Deleting a tag removes a name. It may not remove the manifest, layers, related artifacts, local caches, or deployed containers.

Deleting a manifest by digest can affect every tag and index that references it. Registries vary in deletion support and garbage-collection timing.

Retention should account for:

- active deployments and rollback candidates;
- incident and audit windows;
- signatures, provenance, SBOMs, and scan reports;
- legal holds and data classification;
- shared blobs referenced by other manifests;
- failed and untagged candidate cleanup;
- replication and backup lag.

Never prune solely by tag age without resolving live digest references from deployment systems.

## 11. Scan an immutable subject

Vulnerability scanning compares an inventory with vulnerability intelligence and policy. Scan by digest and record:

- subject digest and platform;
- scanner and rule version;
- vulnerability database version or update time;
- inventory source and completeness;
- scan time;
- severity and exception policy;
- remediation or VEX context.

A scan is a point-in-time observation. An artifact can become affected when new vulnerability information appears without its bytes changing.

Rescan deployed digests continuously or on intelligence updates. Do not publish a new image merely to obtain a fresh report about identical bytes.

## 12. Understand scanning limits

An image scanner may miss or misclassify:

- statically linked or vendored components;
- files installed outside package-manager databases;
- dynamically downloaded runtime plugins;
- language packages without recognizable metadata;
- unreachable versus reachable vulnerable code;
- runtime configuration and exposed services;
- host-kernel vulnerabilities;
- credentials, malware, or logic defects.

Severity is not business impact. Prioritize using exploitability, reachability, exposure, compensating controls, asset importance, and remediation risk.

A “zero critical findings” gate is only as strong as inventory, intelligence freshness, matching accuracy, and exception governance.

## 13. An SBOM is inventory evidence

A software bill of materials is a machine-readable inventory of components and relationships. It can support:

- vulnerability response;
- license and policy review;
- dependency discovery;
- customer transparency;
- incident scoping;
- comparison between releases.

Bind the SBOM to the image digest and record its generation context. A source SBOM, build SBOM, and post-build binary-analysis SBOM observe different inputs and can contain different components.

An SBOM is not a vulnerability report, signature, provenance statement, or guarantee of completeness. Validate both its format and its correspondence with the subject artifact.

## 14. VEX adds vulnerability status context

A Vulnerability Exploitability eXchange statement can express whether a product is affected by a vulnerability and why. It may distinguish:

- affected;
- not affected with justification;
- fixed;
- under investigation.

VEX does not erase the component or vulnerability from an SBOM. It adds supplier or analyst context that consumers evaluate under their own trust policy.

Bind VEX to specific product identities and versions, authenticate its issuer, retain its timestamp, and reassess it when code, configuration, or vulnerability knowledge changes.

## 15. Signatures authenticate claims

A digital signature can authenticate that a key or identity made a claim over a digest. Verification needs:

- the exact signed subject;
- accepted signature and envelope formats;
- a trusted key or identity root;
- certificate and issuer constraints where applicable;
- validity, revocation, and transparency evidence;
- a policy for which signer may authorize which repository and workflow.

“Signature valid” is incomplete. A valid signature from an unrelated developer does not authorize a production image.

Keyless systems can bind a short-lived certificate to workload identity claims. Consumers still need to constrain issuer, subject identity, repository, workflow, and source reference.

## 16. Attestations make typed statements

An attestation is an authenticated statement whose predicate describes a claim about a subject. Examples include:

- build provenance;
- SBOM;
- vulnerability scan result;
- test result;
- policy evaluation.

Verification must check that the attestation subject digest equals the artifact being consumed. Then verify the envelope and evaluate the predicate type, schema, issuer, builder, parameters, and freshness against expectations.

Do not accept unknown predicate fields or types silently in a privileged gate. A signed but misunderstood statement is not useful evidence.

## 17. Provenance links artifact to build

Build provenance can describe:

- artifact subject digest;
- builder identity;
- build type and invocation parameters;
- source repository and revision;
- resolved dependencies;
- build timing and environment claims.

The consumer should compare these claims with a preconfigured expectation: approved builder, canonical repository, protected source reference, allowed build definition, and recognized parameters.

Provenance generated and signed by arbitrary build code is weaker than provenance generated by a trusted build platform outside the build's control.

Provenance supports traceability and tamper detection. It does not prove tests were sufficient or source was free of malicious logic.

## 18. Attach related artifacts by subject

OCI registries can expose referrers whose manifests name a subject digest. This supports storing signatures, attestations, and SBOMs alongside the image without modifying its manifest.

Related artifacts are independent content-addressed objects. Updating a scan report need not change the image digest.

Discovery is not verification. A malicious publisher can attach a false statement to a public subject. Consumers must verify the referrer's digest, media type, subject binding, signature, issuer, and predicate policy.

Retention and replication should keep required referrers available with the subject image.

## 19. Define the admission policy

Before deployment, a consumer can require:

- a fully qualified digest reference;
- approved registry and repository;
- allowed operating system and architecture;
- verified provenance from an approved builder;
- canonical source repository and permitted revision;
- SBOM tied to the same digest;
- vulnerability report within a freshness window;
- no unexpired policy-blocking findings;
- required signatures and transparency evidence;
- runtime configuration constraints from Chapter 78.

Fail closed on missing or unverifiable required evidence. Record the policy version and verification result so later audits explain why the digest was admitted.

Keep emergency exceptions narrow, expiring, attributable, and visible. An exception should not silently become the permanent release path.

## 20. Complete example: tags, promotion, and evidence binding

This standard-library simulation models repository-scoped tags over immutable manifest bytes. It verifies content on every pull and applies a release policy to already-authenticated evidence. Cryptographic envelope verification is intentionally outside the model; production code must perform it before constructing authenticated evidence:

```python
from __future__ import annotations

import hashlib
import unittest
from dataclasses import dataclass


class RegistryError(RuntimeError):
    pass


class PolicyError(RuntimeError):
    pass


def digest(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


class InMemoryRegistry:
    def __init__(self) -> None:
        self.manifests: dict[tuple[str, str], bytes] = {}
        self.tags: dict[tuple[str, str], str] = {}

    def push(self, repository: str, content: bytes, *, tag: str | None = None) -> str:
        identity = digest(content)
        self.manifests[(repository, identity)] = content
        if tag is not None:
            self.tags[(repository, tag)] = identity
        return identity

    def tag(self, repository: str, identity: str, tag: str) -> None:
        if (repository, identity) not in self.manifests:
            raise RegistryError("manifest is not present in repository")
        self.tags[(repository, tag)] = identity

    def resolve(self, repository: str, tag_or_digest: str) -> str:
        if tag_or_digest.startswith("sha256:"):
            identity = tag_or_digest
        else:
            try:
                identity = self.tags[(repository, tag_or_digest)]
            except KeyError as error:
                raise RegistryError("tag not found") from error
        if (repository, identity) not in self.manifests:
            raise RegistryError("manifest not found")
        return identity

    def pull(self, repository: str, tag_or_digest: str) -> tuple[str, bytes]:
        identity = self.resolve(repository, tag_or_digest)
        content = self.manifests[(repository, identity)]
        if digest(content) != identity:
            raise RegistryError("manifest digest verification failed")
        return identity, content

    def promote(
        self,
        *,
        source_repository: str,
        identity: str,
        target_repository: str,
        target_tag: str,
    ) -> str:
        verified_identity, content = self.pull(source_repository, identity)
        destination_identity = self.push(
            target_repository,
            content,
            tag=target_tag,
        )
        if destination_identity != verified_identity:
            raise RegistryError("promotion changed manifest identity")
        return destination_identity


@dataclass(frozen=True)
class AuthenticatedEvidence:
    kind: str
    subject_digest: str
    issued_at: int
    issuer: str
    claims: tuple[tuple[str, str], ...]

    def claim(self, name: str) -> str | None:
        return dict(self.claims).get(name)


@dataclass(frozen=True)
class ReleasePolicy:
    expected_builder: str
    expected_source_repository: str
    expected_source_revision: str
    maximum_scan_age: int


def authorize_release(
    identity: str,
    evidence: tuple[AuthenticatedEvidence, ...],
    policy: ReleasePolicy,
    *,
    now: int,
) -> None:
    by_kind: dict[str, AuthenticatedEvidence] = {}
    for item in evidence:
        if item.kind in by_kind:
            raise PolicyError(f"duplicate evidence kind: {item.kind}")
        if item.subject_digest != identity:
            raise PolicyError(f"{item.kind} names a different subject")
        by_kind[item.kind] = item

    required = {"provenance", "sbom", "vulnerability-scan"}
    missing = required - set(by_kind)
    if missing:
        raise PolicyError(f"missing evidence: {sorted(missing)}")

    provenance = by_kind["provenance"]
    if provenance.issuer != policy.expected_builder:
        raise PolicyError("unapproved provenance issuer")
    if provenance.claim("source_repository") != policy.expected_source_repository:
        raise PolicyError("unexpected source repository")
    if provenance.claim("source_revision") != policy.expected_source_revision:
        raise PolicyError("unexpected source revision")

    sbom = by_kind["sbom"]
    if sbom.claim("generation_context") != "build":
        raise PolicyError("release requires a build-time SBOM")

    scan = by_kind["vulnerability-scan"]
    age = now - scan.issued_at
    if age < 0 or age > policy.maximum_scan_age:
        raise PolicyError("vulnerability scan is outside the freshness window")
    if scan.claim("blocking_findings") != "0":
        raise PolicyError("vulnerability policy has blocking findings")


class RegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = InMemoryRegistry()
        self.first = self.registry.push(
            "candidate/service",
            b'{"schemaVersion":2,"version":1}',
            tag="stable",
        )
        self.second = self.registry.push(
            "candidate/service",
            b'{"schemaVersion":2,"version":2}',
        )
        self.policy = ReleasePolicy(
            expected_builder="builder.example/workflow/release",
            expected_source_repository="https://example.invalid/service",
            expected_source_revision="a" * 40,
            maximum_scan_age=3_600,
        )

    def evidence_for(self, identity: str) -> tuple[AuthenticatedEvidence, ...]:
        return (
            AuthenticatedEvidence(
                "provenance",
                identity,
                9_000,
                "builder.example/workflow/release",
                (
                    ("source_repository", "https://example.invalid/service"),
                    ("source_revision", "a" * 40),
                ),
            ),
            AuthenticatedEvidence(
                "sbom",
                identity,
                9_000,
                "builder.example/workflow/release",
                (("generation_context", "build"),),
            ),
            AuthenticatedEvidence(
                "vulnerability-scan",
                identity,
                9_500,
                "scanner.example/policy/default",
                (("blocking_findings", "0"),),
            ),
        )

    def test_moving_tag_does_not_change_old_digest_identity(self) -> None:
        self.registry.tag("candidate/service", self.second, "stable")

        current, _ = self.registry.pull("candidate/service", "stable")
        original, content = self.registry.pull("candidate/service", self.first)

        self.assertEqual(current, self.second)
        self.assertEqual(original, self.first)
        self.assertIn(b'"version":1', content)

    def test_promotion_preserves_verified_digest(self) -> None:
        promoted = self.registry.promote(
            source_repository="candidate/service",
            identity=self.second,
            target_repository="release/service",
            target_tag="production",
        )

        resolved, _ = self.registry.pull("release/service", "production")
        self.assertEqual(promoted, self.second)
        self.assertEqual(resolved, self.second)

    def test_corrupted_registry_content_is_rejected(self) -> None:
        self.registry.manifests[("candidate/service", self.first)] += b"tampered"
        with self.assertRaisesRegex(RegistryError, "digest verification"):
            self.registry.pull("candidate/service", self.first)

    def test_evidence_must_name_the_promoted_subject(self) -> None:
        wrong = list(self.evidence_for(self.second))
        wrong[1] = AuthenticatedEvidence(
            "sbom",
            self.first,
            9_000,
            "builder.example/workflow/release",
            (("generation_context", "build"),),
        )

        with self.assertRaisesRegex(PolicyError, "different subject"):
            authorize_release(
                self.second,
                tuple(wrong),
                self.policy,
                now=10_000,
            )

    def test_stale_scan_is_rejected(self) -> None:
        with self.assertRaisesRegex(PolicyError, "freshness"):
            authorize_release(
                self.second,
                self.evidence_for(self.second),
                self.policy,
                now=20_000,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

Run it in a disposable directory:

```bash
python -m unittest -v test_registry_policy.py
```

`AuthenticatedEvidence` represents a statement whose envelope, signature, certificate, and identity constraints have already been verified by a trusted implementation. Do not replace cryptographic verification with a Boolean field supplied by an artifact publisher.

The in-memory registry omits authentication, media-type negotiation, blobs, indexes, referrers, concurrency, conditional requests, and retention. Its purpose is to make tag movement, digest verification, promotion, and subject binding directly testable.

## 21. Verify before deployment

A production consumer should perform this order:

1. accept a fully qualified registry and repository under policy;
2. resolve the requested tag only as user intent;
3. obtain and verify the manifest or index digest;
4. select and record the target platform manifest;
5. verify descriptors and pull content by digest;
6. discover required related artifacts by subject digest;
7. authenticate signatures and attestation envelopes;
8. compare provenance and evidence with preconfigured expectations;
9. evaluate freshness, vulnerability, license, and exception policy;
10. admit and deploy the verified digest;
11. record index, platform manifest, policy, and environment result.

Verification should happen outside artifact-controlled code. A script inside the image cannot be trusted to approve its own image.

## 22. Respond to a compromised image

When an image or publisher is compromised:

- stop promotion and new pulls under affected identities;
- identify every tag, digest, platform, and referrer involved;
- find deployments by digest rather than current tag value;
- revoke publisher credentials and signing identity as appropriate;
- preserve registry, transparency, build, and deployment evidence;
- build a repaired artifact from reviewed source and clean infrastructure;
- verify and deploy the new digest;
- retire affected tags and manifests under retention and legal policy;
- rescan retained and deployed related digests;
- document consumers that cannot yet enforce the new policy.

Moving a tag away from the compromised digest helps future tag pulls but does not replace already cached or deployed content.

## Common Misconceptions

- “A version-looking tag is immutable.” Tags are mutable unless repository policy enforces otherwise.
- “A digest proves the image is trusted.” It proves exact bytes, not origin or acceptability.
- “A valid signature means deploy.” The signer and claim still need authorization under policy.
- “An SBOM proves no vulnerabilities.” It is inventory evidence and may be incomplete.
- “A clean scan remains clean.” Vulnerability intelligence changes while the digest remains fixed.
- “Deleting a tag deletes the image everywhere.” Manifests, blobs, caches, deployments, and referrers can remain.

## Core Computer Science Concept

Registry distribution separates **mutable naming from immutable content addressing**. Trust is a policy evaluation over authenticated statements bound to the immutable subject, not a property of the convenient name.

## Engineering Connections

- Registry pulls traverse the content-addressed image graph from Chapter 79.
- Promotion by digest applies Chapter 77's build-once release chain.
- Short-lived registry identity and scoped permissions apply least authority from Part VI.
- Scan freshness is cache invalidation over changing vulnerability intelligence.
- Subject-bound attestations turn operational evidence into typed, verifiable data.

## From the Field

A deployment approves `service:stable` after a scan, then resolves the tag again during rollout. Another pipeline moves `stable` between those events. Production receives a digest the scanner never evaluated. Resolving once, binding evidence to that digest, and deploying the same digest would have closed the time-of-check/time-of-use gap.

## Engineering Review

### What problem does this solve?

It preserves exact image identity and verifiable supply-chain evidence across naming, distribution, promotion, deployment, retention, and incident response.

### Why was it designed this way?

Mutable tags support human workflows, content addressing supports integrity and deduplication, and subject-bound attestations support independent policy decisions.

### When should I use it?

Use these controls for every image that crosses a machine, team, environment, registry, or trust boundary.

### When should I avoid it?

Avoid treating optional or unverifiable evidence as a mandatory gate; first establish trustworthy generation, verification, ownership, and recovery.

### How does this make me a better engineer?

It teaches you to distinguish identity, origin, inventory, vulnerability observation, authorization, and naming instead of compressing them into “trusted image.”

### How does this reduce waste?

It prevents tag races, redundant rebuilds, ambiguous deployments, stale scan decisions, orphaned evidence, unsafe pruning, and slow compromise scoping.

## Handbook Principle #81

> Resolve names once, verify bytes and evidence by digest, and promote the same authenticated subject through every environment.

## Practical Observation

Run the registry-policy lab. Move `stable` from the first manifest to the second and confirm that the old digest still retrieves its original bytes. Promote the second digest, then substitute the first digest into its SBOM evidence and advance the policy clock until the scan expires. Confirm both admissions fail.

## Looking Ahead

Verified images eventually become running processes. Chapter 82 follows the container's initial process through entrypoint composition, PID 1 behavior, signals, readiness, shutdown, restart, exit status, and cleanup.

## References

- [OCI Distribution Specification](https://github.com/opencontainers/distribution-spec/blob/main/spec.md)
- [OCI Image Format Specification](https://github.com/opencontainers/image-spec)
- [OCI Image Manifest Specification](https://github.com/opencontainers/image-spec/blob/main/manifest.md)
- [SLSA v1.2 — Provenance](https://slsa.dev/spec/v1.2/provenance)
- [SLSA v1.2 — Verifying artifacts](https://slsa.dev/spec/v1.2/verifying-artifacts)
- [Sigstore Cosign — Verifying signatures](https://docs.sigstore.dev/cosign/verifying/verify/)
- [CISA — Minimum Elements for an SBOM](https://www.cisa.gov/sites/default/files/2025-08/2025_CISA_SBOM_Minimum_Elements.pdf)
- [NIST SP 800-190 — Application Container Security Guide](https://csrc.nist.gov/pubs/sp/800/190/final)
