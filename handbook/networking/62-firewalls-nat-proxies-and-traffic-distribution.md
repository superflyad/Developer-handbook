# Chapter 62 — Firewalls, NAT, Proxies, and Traffic Distribution

Network paths often contain components that filter packets, translate endpoints, terminate protocols, or choose backends. These functions can share one appliance or service, but they make different decisions from different evidence.

The central idea is:

> Diagnose every intermediary by its exact function, policy inputs, state, and ownership instead of naming the whole path “the firewall.”

## 1. Draw the policy path

A client-to-service path might be:

```text
client -> host firewall -> egress gateway/NAT -> edge firewall
       -> load balancer/TLS proxy -> service firewall -> application
```

Return traffic can traverse the same components in reverse, a different route, or another redundant device with synchronized state. Each hop can have a distinct source address, destination address, port, protocol, identity, and encryption context.

Start with a time-bounded flow tuple and expected outcome. Record both sides of each transformation. A rule that appears correct for the original client tuple may never see that tuple after translation or proxying.

## 2. Stateless filters evaluate packets

A stateless filter decides from fields available in each packet and fixed context, such as source and destination prefixes, protocol, ports, interface, and direction. It does not infer that a packet belongs to an earlier allowed exchange unless rules explicitly permit the reverse traffic.

Rules are commonly ordered, and an earlier match can prevent a later rule from applying. A final default deny is useful only when required traffic, including control traffic such as selected ICMP and IPv6 Neighbor Discovery, is deliberately allowed.

Stateless policy is predictable and distributable, but bidirectional protocols require rules for each direction. Fragmentation can complicate decisions because later fragments do not carry the original transport header.

## 3. Stateful filters track flows

A stateful firewall records observed connection or flow state. An outbound TCP connection allowed by policy can create state that permits matching replies without a separate broad inbound rule. UDP state is inferred from tuples and timers because UDP has no handshake or close.

State entries consume finite resources and expire. Asymmetric routing can send the reply through a device that never saw the opening traffic. Failover can lose state unless devices synchronize it. A packet can therefore match a static rule yet be rejected because its expected state is absent or invalid.

“Stateful” does not mean application-aware. A transport flow can be allowed while its HTTP request is denied later by a reverse proxy or application policy.

## 4. Ingress and egress are viewpoints

Ingress policy controls traffic entering a boundary; egress policy controls traffic leaving it. The same packet is egress from one component and ingress to the next.

Host, subnet, workload, and organizational boundaries can all enforce policy. An outbound connection can pass the source host firewall but fail an egress gateway allowlist. A service can accept traffic at a public load balancer while its backend security policy rejects the load balancer's source identity.

Write policy intent in both directions: who may initiate, toward which destination and port, what reply behavior is expected, and which component owns the decision.

## 5. NAT translates endpoint identity

Basic NAT maps IP addresses. Network address and port translation (NAPT) can map many internal address-and-port pairs onto one external address with distinct ports. A state table reverses the mapping for replies.

```text
10.0.1.8:53124 -> NAT -> 203.0.113.7:41002 -> service:443
```

The service observes the translated source unless a higher-layer proxy supplies another identity. Mapping lifetimes, endpoint dependence, hairpin behavior, and port availability vary by implementation and protocol.

NAT is not a firewall or an authentication system. Translation can incidentally prevent unsolicited inbound traffic when no mapping exists, but explicit forwarding can create one and policy can still allow or deny traffic independently. IPv6 does not require address translation to enforce ingress policy.

Inbound destination translation or port forwarding maps a public endpoint to an internal one. Document both endpoints; operators otherwise inspect the public port while the backend is listening on another address or port.

## 6. Forward proxies act for clients

A forward proxy accepts requests from clients and makes onward connections under proxy policy. Clients may configure it explicitly, discover it, or be redirected transparently by the network.

For HTTP, the proxy can enforce destination policy, authenticate users, cache responses, and log requests. HTTPS can pass through an HTTP `CONNECT` tunnel, leaving application encryption end to end through the proxy, or be intercepted by an authorized TLS inspection system that terminates and re-establishes TLS under an installed trust authority.

TLS inspection creates two channels, exposes plaintext at the proxy, and changes the certificate issuer observed by clients. It requires explicit organizational authority, protected keys, privacy controls, exclusions, and a clear failure model.

## 7. Reverse proxies act for services

A reverse proxy receives traffic for an origin service and forwards selected requests to backends. It can terminate TLS, normalize HTTP, authenticate requests, apply limits, cache content, and hide backend topology.

The backend's peer is then the proxy. Any original client identity carried in `Forwarded`, `X-Forwarded-For`, or a transport metadata protocol is trustworthy only when:

- untrusted clients cannot directly reach the backend;
- the trusted proxy removes or overwrites spoofed values;
- the backend accepts identity metadata only from known proxy hops;
- the hop order and parsing rules are defined.

A client-supplied `X-Forwarded-For` string is not proof of client address. Source address is also not a durable user identity.

## 8. Load balancers select a destination

A layer-4 load balancer distributes transport flows using tuple and health information without interpreting the complete application protocol. A layer-7 load balancer or reverse proxy can route by host, path, method, header, or other application data after terminating that protocol.

Selection strategies include round robin, least connections, hashing, and weighted choices. Session persistence can keep related requests on one backend but can create uneven load and hide state that belongs in a shared service.

Connection reuse changes what is balanced. Thousands of HTTP requests can traverse one long-lived upstream connection, while one user action can create several flows. Measure both connections and application work.

## 9. Health checks are narrow observations

