# Chapter 94 — VPC Security, DNS, and Hybrid Connectivity

A route exists from an application subnet to a database, yet the connection times out. The security group allows the service port, but a stateless subnet rule drops the return packet. In another VPC, the same hostname resolves to a public endpoint because private DNS was never associated. Connectivity is the composition of routing, filtering, naming, and ownership.

The central idea is:

> Trace the complete bidirectional path and name every control that routes, filters, resolves, or owns it. No single “network allowed” setting proves connectivity or trust.

## 1. Routes make paths possible; policy admits traffic

Chapter 93 selected route targets. A usable connection also depends on:

- source and destination security groups;
- subnet network ACLs;
- host and application policy;
- intermediate endpoints, gateways, and appliances;
- DNS answers visible to the source;
- return routing;
- identity and application authorization.

Network reachability does not authorize an API call. Conversely, valid IAM permission cannot deliver a packet through a missing route or filter.

## 2. Security groups protect interfaces

A security group is a stateful virtual firewall associated with supported network interfaces. Its rules allow traffic; ordinary security-group rules do not create explicit denies.

Rules can constrain:

- direction;
- protocol;
- port or ICMP type;
- IPv4 or IPv6 CIDR;
- another security group in supported topologies;
- a managed prefix list.

All applicable rules are evaluated as a set. Rule order is not significant. If no rule allows a new flow, it is denied.

Attach groups by workload role, such as `web-ingress`, `orders-app`, or `database-client`, rather than by one server's name. Review the union of all groups attached to an interface.

## 3. Stateful filtering tracks allowed flows

When a security group allows a flow, response traffic for that flow is allowed regardless of a separate reverse-direction security-group rule. For example, an application ENI with outbound TCP 5432 and a database ENI with inbound TCP 5432 can exchange responses without an application inbound rule for the client's ephemeral port.

Statefulness does not remove:

- route requirements in both directions;
- stateless network ACL return rules;
- connection-tracking limits and timeouts;
- host firewalls;
- application listeners and authentication.

A second connection initiated in the reverse direction is a new flow and needs its own allow path.

## 4. Reference identities where addresses are unstable

A security-group rule can reference another security group in supported same-VPC, peering, or transit topologies. This expresses “interfaces associated with this group” more reliably than listing autoscaled private addresses.

The reference does not copy rules from the referenced group and does not authenticate an application user. It selects network interfaces as allowed peers. Confirm support for the exact cross-VPC topology and direction.

Use CIDRs when the peer is genuinely an address range, such as an approved corporate egress range. Avoid `0.0.0.0/0` or `::/0` on administration and data ports merely to simplify testing.

## 5. Egress deserves least privilege

Default security groups often begin with broad outbound access. Production workloads should have an explicit dependency inventory:

- DNS resolver;
- service APIs;
- database and cache;
- identity provider;
- telemetry destinations;
- package or update sources;
- time and metadata paths;
- recovery dependencies.

Restrict egress where the operational benefit exceeds the complexity, then test failure behavior. IP allowlists for public SaaS dependencies can be brittle; a controlled proxy or provider-maintained prefix information may be more maintainable.

Security groups do not filter several reserved infrastructure paths documented by AWS. Do not assume a missing security-group rule blocks metadata, DHCP, Amazon-provided DNS, or time service traffic.

## 6. Network ACLs protect subnet boundaries

A network ACL, or NACL, applies at the subnet boundary. It differs from a security group:

| Property | Security group | Network ACL |
| --- | --- | --- |
| Scope | Interface | Subnet |
| State | Stateful | Stateless |
| Rules | Allow | Allow and deny |
| Evaluation | All rules | Lowest numbered match first |
| Return traffic | Tracked automatically | Must be allowed explicitly |

Use security groups as the primary workload control. NACLs can add coarse subnet guardrails or explicit CIDR denies, but detailed NACL policy is easy to misconfigure and applies to every interface in associated subnets.

## 7. Stateless rules require both directions

For a client using local TCP port 49160 to reach a server on 443, subnet ACLs need to permit:

```text
forward:
client subnet outbound -> server:443
server subnet inbound  <- client:any-source-port

return:
server subnet outbound -> client:49160
client subnet inbound  <- server:443
```

The client's ephemeral range depends on its operating system and configuration. Broad assumptions such as `1024-65535` may work but are not automatically least privilege. Document the actual clients and appliances.

Because the first matching numbered NACL rule wins, leave numbering gaps for controlled additions and test that a new low-number deny does not shadow a required allow.

