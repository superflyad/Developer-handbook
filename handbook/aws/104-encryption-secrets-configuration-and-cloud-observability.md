# Chapter 104 — Encryption, Secrets, Configuration, and Cloud Observability

An application can encrypt every disk and still leak a credential into a log. It can retain years of audit events and still page nobody when production fails. It can rotate a secret on schedule and still keep using the old value from a cache until every request is denied.

The central idea is:

> Treat keys, secrets, configuration, telemetry, and audit evidence as separate lifecycles joined by explicit identity, retention, rotation, and response contracts.

## 1. Separate five control planes

These concerns interact but are not interchangeable:

- **KMS keys** protect cryptographic key material and authorize cryptographic operations.
- **Secrets** contain confidential credentials or tokens that applications retrieve and rotate.
- **Configuration** changes non-secret application behavior and needs validation and rollout.
- **Observability** explains workload health through metrics, logs, and traces.
- **Audit and configuration evidence** records control-plane activity and resource state through CloudTrail and AWS Config.

For each one, record:

- authoritative service and Region;
- data class and owner;
- reader, writer, administrator, and recovery identities;
- encryption and transport protections;
- version, rotation, rollout, and rollback;
- cache lifetime and stale behavior;
- retention, deletion, legal hold, and cost;
- alarm, runbook, responder, and test;
- cross-account collection and failure behavior.

Encryption answers who can perform a cryptographic operation. It does not answer who can reach the plaintext before encryption, query a log, change a resource, or ignore an alarm.

## 2. Choose a KMS key type for control, not ceremony

AWS services can encrypt with:

- an **AWS owned key**, invisible and fully managed by the service;
- an **AWS managed key**, visible in the account but with lifecycle and policy managed by the service;
- a **customer managed KMS key**, whose policy, lifecycle, aliases, rotation, and deletion the customer controls.

Use service-default encryption when it satisfies the threat, audit, sharing, and recovery requirements. Choose a customer managed key when you need your own key policy, cross-account authorization, cryptographic audit, separation by data class, explicit disable or deletion control, or service-supported encryption-context constraints.

More keys do not automatically mean more security. A key per object produces policy, quota, cost, recovery, and inventory overhead. A single key for every workload creates excessive blast radius. Group keys by compatible administrators, users, data class, Region, lifecycle, and recovery boundary.

Key aliases are mutable names, not cryptographic identity. Record key ARN or ID in evidence and understand what an alias change will affect.

## 3. Envelope encryption separates data from root keys

KMS is designed to protect keys, not to accept every large application payload directly. Envelope encryption works as follows:

1. generate a plaintext data encryption key and an encrypted copy under a KMS key;
2. encrypt the application data locally with the plaintext data key;
3. erase the plaintext data key from memory as soon as practical;
4. store the ciphertext and encrypted data key together;
5. later ask KMS to decrypt the encrypted data key and use the plaintext result locally.

```text
KMS key -> protects encrypted data key
data key -> encrypts application data
```

This limits KMS payload and request volume while centralizing control of key encryption keys. AWS service integrations often perform envelope encryption internally. Use the AWS Encryption SDK or a reviewed construction rather than inventing a ciphertext format, nonce scheme, or key cache.

KMS availability, request quota, network path, and permissions become decrypt dependencies. Cache only according to the library and threat model; never persist plaintext data keys casually.

## 4. Key policy is the primary authorization boundary

Every KMS key has one key policy. IAM permissions alone do not grant use unless the key policy enables the account or principal path. Grants provide delegated, often service-integrated use and can include constraints.

Separate:

- **key administrators**, who manage policy, aliases, rotation, and deletion;
- **key users**, who encrypt, decrypt, re-encrypt, or generate data keys;
- **service principals**, constrained to the intended resource and service path;
- **auditors**, who inspect metadata and CloudTrail without decrypt authority.

Avoid granting key administrators routine decrypt access. Constrain service use with `kms:ViaService`, source conditions, encryption context, and grant constraints where the integration supports them. Test the key policy from both an allowed and denied role before production.

Back up policy source in reviewed infrastructure code. A malformed policy can lock out administrators or expose every ciphertext protected by the key.

## 5. Encryption context authenticates non-secret context

