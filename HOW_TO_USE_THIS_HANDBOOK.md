# How to Use This Handbook

This handbook should be read progressively, but it is also designed for later reference.

## During initial learning

Work through chapters in order within each part. Later chapters assume the mental models established earlier. Do not rush to memorize commands before understanding the system they operate on.

For each chapter:

1. Read for the central mental model.
2. Connect it to prior chapters.
3. Complete the practice section.
4. Test the idea in real work.
5. Record questions, failures, and better examples for future revisions.

## During daily engineering work

Use the handbook as an operating manual:

- consult workflows before repeating manual work,
- use debugging checklists instead of guessing,
- record important technical decisions and their reasoning,
- convert production lessons into reusable knowledge,
- refine personal standards when a better practice is proven.

## With an AI assistant

Give the assistant a link to the relevant chapter or the [machine-readable chapter index](https://superflyad.github.io/Developer-handbook/llms.txt). Ask for a recap before a deeper explanation, then use the chapter's example or practice section to test your understanding. The Markdown chapter remains the source of truth; an answer produced by an assistant is a reading aid.

For example:

```text
Read this handbook chapter as your source. Summarize its central model in one
paragraph. List when to use it, when to avoid it, and one failure mode. Cite the
chapter sections and any primary references you rely on. Mark claims that may
depend on a product version or current service behavior. Tell me what the
chapter does not establish. Then give me one scenario to reason through.
```

Check the cited passage when an answer affects a production change, security boundary, data recovery plan, or cost decision. Follow the chapter's primary references for behavior that may have changed since publication. If the answer cannot identify supporting text, treat the claim as unverified and report the gap through the chapter's edit link.

## Content workflow

Conversation and experimentation are the drafting environment. GitHub is the publication environment.

```text
Learn → Refine → Publish → Apply → Revisit
```

Raw discussion should not be copied directly into the handbook. A chapter is published only after it is coherent, technically accurate, and useful without the surrounding conversation.

## Source of truth

Markdown in this repository is canonical. Generated PDFs, Word documents, ebooks, or websites are distribution formats and should not be edited independently.
