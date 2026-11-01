# Chapter 93 — VPCs, Subnets, Routes, and Address Planning

An instance has a private address in a subnet named `private-a`, yet it reaches the internet. Another instance has a public IPv4 address in a subnet named `public-b`, yet it cannot. The names describe intent; addresses, route tables, gateways, and return paths determine behavior.

The central idea is:

> Trace a VPC path from interface address to subnet route and gateway in both directions. Public and private are outcomes of that path, not properties created by a subnet's name.

## 1. A VPC is a Regional network boundary

An Amazon Virtual Private Cloud is a logically isolated virtual network in one AWS Region. It has address ranges, an implicit router, route tables, and attachments to other network domains.

A VPC is not:

- one physical switch;
- one Availability Zone;
- automatically connected to the internet;
- automatically connected to another VPC;
- an application authorization boundary;
- proof that all contained resources can communicate.

Subnets, interfaces, routes, gateways, security controls, and service behavior determine actual reachability. Chapter 94 adds packet filters, DNS, endpoints, and connections beyond one VPC.

## 2. Map cloud networking to the packet model

Part V followed a packet through names, addresses, routes, links, transport, and applications. AWS changes the control surface, not those questions.

For an EC2 path, identify:

1. the source process and socket;
2. the destination address selected after name resolution;
3. the source elastic network interface and address;
4. the source subnet;
5. the route table associated with that subnet;
6. the longest-prefix route and target;
7. each gateway, translation, or network interface in the path;
8. the destination interface and listener;
9. every return-path decision;
10. filtering and authorization at each layer.

“Same VPC” answers only part of step 6. It does not prove that a service is listening, a route target is healthy, or policy permits the flow.

## 3. Plan address space before resources consume it

A VPC must have an IPv4 CIDR block. It can have additional non-overlapping IPv4 CIDRs and one or more IPv6 CIDRs under supported allocation rules.

An address plan should account for:

- every connected VPC and on-premises network;
- other cloud environments and developer networks;
- Regions, accounts, environments, and future acquisitions;
- Availability Zones;
- public, application, data, management, and endpoint tiers;
- load balancers and managed-service interfaces;
- container and Kubernetes pod addressing;
- rolling deployments and blue/green overlap;
- autoscaling bursts;
- one-AZ failure capacity;
- temporary migration resources;
- reserved addresses and operational headroom.

Overlapping networks can make later routing, peering, transit, and hybrid connectivity difficult or impossible without translation or renumbering. A large unused range is usually cheaper than an emergency renumbering project, but address allocation still needs central visibility.

## 4. CIDR prefixes describe containment

CIDR notation combines an address and prefix length:

```text
10.42.0.0/16
10.42.16.0/20
2001:db8:1234:1a10::/64
```

For IPv4, a shorter prefix represents more addresses. A `/16` has 65,536 total addresses; a `/24` has 256; a `/28` has 16. AWS permits VPC and IPv4 subnet blocks from `/16` through `/28` under the documented rules.

Subnets in one VPC cannot overlap. A subnet CIDR must fit inside an associated VPC CIDR. AWS canonicalizes host bits in CIDRs supplied through APIs, so reviewers should record canonical network ranges rather than informal starting addresses.

Use a CIDR calculator or a standard library such as Python's `ipaddress`; do not calculate production ranges by visual inspection.

## 5. Usable IPv4 addresses are fewer than the block

For a normal IPv4 subnet, AWS reserves the first four addresses and the last address. A `/28` therefore has 16 total addresses but only 11 ordinarily assignable to resources.

Count consumers, not just instances. Addresses can be used by:

- primary and secondary instance interfaces;
- load-balancer nodes;
- NAT gateways;
- interface endpoints;
- managed database interfaces;
- container tasks or pods under some networking modes;
- replacement resources during deployments;
- service-managed interfaces.

The subnet must support the failure peak, not only today's steady state. If one AZ fails, the surviving AZs may need enough addresses to launch replacement capacity.

## 6. A subnet belongs to one Availability Zone

A subnet resides entirely in one Availability Zone and cannot span zones. To build a multi-AZ workload, create corresponding subnets in multiple AZs and place enough independent resources in each.

Use the account's AZ identifiers when coordinating physical-zone placement across accounts. AZ names such as `us-east-1a` can map differently between accounts, while AZ IDs provide consistent identifiers.

