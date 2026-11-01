# Chapter 96 — Elastic Load Balancing, Route 53, and CloudFront

A public request may cross recursive DNS caches, an authoritative DNS service, a content-delivery edge, a load balancer, and several application targets before it produces a response. Calling that entire path “the network” hides who made each decision and makes outages harder to diagnose.

The central idea is:

> Trace delivery as separate naming, edge, load-balancing, and application decisions. Each layer has its own health signal, cache, identity evidence, TLS connection, and failure behavior.

## 1. One request crosses several control planes

For a common web architecture, the path is:

```text
viewer
  -> recursive DNS cache
  -> Route 53 authoritative answer
  -> CloudFront edge location
  -> origin connection
  -> Application Load Balancer listener
  -> listener rule and target group
  -> healthy application target
```

The path is not mandatory. Route 53 can point directly to a load balancer, CloudFront can use S3 or another HTTP service as an origin, and a Network Load Balancer can carry non-HTTP traffic. What matters is naming every active layer.

Three questions separate the main decisions:

1. **DNS:** Which endpoint name or address should the client try?
2. **CloudFront:** Can an edge cache answer this representation, or which origin should receive the request?
3. **Elastic Load Balancing:** Which registered target should receive this connection or request?

A healthy answer at one layer does not prove health at the next. DNS may return a load balancer whose targets are failing. A load balancer may reach an application that cannot reach its database. CloudFront may correctly serve an object that is operationally stale.

## 2. DNS returns answers; it does not proxy the request

Route 53 is an authoritative Domain Name System service. A public hosted zone holds records for an internet namespace; a private hosted zone makes records resolvable through associated VPCs. Route 53 answers queries according to record configuration, routing policy, and health information.

After receiving an answer, a client connects to the returned destination. Route 53 is normally not on the HTTP or TCP data path. Consequently:

- DNS logs do not replace load-balancer or application access logs;
- changing a record does not recall answers already cached by resolvers or clients;
- DNS health checks do not inspect every user request;
- a successful lookup does not prove that a later TLS or application exchange succeeds.

When debugging, distinguish “name did not resolve,” “name resolved to the wrong endpoint,” and “the selected endpoint failed.”

## 3. Records bind names to delivery endpoints

Common record types include:

- `A` and `AAAA` for IPv4 and IPv6 addresses;
- `CNAME` for one non-apex name referring to another name;
- `MX` for mail delivery;
- `TXT` for verification and policy data;
- Route 53 **alias records** for supported AWS resources and other records in the same hosted zone.

An alias record resembles a CNAME from an operator's perspective, but Route 53 can create one at the zone apex and can point it to resources such as an ELB load balancer or CloudFront distribution. Use the resource's assigned DNS name or an alias—not discovered load-balancer node addresses, which can change.

Ownership matters. Record the hosted-zone owner, registrar owner, delegation, certificate validation records, and change path. A perfectly configured load balancer remains unreachable if delegation points elsewhere or a validation record is removed.

## 4. Routing policy selects a candidate answer

Route 53 routing policies express different intentions:

| Policy | Primary question | Typical purpose |
| --- | --- | --- |
| Simple | What is the ordinary answer? | One endpoint or basic multi-value response |
| Weighted | Which configured proportion should receive traffic? | Controlled migration or experiments |
| Latency | Which configured Region has the lowest modeled latency? | Multi-Region service selection |
| Failover | Is the primary healthy; otherwise use secondary? | Active-passive recovery |
| Multivalue answer | Which healthy values can be returned? | Simple DNS-level distribution |
| Geolocation | Where is the requester located? | Localized or regulated routing |
| Geoproximity | How near are resources and users, with optional bias? | Geographic traffic shifting |
| IP-based | Which configured client CIDR matched? | Routing known network populations |

Routing policy is not a substitute for capacity or application correctness. A 10% weighted record can receive more or less than exactly 10% of requests because resolvers cache answers and many users may share a resolver. Latency policy uses AWS measurements and record configuration; it does not sample each application's current response time.

Write the intent before choosing the policy. “Send users to the best endpoint” is not testable. “Prefer the primary while its published health condition passes; otherwise answer with the secondary” is.

## 5. TTL is a convergence contract

