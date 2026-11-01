# Chapter 39 — File Identity, Hard Links, and Symbolic Links

A directory name can refer directly to a filesystem object or indirectly to another path. Hard links and symbolic links exploit that difference. They are useful for deduplication, stable releases, configuration, and compatibility, but they fail in different ways.

The central idea is:

> A hard link adds a name to an object; a symbolic link stores a path to resolve later.

## 1. Object identity is scoped to a filesystem

On Unix-like systems, the pair of filesystem device identity and inode number is a practical model for identifying a file object. An inode number alone is not globally unique. NTFS exposes file IDs within a volume; other filesystems have different schemes and guarantees.

Inspecting identity helps answer whether two paths currently refer to one object:

```bash
stat -- path-a path-b       # Linux
stat -x path-a path-b       # macOS
```

On Windows, `fsutil file queryfileid path` can query an NTFS file ID but may require appropriate permissions and filesystem support. PowerShell's ordinary `Get-Item` output does not provide a universal cross-filesystem identity test.

Identity can be reused after an object is deleted, so a raw ID without filesystem and time context is not a permanent business identifier.

## 2. A hard link is another directory entry

A regular file begins with at least one directory name. Creating a hard link adds another name for the same object:

```text
directory A / report.txt ─┐
                          ├→ one file object → one content stream
directory B / current.txt ┘
```

Changing content through either name changes the one shared object. Ownership and permissions belong to that object, not independently to each link. There is no privileged “original” name.

On Linux or macOS, in a disposable directory:

```bash
printf 'version one\n' > report.txt
ln report.txt current.txt
ls -li report.txt current.txt
```

On Windows with NTFS:

```powershell
New-Item -ItemType HardLink -Path current.txt -Target report.txt
fsutil hardlink list report.txt
```

Hard links normally cannot cross filesystem or volume boundaries because the destination directory must name an object managed by the same filesystem. Directories are usually restricted from ordinary hard-link creation to protect namespace structure.

## 3. Unlink removes a name, not necessarily the object

Removing one hard link removes that directory entry and decrements the link count. The object remains accessible through other names and, on Unix-like systems, through existing open references. Storage is reclaimable only when no names and no relevant open references retain it.

This makes `rm` better understood as an unlink operation for directory entries, not a guaranteed byte-erasure mechanism. Snapshots, backups, storage remanence, and other links can retain data. Secure data disposal is a separate storage-policy problem.

Renaming a file within one filesystem ordinarily changes namespace entries while retaining object identity. Replacing a path with a new object is different: processes holding the old object continue to see it, while new opens of the path reach the replacement.

## 4. A symbolic link contains a pathname

A symbolic link is its own filesystem object whose payload names another path. When an operation follows the link, the operating system resolves that stored path:

```text
current → releases/2026-10/app
```

On a Unix-like system:

```bash
ln -s releases/2026-10/app current
readlink current
```

If the stored target is relative, it is resolved relative to the directory containing the link, not the caller's current directory. Moving the link or its target can therefore change or break resolution. A missing target leaves a **dangling link**; the link object still exists even though normal target-following operations fail.

Symbolic links can cross filesystem boundaries because they store paths rather than direct filesystem-local object references. Their own metadata and the target's metadata are separate, though commands differ on whether they inspect the link or follow it.

## 5. Windows has several link-like mechanisms

NTFS supports hard links for files and symbolic links for files or directories. Directory junctions and volume mount points are implemented with reparse points and have different resolution and administration rules. Do not call every Windows redirection a symlink.

PowerShell supports `New-Item -ItemType SymbolicLink` on supported systems, but link creation rights and behavior depend on Windows version, Developer Mode, process privilege, filesystem, and target type. Inspect `LinkType` and `Target`, and use `fsutil reparsepoint query` only when lower-level reparse information is needed.

Deleting a link-like object must target the link itself, not recursively traverse and erase its destination. Confirm the tool's semantics before automating cleanup across junctions or reparse points.