Keep tiers symmetrical only where their capacity needs are similar. Public load-balancer subnets, application subnets, and data subnets may need different sizes. Symmetry in purpose does not require equal address waste.

## 7. Subnet names do not create behavior

Teams commonly use these names:

- **public subnet:** has a direct route for internet destinations to an internet gateway;
- **private subnet:** has no direct route to an internet gateway, but may have outbound access through NAT or private service paths;
- **isolated subnet:** has no default route to the internet and only deliberate internal or service routes.

These are architectural conventions, not immutable AWS subnet types. The associated route table is decisive.

A subnet with `0.0.0.0/0 -> igw-id` is public for IPv4 routing even if named `private`. A subnet with no internet-gateway route is not made public by assigning an instance a public IPv4 address.

## 8. Every subnet uses one subnet route table

Each subnet is associated with one route table. The association can be explicit or implicit through the VPC's main route table. One route table can serve multiple subnets.

Explicit associations make intent visible. A safe convention is to keep the main route table minimal and explicitly associate each workload subnet with a purpose-built table. This reduces the chance that a newly created subnet inherits unexpected internet or transit connectivity.

For every subnet inventory:

- route table ID and owner;
- whether association is explicit;
- IPv4 and IPv6 routes;
- propagated routes where applicable;
- target state;
- expected path tests;
- change history.

Renaming a route table does not change associations, and changing the main route table can affect every subnet using its implicit association.

## 9. Routes map destinations to targets

A route has a destination and target:

```text
Destination       Target
10.42.0.0/16      local
0.0.0.0/0         igw-0123456789abcdef0
```

The destination is a CIDR or supported prefix list. The target can be a gateway, connection, network interface, or other supported AWS networking resource.

IPv4 and IPv6 are separate. `0.0.0.0/0` does not match IPv6; `::/0` does not match IPv4.

The route target must be valid for the route table and path. A route can remain in `blackhole` state when its target is unavailable or deleted. The presence of the row does not prove forwarding succeeds.

## 10. Longest prefix match chooses the route

The implicit VPC router selects the most specific matching destination, called longest prefix match.

Given:

```text
10.42.0.0/16      local
10.42.48.0/24     eni-inspection
0.0.0.0/0         nat-az-a
```

traffic to `10.42.48.10` matches all three prefixes, but the `/24` is most specific. It uses `eni-inspection`, not the local or default route.

When equally specific routes exist, AWS has additional priority rules among static, prefix-list, and propagated routes. Do not rely on list order in the console. Inspect the documented priority for the exact route types.

## 11. Local routes connect VPC CIDRs

Each route table contains a `local` route for each associated VPC CIDR. It enables routing between subnets in the VPC.

The local route does not guarantee application reachability. Traffic can still fail because of:

- a more-specific route;
- security group or network ACL policy;
- source/destination checking on an appliance path;
- no destination listener;
- operating-system firewall or route;
- asymmetric return routing;
- a service-managed interface state;
- an incorrect address family.

Adding a secondary VPC CIDR adds a corresponding local route. It does not automatically resolve overlaps with networks outside the VPC.

## 12. Internet gateways provide direct internet routing

An internet gateway attaches to a VPC and can be the target for public IPv4 or IPv6 routes. For direct IPv4 internet communication, an instance normally needs:

- a public subnet route to the internet gateway;
- a public IPv4 address or Elastic IP associated with its private address;
- filtering that permits the flow;
- a return path;
- a listening and correctly configured application for inbound traffic.

The instance itself sees its private IPv4 address. The internet gateway performs the one-to-one address mapping for the public IPv4 address.

For public IPv6, the resource has an IPv6 address and the subnet route table can send `::/0` to the internet gateway. There is no IPv4-style public-to-private translation in that path.

An internet gateway is not a firewall. A route makes a path possible; Chapter 94 controls which traffic is permitted.

## 13. Public addresses do not imply public services

A public IPv4 or globally scoped IPv6 address identifies a possible internet endpoint. It does not prove that:

- a route exists;
- inbound policy permits traffic;
- the host accepts the protocol and port;
- the application binds the relevant interface;
- authentication and authorization succeed;
- a stable DNS name refers to it.

Conversely, a resource can serve internet users without a public address on its own interface when a public load balancer, CDN, or proxy terminates the public connection and uses a private backend path.

