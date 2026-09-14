# Chapter 16 — Searching Text and Working with Regular Expressions

Text search is not simply “look for some characters.” It combines an input boundary, a pattern language, selection semantics, output formatting, and an exit-status contract.

The central idea is:

> Constrain the input set, choose the smallest pattern language that expresses the question, and treat matches, output, and exit status as separate results.

## 1. Search is a selection operation

By default, `grep` reads text records and writes selected lines:

```bash
grep 'ERROR' application.log
```

Conceptually:

```text
input lines → pattern predicate → selected lines
```

The normal output answers “which records matched?” The exit status answers “did selection occur, or did an error occur?” Diagnostics describe operational problems.

## 2. Start with a literal question

If the desired text is literal, say so:

```bash
grep -F 'price=$5.00' invoice.txt
```

`-F` treats the pattern as fixed strings rather than regular expressions. This avoids accidental meaning for characters such as `.`, `*`, `[`, or `$` and can communicate intent more clearly.

Do not reach for regex syntax when exact substring search solves the problem.

## 3. A regular expression describes text structure

A regular expression is a pattern language. With extended regular expressions:

```bash
grep -E '^(INFO|WARN|ERROR):' application.log
```

Selected operators include:

| Form | Meaning in a common extended regex |
| --- | --- |
| `^` | start of line |
| `$` | end of line |
| `.` | one matching character |
| `[abc]` | one character from a set |
| `[^abc]` | one character outside a set |
| `*` | zero or more of the preceding atom |
| `+` | one or more of the preceding atom |
| `?` | zero or one of the preceding atom |
| `(a\|b)` | grouped alternatives |

Regex dialects differ. “Regular expression” does not identify one universal language.

## 4. Basic and extended regex are different interfaces

Traditional `grep` uses basic regular expressions by default. `grep -E` selects extended regular expressions.

The same conceptual operator can require different escaping between dialects. Prefer an explicit mode and a readable pattern over punctuation optimized for brevity.

```bash
grep -E '^(GET|POST) ' access.log
```

Perl-compatible regex options exist in some implementations, including GNU `grep -P` and ripgrep's optional modes, but they are not a portable baseline. Use them only for a demonstrated requirement.

## 5. Quote the pattern for the shell

This protects regex characters from shell interpretation:

```bash
grep -E '^[[:space:]]*#' settings.conf
```

Single quotes are a strong default for static patterns. If shell data must become part of a search, first ask whether fixed-string mode is safer:

```bash
needle='a[b]'
grep -F -- "$needle" data.txt
```

Interpolating untrusted text into a regex changes the pattern program. Preserving it as one shell argument is necessary but does not make it literal.

## 6. Globs and regex solve different matching problems

Compare:

```bash
find . -name '*.log' -print
grep -E '.*\.log' names.txt
```

In a glob, `*` matches a sequence by itself. In a regex, `*` repeats the preceding atom, so `.*` means a sequence of matching characters.

The shell can interpret globs, `find -name` can interpret glob-like patterns, and `grep` can interpret regex. Always identify which component owns the pattern.

## 7. Scope inputs before optimizing patterns

Recursive search can visit far more than intended:

```bash
grep -R 'TODO' .
```

Prefer a constrained root and exclusions appropriate to the implementation:

```bash
grep -R --exclude-dir=.git --include='*.md' 'TODO' handbook
```

GNU `grep -r` and `-R` differ in symbolic-link handling. Other implementations vary. Search roots, link traversal, devices, generated files, dependencies, and binary inputs are part of the correctness boundary.

## 8. Output format serves a consumer

Useful reporting modes include:

```bash
grep -n 'ERROR' application.log       # line numbers
grep -H 'ERROR' ./*.log               # filenames
grep -l 'ERROR' ./*.log               # matching filenames only
grep -c 'ERROR' application.log       # selected-line count
grep -C 2 'ERROR' application.log     # surrounding context
```

`grep -c` counts selected lines, not necessarily the number of non-overlapping matches. A line containing the pattern three times still contributes one selected line.

Choose output for people or machines intentionally. Decorative color should generally be disabled when output is parsed.

## 9. Exit status distinguishes match, no match, and error

For common `grep` implementations:

```text
0  at least one line selected
1  no line selected
2  error
```

This makes quiet search useful in conditions:

```bash
if grep -qF 'enabled=true' settings.conf; then
  printf '%s\n' 'feature enabled'
else
  status=$?
  printf 'search status=%s\n' "$status" >&2
fi
```

A production script should distinguish status 1 from an operational error. Also check implementation notes: quiet mode may return success after a match even if another input later produces an error.

## 10. Empty patterns and empty input need policy

An empty fixed string or regex can match every line:

```bash
needle=''
grep -F -- "$needle" data.txt
```

If an empty search term is invalid for an application, validate it before invoking the tool:

```bash
test -n "$needle" || {
  printf '%s\n' 'search term must not be empty' >&2
  exit 2
}
```

An empty input file normally produces no selected lines and a no-match status. That may mean “valid empty result” or “upstream failure”; the surrounding workflow decides.

## 11. Locale affects character interpretation

Character classes, ranges, case folding, and which byte sequences form characters can depend on locale.

Prefer named classes for intent:

```bash
grep -E '^[[:digit:]]+$' identifiers.txt
```