## 8. VPC endpoints create private service paths

A VPC endpoint lets resources reach a supported service without using an internet gateway or NAT path.

Two important forms are:

- **Gateway endpoints:** route-table targets for supported services such as Amazon S3 and DynamoDB.
- **Interface endpoints:** PrivateLink endpoint ENIs with private addresses in selected subnets.

An interface endpoint consumes subnet addresses, has security groups, incurs applicable hourly and data-processing charges, and should be placed across the AZs that need resilient access. Gateway endpoints alter associated route tables through service prefix-list routes.

An endpoint policy is another authorization layer. It does not replace identity or resource policies, and the default policy may allow broad use. Review principal, action, resource, and service support.

## 9. Private DNS determines which endpoint is used

When private DNS is enabled for many AWS interface endpoints, an AWS-managed private hosted zone makes the service's normal Regional hostname resolve to endpoint ENI addresses inside associated VPC context. Existing SDK calls can then use the private path without changing the hostname.

Verify:

- VPC DNS support and DNS hostnames settings;
- private DNS enabled on the endpoint;
- hosted-zone associations;
- resolver rule precedence;
- endpoint address family;
- answers from the actual source network;
- security groups and NACLs for the resolved endpoint addresses.

A private IP answer is not proof of application permission, and a public DNS name can still return private endpoint addresses.

## 10. Route 53 Resolver joins DNS domains

The VPC Resolver answers VPC and private hosted-zone queries under its documented rules. Resolver endpoints connect that service to other DNS systems:

- an **inbound endpoint** lets resolvers in reachable networks query VPC Resolver;
- an **outbound endpoint** sends matching VPC queries toward resolvers in another network;
- forwarding rules select domain suffixes and target DNS servers.

Deploy endpoint addresses across failure domains and permit DNS traffic in network policy. Record ownership of both directions; hybrid name resolution often fails because cloud-to-premises forwarding works while the reverse path, delegation, or firewall does not.

Avoid forwarding loops. The most specific applicable DNS rule or hosted-zone namespace should have an authoritative owner.

## 11. Peering is point-to-point

VPC peering privately connects two non-overlapping VPCs. Each side still needs routes, filtering, DNS decisions, and owner approval.

Peering is not transitive. If A peers with B and B peers with C, A cannot use B as a peering transit path to C. A mesh therefore grows in connections and route policy as VPC count rises.

Use peering for a limited number of direct relationships with clear ownership. Reject overlapping CIDRs early; AWS does not create a peering connection between overlapping VPC address ranges.

## 12. Transit Gateway is a routed hub

AWS Transit Gateway is a Regional layer-3 transit hub for VPC, VPN, Direct Connect gateway, peering, and supported appliance attachments.

Its route tables provide segmentation:

- each attachment associates with one transit route table;
- attachments can propagate routes to selected tables;
- static and propagated routes choose destination attachments;
- VPC subnet route tables must also send traffic to the transit gateway;
- attachment subnets must exist in the AZs that need the path.

Centralization simplifies many-to-many routing but increases governance impact. A propagation or association mistake can connect trust zones or blackhole many networks. Stage route changes and test both intended reachability and intended isolation.

## 13. Choose peering or transit from topology

Peering favors direct, simple, high-throughput relationships with no transit requirement. Transit Gateway favors hub-and-spoke connectivity, centralized segmentation, and hybrid aggregation.

Compare:

- number and growth of VPCs;
- transitive routing need;
- route-table ownership;
- inspection architecture;
- inter-Region requirements;
- throughput and appliance symmetry;
- data-processing and transfer costs;
- failure and change blast radius.

Do not select a hub merely because it makes the diagram tidy. Model paths and costs for real traffic.

## 14. Site-to-Site VPN provides encrypted tunnels

AWS Site-to-Site VPN connects a customer gateway to a virtual private gateway, Transit Gateway, or another supported target through IPsec tunnels. Configure both tunnels for redundancy and understand whether routing is static or uses BGP.

The internet path, customer device, tunnel endpoints, BGP policy, and AWS attachment each have failure modes. Monitor both tunnels and rehearse failover; “two tunnels configured” is not evidence that the customer device uses both correctly.

VPN is useful for initial hybrid access, backup, encryption over another connection, or workloads whose bandwidth and consistency needs fit the service.

## 15. Direct Connect is dedicated connectivity, not automatic encryption

AWS Direct Connect establishes dedicated connectivity through a Direct Connect location and virtual interfaces. It can provide more consistent network performance and private routing than an internet VPN.

