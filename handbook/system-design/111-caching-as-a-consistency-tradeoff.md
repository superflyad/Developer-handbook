# Chapter 111 — Caching as a Consistency Tradeoff

A cache makes a fast copy easy to read. It also creates another version of truth, another authorization surface, another failure mode, and another traffic pattern when the copy disappears. A cache hit can be fast and wrong; a cache miss can be correct and take the source down with it.

The central idea is:

> Cache only a named representation whose authority, key, freshness, invalidation, failure behavior, and source-protection plan are explicit.

## 1. A cache is a derived replica

A cache stores a representation derived from an authority so later work can avoid or reduce an expensive operation. That representation may live in:

- a process or thread;
- an operating-system page cache;
- a shared in-memory service;
- a database buffer or result cache;
- a reverse proxy or content-delivery network;
- a browser or mobile client;
- an intermediate service;
- a precomputed application object.

Each location has a different scope, trust boundary, eviction policy, latency, and invalidation path. “We cache it” is not a design statement.

For each cached value, name the authoritative source, exact representation, allowed readers, maximum useful age, source version, and behavior when the cache or source is unavailable.

## 2. Prove the cache has a purpose

Add a cache to address a measured constraint:

- source latency dominates a critical read;
- repeated computation consumes substantial resources;
- a hot read overloads an authority;
- network distance needs an edge copy;
- a bounded stale response is preferable during source failure;
- immutable content benefits from local reuse.

Measure baseline request rate, hit potential, source cost, latency distribution, object size, update rate, and skew. A cache with a 20% hit rate can add network hops and operational work without protecting the source.

Do not cache merely because a technology is available. First improve indexes, query shape, payload size, pooling, or an accidentally repeated call when those are the actual cause.

## 3. Define the cached representation

A cache should not contain “the user” or “the task” without a representation contract. It may contain:

- authoritative task version 42;
- a board summary projected from version 42;
- an authorization decision for principal P, action A, resource R, and policy version V;
- a negative result that no object existed at an observed version;
- rendered HTML varying by language and encoding;
- an immutable object version addressed by digest.

Include enough version and variant information to detect unsafe reuse. A summary cache cannot answer a full-record query merely because both share a task ID.

Do not place mutable object references in a process cache and let callers modify them. Cache immutable values or defensive copies so one request cannot alter another request's view.

## 4. Design keys as correctness boundaries

A cache key must include every request dimension that changes the representation:

```text
tenant + resource identity + representation + source version
+ locale + authorization scope + content encoding + feature cohort
```

Omitting tenant or authorization scope can leak data. Omitting locale can serve the wrong language. Omitting schema or representation version can make a new binary decode an old incompatible entry. Omitting a query predicate can return the wrong collection.

Canonicalize keys deliberately. Define case, Unicode, sorting, defaults, URL normalization, and hashing. Bound key size and never embed plaintext secrets or sensitive query data that will appear in logs and dashboards.

Namespaces and versioned prefixes simplify bulk migration, but abandoning an old namespace leaves cost until eviction. Track and remove it.

## 5. TTL bounds age, not correctness

A time to live makes an entry ineligible after a duration. It does not guarantee that the value remains correct until then, that it disappears physically at expiry, or that every cache node agrees on time.

Choose TTL from the consequence of staleness and update rate:

```text
maximum stale exposure <= business tolerance
```

A 24-hour TTL might fit immutable documentation and be disastrous for revoked membership. Some values should not be cached without version-aware validation. Others can safely use hours or days.

Add random jitter to large populations of similar TTLs so they do not expire simultaneously. Keep the maximum including jitter within the allowed stale window.

Treat TTL as a safety net when explicit invalidation is expected. It is not a substitute for a missed-update reconciliation plan.

## 6. Use cache-aside with its race model visible

In cache-aside, the application:

1. reads the cache;
2. on miss, reads the authority;
3. stores the representation with a TTL;
4. returns it.

On mutation, a common sequence is commit to the authority and then invalidate the cache. This avoids making the cache authoritative, but races remain:

```text
reader misses cache
reader reads old database value
writer commits new value and invalidates cache
reader stores the old value after invalidation
```

Mitigations include versioned cache entries, compare-before-populate, delayed second invalidation, change-stream invalidation, shorter TTL, or a design where readers reject a version older than a required token.

Document writers outside the application. A migration or administrative tool that bypasses invalidation can keep stale data alive until TTL.

## 7. Understand write-through and write-around

**Write-through** updates the cache as part of the write path, usually after or through the authority. It can improve immediate reads but adds cache latency and failure decisions to every write.

