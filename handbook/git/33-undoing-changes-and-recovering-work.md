# Chapter 33 — Undoing Changes and Recovering Work

“Undo my Git change” is incomplete. The right operation depends on *which state changed*, *what must be preserved*, and *whether anyone else has seen the commit*. A useful recovery procedure begins with observation, not a destructive command.

The central idea is:

> Name the state you want to change before choosing an undo command; recoverability shrinks as you discard uncommitted data.

## 1. Diagnose before touching state

Recall the three local states from [Chapter 25](25-the-working-tree-index-and-head.md): the working tree, index, and `HEAD`. Add one more dimension: the remote or another person's clone may already reference the commit. Start with read-only evidence:

```bash
git status --short
git diff
git diff --staged
git log --oneline --decorate -n 8
```

Ask: Is the change tracked? Is it staged? Is it committed? Is that commit published? Do I want to keep the file content, keep the commit in history, or reverse its effect? If uncertain, copy the affected file outside the disposable exercise repository or make a new, clearly named safety branch before changing a ref. A branch protects a committed tip; it does not protect uncommitted edits.

## 2. A state-based decision table

| Situation | Typical action | What remains |
| --- | --- | --- |
| Unstaged tracked edit to discard | `git restore -- path` | Index and `HEAD` unchanged; working-tree edit lost |
| Staged change to unstage, but keep | `git restore --staged -- path` | Working-tree content kept; index reset for that path |
| Local last commit to uncommit, keep staged | `git reset --soft HEAD^` | Content stays in index and working tree |
| Local last commit to uncommit, keep edits unstaged | `git reset HEAD^` | Working-tree content kept; index matches new `HEAD` |
| Published commit whose effect must be reversed | `git revert <commit>` | Existing history kept; a new inverse commit is added |

These are typical cases, not commands to run in sequence. `HEAD^` requires a parent and is inappropriate for a root commit. Check the graph and affected paths before using it. A merge commit needs special treatment for revert; see the command's documentation and decide which parent is the mainline.

## 3. Restore a tracked working-tree path

By default, `git restore -- path/to/file` writes the index version into that working-tree path. Any unstaged tracked edits to that path are discarded. It does not unstage changes already in the index. To unstage while retaining current working-tree content:

```bash
git restore --staged -- path/to/file
git diff -- path/to/file
```

To explicitly restore a tracked path from `HEAD` into both the index and working tree, Git supports `git restore --source=HEAD --staged --worktree -- path/to/file`. That is a double discard; inspect both diffs and consider a backup before using it. `restore` does not recover an untracked file deleted by the operating system, because Git never recorded that file.

## 4. Reset moves a ref; its mode controls the other states

The commit-moving form of `git reset` changes the current branch tip. Its modes decide what happens to index and working tree:

| Mode | Branch tip | Index | Working tree |
| --- | --- | --- | --- |
| `--soft` | Moves | Preserved | Preserved |
| `--mixed` (default) | Moves | Reset to target | Preserved |
| `--hard` | Moves | Reset to target | Reset to target |

`--soft` and default mixed reset are useful for fixing unpublished commits while retaining the content. `--hard` can destroy tracked uncommitted changes; it can also overwrite untracked paths that obstruct checkout. It is not a generic “make Git happy” button. This handbook uses it only as a concept, not as a routine recovery exercise.

The path form, such as `git reset HEAD -- path/to/file`, changes the index entry for a path rather than moving the current branch. That overloading is one reason `git restore --staged` communicates intent more clearly for unstaging.

Before moving a local branch tip, record it if recovery may matter:

```bash
git branch safety/before-reset
git log --oneline --decorate -n 5
```

Do this only after confirming a branch name is free and the current `HEAD` is the commit you want to retain. Do not reset a shared branch to erase published commits; other clones still contain them and later synchronization becomes harder.

## 5. Revert shared history visibly

`git revert <commit>` applies the inverse effect of a commit and creates a *new* commit. It leaves the original commit in ancestry. That makes revert appropriate for a bad change on a shared branch: people and automation can see both the original and the correction.

```bash
git status --short
git revert <commit-id>
git log --oneline -n 3
```

Revert can conflict when later commits depend on or modify the same content. Review the resulting diff and run tests. Reverting a merge needs a deliberate `-m <parent-number>` choice; it has future merge consequences, so it is not equivalent to reverting an ordinary single-parent commit. A revert is not a substitute for diagnosing whether the original change should be fixed rather than entirely backed out.

