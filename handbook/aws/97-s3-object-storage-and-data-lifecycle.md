# Chapter 97 — S3 Object Storage and Data Lifecycle

A bucket can hold billions of durable objects, yet a careless design can still lose the only useful version, expose private data, retain abandoned multipart parts forever, or emit the same business event twice. S3 removes disk administration; it does not remove the need to define data identity and lifecycle.

The central idea is:

> Treat every object as an immutable value identified by bucket, key, and version, then design authorization, recovery, retention, replication, events, and cost around that identity.

## 1. Object storage is not a remote filesystem

Amazon Simple Storage Service stores objects through an API. A general purpose bucket is a Regional resource; an object contains bytes plus system and user metadata and is addressed by a key. Applications use operations such as `PutObject`, `GetObject`, `HeadObject`, `ListObjectsV2`, `CopyObject`, and `DeleteObject` rather than filesystem syscalls.

Important differences from a mounted filesystem include:

- keys are identifiers, not inode-backed paths;
- a slash in a key has no inherent directory semantics;
- there is no atomic rename operation for an ordinary object;
- listing a prefix is not opening a directory;
- one object update is atomic, but a group of key updates is not a transaction;
- object metadata is part of the stored object contract;
- permissions can depend on principal, bucket, key, tags, network path, and encryption request;
- storage class and lifecycle affect retrieval time and cost;
- event notifications are asynchronous delivery, not a transaction callback.

S3 can be a source of truth, artifact store, backup target, static-content origin, exchange boundary, or data-lake substrate. Name which role a bucket and prefix serve before configuring them.

## 2. Bucket, key, and version form the object identity

Without versioning, an object is commonly described by:

```text
s3://example-records/tenant-42/2026/11/01/report.json
```

The bucket is `example-records`; everything after it is one key. With versioning enabled, the durable identity also includes a version ID:

```text
(bucket, key, version-id)
```

The unversioned URI means “the current version at this key,” which can change. A version-qualified reference means one particular stored value. Record the version ID when provenance, rollback, or reproducibility matters.

Bucket names, Regions, account ownership, and partition are infrastructure decisions. Keys are application data. Do not encode a credential or regulated secret in either: names can appear in logs, events, inventory, URLs, bills, and support evidence.

## 3. Key design is a data-model decision

Prefixes and delimiters let clients organize and list keys hierarchically, but they do not create real directories. Design a key scheme for its readers, lifecycle rules, authorization boundaries, event filters, and operational tools.

A useful scheme often includes stable fields such as:

```text
orders/tenant=42/year=2026/month=11/day=01/order-7f8c.json
```

Evaluate:

- uniqueness and collision handling;
- immutable identifiers versus mutable “latest” pointers;
- tenant isolation;
- prefix-scoped access;
- expected list queries;
- lifecycle and replication filters;
- event prefix and suffix filters;
- characters, Unicode normalization, and URL encoding;
- human debugging without personal data leakage;
- distribution across request patterns.

Do not infer business truth solely from a listing convention. Store a manifest, database record, or immutable event when a set of objects must form one published release.

## 4. S3 is strongly consistent, but not multi-object transactional

S3 provides strong read-after-write consistency for object `PUT` and `DELETE` operations in all Regions. After a successful write, subsequent reads and listings observe it. Updating one key is atomic: a concurrent reader gets the old value or the new value, not partial bytes.

Strong consistency does not make this sequence atomic:

```text
PUT data/part-1
PUT data/part-2
PUT manifests/current
```

A reader can observe an intermediate set, and the process can fail between operations. Common publication patterns include:

- write immutable, uniquely named objects, validate them, then publish one manifest pointer;
- write a versioned manifest whose contents identify every exact object version;
- use a database transaction to publish metadata after objects are durable;
- make readers tolerate absent or not-yet-published members;
- reconcile incomplete uploads and abandoned staging prefixes.

Define which successful response constitutes commitment. “All calls usually finish” is not an atomicity model.

## 5. Prevent accidental overwrite with immutable keys or conditions

A `PUT` to an existing key creates a new current value. Versioning preserves the earlier version, but it does not tell the caller that a collision occurred. Prefer unique, content-addressed, event-ID, or release-version keys when values should be immutable.