For symmetric KMS encryption operations, encryption context is a set of non-secret key-value pairs cryptographically bound as additional authenticated data. Decryption must provide the same context. Policies and grants can require context values.

Useful values can identify an application, tenant, purpose, or resource without revealing sensitive content:

```text
Application = billing
Purpose = invoice-archive
TenantClass = enterprise
```

Encryption context appears in plaintext in CloudTrail. Never place personal data, secrets, full document names, or tokens in it. Use stable canonical encoding and store enough metadata beside the ciphertext to reconstruct the exact context.

Context can prevent ciphertext from one purpose being decrypted under another. It does not validate the business truth of a client-supplied tenant ID unless the trusted application constructs and authorizes it.

## 6. Rotation does not re-encrypt old data

Automatic or on-demand KMS key-material rotation creates new material for future encryption while preserving prior material for decryption. Existing ciphertext does not need rewriting and is not re-encrypted merely because rotation occurred.

Manual key rotation creates a new KMS key and changes aliases or application configuration. It can support a new policy or boundary but requires a migration and old-key retention plan. Do not disable or schedule deletion of the old key until every dependent ciphertext, backup, snapshot, log, secret, and disaster-recovery copy has been inventoried and tested.

Key deletion is intentionally delayed but can make data permanently unrecoverable. Require narrow permission, independent approval, CloudTrail monitoring, and an alarm for disable or scheduled deletion. Test restores with the actual key and policy in the target account and Region.

Multi-Region keys are related keys with synchronized material, not global endpoints or automatic data replication. Each Region still needs policy, service configuration, monitoring, and recovery validation.

## 7. Encryption is not authorization or deletion

Server-side encryption protects stored bytes from certain storage-layer threats. A principal allowed to call the service and decrypt through it can still retrieve plaintext. TLS protects traffic in transit but not a compromised endpoint. Client-side encryption can narrow who sees plaintext but adds key distribution, search, rotation, and recovery complexity.

For every encrypted resource, trace:

```text
caller -> service authorization -> KMS authorization -> plaintext path
```

Also trace logs, caches, exports, replicas, backups, DLQs, snapshots, and temporary files. Encrypting the primary database while exporting plaintext CSV files to a broad bucket does not protect the dataset.

Crypto-shredding by deleting a key is safe only when that key protects exactly the intended data and every ciphertext copy is known. Retention and deletion remain data-lifecycle problems.

## 8. Secrets Manager owns credential lifecycle

Secrets Manager stores secret versions encrypted through KMS and provides runtime retrieval, access control, replication options, version staging, audit events, and automatic rotation for supported designs. Use it for database credentials, API keys, OAuth material, and other confidential values whose lifecycle matters.

Applications should retrieve a secret with workload identity, cache it in memory for a bounded time, and never log it. Infrastructure definitions should reference the secret, not contain its value. A secret ARN is normally configuration; the value is sensitive.

Scope both `secretsmanager:GetSecretValue` and any required `kms:Decrypt`. A broad KMS grant does not grant Secrets Manager access by itself, and secret access without the customer key may still fail.

Name and tag secrets without embedding confidential data. Separate secrets by access and rotation boundary; a single JSON object containing ten unrelated credentials forces every consumer and rotation to share privileges.

## 9. Rotation is a distributed compatibility change

Rotation must update both the secret store and the target system. A custom Secrets Manager rotation function follows create, set, test, and finish stages using version labels such as `AWSPENDING`, `AWSCURRENT`, and `AWSPREVIOUS`.

A complete rotation contract defines:

- rotation frequency and owner;
- target system and privileged rotation identity;
- idempotent retry for every stage;
- overlap during which old and new credentials work;
- application cache TTL and refresh trigger;
- behavior for existing connections;
- rollback or recovery using the prior version;
- alarms for missed, failed, or stale rotation;
- a production-like rotation test.

Single-user database rotation briefly changes one user's password. Alternating-user rotation can preserve availability but adds a second principal whose permissions must stay synchronized. Prefer temporary role credentials or identity federation over rotating static secrets when possible.

A secret changed every four hours but cached for a day is not a four-hour credential at the application boundary.

## 10. Cache secrets with a stale-failure policy

