# Chapter 30 — Remotes, Tracking, Fetching, and Pushing

Git is distributed: each repository has its own objects and references. Collaboration requires transferring objects and deciding which local and remote names should advance.

The central idea is:

> Fetch to observe another repository, integrate by an explicit local choice, and push only after verifying the remote ref you intend to update.

## 1. A remote name is configuration

`origin` is a conventional short name, not a special authority built into Git. Inspect configured destinations:

```bash
git remote -v
git remote get-url origin
```

Fetch and push URLs can differ. Before a consequential push, verify both the repository and branch destination. A developer can have multiple remotes, forks, mirrors, and read-only upstreams.

Authentication proves that an identity may access a remote endpoint; it does not mean the proposed content has been reviewed or should be merged.

## 2. Separate three kinds of refs

```text
refs/heads/main             your local branch
refs/remotes/origin/main    your last fetched view of origin's main
origin's refs/heads/main    branch in the other repository
```

The local remote-tracking ref is a record of what Git learned at the last fetch or relevant push. It is not a live network query. Someone may have advanced the remote after your last contact.

This distinction makes “my local `origin/main` is current” a time-bound statement.

## 3. Fetch observes without integrating

```bash
git fetch origin
git log --oneline --graph --decorate --all -12
git log --oneline main..origin/main
```

Fetch transfers objects and updates configured remote-tracking refs. It normally does not change the current branch, index, or working tree. It can update local tags under documented rules and repository configuration, so inspect the refspec when exact behavior matters.

Fetch first when you need to compare before deciding how to integrate.

## 4. Upstream is a relationship, not ownership

A local branch can be configured to track a remote branch:

```bash
git branch -vv
git status --short --branch
```

The upstream relationship supports ahead/behind displays and argument-less pull or push behavior under configuration. It does not make the local branch identical to the remote branch.

When first publishing a topic branch:

```bash
git push -u origin topic/example
```

`-u` records upstream tracking for the successfully pushed branch. In a shared repository, use the team's branch and review policy rather than publishing arbitrary names to a protected namespace.

## 5. Ahead and behind are graph counts

If local `main` is ahead by two and behind by one, the histories have diverged:

```text
         L1 ← L2   local main
        /
common
        \
         R1        origin/main
```

The counts refer to commits reachable from one tip but not the other. They do not tell whether the content changes conflict or whether one side is “better.”

Inspect both directions:

```bash
git log --oneline origin/main..main
git log --oneline main..origin/main
```

## 6. Push updates a remote ref

An explicit push names the source and destination:

```bash
git push origin HEAD:refs/heads/topic/example
```

This asks the remote to advance `topic/example` to the current commit. A push may fail because of network errors, authentication, server policy, required checks, or a non-fast-forward update. A successful local commit is not evidence of a successful push.

Verify the result through a fresh fetch, remote-ref query, or hosting service response when the distinction matters.

## 7. Fast-forward protects history from accidental replacement

Ordinarily, Git rejects a push that would replace a remote branch tip with a commit that does not contain it as an ancestor. The rejection means the update is not a simple advance:

```text
remote: A ← B ← C
local:  A ← B ← D
```

The correct next step is to fetch and inspect, then merge, rebase unpublished local work, or coordinate. Do not reflexively force push. `--force-with-lease` adds an expected-ref check but still rewrites a remote branch and has caveats if background fetches update the local remote-tracking view. A team policy must authorize that operation.

## 8. `pull` composes fetch and integration

`git pull` first fetches and then integrates the selected remote branch into the current branch. The integration may be fast-forward, merge, or rebase depending on explicit options, configuration, Git version, and situation.

For a branch that must not create a merge commit or rewrite local history:

```bash
git pull --ff-only
```

This succeeds only when the local branch can fast-forward. When it refuses, inspect divergence and choose an integration policy deliberately. Do not rely on an unspecified `pull` default in a shared runbook.