When a key must be created only if absent, use a supported conditional write such as `If-None-Match: *`. When replacing a value only if it remains the version previously read, use an appropriate `If-Match` condition and compare the current entity tag. Handle precondition failures as concurrency outcomes, not generic network retries.

Do not assume the entity tag is always the MD5 digest of object bytes. Multipart upload and encryption choices can produce other ETag semantics. Use S3's supported checksum features when content integrity requires a portable checksum contract.

## 6. Authorization is evaluated around each request

An S3 request can be affected by:

- the caller's identity policy and permissions boundary;
- session policy and organization service control policy;
- bucket or access-point resource policy;
- VPC endpoint policy;
- explicit denies and condition keys;
- KMS key policy and grants for SSE-KMS data;
- Object Ownership and, in legacy designs, ACLs;
- Block Public Access settings;
- Object Lock for destructive operations.

Separate bucket actions such as listing from object actions such as reading a key. Scope object ARNs to intended prefixes, require TLS with an explicit deny on insecure transport, and constrain cross-account writers deliberately.

Presigned URLs delegate one signed operation until expiration using the signing principal's effective authority. They are bearer capabilities: keep lifetimes short, restrict operation and key, protect them from logs and referrers, and design revocation rather than assuming a URL is merely a private address.

## 7. Prefer bucket-owner-enforced ownership

New general purpose buckets default to **Bucket owner enforced** Object Ownership, which disables ACLs. The bucket owner owns every object and policies control access. This removes a class of cross-account uploads that the paying bucket account cannot fully administer.

Keep ACLs disabled unless a documented compatibility requirement demands per-object ACL behavior. For legacy migration:

1. inventory bucket and object ACL dependencies;
2. reproduce required grants in policies;
3. remove public or cross-account ACL grants;
4. update uploaders that send unsupported ACL headers;
5. enable bucket-owner-enforced ownership;
6. test each producer and consumer.

An ACL migration changes authorization behavior. Treat it as a security release with rollback evidence, not a console cleanup.

## 8. Block Public Access is a guardrail, not the whole policy

S3 Block Public Access can apply at account and bucket scope and prevents policy or ACL configurations considered public. Keep all settings enabled for private data. A request can still be allowed to another AWS account or organization through a nonpublic policy, so “not public” does not mean “least privilege.”

For intentionally public content, prefer a private S3 origin behind CloudFront as described in Chapter 96. If direct public S3 access is truly required:

- isolate it in a dedicated bucket and account boundary;
- classify exactly which keys are public;
- require an explicit review to relax account and bucket guardrails;
- prevent public write and administrative access;
- log, monitor, and periodically prove exposure;
- keep private and public datasets out of the same policy surface.

Never disable public-access controls as a first response to `AccessDenied`. Identify the denied principal, action, resource, condition, network path, ownership setting, and KMS decision.

## 9. Encrypt every transport and stored object deliberately

S3 encrypts new uploads at rest by default with S3-managed encryption keys. A bucket can set default server-side encryption using SSE-S3, SSE-KMS, or supported dual-layer KMS encryption. Default encryption is a baseline; policies can additionally require the intended algorithm and key.

Choose by control requirements:

- **SSE-S3:** S3 manages encryption keys and operation, minimizing customer key administration.
- **SSE-KMS:** KMS supplies key policy, audit, disablement, grants, and customer-managed-key options; callers also need the necessary KMS authority.
- **DSSE-KMS:** two independent KMS-based encryption layers for requirements that call for dual-layer server-side protection.
- **Client-side encryption:** the application encrypts before upload and owns envelope, key, metadata, and recovery design.

S3 Bucket Keys can reduce KMS request traffic and cost for SSE-KMS, with implications for the encryption context and audit pattern. Test cross-account upload, replication, restore, inventory, batch operations, and disaster recovery against key policies.

Require HTTPS with policy conditions. At-rest encryption does not protect plaintext sent over an insecure client connection, and deleting or disabling a KMS key can make otherwise durable objects unreadable.

## 10. Versioning makes current state recoverable

With versioning enabled, each successful overwrite creates a new version. A simple `DELETE` normally inserts a delete marker as the current version instead of permanently erasing prior versions. Removing that marker can reveal the previous version.

Versioning changes operations:

- storage includes current versions, noncurrent versions, and delete markers;
- permanent deletion requires selecting a version ID;
- lifecycle must address current and noncurrent versions separately;
- replication requires versioning at both ends;
- restoration may mean copying a prior version to create a new current version;
- a current-key `404` can mean the latest entry is a delete marker;
- suspending versioning introduces `null`-version behavior rather than returning to a never-versioned bucket.

