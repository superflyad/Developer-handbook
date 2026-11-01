# Chapter 83 — Container Filesystems, Volumes, and Persistent Data

A process can write `/data/report.db` successfully without that data surviving container replacement. The pathname describes the view inside the container, not the storage lifetime, owner, durability, or backup boundary behind it.

The central idea is:

> Place every writable path according to its required lifetime and owner, and verify persistence by replacing the container and restoring the data—not by inspecting one running instance.

## 1. Classify state before choosing a mount

For every path the application reads or writes, ask:

- Is the content part of the immutable application artifact?
- Can it be regenerated safely and how long would that take?
- Must it survive process restart, container replacement, host loss, or region loss?
- Is it shared by several processes or instances?
- Who owns its schema and lifecycle?
- What consistency, latency, and locking semantics does it require?
- What is the maximum size and growth rate?
- Does it contain credentials, customer data, or regulated data?
- How is it backed up, restored, migrated, and retired?

The answer may be an image layer, writable container layer, temporary filesystem, bind mount, managed volume, network filesystem, object store, or database service. “Put it in `/data`” is not a design.

## 2. Understand the merged root filesystem

At runtime, the container often sees a merged root:

```text
read-only image layers
          +
container-specific writable layer
          +
mounted paths that obscure parts of the merged root
```

Reads can come from immutable lower image content. A first write to a lower file may copy it into the writable upper layer before changing it.

The exact snapshotter or storage driver varies. Do not couple application correctness to its internal host directory layout.

The writable layer belongs to the container instance, not the image. Another container from the same image receives a different writable layer.

## 3. Use the writable layer for disposable state

Appropriate writable-layer content includes:

- small regenerated caches;
- extracted temporary assets that can be recreated;
- short-lived process markers;
- diagnostic output captured before removal;
- state used only during one one-shot execution.

It is a poor home for:

- databases and user uploads;
- irreplaceable work queues;
- encryption keys;
- audit records that must outlive the process;
- artifacts needed by another container;
- growing logs without an external lifecycle.

Container removal discards the writable layer. A host crash can lose it earlier. Restarting the same retained container may preserve it, which can create false confidence before replacement.

## 4. Account for copy-up behavior

With copy-on-write storage, modifying a lower-layer file can copy its content and metadata into the upper layer. Large or frequently modified files can therefore create unexpected I/O and storage use.

Writing into an image directory can also hide whether a file came from the build or runtime. Prefer explicit writable mount points such as `/run/app`, `/tmp`, or `/var/lib/app` according to the state contract.

Copy-up is an implementation optimization, not a durability guarantee. The application still needs correct file synchronization and atomic-update behavior under the backing filesystem's contract.

## 5. Make the root filesystem read-only where practical

A read-only root converts undeclared writes into immediate failures and narrows post-compromise persistence. Add explicit writable locations for:

- temporary files;
- runtime sockets and PID files;
- bounded caches;
- durable application data;
- package-specific paths that cannot yet be redesigned.

Test startup, normal operation, diagnostics, certificate refresh, time-zone access, and shutdown under this policy. Applications often write bytecode, history, plugin caches, or temporary files unexpectedly.

Read-only root does not make mounted paths read-only. Each mount has its own mode and policy.

## 6. Use temporary filesystems for truly temporary data

A tmpfs-style mount stores data in volatile memory-backed storage under the host's implementation and policy. It is useful for:

- scratch files that must not persist;
- runtime sockets;
- bounded intermediate transformations;
- short-lived sensitive material when the threat model permits;
- reducing writes to durable media.

Set a size limit and include tmpfs memory in capacity planning. Memory-backed data can contribute to memory pressure, and host swap or crash-dump policy can affect claims that data never reaches persistent media.

The data disappears when the mount or host lifecycle ends. Do not place recoverable work there unless it can be regenerated from a durable source.

## 7. Bind mounts expose a host path directly

A bind mount maps an existing host file or directory into the container. It is useful when the host and container intentionally share source, configuration, artifacts, or device-adjacent data.

Bind mounts create coupling to:

- exact host paths;
- host ownership and permissions;
- filesystem type and mount options;
- security labels;
- host backup and retention policy;
- files changed by non-container processes;
- node placement in a scheduler.

They are writable by default in many tools. Use read-only mode unless the container must modify the host content.

