# Chapter 98 — EBS, EFS, and Choosing Cloud Storage

“Put it on durable storage” is not a design. A database needs blocks with predictable latency, a fleet may need a shared POSIX namespace, a web service may need immutable objects, and a batch job may need disposable local scratch. Those requirements lead to different services and different failure boundaries.

The central idea is:

> Choose storage by access semantics first, then prove attachment scope, concurrency, latency, persistence, recovery, encryption, and cost under the failures the workload must survive.

## 1. Start with the interface, not the product name

AWS exposes several storage models to compute:

| Model | Common AWS choice | Application sees | Natural scope |
| --- | --- | --- | --- |
| Block | Amazon EBS | A raw block device | One Availability Zone |
| Shared file | Amazon EFS | An NFS file hierarchy | Regional or One Zone |
| Object | Amazon S3 | Bucket, key, version, and API | Regional service |
| Ephemeral block | EC2 instance store | A local block device | One instance lifetime |

The models are not interchangeable abstractions over the same disk. A filesystem can be created on a block device, but that does not make the device safe for independent writers. An object key can contain slashes, but that does not create POSIX rename, locking, or append semantics. A shared file system can be mounted by many clients, but it is not local NVMe latency.

Ask which operations must be correct:

- sector or page reads and writes;
- open, seek, append, rename, permissions, and file locking;
- whole-object `PUT`, `GET`, list, version, and conditional update;
- temporary spill, cache, shuffle, or replicated shard data.

Only then compare products.

## 2. EBS is network-attached block storage

An EBS volume appears to an EC2 instance as a block device. The guest operating system owns partitioning, filesystem or database layout, mounting, free-space management, and application consistency.

EBS persists independently from an instance when its lifecycle settings preserve the volume. It is suited to:

- boot and data volumes;
- database files and journals;
- filesystems used by one active host;
- applications expecting raw devices;
- durable state that must detach and reattach within an Availability Zone.

The service stores blocks; it does not understand whether a block belongs to a committed transaction, a half-written file, or unused filesystem space. Backup and recovery must coordinate with the software interpreting those blocks.

## 3. EBS volumes are Availability Zone resources

Create and attach an EBS volume in the same Availability Zone as its EC2 instance. An ordinary volume cannot be detached in one zone and attached directly in another. The volume's data is replicated within its zone for durability, but that does not turn it into a multi-zone application.

To recover in another zone, a common path is:

1. create or locate a usable snapshot;
2. create a new volume from that snapshot in the destination zone;
3. attach it to replacement compute;
4. initialize blocks as required;
5. mount or recover the filesystem or database;
6. validate application state before serving traffic.

Recovery time includes snapshot age, volume creation, block initialization, operating-system discovery, filesystem or database recovery, and application validation. “We take snapshots” is not an Availability Zone recovery objective.

## 4. Attachment lifecycle can delete durable data

Every EBS block-device mapping has lifecycle behavior. `DeleteOnTermination` determines whether EC2 deletes the volume when the attached instance terminates. Root volumes commonly default to deletion; data-volume behavior depends on how they were attached and configured.

Record for every volume:

- purpose and data owner;
- instance and device mapping;
- `DeleteOnTermination` value;
- filesystem UUID or logical-volume identity;
- mount unit and ordering;
- encryption key;
- snapshot and restore policy;
- orphan detection and final deletion authority.

Setting deletion to false can protect data from instance termination but creates orphaned cost and sensitive remnants. Setting it to true makes instance replacement destructive unless data is reproducible or recovered elsewhere. Match the flag to a tested lifecycle rather than a universal default.

## 5. Choose EBS type from measured I/O

EBS performance has several independent dimensions:

- I/O operations per second;
- throughput in bytes per second;
- operation size and read/write mix;
- latency distribution and queue depth;
- burst or sustained behavior;
- volume size and provisioned performance;
- EC2 instance EBS bandwidth and IOPS limits;
- application and filesystem behavior.

Major families include:

- `gp3` general-purpose SSD, with capacity, IOPS, and throughput provisioned independently within service limits;
- `gp2` previous-generation general-purpose SSD, whose baseline and burst behavior are tied more closely to size;
- `io2` and `io1` provisioned-IOPS SSD for demanding latency and durability needs, with feature and limit differences;
- `st1` throughput-optimized HDD for large sequential workloads;
- `sc1` cold HDD for lower-cost, infrequently accessed sequential data;
- magnetic `standard` for previous-generation compatibility.

