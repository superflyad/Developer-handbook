# Chapter 79 — Images, Layers, Build Contexts, and Caches

A container image often appears to be one filesystem archive. In an OCI-compatible system, it is a graph of content-addressed documents and filesystem changesets. That distinction explains image identity, cache behavior, deletion, sharing, and unexpected content.

The central idea is:

> An image is an immutable object graph whose ordered layers describe filesystem changes; a build context and complete cache keys determine which graph the builder produces.

## 1. Follow the image object graph

An OCI image commonly contains:

```text
image index (optional multi-platform entry point)
        |
        v
platform-specific image manifest
        |                    |
        v                    v
image configuration     ordered layer descriptors
                              |
                              v
                     filesystem changeset blobs
```

The image index can reference manifests for several operating systems, architectures, or variants. One image manifest references one configuration object and an ordered list of layers.

The runtime uses the configuration and applied filesystem to prepare the process model from Chapter 78.

## 2. Descriptors bind metadata to bytes

An OCI descriptor names content with fields including:

- media type;
- cryptographic digest;
- byte size;
- optional platform or annotations.

A consumer should retrieve the blob, verify its size and digest, and interpret it according to the expected media type. The digest is calculated over the exact stored bytes.

If one byte changes, the digest changes. Every parent document that embeds the old descriptor must also change to reference the new object. Content addressing therefore makes mutation visible and allows identical blobs to be shared.

A digest proves identity and integrity relative to bytes. It does not prove who created them, whether they are safe, or whether a named repository is authorized to publish them.

## 3. The manifest orders the filesystem changes

The manifest's `layers` array runs from the base layer to the final layer. Each descriptor references a tar-based changeset.

A layer can:

- add a file or directory;
- replace content or metadata at an existing path;
- mark a lower path as removed;
- mark a directory opaque to lower children.

The final image filesystem is the result of applying every changeset in order to an initially empty root.

Layer order matters. The same two changesets applied in the opposite order can produce a different filesystem even though their individual digests are unchanged.

## 4. Layers record changes, not complete trees

A layer is not necessarily a directory tree that can run by itself. It is a delta relative to the layers before it.

Suppose a base layer contains:

```text
/app/main.py
/app/config.txt
```

A later layer can replace `main.py` and white out `config.txt`. The merged view then contains only the newer `main.py`, but the older layer blob still contains both original files.

This has two consequences:

1. deleting a large file in a later layer does not remove its bytes from earlier blobs;
2. deleting a secret after copying it into an earlier layer does not make the secret absent from the image graph.

Prevent sensitive or unnecessary content from entering any layer.

## 5. Whiteouts encode deletion

An archive cannot express “remove a path from an earlier archive” with ordinary file entries. OCI layers use whiteout entries.

For a lower path `app/config.txt`, a later layer can contain:

```text
app/.wh.config.txt
```

The whiteout hides the lower path when layers are applied. The marker itself is not visible in the final filesystem.

The special `.wh..wh..opq` marker makes a directory opaque, hiding lower children before the current layer's entries are applied. Correct readers process opaque markers independently of their archive order.

Whiteouts are an image-format concept. A runtime snapshotter may represent deletion differently in its backing filesystem.

## 6. Configuration is separate from layers

The image configuration describes execution defaults and root filesystem identity. It can include:

- operating system and architecture;
- default user and working directory;
- entrypoint and arguments;
- environment values;
- labels;
- declared volumes and exposed ports;
- layer DiffIDs and history.

Configuration changes can produce a new image identity without adding a filesystem layer. A history entry can therefore be marked as an empty layer.

Do not infer the number of filesystem layers by counting build-file instructions or history lines.

Configuration values are defaults, not an enforcement boundary. Runtime arguments can override many of them, and metadata such as an exposed port does not publish a host port.

## 7. Distinguish layer digest, DiffID, and chain identity