Minimize direct public interfaces. Make the intended ingress layer explicit.

## 14. NAT gateways provide translated egress

A public NAT gateway is placed in a public subnet, receives an Elastic IP, and reaches the internet through an internet gateway. A private IPv4 subnet can route `0.0.0.0/0` to that NAT gateway so its resources initiate connections without receiving direct inbound internet connections through the NAT.

The packet path is:

```text
private interface
  -> private subnet route table
  -> NAT gateway private address
  -> public subnet route table
  -> internet gateway
  -> NAT gateway Elastic IP on the internet
```

Responses follow the established translation state back to the source. The NAT gateway does not accept arbitrary internet-initiated connections for private instances.

Private NAT gateways serve private connectivity patterns and do not provide internet egress by routing to an internet gateway.

## 15. Align NAT gateways with Availability Zones

A NAT gateway is created in one Availability Zone and is redundant within that zone. If private subnets in several AZs all use one NAT gateway, they gain:

- dependence on the NAT gateway's AZ;
- cross-AZ data paths and possible transfer cost;
- a shared capacity and port-allocation boundary;
- a wider egress failure domain.

For resilient decentralized egress, deploy a NAT gateway per active AZ and route each private subnet to the NAT gateway in the same AZ. This costs more, so review whether private endpoints, proxies, IPv6, or eliminating unnecessary internet dependencies better fit the workload.

Monitor NAT gateway errors, port allocation, bytes, packets, and cost. A default route is not capacity evidence.

## 16. IPv6 changes egress design

IPv6 addresses are not made private by address translation. A dual-stack or IPv6-only subnet needs explicit IPv6 routes and policy.

For outbound-only public IPv6 behavior, route `::/0` to an egress-only internet gateway. It is stateful: it allows connections initiated from the VPC and their responses while preventing the internet from initiating connections through it.

For IPv6-only workloads that must reach IPv4-only destinations, AWS supports DNS64 and NAT64 through a NAT gateway. The Route 53 Resolver can synthesize an IPv6 address under `64:ff9b::/96`, and a route for that prefix can send traffic to the NAT gateway for translation.

Do not assume dual stack automatically creates equivalent IPv4 and IPv6 controls. Test both address families. An application may prefer IPv6 and bypass an IPv4-only inspection assumption.

## 17. IPv6 still requires an allocation plan

The IPv6 space is large, but hierarchy matters. Allocate stable VPC and subnet prefixes that preserve:

- Region and environment structure;
- AZ placement;
- aggregation in route and policy rules;
- room for new tiers;
- public versus private IPv6 intent;
- compatibility with connected networks.

AWS supports subnet IPv6 prefix sizes under documented rules; `/64` remains a common subnet choice and is the local standard used by this chapter's lab. AWS also reserves five addresses in each IPv6 subnet under the documented allocation behavior.

Large address capacity does not remove quotas on interfaces, routes, gateways, or compute resources.

## 18. Elastic network interfaces hold network identity

An elastic network interface, or ENI, is a VPC network interface with properties such as:

- VPC and subnet;
- Availability Zone;
- primary and secondary private IPv4 addresses;
- IPv6 addresses or prefixes;
- public or Elastic IP associations where applicable;
- security groups;
- MAC address;
- source/destination check;
- attachment and deletion behavior;
- requester or service management.

The primary ENI of an EC2 instance cannot be detached. Secondary ENIs can support additional addresses or traffic roles subject to instance and AZ constraints. An ENI can attach only to an instance in the same Availability Zone.

Many managed services create requester-managed ENIs in your subnets. Include their address use and lifecycle in the plan, and do not assume an unfamiliar interface is safe to delete.

## 19. Source/destination checking protects the normal host model

EC2 network interfaces enable source/destination checking by default. A normal instance should be the source or destination of traffic it handles.

An instance intentionally acting as a router, NAT device, or firewall may require the check to be disabled. That change expands the interface's forwarding role and must be paired with:

- operating-system forwarding configuration;
- correct routes in both directions;
- anti-spoofing and filtering controls;
- appliance availability and scaling;
- asymmetric-path analysis;
- monitoring and recovery.

Disabling the check does not turn an instance into a working router by itself.

## 20. Design every tier across failure domains

A two-AZ application commonly has paired subnets:

```text
AZ A                      AZ B
public-a                  public-b
app-a                     app-b
data-a                    data-b
NAT-a                     NAT-b
```

