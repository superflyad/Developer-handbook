# Chapter 55 — DNS and Name Resolution

Applications usually begin with a name, but the network routes to addresses. The Domain Name System (DNS) is a distributed, delegated database that maps names to typed data and caches answers across several layers. A lookup result is therefore evidence from a resolution path, not a permanent property of a hostname.

The central idea is:

> Trace a name through the application's resolver, local policy, recursive cache, delegation, and authoritative data—keeping the queried name, type, and time together.

## 1. DNS is a tree of names and delegated authority

DNS names are sequences of labels beneath the root. The fully qualified name `api.example.test.` ends with an explicit root label represented by the trailing dot. User interfaces commonly omit that final dot.

```text
.                       root
└── test.                top-level domain
    └── example.test.    delegated or managed domain
        └── api.example.test.
```

The example above is conceptual; `.test` is reserved for testing and is not ordinary public DNS data.

A **zone** is an administrative portion of the namespace served authoritatively. It is not necessarily the same as every domain beneath a name. A parent zone delegates a child by publishing name-server information; the child zone then owns its authoritative data.

The root does not store every host address. It directs resolvers toward delegated top-level-domain servers, which can direct them farther down the tree.

## 2. DNS stores typed resource-record sets

A query asks for a name, class, and record type. Common types include:

- `A` for IPv4 addresses;
- `AAAA` for IPv6 addresses;
- `NS` for authoritative name servers;
- `CNAME` for an alias to another canonical name;
- `MX` for mail-exchange targets;
- `TXT` for text used by many application conventions;
- `SRV` for service location under a defined naming scheme;
- `SOA` for zone authority and timing information.

Records with the same owner name, class, and type form an RRset. DNS can return several addresses; their order and the application's connection order can vary. One successful address does not prove every returned endpoint works.

A DNS name is not a URL. It has no scheme, path, or application port unless a particular record convention supplies related service data.

## 3. The application usually asks a stub resolver

Most applications call an operating-system or runtime name-resolution API. A local **stub resolver** sends the request to a recursive resolver or local proxy and may apply:

- a hosts file or another local naming source;
- search suffixes for short names;
- per-interface or VPN resolver selection;
- application or operating-system caches;
- IPv4/IPv6 destination ordering;
- enterprise filtering or split DNS.

An application can also embed its own resolver, use encrypted DNS, or query a selected server directly. Therefore, `dig` returning one answer does not prove the application asked the same server, used the same search name, requested the same type, or accepted the result.

Start by reproducing through the application's normal resolution API, then compare lower layers deliberately.

## 4. Recursive resolvers do work on the client's behalf

A recursive resolver can answer from cache. If it lacks usable cached data, it follows referrals conceptually from root toward the authoritative zone:

```text
stub → recursive resolver
          ├── root referral
          ├── top-level-domain referral
          └── authoritative answer
```

The recursive resolver validates message structure, follows aliases and delegations under protocol rules, caches eligible data, and returns a result or failure. Real resolvers use cached delegation information, forwarding, minimization, parallelism, and policy, so each lookup does not literally start at a root server.

A forwarder passes queries to another resolver rather than performing all iterative resolution itself. Enterprise and home networks often contain several forwarding layers.

## 5. Authority, recursion, and caching are separate roles

One server process can perform more than one role, but the concepts differ:

- an **authoritative server** answers from zone data it serves;
- a **recursive resolver** pursues resolution for a client;
- a **caching resolver** reuses prior results within their validity;
- a **forwarder** sends queries to another resolver;
- a **policy resolver** may block or rewrite selected answers.

The DNS header's Authoritative Answer flag describes the response's authority context; it does not mean the server is trusted by the application for every purpose. A response from a configured recursive resolver is normally non-authoritative even when it contains correctly cached authoritative data.

Do not expose an unrestricted recursive resolver to untrusted networks. Open recursion can be abused for amplification and resource consumption.

