# Chapter 67 — Structured Inputs, Outputs, and Data Formats

Automation exchanges bytes, but engineers reason about records, fields, identifiers, numbers, and states. A data format is reliable only when both producer and consumer agree on how those meanings are represented and validated.

The central idea is:

> Define record boundaries, encoding, schema, and compatibility before choosing parsing commands; syntax alone is not a data contract.

## 1. Bytes need a declared interpretation

A file, pipe, or response body is a byte sequence. To recover data, the consumer needs several layers of agreement:

```text
bytes
  └─ encoding and framing
       └─ syntax and data model
            └─ schema and field meaning
                 └─ domain validation
```

UTF-8 answers how Unicode text becomes bytes. JSON answers how strings, numbers, arrays, objects, booleans, and null are serialized. A schema can require an `id` string. Domain rules decide whether that identifier names an existing object the caller may use.

Passing syntax validation proves only one layer. `{"port": 99999}` can be valid JSON and invalid network configuration.

## 2. Lines are delimiters, not universal records

Line-oriented text composes well when a line is the complete record and newline is forbidden or escaped inside fields. Logs, simple identifiers, and one-value-per-line lists can fit this model.

Problems begin when an unescaped field can itself contain a newline:

```text
id=42 message=first line
second line
```

A line-counting consumer sees two records while the producer intended one. Splitting on spaces or `:` creates the same ambiguity when those characters are valid data.

Define:

- line ending accepted and emitted;
- whether the final record requires a terminator;
- whether blank lines are records, separators, or ignored;
- escaping for delimiters and control characters;
- maximum line and record sizes;
- behavior for malformed or incomplete records.

Human-readable prose output is not automatically a stable line protocol. Alignment, labels, color, localization, and warnings can change it.

## 3. Pathnames need lossless framing

On common Unix filesystems, a pathname component can contain any byte except null and `/`. Newline, tab, quote, wildcard, and leading dash are therefore valid filename content. A newline-delimited filename list cannot represent every pathname unambiguously.

Use null-delimited records when compatible tools exchange pathnames:

```bash
find "$root" -type f -print0 |
    while IFS= read -r -d '' path; do
        inspect_path "$path"
    done
```

The null byte cannot occur in a Unix pathname, so it is an unambiguous terminator. Both producer and consumer must opt into the convention; displaying null-delimited output in a terminal is not a useful review interface.

Never parse `ls` output. It is presentation for humans and can quote, escape, sort, color, or arrange names according to options, terminal, and locale.

Windows path rules differ, and PowerShell can pass path objects through its own pipeline. Crossing into a native text process requires an explicit serialization boundary again.

## 4. JSON has a small typed data model

JSON represents objects, arrays, strings, numbers, booleans, and null. A machine interface can use those types without inventing a delimiter grammar:

```json
{
  "schema": "inventory/v1",
  "generated_at": "2026-11-01T15:20:00Z",
  "items": [
    {
      "id": "srv-042",
      "enabled": true,
      "labels": ["edge", "blue"]
    }
  ]
}
```

Internet JSON is encoded as UTF-8. Standard JSON does not allow comments or trailing commas. Object member names should be unique; parsers can disagree about duplicates. Reject duplicate names at trust boundaries rather than accepting whichever value a library happens to retain.

Objects are semantically unordered. Do not use member order to encode priority. Use an array when sequence matters.

JSON numbers have interoperability limits. Many consumers use IEEE 754 binary64 values, which cannot exactly represent every large integer. Represent an identifier as a string, not a number, and define range and precision for actual quantities. Monetary values need an agreed unit and representation, such as integer minor units or a constrained decimal string.

## 5. One JSON value and JSON sequences differ

A single JSON document can contain an array of records. It is easy to validate as one unit but can require buffering and makes append or streaming awkward.

Newline-delimited JSON, often called JSON Lines or NDJSON, places one complete JSON value on each line. It supports streaming only when embedded newlines are escaped within JSON strings and the contract defines blank-line and final-newline behavior.

```json
{"id":"job-1","state":"ready"}
{"id":"job-2","state":"blocked"}
```

NDJSON is a framing convention around JSON, not the same representation as a JSON array. A standard JSON parser expecting one value will not accept two adjacent line values without a sequence-aware layer.

RFC 7464 defines a different JSON text sequence using the ASCII record-separator byte. Name the exact convention instead of saying only “streaming JSON.”

## 6. CSV is not `split(',')`

CSV represents tabular records, but deployed dialects differ in delimiter, quoting, escaping, line endings, encoding, header presence, and treatment of blank rows. In the commonly documented format, a quoted field can contain commas, quotes, and line breaks; an embedded quote is doubled.

```csv
id,description,enabled
42,"contains, a comma",true
43,"two
lines",false
44,"quoted ""word""",true
```

Splitting each physical line on commas corrupts all three interesting cases. Use a CSV library configured for the producer's dialect.

CSV supplies strings and rows, not a universal schema or type system. The contract must define column names, order, null versus empty, types, units, encoding, header rules, and additional-column behavior.