## 9. A local bare remote is enough to learn

In a disposable directory:

```bash
practice=$(mktemp -d)
git init -q --bare "$practice/remote.git"
git clone -q "$practice/remote.git" "$practice/author"
cd -- "$practice/author" || exit 1
git config user.name 'Practice Author'
git config user.email 'practice@example.invalid'
printf '%s\n' 'hello' > README.md
git add -- README.md
git commit -qm 'Add greeting'
git push -u origin HEAD:refs/heads/main
```

The bare repository has no ordinary checked-out working tree. It is a useful local stand-in for a shared remote. Since an empty bare repository's default `HEAD` may still name a different branch, explicitly select `main` when cloning again or set the bare repository's symbolic `HEAD` before relying on a default checkout.

## 10. Remote tags and deletions are separate choices

Creating a local tag does not necessarily publish it with an ordinary branch push. Pushing all tags, deleting remote branches, and pruning stale remote-tracking refs are distinct operations with shared consequences.

Use explicit commands only after identifying the exact ref and retention policy. A stale remote-tracking ref is not proof the server still has the branch; a deleted remote branch is not proof every clone has forgotten its commits.

## 11. Common misconceptions

### “`origin/main` is the server's live state”

It is your locally recorded view from a prior fetch or push.

### “`fetch` changes my files”

Normal fetch updates local object and tracking-ref state, not the current worktree or branch.

### “`pull` is one indivisible operation”

It composes fetching with an integration decision.

### “A rejected push means Git lost my commits”

They remain local; the remote ref was not advanced.

### “A successful push means the change is merged”

Publishing a topic branch and integrating it into a protected base branch are different events.

## Core Computer Science Concept

Remote synchronization is **replicated state with explicit ref updates**. Each repository owns local knowledge; fetch updates a local observation, while push proposes a write to another authority. Ahead/behind counts are graph relationships, not wall-clock freshness guarantees.

## Engineering Connections

- CI often checks out a specific pushed commit while a branch continues moving.
- Protected branches can reject a technically valid Git push as a policy decision.
- Mirrors and forks demonstrate that a remote is another repository, not necessarily a single central truth.
- Distributed systems face the same distinction between cached observations and current authoritative state.

## From the Field

An engineer sees `origin/main` at the same commit as local `main` and pushes a release change. The server rejects it because another teammate advanced `main` after the engineer's last fetch. The local tracking ref was an old observation, not a live lock on the remote.

## Engineering Review

### What problem does this solve?

It makes repository collaboration possible while preserving explicit ownership of local and remote references.

### Why was it designed this way?

Git keeps local work independent and transfers objects and ref updates only when requested.

### When should I use it?

Fetch before integrating others' work; push after verifying branch, destination, history, and policy.

### When should I avoid it?

Avoid force-pushing shared history or relying on a remote-tracking ref as a continuously current server view.

### How does this make me a better engineer?

It teaches cached-state reasoning, explicit synchronization, and separation of publication from integration.

### How does this reduce waste?

Intentional fetch–inspect–integrate–push loops prevent rejected pushes, accidental branch updates, and confused collaboration.

## Handbook Principle #30

> Fetch to learn, integrate to reconcile, and push to publish; verify the exact ref at every boundary.

## Practical Observation

Run the bare-remote fixture from Section 9. Clone a second working repository with `git clone -b main "$practice/remote.git" "$practice/reader"`. Make a new commit in `author` and push it. In `reader`, compare `git log main` and `git log origin/main` before and after `git fetch origin`. Explain what changed without using `git pull`.

## Looking Ahead

Once two histories diverge, a team must integrate them. Chapter 31 explains fast-forward and three-way merges, including the index state left by conflicts.

## References

- [Git fetch](https://git-scm.com/docs/git-fetch)
- [Git push](https://git-scm.com/docs/git-push)
- [Git pull](https://git-scm.com/docs/git-pull)
