# Chapter 69 — Files, Paths, Text, and Structured Data in Python

Filesystem automation crosses several contracts at once: path interpretation, object type, permissions, encoding, structured syntax, metadata, concurrency, and recovery. A path-looking string proves none of them.

The central idea is:

> Treat a filesystem path as a reference to changing external state, validate every representation boundary, and publish output without exposing partial content.

## 1. Paths model platform semantics

`pathlib.Path` joins, inspects, and operates on paths using the current platform's rules:

```python
from pathlib import Path

root = Path("data")
source = root / "input" / "records.json"
```

The `/` operator joins path components; it does not open or validate them. `Path` preserves relative versus absolute form, and relative paths are interpreted from the process working directory.

Do not build paths by concatenating separators:

```python
source = root_text + "/input/" + filename  # fragile
```

Windows drive and UNC paths, POSIX roots, separators, reserved names, and case behavior differ. `PurePosixPath` and `PureWindowsPath` can manipulate a foreign path syntax without accessing that filesystem; `Path` is for the host filesystem.

A path can name a regular file, directory, symbolic link, socket, device, missing entry, or an object that changes between inspection and use.

## 2. Lexical paths and resolved paths answer different questions

`Path.absolute()` makes a path absolute without resolving symbolic links. `Path.resolve()` resolves links and removes `..` components as far as its mode permits.

Resolution is not universal authorization. A path can change after resolution, a mount can redirect access, filesystem case rules vary, and a caller can still lack permission. Prefix comparisons on path strings are particularly unsafe:

```text
/safe/project-old starts with /safe/project as text
```

When confining access beneath a root, use platform-appropriate open and traversal controls, reject links if the contract requires it, and consider operating-system APIs that bind checks to opened handles. A pre-check followed by a later open has a time-of-check/time-of-use race.

Use `resolve(strict=True)` only when existence and link resolution at that moment are intended requirements. Do not call it reflexively on an output that does not yet exist.

## 3. Existence helpers can collapse useful errors

Methods such as `exists()`, `is_file()`, and `is_dir()` return convenient Boolean answers and can treat missing, inaccessible, or invalid paths similarly. When the distinction matters, perform the intended operation and handle its specific `OSError` subclass.

```python
from pathlib import Path


def load_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except FileNotFoundError as exc:
        raise ValueError(f"input does not exist: {path}") from exc
    except PermissionError as exc:
        raise ValueError(f"input is not readable: {path}") from exc
```

Checking `exists()` before `read_bytes()` does not eliminate the need to catch failure; the entry can disappear or change between calls.

Distinguish symbolic-link policy. Most ordinary operations follow links. `lstat()` and `is_symlink()` inspect the link itself, while newer APIs expose `follow_symlinks` controls for selected operations.

## 4. Choose bytes or text at the boundary

Binary input is bytes. Text input decodes bytes using an encoding and error policy:

```python
with path.open("r", encoding="utf-8", errors="strict") as stream:
    text = stream.read()
```

Always declare encoding for persisted or exchanged text. A platform default can differ by host, locale, and interpreter configuration.

`errors="strict"` prevents silent replacement of invalid data. Replacement or escape error handlers are appropriate only when the contract explicitly prefers partial display over rejection.

Newline translation is another boundary. For JSON, ordinary text mode is usually appropriate. For CSV, Python's `csv` module requires opening files with `newline=""` so the library, not the text layer, owns CSV newline handling.

Avoid reading an unbounded file into memory. Check trusted metadata only as an initial limit—file size can change—and use bounded or streaming parsing where adversarial size matters.

## 5. Context managers close resources

Use `with` so files close when parsing or transformation raises:

```python
import json
from pathlib import Path


def load_json(path: Path) -> object:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)
```

`Path.read_text()` and `read_bytes()` open, read, and close conveniently for bounded data. An explicit context is clearer when streaming, configuring newline, processing several operations, or handling failure stages separately.

Closing a file flushes Python buffers but does not by itself promise power-loss durability. Durability requirements can involve `flush`, `os.fsync`, directory synchronization, storage hardware, and application recovery.