The design must survive a zone loss at every dependency:

- load-balancer nodes and targets;
- application capacity;
- data replicas or failover targets;
- NAT and endpoint paths;
- available addresses;
- route targets;
- deployment and observability services.

Having two subnets does not prove the workload uses both. Verify placement, capacity, routing, health checks, and failover behavior.

## 21. Separate ingress, egress, and service access

Avoid treating one default route as the answer to every dependency. Classify destinations:

- internet ingress;
- internet egress;
- AWS service APIs;
- same-VPC services;
- other VPCs;
- on-premises networks;
- management and observability systems.

Each class can use a different path. VPC endpoints can keep supported service traffic off NAT and internet paths; Chapter 94 covers their policy and DNS behavior. Private dependencies should not silently require public DNS and NAT because that was the easiest first route.

## 22. Inspect routes before changing them

With authorized read-only AWS credentials, inspect the deployed association and routes:

```bash
aws ec2 describe-route-tables \
  --filters Name=association.subnet-id,Values=subnet-0123456789abcdef0 \
  --no-cli-pager
```

If no explicit subnet association is returned, identify the VPC's main route table:

```bash
aws ec2 describe-route-tables \
  --filters \
    Name=vpc-id,Values=vpc-0123456789abcdef0 \
    Name=association.main,Values=true \
  --no-cli-pager
```

Inspect interfaces and their actual addresses:

```bash
aws ec2 describe-network-interfaces \
  --network-interface-ids eni-0123456789abcdef0 \
  --no-cli-pager
```

These calls are read-only but their output can expose account topology, public addresses, tags, and identifiers. Store and share it according to your environment's data policy.

Do not paste example IDs into a mutation command. Confirm account, Region, resource owner, and intended change through reviewed infrastructure code.

## 23. Trace both directions

For a failing connection, build two route traces:

```text
forward: source interface -> source subnet table -> targets -> destination
return:  destination interface -> destination subnet table -> targets -> source
```

At each hop record:

- source and destination after any translation;
- address family;
- longest-prefix match;
- route target and state;
- AZ transition;
- expected filtering layer;
- ownership and observability.

Asymmetric routing is not always invalid, but stateful devices and NAT translations often require the return flow to traverse compatible state. A working forward route alone is insufficient.

## 24. Practical model: validate an address and route plan

This standard-library lab validates a dual-stack, two-AZ plan locally. It checks containment, overlap, IPv4 headroom, the chapter's `/64` IPv6 convention, explicit tier defaults, multi-AZ placement, and same-AZ NAT routing. It does not call AWS or model packet filters.

