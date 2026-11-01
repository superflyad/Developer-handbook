# Chapter 107 — Interfaces, Contracts, and Evolution

Two programs can exchange valid JSON and still disagree about whether an omitted field means false, unknown, unchanged, or invalid. A producer can add an optional enum value without breaking the wire format while crashing every consumer that assumes the old set is exhaustive. An API can return success before its effect is durable, leaving callers unable to retry safely after a timeout.

Syntax is only one layer of an interface.

The central idea is:

> A stable interface defines meaning, authority, state transitions, failure, time, repetition, and evolution—not merely fields and endpoints—and it changes safely only when real consumers prove they can coexist.

## 1. A boundary creates a contract

An interface is any boundary across which independently changing parties communicate. It may be:

- a public or internal request API;
- a queue message or event stream;
- a command-line interface and exit status;
- a library API;
- a file or object format;
- a database view or change feed;
- a callback, webhook, or plugin protocol;
- a configuration or secret schema.

The contract includes more than a schema:

- operation meaning and ownership;
- identity, authentication, and authorization context;
- preconditions, postconditions, and invariants;
- field semantics, units, defaults, and limits;
- error categories and retry behavior;
- timeout, deadline, cancellation, and partial completion;
- idempotency scope and lifetime;
- ordering, duplication, replay, and consistency;
- compatibility, versioning, deprecation, and support;
- privacy, retention, observability, and cost constraints.

If any of these behaviors matter but remain implicit, each consumer invents its own interpretation. That hidden contract eventually becomes harder to change than an explicit one.

## 2. Name provider and consumer ownership

The **provider** implements or publishes an interface. A **consumer** relies on it. For events, the producer publishes facts and multiple consumers interpret them; the producer may not know every downstream reader. For shared files or databases, ownership can be less visible but still exists.

Record:

- business owner and technical owner;
- authoritative specification and schema location;
- supported environments and versions;
- known consumers and their owners;
- on-call and incident path;
- availability and latency objectives;
- change-review and retirement process;
- data classification and access boundary.

Do not confuse network reachability with permission to depend. A team querying another service's private database has created an interface without giving the provider a way to evolve it. A topic that anyone can subscribe to becomes a long-lived product whether or not the publisher intended it.

Consumers own correct use: bounded retries, deadlines, tolerant parsing where promised, version upgrades, and deprecation response. Providers own truthful behavior, compatibility within the supported contract, discoverable changes, and evidence before retirement.

## 3. Separate syntax, structure, and semantics

Compatibility has layers:

1. **transport compatibility** — peers can connect and frame messages;
2. **wire compatibility** — old and new parsers can decode the representation;
3. **schema compatibility** — required fields and types remain acceptable;
4. **behavioral compatibility** — the same input produces behavior consumers can still use;
5. **business compatibility** — workflows and outcomes remain valid;
6. **operational compatibility** — latency, load, quotas, security, and observability remain supportable.

Adding a response field may be wire-compatible. It is behaviorally breaking if a strict JSON consumer rejects unknown fields. Adding an enum value may parse correctly but break exhaustive application logic. Changing a default page size may preserve the schema while making an old client silently process only part of the collection. Tightening a rate limit can preserve every payload and still break a batch workflow.

Review every change at all relevant layers. A schema checker can prove only the rules it encodes.

## 4. Choose command, query, and event semantics deliberately

A **command** asks an owner to attempt a state change. It may be rejected by authorization, precondition, validation, or current state. A **query** asks for a representation without intending a business mutation. An **event** reports a fact the producer considers to have happened.

Examples:

```text
command: AssignTask(task_id, assignee_id, expected_version)
query:   GetTask(task_id, read_consistency)
event:   TaskAssigned(task_id, assignee_id, task_version, occurred_at)
```

Do not disguise commands as past-tense events. `SendWelcomeEmailRequested` delegates work; it is not proof that an email was sent. Do not let a query trigger hidden durable effects that make caching, retries, or access review unsafe.