Do not choose HDD-backed volumes for small random I/O or boot volumes. Do not buy maximum IOPS when the instance, queue depth, filesystem, or application cannot drive them. Benchmark representative data size and concurrency, then observe both the volume and instance ceilings.

## 6. Filesystems remain the customer's responsibility

After attaching an empty volume, the guest may need partitioning, a filesystem, a mount point, and a persistent mount definition. A restored volume may contain an existing filesystem and must not be reformatted.

Automation should distinguish:

- new blank device;
- expected existing filesystem;
- restored clone with a duplicate UUID;
- device name that changed after reboot;
- missing or incorrectly attached volume;
- filesystem requiring repair;
- encrypted or layered device mapping.

Identify devices through stable metadata rather than assuming a Linux device name remains fixed. Mount with bounded failure behavior; a critical missing data volume may need to stop application startup, while an optional scratch volume may degrade safely.

The storage service can be healthy while the filesystem is full, read-only, corrupt, or mounted at the wrong path. Monitor the guest layer too.

## 7. Resizing has a service step and a guest step

Elastic Volumes can modify supported volume type, size, IOPS, and throughput without detaching in many configurations. Increasing EBS capacity does not automatically expand every partition, logical volume, or filesystem inside it.

A safe growth procedure includes:

1. confirm backup and rollback constraints;
2. measure which layer is full or slow;
3. request a supported volume modification;
4. observe modification state and new limits;
5. extend the partition or logical volume if present;
6. grow the filesystem using its supported tool;
7. validate capacity and application latency;
8. update infrastructure code and cost expectations.

Most EBS size changes are increases; shrinking generally requires creating a smaller destination, copying data at the filesystem or application layer, and cutting over. Do not confuse a larger block device with successful filesystem growth.

## 8. Multi-Attach is a specialized block contract

Supported provisioned-IOPS volumes can use EBS Multi-Attach in documented configurations. This lets multiple instances in the same Availability Zone attach the same volume, but it does not turn an ordinary filesystem into a safe cluster filesystem.

Independent writers can corrupt metadata and data unless the application or cluster filesystem coordinates access. Multi-Attach designs need:

- a supported volume and instance configuration;
- cluster-aware filesystem or application semantics;
- fencing so a failed node cannot continue writing;
- reservation and lock behavior;
- failover and split-brain tests;
- one-zone failure assumptions;
- snapshot consistency across writers.

If the requirement is simply “many Linux hosts need the same files,” EFS is usually the more natural semantic match.

## 9. EBS snapshots are incremental point-in-time copies

An EBS snapshot captures the blocks needed to restore a volume. The first snapshot is logically full; later snapshots are incremental in storage, while each snapshot can independently restore a complete volume. Snapshots are Regional and their data is replicated across Availability Zones in that Region.

Incremental implementation affects cost, not restore usability. Deleting one snapshot does not necessarily free all blocks written during its interval because later snapshots can still reference them.

A snapshot records blocks at a point in time, but application consistency depends on what the guest was doing. Options include:

- crash-consistent snapshot, relying on filesystem and database recovery;
- flushing and freezing a filesystem briefly;
- database-native quiesce or backup mode;
- application-consistent orchestration;
- coordinated multi-volume snapshot when one dataset spans volumes.

Never claim application-consistent backup solely because the snapshot API completed.

## 10. Restore performance is part of the backup contract

Volumes restored from snapshots can fetch blocks from backing snapshot storage as those blocks are first accessed. Until initialization completes, first access can have higher latency. Options include:

- reading every required block before production use;
- specifying a supported volume initialization rate;
- enabling Fast Snapshot Restore for selected snapshots and zones;
- accepting lazy initialization only when the application tolerates it.

Restore drills should measure time from incident declaration to validated application service, not merely time to create a volume. Include KMS access, snapshot sharing or copy, destination-zone capacity, initialization, filesystem recovery, and data verification.

Retention and copy policy should cover accidental deletion, ransomware or administrator compromise, Regional recovery, and regulatory needs. Snapshot lock or separately governed backup vaults may strengthen independence when required.

## 11. EBS encryption follows the volume and snapshot chain

