# Chapter 71 — Python Environments, Dependencies, and Packaging

A Python program is reproducible only when another machine can select a compatible interpreter, obtain the intended distributions from trusted sources, install them into an isolated environment, and expose the same entry point.

The central idea is:

> Declare the runtime and dependency graph as rebuildable inputs; never treat one developer's installed environment as the specification.

## 1. Separate the layers people call “Python”

Several objects are easy to collapse into one word:

- an **interpreter installation** supplies a Python implementation and standard library;
- a **virtual environment** selects one base interpreter and isolated installation directories;
- a **project** is source, metadata, configuration, and tests under development;
- an **import package** is a namespace such as `status_report` used by Python code;
- a **distribution package** is installable metadata and files identified by a distribution name;
- an **application** is an installed, runnable program with an entry point;
- a **package index** helps installers discover distribution artifacts.

Distribution names and import names need not match. Installing `some-project` does not prove that `import some_project` is correct, and one distribution can provide several import packages.

A virtual environment does not install a new independent Python runtime from nothing. It is created from a base interpreter and refers back to it.

## 2. Identify the interpreter before installing

Shell command resolution can select different interpreters and installers:

```text
python --version
python -c "import sys; print(sys.executable); print(sys.prefix); print(sys.base_prefix)"
python -m pip --version
```

Use `python -m pip` so the chosen interpreter imports and runs its `pip` module. A bare `pip` command can belong to another installation.

On Windows, `py --list-paths` inventories registered interpreters and `py -3.14` selects one. On Unix-like systems, names such as `python3.14` depend on installation and distribution policy.

Record implementation, major and minor version, architecture, operating system, and—when native extensions matter—the relevant ABI and platform. A lock produced for one platform may not describe artifacts for another.

## 3. Virtual environments isolate installations

Create a disposable environment with the intended base interpreter:

```text
python -m venv .venv
```

By default, packages installed into that environment are isolated from the base environment's site-packages. Project source should remain outside `.venv`, and the environment directory should not be committed.

Activation prepends the environment's executable directory to `PATH`; it is convenience, not a requirement. Automation can invoke the interpreter directly:

```text
.venv/bin/python -m status_report       # POSIX
.venv\Scripts\python.exe -m status_report  # Windows
```

Inside a virtual environment, `sys.prefix` differs from `sys.base_prefix`. Do not rely only on `VIRTUAL_ENV`; direct interpreter invocation does not require activation.

Virtual environments are disposable and generally not movable. Installed script wrappers can contain absolute interpreter paths. Recreate an environment after moving it or changing the base interpreter.

## 4. Isolation is not reproducibility

A fresh empty environment prevents accidental access to unrelated packages, but `pip install some-package` still asks a resolver and index for whatever currently satisfies an open request.

Reproduction needs inputs such as:

- supported Python versions and platforms;
- direct dependency declarations;
- resolved transitive versions for an application;
- selected artifacts and integrity hashes where supported;
- index and trusted artifact policy;
- installer or lock-tool version and options;
- local project revision and build configuration;
- environment markers and optional dependency groups.

An environment snapshot such as `pip freeze` records installed distributions, including incidental tools, but does not explain which dependencies are direct or why they exist. It can be useful evidence or one locking input, not a complete project model.

## 5. Declare project metadata in `pyproject.toml`

Modern Python projects use `pyproject.toml` for build-system requirements, standardized project metadata, and tool configuration:

```toml
[build-system]
requires = ["setuptools>=77,<78"]
build-backend = "setuptools.build_meta"

[project]
name = "status-report"
version = "0.1.0"
description = "Generate a bounded service status report"
requires-python = ">=3.12"
dependencies = [
  "httpx>=0.28,<1",
]

[project.optional-dependencies]
test = [
  "pytest>=8,<9",
]

[project.scripts]
status-report = "status_report.cli:main"
```

The build backend is code executed to build or install the project, so it is itself a dependency and trust decision. The example ranges are illustrative, not recommendations for future versions.

`requires-python` lets tools reject incompatible interpreters. `dependencies` describes runtime requirements using standardized dependency specifiers. Optional dependencies group named capabilities; they are not automatically installed.

The `[tool.*]` namespace holds tool-specific configuration. Do not invent keys under standardized tables.

## 6. Direct requirements and locks solve different problems

A library usually declares compatible ranges so downstream applications can resolve it with other components. An application commonly needs a tested, fully resolved environment.

```text
declaration: httpx>=0.28,<1
lock result: exact httpx version plus exact transitive packages and artifacts
```

The declaration states intent; the lock records one accepted resolution for defined environments. Do not replace thoughtful compatibility ranges with exact pins in published library metadata merely because the application's deployment is locked elsewhere.

