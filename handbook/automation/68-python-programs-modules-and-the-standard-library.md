# Chapter 68 — Python Programs, Modules, and the Standard Library

Python becomes useful for automation when a command is separated into testable computation, controlled input and output, and a thin process entry point. Saving shell commands inside a Python file does not create that structure automatically.

The central idea is:

> Put domain behavior in importable functions, keep external effects at explicit boundaries, and let one small entry point translate between process status and Python outcomes.

## 1. Select the interpreter intentionally

The command `python` resolves through the current process environment. It can name different installations across hosts, terminals, virtual environments, schedulers, and IDEs.

Inspect the interpreter that will run the program:

```text
python --version
python -c "import sys; print(sys.executable); print(sys.version)"
```

On Windows, the `py` launcher can select an installed version such as `py -3.14`. On Unix-like systems, environments often expose `python3`. These names are conventions, not proof of one universal path.

Declare the minimum supported Python version from the syntax and library behavior the program uses, then test that version. A type-union expression such as `str | None` requires newer Python than older `Optional[str]` syntax.

Chapter 71 will separate interpreter installation, virtual environments, packages, and application entry points. For now, run examples with one known interpreter and the standard library only.

## 2. Execution creates a top-level module

Python can execute a file, module, package, command string, or standard input:

```text
python tool.py
python -m package.module
python -c "print('hello')"
```

The first user-specified module runs in the top-level environment with `__name__ == "__main__"`. Imported modules normally receive their import name instead.

Use an entry-point guard:

```python
def main() -> int:
    print("hello")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Importing this file defines `main` without running the command. Direct execution calls it and converts its integer result into process exit status. `raise SystemExit(...)` is explicit and works naturally with later packaging entry points.

Avoid top-level network calls, file mutations, argument parsing, or environment validation. Imports happen in test discovery, documentation tools, child processes, and other modules where those effects are surprising.

## 3. Modules create namespaces and reuse boundaries

A `.py` file is a module. A package organizes related modules, commonly in a directory with package metadata and, for regular packages, an `__init__.py` file.

```text
inventory_tool/
├── __init__.py
├── __main__.py
├── cli.py
└── summarize.py
```

One useful division is:

- `summarize.py` contains domain transformations;
- `cli.py` parses arguments and reports results;
- `__main__.py` calls the CLI for `python -m inventory_tool`;
- `__init__.py` exposes only deliberate package interfaces.

Imports bind names to module objects:

```python
from collections import Counter

import json
```

Prefer explicit imports. Wildcard imports obscure where names came from and make compatibility review harder.

Do not name a local module `json.py`, `pathlib.py`, or after another dependency. The import search path can select that file instead of the intended library. Diagnose uncertain imports with `module.__file__` and `sys.path`, but do not patch `sys.path` casually to hide a packaging error.

## 4. Names refer to objects

Python variables are names bound to objects. Assignment does not copy a mutable object:

```python
first = ["a"]
second = first
second.append("b")
assert first == ["a", "b"]
```

This matters when functions share lists, dictionaries, sets, or application objects. Copy only when the contract needs independent state, and choose shallow versus deep copying deliberately.

Common built-in structures have different semantics:

| Type | Useful property |
| --- | --- |
| `list` | ordered mutable sequence, duplicates allowed |
| `tuple` | ordered immutable sequence |
| `dict` | key-to-value mapping, insertion order retained |
| `set` | unique hashable members, no business ordering contract |
| `str` | immutable Unicode text |
| `bytes` | immutable byte sequence |

Do not choose a set merely to remove duplicates when first-seen order matters. Do not use a list when keys define identity and duplicate keys should be rejected.

## 5. Functions should make data flow visible

A function should have a narrow purpose, explicit parameters, a stable return value, and documented side effects:

```python
from collections.abc import Iterable


def normalize_names(names: Iterable[str]) -> list[str]:
    result: list[str] = []
    for name in names:
        normalized = name.strip().casefold()
        if normalized:
            result.append(normalized)
    return result
```

The type annotations help readers and static tools; Python does not enforce them automatically at runtime. Validate untrusted values at the boundary.

Avoid mutable default arguments:

```python
def add_label(label: str, labels: list[str] = []) -> list[str]:  # unsafe
    labels.append(label)
    return labels
```

That list is created once when the function is defined and reused across calls. Use `None` as a sentinel when a new collection is required:

```python
def add_label(label: str, labels: list[str] | None = None) -> list[str]:
    result = [] if labels is None else list(labels)
    result.append(label)
    return result