The manifest descriptor digest identifies the stored layer blob, which may be compressed. The configuration's **DiffID** identifies the uncompressed tar archive.

For an uncompressed layer, the two digests can be equal. For a compressed layer, they usually differ because they hash different byte streams.

A **ChainID** identifies an ordered sequence of applied DiffIDs. It distinguishes the same changeset applied after different parents.

When diagnosing, name the identity you mean:

- compressed or stored blob;
- uncompressed changeset;
- applied layer chain;
- image configuration;
- image manifest;
- multi-platform index.

“Image ID” can be ambiguous across tools if this boundary is omitted.

## 8. The runtime adds a writable snapshot

Image layers are immutable. When a container writes to its root filesystem, the runtime records changes in a container-specific writable snapshot or layer.

With a copy-on-write filesystem, reading can use a lower immutable object directly. The first write to a lower file may copy it into an upper writable area before modification.

This writable state:

- is not automatically part of the image;
- normally disappears when the container is removed;
- can consume storage independently of image size;
- can hide lower files without changing their blobs;
- is inappropriate for durable application data.

Creating an image from arbitrary container state makes inputs and history difficult to reproduce. Encode intended changes in a reviewed build instead.

## 9. Sharing layers saves transfer and storage

Content addressing lets images reuse identical blobs. If ten images reference the same base layer, a local content store can keep one verified copy.

Do not add layer sizes to estimate host storage blindly. Storage depends on:

- shared content across images;
- compressed versus unpacked data;
- snapshotter representation;
- writable container snapshots;
- build cache records;
- temporary and garbage-collection state.

Removing one image reference may not remove a shared blob. Conversely, pruning a build cache may reclaim space without removing a tagged image.

Inspect the runtime's content, snapshot, image, container, and build-cache accounting separately.

## 10. An image index selects a platform

An OCI image index contains descriptors for manifests, often with platform metadata such as:

- `os`;
- `architecture`;
- architecture variant;
- operating-system version or features.

When a reference supports several platforms, the client selects a compatible manifest. Two machines can resolve the same human-readable reference to different platform-specific manifests and layer sets.

Multi-platform does not mean one binary runs everywhere. It means the index can point to distinct images built for distinct platform contracts.

Record both the selected manifest digest and platform when reproducibility matters.

## 11. The build context is an input boundary

The build context is the set of files and metadata available to the builder for context-dependent operations such as copying source.

The context may be a local directory, archive, repository, URL, or product-specific named source. A remote builder receives only the context supplied through that interface—not every path on the client machine.

Choose the narrowest directory that contains required inputs. Using a repository's parent directory can expose unrelated projects, credentials, caches, and large generated trees to the builder.

The build file itself and ignore rules are also inputs. Review them with the same care as application source.

## 12. Ignore rules reduce context, not history

Docker-compatible builders commonly read `.dockerignore` from the context root to exclude paths before sending the context.

A useful ignore file often excludes:

```text
.git
.env
.venv
__pycache__
build
dist
node_modules
*.log
```

Adapt the list to the project. Do not copy a generic ignore file that removes required lock files, certificates intended as public trust anchors, generated source, or test fixtures.

Ignore rules are preventive. Adding a secret to `.dockerignore` after it entered a committed layer, remote cache, or published image does not erase existing copies.

Test the effective context contents and transferred size. A pattern can behave differently from a developer's shell glob expectation.

## 13. Each build step has a cache contract

A builder can reuse prior output when the operation and every relevant input match its cache record. Inputs can include:

- parent layer or build-stage identity;
- normalized instruction and arguments;
- copied file content and selected metadata;
- build arguments and environment;
- mounts and their options;
- toolchain and frontend version;
- target platform;
- declared network or secret identifiers;
- product-specific cache scope.

An incomplete key returns stale output. An overly broad key rebuilds unnecessarily. Cache semantics belong to the specific builder and version; do not infer them only from the visible layer list.