A useful lock captures transitive dependencies, markers, artifact filenames or URLs, and hashes for every supported platform. If one file cannot express the platform matrix clearly, generate and test named locks per environment.

Python now has a standardized `pylock.toml` format defined from PEP 751, but tool support and workflows still vary. Select a maintained locking tool, commit its lock output, pin the tool where required, and test installation from the lock without re-resolving.

## 7. Requirements and constraints are installer inputs

Pip requirements files can list install requests, options, URLs, local paths, and includes. They are pip-specific inputs, not standardized project metadata.

A constraints file limits versions selected for dependencies without itself requesting that every named project be installed. Requirements ask for installation; constraints bound resolution.

Fully pinned requirements can improve repeatability, especially with hashes and `--no-deps`, but platform-specific wheels and environment markers require deliberate generation. A file copied from one workstation can include unrelated tools or fail on another platform.

Never assume a filename named `requirements.txt` has one universal semantic. Review its contents and the exact installation command.

## 8. Hashes protect integrity, not all trust

Hash-checking lets an installer reject an artifact whose bytes differ from the approved digest. It helps detect tampering, corruption, or an unexpected file under the same version.

Hashes do not prove:

- the package author is trustworthy;
- the approved artifact is free of malicious code;
- the dependency name is the intended project;
- the selected version has no vulnerability;
- build-time or runtime behavior is safe;
- the index remains available.

Hash every permitted artifact under an all-or-nothing policy. Allowing one unhashed transitive dependency leaves the resolver a route to unapproved bytes.

Source distributions can execute build-backend code to create a wheel. Wheels avoid a local source build but still install and later execute code. Treat both as software supply-chain inputs.

## 9. Index configuration defines a namespace

An installer can query public and private indexes or direct artifact locations. Project names share a resolution namespace across those sources.

Using an extra public index alongside a private index can enable dependency confusion: an attacker publishes the same internal project name with a version the resolver prefers. Isolation requires index policy, unique naming, or an internal repository that controls upstream proxying—not merely another URL flag.

Protect index credentials, TLS validation, and configuration files. Do not embed secrets in requirement URLs, command history, or committed `pip.conf` files.

Record the artifact's source and digest in installation evidence. “Installed version 2.4” is incomplete when several sources can serve that name and version.

## 10. Build isolation is a separate environment

PEP 517 build frontends normally create an isolated environment for requirements listed under `[build-system]`. Runtime dependencies and build dependencies are different graphs.

Disabling build isolation transfers responsibility to the caller to provide correct build tools. It can help a controlled offline build, but it is not a harmless speed option.

Prefer building a wheel once in a controlled build job and promoting the immutable artifact through environments. Rebuilding the same source independently in production can select different tools, environment inputs, or native libraries.

Inspect wheel metadata and installation reports where available. A successful build proves that code ran, not that its result is reproducible or trusted.

## 11. Editable installs are for development

An editable install connects an environment to a working source tree:

```text
python -m pip install --editable .
```

Python source edits can then appear without rebuilding or copying the package. Backend implementation details vary, and metadata, entry-point, dependency, or native-extension changes can still require reinstallation.

Editable behavior is not proof that a built wheel contains the expected files. Test both editable development and an ordinary wheel installation in a clean environment.

Do not deploy an editable checkout as a production artifact. It couples runtime behavior to mutable source and filesystem layout.

## 12. Entry points make commands installable

The `[project.scripts]` table maps a command name to an importable callable:

```toml
[project.scripts]
status-report = "status_report.cli:main"
```

An installer creates a platform-appropriate wrapper that imports and calls `main`, then translates its return value into process status. The function should take no required Python arguments; it reads the process argument vector through its CLI adapter.

Keep this callable thin and import-safe. The same domain functions should work from unit tests, `python -m status_report`, and the installed command.

A package's `__main__.py` supports module execution but is not the same as an installed console-script declaration. Test both interfaces only if both are supported contracts.

## 13. Verify the built artifact, not only the source tree

A packaging test should:

1. create a clean temporary environment;
2. build the project artifact with controlled build inputs;
3. inspect the artifact contents and metadata;
4. install from the artifact without contacting unintended indexes;
5. run the installed entry point outside the source directory;
6. exercise help, version, success, and failure status;
7. verify import and dependency provenance;
8. discard and recreate the environment.

Running tests from the repository root can accidentally import local source rather than the installed artifact. Change to a neutral directory or use a source layout that makes this mistake visible.

An offline installation test against an approved wheelhouse demonstrates that deployment is not silently resolving from the internet.

## 14. Make upgrades routine and bounded

A lock is a controlled delay, not a promise to keep dependencies forever. Define an upgrade cadence and exceptional path for urgent security fixes.

For each update:

- re-resolve from reviewed declarations and approved indexes;
- inspect direct and transitive changes;
- verify new artifact sources and hashes;
- read relevant release and security notes;
- run unit, integration, artifact, and platform tests;
- deploy through a bounded canary or preview where applicable;
- retain the prior lock and artifact for rollback;
- record why the update was accepted.

Automated update proposals reduce discovery toil but do not replace compatibility and trust review. Large infrequent jumps accumulate uncertainty; unreviewed continuous upgrades outsource change control to publishers.

Rebuild from the prior lock for rollback. Copying an old virtual environment is not a reliable recovery plan.

## 15. Reproduce one minimal project

Use this structure in a disposable directory:

```text
status-report/
├── pyproject.toml
└── src/
    └── status_report/
        ├── __init__.py
        ├── __main__.py
        └── cli.py
```

`cli.py` contains an ordinary entry point:

```python
from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    print("status-report 0.1.0")
    return 0
```

`__main__.py` adapts module execution:

```python
from status_report.cli import main

raise SystemExit(main())
```

Create a clean environment, install the project in editable mode for development, and exercise both the module and generated script. Then build a wheel, create a second clean environment, install only that wheel, change to a directory outside the source tree, and repeat the checks.

Use an empty `dependencies` list for this isolated lesson unless an approved local wheelhouse is available. Adding an arbitrary internet dependency merely to demonstrate installation broadens the test's trust boundary unnecessarily.

## Common Misconceptions

- “A virtual environment makes installs reproducible.” It isolates packages; declarations, resolution, artifacts, and tools still need control.
- “Activation is required.” Directly invoking the environment interpreter is sufficient and clearer in automation.
- “`pip freeze` is the project manifest.” It records installed distributions without direct-dependency intent.
- “A hash proves a package is safe.” It proves bytes match an approved digest, not that the bytes are trustworthy.
- “Editable install is what production will run.” It can differ from the built and installed artifact.

## Core Computer Science Concept

Python packaging is **dependency-graph resolution plus artifact realization**. Declarations constrain acceptable nodes and edges; a lock selects a graph for environments; installers verify and materialize artifacts into an interpreter-specific namespace.

## Engineering Connections

- Virtual environments isolate Python packages like process environments isolate command execution, but neither replaces explicit inputs.
- Lock files apply structured-data versioning and compatibility rules from Chapter 67.
- Package indexes and build backends are external trust boundaries governed by Chapter 70's principles.
- Console scripts translate an importable function into the process interface developed in Chapters 65 and 68.

## From the Field

A deployment recreates an environment with an open dependency range and silently receives a new transitive release. The service fails at startup even though application source is unchanged. Committed locks, artifact hashes, an offline installation test, and a routine reviewed update process turn hidden resolver state into an explicit change.

## Engineering Review

### What problem does this solve?

It makes a Python application's interpreter, dependency graph, artifacts, installation, and command entry point reconstructable and reviewable.

### Why was it designed this way?

Python projects run across many interpreters and platforms, while dependency resolution and artifact selection happen outside source code.

### When should I use it?

Use these practices for every Python automation that imports third-party code or must run consistently beyond one workstation.

### When should I avoid it?

Avoid adding packaging and dependencies to a one-file standard-library script unless distribution or isolation requirements justify the lifecycle cost.

### How does this make me a better engineer?

It lets you explain exactly which interpreter loaded which installed artifact from which approved source.

### How does this reduce waste?

It prevents environment drift, wrong-interpreter installs, source-tree-only successes, dependency confusion, unrepeatable rollbacks, and surprise upgrades.

## Handbook Principle #71

> Rebuild environments from declared runtime constraints, reviewed locks, verified artifacts, and tested entry points—never from the memory of an existing installation.

## Practical Observation

Create the minimal project in a disposable directory. Record the base interpreter, create two independent virtual environments, and compare `sys.executable`, `sys.prefix`, and installed metadata. Test editable execution in the first and wheel-only execution outside the source tree in the second. Delete both environments and prove they can be recreated from committed inputs.

## Looking Ahead

Reproducible code still needs predictable runtime inputs and controlled evidence. Chapter 72 defines configuration precedence, secret references, validation, structured logs, correlation identifiers, batch metrics, redaction, and dry-run reporting.

## References

- [Python `venv` documentation](https://docs.python.org/3.14/library/venv.html)
- [Python Packaging User Guide — `pyproject.toml` specification](https://packaging.python.org/en/latest/specifications/pyproject-toml/)
- [Python Packaging User Guide — `pylock.toml` specification](https://packaging.python.org/en/latest/specifications/pylock-toml/)
- [Python Packaging User Guide — Entry points specification](https://packaging.python.org/en/latest/specifications/entry-points/)
- [pip — Repeatable installs](https://pip.pypa.io/en/stable/topics/repeatable-installs/)
- [pip — Secure installs](https://pip.pypa.io/en/stable/topics/secure-installs/)
