# Chapter 24 — Why Git Works: Repositories, Objects, and History

Part II taught us to inspect system state before changing it. Git applies that discipline to a project's history. Its commands become easier to predict once the stored model is clear.

The central idea is:

> Git stores content-addressed objects and uses named references to select commits; the working directory is a view and workspace built from that history, not the history itself.

## 1. The problem version control solves

A sequence of copied directories named `project-final`, `project-final-2`, and `project-really-final` cannot reliably answer which change introduced a defect, how two contributors' work relates, or what was shipped. Timestamps are not a reviewable explanation of intent.

Version control records meaningful states and their ancestry. Git also makes each clone a repository with local history, so inspection and commits need not wait for a server. A hosting service adds sharing, policy, and review; it is not the sole owner of the repository model.

## 2. Repository, working tree, and remote

A normal Git project has two local pieces:

```text
project/
├── .git/        repository metadata, objects, and references
└── files...     working tree available to editors and tools
```

The `.git` entry can be a file pointing elsewhere, as with linked worktrees. Treat `.git` as an implementation boundary, not a directory to edit manually.

A **remote** is another repository identified by a convenient name such as `origin`. It may be on another machine or on the same machine. The remote is not inherently the authoritative version; a team's policy determines which references may be published and integrated.

## 3. `init` and `clone` establish different starting states

In a new disposable directory:

```bash
git init project
```

This initializes a local repository. It does not automatically make a commit or connect a remote. The unborn initial branch has no commit yet.

By contrast:

```bash
git clone /path/to/existing-repository project-copy
```

This copies reachable repository data, creates local configuration and remote-tracking information, and normally checks out a branch. Shallow or filtered clones intentionally omit some history or objects; do not assume every clone is complete without checking how it was created.

## 4. Objects carry content and relationships

Git's central object types are:

| Object | Role |
| --- | --- |
| Blob | Stores file content, not its pathname |
| Tree | Maps names and modes to blobs or other trees |
| Commit | Names a root tree, parent commit(s), and metadata |
| Annotated tag | Names another object with tag metadata |

A pathname is represented by entries in trees. The same content can be referenced under different names. A commit points to a tree describing one recorded project state.

## 5. A commit is a snapshot with ancestry

Conceptually:

```text
commit C
├── tree → recorded project contents
├── parent → commit B
├── author and committer metadata
└── message
```

Git does not need to store every revision as a textual patch to make history useful. It records snapshots of trees and derives diffs by comparing states. Storage mechanisms may optimize repeated content; the conceptual model remains snapshots and references.

A root commit has no parent. An ordinary commit normally has one. A merge commit usually has two or more parents. Those parent links form a directed acyclic graph, not simply a list.

## 6. Object IDs identify exact object content

Git computes an object name from its type and contents. Changing a commit's tree, message, parent, author, or committer information produces a different commit identity. The identifier is not a permanent label for a human idea such as “the login fix.”

Git repositories can use different object-hash formats, so examples should not assume a fixed ID length or algorithm. Abbreviated IDs are convenient only while they remain unambiguous in the repository where they are used.

Content addressing supports integrity checks and deduplication. It does not establish that a commit is trustworthy, reviewed, or authorized. Those are separate social and cryptographic questions.

## 7. References make history usable

Humans rarely type full object IDs. A branch name such as `main` is a reference to a commit. `HEAD` identifies the current checkout position, normally through a branch reference.

```text
main → commit C → commit B → commit A
HEAD → main
```

The commits do not contain the name `main`. The name can move to a later commit while old commits remain in the object graph for some time. Chapter 29 develops references in detail.

## 8. Git history is not a backup policy

Git can recover many committed states, but it does not automatically protect every local file:

- untracked files are outside ordinary commits,
- ignored files may never be recorded,
- uncommitted edits can be discarded,
- unreachable objects can eventually be pruned,
- and a remote may not have received local commits.

Backups, replication, retention, and access control remain separate responsibilities. A successful `git commit` records a local state; it does not prove another machine has it.

## 9. Observe the model without editing internals