Chapter 75's rule still applies: deleting the cache may make a correct build slower, but it must not change the intended result.

## 14. Invalidation flows downstream

Build steps form a dependency graph. If one step changes, downstream steps that use its result require new cache records.

For a common application pattern:

```text
copy dependency manifests
-> resolve locked dependencies
-> copy application source
-> compile or package application
```

Changing application source can preserve the expensive dependency step. Copying the entire repository before dependency resolution makes every source edit invalidate it.

Optimize only after correctness. Combining unrelated work solely to reduce layer count can create opaque commands, poor cache reuse, and harder review.

## 15. A cached command does not recheck the world

If a command string is unchanged, a builder may reuse its prior result without querying an external package repository again. Re-running the same build later does not necessarily fetch current packages.

Conversely, disabling the cache does not create reproducibility. An unpinned package query can resolve different content on every clean build.

Control external inputs with lock files, immutable base identities, verified downloads, repository snapshots, and explicit update workflows. Treat network access as a declared build dependency.

Use no-cache builds as diagnostic evidence, not as a substitute for a complete input model.

## 16. Keep secrets out of layers and cache records

Do not pass secrets through copied files, ordinary build arguments, environment declarations, or command text that becomes image metadata or history.

Use the builder's secret-mount mechanism so the credential is available only to the operation that needs it and is not committed to the resulting filesystem snapshot. Confirm the product's cache semantics: secret contents may intentionally be excluded from cache keys, so secret rotation may need an explicit non-secret invalidation input.

Even with a secret mount, the command can copy or print the secret. The mechanism narrows exposure; the build step must still behave safely.

Scan every layer and configuration, not only the merged filesystem.

## 17. Inspect before running

Image inspection is a read-only supply-chain step. Examine:

- index and selected platform;
- manifest, configuration, and all descriptor digests;
- layer media types and sizes;
- default user, entrypoint, arguments, environment, and working directory;
- history and empty-layer relationships;
- unexpected files in every layer;
- package and dependency inventory;
- provenance and signature evidence.

Do not execute an untrusted image merely to discover its contents. Parsers for archives and image metadata also need input limits and path validation.

Chapter 81 develops registry references, provenance, and verification policy.

## 18. Complete example: construct and inspect an OCI layout

This standard-library lab creates a disposable OCI image layout with two uncompressed layers. The second layer replaces one file and whites out another. The inspector verifies every descriptor before reading it and never extracts archive paths to disk:

```python
from __future__ import annotations

import hashlib
import io
import json
import tarfile
import unittest
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from typing import Any, Iterable, Mapping


OCI_LAYOUT = "application/vnd.oci.image.layout.v1+json"
OCI_INDEX = "application/vnd.oci.image.index.v1+json"
OCI_MANIFEST = "application/vnd.oci.image.manifest.v1+json"
OCI_CONFIG = "application/vnd.oci.image.config.v1+json"
OCI_LAYER = "application/vnd.oci.image.layer.v1.tar"


def json_bytes(document: Mapping[str, Any]) -> bytes:
    return json.dumps(
        document,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def descriptor(content: bytes, media_type: str) -> dict[str, Any]:
    return {
        "mediaType": media_type,
        "digest": f"sha256:{hashlib.sha256(content).hexdigest()}",
        "size": len(content),
    }


def store_blob(root: Path, content: bytes, media_type: str) -> dict[str, Any]:
    result = descriptor(content, media_type)
    algorithm, encoded = result["digest"].split(":", 1)
    path = root / "blobs" / algorithm / encoded
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return result


def make_layer(entries: Mapping[str, bytes]) -> bytes:
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        for name, content in sorted(entries.items()):
            info = tarfile.TarInfo(name)
            info.size = len(content)
            info.mode = 0o644
            info.mtime = 0
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            archive.addfile(info, io.BytesIO(content))
    return stream.getvalue()


def create_layout(root: Path) -> None:
    root.mkdir(parents=True)
    (root / "oci-layout").write_bytes(
        json_bytes({"imageLayoutVersion": "1.0.0"})
    )

    base = make_layer(
        {
            "app/config.txt": b"retired-setting=true\n",
            "app/main.py": b'print("version 1")\n',
        }
    )
    update = make_layer(
        {
            "app/.wh.config.txt": b"",
            "app/main.py": b'print("version 2")\n',
        }
    )
    layers = (
        store_blob(root, base, OCI_LAYER),
        store_blob(root, update, OCI_LAYER),
    )

    config = json_bytes(
        {
            "architecture": "amd64",
            "os": "linux",
            "config": {
                "Entrypoint": ["python", "/app/main.py"],
                "User": "65532:65532",
                "WorkingDir": "/app",
            },
            "rootfs": {
                "type": "layers",
                "diff_ids": [item["digest"] for item in layers],
            },
            "history": [
                {"created_by": "create base files"},
                {"created_by": "replace main and remove config"},
            ],
        }
    )
    config_descriptor = store_blob(root, config, OCI_CONFIG)
    manifest = json_bytes(
        {
            "schemaVersion": 2,
            "mediaType": OCI_MANIFEST,
            "config": config_descriptor,
            "layers": list(layers),
        }
    )
    manifest_descriptor = store_blob(root, manifest, OCI_MANIFEST)
    manifest_descriptor["platform"] = {
        "architecture": "amd64",
        "os": "linux",
    }
    index = {
        "schemaVersion": 2,
        "mediaType": OCI_INDEX,
        "manifests": [manifest_descriptor],
    }
    (root / "index.json").write_bytes(json_bytes(index))


def read_blob(root: Path, item: Mapping[str, Any]) -> bytes:
    try:
        algorithm, encoded = item["digest"].split(":", 1)
        expected_size = item["size"]
    except (KeyError, ValueError, AttributeError) as error:
        raise ValueError("invalid descriptor") from error
    if algorithm != "sha256" or len(encoded) != 64:
        raise ValueError("unsupported or malformed digest")

    content = (root / "blobs" / algorithm / encoded).read_bytes()
    if len(content) != expected_size:
        raise ValueError("descriptor size mismatch")
    if hashlib.sha256(content).hexdigest() != encoded:
        raise ValueError("descriptor digest mismatch")
    return content


def select_image(
    root: Path,
    *,
    operating_system: str,
    architecture: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    index = json.loads((root / "index.json").read_bytes())
    selected = next(
        (
            item
            for item in index["manifests"]
            if item.get("platform", {}).get("os") == operating_system
            and item.get("platform", {}).get("architecture") == architecture
        ),
        None,
    )
    if selected is None:
        raise ValueError("no compatible platform manifest")

    manifest = json.loads(read_blob(root, selected))
    config = json.loads(read_blob(root, manifest["config"]))
    if config.get("rootfs", {}).get("type") != "layers":
        raise ValueError("unsupported rootfs type")
    diff_ids = config["rootfs"]["diff_ids"]
    layer_digests = [item["digest"] for item in manifest["layers"]]
    if diff_ids != layer_digests:
        raise ValueError("uncompressed layer identities do not match")
    return manifest, config


def safe_archive_name(name: str) -> str:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe archive path: {name}")
    normalized = PurePosixPath(*(part for part in path.parts if part != "."))
    if not normalized.parts:
        raise ValueError("empty archive path")
    return normalized.as_posix()


def remove_path(files: dict[str, bytes], target: str) -> None:
    for name in tuple(files):
        if name == target or name.startswith(f"{target}/"):
            del files[name]


def merged_files(
    root: Path,
    layers: Iterable[Mapping[str, Any]],
) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for layer in layers:
        content = read_blob(root, layer)
        with tarfile.open(fileobj=io.BytesIO(content), mode="r:") as archive:
            members = tuple(archive.getmembers())

            for member in members:
                name = safe_archive_name(member.name)
                path = PurePosixPath(name)
                if path.name == ".wh..wh..opq":
                    parent = path.parent.as_posix()
                    prefix = "" if parent == "." else f"{parent}/"
                    for old_name in tuple(files):
                        if old_name.startswith(prefix):
                            del files[old_name]
                elif path.name.startswith(".wh."):
                    target = (path.parent / path.name[4:]).as_posix()
                    remove_path(files, target)

            for member in members:
                name = safe_archive_name(member.name)
                path = PurePosixPath(name)
                if path.name.startswith(".wh.") or not member.isfile():
                    continue
                extracted = archive.extractfile(member)
                if extracted is None:
                    raise ValueError(f"missing content for {name}")
                files[name] = extracted.read()
    return files


class ImageLayoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.root = Path(self.temporary_directory.name) / "layout"
        create_layout(self.root)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_layers_produce_expected_merged_view(self) -> None:
        manifest, config = select_image(
            self.root,
            operating_system="linux",
            architecture="amd64",
        )
        files = merged_files(self.root, manifest["layers"])

        self.assertEqual(files, {"app/main.py": b'print("version 2")\n'})
        self.assertEqual(config["config"]["User"], "65532:65532")

    def test_whiteout_does_not_erase_bytes_from_lower_layer(self) -> None:
        manifest, _config = select_image(
            self.root,
            operating_system="linux",
            architecture="amd64",
        )
        base = read_blob(self.root, manifest["layers"][0])

        with tarfile.open(fileobj=io.BytesIO(base), mode="r:") as archive:
            old = archive.extractfile("app/config.txt")
            assert old is not None
            self.assertEqual(old.read(), b"retired-setting=true\n")

    def test_corrupted_blob_is_rejected_before_layer_use(self) -> None:
        manifest, _config = select_image(
            self.root,
            operating_system="linux",
            architecture="amd64",
        )
        layer = manifest["layers"][0]
        encoded = layer["digest"].split(":", 1)[1]
        path = self.root / "blobs" / "sha256" / encoded
        path.write_bytes(path.read_bytes() + b"corrupt")

        with self.assertRaisesRegex(ValueError, "size mismatch"):
            merged_files(self.root, manifest["layers"])

    def test_unsupported_platform_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "no compatible"):
            select_image(
                self.root,
                operating_system="linux",
                architecture="arm64",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

Save it as `test_oci_layout.py` in a disposable directory and run:

```bash
python -m unittest -v test_oci_layout.py
```

The example uses uncompressed layers, so each layer descriptor digest equals its DiffID. A production inspector must support the declared compression media type, verify the compressed descriptor first, then calculate the DiffID over the uncompressed stream while applying decompression limits.

The parser validates archive paths and reads members without extracting them. A production parser also needs limits on object sizes, layer count, archive members, decompression ratio, JSON depth, and total work.

## 19. Predict cache invalidation before building

For each build step, write:

```text
parent identity
+ operation definition
+ file and metadata inputs
+ build arguments and mounts
+ platform and toolchain
= expected cache key boundary
```

Then change one input and predict which step first becomes invalid and which downstream results must rebuild. Compare the prediction with plain build progress output.

Unexpected reuse indicates a missing input or misunderstood builder rule. Unexpected rebuilding indicates a broader-than-needed dependency, nondeterministic input, or cache scope mismatch.

## 20. Diagnose unexpected image content

When a file is unexpectedly present or absent:

1. resolve the selected platform manifest;
2. verify every descriptor;
3. inspect layers from newest to oldest for the path or whiteout;
4. inspect build history as a clue, not proof;
5. identify the context path and ignore rule that admitted the source;
6. identify the first build step that copied or generated it;
7. determine whether a reused cache record predates the intended change;
8. rebuild with controlled inputs and compare digests;
9. rotate any exposed credential and remove published artifacts under policy.

Deleting only the local tag or merged file does not remediate copies in registries, caches, logs, or downstream deployments.

## Common Misconceptions

- “Each build-file line creates one layer.” Metadata-only steps and modern build graphs do not guarantee that relationship.
- “Deleting a file makes the image smaller.” Earlier immutable layers still contain their bytes.
- “The image digest is the hash of the merged filesystem.” Manifests, configuration, descriptors, layer bytes, and platform indexes have distinct identities.
- “A clean build is reproducible.” Mutable network inputs can produce a different graph every time.
- “The cache looks only at file modification time.” Cache inputs are builder-specific and can use content and selected metadata.
- “A multi-platform image is one portable binary.” The index commonly selects different platform-specific images.

## Core Computer Science Concept

An image is a **content-addressed directed acyclic graph of immutable values**, while its filesystem is an ordered fold over changesets. Build caching memoizes transformations when their declared inputs match.

## Engineering Connections

- Descriptors apply cryptographic content identity from Chapter 77's artifact chain of custody.
- Ordered layers are event-like changesets whose fold produces current state.
- Whiteouts demonstrate why logical deletion is not physical erasure.
- Build contexts are authority and data-exposure boundaries like subprocess input in Chapter 70.
- Cache keys reuse the dependency-graph model from Chapter 75.

## From the Field

A developer copies the repository into an image, deletes `.env` in the next step, and verifies that the running container cannot see it. An attacker downloads the earlier layer and reads the credential. The merged view hid the path; the immutable image graph retained its bytes.

## Engineering Review

### What problem does this solve?

It makes image identity, layer application, build input, cache invalidation, storage sharing, and hidden historical content predictable.

### Why was it designed this way?

Immutable content-addressed objects support verification, sharing, transport, and caching, while ordered changesets efficiently assemble filesystems.

### When should I use it?

Use this model when building, inspecting, transferring, caching, scanning, or debugging OCI-compatible images.

### When should I avoid it?

Avoid inferring security or reproducibility from a merged filesystem view, tag, cache hit, or small visible layer history alone.

### How does this make me a better engineer?

It lets you trace a visible path or unexpected rebuild back through concrete descriptors, changesets, context inputs, and cache dependencies.

### How does this reduce waste?

It prevents leaked context, ineffective deletion, redundant transfer, invalid cache reuse, needless rebuilds, and platform-selection surprises.

## Handbook Principle #79

> Trace every image through verified descriptors and ordered changesets, and treat the build context plus cache contract as part of the artifact's complete input.

## Practical Observation

Run the OCI layout lab and inspect `index.json`, then follow each descriptor to `blobs/sha256`. Confirm the merged view lacks `config.txt`, open the base layer to find its bytes, corrupt a copy of one blob, and verify that inspection fails before applying the layer.

## Looking Ahead

Understanding the object graph explains what a build produces. Chapter 80 designs Dockerfiles and build stages that produce smaller, reproducible, least-authority images without sacrificing cache efficiency or supply-chain evidence.

## References

- [OCI Image Format Specification](https://github.com/opencontainers/image-spec/blob/main/spec.md)
- [OCI Image Manifest Specification](https://github.com/opencontainers/image-spec/blob/main/manifest.md)
- [OCI Image Configuration](https://github.com/opencontainers/image-spec/blob/main/config.md)
- [OCI Image Layer Filesystem Changeset](https://github.com/opencontainers/image-spec/blob/main/layer.md)
- [OCI Image Layout](https://github.com/opencontainers/image-spec/blob/main/image-layout.md)
- [Docker build context](https://docs.docker.com/build/concepts/context/)
- [Docker build cache invalidation](https://docs.docker.com/build/cache/invalidation/)
- [Linux kernel documentation — Overlay Filesystem](https://docs.kernel.org/filesystems/overlayfs.html)