```

Do not hide dependencies in module globals when a parameter would make testing and ownership clearer.

## 6. Iteration separates production from storage

An iterable can produce values one at a time. A list comprehension builds a list eagerly:

```python
active_ids = [item["id"] for item in items if item["enabled"]]
```

A generator expression produces values lazily:

```python
active_ids = (item["id"] for item in items if item["enabled"])
```

Lazy iteration can reduce memory and allow streaming, but it also defers work and failure until consumption. A generator tied to an open file must not escape the file's lifetime accidentally.

Prefer a plain loop when it needs multiple branches, diagnostics, counters, or error context. Compact syntax is not a goal when it hides policy.

Avoid mutating a collection while iterating over it unless the algorithm explicitly permits it. Iterate over a copy or build a new result when membership changes.

## 7. Exceptions report exceptional outcomes

An exception unwinds normal control flow until a matching handler is found. Catch only exceptions the current layer can interpret or enrich:

```python
import json
from pathlib import Path


def load_document(path: Path) -> object:
    try:
        with path.open(encoding="utf-8") as stream:
            return json.load(stream)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"invalid JSON in {path}: line {exc.lineno}, column {exc.colno}"
        ) from exc
```

`raise ... from exc` preserves the cause while providing domain context. The entry point can catch `ValueError` and report a controlled user error without pretending every programmer defect is expected.

Avoid `except Exception: pass`. It hides failures, can leave partial state, and makes success indistinguishable from skipped work. Do not catch `BaseException` for ordinary recovery; it includes process-level events such as `KeyboardInterrupt` and `SystemExit`.

Use `else` for work that should run only when the protected operation succeeds, and `finally` for cleanup that must be attempted whether or not an exception occurs. Cleanup itself can fail, so preserve the most useful causal evidence.

## 8. Context managers define resource lifetime

The `with` statement enters a context and guarantees its exit protocol is invoked:

```python
from pathlib import Path


def read_text(path: Path) -> str:
    with path.open(encoding="utf-8") as stream:
        return stream.read()
```

The file closes after the block even if reading raises. Context managers also govern locks, temporary directories, database transactions, and redirected streams.

They do not guarantee the desired business outcome. Closing a file does not make a multi-file update atomic; releasing a lock does not roll back external changes.

Build custom context managers only when one resource lifetime truly has enter and exit semantics. `contextlib` provides helpers, but a plain `try` and `finally` can be clearer for unique cleanup.

## 9. Keep pure computation separate from effects

Pure functions derive output from arguments without reading hidden state or changing the outside world:

```python
from collections import Counter
from collections.abc import Iterable


def count_names(names: Iterable[str]) -> dict[str, int]:
    normalized = (name.strip().casefold() for name in names)
    return dict(Counter(name for name in normalized if name))
```

Time, randomness, environment variables, files, network calls, and process execution are effects. Keep them near adapters and pass their results into domain functions.

This separation allows tests to exercise policy with ordinary values. It also exposes where timeouts, credentials, cleanup, and partial failure belong.

Not every function must be mathematically pure. The goal is to keep effect boundaries visible rather than scattering them through transformations.

## 10. Parse command lines with a library

`argparse` supplies help, usage errors, option parsing, and type conversion in the standard library:

```python
import argparse
from collections.abc import Sequence


def positive_integer(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=positive_integer, default=10)
    parser.add_argument("names", nargs="+")
    return parser.parse_args(argv)
```

Passing `argv` makes parsing testable without rewriting global `sys.argv`. Usage failures conventionally exit nonzero through `argparse`; domain failures should have separately documented status behavior.

Do not parse a command line by joining arguments into one string and splitting again. The operating system already supplied argument boundaries.

## 11. A complete standard-library command

This program normalizes names, counts them, and emits one JSON object on stdout. Diagnostics and usage remain separate:

```python
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Iterable, Sequence


