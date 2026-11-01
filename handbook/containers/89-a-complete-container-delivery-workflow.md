# Chapter 89 — A Complete Container Delivery Workflow

A successful image build is not a release. A releasable container has traceable source, tested contents, policy evidence, immutable registry identity, constrained runtime configuration, verified service behavior, observable failure handling, rollback evidence, and an owner after deployment.

The central idea is:

> Promote one verified digest through explicit gates, prove the running process and data lifecycle under failure, and retain enough evidence to reproduce, roll back, and retire the release safely.

## 1. Define the delivery contract before building

For one release, identify:

- source repository, immutable revision, and clean-tree policy;
- reviewed Dockerfile and build context;
- pinned base images and dependency locks;
- builder identity and provenance requirements;
- test suites and required results;
- SBOM, vulnerability, license, and policy gates;
- registry repository and immutable promotion rules;
- runtime identity, limits, mounts, networks, and secrets;
- health and acceptance checks;
- rollout and rollback conditions;
- persistent-data compatibility and recovery;
- logging, metrics, events, and evidence retention;
- owner, approval, expiration, and patch policy.

The contract turns “ship the container” into a sequence of claims that can fail independently.

## 2. Use one release identity across every stage

A useful release record connects:

```text
source revision
  -> build invocation and builder
  -> image index and platform-manifest digests
  -> provenance and SBOM attestations
  -> test and policy results
  -> promoted registry reference by digest
  -> runtime configuration digest
  -> deployed workload and observed image identity
  -> acceptance, rollback, and retirement evidence
```

Tags remain useful labels, but the digest is the immutable artifact identity. Record both the multi-platform index digest and the selected platform manifest when those distinctions matter.

Do not rebuild separately for test, staging, and production. Promote the tested artifact or prove why a platform-specific output belongs to the same attested build.

## 3. Keep source state reproducible

Before a release build:

- require an immutable commit;
- reject untracked or modified release inputs;
- include Dockerfile, lockfiles, configuration schema, and tests in review;
- keep generated artifacts reproducible or attested;
- record submodule and external-source revisions;
- minimize `.dockerignore` exceptions;
- prevent local credentials and build outputs from entering context;
- tag the source only after release evidence is complete according to policy.

A source revision does not identify undeclared files copied from a developer workstation. Inspect the effective build context.

## 4. Pin every build input that affects output

Pin:

- base image digests;
- language and operating-system dependencies through supported lock mechanisms;
- compiler and package-manager versions;
- downloaded tools by version and digest or signature;
- build frontend and external build stages;
- target platform;
- locale, time zone, and source-date behavior where relevant.

Some outputs contain timestamps, compression variation, signatures, or registry-generated metadata, so byte-for-byte reproducibility requires more than pinning. Provenance records how the output was produced even when deterministic rebuilding is not yet achieved.

## 5. Test before creating a runtime artifact

Run cheap, deterministic gates first:

1. formatting and static analysis;
2. unit and property tests;
3. dependency and secret checks;
4. build definition checks;
5. image build tests;
6. runtime contract tests;
7. multi-service integration tests;
8. security and vulnerability policy;
9. replacement, failure, and rollback tests.

Fail closed when required evidence is unavailable. A scanner outage is not a clean scan. Define an emergency exception workflow separately with scope, owner, expiration, and compensating controls.

## 6. Build with stages that express trust boundaries

The builder can contain compilers, headers, package managers, test tools, and source. The runtime stage should contain only the files and runtime support required to execute.

```text
source + locked inputs
        |
        v
builder/test stage -- test evidence --> gate
        |
        | copy selected outputs only
        v
minimal runtime stage --> image artifact
```

Do not copy the entire builder filesystem into the runtime stage. Do not leave package-manager caches, source-control metadata, test credentials, or build secrets in the final image.

## 7. A small application with explicit contracts

The integration example is a standard-library HTTP service. It exposes:

- `/healthz` for local process health;
- `/readyz` for local readiness;
- `/` for non-sensitive build and instance identity;
- `/protected` for a bearer-token authorization check.

