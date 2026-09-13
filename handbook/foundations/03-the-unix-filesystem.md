# Chapter 3 — The Unix Filesystem

Chapter 2 introduced the operating system as a resource manager. The filesystem is one of its most important interfaces: it gives programs and people a stable way to name, organize, inspect, and share persistent data.

The central idea is:

> A filesystem separates human-readable names from stored objects and organizes those names into a navigable hierarchy.

## 1. The problem a filesystem solves

Storage hardware deals in blocks of data. Applications need something more useful:

- stable names,
- directories and paths,
- ownership and permissions,
- metadata,
- controlled sharing,
- a way to find data again after a process exits.

Without a filesystem, every program would need to know where its data lived on a device and how to avoid overwriting another program's data. A filesystem turns raw storage into a managed namespace.

Conceptually:

```text
storage blocks
      ↓
filesystem structures and rules
      ↓
named files and directories
      ↓
programs and people
```

The filesystem is therefore both a storage abstraction and a coordination mechanism.

## 2. Names are not the stored objects

A filename is a name in a directory. It is not the file's contents, and on common Unix filesystems it is not the file's underlying identity.

A useful simplified model is:

```text
directory entry
├── name: report.txt
└── reference to a filesystem object
    ├── data
    └── metadata
```

Many Unix filesystems represent the underlying object with an inode. Exact implementation details vary, so **directory entry**, **filesystem object**, and **inode** should not be treated as universal synonyms. The durable idea is that a human-readable path is resolved through names to an object managed by the filesystem.

This separation explains behaviors that otherwise seem surprising:

- an object can have more than one hard-link name,
- renaming a file need not rewrite its contents,
- removing one name may not immediately destroy the object,
- a process can keep using an already-open file after its visible name is removed.

Links and open-file behavior will be examined in more detail later. For now, distinguish the route used to find an object from the object itself.

## 3. Directories create a namespace

A directory maps names to filesystem objects. Those objects may be regular files, other directories, symbolic links, or other supported types.

Directories can contain directories, producing a hierarchy:

```text
/
├── Users
│   └── michael
│       └── Projects
├── Applications
├── Library
└── tmp
```

This hierarchy gives every reachable object a location within a namespace. The same filename can appear in different directories because the containing directory is part of the name's context.

```text
/Users/michael/Projects/app/config.json
/Users/michael/Projects/api/config.json
```

Both objects are named `config.json`, but their paths distinguish them.

## 4. The root of the tree

Unix-like systems expose one filesystem tree rooted at `/`.

```text
/
```

The root is the starting point for absolute paths. It is not the same thing as the `root` user, even though both use the word *root*:

- `/` is the root directory of the filesystem namespace.
- `root` is the traditional privileged Unix identity.

Keeping namespace and identity separate prevents an easy conceptual mistake.

## 5. Absolute and relative paths

An **absolute path** starts at the root directory:

```text
/Users/michael/Projects/handbook/README.md
```

A **relative path** starts at a process's current working directory:

```text
handbook/README.md
```

If the working directory is `/Users/michael/Projects`, the relative path above resolves to:

```text
/Users/michael/Projects/handbook/README.md
```

Relative paths are convenient because a project can move as a unit. Absolute paths are explicit but often bind a workflow to one machine or directory layout.

The correct choice depends on the required stability:

- use project-relative paths for files that move with a repository,
- use absolute paths when the exact system location is part of the contract,
- do not assume a process starts in the directory you expect.

## 6. The current working directory belongs to a process

The current working directory is process state. A relative path has no complete meaning until it is combined with that state.

```text
process working directory + relative path = resolved location
```

This is why the same command can succeed in one context and fail in another:

- a terminal shell starts in one directory,
- an IDE launches a tool from another,
- a CI job checks out code into a generated workspace,
- a service manager assigns its own working directory,
- a container image defines a working directory.

When software reports that a relative path does not exist, inspect the process's working directory before changing the path or copying files randomly.

## 7. Special path components

Unix paths use `/` as the component separator. Two components have special meanings:

```text
.   current directory
..  parent directory
```

For example:

```text
./scripts/build.sh
../shared/config.json
```

The first begins in the current directory. The second begins in its parent.

Shells also commonly expand `~` to a user's home directory:

```text
~/Projects
```

The tilde is shell syntax, not a literal directory named `~` and not a feature implemented by every program. This distinction matters when a path passes through configuration files, APIs, or tools that do not perform shell expansion.

## 8. Filenames and extensions

Unix filenames do not require extensions. A name such as `README`, `Makefile`, or `docker-entrypoint` is valid without one.

Extensions such as `.md`, `.py`, and `.json` are conventions that help people and tools infer purpose. They do not define the underlying object type or guarantee its contents.

An executable program is not executable merely because its name ends in a particular suffix. Its format, permissions, interpreter declaration, and launch context all participate.

Likewise, changing `notes.txt` to `notes.jpg` changes the name, not the bytes stored in the file.