Name operations from business intent rather than storage mechanics. `AssignTask` preserves an authorization and invariant boundary; `PatchRow` exports the provider's storage model and makes consumers reconstruct business rules.

## 5. Specify preconditions, postconditions, and invariants

A contract should state what must be true before an operation, what becomes true after acceptance, and what always remains true.

For task assignment:

```text
preconditions:
- caller may edit the project
- task exists and is open
- assignee is an active member of the same tenant
- expected_version equals the current version

postconditions on success:
- assignee is changed exactly once for this command identity
- task version increases by one
- audit record identifies actor, old value, new value, and version
- a TaskAssigned event is eventually publishable from durable state

invariants:
- task and assignee never cross tenant boundaries
- a version never decreases or represents two committed states
```

Define what “success” acknowledges. Does it mean validation passed, work was queued, state committed, replicas observed it, or downstream effects completed? A `202 Accepted` response should identify how progress and terminal failure can be observed. A synchronous success should not imply email or analytics completion unless the contract actually includes them.

## 6. Define resource identity and lifecycle

Stable identifiers should not encode mutable names, database locations, or authorization assumptions. Record format, scope, case sensitivity, uniqueness, opacity, lifetime, and reuse policy.

For each resource, define lifecycle states and legal operations. Deletion may mean immediate removal, tombstoning, scheduled erasure, revocation of access, or transition to an archive. Clients need to know whether identifiers can later refer to a different object.

Use client-selected identifiers only when the collision, authorization, and enumeration consequences are understood. If a create operation returns a server-generated identity, a retry needs a separate idempotency identity or lookup path.

Never authorize solely from an identifier's shape. A tenant-prefixed ID can aid routing, but the provider must still validate the authenticated principal's relationship to the resource.

## 7. Make fields complete domain statements

For every field, document:

- meaning and authoritative source;
- type, encoding, and maximum size;
- required, optional, output-only, immutable, or deprecated behavior;
- absence versus explicit null versus default;
- units, precision, range, and time basis;
- normalization and case rules;
- sensitivity and redaction;
- validation and unknown-value behavior;
- compatibility expectations.

A timestamp needs a time scale and semantic event: `occurred_at` is different from `recorded_at`. A duration needs units. Money needs currency and rounding. A name needs Unicode and comparison rules. A Boolean often hides more than two states; `is_complete=false` cannot distinguish open, canceled, unknown, and unavailable.

Do not silently discard misspelled input fields when that can turn intended behavior into a default. Conversely, rejecting every unknown response field prevents additive evolution. Input and output tolerance may intentionally differ.

## 8. Bound messages and collections

Every interface needs limits before traffic finds them:

- request, response, and event byte size;
- string and binary-field length;
- list length and nesting depth;
- batch item count and total work;
- attachment type and decompressed size;
- concurrent streams or subscriptions;
- timeout and maximum processing duration;
- rate and quota scope.

Reject oversize input before expensive parsing or downstream fan-out where possible. A compressed payload needs an expanded-size bound. One batch request must not bypass per-item authorization, validation, idempotency, or quota accounting.

Publish limits as contract values and return a machine-readable error. Changing a limit downward can be breaking even when few consumers currently approach it.

## 9. Design errors for decisions

An error contract lets a consumer decide whether to correct input, refresh state, authenticate again, retry later, reconcile an unknown outcome, or stop.

A structured error can include:

- stable machine-readable code;
- human-safe message;
- correlation or operation identity;
- field-level violations where appropriate;
- current version for conflicts without leaking forbidden data;
- retry hint and server throttling guidance;
- documentation reference.

Distinguish at least invalid input, unauthenticated identity, unauthorized action, missing or concealed resource, state conflict, quota or rate limit, dependency unavailable, internal failure, and unknown operation outcome.

Do not make consumers parse prose. Do not expose stack traces, credentials, policy internals, or tenant existence. Preserve the semantic category through gateways; turning every provider failure into a generic `500` destroys retry and support behavior.

## 10. Timeouts create ambiguous outcomes

A client timeout proves only that the client stopped waiting. The provider may have rejected, committed, or still be executing the operation. Retrying a mutation can duplicate its effect.