**Write-around** updates the authority and invalidates or bypasses the cache, avoiding pollution from data unlikely to be read soon. The next read pays a miss.

Neither makes two independent systems atomic. Define the order and each failure:

- authority commits, cache write fails;
- cache updates, authority fails;
- response is lost after one or both effects;
- retry arrives;
- another writer races.

The authority must remain clear. If cache failure causes the authoritative write to fail, the cache has become part of availability even if it is not the source of truth.

## 8. Treat write-behind as asynchronous persistence

In write-behind, a write is accepted into the cache or buffer and persisted to the downstream store later. This can batch and reduce latency, but the cache now holds acknowledged state that may be lost, reordered, duplicated, or conflicted.

It needs a durable log, idempotent persistence, ordering scope, retry and DLQ policy, backpressure, recovery, and an explicit durability acknowledgment. An ordinary volatile cache is not a safe write-behind authority.

If the business cannot lose an acknowledged update, persist it under that durability contract before returning success. Do not call write-behind “just caching” to avoid reviewing it as asynchronous data ownership.

## 9. Prevent cache stampedes

When a hot key expires or is evicted, many requests can miss and recompute it simultaneously. The source receives a burst exactly when protection is needed.

Techniques include:

- request coalescing or single-flight per key;
- probabilistic early refresh;
- TTL jitter;
- stale-while-revalidate within an allowed window;
- background refresh of known hot keys;
- bounded refresh concurrency;
- source rate and concurrency limits;
- prewarming before a predictable launch.

A distributed refresh lock needs timeout, ownership, failure, and fencing behavior. Often a short single-flight promise per process plus source limits is simpler; a shared cache may still see one refresh per process.

Return an explicit failure rather than start unlimited recomputation when neither stale data nor source capacity is safe.

## 10. Distinguish stale-while-revalidate from stale-if-error

**Stale-while-revalidate** allows serving a stale response for a bounded window while one refresh occurs. It improves tail latency and limits miss bursts.

**Stale-if-error** allows a stale response when the source fails. It trades freshness for availability.

These need different business review. Serving yesterday's public article may be acceptable; serving revoked authorization, changed price, deleted private content, or obsolete safety instructions may not be.

RFC 9111 defines HTTP cache reuse and revalidation rules, including `must-revalidate`. RFC 5861 defines stale extensions. Application caches should be equally explicit even when they do not use HTTP directives.

Expose age or source version where consumers need to judge the result. Never silently serve stale data beyond the declared window.

## 11. Use validators to avoid unnecessary transfer

Version identifiers, entity tags, or last-modified metadata let a cache ask whether its representation remains current. A successful validation can reuse the stored body without retransferring it.

Validators must correspond to the representation and all its variants. A weak timestamp with insufficient resolution can miss rapid updates. A hash over the representation can be strong but costs computation.

Conditional validation still calls the source and consumes capacity. It reduces payload and serialization work; it does not provide disconnected availability unless stale reuse is separately allowed.

Do not use an untrusted client-supplied version as proof that authorization or state is current.

## 12. Design negative caching deliberately

Caching “not found” or another failure can protect a source from repeated requests for nonexistent keys. It can also hide a newly created object or prolong an outage.

Define which negative outcomes are cacheable:

- authoritative absence;
- forbidden response intentionally indistinguishable from absence;
- transient dependency error;
- rate limit;
- validation failure.

Use a short TTL for absence when objects may appear soon. Do not cache transient server errors as absence. Include tenant, authorization, and query variants in the key. Limit attacker-controlled key cardinality so random misses cannot fill the cache or hammer the source.

## 13. Treat eviction as expected behavior

TTL expiry, least-recently-used policy, memory pressure, node replacement, rebalancing, and operator action can remove entries at any time.

The application must remain correct on a miss. The source and fallback path must survive a cold cache at an explicitly tested rate. If they cannot, the cache is an operational dependency and needs minimum capacity, recovery objectives, and failure controls.

Do not use cache contents as the only enumeration of business objects, lock ownership, job progress, idempotency result, or audit history unless the store is deliberately configured and operated as the authority for that state.

## 14. Avoid cache pollution and unbounded cardinality

Large one-time scans and attacker-chosen keys can evict valuable hot entries. Segment caches, limit object size, bypass cache for bulk and low-reuse queries, and admission-control new entries when necessary.

Measure reuse before caching query combinations. A high-cardinality search cache can have near-zero hits while consuming memory and invalidation work.

Per-tenant quotas can prevent one noisy tenant from evicting everyone else. Sensitive tenants may require separate encryption, keys, or cache boundaries.

## 15. Protect authorization and private data

