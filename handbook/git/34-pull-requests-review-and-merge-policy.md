# Chapter 34 — Pull Requests, Review, and Merge Policy

Git can exchange commits without a hosting service. A pull request (PR) adds a collaboration layer: it proposes integrating one branch into another, exposes a diff for review, and often gates the integration on checks and approvals. The branch and commits are Git; the PR, discussion, and policy are hosting-platform features.

The central idea is:

> A pull request is a decision record around a proposed change, not a certificate that the code is correct.

## 1. The review unit is a coherent change

A reviewable branch has one purpose, a clear base, and enough context for another engineer to evaluate the result. A small PR is not automatically good: splitting a behavior change from its necessary tests may make both harder to judge. Conversely, combining unrelated refactoring, a new feature, and a dependency upgrade makes risk hard to isolate.

Prepare a PR by inspecting the same comparisons a reviewer will see:

```bash
git status --short
git fetch origin
git log --oneline origin/main..HEAD
git diff --stat origin/main...HEAD
git diff origin/main...HEAD
```

These commands assume `origin/main` exists. Fetch updates your local remote-tracking ref; it does not merge it into your branch. The three-dot diff shows changes from the merge base to your branch tip. If the base branch has advanced, the final integration result may differ, so test against an up-to-date base according to team policy.

Before opening review, state the problem, design decision, test evidence, user-visible effects, and any known limitations. A draft PR communicates that the change is visible but not yet ready to merge. Do not place secrets or private data in a draft; publication to a hosted service is still publication.

## 2. Review is a conversation with evidence

Reviewers should ask whether the change solves the stated problem, preserves invariants, handles failure cases, and fits the system. They can inspect code, tests, docs, and the commit graph. Authors should answer substantive comments with reasoning or a change, not merely mark them resolved. When updating the branch, re-read the final diff: feedback fixes can create new interactions.

Automation is complementary evidence. A green CI check means the configured checks passed for a particular commit or merge candidate; it does not prove the requirements were right, the tests were sufficient, or the eventual merged tree is identical. A red check needs investigation, not a reflexive rerun. If a required check was run against an old SHA, verify that it covers the current candidate before merging.

## 3. Branch protection makes policy executable

Hosting services can restrict direct pushes and require reviews, status checks, or other conditions before integration. Exact settings vary by repository and administrator. Protection reduces accidental bypasses; it does not replace engineering judgment or incident procedures. The team should know who can approve, whether authors may self-merge, how stale approvals are handled, and what to do when an urgent fix cannot wait.

A local branch can still be created and committed without any PR. Git does not enforce a hosted branch's review policy in your personal clone; the remote host enforces it when accepting or integrating changes. Never infer that “I could commit locally” means “I may push to protected `main`.”

## 4. Merge policy changes the graph

The three common GitHub PR integration methods leave different histories:

| Method | Result on base branch | Useful when |
| --- | --- | --- |
| Merge commit | Individual branch commits plus a two-parent integration commit | Branch ancestry and separate commits matter |
| Squash merge | One new commit representing the PR's combined change | The PR is one logical unit with intermediate fixups |
| Rebase merge | Replayed commits in a linear sequence | Individual commits are meaningful and linear history is desired |

Hosting implementations and repository settings determine the exact buttons and allowed methods. A squash or rebase merge ordinarily creates new commit IDs on the base. The topic branch's old commits may remain visible in the PR but are not the same objects as the integrated commits. A merge commit preserves the branch commits and records the integration point. None of these methods replaces tests on the integrated state.

Choose intentionally. If each commit is bisectable and tells a meaningful story, preserving them can help future investigation. If most are review fixups, one squash commit often makes the base history clearer. A merge commit is valuable when the branch line itself explains the project history. Do not impose a universal “clean history” rule without considering traceability and rollback.

## 5. This handbook's publication workflow

The repository's [architecture](../../ARCHITECTURE.md) describes its normal path as:

```text
Discuss → Approve → Branch → Commit → Draft PR → Review → Squash merge
```

Its convention is a focused `agent/<description>` branch, concise `docs: ...` commits, a draft PR by default, and squash merge unless separate commits add clear value. Its [documentation workflow](../../.github/workflows/docs.yml) runs Markdown lint and `scripts/check_docs.py` for PRs and pushes to `main`. The GitHub configuration visible in the repository does not by itself prove that branch protection or required checks are enabled on the host; verify those settings in the hosting UI if they affect a decision.

That workflow is a repository convention, not a property of Git. This chapter's examples do not create a hosted PR or push to `origin/main`. Publication requires the actual review and authorization appropriate to the repository.

## 6. A review-ready handoff

A concise PR description can answer:

1. What problem and scope does this change address?
2. What changed, and what did not?
3. Which tests or checks ran, and at which revision?
4. Which risks, migrations, or compatibility concerns remain?
5. What should a reviewer focus on?

After approval, check for new base-branch movement and rerun relevant checks as policy requires. Merge using the selected method, verify the resulting base commit and checks, then retire the topic branch only when no one still depends on it. A merged PR is the start of operational observation, not the end of responsibility.

## Common Misconceptions

- “A PR is a Git object.” It is hosting metadata around Git branches and commits.
- “Green checks mean the change is safe.” They mean specified automation passed for a particular candidate.
- “Squash merge preserves my branch commit IDs.” It creates a new combined commit on the base.
- “Branch protection prevents all mistakes.” It enforces selected gates, not product correctness.

## Core Computer Science Concept

Review and CI are **independent validation signals** around a state transition. Each checks a limited predicate; integration is safe only relative to the assumptions those predicates cover. The reviewed diff, checked SHA, and merged tree must be related explicitly rather than treated as interchangeable.

## Engineering Connections

- Release notes and incident analysis need a traceable reason for a change, not only a patch.
- Required checks encode a minimum quality bar and expose reproducibility failures.
- Security review should consider who can approve and who can bypass branch rules.
- Small, coherent changes reduce the blast radius of rollback.

## From the Field

A PR passes all checks, then the base branch receives a database migration. The PR is merged without retesting the combined tree and fails at startup. Neither the original reviewer nor CI necessarily saw that exact integration state. The remedy is a policy that validates the current merge candidate and keeps the final diff visible.

## Engineering Review

### What problem does this solve?

It creates a visible, reviewable path from a branch's proposed change to an integrated base-branch state.

### Why was it designed this way?

Git records and exchanges history; hosting services add human discussion and enforceable integration gates around that history.

### When should I use it?

Use a PR for shared repository changes that need review, checks, or an auditable integration decision.

### When should I avoid it?

Do not treat PR approval as proof of correctness or use a giant PR to hide unrelated changes under one approval.

### How does this make me a better engineer?

It improves change framing, risk communication, evidence-based review, and awareness of what was actually tested.

### How does this reduce waste?

Coherent review units find issues before integration and make later investigation and rollback faster.

## Handbook Principle #34

> Review the proposed state, verify the checked state, and know which state your merge actually publishes.

## Practical Observation

Choose a public repository PR or a disposable local branch. Compare its topic to its base with `git diff base...topic`, then sketch the graph each merge policy would produce. Identify what a reviewer can infer from the diff and what requires a test or design explanation. Do not alter a live hosted repository for this exercise.

## Looking Ahead

Review often overlaps with another task. Chapter 35 shows how to keep parallel working states separate without turning a stash into a long-term storage system.

## References

- [GitHub: Pull request merges](https://docs.github.com/en/pull-requests/reference/pull-request-merges)
- [GitHub: About pull request reviews](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/about-pull-request-reviews)
- [GitHub: About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