Define:

- client and provider time budgets;
- propagated deadline rather than independent full timeouts;
- cancellation semantics and whether work may continue;
- how to query operation status;
- idempotency and reconciliation after uncertainty;
- maximum server retention of operation results.

Cancellation is not rollback. Once a durable effect or external side effect occurs, cancellation may only stop remaining work. The response must not claim atomic cancellation across systems that cannot provide it.

For long operations, return a stable operation resource with state, progress where meaningful, terminal result, error, and expiration. Polling and callbacks must share the same authoritative operation identity.

## 11. Define idempotency as stored behavior

An idempotent business operation produces the same accepted effect when repeated within a defined scope. HTTP method labels or queue deduplication alone do not provide the complete business guarantee.

A mutating contract should define:

- who creates the idempotency key;
- principal, tenant, operation, and resource scope;
- payload fingerprint and canonicalization;
- atomic claim with the business effect;
- result returned for a matching repeat;
- conflict behavior for the same key with different input;
- retention window and maximum replay age;
- behavior after expiration;
- downstream side-effect identity.

If a caller can retry for seven days but the provider retains idempotency results for one hour, the operation is idempotent for one hour. Say so.

Read operations may be safe to repeat but still consume cost, observe different state, or trigger audit and rate accounting. “Idempotent” does not mean free or temporally identical.

## 12. Specify pagination, filtering, and ordering

Collections change while clients traverse them. Define:

- stable ordering and tie-breaker;
- opaque cursor or page-token semantics;
- snapshot, monotonic, or best-effort consistency;
- maximum and default page size;
- filter and sort grammar;
- token scope, expiration, and tamper protection;
- duplicate or missing-item behavior under concurrent change.

Offset pagination can skip or duplicate items when earlier records change and can become expensive at deep offsets. Cursor pagination can preserve a position but does not automatically create a snapshot. If consumers require a complete point-in-time export, provide that contract explicitly.

Never let clients construct meaning from an opaque token. A provider must be able to change its token encoding without breaking consumers. Bind tokens to the query, principal, tenant, and supported lifetime.

Adding pagination later can break older clients that assumed one response contained all items. Google AIP compatibility guidance highlights this exact default-behavior problem. Plan bounded collections from the beginning.

## 13. Give events an owned envelope

An event should identify what happened, to which entity, under which schema and producer, and with enough causal context for supported consumers.

```text
event_id: globally unique publication identity
event_type: task.assigned
schema: task.assigned/v1
producer: task-service
subject: task/01J...
tenant_id: tenant/01H...
occurred_at: business transition time
recorded_at: producer persistence time
correlation_id: originating journey
causation_id: command or prior event
partition_key: task identity
data: versioned business payload
```

Keep transport metadata distinct from business payload. Document which identity supports deduplication, which establishes ordering, and which traces causation. Do not use event publication time as the business occurrence time unless they are guaranteed to coincide.

Events are durable integration products. Owners must classify their data, control subscriptions, define retention and replay, publish schemas, and support consumers through change.

## 14. State delivery, ordering, and replay honestly

At-least-once delivery means consumers can receive duplicates. Ordering is normally scoped to a partition, entity, or session—not the universe. Redelivery can make an older event arrive after a newer observation. Replay can occur long after ordinary retry windows.

Define:

- delivery and acknowledgment semantics;
- partition and ordering key;
- producer sequence or entity version where needed;
- duplicate identity and retention;
- maximum event age and normal retention;
- late and out-of-order policy;
- poison-message and dead-letter ownership;
- replay authorization, rate, and side-effect suppression;
- recovery when a consumer falls beyond retention.

A consumer must distinguish rebuilding a projection from repeating an external side effect. An analytics event can often replay freely; a shipment request cannot.

Exactly-once marketing language should be translated into concrete boundaries: exactly one log offset transaction, one database uniqueness claim, or one business effect under a retained key. No label removes failures across unrelated systems.

## 15. Define compatibility direction

“Backward compatible” is ambiguous unless it names old and new readers and writers. Evaluate at least:

```text
old consumer <- new provider
new consumer <- old provider
old reader   <- new message
new reader   <- old message
old binary   <-> new stored data
```

Rolling deployments commonly require both old and new instances to read and write during overlap. Queues, archives, offline clients, caches, and restored backups extend the overlap far beyond the deployment window.

Protocol Buffers illustrates why representation rules matter: adding a field is binary wire-safe, changing a field number is unsafe, and removed field numbers should be reserved rather than reused. Yet a wire-safe change can still break generated application code or business behavior. ProtoJSON has different compatibility rules from the binary format.

Publish a compatibility policy per representation and transport. Test the actual languages, generated bindings, gateways, and storage paths in use.

## 16. Additive is not automatically safe

Adding an optional field is usually safer than renaming one, but ask:

- Does absence preserve the old behavior?
- Will strict consumers reject it?
- Will generated equality, signing, or caching change?
- Does an old intermediary drop unknown fields?
- Does the field expose sensitive data to existing readers?
- Does it increase payload size beyond a limit?
- Does a new enum value break exhaustive switching?
- Does its presence change authorization or interpretation of old fields?

Response enums are especially risky because a producer can add a value before every consumer handles `unknown`. Define an explicit unknown strategy and test it.

Never reuse a removed field identifier for a new meaning. Historical messages, stored objects, delayed clients, and backup restoration can revive the old interpretation.

## 17. Version only when compatibility cannot carry the change

Versioning creates parallel contracts and migration work; it does not solve evolution by itself. Prefer compatible additions and staged migrations within a version when semantics remain coherent.

A new major version may be justified when changing core meaning, identifiers, required behavior, security model, error semantics, or representation in a way old consumers cannot safely accept.

Define what is versioned:

- complete API surface;
- individual resource or method;
- event type and schema;
- media type;
- SDK or library;
- stored document.

Do not put a `version` integer in every payload without defining its authority, supported values, negotiation, and failure behavior. Do not negotiate a version that the server cannot support consistently across downstream calls.

Each supported version needs security fixes, monitoring, documentation, tests, capacity, and an owner. Unbounded version support is an operational leak.

## 18. Design for deployment skew

Distributed change is a period, not an instant. During rollout, old and new producers, consumers, data, caches, and jobs coexist. A rollback reintroduces the old version after new writes may exist.

Use expand-and-contract:

1. add new representation or behavior without removing old;
2. deploy readers that accept both;
3. begin dual production or translation where necessary;
4. migrate stored state with checkpoints and reconciliation;
5. switch consumers using measured capability;
6. stop old production;
7. wait through the retry, replay, cache, backup, and rollback windows;
8. remove old behavior in a separately reviewed change.

Dual writes can diverge. Prefer one authoritative write with transactional capture or an owned reconciliation process. If translation is lossy, record the loss and do not pretend versions are equivalent.

## 19. Deprecation is a measured migration

Deprecation says a contract remains available but should no longer be chosen. Sunset says when it is expected to stop being available. They are not the same event.

A deprecation plan needs:

- replacement contract and migration guide;
- affected consumer inventory and owners;
- announcement and support dates;
- runtime signals where the protocol supports them;
- usage telemetry by authenticated consumer and version;
- test environment and compatibility tooling;
- escalation for unknown or inactive consumers;
- security exception process;
- objective retirement criteria;
- post-removal monitoring and rollback decision.

RFC 9745 defines an HTTP `Deprecation` response header, while RFC 8594 defines `Sunset` for expected unavailability. Headers can assist discoverability but do not replace direct ownership and telemetry.

Do not remove an interface because documentation traffic looks zero. Measure actual requests, event subscriptions, offline clients, batch schedules, and emergency procedures. A quarterly recovery job can be invisible for months and still critical.

## 20. Make consumer capability observable

A provider needs to know which behavior a consumer actually uses, not only which SDK it downloaded. Track authenticated client identity, contract version, operation, field or feature use where privacy permits, error category, and last-seen time.