Never bind arbitrary system directories merely to satisfy a missing file. A writable bind of the host root, runtime socket, credential directory, or device path can collapse the isolation from Chapter 78.

## 8. Mounts obscure image content

Mounting at `/app/config` hides whatever the image supplied at that path for the life of the container. The hidden bytes remain in the image layer; they are not deleted.

This can cause confusing failures:

- an empty host directory hides default configuration;
- a file mount targets a path whose parent is missing;
- a volume seeded on first use contains an old schema;
- a mount at `/usr` hides the executable and prevents startup.

Inspect effective mounts and the unmounted image separately. Recreate the container with corrected mounts rather than attempting to unmount paths from inside it.

## 9. Managed volumes separate data from container identity

A managed volume has a lifecycle controlled by the container engine or a volume driver. A named volume can survive removal of every container that used it.

This is useful for application-owned data that needs local persistence without coupling the deployment specification to an arbitrary host path.

Do not confuse engine management with application durability. A local volume can still be lost with its host or disk. A remote volume's availability and consistency depend on its driver and storage service.

Name, label, encrypt, monitor, back up, and retire volumes as owned resources. Anonymous volumes are easy to orphan.

## 10. Understand first-use population

Some engines copy existing image content into a newly created empty volume mounted over that directory. Reusing a nonempty volume does not repeat the copy.

This behavior can surprise deployments:

- new image defaults never reach an existing volume;
- a volume silently receives files from an older image;
- ownership depends on the image content at first use;
- initialization races when several containers attach concurrently.

Do not rely on implicit population for schema migration. Use an explicit, versioned, idempotent initialization or migration step with durable state and exclusive ownership.

## 11. Match user IDs and permissions across the mount

The kernel authorizes filesystem operations using effective credentials and filesystem metadata. Names such as `appuser` are resolved separately inside and outside the container; numeric IDs cross the boundary.

Plan:

- runtime UID and GID;
- supplementary groups;
- user-namespace ID mapping;
- initial volume ownership;
- host-created file ownership;
- directory setgid and umask behavior;
- ACLs and security-module labels;
- read-only versus read-write mounts.

Avoid recursively changing ownership on every startup. It can be slow, can alter shared data unexpectedly, and often requires excess privilege. Initialize ownership once under a controlled step.

## 12. Include security labels and mount options

Ordinary mode bits can allow access while SELinux, AppArmor, or another policy denies it. Bind-mounted host paths may need labels compatible with the container policy.

Relabeling host directories has consequences outside the container. Apply product-specific shared or private labeling only to exact approved paths and inspect the resulting host label.

Useful mount controls can include:

- read-only;
- `nosuid`;
- `nodev`;
- `noexec` where execution is unnecessary;
- private mount propagation;
- filesystem-specific encryption and integrity options.

Support varies by platform and mount type. Verify effective mount information rather than trusting requested flags blindly.

## 13. External services can own durable state

An application does not need to store durable state in the container host. Databases, object stores, queues, and managed filesystems can provide independent lifecycles and replication.

External storage adds network, identity, latency, quota, consistency, and cost boundaries. It is not automatically safer or more durable.

Use stable operation identities and retries from Chapter 74. A container restart during an ambiguous remote write has the same duplicate-effect problem as any other client.

Keep endpoint configuration and credentials outside the image and scope them to the minimum data operations.

## 14. One volume does not create concurrency control

Mounting the same writable volume into several containers does not make the application safe for concurrent access.

Confirm:

- whether the filesystem supports the application's lock mechanism;
- whether locks work across hosts and failure modes;
- whether the data format permits multiple writers;
- whether append and rename semantics match expectations;
- how stale clients are fenced after lease loss;
- what happens during network partitions;
- whether caches remain coherent.

Use a single writer, database protocol, distributed lock with fencing, or partitioned data ownership according to the actual storage contract.

## 15. Design atomic and durable file updates

A common local-file update pattern is:

1. create a temporary file in the same filesystem;
2. write and validate complete content;
3. flush file data under the required durability policy;
4. atomically replace the destination;
5. flush the parent directory when required;
6. preserve or set intended ownership and mode.

Atomic visibility and crash durability are different properties. `rename` can prevent readers from observing a partial file while data remains vulnerable to power loss without synchronization.

Network filesystems and storage drivers can implement locks, rename, synchronization, sparse files, and direct I/O differently. Test the deployed storage type.

