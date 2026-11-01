# Chapter 54 — Routing, Gateways, and Path Selection

Once a host knows a destination address, it must decide where to send the packet next. Hosts and routers make that decision from forwarding state, choosing the most specific applicable prefix before considering policy and preference among comparable paths.

The central idea is:

> Routing selects the next hop for one direction by matching the destination against the most specific known prefix.

## 1. Every IP sender performs route selection

Routing is not only a router's job. An end host chooses among local, connected, specific, and default routes before it can transmit a packet. A route commonly describes:

- a destination prefix;
- an outgoing interface;
- an on-link disposition or next-hop gateway;
- preference or metric information;
- optional source, table, protocol, lifetime, and policy metadata.

Conceptually:

```text
destination address
→ policy selects eligible routing state
→ longest matching prefix wins
→ preference chooses among comparable routes
→ next hop and interface selected
→ source address selected
→ local neighbor resolution
```

Actual ordering and fields differ by platform. Policy routing, virtual routing tables, multipath routes, VPNs, and application binding can add decisions that a simple route-table view does not show.

## 2. Longest-prefix match chooses specificity

Suppose a host has these routes:

```text
0.0.0.0/0          via 192.0.2.1
198.51.100.0/24    via 192.0.2.9
198.51.100.64/26   via 192.0.2.17
```

A packet for `198.51.100.70` matches all three prefixes. The `/26` route is most specific and wins. A packet for `198.51.100.200` matches `/24` and `/0`, so `/24` wins. The default `/0` matches every IPv4 destination but loses to any eligible more-specific route.

Metrics do not normally make a default route beat a matching specific route. They help choose among routes the platform regards as otherwise comparable. Exact preference rules depend on route source, administrative policy, address family, and operating system.

IPv6 uses the same prefix-specificity principle with 128-bit addresses. `::/0` is the IPv6 default route and is separate from IPv4 `0.0.0.0/0`.

## 3. Connected and local routes have distinct purposes

When an interface receives `192.0.2.20/24`, the operating system ordinarily installs connected knowledge for `192.0.2.0/24`. Destinations within that prefix are candidates for on-link neighbor resolution. It also knows that `192.0.2.20` is a local address to deliver internally.

The exact route tables can distinguish:

- addresses owned by the host;
- directly connected prefixes;
- broadcast or multicast handling;
- routes learned or configured through a gateway;
- unreachable, prohibited, blackhole, or throw behavior.

Do not interpret every table entry as “send to a router.” Some routes cause local delivery, direct-link resolution, explicit rejection, or table lookup continuation.

## 4. A gateway is a next hop, not the whole path

A route through `192.0.2.1` means the sender should deliver the local frame to that next-hop router. It does not reveal what that router will do afterward. Each router independently selects a route for the packet's destination.

The gateway ordinarily must itself be reachable through an interface and link, either because it is on-link or because the platform supports a deliberate recursive or special next-hop arrangement. A configured default gateway that cannot be resolved locally is not useful.

A default route does not guarantee internet access. The gateway can lack an onward route, filtering can deny traffic, NAT can be absent, or the destination can fail. It only supplies a candidate next hop when no more-specific route wins.

## 5. Source and destination selection interact

A multihomed host can have several addresses, interfaces, and default routes. The selected destination address family and route constrain candidate source addresses; source policy and application binding can in turn affect which path is viable.

An application listening only on loopback is not reachable through an external route. A client that binds a source address from the wrong interface can receive an immediate error or create asymmetric behavior. Dual-stack applications can receive multiple IPv4 and IPv6 destination addresses and use address-selection and connection-attempt algorithms beyond a single route lookup.

When troubleshooting, record both source and destination. “The route to the server” is incomplete if the host could originate from several addresses or namespaces.

## 6. Forwarding and routing state are separate

A system can contain routes without being authorized or configured to forward traffic between interfaces. End hosts need routes for their own packets; routers additionally accept eligible packets not addressed to themselves and forward them according to policy.

Forwarding depends on:

- operating-system forwarding state;
- ingress and egress filtering;
- hop limit or TTL;
- route and next-hop availability;
- namespace and virtual-router context;
- sometimes NAT or tunnel policy.

Enabling forwarding changes the host's security role and is not a harmless troubleshooting step. This chapter uses inspection only.

## 7. TTL and Hop Limit bound forwarding loops

IPv4's Time to Live field and IPv6's Hop Limit are decremented as routers forward packets. A router discards a packet when the value expires and ordinarily sends an ICMP Time Exceeded message under the protocol rules.

The field bounds a packet's lifetime during a routing loop; it is not a wall-clock timer. A persistent routing loop can still waste capacity by generating many short-lived packets.

Routing loops arise when devices have inconsistent next-hop beliefs. Symptoms can include repeated addresses in a trace, TTL expiration, elevated traffic, and failure only for certain prefixes. Correct the forwarding state rather than increasing TTL.

## 8. Traceroute reveals responses, not a complete path truth

Traceroute-style tools send probes with increasing TTL or Hop Limit. Each expiring hop may return ICMP Time Exceeded; the destination responds according to the probe method. Implementations use UDP, ICMP Echo, TCP, or selectable modes.

An output line means a response associated with a probe was observed. An asterisk can mean filtering, rate limiting, loss, an unresponsive router, or a return-path issue—not necessarily that forward traffic stopped there. Load balancing can show different addresses across probes, and the response path can differ from the probe path.