For events, maintain an owned subscription registry and consumer lag or checkpoint evidence. For libraries and file formats, runtime telemetry may be unavailable, so release policy, dependency inventory, ecosystem scanning, and extended support windows become more important.

Do not require every consumer to send an arbitrary claimed version and trust it. Where negotiation is needed, bind capabilities to tested behavior and fail clearly when no safe intersection exists.

Unknown consumers are risk, not permission to keep every interface forever. Restrict discovery and subscription, establish ownership, and publish a finite support policy from the beginning.

## 21. Test contracts from several directions

Different tests answer different questions:

- **schema validation** checks structure, required values, and constraints;
- **provider tests** verify implementation against its published contract;
- **consumer tests** verify client behavior against representative responses and failures;
- **consumer-driven contracts** capture interactions a consumer depends on and verify them against the provider;
- **compatibility tests** compare old/new readers, writers, and generated clients;
- **conformance suites** verify multiple implementations against shared rules;
- **integration tests** exercise real authentication, transport, and dependencies;
- **production probes** verify deployed behavior and objectives.

Pact describes consumer-driven contracts as executable examples of the interactions consumers use. This can prevent provider changes from violating known expectations, but examples are not a complete schema, security review, performance test, or proof that every consumer is registered.

Include negative behavior: unknown fields and enums, missing optional values, expired tokens, repeated commands, stale versions, timeouts after commit, oversized input, dependency failure, late events, and replay.

## 22. Generated code does not replace design

OpenAPI, Protocol Buffers, JSON Schema, AsyncAPI, and similar descriptions can generate clients, validators, documentation, and compatibility checks. They improve consistency when treated as reviewed source.

They do not automatically define:

- authorization relationships;
- business invariants;
- idempotency storage;
- transaction boundaries;
- timeout aftermath;
- event meaning and replay safety;
- privacy purpose and retention;
- deprecation ownership;
- acceptable performance and availability.

Generated clients also encode tool-version and language behavior. Pin generators, review generated diffs, test supported runtimes, and avoid making consumers depend on unstable generated names or undocumented serialization details.

## 23. Protect the interface as an attack surface

Every operation needs authentication, object- and field-level authorization, input limits, rate policy, tenant context, audit, and safe error behavior. Batch, export, search, and administrative endpoints often expose more than ordinary reads.

Avoid mass-assignment behavior where a decoded object can update fields the caller should not control. Separate input, stored, and output models. Mark sensitive fields and prevent them from entering logs, events, caches, generated examples, or broad schemas.

Signed webhooks need canonical signature input, timestamp or nonce policy, replay window, key rotation, delivery identity, and receiver-side idempotency. A signature proves possession of a key under a scheme; it does not make payload content authorized for every action.

Contract changes can be security changes. Adding a field to an existing response grants it to all current readers unless field-level policy prevents that.

## 24. Keep interfaces small and cohesive

An interface should group operations with compatible ownership, data, lifecycle, and objectives. A universal API shared by unrelated domains couples release, authorization, scaling, and deprecation. Excessively tiny interfaces create call chains and distributed failure without creating meaningful autonomy.

Expose the smallest stable business contract, not every internal table or class. Keep implementation fields private until a real consumer requirement exists. Each published field becomes something someone can depend on.

Document consistency across operations. If `AssignTask` succeeds but `GetTask` can briefly return the old version, state the read behavior and offer a version or session mechanism if the journey requires read-your-write.

## 25. Evolve the task-assignment contract

Suppose `AssignTask` initially assigns one person:

```text
request: task_id, assignee_id, expected_version, idempotency_key
response: task_id, assignee_id, task_version, committed_at
```

The product later needs multiple responsible people. Renaming `assignee_id` to `assignee_ids` and immediately emitting arrays breaks old consumers and stored events. Keeping both fields indefinitely without precedence rules creates ambiguity.

A staged migration can:

1. define the new collection, bounds, ordering, uniqueness, and authorization;
2. teach readers that legacy `assignee_id` represents a singleton collection;
3. add a new operation or version when multi-assignment changes core semantics;
4. deploy providers that produce both forms only where the mapping is lossless;
5. publish new events with a distinct schema and translation policy;
6. migrate consumers using telemetry and contract tests;
7. stop legacy writes, wait through replay and rollback windows, then retire reads;
8. preserve removed wire identifiers and historical decoding.

If order, individual roles, or per-assignee status matter, a plain list may already be the wrong domain model. Interface evolution should revisit meaning, not merely change cardinality.

## 26. Encode an evolution review

This standard-library model checks a proposed interface change against a declared compatibility and retirement contract. Real schema tools must supply the structural comparison.

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class InterfaceContract:
    owner: str
    consumers_known: bool
    preconditions_defined: bool
    postconditions_defined: bool
    errors_machine_readable: bool
    idempotency_window_hours: int
    maximum_retry_age_hours: int
    unknown_fields_supported: bool
    unknown_enum_supported: bool

    def validate(self) -> None:
        if not self.owner.strip() or not self.consumers_known:
            raise ValueError("interface needs an owner and known consumers")
        if not self.preconditions_defined or not self.postconditions_defined:
            raise ValueError("state transition contract is incomplete")
        if not self.errors_machine_readable:
            raise ValueError("errors must support machine decisions")
        if self.idempotency_window_hours < self.maximum_retry_age_hours:
            raise ValueError("idempotency window is shorter than retry age")


@dataclass(frozen=True)
class EvolutionPlan:
    additive_wire_change: bool
    preserves_old_default_behavior: bool
    adds_response_enum_value: bool
    field_identifier_reused: bool
    old_reader_tested: bool
    new_reader_tested: bool
    deployed_consumers_tested: bool
    usage_telemetry_reviewed: bool
    migration_documented: bool
    rollback_window_covered: bool

    def validate(self, contract: InterfaceContract) -> None:
        contract.validate()
        if self.field_identifier_reused:
            raise ValueError("removed field identifiers must not be reused")
        if self.additive_wire_change and not self.preserves_old_default_behavior:
            raise ValueError("additive change alters old default behavior")
        if self.adds_response_enum_value and not contract.unknown_enum_supported:
            raise ValueError("consumers do not safely handle unknown enum values")
        if self.additive_wire_change and not contract.unknown_fields_supported:
            raise ValueError("consumers reject unknown fields")
        if not self.old_reader_tested or not self.new_reader_tested:
            raise ValueError("both compatibility directions require tests")
        if not self.deployed_consumers_tested:
            raise ValueError("schema compatibility is not consumer compatibility")
        if not self.usage_telemetry_reviewed or not self.migration_documented:
            raise ValueError("migration needs telemetry and documentation")
        if not self.rollback_window_covered:
            raise ValueError("migration does not cover deployment skew")
```

Executable tests exercise the review boundary:

```python
import unittest

from interface_contract import EvolutionPlan, InterfaceContract


def valid_contract() -> InterfaceContract:
    return InterfaceContract("task team", True, True, True, True, 168, 72, True, True)


def valid_plan() -> EvolutionPlan:
    return EvolutionPlan(True, True, False, False, True, True, True, True, True, True)


