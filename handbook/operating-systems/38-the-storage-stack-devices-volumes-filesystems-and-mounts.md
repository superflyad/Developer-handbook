# Chapter 38 — The Storage Stack: Devices, Volumes, Filesystems, and Mounts

“The disk is full” compresses several layers into one sentence. A path belongs to a mounted filesystem; that filesystem may live on a logical volume, partition, disk image, network service, or physical device. Accurate diagnosis moves through those layers rather than guessing from a drive letter.

The central idea is:

> Trace storage from the path downward: mount, filesystem, volume, then backing device or service.

## 1. The layers are related, not interchangeable

A common local-storage arrangement is:

```text
application path
→ mounted filesystem namespace
→ filesystem format and allocation
→ volume or partition
→ block device or virtual device
→ physical or remote storage
```

Some systems add encryption, logical-volume management, software RAID, snapshots, or disk images between these layers. A network filesystem replaces much of the local lower stack with a client protocol and remote server. A memory filesystem has no persistent block device at all.

A **disk** is a physical or virtual device. A **partition** describes a region of a disk. A **volume** is a logical storage unit presented for formatting or mounting and may span or share underlying devices. A **filesystem** organizes objects and space within a storage source. A **mount** attaches that filesystem to a namespace location. Platform tools sometimes use these words differently, so read the tool's definition.

## 2. Formatting and mounting are different operations

Formatting creates filesystem structures on a target storage unit and can destroy existing data. Mounting makes an existing filesystem accessible at a namespace location. These operations have radically different risk.

This chapter uses no formatting commands. Observe first; use graphical storage tools or administrative commands only with a verified backup, exact device identity, and an approved change plan. Device names can change across boots or attachment order, making a remembered label unsafe as the sole identifier.

## 3. Unix-like systems build one visible tree

Linux and macOS attach filesystems at directories. The path `/home` or `/Volumes/Archive` can be part of the root filesystem or the root of another mounted filesystem. Traversing the directory crosses that boundary without changing path syntax.

On Linux, read-only inspection can begin with:

```bash
findmnt -T /path/to/inspect
df -hT /path/to/inspect
lsblk -o NAME,TYPE,FSTYPE,SIZE,MOUNTPOINTS
```

`findmnt -T` maps a path to a mount; `df` reports allocation for the containing mounted filesystem; `lsblk` describes block-device relationships. Their sources may be virtual, encrypted, or network-backed, so do not assume the first device-like name is physical hardware.

On macOS, useful read-only views include:

```bash
df -h /path/to/inspect
mount
diskutil info /path/to/inspect
diskutil list
```

Modern APFS commonly groups volumes inside a container with shared free space. A visible APFS volume is therefore not necessarily a fixed partition-sized slice. macOS system and data volumes can also be presented as one coherent user-visible hierarchy.

## 4. Windows separates volumes, letters, and physical disks

Windows volumes may receive drive letters such as `C:`, be mounted into NTFS directories, or be addressed through volume GUID paths. A physical disk can contain several partitions and volumes; a volume can exist without a drive letter. UNC paths such as `\\server\share` name network shares, not local volumes.

PowerShell can inspect the relationships without changing them:

```powershell
Get-Volume
Get-Partition
Get-Disk
Get-PSDrive -PSProvider FileSystem
```

Correlate stable identifiers, sizes, filesystem types, and partition-to-disk relationships. `Get-PSDrive` also reports PowerShell's filesystem views; it is not a substitute for the storage cmdlets. A drive letter is a namespace assignment that can be changed, not an intrinsic property of a device.

## 5. A mount point can hide prior directory contents

On Unix-like systems, mounting a filesystem over a nonempty directory ordinarily makes the directory's previous contents inaccessible through that path until unmount. The underlying files were not necessarily deleted; the new mounted root obscures them. Similar namespace indirection exists with Windows volume mount points.

This can produce incidents where data appears missing after a mount, or a service writes to the underlying root filesystem when an expected mount failed. After the mount later returns, those misplaced files become hidden and root space remains consumed. Check that the expected filesystem is mounted *before* trusting a path's contents.

