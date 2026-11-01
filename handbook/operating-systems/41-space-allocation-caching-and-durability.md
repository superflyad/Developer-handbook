# Chapter 41 — Space, Allocation, Caching, and Durability

A successful write can be visible to the application before it is durable on storage. A one-terabyte logical file can consume almost no blocks, while a deleted file can continue consuming space. Storage measurements answer different questions and must not be treated as interchangeable.

The central idea is:

> Distinguish logical bytes, allocated space, cached state, and durable state before drawing conclusions about storage.

## 1. Logical size is not allocated size

A file's logical size describes the byte range visible to readers. Allocation describes storage resources reserved for its data and metadata. Compression, sparse regions, deduplication, copy-on-write, block size, and metadata overhead can make these values differ.

On Linux or macOS, compare a disposable file's apparent size with allocated usage:

```bash
ls -l path
du -h path
```

Exact units and options vary. GNU `du --apparent-size` makes the logical comparison explicit. On Windows, `Get-Item path` reports logical length, while allocation queries require filesystem-aware APIs or tools. File Explorer's “Size” and “Size on disk” are related but can still be affected by compression, links, and allocation-unit behavior.

Never add the reported size of every hard link as if each owns separate data. Conversely, small files can consume more allocation than their content length because storage is assigned in units and directories require metadata.

## 2. Sparse files represent holes efficiently

A sparse file has logical ranges that read as zeros without requiring equivalent allocated blocks. Databases, virtual disks, and scientific applications use sparseness to represent large address spaces efficiently.

Copying a sparse file with a tool or destination that does not preserve holes can expand it to its full logical size. Compression is not the same mechanism: sparse holes represent unwritten zero ranges, while compression encodes content more compactly. Confirm both tool behavior and destination support during migration.

Do not create huge sparse-file exercises on shared storage. A later operation that fills the holes can consume the logical capacity and trigger an outage.

## 3. Filesystem free space is not a directory property

Free-space tools usually report allocation for the containing filesystem or volume, not for an individual directory. Quotas, reserved blocks, snapshots, thin provisioning, container limits, cloud allocation, and user-specific policy can make “available” differ by caller and layer.

Useful observations include:

```bash
df -h /path
du -sh /path
```

`df` asks the filesystem about overall allocation; `du` walks reachable directory entries and sums what it sees. They can disagree legitimately. On Windows, combine `Get-Volume`, exact path-to-volume mapping, and quota or storage-system evidence rather than relying on a directory traversal alone.

## 4. Deleted-open files explain invisible usage

On Unix-like systems, unlinking the last pathname does not reclaim an object while a process still holds it open. `du` cannot find the now-unreachable name, but `df` still reflects allocated blocks. Linux tools such as `lsof +L1` can identify open files with a link count below one when permissions allow.

Do not kill the first process shown. Identify its owner, service role, data importance, and supported log-reopen or restart procedure. Copying `/proc/<pid>/fd/...` or truncating through a descriptor can have application-specific consequences and is not a generic repair.

Snapshots can create another mismatch: deleting current files may not release blocks still referenced by a snapshot. Thin-provisioned lower layers can also report capacity independently of the guest filesystem.

## 5. Write visibility is not durability

Applications typically write into operating-system caches. Other reads can observe new data while the operating system still intends to flush it later. A process exit, kernel crash, power loss, device cache, or remote server failure creates different durability boundaries.

On POSIX systems, `fsync` requests synchronization for a file descriptor; durable creation or rename may also require directory metadata synchronization. Windows exposes `FlushFileBuffers`, and application APIs may offer higher-level durability contracts. Exact guarantees depend on filesystem, mount mode, device, driver, and remote protocol.

Frequent forced flushes can be expensive. Too few can violate data-loss requirements. Choose a durability contract from product requirements, then use a well-tested database or storage library rather than improvising transactional persistence from ordinary writes.

## 6. Atomic replace and durable commit are separate