Save as `app.py`:

```python
from __future__ import annotations

import hmac
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import signal
import socket
import sys
import time


def load_token(path: str) -> bytes:
    token = Path(path).read_bytes().strip()
    if not token:
        raise ValueError("token file is empty")
    return token


def authorized(header: str | None, expected: bytes) -> bool:
    prefix = "Bearer "
    if header is None or not header.startswith(prefix):
        return False
    supplied = header[len(prefix) :].encode("utf-8")
    return hmac.compare_digest(supplied, expected)


def emit(event: str, **fields: object) -> None:
    record = {
        "event": event,
        "time_unix": time.time(),
        **fields,
    }
    print(json.dumps(record, sort_keys=True), flush=True)


class Handler(BaseHTTPRequestHandler):
    token: bytes
    revision: str

    def log_message(self, format: str, *args: object) -> None:
        emit(
            "http_access",
            client=self.client_address[0],
            message=format % args,
        )

    def respond(self, status: HTTPStatus, payload: dict[str, object]) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8") + b"\n"
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in {"/healthz", "/readyz"}:
            self.respond(HTTPStatus.OK, {"status": "ok"})
            return
        if self.path == "/":
            self.respond(
                HTTPStatus.OK,
                {
                    "instance": socket.gethostname(),
                    "revision": self.revision,
                },
            )
            return
        if self.path == "/protected":
            if not authorized(self.headers.get("Authorization"), self.token):
                self.respond(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                return
            self.respond(HTTPStatus.OK, {"authorized": True})
            return
        self.respond(HTTPStatus.NOT_FOUND, {"error": "not_found"})


def main() -> None:
    token_path = os.environ.get("API_TOKEN_FILE", "/run/secrets/api_token")
    token = load_token(token_path)
    Handler.token = token
    Handler.revision = os.environ.get("SOURCE_REVISION", "unknown")
    server = ThreadingHTTPServer(("0.0.0.0", 8080), Handler)

    def request_stop(signal_number: int, frame: object) -> None:
        del frame
        emit("stop_requested", signal=signal_number)
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    emit("server_started", address="0.0.0.0", port=8080)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        emit("server_stopped")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        emit("startup_failed", error=type(error).__name__)
        sys.exit(1)
```

The service reads the token from a mounted file and never logs or returns it. Its root endpoint identifies the artifact revision without exposing environment or secrets.

## 8. Test the security-sensitive application functions

Save as `test_app.py`:

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app import authorized, load_token


