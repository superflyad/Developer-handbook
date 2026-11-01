# The Developer Handbook

A living software engineering handbook focused on first principles, systems thinking, technical judgment, and efficient professional workflows.

> **Understand systems. Build mental models. Automate everything worth repeating.**

This project is a continuous learning system rather than a collection of isolated notes. Chapters are refined as practical experience grows, and the repository preserves both the current guidance and the history of how that guidance evolved.

## Start here

- [Preface](PREFACE.md)
- [Handbook Philosophy](PHILOSOPHY.md)
- [How to Use This Handbook](HOW_TO_USE_THIS_HANDBOOK.md)
- [Learning Roadmap](LEARNING_ROADMAP.md)
- [Table of Contents](SUMMARY.md)

## Project governance

- [Handbook Architecture](ARCHITECTURE.md)
- [Editorial Guide](EDITORIAL_GUIDE.md)
- [Handbook Decisions](DECISIONS.md)

These documents preserve the roadmap, publication workflow, writing standards, and reasoning behind major structural decisions.

## Core priorities

1. Keyboard-first workflow
2. Terminal and Unix mastery
3. Git mastery
4. Filesystem and operating-system fundamentals
5. Networking fundamentals
6. Automation and scripting
7. Docker and containers
8. AWS and cloud-native development
9. System design
10. Performance, debugging, and observability

## Working method

```text
Learn → Refine → Publish → Apply → Revisit
```

Discussion and experimentation happen before publication. GitHub contains the refined, handbook-quality source.

Operational meanings:

- **Discuss:** explore without repository changes.
- **Draft:** prepare polished proposed content.
- **Publish / Commit:** write the approved files to a feature branch and open or update a draft pull request.
- **Merge:** integrate an approved pull request into `main`.

## Handbook standard

Each chapter should answer:

- What problem does this solve?
- Why was it designed this way?
- When should I use it?
- When should I avoid it?
- How does this make me a better software engineer?
- How does this reduce waste or improve efficiency?

The canonical source is Markdown in this repository. PDF, Word, ebook, and website versions are generated outputs rather than independent sources.

## Publication formats

`SUMMARY.md` defines canonical reading order. The publication builder combines the preface, philosophy, usage guide, Chapters 1–129, and Engineering Patterns appendix; assigns stable cross-format anchors; rewrites local cross-references; and records source and artifact hashes in a manifest.

Build the combined Markdown and manifest with the Python standard library:

```text
python scripts/build_book.py
```

With Pandoc 3.13 and WeasyPrint 70.0 available, build every preview format:

```text
python scripts/build_book.py --formats html epub docx pdf
```

Outputs are written to ignored `build/` and are never edited as source. The documentation workflow validates the repository, builds standalone HTML, EPUB, DOCX, and PDF previews, verifies their file signatures, records their SHA-256 digests, and uploads the complete build directory as a revision-specific CI artifact.