In a disposable repository with a commit:

```bash
git log --oneline --decorate --graph
git cat-file -t HEAD
git cat-file -p HEAD
git ls-tree HEAD
```

`cat-file` and `ls-tree` expose the stored model. They are useful for learning and diagnosis; everyday work can usually use `status`, `show`, `log`, and `diff`.

Do not write directly into `.git/objects` or `.git/refs` to “fix” a repository. Use Git interfaces that maintain the relationships and invariants.

## 10. A reproducible first observation

The following Bash example creates a new repository under a disposable directory. It does not touch this handbook's history:

```bash
practice=$(mktemp -d)
cd -- "$practice" || exit 1
git init -q demo
cd demo || exit 1
git config user.name 'Practice Author'
git config user.email 'practice@example.invalid'
printf '%s\n' 'version one' > note.txt
git add -- note.txt
git commit -qm 'Add first note'

git log --oneline --decorate
git cat-file -t HEAD
git ls-tree HEAD
```

The name and email here are local practice metadata, not a real identity. The output's object ID will differ across runs because commit metadata includes time and other content.

## 11. Common misconceptions

### “GitHub is Git”

Git is a version-control system. GitHub is a hosting and collaboration service that operates on Git repositories.

### “A commit is a diff”

A commit names a tree and its ancestry. A diff is calculated between selected states.

### “A branch is a copy of every file”

A branch is a reference into shared object history. A checkout makes one state visible in a working tree.

### “A commit ID never changes for the same idea”

Rewriting the commit's metadata, content, or parents produces a new object ID.

### “Committed means backed up remotely”

A local commit is local until successfully transferred and retained elsewhere.

## Core Computer Science Concept

Git combines a **content-addressed object store** with a **directed acyclic graph**. Object identity answers “which exact data?” Parent links answer “which history led here?” References answer “which point in that graph do we mean today?”

Separating immutable objects from movable names is a pattern also seen in artifact registries, object stores, and deployment systems.

## Engineering Connections

- CI builds should identify an exact commit rather than a mutable branch name alone.
- Release artifacts need a traceable relationship to source commits and build inputs.
- A merge expresses two lines of ancestry, which matters during auditing and rollback.
- A repository can be healthy locally while the remote or backup policy is failing.

## From the Field

An engineer changes a commit message after sending a commit for review and is surprised that the review's old commit ID no longer appears at the branch tip. The file changes may be identical, but the commit object changed. The safe response is to inspect the new graph and coordinate before rewriting history others may have fetched.

## Engineering Review

### What problem does this solve?

Git preserves identifiable project states and their relationships so changes can be inspected, shared, and integrated.

### Why was it designed this way?

Content-addressed objects and local repositories support integrity checks, efficient sharing, and work without a central server.

### When should I use it?

Use this model whenever interpreting a commit, clone, branch, merge, or recovery operation.

### When should I avoid it?

Do not treat Git as a database for large generated artifacts, a secret vault, or a substitute for backups and access policy.

### How does this make me a better engineer?

It lets you reason from stored state and ancestry instead of memorizing command incantations.

### How does this reduce waste?

Correct object-model reasoning prevents lost local work, mistaken branch assumptions, and confusing snapshot-versus-diff explanations.

## Handbook Principle #24

> Treat commits as immutable recorded states, ancestry as a graph, and branch names as movable references—not as copies of directories.

## Practical Observation

Run the disposable example in Section 10. Add a second commit with changed `note.txt`, then compare:

```bash
git rev-parse HEAD
git rev-parse HEAD^
git show --stat HEAD
git diff HEAD^ HEAD -- note.txt
```

Explain which commands name stored objects and which derive a comparison. Keep this experiment outside any valuable repository.

## Looking Ahead

The object graph records history, but the next commit is assembled from local working state. Chapter 25 makes the working tree, index, and `HEAD` relationship explicit.

## References

- [Git object model](https://git-scm.com/book/en/v2/Git-Internals-Git-Objects)
- [Git glossary](https://git-scm.com/docs/gitglossary)
