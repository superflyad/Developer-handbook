# The Developer Handbook

[![Documentation checks](https://github.com/superflyad/Developer-handbook/actions/workflows/docs.yml/badge.svg)](https://github.com/superflyad/Developer-handbook/actions/workflows/docs.yml)
[![Latest release](https://img.shields.io/github/v/release/superflyad/Developer-handbook?display_name=tag&sort=semver)](https://github.com/superflyad/Developer-handbook/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-0b7189.svg)](LICENSE)
[![Read online](https://img.shields.io/badge/read-online-06b6d4.svg)](https://superflyad.github.io/Developer-handbook/)

![The Developer Handbook — Systems thinking for working engineers](assets/social-preview.png)

An open-source, systems-first guide to becoming a stronger software engineer—from Unix and Git to networking, containers, cloud architecture, system design, and production debugging.

> **Understand systems. Build mental models. Automate everything worth repeating.**

## Start reading

| Experience | Where to begin |
| --- | --- |
| Read the complete handbook | **[Open the searchable web edition](https://superflyad.github.io/Developer-handbook/)** |
| Build the foundations in order | [Chapter 1 — Thinking Like a Unix Developer](handbook/foundations/01-thinking-like-a-unix-developer.md) |
| Choose a focused learning path | [Learning Roadmap](LEARNING_ROADMAP.md) |
| Understand the teaching method | [How to Use This Handbook](HOW_TO_USE_THIS_HANDBOOK.md) |
| Download PDF, EPUB, DOCX, HTML, or Markdown | [Latest release](https://github.com/superflyad/Developer-handbook/releases/latest) |

## What makes this handbook different

The Developer Handbook is not a command reference or a collection of disconnected tutorials. It develops the mental models that let engineers reason across layers: what a tool is doing, why a system behaves that way, where ownership changes, and how to investigate failures without guessing.

Every chapter is designed to answer six practical questions:

1. What problem does this solve?
2. Why was it designed this way?
3. When should I use it?
4. When should I avoid it?
5. How does this make me a better software engineer?
6. How does this reduce waste or improve efficiency?

The result is a coherent curriculum for working engineers, students moving beyond framework-level knowledge, and experienced developers strengthening their systems judgment.

## The curriculum

The first edition contains **129 chapters across ten parts**, followed by a cross-cutting Engineering Patterns appendix.

| Part | Chapters | Focus |
| --- | ---: | --- |
| I. Foundations | 1–11 | Unix thinking, processes, shells, streams, permissions, and composition |
| II. Unix Environment | 12–23 | Navigation, files, text processing, jobs, software, and terminal workflow |
| III. Git Mastery | 24–36 | Git objects, commits, branches, recovery, collaboration, and change lifecycles |
| IV. Operating Systems | 37–49 | Storage, filesystems, processes, memory, services, boot, and identity boundaries |
| V. Networking | 50–63 | Packets, addressing, routing, DNS, sockets, TCP, TLS, HTTP, and troubleshooting |
| VI. Automation | 64–77 | Reliable shell and Python programs, configuration, testing, state, and CI/CD |
| VII. Containers | 78–89 | Isolation, images, builds, storage, networking, security, and orchestration |
| VIII. AWS | 90–105 | Governance, IAM, VPCs, compute, data, messaging, serverless, and delivery |
| IX. System Design | 106–117 | Requirements, contracts, scale, consistency, events, resilience, and evolution |
| X. Observability | 118–129 | Debugging, logs, metrics, traces, profiling, load, incidents, and learning |

Browse the complete [Table of Contents](SUMMARY.md) or jump directly to the [Engineering Patterns appendix](handbook/appendices/engineering-patterns.md).

## A living engineering reference

The handbook is versioned like software. Markdown is the source of truth; the website and downloadable editions are reproducible build artifacts. Guidance evolves when platforms change, better evidence appears, or operational experience exposes a sharper model.

```text
Learn → Refine → Publish → Apply → Revisit
```

Major editions receive tagged releases and permanent publication files. Smaller improvements remain visible through Git history and the [changelog](CHANGELOG.md).

## Contributing

Corrections, clearer explanations, reproducible examples, accessibility improvements, and well-scoped new material are welcome. Start with [CONTRIBUTING.md](CONTRIBUTING.md), use the appropriate issue form, and read the [Editorial Guide](EDITORIAL_GUIDE.md) before proposing a chapter-sized change.

- Ask usage and learning questions in [GitHub Discussions](https://github.com/superflyad/Developer-handbook/discussions).
- Report content errors through [GitHub Issues](https://github.com/superflyad/Developer-handbook/issues/new/choose).
- Report security-sensitive problems privately through [GitHub Security Advisories](https://github.com/superflyad/Developer-handbook/security/advisories/new).

Participation is governed by the [Code of Conduct](CODE_OF_CONDUCT.md). Project decisions and maintainer responsibilities are described in [GOVERNANCE.md](GOVERNANCE.md).

## Build locally

Validate the source:

```text
python scripts/check_docs.py
npx --yes markdownlint-cli2@0.23.2 "**/*.md"
```

Build the searchable website:

```text
python -m pip install -r requirements-docs.txt
python scripts/build_site.py
```

Build the combined Markdown publication:

```text
python scripts/build_book.py
```

With Pandoc 3.13 and WeasyPrint 70.0 installed, build every downloadable format:

```text
python scripts/build_book.py --formats html epub docx pdf
```

Generated files are written beneath ignored `build/` directories. See [ARCHITECTURE.md](ARCHITECTURE.md) for the source, website, and release architecture.

## Project information

- **Maintainer:** [Michael Adeniken](https://github.com/superflyad)
- **Current edition:** [v1.0.0](https://github.com/superflyad/Developer-handbook/releases/tag/v1.0.0)
- **License:** [MIT](LICENSE)
- **Citation:** [CITATION.cff](CITATION.cff)
- **Support:** [SUPPORT.md](SUPPORT.md)

If the handbook helps you reason more clearly about real systems, consider starring the repository or sharing the chapter that helped you.