EBS encryption covers data at rest, data moving between volume and instance, snapshots, and volumes created from encrypted snapshots. Account-level encryption by default helps prevent accidental unencrypted creation. Customer-managed KMS keys add policy and revocation control but also add a recovery dependency.

Review:

- default key per Region;
- launch permissions and cross-account snapshot copy;
- grants created for EC2 and Auto Scaling;
- key availability during replacement and disaster recovery;
- re-encryption when copying snapshots;
- public snapshot controls;
- separation between snapshot deletion and KMS-key deletion.

An encrypted snapshot shared without usable KMS permission is not recoverable by the recipient. Test the exact restore principal and account.

## 12. EFS is a managed shared NFS filesystem

EFS presents NFS file semantics to supported AWS compute and connected clients. Multiple EC2 instances, containers, and supported Lambda functions can share directories and files without attaching one block volume to every writer.

EFS is a natural fit for:

- shared web content or user uploads requiring file APIs;
- home directories and developer tooling;
- content-management systems built for NFS;
- shared model, media, or configuration files;
- container workloads needing ReadWriteMany-style storage;
- migrations that genuinely depend on POSIX-like paths and permissions.

It is not automatically the right database volume. Network filesystem latency, locking, small-file metadata behavior, application support, and database durability requirements must be validated by the software vendor and workload tests.

## 13. Regional and One Zone EFS have different failure scopes

A Regional EFS filesystem stores data across multiple Availability Zones. Create a mount target in each zone where clients run and use the same-zone target for performance and transfer-cost reasons. DNS and the EFS mount helper support this normal path.

An EFS One Zone filesystem stores data within one Availability Zone and has one mount target. It can reduce storage cost for workloads whose recovery and zone-loss posture accept that scope. Cross-zone access adds transfer cost and can add latency while retaining the one-zone data dependency.

Do not describe both as simply “EFS.” Record:

- filesystem type and zone scope;
- client zones and mount targets;
- remaining service after a client or mount-target failure;
- behavior after a data-zone failure;
- replication or backup recovery path;
- cross-zone transfer and latency;
- placement constraints for ECS, EKS, and Lambda clients.

## 14. Network and POSIX authorization both matter

An EFS client path can cross several controls:

- VPC routes and DNS;
- mount-target security group allowing NFS traffic;
- filesystem resource policy;
- IAM authorization when the mount uses it;
- access-point identity and root-directory settings;
- NFS user and group IDs;
- POSIX owner, mode bits, and application permissions.

A permissive security group does not grant file access, and restrictive POSIX modes do not prevent every network client from reaching the NFS endpoint. Test the complete mount identity.

EFS access points can present an application-specific root directory and POSIX identity. They are useful for isolating workloads on one filesystem, but do not make every tenant design secure by default. Review namespace escape, shared numeric IDs, filesystem policy, and administrative mounts.

## 15. Encrypt EFS at rest and in transit

EFS can encrypt data and metadata at rest with KMS. The choice is made when the filesystem is created; converting an existing unencrypted filesystem requires migration to a new encrypted filesystem.

Encryption in transit is a client mount decision. The EFS mount helper establishes a TLS tunnel when the `tls` option is used. Enforce it with filesystem policy where required and verify active mounts rather than assuming at-rest encryption covers NFS traffic.

Customer-managed KMS keys need usable policy and grants for the EFS service. Revoking access can make the filesystem unavailable. Include key recovery, cross-account administration, replication, backup restore, and retirement in the design.

## 16. EFS performance is workload-shaped

EFS performance depends on filesystem type, performance mode, throughput mode, client version, I/O size, concurrency, storage class, and Region limits.

Current design choices include:

- **General Purpose** performance mode for the lowest per-operation latency and recommended new use;
- **Elastic throughput** that scales with workload activity;
- **Provisioned throughput** for an explicitly purchased level independent of stored size;
- **Bursting throughput** whose baseline and credits relate to data stored in Standard class.

Small serial metadata operations may expose network round trips even when aggregate throughput looks high. Parallel clients and larger I/O can improve total throughput. Measure open/stat/list behavior, read and write sizes, metadata intensity, sync writes, lock contention, and per-client ceilings with representative files.

Monitor throughput utilization, burst credits where applicable, connections, client health, and application latency. Provisioning more throughput does not remove per-operation latency or a single-threaded application bottleneck.

