# Chapter 120 — Logs and Structured Events

A log is an event record emitted because a future operator, developer, security responder, or automated system may need evidence about what happened. It is not a transcript of every line executed and not a substitute for metrics or traces.

Good logging lets an investigator reconstruct one failed journey across components without exposing credentials, retaining unnecessary personal data, or paying to store millions of indistinguishable messages. That requires event schemas, stable identity, bounded context, lifecycle policy, and tests.

This chapter focuses on application and service events. It does not administer a log vendor, define an enterprise-wide schema, or operate a security information and event management platform.

## 1. Emit events, not prose fragments

Compare:

```text
something went wrong for task 8392
```

with a structured event:

```json
{
  "event_name": "task.update.failed",
  "event_version": 2,
  "occurred_at": "2026-11-01T14:07:31.482Z",
  "severity": "error",
  "service": "task-api",
  "service_version": "2026.11.1",
  "environment": "production",
  "cell": "b",
  "request_id": "req_01JBN7...",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "tenant_ref": "tn_8f16...",
  "operation": "task.update",
  "outcome": "dependency_timeout",
  "dependency": "primary_database",
  "duration_ms": 2004,
  "error_type": "ConnectionAcquireTimeout"
}
```

The second record has stable fields that can be filtered, aggregated, validated, and joined. Its human-readable rendering can change without breaking queries.

Keep an optional message for human orientation, but do not bury important dimensions inside interpolated text.

## 2. Define the purpose of each event

An event should answer a real question. Common purposes include:

- reconstructing a user or asynchronous journey;
- diagnosing a failed state transition;
- proving a security-relevant action occurred;
- explaining configuration or lifecycle change;
- identifying dependency and resource failure;
- providing detail behind a metric or alert;
- preserving evidence that a recovery or deletion step completed.

Avoid “just in case” emission. If no likely consumer or question exists, the event adds cost and noise. Conversely, a single generic error event cannot explain every workflow.

Document the owner, intended use, sensitivity, expected volume, and retention class. That turns log design into an interface rather than scattered print statements.

## 3. Use a stable event envelope

A shared envelope makes records from different services queryable. Useful fields include:

| Field | Meaning |
| --- | --- |
| `event_name` | Stable class of occurrence, such as `task.update.failed` |
| `event_version` | Schema version, not application version |
| `occurred_at` | Time the source says the event happened |
| `observed_at` | Time the collector observed it, when different |
| `severity` | Operational significance under a defined policy |
| `service`, `service_version` | Emitting component and build identity |
| `environment`, `region`, `cell`, `instance` | Resource and deployment context |
| `request_id`, `trace_id`, `span_id` | Journey and causal correlation |
| `tenant_ref`, `subject_ref` | Approved pseudonymous scope references |
| `operation`, `outcome` | Business or technical action and result |
| `error_type`, `error_code` | Stable failure classification |
| `attributes` | Event-specific, bounded structured fields |

Follow common telemetry conventions where they fit. OpenTelemetry's log data model separates event timestamp, observed timestamp, trace context, severity, resource, instrumentation scope, body, event name, and attributes.

Do not make every field mandatory. A startup event has no request ID; a collector-derived record may not know occurrence time. Define required fields per event family.

## 4. Name events for occurrences, not code locations

Use stable domain or operational names:

- `task.update.accepted`;
- `authorization.denied`;
- `queue.message.dead_lettered`;
- `database.connection_pool.exhausted`;
- `tenant.deletion.completed`;
- `configuration.loaded`.

Avoid names such as `handler_error_7`, filenames, method names, or arbitrary English sentences. Refactoring should not break dashboards and investigations.

An event name describes what occurred; fields describe this occurrence. Do not create a distinct name for every tenant, status code, or error string. That moves high-cardinality data into the schema itself.

Version the schema when field meanings or required structure change incompatibly. Additive optional fields often do not require a new version, but consumers must tolerate them.

## 5. Record event time and observation time

Distributed pipelines can delay and reorder records. Preserve:

- **occurrence time:** the source's best estimate of when the event happened;
- **observation time:** when a collector or receiver saw it;
- ingestion time where the storage system adds it.

