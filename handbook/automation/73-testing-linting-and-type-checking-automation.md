# Chapter 73 — Testing, Linting, and Type Checking Automation

Automation can change many systems quickly and without a person watching. A script that passes a happy-path demonstration may still delete the wrong objects, conceal a partial failure, or behave differently in a scheduler.

The central idea is:

> Build evidence in layers: prove decisions with fast tests, prove boundaries with controlled integrations, and use static checks to remove defects before execution.

## 1. Match evidence to blast radius

Testing effort should follow risk, not line count. A 30-line account-deletion script may deserve more scrutiny than a 3,000-line read-only report generator.

Assess at least:

- the number and importance of resources the automation can affect;
- whether an effect is reversible and how long recovery takes;
- the authority of its credentials;
- whether it runs unattended or concurrently;
- the reliability and ambiguity of its external systems;
- how quickly a defect can propagate;
- whether operators can observe and stop a run.

A local formatter may need focused unit tests and a smoke test. Fleet-wide credential rotation needs boundary tests, failure injection, staged rollout, reconciliation, and a rehearsed recovery path.

This is not permission to leave low-risk code untested. It is a way to place the strongest evidence where failure costs the most.

## 2. Start with contracts and invariants

A test is useful when it proves a property that matters. Before choosing a framework, write the contract:

```text
Given observed resources and a policy,
produce a deterministic, bounded plan.

Never select protected resources.
Never select more than the configured limit.
Never mutate during planning or dry-run.
Report every attempted effect accurately.
```

Contracts identify inputs, outputs, effects, errors, and invariants. They also reveal designs that are difficult to test. If planning, network access, logging, and mutation happen in one function, the code has no clean seam at which to prove decisions independently.

Test names should state behavior, such as `test_plan_excludes_protected_resources`, rather than restating a function name.

## 3. Separate decisions from effects

The most valuable testability technique is architectural, not framework-specific:

```text
external observations -> typed values -> pure decision -> explicit plan
                                                    |
                                                    v
                                           effectful executor
```

A pure decision function returns the same result for the same input and does not read clocks, environment variables, files, networks, or global state. It can be tested quickly with ordinary values.

The effectful executor receives an explicit plan and a narrow dependency. Tests can replace that dependency with a controlled fake. Production supplies the real client.

This structure does not make external systems reliable. It makes policy defects and boundary defects distinguishable.

## 4. Build a layered test portfolio

Different tests answer different questions:

| Layer | Primary question | Typical dependencies | Feedback |
| --- | --- | --- | --- |
| Unit | Is one decision or transformation correct? | In-memory values | Very fast |
| Component | Do cooperating modules honor their contract? | Fakes, temporary files, local processes | Fast |
| Integration | Does the code speak to the real boundary correctly? | Disposable database, service sandbox, real shell | Moderate |
| End-to-end | Can a representative workflow complete? | Deployed system and controlled test resources | Slowest |

Keep a broad base of fast tests and a smaller number of expensive tests. Do not infer boundary compatibility from unit tests, and do not force every policy edge case through a costly end-to-end environment.

An integration test should use the real parser, protocol, filesystem behavior, database engine, or supported shell that it claims to cover. Replacing every boundary with a mock turns it back into a unit test.

## 5. Choose test cases from the state space

One representative input is rarely enough. Partition the input space and test boundaries:

- empty, single-item, and many-item collections;
- values just below, at, and above a threshold;
- zero, one, and maximum batch sizes;
- duplicates and conflicting identifiers;
- reordered input and stable output ordering;
- missing, malformed, oversized, and unsupported data;
- protected, stale, already-complete, and concurrently changed resources;
- success before and after a failing operation;
- interruption before, during, and after a visible effect.

Table-driven tests express many cases against one contract. Property-based tests generate values and verify invariants such as “the result is never larger than the limit” or “sorting the input cannot change the selected identifiers.” Generated cases complement named examples; they do not replace domain-specific failure stories.

## 6. Own fixtures and test data deliberately

A fixture establishes a known starting state and returns it to a known ending state. Good fixtures are:

- minimal enough that a failure is understandable;
- local to the tests that need them;
- immutable by default;
- explicit about setup and cleanup;
- independent of execution order;
- free of production identifiers and secrets.

Shared mutable fixtures make tests influence each other. A test that passes only after another test is not repeatable evidence.

Use builders or small factory functions when many cases need related data. Give defaults safe meanings, but make values relevant to the assertion visible in the test.

## 7. Isolate temporary resources

Tests that exercise files, databases, or processes need unique disposable resources. Python's `tempfile.TemporaryDirectory` and pytest's `tmp_path` provide test-scoped directories. Similar isolation should apply to database schemas, queue names, cloud resources, ports, and object prefixes.

For every temporary resource:

1. create a unique name under an approved test scope;
2. label ownership and expiration when the platform supports it;
3. register cleanup before the risky action;
4. make cleanup safe to repeat;
5. report leftover resources without hiding the original failure.

Cleanup is not a substitute for containment. Test credentials should be technically unable to reach production resources.

## 8. Use fakes, stubs, and mocks for different purposes

Test doubles are not interchangeable:

- A **stub** returns controlled responses.
- A **fake** is a simplified working implementation, such as an in-memory repository.
- A **spy** records interactions for later assertions.
- A **mock** is configured with expected interactions and can fail when they differ.

Use a fake when state and behavior matter. Use a stub to force a timeout or error. Use interaction assertions when the call itself is the contract, such as proving dry-run never invokes deletion.

Avoid mocking private calls or an exact internal sequence that callers do not observe. Those tests resist harmless refactoring while still missing contract violations.

Python's `unittest.mock` can constrain a double to a real interface with `spec` or `autospec`. That catches misspelled methods, but it still cannot prove the external system's semantics.

## 9. Inject unstable dependencies

Code becomes nondeterministic when it reads implicit process state. Pass unstable dependencies through narrow interfaces:

- a clock instead of calling the current time throughout the program;
- a random source instead of using a global generator;
- a filesystem root instead of assuming the working directory;
- an HTTP client instead of opening connections inside policy code;
- a command runner instead of starting subprocesses everywhere;
- resolved configuration instead of rereading environment variables.

An interface should expose the smallest operation the code needs. A cleanup executor needs `delete(identifier)`, not an entire vendor SDK.

Dependency injection is valuable because it makes authority visible and replaceable, not because every object needs a framework.

## 10. Make tests deterministic

A test should fail because behavior changed, not because time, scheduling, locale, or ordering changed.

Control or eliminate:

- wall-clock time and time zones;
- random seeds and generated identifiers;
- filesystem and map iteration order;
- locale, encoding, and line endings;
- network access and DNS;
- parallel execution order;
- global caches and process environment;
- unbounded waits.

Prefer polling a documented condition with a deadline over sleeping for a guessed interval. Sort sets before comparing serialized output. Assert structured values rather than timestamps and presentation whitespace that the contract does not promise.

A flaky test is a defect in the evidence system. Quarantining it may protect an urgent build, but it must retain an owner and repair deadline.

## 11. Test failure paths and recovery evidence

Production automation spends much of its complexity handling what did not complete. Tests should deliberately produce:

- permission denial and authentication expiry;
- malformed responses and schema changes;
- connection refusal, timeout, and rate limiting;
- disk full, read-only paths, and atomic-replace failure;
- subprocess nonzero status and invalid output;
- one failed item after earlier items succeeded;
- logging, metrics, or checkpoint sink failure;
- interruption and restart at every durable transition;
- exhausted retry budgets.

Assert more than the raised exception. Verify which effects occurred, which did not, what evidence was persisted, whether an error was classified correctly, and whether a retry or restart remains safe.

Chapter 74 develops the state and recovery mechanisms needed to make these assertions meaningful.

## 12. Check shell automation at several levels

Shell syntax checks and linters find different classes of defects:

```bash
bash -n scripts/cleanup.sh
shellcheck scripts/cleanup.sh
```