## 17. EFS lifecycle and backup are separate controls

EFS lifecycle management can move files among Standard, Infrequent Access, and Archive classes according to access age and configured return behavior. Metadata operations do not necessarily count like data access for lifecycle decisions. Lower-cost classes can add access charges and different latency expectations.

Lifecycle changes storage cost; it is not backup. AWS Backup can schedule protected EFS recovery points and restore a full filesystem or selected items according to supported behavior. Define:

- backup frequency and recovery point objective;
- retention and vault/account separation;
- whole-filesystem versus item-level recovery;
- restore destination and permissions;
- encryption-key availability;
- recovered path and name conflicts;
- time to scan and validate large file counts.

Replicating EFS can support Regional or zone recovery designs, but—as with S3—replication and backup have different independence and corruption semantics.

## 18. Instance store is intentionally ephemeral

Instance store exposes physically attached storage included with certain EC2 instance types. It can provide high local IOPS and low latency without separate EBS billing, making it useful for:

- caches and rebuildable indexes;
- sort, shuffle, and temporary workspace;
- replicated database shards whose cluster tolerates member loss;
- buffers whose authoritative data is elsewhere;
- high-performance scratch.

Data survives an ordinary reboot but not stop, hibernation, termination, many recovery events, underlying device failure, or movement to another instance. It cannot be detached and reattached elsewhere. An EBS-backed AMI does not capture instance-store data.

Use it only when loss is an expected state transition. Startup should format or validate it, the application should rebuild without operator archaeology, and monitoring should avoid treating its disappearance as mysterious corruption.

## 19. S3 remains the object alternative

Chapter 97 established S3's bucket/key/version model. Compared with mounted storage, S3 offers whole-object APIs, independent compute access, versioning, lifecycle, replication, and very large namespace scale. It does not offer ordinary block writes or POSIX file behavior.

Choose S3 when applications can use object semantics for:

- immutable artifacts and media;
- backups and exports;
- logs and analytical data;
- static web assets;
- manifests and datasets;
- asynchronous exchange between systems.

Avoid adding a filesystem gateway inside an application merely to hide object semantics unless that gateway's caching, consistency, rename, permissions, and failure behavior are explicitly acceptable. Sometimes changing the application to use object APIs produces the simpler durable design.

## 20. Compare choices against the workload contract

| Requirement | EBS | EFS Regional | EFS One Zone | S3 | Instance store |
| --- | --- | --- | --- | --- | --- |
| Raw block device | Yes | No | No | No | Yes |
| Shared file namespace | Specialized only | Yes | Yes | No | No |
| Object API | No | No | No | Yes | No |
| Survives instance replacement | If preserved | Yes | Yes | Yes | No |
| Native scope beyond one AZ | Snapshot recovery | Yes | No | Yes | No |
| Local-device latency | No | No | No | No | Yes |
| Independent version history | Snapshots | Backup | Backup | Object versions | No |
| Capacity management | Provision/modify | Elastic | Elastic | Elastic | Instance-defined |

This table narrows candidates; it does not select a final design. A requirement for synchronous cross-zone database writes, Windows file protocols, high-performance parallel files, or enterprise NAS features may point to a database service or an FSx family deferred from this chapter.

## 21. Separate capacity, performance, and recovery

Three plans are often confused:

1. **Capacity plan:** how much data and growth can be stored?
2. **Performance plan:** what IOPS, throughput, latency, concurrency, and request shape are required?
3. **Recovery plan:** from which independent point can data be restored, where, and within what time?

A 10-TiB EBS volume can have inadequate IOPS. An EFS filesystem that expands automatically can have an unsuitable metadata workload. A fast instance store can have zero recoverability. A complete design answers all three plans independently.

Benchmark at the application boundary. Synthetic storage tools help isolate limits, but user-visible latency includes serialization, filesystem, kernel cache, network, queueing, locks, database behavior, and downstream work.

## 22. Migration changes semantics as well as bytes

A storage migration must preserve the application contract, not only copy content.

Inventory:

- file types, sizes, sparsity, links, ownership, modes, ACLs, and timestamps;
- active writers and locking;
- case sensitivity and name constraints;
- object metadata, checksums, versions, and tags;
- capacity and change rate;
- expected cutover outage;
- encryption and network path;
- destination performance and quotas;
- validation and rollback evidence.