## 16. Treat database storage as a database contract

A volume makes database files persist. It does not make them consistent, backed up, replicated, or safe on every filesystem.

Follow the database's requirements for:

- filesystem and mount options;
- write ordering and synchronization;
- direct I/O or memory mapping;
- file locks;
- ownership and permissions;
- one-writer versus clustered operation;
- shutdown and crash recovery;
- snapshot and backup tooling;
- version upgrades and rollback.

Copying live database files without a database-supported snapshot boundary can produce a backup whose files never represented one consistent point in time.

## 17. Define backup consistency and scope

A backup design must identify:

- exact volume, database, and external objects included;
- application or database consistency point;
- encryption and key ownership;
- retention, immutability, and deletion;
- cross-host or cross-region copies;
- recovery point and recovery time objectives;
- schema and application compatibility;
- restore destination and authorization;
- verification and restore-test frequency.

A storage snapshot can be crash-consistent, application-consistent, or neither under the relevant system. Quiesce writes or use application-native backup interfaces when required.

The backup is not proven until a restore creates usable state and the application validates it.

## 18. Separate configuration, secrets, and data

Configuration and secrets often need different lifecycles from application data:

- configuration may be a read-only file or environment-specific object;
- a secret may be a read-only memory-backed file with rotation;
- generated runtime configuration may belong in tmpfs;
- durable application data belongs in a backed-up volume or service;
- immutable defaults belong in the image.

Mounting a secret file over a directory can hide adjacent configuration. Mount exact paths and validate ownership and mode.

Rotation can replace the mounted object while an application keeps an old open file descriptor. Define reload or restart behavior explicitly.

## 19. Monitor capacity and write amplification

Track more than volume byte usage:

- free bytes and inodes;
- writable-layer growth;
- copy-up and I/O latency;
- volume latency and errors;
- tmpfs and total memory pressure;
- log-driver storage;
- backup duration and failure;
- orphaned volumes and snapshots;
- quota consumption;
- filesystem read-only remounts or corruption signals.

Set alerts early enough to stop admission or expand capacity safely. Disk-full behavior should be tested; applications often report secondary errors after the first failed write.

## 20. Plan schema and ownership migration

Persistent data outlives image versions. Every release must state which data versions it can read and write.

Use a migration protocol with:

- durable version marker;
- exclusive ownership or fencing;
- preconditions and backup requirements;
- resumable steps and checkpoints;
- forward and backward compatibility window;
- post-migration validation;
- explicit irreversible boundary;
- operator evidence and recovery procedure.

Replacing a container with an older image does not roll back a data migration.

## 21. Complete example: model replacement and backup evidence

This standard-library model creates instance-local writable and temporary directories, a separately owned volume, and a host bind source inside one disposable sandbox. Replacing the instance removes only its owned ephemeral paths:

```python
from __future__ import annotations

import hashlib
import json
import shutil
import unittest
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory


@dataclass(frozen=True)
class InstancePaths:
    writable: Path
    temporary: Path
    volume: Path
    bind: Path


class StorageModel:
    def __init__(self, sandbox: Path) -> None:
        self.sandbox = sandbox.resolve()
        self.instances = self.sandbox / "instances"
        self.volumes = self.sandbox / "volumes"
        self.host_paths = self.sandbox / "host-paths"
        self.instances.mkdir(parents=True)
        self.volumes.mkdir()
        self.host_paths.mkdir()

    def create_instance(self, name: str, volume_name: str) -> InstancePaths:
        root = (self.instances / name).resolve()
        volume = (self.volumes / volume_name).resolve()
        if root.parent != self.instances.resolve():
            raise RuntimeError(f"refusing unsafe instance path: {root}")
        if volume.parent != self.volumes.resolve():
            raise RuntimeError(f"refusing unsafe volume path: {volume}")
        writable = root / "writable"
        temporary = root / "tmpfs-simulation"
        bind = self.host_paths / "shared-input"
        for path in (writable, temporary, volume, bind):
            path.mkdir(parents=True, exist_ok=True)
        return InstancePaths(writable, temporary, volume, bind)

    def remove_instance(self, name: str) -> None:
        target = (self.instances / name).resolve()
        if target.parent != self.instances.resolve():
            raise RuntimeError(f"refusing unsafe instance path: {target}")
        if target.exists():
            shutil.rmtree(target)


def file_manifest(root: Path) -> bytes:
    entries = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        content = path.read_bytes()
        entries.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": hashlib.sha256(content).hexdigest(),
                "size": len(content),
            }
        )
    return (
        json.dumps(entries, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def verify_manifest(root: Path, manifest: bytes) -> None:
    expected = json.loads(manifest)
    actual = json.loads(file_manifest(root))
    if actual != expected:
        raise ValueError("restored data does not match backup manifest")


class StorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.sandbox = Path(self.temporary_directory.name) / "sandbox"
        self.sandbox.mkdir()
        self.model = StorageModel(self.sandbox)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_volume_survives_instance_replacement(self) -> None:
        first = self.model.create_instance("container-a", "application-data")
        (first.writable / "cache.bin").write_bytes(b"rebuildable")
        (first.temporary / "session.tmp").write_bytes(b"temporary")
        (first.volume / "records.db").write_bytes(b"durable-records")

        self.model.remove_instance("container-a")
        second = self.model.create_instance("container-b", "application-data")

        self.assertFalse((second.writable / "cache.bin").exists())
        self.assertFalse((second.temporary / "session.tmp").exists())
        self.assertEqual(
            (second.volume / "records.db").read_bytes(),
            b"durable-records",
        )

    def test_bind_path_is_owned_outside_instance(self) -> None:
        first = self.model.create_instance("container-a", "data")
        (first.bind / "config.toml").write_text(
            "mode = 'safe'\n",
            encoding="utf-8",
        )

        self.model.remove_instance("container-a")
        second = self.model.create_instance("container-b", "data")

        self.assertEqual(
            (second.bind / "config.toml").read_text(encoding="utf-8"),
            "mode = 'safe'\n",
        )

    def test_backup_manifest_detects_restore_corruption(self) -> None:
        instance = self.model.create_instance("container-a", "data")
        (instance.volume / "a.txt").write_bytes(b"alpha")
        (instance.volume / "nested").mkdir()
        (instance.volume / "nested" / "b.txt").write_bytes(b"beta")
        manifest = file_manifest(instance.volume)

        restore = self.sandbox / "restore"
        shutil.copytree(instance.volume, restore)
        verify_manifest(restore, manifest)

        (restore / "a.txt").write_bytes(b"corrupt")
        with self.assertRaisesRegex(ValueError, "does not match"):
            verify_manifest(restore, manifest)

    def test_instance_removal_is_bounded_to_owned_directory(self) -> None:
        sentinel = self.model.host_paths / "sentinel.txt"
        sentinel.write_text("keep\n", encoding="utf-8")
        self.model.create_instance("container-a", "data")

        self.model.remove_instance("container-a")

        self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

Run it in a disposable directory:

```bash
python -m unittest -v test_storage_lifecycle.py
```

The `tmpfs-simulation` directory models lifetime only; it is not memory-backed. The test proves ownership and replacement logic, not Docker mount implementation or crash durability.

The backup manifest proves copied bytes match one captured source tree. It does not create an application-consistent snapshot of a live database. Use the application's supported backup boundary first, then add integrity evidence.

## 22. Safe engine lab: replace the container

On an approved disposable Docker-compatible engine, this Bash lab creates a uniquely named volume, writes one durable and one instance-local file, removes the container, and verifies only the volume data survives replacement:

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

suffix="$RANDOM-$$"
volume="handbook-data-$suffix"
first="handbook-storage-a-$suffix"
second="handbook-storage-b-$suffix"
image="alpine:3.21"

cleanup() {
  docker rm --force "$first" "$second" >/dev/null 2>&1 || true
  docker volume rm "$volume" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker volume create "$volume" >/dev/null
docker run --name "$first" \
  --mount "type=volume,source=$volume,target=/data" \
  "$image" sh -c \
  'printf "durable\n" > /data/record && printf "ephemeral\n" > /instance'
docker rm "$first" >/dev/null

docker run --name "$second" \
  --read-only \
  --tmpfs /tmp:rw,nosuid,nodev,noexec,size=16m \
  --mount "type=volume,source=$volume,target=/data" \
  "$image" sh -c '
    test "$(cat /data/record)" = "durable"
    test ! -e /instance
    printf "temporary\n" > /tmp/probe
  '

docker rm "$second" >/dev/null
docker volume rm "$volume" >/dev/null
trap - EXIT
```

