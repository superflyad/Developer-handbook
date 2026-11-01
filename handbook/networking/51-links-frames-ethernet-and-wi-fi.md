# Chapter 51 — Links, Frames, Ethernet, and Wi-Fi

Before an IP packet can reach a router or another local host, it must cross a link. Ethernet and Wi-Fi provide link-layer delivery with different media and coordination, while switches and access points determine how far a frame can travel.

The central idea is:

> A link delivers frames within one local forwarding domain; it does not choose the end-to-end route.

## 1. A link is a local delivery contract

A network interface attaches a host to a physical or virtual link. The link defines framing, addressing, size limits, error detection, and rules for access to its medium. Common examples include:

- wired Ethernet;
- Wi-Fi through an access point;
- loopback inside one host;
- point-to-point virtual tunnels;
- virtual bridges connecting containers or virtual machines.

An interface can be administratively enabled yet lack usable physical signal, association, link negotiation, or IP configuration. “Interface exists,” “link is up,” and “IP traffic succeeds” are separate observations.

## 2. Frames carry packets one hop at a time

An Ethernet frame conceptually includes destination and source MAC addresses, a type identifying the payload, the payload itself, and an error-detection field transmitted on the link. Hardware may add, remove, or hide details before packet-capture tools observe it.

```text
destination MAC | source MAC | type | network-layer packet | check value
```

MAC addresses identify interfaces within a link-layer context. They are not trustworthy global identities: addresses can be changed, virtualized, duplicated through mistakes, or randomized for privacy. Authorization should not rely on an observed MAC address alone.

When an IP destination is remote, the frame's destination is ordinarily the local next-hop router, while the enclosed IP destination remains the remote host. At the next routed hop, a new link frame is created for that link.

## 3. Switches learn where source addresses appear

An Ethernet bridge or switch connects link segments and forwards frames based on learned source-address locations. When a frame arrives, the switch can learn that the source MAC is reachable through that port. It then uses its forwarding database for later destination decisions.

If the destination is unknown, broadcast, or relevant multicast, the switch may send the frame through multiple eligible ports in the same forwarding domain. That behavior is not IP routing. It is local frame delivery.

Forwarding entries age and topology changes. A temporary flood does not automatically prove a switch failure. Conversely, a stale, filtered, or mislearned entry can make local connectivity selective.

Redundant bridged paths can create loops in which frames multiply. Technologies such as spanning tree constrain active topology. Designing or changing loop-prevention policy is network administration and outside this chapter.

## 4. VLANs create logical link-layer boundaries

IEEE 802.1Q VLAN tagging lets one physical switching system carry several logical broadcast domains. An access port commonly presents one VLAN without a tag to an endpoint; a trunk can carry multiple tagged VLANs between aware devices. Exact terminology and native/untagged behavior depend on configuration and vendor.

A VLAN is not an IP subnet, though designs often map one subnet to one VLAN for clarity. A host in the correct IP prefix but the wrong VLAN may fail to reach its intended neighbors. Routing between VLANs requires a layer-3 function and policy.

Do not add or change VLAN tags as a connectivity experiment on a managed network. Confirm the intended switch port, virtual-switch, and host interface configuration with the network owner.

## 5. Ethernet links negotiate physical behavior

Modern switched Ethernet normally uses full-duplex point-to-point links between an interface and a switch port. Speed and duplex may be negotiated. Cabling, optics, transceivers, power, and interface settings can affect link state and error counters.

Incrementing errors, drops, or renegotiations are evidence, but counters need a time interval and traffic context. A lifetime counter of 100 errors might describe a past incident; a rapidly increasing counter during current failures is stronger evidence.

Do not force speed or duplex based on a generic recipe. A mismatch can degrade or break the link, and managed environments may require specific settings at both ends.

## 6. Wi-Fi shares radio airtime

Wi-Fi presents a link service but uses a shared radio medium. A client discovers networks, authenticates and associates with an access point, negotiates security, and competes for airtime. Signal strength is only one factor; interference, channel use, retransmission, power saving, roaming, client density, and access-point backhaul all matter.

An access point commonly bridges wireless clients toward a wired distribution network, but client isolation, guest policy, multiple SSIDs, and VLAN mappings can restrict who shares a forwarding domain. Being associated with an SSID does not prove DHCP, DNS, internet reachability, or application access.

Wi-Fi throughput is not the displayed link rate. Protocol overhead, contention, retries, direction, channel width, and other clients reduce usable application throughput. Measure the user workload and relevant airtime evidence rather than comparing only advertised rates.

## 7. MTU bounds the network-layer payload

An interface MTU is the largest network-layer packet the link exposes without requiring a different handling path. Standard Ethernet commonly carries a 1500-byte IP payload, but tunnels, PPP links, VPNs, cloud overlays, and deliberately configured jumbo frames can use other values.