Use an initial bulk copy, incremental synchronization or change capture, a write freeze or dual-write protocol with reconciliation, final validation, and an explicit switch. Dual writes are not automatically atomic; define what happens when one destination succeeds and the other fails.

Validate counts, logical bytes, checksums, permissions, application reads and writes, performance, backups, and recovery. Retain the source read-only through the rollback window before reviewed deletion.

## 23. Rehearse storage failures

Test at least:

- an instance terminates with each EBS deletion setting;
- a volume reaches full capacity or its performance ceiling;
- a snapshot is crash-consistent but the database needs recovery;
- a restored EBS volume encounters first-read latency;
- a KMS key or grant is unavailable;
- one Availability Zone and its EBS volumes are unavailable;
- an EFS mount target or client TLS helper fails;
- a shared filesystem sees conflicting writers and locks;
- EFS lifecycle moves a cold file before a latency-sensitive read;
- instance-store data disappears during replacement;
- backup exists but restore permissions or destination quota fail;
- the migration cutover must roll back after new writes.

For each, define detection, application behavior, data-loss bound, recovery time, authority, evidence, and cleanup. Device presence and successful mounting are not data correctness.

## 24. Make storage selection executable

The following standard-library lab encodes a small requirements-to-service decision and validates the surrounding protection contract. Specialized cluster filesystems and managed databases intentionally require a separate review.

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StorageRequirement:
    access_model: str
    shared_writers: bool
    survive_instance_loss: bool
    survive_az_loss_without_restore: bool
    data_loss_tolerated: bool


def choose_service(requirement: StorageRequirement) -> str:
    if requirement.access_model == "object":
        return "s3"
    if requirement.access_model == "shared-file":
        return "efs-regional" if requirement.survive_az_loss_without_restore else "efs-one-zone"
    if requirement.access_model == "block":
        if requirement.shared_writers:
            raise ValueError("shared block writers require a specialized cluster review")
        if requirement.survive_az_loss_without_restore:
            raise ValueError("zonal block storage cannot provide no-restore AZ survival")
        return "ebs"
    if requirement.access_model == "ephemeral-block":
        if requirement.survive_instance_loss or not requirement.data_loss_tolerated:
            raise ValueError("instance store requires disposable data")
        return "instance-store"
    raise ValueError("unsupported access model")


@dataclass(frozen=True)
class StorageContract:
    requirement: StorageRequirement
    selected_service: str
    encrypted_at_rest: bool
    encrypted_in_transit: bool
    backup_enabled: bool
    restore_tested: bool
    performance_tested: bool
    lifecycle_owner: str
    ebs_delete_on_termination: bool | None = None
    efs_mount_targets: int | None = None

    def validate(self) -> None:
        expected = choose_service(self.requirement)
        if self.selected_service != expected:
            raise ValueError(f"access contract requires {expected}")
        if not self.encrypted_at_rest:
            raise ValueError("persistent storage must be encrypted at rest")
        if self.selected_service == "efs-regional" and not self.encrypted_in_transit:
            raise ValueError("shared file traffic must use TLS")
        if self.selected_service == "efs-regional":
            if self.efs_mount_targets is None or self.efs_mount_targets < 2:
                raise ValueError("Regional EFS needs mount targets in client AZs")
        if self.selected_service == "ebs" and self.ebs_delete_on_termination is None:
            raise ValueError("EBS deletion behavior must be explicit")
        if not self.requirement.data_loss_tolerated:
            if not self.backup_enabled or not self.restore_tested:
                raise ValueError("durable data needs tested backup and restore")
        if not self.performance_tested:
            raise ValueError("storage performance must be workload-tested")
        if not self.lifecycle_owner:
            raise ValueError("storage lifecycle needs an owner")
```

Tests cover semantic mismatches rather than vendor labels:

```python
import unittest

from storage_contract import StorageContract, StorageRequirement, choose_service