Fetching a secret on every request adds latency, cost, quota pressure, and dependence on the Secrets Manager path. Cache in memory through a supported library, extension, or workload provider. Bound TTL below the planned overlap and revocation objective.

When authentication fails after rotation:

1. invalidate the cached version;
2. fetch `AWSCURRENT` once;
3. retry the operation only when safe;
4. surface a bounded failure rather than loop;
5. alarm if refresh continues failing.

Decide whether an application may use a cached secret during a Secrets Manager outage and for how long. Availability and emergency revocation pull in opposite directions. Document the chosen risk.

Do not write cached secrets to disk, core dumps, traces, exception messages, or debug endpoints. Redaction after ingestion is a second line of defense, not permission to log plaintext.

## 11. Parameter Store is primarily configuration storage

Systems Manager Parameter Store provides hierarchical `String`, `StringList`, and KMS-protected `SecureString` values with versions and labels. It fits centrally referenced configuration such as an approved AMI ID, endpoint, or feature threshold.

AWS recommends Secrets Manager for credentials needing automatic rotation, cross-account access, fine-grained secret audit, or cross-Region replication. `SecureString` encrypts the value, but names and metadata remain visible.

Parameter hierarchy affects authorization. `GetParametersByPath` permission on an ancestor can return descendants even when another statement appears to deny a narrower path for other actions. Design environment and application hierarchies around security boundaries, test effective access, and do not assume path resemblance creates isolation.

Pin a version or label when reproducibility matters. Reading “latest” at each startup can deploy a configuration change without a workload release or rollout record.

## 12. AppConfig makes dynamic configuration a deployment

AWS AppConfig can source hosted configuration, feature flags, Parameter Store, Secrets Manager, or S3. It adds validators, gradual deployment strategies, bake time, CloudWatch alarm monitoring, and automatic rollback.

Use it when configuration must change independently of code but still needs release discipline. Define:

- schema and semantic validators;
- target environments or entities;
- growth pattern and deployment duration;
- bake time and health alarms;
- retrieval cache and last-known-good behavior;
- owner, expiry, and cleanup for feature flags;
- rollback and audit evidence.

A feature flag is production code with multiple paths. Test both states, include it in observability, and remove it after rollout. Long-lived flags create an unbounded configuration state space.

Do not use dynamic configuration to bypass code review or make a breaking data-model change instantaneously.

## 13. Metrics, logs, and traces answer different questions

- **Metrics** aggregate numeric behavior over time and support inexpensive alerting.
- **Logs** record discrete structured events and diagnostic context.
- **Traces** connect causal work across process and service boundaries.

One signal cannot replace the others. A trace sample may miss a rare failure; logs may be too expensive to scan for every alert; a metric can show latency without explaining which dependency caused it.

Start with user or business outcomes, then platform saturation. Use RED for request paths—rate, errors, duration—and queue age or completion for asynchronous work. Use resource metrics to explain a symptom, not as the only definition of health.

Standardize service name, environment, Region, version or image digest, operation, outcome, correlation ID, trace context, and safe tenant class across telemetry.

## 14. Metric dimensions must be bounded

CloudWatch metrics are identified by namespace, name, and dimension set. Every unique dimension combination creates a time series and cost. Never use request ID, user ID, raw URL, message ID, or unbounded customer value as a metric dimension.

Prefer bounded dimensions:

```text
Service = checkout
Operation = create-order
Outcome = success | invalid | dependency_error
Environment = production
```

Put high-cardinality identifiers in structured logs and traces. Keep a documented cardinality budget and reject dynamic metric names.

Choose statistic and period deliberately. Averages hide tail latency and burst errors; use percentiles, rates, sums, or maxima according to meaning. CloudWatch aggregates older high-resolution data over time, so retain separate evidence if an investigation requires original granularity.

## 15. Logs need schema, redaction, and retention

Log structured events rather than prose fragments:

```json
{
  "timestamp": "2026-11-01T15:04:05Z",
  "level": "ERROR",
  "service": "checkout",
  "operation": "authorize_payment",
  "outcome": "dependency_timeout",
  "correlation_id": "request-7f2c",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736"
}
```

