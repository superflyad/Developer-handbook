# Handbook Decisions

This file records durable decisions about how the Developer Handbook is designed and maintained.

Each decision includes its status, context, decision, and consequences. Replaced decisions remain in the history rather than disappearing.

## ADR-001 — Treat the handbook as a living system

**Status:** Accepted

### Context

Engineering knowledge changes through practice, new technologies, corrected assumptions, and deeper understanding. A static document would gradually become stale.

### Decision

The handbook will be continuously revised. Existing chapters should be improved as understanding grows.

### Consequences

- Chapters are never considered permanently finished.
- Git history preserves how guidance evolved.
- Corrections are expected and documented rather than hidden.

## ADR-002 — Teach principles before commands

**Status:** Accepted

### Context

Command-first tutorials often produce shallow recall without helping engineers reason about unfamiliar systems or debug failures.

### Decision

Introduce the problem, system model, and design rationale before teaching command syntax whenever the command depends on those concepts.

### Consequences

- Part I builds the machine's mental model before command mastery.
- Chapters may intentionally defer procedures until prerequisites are established.
- Commands are taught as interfaces to known mechanisms rather than magic incantations.

## ADR-003 — Use GitHub pull requests as the publication workflow

**Status:** Accepted

### Context

Exploratory discussion and permanent reference material have different quality requirements.

### Decision

Published changes flow through feature branches and pull requests. Draft pull requests are the default review boundary.

### Consequences

- Conversation remains safe for experimentation.
- Repository content is intentionally curated.
- Changes have reviewable scope and durable history.
- Approved changes are normally squash-merged into `main`.

## ADR-004 — Organize published material into Parts and Chapters

**Status:** Accepted

### Context

The project is evolving into a long-term professional reference rather than a short course.

### Decision

Published content uses **Part** and **Chapter** terminology. **Lesson** may describe the learning conversation but not the canonical book structure.

### Consequences

- The roadmap and table of contents use chapter terminology.
- Future chapter titles use `Chapter N` internally where numbered headings are appropriate.
- Existing content may be standardized during editorial revisions.

## ADR-005 — Use Unix as a vehicle for transferable engineering concepts

**Status:** Accepted

### Context

The immediate curriculum begins with Unix, macOS, and terminal workflows, but the long-term goal is broad software engineering mastery.

### Decision

Unix chapters must surface reusable concepts such as process isolation, stable interfaces, least privilege, composability, explicit state, and failure containment.

### Consequences

- Chapters connect to Windows, Linux, cloud systems, containers, databases, and distributed applications when useful.
- The handbook avoids becoming a catalog of Unix trivia.
- A planned Engineering Patterns appendix collects recurring principles.

## ADR-006 — Make Markdown the canonical source

**Status:** Accepted

### Context

Maintaining Word, PDF, ebook, website, and Markdown as independent documents would create drift and duplicated work.

### Decision

Markdown in this repository is the source of truth. Other formats are generated artifacts.

### Consequences

- Content is searchable, diffable, version-controlled, and automation-friendly.
- Publication tooling can evolve without rewriting the source.
- Generated outputs should not be edited independently.

## ADR-007 — Separate discussion, drafting, publishing, and merging

**Status:** Accepted

### Context

Ambiguous verbs led to confusion about whether content had merely been written in conversation or actually committed to GitHub.

### Decision

Use these workflow meanings:

- **Discuss:** explore without repository changes.
- **Draft:** produce polished proposed content without repository changes unless GitHub is explicitly requested.
- **Publish / Commit:** create or update a branch, commit the files, and open or update a draft pull request.
- **Merge:** merge an approved pull request into `main`.

### Consequences

- Repository actions require explicit intent.
- Completion claims must be backed by actual tool results.
- PR links are returned only after GitHub confirms creation.

## ADR-008 — Prefer focused, coherent pull requests

**Status:** Accepted

### Context

Extremely small commits create noise, while oversized pull requests make review and history difficult.

### Decision

Each pull request should represent one coherent chapter, related chapter pair, structural revision, or editorial improvement.

### Consequences

- Related chapters may share a pull request when they form one conceptual unit.
- Unrelated changes are separated.
- Commit and PR history should communicate the handbook's evolution clearly.