class StorageContractTests(unittest.TestCase):
    def test_regional_shared_file_contract_is_accepted(self) -> None:
        requirement = StorageRequirement(
            access_model="shared-file",
            shared_writers=True,
            survive_instance_loss=True,
            survive_az_loss_without_restore=True,
            data_loss_tolerated=False,
        )
        StorageContract(
            requirement=requirement,
            selected_service="efs-regional",
            encrypted_at_rest=True,
            encrypted_in_transit=True,
            backup_enabled=True,
            restore_tested=True,
            performance_tested=True,
            lifecycle_owner="platform-storage",
            efs_mount_targets=3,
        ).validate()

    def test_shared_file_requirement_rejects_ebs(self) -> None:
        requirement = StorageRequirement(
            "shared-file", True, True, True, False
        )
        contract = StorageContract(
            requirement, "ebs", True, True, True, True, True, "team",
            ebs_delete_on_termination=False,
        )
        with self.assertRaisesRegex(ValueError, "requires efs-regional"):
            contract.validate()

    def test_instance_store_rejects_durable_data(self) -> None:
        requirement = StorageRequirement(
            "ephemeral-block", False, True, False, False
        )
        with self.assertRaisesRegex(ValueError, "requires disposable data"):
            choose_service(requirement)

    def test_ebs_requires_explicit_termination_behavior(self) -> None:
        requirement = StorageRequirement("block", False, True, False, False)
        contract = StorageContract(
            requirement, "ebs", True, True, True, True, True, "database"
        )
        with self.assertRaisesRegex(ValueError, "deletion behavior"):
            contract.validate()

    def test_untested_restore_is_rejected(self) -> None:
        requirement = StorageRequirement("object", True, True, True, False)
        contract = StorageContract(
            requirement, "s3", True, True, True, False, True, "records"
        )
        with self.assertRaisesRegex(ValueError, "tested backup and restore"):
            contract.validate()


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

Save the blocks as `storage_contract.py` and `test_storage_contract.py`, then run:

```bash
python -m unittest -v test_storage_contract.py
```

The selector demonstrates reasoning, not a universal product recommendation. A production verifier should inspect authorized read-only inventory for EBS attachment and deletion settings, types, performance, encryption, snapshots, initialization, EFS type, mount targets, policies, access points, encryption, lifecycle, backup, metrics, and instance-store mappings. It must not attach, resize, mount, snapshot, restore, or delete storage during validation.

## 25. Review a storage choice

```text
workload, owner, data class, access model, and authoritative source:
block, shared-file, object, or disposable-local operations required:
single writer, coordinated multi-writer, or independent object writers:
capacity, growth, object/file count, and free-space alarm:
IOPS, throughput, latency, I/O size, concurrency, and measured ceilings:
instance, AZ, Region, account, and client attachment scope:
filesystem, mount, device identity, permissions, and locking:
encryption at rest, in transit, keys, grants, and recovery:
instance termination, scale-in, detach, and orphan behavior:
snapshot or backup consistency, frequency, retention, and independence:
restore location, initialization, validation, RPO, and measured RTO:
zone-loss and Region-loss behavior:
lifecycle tiers, access charges, minimum durations, and deletion owner:
logs, metrics, quotas, failure alarms, and cost allocation:
migration copy, change capture, cutover, validation, and rollback:
```

## Common Misconceptions

- “Storage is storage.” Block, file, object, and ephemeral devices expose different correctness contracts.
- “EBS is tied to an instance.” A preserved volume outlives it, but remains tied to an Availability Zone.
- “A snapshot is automatically application-consistent.” Guest writes and transactions require coordination or recovery.
- “Increasing an EBS volume grows the filesystem.” The guest layers may need separate extension.
- “Multi-Attach makes any filesystem shared.” Writers need cluster coordination and fencing.
- “EFS is an infinitely fast local disk.” Network round trips, metadata, throughput mode, and clients shape performance.
- “Regional EFS needs one mount target.” Use a target in each client zone for resilience, performance, and cost.
- “At-rest encryption secures NFS traffic.” EFS transport encryption is a separate mount and policy choice.
- “Instance store is unreliable EBS.” It is deliberately disposable local storage with different performance and lifecycle.
- “Backup exists because data is durable.” Recovery points, keys, permissions, and tested restore remain separate.

## Core Computer Science Concept

Storage selection applies **abstract data types and failure-domain composition**. Block devices expose addressable sectors, filesystems expose named mutable byte streams and metadata, and object stores expose versionable values. The chosen abstraction determines legal operations; its physical and service scope determines which failures can remove availability or state.

## Engineering Connections

