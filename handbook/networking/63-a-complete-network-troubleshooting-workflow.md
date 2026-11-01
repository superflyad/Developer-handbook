# Chapter 63 — A Complete Network Troubleshooting Workflow

Network troubleshooting is the disciplined reduction of uncertainty across a path. It begins with one observable failure, uses the least invasive evidence that can separate competing explanations, and stops when ownership and the next action are clear.

The central idea is:

> Find the highest layer already proven to work, test the next unproven boundary, and preserve enough context for another engineer to reproduce the reasoning.

## 1. Turn the report into a testable symptom

“The network is down” is not a test condition. Rewrite the report with six fields:

- **actor:** user, process, host, network, or region experiencing the problem;
- **action:** exact operation, method, protocol, destination name, and port;
- **expected:** observable result and normal timing;
- **actual:** error, status, timeout, wrong data, or performance symptom;
- **time:** first and last occurrence with timezone and clock source;
- **scope:** affected and unaffected clients, destinations, paths, and accounts.

Add the last known success and relevant changes without assuming a change caused the failure. Preserve the original error text and request or correlation identifier. A screenshot without time, destination, and reproduction steps is weak evidence.

One precise statement might be:

> From workstation A on office Wi-Fi, `GET https://api.example.test/health` returned HTTP 503 through gateway G at 14:07 UTC; the same request from workload B returned 200, and TLS validation succeeded in both cases.

That statement already places the failure above basic connectivity and client-side TLS validation for the failing path.

## 2. Separate observation from inference

Record raw facts before interpretation:

```text
Observation: TCP connection to 192.0.2.40:443 completed in 42 ms.
Inference: A TCP listener or intermediary accepted the connection at that tuple.
Not proven: The application is healthy or the intended backend handled it.
```

Use one working hypothesis at a time and name a competing explanation. Select the next observation by how well it distinguishes them, not by how familiar the command is.

Avoid changing DNS, routes, firewall rules, certificates, or service state during evidence collection. A change can erase the condition and create a second incident. If mitigation becomes necessary, record its exact time, owner, expected effect, rollback, and observed result.

## 3. Start where the evidence places you

The stack is a responsibility map, not a ritual that always starts at the cable:

```text
application semantics        HTTP status, SSH result, protocol error
security and identity        TLS name, chain, handshake, authentication
transport and endpoint       TCP/UDP tuple, listener, state, timeout
name and path                DNS answer, source selection, route, middleboxes
host and link                interface, address, gateway, neighbor, frames
```

An HTTP response proves that some lower-layer path carried an HTTP exchange. A TLS certificate error proves name resolution and transport progressed far enough to meet a TLS endpoint. A local “connection refused” after an immediate reset differs from a silent SYN timeout.

Begin at the highest useful evidence and cross the adjacent boundary it does not explain. [Chapter 50](50-a-packets-journey-through-the-network-stack.md) defines these protocol responsibilities.

## 4. Verify the process and endpoint first

On the client, identify the actual process, destination name, address family, proxy settings, and local source context. On the server side, verify that the intended process owns the expected socket and bind scope.

| Question | Linux | macOS | Windows PowerShell |
| --- | --- | --- | --- |
| What owns the socket? | `ss -ltnp` | `lsof -nP -iTCP -sTCP:LISTEN` | `Get-NetTCPConnection -State Listen` |
| What connection exists? | `ss -tanp` | `netstat -anv -p tcp` | `Get-NetTCPConnection` |
| What process owns the PID? | `ps -p PID -o pid,user,args` | `ps -p PID -o pid,user,args` | `Get-Process -Id PID` |

A service bound only to loopback cannot accept traffic arriving on an external interface. A wildcard listener can still be unreachable because of routing or policy. A container or proxy listener can own the host port while the application listens elsewhere.

Do not start a second listener to “test” a production port. Read the existing state and service logs. [Chapter 56](56-sockets-ports-and-endpoint-ownership.md) explains tuple and ownership boundaries.

## 5. Establish the host's source and route decision

Record active interface state, source address, prefix, gateway, and the route selected for the exact destination. The default route is irrelevant when a more specific route wins.

| System | Read-only route selection |
| --- | --- |
| Linux | `ip route get 192.0.2.40` |
| macOS | `route -n get 192.0.2.40` |
| Windows | `Test-NetConnection 192.0.2.40 -DiagnoseRouting -InformationLevel Detailed` |

For a directly connected next hop, inspect neighbor state only after confirming the route chooses that link. For Wi-Fi, verify association and local link conditions without assuming signal quality explains an application error.

VPNs, virtual adapters, policy routing, containers, and multiple address families can change source selection. Capture the route decision while the failure exists; a later snapshot after roaming is not equivalent.

## 6. Compare name resolution without discarding the name

Record the exact queried name, answer type, returned addresses, resolver used, TTL, search behavior, and failure category. Compare the affected client with a known-working client and, when authorized, the intended recursive resolver.

```text
Linux/macOS: dig api.example.test A
Windows:     Resolve-DnsName api.example.test -Type A
```

