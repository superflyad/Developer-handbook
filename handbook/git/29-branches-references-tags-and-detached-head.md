# Chapter 29 — Branches, References, Tags, and Detached `HEAD`

Once a commit graph exists, humans need stable names for points of interest. Git uses references, while the working tree shows one selected state at a time.

The central idea is:

> A branch is a movable reference to a commit, a tag is usually a deliberately stable label, and `HEAD` tells Git where new local commits attach.

## 1. Branches do not copy the repository

Suppose the graph is:

```text
A ← B ← C   main
```

Creating `topic` at `C` adds another name for the same commit:

```text
A ← B ← C   main, topic
```

After switching to `topic` and committing `D`:

```text
A ← B ← C   main
        ↖ D   topic
```

The arrows in this drawing stand for ancestry conceptually; a commit actually records parent references toward older commits. The key point is that no complete duplicate history was created. The branch name moved to a new commit while `main` remained at `C`.

## 2. `HEAD` selects the current context

Normally `HEAD` is attached to a branch:

```text
HEAD → topic → D
```

An ordinary new commit advances `topic`. To observe:

```bash
git branch --show-current
git symbolic-ref --short HEAD
git log -1 --oneline --decorate
```

The low-level `symbolic-ref` command fails in a detached state; that failure is useful evidence, not a Git malfunction.

## 3. Create and switch deliberately

```bash
git switch -c topic/clear-error
```

This creates a branch at the current commit and switches to it. `git branch topic/clear-error` alone creates the name without switching.

Before switching in a real repository:

```bash
git status --short --branch
```

Git may carry compatible uncommitted changes across a switch or refuse a switch that would overwrite them. Do not assume switching automatically saves, discards, or isolates unfinished work.

## 4. Branches are pointers, not workspaces

With one ordinary working tree, switching branches updates the index and files to reflect the selected branch where safe. Two branches do not mean two simultaneously separate directories.

If parallel tasks need independent files, use separate clones or Git worktrees. Chapter 35 explains why a worktree has its own `HEAD` and index while sharing much repository data.

## 5. Detached `HEAD` is an inspection state

To inspect a recorded commit without attaching to a branch:

```bash
git switch --detach HEAD~1
```

Now `HEAD` names a commit directly. You can build, test, and even commit there. New commits made while detached are not automatically advanced by an ordinary branch name. Before switching away from valuable detached work, give it a name:

```bash
git switch -c topic/keep-discovery
```

Reflogs may help recover an unnamed detached commit for a time, but an intentional branch is safer than relying on retention behavior.

## 6. Tags label meaningful points

A lightweight tag is a reference directly to an object, commonly a commit:

```bash
git tag experiment-v1
```

An annotated tag creates a tag object with message and tagger metadata:

```bash
git tag -a v1.0.0 -m 'Release 1.0.0'
```

Annotated tags are usually better for release records. Neither form proves a release artifact was built or deployed. A tag is a label in the repository, while a release process needs additional provenance and policy.

Tags can technically be moved or deleted, but consumers often treat published release tags as stable. Moving one after distribution creates ambiguity and may require coordination.

## 7. Reachability explains branch deletion

A commit is **reachable** from a ref if following parent links from the ref can reach it. A commit may remain reachable from another branch or tag after one branch is deleted.

Inspect before deleting a local branch:

```bash
git branch --merged
git log --oneline main..topic/clear-error
```

`git branch -d topic/clear-error` refuses deletion when Git's merged check is not satisfied. `-D` forces deletion of the reference, not necessarily immediate deletion of every underlying object. Force deletion can still make work hard to find; verify what remains reachable first.

## 8. Tags and branches are different contracts

```text
branch → expected to advance with new commits
tag    → expected to identify a chosen point
```

Git permits more than this social convention, but workflows rely on it. CI systems often build a branch's changing tip for continuous integration and a tag's chosen commit for a release candidate.

The exact deployed artifact still needs its own immutable identity and verification.

## 9. A disposable branch observation

Start from a disposable repository with an initial commit:

```bash
git branch main-point
git switch -c topic/demo
printf '%s\n' 'new work' > feature.txt
git add -- feature.txt
git commit -m 'Add feature note'
git log --oneline --graph --decorate --all
```

`main-point` still identifies the original commit. `topic/demo` identifies the new one. The example does not depend on the initial branch being named `main`.

## 10. Common misconceptions

### “A branch is a copied directory”

It is a ref into shared commit history. The working tree changes when you switch.

### “Switching always requires a clean tree”

Git can carry compatible edits, but it refuses operations that would lose changes unless explicitly overridden.

### “Detached `HEAD` means broken repository”

It is a valid state for inspection and testing; new commits need a ref if they should remain easy to find.

### “Deleting a branch instantly deletes all its commits”

Other refs and reflogs may still reach them, and object cleanup is separate. Still, deletion can remove the only convenient name.

### “A tag guarantees deployment”

It names a Git object; deployment is a separate external state transition.

## Core Computer Science Concept

References are **mutable names over immutable graph nodes**. This separates stable object identity from convenient labels that can advance with work. Reachability from refs determines which history is easy to discover and retain.

## Engineering Connections

- Feature branches isolate review scope without copying all historical data.
- Release tags provide stable source coordinates for builds and incident response.
- Detached checkouts let CI test exact commits independently of moving branch tips.
- Reachability is central to garbage collection and recovery, not merely branch listing.

## From the Field

An engineer checks out an older commit to reproduce a bug, fixes it, and commits while detached. They then switch to `main` and cannot see the fix in `git log main`. The work may still exist locally, but it was never attached to a branch. Creating a branch at the detached commit before switching would have made ownership explicit.

## Engineering Review

### What problem does this solve?

It gives meaningful names to positions in the commit graph and supports independent lines of work.

### Why was it designed this way?

Lightweight refs make branches cheap while immutable commits preserve exact history.

### When should I use it?

Use branches for evolving work, tags for selected stable points, and detached checkouts for deliberate inspection.

### When should I avoid it?

Avoid treating branch names as durable artifact identities or leaving valuable detached commits unnamed.

### How does this make me a better engineer?

It makes history shape, current context, and reachability visible before switching or deleting work.

### How does this reduce waste?

Correct ref reasoning prevents misplaced commits, accidental branch deletion, and confusion about what a release label proves.

## Handbook Principle #29

> Preserve exact commits as objects, advance branches by intent, and give valuable work a name before leaving its checkout.

## Practical Observation

In a disposable repository, create `topic/demo`, commit once, then inspect `git branch -v` and `git log --all --graph --decorate --oneline`. Switch to the original commit with `git switch --detach <commit-id>`, confirm `git branch --show-current` is empty, and return to the topic branch without changing files.

## Looking Ahead

Local references are only one repository's view. Chapter 30 introduces remote-tracking refs and the separate operations of fetching, integrating, and pushing.

## References

- [Git branches](https://git-scm.com/docs/git-branch)
- [Git switch](https://git-scm.com/docs/git-switch)
- [Git tags](https://git-scm.com/docs/git-tag)