Use an unambiguous timestamp with timezone, commonly UTC in an RFC 3339 profile, and enough resolution for the question. Also record monotonic duration for elapsed-time measurement; subtracting wall-clock timestamps can be wrong if clocks step.

Clock synchronization reduces error but does not produce perfect global order. For causal order, use trace relationships, message identities, aggregate versions, queue offsets, or logical sequence fields.

When timestamps come from a user device or external system, record source and confidence rather than presenting them as authoritative server time.

## 6. Define severity as operational meaning

Severity should be consistent enough that filtering has meaning:

- **debug/trace:** high-detail diagnostic evidence, normally disabled or sampled;
- **info:** expected lifecycle or business events useful for operation;
- **warn:** abnormal or degraded behavior handled within contract;
- **error:** an operation failed or an invariant was violated and needs investigation;
- **fatal:** the process or critical subsystem cannot continue safely.

An HTTP `404` for an optional lookup may be normal, while a `200` response containing a violated invariant can be an error. Severity is not a direct mapping from status code.

Do not emit the same failure as `error` at every layer. The boundary that owns or observes the failed operation should record the definitive event; lower layers can attach structured error context to a trace or propagate the exception. Duplicate error logs distort counts and cost.

Alerts should rarely be defined as “any error log.” Chapter 121 will derive alerts from user impact and objectives.

## 7. Correlate one journey across boundaries

Identifiers have distinct jobs:

- **request ID:** one service-entry request;
- **trace ID:** a causal journey across services and asynchronous hops;
- **span ID:** one operation within the trace;
- **message/event ID:** durable asynchronous identity;
- **idempotency key:** deduplicates one semantic operation;
- **aggregate ID and version:** business object and ordered state;
- **tenant and subject references:** authorization and scope context.

Do not call all of them `correlation_id`. Carry the appropriate identity through HTTP, queues, schedules, retries, and repair tools. W3C Trace Context defines interoperable trace propagation fields, but a trace ID is not authorization proof and may carry privacy risk through correlation.

Validate incoming identifiers. Generate a trusted internal value when absent or malformed, and avoid allowing attackers to inject delimiters, unbounded strings, or another tenant's context into evidence.

## 8. Log route templates, not raw destinations

Raw URLs and query strings can contain task titles, search terms, access tokens, email addresses, and high-cardinality identifiers. Prefer:

```json
{
  "http.request.method": "PATCH",
  "http.route": "/tenants/{tenant_id}/tasks/{task_id}",
  "http.response.status_code": 503,
  "server.address": "api.example.invalid"
}
```

Record approved pseudonymous resource references only when investigation needs them. Normalize paths and error classifications so aggregation remains useful.

Headers, cookies, request bodies, SQL text with literals, and object contents should not be logged by default. If a bounded diagnostic case requires payload detail, use an allow-listed extractor, strict size limit, short retention, access restriction, and explicit disable time.

## 9. Prefer allow-listed fields and typed values

An allow list begins with fields known to be useful and safe. A deny list tries to recognize every secret name after arbitrary objects have already been serialized and will eventually miss one.

Use types consistently:

- durations as numeric milliseconds or standardized units, not `"two seconds"`;
- counts as integers;
- outcomes and error codes as bounded enumerations;
- booleans as booleans;
- identifiers as strings with length and character constraints;
- nested structures only when consumers support them predictably.

Limit field size, nesting depth, and array length. One malicious input or stack trace must not create a multi-megabyte event.

Do not serialize entire request, response, user, exception, or configuration objects. Their fields evolve outside the event schema and will eventually contain sensitive data.

## 10. Treat logs as sensitive data stores

Logs can centralize data from every service and often have broad readership. Exclude or transform:

- passwords, authentication factors, access and refresh tokens;
- session identifiers and private keys;
- connection strings and secret-bearing URLs;
- raw personal or regulated data not required for the purpose;
- full request and response bodies;
- payment or government identifiers;
- customer content and attachments;
- data classified above the logging system's protection level.

Pseudonymization reduces direct exposure but does not make data anonymous. Stable hashed identifiers can still link a person's activity over time. Use a purpose-specific keyed transformation when stable lookup is necessary, rotate it deliberately, and restrict who can reverse or correlate.