The final responding router is not proof of physical geography or organizational ownership. MPLS, tunnels, anycast, and private addresses can obscure or reshape the visible sequence.

Use traceroute as one experiment with a stated protocol and destination. Do not use high-rate probing or scan unauthorized networks.

## 9. Asymmetric routing can be valid or harmful

IP does not require request and response packets to traverse the same routers. Asymmetry is common in multihomed and provider networks. It becomes operationally important when:

- a stateful firewall sees only one direction;
- reverse-path checks reject unexpected sources;
- NAT state exists on only one path;
- measurements observe only one direction;
- bandwidth and latency differ materially.

One host's route table proves only its local forward decision. To reconstruct a round trip, gather evidence at both endpoints and relevant policy devices.

## 10. Inspect the route the system would use

Listing all routes is useful, but a destination-specific lookup is stronger evidence:

| Goal | Linux | macOS | Windows PowerShell |
| --- | --- | --- | --- |
| IPv4 routes | `ip route show` | `netstat -rn -f inet` | `Get-NetRoute -AddressFamily IPv4` |
| IPv6 routes | `ip -6 route show` | `netstat -rn -f inet6` | `Get-NetRoute -AddressFamily IPv6` |
| Lookup destination | `ip route get 198.51.100.70` | `route -n get 198.51.100.70` | Inspect sorted matching `Get-NetRoute` entries |
| Trace | `traceroute` or `tracepath` where installed | `traceroute` | `Test-NetConnection -TraceRoute` or `tracert` |

Windows route selection also considers interface and route metrics; `Find-NetRoute` may be available on supported systems for remote-address selection. Record the exact destination and source constraints rather than relying only on a printed table.

Route modifications can disconnect the current management session. Never add, delete, or flush routes merely to test a theory on a shared or remote host.

## 11. Diagnose a path in bounded steps

For one source, destination, and protocol:

1. Resolve the intended destination address and family.
2. Ask the operating system for its selected route, interface, gateway, and source.
3. Confirm the interface and next-hop neighbor are usable.
4. Observe whether the packet leaves and whether an error returns.
5. Inspect relevant policy at known boundaries.
6. Gather destination-side and return-path evidence.
7. Compare intended control-plane state with installed data-plane state.

Do not infer a route from DNS name alone. A name can yield several addresses with different routes and results.

## Common Misconceptions

- “The lowest metric always wins.” Prefix specificity and policy normally constrain the comparison first.
- “A default gateway means internet access.” It is only a least-specific next hop.
- “Traceroute displays every router in the path.” It displays responses to a particular probe sequence.
- “The return path is the reverse of the request.” Routing decisions are directional and can be asymmetric.

## Core Computer Science Concept

IP routing uses **hierarchical lookup with local decisions**. Longest-prefix match compresses forwarding state, while each router chooses only the next hop. Global behavior emerges from many independently maintained local tables.

## Engineering Connections

- Cloud route tables, transit gateways, VPNs, and container routes use the same destination-prefix reasoning.
- Service meshes and proxies add application paths that are not visible in the IP route table.
- Anycast advertises one prefix from multiple locations, so route policy influences which instance receives traffic.
- Network observability must cover both directions and the control/data-plane distinction.

## From the Field

A new VPN installs a broad route that overlaps an internal service prefix. DNS still returns the correct address, but longest-prefix selection now sends traffic into the tunnel. Lowering the default-route metric has no effect because the overlapping route is more specific. A destination-specific lookup reveals the actual winner and directs the correction to VPN route policy.

## Engineering Review

### What problem does this solve?

It selects a next hop for destinations beyond one directly connected link while keeping forwarding state aggregatable.

### Why was it designed this way?

Prefix hierarchy lets each router make a bounded local decision without knowing every endpoint or entire end-to-end path.

### When should I use it?

Use route reasoning for multihomed hosts, VPNs, cloud networks, asymmetric failures, gateway issues, and path changes.

### When should I avoid it?

Avoid treating a route table or traceroute as proof of the return path, application health, or every policy device.

### How does this make me a better engineer?

It makes path selection a predictable prefix-and-policy decision rather than a vague notion of network direction.

### How does this reduce waste?

It reveals the actual winning route before teams change metrics, gateways, DNS, or firewalls that cannot affect the decision.

## Handbook Principle #54

> Ask the operating system which route wins for the exact destination and source context, then investigate that next hop and the separate return path.

## Practical Observation

Choose one documentation address and one reachable service address. Use read-only tools to identify the selected prefix, interface, next hop, and source for each. Explain why the default route wins or loses. If you run a trace, state its probe protocol and treat missing responses as unknown rather than failed hops.

## Looking Ahead

Routes operate on addresses, while applications usually begin with names. Chapter 55 follows DNS through stub resolvers, caches, recursive service, delegation, and authoritative data.

## References

- [RFC 1812 — Requirements for IP Version 4 Routers](https://www.rfc-editor.org/rfc/rfc1812)
- [RFC 8200 — Internet Protocol, Version 6](https://www.rfc-editor.org/rfc/rfc8200)
- [RFC 6724 — Default Address Selection for IPv6](https://www.rfc-editor.org/rfc/rfc6724)
- [Linux `ip-route(8)`](https://man7.org/linux/man-pages/man8/ip-route.8.html)
- [Microsoft PowerShell: `Get-NetRoute`](https://learn.microsoft.com/en-us/powershell/module/nettcpip/get-netroute)