## 9. Hidden names

Unix tools traditionally treat names beginning with `.` as hidden from ordinary directory listings:

```text
.git
.zshrc
.env
```

The leading dot is a naming convention interpreted by tools. It is not a security boundary.

A hidden file can still be opened by any process with a path and sufficient permission. Secrets do not become safe merely because their filenames begin with a dot.

## 10. Filesystem object types

The namespace can expose more than regular files and directories.

Common Unix object types include:

- **regular files** — stored data such as source code, images, and executables,
- **directories** — mappings from names to objects,
- **symbolic links** — objects containing a path to another location,
- **device nodes** — interfaces to certain devices,
- **named pipes** — filesystem-visible communication channels,
- **sockets** — endpoints that processes can use for communication.

This supports the broader Unix preference for a small set of familiar interfaces. It does not mean that every resource is literally a regular file.

## 11. Metadata describes an object

Filesystems store metadata in addition to file contents. Depending on the filesystem and operating system, metadata may include:

- object type,
- size,
- owning user and group,
- permissions or access-control information,
- timestamps,
- link count,
- filesystem-specific flags and attributes.

Metadata answers questions about an object without requiring an application to interpret its contents.

Some details are easy to oversimplify. For example, systems may track several timestamps with different meanings, and the meaning or availability of a creation time varies by filesystem. Use the platform's actual metadata rather than assuming every Unix-like system records identical fields.

## 12. Path resolution

When a process opens a path, the operating system resolves it component by component.

For this path:

```text
/Users/michael/Projects/app/config.json
```

a simplified resolution is:

```text
start at /
  ↓ find Users
  ↓ find michael
  ↓ find Projects
  ↓ find app
  ↓ find config.json
  ↓ return the resolved object or an error
```

Each directory in the route must exist, and the process must have the authority required to traverse it. A failure near the end can be caused by an earlier path component.

Symbolic links can redirect resolution to another path. Mount points can attach another filesystem beneath a directory. The path remains a single-looking string even when resolution crosses those boundaries.

## 13. Mounting creates one visible tree

A Unix-like system can attach a filesystem at a directory called a **mount point**.

```text
existing tree
└── Volumes
    └── ExternalDrive  ← another filesystem mounted here
```

Applications can then access the mounted storage through ordinary paths. The namespace hides much of the device-level complexity.

The mounted filesystem may have different characteristics from its parent, including:

- capacity,
- performance,
- case sensitivity,
- permission behavior,
- supported metadata,
- reliability and availability.

A path crossing a mount point looks continuous, but its storage and operational boundary may have changed.

## 14. Case sensitivity is a filesystem property

Unix paths are commonly case-sensitive, so these may identify different names:

```text
README.md
readme.md
```

However, default macOS volumes are often case-insensitive while preserving the case used when a name was created. Linux filesystems are commonly case-sensitive. Windows filesystems are commonly case-insensitive by default, though modern configurations can introduce exceptions.

This difference causes real portability failures. Code can work on a developer's Mac or Windows machine and fail in a Linux CI runner because an import or path uses the wrong capitalization.

Do not infer path behavior from the operating-system family alone. The mounted filesystem and its configuration own the behavior.

## 15. Safe inspection on macOS and Linux

The following commands assume a POSIX-style shell such as `zsh` or `bash`.

Show the shell's current working directory:

```bash
pwd
```

List directory entries, including dot-prefixed names:

```bash
ls -la
```

Ask a tool to inspect a file's apparent content type:

```bash
file README.md
```

Inspect filesystem metadata:

```bash
stat README.md
```

Find Markdown files beneath the current directory:

```bash
find . -type f -name '*.md'
```

The exact `stat` output differs between macOS and Linux. That is useful evidence that the concept is portable even when the presentation and supported metadata differ.

## 16. Quote paths deliberately

Spaces and shell metacharacters can change how a shell turns text into arguments.

Given a file named:

```text
Engineering Notes.md
```

this preserves the path as one argument:

```bash
file "Engineering Notes.md"
```

Without quoting, the shell may pass two arguments. The filesystem did not split the name; the shell did while parsing the command line.

This is a recurring debugging rule: determine whether a failure belongs to shell parsing or filesystem resolution.

## 17. Removing a name and reclaiming storage are different events

Deleting a directory entry removes a name from the namespace. Reclaiming the underlying storage can occur later.

On common Unix filesystems, an object can remain reachable through another hard link or remain open inside a process. Its data can continue consuming space until the remaining references are gone.

This explains a production symptom in which a large log is deleted but disk space does not immediately return. A running service may still hold the object open. The correct investigation crosses two layers:

1. inspect the filesystem namespace and free space,
2. identify processes holding open resources.

Chapter 4 develops the process side of this model.

## 18. Common failure modes

### “No such file or directory”

The path may be misspelled, relative to an unexpected working directory, incorrectly capitalized, or routed through a broken symbolic link.