Apply access control, encryption, retention, deletion policy, and access auditing to the log platform itself. Debug exports and local copies need the same lifecycle.

## 11. Prevent log injection

Untrusted text may contain newlines, terminal control codes, delimiters, or JSON-like fragments that forge records or mislead viewers. Use a structured encoder that escapes values for the output format. Parameterized logger calls reduce accidental formatting but do not by themselves sanitize carriage returns and line feeds in every sink.

Validate fields from other trust zones. If a value is malformed, omit or replace that field with bounded safe context and emit a validation result; do not discard an important security event entirely.

Treat log viewers and query interfaces as applications exposed to hostile data. Encode on display, restrict links, and do not execute markup, scripts, or terminal sequences from event content.

Cap event and field sizes so an attacker cannot turn logging into storage or memory exhaustion.

## 12. Classify errors without losing diagnostic detail

An error event should carry stable fields:

- operation and outcome;
- error type or code;
- ownership boundary and dependency;
- retryability or final disposition;
- duration and attempt number;
- relevant resource state in bounded form;
- trace and request identity;
- stack trace when it adds actionable information.

Do not use raw exception text as the aggregation key. It can contain identifiers and changes across versions. Map expected failures to stable codes while preserving an escaped message or stack in a restricted field when needed.

Log a stack at the layer that has enough context to classify the failed operation. Re-logging the same stack at five layers increases volume without adding evidence. For handled expected errors, a stack may be unnecessary; for an unexpected invariant violation, it can be essential.

Chain or group causes structurally rather than concatenating them into one ambiguous message.

## 13. Distinguish logs, metrics, traces, and audit records

- **Logs/events** explain discrete occurrences with contextual detail.
- **Metrics** summarize behavior over dimensions and time efficiently.
- **Traces** represent causal work and timing across operations.
- **Audit records** preserve accountable security or business actions under stronger completeness, integrity, and retention requirements.

One occurrence may produce several signals, but do not force one store to satisfy every need. A high-volume success event may be aggregated into a metric and sampled as a log. A permission change may require an unsampled audit event even if an ordinary debug pipeline is degraded.

Security audit evidence often needs separate access, retention, immutability, and delivery guarantees. Calling an application log “audit” does not provide those properties.

## 14. Sample without erasing rare failures

Sampling controls volume and cost but changes what absence means. Strategies include:

- fixed-rate sampling for homogeneous success events;
- head sampling decided when a request begins;
- tail sampling after an outcome is known;
- keep-all rules for errors, high latency, security events, or rare cohorts;
- deterministic sampling by trace or stable key;
- adaptive sampling under extreme volume;
- aggregation of repeated identical events with counts.

Record sampling policy or weight when downstream analysis needs estimates. Keep all events required for audit or correctness unless their separate pipeline defines another approved guarantee.

Head sampling may discard the trace that later fails. Tail sampling captures outcomes but requires buffering and has resource limits. Error-only retention misses slow successes and the normal comparison group. Preserve enough successes to establish a baseline.

## 15. Control cardinality and volume

Cardinality is the number of distinct values a field can take. Request IDs, user IDs, task IDs, raw URLs, error messages, and stack traces are high-cardinality. They are useful for lookup in event storage but dangerous as indexed facets, metric labels, or partition keys.

Classify fields:

- bounded dimensions for common aggregation: service, environment, route, outcome, error code;
- high-cardinality lookup fields: request, trace, tenant, resource reference;
- large diagnostic fields: stack, safe message, bounded payload fragment.

Choose indexing and retention accordingly. Estimate daily volume:

```text
events/day × average encoded bytes × replication × retention days
```

Include collector overhead, indexes, parsing, transfer, and queries. A harmless debug event emitted in a tight loop can become the largest system cost or fill local disk.

Use per-event volume budgets and alerts for unexpected schema or rate growth.

## 16. Design retention by event class

Retention follows purpose, investigation horizon, privacy risk, legal or contractual need, and cost. Different classes need different policies:

- short-lived debug detail;
- operational application events;
- security detections;
- accountable audit records;
- local buffers awaiting delivery;
- exported incident evidence under a case-specific hold.

Do not keep all logs forever. Do not delete audit evidence according to an arbitrary application-debug window. Document archive, access, deletion, and backup behavior.

