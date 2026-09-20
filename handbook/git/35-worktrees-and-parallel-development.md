# Chapter 35 — Worktrees and Parallel Development

Two tasks often need the same repository at once: a feature is waiting for review while an urgent fix needs a different branch. Switching branches in one dirty directory risks mixing changes. A second clone works, but duplicates setup and can obscure which local refs are shared. Git worktrees provide separate checked-out directories attached to one repository.

The central idea is:

> Give each active task its own working state while keeping shared history explicit.

## 1. One repository, multiple checked-out states

The main worktree and linked worktrees share most Git objects and refs. Each worktree has its own `HEAD`, index, and working files. A commit made on a branch in one worktree updates that shared branch ref and is visible from the others. An unstaged file edit stays in its own directory. Some metadata and configuration have subtleties; use `git worktree list` rather than assuming every `.git` path is a standalone object database.

Git normally prevents the same branch from being checked out in two worktrees at once. This is a safety feature: two independent indexes should not silently advance one branch. Use a different branch per worktree. A detached worktree can be useful for inspection, but give any new commits a branch before removing it.

## 2. Create a second task workspace

Run this only in a **disposable** repository whose parent directory has room for the exact sibling path `second-task`. Start in the primary worktree on `main`, with the desired base already present:

```bash
git status --short
git worktree list
git worktree add -b task/second ../second-task main
git worktree list
```

`-b` creates `task/second` from `main`; the final argument is the base, not a remote. Git checks out the new branch in `../second-task`. Move into that directory with your shell's `cd` command and check its state:

```bash
cd ../second-task
git status --short --branch
git branch --show-current
```

These relative paths assume the initial repository and `second-task` are siblings. On PowerShell, `cd ..\second-task` is the equivalent navigation. For a real project, choose an explicit new path that will not overlap existing user data. `git worktree add` will fail rather than silently overwrite an occupied path, but you should inspect it first.

## 3. Parallel work is isolated, not independent history

You can edit and test `task/second` while the primary worktree remains on `main` or another task branch. The files and index are separate, but commits and branches are shared. If you fetch in either worktree, remote-tracking refs update for the repository. If you delete a branch that another worktree has checked out, Git should reject it. Do not use worktrees to hide unrelated changes in one branch; make each task's commits coherent.

Dependencies can still interact. Two worktrees may share external resources such as a database, container name, port, build cache, or environment variable. Isolate those resources deliberately; Git only separates checkout state.

## 4. Stash is a short-lived parking place

`git stash push -m "pause for review"` stores tracked working-tree and index changes for later application. Untracked files are not included unless requested, for example with `-u`; ignored files require different handling. Inspect before and after:

```bash
git status --short
git stash push -m "pause for review"
git stash list
git stash show --stat stash@{0}
```

Only do this when the changes are understood and you intend to return to them soon. A stash is repository-local and its stack is shared across linked worktrees; it is easy to apply the wrong entry in the wrong place. It is not a remote backup or a durable task tracker. A small WIP commit on a private branch is often clearer for work that must survive days or be handed to someone else.

To resume, inspect the target branch and working tree, then use `git stash apply <verified-stash-ref>`. Applying leaves the stash entry in place; verify the resulting diff and tests before dropping that *specific* entry. `git stash pop` combines application and removal on success, which is convenient but gives less opportunity to inspect. Stash application can conflict, so do not assume it is a reversible pause button.

## 5. Retire a worktree without losing work

After `task/second` is integrated and no process uses its directory, move the shell back to the primary worktree. Confirm the linked worktree is clean, then remove the exact path:

```bash
git worktree list
git -C ../second-task status --short
git worktree remove ../second-task
git worktree list
```

`git worktree remove` refuses a dirty worktree by default. Treat that refusal as a chance to inspect, not an invitation to force removal. Removing a worktree removes its checked-out directory; the branch and committed objects remain. Once the branch is fully integrated and no longer needed, `git branch -d task/second` checks whether it is merged before deletion. If that check refuses, inspect the graph. Do not reflexively replace `-d` with `-D`.

If a worktree directory was moved or deleted outside Git, the repository's registration may become stale. `git worktree list` and the worktree documentation cover repair and pruning, but those maintenance operations are not part of normal task cleanup. Do not run them against unknown paths.

## Common Misconceptions

- “A worktree is a full clone.” It shares the repository's objects and most refs.
- “Two worktrees can safely edit one branch independently.” Git normally prohibits the duplicate checkout.
- “A stash is a durable backup.” It is local temporary state with easy-to-confuse entries.
- “Removing a worktree deletes its branch.” The branch remains until separately deleted.

## Core Computer Science Concept

Worktrees separate **mutable views over shared immutable data**. Each view has its own index and files, while branches point into a common object graph. That separation resembles multiple processes using one database: local workspace state is isolated, but shared references and external side effects still require coordination.

## Engineering Connections

- Parallel builds need separate output directories when generated files are not safely shareable.
- Multiple app instances may need unique ports, credentials, or database schemas.
- Review feedback can be addressed without disturbing a hotfix checkout.
- Clear branch ownership prevents accidental commits to the wrong task.

## From the Field

A developer has an unfinished migration in one working tree and needs to patch a production bug. They stash the migration, switch branches, and later apply the wrong stash over the hotfix. Separate worktrees would have made each task's working state visible, while a named WIP commit would have protected long-lived migration work. The lesson is to choose isolation that matches task duration and handoff needs.

## Engineering Review

### What problem does this solve?

It keeps concurrent tasks from contaminating one working tree while sharing the repository's commit history.

### Why was it designed this way?

Commits and refs can be shared, but each checked-out task needs its own `HEAD`, index, and files.

### When should I use it?

Use a linked worktree when two branches need active, independent edit-and-test cycles.

### When should I avoid it?

Avoid worktrees when external build or runtime resources cannot be isolated, and avoid using stashes as long-term project storage.

### How does this make me a better engineer?

It makes ownership of local state explicit and encourages deliberate cleanup after integration.

### How does this reduce waste?

It avoids repeated branch-switch friction, accidental mixed commits, and lost context when urgent work interrupts a feature.

## Handbook Principle #35

> Isolate each active task's mutable workspace, and coordinate every shared reference deliberately.

## Practical Observation

In a disposable repository, make a second worktree with the commands above. Edit a file in `second-task` without committing and confirm the primary worktree's `git status` remains clean. Commit in the second worktree and observe the branch in `git log --all` from the first. After integrating it, verify the linked worktree is clean and remove its exact directory with `git worktree remove`.

## Looking Ahead

Chapter 36 combines local state, remote synchronization, conflicts, review, rollback, and cleanup in one inspectable change lifecycle.

## References

- [Git worktree](https://git-scm.com/docs/git-worktree)
- [Git stash](https://git-scm.com/docs/git-stash)