Enable versioning before data needs recovery. It cannot reconstruct values overwritten or deleted while versioning was absent. Protect permissions that delete versions or change versioning state, and rehearse recovery without erasing forensic evidence.

## 11. Object Lock adds version-level retention

S3 Object Lock provides write-once-read-many protection for versioned objects. A version can have a retention period, a legal hold, or both.

- **Governance mode** blocks deletion or retention changes unless an authorized caller explicitly uses bypass authority.
- **Compliance mode** prevents deletion or shortening by any user, including the account root, until retention expires.
- **Legal hold** has no automatic expiry and remains until an authorized operation removes it.

Object Lock protects a particular version. It does not prevent creating a new version or adding a delete marker above it. Compliance mode is intentionally difficult to reverse; test governance mode, legal obligations, time sources, administrator separation, lifecycle interaction, replication, and account closure implications before setting production retention.

Retention is not backup by itself. A protected corrupt version remains corrupt, and availability still depends on keys, account access, Region strategy, and restore procedures.

## 12. Storage classes encode access and resilience assumptions

Choose storage class from access frequency, retrieval latency, availability needs, resilience scope, object size, retention duration, and request/retrieval cost—not from the storage rate alone.

The main families include:

- S3 Standard for frequently accessed, multi-AZ data;
- S3 Intelligent-Tiering for changing or unknown access patterns, with monitoring and tiering behavior;
- S3 Standard-Infrequent Access for less frequent access requiring rapid retrieval and multi-AZ resilience;
- S3 One Zone-Infrequent Access when recreatable data can accept one-AZ storage scope;
- S3 Glacier Instant Retrieval for archive access requiring millisecond retrieval;
- S3 Glacier Flexible Retrieval for asynchronous archive retrieval;
- S3 Glacier Deep Archive for the lowest-cost, longest-horizon asynchronous access;
- S3 Express One Zone for specialized low-latency access through directory buckets, with different semantics and scope.

Some classes have minimum billable object sizes, minimum storage durations, retrieval charges, and asynchronous restore workflows. Benchmark the complete workload: object count, request rate, bytes, transitions, retrievals, restores, replication, KMS, inventory, and transfer.

## 13. Lifecycle is automated destructive policy

An S3 Lifecycle configuration uses rules, filters, and actions to transition or expire eligible data. Rules can filter by prefix, tag, object size, or combinations supported by the service.

Current-version actions and noncurrent-version actions are different. In a versioned bucket, expiring a current object generally creates a delete marker and leaves the former current value as a noncurrent version. Permanent recovery cost continues until a noncurrent-version expiration rule removes it.

Review each rule as code:

- exact included and excluded prefixes or tags;
- current transition and expiration ages;
- noncurrent transition, retention count, and expiration ages;
- expired delete-marker cleanup;
- incomplete multipart upload abortion;
- minimum storage duration and early-deletion cost;
- replication and Object Lock interactions;
- effect on existing objects, not only future uploads;
- restore time before a downstream retention deadline;
- evidence that a sample object received the intended action.

Lifecycle expiration is not an undoable “move to trash.” If a rule permanently expires the final recoverable version, AWS cannot reconstruct it. Require peer review and simulate the selected inventory before enabling a broad destructive filter.

## 14. Durability, availability, backup, and retention differ

S3 is designed for extremely high object durability, but durability answers a narrow question: will the stored bytes survive infrastructure failures covered by the service design? It does not protect against every operational outcome.

Separate:

- **durability:** probability that stored data is not lost by storage failures;
- **availability:** whether an authorized request can access it now;
- **version recovery:** whether an older value still exists after overwrite or delete;
- **backup:** an independently governed recovery copy with tested restore;
- **retention:** how long deletion is prevented or delayed;
- **replication:** asynchronous copying according to configured rules;
- **archive:** a cost and retrieval-latency choice;
- **business continuity:** applications, identities, keys, metadata, dependencies, and runbooks needed to use recovered data.

A durable encrypted object with a deleted KMS key is not usable. A replicated accidental overwrite may exist twice. A lifecycle rule can faithfully delete every version it selects. Define recovery point and recovery time objectives and test them.

