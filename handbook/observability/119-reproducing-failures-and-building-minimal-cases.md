# Chapter 119 — Reproducing Failures and Building Minimal Cases

A reproduction converts a one-time observation into a repeatable experiment. A minimal case removes everything not required for the same failure mechanism. Together they make a bug safe to study, cheap to share, and permanent as a regression fixture.

Reproduction is not always possible. Production may contain unique data, traffic, timing, topology, hardware, or third-party behavior. The engineering obligation is then to identify which dimensions remain unmatched, preserve evidence, and state why the failure is still production-only instead of claiming that it vanished.

This chapter does not cover formal delta-debugging algorithms, unrestricted production traffic replay, or vendor-specific test laboratories.

## 1. Define the behavior before reproducing it

A reproduction needs an oracle: a reliable way to classify a run as the same failure, a pass, or inconclusive.

Define:

- exact setup and preconditions;
- action or input;
- expected result;
- observed failure signature;
- timeout and completion criteria;
- cleanup and reset steps;
- evidence captured on each run.

For the Atlas Tasks incident:

> With 40 API instances each requesting a minimum of 10 primary database connections, lower the database connection limit to 250 and submit 300 task updates per second for five minutes. The case fails when at least 5% of valid writes return `503` and failed traces spend more than 1.5 seconds acquiring a connection while query execution p95 remains below 50 ms.

That is more useful than “load test until writes fail.” It identifies the mechanism, not merely an error code that many faults could produce.

## 2. Preserve the original failure signature

A smaller example is valid only if it continues to represent the original fault. Compare several independent signatures:

- exception type, message, and stack location;
- failed invariant or incorrect output;
- request phase and dependency boundary;
- resource or timing pattern;
- affected versions and scope;
- crash address or diagnostic fingerprint where appropriate;
- corrective change that makes both cases pass.

If production times out during connection acquisition but the local case fails authentication, both may return `503` but they are different failures. If reducing a race changes a deadlock into a deterministic assertion, the minimized input may have removed the mechanism under study.

Record the signature before minimization and recheck it after every major reduction.

## 3. Capture the environment as input

“Works on my machine” usually means the environment was not modeled. Capture the dimensions that can affect behavior:

- source revision and uncommitted changes;
- build flags, generated code, and artifact digest;
- runtime, library, driver, and operating-system versions;
- CPU architecture and relevant hardware features;
- configuration, feature flags, locale, timezone, and encoding;
- dependency endpoints and protocol versions;
- schema and migration state;
- container image and orchestration settings;
- resource limits, process count, and concurrency;
- clock source, random seed, and test order;
- sanitized input data and its checksum.

Capture values, not merely filenames. `requirements.txt` does not prove which transitive versions were installed; `latest` does not identify an image; “production config” changes over time.

Never copy secrets or personal data into a reproduction manifest. Record secret identifiers or required capabilities, and create synthetic substitutes.

## 4. Write a clean-room recipe

A good reproduction starts from an empty disposable environment, not from a developer workstation carrying unknown state. The recipe should state:

1. prerequisites and their versions;
2. exact source or artifact identity;
3. environment construction;
4. sanitized fixture creation;
5. one command to execute the case;
6. pass, fail, and inconclusive exit meanings;
7. expected duration and resource use;
8. evidence location;
9. cleanup.

Have another person or automated worker run it without oral instructions. Missing setup steps appear quickly.

Containers and virtual machines can package many dependencies, but they do not automatically reproduce kernel behavior, CPU architecture, external services, network topology, time, or load. Treat the image digest as one input among many.

## 5. Establish a reproducibility rate

One successful reproduction proves possibility, not reliability. Run repeated trials and report the ratio:

```text
environment: disposable cell simulator, revision 8f4c2d1
trials: 50
same-signature failures: 43
passes: 6
inconclusive setup failures: 1
reproduction rate: 43 / 49 classified trials = 87.8%
```

Separate infrastructure failures from test outcomes. A fixture download failure should not count as the product bug passing.

For a deterministic case, expect the same classification every run. For timing or race failures, the rate and confidence interval matter. An apparent fix that moves failure frequency from 1 in 20 runs to 1 in 100 is not proved by ten passing trials.

Use enough repetitions to distinguish a meaningful change, and report the remaining uncertainty honestly.

## 6. Control randomness without hiding it

Record pseudo-random seeds and print the seed on failure. A compatible generator can reproduce a sequence from the same seed, but results can still change with runtime version, algorithm, thread scheduling, iteration order, or consumption order.

Use two modes:

- fixed seeds for regression and debugging;
- varied recorded seeds for exploration.

Do not make every test use one permanent seed and conclude the state space is covered. When a generated case fails, preserve the seed and preferably serialize the minimized input, because seed semantics may not survive tool upgrades.

Cryptographic randomness and operating-system scheduling are not generally reproducible by setting an application seed.

## 7. Control time explicitly

Time-dependent failures need more than setting the wall clock. Identify:

- wall versus monotonic time;
- timezone and daylight-saving behavior;
- clock resolution and skew;
- lease, cache, retry, and deadline durations;
- scheduled-job boundaries;
- token and certificate validity;
- dependency timestamps;
- pause, suspend, and clock-step behavior.

Inject a controllable clock into business logic where practical. Advance it deliberately instead of sleeping for long durations. Keep integration tests for real clock and scheduler behavior because a fake clock cannot reproduce kernel timers or distributed skew.

Record timeouts as part of the case. Increasing a timeout until a flaky test passes can conceal a deadlock, overload mechanism, or invalid latency expectation.

## 8. Reproduce concurrency with coordination, not sleep

Race conditions depend on ordering. Arbitrary sleeps make the window wider but remain sensitive to machine speed. Prefer explicit synchronization hooks in a test build:

1. worker A reads version 7 and pauses at a barrier;
2. worker B reads version 7 and commits version 8;
3. release worker A;
4. verify its conditional write conflicts rather than overwrites.

For deadlocks, coordinate each participant to hold one resource before requesting the other. For queue races, pause between message claim and acknowledgement. For initialization races, barrier concurrent first requests.

Instrumentation can change scheduling—the observer effect. Keep a lower-intrusion mode and compare the original signature. Stress repetition, scheduler variation, sanitizers, and record/replay tools may help, but each has boundaries.

## 9. Capture data shape without copying sensitive data

Failures often depend on shape rather than exact values:

- length and distribution;
- null, empty, duplicate, or boundary values;
- character classes and normalization;
- graph depth or cycle;
- row count and skew;
- ordering and correlation;
- compressed or encoded size;
- tenant and authorization relationships.

Create synthetic data that preserves the relevant property. If an SQL plan changes because one tenant owns 40% of rows, a uniform generator is not representative. If a parser fails on a combining character, replacing all text with ASCII removes the cause.

Maintain a mapping from production evidence to synthetic properties, not a copied dataset. Apply access control and retention to diagnostic artifacts because even sanitized samples can reveal structure.

## 10. Reproduce external dependencies at the right fidelity

Choose among:

- real dependency in an isolated account;
- local emulator known to match the required semantics;
- protocol stub with scripted responses;
- fake implementation for application behavior;
- recorded interaction with sensitive fields removed and replay authorization checked.

A mock that returns the response you expect cannot reveal a TLS, retry, streaming, throttling, or consistency defect. A real dependency may be costly, slow, unsafe, or non-deterministic.

State which properties the substitute preserves: status and body, latency, connection reuse, ordering, duplicate delivery, rate limits, authentication, or failure modes. Use the lightest substitute that retains the suspected mechanism.

Contract tests should detect when a fake drifts from the real interface.

## 11. Minimize one dimension at a time

Start from a reproducing case and remove or simplify one dimension:

- data records;
- request fields;
- sequence steps;
- services and dependencies;
- configuration options;
- concurrency participants;
- source changes;
- environment packages;
- permissions;
- feature flags.

After each change, run enough trials and verify the same signature. If the case stops failing, restore that dimension and reduce elsewhere. Keep a log of removed and required elements.

Large chunks reduce quickly: halve a record set, remove half a request sequence, disable half a feature set. Once near the boundary, remove elements individually. This is conceptually similar to binary search, but interactions mean two individually unnecessary elements may be necessary together.

Minimal means no known element can be removed under the chosen method while retaining the signature. It does not prove a globally smallest case.

## 12. Preserve dependencies among removals

Naive reduction can fail when features interact. Suppose a bug requires both cache reuse and authorization revocation. Removing either stops the failure, so each looks necessary. But two logging modules may be removable only together because one references the other.

Track dependencies among fixture pieces. Reduce coherent groups first, then split them. If the test becomes invalid rather than passing, classify it as inconclusive; do not infer that the removed element causes the bug.

A schema field may be structurally required but irrelevant to the failure. Replace it with the simplest valid value rather than removing it. Validity constraints and causal requirements are different.

## 13. Bisect code, configuration, and inputs

If known-good and known-bad states exist, bisection can isolate a transition:

- revision history with `git bisect`;
- configuration changes by time or version;
- schema migrations;
- dependency upgrades;
- feature-flag sets;
- input size or ordered event sequence.

The classifier must be automated and stable. For Git, exit success for good, failure for bad, and the documented skip code for untestable revisions. Preserve the bisect log so the result can be replayed.

Historical revisions may require matching build tools, dependencies, schemas, and data. If the environment changes along with the code, the bisect may attribute the transition to a revision that merely exposes an environmental incompatibility. Package the historical test environment or record the limitation.

## 14. Use feature flags as experimental dimensions

Feature flags can narrow a failure by cohort or component without redeploying. Record flag definitions, evaluation context, default, version, and dependencies. A screenshot of a control panel is not enough.

Change one logical feature boundary at a time. Flags often interact, and disabling a feature may change load or traffic shape for the whole system. Use an unchanged control cohort and monitor indirect effects.

Do not leave diagnostic combinations permanently supported by accident. Clean up temporary flags and codify the final regression fixture.

## 15. Define record-and-replay boundaries

Replay can reproduce deterministic processing of captured inputs, but it does not automatically reproduce:

- concurrency and timing;
- external state changes;
- random values not captured;
- network loss and backpressure;
- identity and secret lifecycles;
- nondeterministic database plans;
- side effects already performed.

Record at a boundary where inputs can be authorized, minimized, redacted, versioned, and replayed safely. Replace external effects with isolated targets. Never replay production writes, emails, payments, or privileged operations into live systems.

Include schema and recorder version. A replay that silently drops unknown fields can manufacture a different case.

## 16. Use disposable environments

A disposable environment begins from declared inputs and can be destroyed without losing evidence. It prevents hidden local state, protects shared systems, and makes repeated trials affordable.

Pin source revisions, dependency versions, and container image digests where exact identity matters. Save build provenance and fixture checksums. Clear databases, caches, queues, temporary files, and process state between trials unless persistence is the variable being tested.

Teardown must target only the isolated environment. Label resources, validate identifiers, and set expiry. Cleanup that reaches shared or production data is a greater defect than the one being reproduced.

Rebuild periodically from the recipe; a long-lived “test box” becomes another undocumented environment.

## 17. Avoid observer and cleanup effects

Debug builds, trace logging, sanitizers, breakpoints, and instrumentation can change memory layout, timing, optimization, I/O, and concurrency. If a failure disappears:

- compare instrumented and uninstrumented rates;
- use lower-overhead signals;
- capture state after rather than during the critical window;
- reproduce under multiple optimization levels;
- make instrumentation itself a recorded dimension.

Cleanup can also change the case. A test that succeeds only after clearing a cache proves persistent state matters; it does not prove the cache is corrupt. Alternate clean and reused-state trials to isolate the condition.

## 18. Convert the case into a regression fixture

Once the mechanism is understood:

1. keep the smallest representative input or construction recipe;
2. assert the invariant, not incidental output;
3. prove the test fails on the broken state and passes with the correction;
4. place it at the cheapest reliable test layer;
5. retain an integration case when lower layers cannot preserve the mechanism;
6. record the bug and decision context;
7. remove secrets, personal data, and excessive artifacts;
8. define ownership and flake policy.

A regression test that never failed against the defect may test the wrong thing. Demonstrate the red-to-green transition using a safe historical revision, reverted fix, or isolated faulty implementation.

Do not make timing tests pass by retrying them silently. Report flakes and fix or quarantine them with ownership and evidence.

## 19. State why a failure remains production-only

Sometimes no safe reproduction exists. Write a bounded statement:

```text
Reproduced: the same database wait signature at 2,300 requests/second in the
cell simulator on the production artifact and configuration snapshot.

Not reproduced: the sharp 14:05 onset. The simulator cannot reproduce the
managed database control-plane connection redistribution observed in cell B.

Evidence retained: failed traces, pool gauges, database events, configuration
versions, and ten sanitized request shapes.

Next evidence: add connection-generation identifiers and wait-reason sampling;
reopen on the next managed event or if error rate exceeds 0.5% for five minutes.
```

This is actionable. “Only happens in prod” is not.

Avoid exporting unrestricted production traffic or data to close the gap. Add bounded instrumentation, use synthetic cohorts, mirror only authorized metadata, or wait for the trigger under improved observation.

## 20. Apply minimization to the task-platform failure

The original incident includes 40 API instances, normal mixed traffic, three cells, search, notifications, autoscaling, and a database configuration change.

Reduction proceeds:

1. Use only cell B and synthetic task writes; signature remains.
2. Disable search and notification consumers; signature remains.
3. Replace task bodies with one fixed valid payload; signature remains.
4. Remove tenant skew; signature remains.
5. Fix instance count at 40; signature remains, so autoscaling is an amplifier but not required.
6. Reduce to 26 instances with minimum pool 10 against limit 250; signature remains.
7. Reduce to 25 instances; no exhaustion, establishing the capacity boundary.
8. Lower pool minimum to 9 at 26 instances; signature disappears.

The minimal model is aggregate requested minimum connections exceeding the database limit under concurrent acquisition. The production case adds autoscaling, which worsens it. The regression fixture asserts the configuration invariant and an integration test verifies bounded acquisition behavior.

## 21. Encode a reproduction manifest

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class ReproductionManifest:
    failure_signature: str
    expected_result: str
    source_revision: str
    artifact_digest: str
    environment_fingerprint: str
    sanitized_fixture_digest: str
    command: str
    classified_trials: int
    matching_failures: int
    inconclusive_trials: int
    reset_between_trials: bool
    same_mechanism_verified: bool
    cleanup_target_isolated: bool
    regression_fixture: str

    def validate(self) -> None:
        required = (
            self.failure_signature,
            self.expected_result,
            self.source_revision,
            self.artifact_digest,
            self.environment_fingerprint,
            self.sanitized_fixture_digest,
            self.command,
        )
        if not all(value.strip() for value in required):
            raise ValueError("manifest lacks identity, environment, fixture, or oracle")
        if self.classified_trials <= 0:
            raise ValueError("reproduction has no classified trials")
        if not 0 <= self.matching_failures <= self.classified_trials:
            raise ValueError("matching failure count is invalid")
        if self.inconclusive_trials < 0:
            raise ValueError("inconclusive count is invalid")
        if not self.reset_between_trials:
            raise ValueError("trial state is not controlled")
        if not self.same_mechanism_verified:
            raise ValueError("minimal case changed the failure mechanism")
        if not self.cleanup_target_isolated:
            raise ValueError("cleanup can affect shared resources")
        if not self.regression_fixture.strip():
            raise ValueError("reproduction was not preserved as a fixture")

    @property
    def reproduction_rate(self) -> float:
        return self.matching_failures / self.classified_trials
```

Tests protect the provenance and safety of the case:

```python
from dataclasses import replace
import unittest

from reproduction_manifest import ReproductionManifest


def valid_manifest() -> ReproductionManifest:
    return ReproductionManifest(
        failure_signature="503 after >1.5s connection acquisition",
        expected_result="write completes within 500ms",
        source_revision="8f4c2d1",
        artifact_digest="sha256:abc123",
        environment_fingerprint="linux-amd64; runtime-3.15; db-schema-42",
        sanitized_fixture_digest="sha256:def456",
        command="python reproduce_pool_exhaustion.py --seed 118119",
        classified_trials=49,
        matching_failures=43,
        inconclusive_trials=1,
        reset_between_trials=True,
        same_mechanism_verified=True,
        cleanup_target_isolated=True,
        regression_fixture="tests/regression/test_pool_capacity.py",
    )


class ReproductionManifestTests(unittest.TestCase):
    def test_complete_manifest_is_accepted(self):
        manifest = valid_manifest()
        manifest.validate()
        self.assertAlmostEqual(43 / 49, manifest.reproduction_rate)

    def test_unidentified_artifact_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "identity"):
            replace(valid_manifest(), artifact_digest="").validate()

    def test_zero_trials_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "classified"):
            replace(valid_manifest(), classified_trials=0).validate()

    def test_impossible_failure_count_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "failure count"):
            replace(valid_manifest(), matching_failures=50).validate()

    def test_state_leak_between_trials_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "state"):
            replace(valid_manifest(), reset_between_trials=False).validate()

    def test_changed_failure_mechanism_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "mechanism"):
            replace(valid_manifest(), same_mechanism_verified=False).validate()

    def test_unsafe_cleanup_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "shared"):
            replace(valid_manifest(), cleanup_target_isolated=False).validate()

    def test_unpreserved_case_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "fixture"):
            replace(valid_manifest(), regression_fixture="").validate()


if __name__ == "__main__":
    unittest.main()