class EvolutionPlanTests(unittest.TestCase):
    def test_compatible_plan_is_accepted(self) -> None:
        valid_plan().validate(valid_contract())

    def test_short_idempotency_window_is_rejected(self) -> None:
        contract = valid_contract()
        fields = {**contract.__dict__, "idempotency_window_hours": 24}
        with self.assertRaisesRegex(ValueError, "shorter"):
            valid_plan().validate(InterfaceContract(**fields))

    def test_reused_field_identifier_is_rejected(self) -> None:
        plan = valid_plan()
        fields = {**plan.__dict__, "field_identifier_reused": True}
        with self.assertRaisesRegex(ValueError, "must not be reused"):
            EvolutionPlan(**fields).validate(valid_contract())

    def test_changed_default_is_rejected(self) -> None:
        plan = valid_plan()
        fields = {**plan.__dict__, "preserves_old_default_behavior": False}
        with self.assertRaisesRegex(ValueError, "default behavior"):
            EvolutionPlan(**fields).validate(valid_contract())

    def test_unknown_response_enum_is_rejected(self) -> None:
        contract = valid_contract()
        plan_fields = {**valid_plan().__dict__, "adds_response_enum_value": True}
        contract_fields = {**contract.__dict__, "unknown_enum_supported": False}
        with self.assertRaisesRegex(ValueError, "unknown enum"):
            EvolutionPlan(**plan_fields).validate(InterfaceContract(**contract_fields))

    def test_schema_only_evidence_is_rejected(self) -> None:
        plan = valid_plan()
        fields = {**plan.__dict__, "deployed_consumers_tested": False}
        with self.assertRaisesRegex(ValueError, "consumer compatibility"):
            EvolutionPlan(**fields).validate(valid_contract())

    def test_missing_old_reader_test_is_rejected(self) -> None:
        plan = valid_plan()
        fields = {**plan.__dict__, "old_reader_tested": False}
        with self.assertRaisesRegex(ValueError, "both compatibility directions"):
            EvolutionPlan(**fields).validate(valid_contract())

    def test_unmeasured_migration_is_rejected(self) -> None:
        plan = valid_plan()
        fields = {**plan.__dict__, "usage_telemetry_reviewed": False}
        with self.assertRaisesRegex(ValueError, "telemetry"):
            EvolutionPlan(**fields).validate(valid_contract())


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

Save the blocks as `interface_contract.py` and `test_interface_contract.py`, then run:

```bash
python -m unittest -v test_interface_contract.py
```

A production checker should parse the authoritative API or event schemas, compare compatibility in the declared direction, compile supported generated clients, run provider and consumer contracts, inspect deployment and subscription inventory, verify idempotency and retry windows, and confirm deprecation telemetry. It must not infer behavioral safety from schema compatibility alone.

## 27. Review an interface and its change

```text
provider, business owner, technical owner, consumers, and support path:
command, query, event, or representation semantics and authority:
principal, tenant, resource, authorization, and audit context:
preconditions, postconditions, invariants, commit, and acknowledgment point:
identities, lifecycle, reuse, opacity, and deletion behavior:
fields, absence, null, defaults, units, limits, and sensitivity:
unknown fields, enums, invalid input, normalization, and strictness:
error codes, safe messages, conflicts, retry hints, and correlation:
deadlines, cancellation, unknown outcomes, status, and reconciliation:
idempotency key, scope, fingerprint, atomicity, result, and retention:
pagination, ordering, snapshot, filters, tokens, and concurrent change:
event envelope, occurrence, recording, causation, partition, and version:
delivery, duplicates, ordering scope, late events, retention, and replay:
wire, schema, behavioral, business, operational compatibility directions:
old/new readers, writers, clients, stored data, rollback, and backup windows:
version scope, negotiation, support, security fixes, and ownership:
deprecation, replacement, telemetry, consumers, dates, and retirement proof:
schema, provider, consumer, compatibility, integration, and production tests:
privacy, rate, payload, export, webhook, and field-level access controls:
```

## Common Misconceptions

- “The schema is the contract.” Meaning, state, time, failure, and evolution are also contractual.
- “Internal APIs do not need compatibility.” Independent deployments and teams create the same skew as external clients.
- “Adding an optional field cannot break anyone.” Defaults, strict readers, payload size, privacy, and behavior can break.
- “A wire-safe enum addition is safe.” Exhaustive consumer logic may fail on the new value.
- “A timeout means the operation failed.” Its outcome is unknown unless the contract provides idempotency or status.
- “POST is not idempotent.” Business idempotency can be implemented for any mutating transport operation.
- “Versioning lets us break consumers.” It creates another interface that still needs migration and support.
- “Dual write guarantees migration.” Two writes can diverge without an atomic source or reconciliation.
- “Nobody uses the old endpoint.” Usage requires authenticated telemetry across batch, recovery, and offline windows.
- “Contract tests replace integration tests.” They prove different boundaries and both can miss production behavior.

## Core Computer Science Concept

