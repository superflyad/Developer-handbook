# Chapter 27 — Reading History and Investigating Changes

Git's graph is useful only when we can ask precise questions of it. Investigation should begin with a hypothesis and a comparison, not with an indiscriminate scroll through commit messages.

The central idea is:

> Treat history as evidence: select a revision range, compare exact states, then test a causal hypothesis against the code and behavior.

## 1. Start with the question

Different questions need different views:

| Question | Useful starting point |
| --- | --- |
| What is the current history shape? | `git log --oneline --graph --decorate` |
| What changed in one commit? | `git show --stat <commit>` then `git show <commit>` |
| How do two states differ? | `git diff <old> <new>` |
| When did a path change? | `git log -- <path>` |
| Which commit introduced a string? | `git log -S<string> -- <path>` |
| Which change introduced a regression? | controlled `git bisect` |

The command is not the conclusion. A matching commit may reveal the symptom while the cause lies in a dependency, configuration, or earlier design decision.

## 2. Read the graph, not just the dates

```bash
git log --oneline --graph --decorate --all
```

`--graph` shows parent relationships. `--decorate` shows refs pointing at commits. `--all` includes commits reachable from more refs than the current branch alone.

Commit timestamps are metadata, not a total order of causality across contributors. Ancestry tells which commits a descendant includes. Two independent branches can contain commits with interleaved timestamps and no ancestor relationship.

## 3. Inspect a commit and its context

```bash
git show --stat HEAD
git show --format=fuller HEAD
git show HEAD -- src/parser.py
```

`git show` for a commit normally displays metadata and a patch relative to a parent. A merge commit can have multiple parents, so its default display and available combined-diff modes require care. A patch shows line differences, not a complete account of runtime behavior.

Read the commit message for intent, the diff for implementation, and adjacent commits for context.

## 4. A diff needs two endpoints

```bash
git diff A B
```

This compares the trees at `A` and `B`. It does not mean “replay the commits between them.” Different histories can produce the same final tree.

Some useful local comparisons are:

```bash
git diff                 # working tree versus index
git diff --cached        # index versus HEAD
git diff HEAD~2 HEAD     # two recorded states
```

Use `--` before pathspecs when a pathname might be confused with a revision or option:

```bash
git diff HEAD~2 HEAD -- src/parser.py
```

## 5. Revision ranges express reachability

For `git log`, `A..B` selects commits reachable from `B` but not from `A`:

```bash
git log --oneline main..topic
```

This answers what `topic` has that `main` does not. `A...B` in `git log` selects the symmetric difference: commits reachable from either side but not both.

Be careful: three-dot syntax for `git diff A...B` has different comparison behavior. It commonly compares the merge base of `A` and `B` with `B`, showing the topic-side change. The same punctuation has different command-specific meanings; inspect the manual rather than memorizing a slogan.

## 6. Limit the search without hiding context

```bash
git log --oneline -- docs/guide.md
git log -p -- docs/guide.md
git log --follow --oneline -- docs/guide.md
```

Path-limited history is useful but can simplify the displayed graph. `--follow` attempts to continue through renames for one path; Git's rename detection is heuristic, and complex moves or splits may need manual investigation.

For a behavior spanning multiple files, a single-path log can miss important changes.

## 7. Search changes by content, not just filenames

`-S` searches for commits where the count of a specified string changes:

```bash
git log -S'legacyMode' --oneline -- src
```

`-G` searches for patch lines matching a regular expression:

```bash
git log -G'legacyMode|compatMode' --oneline -- src
```

These are different predicates. A refactor that moves a string without changing its count may not appear under `-S` the way you expect. Inspect candidate diffs after selection.

## 8. `blame` names a last recorded line change

```bash
git blame -L 20,40 -- src/parser.py
```

`blame` associates lines with commits under a chosen revision and options. It does not identify the person morally responsible for a bug or prove why a line exists. Formatting, moves, generated code, and later edits can obscure the original design decision.

Use the commit as a doorway into context: read its message, patch, related issue, and tests. Avoid turning a debugging tool into a people-ranking tool.