When an event contains tenant or personal references, define how tenant deletion and individual privacy requests interact with required security or legal retention. This needs qualified organizational guidance; the technical design should make categories and copies discoverable.

## 17. Make logging failure behavior explicit

Logging is a dependency. It can block, allocate memory, fill disk, lose network connectivity, reject schema, or expose data through fallback output.

Choose behavior by event class:

- ordinary diagnostic events may use bounded asynchronous buffers and drop with counters;
- high-value audit events may require a durable local handoff or make the business operation fail if accountability cannot be preserved;
- fatal startup evidence may write to a protected local fallback;
- no logger should recurse indefinitely while reporting its own failure.

Never let an unbounded event queue consume the service. Expose dropped, rejected, delayed, and oversized event counts as metrics. Protect application storage from log-file exhaustion with separate quotas or streams.

Test collector outage, slow sink, invalid schema, full disk, lost permissions, and oversized events.

## 18. Govern dynamic log levels

Temporary debug logging can expose data, change timing, and multiply cost. A safe change policy specifies:

- who can change levels and for which service or cohort;
- approved fields at each level;
- maximum duration and automatic expiry;
- event-rate and byte limits;
- access and change audit;
- rollback trigger;
- whether restart is required;
- how secrets remain excluded at every level.

“Debug” must not mean serialize everything. The same redaction and schema rules apply.

Prefer targeted activation by request, tenant cohort, instance, or trace when authorized. Avoid allowing a client header to turn on privileged logging without server-side authentication and policy.

## 19. Keep schemas compatible and discoverable

Store event definitions with code or in a versioned schema registry. For each event, document:

- name, version, owner, and purpose;
- required and optional fields with types;
- bounded enumerations;
- sensitivity and retention class;
- expected rate and sampling;
- example records;
- consumers and compatibility policy;
- deprecation and removal path.

Validate schemas in tests and at ingestion. Producers should not silently change `duration_ms` from a number to a string or redefine `outcome=success` to include partial failure.

Consumers must tolerate documented optional additions. For incompatible meaning, publish a new event version and migrate queries before retiring the old one.

## 20. Design for investigation queries

Start from a failure question and ensure fields support it:

> Reconstruct request `req_...`, find its trace, identify the first failed operation, compare it with successful cell-A writes at the same time, and determine whether the same tenant or deployment version is overrepresented.

This needs request and trace IDs, occurrence time, cell, service version, operation, outcome, duration, dependency, error code, and approved tenant reference.

Another query may ask which users invoked emergency administration. That requires subject, tenant, authorization path, reason reference, action, result, and policy version in protected audit records.

Test saved queries against representative events and schema changes. An event that is emitted but cannot be found within the operational window is not useful evidence.

## 21. Instrument the task-update workflow

For one successful update, avoid emitting a line at every function. A trace captures timing; a bounded completion event records business outcome:

```json
{
  "event_name": "task.update.completed",
  "event_version": 2,
  "occurred_at": "2026-11-01T14:02:08.104Z",
  "severity": "info",
  "service": "task-api",
  "service_version": "2026.11.1",
  "environment": "production",
  "cell": "b",
  "request_id": "req_01JBN6...",
  "trace_id": "80f198ee56343ba864fe8b2a57d3eff7",
  "tenant_ref": "tn_8f16...",
  "operation": "task.update",
  "outcome": "success",
  "duration_ms": 84,
  "task_version": 42
}
```

For failure, keep the same envelope and add stable dependency and error classification. The investigation in Chapter 118 can then compare acquisition versus execution spans and filter completion events by cell, version, and outcome.

The audit stream separately records who changed which tenant-owned task under which authorization decision. It does not copy the task title or body.

## 22. Encode and validate an event contract

