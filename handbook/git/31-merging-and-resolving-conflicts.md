# Chapter 31 — Merging and Resolving Conflicts

Two branches can evolve from one commit into different states. Merging reconciles their histories and content while preserving their ancestry.

The central idea is:

> A merge is a graph operation plus a content decision; Git can combine nonconflicting edits, but only a person or an explicit policy can resolve competing intent.

## 1. Start from the shared ancestor

Suppose `main` and `topic` both descend from commit `B`:

```text
      C ← D   main
     /
A ← B
     \
      E ← F   topic
```

The merge base is a best common ancestor used as a comparison point. For a common simple case:

```bash
git merge-base main topic
```

Git compares changes from that base toward each tip and attempts to construct a combined tree. Complex graphs can have multiple best merge bases, so the simple drawing is a mental model, not every implementation detail.

## 2. Fast-forward is only a ref advance

If `main` has not changed since `topic` branched, the topic tip already contains `main` as an ancestor:

```text
A ← B   main
     ← C ← D   topic
```

Merging `topic` into `main` can simply move `main` to `D`. No new merge commit is required. This is a fast-forward.

Use `git merge --ff-only topic` when the policy requires this shape and should refuse divergence rather than choosing another integration strategy implicitly.

## 3. A true merge records both parents

When both branches advanced, a successful normal merge creates a commit with two parents:

```text
      C ← D ──┐
     /        ↓
A ← B         M   main
     \        ↑
      E ← F ──┘   topic
```

`M` records one resolved tree and both lines of ancestry. A merge commit is not just a marker; its tree contains the combined result. Inspect its parents:

```bash
git show --no-patch --format='%h %p %s' HEAD
```

For this reason, the merge result needs tests even when Git reports no textual conflict. A syntactically clean merge can still combine incompatible behavior.

## 4. Conflict means automatic reconciliation stopped

A conflict occurs when Git cannot choose a single result under the selected merge strategy. It may involve the same lines, a delete-versus-edit choice, renames, file types, or other competing changes.

No conflict does **not** prove semantic compatibility. Conversely, a conflict is not a failure of Git; it is a request for an explicit decision.

Start with:

```bash
git status
git diff --name-only --diff-filter=U
```

The current branch remains at its pre-merge tip until the merge is completed. The other tip is recorded in merge state such as `MERGE_HEAD`.

## 5. Understand the index's three stages

For an unmerged path, Git may hold:

```text
stage 1  merge-base version
stage 2  ours: current HEAD side
stage 3  theirs: merged-in side
```

Inspect them without overwriting the working file:

```bash
git ls-files -u -- config.txt
git show :1:config.txt
git show :2:config.txt
git show :3:config.txt
```

These meanings apply to an ordinary merge from the current branch. During rebase or other replay operations, “ours” and “theirs” can feel reversed relative to a developer's original branch; identify the active operation before choosing sides.

## 6. Conflict markers are evidence, not the answer

A textual conflict can appear as:

```text
<<<<<<< HEAD
mode=stable
=======
mode=experimental
>>>>>>> topic
```

The resolution might choose one side, combine both, or create entirely new content. Deleting marker lines without understanding behavior merely silences the conflict signal.

After editing, validate the full file. Search for remaining marker syntax, but be aware legitimate files can contain similar strings.

## 7. Complete the merge deliberately

When a path is resolved:

```bash
git add -- config.txt
git status --short
git diff --cached --check
git diff --cached
git merge --continue
```

Staging the resolved path replaces its unmerged index entries with the chosen content. `git merge --continue` completes an in-progress merge, usually invoking an editor for the merge message. `git commit` is another documented completion route.

Afterward inspect the graph and run tests relevant to the combined behavior.

## 8. Abort is a controlled retreat

If the merge should not continue:

```bash
git merge --abort
```

Git attempts to restore the pre-merge state. This is most reliable when the operation began with a clean working tree. Existing uncommitted changes, especially if further edited during the merge, may not be perfectly reconstructed.

Do not use `git reset --hard` as a generic conflict escape. It discards local changes and has a different scope.

## 9. A disposable conflict exercise

In Bash, start outside this handbook repository:

```bash
practice=$(mktemp -d)
cd -- "$practice" || exit 1
git init -q demo
cd demo || exit 1
git config user.name 'Practice Author'
git config user.email 'practice@example.invalid'
printf '%s\n' 'mode=base' > config.txt
git add -- config.txt
git commit -qm 'Add base configuration'
git branch -M main

git switch -c topic
printf '%s\n' 'mode=topic' > config.txt
git commit -qam 'Change topic mode'

git switch main
printf '%s\n' 'mode=main' > config.txt
git commit -qam 'Change main mode'
git merge topic
```

The last command is expected to stop with a conflict. Inspect all three stages. For this exercise, decide that neither setting is valid alone and write an agreed value:

```bash
printf '%s\n' 'mode=reviewed' > config.txt
git add -- config.txt
git -c core.editor=true merge --continue
git log --oneline --graph --all
```

`core.editor=true` suppresses an interactive editor only for this disposable example; a real merge message deserves review.

## 10. Common misconceptions

### “A fast-forward is a merge commit”

It advances a reference without creating a new commit.

### “No conflict means the result works”

Git can combine text cleanly while the application behavior becomes invalid.

### “Conflict markers tell me which side is correct”

They display alternatives, not the business or technical decision.

### “I edited the file, so the merge is complete”

The resolved content must be staged, and the merge must be completed and verified.

### “Abort always reconstructs arbitrary dirty state”

Uncommitted changes present before or modified during a merge can make restoration difficult.

## Core Computer Science Concept

Three-way merge is **reconciliation against a common baseline**. Each side's delta is interpreted relative to that baseline; the resulting tree is a new state that must satisfy invariants neither branch could check alone.

## Engineering Connections

- Database schema changes on separate branches can merge cleanly yet break deployed data.
- CI must test the integrated result, not only each branch independently.
- Conflict resolution is a design decision that should be reviewable in the final diff.
- Merge commits preserve evidence of where development histories joined.

## From the Field

Two feature branches add different configuration flags on separate lines, so Git merges without conflict. At runtime both flags enable mutually exclusive code paths. The root problem is assuming textual merge success proves semantic compatibility. Integration tests are required at the combined state.

## Engineering Review

### What problem does this solve?

It combines diverged histories while preserving ancestry and requiring explicit decisions where automatic content merging is insufficient.

### Why was it designed this way?

Comparing both sides to a shared ancestor lets Git combine independent changes without discarding either history.

### When should I use it?

Use merges when preserving both lines of history is valuable or team policy favors merge commits; use fast-forward-only when divergence should be rejected.

### When should I avoid it?

Avoid beginning a complex merge in an unexplained dirty tree or treating an auto-merge as a substitute for testing.

### How does this make me a better engineer?

It teaches graph reasoning, explicit conflict decisions, and verification of combined behavior.

### How does this reduce waste?

Understanding merge state makes conflicts manageable and prevents destructive “start over” commands.

## Handbook Principle #31

> Merge ancestry and content separately in your mind, then test the combined state as a new product rather than assuming Git proved compatibility.

## Practical Observation

Run the exercise in Section 9. Before resolving, record `git merge-base main topic`, the three indexed versions, and `git status --short`. After completing, inspect `git rev-list --parents -n 1 HEAD` and explain why the merge commit has two parents.

## Looking Ahead

Merging retains the divergent graph. Chapter 32 examines replaying commits onto a different base and the new identities that history rewriting creates.

## References

- [Git merge](https://git-scm.com/docs/git-merge)
- [Git merge-base](https://git-scm.com/docs/git-merge-base)