class ApplicationTests(unittest.TestCase):
    def test_token_is_loaded_from_a_file(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "token"
            path.write_text("correct-token\n", encoding="utf-8")
            self.assertEqual(load_token(str(path)), b"correct-token")

    def test_empty_token_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "token"
            path.write_text("\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "empty"):
                load_token(str(path))

    def test_authorization_requires_exact_bearer_token(self) -> None:
        expected = b"correct-token"
        self.assertTrue(authorized("Bearer correct-token", expected))
        self.assertFalse(authorized("Bearer wrong-token", expected))
        self.assertFalse(authorized("Basic correct-token", expected))
        self.assertFalse(authorized(None, expected))


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

Run before the image build and again in the builder stage:

```bash
python -m unittest -v test_app.py
```

These tests do not replace endpoint, concurrency, shutdown, malformed-request, or penetration tests. They prove the credential boundary's smallest deterministic functions.

## 9. Build and test in a multi-stage Dockerfile

The build requires `BASE_IMAGE` to be a verified digest reference and records the source revision:

```dockerfile
# syntax=docker/dockerfile:1
ARG BASE_IMAGE

FROM ${BASE_IMAGE} AS test
WORKDIR /src
COPY app.py test_app.py ./
RUN python -m unittest -v test_app.py \
    && python -m compileall -q app.py

FROM ${BASE_IMAGE} AS runtime
ARG SOURCE_REVISION
LABEL org.opencontainers.image.revision="${SOURCE_REVISION}"
WORKDIR /app
RUN addgroup -S -g 10001 app \
    && adduser -S -D -H -u 10001 -G app app
COPY --from=test --chown=10001:10001 /src/app.py /app/app.py
USER 10001:10001
EXPOSE 8080
ENTRYPOINT ["python", "/app/app.py"]
```

This example expects an Alpine-based Python image, so its account-management commands are deliberately distribution-specific. If the approved base changes, review those commands instead of assuming compatibility.

The tests and test file do not enter the runtime stage. The Python runtime and its operating-system packages still do, so the SBOM and vulnerability policy must cover them.

## 10. Resolve and record the base digest

Resolve a reviewed tag to its registry digest, verify it against policy, then pass the immutable reference:

```bash
docker pull python:3.13-alpine
base_image="$(
  docker image inspect python:3.13-alpine \
    --format '{{index .RepoDigests 0}}'
)"
case "$base_image" in
  *@sha256:*) ;;
  *)
    printf 'base image is not digest-pinned: %s\n' "$base_image" >&2
    exit 1
    ;;
esac
printf 'BASE_IMAGE=%s\n' "$base_image"
```

Do not make an unreviewed tag-resolution step part of a release and call the result pinned. The resolved digest must pass source, age, provenance, vulnerability, and organizational base-image policy.

## 11. Build the candidate once into quarantine

An attested image normally needs an attestation-capable image store or registry. Build once into an isolated private repository or quarantine tag that is not deployable to production:

```bash
source_revision="$(git rev-parse HEAD)"
test -z "$(git status --porcelain)"
repository="registry.example.invalid/team/handbook-app"
candidate_tag="$repository:quarantine-git-$source_revision"

docker buildx build \
  --build-arg "BASE_IMAGE=$base_image" \
  --build-arg "SOURCE_REVISION=$source_revision" \
  --provenance=mode=max \
  --sbom=true \
  --tag "$candidate_tag" \
  --push \
  .
```

The `.invalid` registry is intentionally non-routable documentation. Use an approved quarantine repository or a disposable local registry; this handbook does not mutate a public registry.

Resolve the pushed result immediately with machine-readable output from a pinned registry client. Record the index digest and form:

```text
registry.example.invalid/team/handbook-app@sha256:<candidate-index-digest>
```

Call that value `candidate_ref`. From this point forward, tests and policy address the digest, not the quarantine tag.

## 12. Inventory and scan the final artifact

Policy should evaluate the runtime artifact, not only source lockfiles. It can include:

- SBOM generation and completeness;
- operating-system and language-package vulnerabilities;
- fix availability and exploitability evidence;
- prohibited licenses or components;
- embedded secrets and private keys;
- malware or organization-specific indicators;
- non-root default user;
- approved base-image provenance;
- required labels and attestations.

One Docker Scout example is:

```bash
docker scout cves \
  --exit-code \
  --only-severity critical,high \
  "$candidate_ref"
docker scout policy "$candidate_ref"
```

Tool availability, databases, policy bundles, exceptions, and output retention must be pinned and owned. Adapt command flags to the approved scanner version. Never interpret “no data” as compliant.

## 13. Verify provenance and SBOM on the registry subject

Build attestations attach to an image index. Verify that the selected builder, exporter, and registry preserved them. Required checks include:

- the attestation subject is `candidate_ref`;
- the provenance names the expected source revision;
- builder identity and parameters satisfy policy;
- material identities include the approved base and declared inputs;
- the SBOM covers the expected platform artifact;
- signatures or trusted workload identity verify;
- no secret appears in provenance, SBOM, or build logs.

A successful push without required attestations fails the release contract. Preserve verification output in the release packet.

## 14. Promote the same digest without rebuilding

Promotion is an authorization change, not another image build. Use registry-native immutable tagging, repository copy, or an admission allowlist that preserves the exact index digest. For example, inspect the candidate before promotion:

```bash
docker buildx imagetools inspect "$candidate_ref"
```

An approved release reference can be:

```text
registry.example.invalid/team/handbook-app@sha256:<index-digest>
```

If policy also requires a human-readable release tag, make the registry point that tag at the already approved manifest bytes, then resolve it and require the resulting digest to equal the candidate digest.

Retagging or copying can handle attached attestations and signatures differently across registries. Verify the release subject's referrers and policy after promotion. Rebuilding with a “production” tag creates another artifact and invalidates the candidate evidence.

## 15. Define the runtime model separately

This Compose model requires a digest reference and constrains runtime authority:

```yaml
services:
  app:
    image: "${IMAGE_REF:?set IMAGE_REF to an approved digest}"
    user: "10001:10001"
    read_only: true
    tmpfs:
      - /tmp:rw,nosuid,nodev,noexec,size=8m
    cap_drop: [ALL]
    security_opt: [no-new-privileges:true]
    pids_limit: 64
    mem_limit: 96m
    memswap_limit: 96m
    cpus: 0.50
    environment:
      SOURCE_REVISION: "${SOURCE_REVISION:?set SOURCE_REVISION}"
      API_TOKEN_FILE: /run/secrets/api_token
    secrets: [api_token]
    ports:
      - "127.0.0.1::8080"
    healthcheck:
      test:
        - CMD
        - python
        - -c
        - >-
          import urllib.request;
          urllib.request.urlopen(
          'http://127.0.0.1:8080/healthz', timeout=1).read()
      interval: 2s
      timeout: 2s
      retries: 10
      start_period: 2s
    stop_grace_period: 10s
    restart: on-failure:3
    logging:
      driver: local
      options:
        max-size: 10m
        max-file: "3"

secrets:
  api_token:
    file: "${API_TOKEN_FILE:?set API_TOKEN_FILE}"
```

The token file remains a local-Compose simulation whose host protection must be managed. A production platform needs its own secret storage, delivery, rotation, and audit contract.

The application has no durable state, so replacement is safe. Adding state would require Chapter 83's volume, backup, migration, and restore design before release.

## 16. Validate configuration before creating resources

With exact environment and file selection:

```bash
docker compose --project-name "$project" config --quiet
docker compose --project-name "$project" config --images
docker compose --project-name "$project" config > resolved-compose.yaml
```

Protect `resolved-compose.yaml`; it can reveal endpoints and configuration. Prefer a redacted digest plus restricted full evidence when sensitive values can be rendered.

Review:

- digest-only image identity;
- loopback-only publication;
- service user and security options;
- write paths and secret grants;
- resource and PID limits;
- health and stop timing;
- logging bounds;
- project name and external resources.

## 17. Use a unique disposable project for acceptance

For a safe local acceptance run:

```bash
suffix="$RANDOM-$$"
project="handbook-release-$suffix"
token_directory="$(mktemp -d "${TMPDIR:-/tmp}/handbook-token.XXXXXX")"
token_file="$token_directory/api-token"
printf 'local-acceptance-%s\n' "$suffix" > "$token_file"
chmod 600 "$token_file"

cleanup() {
  docker compose --project-name "$project" \
    down --volumes --remove-orphans >/dev/null 2>&1 || true
  case "$token_directory" in
    "${TMPDIR:-/tmp}"/handbook-token.*)
      rm -rf -- "$token_directory"
      ;;
  esac
}
trap cleanup EXIT

export API_TOKEN_FILE="$token_file"
export IMAGE_REF="$approved_digest_reference"
export SOURCE_REVISION="$source_revision"

docker compose --project-name "$project" config --quiet
docker compose --project-name "$project" \
  up --detach --wait --wait-timeout 60

endpoint="$(docker compose --project-name "$project" port app 8080)"
case "$endpoint" in
  127.0.0.1:*) ;;
  *)
    printf 'unexpected endpoint: %s\n' "$endpoint" >&2
    exit 1
    ;;
esac
```

The trap removes only the unique project and token directory. Confirm the active Docker context before running. The project has no durable application volume; `--volumes` is included to prove complete disposable cleanup.

## 18. Test the user-visible and protected paths

From the host:

```bash
curl --fail --silent --show-error "http://$endpoint/healthz"
curl --fail --silent --show-error "http://$endpoint/readyz"
curl --fail --silent --show-error "http://$endpoint/"

status="$(
  curl --silent --output /dev/null --write-out '%{http_code}' \
    "http://$endpoint/protected"
)"
test "$status" = "401"

curl --fail --silent --show-error \
  --header "Authorization: Bearer $(cat "$token_file")" \
  "http://$endpoint/protected"
```

Avoid putting real secrets on a command line. This disposable token makes the boundary visible; production acceptance should use a client that obtains short-lived credentials without exposing them through process arguments or logs.

Verify the response revision equals the source record. Verify logs do not contain the token.

## 19. Verify the running artifact and policy

Collect:

```bash
container_id="$(
  docker compose --project-name "$project" ps --quiet app
)"
docker inspect "$container_id" --format '{{.Image}}'
docker inspect "$container_id" --format '{{.Config.User}}'
docker inspect "$container_id" --format '{{.HostConfig.ReadonlyRootfs}}'
docker inspect "$container_id" --format '{{json .HostConfig.CapDrop}}'
docker inspect "$container_id" --format '{{json .HostConfig.SecurityOpt}}'
docker inspect "$container_id" --format '{{json .HostConfig.LogConfig}}'
docker inspect "$container_id" --format '{{json .State.Health}}'
docker stats --no-stream "$container_id"
```

Registry index digest, platform manifest digest, image configuration digest, and runtime `.Image` ID are related but not interchangeable. Use registry and runtime APIs that explicitly identify each, then link them in the release record.

Do not write a string comparison between different digest kinds and call the mismatch drift.

## 20. Prove replacement behavior

Capture the current container ID, then force reconciliation from the same model:

```bash
before="$container_id"
docker compose --project-name "$project" \
  up --detach --wait --wait-timeout 60 --force-recreate
after="$(docker compose --project-name "$project" ps --quiet app)"

test "$before" != "$after"
curl --fail --silent --show-error "http://$endpoint/healthz"
```

Rediscover the host port after recreation if it was allocated dynamically; it can change. The old `endpoint` variable is not a durable contract.

Verify the new instance reports the same approved revision, accepts the token, has no dependency on the old writable layer, and retains all runtime restrictions.

## 21. Inject bounded failures

In a disposable environment, test:

- process termination and restart-policy behavior;
- health-check failure and evidence;
- absent or unreadable secret at startup;
- port collision or publication misconfiguration;
- memory-limit OOM using Chapter 86's bounded worker, not this service;
- dependency timeout and retry behavior when dependencies exist;
- graceful stop within the declared timeout;
- registry unavailability after the image is present;
- replacement with no local instance state;
- logging destination pressure according to driver policy.

Record runtime events, exit state, health history, and application logs. A failure test without evidence assertions verifies only that something broke.

Never inject destructive failure into shared production state under this lab procedure.

## 22. Roll back by digest through the same gates

A rollback candidate must be:

- an already verified immutable digest;
- compatible with current data and external contracts;
- available in the registry;
- authorized by current policy;
- deployable through the same runtime model;
- followed by acceptance and evidence capture.

```bash
export IMAGE_REF="$previous_approved_digest_reference"
export SOURCE_REVISION="$previous_source_revision"

docker compose --project-name "$project" config --quiet
docker compose --project-name "$project" \
  up --detach --wait --wait-timeout 60
```

Do not move a mutable `latest` tag and hope reconciliation finds it. Change declared digest identity and verify the observed runtime.

Rollback is a new deployment decision. It does not reverse external effects or incompatible data migrations.

## 23. Keep forward recovery available

Rollback can be slower or riskier than a small forward fix when:

- data changed incompatibly;
- old dependencies are no longer available;
- credentials or certificates rotated;
- the vulnerability policy now rejects the old digest;
- external consumers adopted the new contract;
- the failure is configuration rather than code.

Prepare both paths. Use feature controls, compatible schema evolution, and independently versioned configuration to reduce the number of changes that require binary rollback.

## 24. Retire instances, artifacts, and credentials separately

After a successful replacement:

- drain and stop old runtime instances;
- preserve incident or release evidence under retention policy;
- remove disposable networks, volumes, and secrets;
- retain rollback artifacts for the approved window;
- revoke temporary registry and build credentials;
- remove mutable or superseded tags under registry policy;
- expire exceptions;
- keep SBOM, provenance, signatures, and scan results addressable by digest;
- eventually delete artifacts according to legal, recovery, and storage policy.

Stopping a container does not retire its image, token, volume, registry reference, or external authorization.

## 25. Store a release evidence packet

A release packet should contain or reference:

```text
release ID and owner:
source repository and revision:
review and CI run:
builder identity and version:
Dockerfile and build-context digest:
pinned base and dependency identities:
image index and platform manifest digests:
signature and provenance verification:
SBOM identity and review:
vulnerability/license/secret policy result and data timestamp:
exceptions with owners and expiration:
unit, integration, runtime, failure, and rollback results:
resolved runtime-model digest:
secret and external identity references, never secret values:
deployed environment and observed artifact identities:
health, limits, logs, metrics, and lifecycle evidence:
data migration, backup, restore, and compatibility evidence:
rollout, rollback, and retirement decisions:
```

Store evidence where release operators can retrieve it after the build worker and failed containers are gone.

## 26. Validate release records as data

This standard-library model makes several release invariants executable. It does not sign artifacts or query a registry; it validates that a packet consistently names immutable evidence and an observed runtime.

Save as `test_release_packet.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
import re
import unittest


HEX = re.compile(r"^[0-9a-f]{40,64}$")
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class ReleasePacket:
    source_revision: str
    image_digest: str
    provenance_digest: str
    sbom_digest: str
    runtime_config_digest: str
    tests_passed: bool
    policy_passed: bool
    signature_verified: bool
    observed_runtime_digest: str | None = None
    rollback_from: str | None = None
    retired_digest: str | None = None

    def validate_candidate(self) -> None:
        if not HEX.fullmatch(self.source_revision):
            raise ValueError("source revision must be immutable hexadecimal identity")
        for name in (
            "image_digest",
            "provenance_digest",
            "sbom_digest",
            "runtime_config_digest",
        ):
            if not DIGEST.fullmatch(getattr(self, name)):
                raise ValueError(f"{name} must be a sha256 digest")
        gates = {
            "tests": self.tests_passed,
            "policy": self.policy_passed,
            "signature": self.signature_verified,
        }
        failed = sorted(name for name, passed in gates.items() if not passed)
        if failed:
            raise ValueError(f"release gates failed: {', '.join(failed)}")

    def validate_deployment(self) -> None:
        self.validate_candidate()
        if self.observed_runtime_digest != self.image_digest:
            raise ValueError("observed runtime digest differs from approved digest")

    def validate_rollback(self) -> None:
        self.validate_deployment()
        if not self.rollback_from or not DIGEST.fullmatch(self.rollback_from):
            raise ValueError("rollback must identify the replaced digest")
        if self.rollback_from == self.image_digest:
            raise ValueError("rollback target must differ from replaced digest")
        if self.retired_digest != self.rollback_from:
            raise ValueError("replaced digest lacks retirement evidence")

    def evidence_digest(self) -> str:
        payload = json.dumps(
            self.__dict__,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(payload).hexdigest()


def digest(character: str) -> str:
    return "sha256:" + character * 64


class ReleasePacketTests(unittest.TestCase):
    def candidate(self) -> ReleasePacket:
        return ReleasePacket(
            source_revision="a" * 40,
            image_digest=digest("1"),
            provenance_digest=digest("2"),
            sbom_digest=digest("3"),
            runtime_config_digest=digest("4"),
            tests_passed=True,
            policy_passed=True,
            signature_verified=True,
        )

    def test_verified_deployment_matches_approved_digest(self) -> None:
        packet = replace(
            self.candidate(),
            observed_runtime_digest=digest("1"),
        )
        packet.validate_deployment()
        self.assertRegex(packet.evidence_digest(), DIGEST)

    def test_tag_or_missing_gate_cannot_be_promoted(self) -> None:
        with self.assertRaisesRegex(ValueError, "sha256"):
            replace(self.candidate(), image_digest="release-latest").validate_candidate()
        with self.assertRaisesRegex(ValueError, "policy"):
            replace(self.candidate(), policy_passed=False).validate_candidate()

    def test_runtime_drift_is_rejected(self) -> None:
        packet = replace(
            self.candidate(),
            observed_runtime_digest=digest("9"),
        )
        with self.assertRaisesRegex(ValueError, "differs"):
            packet.validate_deployment()

    def test_rollback_requires_retirement_of_replaced_digest(self) -> None:
        packet = replace(
            self.candidate(),
            image_digest=digest("5"),
            observed_runtime_digest=digest("5"),
            rollback_from=digest("1"),
            retired_digest=digest("1"),
        )
        packet.validate_rollback()

        incomplete = replace(packet, retired_digest=None)
        with self.assertRaisesRegex(ValueError, "retirement"):
            incomplete.validate_rollback()


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

Run it:

```bash
python -m unittest -v test_release_packet.py
```

The packet digest detects accidental record changes; it does not authenticate the author. Sign or store release records in an authenticated append-only system according to the threat model.

## 27. Make CI prove, not merely perform, the workflow

A reliable pipeline:

- pins third-party actions, images, and tools;
- uses short-lived least-privilege credentials;
- isolates untrusted pull-request code from release secrets;
- records logs and structured results;
- signs or attests from a protected identity;
- separates build permission from promotion permission;
- prevents mutable tag overwrite where possible;
- requires human approval only where judgment is real;
- can resume safely without duplicating external effects;
- cleans disposable builders and credentials;
- produces a complete release packet on success;
- produces failure evidence without publishing on failure.

Cache is an optimization, not an authority source. Scope it, verify outputs, and prevent untrusted jobs from poisoning release caches.

## 28. Audit the complete chain periodically

At release time and on a schedule, sample deployed workloads and answer:

- Does source still map to valid provenance?
- Does the registry digest still have required signatures and attestations?
- Has new vulnerability intelligence changed policy?
- Does the runtime still use the approved digest and configuration?
- Are least-privilege settings effective after platform upgrades?
- Do secrets and identities remain scoped and rotated?
- Are logs, metrics, events, backups, and restore tests current?
- Can the previous compatible digest still be deployed?
- Are old instances, volumes, tags, credentials, and exceptions retired?
- Does the owner still accept the operational contract?

Security and operability are continuing states, not properties frozen into a release-day report.

## 29. Know what this workflow does not prove

Even complete evidence does not prove:

- the absence of unknown vulnerabilities;
- that every dependency behaved honestly;
- that a trusted builder was uncompromised;
- that a signature owner intended the deployment;
- that runtime policy has no implementation flaws;
- that production traffic matches tests;
- that backups restore under every disaster;
- that a rollback can undo external effects;
- that the host kernel contains malicious code.

State assurance precisely. Strong engineering replaces absolute claims with verified controls, residual risk, detection, and recovery.

## Common Misconceptions

- “The tag we tested is the image we deployed.” A mutable tag is a lookup; compare immutable registry and runtime identities.
- “An SBOM proves the image is safe.” It inventories components; policy, provenance, exploitability, runtime authority, and new intelligence still matter.
- “The scanner passed, so release is approved forever.” Vulnerability data and policy change after publication.
- “A health check proves the user workflow.” It proves only the probe's bounded contract from its execution point.
- “Rollback means rebuild the old commit.” That creates a new artifact; deploy the previously verified compatible digest.
- “Read-only root means no state.” Volumes, tmpfs, logs, queues, databases, and external effects remain state.
- “Stopping old containers completes retirement.” Artifacts, data, credentials, evidence, and authorizations have separate lifecycles.

## Core Computer Science Concept

Container delivery is **a chain of custody implemented as monotonic evidence and guarded state transitions**. Each gate adds a verifiable claim about one immutable subject; promotion preserves subject identity, deployment compares desired with observed state, and rollback selects another previously verified subject rather than rewriting history.

## Engineering Connections

- Build context, layer, and cache rules come from Chapters 79 and 80.
- Digest, registry, provenance, and SBOM identity come from Chapter 81.
- Signal and replacement behavior come from Chapter 82.
- Data ownership, backup, and restore come from Chapter 83.
- Endpoint publication and discovery come from Chapter 84.
- Compose project validation and teardown come from Chapter 85.
- Runtime evidence and bounded failure injection come from Chapter 86.
- Least authority and secret boundaries come from Chapter 87.
- Multi-host promotion maps to Chapter 88's reconciliation and rollout responsibilities.

## From the Field

A pipeline tests `team/api:release`, rebuilds it in a later job, pushes the same tag, and deploys that tag. The second build resolves a newer base image, so production runs bytes never tested. Recording the candidate digest, publishing attestations, applying policy to that digest, and promoting the same registry subject removes the hidden rebuild boundary.

## Engineering Review

### What problem does this solve?

It provides an auditable path from reviewed source to a verified, constrained runtime and then to rollback and retirement without losing artifact identity.

### Why was it designed this way?

Build, distribution, runtime, data, and operations fail independently, so one immutable digest must accumulate evidence through explicit gates rather than inherit trust from a tag or successful command.

### When should I use it?

Use this workflow for every container release, scaling the evidence depth and approval policy to the workload's risk while retaining immutable identity and runtime verification.

### When should I avoid it?

Avoid copying the example commands unchanged into a platform whose registry, attestation, secret, scanner, or orchestrator semantics differ; preserve the chain-of-custody invariants and implement them with approved tools.

### How does this make me a better engineer?

It teaches you to connect source, artifact, policy, runtime, data, failure, and retirement as one operated system instead of treating an image build as delivery.

### How does this reduce waste?

It prevents duplicate rebuilds, untraceable tags, unsafe emergency privilege, unreproducible incidents, unused attestations, failed rollbacks, leaked temporary resources, and artifacts retained without owners.

## Handbook Principle #89

> Build once, identify by digest, accumulate evidence, deploy under least authority, verify observed state, and retire every resource deliberately.

## Practical Observation

Run the application and release-packet tests locally. On an approved disposable engine, perform candidate build, scan, Compose validation, loopback acceptance, replacement, and cleanup with unique names. Use a local registry or isolated private repository for attestation tests; do not push this example to a public namespace. Record every artifact identity and every unexecuted platform-specific gate honestly.

## Looking Ahead

Container delivery makes infrastructure portable, but cloud platforms add accounts, regions, metered APIs, managed services, quotas, and a shared-responsibility boundary. Chapter 90 begins Part VIII by showing what changes—and what remains an engineering obligation—when infrastructure becomes an on-demand service.

## References

- [Docker Build multi-stage builds](https://docs.docker.com/build/building/multi-stage/)
- [Docker Build reproducible builds](https://docs.docker.com/build/ci/github-actions/reproducible-builds/)
- [Docker Build attestations](https://docs.docker.com/build/metadata/attestations/)
- [Docker Build provenance attestations](https://docs.docker.com/build/metadata/attestations/slsa-provenance/)
- [Docker Build SBOM attestations](https://docs.docker.com/build/metadata/attestations/sbom/)
- [Docker CLI `docker buildx build`](https://docs.docker.com/reference/cli/docker/buildx/build/)
- [Docker CLI `docker buildx imagetools inspect`](https://docs.docker.com/reference/cli/docker/buildx/imagetools/inspect/)
- [Docker Scout vulnerability analysis](https://docs.docker.com/reference/cli/docker/scout/cves/)
- [Docker Scout policy evaluation](https://docs.docker.com/scout/policy/)
- [Docker Compose file reference](https://docs.docker.com/reference/compose-file/)
- [Open Container Initiative Image Format Specification](https://specs.opencontainers.org/image-spec/)
- [SLSA provenance](https://slsa.dev/spec/v1.0/provenance)
- [in-toto Attestation Framework](https://github.com/in-toto/attestation)