## 6. TTL controls cache reuse, not instant propagation

A resource record's TTL is the maximum interval it may be cached before the source should be consulted again. A recursive resolver returns the remaining TTL, which decreases while cached. Resolvers and applications may apply policy that shortens caching, and some applications cache independently.

When authoritative data changes, existing caches can continue serving the earlier RRset until its prior TTL expires. Lowering the TTL *after* a long-lived value was cached does not recall that cached copy. Planned migrations reduce TTL early enough for old cache entries to age out, then verify multiple resolver paths.

A TTL of zero discourages reuse beyond the current transaction but does not make an update globally atomic. Delegation, application, negative, and intermediate caches have their own data and timing.

## 7. Negative answers and failures are not one result

Important outcomes include:

- **NXDOMAIN:** the queried name does not exist under the response's semantics;
- **NODATA:** the name exists but has no record of the requested type;
- **SERVFAIL:** the server could not complete resolution, perhaps because of validation or upstream failure;
- **REFUSED:** the server declined the query under policy;
- timeout or transport failure: no useful DNS response arrived.

Negative answers can be cached using zone authority data. Modern requirements also allow or require bounded caching of several resolution failures to avoid retry storms. Repeated querying can therefore reproduce a cached failure after the authoritative problem is repaired.

Do not say “DNS says it does not exist” for every empty result. Preserve response code, query type, server, flags, and authority section.

## 8. Search domains can change the queried name

A short input such as `db` can be tried with one or more configured suffixes:

```text
db.corp.example.
db.dev.example.
db.
```

The exact order depends on resolver configuration, dot count, and platform policy. This creates ambiguity, extra queries, and security surprises when software moves between networks.

Use fully qualified names for service configuration when suffix expansion is not explicitly required. A trailing dot can force absolute DNS interpretation in DNS-aware tools, but application APIs and user interfaces do not all preserve it identically.

Split DNS can return different answers based on resolver, client network, identity, or view. Comparing a corporate resolver with a public resolver is useful only after acknowledging that they may intentionally serve different namespaces.

## 9. DNS transport is not DNS data authenticity

Classic DNS commonly uses UDP and falls back or switches to TCP when necessary; modern DNS also uses EDNS and encrypted transports such as DNS over TLS or HTTPS. Encryption protects the client-to-resolver channel from ordinary observation or modification on that segment. It does not prove the underlying zone data is correct or that the resolved application is trustworthy.

DNSSEC lets validating resolvers verify signatures and authenticated denial for signed portions of the DNS hierarchy. It provides origin authentication and integrity for DNS data, not confidentiality. Deployment gaps, unsigned zones, validation policy, and clock correctness affect what can be proven.

Applications still authenticate services with mechanisms such as TLS certificate validation or SSH host keys. A signed address record does not authorize the application operation.

## 10. Query the right layer

| Question | Linux | macOS | Windows PowerShell |
| --- | --- | --- | --- |
| Application-style resolution | `getent ahosts name` where available | `dscacheutil -q host -a name name` | `[Net.Dns]::GetHostAddresses('name')` |
| Resolver configuration | `resolvectl status` where applicable | `scutil --dns` | `Get-DnsClientServerAddress`; `Get-DnsClient` |
| Detailed DNS query | `dig name A` or `resolvectl query name` | `dig name A` | `Resolve-DnsName -Name name -Type A` |
| Local cache | implementation-specific | implementation-specific | `Get-DnsClientCache` |

`dig` may not be installed and generally bypasses parts of the operating-system application lookup path. `nslookup` is widely available but its interface and interpretation differ; prefer tools whose queried server, type, and flags are explicit.

For a comparison, query the configured resolver first. Querying an arbitrary public resolver can bypass corporate views, filtering, and private zones and may violate policy. Do not flush caches before recording their current contents and timestamps.

## 11. A bounded DNS investigation

For one failing application lookup:

1. Record the exact input name, application, host, time, and requested operation.
2. Determine the fully expanded query name and address families.
3. Reproduce through the application or system resolver API.
4. Identify the selected resolver and interface policy.
5. Query that resolver explicitly for relevant types and preserve codes, flags, TTLs, and sections.
6. Compare authoritative data only if necessary and authorized.
7. Inspect aliases and delegations without assuming the first difference is wrong.
8. Test resulting addresses separately through the application protocol.

Changing `/etc/hosts`, resolver settings, or production DNS to “test” a hypothesis changes the very path under investigation. Prefer an application-specific override in a disposable environment if a controlled alternate answer is required.

## Common Misconceptions

- “DNS maps a hostname to one IP.” It stores typed RRsets and can return several values or aliases.
- “The DNS server contains every answer.” Recursive resolvers follow delegation and reuse caches.
- “Changing a record updates everyone immediately.” Existing positive and negative cache entries retain their prior lifetimes.
- “A DNS answer proves the service is authentic.” Naming, transport security, and application authorization are separate.

## Core Computer Science Concept

DNS is a **delegated, eventually refreshed namespace**. Authority is partitioned down a tree, while caching trades immediate consistency for latency and scale. Every answer therefore has provenance and a lifetime.

## Engineering Connections

- Service discovery systems reuse naming, health, caching, and lifecycle ideas under different consistency models.
- CDNs and load balancers publish multiple or changing endpoints, making TTL and client behavior operational inputs.
- Kubernetes and cloud private DNS add resolver views tied to network and account boundaries.
- Incident timelines must include cached negative responses and application-level caches, not only authoritative changes.

## From the Field

An operator corrects an authoritative `A` record and verifies it directly, but one office still receives NXDOMAIN. Its recursive resolver cached the earlier negative answer using the zone's negative TTL. Repeated client retries cannot bypass that valid cached state. Comparing the configured resolver's response, remaining TTL, and authoritative response explains the delay without another DNS change.

## Engineering Review

### What problem does this solve?

It provides a scalable, delegated way to map hierarchical names to typed data without requiring every client to store the global namespace.

### Why was it designed this way?

Delegation distributes ownership, while recursive caching reduces latency and authoritative-server load.

### When should I use it?

Use this model for application lookup failures, migrations, split DNS, cache behavior, service discovery, and trust analysis.

### When should I avoid it?

Avoid using direct public-resolver queries as proof of an application's path or flushing caches before preserving evidence.

### How does this make me a better engineer?

It turns “DNS is broken” into a traceable query with type, resolver, authority, response, cache, and lifetime.

### How does this reduce waste?

It prevents repeated record edits and cache flushing when the observed difference is expected delegation, view, or TTL behavior.

## Handbook Principle #55

> A DNS result is a typed, timed answer from a specific resolution path—not a timeless property of a name.

## Practical Observation

Choose a public documentation domain that is safe to query. Resolve it through the operating-system API and the configured recursive resolver, recording type, server, response code, addresses, aliases, and TTL where available. Repeat once and explain which layer could have cached the result. Do not flush caches or query private names through public resolvers.

## Looking Ahead

DNS produces candidate addresses, but a process still needs a socket endpoint. Chapter 56 connects addresses, ports, protocols, bind/listen/connect state, and process ownership.

## References

- [RFC 1034 — Domain Names: Concepts and Facilities](https://www.rfc-editor.org/rfc/rfc1034)
- [RFC 1035 — Domain Names: Implementation and Specification](https://www.rfc-editor.org/rfc/rfc1035)
- [RFC 9499 — DNS Terminology](https://www.rfc-editor.org/rfc/rfc9499)
- [RFC 2308 — Negative Caching of DNS Queries](https://www.rfc-editor.org/rfc/rfc2308)
- [RFC 9520 — Negative Caching of DNS Resolution Failures](https://www.rfc-editor.org/rfc/rfc9520)