Redact before emission. Do not log passwords, secret values, access tokens, cookies, authorization headers, full payment data, or unnecessary personal data. CloudWatch Logs data-protection policies can audit and mask recognized patterns, but privileged users with unmask authority may still access underlying values and custom formats may evade detection.

Create log groups through infrastructure code with explicit retention, KMS choice, deletion protection where required, access controls, subscription or centralization, tags, and cost alarms. CloudWatch Logs otherwise stores log data indefinitely by default.

Retention follows investigation, security, legal, and privacy needs—not “forever just in case.” Test that deletion, export, and legal-hold procedures match the policy.

## 16. Instrument new traces with OpenTelemetry

Propagate W3C trace context through HTTP and message metadata. Create spans around meaningful boundaries, record bounded attributes and status, and link asynchronous consumers to producer context when parent-child timing no longer fits.

AWS has placed the X-Ray SDKs and daemon into maintenance mode as of February 25, 2026, with end of support scheduled for February 25, 2027. New instrumentation should use OpenTelemetry and a supported collector or CloudWatch agent path, exporting to CloudWatch/X-Ray or another approved backend. Plan migration for existing X-Ray SDK users before the support deadline.

Sampling controls cost but can hide rare errors. Use head or tail sampling policies that preserve failures and high-latency traces where possible. Never attach secret values or raw sensitive payloads as span attributes.

Trace context is untrusted input at an external boundary. Validate format, start or restart traces according to policy, and prevent arbitrary client baggage from becoming metric dimensions or log fields.

## 17. Correlation must survive asynchronous boundaries

Carry separate identifiers:

- trace ID for one sampled technical path;
- correlation ID for a business journey across time and replays;
- event ID for one domain occurrence;
- causation ID for the input that produced an event;
- AWS request IDs for provider support and API evidence.

Preserve the original event identity through retries and use a new delivery-attempt identity where needed. A replay may create a new trace but should retain the event and replay batch identity.

Do not use one global “transaction ID” without semantics. Operators need to know whether two entries represent the same effect, the same customer journey, or merely the same delivery attempt.

Synchronize clocks through supported platform mechanisms and emit UTC timestamps. Distributed timestamps help order evidence but do not establish one absolute event order across services.

## 18. Alerts must map symptoms to action

An alarm needs:

- user or business symptom;
- metric expression, period, evaluation count, and threshold;
- missing-data treatment;
- owner and severity;
- notification and escalation path;
- dashboard and runbook;
- expected action and safe automation;
- test and review date.

CloudWatch alarms change among `OK`, `ALARM`, and `INSUFFICIENT_DATA`. Missing telemetry can mean an idle resource, a broken emitter, or a failed collection path. Choose behavior per metric rather than treating all missing data as good.

Use composite alarms to reduce noise when several signals must agree. Page for urgent, actionable user impact; create tickets for capacity trends or hygiene. Alert on telemetry-pipeline and alarm-action failures too—CloudWatch does not validate that every configured action will succeed.

Relate alarms to service-level objectives where possible. CPU at 80 percent is not an incident when latency and errors remain healthy; one percent failed payments may be urgent at low CPU.

## 19. CloudTrail records AWS activity, not application logs

CloudTrail captures management, data, network activity, and Insights event categories according to configuration. The automatically available Event history provides 90 days of management events per account and Region. It is useful for recent investigation but is not an organization-wide long-term audit design.

Create an organization multi-Region trail or CloudTrail Lake event data store according to audit and query requirements. Trails deliver selected events to S3 and can integrate with CloudWatch Logs and EventBridge. Protect the destination in a dedicated log archive account with narrow write and read policy, encryption, versioning or immutability where required, and log-file validation.

CloudTrail records who called an AWS API, from what context, against which resource, and with what result when supported. It does not record arbitrary application business events unless the application emits them through an appropriate mechanism.

CloudTrail files are not a totally ordered stack trace. Correlate request IDs, event times, source identity, and resource history.

## 20. Select high-volume CloudTrail events deliberately

Management events cover control-plane operations and are commonly enabled by default in trails. Data events cover high-volume resource operations such as selected S3 object or Lambda invocation activity and require explicit selectors. Network activity events and Insights serve different investigation needs.

