# Chapter 80 — Reproducible and Efficient Container Builds

A Dockerfile can produce a running image while still hiding mutable dependencies, leaking build context, retaining compilers and credentials, or changing output between identical source revisions. A build is a supply-chain transformation, not merely a packaging command.

The central idea is:

> Declare and verify every build input, separate build authority from runtime content, and optimize the dependency graph without weakening reproducibility.

## 1. Define the build contract

Before writing instructions, name:

- immutable source revision and build context;
- target operating system and architecture;
- base-image identities;
- dependency locks and package sources;
- build frontend, builder, and toolchain versions;
- network and secret requirements;
- expected runtime files, user, and entry point;
- reproducibility inputs such as timestamps and locale;
- verification, provenance, and publication outputs.

The build should fail when a required input is absent or incompatible. Falling back from a lock file to unconstrained resolution makes the successful output less trustworthy.

## 2. Pin base images by digest

A base tag is a convenient update channel, not an immutable input. A reference such as:

```dockerfile
FROM python:3.14-slim
```

can resolve to different manifests over time. Retain the readable tag while pinning the reviewed digest:

```dockerfile
FROM python:3.14-slim@sha256:<reviewed-platform-or-index-digest>
```

The digest must come from an authenticated registry path and match the intended platform. A multi-platform index digest and a platform-specific manifest digest identify different objects.

Pinning also freezes vulnerabilities. Use an automated update workflow that proposes new tags and digests, shows provenance and vulnerability differences, rebuilds, tests, and records the reviewed change.

## 3. Choose bases by runtime requirements

The smallest possible base is not automatically the best base. Determine whether the program needs:

- a shell;
- a dynamic loader and shared libraries;
- CA certificates;
- time-zone or locale data;
- user and group database entries;
- native extension libraries;
- diagnostic utilities;
- package-manager behavior;
- an organizationally maintained patch stream.

A minimal runtime reduces transfer, filesystem surface, and unused packages. It can also make diagnosis harder or omit a dependency that was accidentally supplied by a larger development image.

Use a separate debug image or ephemeral diagnostic tooling when production policy permits. Do not install an entire administration environment into every runtime image by habit.

## 4. Pin the build frontend and checks

Modern Dockerfiles can select a frontend syntax version. Features, parser behavior, and built-in checks depend on that frontend.

```dockerfile
# syntax=docker/dockerfile:1.19
# check=error=true
```

Pin a supported version when treating warnings as errors so a newly introduced check does not break an unchanged build without review. Update the frontend deliberately and inspect changed semantics.

Static checks find suspicious forms and portability problems. They do not prove that downloads are authentic, tests are meaningful, or the resulting process is least privilege.

## 5. Make the context an allowlist in practice

Set the context root narrowly and maintain `.dockerignore`. Prefer explicit `COPY` instructions:

```dockerfile
COPY pyproject.toml requirements.lock ./
COPY src/ ./src/
```

over:

```dockerfile
COPY . .
```

The explicit form shows which files affect each step and reduces accidental inclusion. It also improves cache precision.

An ignore rule is defense in depth, not permission to use a broad copy without review. Test the actual context sent to remote builders and reject secret-like canaries in every produced layer.

## 6. Separate build, test, and runtime stages

A multi-stage build gives different phases different files and tools:

```text
dependency/build stage: compiler, headers, package manager, test tools
test stage: candidate output plus tests and test-only dependencies
runtime stage: runtime, application output, required data
```

Copy only the verified output into the runtime stage. Build credentials, source-control metadata, compiler caches, tests, and toolchains should not cross that boundary unless runtime behavior requires them.

Stage separation is not automatic verification. A careless `COPY --from=build / /` defeats it.

## 7. Order instructions by dependency stability

Place stable, expensive dependencies before frequently changing application source when the dependency graph permits:

```text
base identity
-> dependency lock
-> resolved dependencies
-> source
-> compilation and tests
-> runtime assembly
```

A source edit then preserves the dependency cache. A lock-file edit invalidates dependency resolution and every step that consumes it.

Do not reorder instructions across a real semantic dependency just to gain a cache hit. Correctness precedes build speed.

## 8. Resolve dependencies from locked inputs

Language locks and operating-system package versions need a policy appropriate to their ecosystem. A reproducible dependency step should identify:

- package name and version;
- artifact digest where supported;
- package index or repository snapshot;
- target platform and optional features;
- resolver and installer version;
- trust roots and signature policy.

