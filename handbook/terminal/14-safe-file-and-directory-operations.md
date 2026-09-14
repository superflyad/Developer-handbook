# Chapter 14 — Safe File and Directory Operations

Navigation establishes context. File operations change persistent names and content, so their scope, overwrite behavior, and recovery path must be understood before execution.

The central idea is:

> Treat every filesystem mutation as a state transition: inspect the starting state, constrain the target, perform one deliberate change, and verify the result.

## 1. Names and content are different concerns

A directory maps names to filesystem objects. Common commands change either the mapping, the object contents, or both.

```text
mkdir  creates a directory object and a name
cp     creates or replaces destination content
mv     changes a name or relocates content
rm     removes a name from a directory
```

Thinking only in terms of visible files hides important behavior. A rename within one filesystem can be a metadata operation, while a move across filesystems may require copying data and removing the source.

## 2. Work in an intentionally disposable boundary

Practice in a new directory whose exact path you can inspect:

```bash
practice=$(mktemp -d)
printf 'practice=%q\n' "$practice"
cd -- "$practice" || exit 1
```

Do not practice destructive commands in a repository, home directory, mounted share, or directory selected through an unchecked variable.

The safety boundary is not “I plan to be careful.” It is an isolated location with no valuable contents.

## 3. Create directories with explicit intent

`mkdir` creates directory entries:

```bash
mkdir reports
mkdir -p reports/2026/september
```

Without `-p`, a missing parent is an error. With `-p`, required parent directories are created and existing directories do not cause the same failure.

This makes `mkdir -p` useful for ensuring a path exists, but it can also conceal a mistaken path. Print or validate paths before using it with expanded variables.

```bash
destination="$practice/reports/2026"
case $destination in
  "$practice"/*) mkdir -p -- "$destination" ;;
  *) printf '%s\n' 'refusing path outside practice area' >&2 ;;
esac
```

This is an illustration of boundary checking, not a complete secure-deletion framework.

## 4. `touch` primarily changes timestamps

`touch` updates access and modification timestamps. If a named file does not exist, it normally creates an empty file:

```bash
touch notes.txt
```

That common creation behavior does not make `touch` a content-writing tool. To create a known file with known content, write the content explicitly:

```bash
printf '%s\n' 'status=ready' > status.txt
```

Use `touch -c` when supported if an absent file must not be created.

## 5. Copying creates another state to maintain

The basic interface is:

```bash
cp -- source.txt destination.txt
cp -R -- source-directory destination-directory
```

Before copying, answer:

- Does the destination exist?
- Will it be replaced or nested beneath another directory?
- Are permissions, timestamps, links, or extended metadata important?
- Is the destination on the same machine and filesystem?
- How will partial failure be detected?

Plain `cp` is suitable for ordinary files. Archival copies and deployments often need stronger preservation or transactional guarantees than a default recursive copy provides.

## 6. Destination interpretation depends on state

These commands do not mean the same thing when `archive` exists as a directory:

```bash
cp report.txt archive
cp report.txt archive/report.txt
```

The first may create `archive/report.txt`; if `archive` is absent, it creates a file named `archive`. This state-dependent interpretation is convenient interactively and risky in automation.

Validate the required type:

```bash
test -d archive || {
  printf '%s\n' 'archive directory is missing' >&2
  exit 1
}
cp -- report.txt archive/report.txt
```

## 7. Overwrite protection is a policy choice

Interactive prompts can help during manual work:

```bash
cp -i -- draft.txt final.txt
mv -i -- draft.txt final.txt
```

They are poor foundations for unattended automation because a prompt may block forever or behave differently without a terminal.

Alternatives include:

- fail if the destination exists,
- create a versioned destination,
- write to a temporary file and rename after validation,
- preserve an explicit backup,
- or make replacement an intentional documented operation.

Options such as GNU `-n` or `--backup` are useful but not uniform across platforms. Check the local manual.

## 8. Moving can mean rename or copy-and-remove

Within one filesystem, `mv` can often rename an entry atomically:

```bash
mv -- report.tmp report.txt
```

Readers generally see either the old name or the new name rather than partial file contents. This makes a validated temporary file followed by a same-filesystem rename a valuable publication pattern.

Across filesystems, an implementation may need to copy and then remove. That operation has a larger failure window and different performance characteristics. Do not assume every `mv` is a cheap atomic rename.

## 9. Removal usually removes a name

For a regular file:

```bash
rm -- obsolete.txt
```

The command requests removal of a directory entry. Storage is reclaimable when the filesystem no longer has relevant links or open references. A process that already has the file open may continue accessing it even after the name disappears.

This explains a common operational surprise: deleting a large active log may not immediately free space until the writer closes its open file descriptor.

Command-line removal does not normally move content to a desktop trash system. Recovery may be difficult or impossible.

## 10. Directory removal is intentionally constrained

`rmdir` removes empty directories:

```bash
rmdir empty-directory
```

Its refusal to remove nonempty directories is a useful safety property.

Recursive removal broadens scope through an entire tree. Never teach or use `rm -rf` as a generic response to permission, build, or cleanup problems. Before any recursive removal:

1. resolve the exact target,
2. reject empty or broad values,
3. ensure the target is inside the intended boundary,
4. inspect the tree,
5. consider a recoverable move instead,
6. and verify after the operation.

