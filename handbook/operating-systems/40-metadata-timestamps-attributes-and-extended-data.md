# Chapter 40 — Metadata, Timestamps, Attributes, and Extended Data

Two files can contain identical visible bytes yet behave differently because their metadata differs. Ownership, access policy, timestamps, flags, link state, extended attributes, and alternate streams can affect execution, synchronization, backup, and security.

The central idea is:

> File content answers “what bytes?”; metadata answers “what object, governed and interpreted how?”

## 1. Inventory the full object state

Common metadata includes:

- object type, logical size, and allocated size;
- filesystem-local identity and hard-link count;
- owner, group, mode, and access-control information;
- modification, access, status-change, and sometimes birth or creation times;
- filesystem flags and platform attributes;
- extended attributes, alternate streams, and reparse data;
- labels or policy data used by security frameworks.

Not every filesystem represents every field. APIs may synthesize values, suppress expensive updates, round timestamps, or translate metadata across a network. Treat missing fields as unsupported or unobserved until proven otherwise.

## 2. File type is metadata

Regular files, directories, symbolic links, devices, sockets, and named pipes can all occupy pathname entries on Unix-like systems. Opening each with the same assumptions is unsafe. Windows similarly distinguishes directories, reparse points, devices, and other object behavior through APIs and attributes.

Inspect type before recursive automation. A directory-like entry may redirect into another volume or tree. A special file may represent a kernel or process interface rather than stored bytes. Tools that say “file” sometimes mean any filesystem object, while users often mean only a regular data file.

## 3. Timestamps describe events, not ground truth

On common Unix-like filesystems:

- **mtime** reflects content modification;
- **ctime** reflects inode-status change, not creation time;
- **atime** reflects access, subject to mount and update policy;
- **birth time** may exist but is not universally available.

Windows filesystems commonly expose creation, last-access, and last-write times, but resolution and update behavior vary by filesystem. Network copies, archive extraction, synchronization software, and explicit timestamp-setting calls can preserve or rewrite values.

Do not use mtime alone as proof that content was authored at that time, or ctime as a creation date. Clock skew, delayed updates, timezone presentation, timestamp precision, and deliberate modification all limit forensic conclusions. Store application events in an auditable domain record when their time matters.

## 4. Attributes and flags modify behavior

Windows file attributes include concepts such as read-only, hidden, system, archive, compressed, encrypted, sparse, and reparse point. Their semantics depend on filesystem and API; the read-only attribute is not the same authorization mechanism as an NTFS DACL.

Linux filesystems may support flags such as immutable or append-only, and macOS exposes BSD flags in addition to other metadata. Changing restrictive flags can require elevated authority. A failed write may therefore be caused by policy beyond ordinary mode bits.

Observe first:

```bash
ls -ldO path       # macOS flags and basic listing
lsattr -- path     # Linux filesystem attributes, when supported
```

```powershell
Get-Item -LiteralPath path -Force | Select-Object FullName, Attributes, Length, CreationTimeUtc, LastWriteTimeUtc
```

These commands expose different layers and are not equivalent schemas.

## 5. Extended attributes carry namespaced data

Extended attributes associate named byte values with an object outside its primary data. Linux, macOS, and other Unix-like systems expose different namespaces and tools. They can hold security labels, provenance, quarantine information, application metadata, or user-defined values.

Read-only inspection examples are:

```bash
getfattr -d -- path     # Linux, when the attr tools are installed
xattr -l path           # macOS
```

A copy tool may omit extended attributes unless configured to preserve them. A destination filesystem may not support the same namespaces. Blindly deleting unfamiliar attributes can disable security controls or remove provenance, so identify the owner and purpose first.

## 6. NTFS alternate data streams are additional content

NTFS can associate multiple named data streams with one file. The default unnamed stream is what ordinary tools usually show, while named streams can hold additional bytes. PowerShell can enumerate supported streams:

```powershell
Get-Item -LiteralPath path -Stream *
```

Copying to a filesystem without stream support can lose named streams. Archive and transfer tools vary. Stream presence is not inherently malicious—Windows uses related metadata mechanisms for legitimate features—but hidden or unexpected data belongs in the security model.

Extended attributes and alternate data streams are not identical implementations, even though both attach data beyond the primary visible content.

## 7. Preservation is a declared requirement

“Copy the file” can mean several things:

1. reproduce only primary bytes;
2. preserve names and directory structure;
3. preserve timestamps and ownership;
4. preserve ACLs, flags, links, extended data, and sparse layout;
5. reproduce an application-consistent point in time.

No generic copy command guarantees all five across every source and destination. Before migration or backup, define required metadata, confirm tool support, run a representative test, and verify the restored result—not merely the copy command's exit status.

Checksums of primary content do not validate ACLs, streams, or attributes. Conversely, metadata differences do not necessarily mean primary bytes changed. Select evidence for the property you need to prove.

## Common Misconceptions

- “ctime is creation time.” On Unix it conventionally means status-change time.
- “Read-only means access is denied.” A file attribute and an authorization decision are different mechanisms.
- “A matching checksum proves the files are equivalent.” It proves only the checked byte stream matches under that algorithm.
- “Copying a file preserves everything.” Preservation depends on source, destination, tool, options, and privileges.

## Core Computer Science Concept

Metadata is a **schema around data**. Compatibility requires more than transporting values; both ends must agree on field meaning, precision, ownership, and unsupported cases. Cross-filesystem copying is therefore a schema-translation problem, not only byte transfer.

## Engineering Connections

- Build tools use timestamps for incremental work and can fail under skew or coarse precision.
- Security labels and quarantine metadata can control whether downloaded code executes.
- Backup validation must include policy metadata required for a safe restore.
- Deployment tools should distinguish content identity from ownership and runtime access.

## From the Field

A migration verifies every file with a content checksum, then the application fails because executable bits, ACLs, and extended security labels were not preserved. The byte-transfer validation succeeded; the object-state migration did not. The corrected plan defines the required metadata contract and performs a restore rehearsal on the target filesystem.

## Engineering Review

### What problem does this solve?

It identifies the non-content state that controls how filesystem objects are interpreted, accessed, synchronized, and restored.

### Why was it designed this way?

Separating content from metadata allows the filesystem and operating system to manage identity, policy, lifecycle, and optimization independently.

### When should I use it?

Use this model for migrations, backups, build caching, permission diagnosis, file comparison, and security review.

### When should I avoid it?

Avoid inferring business events from timestamps alone or changing unfamiliar attributes merely to make an operation succeed.

### How does this make me a better engineer?

It makes you define what “same file” and “successful copy” mean for the system at hand.

### How does this reduce waste?

It catches incomplete migrations and false comparisons before they become recovery or production incidents.

## Handbook Principle #40

> Define and verify the metadata contract whenever file behavior matters beyond its visible bytes.

## Practical Observation

Create a disposable file, record its content checksum and available metadata, then copy it to another temporary location using the platform's ordinary copy command. Compare timestamps, attributes, ownership, and extended data as well as bytes. Explain each preserved or changed field without altering system files.

## Looking Ahead

Metadata reports logical size and timestamps, but neither proves how much storage is allocated or when writes became durable. Chapter 41 examines space, caching, and persistence boundaries.

## References

- [Linux `inode(7)`](https://man7.org/linux/man-pages/man7/inode.7.html)
- [Linux `xattr(7)`](https://man7.org/linux/man-pages/man7/xattr.7.html)
- [Microsoft: File Attribute Constants](https://learn.microsoft.com/en-us/windows/win32/fileio/file-attribute-constants)
- [Microsoft: File Streams](https://learn.microsoft.com/en-us/windows/win32/fileio/file-streams)