```python
from dataclasses import dataclass
from datetime import datetime
import json
import re


SAFE_NAME = re.compile(r"^[a-z][a-z0-9_.]{2,79}$")
FORBIDDEN_KEYS = {"password", "access_token", "refresh_token", "secret", "cookie"}


@dataclass(frozen=True)
class Event:
    event_name: str
    event_version: int
    occurred_at: str
    severity: str
    service: str
    operation: str
    outcome: str
    attributes: dict[str, object]
    trace_id: str | None = None
    request_id: str | None = None

    def validate(self) -> None:
        if not SAFE_NAME.fullmatch(self.event_name):
            raise ValueError("event name is not stable or bounded")
        if self.event_version <= 0:
            raise ValueError("event schema version is invalid")
        parsed = datetime.fromisoformat(self.occurred_at.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("event timestamp lacks a timezone")
        if self.severity not in {"debug", "info", "warn", "error", "fatal"}:
            raise ValueError("event severity is invalid")
        if not all((self.service.strip(), self.operation.strip(), self.outcome.strip())):
            raise ValueError("event lacks service, operation, or outcome")
        normalized_keys = {key.lower() for key in self.attributes}
        if normalized_keys & FORBIDDEN_KEYS:
            raise ValueError("event contains a forbidden sensitive field")
        encoded = json.dumps(self.attributes, separators=(",", ":"))
        if len(encoded.encode("utf-8")) > 2048:
            raise ValueError("event attributes exceed the size budget")
        if self.trace_id is not None and len(self.trace_id) != 32:
            raise ValueError("trace identity has an invalid shape")
```

Tests exercise safety and compatibility boundaries:

```python
from dataclasses import replace
import unittest

from event_contract import Event


def valid_event() -> Event:
    return Event(
        event_name="task.update.failed",
        event_version=2,
        occurred_at="2026-11-01T14:07:31.482Z",
        severity="error",
        service="task-api",
        operation="task.update",
        outcome="dependency_timeout",
        attributes={"dependency": "primary_database", "duration_ms": 2004},
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        request_id="req_01JBN7",
    )


class EventContractTests(unittest.TestCase):
    def test_complete_event_is_accepted(self):
        valid_event().validate()

    def test_dynamic_event_name_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "name"):
            replace(valid_event(), event_name="Task 8392 failed!").validate()

    def test_naive_timestamp_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "timezone"):
            replace(valid_event(), occurred_at="2026-11-01T14:07:31").validate()

    def test_unknown_severity_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "severity"):
            replace(valid_event(), severity="urgent").validate()

    def test_secret_field_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "sensitive"):
            replace(valid_event(), attributes={"access_token": "do-not-log"}).validate()

    def test_oversized_attributes_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "size budget"):
            replace(valid_event(), attributes={"safe_detail": "x" * 3000}).validate()

    def test_malformed_trace_identity_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "trace"):
            replace(valid_event(), trace_id="short").validate()

    def test_missing_operation_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "operation"):
            replace(valid_event(), operation="").validate()


if __name__ == "__main__":
    unittest.main()
```

Real systems need recursive sensitivity rules, Unicode-safe limits, schema registries, secure encoders, and integration tests for every sink. The example demonstrates the principle: structure, time, severity, identity, sensitivity, and size are enforceable contracts.

## 23. Test the logging path

Verify more than “a line appeared”:

- required fields, types, versions, and enumerations;
- escaping of newlines, delimiters, control characters, and invalid Unicode;
- exclusion of credentials and representative personal data;
- maximum field and event sizes;
- correlation through HTTP, queue, retry, and scheduled work;
- exactly where one failure is classified and logged;
- sampler behavior for success, error, slow, and security events;
- collector outage, backpressure, full disk, and rejected schema;
- dropped-event counters and fallback behavior;
- access control, retention, deletion, and tamper signals;
- saved queries against old and new event versions;
- performance overhead under peak volume.

Include logging in security, fuzz, load, and recovery tests. It is executable production code with confidentiality, integrity, availability, and cost consequences.

## 24. Review structured logging

Before approving instrumentation, ask:

### Event meaning

- Which investigation, operation, or security question does the event answer?
- Is its name stable and its schema versioned?
- Are severity, operation, outcome, and error classifications consistent?
- Is the event emitted once at the boundary that understands it?

### Context and correlation

- Can one journey cross requests, services, queues, retries, and repair tools?
- Are request, trace, message, idempotency, resource, and tenant identities distinct?
- Are occurrence time, observation time, duration, version, and deployment context available?

### Safety and lifecycle

