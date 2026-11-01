# Chapter 72 — Configuration, Secrets, Logging, and Observability

Automation needs runtime choices, authority, and evidence. Mixing those concerns into source code or unstructured print statements makes behavior difficult to reproduce and dangerous to diagnose.

The central idea is:

> Resolve configuration through one documented precedence chain, refer to secrets without exposing them, and emit bounded evidence that explains every run and intended effect.

## 1. Configuration is a versioned runtime contract

Configuration selects behavior without changing program source. It can define an endpoint, timeout, input scope, concurrency limit, feature mode, or reference to a credential.

Every setting needs:

- a stable name and meaning;
- type, unit, range, and allowed values;
- default or required status;
- accepted sources and precedence;
- whether changes require restart or affect work in progress;
- sensitivity and redaction policy;
- compatibility and deprecation behavior.

Do not expose every internal constant as configuration. Each option creates states that need validation, testing, documentation, and support.

Configuration syntax passing does not make a combination safe. A valid endpoint and valid credential reference can still name different security realms.

## 2. Define one precedence chain

Choose and document exactly how sources combine. One common application policy is:

```text
built-in safe defaults
    < configuration file
    < environment variables
    < command-line options
```

Higher sources override lower ones only when explicitly present. An omitted CLI option must not replace a file value with the parser's default.

This ordering is a policy, not a law. Some systems prohibit command-line override of security-critical settings or accept only centrally managed configuration. Name exceptions rather than creating a hidden second chain.

At startup, record which source selected each non-secret setting without necessarily recording its value. This makes an unexpected override diagnosable.

## 3. Defaults must be safe and visible

A default should support the least surprising safe behavior. Good examples include a bounded timeout, one worker, dry-run enabled for a migration tool, or no optional deletion.

Do not default a missing production endpoint to a similarly named public service or a missing tenant to “all tenants.” Required scope and authority should fail closed.

Keep defaults in one typed structure rather than scattering fallback expressions:

```python
DEFAULTS = {
    "timeout_seconds": 5.0,
    "maximum_items": 100,
    "dry_run": True,
    "log_level": "INFO",
}
```

The resolved configuration should be immutable for one run unless live reload is an explicit, synchronized feature. Capturing values at different times can make one run internally inconsistent.

## 4. Files provide reviewable shared configuration

A configuration file can be versioned, reviewed, mounted, and validated before application startup. Use a structured parser rather than executing the file as code.

Python 3.11+ includes a read-only TOML parser:

```python
import tomllib

with path.open("rb") as stream:
    document = tomllib.load(stream)
```

Limit file size before parsing untrusted content, reject unknown keys under a strict schema, and handle malformed syntax with path and line context. Check permissions and ownership according to the deployment boundary.

Do not edit TOML with regular-expression replacement. `tomllib` intentionally does not write TOML, and a serializer may not preserve comments or style.

A file containing plaintext credentials is a secret file, not ordinary configuration. It needs different access, distribution, audit, and rotation controls.

## 5. Environment variables are string inputs

Environment variables work well for small deployment-specific overrides and references injected by a runtime. They are always strings at the application boundary.

Parse explicitly:

```text
"false" is not false merely because it is nonempty
"30" needs range and unit validation
an empty value differs from an absent variable when the contract says so
```

Use an application-specific prefix such as `REPORT_TIMEOUT_SECONDS`. Reject invalid values at startup rather than discovering them halfway through a batch.

Environment variables are inherited by child processes unless the caller constructs a new environment. They can appear in diagnostic dumps and local process inspection under some systems. They are a delivery mechanism, not automatically a secure secret store.

## 6. Command-line options are observable overrides

Command arguments are useful for one-run choices such as input path, dry-run, or output format. They can be visible in shell history, process listings, scheduler definitions, and audit systems.

Never put passwords, tokens, private keys, or sensitive connection strings directly on the command line. Accept a secret reference or protected file descriptor instead.

With `argparse`, use `default=argparse.SUPPRESS` for options whose absence must preserve lower-precedence configuration:

```python
parser.add_argument(
    "--timeout-seconds",
    type=float,
    default=argparse.SUPPRESS,
)
```

After parsing, `vars(namespace)` contains only explicitly supplied values for that option.

## 7. Merge first, validate the final object

Each source should be syntactically decoded, but cross-field validation belongs after precedence resolution:

```text
defaults + file + environment + CLI → merged values → typed Config
```

Validate:

- exact types rather than truthiness;
- ranges, units, and enumerations;
- URL scheme and authority;
- path scope and object type;
- mutually exclusive and required-together fields;
- credential reference compatible with endpoint;
- limits consistent with blast-radius policy.

Return one immutable configuration object. Downstream functions should not reread environment variables or parser namespaces.

Aggregate independent validation errors when that helps operators repair one deployment, but do not continue with a partially valid security policy.

## 8. Store references, not secret values

Ordinary configuration should say which secret is needed:

```toml
[report]
token_reference = "secret://operations/status-api"
```

At runtime, an approved provider resolves that reference for an authorized identity. The program holds the value only as long as required and never serializes it into configuration, logs, metrics, dry-run output, cache keys, exceptions, or child arguments.

A reference is not harmless metadata in every organization; names can reveal customers, environments, or topology. Give references their own disclosure policy.

Prefer short-lived, narrowly scoped, revocable credentials. Sharing one long-lived secret across hosts destroys attribution and enlarges rotation impact.

## 9. Secret handling includes failure and rotation

Define the whole lifecycle:

- creation and authorized distribution;
- in-memory and temporary-storage boundaries;
- use and audit without value disclosure;
- expiration and proactive refresh;
- rotation with an overlap or cutover model;
- revocation and incident containment;
- deletion from logs, artifacts, backups, and history after exposure.

Do not compare or print a secret to diagnose authentication. Log the reference category, credential version identifier if safe, provider outcome, and remote status—not the credential bytes.

If a secret appears in a log or commit, assume exposure. Redaction after the fact does not revoke the copied value; rotate or revoke it.

## 10. Standard output is not the log

A command can reserve stdout for its machine-readable result and stderr for diagnostics or structured events. Mixing them breaks downstream parsers.

Python's `logging` package separates loggers, handlers, filters, and formatters. Application modules should use named loggers and let the entry point configure handlers once.

Avoid configuring the root logger during import. Libraries should not choose the application's destination, retention, or global verbosity.

Log levels need consistent meaning:

- `DEBUG` supplies bounded development detail;
- `INFO` records normal lifecycle and significant outcomes;
- `WARNING` records a recoverable abnormal condition;
- `ERROR` records failed work requiring attention;
- `CRITICAL` is reserved for application- or service-threatening failure.

Volume is a cost and availability concern. A per-item `INFO` event across millions of objects can hide the run outcome and exhaust storage.

## 11. Structured events have a schema

A useful event is a record, not prose that must be parsed later:

```json
{
  "timestamp": "2026-11-01T18:42:19.128Z",
  "level": "INFO",
  "event": "batch.completed",
  "run_id": "36f1c1c5-812c-48e9-941e-b493f99b44fb",
  "outcome": "success",
  "processed": 120,
  "changed": 14,
  "failed": 0,
  "duration_ms": 4821
}
```

Define field names, types, maximum lengths, timestamp basis, event vocabulary, and compatibility policy. JSON encoding escapes embedded newlines, but field values still require size limits and sensitivity review.

Keep the event name stable and put variable data in fields. A dashboard should not need to recognize a hundred sentence variants.

Use UTC timestamps with an explicit offset and a monotonic clock for durations. Wall clocks can jump during a run.

## 12. Correlation identifiers connect one operation

Generate a run identifier at the entry point and attach it to every event, child request, run report, and supported downstream call.

A correlation ID is not authentication and must not grant access. Validate and bound an inbound identifier before logging or forwarding it. Generate a new internal run ID when external values are absent or unsuitable, and retain the relationship only under the data policy.

Use item or operation identifiers for high-value per-object state, but avoid turning every customer identifier into an unrestricted log field.

Correlation enables a timeline; it does not prove causal order across unsynchronized systems. Include operation identifiers and state versions where reconciliation matters.

## 13. Metrics summarize behavior over time

Logs describe events. Metrics provide aggregatable measurements. A batch automation often needs:

- run count by outcome;
- duration distribution;
- items discovered, attempted, changed, skipped, and failed;
- retries and ambiguous outcomes;
- age of last successful run;
- queue depth or oldest pending item;
- dry-run proposed change count;
- configuration or dependency version as bounded resource metadata.

