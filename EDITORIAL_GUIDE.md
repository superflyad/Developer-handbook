# Editorial Guide

This guide defines how published chapters should be written and maintained.

## Editorial objective

The handbook should help a professional developer become a stronger engineer, not merely complete isolated tasks.

Every chapter must improve at least one of these capabilities:

- reasoning about systems,
- making technical decisions,
- debugging methodically,
- designing maintainable software,
- operating systems safely,
- reducing repetitive work,
- transferring knowledge across platforms and technologies.

## Terminology

Published material uses **Part** and **Chapter**.

Use **lesson** only when describing the live learning process. Do not title published files as lessons.

## Teaching order

Teach in this order whenever practical:

1. The problem
2. The first-principles model
3. Why the design exists
4. How the mechanism works
5. Practical use
6. Failure modes and misuse
7. Connections to production engineering
8. Practice or observation

Do not lead with commands when the command depends on an unexplained mental model.

## Required questions

Every chapter should answer:

- What problem does this solve?
- Why was it designed this way?
- When should I use it?
- When should I avoid it?
- How does this make me a better software engineer?
- How does this reduce waste or improve efficiency?

These answers may appear throughout the chapter and be summarized near the end.

## Standard chapter structure

Use the following structure when it improves the chapter. It is a strong default, not a rigid form that forces empty sections.

1. Title and central idea
2. First principles
3. Mental model
4. Design rationale
5. Practical examples
6. Platform comparison, when useful
7. Common misconceptions
8. Engineering Connections
9. Core Computer Science Concept, when applicable
10. From the Field
11. Engineering Review
12. Handbook Principle
13. Practical observation or exercise
14. Looking Ahead

## Writing standards

### Explain why before how

A command or API is easier to remember when its purpose and underlying mechanism are understood.

### Build on previous chapters

Cross-reference earlier concepts instead of re-teaching them from scratch. State the connection explicitly.

### Prefer durable principles

Prioritize concepts that remain useful when tools, versions, and vendors change.

### Be technically precise

Avoid memorable claims that are only approximately true. Qualify simplifications and distinguish mental models from exact implementations.

### Show boundaries

Explain when a technique should not be used. Every useful abstraction has limits.

### Use real engineering consequences

Connect concepts to source control, CI/CD, containers, cloud systems, databases, security, debugging, performance, or maintainability.

### Compare platforms intentionally

Compare Windows, macOS, and Linux when the comparison improves understanding. Do not add platform tables merely for symmetry.

### Prefer native tools first

Teach the operating system and standard environment before introducing third-party replacements. Recommend third-party tools when they solve a demonstrated problem.

### Avoid information dumping

Introduce complexity progressively. A chapter may point ahead instead of explaining every advanced edge case immediately.

## Examples and code

- Use examples that can be executed or reasoned about with minimal hidden setup.
- State which shell, platform, language, or environment an example assumes.
- Do not present destructive commands casually.
- Prefer explicit, readable commands before compressed expert shorthand.
- Explain shell syntax separately from the external command receiving its arguments.
- Use placeholders that are clearly placeholders.

## Security guidance

- Teach least privilege by default.
- Do not normalize routine use of administrative access.
- Distinguish authentication, authorization, identity, authority, and capability.
- Explain the security boundary being crossed when using privileged operations.

## Automation guidance

Do not automate a process before understanding and simplifying it.

The preferred sequence is:

```text
Observe → Understand → Remove waste → Stabilize → Automate → Measure
```

## Chapter principles

Each chapter ends with one concise Handbook Principle. It should express a durable mental model, not summarize every section.

## Revision policy

Revise existing chapters when new experience improves the explanation. Avoid creating duplicate chapters solely because the understanding evolved.

A revision should preserve what remains correct, remove what is misleading, and document meaningful conceptual changes in the pull request.

## Publication checklist

Before opening a pull request, verify:

- The title uses Chapter terminology.
- The central idea is clear near the beginning.
- The chapter explains why before commands or procedures.
- Technical claims are accurate and appropriately qualified.
- Examples match the stated platform and shell.
- Misuse and limitations are included.
- Engineering connections are concrete.
- The table of contents and roadmap are updated.
- The content is polished prose, not raw conversation.
- The PR has one coherent purpose.