Authorization decisions change when roles, relationships, policies, resource state, or risk context changes. If cached, key them by principal, tenant, action, resource, and relevant policy or relationship version.

Define revocation objective. If access must end within one minute, a ten-minute TTL without event invalidation violates it. Denial caching also needs care: a user granted access should not remain denied indefinitely.

Shared HTTP caches must follow `private`, `no-store`, authorization, and variation semantics. Application caches need equivalent controls. Redaction is not enough if keys, sizes, or hit timing expose sensitive existence.

Delete or make inaccessible all cached copies when privacy or security requirements demand it; TTL alone may not meet immediate revocation.

## 16. Use multi-level caches without hiding age

A request can traverse browser, CDN, proxy, process, shared cache, database buffer, and replica. Their freshness windows compose.

If each layer may serve ten minutes stale, the result is not necessarily only ten minutes stale; an inner layer can refresh an outer layer with already stale data. Carry source version and observed time, and define maximum age relative to authority.

Coordinate invalidation across layers or use immutable versioned names. Purging a CDN while a reverse proxy still holds stale content simply repopulates the edge with the old representation.

Observe which layer served the response without leaking internal topology to untrusted clients.

## 17. Prefer immutable content addressing where possible

If content is immutable and named by a cryptographic digest or immutable version, caches need no invalidation for that identity. New content gets a new identity, and mutable aliases can have short TTLs or explicit update.

This works well for static assets, container layers, artifacts, and versioned objects. It does not solve mutable business identity: clients still need a contract for discovering the current version.

Verify content against the digest at trust boundaries. A content address identifies bytes; it does not authorize access or establish publisher trust.

## 18. Make cache failure behavior explicit

Decide separately for read timeout, connection failure, corrupt value, cluster partition, and write failure:

- bypass to source;
- serve bounded stale data;
- fail closed;
- shed optional work;
- use a local fallback;
- return an explicit unavailable response.

Fail-open bypass can cause a source avalanche. Protect it with concurrency limits, rate limits, circuit breaking, and admission control. Failing closed may be correct for authorization and dangerous for a public content path.

Cache timeouts should be far shorter than the request deadline. A slow cache followed by a slow source consumes the entire budget twice.

## 19. Observe both performance and correctness

Monitor:

- hit, miss, and bypass rates by bounded representation class;
- fresh, stale, revalidated, and negative hits;
- cache and source latency distributions;
- origin requests avoided and generated;
- fill and invalidation failures;
- entry age and source-version lag;
- evictions, memory, object sizes, and hot keys;
- refresh concurrency and coalescing;
- source load during cold start or outage;
- stale-data and authorization incidents.

A high hit ratio can hide one low-volume but expensive miss class. Weight hits by source cost and user importance, not only request count.

Never include raw sensitive keys in metrics. Use bounded categories and protected diagnostic samples.

## 20. Test the cold and broken states

Test:

- empty cache under peak traffic;
- hot-key expiry with synchronized requests;
- cache node loss and rebalancing;
- invalidation loss or delay;
- stale fill racing a committed write;
- corrupt or incompatible serialized values;
- source failure with and without allowed stale data;
- cache timeout and bypass protection;
- authorization revocation;
- bulk migration and namespace cutover;
- deletion across all cache layers.

Use a disposable or authorized environment with bounded load and stop conditions. A warm-cache benchmark alone measures the easiest state.

## 21. Apply the model to task collaboration

A defensible initial plan might cache:

- immutable attachment versions at the edge under content-version keys;
- task board summaries for a short TTL, keyed by tenant, project, query, locale, and representation version;
- membership lookups only with membership-policy version and a strict revocation bound;
- negative task lookups briefly to absorb repeated invalid identifiers.

Task assignment writes remain authoritative in the database. They publish versioned invalidation after commit. Interactive read-your-writes uses the commit version to bypass or reject an older cached summary. Search remains a separate derived model rather than being hidden behind the word cache.

The system must survive shared-cache loss through bounded source concurrency and load shedding. Bulk exports bypass interactive cache admission so they do not evict board data.

## 22. Encode a cache contract

