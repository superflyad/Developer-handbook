# Chapter 52 — IP Addressing and Subnetting

An IP address identifies an interface within an addressing scope. A prefix says which leading bits describe a network. Together they let a host decide whether a destination is directly reachable and let routers aggregate many destinations into manageable forwarding entries.

The central idea is:

> Subnetting is prefix-bit reasoning: addresses share a network when the configured leading bits match.

## 1. Addresses identify interfaces, not people or machines forever

A host can have several interfaces, each with several IPv4 or IPv6 addresses. Addresses can be temporary, reassigned, translated, shared, or scoped to one link. Containers and virtual machines add more interfaces without adding physical computers.

An address is therefore routing and endpoint information, not durable identity. Authentication should use cryptographic or application identity rather than assuming an IP address permanently names a trustworthy actor.

Always record an address with context:

- address family and prefix length;
- interface and namespace;
- assignment source and lifetime;
- relevant scope;
- observation time.

## 2. Prefix notation replaces classful thinking

IPv4 addresses contain 32 bits; IPv6 addresses contain 128. CIDR notation appends the number of leading prefix bits:

```text
192.0.2.134/26
2001:db8:1234:5678::25/64
```

The first address has 26 network-prefix bits and 6 remaining bits. The second has a 64-bit prefix and 64 remaining interface-identifier bits. Prefix lengths are routing boundaries, not a statement that every remaining value is assignable to an ordinary host.

Historic IPv4 classes A, B, and C are not the modern allocation or routing model. Avoid calling `/24` a “Class C network.” CIDR permits prefixes at arbitrary bit lengths and supports route aggregation.

## 3. IPv4 masks are another prefix representation

An IPv4 subnet mask has contiguous one bits for the prefix followed by zero bits. `/26` corresponds to:

```text
11111111.11111111.11111111.11000000
255.255.255.192
```

To find the network prefix, conceptually apply a bitwise AND between the address and mask:

```text
address: 192.0.2.134  → last octet 10000110
mask:    255.255.255.192 → last octet 11000000
network: 192.0.2.128  → last octet 10000000
```

The final six bits vary from binary `000000` through `111111`, so the block spans `192.0.2.128` through `192.0.2.191`. On a conventional IPv4 multiaccess subnet, the all-zero host portion names the network and the all-one portion is the directed broadcast, leaving `.129` through `.190` for ordinary assignments.

That “subtract two” shortcut is not universal. `/31` is standardized for point-to-point links, and `/32` names one IPv4 address. Always use the semantics of the actual link and platform.

## 4. Block size gives a fast IPv4 check

When a prefix ends within one octet, subtract the mask octet from 256 to get the block size. For `/26`, the last mask octet is 192:

```text
256 - 192 = 64
```

Subnet boundaries in that octet occur at 0, 64, 128, and 192. The address `.134` lies in the 128–191 block. This shortcut is useful, but binary reasoning remains the source of truth when a prefix is unfamiliar.

The number of values in an IPv4 prefix is `2^(32-prefix length)`. That is the address-block size, not necessarily the count of deployable hosts after reservations and policy.

## 5. Prefixes enable aggregation

Routers need not carry a separate route for every host. A route for `192.0.2.0/24` covers all addresses whose first 24 bits match. A more specific route such as `192.0.2.128/26` covers a subset.

Aggregation works only when address allocation is sufficiently contiguous and the aggregate has a valid route to all covered destinations. Advertising an aggregate without reachability to every included subnet can create a black hole.

Chapter 54 explains how a router chooses among overlapping prefixes. For now, remember that a shorter prefix covers more addresses and a longer prefix is more specific.

## 6. IPv6 notation compresses zeros, not meaning

IPv6 writes 128 bits as eight hexadecimal groups. Leading zeros within a group can be omitted, and one longest run of all-zero groups can be compressed with `::`:

```text
2001:0db8:1234:0000:0000:0000:0000:0025
2001:db8:1234::25
```

Only one `::` can appear because otherwise the number of omitted groups would be ambiguous. Expand an address to eight groups before doing unfamiliar prefix calculations.

Each hexadecimal digit represents four bits. IPv6 prefixes ending on a four-bit boundary are therefore easy to compare by hex digits. `/64` fixes the first 16 hex digits; `/56` fixes the first 14.

IPv6 has no broadcast address. Multicast and Neighbor Discovery handle roles that IPv4 often associates with broadcast. Do not import IPv4 network/broadcast subtraction rules into IPv6.

## 7. Scope is part of IPv6 interpretation

Important IPv6 categories include:

- loopback `::1/128` for the local host;
- unspecified `::/128`, which is not a normal destination;
- link-local `fe80::/10`, valid on a particular link;
- unique local `fc00::/7`, with locally assigned addresses conventionally drawn from `fd00::/8`;
- global unicast space, subject to current allocation registries;
- multicast `ff00::/8`, with scope encoded in the address.

A link-local destination can be ambiguous on a multihomed host, so APIs and tools may require an interface zone such as `%eth0` or a numeric interface index. The zone is local context, not part of the 128-bit address carried end to end.

IPv6 subnets commonly use `/64` for ordinary LANs because several protocol mechanisms assume that size. That is a strong operational convention, not proof that every IPv6 route, point-to-point link, or delegation must be `/64`.