```

The manifest cannot prove causality, but it makes identity, repeatability, mechanism, isolation, and preservation reviewable.

## 22. Review a reproduction

Before sharing or accepting a minimal case, ask:

### Identity and oracle

- Are expected behavior and the original failure signature precise?
- Are source, artifact, dependency, configuration, schema, data, and platform versions captured?
- Can a run be classified as fail, pass, or inconclusive automatically?

### Repeatability and reduction

- Does the recipe start from a clean disposable environment?
- Are seeds, time, ordering, concurrency, and persistent state controlled or recorded?
- Is the reproduction rate reported across classified trials?
- Was one dimension reduced at a time and the same mechanism reverified?
- Are required validity fields distinguished from causal inputs?

### Safety and preservation

- Is production data synthetic or properly minimized and protected?
- Are external side effects isolated?
- Can cleanup touch only explicitly labeled disposable targets?
- Does the regression fixture fail on the defect and pass with the correction?
- If production-only, are unmatched dimensions, retained evidence, and reopening triggers explicit?

## Common Misconceptions

- **“It happened twice, so the test is deterministic.”** Repeatability needs classified trials and controlled state.
- **“A container reproduces the environment.”** Kernel, hardware, topology, dependencies, time, and load may remain different.
- **“Same error code means same bug.”** Verify mechanism with several independent signatures.
- **“Set a seed and concurrency becomes deterministic.”** Scheduling and consumption order can still vary.
- **“Minimal means the fewest lines.”** Preserve the causal mechanism, not an aesthetic size target.
- **“Mocks are safer versions of real dependencies.”** They may omit the exact protocol or failure semantics required.
- **“Cannot reproduce means cannot fix.”** Production evidence can still narrow mechanisms and guide bounded instrumentation.

## Core Computer Science Concept

This chapter applies **experimental repeatability, state-space reduction, equivalence of failure signatures, binary search, controlled nondeterminism, provenance, isolation, and regression oracles**. Minimization reduces the dimensions of a failing state without crossing into a different behavior.

## Engineering Connections

- Disposable environments and fixtures extend Chapters 73, 83, 88, and 100.
- Version identity and bisection build on Chapters 29, 33, 36, and 118.
- Timing, ordering, and partial failure use Chapters 110, 112, 113, and 114.
- Security and data minimization follow Chapters 104 and 115.
- Chapter 120 instruments structured evidence when the failure cannot yet be reproduced.

## From the Field

A team copies a production request into a local test and gets the same `503`, then declares success. Locally the request fails because an expired token was copied; in production it timed out waiting for a database connection. The shared status code hid two mechanisms. Comparing request phase, trace shape, and corrective change would have rejected the false reproduction before it sent investigation in the wrong direction.

## Engineering Review

### What problem does this solve?

It transforms unstable or environment-specific failures into repeatable experiments that can be safely reduced, shared, corrected, and retained.

### Why was it designed this way?

Explicit provenance and failure signatures prevent a convenient test from silently substituting a different bug for the original one.

### When should I use it?

Use it after a failure is observed and scoped, before making broad corrective changes, and whenever a regression fixture can preserve the learning.

### When should I avoid it?

Do not replay sensitive production data or side effects merely to achieve fidelity; use bounded evidence and synthetic equivalents.

### How does this make me a better engineer?

You learn to model environment as input, control nondeterminism, reduce causal dimensions, and distinguish absence of reproduction from absence of defect.

### How does this reduce waste?

It shortens test cycles, improves bug handoff, avoids chasing false reproductions, makes bisection reliable, and prevents fixed defects from returning.

## Handbook Principle #119

> Reproduce the mechanism, not merely the message: capture identity and environment, control state and nondeterminism, minimize one dimension at a time, and preserve the smallest faithful case as a regression fixture.

## Practical Observation

Run an existing flaky test fifty times from a clean state while recording seed, duration, environment, and failure signature. Separate setup failures from the target failure. The resulting distribution usually reveals that “flaky” was hiding several different cases.

## Looking Ahead

Chapter 120 designs logs as bounded structured evidence so a failed request can be reconstructed even when a safe local reproduction does not yet exist.

## References

- [Chromium — Bug reporting guidelines](https://www.chromium.org/for-testers/bug-reporting-guidelines/)
- [Chromium — Reproducing ClusterFuzz bugs](https://www.chromium.org/Home/chromium-security/bugs/reproducing-clusterfuzz-bugs/)
- [Git documentation — git-bisect](https://git-scm.com/docs/git-bisect)
- [Python documentation — Notes on reproducibility for random](https://docs.python.org/3/library/random.html#notes-on-reproducibility)
- [Docker documentation — Build context](https://docs.docker.com/build/concepts/context/)
- [Docker documentation — Building best practices](https://docs.docker.com/build/building/best-practices/)
- [Chapter 118 — Debugging as Hypothesis Testing](118-debugging-as-hypothesis-testing.md)