A common configuration update pattern is:

1. create a temporary file in the destination directory;
2. write and validate complete content;
3. flush as required by the durability contract;
4. atomically rename or replace the destination;
5. synchronize containing metadata when required.

An atomic rename can prevent readers from seeing half-written content, but it does not by itself guarantee the new directory entry survives sudden power loss. Cross-filesystem moves cannot use the same single-filesystem rename guarantee. Windows sharing modes and replacement APIs add platform-specific constraints.

Use established libraries that document crash behavior. Test interruption cases on the actual storage stack when data loss matters.

## 7. Capacity and durability are operational contracts

Capacity monitoring should distinguish filesystem allocation, quota, snapshot retention, thin-pool capacity, and physical backing. Alert before hard exhaustion and reserve room for recovery operations, logs, and metadata growth.

Durability should state what can be lost: the last log line, one request, a transaction, or nothing after acknowledgement. Backups protect against different events than flushes. Replication protects against some device failures but can copy corruption. A durable local write is not a disaster-recovery plan.

## Common Misconceptions

- “File size equals disk usage.” Sparse, compressed, linked, and block-rounded files disprove that.
- “`du` and `df` should match.” They measure reachable objects and filesystem allocation differently.
- “A successful `write` means power-loss safety.” It may only mean the cache accepted bytes.
- “Atomic rename makes the whole update durable.” Namespace atomicity and persistence are separate guarantees.

## Core Computer Science Concept

Storage exposes **consistency and durability boundaries**. Caches improve throughput by acknowledging work before slower layers finish. Correct systems define which ordering and persistence guarantees they require, then introduce synchronization only at those boundaries.

## Engineering Connections

- Databases use journals or write-ahead logs to recover from interrupted multi-step updates.
- Container and cloud capacity can fail at the guest, thin-pool, volume, or account layer.
- Log rotation must coordinate pathname replacement with long-lived open descriptors.
- Backup testing must verify restored data after caches, snapshots, and metadata are considered.

## From the Field

A host reports 95 percent filesystem usage, but `du` accounts for only half. An operator deletes more visible logs without effect. Investigation finds a large rotated log still held open and several snapshots retaining older blocks. The correct response coordinates service log reopening and snapshot retention rather than repeatedly deleting reachable files.

## Engineering Review

### What problem does this solve?

It explains apparent capacity contradictions and the gap between acknowledged writes and durable storage.

### Why was it designed this way?

Allocation techniques save space, while caching and batching improve performance; both trade simple accounting for efficiency.

### When should I use it?

Use this model for disk-full incidents, file migration, database persistence, backup design, and crash-safe updates.

### When should I avoid it?

Avoid forcing flushes or deleting files based on one metric without understanding application and storage-layer contracts.

### How does this make me a better engineer?

It makes you state which bytes are allocated, visible, ordered, and durable at each boundary.

### How does this reduce waste?

It prevents capacity work aimed at invisible or wrong layers and avoids fragile homegrown persistence schemes.

## Handbook Principle #41

> Measure the storage property you actually need: size, allocation, availability, visibility, or durability.

## Practical Observation

In a disposable directory, create a small text file and record its logical size and allocated usage with native tools. Copy it and compare again. If your platform provides a safe built-in way to inspect sparse files, inspect an existing noncritical example rather than allocating a large one. Do not fill storage or force system-wide cache operations.

## Looking Ahead

Files persist program code and data; processes turn that code into running state. Chapter 42 follows process creation, inherited context, execution, and exit.

## References

- [Linux `fsync(2)`](https://man7.org/linux/man-pages/man2/fsync.2.html)
- [Linux `lseek(2)`: Seeking File Data and Holes](https://man7.org/linux/man-pages/man2/lseek.2.html)
- [Microsoft: `FlushFileBuffers`](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-flushfilebuffers)
- [SQLite: Atomic Commit](https://www.sqlite.org/atomiccommit.html)