Enable data events from threat and audit questions, not indiscriminately:

```text
Which protected bucket object reads must be attributable?
Which production functions require invocation audit?
Which DynamoDB tables contain regulated records?
```

Use advanced selectors to bound resources and operations, estimate event volume and storage, and verify representative events arrive. Excluding noisy reads can save cost but may remove the evidence needed for exfiltration investigation.

Monitor trail health, delivery errors, unauthorized configuration change, and deletion attempts. Retaining a trail configuration while its destination rejects writes provides false assurance.

## 21. AWS Config records resource state and evaluates rules

AWS Config discovers supported resources in configured scope, records configuration items and relationships, builds history, and evaluates managed or custom rules. It answers questions such as “When did this security group change?” and “Which recorded buckets are currently noncompliant?”

AWS Config is detective by default. A rule marks a resource compliant or noncompliant after change or on a schedule; it does not prevent the change. Prevention belongs in IAM, service control policies, resource control policies, admission controls, or deployment policy. Remediation is a separate automated action whose safety and permissions need review.

Configure every intended account and Region, recorder scope, recording frequency, delivery channel, aggregator, retention, and alerts. Coverage differs by resource type and Region, and best-effort recording can lag. Verify coverage instead of assuming “Config is enabled” means every resource is recorded.

Organization aggregation centralizes view; it does not retroactively create history for an account or resource that was not recorded.

## 22. Join evidence without collapsing its meaning

An investigation often combines:

- CloudTrail: who changed an IAM policy;
- AWS Config: before and after resource state;
- deployment record: which reviewed artifact initiated the change;
- workload logs: what the application observed;
- metrics: when user impact began;
- traces: which dependency path slowed;
- KMS and secret audit: which protected material was accessed;
- business ledger: which outcomes actually occurred.

Centralize enough metadata to correlate account, Region, resource ARN, workload version, principal, request ID, trace ID, and time. Preserve source records and provenance; a derived dashboard is not the audit source.

Separate telemetry writers from readers and administrators. A compromised workload should not be able to rewrite or delete the evidence used to investigate it. Use a log archive account, narrow destination policies, and retention controls matched to the threat model.

## 23. Control telemetry cost without blinding operations

Telemetry cost comes from ingestion, indexed fields, metric time series, trace sampling, storage, cross-Region transfer, queries, exports, and duplicate pipelines.

Reduce waste safely:

- reject unbounded metric dimensions;
- use log levels and sampling without dropping errors;
- aggregate repetitive success events into metrics;
- retain hot searchable logs briefly and archive evidence when appropriate;
- filter at collectors after preserving required security events;
- avoid sending identical data through several unowned tools;
- measure bytes and cost per service and outcome;
- attach an owner and expiry to temporary debug logging.

Never solve an unexplained bill by disabling the only audit trail or shortening retention below investigation needs. First identify the producing field, service, account, and query pattern.

## 24. Test observability and recovery as features

Run controlled tests for:

- denied decrypt and disabled KMS key;
- scheduled key deletion alarm and cancellation procedure;
- secret rotation with old connections and stale cache;
- unavailable secret or KMS endpoint;
- invalid dynamic configuration and alarm-triggered rollback;
- sensitive token deliberately blocked before log emission;
- missing metric and `INSUFFICIENT_DATA` behavior;
- alarm notification and escalation delivery;
- trace propagation through HTTP, queue, retry, and replay;
- CloudTrail data-event selector and archive delivery;
- unauthorized trail or recorder change;
- AWS Config noncompliance, lag, and safe remediation;
- cross-account collector or KMS policy failure.

Use synthetic secrets and disposable resources. Do not place real credentials in a test event to prove redaction.

## 25. Build an evidence contract checker

The following standard-library model rejects common lifecycle and evidence gaps:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class ProtectionContract:
    customer_managed_key: bool
    key_policy_reviewed: bool
    admin_separate_from_users: bool
    deletion_alarm: bool
    secret_is_runtime_reference: bool
    rotation_tested: bool
    secret_cache_hours: int
    credential_overlap_hours: int


