# Contributing to The Developer Handbook

Thank you for helping make the handbook more accurate, useful, and durable. Contributions are welcome from learners, working engineers, educators, reviewers, and subject-matter experts.

## Ways to contribute

- Correct a technical error, broken link, typo, or ambiguous explanation.
- Add platform-specific context where behavior differs materially.
- Improve an example, exercise, diagram, or troubleshooting method.
- Add evidence from an authoritative primary source.
- Improve accessibility, navigation, or publication tooling.
- Propose new material that fits the handbook's systems-first curriculum.

Questions and open-ended ideas belong in [GitHub Discussions](https://github.com/superflyad/Developer-handbook/discussions). Actionable defects and scoped proposals belong in [GitHub Issues](https://github.com/superflyad/Developer-handbook/issues/new/choose).

## Before opening a change

1. Search existing issues, discussions, and pull requests.
2. Read the [Editorial Guide](EDITORIAL_GUIDE.md) and [Handbook Architecture](ARCHITECTURE.md).
3. For chapter-sized work, open a content proposal before drafting.
4. Prefer primary, authoritative sources over summaries and search-result snippets.
5. Never include real credentials, production identifiers, private logs, or unsafe destructive examples.

Small corrections can go directly to a pull request. Large structural changes should start with an issue so scope and placement can be agreed before substantial writing begins.

## Local setup

The core validation tools require Python 3.11 or newer and Node.js:

```text
python scripts/check_docs.py
npx --yes markdownlint-cli2@0.23.2 "**/*.md"
```

To build the searchable website:

```text
python -m pip install -r requirements-docs.txt
python scripts/build_site.py
```

Pandoc 3.13 and WeasyPrint 70.0 are required only when building every downloadable publication format:

```text
python scripts/build_book.py --formats html epub docx pdf
```

## Writing standard

Write for an engineer who wants a transferable mental model, not merely a command that works once. A chapter should:

- state the problem and central idea early;
- explain mechanisms, boundaries, ownership, and failure behavior;
- distinguish stable concepts from platform-specific details;
- show safe, reproducible examples in disposable environments;
- connect the topic to real engineering work;
- include review questions and practical exercises where appropriate;
- cite authoritative references near the claims they support.

Do not add invented benchmarks, unverifiable claims, vendor marketing language, or examples whose safe outcome depends on an unstated environment.

## Pull requests

Keep each pull request coherent and reviewable. Complete the pull-request template and include:

- the problem being solved;
- the affected chapters or publication surfaces;
- the sources used for technical claims;
- the commands used to verify examples;
- the validation commands and results;
- any compatibility, safety, or release implications.

Use imperative commit subjects such as:

```text
docs: clarify TCP connection ownership
site: improve chapter navigation
ci: validate publication links
```

By contributing, you agree that your contribution is licensed under the repository's [MIT License](LICENSE).

## Review and acceptance

Maintainers review changes for technical accuracy, pedagogy, source quality, safety, structure, and long-term maintenance cost. A technically correct change may still need revision if it weakens the learning sequence or duplicates existing material.

See [GOVERNANCE.md](GOVERNANCE.md) for decision-making and release responsibilities.
