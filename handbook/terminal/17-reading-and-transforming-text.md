# Chapter 17 — Reading and Transforming Text

Unix text tools are powerful because each applies a small operation to a stream. Their correctness depends on the structure the bytes are assumed to represent.

The central idea is:

> Choose a text tool only after identifying the data's records, fields, ordering, encoding, and delimiter rules.

## 1. Text is structured by agreement

A byte stream does not inherently contain lines, columns, headers, or fields. Tools interpret structure through conventions:

```text
bytes → characters → records → fields → meaning
```

Common utilities often assume newline-delimited records. Some then split each record by a character or whitespace rule.

If a field can contain the chosen delimiter, the apparent table may not have the structure the command assumes. That is why a real CSV parser is different from `cut -d,`.

## 2. Display small files without disguising the operation

`cat` copies its inputs to standard output:

```bash
cat -- README.md
cat -- header.txt body.txt
```

Its core job is concatenation. A terminal happens to display the output when connected.

For a file larger than one screen, use a pager:

```bash
less README.md
```

`less` supports interactive navigation and search without requiring the entire file to be printed into terminal scrollback. Exit with `q`; search forward with `/pattern`.

## 3. Select the beginning or end

Use `head` and `tail` to inspect a bounded sample:

```bash
head -n 20 application.log
tail -n 50 application.log
```

Sampling reduces noise and cost, but it can hide anomalies outside the selected region. Never infer whole-file properties solely from the first convenient lines.

Follow a growing file where supported:

```bash
tail -f application.log
```

Following a pathname across log rotation differs by implementation and option. For production logs, service or observability tooling may provide a stronger interface.

## 4. Count the unit you actually need

`wc` can report line, word, and byte counts:

```bash
wc -l records.txt
wc -w records.txt
wc -c artifact.bin
```

A “line” count often counts newline characters. A final unterminated record can make the displayed number differ from a person's visual idea of lines.

Byte count and character count are also different in multibyte encodings. Use the metric that corresponds to the contract.

## 5. Ordering is controlled by comparison rules

`sort` orders records:

```bash
sort names.txt
sort -n measurements.txt
sort -t, -k2,2n metrics.csv
```

The last example assumes comma-delimited fields without embedded commas and requests a numeric comparison of field two. It is not a general CSV operation.

Locale affects collation. For reproducible byte-oriented ordering, a workflow may set:

```bash
LC_ALL=C sort names.txt
```

Human language ordering may require a locale-aware or domain-specific collation instead.

## 6. `uniq` compares adjacent records

`uniq` does not find duplicates scattered arbitrarily through a file. It compares neighboring records:

```bash
sort names.txt | uniq
sort names.txt | uniq -c
```

The `sort` stage groups equal values; `uniq` then collapses or counts adjacent groups.

If original order matters, sorting may destroy required information. A language, database, or `awk` program can track seen values while preserving first occurrence, but that is a different algorithm with memory costs.

## 7. Select delimited fields with `cut`

For a simple colon-delimited format:

```bash
cut -d: -f1,3 accounts.txt
```

This asks for fields one and three using `:` as the delimiter. It works when:

- records are line-delimited,
- the delimiter cannot appear unescaped inside a field,
- and missing fields have understood behavior.

It does not understand quoting, escaped delimiters, nested structures, or typed values.

## 8. Combine corresponding records with `paste`

`paste` joins lines from inputs side by side:

```bash
paste names.txt scores.txt
paste -d, names.txt scores.txt
```

This is useful when record positions correspond. If one file is missing a line or has a different order, the output can silently associate unrelated data.

A positional join needs a validated alignment invariant. When records have keys, use a key-aware join or database operation.

## 9. Translate or delete characters with `tr`

`tr` transforms character sets from standard input:

```bash
printf '%s\n' 'READY' | tr '[:upper:]' '[:lower:]'
printf '%s\n' 'a   b' | tr -s ' '
```

The second form squeezes repeated spaces. It does not normalize all whitespace unless the specified set says so.

`tr` is appropriate for character-level transformations. It has no concept of fields, words, or JSON strings.

## 10. Use `sed` for small stream edits

`sed` applies editing commands to a stream and normally writes the resulting records:

```bash
sed 's/^DEBUG: //' application.log
sed -n '/^ERROR:/p' application.log
```

The first substitutes once per selected line by default. The second suppresses automatic printing and explicitly prints matching lines.

In-place editing flags differ between GNU and BSD `sed` and combine transformation with mutation. Prefer writing to a new file, validating it, and replacing deliberately when correctness matters.

## 11. Use `awk` when records have fields and rules

`awk` combines pattern selection with field-aware actions:

```bash
awk -F, '$3 == "error" { print $1, $2 }' events.txt
```

By default, an input line is a record, `$0` is the full record, `$1` through `$NF` are fields, and `NF` is the number of fields.

This example still is not a robust CSV parser. `-F,` treats commas as separators without implementing quoted CSV fields.

Use `awk` when the data contract genuinely fits record-and-field processing. Promote growing programs into readable files or a general-purpose language rather than maintaining punctuation-heavy one-liners.

## 12. Keep headers out of numeric transformations

Human-readable tables often mix labels and data:

```text
service,count
api,12
worker,3
```

A numeric sort over the full stream must define header behavior. One approach is to preserve it separately:

```bash
{
  head -n 1 metrics.txt
  tail -n +2 metrics.txt | sort -t, -k2,2n
}
```

`tail -n +2` is widely available but should be checked for the target environment. More importantly, the braces and redirections are shell syntax, not features of `sort`.

## 13. Materialization changes resource behavior

Many tools stream records and keep limited state. Others need broader knowledge:

- `head` can stop after a prefix,
- `tr` can transform incrementally,
- `sort` must determine global order and may use memory plus temporary storage,
- duplicate tracking can grow with the number of distinct values.

An apparently simple pipeline can therefore have disk, memory, latency, and temporary-file implications. Test with representative scale, not only a three-line fixture.

## 14. Preserve diagnostics and statuses

Consider:

```bash
producer | sort | uniq -c
```

The visible result may look plausible even if `producer` emitted incomplete data or a middle stage failed. Chapter 9 explained pipeline status; practical data work must apply it.

Inspect intermediate stages while developing:

```bash
producer > raw.txt
sort raw.txt > sorted.txt
uniq -c sorted.txt > counts.txt
```

Materializing each stage is not always the final design, but it makes contracts observable while debugging.

## 15. Know when text tools stop fitting

Escalate to a format-aware tool or programming language when the input has:

- quoted delimiters,
- nested structures,
- multiline records,
- schemas and types,
- escaping rules,
- binary encoding,
- transactions,
- or error recovery requirements.

Examples include JSON processors, CSV libraries, SQL engines, XML parsers, and application APIs.

The goal is not to prove a pipeline can parse the data. It is to choose the smallest abstraction that preserves meaning.

## 16. A worked transformation

Given this controlled, comma-delimited input:

```text
api,200,43
worker,500,12
api,500,7
worker,200,58
```

Count error records per service:

```bash
awk -F, '$2 >= 500 { print $1 }' events.txt |
  sort |
  uniq -c |
  sort -nr
```

Each stage has one contract:

```text
awk     selects error records and emits service names
sort    groups equal names
uniq -c counts adjacent groups
sort -n orders counts numerically
```

The pipeline is valid only while the simple delimiter contract holds.

## 17. Common misconceptions

### “`cat` is the file viewer”

It concatenates inputs to output. A pager is better for interactive navigation through large text.

### “`uniq` removes all duplicates”

It operates on adjacent equal records.

### “`cut -d,` parses CSV”

It splits on a delimiter and does not implement CSV quoting rules.

### “Sorting is neutral”

It changes order according to locale and comparison options, potentially destroying meaningful input order.

### “A one-liner uses no resources”

Global operations may materialize data in memory or temporary storage.

## 18. Platform comparison

| Task | Unix text tools | PowerShell |
| --- | --- | --- |
| Select records | `grep`, `sed`, `awk` | `Where-Object`, `Select-String` |
| Select fields | `cut`, `awk` | `Select-Object` properties |
| Order values | `sort` | `Sort-Object` |
| Group values | `uniq -c` after ordering | `Group-Object` |
| Pipeline representation | bytes interpreted as text | .NET objects between cmdlets |

PowerShell avoids some delimiter parsing when objects remain inside its pipeline. Native-process boundaries still return to byte streams.

## Core Computer Science Concept

Text pipelines implement **relational-style operations over streams**: selection, projection, ordering, grouping, and aggregation.

Their simplicity comes from a lightweight representation. That same representation lacks schemas, types, and escaping unless the workflow supplies them.

## Engineering Connections

- Log analysis depends on stable event representation.
- Data pipelines separate transformations into observable stages.
- Database queries provide typed, schema-aware versions of similar operations.
- Build systems use hashing and manifests when timestamps or text comparisons are insufficient.
- Streaming architectures trade global knowledge for bounded memory and lower latency.

## From the Field

A team groups comma-delimited export rows using `cut`. A customer name later contains a comma inside valid CSV quotes. Counts remain syntactically plausible but become semantically wrong.

The failure is not a missing `cut` option. The representation outgrew delimiter-only processing and requires a CSV parser.

## Engineering Review

### What problem does this solve?

It provides small composable operations for inspecting and transforming line-oriented text.

### Why was it designed this way?

Stable stream interfaces let independent tools implement selection, projection, ordering, and aggregation without one monolithic program.

### When should I use it?

Use these tools when the input has a simple documented text contract and the required transformation fits their model.

### When should I avoid it?

Avoid delimiter-based shortcuts for structured, adversarial, nested, multiline, or strongly typed data.

### How does this make me a better engineer?

It teaches you to reason about representation, ordering, streaming state, resource costs, and intermediate contracts.

### How does this reduce waste?

Small tools make exploratory transformations fast while clear escalation boundaries prevent fragile pipelines from becoming permanent debt.

## Handbook Principle #17

> Select text tools from the data's actual record and field contract, and escalate as soon as the representation stops preserving meaning.

## Practical Observation

Create the `events.txt` fixture from Section 16 and run each stage separately. Then append:

```text
"api,east",500,3
```

Explain exactly where the assumed representation fails. Reimplement the selection with a CSV-aware tool in a language available to you, and compare the resulting service identity.

## Looking Ahead

These utilities receive arguments only after the shell evaluates the command line. Chapter 18 makes quoting, expansion, and redirection order explicit so the intended data reaches each tool intact.