## 15. Replication is asynchronous policy, not magic backup

Same-Region Replication and Cross-Region Replication copy eligible object versions between versioning-enabled buckets. Replication needs an IAM role and permissions; SSE-KMS data needs deliberate key configuration. Filters, ownership, delete-marker behavior, existing-object backfill, replication time controls, and replica modification settings all affect outcomes.

Use replication for requirements such as:

- a second-account trust boundary;
- Regional proximity or recovery;
- compliance copy placement;
- aggregation into a central bucket;
- ownership transition;
- operational separation.

Do not call it backup without testing independence. Ask:

- Does accidental overwrite replicate?
- Do delete markers replicate under this rule?
- Can the source administrator delete destination versions?
- Are destination KMS keys independently governed?
- What happens to objects written before the rule?
- How is failed or pending replication detected and repaired?
- Can the application actually operate from the destination?

Replication status is part of the object lifecycle. Monitor pending bytes, latency, failures, and destination policy drift.

## 16. Multipart upload is a protocol with cleanup state

Multipart upload separates a large object into independently uploaded parts. The client initiates an upload, records its upload ID, uploads numbered parts, records returned ETags and checksums, then completes the upload with the intended part list. S3 assembles the final object in part-number order.

Multipart upload supports parallelism and retrying only failed parts. It also creates intermediate billable state. After initiation, uploaded parts remain until the upload is completed or aborted. Configure `AbortIncompleteMultipartUpload` lifecycle cleanup and monitor aging uploads.

Correct clients must:

- choose bounded part size and concurrency;
- persist upload ID and completed-part evidence when resume is required;
- retry idempotently without confusing concurrent uploads for the same key;
- verify the final checksum and metadata;
- abort abandoned uploads;
- handle completion uncertainty by reading object state before blindly retrying;
- use conditional completion where overwrite prevention is required.

The ETag of a multipart object is not a portable whole-object MD5 checksum. Store and verify an explicit supported checksum when end-to-end integrity matters.

## 17. Metadata and tags serve different control planes

System metadata includes properties such as content length, content type, storage class, encryption, and modification time. User-defined metadata is supplied when the object is created. Replacing user metadata generally requires a copy operation that creates or replaces the object.

Object tags are a separate key-value control surface. They can participate in lifecycle filters, authorization conditions, replication selection, cost allocation, and operations. Tag changes are strongly consistent, but they are not a substitute for a transactional business database.

Classify metadata as carefully as object bytes. Do not put secrets or unnecessary personal data in keys, tags, headers, or metadata. Define canonical content type, content disposition, cache control, checksum, producer, schema version, and provenance fields where consumers depend on them.

## 18. Events require idempotent, order-aware consumers

S3 can send event notifications to supported SNS topics, SQS queues, Lambda functions, and EventBridge. Notifications are designed for at-least-once delivery and are not guaranteed to arrive in event order. Rare duplicates are expected behavior.

An event consumer should:

- identify the bucket, decoded key, version ID, event name, and event ID;
- make processing idempotent;
- tolerate duplicate, delayed, and out-of-order events;
- compare the per-key sequencer where applicable;
- fetch and validate authoritative object state rather than trusting every event field as current;
- handle an object that was deleted or superseded before processing;
- bound retries and use a dead-letter or failure destination;
- prevent writes from recursively triggering an infinite notification loop;
- reconcile from inventory or listing when delivery evidence is incomplete.

Do not use notification arrival as the commit point for the original upload. The successful object operation is one fact; eventual downstream processing is another workflow with its own state machine.

## 19. Static content still needs a publication model

S3 can store static site assets, while CloudFront provides the public HTTPS and cache boundary. Prefer a private bucket origin with Origin Access Control instead of making the bucket public.

Publish immutable, content-versioned assets and a short-lived manifest or HTML entry point. Set correct `Content-Type`, `Cache-Control`, and content encoding metadata at upload time. Validate that:

- the distribution can read only its intended prefix;
- direct-origin access is denied;
- old release assets remain for rollback during their cache lifetime;
- lifecycle does not delete a still-referenced release;
- upload completion precedes manifest publication;
- client and edge cache behavior matches the release contract.

S3 website endpoints are custom HTTP origins with distinct feature and security behavior. Do not assume they are equivalent to private REST endpoints behind OAC.

## 20. Observe inventory, operations, and exposure