DNS time to live controls how long a resolver may cache an answer. A lower TTL can reduce—but does not eliminate—change propagation delay. It also increases query frequency and cannot force every client, browser, operating system, or intermediary to discard an answer immediately.

Choose TTL from an operational contract:

- expected failover or migration time;
- query cost and authoritative load;
- endpoint stability;
- resolver behavior observed for the user population;
- rollback procedure;
- certificate and application readiness at every possible answer.

Lower the TTL before a planned migration, wait for the previous TTL window, make the change, observe both old and new destinations, and restore the steady-state TTL after convergence. Emergency failover must assume some traffic continues to the old answer.

## 6. Route 53 health is sampled and policy-specific

A Route 53 health check probes an endpoint periodically; it does not run when each DNS query arrives. An alias can instead evaluate the health of its AWS target, including an ELB resource. Route 53 first applies routing-policy rules and then considers health among eligible records.

Important consequences include:

- a record without a configured health check is generally treated as healthy;
- health-check endpoints need network reachability from the checkers;
- a shallow probe can pass while dependencies are unusable;
- a deep probe can withdraw every endpoint during a shared dependency failure;
- alias health depends on the target resource's documented health semantics;
- if every applicable record is unhealthy, Route 53 can return records rather than return no answer.

That last behavior prevents a health configuration from automatically becoming a total DNS outage, but it is a fail-open condition. Test the all-unhealthy case and decide whether the application can degrade safely.

## 7. Choose a load-balancer family by protocol and control

Elastic Load Balancing offers distinct families:

- **Application Load Balancer (ALB):** Layer 7 HTTP and HTTPS routing with host, path, header, query, method, source-IP, redirect, fixed-response, and weighted-forwarding capabilities. It supports HTTP/2, WebSockets, and gRPC in documented configurations.
- **Network Load Balancer (NLB):** Layer 4 TCP, TLS, UDP, and TCP_UDP delivery for high-performance connection handling, static per-zone addresses, source-IP behavior, or TLS pass-through/termination requirements.
- **Gateway Load Balancer (GWLB):** insertion and scaling of compatible network virtual appliances using GENEVE. It is a service-chain tool, not a general web router.
- **Classic Load Balancer:** the previous generation. Prefer a current family for new designs unless a documented compatibility constraint requires it.

Protocol determines which evidence the load balancer can use. An ALB can route on HTTP attributes because it terminates and understands that protocol. An NLB forwarding TCP cannot make a path-based decision about encrypted bytes it does not decrypt.

## 8. A listener is the front-door contract

A listener binds a protocol and port and applies a default action plus ordered rules. For an ALB, a rule can forward to target groups, redirect, return a fixed response, or authenticate in supported arrangements.

Review a listener as an API boundary:

- internet-facing or internal scheme;
- allowed security-group sources;
- protocol, port, and HTTP versions;
- certificate names, issuer, renewal, and security policy;
- default action;
- rule priorities and unmatched behavior;
- header and host normalization assumptions;
- idle timeout and long-lived connection behavior;
- access logging and correlation identifiers.

Rule overlap deserves tests. A broad `/api/*` rule placed before a narrower contract can send traffic to the wrong target group. Make the default action intentionally safe; do not let unmatched hosts silently reach a privileged application.

## 9. Target groups define the backend contract

A target group combines:

- target type, such as instance, IP address, or Lambda where supported;
- target protocol, port, and protocol version;
- registered targets;
- health-check configuration;
- load-balancing attributes;
- deregistration and connection-draining behavior;
- optional stickiness;
- failover and health thresholds where supported.

The listener answers “where should this class of request go?” The target group answers “which members implement that backend contract?” Keep target groups aligned with one deployable health and protocol contract. Combining unrelated applications makes health, rollout, and rollback ambiguous.

Registration is not readiness. A new target should receive production traffic only after bootstrap, dependency initialization, and application readiness succeed.

## 10. Health checks must represent readiness

An ALB periodically checks each registered target using the target group's protocol, port, path, timeout, interval, success matcher, and healthy/unhealthy thresholds. It routes ordinary requests to targets considered healthy.

A useful readiness endpoint proves that the process can serve its current traffic contract without performing expensive work. It should usually check local initialization and critical, bounded dependencies while avoiding side effects. Separate signals help:

- **liveness:** should the process be restarted?
- **readiness:** should this replica receive traffic?
- **business health:** can the user journey complete?

Do not make every shared downstream dependency a binary readiness requirement without analyzing correlated failure. If a shared database briefly fails and every replica becomes unhealthy, an ALB target group containing only unhealthy targets fails open and routes to them anyway. Health checks are routing evidence, not a circuit breaker or correctness proof.

## 11. Design for Availability Zone loss

Attach an ALB to subnets in at least two Availability Zones and place ready targets across those zones. Then examine:

- capacity remaining after one zone is unavailable;
- per-zone target registration and scaling;
- cross-zone load-balancing behavior for the chosen family and target group;
- zonal data-transfer implications;
- zonal dependencies such as NAT gateways or databases;
- DNS zonal-shift or failover behavior where used;
- deployments that temporarily reduce healthy capacity;
- quotas and capacity reservations.

“Multi-AZ load balancer” is incomplete when every target, NAT path, or stateful dependency still lives in one zone. Draw the entire request path by zone and remove each zone in a tabletop exercise.

## 12. TLS creates separate trust legs

TLS can terminate at several points:

```text
viewer ==TLS 1==> CloudFront ==TLS 2==> ALB ==TLS 3==> target
```

Each `==TLS==>` is a distinct connection with its own certificate validation, policy, hostname, logs, and failure modes. TLS from viewer to CloudFront does not encrypt a later origin connection configured as HTTP. An ALB HTTPS listener terminates the client connection; its target-group protocol independently determines whether the backend leg uses HTTPS.

For each leg, record:

- peer hostname and certificate owner;
- minimum protocol and cipher policy;
- certificate issue, renewal, and deployment path;
- whether client authentication is required;
- where plaintext can exist;
- which logs identify negotiation failures.

Terminate where protocol-aware routing or inspection is needed, then re-encrypt sensitive traffic across untrusted or policy-controlled boundaries. Use TCP pass-through when the target must terminate TLS and accept the loss of Layer 7 routing at that hop.

## 13. Client identity is forwarded evidence, not magic

A proxy changes the network peer seen by the application. An ALB normally appends the last-hop client address to `X-Forwarded-For` and supplies `X-Forwarded-Proto` and `X-Forwarded-Port`. CloudFront and other proxies add their own headers.

Never trust an arbitrary leftmost forwarded value merely because it looks like an IP address. A client can send a forged header before reaching the first trusted proxy. Configure a known proxy chain, normalize or remove untrusted input at the boundary, and parse from the trusted side according to framework behavior.

Keep distinct concepts distinct:

- transport peer address;
- asserted viewer address;
- authenticated user or workload identity;
- geographic inference;
- request correlation ID.

IP addresses are weak user identity. Use them for bounded security signals and diagnostics, not as the sole authorization credential.

## 14. Stickiness is not durable session state

Load-balancer stickiness can route a client repeatedly to the same target. It may help compatibility or cache locality, but it introduces uneven load and complicates replacement. A sticky target can still drain, fail, scale in, or disappear.

Prefer stateless replicas with durable session state in an appropriate shared store or cryptographically protected client token. If stickiness is required, specify:

- cookie ownership and lifetime;
- behavior when the target is unhealthy;
- deployment and draining interaction;
- privacy and consent implications;
- skew monitoring;
- the recovery path when affinity is lost.

The acceptance test remains: any healthy target can continue the request after another target disappears.

## 15. CloudFront is an edge proxy and cache

A CloudFront distribution has one or more origins and ordered cache behaviors. A behavior matches a path pattern and controls viewer protocol, allowed methods, cache policy, origin request policy, response headers, compression, and origin selection.

On a cache hit, an edge location can answer without contacting the origin. On a miss or expired object, CloudFront sends an origin request. This can reduce viewer latency and origin load, absorb repeated reads, and provide a stable public boundary.

The default behavior catches requests not matched by earlier behaviors. Review behavior order like load-balancer rule order. A public static policy must not accidentally match a personalized API path.

## 16. The cache key defines representation identity

A cache key identifies which viewer requests may share one cached response. CloudFront always uses the object path and can vary the key by selected query strings, headers, cookies, and compression support.