@dataclass(frozen=True)
class EvidenceContract:
    log_retention_days: int
    redaction_at_source: bool
    bounded_metric_dimensions: bool
    alarm_owner: str
    alarm_runbook: bool
    cloudtrail_ongoing_store: bool
    cloudtrail_scope_tested: bool
    config_recorder_verified: bool
    trace_instrumentation: str


@dataclass(frozen=True)
class OperationsContract:
    protection: ProtectionContract
    evidence: EvidenceContract

    def validate(self) -> None:
        protection = self.protection
        evidence = self.evidence
        if protection.customer_managed_key:
            if not protection.key_policy_reviewed:
                raise ValueError("customer managed key policy requires review")
            if not protection.admin_separate_from_users:
                raise ValueError("key administrators must be separate from key users")
            if not protection.deletion_alarm:
                raise ValueError("customer managed key requires deletion monitoring")
        if not protection.secret_is_runtime_reference:
            raise ValueError("secret values cannot be embedded in artifacts")
        if not protection.rotation_tested:
            raise ValueError("secret rotation requires a tested target workflow")
        if protection.secret_cache_hours >= protection.credential_overlap_hours:
            raise ValueError("secret cache must expire inside credential overlap")
        if evidence.log_retention_days <= 0 or not evidence.redaction_at_source:
            raise ValueError("logs require retention and source redaction")
        if not evidence.bounded_metric_dimensions:
            raise ValueError("metric dimensions must have bounded cardinality")
        if not evidence.alarm_owner.strip() or not evidence.alarm_runbook:
            raise ValueError("alarms require an owner and runbook")
        if not evidence.cloudtrail_ongoing_store or not evidence.cloudtrail_scope_tested:
            raise ValueError("CloudTrail requires ongoing storage and scope testing")
        if not evidence.config_recorder_verified:
            raise ValueError("AWS Config recorder coverage must be verified")
        if evidence.trace_instrumentation != "opentelemetry":
            raise ValueError("new tracing must use supported OpenTelemetry instrumentation")
```

Tests make the expected controls executable:

```python
import unittest

from evidence_contract import EvidenceContract, OperationsContract, ProtectionContract


def valid_contract() -> OperationsContract:
    protection = ProtectionContract(True, True, True, True, True, True, 1, 4)
    evidence = EvidenceContract(
        90, True, True, "operations", True, True, True, True, "opentelemetry"
    )
    return OperationsContract(protection, evidence)


class OperationsContractTests(unittest.TestCase):
    def test_complete_contract_is_accepted(self) -> None:
        valid_contract().validate()

    def test_unreviewed_key_policy_is_rejected(self) -> None:
        contract = valid_contract()
        fields = {**contract.protection.__dict__, "key_policy_reviewed": False}
        with self.assertRaisesRegex(ValueError, "policy requires review"):
            OperationsContract(ProtectionContract(**fields), contract.evidence).validate()

    def test_secret_embedded_in_artifact_is_rejected(self) -> None:
        contract = valid_contract()
        fields = {**contract.protection.__dict__, "secret_is_runtime_reference": False}
        with self.assertRaisesRegex(ValueError, "embedded in artifacts"):
            OperationsContract(ProtectionContract(**fields), contract.evidence).validate()

    def test_stale_secret_cache_is_rejected(self) -> None:
        contract = valid_contract()
        fields = {**contract.protection.__dict__, "secret_cache_hours": 4}
        with self.assertRaisesRegex(ValueError, "inside credential overlap"):
            OperationsContract(ProtectionContract(**fields), contract.evidence).validate()

    def test_unbounded_metric_dimensions_are_rejected(self) -> None:
        contract = valid_contract()
        fields = {**contract.evidence.__dict__, "bounded_metric_dimensions": False}
        with self.assertRaisesRegex(ValueError, "bounded cardinality"):
            OperationsContract(contract.protection, EvidenceContract(**fields)).validate()

    def test_event_history_alone_is_rejected(self) -> None:
        contract = valid_contract()
        fields = {**contract.evidence.__dict__, "cloudtrail_ongoing_store": False}
        with self.assertRaisesRegex(ValueError, "ongoing storage"):
            OperationsContract(contract.protection, EvidenceContract(**fields)).validate()

    def test_new_xray_sdk_instrumentation_is_rejected(self) -> None:
        contract = valid_contract()
        fields = {**contract.evidence.__dict__, "trace_instrumentation": "xray-sdk"}
        with self.assertRaisesRegex(ValueError, "OpenTelemetry"):
            OperationsContract(contract.protection, EvidenceContract(**fields)).validate()


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

