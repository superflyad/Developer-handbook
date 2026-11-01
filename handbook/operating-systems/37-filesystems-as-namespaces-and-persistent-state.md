# Chapter 37 — Filesystems as Namespaces and Persistent State

A path looks like a file's identity, but it is an instruction for finding an object through a namespace. The distinction matters whenever a file is renamed, deleted while open, mounted from another volume, or accessed through more than one name.

The central idea is:

> A filesystem connects names to objects and objects to persistent state; a pathname is a lookup request, not the object itself.

## 1. A filesystem solves several problems at once

Applications need more than raw blocks of bytes. They need names, directories, metadata, access rules, allocation, and a way to find data after restart. A filesystem supplies those mechanisms over some backing store or virtual source.

Its responsibilities commonly include:

- mapping path components through directories;
- representing regular files, directories, and special object types;
- storing content and metadata;
- allocating and reclaiming space;
- coordinating concurrent access and caching;
- defining recovery behavior after interruption.

Not every filesystem is backed by a local disk. Memory-backed, network, pseudo, and synthetic filesystems can expose the same path-oriented interface with different persistence and failure properties. “It has a path” does not prove “it survives reboot” or “it is local.”

## 2. Separate four layers

For ordinary file access, keep four concepts distinct:

```text
path string → directory lookup → filesystem object → stored content/metadata
```

- A **path string** is input interpreted relative to a root and often a current directory.
- A **directory entry** associates a component name with an object in that filesystem.
- A **filesystem object** has identity and metadata independent of one particular path.
- **Content and metadata** are the state applications ultimately read or change.

The exact implementation differs. Unix documentation often uses an inode number as a filesystem-local identifier. Windows APIs expose file IDs and file handles, while NTFS uses its own internal records. Do not turn “everything is an inode” into a cross-platform rule.

## 3. Path resolution is component-by-component

An absolute POSIX path such as `/srv/app/config.json` starts at the process's root and resolves `srv`, then `app`, then `config.json`. A relative path starts from the process's current working directory. On Windows, path prefixes can select a drive, UNC share, or another namespace; `C:\logs\today.txt` and `\\server\share\logs\today.txt` begin from different roots.

Resolution can cross symbolic links and mount boundaries. It can fail because a component does not exist, a non-directory appears before the end, access is denied on an intermediate directory, a link loop is detected, or the target filesystem becomes unavailable. The final filename is only one lookup step.

This is why logging only `config.json not found` often hides the useful evidence. Record the resolved or intended full path, execution identity, current directory, and relevant mount or share.

## 4. An open file is not just a pathname

An application asks the operating system to open a path. On success, it receives a process-local reference: commonly a file descriptor on Unix-like systems or a handle on Windows. Later reads and writes use that reference rather than repeating pathname resolution each time.

```text
process table entry → open-file state → filesystem object
```

The reference may retain current offset and access mode. Multiple descriptors or handles can refer to the same object while having different process-local state. Closing the reference releases the process's claim; it does not normally delete the named file.

On Unix-like systems, an open file can remain usable after its last directory name is unlinked; storage is reclaimed only after the final name and open reference disappear. Windows deletion and sharing behavior depends on how handles were opened, but the general lesson remains: a pathname and an active handle are different kinds of reference.

## 5. Directories are namespaces, not folders painted on a disk

A directory maps names to child objects. Renaming within one filesystem generally changes directory entries rather than copying all file bytes. Moving across filesystem boundaries usually requires copy-and-remove behavior because the destination cannot simply adopt the source filesystem's object identity.

Directory traversal is also an authorization operation. A process may know a complete path yet lack permission to search an intermediate directory. Conversely, permission on a file alone does not grant a route through every parent directory. Chapter 48 develops that model.

## 6. Roots depend on platform and process context

Linux and macOS normally present one rooted path tree, with other filesystems attached at mount points. A process may see a restricted or rearranged view because of containers, chroots, or mount namespaces.