The correctness equation is:

```text
same cache key => safe to receive the same representation
```

Too few dimensions can leak or corrupt responses. If language, tenant, authorization, device class, or query input changes the representation, the policy must include the relevant normalized dimension or disable caching. Too many dimensions fragment the cache and reduce hit ratio.

Start from application semantics, not “forward everything.” Enumerate every input that changes the response, normalize high-cardinality values where possible, and test two viewers who must not share content.

## 17. Forwarding and varying are different decisions

A cache policy controls values included in the cache key. An origin request policy can forward additional headers, cookies, and query strings without adding them to that key. Values in the cache key are automatically included in origin requests.

This separation is useful when the origin needs telemetry that does not change its response. For example, a correlation header can be forwarded without producing a unique cached object for every request.

It is dangerous when a forwarded value does change the response but is absent from the cache key. Document two sets for every behavior:

1. values that select the representation and therefore vary the cache key;
2. additional values needed only by the origin.

Treat `Authorization`, session cookies, tenant headers, and user-specific query parameters as security-sensitive inputs. A shared cache needs an explicit proof that responses cannot cross identities.

## 18. TTL and revalidation govern freshness

CloudFront cache policy defines minimum, default, and maximum TTL boundaries. Origin `Cache-Control` and `Expires` metadata participate within those boundaries. When an object expires, CloudFront can request the current representation or revalidate it; a `304 Not Modified` lets the cached body remain, while a new `200` replaces it.

A minimum TTL greater than zero can make CloudFront retain an object for at least that duration even when an origin response says `no-cache`, `no-store`, or `private`. For personalized or rapidly revocable content, use the managed caching-disabled policy or ensure all TTL values are zero unless a reviewed cache-key design proves sharing safe.

Browser caching is separate. Purging an edge object does not force a browser to discard a still-fresh local copy. Error responses can also have caching behavior. Include normal, error, and negative results in freshness tests.

## 19. Prefer versioned object names to routine invalidation

An invalidation asks CloudFront to evict matching cached paths. It is useful for emergencies and content whose URL cannot change, but it takes time, has request limits and cost considerations, and does not repair caches outside CloudFront.

For immutable assets, publish a new name containing a content hash or release version:

```text
/assets/app.7f3a91c2.js
```

Then update the short-lived HTML or manifest that refers to it. Old and new releases can coexist, rollbacks remain possible, and long TTLs are safe. Never overwrite a supposedly immutable object with different bytes.

## 20. Protect the origin from bypass

If viewers can reach the origin directly, they may bypass CloudFront's TLS policy, caching, logging, authorization, rate controls, or future WAF policy. Restrict the origin where the architecture permits it.

For an S3 bucket origin, use Origin Access Control and a bucket policy that grants only the intended distribution access. Keep S3 Block Public Access enabled unless a separately reviewed public model requires otherwise. An S3 website endpoint is a custom origin with different capabilities and does not support the same private OAC pattern.

For a custom origin such as an ALB:

- use HTTPS on the origin leg;
- constrain network sources where supported;
- use a rotated secret header only as defense in depth, not as the sole identity model;
- validate hostnames and reject unknown hosts;
- prevent alternate public paths from bypassing controls;
- monitor direct-origin attempts.

Origin protection is an authorization boundary, not merely a bandwidth optimization.

## 21. Trace one request end to end

For `https://www.example.com/api/orders/42`, record:

1. which hosted zone is authoritative and which record answers;
2. the answer TTL and routing policy;
3. the CloudFront distribution and matching behavior;
4. whether the request is a hit, miss, refresh, or error;
5. the exact cache key and forwarded values;
6. the selected origin and TLS policy;
7. the ALB listener, certificate, and rule;
8. the selected target group and target health state;
9. the trusted forwarded-address chain;
10. the application trace, dependency calls, and response;
11. which layer applied each timeout, retry, or cached error.

This trace turns “CloudFront is down” into a falsifiable claim. A `502` can arise from edge-to-origin certificate failure, an unreachable origin, a load-balancer response, or the application. Evidence must identify the layer that generated it.

## 22. Observe the delivery path by layer

Combine evidence without flattening it:

- Route 53 query logs, health-check status, and change history;
- CloudFront standard or real-time logs, cache status, result type, origin latency, and distribution configuration;
- load-balancer access logs, target health, connection counts, response codes, and latency;
- VPC Flow Logs for accepted and rejected network flows;
- application access logs, metrics, and distributed traces;
- certificate expiration and TLS errors;
- deployment events, scaling activity, and configuration changes.

Propagate a correlation identifier where safe, while retaining each service's generated request ID. Separate viewer latency, edge processing, origin connection, target processing, and dependency latency. Sample carefully, protect personal data, and define log retention before an incident.

Alert on user-visible symptoms and exhausted redundancy, not merely resource existence. Healthy-host count, per-zone capacity, origin error rate, cache-hit changes, certificate age, DNS health, and application success rate tell different stories.

## 23. Rehearse failure and stale-state scenarios

At minimum, test:

- one target becomes unhealthy during normal load;
- every target fails the same readiness check;
- one Availability Zone loses targets or dependencies;
- the primary DNS endpoint is withdrawn while old answers remain cached;
- a certificate expires or presents the wrong hostname on an origin leg;
- a personalized response is requested by two identities;
- an asset is replaced at the same URL;
- CloudFront cannot reach the origin;
- a target drains during a long-lived request;
- a client supplies forged forwarding headers;
- the origin is called directly;
- logging at one layer is unavailable.

Define expected response, maximum detection time, degraded behavior, recovery owner, and evidence for each. “The service handles it” is not a failure contract.

## 24. Build a delivery contract checker

The following standard-library lab encodes one opinionated policy for a sensitive, production web service. It does not prove that AWS resources match the model; it makes architectural assumptions executable before an authorized inventory tool performs that comparison.

```python
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DnsContract:
    routing_policy: str
    ttl_seconds: int
    health_source: str
    all_unhealthy_tested: bool


@dataclass(frozen=True)
class LoadBalancerContract:
    family: str
    availability_zones: frozenset[str]
    listener_protocol: str
    target_protocol: str
    health_path: str
    health_checks_readiness: bool
    session_state_externalized: bool
    trusted_proxy_hops: int


@dataclass(frozen=True)
class CacheBehavior:
    path_pattern: str
    viewer_protocol_policy: str
    origin_protocol_policy: str
    allowed_methods: frozenset[str]
    cached_methods: frozenset[str]
    cache_key_fields: frozenset[str] = field(default_factory=frozenset)
    origin_request_fields: frozenset[str] = field(default_factory=frozenset)
    identity_fields: frozenset[str] = field(default_factory=frozenset)
    min_ttl: int = 0
    default_ttl: int = 0
    max_ttl: int = 0
    personalized: bool = False
    immutable_assets: bool = False

    @property
    def caching_enabled(self) -> bool:
        return any((self.min_ttl, self.default_ttl, self.max_ttl))

    def validate(self) -> None:
        if self.viewer_protocol_policy not in {"https-only", "redirect-to-https"}:
            raise ValueError(f"{self.path_pattern}: viewers must use HTTPS")
        if self.origin_protocol_policy != "https-only":
            raise ValueError(f"{self.path_pattern}: origin must use HTTPS")
        if not self.cached_methods <= self.allowed_methods:
            raise ValueError(f"{self.path_pattern}: cached methods must be allowed")
        if not self.cached_methods <= {"GET", "HEAD", "OPTIONS"}:
            raise ValueError(f"{self.path_pattern}: mutating methods cannot be cached")
        if not 0 <= self.min_ttl <= self.default_ttl <= self.max_ttl:
            raise ValueError(f"{self.path_pattern}: TTLs must be ordered")
        if self.personalized and self.caching_enabled:
            if not self.identity_fields:
                raise ValueError(f"{self.path_pattern}: cached personalization needs identity")
            if not self.identity_fields <= self.cache_key_fields:
                raise ValueError(f"{self.path_pattern}: identity must vary cache key")
        if self.immutable_assets and not self.caching_enabled:
            raise ValueError(f"{self.path_pattern}: immutable assets should be cacheable")


@dataclass(frozen=True)
class DeliveryContract:
    dns: DnsContract
    load_balancer: LoadBalancerContract
    behaviors: tuple[CacheBehavior, ...]
    origin_private: bool

    def validate(self) -> None:
        if self.dns.routing_policy not in {
            "simple", "weighted", "latency", "failover", "multivalue"
        }:
            raise ValueError("unsupported DNS routing policy")
        if not 0 <= self.dns.ttl_seconds <= 300:
            raise ValueError("DNS TTL exceeds the reviewed convergence bound")
        if self.dns.health_source not in {"route53-check", "evaluate-target-health"}:
            raise ValueError("DNS health source is not explicit")
        if not self.dns.all_unhealthy_tested:
            raise ValueError("all-unhealthy DNS behavior must be rehearsed")

        lb = self.load_balancer
        if lb.family != "application":
            raise ValueError("this HTTP contract requires an Application Load Balancer")
        if len(lb.availability_zones) < 2:
            raise ValueError("production load balancer needs at least two AZs")
        if lb.listener_protocol != "HTTPS" or lb.target_protocol != "HTTPS":
            raise ValueError("sensitive traffic requires TLS on both ALB legs")
        if not lb.health_path.startswith("/") or not lb.health_checks_readiness:
            raise ValueError("target health must use an application readiness path")
        if not lb.session_state_externalized:
            raise ValueError("session state must survive target replacement")
        if lb.trusted_proxy_hops < 1:
            raise ValueError("trusted proxy chain must be explicit")

        if not self.behaviors or "*" not in {b.path_pattern for b in self.behaviors}:
            raise ValueError("a reviewed default cache behavior is required")
        for behavior in self.behaviors:
            behavior.validate()
        if not self.origin_private:
            raise ValueError("origin bypass must be prevented")
```