Run package-index update and installation in the same layer when the package manager requires fresh metadata. Use noninteractive flags for that command rather than persisting a global environment value that changes runtime behavior.

`--no-cache` makes a resolver run again. It does not make mutable repository results deterministic.

## 9. Use cache mounts only for acceleration

BuildKit cache mounts can preserve compiler or package-manager data across builds without committing the cache directory to the image layer.

```dockerfile
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip wheel --require-hashes \
    --wheel-dir /wheels --requirement requirements.lock
```

The build must remain correct if the cache begins empty, contains stale entries, or is garbage-collected. Validate downloaded artifacts through the package manager's hash or signature mechanisms.

Select cache-sharing behavior according to the tool. A package database that requires exclusive access may need a locked cache rather than concurrent writers.

Keep untrusted change caches separate from privileged release caches.

## 10. Mount secrets; never encode them

Build arguments and ordinary environment variables can appear in history, provenance, logs, or process state. Use a secret or SSH mount for credentials required by one build step:

```dockerfile
RUN --mount=type=secret,id=package_token,required=true \
    PACKAGE_TOKEN_FILE=/run/secrets/package_token \
    ./fetch-private-dependency
```

The mount prevents automatic persistence into the layer, but the command can still copy or print the secret. Test the final configuration, every layer, logs, cache exports, and attestations with a synthetic canary.

Secret contents may be excluded from cache identity. If rotation must force new output, add an explicit non-secret version input instead of exposing the value.

## 11. Make network access explicit

Build network calls reduce hermeticity and add mutable failure modes. Prefer fetching verified dependencies in a dedicated step with:

- allowlisted endpoints;
- TLS and repository trust policy;
- immutable versions and digests;
- timeouts and bounded retries;
- offline consumption by later stages;
- retained dependency evidence.

Run steps with no network when they do not need it. A compiler that unexpectedly calls the internet should fail rather than silently add an undeclared input.

Do not embed proxy credentials in build arguments or committed configuration.

## 12. Normalize time and nondeterministic metadata

Equivalent source can produce different bytes through:

- current timestamps;
- filesystem traversal order;
- archive owner and mode fields;
- absolute build paths;
- random build IDs;
- locale and time zone;
- parallel link ordering;
- compression headers;
- generated provenance timestamps.

Use a source-derived `SOURCE_DATE_EPOCH` where supported, stable sorting, normalized ownership and modes, path remapping, deterministic compiler flags, and controlled tool versions.

Reproducibility is scoped. A filesystem layer might reproduce while a separately generated attestation truthfully records a different build time. Compare the intended subject objects, not unrelated event evidence.

## 13. Avoid host-specific build leakage

Do not let results depend on the developer's:

- current working-directory spelling;
- home-directory configuration;
- Git state outside the selected revision;
- local package cache without integrity checks;
- host architecture when cross-building;
- user and group IDs;
- locale, umask, or line-ending conversion;
- credentials or environment not declared by the task.

Use clean builders and compare output from different absolute paths. A successful build on one laptop proves little about this boundary.

## 14. Handle target platforms explicitly

A multi-platform build can execute natively, cross-compile, or use emulation. Each approach affects performance, test fidelity, and toolchain inputs.

Build systems commonly expose build-platform and target-platform values. Pass the target to compilers and dependency resolvers rather than letting them infer the worker architecture.

Do not claim a platform is supported because compilation completed. Run representative tests on the target architecture or an accepted equivalent and record which evidence used emulation.

Each platform produces a distinct manifest and configuration even when the source revision is shared.

## 15. Set runtime defaults deliberately

A runtime stage should define or inherit an explainable:

- numeric or named non-root user;
- absolute working directory;
- executable-form entry point and default arguments;
- minimal runtime environment;
- ownership and modes for copied files;
- OCI source, revision, version, and license labels;
- exposed-port metadata only when useful.

Use JSON array form for entry points to avoid an implicit shell and preserve signal delivery. Decide which arguments operators may override.

Build-time settings should not persist into runtime unless the application contract needs them.

## 16. Do not optimize only for image size

Useful objectives include:

- reproducibility;
- security patchability;
- startup and transfer time;
- cache efficiency;
- runtime compatibility;
- debuggability;
- provenance completeness;
- maintenance cost.

Compressing every operation into one unreadable command may save metadata while harming cache reuse and review. Removing CA roots can make the image smaller and the application unusable. A familiar maintained base can be safer than an obscure tiny one.

