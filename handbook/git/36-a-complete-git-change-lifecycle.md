# Chapter 36 — A Complete Git Change Lifecycle

A Git command is meaningful only in the state where it runs. This exercise follows one change from local work through a simulated review, integration, and rollback. It uses a temporary bare repository as `origin` and two disposable clones. No GitHub account, hosted PR, or change to this handbook is involved.

The central idea is:

> At every transition, inspect the working state, the proposed diff, the commit graph, and the recovery path.

## 1. Map the participants and boundaries

The exercise has three repositories:

```text
temporary directory/
├── remote.git/   bare shared repository; no working tree
├── author/       feature branch and conflict resolution
└── reviewer/     second clone, base change, integration, rollback
```

The bare repository stands in for a remote, but it does not provide pull requests, branch protection, or CI. The reviewer clone stands in for another developer and the integration operator. All commands below use a POSIX-compatible shell (Git Bash on Windows, or a typical macOS/Linux shell). Run them from a scratch location, **not** inside this handbook or any other live repository. The shell variable `lab_dir` points to the temporary directory created by `mktemp -d`; save its printed path if you want to inspect the result later.

## 2. Create a shared starting point

```bash
lab_dir=$(mktemp -d)
printf 'Lab: %s\n' "$lab_dir"
cd "$lab_dir"
git init --bare remote.git
git --git-dir=remote.git symbolic-ref HEAD refs/heads/main
git init -b main author
git -C author config user.name "Lab Author"
git -C author config user.email "author@example.invalid"
printf 'mode=base\n' > author/config.txt
git -C author add config.txt
git -C author commit -m "Add baseline configuration"
git -C author remote add origin ../remote.git
git -C author push -u origin main
git clone remote.git reviewer
git -C reviewer config user.name "Lab Reviewer"
git -C reviewer config user.email "reviewer@example.invalid"
```

The bare repository stores refs and objects, not checked-out files. `main` exists in both clones after the push and clone. The `.invalid` email domain is deliberately non-deliverable lab identity. Inspect the baseline before proceeding:

```bash
git -C author status --short --branch
git -C reviewer log --oneline --decorate -n 3
git -C reviewer remote -v
```

## 3. Author a focused change

The author makes a feature branch and one coherent commit:

```bash
git -C author switch -c feature/safe-mode
printf 'mode=feature\n' > author/config.txt
git -C author diff
git -C author add config.txt
git -C author diff --staged
git -C author commit -m "Set feature mode"
git -C author push -u origin feature/safe-mode
```

The first diff compares working tree with index; the staged diff shows the proposed commit. The push publishes the branch to the *local lab remote*, making its commits shared with the reviewer clone. In a hosted project this is where a draft PR and checks could be opened; this lab does not create one.

## 4. Let the base advance independently

The reviewer changes the same line on `main` and publishes it:

```bash
printf 'mode=reviewer\n' > reviewer/config.txt
git -C reviewer add config.txt
git -C reviewer commit -m "Set reviewer mode on main"
git -C reviewer push origin main
git -C author fetch origin
git -C author log --oneline --graph --decorate --all -n 8
```

The two branch tips now diverge from the baseline. Fetch updates `author`'s `origin/main` but does not alter the author's feature working tree. The graph should show two children of the baseline commit.

## 5. Resolve a deliberate conflict

The author integrates the updated base into the feature branch:

```bash
git -C author merge origin/main
```

This command is **expected to stop with a conflict** in `config.txt`. Do not interpret its nonzero exit as a failed lab. Inspect before resolving:

```bash
git -C author status --short
git -C author ls-files -u
git -C author show :1:config.txt
git -C author show :2:config.txt
git -C author show :3:config.txt
```

Stage 1 is the shared baseline, stage 2 is the checked-out feature side, and stage 3 is the incoming `origin/main` side for this merge. The engineer decides that `mode=integrated` is the intended combined behavior. This is a *product decision*, not a value Git can infer:

```bash
printf 'mode=integrated\n' > author/config.txt
git -C author add config.txt
git -C author diff --cached --check
git -C author commit -m "Merge main and reconcile mode"
git -C author grep -n '^mode=integrated$' -- config.txt
git -C author push origin feature/safe-mode
```

Inspect the merge commit's two parents with `git -C author rev-list --parents -n 1 HEAD`. If the chosen integrated value were wrong, the conflict would still be textually resolved; a test or review must catch the semantic mistake.

## 6. Review the candidate, then integrate

The reviewer fetches the updated branch and inspects what it proposes relative to the current base:

```bash
git -C reviewer fetch origin
git -C reviewer log --oneline --graph --decorate --all -n 10
git -C reviewer diff --stat main...origin/feature/safe-mode
git -C reviewer diff main...origin/feature/safe-mode
git -C reviewer show origin/feature/safe-mode:config.txt
```

The proposed final diff should change `mode=reviewer` to `mode=integrated`. In a real PR, reviewers would also consider tests, requirements, and deployment effects. Here the reviewer chooses a squash integration to put one logical feature commit on `main`:

```bash
git -C reviewer status --short
git -C reviewer merge --squash origin/feature/safe-mode
git -C reviewer diff --staged
git -C reviewer commit -m "Integrate safe mode feature"
git -C reviewer grep -n '^mode=integrated$' -- config.txt
git -C reviewer push origin main
```

`--squash` stages the combined change but does not create a merge commit. The commit made afterward has one parent. The feature branch's merge commit remains on its branch and is not an ancestor of the new squash commit. Compare the graph and IDs; similar trees do not imply identical ancestry.

## 7. Practice a visible rollback

Assume post-integration validation finds that the feature behavior is unsafe. Since the new squash commit is already published to the lab's `main`, correct it with a new revert commit rather than resetting `main`:

```bash
git -C reviewer log --oneline -n 3
git -C reviewer revert --no-edit HEAD
git -C reviewer grep -n '^mode=reviewer$' -- config.txt
git -C reviewer log --oneline --graph --decorate -n 5
git -C reviewer push origin main
```

The revert is straightforward here because the squash integration produced a single-parent commit. Reverting the feature branch's merge commit would require choosing a mainline parent and would have different future merge consequences. The rollback is a deliberate lab scenario, not a step every successful change should take.

## 8. Verify the final state

```bash
git -C author fetch origin
git -C reviewer status --short --branch
git -C author status --short --branch
git -C reviewer log --oneline --graph --decorate --all -n 12
git -C reviewer diff origin/main main
git --git-dir=remote.git rev-parse refs/heads/main
git -C reviewer rev-parse HEAD
```

The last two IDs should match. `reviewer` should be clean and aligned with `origin/main`; the author feature branch should still contain the integrated value, while its fetched `origin/main` reflects the rollback. That difference is expected. The lab directory is the only disposable target; inspect its printed absolute path before removing it with your file manager or a carefully scoped shell operation. Do not apply broad recursive cleanup commands from this chapter to an arbitrary workspace.

## 9. What this lab did not prove

This exercise tested command mechanics and graph reasoning. It did not create a hosted PR, enforce branch protection, run CI, verify application behavior, or publish a production release. A local bare remote can simulate exchange of Git objects and refs but not the surrounding governance. The same restraint applies to rollback: a successful Git revert says the inverse patch applied, not that the service is healthy.

## Core Computer Science Concept

The lifecycle is a series of **state transitions with observable invariants**. Before each write, inspect the current state; after it, verify the intended ref, index, tree, and external effect. The commit graph is immutable evidence, while refs and working trees are mutable views of that evidence.

## Engineering Connections

- Review and CI should validate the candidate that will actually be integrated.
- A conflict resolution is a new behavior choice requiring tests.
- A published rollback preserves an audit trail and coordinates cleanly with other clones.
- Disposable environments make risky learning repeatable without risking production repositories.

## From the Field

A team approves a feature branch, resolves a late merge conflict, and immediately merges without reviewing the resolution. The conflict was syntactically settled but changed a default flag. The incident is not explained by Git “getting the merge wrong”; the team's review boundary ended before the final tree existed. Review and test the post-conflict candidate, then publish that exact state.

## Engineering Review

### What problem does this solve?

It joins the individual Git concepts into one inspectable path from proposed change to shared integration and recovery.

### Why was it designed this way?

Git records immutable snapshots and mutable refs, while collaboration requires explicit decisions at branch, review, merge, and rollback boundaries.

### When should I use it?

Use this lab to rehearse a workflow safely; adapt its checks and integration method to the policy of a real repository.

### When should I avoid it?

Do not run its setup or deliberate conflict on a live project, and do not mistake the local bare remote for hosted review or CI.

### How does this make me a better engineer?

It builds the habit of predicting and verifying state transitions instead of memorizing isolated commands.

### How does this reduce waste?

It catches mistakes at the smallest boundary and gives a known recovery path before a change affects others.

## Handbook Principle #36

> Treat every Git operation as a state transition: predict it, inspect it, verify it, and know how to recover.

## Practical Observation

Run the lab once as written in a disposable directory. Then draw the commit graph just before the conflict, after the feature merge, after the squash integration, and after the revert. At each point, name the value in `config.txt` for the author feature, reviewer `main`, and bare remote `main`. If any answer surprises you, use `git show`, `git status`, and `git log --graph` to locate the transition you misunderstood.

## Looking Ahead

Part III established a model for recording, sharing, integrating, and recovering changes. Later parts apply the same discipline to filesystems, operating systems, networks, and software delivery: identify state and ownership, observe the boundary, then change one thing with a way back.

## References

- [Git merge](https://git-scm.com/docs/git-merge)
- [Git fetch](https://git-scm.com/docs/git-fetch)
- [Git revert](https://git-scm.com/docs/git-revert)
- [GitHub: Pull request merges](https://docs.github.com/en/pull-requests/reference/pull-request-merges)