## 6. Parse JSON with an application policy

Python's `json` module maps objects to dictionaries, arrays to lists, strings to `str`, numbers to numeric types, booleans to `bool`, and null to `None`. Add the interoperability policies from Chapter 67.

By default, duplicate JSON object names are accepted and later values replace earlier ones. Reject them when ambiguity is unsafe:

```python
def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON member: {key}")
        result[key] = value
    return result
```

Pass it as `object_pairs_hook=unique_object`. Also decide whether non-finite numbers such as `NaN` are acceptable; strict interoperable JSON normally rejects them. On output, `allow_nan=False` prevents emitting those extensions.

Catch `json.JSONDecodeError` to add safe path, line, and column context. Do not echo an entire sensitive document in the error.

## 7. Validate the parsed model

Parsing produces Python values, not trusted domain objects. Validate exact types and constraints before effects:

```python
def validate_record(value: object, source: Path) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"record must be an object: {source}")

    identifier = value.get("id")
    enabled = value.get("enabled")

    if not isinstance(identifier, str) or not identifier:
        raise ValueError(f"id must be a nonempty string: {source}")
    if type(enabled) is not bool:
        raise ValueError(f"enabled must be a boolean: {source}")

    return {"id": identifier, "enabled": enabled}
```

The exact `type(enabled) is bool` check is deliberate because `bool` is a subclass of `int` in Python. For most application classes, `isinstance` is the extensible check; validation rules decide when exact types matter.

Define unknown-field behavior. Silently discarding a misspelled field can be dangerous, while rejecting every extension can prevent compatible evolution. Tie the rule to a schema version.

## 8. Use the CSV library for records

Open CSV with `newline=""` and configure its dialect:

```python
import csv

with path.open(encoding="utf-8", newline="") as stream:
    reader = csv.DictReader(stream)
    for row_number, row in enumerate(reader, start=2):
        validate_row(row, row_number)
```

`DictReader` does not infer a schema. Values are normally strings or `None` in certain malformed-width cases. Validate header names, duplicate headers, row widths, null conventions, types, and size limits explicitly.

When writing, pass field names and choose behavior for extra keys. Spreadsheet formula interpretation remains a downstream context, not something `csv.writer` automatically neutralizes.

Do not use `str.split(",")`, regular expressions, or line iteration as a CSV parser.

## 9. Traverse with an explicit link and error policy

`Path.iterdir()` reads one directory. `glob` and `rglob` select patterns. `Path.walk()` and `os.walk()` traverse trees.

A safe traversal contract states:

- root and permitted scope;
- whether traversal is recursive;
- whether directory symlinks are followed;
- file types accepted;
- order requirements;
- maximum depth, files, and bytes;
- behavior when a directory changes or becomes inaccessible;
- whether mount boundaries may be crossed.

Following links can escape the apparent root or create cycles. Not following links can omit intended data. Neither policy is universally correct.

Sort paths when deterministic output matters. Filesystem enumeration order is not a stable business ordering.

For `Path.walk`, supply an `on_error` function if ignored scanning errors would make a partial result look complete. A successful loop over only readable directories is not necessarily a successful inventory.

## 10. Temporary directories isolate multi-file work

`tempfile.TemporaryDirectory` securely creates an owned directory and attempts cleanup at context exit:

```python
from pathlib import Path
from tempfile import TemporaryDirectory

with TemporaryDirectory(prefix="inventory-test-") as temporary:
    root = Path(temporary)
    input_path = root / "input.json"
    input_path.write_text("{}\n", encoding="utf-8")
    run_transform(root)
```

This is ideal for tests and intermediate work whose entire lifetime matches the block. Cleanup can fail because files remain open, permissions change, or another process interferes. Do not ignore cleanup errors by default.

Use `NamedTemporaryFile` when a named file is required, but understand Windows reopening and delete-sharing behavior. Close the temporary file before asking another process to open it unless the selected cross-platform pattern says otherwise.

Never use deprecated `tempfile.mktemp`; generating a name separately from creation permits a race.