This chapter applies **design by contract, state machines, partial failure, algebraic idempotence, serialization compatibility, monotonic evolution, and observational equivalence**. Two implementations are compatible only to the extent that supported observers cannot distinguish a harmful change under the declared contract. Syntax narrows the possible messages; semantics determines their effects.

## Engineering Connections

- Boundary syntax extends Chapters 8, 9, 60, 67, and 70's framing and protocol models.
- Preconditions and invariants build on Chapters 15, 41, 74, and 106.
- Idempotency and replay extend Chapters 74, 76, and 101.
- Deployment skew applies Chapters 77, 88, 103, and 105's rollout model.
- Consumer telemetry uses Chapter 104's evidence and privacy discipline.
- Stable contracts become inputs to Chapter 108's data model and Chapter 112's messaging design.

## From the Field

A list endpoint originally returns every project. The provider adds optional `page_size` and `page_token` fields, defaulting to 100 to protect itself. The schema checker calls this additive. Old clients ignore the new response token, process the first 100 projects, and report successful incomplete exports. Had the original contract bounded collections—or the change preserved old default behavior and measured consumer pagination capability—the provider could have avoided a silent business break.

## Engineering Review

### What problem does this solve?

It lets independently deployed components and teams share business behavior while changing without coordinated rewrites or silent reinterpretation.

### Why was it designed this way?

Most interface incidents occur outside field syntax: ambiguous acknowledgment, unsafe retry, hidden defaults, unknown consumer assumptions, deployment overlap, or premature retirement. The model makes those boundaries explicit and testable.

### When should I use it?

Use it for every interface that crosses an independent deployment, ownership, trust, data-lifecycle, or recovery boundary. Scale the documentation to consequence.

### When should I avoid it?

Do not publish an interface merely to decouple code inside one cohesive process. Ordinary language-level modules may provide a simpler boundary until independent ownership or deployment is real.

### How does this make me a better engineer?

It teaches you to distinguish parseability from meaning, reason through ambiguous outcomes, predict compatibility in both directions, and migrate from observed consumer behavior.

### How does this reduce waste?

It reduces accidental public surfaces, duplicate effects, client-specific workarounds, permanent versions, synchronized releases, failed replays, unknown consumers, and compatibility ceremonies that test only schemas.

## Handbook Principle #107

> An interface is stable when its meaning under success, failure, repetition, and change is explicit—and its evolution is proven against deployed consumers, not assumed from syntax.

## Practical Observation

Choose one mutating API or event. Ask what happens when the response is lost after commit, the same input arrives twice, an old consumer sees a new enum, a replay occurs after idempotency expires, and the provider wants to remove a field. If the answers live only in implementation folklore, the interface is not yet a contract.

## Looking Ahead

Interfaces define the operations and observations a system must support. Chapter 108 maps those access patterns, invariants, consistency needs, and lifecycles to data models and storage engines without treating any one database as universal.

## References

- [Google AIP-180 — Backwards compatibility](https://google.aip.dev/180)
- [Google AIP-203 — Field behavior documentation](https://google.aip.dev/203)
- [Protocol Buffers — Proto3 language guide and message evolution](https://protobuf.dev/programming-guides/proto3/)
- [Protocol Buffers — Proto best practices](https://protobuf.dev/best-practices/dos-donts/)
- [RFC 9745 — The Deprecation HTTP Response Header Field](https://www.rfc-editor.org/rfc/rfc9745.html)
- [RFC 8594 — The Sunset HTTP Header Field](https://www.rfc-editor.org/rfc/rfc8594.html)
- [Pact — Consumer-driven contract testing](https://docs.pact.io/)
- [Chapter 74 — Idempotency, State, Retries, and Recovery](../automation/74-idempotency-state-retries-and-recovery.md)
- [Chapter 101 — SQS, SNS, EventBridge, and Asynchronous Workflows](../aws/101-sqs-sns-eventbridge-and-asynchronous-workflows.md)
- [Chapter 106 — From Requirements to a System Model](106-from-requirements-to-a-system-model.md)