The lab deletes its volume intentionally and permanently during cleanup. Use only the uniquely created disposable volume; never substitute an existing data volume.

## 23. Diagnose missing or unwritable data

Inspect in this order:

1. effective mount type, source, destination, and read/write mode;
2. whether the mount obscures image content;
3. container UID, GID, supplementary groups, and user mapping;
4. numeric ownership, mode, ACLs, and security labels;
5. host path existence and node placement;
6. filesystem type, mount options, and capacity;
7. volume-driver and storage-service health;
8. application locks, synchronization, and error logs;
9. migration or initialization state;
10. backup and last verified restore.

Do not fix a permission error with privileged mode or mode `0777` before identifying the failed check and intended owner.

## Common Misconceptions

- “Restarting proves persistence.” The same container can retain its writable layer; replacement is the real test.
- “A named volume is a backup.” It can share the same host, disk, failure domain, and administrative mistakes.
- “Read-only root means the whole container is read-only.” Mounted paths retain independent modes.
- “Bind mounts are portable.” They couple the deployment to host paths and semantics.
- “Shared storage supports multiple writers.” The application and filesystem must provide a compatible concurrency protocol.
- “Copying database files creates a valid backup.” Live files may not form one consistent recovery point.

## Core Computer Science Concept

Container storage is **lifetime and ownership composition over mounted namespaces**. A pathname resolves through the effective mount graph, while durability, consistency, and recovery belong to the backing store's contract.

## Engineering Connections

- Image lower layers and copy-on-write extend Chapter 79's ordered changeset model.
- Instance replacement applies the process lifecycle from Chapter 82.
- Stable operation identities remain necessary for remote storage retries from Chapter 74.
- Volume migration is another durable state machine with irreversible transitions.
- Restore verification turns backup from intent into testable evidence.

## From the Field

A database writes to `/var/lib/database` in the container's writable layer. Repeated restarts preserve the same container, so the team believes data is durable. A deployment replaces the container and every record disappears. A named, backed-up volume plus a replacement and restore test would have exposed the lifetime mismatch before production.

## Engineering Review

### What problem does this solve?

It gives every writable path an explicit lifetime, owner, permission model, consistency contract, capacity limit, backup boundary, and replacement behavior.

### Why was it designed this way?

Container instances are replaceable, while different classes of state require different storage and failure domains.

### When should I use it?

Use this classification for every container that writes files, mounts host or managed storage, or accesses an external data service.

### When should I avoid it?

Avoid local persistent volumes when the required availability, sharing, or failure-domain contract needs an external or replicated storage service.

### How does this make me a better engineer?

It teaches you to reason from data lifetime and consistency to storage choice instead of treating a container pathname as durability.

### How does this reduce waste?

It prevents accidental data loss, orphaned volumes, permission workarounds, copy-up overhead, inconsistent backups, and unreproducible host coupling.

## Handbook Principle #83

> Make the root disposable, mount only deliberate state, and prove durability by replacement plus restore under the real storage contract.

## Practical Observation

Run the filesystem model and then the disposable engine lab where available. Record which paths survive process restart, container replacement, volume removal, and host replacement. For durable data, produce a backup manifest, restore elsewhere, and validate it with the application—not only a checksum.

## Looking Ahead

Storage mounts connect containers to data; network paths connect them to clients and services. Chapter 84 follows namespace interfaces, bridge routing, port publication, DNS, service identity, and packet diagnosis without confusing container ports with host ports.

## References

- [Docker Engine storage overview](https://docs.docker.com/engine/storage/)
- [Docker Engine volumes](https://docs.docker.com/engine/storage/volumes/)
- [Docker Engine bind mounts](https://docs.docker.com/engine/storage/bind-mounts/)
- [Docker Engine tmpfs mounts](https://docs.docker.com/engine/storage/tmpfs/)
- [Docker Engine storage drivers](https://docs.docker.com/engine/storage/drivers/)
- [Linux kernel documentation — Overlay Filesystem](https://docs.kernel.org/filesystems/overlayfs.html)
- [OCI Runtime Specification — Mount configuration](https://specs.opencontainers.org/runtime-spec/config/#mounts)
- [Linux `fsync(2)` manual page](https://man7.org/linux/man-pages/man2/fsync.2.html)
