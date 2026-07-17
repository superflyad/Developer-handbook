# Handbook Architecture

## Purpose

The Developer Handbook is a living, version-controlled engineering knowledge system. It is not a chronological transcript of conversations and not a static book that becomes obsolete after publication.

Its purpose is to preserve durable mental models, professional workflows, technical judgment, and lessons learned throughout a software engineering career.

> Understand systems. Build mental models. Automate everything worth repeating.

## Source of truth

Markdown in this repository is the canonical source.

PDF, Word, ebook, and website editions are generated publication formats. They must not become independent versions of the handbook.

## Content lifecycle

Every chapter follows this lifecycle:

```text
Learn → Refine → Publish → Apply → Revisit
```

### Learn

Explore the concept freely. Ask questions, challenge assumptions, and identify gaps.

### Refine

Turn the discussion into a coherent chapter. Remove conversational repetition, improve examples, verify the mental model, and connect it to earlier material.

### Publish

Create a focused feature branch, update the chapter and table of contents, and open a draft pull request.

### Apply

Use the concept in real engineering work, exercises, projects, debugging, or automation.

### Revisit

Update the existing chapter as practical experience deepens. Prefer improving the canonical chapter over creating duplicate explanations.

## Repository structure

```text
Developer-handbook/
├── README.md
├── PREFACE.md
├── PHILOSOPHY.md
├── HOW_TO_USE_THIS_HANDBOOK.md
├── LEARNING_ROADMAP.md
├── SUMMARY.md
├── ARCHITECTURE.md
├── EDITORIAL_GUIDE.md
├── DECISIONS.md
├── handbook/
│   ├── foundations/
│   ├── terminal/
│   ├── git/
│   ├── operating-systems/
│   ├── networking/
│   ├── automation/
│   ├── containers/
│   ├── cloud/
│   ├── system-design/
│   └── debugging-performance-observability/
└── appendices/
    └── engineering-patterns/
```

Directories may be introduced when their first chapter is published. Empty scaffolding is unnecessary.

## Book structure

The handbook is organized into Parts and Chapters.

- **Parts** define major areas of engineering capability.
- **Chapters** teach one coherent concept or tightly connected set of concepts.
- **Appendices** collect reusable references, patterns, checklists, and comparisons.

The repository should use **Chapter**, not **Lesson**, for published material. Conversation may still use the word lesson while learning.

## Part I — Foundations: Building the Machine

1. Thinking Like a Unix Developer
2. The Unix Mental Model
3. The Unix Filesystem
4. Programs, Processes, and the Kernel
5. The Shell
6. Terminal Emulators: The Window into Unix
7. Identity, Authentication, Authorization, and Permissions
8. Standard Input, Standard Output, and Standard Error
9. Pipes: Composing Small Tools
10. Environment Variables
11. The Unix Way: Composability in Practice

Part I builds the operating-system mental model before introducing command-focused productivity.

## Long-term roadmap

### Part II — Mastering the Unix Environment

Navigation, file operations, search, text processing, redirection, expansion, process control, practical permissions, package management, shell configuration, and command-line workflows.

### Part III — Git Mastery

The object model, working tree, index, commits, branches, merging, rebasing, remotes, recovery, collaboration, and professional repository workflows.

### Part IV — Filesystems and Operating Systems

Storage, mounting, links, metadata, processes, scheduling, memory, services, startup, security boundaries, and platform comparisons.

### Part V — Networking

Addressing, routing, DNS, ports, sockets, HTTP, TLS, SSH, firewalls, troubleshooting, and cloud networking.

### Part VI — Automation and Scripting

Shell scripting, Python automation, task runners, repeatable environments, scheduling, CI/CD, and replacing manual workflows with reliable systems.

### Part VII — Docker and Containers

Images, layers, registries, namespaces, control groups, networking, volumes, security, orchestration foundations, and production practices.

### Part VIII — AWS and Cloud-Native Development

Identity, networking, compute, storage, databases, observability, infrastructure as code, deployment, reliability, cost, and operational ownership.

### Part IX — System Design

Requirements, tradeoffs, interfaces, data models, scalability, consistency, caching, messaging, resilience, security, and architectural decisions.

### Part X — Performance, Debugging, and Observability

Systematic debugging, profiling, metrics, logs, traces, failure analysis, capacity planning, incident response, and continuous improvement.

## Engineering Patterns appendix

The handbook will maintain an appendix of recurring patterns that appear across technologies:

- Layered systems
- Separation of concerns
- Composition over complexity
- Stable interfaces
- Least privilege
- Identity before authority
- Small tools, loosely coupled
- Automate repetitive work
- Explicit state and ownership
- Failure containment
- Convention over unnecessary configuration

Chapters should link to these patterns once the corresponding appendix entries exist.

## Publishing workflow

```text
Discuss → Approve → Branch → Commit → Draft PR → Review → Squash merge
```

Repository conventions:

- Branch: `agent/<focused-description>`
- Commit: concise Conventional Commit style, usually `docs: ...`
- Pull request: draft by default
- Merge: squash unless preserving separate commits has clear value
- Scope: one coherent chapter, revision, or structural change per PR

## Versioning

Git history is the primary revision history.

Explicit chapter version numbers are optional and should only be introduced when they provide value beyond Git history. Major conceptual rewrites should be clearly described in commit and pull-request messages.

## Quality boundary

Conversation is exploratory. The repository is curated.

Do not publish raw dialogue, unsupported claims, unnecessary repetition, or tool-specific trivia that lacks durable engineering value.