## 11. Globs can silently broaden or shrink scope

The shell expands a pattern before invoking the utility:

```bash
printf '%q\n' ./*.tmp
```

Inspecting with `printf` is safer than first discovering the expansion through `rm`.

Patterns also have edge cases:

- `*` normally omits leading-dot names,
- an unmatched pattern may remain literal in default Bash,
- configuration can change unmatched-pattern behavior,
- and a variable that expands to an empty string may change a constructed path.

Do not attempt to include hidden files with patterns such as `.*`; that style is difficult to reason about and can include special entries on some systems.

## 12. Quoting preserves one pathname, not correctness

This preserves the variable value as one argument:

```bash
rm -- "$target"
```

Quoting prevents splitting and pathname expansion. It does not prove that `$target` names the intended object.

Safety needs both syntactic and semantic checks:

```text
quote the value     → preserve its argument boundary
validate the value  → prove it belongs to the intended scope
inspect the object  → understand current state
```

## 13. Prefer reversible transitions

When practical, stage changes before deletion:

```bash
mkdir -p -- quarantine
mv -- candidate.txt quarantine/
```

After verification and an appropriate retention period, the quarantine can be cleaned deliberately.

Version control, snapshots, backups, object versioning, and trash systems provide different recovery guarantees. A copy in the same directory is not a backup against disk failure, account compromise, or broad deletion.

## 14. Verify outcomes independently

Do not infer success only from silence. Inspect the expected postcondition:

```bash
test -f final.txt || {
  printf '%s\n' 'final file missing' >&2
  exit 1
}
```

For important content, compare sizes or cryptographic hashes as appropriate. For a rename, verify both that the destination exists and that the obsolete source name is gone.

The correct verification depends on the guarantee required.

## 15. Common misconceptions

### “`rm` erases bytes immediately”

It normally removes directory entries. Open references, links, filesystem behavior, and storage reuse affect what happens next.

### “`mv` is always atomic”

Same-filesystem rename can be atomic; cross-filesystem movement may be copy-and-remove.

### “Quotes make a destructive command safe”

They preserve argument boundaries. They cannot validate intent.

### “Interactive prompts make automation safe”

Prompts require a person and a terminal. Automated safety needs explicit preconditions and failure behavior.

### “A recursive flag is just a convenience”

It changes one-object scope into tree scope and deserves a higher review threshold.

## 16. Platform comparison

| Concern | Linux/GNU tools | macOS/BSD tools | Windows/PowerShell |
| --- | --- | --- | --- |
| Recursive copy options | commonly `cp -R` or `-r` | `cp -R`; details differ | `Copy-Item -Recurse` |
| Removal recovery | no default trash behavior | no default trash behavior | `Remove-Item` also bypasses Explorer Recycle Bin |
| Atomic rename | filesystem- and boundary-dependent | filesystem- and boundary-dependent | filesystem- and sharing-dependent |
| Metadata preservation | explicit options required | options differ | object/provider semantics differ |

Cross-platform tools should specify required guarantees instead of assuming identical flags.

## Core Computer Science Concept

Filesystem changes are **state transitions with preconditions and postconditions**.

```text
precondition → operation → postcondition
```

Idempotence, atomicity, durability, and reversibility are separate properties. A command can have one without the others.

## Engineering Connections

- Deployments often publish by atomic same-filesystem rename.
- Database migrations use the same precondition-and-verification discipline.
- Object stores may implement “rename” as copy plus delete.
- Build systems isolate generated outputs so cleanup has a narrow boundary.
- Incident recovery depends on backups tested before destructive maintenance.

## From the Field

A cleanup script constructs `"$build_root/output"`. When `build_root` is unexpectedly empty, the result becomes `/output`, a valid absolute path outside the project.

Quoting worked perfectly. Validation was missing. A safe implementation establishes a trusted root and proves that the resolved target remains beneath it.

## Engineering Review

### What problem does this solve?

It provides a disciplined way to change filesystem state without relying on optimistic assumptions.

### Why was it designed this way?

Unix exposes small operations over names and objects; their composition gives flexibility while leaving policy to the caller.

### When should I use it?

Use the inspect–constrain–change–verify sequence for routine work, scripts, deployments, and maintenance.

### When should I avoid it?

Avoid basic commands when the job needs transactions, synchronization, durable backups, access coordination, or application-aware migration.

### How does this make me a better engineer?

It teaches you to reason about scope, state-dependent behavior, atomicity, and recovery before mutation.

### How does this reduce waste?

Precise operations prevent rework, data loss, blocked automation, and time-consuming recovery.

## Handbook Principle #14

> Inspect before mutation, constrain destructive scope, prefer reversible transitions, and verify the postcondition independently.

## Practical Observation

In a disposable directory on macOS or Linux:

```bash
printf '%s\n' 'version 1' > report.txt
cp -- report.txt report.backup
printf '%s\n' 'version 2' > report.next
mv -- report.next report.txt
printf 'current: '; cat report.txt
printf 'backup:  '; cat report.backup
```

Identify which steps create content, which create another name or object, and which transition could publish a completely written file at one pathname.

## Looking Ahead

Chapter 15 stops changing files and asks a different question: how can a filesystem tree be queried precisely by name, type, size, time, and other metadata?