Save the blocks as `evidence_contract.py` and `test_evidence_contract.py`, then run:

```bash
python -m unittest -v test_evidence_contract.py
```

A production checker should inspect authorized read-only inventory for key policies, rotation and deletion state; secret versions and rotation; parameter metadata; AppConfig validators and deployments; log retention and data protection; metrics and alarms; trace collectors; CloudTrail trails or stores and selectors; Config recorders, channels, aggregators and rules; central destinations; and tags. It must not decrypt values, retrieve secret plaintext, rotate credentials, change configuration, set alarm state, or modify evidence systems during validation.

## 26. Review protection and observability

```text
data classes, owners, plaintext paths, Regions, retention, and recovery:
AWS owned, managed, or customer managed keys and why:
key administrators, users, policy, grants, context, quotas, and audit:
rotation method, old ciphertext, disable/delete controls, and restore test:
secret boundaries, readers, KMS, versions, target, schedule, and overlap:
cache TTL, refresh on denial, outage behavior, redaction, and rotation test:
Parameter Store paths, versions, labels, hierarchy access, and consumers:
AppConfig validation, gradual strategy, alarms, bake time, and rollback:
metric names, bounded dimensions, units, statistics, periods, and retention:
log schema, source redaction, masking, readers, retention, and deletion:
OpenTelemetry propagation, sampling, attributes, collector, and backend:
correlation, event/causation identity, request IDs, clocks, and replay:
alarm symptom, threshold, missing data, owner, runbook, action, and test:
CloudTrail organization scope, event selectors, destination, and validation:
AWS Config accounts/Regions/types, recorder, rules, aggregator, and lag:
archive isolation, evidence access, pipeline failures, cost, and review date:
```

## Common Misconceptions

- “Encrypted means authorized.” A permitted service caller may still receive plaintext.
- “Customer managed keys are always more secure.” They add control and also policy, recovery, cost, and deletion responsibility.
- “KMS rotation re-encrypts everything.” It changes material for future encryption while retaining prior decrypt capability.
- “Encryption context can contain private metadata.” It is logged in plaintext in CloudTrail.
- “Moving a secret into an environment variable solves secret management.” It can still leak and does not define refresh or rotation.
- “Rotation is done when the secret value changes.” Applications, caches, connections, and target credentials must remain compatible.
- “More logs mean more observability.” Unstructured, sensitive, or unowned logs add cost and risk without answers.
- “CloudWatch alarms always fire if their action is broken.” Alarm actions and notification paths require independent tests.
- “CloudTrail event history is our audit archive.” It is a 90-day, per-Region management-event view.
- “AWS Config prevents noncompliant changes.” It records and evaluates; prevention and remediation are separate controls.

## Core Computer Science Concept

This chapter applies **envelope encryption, capability-based authorization, versioned configuration, time-series aggregation, causal tracing, and append-oriented evidence**. Each mechanism preserves a different property: secrecy, permitted use, controlled change, measurable behavior, causal explanation, or historical accountability.

## Engineering Connections

- Key and secret identities extend Chapter 92's principal and policy evaluation.
- Rotation is a compatible distributed rollout like Chapters 77 and 103.
- Bounded metric dimensions apply Chapter 76's cardinality and capacity thinking.
- Trace propagation follows Chapter 101's correlation across asynchronous delivery.
- CloudTrail and Config complement Chapter 91's organization governance.
- Evidence retention follows Chapters 97 through 100's backup and lifecycle principles.

## From the Field

A database password rotates successfully at midnight. Application tasks cache it for 12 hours, while the database invalidates the old password after 15 minutes. New tasks work; warm tasks fail every query and retry aggressively. A cache TTL inside the credential overlap, refresh-on-authentication-failure, bounded retries, rotation canary, and alarm on authentication denial would make rotation an ordinary deployment instead of an outage.

## Engineering Review

### What problem does this solve?