## 8. Special-purpose addresses have defined reachability

Private IPv4 ranges, documentation prefixes, loopback, link-local, multicast, and other reserved blocks have different forwarding expectations. “Not publicly routable” does not mean “safe,” and “private” does not mean “authenticated.”

Examples in this handbook use documentation ranges:

- IPv4: `192.0.2.0/24`, `198.51.100.0/24`, and `203.0.113.0/24`;
- IPv6: `2001:db8::/32`.

Do not paste documentation addresses into a live route or DNS record. Consult the current IANA special-purpose registries rather than relying on a memorized list for production validation.

## 9. Subnet membership depends on local configuration

Two hosts can hold numerically similar addresses but disagree about whether they share a subnet if their prefix lengths differ. That misconfiguration can make one host attempt local neighbor resolution while another sends through a gateway.

For example:

```text
host A: 192.0.2.20/24
host B: 192.0.2.200/25
```

Host A considers both addresses part of `192.0.2.0/24`. Host B considers itself part of `192.0.2.128/25` and sees `.20` outside that prefix. Communication may become asymmetric or rely on proxy behavior.

Subnetting is therefore not inferred from the address alone. Inspect the prefix configured on each relevant interface.

## 10. Observe addresses without changing them

| Goal | Linux | macOS | Windows PowerShell |
| --- | --- | --- | --- |
| Interface addresses | `ip address show` | `ifconfig` | `Get-NetIPAddress` |
| IPv4 routes | `ip route show` | `route -n get default`; `netstat -rn` | `Get-NetRoute -AddressFamily IPv4` |
| IPv6 routes | `ip -6 route show` | `netstat -rn -f inet6` | `Get-NetRoute -AddressFamily IPv6` |

Outputs can include temporary IPv6 addresses, deprecated addresses, tunnel interfaces, and virtual adapters. Record interface, prefix length, state, and lifetime rather than selecting the first address displayed.

Do not add an address or route for practice on a shared machine. A disposable network namespace or isolated lab belongs in a later exercise with exact cleanup.

## Common Misconceptions

- “An IP address identifies one device.” It identifies an interface in context and can change or be shared.
- “A `/24` is a Class C network.” Modern routing is classless.
- “Every IPv4 subnet loses exactly two addresses.” `/31`, `/32`, and platform semantics are exceptions.
- “IPv6 is IPv4 with longer addresses.” Its scope, multicast, autoconfiguration, and fragmentation behavior differ materially.

## Core Computer Science Concept

CIDR uses **hierarchical prefix aggregation**. Leading bits encode a routing region, allowing one entry to represent many addresses. This reduces global state at the cost of requiring address plans that align with topology and ownership.

## Engineering Connections

- Cloud subnets are prefix allocations plus route and policy, not merely address containers.
- Kubernetes pod and service ranges must not overlap networks that need direct reachability.
- Database allowlists based on client IP inherit NAT and address-reassignment limitations.
- Capacity planning for a subnet must include reserved addresses, growth, failure domains, and migration space.

## From the Field

Two servers have addresses in `10.20.30.x`, so an engineer assumes they are local peers. One interface uses `/24`; the other uses `/27`. Their local-delivery decisions disagree, producing an asymmetric failure that seems intermittent behind proxy ARP. Comparing prefix bits, not dotted-decimal appearance, exposes the configuration mismatch.

## Engineering Review

### What problem does this solve?

It gives interfaces hierarchical addresses that support local-subnet decisions and aggregated routing across networks.

### Why was it designed this way?

Prefixes let routing systems represent many destinations with bounded state instead of one route per host.

### When should I use it?

Use prefix reasoning for address plans, route analysis, cloud networks, firewall scope, and overlapping-network diagnosis.

### When should I avoid it?

Avoid using an address as durable identity or applying IPv4 host-count and broadcast rules to every prefix and address family.

### How does this make me a better engineer?

It replaces visual guesses with bit-accurate membership and scope reasoning.

### How does this reduce waste?

It prevents address overlap, undersized networks, false local-delivery assumptions, and unnecessary routing changes.

## Handbook Principle #52

> Carry the prefix with the address; without scope and leading-bit context, the number alone is incomplete.

## Practical Observation

Choose one interface you own and record each IPv4 and IPv6 address with prefix length and scope. Calculate the matching prefix for one address by hand, then compare it with the operating system's route display. Do not change addresses, masks, or routes.

## Looking Ahead

An address and prefix may be configured manually or learned. Chapter 53 explains DHCP, IPv6 configuration, ARP, and Neighbor Discovery as distinct mechanisms for configuration and local next-hop resolution.

## References

- [RFC 4632 — Classless Inter-domain Routing](https://www.rfc-editor.org/rfc/rfc4632)
- [RFC 4291 — IPv6 Addressing Architecture](https://www.rfc-editor.org/rfc/rfc4291)
- [RFC 3021 — Using 31-Bit Prefixes on IPv4 Point-to-Point Links](https://www.rfc-editor.org/rfc/rfc3021)
- [IANA IPv4 and IPv6 Special-Purpose Address Registries](https://www.iana.org/assignments/iana-ipv4-special-registry/iana-ipv4-special-registry.xhtml)
