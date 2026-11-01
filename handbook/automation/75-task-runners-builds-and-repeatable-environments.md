# Chapter 75 — Task Runners, Builds, and Repeatable Environments

A workflow known only as a sequence in one developer's shell history is not an engineering interface. It cannot be reviewed, discovered, or reproduced reliably by a new contributor or CI worker.

The central idea is:

> Give the project a small versioned task interface, model real dependencies and outputs, and make every environment input explicit enough to reproduce the result.

## 1. Replace command folklore with named intent

Compare these instructions:

```text
Run the formatter in check mode, then the linter with our config,
then type checking, then the fast tests, and remember the package flag.
```

```text
task verify
task build
```

The second form does not hide complexity; it gives the complexity one maintained entry point. The task implementation remains inspectable in the repository.

Useful task names express intent:

- `bootstrap` prepares a supported development environment;
- `format` changes source layout;
- `lint`, `typecheck`, and `test` verify specific properties;
- `verify` composes required evidence without changing source;
- `build` produces a distributable artifact;
- `clean` removes known generated output;
- `run` starts a local instance with documented defaults.

Do not create aliases that conceal unexplained commands. A task is a public project contract with inputs, outputs, effects, and failure behavior.

## 2. Choose a runner for the project's constraints

Task interfaces can be implemented with Make, language package scripts, a dedicated task runner, build-system targets, or a small project script. Evaluate:

- supported operating systems and shells;
- availability before bootstrap;
- dependency-graph and incremental-build needs;
- quoting and environment semantics;
- discoverability and help output;
- parallel execution behavior;
- ecosystem integration;
- maintenance and supply-chain cost.

There is no universal runner. A polyglot repository may use one thin top-level interface that delegates to native build tools. A small Python project may need only a portable script. A large compiled system may require a content-aware build graph.

Keep wrappers thin. Do not reimplement a compiler, package manager, or test framework inside the task file.

## 3. Define a contract for every task

For each task, document:

- purpose and whether it changes source or external state;
- prerequisites and tool versions;
- source, configuration, and environment inputs;
- generated outputs and their ownership;
- network and credential requirements;
- expected exit status and evidence;
- concurrency and cache behavior;
- cleanup and recovery.

`verify` should normally be read-only with respect to tracked source. `format` is intentionally mutating. `deploy` crosses an external authority boundary and should not be an undocumented dependency of `build`.

Tasks should propagate failure. A wrapper that prints an error and exits zero breaks every caller's evidence.

## 4. Model a dependency graph

A build is a directed graph:

```text
source + configuration + tools
              |
              v
        generated object
              |
              v
       packaged artifact
```

An edge means the downstream output depends on the upstream input. The graph determines ordering, invalidation, and safe parallelism.

Dependencies are not merely a preferred sequence. If a generated client depends on an API schema and generator version, both belong in its input model. Missing an edge can reuse stale output; adding a false edge causes needless rebuilds.

Reject dependency cycles with a clear path. A cycle means no task can establish the prerequisite state the other requires.

## 5. Distinguish actions from file outputs

Some targets name real artifacts; others name actions. GNU Make calls action targets **phony**. Declaring them prevents a file named `clean` or `test` from making the action appear current.

A real output rule answers:

```text
What file is produced?
Which files and configuration determine it?
How is it regenerated?
```

An action task such as `test` usually runs whenever requested. Do not make a permanently out-of-date action an ordinary prerequisite of a real artifact unless rerunning it every time is intentional.

## 6. Understand incremental work

Incremental builds avoid recomputing outputs whose inputs have not changed. Common validity strategies include:

- modification-time comparison;
- explicit stamp files;
- content hashes of declared inputs;
- a build database containing commands and tool versions;
- immutable content-addressed artifacts.

Timestamps are fast but can lie after clock changes, archive extraction, version-control checkout, or coarse filesystem resolution. A stamp proves only that something wrote the stamp, not that every relevant input was represented.

Content hashing is stronger but still incomplete if the hash omits compiler flags, environment variables, imported files, or tool versions. The cache key must describe the whole result-producing contract.

## 7. Keep bootstrapping separate from ordinary verification

Bootstrap creates the environment needed to run project tasks. It might:

- verify an interpreter or runtime version;
- create an isolated environment;
- install locked development dependencies;
- install repository hooks when explicitly requested;
- validate required external tools;
- print the next supported command.

Bootstrap should be safe to repeat and should not silently change global tools or shell profiles. Prefer project-local state and explain what will be downloaded.

Ordinary `verify` should not update dependencies implicitly. Otherwise the same source can begin failing because the task resolved a newer tool during execution.

## 8. Control tool and dependency versions

A source revision is not a complete build input. Record or constrain:

- language runtime and compiler;
- package manager and build backend;
- direct and transitive dependencies through a lock mechanism where supported;
- linters, formatters, code generators, and documentation tools;
- native libraries and platform requirements;
- task-runner behavior itself.

Use the ecosystem's supported metadata rather than a parallel homemade version file. Python's `pyproject.toml`, for example, declares the build backend and its Python-level requirements.

Exact pinning improves repeatability but does not remove maintenance. Update deliberately, review the diff, rerun evidence, and retain a rollback path.

## 9. Make environment inputs explicit

Build behavior can vary with:

- operating system and CPU architecture;
- locale, time zone, and encoding;
- current directory and filesystem case behavior;
- `PATH` order and user-level configuration;
- environment variables and feature flags;
- network responses and package indexes;
- available CPU, memory, and parallelism;
- current time and random values.

Start tasks from the repository root or pass explicit paths. Set required locale and encoding when output depends on them. Allowlist meaningful environment variables instead of inheriting every ambient setting into a cache key or subprocess.

Never print the complete environment for diagnosis; it may contain credentials.

## 10. Treat hermeticity as a spectrum

A hermetic action receives only declared inputs and tools and cannot observe undeclared host state. Strong isolation improves repeatability and cache correctness, but it has cost.

Useful levels include:

1. documented host prerequisites;
2. project-local dependencies and controlled commands;
3. isolated environments with restricted environment and network;
4. sandboxed, content-addressed actions with declared toolchains.

Choose according to build risk and scale. Do not describe a build as hermetic if it reads the user's home directory, downloads unpinned content, or embeds the current clock.

A container can standardize part of the userspace but does not automatically declare every input or produce deterministic output. Part VII develops that boundary.

## 11. Keep local and CI workflows aligned

CI should call the project's versioned tasks:

```text
checkout
bootstrap using locked inputs
task verify
task build
publish recorded artifact
```

Do not rewrite the linter flags, test selection, and build sequence in vendor-specific workflow syntax. That creates two implementations that drift.

Parity does not mean the environments are identical. CI may use fresh credentials, clean machines, or multiple platforms. The task contract should make those deliberate differences visible while keeping the underlying commands consistent.

## 12. Separate source, intermediates, and artifacts

Use explicit directories and ownership:

```text
src/       tracked source
tests/     tracked verification code
.cache/    disposable acceleration data
build/     disposable intermediates
dist/      release candidates
```

Generated files should answer:

- Is this file tracked or regenerated?
- Which task owns it?
- What inputs and tool version created it?
- May another task modify it?
- Is it an intermediate or a publication candidate?

Generate into a temporary path and atomically replace the destination after success when practical. A failed build should not leave a plausible-looking partial artifact.

## 13. Design reproducible artifacts

A reproducible build produces equivalent output from equivalent declared inputs. Bit-for-bit reproducibility additionally requires normalizing metadata such as:

- embedded timestamps;
- archive entry order and permissions;
- absolute build paths;
- random identifiers;
- locale-dependent sorting;
- compression settings;
- toolchain and dependency versions.

When tools support it, `SOURCE_DATE_EPOCH` supplies a source-derived timestamp instead of the wall clock. The value is an input and must itself be reproducible.

Do not remove useful provenance. Record source revision, build recipe, toolchain, and dependency evidence in a stable manifest or attestation rather than inserting the worker's incidental directory and current time.

Build twice in clean, intentionally varied directories and compare cryptographic digests. When output differs, inspect the artifact structure rather than accepting “close enough.”

## 14. Treat caches as disposable acceleration

A cache hit must not change correctness. Deleting every cache should make the build slower, not different.

A cache entry needs:

- a key derived from complete relevant inputs;
- format and tool-version compatibility;
- integrity validation;
- isolation between trust levels;
- bounded retention and size;
- a fallback that rebuilds from source.

Do not restore executable cache content from untrusted changes into a privileged release job. Cache poisoning is a supply-chain boundary, not just a performance defect.

Never place the only copy of a required artifact in a cache. Publication storage and caches have different durability contracts.

## 15. Make cleanup narrow and recoverable

`clean` should remove only documented generated paths beneath the project. Resolve and validate targets before recursive deletion. Never construct a destructive path from an empty or untrusted environment variable.

Separate levels when useful:

- `clean` removes build intermediates;
- `clean-cache` removes disposable acceleration data;
- `dist-clean` removes the bootstrapped local environment after explicit request.

Cleaning should not be required for correctness. If every build needs `clean`, the dependency or invalidation model is defective.

## 16. Keep build and release separate

`build` creates a candidate artifact. `release` promotes an already identified candidate after required evidence. Rebuilding during promotion creates a new object that was not the one tested.

Record an artifact digest and pass that identity through later stages. Publication should be explicit, authenticated, and protected from accidental local invocation.

The same separation applies to infrastructure plans, generated documentation, and database migrations: create and verify an immutable candidate before applying it to a shared system.

## 17. Treat task definitions as executable code

Task files and build definitions can run arbitrary commands with the developer's or CI worker's authority. Review changes to them accordingly.

Before executing tasks from an untrusted branch:

- inspect the task and dependency changes;
- use credentials with minimal scope or none at all;
- isolate the worker from trusted caches and networks;
- prevent unreviewed code from publishing artifacts;
- bound generated paths and subprocesses;
- retain command, tool, source, and artifact evidence.

Convenient task names do not create a security boundary.

## 18. Complete example: a portable project task interface

The following single-file runner demonstrates named tasks, dependency ordering, cycle detection, deterministic manifest generation, write-if-changed behavior, and bounded cleanup. It uses only the Python standard library so the interface works anywhere the supported interpreter is available:

```python
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import unittest
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable, Iterable


ROOT = Path(__file__).resolve().parent
BUILD_DIRECTORY = ROOT / "build"
MANIFEST = BUILD_DIRECTORY / "manifest.json"
SOURCE_FILES = (ROOT / "tasks.py",)


@dataclass(frozen=True)
class Task:
    description: str
    dependencies: tuple[str, ...]
    action: Callable[[], None]


def render_manifest(
    files: Iterable[Path],
    *,
    root: Path,
    source_date_epoch: int,
) -> bytes:
    entries = []
    for path in sorted(files, key=lambda item: item.relative_to(root).as_posix()):
        entries.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "size": path.stat().st_size,
            }
        )
    document = {
        "schema": 1,
        "source_date_epoch": source_date_epoch,
        "files": entries,
    }
    return (
        json.dumps(document, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def write_if_changed(path: Path, content: bytes) -> bool:
    if path.exists() and path.read_bytes() == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(content)
    os.replace(temporary, path)
    return True


def source_date_epoch() -> int:
    raw = os.environ.get("SOURCE_DATE_EPOCH", "0")
    try:
        value = int(raw)
    except ValueError as error:
        raise RuntimeError("SOURCE_DATE_EPOCH must be an integer") from error
    if value < 0:
        raise RuntimeError("SOURCE_DATE_EPOCH must be nonnegative")
    return value


def check_syntax() -> None:
    source = Path(__file__).read_text(encoding="utf-8")
    compile(source, str(Path(__file__)), "exec")
    print("syntax: ok")


def run_self_tests() -> None:
    completed = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(TaskTests)
    )
    if not completed.wasSuccessful():
        raise RuntimeError("tests failed")


def build_manifest() -> None:
    content = render_manifest(
        SOURCE_FILES,
        root=ROOT,
        source_date_epoch=source_date_epoch(),
    )
    changed = write_if_changed(MANIFEST, content)
    digest = hashlib.sha256(content).hexdigest()
    state = "updated" if changed else "unchanged"
    print(f"build: {state} {MANIFEST.relative_to(ROOT)} sha256={digest}")


def clean() -> None:
    target = BUILD_DIRECTORY.resolve()
    root = ROOT.resolve()
    if target.parent != root or target.name != "build":
        raise RuntimeError(f"refusing unsafe clean target: {target}")
    if target.exists():
        shutil.rmtree(target)
        print("clean: removed build/")
    else:
        print("clean: build/ already absent")


def no_action() -> None:
    pass


TASKS = {
    "check-syntax": Task("parse the task source", (), check_syntax),
    "test": Task("run fast project tests", (), run_self_tests),
    "build": Task(
        "create a deterministic source manifest",
        ("check-syntax",),
        build_manifest,
    ),
    "verify": Task(
        "run all required local evidence",
        ("check-syntax", "test", "build"),
        no_action,
    ),
    "clean": Task("remove owned generated output", (), clean),
}


def run_task(name: str, tasks: dict[str, Task] = TASKS) -> None:
    completed: set[str] = set()
    visiting: list[str] = []

    def visit(current: str) -> None:
        if current in completed:
            return
        if current in visiting:
            cycle = " -> ".join((*visiting, current))
            raise RuntimeError(f"task dependency cycle: {cycle}")
        try:
            task = tasks[current]
        except KeyError as error:
            raise RuntimeError(f"unknown task: {current}") from error

        visiting.append(current)
        for dependency in task.dependencies:
            visit(dependency)
        visiting.pop()

        print(f"==> {current}")
        task.action()
        completed.add(current)

    visit(name)


class TaskTests(unittest.TestCase):
    def test_manifest_is_sorted_and_reproducible(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            second = root / "b.txt"
            first = root / "a.txt"
            second.write_text("second\n", encoding="utf-8")
            first.write_text("first\n", encoding="utf-8")

            left = render_manifest(
                (second, first),
                root=root,
                source_date_epoch=1_700_000_000,
            )
            right = render_manifest(
                (first, second),
                root=root,
                source_date_epoch=1_700_000_000,
            )

            self.assertEqual(left, right)
            self.assertLess(left.index(b'a.txt'), left.index(b'b.txt'))

    def test_write_if_changed_preserves_unchanged_output(self) -> None:
        with TemporaryDirectory() as directory:
            output = Path(directory) / "artifact.txt"
            self.assertTrue(write_if_changed(output, b"stable\n"))
            first_time = output.stat().st_mtime_ns
            self.assertFalse(write_if_changed(output, b"stable\n"))
            self.assertEqual(output.stat().st_mtime_ns, first_time)

    def test_cycle_is_rejected_before_actions_run(self) -> None:
        actions: list[str] = []
        tasks = {
            "a": Task("a", ("b",), lambda: actions.append("a")),
            "b": Task("b", ("a",), lambda: actions.append("b")),
        }
        with self.assertRaisesRegex(RuntimeError, "a -> b -> a"):
            run_task("a", tasks)
        self.assertEqual(actions, [])


def main() -> int:
    parser = argparse.ArgumentParser(description="Project task interface")
    parser.add_argument("task", nargs="?", choices=sorted(TASKS))
    parser.add_argument("--list", action="store_true", help="list tasks")
    arguments = parser.parse_args()

    if arguments.list or arguments.task is None:
        for name, task in sorted(TASKS.items()):
            print(f"{name:14} {task.description}")
        return 0

    run_task(arguments.task)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Save it as `tasks.py` in a disposable directory, then run:

```bash
python tasks.py --list
SOURCE_DATE_EPOCH=1700000000 python tasks.py verify
SOURCE_DATE_EPOCH=1700000000 python tasks.py build
python tasks.py clean
```

In PowerShell, set the build input for one process like this:

```powershell
$env:SOURCE_DATE_EPOCH = "1700000000"
python tasks.py verify
Remove-Item Env:SOURCE_DATE_EPOCH
```

`verify` runs `check-syntax` only once even though both `verify` and `build` depend on it. The second `build` leaves an identical manifest untouched. The task script refuses to clean anything except its exact `build` child directory.

This educational runner is not a replacement for a mature build system. It demonstrates the contracts to preserve when the project adopts one: named intent, explicit dependencies, deterministic inputs, truthful output, and bounded effects.

## 19. Introduce tasks incrementally

Start with the commands contributors already need:

1. capture the current supported commands and versions;
2. name `verify`, `build`, and `clean` with clear effects;
3. move duplicated local and CI command sequences behind them;
4. declare outputs and generated-path ownership;
5. test from a clean checkout and a path containing spaces;
6. compare repeated clean builds;
7. add caching only after correctness is stable;
8. measure task duration and remove obsolete paths.

Do not migrate every command at once. A small interface that the project actually maintains is better than a catalog of stale wrappers.

## Common Misconceptions

- “A task runner makes the build reproducible.” It only invokes commands; inputs and tools still need control.
- “Containers make builds hermetic.” They can still read undeclared state and fetch changing dependencies.
- “A lock file freezes everything.” Runtimes, native libraries, indexes, and build tools may remain variable.
- “Clean builds are always safer.” They are useful evidence, but requiring them can hide an invalid incremental graph.
- “A cache is artifact storage.” Caches are disposable and can be evicted or poisoned.
- “Local and CI parity means identical machines.” It means one task contract with explicit, purposeful environment differences.

## Core Computer Science Concept

A build is **dependency-graph evaluation with memoization**. Inputs and transformations form a directed graph; valid prior outputs may be reused only when the complete result-producing inputs are equivalent.

## Engineering Connections

- Stable task contracts apply the interface design from Chapters 65 and 68.
- Locked tools and isolated environments extend the packaging model from Chapter 71.
- Verification tasks compose the evidence layers from Chapter 73.
- Content fingerprints reuse canonical data and hashing concepts from Chapters 67 and 74.
- Immutable candidate artifacts prepare the promotion flow in Chapter 77.

## From the Field

A release job rebuilds a package after tests pass. Its worker resolves a newer transitive dependency than the test job, so the published digest was never tested. A locked build environment and promotion of the already verified artifact would have kept evidence attached to the object released.

## Engineering Review

### What problem does this solve?

It turns tribal command sequences into a discoverable, reviewable interface and makes the inputs, outputs, and invalidation rules of builds explicit.

### Why was it designed this way?

Named tasks stabilize human and CI entry points, dependency graphs prevent stale ordering assumptions, and controlled environments make evidence reproducible.

### When should I use it?

Use a task interface as soon as a project has repeated setup, verification, generation, build, or cleanup commands.

### When should I avoid it?

Avoid wrappers that add no stable contract, duplicate native tool behavior, or conceal external mutations behind harmless names.

### How does this make me a better engineer?

It teaches you to model workflows as explicit dependencies and to recognize ambient state as an input rather than luck.

### How does this reduce waste?

It removes command rediscovery, CI drift, stale artifacts, unnecessary rebuilds, cache errors, and “works on my machine” investigation.

## Handbook Principle #75

> Make the supported workflow one small, versioned interface whose graph, inputs, outputs, and destructive boundaries can all be inspected.

## Practical Observation

Run the example in a disposable directory. Verify twice with the same `SOURCE_DATE_EPOCH`, record the manifest digest, and confirm the second build reports `unchanged`. Change one source byte and confirm the digest changes. Finally, create an unrelated sibling directory and prove `clean` removes only `build/`.

## Looking Ahead

A repeatable task still needs an owner, start policy, overlap rule, and capacity limit when it runs unattended. Chapter 76 adds schedules, locks, leases, queues, concurrency limits, backpressure, and run history.

## References

- [GNU Make manual](https://www.gnu.org/software/make/manual/make.html)
- [GNU Make — Phony Targets](https://www.gnu.org/software/make/manual/html_node/Phony-Targets.html)
- [Python Packaging User Guide — `pyproject.toml` specification](https://packaging.python.org/en/latest/specifications/pyproject-toml/)
- [Reproducible Builds — `SOURCE_DATE_EPOCH` specification](https://reproducible-builds.org/specs/source-date-epoch/)
- [Reproducible Builds — Timestamps](https://reproducible-builds.org/docs/timestamps/)
- [Bazel documentation — Hermeticity](https://bazel.build/basics/hermeticity)
- [SLSA — Build Track](https://slsa.dev/spec/v1.1/build-requirements)