No single log is a complete S3 ledger. Combine:

- CloudTrail management events for bucket configuration changes;
- CloudTrail data events where object-level API auditing is required;
- S3 server access logging for best-effort request records and lifecycle evidence;
- S3 Inventory for scheduled object, version, encryption, replication, checksum, and lock metadata reports;
- S3 Storage Lens for organization, account, bucket, prefix, cost, activity, and protection metrics;
- CloudWatch request metrics where enabled;
- EventBridge or notification processing metrics;
- AWS Config and security findings for configuration drift;
- KMS logs and metrics for encrypted access paths;
- billing and cost-allocation data.

Inventory is particularly useful for proving lifecycle scope before a destructive change. Store logs and reports in separately governed destinations so a compromise of the data bucket cannot erase its own evidence.

Alert on changes to public access, bucket policy, ownership, versioning, Object Lock, replication, lifecycle, encryption, and logging. Detect noncurrent-version growth, incomplete multipart bytes, failed replication, unexpected storage classes, and unowned prefixes.

## 21. Model cost across the whole lifecycle

S3 cost is more than current bytes. Include:

- current and noncurrent version storage;
- delete markers and small-object overhead;
- request classes and high-frequency polling;
- lifecycle transition requests;
- minimum storage-duration and minimum-size charges;
- archive retrieval and restore duration;
- multipart parts that were never completed;
- replication requests and destination storage;
- same-Region and cross-Region transfer paths;
- internet egress and CDN origin transfer;
- KMS requests and Bucket Key behavior;
- inventory, analytics, logs, and observability;
- test and abandoned buckets.

Optimize after measuring access and recovery needs. Deleting the only recoverable version or placing frequently read data in an expensive retrieval tier is not cost optimization.

## 22. Copy and delete is not atomic rename

Changing an object's key usually means copying it to a new key and deleting the old one. Between those operations, both keys or only the old key may exist. Large copies can use multipart copy. Metadata, tags, encryption, storage class, ownership, retention, and version identity must be specified or verified.

For migrations:

1. inventory source versions and metadata;
2. define exact destination identity and ownership;
3. copy without deleting source;
4. validate count, size, checksums, metadata, tags, permissions, encryption, and retention;
5. switch readers through a manifest or configuration boundary;
6. observe old and new paths;
7. retain the source through rollback and compliance windows;
8. delete only through reviewed lifecycle or an auditable batch process.

S3 Batch Operations can apply work to large manifests, but scale magnifies mistakes. Test a small representative manifest, use completion reports, and separate selection from execution approval.

## 23. Rehearse object-lifecycle failures

Test at least:

- two writers create the same supposedly immutable key;
- the current version is overwritten with corrupt bytes;
- a simple delete creates a marker and a permanent version delete is attempted;
- a lifecycle filter selects an unexpected existing prefix;
- the KMS key is denied or disabled;
- replication remains pending or fails;
- a notification is duplicated and a newer event arrives first;
- a multipart completion response is lost;
- the origin application sees `AccessDenied` after an ownership migration;
- an archive restore misses the business recovery deadline;
- a public-access setting or bucket policy drifts;
- inventory and access logs are unavailable during investigation.

For each case, record detection, blast radius, recovery version, authority required, maximum restore time, evidence, and cost. Recovery is a tested operation, not the existence of a checkbox.

## 24. Make the lifecycle contract executable

The following standard-library model validates one private production bucket with version recovery, explicit encryption, bounded lifecycle, and safe event consumers. It is deliberately stricter than every possible S3 design.

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DataLifecycle:
    prefix: str
    retention_days: int
    current_transition_days: int | None
    current_expiration_days: int | None
    noncurrent_expiration_days: int
    minimum_recoverable_versions: int
    replication_required: bool

    def validate(self) -> None:
        if not self.prefix or not self.prefix.endswith("/"):
            raise ValueError("lifecycle prefix must be explicit and end with /")
        if self.retention_days < 1:
            raise ValueError(f"{self.prefix}: retention must be positive")
        if self.current_transition_days is not None:
            if self.current_transition_days < 0:
                raise ValueError(f"{self.prefix}: transition age cannot be negative")
            if (
                self.current_expiration_days is not None
                and self.current_transition_days >= self.current_expiration_days
            ):
                raise ValueError(f"{self.prefix}: transition must precede expiration")
        if (
            self.current_expiration_days is not None
            and self.current_expiration_days < self.retention_days
        ):
            raise ValueError(f"{self.prefix}: current expiration violates retention")
        if self.noncurrent_expiration_days < self.retention_days:
            raise ValueError(f"{self.prefix}: noncurrent expiration violates retention")
        if self.minimum_recoverable_versions < 1:
            raise ValueError(f"{self.prefix}: preserve at least one recoverable version")