- Are fields allow-listed, typed, bounded, escaped, and tested against secrets?
- Are high-cardinality fields indexed and retained deliberately?
- Is sampling visible, and are rare failures plus baseline successes preserved?
- Do access, integrity, retention, deletion, and debug-level policies match sensitivity?
- What happens when the logging pipeline is slow, full, unavailable, or rejects the event?

## Common Misconceptions

- **“More logs make a system more observable.”** Unbounded low-value events make useful evidence harder and more expensive to find.
- **“JSON means logs are structured.”** Stable names, types, semantics, sensitivity, and compatibility create structure.
- **“A correlation ID connects everything.”** Different identities represent request, trace, message, idempotency, tenant, and resource semantics.
- **“Debug logging can include anything temporarily.”** Temporary sensitive data can be copied, indexed, backed up, and retained.
- **“Errors should be logged at every catch.”** Duplicate records distort counts and obscure the ownership boundary.
- **“Sampling only saves money.”** It changes which questions the evidence can answer and what absence means.
- **“Application logs are audit logs.”** Audit evidence needs defined completeness, integrity, access, and retention properties.

## Core Computer Science Concept

This chapter applies **event schemas, typed records, causal identity, clocks, bounded queues, sampling, cardinality, information lifecycle, and integrity controls**. Logging is a lossy evidence pipeline whose contracts determine what future questions remain answerable.

## Engineering Connections

- Timestamps, streams, and process context extend Chapters 42, 46, 53, and 113.
- Configuration, secrets, and existing logging practice build on Chapters 72 and 104.
- Security, privacy, and audit boundaries apply Chapter 115.
- Chapters 118 and 119 define the questions and failure signatures the events must support.
- Chapters 121 and 122 will connect events to metrics, objectives, traces, and profiles.

## From the Field

A service emits every request body at debug level during a production investigation. The extra I/O worsens latency, logs expose customer task content, and the relevant timeout event is sampled among terabytes of noise. A targeted schema containing route, trace, tenant reference, dependency phase, duration, outcome, and version would have answered the question with less risk and cost.

## Engineering Review

### What problem does this solve?

It creates bounded, searchable evidence that reconstructs behavior across components without treating logs as an uncontrolled copy of application state.

### Why was it designed this way?

Stable typed schemas support automation and correlation, while allow lists, size limits, sampling, and retention bound confidentiality, availability, and cost risk.

### When should I use it?

Use structured events at workflow, failure, security, configuration, and lifecycle boundaries where future investigation needs occurrence-specific context.

### When should I avoid it?

Do not emit a log for every internal step when a trace, metric, debugger, or test provides the evidence more efficiently.

### How does this make me a better engineer?

You learn to design evidence from future questions, distinguish identity semantics, and consider telemetry as production data with security and lifecycle obligations.

### How does this reduce waste?

It reduces duplicate errors, unqueryable prose, excessive ingestion, leaked data, manual correlation, and emergency redeployment merely to add one missing field.

## Handbook Principle #120

> Emit a bounded typed event for a defined question: preserve time, causal and deployment context, classify the outcome once, exclude sensitive content by design, and make loss, sampling, retention, and schema change visible.

## Practical Observation

Take one common error query and list the fields it extracts from message text. Promote stable concepts into typed schema fields, define their sensitivity and cardinality, then test that one failed request can be reconstructed without reading a body or secret.

## Looking Ahead

Chapter 121 converts user journeys into metrics, service-level indicators, objectives, error budgets, and alerts that demand action rather than merely report activity.

## References

- [OpenTelemetry — Logs Data Model](https://opentelemetry.io/docs/specs/otel/logs/data-model/)
- [OpenTelemetry — Semantic conventions for events](https://opentelemetry.io/docs/specs/semconv/general/events/)
- [W3C — Trace Context](https://www.w3.org/TR/trace-context/)
- [OWASP — Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)
- [RFC 3339 — Date and Time on the Internet: Timestamps](https://www.rfc-editor.org/rfc/rfc3339.html)
- [Chapter 115 — Security, Privacy, and Multi-Tenant Boundaries](../system-design/115-security-privacy-and-multi-tenant-boundaries.md)
- [Chapter 119 — Reproducing Failures and Building Minimal Cases](119-reproducing-failures-and-building-minimal-cases.md)