## 11. Publish with same-directory replacement

Writing directly to the final path can expose a truncated or partially serialized file. Instead:

1. create a unique temporary file in the destination directory;
2. write and validate complete content;
3. flush and, if required, synchronize it;
4. close it;
5. replace the destination with the temporary path;
6. clean the temporary path after failure.

Creating beside the destination keeps the final rename on one filesystem. `Path.replace()` replaces an existing target using platform rename semantics.

Replacement makes one pathname switch from old content to new content under supported same-filesystem semantics. It does not create a transaction across several files, prevent competing writers, preserve old metadata, or guarantee survival after sudden power loss.

If the destination is a security-sensitive configuration file, define ownership, permissions, access-control lists, extended attributes, and link behavior before replacement. A new temporary file inherits creation policy, not necessarily the target's metadata.

## 12. Metadata is data when the contract says so

File content is only part of filesystem state. Relevant metadata can include:

- owner and group;
- permission bits and ACLs;
- timestamps;
- extended attributes and labels;
- link type and count;
- sparse allocation;
- platform-specific flags;
- alternate data streams;
- durability and synchronization state.

`shutil.copy`, `copy2`, and `copystat` preserve different subsets, with platform limitations. No single high-level copy promises every metadata feature everywhere.

State explicitly whether automation generates a new artifact, edits an existing object, or clones one. A generated report often should use fresh controlled permissions; an in-place configuration update may need verified metadata preservation.

## 13. A complete directory transformation

This Python 3.11+ program reads top-level `*.json` records, validates them, and publishes a deterministic summary. The output is excluded if it lives inside the input directory:

```python
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path


class InputError(Exception):
    """A controlled error in an input record."""


def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise InputError(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def load_record(path: Path) -> dict[str, object]:
    try:
        with path.open(encoding="utf-8") as stream:
            value = json.load(stream, object_pairs_hook=unique_object)
    except json.JSONDecodeError as exc:
        raise InputError(
            f"invalid JSON in {path}: line {exc.lineno}, column {exc.colno}"
        ) from exc

    if not isinstance(value, dict):
        raise InputError(f"record must be an object: {path}")

    expected = {"id", "enabled"}
    if set(value) != expected:
        raise InputError(
            f"record fields must be exactly {sorted(expected)}: {path}"
        )

    identifier = value["id"]
    enabled = value["enabled"]
    if not isinstance(identifier, str) or not identifier:
        raise InputError(f"id must be a nonempty string: {path}")
    if type(enabled) is not bool:
        raise InputError(f"enabled must be a boolean: {path}")

    return {"id": identifier, "enabled": enabled}


def build_summary(input_dir: Path, output_path: Path) -> dict[str, object]:
    if not input_dir.is_dir():
        raise InputError(f"input is not a directory: {input_dir}")

    output_resolved = output_path.resolve()
    records: list[dict[str, object]] = []
    seen: set[str] = set()

    for path in sorted(input_dir.glob("*.json")):
        if path.resolve() == output_resolved:
            continue
        if path.is_symlink() or not path.is_file():
            raise InputError(f"input must be a regular non-link file: {path}")

        record = load_record(path)
        identifier = str(record["id"])
        if identifier in seen:
            raise InputError(f"duplicate record id: {identifier}")
        seen.add(identifier)
        records.append(record)

    records.sort(key=lambda item: str(item["id"]))
    return {
        "schema": "inventory-summary/v1",
        "total": len(records),
        "enabled": sum(record["enabled"] is True for record in records),
        "items": records,
    }


def write_json_replacing(path: Path, document: object) -> None:
    if not path.parent.is_dir():
        raise InputError(f"output directory does not exist: {path.parent}")

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            json.dump(
                document,
                stream,
                allow_nan=False,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())

        temporary_path.replace(path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("output", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary = build_summary(args.input_dir, args.output)
        write_json_replacing(args.output, summary)
    except (InputError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

The example is for an isolated directory whose contents are trusted not to change concurrently. It intentionally rejects symlink inputs and exact-schema deviations. It does not lock against competing writers or preserve metadata from an existing output.

## 14. Test in a disposable tree

Use `TemporaryDirectory` to create fixtures for:

- zero, one, and several records in different enumeration order;
- duplicate IDs across files;
- duplicate JSON member names;
- invalid UTF-8 and malformed JSON;
- missing, unknown, null, and wrong-type fields;
- a symlink input where the platform permits it;
- an output inside and outside the input directory;
- a pre-existing valid output followed by a failed run;
- forced serialization or replacement failure;
- filenames containing spaces and non-ASCII characters;
- concurrent modification if the production contract must handle it.

After each failed run, assert that an old output remains valid and no temporary file remains. A happy-path content assertion alone cannot prove safe publication.

Do not point the example at a real configuration or data directory. Its exact-schema policy and replacement behavior are intentionally narrow.

## Common Misconceptions

- “A `Path` object is safer than a string.” It models path operations; authorization and race policy still belong to the program.
- “Checking `exists()` prevents open failures.” State can change, and Boolean helpers can hide why access failed.
- “Valid JSON is a valid record.” Schema and domain validation still apply.
- “Rename makes the whole update transactional.” It covers one namespace replacement, not several files, metadata, or arbitrary durability.
- “A copy preserves the file.” Content and different metadata subsets require separate guarantees.

## Core Computer Science Concept

Filesystem automation is **stateful I/O over a mutable namespace**. Paths name entries, handles access objects, encodings map bytes to text, parsers map text to values, and replacement publishes a new namespace binding under platform constraints.

## Engineering Connections

- Context managers replace ad hoc cleanup with explicit resource lifetime.
- Schema validation carries Chapter 67's representation contract into Python values.
- Same-directory temporary replacement is the file analogue of staging and committing one bounded result.
- Link policy, metadata, and permissions connect application logic to operating-system security boundaries.

## From the Field

A formatter opens a production configuration with `"w"` before parsing the proposed replacement. The proposed JSON is invalid, but opening already truncated the working file. Writing and validating in the destination directory, then replacing only after success, keeps the old valid configuration available on failure.

## Engineering Review

### What problem does this solve?

It lets automation read, validate, transform, and publish filesystem data without assuming paths, text, structure, or replacement are trivial.

### Why was it designed this way?

Filesystem state changes concurrently and representation has several layers, so each boundary needs explicit validation and recovery behavior.

### When should I use it?

Use these patterns for bounded file transformations, generated reports, configuration preparation, and structured directory inventories.

### When should I avoid it?

Avoid treating this single-file pattern as a database transaction, security confinement mechanism, or multi-writer coordination protocol.

### How does this make me a better engineer?

It makes you distinguish path syntax, object identity, bytes, text, parsed values, metadata, and published state.

### How does this reduce waste?

It prevents truncated outputs, encoding corruption, link surprises, temporary-file leaks, nondeterministic artifacts, and repeated handwritten parsers.

## Handbook Principle #69

> Validate from path through domain model, stage output beside its destination, and claim only the replacement, metadata, and durability guarantees you actually implement.

## Practical Observation

Save the complete program in a disposable directory and build the listed fixtures with `TemporaryDirectory`. Verify deterministic output and each rejection case, then simulate a failure after creating a valid old output and prove the old JSON remains parseable. Inspect permissions and timestamps before and after replacement, and delete the tree.

## Looking Ahead

Files are one external boundary. Chapter 70 applies the same discipline to child processes and HTTP services: argument vectors, streams, timeouts, cancellation, authentication, status, retries, and response validation.

## References

- [Python `pathlib` documentation](https://docs.python.org/3.14/library/pathlib.html)
- [Python `tempfile` documentation](https://docs.python.org/3.14/library/tempfile.html)
- [Python `json` documentation](https://docs.python.org/3.14/library/json.html)
- [Python `csv` documentation](https://docs.python.org/3.14/library/csv.html)
- [Python `os` documentation](https://docs.python.org/3.14/library/os.html)
- [Python `shutil` documentation](https://docs.python.org/3.14/library/shutil.html)