### “Permission denied”

The object may exist, but the process may lack permission to traverse a parent directory, read the object, write it, or execute it. Chapter 7 develops this authorization model.

### “Disk full”

The target filesystem may be out of data space or metadata capacity. Free space elsewhere in the namespace does not help if it belongs to a different mounted filesystem.

### “It exists on my machine”

The path may depend on one user's home directory, an untracked file, a case-insensitive filesystem, or a mount that does not exist in CI or production.

### “Changing the extension converted the file”

A rename changed the path, not the data representation.

## 19. A filesystem debugging model

When a path-related operation fails, ask:

1. Which process is making the request?
2. What is its current working directory?
3. Is the path absolute or relative?
4. How does each path component resolve?
5. Are symbolic links or mount points involved?
6. Does capitalization match on this filesystem?
7. What object type and metadata are present?
8. Does the process have permission for the requested operation?
9. Is the target filesystem available and healthy?

This sequence replaces path guessing with evidence.

## 20. Platform comparison

| Concept | Windows | macOS | Linux |
| --- | --- | --- | --- |
| Common namespace roots | Drive letters and mounted locations | One tree rooted at `/` | One tree rooted at `/` |
| Common path separator | `\` | `/` | `/` |
| Typical default case behavior | Case-insensitive, case-preserving | Often case-insensitive, case-preserving | Commonly case-sensitive |
| Common user home | `C:\Users\name` | `/Users/name` | `/home/name` |
| Common security model | NTFS ACLs and access tokens | POSIX permissions, ACLs, and platform controls | POSIX permissions, ACLs, capabilities, and policy controls |

These are common defaults, not universal laws. Filesystems can be mounted across platforms, and configuration can change their behavior.

The transferable model is the same: paths navigate a namespace, directories map names, objects carry data and metadata, and processes request operations through the operating system.

## Core Computer Science Concept

The filesystem is a **namespace**: a structured system for mapping human-meaningful names to managed objects.

The pattern appears elsewhere:

```text
DNS name        → network address
variable name   → value or storage location
URL path        → application resource
database key    → record
filesystem path → filesystem object
```

Names make systems usable, but names and objects have different lifecycles. Strong engineers learn to ask whether a problem concerns naming, resolution, identity, metadata, or stored data.

## Engineering Connections

The filesystem model appears throughout professional engineering:

- Git tracks paths and content while maintaining its own object model.
- Build systems map source paths to generated artifacts.
- Containers assemble filesystem layers and define a working directory.
- CI runners create temporary workspaces and checkouts.
- Applications locate configuration, templates, certificates, and static assets by path.
- Databases and logs consume storage on specific mounted filesystems.
- Deployments use permissions and atomic name changes to control visibility.
- Cloud volumes and network filesystems appear beneath ordinary paths.

Many application failures are filesystem-model failures wearing a framework-specific error message.

## From the Field

An application works in an interactive terminal but fails as a service:

```text
FileNotFoundError: config/settings.json
```

The file exists inside the repository. The service, however, starts with `/` as its working directory.

The application therefore asks for:

```text
/config/settings.json
```

rather than the repository's configuration file.

Copying the file into random locations would hide the model error. A better fix is to define the service's working directory or resolve configuration relative to a deliberate, stable base path.

## Engineering Review

### What problem does this solve?

A filesystem turns raw storage into a named, hierarchical, shareable collection of objects with data and metadata.

### Why was it designed this way?

Separating names, hierarchy, metadata, and storage lets programs locate and manage data without controlling physical device blocks directly.

### When should I use it?

Use this model whenever software reads configuration, writes artifacts, resolves paths, manages storage, crosses mount points, or reports file-related failures.

### When should I avoid it?

Do not treat every resource as a regular file or assume every filesystem has Unix semantics. Databases, object stores, remote APIs, virtual filesystems, and Windows paths expose different guarantees.

### How does this make me a better engineer?

It separates path parsing, name resolution, object identity, metadata, permissions, storage, and process state into distinct questions.

### How does this reduce waste?

It prevents random path edits and duplicate files by directing investigation toward the working directory, namespace, mount, metadata, or permission boundary that actually owns the failure.

## Handbook Principle #3

> A path is a route through a namespace, not the data itself; resolve the route, inspect the object, and identify the process using it.

## Practical Observation

From the handbook repository on macOS or Linux, run:

```bash
pwd
ls -la
file README.md
stat README.md
find . -type f -name '*.md'
```

For each command, identify whether its result describes:

- the process's working directory,
- directory entries,
- interpreted file contents,
- filesystem metadata,
- or paths discovered through the namespace.

Then consider how the result might differ on another filesystem without changing the underlying concept.

## Looking Ahead

The filesystem explains how programs and data are named and found. Chapter 4 adds motion: how stored program files become running processes with memory, identity, open resources, and a lifecycle managed by the kernel.