A TCP health check proves that a handshake completed at one endpoint. An HTTP check can validate a status and bounded response. Neither proves every dependency or business operation works.

Checks that are too shallow route traffic to broken backends. Checks that include every dependency can remove all backends during one shared dependency failure and amplify an outage. Design readiness around whether this instance can safely accept work, with bounded cost and explicit failure thresholds.

Different components may check different endpoints on different schedules. Record the checker source, destination, interval, timeout, success criteria, and removal and recovery thresholds before explaining why a backend was selected.

## 10. Cloud controls overlap without being identical

Cloud security groups, network ACLs, route tables, managed firewalls, gateways, and load balancers can all affect a flow. Their statefulness, rule order, attachment point, identity model, and default behavior are provider-specific.

Inventory attachments as well as rules. A correct security group attached to the wrong interface has no effect; a subnet ACL can deny traffic that an instance group allows; a missing return route can resemble a filter drop.

Use read-only policy simulation, flow logs, and configuration views when available. Logs show what a component observed under its logging policy, not every packet that existed.

## 11. Locate the deciding component

Classify evidence by layer and viewpoint:

| Observation | Likely next owner to inspect |
| --- | --- |
| No route or neighbor resolution | Host/link/routing configuration |
| TCP SYN retransmits with no reply | Path, destination listener, filter, or return route |
| Immediate TCP reset | Reached endpoint or intermediary rejecting the connection |
| TLS identity or trust failure | TLS termination, certificate, name, or trust policy |
| HTTP proxy status such as `407` | Forward-proxy authentication or configuration |
| Gateway `502` or `503` | Reverse proxy, upstream selection, health, or backend |
| One backend fails while others work | Load-balancer selection or backend-specific state |

These are starting hypotheses, not universal proofs. Correlate timestamps and the tuple as seen at adjacent components. A capture before NAT and a log after NAT need a mapping record to describe the same flow.

Read-only host observations include `Get-NetFirewallProfile` and `Get-NetFirewallRule` on Windows, `nft list ruleset` on Linux when authorized, and `pfctl -sr` on systems using PF when authorized. Cloud configuration and flow logs require equally careful access and redaction.

Do not disable a firewall, widen a production rule, bypass a proxy, or scan address ranges merely to test a hypothesis. A narrow authorized connection test and logs from the component that owns the decision produce safer evidence.

## Common Misconceptions

- “NAT is a security boundary.” Translation and filtering are separate functions.
- “An allowed security group means the path is allowed.” Other attached controls and routes still apply.
- “A 503 proves the application generated it.” A reverse proxy or load balancer can originate it.
- “The backend sees the client address.” A proxy or translation can replace it.
- “A passing health check means the service works.” It proves only the check's bounded condition.

## Core Computer Science Concept

Network intermediaries are **composed state machines with transformed identities**. Each component observes a local representation of the flow, applies policy, may create state or rewrite fields, and passes a new representation downstream.

## Engineering Connections

- Socket ownership identifies the listener before any firewall theory is useful.
- NAT state and stateful filtering depend on the transport lifecycles described in Chapters 57 and 58.
- TLS termination creates separate certificate and encryption boundaries at reverse proxies.
- HTTP status and forwarding fields must be interpreted according to the intermediary that generated them.

## From the Field

A backend allowlist contains customer public addresses, but traffic arrives through a reverse proxy whose addresses are not allowed. Operators repeatedly add customer ranges without effect. Mapping the path reveals that the backend policy sees the proxy as its peer; allowing only the controlled proxy tier and validating proxy-provided identity fixes the actual boundary.

## Engineering Review

### What problem does this solve?

These components enforce communication policy, conserve or translate address space, mediate protocols, and distribute work across service instances.

### Why was it designed this way?

Different layers expose different useful inputs: packets support broad filtering, connection state supports return traffic, and terminated application protocols support content-aware routing.

### When should I use it?

Use each function when its policy boundary, ownership, failure behavior, and observable evidence are explicit.

### When should I avoid it?

Avoid stacking undocumented translation and proxy layers or using source addresses and health checks as stronger identity and correctness proofs than they are.

### How does this make me a better engineer?

It lets you identify which component saw which tuple and made which decision instead of changing unrelated controls.

### How does this reduce waste?

It prevents rule sprawl, unsafe bypasses, spoofed client identity, misleading health signals, and hours spent debugging a component outside the flow.

## Handbook Principle #62

> For every intermediary, name what it sees, what it changes, what state it keeps, and which policy owner can explain its decision.

## Practical Observation

Choose one authorized service path and draw each known filter, NAT, proxy, and load balancer. For every hop, record the inbound and outbound tuple, TLS endpoint, client-identity source, health check, and policy owner. Mark unknowns rather than guessing, then select one read-only observation that could resolve the first unknown.

## Looking Ahead

The networking chapters have built evidence at every layer. Chapter 63 combines them into a complete, safe troubleshooting workflow from symptom definition through handoff.

## References

- [RFC 3022 — Traditional IP Network Address Translator](https://www.rfc-editor.org/rfc/rfc3022)
- [RFC 4787 — NAT Behavioral Requirements for Unicast UDP](https://www.rfc-editor.org/rfc/rfc4787)
- [RFC 7239 — Forwarded HTTP Extension](https://www.rfc-editor.org/rfc/rfc7239)
- [RFC 9110 — HTTP Semantics: Intermediaries](https://www.rfc-editor.org/rfc/rfc9110)
- [NIST SP 800-41 Rev. 1 — Guidelines on Firewalls and Firewall Policy](https://csrc.nist.gov/pubs/sp/800/41/r1/final)