## 6. Reflogs are local breadcrumbs, not backups

Branch refs and `HEAD` reflogs record recent local ref movements. After a mistaken local reset or rebase, inspect them:

```bash
git reflog -n 12
git show <candidate-commit-id>
git branch recovery/found-work <candidate-commit-id>
```

The last command creates a reference to a verified candidate without changing the working tree. Then compare its tree or cherry-pick a wanted commit onto the correct branch. `HEAD@{1}` can be convenient, but its meaning changes after each ref movement; verify an explicit object ID before acting.

Reflogs are local to a repository and have expiration policies. Unreachable objects may later be pruned. Another clone's reflog is not synchronized with yours. A committed change is often recoverable for a time after a ref move, but that is not a retention guarantee. A discarded uncommitted edit that was never written to Git's object database usually cannot be restored by reflog. Git is not a backup system for untracked files or secrets.

## 7. A recovery sequence under pressure

1. Stop making further writes to the affected repository.
2. Capture `git status`, the current branch and commit ID, and relevant diffs.
3. Identify the state that contained the desired content: working tree, index, commit, another ref, or remote.
4. Prefer a non-destructive recovery target, such as a new branch at a verified commit.
5. Make one scoped change, inspect the result, and test before sharing it.

If the only copy was an untracked file deleted outside Git, look to editor history, filesystem backup, or a teammate's copy. Do not promise a Git-only recovery path that never existed.

## Common Misconceptions

- “`restore` always gets the last commit.” Without `--staged`, its default source is the index.
- “`reset` always deletes work.” Its mode matters; `--hard` is the especially destructive mode.
- “A revert removes the bad commit.” It adds a new commit that reverses its effect.
- “Reflog is shared and permanent.” It is local and subject to expiration.

## Core Computer Science Concept

Recovery depends on **reachability and durability**. A commit object may survive after a branch stops naming it, while an unwritten working-tree edit may have no Git object to find. A reflog is a temporary index of ref movements, not a second durable copy of every file state.

## Engineering Connections

- Incident response benefits from preserving evidence before attempting repair.
- Shared reversals provide an audit trail for release and deployment systems.
- Backups, editor history, and remote clones cover different failure modes than Git's object database.
- A small, explicit rollback is easier to review than an unexplained branch rewind.

## From the Field

A production fix is reverted on `main` after an outage. Someone suggests resetting `main` to the previous commit instead. That would rewrite the branch everyone already fetched and hide the corrective event from the timeline. A revert keeps both the failure and its response visible, while tests and incident notes explain why the inverse change is safe.

## Engineering Review

### What problem does this solve?

It provides state-specific ways to undo a mistake or recover a reachable commit without guessing at a destructive command.

### Why was it designed this way?

Git separates working-tree files, index entries, immutable commits, and movable refs, so each recovery tool targets a different layer.

### When should I use it?

Use `restore` for a scoped file state, reset for unpublished ref adjustments, revert for shared corrections, and reflog to locate recent local ref tips.

### When should I avoid it?

Avoid discarding tracked edits without inspection, rewriting published history, and treating reflog as guaranteed backup storage.

### How does this make me a better engineer?

It turns recovery into diagnosis, evidence preservation, and controlled change rather than panic-driven commands.

### How does this reduce waste?

Precise recovery preserves good work and avoids forcing teammates to repair rewritten shared history.

## Handbook Principle #33

> Recover by locating the last durable copy and changing the narrowest state necessary.

## Practical Observation

In a disposable repository, commit a file, change it, stage it, then run `git restore --staged -- file` and inspect both diffs. Commit another change, record its ID, and use `git reset --soft HEAD^` to observe what remains staged. Use `git reflog` to locate the former tip and create a `recovery/` branch at its explicit ID. Never run this sequence against this handbook's live branch.

## Looking Ahead

The safest correction depends on who has already seen the change. Chapter 34 moves from local commands to review, protected branches, and an explicit publication policy.

## References

- [Git restore](https://git-scm.com/docs/git-restore)
- [Git reset](https://git-scm.com/docs/git-reset)
- [Git revert](https://git-scm.com/docs/git-revert)
- [Git reflog](https://git-scm.com/docs/git-reflog)