def positive_integer(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def normalize(names: Iterable[str], minimum_length: int) -> list[str]:
    result: list[str] = []
    for name in names:
        candidate = name.strip().casefold()
        if len(candidate) >= minimum_length:
            result.append(candidate)
    return result


def summarize(names: Iterable[str]) -> dict[str, object]:
    counts = Counter(names)
    return {
        "schema": "name-summary/v1",
        "total": counts.total(),
        "counts": dict(sorted(counts.items())),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Normalize and count names."
    )
    parser.add_argument(
        "--minimum-length",
        type=positive_integer,
        default=1,
        help="ignore normalized names shorter than this value",
    )
    parser.add_argument("names", nargs="+", help="names to count")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    names = normalize(args.names, args.minimum_length)
    document = summarize(names)
    json.dump(document, sys.stdout, ensure_ascii=False, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

The domain functions accept and return ordinary values. `main` owns argument and stream boundaries. The guard makes import safe. The schema identifier gives consumers a named contract rather than an accidental dictionary shape.

`Counter.total()` requires a modern Python version; a project supporting older versions would use `sum(counts.values())` or raise its declared minimum.

## 12. Import the behavior in tests

Once saved as `name_summary.py`, the computation can be tested without a child process:

```python
from name_summary import normalize, summarize


def test_normalization_and_counting() -> None:
    names = normalize([" Alice ", "ALICE", "Bob"], minimum_length=4)

    assert summarize(names) == {
        "schema": "name-summary/v1",
        "total": 2,
        "counts": {"alice": 2},
    }
```

An additional integration test should invoke the command boundary and assert stdout, stderr, and status. Unit tests of `summarize` cannot prove that command-line parsing or JSON output works.

Avoid tests that import a module only to discover it immediately executes the command. That is exactly what the entry-point guard prevents.

## 13. Discover the standard library before adding dependencies

Python's standard library covers command parsing, paths, files, JSON, CSV, temporary resources, subprocesses, HTTP primitives, logging, dates, hashing, archives, databases, concurrency, and testing.

Use current documentation and interpreter introspection:

```text
python -m pydoc argparse
python -c "import pathlib; help(pathlib.Path.read_text)"
```

In an interactive session, `help(object)`, `dir(object)`, `object.__doc__`, and `module.__file__` can answer different questions. `dir` lists names but is not an API stability guarantee; documentation defines supported behavior.

Prefer a standard module when it meets the contract. Add a third-party dependency when its maintained interface materially improves correctness or capability, not merely to avoid learning the standard library.

Check version-specific documentation. Search results can land on Python 3.15 while the program runs 3.12.

## 14. Make errors cross the process boundary truthfully

The CLI layer should translate known domain failures into concise stderr messages and stable nonzero status while allowing unexpected defects to retain tracebacks in controlled development or logs.

```python
def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = perform(args)
    except InputError as exc:
        print(f"input error: {exc}", file=sys.stderr)
        return 65
    except OperationalError as exc:
        print(f"operation failed: {exc}", file=sys.stderr)
        return 1
    emit(result)
    return 0
```

Custom exception classes let a boundary distinguish categories without matching message text. Do not print an error and then fall through to return zero. Do not expose secrets in exception strings or tracebacks sent to untrusted users.

Cancellation through `KeyboardInterrupt` should normally stop the program. Catch it only at the top boundary when cleanup or a conventional status requires it, then preserve interruption rather than reporting ordinary success.

## Common Misconceptions

- “A `.py` file is automatically a maintainable program.” Structure and effect boundaries still require design.
- “Type hints validate input.” They document and support tools; runtime validation remains necessary.
- “Assignment copies a value.” Mutable objects can be shared through several names.
- “Catching every exception makes automation reliable.” It can hide defects and partial state.
- “The standard library is always the best choice.” It is the first place to look, not a ban on justified dependencies.

## Core Computer Science Concept

Python modules apply **decomposition and abstraction**: namespaces group behavior, functions transform values behind contracts, context managers bound resources, and exceptions separate exceptional paths from normal returns.

## Engineering Connections

- The `main` function translates Python outcomes into the same process status and stream contract introduced for shell.
- Python collections represent JSON-like structures without discarding types and nesting.
- Context managers give resources explicit lifetimes analogous to `trap`-based cleanup, with language-level composition.
- Pure functions isolate policy from files, processes, networks, time, and credentials.

## From the Field

A script reads configuration and contacts an API at import time. A test runner imports it to discover one helper function and unexpectedly changes production state using the developer's environment credentials. Moving effects into `main`, passing validated data into pure functions, and protecting the entry point makes import safe and the behavior testable.

## Engineering Review

### What problem does this solve?

It structures automation into importable, testable behavior with explicit process, resource, and error boundaries.

### Why was it designed this way?

Modules, functions, collections, iteration, context managers, and exceptions let programs represent richer state and lifecycle than ad hoc command composition.

### When should I use it?

Use Python when automation needs structured data, reusable logic, libraries, testing, or error handling beyond a small shell program.

### When should I avoid it?

Avoid replacing a clear one-command or short pipeline with a Python application that adds no meaningful contract or safety.

### How does this make me a better engineer?

It teaches you to separate computation from effects and to design entry points as adapters rather than the entire program.

### How does this reduce waste?

It prevents import-time incidents, duplicated parsing, untestable global state, swallowed exceptions, and unnecessary dependencies.

## Handbook Principle #68

> Build Python automation from import-safe modules, value-oriented functions, explicit resource lifetimes, and one thin entry point that reports truthful process outcomes.

## Practical Observation

Save the complete command in a disposable directory. Run it with repeated mixed-case names, whitespace-only input, an invalid minimum, and redirected stdout. Import `normalize` from a separate Python process and verify that import emits nothing. Then add the unit test shown above, run it with your test tool or a direct assertion, and delete the directory.

## Looking Ahead

Python structure makes effect boundaries visible. Chapter 69 applies that structure to paths, encodings, JSON and CSV libraries, temporary directories, traversal, metadata, validation, and atomic file replacement.

## References

- [Python 3.14 Tutorial](https://docs.python.org/3.14/tutorial/)
- [Python `__main__` documentation](https://docs.python.org/3.14/library/__main__.html)
- [Python `argparse` documentation](https://docs.python.org/3.14/library/argparse.html)
- [Python `contextlib` documentation](https://docs.python.org/3.14/library/contextlib.html)
- [Python Standard Library](https://docs.python.org/3.14/library/)