This model rejects missing authority, incomplete keys, unbounded staleness, and unsafe bypass.

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class CacheContract:
    representation: str
    authority: str
    key_includes_tenant: bool
    key_includes_authorization_scope: bool
    key_includes_representation_version: bool
    ttl_seconds: int
    maximum_stale_seconds: int
    invalidation_defined: bool
    stampede_control: bool
    cold_source_tested: bool
    bypass_bounded: bool
    deletion_propagates: bool

    def validate(self) -> None:
        if not self.representation.strip() or not self.authority.strip():
            raise ValueError("cache needs a representation and authority")
        if not self.key_includes_tenant or not self.key_includes_authorization_scope:
            raise ValueError("cache key omits isolation or authorization scope")
        if not self.key_includes_representation_version:
            raise ValueError("cache key omits representation version")
        if self.ttl_seconds <= 0:
            raise ValueError("cache requires a positive TTL")
        if self.ttl_seconds > self.maximum_stale_seconds:
            raise ValueError("TTL exceeds permitted staleness")
        if not self.invalidation_defined:
            raise ValueError("cache invalidation is undefined")
        if not self.stampede_control:
            raise ValueError("hot misses can stampede the authority")
        if not self.cold_source_tested or not self.bypass_bounded:
            raise ValueError("cold-cache fallback does not protect the source")
        if not self.deletion_propagates:
            raise ValueError("cache does not honor deletion")
```

Executable tests exercise the contract:

```python
import unittest

from cache_contract import CacheContract


def valid_contract() -> CacheContract:
    return CacheContract(
        "project board summary", "task database", True, True, True,
        30, 60, True, True, True, True, True,
    )


class CacheContractTests(unittest.TestCase):
    def test_complete_contract_is_accepted(self) -> None:
        valid_contract().validate()

    def test_missing_tenant_scope_is_rejected(self) -> None:
        contract = valid_contract()
        fields = {**contract.__dict__, "key_includes_tenant": False}
        with self.assertRaisesRegex(ValueError, "isolation"):
            CacheContract(**fields).validate()

    def test_missing_auth_scope_is_rejected(self) -> None:
        contract = valid_contract()
        fields = {**contract.__dict__, "key_includes_authorization_scope": False}
        with self.assertRaisesRegex(ValueError, "authorization"):
            CacheContract(**fields).validate()

    def test_excessive_ttl_is_rejected(self) -> None:
        contract = valid_contract()
        fields = {**contract.__dict__, "ttl_seconds": 120}
        with self.assertRaisesRegex(ValueError, "staleness"):
            CacheContract(**fields).validate()

    def test_missing_stampede_control_is_rejected(self) -> None:
        contract = valid_contract()
        fields = {**contract.__dict__, "stampede_control": False}
        with self.assertRaisesRegex(ValueError, "stampede"):
            CacheContract(**fields).validate()

    def test_untested_cold_source_is_rejected(self) -> None:
        contract = valid_contract()
        fields = {**contract.__dict__, "cold_source_tested": False}
        with self.assertRaisesRegex(ValueError, "cold-cache"):
            CacheContract(**fields).validate()

    def test_unbounded_bypass_is_rejected(self) -> None:
        contract = valid_contract()
        fields = {**contract.__dict__, "bypass_bounded": False}
        with self.assertRaisesRegex(ValueError, "protect"):
            CacheContract(**fields).validate()

    def test_missing_deletion_is_rejected(self) -> None:
        contract = valid_contract()
        fields = {**contract.__dict__, "deletion_propagates": False}
        with self.assertRaisesRegex(ValueError, "deletion"):
            CacheContract(**fields).validate()


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

Save the blocks as `cache_contract.py` and `test_cache_contract.py`, then run:

```bash
python -m unittest -v test_cache_contract.py
```

A production checker should inspect actual key construction, authorization variants, serialized schema versions, TTL and jitter, invalidation events, stale age, cold-load tests, bypass limits, source capacity, privacy deletion, and metrics. A configured TTL alone does not prove bounded business staleness.

## 23. Review a cache

```text
measured problem, baseline latency, source cost, reuse, update rate, and skew:
cache location, scope, trust boundary, availability, and owner:
representation, authority, source version, sensitivity, and allowed readers:
key tenant, principal, authorization, locale, query, schema, and normalization:
TTL, jitter, maximum source-relative age, and clock assumptions:
cache-aside read, fill, write, invalidation, and stale-fill race:
write-through/around order, authority failure, cache failure, and retry:
write-behind durability, log, ordering, duplicate, backpressure, and recovery:
single-flight, early refresh, stale window, concurrency, and prewarming:
stale-while-revalidate, stale-if-error, forbidden stale classes, and age signal:
validator identity, variants, collision, source call, and revalidation behavior:
negative outcomes, TTL, appearance delay, attacker keys, and transient errors:
eviction, cold start, source envelope, operational dependency, and rebuild:
admission, maximum object, bulk bypass, tenant quota, and cache pollution:
authorization version, revocation objective, denial cache, and private data:
multi-level age, invalidation propagation, repopulation, and layer evidence:
timeout, bypass, fail closed/open, stale fallback, shedding, and source circuit:
hits, weighted savings, stale age, invalidation, evictions, hot keys, and cost:
cold, stampede, node loss, race, corruption, source failure, revoke, and delete tests:
```