Data beginning with `=`, `+`, `-`, or `@` can be interpreted as a formula by some spreadsheet software. A CSV safe for a parser can become active content when opened in a spreadsheet. Treat export-to-spreadsheet as a separate security context with an explicit neutralization policy that does not silently alter machine data.

## 7. YAML optimizes authoring at a cost

YAML supports mappings, sequences, scalars, comments, multiple styles, tags, anchors, aliases, and schema-dependent type resolution. That expressiveness can make human-maintained configuration pleasant and machine contracts complicated.

Visually similar scalars can resolve to different types across YAML versions, schemas, and libraries. Anchors and aliases can construct shared or recursive graphs and can expand resource use. Tags can request application-specific types; unsafe loaders in some ecosystems have historically constructed executable objects.

For untrusted YAML:

- use a maintained safe loader that does not construct arbitrary objects;
- select and document the YAML version and schema behavior;
- limit input size, nesting, aliases, and expansion;
- reject duplicate mapping keys;
- validate the resulting data model against an application schema;
- emit canonical or consistently formatted output for review.

Do not edit YAML with line-oriented substitution when comments, block scalars, anchors, or duplicate-looking keys can change meaning. Parse, validate, modify the data model, and serialize while acknowledging that comments and style may not round-trip.

Use JSON for machine-to-machine interfaces when YAML's authoring features provide no value.

## 8. Encoding is part of the contract

“Text” does not identify an encoding. A consumer decoding UTF-8 bytes as a legacy code page can corrupt names without producing an obvious error.

Specify:

- character encoding, normally UTF-8 for new interoperable text;
- whether a byte-order mark is permitted;
- newline convention and normalization;
- behavior for invalid byte sequences;
- Unicode normalization policy where comparison matters;
- whether matching is case-sensitive and by which rules;
- maximum byte and character lengths.

Unicode allows visually identical text to have different code-point sequences. Do not normalize blindly: identifiers, filenames, signatures, and external protocols can require exact code points. Normalize only at a boundary whose domain contract defines it.

Decode bytes once near input, operate on text, then encode once near output. Repeated implicit conversions make it hard to locate corruption.

## 9. Null, missing, empty, and zero differ

These states often carry separate meanings:

```text
field absent       producer did not supply it or older version lacks it
field: null        producer explicitly represents no value
field: ""          present empty string
field: []          present empty collection
field: 0           present numeric zero
```

Do not collapse them unless the schema declares them equivalent. Defaults applied to missing values can differ from explicit null. CSV needs an application convention because an empty field alone cannot universally distinguish null from empty string.

Boolean text deserves the same care. Accepting every nonempty string as true makes `"false"` true in many programming languages.

## 10. A schema makes structure reviewable

A schema can define required fields, types, ranges, patterns, enumerations, nested shapes, and whether unknown fields are allowed. It lets producers and consumers test a shared contract before deployment.

A useful schema policy answers:

- which schema identifier or version applies;
- required, optional, and deprecated fields;
- type, range, unit, format, and maximum size;
- uniqueness and ordering requirements;
- unknown-field behavior;
- duplicate-key behavior before schema evaluation;
- defaulting and null rules;
- cross-field and domain invariants;
- error-reporting structure.

JSON Schema is one vocabulary for JSON instance constraints. Its dialect identifier matters; validators using different drafts or optional format behavior can produce different results. Pin and test the implementation rather than treating “JSON Schema” as one timeless runtime.

Schema validation does not authorize the request, prove external references exist, or make data safe to display in another context.

## 11. Validate in layers and fail closed

Process untrusted input through bounded stages:

1. limit bytes, records, nesting, and processing time;
2. decode with the declared encoding;
3. parse with duplicate and resource policies;
4. validate schema and types;
5. validate cross-field and domain invariants;
6. authorize referenced objects and requested actions;
7. create an immutable internal representation;
8. perform effects only after validation succeeds.

Reject the whole unit when partial acceptance is not defined. For batch interfaces, specify whether valid records proceed when others fail and how record-level results correlate to input.

Return errors with stable category, record or field location, and safe explanation. Do not echo secrets or unlimited invalid content into logs.

## 12. Keep machine output free of presentation

If stdout is the machine interface, write only contract data there. Send diagnostics to stderr. Disable color, progress bars, headings, and locale-dependent formatting in machine mode.

```text
tool inspect --format=json --no-color TARGET
```

A format flag should choose a documented schema, not merely replace spaces with braces. Include a schema or API version when independent evolution requires it.

Consider separate commands or flags for human and machine output. Human output can optimize scanning and explanations; machine output can optimize stability and explicit types.

Exit status still matters. Valid JSON describing an operational failure does not necessarily mean the process succeeded; document the relationship between result records and process status.

## 13. Design compatible evolution

Compatibility has two directions:

- a new producer sends data to an old consumer;
- a new consumer reads data from an old producer.

Additive optional fields are often compatible when consumers are designed to ignore unknown fields. They are not compatible when consumers reject extras or a new field changes the meaning of an old one. Removing, renaming, narrowing, or retyping a field is usually breaking.

Define behavior explicitly:

| Change | Typical strategy |
| --- | --- |
| add optional informational field | old consumers ignore; new consumers default when absent |
| add required field | new version or negotiated capability |
| extend enumeration | consumers preserve or reject unknown value predictably |
| change unit or type | new field or schema version |
| deprecate field | dual-read/write period with telemetry |
| change record framing | new media type, command version, or endpoint |

Do not use one `version` integer without defining what it versions and how unsupported values fail. A schema identifier such as `inventory/v1` is useful only when its document and compatibility policy are discoverable.

Test with old and new producer-consumer pairs. Compatibility is behavior, not a promise in release notes.

## 14. Know when shell text processing ends

Shell tools are effective for bounded line and null-delimited streams with simple fields. Stop composing ad hoc text filters when the task requires:

- nested objects or arrays;
- CSV quoting and multiline records;
- schema validation;
- exact decimal or large-integer behavior;
- complex Unicode handling;
- correlated per-record errors;
- safe updates that preserve structured meaning;
- limits on recursive or adversarial input.

Use a format-aware utility for a narrow transformation or a general-purpose language with a maintained parser and explicit data structures. Converting JSON to tab-separated text is safe only if the selected fields are guaranteed not to contain the delimiter or are encoded again.

## 15. Test adversarially small fixtures

A format test set should include:

- empty input and one empty record;
- missing, null, empty, zero, and false values;
- delimiter, quote, newline, backslash, and null-byte boundaries where applicable;
- non-ASCII text and invalid encoding;
- duplicate keys or headers;
- unknown and missing fields;
- minimum, maximum, and out-of-range numbers;
- deep nesting, large fields, and excessive record counts;
- old and new schema versions;
- truncated input at every structural boundary.

Keep fixtures minimal enough that a reviewer can see which rule each case proves. Fuzzing can supplement these examples but does not replace a written contract.

## Common Misconceptions

- “One line always equals one record.” Only a format that forbids or escapes newline in fields makes that true.
- “CSV is comma-separated text.” Quoting permits commas, quotes, and physical line breaks inside fields.
- “Valid JSON is valid input.” Syntax can pass while schema, domain, or authorization fails.
- “YAML is JSON with comments.” Its tags, aliases, schemas, and scalar rules create a broader model.
- “UTF-8 solves all text comparison.” Encoding does not decide normalization, case, or identifier semantics.

## Core Computer Science Concept

Serialization is an **isomorphism contract between an in-memory model and bytes**. Reliability depends on whether encoding and decoding preserve the distinctions the domain cares about, including boundaries, types, order, absence, and precision.

## Engineering Connections

- Shell quoting preserves process argument boundaries; serialization preserves record and field boundaries.
- HTTP media types and content negotiation identify representation contracts over a network.
- Filesystem pathnames demonstrate why presentation-oriented line parsing can be lossy.
- Schema and compatibility rules let automation components evolve without silent reinterpretation.

## From the Field

A cleanup tool reads server names from `inventory.csv` using `cut -d, -f1`. One quoted description contains a newline, shifting subsequent physical lines and causing a description fragment to be treated as a server. A real CSV parser plus a schema rejects the malformed identifier before any deletion; more shell quoting cannot repair the missing record model.

## Engineering Review

### What problem does this solve?

It preserves record boundaries, types, encoding, and meaning when automation exchanges data across files, processes, and services.

### Why was it designed this way?

Bytes carry no inherent records or domain types, so producers and consumers need an explicit representation and validation contract.

### When should I use it?

Use this approach for every machine-readable input, output, configuration, event stream, or persisted intermediate artifact.

### When should I avoid it?

Avoid inventing a custom text grammar when a maintained format and parser already fit the data and its trust boundary.

### How does this make me a better engineer?

It teaches you to distinguish parsing from validation and to preserve every meaningful state through serialization.

### How does this reduce waste?

It prevents delimiter corruption, encoding incidents, parser disagreement, incompatible evolution, and repeated format-specific repair code.

## Handbook Principle #67

> Choose a format only after defining its boundaries, encoding, schema, limits, and compatibility behavior—and stop using shell text parsing when those rules exceed lines.

## Practical Observation

Create a disposable fixture set containing a line with an embedded newline, a filename with spaces and wildcard characters, CSV with a quoted comma and multiline field, and JSON with duplicate keys and an oversized integer. Run the parsers you intend to use, record disagreements, then write the explicit policy that removes each ambiguity. Delete the fixtures afterward.

## Looking Ahead

Structured data often marks the boundary where shell stops being the clearest tool. Chapter 68 introduces Python programs, modules, functions, collections, context managers, exceptions, and standard-library discovery for maintainable automation.

## References

- [RFC 8259 — The JavaScript Object Notation Data Interchange Format](https://www.rfc-editor.org/rfc/rfc8259)
- [RFC 7493 — The I-JSON Message Format](https://www.rfc-editor.org/rfc/rfc7493)
- [RFC 7464 — JSON Text Sequences](https://www.rfc-editor.org/rfc/rfc7464)
- [RFC 4180 — Common Format and MIME Type for CSV Files](https://www.rfc-editor.org/rfc/rfc4180)
- [YAML 1.2.2 Specification](https://yaml.org/spec/1.2.2/)
- [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12)