@dataclass(frozen=True)
class EventConsumer:
    name: str
    idempotent: bool
    handles_out_of_order: bool
    has_failure_destination: bool
    has_reconciliation: bool

    def validate(self) -> None:
        if not self.name:
            raise ValueError("event consumer needs a name")
        if not self.idempotent or not self.handles_out_of_order:
            raise ValueError(f"{self.name}: consumer must handle duplicate and unordered events")
        if not self.has_failure_destination or not self.has_reconciliation:
            raise ValueError(f"{self.name}: consumer needs failure and reconciliation paths")


@dataclass(frozen=True)
class BucketContract:
    region: str
    versioning: str
    object_ownership: str
    block_public_access: tuple[bool, bool, bool, bool]
    default_encryption: str
    tls_only_policy: bool
    kms_recovery_tested: bool
    abort_multipart_after_days: int
    inventory_enabled: bool
    destination_versioning: bool
    lifecycles: tuple[DataLifecycle, ...]
    consumers: tuple[EventConsumer, ...]

    def validate(self) -> None:
        if not self.region:
            raise ValueError("bucket Region must be explicit")
        if self.versioning != "Enabled":
            raise ValueError("production data requires versioning")
        if self.object_ownership != "BucketOwnerEnforced":
            raise ValueError("ACLs must be disabled with bucket-owner enforcement")
        if not all(self.block_public_access):
            raise ValueError("all Block Public Access controls must be enabled")
        if self.default_encryption not in {"SSE-S3", "SSE-KMS", "DSSE-KMS"}:
            raise ValueError("approved default encryption is required")
        if not self.tls_only_policy:
            raise ValueError("bucket policy must deny insecure transport")
        if "KMS" in self.default_encryption and not self.kms_recovery_tested:
            raise ValueError("KMS-encrypted recovery must be tested")
        if not 1 <= self.abort_multipart_after_days <= 14:
            raise ValueError("incomplete multipart cleanup must be bounded")
        if not self.inventory_enabled:
            raise ValueError("object inventory is required")
        if not self.lifecycles:
            raise ValueError("at least one explicit data lifecycle is required")

        prefixes = [item.prefix for item in self.lifecycles]
        if len(prefixes) != len(set(prefixes)):
            raise ValueError("lifecycle prefixes must be unique")
        for lifecycle in self.lifecycles:
            lifecycle.validate()
            if lifecycle.replication_required and not self.destination_versioning:
                raise ValueError(f"{lifecycle.prefix}: replication destination needs versioning")
        for consumer in self.consumers:
            consumer.validate()
```

The tests cover the destructive and asynchronous boundaries:

```python
import unittest

from s3_contract import BucketContract, DataLifecycle, EventConsumer


def valid_contract() -> BucketContract:
    return BucketContract(
        region="us-east-1",
        versioning="Enabled",
        object_ownership="BucketOwnerEnforced",
        block_public_access=(True, True, True, True),
        default_encryption="SSE-KMS",
        tls_only_policy=True,
        kms_recovery_tested=True,
        abort_multipart_after_days=7,
        inventory_enabled=True,
        destination_versioning=True,
        lifecycles=(
            DataLifecycle(
                prefix="records/",
                retention_days=365,
                current_transition_days=30,
                current_expiration_days=2555,
                noncurrent_expiration_days=730,
                minimum_recoverable_versions=2,
                replication_required=True,
            ),
        ),
        consumers=(
            EventConsumer(
                name="record-indexer",
                idempotent=True,
                handles_out_of_order=True,
                has_failure_destination=True,
                has_reconciliation=True,
            ),
        ),
    )