## Common Misconceptions

- “A cache only changes performance.” It changes observation, availability, authorization, and source load.
- “TTL keeps data correct.” It only bounds eligibility by cache-local age.
- “Delete after write eliminates stale cache.” A concurrent miss can refill an older value after deletion.
- “Write-through makes cache and database atomic.” Independent failures and retries remain.
- “Write-behind is just a faster cache.” It accepts durable-state responsibility.
- “A high hit ratio proves value.” Miss cost, object class, correctness, and source protection matter.
- “Eviction is exceptional.” It is ordinary cache behavior.
- “Fail open to the database is safe.” A cache outage can become a source avalanche.
- “Authorization can use a long TTL because permissions rarely change.” Revocation consequence, not update frequency, sets the bound.
- “Every cache layer has a ten-minute TTL, so data is at most ten minutes stale.” Layers can refresh from already stale inner copies.

## Core Computer Science Concept

This chapter applies **memoization, replica consistency, temporal validity, working sets, admission and eviction, request coalescing, and feedback control**. Caching trades recomputation and source traffic for copy coordination; correctness depends on whether the cached observation remains valid for the decision being made.

## Engineering Connections

- Locality and page caching extend Chapters 3, 39, 40, and 41.
- HTTP cache semantics build on Chapters 59 and 67.
- Idempotency and concurrency apply Chapters 74, 100, 107, and 110.
- Stampedes and cold-source capacity use Chapter 109's overload model.
- Security and deletion extend Chapters 87, 92, 97, and 104.

## From the Field

A team caches project membership for 30 minutes because changes are rare. An administrator removes a compromised account, but API instances continue authorizing writes from cached membership. The cache met its hit-rate target and violated the revocation objective. A policy-version key, invalidation event, short maximum stale window, and commit-time authorization check would align performance with consequence.

## Engineering Review

### What problem does this solve?

It reduces measured read or computation cost while preserving an explicit authority, stale bound, failure mode, and source-capacity envelope.

### Why was it designed this way?

Cache failures occur at the boundary between performance and correctness: incomplete keys, races, eviction, stampedes, stale authorization, and unbounded bypass. The contract makes those mechanisms reviewable.

### When should I use it?

Use it for demonstrated repeated reads or computation where the representation's reuse and staleness consequences are understood.

### When should I avoid it?

Avoid caching low-reuse or high-cardinality queries, unbounded sensitive variants, and decisions whose required freshness cannot be enforced by the design.

### How does this make me a better engineer?

It teaches you to see cached data as a replica, build complete keys, analyze races, and test empty and broken cache states rather than only warm hits.

### How does this reduce waste?

It avoids cache layers with no measured benefit, duplicated authorities, stale-fill bugs, stampede incidents, cache pollution, excessive memory, source avalanches, and privacy copies that outlive their data.

## Handbook Principle #111

> A cache is safe only when every hit is scoped to the right representation and reader, every stale value has a tolerated consequence, and every miss has a bounded path to authority.

## Practical Observation

Empty one non-production cache and measure the source traffic and latency until it warms. Then expire its hottest key under concurrent load. If the source envelope, coalescing, and stale behavior are unknown, the cache currently borrows reliability from an untested assumption.

## Looking Ahead

Chapter 112 moves derived work across time and ownership boundaries through queues, logs, events, outboxes, sagas, dead letters, backpressure, schema evolution, and replay while preserving the invariants defined in Chapter 110.

## References

- [RFC 9111 — HTTP Caching](https://www.rfc-editor.org/rfc/rfc9111.html)
- [RFC 5861 — HTTP stale controls](https://www.rfc-editor.org/rfc/rfc5861.html)
- [RFC 9205 — Building Protocols with HTTP](https://www.rfc-editor.org/rfc/rfc9205.html)
- [Redis — Cache-aside pattern](https://redis.io/docs/latest/develop/use-cases/cache-aside/)
- [AWS — Caching best practices](https://aws.amazon.com/caching/best-practices/)
- [Cloudflare — Cache invalidation and revalidation](https://developers.cloudflare.com/cache/guides/invalidate-cache/)
- [Chapter 100 — DynamoDB, Caching, and NoSQL Access Patterns](../aws/100-dynamodb-caching-and-nosql-access-patterns.md)
- [Chapter 110 — Consistency, Transactions, and Concurrent Change](110-consistency-transactions-and-concurrent-change.md)