## 6. Links are deployment tools with sharp boundaries

A release layout can prepare versioned directories and then change a `current` symlink to select one. That makes namespace switching fast, but only if applications reopen the path and all required content changes together. Processes with open handles remain attached to old objects.

Hard links can avoid duplicate file data in a local store, but modifying one name in place modifies every alias. Applications that write by creating a new temporary file and renaming it over one path can break the hard-link relationship for that path. Verify the actual update strategy.

Archives, source-control systems, copy tools, containers, and network filesystems may preserve, dereference, reject, or transform links. A portable artifact must state whether links are data to preserve or targets to materialize.

## 7. Safe questions before following a link

For security-sensitive or automated work, ask:

1. Is this component a link or reparse point?
2. Is its target absolute or relative?
3. Can an untrusted actor replace it between inspection and use?
4. Does resolution cross an intended root, mount, volume, or trust boundary?
5. Does the operation act on the link, the target, or both?

Checking a path and later opening it can create a time-of-check/time-of-use race. Security-sensitive APIs can resolve relative to already-open directories and restrict link traversal; exact facilities are platform-specific.

## Common Misconceptions

- “A hard link is a pointer file.” It is another direct name for the same object.
- “One hard-link name is the original.” The filesystem does not preserve that distinction.
- “A symlink contains the target data.” It contains a path to resolve.
- “Deleting a symlink deletes its target.” Ordinary unlink of the link removes the link object, not the target.

## Core Computer Science Concept

Links demonstrate **aliasing**. Multiple names can designate one mutable object, so reasoning from a name alone misses shared effects. Symbolic links add a second level of indirection whose result can change when namespace mappings change.

## Engineering Connections

- Package stores use hard links or content-addressed objects to reduce duplication.
- Release managers use symbolic links or junctions to select active versions.
- Backup tools must decide whether to preserve link topology or copy target bytes.
- Archive extraction and privileged cleanup must defend against link traversal attacks.

## From the Field

A cleanup task scans a writable directory, validates a path, then opens it later with elevated authority. An attacker swaps a component for a symbolic link between those operations, redirecting the write outside the intended tree. The durable fix uses platform APIs that bind resolution to trusted directory handles and reject unexpected links, rather than adding another pathname check.

## Engineering Review

### What problem does this solve?

It explains how multiple names can share one object and how one object can redirect resolution to another path.

### Why was it designed this way?

Hard links make object naming independent and efficient; symbolic links provide flexible cross-directory and cross-filesystem indirection.

### When should I use it?

Use links for deliberate aliasing, version selection, compatibility paths, or storage reuse when the lifecycle is understood.

### When should I avoid it?

Avoid links where tools cannot preserve their semantics, where aliasing surprises writers, or where untrusted replacement creates a security boundary.

### How does this make me a better engineer?

It teaches you to reason about identity, aliases, resolution time, and object lifetime separately.

### How does this reduce waste?

It prevents needless copies while avoiding outages and data loss caused by treating every path as an independent file.

## Handbook Principle #39

> Before changing a path, determine whether it names an object directly, aliases it, or redirects lookup elsewhere.

## Practical Observation

In a disposable directory, create one file, one hard link, and one symbolic link. Record identity, link count, and link target. Edit through the hard link, rename the original name, then inspect both remaining entries. Remove one name at a time and predict what remains before each operation. Do not use links into important directories.

## Looking Ahead

Identity and content are not the whole object. Chapter 40 inventories timestamps, attributes, permissions, and extended data that can change behavior even when file bytes match.

## References

- [Linux `inode(7)`](https://man7.org/linux/man-pages/man7/inode.7.html)
- [Linux `link(2)`](https://man7.org/linux/man-pages/man2/link.2.html)
- [Linux `symlink(7)`](https://man7.org/linux/man-pages/man7/symlink.7.html)
- [Microsoft: Hard Links and Junctions](https://learn.microsoft.com/en-us/windows/win32/fileio/hard-links-and-junctions)