Measure compressed transfer, unpacked storage, shared layers, cold-start behavior, and vulnerability reachability separately.

## 17. A reviewable multi-stage pattern

This example expects CI to supply reviewed digest-pinned Python build and runtime image references. It copies only application source from the tested stage and uses temporary bind mounts to install wheels without adding the wheel directory to a runtime layer:

```dockerfile
# syntax=docker/dockerfile:1.19
# check=error=true

ARG BUILD_IMAGE
ARG RUNTIME_IMAGE

FROM ${BUILD_IMAGE} AS dependencies
ARG SOURCE_DATE_EPOCH
ENV SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH}
WORKDIR /src
COPY requirements.lock ./
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip wheel \
      --require-hashes \
      --wheel-dir /wheels \
      --requirement requirements.lock && \
    python -m pip install \
      --no-index \
      --find-links=/wheels \
      --require-hashes \
      --requirement requirements.lock

FROM dependencies AS test
COPY src/ ./src/
COPY tests/ ./tests/
RUN --network=none python -m unittest discover -s tests -v

FROM ${RUNTIME_IMAGE} AS runtime
ARG SOURCE_REVISION
LABEL org.opencontainers.image.source="https://example.invalid/project" \
      org.opencontainers.image.revision="${SOURCE_REVISION}"
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
RUN --mount=type=bind,from=dependencies,source=/wheels,target=/wheels,ro \
    --mount=type=bind,source=requirements.lock,target=/tmp/requirements.lock,ro \
    python -m pip install \
      --no-cache-dir \
      --no-index \
      --find-links=/wheels \
      --require-hashes \
      --requirement /tmp/requirements.lock
COPY --from=test --chown=65532:65532 /src/src/ /app/src/
USER 65532:65532
ENTRYPOINT ["python", "-m", "src.main"]
```

Replace the illustrative source label with the canonical repository. CI might invoke it as follows:

```bash
revision="$(git rev-parse HEAD)"
source_date_epoch="$(git show -s --format=%ct "$revision")"

docker buildx build --check .
docker buildx build \
  --platform linux/amd64 \
  --build-arg BUILD_IMAGE="$BUILD_IMAGE" \
  --build-arg RUNTIME_IMAGE="$RUNTIME_IMAGE" \
  --build-arg SOURCE_REVISION="$revision" \
  --build-arg SOURCE_DATE_EPOCH="$source_date_epoch" \
  --provenance=mode=max \
  --sbom=true \
  --output type=oci,dest=dist/application.oci.tar \
  .
```

Validate that both image arguments contain approved digest references before calling the builder. An empty global `ARG` can otherwise make failure messages confusing, and an unpinned value defeats the contract.

## 18. Complete example: verify a reproducible runtime archive

The following engine-independent lab models the final-stage boundary. It copies an allowlisted application file, normalizes archive metadata, embeds an immutable revision and source-derived epoch, and produces a deterministic gzip stream:

```python
from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import re
import tarfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory


REVISION = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class BuildInputs:
    source_revision: str
    source_date_epoch: int

    def validate(self) -> None:
        if not REVISION.fullmatch(self.source_revision):
            raise ValueError("source_revision must be a full 40-character hash")
        if self.source_date_epoch < 0:
            raise ValueError("source_date_epoch must be nonnegative")


def add_directory(archive: tarfile.TarFile, name: str, inputs: BuildInputs) -> None:
    info = tarfile.TarInfo(name)
    info.type = tarfile.DIRTYPE
    info.mode = 0o555
    info.uid = 65532
    info.gid = 65532
    info.uname = ""
    info.gname = ""
    info.mtime = inputs.source_date_epoch
    archive.addfile(info)


def add_file(
    archive: tarfile.TarFile,
    name: str,
    content: bytes,
    inputs: BuildInputs,
) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(content)
    info.mode = 0o444
    info.uid = 65532
    info.gid = 65532
    info.uname = ""
    info.gname = ""
    info.mtime = inputs.source_date_epoch
    archive.addfile(info, io.BytesIO(content))


def build_runtime_archive(context: Path, inputs: BuildInputs) -> bytes:
    inputs.validate()
    source = (context / "src" / "main.py").read_bytes()
    metadata = (
        json.dumps(
            {
                "schema": 1,
                "source_date_epoch": inputs.source_date_epoch,
                "source_revision": inputs.source_revision,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")

    uncompressed = io.BytesIO()
    with tarfile.open(
        fileobj=uncompressed,
        mode="w",
        format=tarfile.USTAR_FORMAT,
    ) as archive:
        add_directory(archive, "app/", inputs)
        add_file(archive, "app/BUILD-METADATA.json", metadata, inputs)
        add_file(archive, "app/main.py", source, inputs)

    compressed = io.BytesIO()
    with gzip.GzipFile(
        fileobj=compressed,
        mode="wb",
        filename="",
        mtime=inputs.source_date_epoch,
        compresslevel=9,
    ) as stream:
        stream.write(uncompressed.getvalue())
    return compressed.getvalue()


def archive_digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def archive_members(content: bytes) -> dict[str, tuple[bytes, tarfile.TarInfo]]:
    result: dict[str, tuple[bytes, tarfile.TarInfo]] = {}
    with tarfile.open(fileobj=io.BytesIO(content), mode="r:gz") as archive:
        for member in archive.getmembers():
            if not member.isfile():
                continue
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError(f"missing content for {member.name}")
            result[member.name] = (stream.read(), member)
    return result


class ReproducibleBuildTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.inputs = BuildInputs(
            source_revision="a" * 40,
            source_date_epoch=1_700_000_000,
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def make_context(self, name: str, source: bytes) -> Path:
        context = self.root / name
        (context / "src").mkdir(parents=True)
        (context / "tests").mkdir()
        (context / "src" / "main.py").write_bytes(source)
        (context / "tests" / "test_main.py").write_text(
            "# build-only test\n",
            encoding="utf-8",
        )
        (context / ".env").write_text(
            "SYNTHETIC_SECRET=must-not-ship\n",
            encoding="utf-8",
        )
        return context

    def test_different_paths_and_mtimes_produce_identical_bytes(self) -> None:
        first = self.make_context("first-location", b'print("hello")\n')
        second = self.make_context("another-location", b'print("hello")\n')
        os.utime(first / "src" / "main.py", (1, 1))
        os.utime(second / "src" / "main.py", (2_000_000_000, 2_000_000_000))

        left = build_runtime_archive(first, self.inputs)
        right = build_runtime_archive(second, self.inputs)

        self.assertEqual(left, right)
        self.assertEqual(archive_digest(left), archive_digest(right))

    def test_source_change_changes_artifact_identity(self) -> None:
        first = self.make_context("first", b'print("version 1")\n')
        second = self.make_context("second", b'print("version 2")\n')

        self.assertNotEqual(
            archive_digest(build_runtime_archive(first, self.inputs)),
            archive_digest(build_runtime_archive(second, self.inputs)),
        )

    def test_runtime_allowlist_excludes_tests_and_environment(self) -> None:
        context = self.make_context("context", b'print("hello")\n')
        content = build_runtime_archive(context, self.inputs)
        members = archive_members(content)

        self.assertEqual(
            set(members),
            {"app/BUILD-METADATA.json", "app/main.py"},
        )
        visible_content = b"".join(
            member_content for member_content, _member in members.values()
        )
        self.assertNotIn(b"SYNTHETIC_SECRET", visible_content)

    def test_runtime_metadata_is_normalized(self) -> None:
        context = self.make_context("context", b'print("hello")\n')
        members = archive_members(build_runtime_archive(context, self.inputs))

        for _content, member in members.values():
            self.assertEqual(member.uid, 65532)
            self.assertEqual(member.gid, 65532)
            self.assertEqual(member.mode, 0o444)
            self.assertEqual(member.mtime, self.inputs.source_date_epoch)


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

Save it as `test_reproducible_build.py` in a disposable directory and run:

```bash
python -m unittest -v test_reproducible_build.py
```

This model deliberately ignores ambient path names and source mtimes. It copies an allowlist rather than archiving the whole context. A real image build additionally needs deterministic base layers, builder behavior, dependency artifacts, image configuration, and compression.

The synthetic secret assertion checks the decompressed allowlisted files for a recognizable canary. Production scanning must also inspect every layer, configuration, history, provenance, logs, and remote cache exports.

## 19. Verify the produced image

Before publication, verify:

- selected platform and immutable base identities;
- manifest, configuration, and layer digests;
- expected runtime file allowlist;
- absence of compilers, tests, caches, package indexes, and credentials;
- numeric non-root runtime user;
- entrypoint and default argument behavior;
- installed dependency versions and licenses;
- execution with read-only root, bounded resources, dropped capabilities, and no network where applicable;
- provenance subject matching the image digest;
- a clean rebuild comparison.

Run the image's tests before stripping build tools, then run installation and smoke tests against the final runtime image. Testing only the build stage can miss a missing shared library or copied data file.

## 20. Compare clean builds by intended subject

Build twice from the same immutable revision and inputs on clean workers with different absolute workspace paths. Compare:

- platform manifest digest;
- configuration digest;
- each filesystem layer DiffID;
- runtime file metadata and content;
- SBOM package identity;
- provenance inputs, allowing explicitly event-specific fields.

If digests differ, unpack metadata and locate the first differing object. Do not dismiss variation as “just timestamps” without fixing or documenting the reproducibility scope.

Record the comparison as evidence. A one-time local match does not prove every supported platform and builder remains reproducible.

## Common Misconceptions

- “Pinning a base digest keeps the image secure.” It preserves identity and requires a separate update process.
- “Multi-stage builds automatically make small images.” Only explicitly copied runtime content crosses the boundary safely.
- “No-cache builds are reproducible.” Mutable dependencies still resolve differently.
- “A secret mount makes the command safe.” The command can still persist or print the secret.
- “The smallest image has the smallest risk.” Maintenance, compatibility, trust, and diagnosis also matter.
- “Tests in the build stage prove the runtime image.” Final-stage assembly can omit or change required content.

## Core Computer Science Concept

A reproducible container build is a **deterministic transformation over a declared dependency graph**. Multi-stage construction creates authority and artifact boundaries; caching memoizes nodes without becoming a source of truth.

## Engineering Connections

- Digest-pinned bases extend the immutable artifact identity from Chapter 77.
- Context allowlisting applies least authority to filesystem inputs.
- Stage boundaries separate build-time capabilities from runtime authority.
- `SOURCE_DATE_EPOCH` carries Chapter 75's reproducible-build model into image metadata.
- Final-runtime testing applies Chapter 73's rule that doubles and earlier stages cannot prove the real boundary.

## From the Field

A service passes every test in its compiler stage. The final image copies the binary but not the CA bundle used for outbound TLS, so production fails on its first request. A smoke test executed against the final runtime stage under production-like filesystem and network policy would have caught the missing runtime dependency.

## Engineering Review

### What problem does this solve?

It turns image construction into a reviewable, repeatable transformation with explicit inputs, narrow authority, efficient cache boundaries, and verified runtime output.

### Why was it designed this way?

Pinned identities control source variation, multi-stage builds keep toolchains out of runtime, and normalized metadata plus locked dependencies make comparisons meaningful.

### When should I use it?

Use these practices for every maintained container build, scaling verification and reproducibility effort with release risk.

### When should I avoid it?

Avoid complexity that lacks a measured build, security, or operational benefit, and avoid minimal bases that cannot satisfy or diagnose the runtime contract.

### How does this make me a better engineer?

It teaches you to treat build systems as privileged dependency graphs and to distinguish fast output from trustworthy output.

### How does this reduce waste?

It prevents repeated dependency resolution, oversized images, leaked tools and secrets, cache churn, environment drift, and production-only assembly failures.

## Handbook Principle #80

> Pin every upstream identity, isolate build authority by stage, and prove the final runtime artifact—not merely the step that compiled it.

## Practical Observation

Run the reproducible archive lab, compare both digests, and inspect member ownership and timestamps. Add `.env` and a test fixture to each context and confirm neither changes the result. Then change `main.py` and confirm the artifact identity changes.

## Looking Ahead

A reproducible image still needs distribution names, immutable registry identity, authentication, retention, vulnerability evidence, signatures, attestations, and promotion policy. Chapter 81 connects those controls from build output to verified consumption.

## References

- [Dockerfile reference](https://docs.docker.com/reference/dockerfile/)
- [Docker build best practices](https://docs.docker.com/build/building/best-practices/)
- [Docker multi-stage builds](https://docs.docker.com/build/building/multi-stage/)
- [Docker build secrets](https://docs.docker.com/build/building/secrets/)
- [Docker build cache invalidation](https://docs.docker.com/build/cache/invalidation/)
- [Docker build checks](https://docs.docker.com/reference/build-checks/)
- [Reproducible Builds — `SOURCE_DATE_EPOCH`](https://reproducible-builds.org/specs/source-date-epoch/)
- [OCI Image Format Specification](https://github.com/opencontainers/image-spec)