class BucketContractTests(unittest.TestCase):
    def test_complete_contract_is_accepted(self) -> None:
        valid_contract().validate()

    def test_public_access_gap_is_rejected(self) -> None:
        contract = valid_contract()
        broken = BucketContract(**{
            **contract.__dict__,
            "block_public_access": (True, True, False, True),
        })
        with self.assertRaisesRegex(ValueError, "all Block Public Access"):
            broken.validate()

    def test_missing_versioning_is_rejected(self) -> None:
        contract = valid_contract()
        broken = BucketContract(**{**contract.__dict__, "versioning": "Suspended"})
        with self.assertRaisesRegex(ValueError, "requires versioning"):
            broken.validate()

    def test_expiration_before_retention_is_rejected(self) -> None:
        contract = valid_contract()
        lifecycle = DataLifecycle(**{
            **contract.lifecycles[0].__dict__,
            "current_expiration_days": 90,
        })
        broken = BucketContract(**{**contract.__dict__, "lifecycles": (lifecycle,)})
        with self.assertRaisesRegex(ValueError, "violates retention"):
            broken.validate()

    def test_non_idempotent_event_consumer_is_rejected(self) -> None:
        contract = valid_contract()
        consumer = EventConsumer(**{
            **contract.consumers[0].__dict__,
            "idempotent": False,
        })
        broken = BucketContract(**{**contract.__dict__, "consumers": (consumer,)})
        with self.assertRaisesRegex(ValueError, "duplicate and unordered"):
            broken.validate()


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

Save the blocks as `s3_contract.py` and `test_s3_contract.py`, then run:

```bash
python -m unittest -v test_s3_contract.py
```

The values are architectural examples, not universal retention advice. A production verifier should use authorized read-only APIs to inspect bucket Region, ownership controls, public-access blocks, policies, encryption, versioning, Object Lock, lifecycle, replication, notifications, inventory, logging, metrics, and sample object metadata. It must not upload, restore, replicate, retag, or delete objects during validation.

## 25. Review an S3 data lifecycle

```text
dataset, owners, classification, account, Region, and recovery objectives:
bucket purpose, Object Ownership, and administrative boundary:
key schema, version-qualified identity, collision, and publication model:
producers, consumers, actions, prefixes, and policy conditions:
account and bucket Block Public Access posture:
transport policy, encryption algorithm, KMS keys, grants, and recovery:
versioning, delete-marker behavior, version deletion authority, and restore drill:
Object Lock mode, retention, legal hold, and administrator separation:
storage classes, access observations, retrieval time, and minimum-duration cost:
lifecycle filters, current/noncurrent actions, exclusions, and sample inventory:
replication filter, destination ownership, keys, backlog, and failover procedure:
multipart thresholds, checksums, concurrency, resume, and abandonment cleanup:
metadata, tags, schema, provenance, and sensitive-field policy:
event destinations, deduplication, ordering, retries, failures, and reconciliation:
CloudTrail, access logs, Inventory, Storage Lens, metrics, alerts, and retention:
total cost, quotas, migration, rollback, and final deletion authority:
```

## Common Misconceptions

- “S3 is a filesystem with unlimited disk.” Keys, copies, listings, metadata, and transactions have object-store semantics.
- “A slash creates a directory.” It is an ordinary character commonly used as a delimiter.
- “Strong consistency makes a batch of writes atomic.” Consistency is not a multi-key transaction.
- “Versioning prevents deletion.” It preserves versions until someone or lifecycle permanently deletes them.
- “Durability is backup.” Recovery independence, old versions, keys, metadata, and restore tests are separate.
- “Replication gives an instant second copy.” It is asynchronous, filtered, permission-dependent, and observable.
- “An ETag is the object's MD5.” That is not reliable for multipart and several encrypted-object cases.
- “Lifecycle only affects new objects.” A new rule can select existing eligible objects.
- “S3 events arrive exactly once in order.” Consumers must handle duplicates and reordering.
- “Block Public Access proves least privilege.” It blocks public exposure patterns, not every excessive private grant.

## Core Computer Science Concept

S3 applies **immutable value identity, optimistic concurrency, and asynchronous materialization**. A version ID names one value. Conditional requests coordinate writers without a lock service. Lifecycle, replication, indexing, and notifications materialize derived state later. Correct systems distinguish the authoritative object operation from every eventual copy and projection.

## Engineering Connections

- Object versions extend Chapter 15's immutable value and state-transition reasoning.
- Conditional writes are compare-and-swap operations from concurrent programming.
- Manifest publication follows Chapter 77's immutable artifact promotion model.
- Bucket and KMS policies apply Chapter 92's layered authorization evaluation.
- Private CloudFront origins continue Chapter 96's origin-bypass boundary.
- At-least-once notifications apply Part VI's idempotency and retry contracts.
- Lifecycle is an automated garbage collector whose reachability policy is written by operators.

