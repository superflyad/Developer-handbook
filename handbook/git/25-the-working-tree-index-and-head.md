# Chapter 25 — The Working Tree, Index, and `HEAD`

A commit records one tree, but development happens between commits. Git keeps the current files, the proposed next snapshot, and the current commit conceptually separate.

The central idea is:

> Before changing Git state, identify whether the content lives in the working tree, the index, or the commit selected by `HEAD`.

## 1. Three states, three questions

```text
HEAD commit  → what is recorded now?
index        → what would the next ordinary commit contain?
working tree → what is present for editors and tools now?
```

The **index**, often called the staging area, is not merely a list of filenames. It records the content and metadata Git is preparing for the next tree. A file may have one version in `HEAD`, another in the index, and a third in the working tree.

`HEAD` normally points through the current branch to a commit. In a detached state it points directly to a commit. It is not a synonym for the current files.

## 2. Differences are relative to a baseline

`git status` reports at least three relevant classes:

- differences between `HEAD` and the index: staged changes,
- differences between the index and the working tree: unstaged changes,
- paths present in the working tree but not tracked in the index: untracked files.

In a disposable repository:

```bash
git status --short
git diff
git diff --cached
```

`git diff` without a revision normally compares working tree to index. `git diff --cached` compares index to `HEAD`. `git diff HEAD` compares working tree to `HEAD` for tracked paths, combining staged and unstaged differences. New untracked files are not shown by these ordinary diffs until staged or otherwise included.

## 3. A single file can be both staged and unstaged

Suppose `note.txt` contains `one` in `HEAD`:

```bash
printf '%s\n' 'two' > note.txt
git add -- note.txt
printf '%s\n' 'three' > note.txt
```

Now:

```text
HEAD:         one
index:        two
working tree: three
```

The next ordinary commit would contain `two`, not `three`. Running `git add` copied the then-current content into the index; later edits did not automatically update the staged version.

Inspect both deltas:

```bash
git diff --cached -- note.txt
git diff -- note.txt
```

## 4. Reading short status correctly

`git status --short` normally presents two columns for tracked changes:

```text
XY path
```

Outside conflicts, `X` describes index versus `HEAD`; `Y` describes working tree versus index. For example, `MM note.txt` means a staged modification plus another unstaged modification. `?? new.txt` means untracked. Conflict states have different two-column meanings; Chapter 31 covers them.

For scripts, use Git's porcelain status formats rather than parsing the human long format. For pathnames with unusual characters, prefer a NUL-delimited machine interface.

## 5. Tracked is a relationship with the index

A tracked path has an entry in the index. Editing or deleting it changes the working tree relative to that entry. An untracked path is not yet represented in the index and is normally not part of the next commit.

An ignored path is generally an untracked path hidden by ignore rules. Ignore rules do not make an already tracked path untracked. Chapter 28 explains that boundary.

Git does not commit every file in the directory because a shell glob happens to see it. The index decides what a normal commit records.

## 6. A clean tree has a precise meaning

When `git status` says the working tree is clean, Git sees no relevant tracked differences and no reportable untracked paths under its current settings. It does not prove:

- ignored files are absent,
- the build is reproducible,
- the branch matches a remote,
- no files exist outside the repository,
- or the committed content is correct.

“Clean” is a local comparison result, not an overall quality judgment.

## 7. State transitions should be drawn before use

Common operations affect different layers:

```text
edit file       changes working tree
git add         updates index from working tree
git commit      creates commit from index and advances current branch
git switch      changes selected commit and may update index/worktree
git restore     copies content toward an explicitly selected layer
```

This is a teaching model, not a promise that every command changes only one layer. Merge, rebase, reset, and checkout operations can affect several. Later chapters make those effects explicit.

## 8. Inspect before and after an operation

A small loop is enough to prevent many mistakes:

```bash
git status --short --branch
git diff --check
git diff --cached --stat
```