Tests exercise the security and availability boundaries:

```python
import unittest

from delivery_contract import (
    CacheBehavior,
    DeliveryContract,
    DnsContract,
    LoadBalancerContract,
)


def valid_contract() -> DeliveryContract:
    return DeliveryContract(
        dns=DnsContract(
            routing_policy="failover",
            ttl_seconds=60,
            health_source="evaluate-target-health",
            all_unhealthy_tested=True,
        ),
        load_balancer=LoadBalancerContract(
            family="application",
            availability_zones=frozenset({"use1-az1", "use1-az2"}),
            listener_protocol="HTTPS",
            target_protocol="HTTPS",
            health_path="/ready",
            health_checks_readiness=True,
            session_state_externalized=True,
            trusted_proxy_hops=2,
        ),
        behaviors=(
            CacheBehavior(
                path_pattern="/assets/*",
                viewer_protocol_policy="redirect-to-https",
                origin_protocol_policy="https-only",
                allowed_methods=frozenset({"GET", "HEAD"}),
                cached_methods=frozenset({"GET", "HEAD"}),
                min_ttl=3600,
                default_ttl=86400,
                max_ttl=31536000,
                immutable_assets=True,
            ),
            CacheBehavior(
                path_pattern="*",
                viewer_protocol_policy="https-only",
                origin_protocol_policy="https-only",
                allowed_methods=frozenset({"GET", "HEAD", "POST"}),
                cached_methods=frozenset({"GET", "HEAD"}),
                origin_request_fields=frozenset({"authorization", "x-request-id"}),
                identity_fields=frozenset({"authorization"}),
                personalized=True,
            ),
        ),
        origin_private=True,
    )


class DeliveryContractTests(unittest.TestCase):
    def test_complete_contract_is_accepted(self) -> None:
        valid_contract().validate()

    def test_single_az_is_rejected(self) -> None:
        contract = valid_contract()
        broken = DeliveryContract(
            contract.dns,
            LoadBalancerContract(**{
                **contract.load_balancer.__dict__,
                "availability_zones": frozenset({"use1-az1"}),
            }),
            contract.behaviors,
            contract.origin_private,
        )
        with self.assertRaisesRegex(ValueError, "at least two AZs"):
            broken.validate()

    def test_plaintext_origin_is_rejected(self) -> None:
        contract = valid_contract()
        behavior = CacheBehavior(**{
            **contract.behaviors[1].__dict__,
            "origin_protocol_policy": "http-only",
        })
        broken = DeliveryContract(
            contract.dns, contract.load_balancer,
            (contract.behaviors[0], behavior), contract.origin_private,
        )
        with self.assertRaisesRegex(ValueError, "origin must use HTTPS"):
            broken.validate()

    def test_shared_personalized_cache_is_rejected(self) -> None:
        contract = valid_contract()
        behavior = CacheBehavior(**{
            **contract.behaviors[1].__dict__,
            "default_ttl": 60,
            "max_ttl": 60,
        })
        broken = DeliveryContract(
            contract.dns, contract.load_balancer,
            (contract.behaviors[0], behavior), contract.origin_private,
        )
        with self.assertRaisesRegex(ValueError, "identity must vary cache key"):
            broken.validate()

    def test_unrehearsed_dns_failure_is_rejected(self) -> None:
        contract = valid_contract()
        broken = DeliveryContract(
            DnsContract("failover", 60, "evaluate-target-health", False),
            contract.load_balancer,
            contract.behaviors,
            contract.origin_private,
        )
        with self.assertRaisesRegex(ValueError, "all-unhealthy"):
            broken.validate()


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

Save the blocks as `delivery_contract.py` and `test_delivery_contract.py`, then run:

```bash
python -m unittest -v test_delivery_contract.py
```

The example uses AZ IDs to avoid account-specific Availability Zone names. A production verifier should query authorized read-only inventory for Route 53 records and health checks, distribution behaviors and policies, certificates, load-balancer listeners and rules, target health, subnets, logging, and origin policy. It must not change DNS, invalidate content, deregister targets, or modify distributions during validation.

## 25. Review an external request path

```text
service, owners, accounts, Regions, data class, and SLO:
registrar, delegation, public/private hosted zones, and change authority:
record names, aliases, routing policies, TTLs, and health sources:
cached-answer convergence and all-unhealthy behavior:
CloudFront distribution, aliases, certificates, and ordered behaviors:
cache key, origin request fields, TTLs, error caching, and invalidation path:
origin names, origin access, TLS policy, and bypass prevention:
load-balancer family, scheme, subnets, AZ IDs, and capacity after AZ loss:
listeners, certificates, security policies, defaults, and ordered rules:
target groups, protocols, ports, readiness, thresholds, and draining:
session-state location and stickiness behavior:
trusted proxy chain, client-address parsing, and authenticated identity:
viewer, edge, origin, and target timeouts and retries:
DNS, edge, load-balancer, flow, application, and trace evidence:
failure rehearsals, rollback, cost, quotas, and retirement owner:
```

## Common Misconceptions

- “Route 53 sends the HTTP request.” It returns a DNS answer; the client then connects to the selected endpoint.
- “A low TTL makes failover instant.” Existing caches and clients still control when they refresh.
- “Health checks guarantee only healthy traffic.” Both Route 53 and ALB have documented all-unhealthy behavior that can return or route traffic.
- “Multi-AZ ELB makes the application Multi-AZ.” Targets and every critical dependency must also survive zone loss.
- “TLS at CloudFront encrypts the whole path.” Viewer, origin, load-balancer, and target connections are separate legs.
- “`X-Forwarded-For` is authenticated identity.” Trust depends on a controlled proxy chain and header processing.
- “Stickiness preserves sessions.” It is routing affinity, not durable state.
- “Forwarded values automatically vary the cache.” Cache and origin-request policies are separate.
- “`Cache-Control: private` always prevents CloudFront caching.” A positive minimum TTL can override that expectation.
- “Invalidation updates every cache.” Browser and intermediary caches remain separate.

## Core Computer Science Concept

Traffic delivery combines **indirection, partial observation, and memoization**. DNS maps a stable name to a changing endpoint. Load balancing maps a service endpoint to one member of a replica set using sampled health. A CDN memoizes representations by cache key and freshness rules. Correctness depends on defining the identity, lifetime, and failure semantics of each mapping.

## Engineering Connections

- DNS TTL and CloudFront TTL extend Chapter 29's cache-invalidation model.
- Listener rules and cache behaviors are ordered dispatch tables like application routers.
- Target health applies Chapter 88's liveness and readiness separation.
- Multi-AZ placement depends on Chapter 93's subnet and route boundaries.
- Trusted proxy headers follow Chapter 54's authentication-boundary reasoning.
- Externalized sessions continue Chapter 95's replaceable-compute contract.
- Versioned assets apply Part VII's immutable-artifact promotion model.

## From the Field

A team caches `/account` at the edge and forwards the session cookie so the origin can authenticate. The cookie is absent from the cache key. The first signed-in response fills the cache, and later users receive that account page because forwarding a value did not vary the representation. A caching-disabled API behavior—or a carefully reviewed identity-aware key—plus a two-user isolation test would have exposed the design before release.

## Engineering Review

### What problem does this solve?

It assigns DNS selection, edge caching, TLS, request routing, target health, client evidence, and session state to explicit layers so the external request path can be secured, tested, and diagnosed.

### Why was it designed this way?

Naming, global delivery, and local target selection operate at different timescales and protocols. Separate services let each layer scale and fail independently, but engineers must preserve the contracts between them.

### When should I use it?

Use this model when publishing an AWS endpoint, choosing an ELB family, defining DNS failover, adding CloudFront, changing certificates, designing cache behavior, or investigating an external request failure.

### When should I avoid it?

Avoid adding a layer without a measured need and an operational owner. A CDN, DNS policy, or load balancer can add valuable control, but also creates configuration, logs, cost, and another failure boundary.

### How does this make me a better engineer?

It teaches you to trace who chose an endpoint or representation, what evidence informed the choice, how long it remains valid, and which failure behavior users actually observe.

### How does this reduce waste?

It reduces origin load, repeated transfers, idle overprovisioning, misdirected debugging, unnecessary cache fragmentation, broad invalidations, sticky snowflakes, and outages caused by hidden plaintext or origin bypass.

## Handbook Principle #96

> Reliable delivery begins when every name, cache key, TLS leg, health signal, and target choice has one explicit owner and one tested failure contract.

## Practical Observation

Choose one production URL and trace it without changing anything. Resolve it through two public resolvers, identify the authoritative record and TTL, determine the matching CloudFront behavior and cache key, follow the origin TLS connection to its listener and target group, and locate one request in every available log. Then rehearse what each layer does when every downstream target is unhealthy. Any step that relies on “AWS figures it out” is an undocumented operating boundary.

## Looking Ahead

Delivery paths move bytes, but they do not define the bytes' durable ownership or lifecycle. Chapter 97 treats S3 as an object store with explicit keys, authorization, version recovery, encryption, storage transitions, replication, events, and public-access boundaries.

## References

- [Elastic Load Balancing — How Elastic Load Balancing works](https://docs.aws.amazon.com/elasticloadbalancing/latest/userguide/how-elastic-load-balancing-works.html)
- [Elastic Load Balancing — Load-balancer families](https://docs.aws.amazon.com/elasticloadbalancing/latest/userguide/what-is-load-balancing.html)
- [Elastic Load Balancing — Network Load Balancers](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/introduction.html)
- [Elastic Load Balancing — Gateway Load Balancers](https://docs.aws.amazon.com/elasticloadbalancing/latest/gateway/introduction.html)
- [Application Load Balancer — Listeners](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-listeners.html)
- [Application Load Balancer — Target groups](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-target-groups.html)
- [Application Load Balancer — Target-group health checks](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/target-group-health-checks.html)
- [Application Load Balancer — HTTP and forwarded headers](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/x-forwarded-headers.html)
- [Route 53 — Routing traffic to an ELB load balancer](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-to-elb-load-balancer.html)
- [Route 53 — Choosing a routing policy](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy.html)
- [Route 53 — How health checks influence record selection](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/health-checks-how-route-53-chooses-records.html)
- [CloudFront — Control the cache key with a policy](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/controlling-the-cache-key.html)
- [CloudFront — Understand cache policy TTLs](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/cache-key-understand-cache-policy.html)
- [CloudFront — Control origin requests with a policy](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/controlling-origin-requests.html)
- [CloudFront — Manage content expiration](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Expiration.html)
- [CloudFront — Request and response behavior for custom origins](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/RequestAndResponseBehaviorCustomOrigin.html)
- [CloudFront — Restrict access to an Amazon S3 origin](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html)
- [CloudFront — Invalidate files](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Invalidation.html)