Avoid unbounded labels such as user ID, raw URL, exception message, or file path. High-cardinality dimensions increase cost and can make a metrics system unusable.

A success counter without a last-success timestamp can hide that the scheduler stopped running. A duration without outcome can make fast failures look like performance improvement.

## 14. Redact before formatting

The safest logging design allowlists fields known to be non-secret. Redacting arbitrary completed strings is fragile because secrets can be encoded, split, embedded in URLs, or copied into exception text.

Never log:

- passwords, access tokens, session values, private keys, or encryption keys;
- authorization and cookie headers;
- full connection strings containing credentials;
- raw secret-manager responses;
- unrestricted request or response bodies;
- complete environment dumps;
- sensitive command arguments or subprocess stderr without review.

Hashing an identifier does not automatically anonymize it. Small or known domains can be guessed, and stable hashes enable correlation. Use a keyed pseudonym only when that exact analytical need and key lifecycle are defined.

Test redaction with representative errors. A logger can be safe on success and leak through a library exception on failure.

## 15. Dry-run reports intent, not certainty

A dry run should execute the same discovery, validation, selection, and planning logic as real execution while replacing mutation with an explicit proposed action record.

It should report:

- resolved non-secret configuration and source;
- items inspected and excluded with reasons;
- exact proposed operations and target identifiers;
- preconditions and safety limits;
- uncertainties that require live execution;
- total proposed scope and expected no-op count.

Do not implement dry-run as “return before doing anything.” That tests no planning logic. Conversely, discovery calls can have cost or side effects; document which external reads still occur.

State can change between preview and execution. Revalidate preconditions at mutation time. A dry run is evidence about a plan at one time, not a future guarantee.

## 16. Preserve a terminal run report

Emit one bounded summary when the run reaches success, failure, interruption, or ambiguous completion. It should include:

- run ID, program version, and schema version;
- start, end, and duration;
- dry-run or apply mode;
- counts by outcome;
- final status and stable failure category;
- checkpoint or reconciliation reference;
- locations of controlled detailed evidence;
- configuration fingerprint or version without secret values.

Write the report even when some items fail, and make process exit status reflect the documented batch policy. A JSON summary saying `"failed": 12` with exit status zero may or may not be correct; define the contract.

Logging failure itself needs policy. Do not corrupt application state because an optional debug sink is unavailable, but do not claim an auditable privileged change succeeded when required audit evidence could not be recorded.

## 17. A typed configuration and event example

This Python 3.11+ module resolves defaults, a TOML table, environment values, and explicit CLI options. It emits allowlisted JSON events and never resolves or prints the secret reference:

```python
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import tomllib
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit


class ConfigError(Exception):
    """A controlled configuration failure."""


@dataclass(frozen=True)
class Config:
    endpoint: str
    timeout_seconds: float
    maximum_items: int
    dry_run: bool
    log_level: str
    token_reference: str


DEFAULTS: dict[str, object] = {
    "timeout_seconds": 5.0,
    "maximum_items": 100,
    "dry_run": True,
    "log_level": "INFO",
}

ENVIRONMENT_NAMES = {
    "REPORT_ENDPOINT": "endpoint",
    "REPORT_TIMEOUT_SECONDS": "timeout_seconds",
    "REPORT_MAXIMUM_ITEMS": "maximum_items",
    "REPORT_DRY_RUN": "dry_run",
    "REPORT_LOG_LEVEL": "log_level",
    "REPORT_TOKEN_REFERENCE": "token_reference",
}

ALLOWED_KEYS = set(DEFAULTS) | {"endpoint", "token_reference"}


def load_file(path: Path | None) -> dict[str, object]:
    if path is None:
        return {}
    if path.stat().st_size > 65_536:
        raise ConfigError("configuration file exceeds 65536 bytes")
    try:
        with path.open("rb") as stream:
            document = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"cannot load configuration {path}: {exc}") from exc

    if set(document) != {"report"} or not isinstance(document["report"], dict):
        raise ConfigError("configuration must contain only a [report] table")
    values = document["report"]
    unknown = set(values) - ALLOWED_KEYS
    if unknown:
        raise ConfigError(f"unknown configuration keys: {sorted(unknown)}")
    return dict(values)


def load_environment(environ: Mapping[str, str]) -> dict[str, object]:
    return {
        key: environ[name]
        for name, key in ENVIRONMENT_NAMES.items()
        if name in environ
    }


def parse_cli(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path)
    parser.add_argument("--endpoint", default=argparse.SUPPRESS)
    parser.add_argument(
        "--timeout-seconds", type=float, default=argparse.SUPPRESS
    )
    parser.add_argument(
        "--maximum-items", type=int, default=argparse.SUPPRESS
    )
    parser.add_argument(
        "--dry-run",
        action=argparse.BooleanOptionalAction,
        default=argparse.SUPPRESS,
    )
    parser.add_argument("--log-level", default=argparse.SUPPRESS)
    parser.add_argument("--token-reference", default=argparse.SUPPRESS)
    return parser.parse_args(argv)


def parse_boolean(value: object, name: str) -> bool:
    if type(value) is bool:
        return value
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
    raise ConfigError(f"{name} must be a boolean")


def build_config(values: Mapping[str, object]) -> Config:
    missing = {"endpoint", "token_reference"} - set(values)
    if missing:
        raise ConfigError(f"missing required configuration: {sorted(missing)}")

    endpoint = values["endpoint"]
    token_reference = values["token_reference"]
    if not isinstance(endpoint, str):
        raise ConfigError("endpoint must be a string")
    parts = urlsplit(endpoint)
    if parts.scheme != "https" or not parts.hostname or \
            parts.username is not None or parts.password is not None:
        raise ConfigError("endpoint must be an HTTPS URL without credentials")
    if not isinstance(token_reference, str) or \
            not token_reference.startswith("secret://"):
        raise ConfigError("token_reference must use the secret:// scheme")

    try:
        timeout_seconds = float(values["timeout_seconds"])
        maximum_items = int(values["maximum_items"])
    except (TypeError, ValueError) as exc:
        raise ConfigError("timeout and maximum_items must be numeric") from exc
    if not 0.0 < timeout_seconds <= 60.0:
        raise ConfigError("timeout_seconds must be greater than 0 and at most 60")
    if not 1 <= maximum_items <= 1000:
        raise ConfigError("maximum_items must be from 1 through 1000")

    log_level = values["log_level"]
    if not isinstance(log_level, str) or \
            log_level.upper() not in {"DEBUG", "INFO", "WARNING", "ERROR"}:
        raise ConfigError("log_level is invalid")

    return Config(
        endpoint=endpoint,
        timeout_seconds=timeout_seconds,
        maximum_items=maximum_items,
        dry_run=parse_boolean(values["dry_run"], "dry_run"),
        log_level=log_level.upper(),
        token_reference=token_reference,
    )


def resolve_config(
    file_values: Mapping[str, object],
    environ: Mapping[str, str],
    cli: argparse.Namespace,
) -> Config:
    values = dict(DEFAULTS)
    values.update(file_values)
    values.update(load_environment(environ))
    cli_values = vars(cli).copy()
    cli_values.pop("config", None)
    values.update(cli_values)
    return build_config(values)


def emit_event(event: str, run_id: str, **safe_fields: object) -> None:
    allowed = {
        "outcome", "mode", "processed", "changed", "failed",
        "duration_ms", "failure_category",
    }
    unknown = set(safe_fields) - allowed
    if unknown:
        raise ValueError(f"unsafe or unknown event fields: {sorted(unknown)}")
    record = {
        "timestamp": datetime.now(UTC).isoformat(timespec="milliseconds"),
        "level": "INFO",
        "event": event,
        "run_id": run_id,
        **safe_fields,
    }
    print(json.dumps(record, sort_keys=True), file=sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    started = time.monotonic()
    run_id = str(uuid.uuid4())
    try:
        cli = parse_cli(argv)
        config = resolve_config(load_file(cli.config), os.environ, cli)
    except (ConfigError, OSError) as exc:
        emit_event(
            "run.completed",
            run_id,
            outcome="failure",
            failure_category="configuration",
            failed=1,
            duration_ms=round((time.monotonic() - started) * 1000),
        )
        print(f"configuration error: {exc}", file=sys.stderr)
        return 78

    mode = "dry-run" if config.dry_run else "apply"
    emit_event("run.started", run_id, mode=mode)
    plan = {
        "schema": "report-plan/v1",
        "run_id": run_id,
        "mode": mode,
        "endpoint": config.endpoint,
        "maximum_items": config.maximum_items,
        "timeout_seconds": config.timeout_seconds,
    }
    print(json.dumps(plan, sort_keys=True))
    emit_event(
        "run.completed",
        run_id,
        outcome="success",
        mode=mode,
        processed=0,
        changed=0,
        failed=0,
        duration_ms=round((time.monotonic() - started) * 1000),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

This example produces a plan only; it does not resolve the token or call the endpoint. Its stdout schema is safe for a caller, while stderr events exclude the token reference and environment. A real application would pass a secret-provider client into a narrowly scoped execution function.

## 18. Test configuration and evidence together

In a disposable directory, test:

- defaults with required file values;
- each precedence layer overriding the one below;
- an explicitly empty environment value;
- malformed TOML, unknown keys, and oversized configuration;
- wrong types, ranges, URL schemes, and secret-reference schemes;
- dry-run and apply plans using a fake executor;
- stable stdout schema and separate JSON stderr events;
- identical run IDs across one run's output and events;
- secret-like canary values absent from every output and exception;
- logging sink failure under the documented audit policy.

Capture stdout and stderr independently. Parse every event as JSON and validate its schema rather than comparing presentation strings.

Do not use real production secrets in a redaction test. Use recognizable synthetic canaries and fail the test if any substring appears.

## Common Misconceptions

- “Environment variables are secure because they are not in source.” They can propagate and appear in process or diagnostic surfaces.
- “Logging everything helps incidents.” Excess volume and sensitive content can reduce safety and usefulness.
- “JSON logs are automatically structured and safe.” Fields still need schema, bounds, escaping, and sensitivity policy.
- “A dry run guarantees the real run.” State and authority can change; mutation-time preconditions still need validation.
- “A correlation ID proves identity.” It connects evidence and must never authorize an action.

## Core Computer Science Concept

Operational configuration and telemetry form a **control-and-observation interface**. Configuration selects a state transition; secrets authorize it; logs and metrics expose bounded evidence about the transition without becoming an alternate data leak.

## Engineering Connections

- Precedence resolution is deterministic merging over typed structured data.
- Secret references preserve least authority across HTTP and subprocess boundaries.
- Correlation identifiers connect events across processes and services without replacing authentication.
- Dry-run planning applies the Observe → Understand → Stabilize → Automate sequence from Chapter 64.

## From the Field

A failed API call logs the complete request headers at debug level, including a bearer token. Central log readers now possess production authority, and the token persists in backups after rotation. Allowlisted structured fields, synthetic redaction tests, and logging only the credential reference version would have preserved diagnostic value without duplicating the secret.

## Engineering Review

### What problem does this solve?

It makes runtime behavior predictable, keeps authority out of ordinary configuration and evidence, and explains what each automation run attempted and achieved.

### Why was it designed this way?

Configuration, credentials, and telemetry have different trust and lifecycle requirements even though they meet inside one process.

### When should I use it?

Use these patterns for every automation that varies by environment, uses credentials, or must be diagnosed after unattended execution.

### When should I avoid it?

Avoid adding configurable modes or high-cardinality telemetry without an operational consumer and lifecycle policy.

### How does this make me a better engineer?

It makes you design runtime control, authority, and evidence as explicit interfaces instead of incidental strings.

### How does this reduce waste?

It prevents configuration drift, secret exposure, unparseable logs, blind batch failures, false dry-run confidence, and repeated incident reconstruction.

## Handbook Principle #72

> Resolve one immutable configuration, keep secrets behind narrow references, and emit the minimum structured evidence needed to explain every run and recover safely.

## Practical Observation

Save the complete example in a disposable directory with a TOML file containing synthetic values. Exercise every precedence layer and validation case, capture stdout and stderr separately, and search both for a synthetic secret canary. Parse the plan and events, verify one run ID connects them, then delete the directory.

## Looking Ahead

Part VI's Python phase now has code, data, external, packaging, configuration, and evidence boundaries. Chapter 73 applies testing, linting, and type checking in proportion to the automation's blast radius.

## References

- [Python Logging HOWTO](https://docs.python.org/3.14/howto/logging.html)
- [Python Logging Cookbook](https://docs.python.org/3.14/howto/logging-cookbook.html)
- [Python `tomllib` documentation](https://docs.python.org/3.14/library/tomllib.html)
- [OpenTelemetry signals](https://opentelemetry.io/docs/concepts/signals/)
- [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
