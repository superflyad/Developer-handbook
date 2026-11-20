# Handbook Audit

The first edition has 129 chapters. This audit checks technical claims, examples, and editorial quality against primary evidence. A chapter's References section makes sources discoverable; it does not certify the whole chapter.

## Review method

For each chapter:

1. Read the complete chapter and identify consequential, platform-dependent, and version-sensitive claims.
2. Check those claims against standards, official manuals, vendor documentation, source code, or a reproducible observation. Link evidence near the claim it supports.
3. Run commands or inspect output in the stated environment when practical. Record the environment and any example that could not be run.
4. Check whether the central model, its limits, and the Engineering Review agree. Remove repetition and unsupported certainty. Apply the [Editorial Guide](EDITORIAL_GUIDE.md), including its prohibition on em dashes.
5. Review the rendered website and publication build for changes that affect navigation, code blocks, tables, or references.
6. In the pull request, list the claims checked, sources used, examples tested, and unresolved questions. Mark the scope of review precisely. A spot check is not a full chapter review.

## Coverage

| Part | Chapters | Audit queue |
| --- | --- | --- |
| Foundations | 1–11 | Chapters 1–3 had initial scoped source work in PRs #17 and #18. Chapters 4–6 are receiving the next source pass. Chapters 7–11 remain queued. |
| Unix environment | 12–23 | Queued in [issue #19](https://github.com/superflyad/Developer-handbook/issues/19). |
| Git | 24–36 | Queued. |
| Operating systems | 37–49 | Queued. |
| Networking | 50–63 | Chapter 55 had initial scoped source work in PR #17. The part remains queued for a complete review. |
| Automation | 64–77 | Queued. |
| Containers | 78–89 | Queued. |
| AWS | 90–105 | Chapter 97 had initial scoped source work in PR #17. The part remains queued for a complete review. |
| System design | 106–117 | Queued. |
| Observability | 118–129 | Queued. |

The audit is complete only when every chapter has a recorded review scope, evidence for consequential claims, verified or explicitly qualified examples, and no unresolved high-impact accuracy issue. The appendix, introduction, roadmap, and cross-chapter consistency also need a final pass. Existing citations alone do not satisfy this criterion.

## Delivery review after the content audit

Once the source review is complete, evaluate the handbook as both a reading experience and a source for agent-assisted learning:

- A reader should find the right chapter, understand its central model, and see its limits without reading an agent-specific version.
- An assistant should retrieve the canonical chapter, cite the relevant section, preserve qualifications, and distinguish the handbook's guidance from current external documentation.
- The generated [chapter index](https://superflyad.github.io/Developer-handbook/llms.txt) and [agent evaluation set](AGENT_EVALUATION.md) are starting points. Record fresh-session results and holdout scenarios as described in [issue #20](https://github.com/superflyad/Developer-handbook/issues/20) before making a general performance claim.
- Check the live website and downloadable formats against the same source revision, including search, chapter navigation, anchors, code blocks, and accessibility.