## From the Field

A team adds a lifecycle rule to expire `exports/` after 30 days, believing it applies only to tomorrow's uploads. The bucket already contains the only copies of several years of regulatory exports, versioning is disabled, and existing objects immediately qualify. Inventory-based preview, versioning, a narrow tag filter, retention review, and a staged sample bucket would have exposed that lifecycle is retrospective destructive policy.

## Engineering Review

### What problem does this solve?

It defines how object identity, authorization, encryption, versions, retention, storage class, lifecycle, replication, multipart state, and events combine into one recoverable S3 data contract.

### Why was it designed this way?

S3 separates durable object values from compute and filesystem administration, then exposes independent controls for access, cost, recovery, and asynchronous integration. That scale requires explicit policy rather than per-disk habits.

### When should I use it?

Use this model for every persistent S3 dataset, artifact or backup bucket, static-content origin, cross-account exchange, lifecycle rule, replication design, large-object uploader, and event-driven consumer.

### When should I avoid it?

Avoid treating S3 as a drop-in replacement for low-latency block storage, shared POSIX files, multi-row transactions, or a mutable database index. Choose the access semantics the application actually needs.

### How does this make me a better engineer?

It teaches you to identify the exact stored value, separate current state from retained history, model asynchronous derived state, and prove who can read, replace, replicate, retain, or permanently delete data.

### How does this reduce waste?

It reduces duplicate copies, uncontrolled public access, abandoned upload parts, needless KMS requests, unrecoverable overwrites, stale noncurrent versions, expensive retrieval mistakes, duplicate event work, and manual storage administration.

## Handbook Principle #97

> Durable object storage begins with exact value identity and ends only when recovery, retention, derived events, and permanent deletion are all intentional.

## Practical Observation

Select one important bucket and list its configuration without changing it. Choose one key and write down its current version, prior versions, delete markers, checksum, encryption key, storage class, retention, replication state, lifecycle eligibility, and event consumers. Then locate the authority and tested procedure that can restore it after overwrite, delete, KMS denial, and Region isolation. If “the object is in S3” is the only recovery evidence, the lifecycle is incomplete.

## Looking Ahead

Object storage is only one data-access model. Chapter 98 compares S3 with EBS block volumes, EFS shared filesystems, and instance-store devices by attachment, sharing, latency, persistence, failure scope, backup, resizing, performance, and cost.

## References

- [Amazon S3 — Service overview and consistency model](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html)
- [Amazon S3 — Naming objects](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-keys.html)
- [Amazon S3 — How access is authorized](https://docs.aws.amazon.com/AmazonS3/latest/userguide/how-s3-evaluates-access-control.html)
- [Amazon S3 — Object Ownership and disabling ACLs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/about-object-ownership.html)
- [Amazon S3 — Blocking public access](https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html)
- [Amazon S3 — Default bucket encryption](https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucket-encryption.html)
- [Amazon S3 — Versioning](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html)
- [Amazon S3 — Object Lock](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html)
- [Amazon S3 — Storage classes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage-class-intro.html)
- [Amazon S3 — Managing object lifecycle](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html)
- [Amazon S3 — Lifecycle rule elements and version behavior](https://docs.aws.amazon.com/AmazonS3/latest/userguide/intro-lifecycle-rules.html)
- [Amazon S3 — Replication requirements and considerations](https://docs.aws.amazon.com/AmazonS3/latest/userguide/replication-requirements.html)
- [Amazon S3 — Multipart upload](https://docs.aws.amazon.com/AmazonS3/latest/userguide/mpuoverview.html)
- [Amazon S3 — Checking object integrity](https://docs.aws.amazon.com/AmazonS3/latest/userguide/checking-object-integrity.html)
- [Amazon S3 — Event types, destinations, ordering, and duplicates](https://docs.aws.amazon.com/AmazonS3/latest/userguide/notification-how-to-event-types-and-destinations.html)
- [Amazon S3 — Conditional writes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html)
- [Chapter 96 — Elastic Load Balancing, Route 53, and CloudFront](96-elastic-load-balancing-route-53-and-cloudfront.md)
