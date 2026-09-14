# Chapter 13 — Navigation and Path Resolution

A command that names a file depends on two things: the pathname supplied and the process's current working directory. Navigation becomes reliable when both are explicit.

The central idea is:

> A pathname is an instruction for resolving a name from a starting directory; predict that resolution before acting on the result.

## 1. Location is process state

Every process has a current working directory. A shell reports its own with:

```bash
pwd
```

When the shell launches a child, the child normally inherits that directory. Relative pathnames passed to the child are resolved from the child's working directory.

```text
shell working directory: /home/ada/project
relative pathname:       docs/guide.md
resolved object:         /home/ada/project/docs/guide.md
```

The terminal window does not own this location. The shell process does. Two shells displayed in two tabs can have different working directories.

## 2. Absolute and relative pathnames

An absolute pathname begins at the filesystem root:

```text
/home/ada/project/docs/guide.md
```

A relative pathname begins at the process's current working directory:

```text
docs/guide.md
```

Absolute paths are independent of the current directory but tied to one filesystem layout. Relative paths are portable within a project but depend on execution context.

Neither is inherently better. Choose based on the boundary you want to make explicit.

## 3. Directory entries form the route

A pathname is resolved component by component:

```text
docs/reference/api.md
 │       │       └─ entry api.md inside reference
 │       └───────── entry reference inside docs
 └───────────────── entry docs inside the starting directory
```

Intermediate components must resolve to searchable directories. The final component may identify a regular file, directory, symbolic link, device, or another filesystem object.

Repeated separators and `.` can often be normalized, but symbolic links and `..` make naive string cleanup different from actual filesystem resolution. The kernel resolves objects; text manipulation merely rewrites names.

## 4. The special entries `.` and `..`

`.` refers to the current directory in pathname resolution:

```bash
ls .
./tools/check
```

`..` refers to the parent directory:

```bash
cd ..
ls ../shared
```

These are not instructions to “go somewhere” by themselves. They are pathname components. `cd` changes the shell's directory to the object resolved by its operand.

At the filesystem root, `/..` still resolves to `/`.

## 5. Home-directory shorthand is shell expansion

In Bash, an unquoted leading tilde can expand before a command runs:

```bash
printf '%s\n' ~
ls ~/projects
```

`~` is not a directory entry and most external programs do not expand it. The shell changes the word first.

Quoting can prevent tilde expansion:

```bash
printf '%s\n' '~'
```

Use `$HOME` when the value is data inside a larger quoted word:

```bash
printf '%s\n' "$HOME/projects"
```

Chapter 18 examines expansion and quoting as a complete evaluation process.

## 6. `cd` must change the current shell

Run:

```bash
cd /tmp
pwd
```

`cd` is a shell builtin because a separate child process cannot permanently change its parent's working directory.

Useful forms include:

```bash
cd              # home directory in Bash
cd -- /tmp      # explicit end of options
cd -            # previous working directory in Bash
```

Check the destination before assuming the change succeeded. In automation, make failure stop the dependent work:

```bash
cd -- project || exit 1
```

Without that check, later relative paths may operate in the wrong directory.

## 7. Logical and physical locations

Symbolic links allow more than one pathname to reach an object. A shell may preserve the logical route used to enter a directory:

```bash
pwd
pwd -P
```

In Bash and POSIX-style environments:

- logical mode preserves symbolic-link components where possible,
- physical mode resolves the physical directory path.

This distinction explains why `pwd` can display a path different from one obtained by resolving links. Use logical paths for human project context and physical paths when diagnosing link or mount behavior.

## 8. Listing is observation, not navigation

`ls` lists directory entries or information about operands. It does not change location.

```bash
ls
ls -la
ls -ld -- directory
```

The distinction between the last two patterns matters. `ls -l directory` usually lists the directory's contents; `ls -ld directory` describes the directory entry itself.

Treat colored or column-formatted output as presentation for people. Do not parse `ls` in automation: names can contain surprising characters, display escaping varies, and metadata columns vary by implementation and locale.

## 9. Hidden means a naming convention

In Unix environments, entries whose names begin with `.` are omitted by many ordinary listings:

```bash
ls -a
```

The leading dot does not create an access-control boundary. A hidden configuration file is still governed by ordinary permissions and is directly addressable by name.

Also remember that shell glob patterns such as `*` traditionally omit leading-dot names unless configured otherwise. “Everything visible” and “every directory entry” are different sets.

## 10. Pathnames can contain spaces and newlines