Direct Connect traffic is not encrypted in transit by default. Use an applicable encryption design, such as supported MACsec or an IPsec VPN over the connection, when required.

Production resilience may require separate devices, connections, locations, and a tested backup path. One circuit and one facility remain one failure domain. Account for BGP, provider, cross-connect, virtual-interface, gateway, and route dependencies.

## 16. Shared VPCs split ownership

VPC sharing lets an owner account share subnets with participant accounts in the same AWS Organization. Participants deploy supported resources while the owner manages core network resources.

The owner controls VPCs, subnets, route tables, NACLs, gateways, endpoints, and major attachments. Participants own their application resources, interfaces, and their security groups under documented limits.

This reduces duplicated VPCs but couples teams to central network change and address capacity. Define request, incident, quota, cost, and teardown responsibilities before sharing. Separate accounts remain identity and billing boundaries; the shared VPC creates a common routing domain.

## 17. Flow logs are delayed metadata evidence

VPC Flow Logs record metadata about IP flows for VPCs, subnets, or ENIs and can publish to supported destinations. They can show addresses, ports, protocol, bytes, packets, and accept or reject status depending on the format.

Flow logs are not packet capture and are not real time. Records can be delayed or skipped, and documented traffic classes are not captured. An `ACCEPT` record proves network filtering accepted observed traffic; it does not prove TLS, authentication, application response, or business success.

Protect the log destination outside the failure and authority boundary being investigated. Define retention, query ownership, cost controls, and sensitive-address handling.

## 18. Diagnose by control plane

For a failed or unexpected path, inspect in order:

1. name resolution from the source;
2. selected address family and destination;
3. source interface and subnet route;
4. every peering, transit, endpoint, VPN, or Direct Connect route table;
5. destination and source security-group rules;
6. both directions of every NACL;
7. appliance state and asymmetric routing;
8. host firewall and listener;
9. TLS and application authorization;
10. flow, DNS, host, and application evidence.

Do not open all ports to locate the problem. Change one bounded control in an isolated test and preserve the denied-path test.

## 19. Practical model: trace stateful and stateless policy

This local model traces one TCP flow. It demonstrates security-group statefulness and NACL first-match statelessness; it does not model every AWS protocol, connection-tracking detail, reserved path, or cross-VPC reference rule.