It connects cryptographic control, secret and configuration change, workload telemetry, and AWS audit evidence into one reviewable operational lifecycle.

### Why was it designed this way?

These systems fail at their boundaries: decrypt policy versus service policy, secret version versus application cache, dynamic configuration versus health, and telemetry collection versus response. Explicit contracts make those boundaries testable.

### When should I use it?

Use this model for every production AWS workload that stores protected data, retrieves credentials, changes runtime behavior, emits telemetry, or requires operational and security evidence.

### When should I avoid it?

Avoid adding a customer managed key, secret store, dynamic flag platform, or telemetry pipeline without a concrete control need and owner. Service defaults can be safer than unmaintained custom control planes.

### How does this make me a better engineer?

It teaches you to separate encryption from authorization, treat rotation as compatibility work, design observability from questions, and preserve evidence outside the workload's blast radius.

### How does this reduce waste?

It reduces needless keys, secret API calls, stale-credential outages, permanent flags, high-cardinality metrics, sensitive logs, noisy alarms, duplicate telemetry, indiscriminate data events, and evidence retained without a question.

## Handbook Principle #104

> Protection and observability are reliable only when their keys, values, signals, evidence, and responders each have an owned lifecycle.

## Practical Observation

Choose one production credential and one critical alarm. For the credential, trace creation, encryption, readers, cache, rotation, overlap, rollback, and audit. For the alarm, trace signal emission, aggregation, missing data, state change, notification, responder, runbook, and verification. If either trace ends with “the service handles it,” the operational contract is incomplete.

## Looking Ahead

The AWS chapters now have governance, identity, network, compute, storage, data, messaging, runtime, and evidence primitives. Chapter 105 integrates them through reviewed infrastructure code and a complete delivery lifecycle with plans, policy, drift, deployment, recovery, cost, and teardown.

## References

- [AWS KMS — Key types and concepts](https://docs.aws.amazon.com/kms/latest/developerguide/concepts.html)
- [AWS KMS — Cryptography and envelope encryption](https://docs.aws.amazon.com/kms/latest/developerguide/kms-cryptography.html)
- [AWS KMS — Key policies](https://docs.aws.amazon.com/kms/latest/developerguide/key-policies.html)
- [AWS KMS — Encryption context](https://docs.aws.amazon.com/kms/latest/developerguide/encrypt_context.html)
- [AWS KMS — Key rotation](https://docs.aws.amazon.com/kms/latest/developerguide/rotate-keys.html)
- [AWS Secrets Manager — What is Secrets Manager?](https://docs.aws.amazon.com/secretsmanager/latest/userguide/)
- [AWS Secrets Manager — Rotation](https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotating-secrets.html)
- [AWS Secrets Manager — Rotation functions](https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotate-secrets_lambda-functions.html)
- [AWS Secrets Manager — Best practices and caching](https://docs.aws.amazon.com/secretsmanager/latest/userguide/best-practices.html)
- [Systems Manager — Parameter Store reference](https://docs.aws.amazon.com/systems-manager/latest/userguide/what-is-a-parameter.html)
- [AWS AppConfig — What is AppConfig?](https://docs.aws.amazon.com/appconfig/latest/userguide/)
- [AWS AppConfig — Deployment strategies](https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-creating-deployment-strategy.html)
- [Amazon CloudWatch — Metrics concepts](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_concepts.html)
- [Amazon CloudWatch Logs — Log groups and retention](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/Working-with-log-groups-and-streams.html)
- [Amazon CloudWatch Logs — Sensitive-data protection](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/mask-sensitive-data.html)
- [Amazon CloudWatch — Alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Alarms.html)
- [AWS X-Ray — Migrating instrumentation to OpenTelemetry](https://docs.aws.amazon.com/xray/latest/devguide/xray-sdk-migration.html)
- [AWS CloudTrail — Concepts](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-concepts.html)
- [AWS CloudTrail — Event history](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/view-cloudtrail-events.html)
- [AWS Config — How AWS Config works](https://docs.aws.amazon.com/config/latest/developerguide/how-does-config-work.html)
- [Chapter 103 — ECS, EKS, ECR, and Container Platforms on AWS](103-ecs-eks-ecr-and-container-platforms-on-aws.md)