Unix pathnames may contain almost any byte except NUL; an individual component cannot contain `/`. Spaces, tabs, quotes, wildcard characters, and newlines may therefore be valid data.

Quote expansions that should remain one pathname:

```bash
target='draft reports/May review.md'
ls -l -- "$target"
```

This is unsafe:

```bash
ls -l $target
```

The shell may split and expand the value into multiple arguments. The bug occurs before `ls` begins.

## 11. Establish location without relying on memory

Before a consequential operation:

```bash
pwd
printf 'target=%q\n' "$target"
```

`printf %q` is a Bash-specific diagnostic that produces reusable shell-escaped output. It helps reveal whitespace and control characters.

A strong interactive sequence is:

```text
locate yourself → inspect the target → constrain the command → perform the action → verify
```

This is more dependable than encoding the current directory in the prompt color and assuming it is correct.

## 12. Project-relative execution

Project tools often assume they run from a repository root. Make that assumption observable:

```bash
project_root=$(git rev-parse --show-toplevel) || exit 1
cd -- "$project_root" || exit 1
```

For a general script, a path relative to the script file and a path relative to the caller's working directory are different contracts. Part VI will address script-location techniques; for now, document which starting directory a command expects.

## 13. Common misconceptions

### “The prompt proves where I am”

The prompt is formatted shell configuration. `pwd` queries the shell's working-directory state.

### “`~` is stored in the filesystem”

It is shell shorthand expanded before pathname resolution.

### “An absolute path is always portable”

It avoids current-directory dependence but embeds a particular filesystem layout.

### “`ls -a` bypasses permissions”

It changes listing selection, not authority.

### “Normal filenames never contain newlines”

Many interfaces encourage simple names, but robust tools cannot assume them when input is untrusted.

## 14. Platform comparison

| Concept | POSIX-style environment | PowerShell on Windows |
| --- | --- | --- |
| Root syntax | `/` | drive roots such as `C:\` and provider roots |
| Home shorthand | shell expands `~` | PowerShell resolves `~` through its provider |
| Separator | `/` | commonly `\`; PowerShell often accepts `/` |
| Case sensitivity | depends on filesystem; commonly sensitive | commonly case-insensitive, case-preserving |
| Current location | process working directory | location can also belong to a PowerShell provider |

Git Bash, WSL, containers, remote shells, and native Windows programs can expose different pathname namespaces on the same computer. Always identify which environment resolves the path.

## Core Computer Science Concept

Path resolution is **name lookup in a hierarchy**. Each component selects an entry relative to a directory object, while the working directory supplies implicit context for relative names.

Implicit context makes interactive work concise. It also creates hidden coupling. Reliable systems either control that context or use names whose starting point is explicit.

## Engineering Connections

- Build tools choose a project root before resolving configuration.
- Web servers map URL paths into separate filesystem or object-store namespaces.
- Containers present a filesystem root different from the host's.
- CI runners frequently start in a checkout directory that differs from a laptop path.
- Path traversal vulnerabilities arise when untrusted components influence resolution beyond an intended root.

## From the Field

A cleanup command assumes it runs in a generated-output directory. A failed `cd` leaves the shell in the repository root, and the following relative removal targets source files instead.

The primary defect is not the removal command. It is allowing a required context change to fail without stopping dependent work.

## Engineering Review

### What problem does this solve?

It makes filesystem location and pathname interpretation predictable.

### Why was it designed this way?

Hierarchical names provide compact, composable references, while a per-process working directory supplies convenient local context.

### When should I use it?

Reason explicitly about paths whenever commands depend on location, cross environment boundaries, or modify files.

### When should I avoid it?

Avoid depending on an undocumented working directory in reusable automation. Establish or validate the required context.

### How does this make me a better engineer?

It teaches you to separate a textual pathname, its starting context, and the filesystem object ultimately resolved.

### How does this reduce waste?

Explicit location prevents “works on my machine” failures, misplaced outputs, and operations performed in the wrong directory.

## Handbook Principle #13

> Treat the working directory as input, and resolve every consequential pathname from a context you have verified.

## Practical Observation

In a disposable directory on macOS or Linux, run:

```bash
mkdir -p actual/work
ln -s actual shortcut
cd shortcut/work || exit 1
printf 'logical:  '; pwd
printf 'physical: '; pwd -P
printf 'parent:   '; printf '%s\n' "$(cd .. && pwd)"
```

Explain why the logical and physical displays may differ and which path a child process inherits as its working directory object.

## Looking Ahead

Navigation observes and changes process location. Chapter 14 uses that verified context to create, copy, move, and remove filesystem entries safely.