`bash -n` parses without executing. ShellCheck reports common quoting, expansion, portability, and control-flow hazards. A formatter can make review easier, but formatting is not correctness.

Then run tests under every shell version the project supports. Use disposable directories, controlled environment variables, fake commands earlier on `PATH`, and captured stdout, stderr, and exit status. Test filenames containing spaces, leading hyphens, glob characters, newlines where supported, and non-ASCII text.

A linter cannot prove that a command is safe, that an API response is current, or that an operation is idempotent.

## 13. Combine Python linting and type checking

Python's parser accepts programs with unreachable branches, unused values, ambiguous types, and inconsistent interfaces. Static tools add earlier feedback:

- a formatter makes layout mechanical;
- a linter detects suspicious constructs and project policy violations;
- a type checker compares annotations across paths without executing them;
- an import or package check proves the installed artifact is usable.

Keep tool configuration in a reviewed project file, commonly `pyproject.toml`, and pin or otherwise control tool versions in the verification environment. Run the same commands locally and in CI.

Type hints are not runtime validation. External JSON remains untrusted data even when assigned to a typed variable. Parse and validate it before constructing trusted domain values.

Adopt stricter checking deliberately. A small, enforced typed boundary is better than thousands of annotations hidden behind broad ignores.

## 14. Treat diagnostics as maintained policy

Every ignored diagnostic creates an exception to the project's rules. Suppress narrowly and explain why:

```python
value = legacy_call()  # type: ignore[no-untyped-call]  # Remove after SDK-184
```

Prefer a rule-specific suppression to disabling an entire file. Periodically identify unused suppressions and expired exceptions. Generated or vendored code may follow a separate policy, but its boundary still needs validation.

Do not make a warning budget grow silently. A clean baseline lets new failures carry information.

## 15. Coverage is a map, not a target

Coverage can reveal code that no test executed. It cannot prove that assertions are correct, inputs are representative, or effects are safe.

Use coverage to ask questions:

- Why is this error branch unexecuted?
- Is this platform-specific path tested anywhere?
- Does a high-risk mutation have failure-path evidence?
- Is dead code inflating the surface?

A target can prevent gross regression, but optimizing solely for a percentage encourages assertions without meaning. Mutation testing can provide stronger feedback by changing code and checking whether tests detect the change.

## 16. Design a fast verification loop

Put cheap, broad checks first and expensive, narrow checks later:

```text
format check
  -> syntax and lint
  -> type check
  -> unit tests
  -> component tests
  -> integration tests
  -> controlled end-to-end test
```

Fast feedback improves both engineering flow and operational safety. Developers run a two-second suite repeatedly; they defer a 40-minute suite until defects have accumulated.

Parallelize independent tests only after proving isolation. Retain deterministic logs, seed values, test case identifiers, and failed artifacts so a CI failure can be reproduced locally without exposing secrets.

## 17. Gate changes with reproducible commands

CI should invoke versioned project commands rather than duplicate a different workflow in YAML. A task runner or build interface might provide:

```text
check-format
lint
typecheck
test-unit
test-integration
verify
```

The `verify` target composes the same checks a contributor runs locally. Chapter 75 develops this repeatable build boundary.

Required checks should be stable, owned, and actionable. A gate that fails for unrelated external instability teaches people to rerun rather than investigate. Keep optional experiments distinct from release evidence.

## 18. Complete example: test a cleanup boundary

The following standard-library example keeps selection pure and deletion behind a protocol. Its test suite proves invariants, dry-run behavior, real call order through a fake, and a partial failure:

```python
from __future__ import annotations

import unittest
from dataclasses import dataclass
from typing import Protocol, Sequence


@dataclass(frozen=True)
class Candidate:
    identifier: str
    age_days: int
    protected: bool = False


@dataclass(frozen=True)
class DeleteAction:
    identifier: str


@dataclass(frozen=True)
class ExecutionResult:
    planned: int
    deleted: int


class DeleteExecutor(Protocol):
    def delete(self, identifier: str) -> None: ...


def plan_cleanup(
    candidates: Sequence[Candidate],
    *,
    minimum_age_days: int,
    maximum_deletions: int,
) -> tuple[DeleteAction, ...]:
    if minimum_age_days < 0:
        raise ValueError("minimum_age_days must be nonnegative")
    if maximum_deletions < 0:
        raise ValueError("maximum_deletions must be nonnegative")

    identifiers = [candidate.identifier for candidate in candidates]
    if any(not identifier for identifier in identifiers):
        raise ValueError("identifiers must not be empty")
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("identifiers must be unique")

    eligible = (
        candidate
        for candidate in candidates
        if not candidate.protected
        and candidate.age_days >= minimum_age_days
    )
    ordered = sorted(
        eligible,
        key=lambda candidate: (-candidate.age_days, candidate.identifier),
    )
    return tuple(
        DeleteAction(candidate.identifier)
        for candidate in ordered[:maximum_deletions]
    )


def execute_cleanup(
    actions: Sequence[DeleteAction],
    executor: DeleteExecutor,
    *,
    dry_run: bool,
) -> ExecutionResult:
    if dry_run:
        return ExecutionResult(planned=len(actions), deleted=0)

    deleted = 0
    for action in actions:
        executor.delete(action.identifier)
        deleted += 1
    return ExecutionResult(planned=len(actions), deleted=deleted)


class FakeExecutor:
    def __init__(self, *, fail_on: str | None = None) -> None:
        self.fail_on = fail_on
        self.calls: list[str] = []

    def delete(self, identifier: str) -> None:
        self.calls.append(identifier)
        if identifier == self.fail_on:
            raise RuntimeError(f"synthetic failure for {identifier}")


class CleanupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.candidates = (
            Candidate("young", age_days=6),
            Candidate("old-b", age_days=90),
            Candidate("old-a", age_days=90),
            Candidate("protected", age_days=365, protected=True),
            Candidate("middle", age_days=45),
        )

    def test_plan_is_bounded_deterministic_and_excludes_protected(self) -> None:
        actions = plan_cleanup(
            tuple(reversed(self.candidates)),
            minimum_age_days=30,
            maximum_deletions=2,
        )

        self.assertEqual(
            actions,
            (DeleteAction("old-a"), DeleteAction("old-b")),
        )

    def test_plan_rejects_duplicate_identifiers(self) -> None:
        with self.assertRaisesRegex(ValueError, "unique"):
            plan_cleanup(
                (Candidate("same", 60), Candidate("same", 90)),
                minimum_age_days=30,
                maximum_deletions=10,
            )

    def test_dry_run_never_calls_executor(self) -> None:
        actions = (DeleteAction("a"), DeleteAction("b"))
        executor = FakeExecutor()

        result = execute_cleanup(actions, executor, dry_run=True)

        self.assertEqual(result, ExecutionResult(planned=2, deleted=0))
        self.assertEqual(executor.calls, [])

    def test_apply_calls_executor_in_plan_order(self) -> None:
        actions = (DeleteAction("a"), DeleteAction("b"))
        executor = FakeExecutor()

        result = execute_cleanup(actions, executor, dry_run=False)

        self.assertEqual(result, ExecutionResult(planned=2, deleted=2))
        self.assertEqual(executor.calls, ["a", "b"])

    def test_failure_propagates_and_exposes_attempted_calls(self) -> None:
        actions = (
            DeleteAction("completed"),
            DeleteAction("fails"),
            DeleteAction("not-attempted"),
        )
        executor = FakeExecutor(fail_on="fails")

        with self.assertRaisesRegex(RuntimeError, "synthetic failure"):
            execute_cleanup(actions, executor, dry_run=False)

        self.assertEqual(executor.calls, ["completed", "fails"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

Run it in a disposable directory:

```bash
python -m unittest -v test_cleanup.py
```

The final test records an important limitation: the function propagates the error but does not persist which action completed. Chapter 74 adds durable operation identity and checkpoints so a restart does not guess.

## 19. Review the suite as production code

Test code can contain defects, obscure intent, and consume significant runtime. Review it for:

- assertions that would fail if the implementation were wrong;
- independence from execution order and developer machines;
- bounded time and resource use;
- meaningful failure messages;
- realistic boundary semantics;
- absence of production credentials and endpoints;
- cleanup under both success and failure;
- a clear owner for fixtures and CI infrastructure.

Occasionally demonstrate that a test catches its target defect by introducing a temporary mutation locally. A test that never fails under a plausible defect may be ceremonial rather than evidential.

## Common Misconceptions

- “All tests should be unit tests.” Unit tests cannot prove compatibility with a real boundary.
- “Mocks make tests realistic.” Mocks prove configured interactions, not external semantics.
- “One hundred percent coverage proves correctness.” Execution without meaningful assertions proves little.
- “Type hints validate API data.” Annotations do not check runtime input by themselves.
- “A flaky test can just be retried.” Automatic retry can conceal a defective product or evidence system.
- “CI is the only place tests need to run.” Slow or inaccessible feedback arrives after development decisions have compounded.

## Core Computer Science Concept

Testing is **systematic sampling of a state space against invariants**. Static analysis proves or approximates properties without executing the program; dynamic tests observe selected executions. Neither covers all possible states, so risk determines how the techniques are combined.

## Engineering Connections

- Pure planning functions turn operational policy into deterministic transformations.
- Narrow protocols apply interface segregation and make authority replaceable.
- Temporary resources extend filesystem isolation to databases, queues, and cloud namespaces.
- Failure injection connects error handling to the observability contract from Chapter 72.
- Reproducible verification commands become the build and CI boundary in later chapters.

## From the Field

A cleanup script has extensive unit tests built around a mocked storage client. The provider changes pagination behavior, and the mock continues returning the old response shape. Tests pass while production processes only the first page and reports success. A small sandbox integration test using multiple pages would have tested the boundary the unit suite assumed.

## Engineering Review

### What problem does this solve?

It creates proportionate, repeatable evidence that automation decisions, boundaries, and failure behavior match their contracts before real systems are affected.

### Why was it designed this way?

Fast pure tests cover policy broadly, controlled boundary tests cover compatibility, and static checks catch defects that do not require execution.

### When should I use it?

Use this layered approach for every maintained automation, increasing isolation, failure injection, and end-to-end evidence with blast radius.

### When should I avoid it?

Avoid costly test layers that cannot exercise a meaningful contract, and avoid doubles that merely reproduce implementation details.

### How does this make me a better engineer?

It teaches you to express invariants, isolate authority, design explicit boundaries, and distinguish confidence from evidence.

### How does this reduce waste?

It catches defects near their source, shortens diagnosis, prevents flaky reruns, limits damaged resources, and keeps manual verification from becoming recurring labor.

## Handbook Principle #73

> Test automation in proportion to its blast radius: prove policy with deterministic values, prove boundaries with disposable reality, and prove failure behavior before production does.

## Practical Observation

Save the complete example as `test_cleanup.py` in a disposable directory and run it. Then reverse the tie-breaker, remove the protected-resource filter, and call the executor during dry-run one change at a time. Confirm that a different focused test fails for each defect. Restore the code and add one table-driven boundary case of your own.

## Looking Ahead

Tests can expose a partial effect, but safe continuation requires the automation to know what operation it is performing and which durable transitions occurred. Chapter 74 designs idempotency, checkpoints, bounded retries, reconciliation, and recovery.

## References

- [Python `unittest` documentation](https://docs.python.org/3.14/library/unittest.html)
- [Python `unittest.mock` documentation](https://docs.python.org/3.14/library/unittest.mock.html)
- [Python `tempfile` documentation](https://docs.python.org/3.14/library/tempfile.html)
- [Python `typing` documentation](https://docs.python.org/3.14/library/typing.html)
- [pytest fixtures](https://docs.pytest.org/en/stable/how-to/fixtures.html)
- [pytest temporary directories and files](https://docs.pytest.org/en/stable/how-to/tmp_path.html)
- [mypy documentation](https://mypy.readthedocs.io/en/stable/)
- [ShellCheck](https://www.shellcheck.net/)