For byte-oriented reproducible behavior, a command may intentionally use:

```bash
LC_ALL=C grep -F 'token' data.bin
```

That is a contract change, not a universal performance trick. It may be inappropriate for human-language text.

## 12. Binary detection is implementation behavior

GNU `grep` may classify input as binary and suppress normal matching output. Options can force text treatment or skip binary files, but sending arbitrary bytes to a terminal can produce confusing or unsafe display effects.

If the data is genuinely structured or binary, use a format-aware tool. Search heuristics do not turn arbitrary bytes into trustworthy text.

## 13. Ripgrep is a practical extension

After understanding the native model, `rg` provides fast recursive project search with useful defaults:

```bash
rg -n -F 'TODO' handbook
rg -n --glob '*.md' 'Chapter [0-9]+' .
```

Ripgrep commonly respects ignore files and skips hidden or binary data by default. Those defaults are excellent for source trees but mean “search this directory” does not automatically mean “read every entry.”

Use `rg --help` and its official guide to inspect the exact selection rules. Tool convenience never removes the need to define scope.

## 14. Search structured data structurally

This is fragile:

```bash
grep '"status": "ready"' response.json
```

Equivalent JSON can vary in whitespace, ordering, escaping, and nesting. Use a JSON parser when the question concerns JSON fields. The same principle applies to CSV, XML, logs with schemas, and compressed formats.

Text search is appropriate when line-oriented text representation is itself the contract.

## 15. Debug patterns with controlled fixtures

Create a small representative input:

```bash
printf '%s\n' \
  'INFO: started' \
  'WARN: retrying' \
  'ERROR: unavailable' > sample.log

grep -nE '^(WARN|ERROR):' sample.log
```

Test:

- a match,
- no match,
- malformed or missing input,
- surprising punctuation,
- non-ASCII text when relevant,
- and the exit status for each case.

The fixture is an executable statement of pattern intent.

## 16. Common misconceptions

### “Regex and shell wildcards are the same”

They are different languages often interpreted by different components.

### “No output means the command failed”

It may mean a valid no-match result. Inspect the documented exit status.

### “`grep -c` counts every occurrence”

It normally counts selected lines.

### “Recursive search reads everything”

Links, ignores, binaries, permissions, devices, and implementation defaults affect the input set.

### “A more powerful regex is always better”

Literal search and format-aware parsers are often clearer and safer.

## 17. Platform comparison

| Concern | POSIX/GNU `grep` | macOS/BSD `grep` | PowerShell |
| --- | --- | --- | --- |
| Literal search | `grep -F` | `grep -F` | `Select-String -SimpleMatch` |
| Extended regex | `grep -E` | `grep -E` | .NET regular expressions by default |
| Recursive options | GNU-specific details | details differ | pipeline over filesystem objects |
| Project-aware tool | `rg` when installed | `rg` when installed | `rg` or `Select-String` |

Patterns must be reviewed when moving between regex engines, not merely between operating systems.

## Core Computer Science Concept

Text search applies a **predicate over a sequence of records**. A regex is a compact recognizer for a language of strings; the tool combines that recognizer with input traversal and result reporting.

Separating recognizer, input set, and output contract prevents a clever pattern from hiding a badly scoped search.

## Engineering Connections

- Source search accelerates code comprehension and refactoring.
- Monitoring rules fail when log representation changes without a stable schema.
- Security filters are dangerous when approximate regex matching stands in for parsing.
- CI conditions need explicit treatment of no-match versus operational error.
- Database indexes and search engines apply the same selection idea with different data structures and guarantees.

## From the Field

A CI check runs `grep -q forbidden generated.log` under a fail-on-any-nonzero wrapper. An empty, valid report produces status 1 and fails the build as if the search crashed.

The repair is to encode the three-state contract: match, no match, and error. Flattening every nonzero status destroyed useful meaning.

## Engineering Review

### What problem does this solve?

It selects relevant text records from a defined input set using literal or pattern-based criteria.

### Why was it designed this way?

Separating the pattern, inputs, selected output, diagnostics, and status makes search composable in interactive and automated workflows.

### When should I use it?

Use it for line-oriented text, source trees, logs, and quick investigations whose representation is understood.

### When should I avoid it?

Avoid regex as a substitute for parsing structured or adversarial data when correctness depends on the structure.

### How does this make me a better engineer?

It teaches precise predicates, dialect awareness, scope control, and three-state result handling.

### How does this reduce waste?

Well-scoped searches replace manual browsing while preventing noisy results and false automation failures.

## Handbook Principle #16

> Define the input boundary, use the least powerful sufficient pattern, and preserve the difference between match, no match, and error.

## Practical Observation

In a disposable directory:

```bash
printf '%s\n' \
  'cost=5.00' \
  'cost=5000' \
  'status=ready' > records.txt

grep 'cost=5.00' records.txt
printf 'regex status=%s\n' "$?"
grep -F 'cost=5.00' records.txt
printf 'fixed status=%s\n' "$?"
```

Explain why the unescaped regex can select text beyond the intended literal value and why shell quoting alone does not change regex semantics.

## Looking Ahead

Search selects records. Chapter 17 broadens the data workflow to viewing, counting, ordering, selecting fields, and transforming text while preserving its representation contract.
