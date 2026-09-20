# Chapter 32 — Rebasing, Cherry-Picking, and History Rewriting

Merging preserves two lines of development. Sometimes a series of *unpublished* commits is easier to review after it is replayed onto a newer base or arranged into a clearer sequence. That convenience has a cost: replayed commits are new commits, even when their patches look identical.

The central idea is:

> Rewrite a private story to make it understandable; preserve a shared story so other people's references remain valid.

## 1. A commit has a position in a graph

A commit identifies its tree, parents, author information, message, and other metadata. Its object ID therefore depends on its parent. If `topic` starts at `B`, while `main` advances to `D`, the graph may look like this:

```text
A ← B ← C ← D   main
     \
      E ← F     topic
```

Rebasing `topic` onto `main` takes the changes introduced by `E` and `F` and replays them after `D`:

```text
A ← B ← C ← D   main
             \
              E' ← F'   topic
```

`E'` and `F'` are not renamed versions of the original commits. Their parents differ, so their object IDs differ. The original commits may remain reachable through a reflog for a while, but teammates who based work on them do not automatically follow the new branch tip.

## 2. Why replay instead of merge?

A linear sequence can make a small feature easier to read and can avoid a merge commit that only records synchronization. Rebasing can also help a topic branch test against the current base before review. It does **not** make integration conflicts disappear; it moves them to the replay step, possibly once per replayed commit.

Use a merge when preserving branch ancestry matters, when the branch is already shared, or when team policy calls for a merge commit. Do not choose rebase merely to make `git log --oneline` look tidy.

## 3. Rebase unpublished topic work

The following commands assume a clean working tree, a disposable repository, and a local `main` that already contains the base you want. Check first:

```bash
git status --short
git log --oneline --graph --decorate --all -n 12
git switch topic
git rebase main
```

Git finds commits unique to `topic`, moves the branch's starting point to `main`, and applies their changes in order. Inspect the result:

```bash
git status
git log --oneline --graph --decorate --all -n 12
git diff main...topic
```

`main...topic` compares the topic tip with its merge base against `main`; after a successful rebase, that base is ordinarily the current `main` tip. Run the relevant tests too. A successful replay proves the patches applied, not that the application still works.

If your goal is only to incorporate new `main` changes into an already shared branch, a normal merge may be safer. Ask what other branches, reviews, or deployment references already name the old commits.

## 4. Conflicts during replay

On a conflict, Git pauses at the commit whose patch could not be applied. The working tree and index expose the conflict. Resolve it as in [Chapter 31](31-merging-and-resolving-conflicts.md), then stage the resolved files and continue:

```bash
git status
git add path/to/resolved-file
git rebase --continue
```

To restore the branch to its pre-rebase state while the rebase is in progress:

```bash
git rebase --abort
```

`git rebase --skip` omits the current commit. That can silently omit needed behavior, so use it only after verifying the change is genuinely redundant. During a rebase, the labels “ours” and “theirs” can feel opposite to an ordinary merge: the checked-out side is the new base plus commits already replayed, while the other side is the commit being replayed. Inspect the actual file versions instead of relying on the labels.

## 5. Interactive rebase: edit the private narrative

An interactive rebase lets you reorder, reword, combine, or drop commits. For a branch with three unpublished commits on top of `main`:

```bash
git switch topic
git rebase -i main
```

Git opens an editor with a todo list. `pick` retains a commit, `reword` changes its message, and `squash` combines it with the preceding commit. The editor controls this operation; it is not a command to paste into a shell. Read the todo list and the resulting log before pushing. Reordering can introduce conflicts or dependency mistakes even if the final tree looks familiar.

Interactive rebase is useful for removing “fix typo” noise from private work or separating a mixed commit into a reviewable sequence. It is not a substitute for meaningful tests or for documenting a consequential design decision.

## 6. Cherry-pick selects a change, not an ancestry line

Suppose an independent fix on `release` should also appear on `main`. From the destination branch, cherry-pick the source commit:

```bash
git switch main
git cherry-pick <source-commit-id>
```

Git applies that commit's change and ordinarily creates a new commit on `main`. The histories now have separate commits with related changes; cherry-pick does not merge all prior ancestry. This is useful for a narrow backport, but repeated cherry-picks make it harder to see which branches contain equivalent fixes. Record the source ID in the message or review when traceability matters. Do not cherry-pick an arbitrary range without inspecting each change and its dependencies.

If a cherry-pick conflicts, resolve and stage, then `git cherry-pick --continue`; `git cherry-pick --abort` returns to the pre-operation state. Verify behavior on the destination branch, where surrounding code may differ.

## 7. The publication boundary

Before rewriting, distinguish *private* from *published* history. A branch already fetched by teammates or used as a review base is effectively shared even if it is not `main`. Rebasing it can require every downstream consumer to reconcile old and new histories. A force-push does not make that coordination disappear and can overwrite another person's remote update.

If a shared commit is wrong, prefer a follow-up fix, a merge, or a revert (covered in Chapter 33). Repository policy may permit coordinated rewriting of a feature branch, but that is an explicit team operation with communication and safeguards, not routine synchronization. Broad history surgery and filter tools are outside this chapter.

## Common Misconceptions

- “Rebase moves commits.” It replays changes into *new* commits and advances a ref.
- “Linear history means fewer conflicts.” Conflicts still occur, potentially at several replay steps.
- “Cherry-pick merges branches.” It selects changes from specified commits, not the whole ancestry.
- “A clean working tree makes rewriting shared history safe.” The risk is to other people's references, not only your local files.

## Core Computer Science Concept

History rewriting is a form of **immutable data transformation**. Existing commit objects are not edited; Git creates new objects and updates a mutable reference to point at the new graph. Distinguishing objects from refs explains both the usefulness of local rewrites and the danger of changing a shared ref.

## Engineering Connections

- A reviewable commit series can separate refactoring from behavior change, reducing reviewer cognitive load.
- A release backport needs its own tests because the destination branch is a different system state.
- CI results tied to old commit IDs do not automatically validate rewritten commits.
- Shared history is an interface other developers and automation may depend on.

## From the Field

A developer rebases a branch after a teammate has branched from it. The developer sees a clean linear log, but the teammate's branch still names the old commits and a later pull request displays duplicate-looking changes. The problem is not a bad rebase command; it is an unrecognized publication boundary. Agree on a shared base or merge the branches before rewriting either history.

## Engineering Review

### What problem does this solve?

It lets you replay or select changes so private history is easier to integrate and review.

### Why was it designed this way?

Commits are immutable objects; making a new sequence requires new objects and a ref update rather than editing old commits in place.

### When should I use it?

Rebase unpublished topic work onto a newer base; use cherry-pick for a deliberate, narrow transfer such as a backport.

### When should I avoid it?

Avoid rewriting shared commits without an explicit team plan, and avoid skipping replayed commits without checking their effects.

### How does this make me a better engineer?

It makes you reason about graph identity, reviewability, and the coordination cost of changing history.

### How does this reduce waste?

A coherent private series reduces review noise, while respecting the publication boundary prevents duplicate work and recovery effort.

## Handbook Principle #32

> Reorganize history only while you own its references; once others depend on them, integrate with visible new commits.

## Practical Observation

In a disposable repository, create `main` and a two-commit `topic`, advance `main` independently, and record `git rev-parse topic` before and after `git rebase main`. Compare `git log --graph --all` and the final diff. Confirm that the topic's behavior remains while its commit IDs change. Never run this exercise on this handbook's live history.

## Looking Ahead

Rebase changes commit identity intentionally. Chapter 33 separates that from recovering a mistaken working-tree edit, staging decision, local commit, or published change.

## References

- [Git rebase](https://git-scm.com/docs/git-rebase)
- [Git cherry-pick](https://git-scm.com/docs/git-cherry-pick)
- [Pro Git: Rebasing](https://git-scm.com/book/en/v2/Git-Branching-Rebasing)