An address difference can be intentional due to geography, split-horizon policy, or service discovery. A matching answer does not prove the application at that address is correct.

To test one address while preserving HTTP host and TLS service identity, use an application-aware override such as:

```text
curl --resolve api.example.test:443:192.0.2.40 https://api.example.test/health
```

This changes the connection address for that invocation while retaining the URL name for TLS and HTTP. Editing a global hosts file or using the raw IP can change identity behavior and contaminate later tests. [Chapter 55](55-dns-and-name-resolution.md) provides the full resolver model.

## 7. Test the exact transport, not generic reachability

ICMP echo can establish one form of IP reachability when permitted. Its failure does not prove that TCP or UDP service traffic is blocked, and its success does not prove that a service port is open.

Use the exact destination address, protocol, and port:

```text
Linux/macOS: nc -vz -w 3 192.0.2.40 443
Windows:     Test-NetConnection 192.0.2.40 -Port 443 -InformationLevel Detailed
```

Interpret the result narrowly:

- a completed TCP handshake proves an accepting transport endpoint on that path;
- an immediate reset proves a reachable component rejected or aborted the connection;
- a timeout is ambiguous among loss, filtering, no return path, overload, and endpoint behavior;
- a UDP send without a response proves almost nothing about a listener.

Do not scan address or port ranges. One authorized tuple tied to the reported service is sufficient. Chapters [57](57-udp-datagrams-and-message-boundaries.md) and [58](58-tcp-reliability-flow-control-and-connection-state.md) define the transport evidence.

## 8. Treat path tracing as partial testimony

Traceroute-style tools manipulate hop limits and report control messages returned by some routers. Missing hops can reflect filtering, rate limiting, asymmetric paths, or devices that forward traffic without responding. A visible hop is an observation point, not proof that the next hop caused the failure.

Compare traces only when source, destination address, protocol mode, time, and network context are equivalent. The forward and return paths can differ. Load balancing can also produce different hop sequences across probes.

Use path tracing to locate a divergence worth investigating, not to declare the last responding router guilty. Cloud overlays can hide physical hops entirely; provider flow logs and route analysis may be more relevant.

## 9. Carry the test through TLS and the application

Once transport succeeds, use the real service name and protocol:

```text
curl --verbose --head --connect-timeout 3 --max-time 10 https://api.example.test/
```

Record name lookup, selected address, proxy use, transport timing, TLS version, certificate validation result, negotiated application protocol, HTTP status, relevant response fields, and bounded sanitized content.

Do not use `--insecure` to make TLS errors disappear. Determine whether the failure is path construction, expiry, service-name matching, client time, or the wrong TLS termination point. [Chapter 60](60-tls-certificates-and-public-key-trust.md) supplies that trust workflow.

For HTTP, distinguish origin responses from gateway-generated responses and preserve request method, effective URI, redirects, and correlation identifiers. A `503` may come from an application, proxy, or load balancer. [Chapter 59](59-http-semantics-and-api-behavior.md) explains the response semantics.

Verbose traces can contain authorization, cookies, query data, and internal names. Redact secrets without deleting the fields and timing needed for analysis.

## 10. Map every intermediary and transformation

Draw the path as deployed, including host firewalls, egress controls, NAT, VPNs, forward proxies, edge filters, load balancers, reverse proxies, backend policy, and service listeners.

For each component record:

- inbound and outbound tuple;
- original and translated source identity;
- TLS termination or pass-through behavior;
- policy attachment and owner;
- state or mapping lifetime;
- health-check source and criteria;
- logs, counters, and timestamps available.

Cloud security controls can be attached to an interface, workload, subnet, gateway, or managed service. Verify attachment and route tables as well as rule text. A rule cannot explain traffic that never traversed its component.

Correlate evidence across the transformation. The client tuple before NAT, the public tuple at an edge, and the proxy-to-backend tuple are three observations of one transaction only when mapping, time, or request identifiers connect them. [Chapter 62](62-firewalls-nat-proxies-and-traffic-distribution.md) supplies the intermediary model.

## 11. Use a working control as a differential experiment

A successful comparison reduces variables when it differs in only one meaningful dimension. Useful pairs include:

- same client and name, different address returned by DNS;
- same address and protocol, affected and unaffected source networks;
- same gateway, healthy and unhealthy backend;
- same request, current and last-known-good deployment;
- same host, IPv4 and IPv6 paths.

Create a comparison matrix before testing. If five dimensions change at once, a success identifies no cause. Preserve version, configuration, identity, and time so “same request” genuinely means the same protocol contract.

Do not send state-changing requests merely to produce a control. Prefer documented health endpoints, `HEAD` or safe `GET` where appropriate, and isolated test data.

## 12. Capture packets only with a boundary and purpose

Packet capture is appropriate when a specific remaining hypothesis depends on packets at a known observation point—for example, whether a SYN leaves an interface, whether a reply returns, or which endpoint sent a reset.

Before capture, define:

- written authorization and interface;
- exact tuple and capture filter;
- start condition, duration, and size limit;
- whether payload is necessary;
- storage, access, redaction, retention, and deletion;
- clock synchronization and a controlled reproduction.