Every hop on a path has a constraint. IPv6 routers do not fragment transit packets; endpoints rely on Path MTU Discovery. IPv4 has different fragmentation behavior, but relying on in-path fragmentation is fragile. If required control messages are filtered, small requests may work while larger transfers stall.

Do not “fix” suspected MTU trouble by raising every interface. All participating links must support the chosen frame size, and a locally accepted configuration does not prove end-to-end support.

## 8. Link errors and higher-layer symptoms overlap

A link problem can appear as packet loss, retransmission, slow DNS, failed TLS, or application timeout. The reverse is also true: an application timeout can occur while the link is perfect. Use evidence at the boundary:

```text
interface state and association
→ transmitted/received frame and error counters
→ neighbor resolution
→ IP route and packet exchange
→ transport and application result
```

On virtualized systems, repeat this map across guest interface, virtual switch or bridge, host interface, and physical network. The name `eth0` inside a container does not identify a physical Ethernet port.

## 9. Observe link state safely

| Question | Linux | macOS | Windows PowerShell |
| --- | --- | --- | --- |
| Interfaces | `ip -details link show` | `ifconfig` | `Get-NetAdapter` |
| Counters | `ip -s link show` | `netstat -ib` | `Get-NetAdapterStatistics` |
| Wi-Fi association | `iw dev` where installed | Apple Wireless Diagnostics or `system_profiler SPAirPortDataType` | `netsh wlan show interfaces` |
| Bridge state | `bridge link`; `bridge fdb show` | platform-specific | `Get-VMSwitch` for owned Hyper-V systems |

Some commands expose every interface and peer address on the host. Limit output to the interface in scope when possible. Bridge and hypervisor commands apply only when those components exist and access is authorized.

Record counter values twice with timestamps. A delta during the symptom is more useful than one total. Also record whether the interface is physical, virtual, tunneled, or loopback.

## Common Misconceptions

- “A MAC address identifies a device permanently.” It is a link-layer value that can be reassigned or randomized.
- “A switch routes IP.” A basic bridge forwards frames; multilayer devices can also perform separate routing functions.
- “A VLAN is a subnet.” They are different link- and internet-layer boundaries that are often aligned by design.
- “Strong Wi-Fi signal means a healthy connection.” Contention, interference, policy, and backhaul can still fail.

## Core Computer Science Concept

Link-layer switching uses **local learning and forwarding**. It trades global topology knowledge for a bounded domain in which devices learn where source addresses appear. Routing scales beyond that domain by using a different addressing and forwarding contract.

## Engineering Connections

- Container bridges create software link domains with the same aliasing and MTU concerns as physical links.
- Cloud virtual networks hide physical switching but still expose MTU and interface boundaries.
- Overlay encapsulation consumes payload space and can cause size-dependent failures.
- Network access control at a switch or access point precedes higher-layer application authorization.

## From the Field

A VPN user can send small requests but large file transfers stall. The Wi-Fi link is stable and TCP establishes successfully. The VPN adds headers, reducing the effective path MTU, while required discovery feedback is blocked. Lowering the tunnel's supported payload according to its documentation fixes the proven boundary; changing Wi-Fi channels would not.

## Engineering Review

### What problem does this solve?

It provides local delivery of network-layer packets across physical and virtual media.

### Why was it designed this way?

Bounded link domains let Ethernet, Wi-Fi, and virtual technologies solve local framing independently of end-to-end routing.

### When should I use it?

Use this model for interface, switch, Wi-Fi, VLAN, local reachability, error-counter, and MTU investigations.

### When should I avoid it?

Avoid treating link identifiers as trusted identity or changing managed link settings without confirming both ends and rollback.

### How does this make me a better engineer?

It separates one-hop delivery evidence from routing and application behavior while exposing virtual and physical boundaries.

### How does this reduce waste?

It prevents application teams from chasing local media faults and network teams from being blamed after link health is already proven.

## Handbook Principle #51

> Prove the local link by interface state, frame delivery, and counter changes before attributing the symptom to a higher layer.

## Practical Observation

Choose one interface you own. Record its type, link state, MTU, addresses, and receive/transmit counters. Generate one harmless request to a known service, record the counter deltas, and explain which observations prove only local-link activity. Do not change interface, VLAN, speed, duplex, or Wi-Fi settings.

## Looking Ahead

Links deliver frames locally. Chapter 52 introduces IPv4 and IPv6 addresses and prefixes, which let hosts determine whether a destination is local or requires routing.

## References

- [RFC 894 — IP over Ethernet](https://www.rfc-editor.org/rfc/rfc894)
- [RFC 8200 — Internet Protocol, Version 6](https://www.rfc-editor.org/rfc/rfc8200)
- [IEEE 802.1 — Bridging and Management](https://www.ieee802.org/1/)
- [Linux Kernel: Ethernet Bridging](https://docs.kernel.org/networking/bridge.html)
