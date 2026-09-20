# Chapter 26 — Staging and Making Coherent Commits

The index allows a commit to express one coherent change even when the working tree contains several unfinished ideas. The discipline is to review the proposed snapshot, not merely to run `git add` and hope.

The central idea is:

> A good commit is an intentional state transition whose content, reason, and verification can be understood independently.

## 1. Commit quality begins before `git commit`

A commit should make one reviewable claim: “this change does X for reason Y.” It may touch several files when those files form one behavior. Splitting by filename alone can produce commits that cannot build or be reviewed independently.

Conversely, a single commit containing a bug fix, unrelated formatting, generated artifacts, and experimental notes obscures intent. The index is where that boundary is enforced.

## 2. Configure identity at the right scope

Git commits record author and committer identities. In a practice repository, set local values without changing global configuration:

```bash
git config --local user.name 'Practice Author'
git config --local user.email 'practice@example.invalid'
git config --show-origin --get user.email
```

Local, global, and system configuration can all contribute effective values. Inspect the origin of a setting when the identity is surprising. An email string is metadata, not proof of authentication or permission to push.

## 3. Stage explicit paths

In a mixed working tree:

```bash
git status --short
git add -- src/parser.py tests/test_parser.py
git diff --cached --stat
git diff --cached --check
git diff --cached
```

The `--` separates options from pathspecs. Explicit paths communicate scope and reduce accidental inclusion of unrelated files. Always inspect the full staged diff before committing consequential changes; a stat is only a summary.

`git add` updates the index to the file content at that moment. If you edit a staged file again, inspect and stage the new version deliberately.

## 4. Stage part of a file when changes are independent

Interactive staging can select hunks:

```bash
git add -p -- src/parser.py
```

This is valuable when one file contains a focused fix plus unrelated cleanup. Review each hunk's context and resulting staged file. A hunk selected in isolation may depend on an unselected import, declaration, or test change.

Partial staging is a preparation tool, not a substitute for maintaining compilable and testable commits.

## 5. New, modified, and deleted paths need attention

`git status --short` reveals untracked files, staged additions, modified tracked files, and deletions. `git add -- path` can stage a deletion of a tracked path as well as new content at a path. A broad `git add -A` stages additions, modifications, and deletions under its pathspec scope.

Before a broad add, inspect generated outputs, credentials, editor files, and unrelated user changes. The fact that a path is visible in the working tree does not mean it belongs in history.

Chapter 28 develops ignore and content policy; the immediate rule is to review every new path.

## 6. A normal commit records the index

After reviewing the staged snapshot:

```bash
git commit -m 'Fix parser handling of empty fields'
git show --stat --oneline HEAD
git status --short
```

An ordinary `git commit` without path operands creates a commit from the index. The working tree may still contain unstaged changes. `git status` after the commit is part of completion, not an optional extra.

`git commit -a` has a different selection rule: it stages tracked modified and deleted paths but does not add new untracked files. It can be convenient only when that complete tracked-file scope is intended.

## 7. Write messages for future readers

A useful subject describes the behavior change in the imperative mood or another consistent repository convention:

```text
Reject malformed request headers
```

The body, when needed, explains why, tradeoffs, compatibility concerns, and migration impact. The diff usually shows *what* changed; the message should preserve the decision that may not be obvious from the code.

Avoid messages such as `fix`, `updates`, or `work`. They impose investigation cost on every future reader of `log`, `blame`, release notes, or incident review.

## 8. Validate the actual snapshot

Running tests before staging is useful, but the staged snapshot may differ from the tested working tree. For a critical commit, inspect the cached diff and consider testing a clean checkout or worktree of the resulting commit.

At minimum:

```bash
git diff --cached --check
git diff --cached
git commit -m 'Describe the change'
git show --check --stat HEAD
```

The commands verify whitespace and recorded content; they do not prove functional correctness. Tests must match the project's risk and build contract.

## 9. Amend only across a clear publication boundary

If a local, unpublished commit has an obvious omission:

```bash
git add -- missing-test.py
git commit --amend --no-edit
```

Amend creates a new commit object with a new identity. If the old commit has been pushed or fetched by others, rewriting it changes the relationship they built upon. Prefer a new corrective commit unless the team explicitly coordinates the rewrite.

The safe question is not “Can Git amend?” It is “Who may already depend on this commit ID?”

## 10. Avoid accidental hooks and signing surprises

Repositories may run hooks before a commit is accepted. Git configuration may require signing. A hook failure or signing prompt is a workflow event, not a reason to disable validation blindly.

Inspect the exact error, understand the project policy, and fix the underlying issue. Some hooks are local and optional, while server-side checks may enforce separate requirements after pushing.

## 11. An independent two-commit exercise

In a disposable repository with an initial commit, make two unrelated changes:

```bash
printf '%s\n' 'parser behavior' > parser.txt
printf '%s\n' 'editor scratch' > scratch.txt
git status --short
git add -- parser.txt
git diff --cached --name-only
git commit -m 'Document parser behavior'
git status --short
```

The first commit should contain `parser.txt` only. `scratch.txt` remains untracked. Do not assume the scratch file is safe to delete merely because it was not committed; it still belongs to whoever created it.

## 12. Common misconceptions

### “One commit means one file”

One coherent behavior can require source, tests, documentation, and migration files together.

### “`git add .` is always harmless”

It can stage more than intended. Scope and inspect before committing.

### “A successful commit means the working tree is clean”

Unstaged and untracked work may remain.

### “Amending only changes the message”

Even a message-only amend creates a new commit identity.

### “The author email authenticates the author”

Commit metadata is not the same as push authentication or cryptographic signing.

## Core Computer Science Concept

The index is a **transaction-preparation boundary**: select a coherent candidate state, validate it, then make that state durable as a new commit. The analogy is useful but incomplete—Git does not automatically guarantee application tests, external consistency, or remote replication.

## Engineering Connections

- Focused commits make code review and regression diagnosis cheaper.
- CI tests exact commits; uncommitted local context is unavailable to it.
- Release notes and `git bisect` work better when commits express independent meaningful steps.
- Signing and hooks add provenance or policy, but cannot replace careful content review.

## From the Field

A developer stages source code, runs tests, then edits a test fixture and commits without restaging it. The local test passed against the working tree, but the recorded commit lacks the updated fixture. The repair is to compare index and working tree and verify the commit that CI will actually receive.

## Engineering Review

### What problem does this solve?

It turns a mixed workspace into focused, reviewable recorded changes.

### Why was it designed this way?

The index lets a developer choose the next snapshot separately from ongoing edits.

### When should I use it?

Use explicit staging and staged-diff review for every meaningful commit, especially in a dirty or shared workspace.

### When should I avoid it?

Avoid splitting changes so finely that intermediate commits are misleading or unusable; coherence matters more than minimum size.

### How does this make me a better engineer?

It teaches change isolation, evidence-based review, and careful publication boundaries.

### How does this reduce waste?

Focused commits accelerate review, rollback, blame investigation, and future maintenance.

## Handbook Principle #26

> Stage by intent, inspect the exact proposed snapshot, and publish a commit whose message explains the reason for that state.

## Practical Observation

Run Section 11 in a disposable repository. After the first commit, compare `git show --name-only --format= HEAD` with `git status --short`. Explain why one lists `parser.txt` and the other lists `scratch.txt`.

## Looking Ahead

Chapter 27 reads commits and differences as evidence to answer when and why a behavior changed.

## References

- [Git add](https://git-scm.com/docs/git-add)
- [Git commit](https://git-scm.com/docs/git-commit)