Save as `test_vpc_plan.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from ipaddress import ip_address, ip_network, IPv4Network, IPv6Network
import unittest


@dataclass(frozen=True)
class Route:
    destination: str
    target: str

    @property
    def network(self) -> IPv4Network | IPv6Network:
        return ip_network(self.destination)


@dataclass(frozen=True)
class RouteTable:
    name: str
    routes: tuple[Route, ...]

    def target_for(self, destination: str) -> str | None:
        address = ip_address(destination)
        matches = [route for route in self.routes if address in route.network]
        if not matches:
            return None
        return max(matches, key=lambda route: route.network.prefixlen).target


@dataclass(frozen=True)
class Subnet:
    name: str
    ipv4: str
    ipv6: str
    az: str
    tier: str
    route_table: str
    projected_ipv4_interfaces: int


@dataclass(frozen=True)
class VpcPlan:
    ipv4: str
    ipv6: str
    subnets: tuple[Subnet, ...]
    route_tables: tuple[RouteTable, ...]
    nat_gateway_az: tuple[tuple[str, str], ...]

    def validate(self) -> None:
        v4 = ip_network(self.ipv4)
        v6 = ip_network(self.ipv6)
        if v4.version != 4 or not 16 <= v4.prefixlen <= 28:
            raise ValueError("VPC IPv4 prefix must be /16 through /28")
        if v6.version != 6:
            raise ValueError("VPC IPv6 block is invalid")

        tables = {table.name: table for table in self.route_tables}
        if len(tables) != len(self.route_tables):
            raise ValueError("route table names must be unique")
        nat_az = dict(self.nat_gateway_az)

        subnet_v4 = [ip_network(subnet.ipv4) for subnet in self.subnets]
        subnet_v6 = [ip_network(subnet.ipv6) for subnet in self.subnets]
        for index, subnet in enumerate(self.subnets):
            network4 = subnet_v4[index]
            network6 = subnet_v6[index]
            if not network4.subnet_of(v4) or not network6.subnet_of(v6):
                raise ValueError(f"{subnet.name} falls outside the VPC")
            if network6.prefixlen != 64:
                raise ValueError(f"{subnet.name} violates the /64 IPv6 convention")
            usable_ipv4 = network4.num_addresses - 5
            required_with_headroom = (subnet.projected_ipv4_interfaces * 5 + 3) // 4
            if required_with_headroom > usable_ipv4:
                raise ValueError(f"{subnet.name} lacks 25 percent IPv4 headroom")
            if subnet.route_table not in tables:
                raise ValueError(f"{subnet.name} lacks a route table")

            table = tables[subnet.route_table]
            ipv4_default = table.target_for("198.51.100.10")
            ipv6_default = table.target_for("2001:4860:4860::8888")
            if subnet.tier == "public":
                if ipv4_default != "igw" or ipv6_default != "igw":
                    raise ValueError(f"{subnet.name} lacks public defaults")
            elif subnet.tier == "private":
                if not ipv4_default or not ipv4_default.startswith("nat-"):
                    raise ValueError(f"{subnet.name} lacks an IPv4 NAT default")
                if nat_az.get(ipv4_default) != subnet.az:
                    raise ValueError(f"{subnet.name} uses cross-AZ NAT")
                if ipv6_default != "egress-only-igw":
                    raise ValueError(f"{subnet.name} lacks IPv6 egress-only route")
            elif subnet.tier == "isolated":
                if ipv4_default is not None or ipv6_default is not None:
                    raise ValueError(f"{subnet.name} is not isolated")
            else:
                raise ValueError(f"unknown tier: {subnet.tier}")

        for index, left in enumerate(subnet_v4):
            for right in subnet_v4[index + 1 :]:
                if left.overlaps(right):
                    raise ValueError(f"overlapping IPv4 subnets: {left}, {right}")
        for index, left in enumerate(subnet_v6):
            for right in subnet_v6[index + 1 :]:
                if left.overlaps(right):
                    raise ValueError(f"overlapping IPv6 subnets: {left}, {right}")

        for tier in {subnet.tier for subnet in self.subnets}:
            zones = {subnet.az for subnet in self.subnets if subnet.tier == tier}
            if len(zones) < 2:
                raise ValueError(f"{tier} tier lacks two-AZ placement")


def routes(name: str, ipv4_default: str | None, ipv6_default: str | None) -> RouteTable:
    entries = [
        Route("10.42.0.0/16", "local"),
        Route("2001:db8:1234:1a00::/56", "local"),
    ]
    if ipv4_default:
        entries.append(Route("0.0.0.0/0", ipv4_default))
    if ipv6_default:
        entries.append(Route("::/0", ipv6_default))
    return RouteTable(name, tuple(entries))


def complete_plan() -> VpcPlan:
    return VpcPlan(
        ipv4="10.42.0.0/16",
        ipv6="2001:db8:1234:1a00::/56",
        route_tables=(
            routes("public-a", "igw", "igw"),
            routes("public-b", "igw", "igw"),
            routes("private-a", "nat-a", "egress-only-igw"),
            routes("private-b", "nat-b", "egress-only-igw"),
            routes("isolated-a", None, None),
            routes("isolated-b", None, None),
        ),
        nat_gateway_az=(("nat-a", "az-a"), ("nat-b", "az-b")),
        subnets=(
            Subnet("public-a", "10.42.0.0/24", "2001:db8:1234:1a00::/64", "az-a", "public", "public-a", 40),
            Subnet("public-b", "10.42.1.0/24", "2001:db8:1234:1a01::/64", "az-b", "public", "public-b", 40),
            Subnet("app-a", "10.42.16.0/20", "2001:db8:1234:1a10::/64", "az-a", "private", "private-a", 1000),
            Subnet("app-b", "10.42.32.0/20", "2001:db8:1234:1a20::/64", "az-b", "private", "private-b", 1000),
            Subnet("data-a", "10.42.48.0/24", "2001:db8:1234:1a30::/64", "az-a", "isolated", "isolated-a", 100),
            Subnet("data-b", "10.42.49.0/24", "2001:db8:1234:1a31::/64", "az-b", "isolated", "isolated-b", 100),
        ),
    )


class VpcPlanTests(unittest.TestCase):
    def test_complete_plan_is_accepted(self) -> None:
        complete_plan().validate()

    def test_longest_prefix_route_wins(self) -> None:
        table = RouteTable(
            "inspection",
            (
                Route("0.0.0.0/0", "nat-a"),
                Route("10.42.0.0/16", "local"),
                Route("10.42.48.0/24", "eni-inspection"),
            ),
        )
        self.assertEqual("eni-inspection", table.target_for("10.42.48.10"))

    def test_cross_az_nat_is_rejected(self) -> None:
        plan = complete_plan()
        broken = VpcPlan(
            ipv4=plan.ipv4,
            ipv6=plan.ipv6,
            subnets=plan.subnets,
            route_tables=tuple(
                routes("private-b", "nat-a", "egress-only-igw")
                if table.name == "private-b"
                else table
                for table in plan.route_tables
            ),
            nat_gateway_az=plan.nat_gateway_az,
        )
        with self.assertRaisesRegex(ValueError, "cross-AZ NAT"):
            broken.validate()

    def test_ipv4_exhaustion_is_rejected(self) -> None:
        plan = complete_plan()
        subnets = list(plan.subnets)
        subnet = subnets[0]
        subnets[0] = Subnet(
            subnet.name,
            subnet.ipv4,
            subnet.ipv6,
            subnet.az,
            subnet.tier,
            subnet.route_table,
            220,
        )
        broken = VpcPlan(
            plan.ipv4,
            plan.ipv6,
            tuple(subnets),
            plan.route_tables,
            plan.nat_gateway_az,
        )
        with self.assertRaisesRegex(ValueError, "headroom"):
            broken.validate()


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

Run it:

```bash
python -m unittest -v test_vpc_plan.py
```

The IPv6 ranges use the documentation prefix `2001:db8::/32` and are examples only. Replace every range, AZ, capacity estimate, and route target with an approved plan before implementation. Validate actual AWS state separately through read-only inventory and reviewed infrastructure code.

## 25. Review a VPC plan

Require this design record:

```text
VPC purpose, account, Region, owners, and lifecycle:
connected and potentially connected networks:
IPv4 and IPv6 allocation sources:
overlap analysis and reserved expansion ranges:
subnets by tier, AZ ID, CIDR, usable addresses, and peak demand:
explicit route-table association for every subnet:
IPv4 and IPv6 routes, targets, priority, and expected state:
internet ingress layers and public-address ownership:
IPv4 egress path, NAT AZ alignment, capacity, and cost:
IPv6 egress and IPv4-only destination strategy:
managed-service and endpoint ENI demand:
one-AZ-loss capacity and address availability:
forward and return traces for every dependency class:
read-only inventory, drift detection, and path tests:
teardown, renumbering, and migration constraints:
```

The plan is incomplete if its largest expected deployment or recovery event cannot fit in the remaining addresses of each surviving subnet.

## Common Misconceptions

- “A subnet named public is public.” A direct route to an internet gateway creates public routing intent.
- “A public IP guarantees internet access.” The route, gateway, policy, return path, and application must also work.
- “A private subnet cannot reach the internet.” It can initiate IPv4 connections through NAT or IPv6 connections through an egress-only internet gateway.
- “A NAT gateway makes a subnet public.” It provides translated, initiated egress; it does not give private interfaces direct inbound internet reachability.
- “One NAT gateway is multi-AZ because the service is managed.” A NAT gateway is zonal; cross-AZ users depend on its zone.
- “The first matching route wins.” Longest prefix match wins, followed by AWS priority rules for equal prefixes.
- “Same VPC means reachable.” Route selection is only one layer of the path.
- “IPv6 needs no planning because addresses are abundant.” Prefix hierarchy, policy, dependencies, and operations still require design.
- “Two subnets provide high availability.” Workload placement, capacity, and every dependency must use both zones correctly.
- “An ENI is just an instance detail.” Many managed services create ENIs that consume addresses and participate in routing and policy.

## Core Computer Science Concept

VPC routing applies **hierarchical address partitioning and longest-prefix selection**. CIDRs divide a finite namespace into nested sets. A route table maps those sets to next hops, and the most specific applicable set wins. Availability design adds another independent partition: each subnet binds an address range to one failure domain.

## Engineering Connections

- CIDR containment and longest-prefix match extend Chapters 52 and 53 into a cloud control plane.
- Subnet and AZ placement apply Chapter 90's failure-domain model.
- Explicit route associations resemble explicit dependency injection: hidden defaults make behavior harder to review.
- NAT state makes return-path symmetry and connection tracking operational concerns.
- ENI address consumption connects container and autoscaling density to network capacity.
- Read-only route inspection applies Part VI's observe-before-mutate discipline.
- IPv4 exhaustion is a capacity problem; a successful creation today says nothing about failover headroom.

## From the Field

A service deploys application instances into two private subnets but routes both through one NAT gateway in AZ A. During an AZ A event, the instances in AZ B remain healthy but cannot reach an external identity endpoint, so new sessions fail. The architecture review counted two application subnets but did not trace the egress dependency. Same-AZ NAT routes, private endpoints where supported, and a tested degraded-mode plan would expose and reduce that hidden shared failure domain.

## Engineering Review

### What problem does this solve?

It provides a method to allocate VPC addresses, place zonal subnets, inspect route selection, and trace public, private, isolated, IPv4, and IPv6 paths without relying on names or diagrams alone.

### Why was it designed this way?

AWS separates Regional address space, zonal placement, interface identity, route intent, and gateway behavior so architectures can compose different connectivity and failure boundaries.

### When should I use it?

Use this model before creating a VPC or subnet, when adding a service or AZ, during capacity and recovery review, and whenever a path is unreachable or unexpectedly reachable.

### When should I avoid it?

Avoid treating this chapter as a complete network-security or hybrid-routing design. Chapter 94 adds filters, DNS, endpoints, multi-VPC, and hybrid boundaries; advanced transit and firewall administration require dedicated design.

### How does this make me a better engineer?

It teaches you to reason from addresses, route associations, prefix priority, translations, interfaces, and return paths instead of treating cloud networking as named boxes connected by lines.

### How does this reduce waste?

It prevents renumbering, stranded address space, unnecessary NAT traffic, cross-AZ egress, oversized public exposure, hidden main-table inheritance, and recovery plans that cannot allocate interfaces.

## Handbook Principle #93

> A subnet's name expresses intent; its address, associated routes, and gateways determine the path.

## Practical Observation

Run the VPC-plan tests, then change one subnet's default route, CIDR, projected interface count, and NAT target. For each failure, draw the exact forward and return path. In an authorized AWS account, use only the read-only inspection commands to compare one real interface, subnet association, and route table with the intended design. Record discrepancies; do not repair them manually during observation.

## Looking Ahead

Routes make paths possible, but they do not decide which packets should pass, how private services are named, or how networks connect across VPC and on-premises boundaries. Chapter 94 combines security groups, network ACLs, VPC endpoints, Route 53 Resolver, peering, Transit Gateway, VPN, Direct Connect, flow logs, and shared-VPC tradeoffs.

## References

- [Amazon VPC — IP addressing for VPCs and subnets](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-ip-addressing.html)
- [Amazon VPC — VPC CIDR blocks](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-cidr-blocks.html)
- [Amazon VPC — Subnet CIDR blocks](https://docs.aws.amazon.com/vpc/latest/userguide/subnet-sizing.html)
- [Amazon VPC — Subnets for your VPC](https://docs.aws.amazon.com/vpc/latest/userguide/configure-subnets.html)
- [Amazon VPC — Subnet route tables](https://docs.aws.amazon.com/vpc/latest/userguide/subnet-route-tables.html)
- [Amazon VPC — How route priority works](https://docs.aws.amazon.com/vpc/latest/userguide/route-tables-priority.html)
- [Amazon VPC — Enable internet access using an internet gateway](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Internet_Gateway.html)
- [Amazon VPC — NAT gateway basics](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-basics.html)
- [Amazon VPC — DNS64 and NAT64](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-nat64-dns64.html)
- [Amazon VPC — Egress-only internet gateways](https://docs.aws.amazon.com/vpc/latest/userguide/egress-only-internet-gateway.html)
- [Amazon EC2 — Elastic network interfaces](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-eni.html)
- [AWS Well-Architected — Ensure IP subnet allocation accounts for expansion and availability](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_planning_network_topology_ip_subnet_allocation.html)