## 9. `bisect` tests a monotonic good-to-bad boundary

If a reproducible test passes at one commit and fails at a later one, `git bisect` can narrow the first bad commit by checking intermediate states:

```bash
git bisect start
git bisect bad HEAD
git bisect good <known-good-commit>
```

At each selected commit, run the same test and report:

```bash
git bisect good
git bisect bad
git bisect skip
```

Use `skip` when a commit cannot be tested. Finally:

```bash
git bisect reset
```

Bisect temporarily changes the checkout and records bisect state. Start with a clean working tree or an isolated worktree, and reset when finished. It does not rewrite the project's commits.

## 10. A failing test must be trustworthy

Bisect assumes a meaningful predicate. If the result depends on network outages, unstated environment variables, generated files, or changing external services, the search can point to a misleading commit.

Prefer a deterministic test with explicit setup. If old commits require different dependencies or build steps, document that and distinguish “cannot test” from “bad.”

Finding the first commit where the test fails identifies an introduction point under the test's assumptions, not necessarily the root design error.

## 11. An investigation loop

1. Reproduce the symptom in a controlled environment.
2. Identify the branch and exact commit under test.
3. Limit the likely time, path, or content range.
4. Compare candidate states and read messages.
5. Use bisect only when the test is repeatable and the range is worth searching.
6. Inspect the selected commit in context.
7. Form and test a causal explanation.

This loop is more efficient than blaming the last person to touch a line.

## 12. Common misconceptions

### “The newest timestamp is the latest ancestor”

History relationships come from parent links; timestamps are not a total causal order.

### “A diff is the set of commits between two points”

It compares two states. A log range selects commits by reachability.

### “Three dots always mean the same thing”

`git log` and `git diff` interpret three-dot forms differently.

### “`blame` tells us who caused the defect”

It identifies a recorded line association, not complete causality or responsibility.

### “Bisect is read-only”

It changes the checkout and manages temporary state, though it does not rewrite commits.

## Core Computer Science Concept

History investigation is **graph search guided by predicates**. Reachability narrows candidate commits; a deterministic behavioral test partitions a good-to-bad range. The quality of the answer depends on the quality of the predicate.

## Engineering Connections

- Incident timelines should record exact commit IDs and deployed artifacts.
- Regression tests turn a history search into a repeatable experiment.
- Reviewers compare a topic branch against its merge base, not necessarily against yesterday's timestamp.
- Code archaeology connects implementation changes to requirements and operational failures.

## From the Field

A performance regression appears after a formatting commit. `blame` points to the formatting change because it touched the affected lines. A bisect with a representative benchmark identifies an earlier data-access change. The line association and behavioral cause were different facts.

## Engineering Review

### What problem does this solve?

It makes recorded history searchable as evidence for change review and debugging.

### Why was it designed this way?

Git's graph, exact states, and derived diffs let users ask ancestry, content, and behavioral questions separately.

### When should I use it?

Use it during code review, regression investigation, incident analysis, and maintenance of unfamiliar code.

### When should I avoid it?

Avoid claiming causality from a timestamp, one diff, or one `blame` line without a reproducing test or contextual evidence.

### How does this make me a better engineer?

It trains precise hypotheses, controlled experiments, and distinction between correlation and cause.

### How does this reduce waste?

Scoped history queries and bisect reduce manual search through large commit ranges.

## Handbook Principle #27

> Use the graph to narrow the question, a diff to inspect a state change, and a test to establish behavioral cause.

## Practical Observation

In a disposable repository, make three commits to one file: a working version, a regression, and an unrelated documentation change. Use `git log --oneline`, `git diff` between the first and last commits, and `git bisect` with a reproducible test to identify the regression. Finish with `git bisect reset` and verify your original checkout is restored.

## Looking Ahead

History is only as useful as the content it records. Chapter 28 defines the boundary between tracked source, ignored local state, generated artifacts, and cross-platform text normalization.

## References

- [Git log](https://git-scm.com/docs/git-log)
- [Git bisect](https://git-scm.com/docs/git-bisect)