- EBS device contracts continue Chapter 95's instance and volume lifecycle.
- S3 comparison uses Chapter 97's immutable object identity.
- Filesystem caches and sync behavior apply operating-system durability semantics.
- Snapshot quiescing is a distributed checkpoint across application and storage layers.
- EFS mount targets depend on Chapter 93's subnet and Availability Zone model.
- KMS dependencies continue Chapter 92's authorization and temporary-identity boundaries.
- Backup and restore apply Part VI's recovery-point and recovery-time reasoning.

## From the Field

A team grows a full EBS volume from 200 to 400 GiB and closes the incident because the console shows the new size. The database still reports no free space: the partition and filesystem were never expanded. Monitoring only the service layer hid the guest layer. A runbook that verifies the block device, partition, filesystem, mount, database, and infrastructure declaration would have completed the change instead of merely allocating it.

## Engineering Review

### What problem does this solve?

It selects and operates AWS storage according to block, shared-file, object, or ephemeral semantics while making attachment, performance, encryption, backup, failure scope, lifecycle, and migration explicit.

### Why was it designed this way?

Different data structures and sharing patterns need different interfaces. AWS separates them so each service can optimize its protocol, scaling, durability, and operational control, leaving the application to choose the correct abstraction.

### When should I use it?

Use this model before provisioning application storage, changing EBS performance or size, introducing shared files, selecting instance store, defining backups, or migrating between storage systems.

### When should I avoid it?

Avoid forcing a general storage service onto a workload whose primary need is a managed database, specialized parallel filesystem, Windows file share, enterprise NAS protocol, or transactional coordination the service does not provide.

### How does this make me a better engineer?

It teaches you to distinguish interface semantics from physical persistence, measure the real bottleneck, and compose storage, compute, zone, key, and backup failure domains into one recovery contract.

### How does this reduce waste?

It reduces overprovisioned IOPS, oversized idle volumes, orphaned disks, needless cross-zone traffic, premature archive tiers, unrecoverable scratch data, unused shared filesystems, and backups that cannot meet restore time.

## Handbook Principle #98

> The right storage service is the one whose native operations and failure scope match the data contract before performance and price are optimized.

## Practical Observation

Pick one stateful workload and trace a single byte from the application call to its durable and recoverable form. Identify the device or API, filesystem and mount, instance and zone, encryption key, snapshot or backup, destination recovery zone, initialization step, and validation query. Measure the restore rather than estimating it. If any layer is described only as “persistent,” replace that label with its exact survival and recovery behavior.

## Looking Ahead

Raw storage still leaves teams operating the database engine, replication, backups, failover, patching, and connections. Chapter 99 examines how RDS and Aurora move parts of that operational burden into a managed relational service while leaving schema, query, capacity, recovery, and change ownership with the application team.

## References

- [Amazon EC2 — Storage options for EC2 instances](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Storage.html)
- [Amazon EBS — Create and attach a volume](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-creating-volume.html)
- [Amazon EBS — Volume types](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-volume-types.html)
- [Amazon EBS — General Purpose SSD volumes](https://docs.aws.amazon.com/ebs/latest/userguide/general-purpose.html)
- [Amazon EBS — Modify a volume](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-modify-volume.html)
- [Amazon EBS — Snapshots](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-snapshots.html)
- [Amazon EBS — Initialize restored volumes](https://docs.aws.amazon.com/ebs/latest/userguide/initalize-volume.html)
- [Amazon EBS — Encryption](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-encryption.html)
- [Amazon EC2 — Instance-store persistence](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-store-lifetime.html)
- [Amazon EFS — How EFS works](https://docs.aws.amazon.com/efs/latest/ug/how-it-works.html)
- [Amazon EFS — Mount targets](https://docs.aws.amazon.com/efs/latest/ug/accessing-fs.html)
- [Amazon EFS — Performance](https://docs.aws.amazon.com/efs/latest/ug/performance.html)
- [Amazon EFS — Encryption](https://docs.aws.amazon.com/efs/latest/ug/encryption.html)
- [Amazon EFS — Lifecycle management](https://docs.aws.amazon.com/efs/latest/ug/enable-lifecycle-management.html)
- [Amazon EFS — Backup](https://docs.aws.amazon.com/efs/latest/ug/awsbackup.html)
- [Chapter 97 — S3 Object Storage and Data Lifecycle](97-s3-object-storage-and-data-lifecycle.md)