## 6. Mount state carries policy

Mounts have options that affect behavior: read-only state, executable-file handling, device interpretation, caching, access checks, and failure semantics. Names and support vary by platform and filesystem. Do not copy a mount-option recipe between systems without reading the relevant implementation documentation.

Network and removable storage add availability boundaries. An open operation can block or fail if a server or device disappears. A successful mount at startup may not remain healthy forever. Applications should treat external storage as a dependency with observable failure, not an ordinary local directory with infinite availability.

## 7. Safe investigation order

When a path reports full, read-only, missing, or unavailable:

1. Record the exact path, host, time, and failing operation.
2. Identify the mount containing that path.
3. Confirm the filesystem type, source, options, and current availability.
4. Map the source through volume, partition, and device layers where applicable.
5. Check allocation, quotas, read-only state, and system logs at the relevant layer.
6. Change configuration only after identifying ownership and a rollback path.

Do not unmount a production filesystem merely to “see if it helps.” Open references, current working directories, and active services can depend on it. An unmount is an operational change requiring impact analysis.

## Common Misconceptions

- “`C:` is the first physical disk.” It is a drive-letter assignment to a volume.
- “Every mounted filesystem is on a partition.” It may be networked, memory-backed, synthetic, or layered.
- “Mounting formats the device.” Formatting creates a filesystem; mounting attaches one.
- “A directory path always reaches the same storage.” Mount state can change what the path resolves into.

## Core Computer Science Concept

The storage stack is **layered virtualization**. Each layer exports an interface while hiding implementation below it. That composition enables encryption, snapshots, shared volumes, and network storage, but a failure reported at the path layer may originate anywhere down the stack.

## Engineering Connections

- Database durability depends on filesystem and device behavior below the application path.
- Containers add mount namespaces and layered filesystems without changing most application path APIs.
- Kubernetes volumes and cloud disks are attachments in a larger control plane, not magical directories.
- Monitoring should label both user-facing mount paths and stable backing identifiers.

## From the Field

A service expects `/data` to be a separate volume. After a boot-time mount failure, it starts anyway and writes into the root filesystem's ordinary `/data` directory. The volume later mounts over that directory, hiding the misplaced files while root remains full. The durable fix validates the mount dependency before service start and investigates the hidden underlying data during an approved outage.

## Engineering Review

### What problem does this solve?

It explains how a pathname reaches a filesystem and how that filesystem relates to logical and physical storage.

### Why was it designed this way?

Layering lets operating systems compose hardware, logical allocation, filesystem semantics, and user-facing namespaces independently.

### When should I use it?

Use the model for capacity, mount, removable-media, network-storage, and device-mapping investigations.

### When should I avoid it?

Avoid assuming every platform uses identical volume terminology or running formatting and mount changes as diagnostic probes.

### How does this make me a better engineer?

It teaches you to locate the failed layer and recognize storage as an external dependency with explicit identity.

### How does this reduce waste?

It prevents repairs aimed at the wrong device, volume, or filesystem and makes capacity evidence comparable.

## Handbook Principle #38

> Never diagnose storage from a path label alone; map the namespace to its actual backing layers.

## Practical Observation

Choose a read-only path on your workstation and use the commands for your platform to record its mount or volume, filesystem type, capacity, and backing device or remote source. Draw the layer stack. Do not create, resize, format, mount, or unmount anything for this observation.

## Looking Ahead

The storage stack identifies where a filesystem lives. Chapter 39 examines how several pathnames can refer to one object—or refer indirectly to another pathname.

## References

- [Linux `findmnt(8)`](https://man7.org/linux/man-pages/man8/findmnt.8.html)
- [Microsoft: Windows Storage Management](https://learn.microsoft.com/en-us/windows-server/storage/storage)
- [Apple: Intro to Disk Utility](https://support.apple.com/guide/disk-utility/intro-to-disk-utility-dskutl1029/mac)