Save as `test_vpc_policy.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from ipaddress import ip_address, ip_network
import unittest


@dataclass(frozen=True)
class SecurityGroupRule:
    direction: str
    port: int
    peer_group: str


@dataclass(frozen=True)
class SecurityGroup:
    name: str
    rules: tuple[SecurityGroupRule, ...]

    def allows(self, direction: str, port: int, peer_group: str) -> bool:
        return any(
            rule.direction == direction
            and rule.port == port
            and rule.peer_group == peer_group
            for rule in self.rules
        )


@dataclass(frozen=True)
class NaclRule:
    number: int
    direction: str
    port_start: int
    port_end: int
    cidr: str
    action: str

    def matches(self, direction: str, port: int, peer_ip: str) -> bool:
        return (
            self.direction == direction
            and self.port_start <= port <= self.port_end
            and ip_address(peer_ip) in ip_network(self.cidr)
        )


@dataclass(frozen=True)
class NetworkAcl:
    name: str
    rules: tuple[NaclRule, ...]

    def allows(self, direction: str, port: int, peer_ip: str) -> bool:
        matches = sorted(
            (
                rule
                for rule in self.rules
                if rule.matches(direction, port, peer_ip)
            ),
            key=lambda rule: rule.number,
        )
        return bool(matches) and matches[0].action == "ALLOW"


def trace_tcp(
    client_ip: str,
    client_group: SecurityGroup,
    client_acl: NetworkAcl,
    client_ephemeral_port: int,
    server_ip: str,
    server_group: SecurityGroup,
    server_acl: NetworkAcl,
    server_port: int,
) -> tuple[bool, tuple[str, ...]]:
    checks = (
        ("client SG egress", client_group.allows("egress", server_port, server_group.name)),
        ("server SG ingress", server_group.allows("ingress", server_port, client_group.name)),
        ("client NACL egress", client_acl.allows("egress", server_port, server_ip)),
        ("server NACL ingress", server_acl.allows("ingress", server_port, client_ip)),
        ("server NACL return egress", server_acl.allows("egress", client_ephemeral_port, client_ip)),
        ("client NACL return ingress", client_acl.allows("ingress", client_ephemeral_port, server_ip)),
    )
    trace = tuple(f"{name}={'ALLOW' if allowed else 'DENY'}" for name, allowed in checks)
    return all(allowed for _, allowed in checks), trace


CLIENT_SG = SecurityGroup(
    "app",
    (SecurityGroupRule("egress", 443, "api"),),
)
SERVER_SG = SecurityGroup(
    "api",
    (SecurityGroupRule("ingress", 443, "app"),),
)
CLIENT_ACL = NetworkAcl(
    "client",
    (
        NaclRule(100, "egress", 443, 443, "10.42.20.0/24", "ALLOW"),
        NaclRule(100, "ingress", 49152, 65535, "10.42.20.0/24", "ALLOW"),
    ),
)
SERVER_ACL = NetworkAcl(
    "server",
    (
        NaclRule(100, "ingress", 443, 443, "10.42.10.0/24", "ALLOW"),
        NaclRule(100, "egress", 49152, 65535, "10.42.10.0/24", "ALLOW"),
    ),
)


class VpcPolicyTests(unittest.TestCase):
    def test_complete_bidirectional_path_is_allowed(self) -> None:
        allowed, trace = trace_tcp(
            "10.42.10.10", CLIENT_SG, CLIENT_ACL, 50000,
            "10.42.20.20", SERVER_SG, SERVER_ACL, 443,
        )
        self.assertTrue(allowed, trace)

    def test_missing_security_group_ingress_is_denied(self) -> None:
        allowed, trace = trace_tcp(
            "10.42.10.10", CLIENT_SG, CLIENT_ACL, 50000,
            "10.42.20.20", SecurityGroup("api", ()), SERVER_ACL, 443,
        )
        self.assertFalse(allowed, trace)

    def test_missing_stateless_return_rule_is_denied(self) -> None:
        missing_return = NetworkAcl(
            "server",
            (NaclRule(100, "ingress", 443, 443, "10.42.10.0/24", "ALLOW"),),
        )
        allowed, trace = trace_tcp(
            "10.42.10.10", CLIENT_SG, CLIENT_ACL, 50000,
            "10.42.20.20", SERVER_SG, missing_return, 443,
        )
        self.assertFalse(allowed, trace)

    def test_lower_numbered_nacl_deny_wins(self) -> None:
        blocked = NetworkAcl(
            "server",
            (
                NaclRule(50, "ingress", 443, 443, "10.42.10.10/32", "DENY"),
                NaclRule(100, "ingress", 443, 443, "10.42.10.0/24", "ALLOW"),
                NaclRule(100, "egress", 49152, 65535, "10.42.10.0/24", "ALLOW"),
            ),
        )
        allowed, trace = trace_tcp(
            "10.42.10.10", CLIENT_SG, CLIENT_ACL, 50000,
            "10.42.20.20", SERVER_SG, blocked, 443,
        )
        self.assertFalse(allowed, trace)


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

Run it:

```bash
python -m unittest -v test_vpc_policy.py
```

The security-group test changes only the server group; the ACL remains intact. In production, derive ephemeral ranges from real clients, inspect actual rule associations, and use Reachability Analyzer or isolated probes as supporting evidence rather than treating this model as AWS parity.

## 20. Review a connectivity proposal

```text
source and destination owners, accounts, VPCs, subnets, and AZs:
protocol, ports, initiation direction, volume, latency, and availability:
forward and return routes through every table and attachment:
security groups and referenced identities:
NACL rules, ordering, ephemeral ports, and both directions:
DNS name, authority, view, resolver path, TTL, and failure behavior:
endpoint type, subnets, private DNS, policy, quota, and cost:
peering or transit scope, segmentation, and non-overlap evidence:
VPN or Direct Connect routing, encryption, redundancy, and failover:
shared-VPC owner and participant responsibilities:
flow-log scope, limitations, destination, retention, and query owner:
allowed-path and denied-path tests:
teardown and revocation owner:
```

## Common Misconceptions

- “Security groups deny traffic explicitly.” Their normal rules allow; unmatched new flows are denied.
- “I need reverse security-group rules for responses.” Stateful tracking permits response traffic for an allowed flow.
- “NACLs are stateful too.” They require explicit forward and return rules.
- “A VPC endpoint grants service access.” Routing and private DNS do not replace IAM or resource policy.
- “Peering through a hub VPC is transitive.” Peering is point-to-point.
- “Transit Gateway connects everything automatically.” Attachments, VPC routes, transit associations, and propagations determine reachability.
- “Direct Connect is encrypted.” It is not encrypted by default.
- “Two VPN tunnels prove resilience.” Both customer and AWS paths must be configured, monitored, and tested.
- “Flow-log ACCEPT means the request succeeded.” It proves selected network filtering, not application success.
- “A shared VPC has one owner for everything.” Network and participant application responsibilities are split.

## Core Computer Science Concept

This chapter applies **composed predicates over a bidirectional graph**. Routes choose graph edges, stateful filters remember flow state, stateless filters evaluate each packet independently, and DNS maps names into destination nodes. A connection succeeds only when every required forward and return predicate holds.

## Engineering Connections

- Security groups and NACLs implement the filtering layers introduced in Chapter 54.
- Resolver views extend Chapter 55's rule that name answers depend on the querying context.
- Stateful filtering uses the connection-state ideas from Chapter 58.
- VPC endpoints add both network and IAM policy layers from Chapter 92.
- Peering and transit make Chapter 93's address non-overlap a connectivity constraint.
- Flow logs are sampled operational evidence, not a proof of absence.

## From the Field

A team creates an S3 interface endpoint but leaves private DNS disabled. Instances continue resolving the public service address and send traffic through a NAT gateway, so the endpoint appears unused while NAT cost grows. Enabling private DNS without checking the endpoint security group then causes timeouts. A complete trace—DNS answer, route, endpoint ENI, security group, endpoint policy, IAM, and bucket policy—would reveal both independent gaps.

## Engineering Review

### What problem does this solve?

It locates which AWS control routes, filters, resolves, or bridges a flow and helps choose connectivity by topology, trust, availability, encryption, ownership, and cost.

### Why was it designed this way?

AWS separates interface policy, subnet guardrails, service endpoints, DNS resolution, and network attachments so each administrative boundary can express its own control.

### When should I use it?

Use it for every new cross-tier, cross-VPC, service-endpoint, or hybrid path and for every reachability, exposure, DNS, or network-cost incident.

### When should I avoid it?

Avoid using this overview as a production hybrid-routing or firewall runbook. Those designs require provider circuits, BGP, appliances, performance, encryption, and failure testing specific to the environment.

### How does this make me a better engineer?

It replaces “the network” as one opaque cause with a testable chain of routing, state, policy, naming, and ownership decisions.

### How does this reduce waste?

It prevents broad temporary rules, unused endpoints, accidental NAT paths, peering meshes, duplicate VPCs, unencrypted assumptions, and logs that nobody can query.

## Handbook Principle #94

> Connectivity is proven only when naming, forward policy, return policy, and application authorization agree on the same path.

## Practical Observation

Run the policy-trace tests and print each check. Remove one return NACL rule, reverse one security-group reference, and add a lower-number deny. Then choose one real dependency and draw its DNS, route, filter, and authorization planes separately. Any control labeled merely “network” needs a concrete owner and artifact.

## Looking Ahead

With account, identity, and network boundaries established, Chapter 95 turns to EC2: instance lifecycle, AMIs, user data, metadata credentials, placement, storage, scaling, patching, and the operational responsibilities retained when renting virtual machines.

## References

- [Amazon VPC — Infrastructure security and filter comparison](https://docs.aws.amazon.com/vpc/latest/userguide/infrastructure-security.html)
- [Amazon VPC — Security groups](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html)
- [AWS PrivateLink — Interface VPC endpoints](https://docs.aws.amazon.com/vpc/latest/privatelink/create-interface-endpoint.html)
- [AWS PrivateLink — Gateway endpoints](https://docs.aws.amazon.com/vpc/latest/privatelink/gateway-endpoints.html)
- [AWS PrivateLink — Endpoint policies](https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints-access.html)
- [Route 53 — Resolver endpoints and forwarding](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver.html)
- [Amazon VPC — VPC peering basics](https://docs.aws.amazon.com/vpc/latest/peering/vpc-peering-basics.html)
- [Amazon VPC — AWS Transit Gateway](https://docs.aws.amazon.com/vpc/latest/tgw/)
- [AWS Site-to-Site VPN User Guide](https://docs.aws.amazon.com/vpn/latest/s2svpn/)
- [AWS Direct Connect — Encryption in transit](https://docs.aws.amazon.com/directconnect/latest/UserGuide/encryption-in-transit.html)
- [Amazon VPC — VPC sharing](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-sharing.html)
- [Amazon VPC — Flow logs](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html)