Windows commonly presents drive-letter roots and UNC share roots, while volumes can also be mounted at directory paths. The NT object namespace and Win32 path rules add layers that a simple `C:` mental model misses. A drive letter is a name assigned to a volume, not the physical disk itself.

Case behavior, Unicode normalization, reserved names, maximum component lengths, and path-length handling vary by filesystem, API, and configuration. Portable applications must test the target environment rather than infer rules from the developer's workstation.

## 7. Observe without changing state

Use native tools to ask which object and filesystem a path reaches:

| Goal | Linux | macOS | Windows PowerShell |
| --- | --- | --- | --- |
| Show path metadata | `stat -- path` | `stat -x path` | `Get-Item -LiteralPath path` |
| Show current directory | `pwd -P` | `pwd -P` | `(Get-Location).Path` |
| Show filesystem for path | `findmnt -T path` | `df path` | `Get-Volume` and `Get-PSDrive -PSProvider FileSystem` |

Options and output vary by operating-system version. `df` answers allocation questions about a containing filesystem; it does not identify every layer of the backing storage. PowerShell providers can expose non-filesystem paths, so confirm `Provider.Name` before treating an item as a disk file.

## Common Misconceptions

- “The filename is stored in the file.” Names ordinarily live in directory namespace entries.
- “An absolute path identifies one global object forever.” Mounts, shares, namespaces, and replacement can change what it resolves to.
- “A file with a path is persistent.” Virtual and memory-backed filesystems may not survive restart.
- “Deleting a name instantly destroys all open access.” Object lifetime can extend beyond a directory entry.

## Core Computer Science Concept

A filesystem namespace is **indirection**. Human-oriented names resolve through mappings to objects, and processes receive capabilities that refer to the resolved objects. Indirection permits rename, mounting, sharing, and policy enforcement, but it also creates time-of-check/time-of-use risks when a name can be rebound between operations.

## Engineering Connections

- Atomic deployment patterns replace a directory entry after preparing new content.
- Containers deliberately alter the process-visible mount namespace.
- Log rotation can unlink or rename a file while a process still writes through an old descriptor.
- Security-sensitive code should avoid assuming that a previously inspected path still names the same object.

## From the Field

A service reports that it wrote a new log, but disk space keeps falling after an operator deletes the visible file. The process still holds the unlinked object open, so its bytes remain allocated without a pathname. Restarting blindly may release it, but first identify the handle and confirm the owning process and log policy.

## Engineering Review

### What problem does this solve?

It explains how operating systems turn path strings into persistent or virtual objects that applications can access.

### Why was it designed this way?

Separating names, objects, and open references permits flexible organization, efficient rename, shared access, and independent lifetime management.

### When should I use it?

Use this model whenever diagnosing path failures, missing files, unexpected mounts, open-file behavior, or cross-platform portability.

### When should I avoid it?

Avoid treating inode terminology, case rules, or root structure from one filesystem as a universal implementation.

### How does this make me a better engineer?

It makes path handling, lifecycle bugs, and storage boundaries explicit instead of collapsing them into “the file.”

### How does this reduce waste?

It directs investigation to the failing lookup or lifetime layer and prevents unnecessary copying, restarts, and permission changes.

## Handbook Principle #37

> Diagnose names, objects, open references, and stored state as separate layers.

## Practical Observation

Create a disposable file in a temporary directory. Inspect its full path and metadata, open it in a text editor, and rename it using the file manager. Observe whether the editor continues to access the already-open content and whether saving creates, replaces, or follows the renamed object. Do not use a shared or important file for this observation.

## Looking Ahead

Paths expose a namespace, but the namespace must be attached to storage or another provider. Chapter 38 traces a path down through mounts, filesystems, volumes, and devices.

## References

- [Linux `path_resolution(7)`](https://man7.org/linux/man-pages/man7/path_resolution.7.html)
- [Microsoft: Naming Files, Paths, and Namespaces](https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file)
- [The Open Group: Pathname Resolution](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap04.html#tag_04_16)