The first reveals location and state. The second checks whitespace problems in unstaged changes. The third summarizes the staged snapshot. `git diff --check` alone does not inspect every staged change; use `git diff --cached --check` before committing as well.

State inspection is especially important in a shared workspace where another tool, editor, or collaborator may have changed files since the last command.

## 9. The index is also a conflict workspace

During a merge conflict, the index can hold multiple versions of one path: common ancestor, ours, and theirs. There is temporarily no single resolved index entry ready for a normal commit.

That is why `git status` reports an unmerged path and why editing the file alone does not finish resolution. `git add` records the chosen resolved content into the index.

This chapter needs only the boundary: the index is the proposed recorded state, including an explicit unresolved condition during integration.

## 10. A safe three-state observation

In Bash, create a disposable repository:

```bash
practice=$(mktemp -d)
cd -- "$practice" || exit 1
git init -q demo
cd demo || exit 1
git config user.name 'Practice Author'
git config user.email 'practice@example.invalid'
printf '%s\n' 'one' > note.txt
git add -- note.txt
git commit -qm 'Add note'

printf '%s\n' 'two' > note.txt
git add -- note.txt
printf '%s\n' 'three' > note.txt
git status --short
git diff --cached -- note.txt
git diff -- note.txt
```

Do not run the experiment in this handbook repository. The fixture intentionally leaves an uncommitted state for observation.

## 11. Common misconceptions

### “Staged means committed”

Staged content is in the index, not yet represented by a new commit.

### “`git add` stages future edits automatically”

It stages the content observed when the command runs. Later edits require another deliberate staging action.

### “`git diff` shows everything changed since the last commit”

The default comparison is working tree versus index; staged and untracked content need other views.

### “A clean tree means I am up to date”

Local cleanliness says nothing by itself about remote commits.

### “`HEAD` is the file I am editing”

`HEAD` selects a commit. The editor changes a working-tree file.

## Core Computer Science Concept

Git's local model is a **three-way state comparison**. The index is an explicit preparation buffer between mutable workspace and immutable commit history. That buffer allows a developer to choose a coherent snapshot instead of committing every visible change.

## Engineering Connections

- Code review depends on the staged snapshot, not merely on files open in an editor.
- CI runs against commits or worktrees derived from commits, not the developer's uncommitted state.
- Conflict resolution uses the index as the point where competing versions become one chosen result.
- A clean build in a dirty tree may rely on uncommitted local files unavailable to teammates.

## From the Field

An engineer stages a configuration correction, then makes another edit before committing. The commit passes local inspection of the working file but fails in CI because the second edit was never staged. Comparing both `git diff --cached` and `git diff` would have exposed the split state.

## Engineering Review

### What problem does this solve?

It separates the current recorded state, proposed next snapshot, and live workspace so each can be inspected independently.

### Why was it designed this way?

The index gives developers control over the exact content of a commit while preserving unfinished work in the working tree.

### When should I use it?

Use this model before staging, committing, switching branches, merging, rebasing, or recovering changes.

### When should I avoid it?

Do not assume these three states are a backup system; untracked and uncommitted content can still be lost.

### How does this make me a better engineer?

It turns Git problems into concrete state comparisons instead of vague “my file disappeared” stories.

### How does this reduce waste?

Knowing the exact layer prevents accidental commits, missing changes, and destructive recovery guesses.

## Handbook Principle #25

> Name the layer before acting: working tree for current files, index for the next snapshot, and `HEAD` for recorded history.

## Practical Observation

Run the fixture in Section 10. Predict what `git commit` would record, then use `git show :note.txt`, `git show HEAD:note.txt`, and `cat note.txt` to inspect each version. Explain why their outputs differ.

## Looking Ahead

Chapter 26 uses the index deliberately to construct focused commits and verify exactly what became history.

## References

- [Git status semantics](https://git-scm.com/docs/git-status)
- [Git diff comparisons](https://git-scm.com/docs/git-diff)
