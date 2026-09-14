# Chapter 15 — Finding Files and Inspecting Metadata

Filesystem discovery answers questions about names and objects. It is different from searching the bytes stored inside regular files.

The central idea is:

> Express discovery as a query over a bounded tree, then choose an action whose filename contract preserves every match exactly.

## 1. Separate discovery from content search

These are different questions:

```text
Which files are named *.log?          → filesystem discovery
Which files contain the word ERROR?   → content search
```

`find` walks directory trees and evaluates information about filesystem entries. `grep` reads content and is the subject of Chapter 16.

Keeping the questions separate improves both performance and correctness. First constrain candidate objects; then read content only when needed.

## 2. A `find` command has start points and an expression

A basic invocation is:

```bash
find logs -type f -name '*.log' -print
```

Its roles are:

```text
logs          starting point
-type f       test: regular files
-name pattern test: basename matches pattern
-print        action: write the matched pathname
```

`find` traverses beneath each starting point and evaluates the expression for each encountered entry.

State the starting point explicitly. An accidental `find /` is not merely slower than `find .`; it crosses a much larger authority, performance, and error boundary.

## 3. Quote patterns meant for `find`

This is deliberate:

```bash
find . -name '*.md' -print
```

The quotes prevent the shell from expanding `*.md`. The pattern reaches `find`, which applies it to each basename during traversal.

Without quotes, the shell may replace the pattern using only entries in the current directory before `find` starts. The same visible text would then have an entirely different interpreter and scope.

## 4. Tests compose into predicates

Common tests include:

```bash
find . -type f -name '*.log' -size +1M -print
find . -type d -empty -print
find . -type f -mtime -2 -print
```

Exact size units and timestamp rounding rules vary by implementation and deserve a manual-page check. Treat examples as query shapes, not universal natural-language translations.

Adjacent tests are commonly combined as logical AND. OR and negation can be expressed too:

```bash
find . -type f \( -name '*.md' -o -name '*.txt' \) -print
find . -type f ! -name '*.bak' -print
```

Parentheses are quoted or escaped because they also have meaning to the shell.

## 5. Expression order affects work

`find` expressions are evaluated per entry, generally from left to right with short-circuit behavior. Put inexpensive, selective tests before costly actions where semantics permit.

Do not confuse logical selection with traversal control. A test may reject an entry without preventing descent into its directory. Use implementation-documented controls such as `-prune` when a subtree must not be traversed.

For example:

```bash
find . -name .git -prune -o -type f -name '*.md' -print
```

Read this as two branches: prune `.git`; otherwise print matching Markdown files.

## 6. Metadata gives evidence about an object

Use purpose-built tools instead of parsing a decorative listing:

```bash
stat -- README.md       # common GNU form
file -- README.md
```

`stat` reports metadata such as type, size, ownership, mode, and timestamps. Its options and output differ substantially between GNU/Linux and macOS.

`file` examines data and other evidence to classify an object. Its result is an informed classification, not a security guarantee and not a substitute for parsing the format.

For portable automation, query the smallest property you need through a documented interface rather than scraping the default human-readable output.

## 7. Time metadata answers different questions

Common Unix metadata includes:

- modification time: when file content was last modified,
- status-change time: when inode metadata or content status changed,
- access time: when content was last accessed, subject to mount policy,
- birth or creation time: available on some filesystems and interfaces, not universally.

The historical name `ctime` means status-change time on Unix, not creation time.

Timestamp behavior depends on filesystem precision, clock state, mount options, caching, and command rounding. Avoid using a casual `-mtime` query as proof of an exact event chronology.

## 8. `locate` trades freshness for speed

Where installed, `locate` searches a database of pathnames rather than walking the live tree:

```bash
locate project.conf
```

It can be much faster across large trees, but results depend on when and how the database was updated. A newly created file may be absent; a removed file may remain listed.

Use `find` when current filesystem state matters. Use `locate` for fast candidate discovery when staleness is acceptable and its database scope is understood.

## 9. Printed pathnames are not safely line-delimited data

A pathname can contain a newline. Therefore this pipeline is not generally safe for arbitrary names:

```bash
find . -type f -print | while read -r path; do
  printf '%s\n' "$path"
done
```

For display to a person, ordinary `-print` may be adequate. For machine transport, use a NUL-delimited interface where supported:

```bash
find . -type f -print0
```

NUL is suitable because it cannot occur inside a Unix pathname.

## 10. Prefer `-exec ... {} +` for direct actions

When a command accepts pathnames as arguments, `find` can build invocations directly:

```bash
find . -type f -name '*.log' -exec wc -l -- {} +
```

`{}` represents matched pathnames, and `+` groups as many as practical into each invocation. This avoids converting pathnames into newline-delimited text.

The semicolon form runs once per match and requires quoting or escaping from the shell:

```bash
find . -type f -name '*.log' -exec wc -l -- {} \;
```

Use per-file invocation only when the action truly requires it.

## 11. Understand the `xargs` boundary

`xargs` turns input records into command arguments. Default blank-delimited input is unsafe for arbitrary filenames.

When both tools support it:

```bash
find . -type f -print0 | xargs -0 wc -l --
```

Even with correct delimiters, behavior for empty input varies by implementation unless an option such as GNU `-r` is used. `find -exec ... {} +` often expresses the relationship more directly.

Also consider time-of-check/time-of-use races: another actor may replace a matched pathname between discovery and action. Strong security boundaries require APIs and designs stronger than a pathname pipeline.

## 12. Actions turn queries into mutations

Begin with a reporting action:

```bash
find candidate-root -type f -name '*.tmp' -print
```

Only after reviewing scope should a mutating action be considered. Deletion through `find` is especially consequential because traversal continuously discovers more targets.

Separate the workflow:

```text
define boundary → print matches → sample metadata → count → approve → mutate → verify
```

For important data, preserve a manifest or move matches into a recoverable quarantine instead of deleting immediately.

## 13. Common misconceptions

### “`find` searches file contents”

It primarily traverses filesystem objects and evaluates names or metadata. Content search needs a reader such as `grep`.

### “`*.log` should be left unquoted”

Unquoted, the current shell may expand it before `find` receives the pattern.

### “One line equals one filename”

Newlines can occur in pathnames. Use a pathname-safe interface for automation.

### “`locate` is a faster `find` with identical results”

It queries an index whose scope and freshness may differ from live state.

### “Metadata proves history”

Metadata reports current recorded values under filesystem-specific rules. It is not a complete audit log.

## 14. Platform comparison

| Capability | GNU/Linux | macOS/BSD | Windows/PowerShell |
| --- | --- | --- | --- |
| Live tree query | GNU `find` | BSD `find` | `Get-ChildItem` with filtering |
| Indexed lookup | commonly `locate` variants | Spotlight tools or `locate` | Windows Search and application indexes |
| Metadata display | GNU `stat` syntax | BSD `stat` syntax differs | `Get-Item` objects |
| NUL-safe handoff | `-print0`, `xargs -0` | commonly available | object pipeline avoids text delimiters between cmdlets |

Teach the query model first; then translate it into the environment's native interface.

## Core Computer Science Concept

Filesystem discovery is **predicate evaluation over a traversal**.

```text
walk bounded graph → evaluate properties → select objects → perform action
```

Selection, traversal, representation, and action are distinct stages. Keeping them separate makes performance and safety easier to reason about.

## Engineering Connections

- Build systems discover source files but often prefer explicit manifests for reproducibility.
- Backup systems compare metadata before deciding which content to transfer.
- Security scanners traverse trees under carefully constrained authority.
- Deployment cleanup needs pathname-safe selection and race-aware mutation.
- Search indexes gain speed by accepting an explicit freshness model.

## From the Field

A maintenance job pipes newline-separated `find` output into `xargs rm`. A user creates a filename containing a newline and text resembling another path. The consumer no longer receives the same set of names that the producer found.

The defect is a broken representation contract. NUL-delimited transport or direct `-exec` preserves pathname boundaries.

## Engineering Review

### What problem does this solve?

It makes live filesystem discovery precise by combining bounded traversal, metadata predicates, and deliberate actions.

### Why was it designed this way?

Separating selection from action allows the same query mechanism to support observation, reporting, and controlled mutation.

### When should I use it?

Use it to locate objects by name, type, size, timestamps, ownership, or other filesystem properties.

### When should I avoid it?

Avoid tree walking when an authoritative manifest, database, application API, or indexed search provides the required guarantee more directly.

### How does this make me a better engineer?

It teaches predicate design, traversal scope, representation safety, and the limits of pathname-based actions.

### How does this reduce waste?

Precise queries reduce manual browsing, unnecessary content reads, accidental matches, and unsafe one-off cleanup logic.

## Handbook Principle #15

> Bound the traversal, express selection as predicates, and preserve pathname boundaries all the way to the action.

## Practical Observation

In a disposable directory on macOS or Linux:

```bash
mkdir -p source vendor nested
printf '%s\n' alpha > source/one.txt
printf '%s\n' beta > nested/two.txt
printf '%s\n' ignored > vendor/three.txt

find . -name vendor -prune -o -type f -name '*.txt' -print
find . -type f -name '*.txt' -exec wc -l -- {} +
```

Explain which expression prevents descent into `vendor`, why the pattern is quoted, and how the second command preserves each pathname as an argument.

## Looking Ahead

Chapter 15 finds objects by names and metadata. Chapter 16 opens text inputs and selects lines by literal or regular-expression content.