Capture filters reduce what is collected; display filters only change what is shown after collection. A capture at one host proves what that observation point saw, not what every device on the path saw.

Prefer header-only or metadata evidence when payload is unnecessary. Never perform an open-ended production capture because earlier steps were skipped.

## 13. Build one causal claim

A good conclusion connects mechanism to evidence and rules out the closest alternative:

```text
Claim: backend B is omitted because its readiness check returns 503.
Evidence: edge logs select A and C only; direct authorized check from the
checker network returns 503 from B with request ID 8f2; B's application log
shows dependency initialization incomplete at the same time.
Alternative ruled out: edge-to-B TCP and TLS both complete successfully.
Next action: application owner repairs B readiness dependency; no firewall
change is indicated.
```

“It is DNS” or “the firewall blocked it” is not a causal claim until the exact record, rule, component, tuple, time, and decision are identified.

Stop diagnostics when the responsible boundary and next safe action are supported. Further probing can add risk without changing ownership.

## 14. Hand off a reproducible evidence package

The handoff should contain:

- one-sentence symptom and impact;
- start, end, timezone, and clock confidence;
- affected and unaffected scope;
- exact source, destination name, addresses, protocol, and port;
- sanitized commands and raw results;
- path and transformation diagram;
- timeline of observations and changes;
- supported hypothesis and competing explanations;
- owner, requested action, and rollback boundary;
- location and retention of sensitive artifacts.

Separate facts, inference, and proposed repair. Hash large immutable artifacts when chain of custody matters. Never attach credentials, private keys, unrestricted packet captures, or customer payload simply because the ticket system is convenient.

## Common Misconceptions

- “Always troubleshoot bottom-up.” Start at the highest layer the evidence reaches and test the adjacent unproven boundary.
- “Ping proves the network.” It tests one control exchange, not a service contract.
- “Traceroute shows the route.” It shows replies to selected probes from one direction and time.
- “A successful port test proves the application.” It proves transport establishment, not protocol health.
- “Packet capture is definitive.” It is definitive only about packets visible at its observation point and scope.

## Core Computer Science Concept

Network troubleshooting is **sequential hypothesis testing across layered contracts**. Every observation updates which guarantees are established, which remain uncertain, and which narrow experiment carries the most information with the least risk.

## Engineering Connections

- Process ownership links application symptoms to the actual socket and security context.
- DNS, routing, and NAT can each change the address a later component observes.
- TLS and HTTP errors prove substantial lower-layer progress and move ownership upward.
- Timelines, correlation identifiers, and controlled comparisons turn distributed logs into one causal narrative.

## From the Field

Users in one office report intermittent HTTPS timeouts. DNS answers and TLS are healthy when requests connect. Route selection shows the affected clients prefer IPv6; a controlled comparison succeeds over IPv4 and times out over IPv6. Edge logs contain no matching IPv6 attempts, while the office gateway shows the IPv6 route pointing to a retired tunnel. The narrow repair is the stale IPv6 route—not DNS flushing, certificate replacement, or a broad firewall exception.

## Engineering Review

### What problem does this solve?

It turns ambiguous end-to-end failures into evidence that identifies a protocol boundary, responsible component, and next safe action.

### Why was it designed this way?

Distributed paths expose only partial local observations, so disciplined comparisons and layered guarantees are more reliable than broad trial-and-error changes.

### When should I use it?

Use this workflow for connectivity, latency, name resolution, transport, TLS, proxy, and application-protocol symptoms across local and cloud paths.

### When should I avoid it?

Do not use production probing or capture beyond authorization, and do not continue network diagnostics after evidence clearly assigns an application or identity failure.

### How does this make me a better engineer?

It teaches you to convert symptoms into falsifiable hypotheses and communicate exactly what each observation proves.

### How does this reduce waste?

It prevents random restarts, cache flushing, firewall widening, duplicate captures, and handoffs that force the next team to repeat discovery.

## Handbook Principle #63

> Prove the highest working boundary, test the next unknown with the narrowest safe observation, and hand off the complete evidence chain.

## Practical Observation

Choose an authorized read-only request to a documentation or lab service. Write the six-field symptom, inspect endpoint ownership where available, record DNS and route selection, test the exact port, and inspect TLS and HTTP. Stop as soon as every layer needed for the successful request is evidenced. Produce a sanitized handoff that distinguishes observations from inferences; do not change system or network state.

## Looking Ahead

Part V replaced “the network” with explicit protocols, endpoints, paths, and evidence. Part VI begins by deciding which stable, understood manual workflows deserve automation—and which still require human judgment.

## References

- [Microsoft `Test-NetConnection` documentation](https://learn.microsoft.com/powershell/module/nettcpip/test-netconnection)
- [Linux `ip-route(8)` manual](https://man7.org/linux/man-pages/man8/ip-route.8.html)
- [curl command-line manual](https://curl.se/docs/manpage.html)
- [Wireshark User's Guide](https://www.wireshark.org/docs/wsug_html_chunked/)
- [Wireshark capture-filter reference](https://wiki.wireshark.org/CaptureFilters)
