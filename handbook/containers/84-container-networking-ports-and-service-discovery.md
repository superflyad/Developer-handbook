# Chapter 84 — Container Networking, Ports, and Service Discovery

A service can listen successfully on port `8080` inside a container and still be unreachable from another container, the host, or a remote client. A port number has meaning only together with a network namespace, address, protocol, and path.

The central idea is:

> Trace every connection hop by hop—from client resolution through host policy and namespace routing to the listening socket—and treat publication, discovery, and application readiness as separate contracts.

## 1. Name every endpoint completely

An endpoint is not merely “port 8080.” Record at least:

- protocol: TCP, UDP, or another transport;
- address family: IPv4 or IPv6;
- network namespace or host;
- local bind address and port;
- client-visible name, address, and port;
- network membership and route;
- publication or load-balancing rule;
- firewall and policy boundary;
- application protocol and security mode.

`127.0.0.1:8080`, `0.0.0.0:8080`, `[::1]:8080`, and `[::]:8080` are different bindings. TCP port 8080 and UDP port 8080 are different sockets. The same port number can exist independently in many network namespaces.

## 2. A network namespace owns a network stack

On Linux, a network namespace isolates networking resources including:

- network interfaces;
- IPv4 and IPv6 protocol stacks;
- routing tables;
- firewall rules;
- port-number and socket space;
- selected network settings and `/proc/net` views;
- the abstract UNIX-domain socket namespace.

A container process normally sees its namespace's loopback device, one or more interfaces, addresses, routes, and a resolver configuration. It does not need to know whether those resources are implemented by a bridge, overlay, virtual machine, or another runtime mechanism.

This is why two containers can both bind TCP port 8080 without conflict: each socket belongs to a different namespace. Publishing both on host port 8080 would conflict because the host-facing bindings share a namespace.

## 3. Loopback never means “the surrounding machine”

Loopback addresses refer to the namespace making the connection.

Inside an ordinarily isolated container:

- `127.0.0.1` and `::1` refer to that container's network namespace;
- the host's loopback is elsewhere;
- another container's loopback is elsewhere;
- a process bound only to container loopback is not reachable through the container's external interface.

An application intended to receive traffic from peers must normally listen on the container interface address or an appropriate wildcard address. Binding `0.0.0.0` accepts IPv4 connections addressed to eligible local interfaces; it does not publish the port or bypass firewall policy.

Do not replace a specific binding with a wildcard blindly. The correct bind address follows the service's intended exposure and platform behavior.

## 4. Virtual Ethernet pairs cross namespace boundaries

On a typical Linux bridge network, the runtime creates a virtual Ethernet pair. One endpoint appears in the container namespace; its peer remains in the host namespace and joins a software bridge.

```text
container namespace                  host namespace

application socket
       |
 container route
       |
     eth0  <========= veth pair =========>  host-side veth
                                                |
                                          bridge device
                                                |
                                    host routing and firewall
```

Packets transmitted on one veth endpoint are received by its peer. The bridge forwards frames among connected endpoints. Host routing, forwarding, filtering, address translation, and physical interfaces determine where traffic can go next.

The diagram is a useful Linux mental model, not a portable promise about interface names or Docker Desktop internals. Desktop products commonly place the engine and Linux containers inside a managed virtual machine.

## 5. A bridge network is a scoped connectivity domain

A user-defined bridge network usually provides:

- an address subnet and gateway;
- interfaces for attached containers;
- communication among attached members;
- isolation from unrelated bridge networks;
- outbound connectivity through routing and often masquerading;
- scoped name resolution for container names and aliases;
- optional port publication through host addresses.

Prefer a user-defined network over the legacy default bridge for an application. It creates an explicit membership boundary and supplies automatic name resolution. The default bridge's historical linking behavior is not a service-discovery design.

Network attachment grants a path to every listening port allowed by the network policy; it is not limited to ports declared with `EXPOSE`.

## 6. `EXPOSE`, listening, and publishing are different

Keep three facts separate:

| Mechanism | What it says | What it does not do |
| --- | --- | --- |
| Image `EXPOSE 8080` | The image documents an intended container port and protocol | Start a listener or create a host mapping |
| Process listens on `0.0.0.0:8080` | A socket accepts eligible traffic in that namespace | Make the socket reachable outside its network path |
| `--publish 127.0.0.1:49152:8080` | Host loopback port 49152 forwards to container port 8080 | Change the application's container port |

`--publish-all` can publish ports declared by image metadata to runtime-selected host ports. It still depends on a real listener and should not replace an explicit exposure review.

## 7. A published port creates a host-facing path

For a typical bridge network in NAT mode:

```text
client -> host IP:host port -> host filtering/DNAT
       -> bridge/veth -> container IP:container port -> socket
```

For example:

```bash
docker run --publish 127.0.0.1:8080:80 example/image
```

maps TCP port 8080 on host IPv4 loopback to TCP port 80 in the container by default. The client uses `127.0.0.1:8080`; a peer on the same container network normally uses the container's service name and port 80.

Publication is a runtime rule, not a socket moved out of the container. The host port and container port need not match.

## 8. The host bind address is an exposure decision

If no host address is specified, Docker normally publishes on all host addresses. That can make a service reachable from adjacent or remote networks, subject to routing and policy.

Use the narrowest intended binding:

```bash
# Host-local IPv4 access
docker run --publish 127.0.0.1:8080:80 example/image

# Host-local IPv6 access
docker run --publish '[::1]:8080:80' example/image

# All eligible host IPv4 interfaces
docker run --publish 0.0.0.0:8080:80 example/image
```

Quoting the bracketed IPv6 form prevents shell interpretation and makes address boundaries clear.

A loopback bind is useful for local development and host-local proxies. It is not an authentication mechanism. Review engine version, forwarding behavior, firewall integration, and any surrounding virtual machine or cloud network policy.

## 9. Port publication is implemented with host policy

On Linux bridge networks, the engine installs packet-filtering and forwarding rules to provide isolation, publication, NAT, and masquerading. Depending on configuration, the backend can be iptables or nftables.

This has operational consequences:

- a host firewall frontend may not observe traffic at the stage you expect;
- disabling engine-managed firewall rules can break isolation and outbound access;
- packets may already have undergone destination translation when user rules see them;
- IP forwarding policy affects routed paths;
- platform and engine versions can change implementation details.

Manage the engine's documented policy integration point rather than editing engine-owned rules. Test from the actual source network, not only from the host.

## 10. Outbound traffic often uses masquerading

In a common bridge configuration, a container sends traffic through its gateway and the host rewrites the source to a host address. The remote system therefore sees the host as the network peer.

```text
container source address
        -> host route and source NAT
        -> external destination sees host address
```

Consequences include:

- remote allowlists usually need the effective egress address;
- application logs may not show the original container address;
- return traffic depends on connection tracking and host policy;
- overlapping host, VPN, and container subnets can cause wrong routes;
- direct routing or IPv6 configurations can preserve container addresses instead.

Never assume NAT exists on every network driver. Inspect the configured driver, gateway mode, and routes.

## 11. Service discovery maps identity to current endpoints

On a user-defined Docker network, an attached container can resolve another member by its name or network alias. This gives applications a stable logical target while container addresses change across replacement.

Use a service identity such as `orders-api`, not a copied container IP. A useful discovery contract answers:

- Which namespace or network can resolve the name?
- Which address families and records can be returned?
- Can several instances share the identity?
- What is the record lifetime?
- How quickly are removed endpoints withdrawn?
- Does the client reconnect and resolve again after failure?
- Is the discovered endpoint authorized, or merely reachable?

DNS supplies location, not trust, readiness, or protocol compatibility. Authenticate the peer at the application or transport layer.

## 12. Discovery is scoped by network membership

A container attached to several networks can have different aliases on each. This supports deliberate boundaries such as:

```text
public network:       gateway <-> web
application network:             web <-> API
data network:                          API <-> database
```

The web service does not need database network membership. The database does not need a published host port merely because the API needs it.

Avoid attaching every service to one broad network for convenience. Network separation is not complete authorization, but it removes unnecessary paths and makes intended flows reviewable.

## 13. Container addresses are runtime state

A container IP can change when the container is recreated, reattached, rescheduled, or moved to another host. Do not store it in source code, image layers, durable configuration, certificates, or long-lived allowlists unless the platform explicitly guarantees that address as an allocated resource.

Clients should use service names or platform endpoints and tolerate endpoint turnover. Long-lived connections continue to use the address selected when they were established; a DNS update does not migrate an existing TCP connection.

After a connection fails, reconnect with bounded backoff, re-resolve according to the discovery contract, and preserve the operation's retry-safety rules from Chapter 74.

## 14. Resolver behavior belongs in the incident model

Name resolution can fail independently of packet delivery and the application:

- the querying container is not attached to the right network;
- the name or alias is scoped elsewhere;
- resolver configuration is wrong or overwritten;
- a client caches a stale result longer than intended;
- IPv4 and IPv6 answers lead to different paths;
- a search suffix changes the queried name;
- the target exists but is not ready or listening.

Record the exact queried name and the returned records from the client namespace. A successful lookup does not prove a TCP handshake; a successful handshake does not prove application readiness.

## 15. IPv4 and IPv6 are related but distinct paths

Dual-stack hosts can expose different policy on each address family. Check:

- whether the network has IPv6 enabled and a usable prefix;
- whether the process listens on IPv4, IPv6, or both;
- whether a wildcard IPv6 socket also accepts IPv4 on that platform;
- which DNS records the client receives and prefers;
- whether host publication targets IPv4, IPv6, or both;
- whether the path uses NAT or direct routing;
- whether every firewall layer has equivalent rules.

Do not infer IPv6 protection from an IPv4 firewall rule. Test both families explicitly when both are enabled.

## 16. Host networking removes the namespace boundary

Host network mode lets the process use the host's network namespace instead of an isolated container network namespace. The process shares the host's interfaces, routes, and port space; ordinary port publication is therefore ignored.

Host networking can reduce translation overhead or support applications with unusual port requirements, but it changes the isolation and conflict model:

- container loopback is host loopback;
- a port collision is a host port collision;
- network policy can no longer rely on a separate container namespace;
- platform support and behavior vary, especially on desktop products;
- the process still has other container isolation boundaries unless separately removed.

Use it only for a measured requirement with an explicit threat and portability review.

## 17. Shared network namespaces share sockets and loopback

Some runtimes allow one container to join another container's network namespace. The processes then share interfaces, routes, loopback, addresses, and port space.

This pattern can support a tightly coupled proxy or diagnostic helper, but it also means:

- either process can collide on a port;
- `localhost` reaches either process's listeners;
- packet capture can observe shared traffic if permitted;
- network identity belongs to the shared namespace, not one image;
- lifecycle ordering becomes important.

Treat the pair as one network security unit even if filesystem and process namespaces remain separate.

## 18. Ingress, egress, and discovery are independent controls

A secure design answers three separate questions:

1. Who can initiate traffic to the service?
2. Which destinations can the service reach?
3. Which names and endpoints can the service discover?

Blocking ingress does not block data exfiltration over unrestricted egress. Removing DNS does not prevent connections to literal addresses. A network path does not authorize the application request.

Combine minimal network membership, narrow publication, egress policy, authenticated protocols, workload identity, and application authorization. Log decisions at the layer that owns them.

## 19. Readiness is above reachability

A complete connection progresses through distinct gates:

```text
name resolution
  -> route selection
  -> filtering/translation
  -> transport handshake
  -> TLS or other session setup
  -> application request
  -> dependency and readiness checks
```

Startup ordering can make a process exist before any later gate succeeds. A retry loop must distinguish temporary unavailability from permanent configuration errors and must have a time budget.

Health checks, readiness, and dependency orchestration are developed further in Chapters 85 and 86.

## 20. Trace failures from the client outward

Collect evidence in this order:

1. **Client intent:** exact scheme, name, port, protocol, and address family.
2. **Resolution:** returned addresses, aliases, search behavior, and resolver errors.
3. **Client route:** selected interface, gateway, and source address.
4. **Network membership:** source and target attachments and policy.
5. **Host publication:** host address, host port, target address, target port, and protocol.
6. **Host policy:** forwarding, firewall, NAT, cloud, VPN, and desktop-VM boundaries.
7. **Target route:** interface state and local address.
8. **Listener:** owning process, bind address, port, protocol, and namespace.
9. **Handshake:** TCP reset, timeout, TLS alert, or successful session.
10. **Application evidence:** request log, authorization, readiness, and response.

Run observations in both relevant namespaces. Host tools can show the publication while missing the container's listener; container tools can show the listener while missing the host path.

## 21. Interpret common symptoms precisely

| Symptom | Strong first hypotheses |
| --- | --- |
| Name does not resolve | Wrong name, alias, network membership, or resolver scope |
| Immediate connection refused | Route reached an address but no eligible listener accepted it |
| Connection timeout | Dropped traffic, wrong route, unavailable target, or asymmetric return path |
| Host succeeds; remote client fails | Loopback-only bind, external firewall, routing, or publication scope |
| Container succeeds on `localhost`; peer fails | Application bound only to container loopback |
| Peer succeeds; host fails | No host publication or wrong host address/port |
| IPv4 succeeds; IPv6 fails | Missing listener, route, publication, or policy for IPv6 |
| Existing connection works; new ones fail | Stale endpoint, exhausted accept queue, policy change, or listener replacement |

These are starting hypotheses, not verdicts. A reset can be generated by the target host, an intermediary, or policy software; a timeout contains less location information than many dashboards imply.

## 22. Inspect the effective runtime state

Useful observations on an approved system include:

```bash
docker network inspect application-network
docker container inspect application-api
docker port application-api
docker exec application-api ip address
docker exec application-api ip route
docker exec application-api cat /etc/resolv.conf
docker exec application-api ss -lntup
```

Minimal images may not contain `ip` or `ss`. Do not install a permanent toolbox into a production image merely for convenience. Use approved host inspection, a purpose-built ephemeral diagnostic container, runtime namespace entry, or application-native diagnostics according to the security policy.

Treat inspection output as potentially sensitive: it can reveal topology, internal names, environment data, and configuration.

## 23. Safe engine lab: discover and publish one service

On an approved disposable Docker-compatible engine, this Bash lab creates a unique bridge network, starts a read-only HTTP service, verifies scoped DNS from a peer, and confirms that Docker selected a loopback-only ephemeral host port:

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

suffix="$RANDOM-$$"
network="handbook-net-$suffix"
server="handbook-api-$suffix"
client="handbook-client-$suffix"
image="alpine:3.21"

cleanup() {
  docker rm --force "$server" "$client" >/dev/null 2>&1 || true
  docker network rm "$network" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker network create "$network" >/dev/null

docker run --detach \
  --name "$server" \
  --network "$network" \
  --network-alias api \
  --publish 127.0.0.1::8080 \
  --read-only \
  --tmpfs /www:rw,nosuid,nodev,noexec,size=1m \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  "$image" sh -c '
    printf "network-path-ok\n" > /www/index.html
    exec httpd -f -p 8080 -h /www
  ' >/dev/null

body=""
for attempt in $(seq 1 20); do
  if body="$(
    docker run --rm \
      --name "$client" \
      --network "$network" \
      --read-only \
      --cap-drop ALL \
      --security-opt no-new-privileges \
      "$image" wget -qO- http://api:8080 2>/dev/null
  )"; then
    break
  fi
  sleep 0.25
done

test "$body" = "network-path-ok"

published="$(docker port "$server" 8080/tcp)"
case "$published" in
  127.0.0.1:*) ;;
  *)
    printf 'unexpected publication: %s\n' "$published" >&2
    exit 1
    ;;
esac

docker network inspect "$network" \
  --format '{{range $id, $entry := .Containers}}{{$entry.Name}} {{end}}'
printf 'peer endpoint: http://api:8080\n'
printf 'host endpoint: http://%s\n' "$published"
```

The peer uses the alias `api` and the container port. The host uses a loopback address and a runtime-selected host port. The lab intentionally does not bind to every host interface.

The cleanup trap removes only uniquely named containers and the unique network. Pulling the image can leave a reusable local image; remove it separately only if your environment requires that cleanup. Pin an approved digest when supply-chain reproducibility matters.

## 24. Record a packet-path worksheet

For one production or staging request, fill in this evidence rather than drawing an unverified arrow:

```text
client namespace:
queried service name:
resolved IPv4/IPv6 addresses:
client source address and route:
host or load-balancer address and port:
translation or direct-routing rule:
firewall/policy decisions:
target network and address:
target listener address, port, and protocol:
TLS peer identity:
application readiness result:
observed response or failure:
capture time and configuration version:
```

Repeat from each materially different source network. “Works from my laptop” verifies only one route and policy context.

## Common Misconceptions

- “`EXPOSE` opens a firewall port.” It records image metadata; it does not publish a port or start a listener.
- “Container port 8080 is host port 8080.” They are endpoints in different namespaces unless a runtime mapping connects them.
- “`localhost` means the host.” It means the loopback interface of the caller's network namespace.
- “DNS success means the service is healthy.” It proves only that a resolver returned an answer.
- “A user-defined network authorizes requests.” It creates reachability and discovery scope, not application identity or permission.
- “NAT always hides container addresses.” Driver and gateway modes can use direct routing, especially with IPv6.
- “Publishing to all interfaces is fine behind a host firewall.” Engine forwarding rules and firewall frontends must be tested together.

## Core Computer Science Concept

Container networking is **graph reachability across isolated namespaces under name-resolution, routing, translation, and policy functions**. Each hop transforms or constrains the endpoint tuple; failure localization requires observing the tuple before and after each boundary.

## Engineering Connections

- Network namespaces extend Chapter 78's kernel isolation model.
- Published endpoints are runtime configuration and must stay separate from the image identity in Chapters 79–81.
- Connection retry safety follows the distributed-systems rules in Chapter 74.
- DNS and layered packet diagnosis reuse the evidence model from Chapters 58 and 63.
- Minimal network membership applies the least-authority principle developed further in Chapter 87.

## From the Field

An API reports that it is listening on `127.0.0.1:8080` inside its container. The host publishes port 8080 and the dashboard shows a healthy process, yet every peer receives a refusal. The publication reaches the container interface, but no socket listens there. Changing the application to its intended container-interface binding—and retaining a narrow host publication—fixes the actual boundary without opening unrelated host interfaces.

## Engineering Review

### What problem does this solve?

It distinguishes service identity, container sockets, network membership, host publication, routing, policy, and readiness so connection failures can be localized rather than guessed at.

### Why was it designed this way?

Network namespaces allow identical addresses and ports to coexist under separate stacks, while bridge and publication mechanisms reconnect only the paths an operator selects.

### When should I use it?

Use this model whenever a container accepts ingress, calls another service, publishes a host port, joins multiple networks, or behaves differently across client locations or address families.

### When should I avoid it?

Avoid assuming this particular Linux bridge path for host networking, overlay networks, macvlan or ipvlan, Windows containers, desktop virtual machines, or orchestrators; inspect their effective data path while preserving the endpoint model.

### How does this make me a better engineer?

It teaches you to turn “the network is broken” into testable claims about resolution, routes, translations, listeners, and application state in named namespaces.

### How does this reduce waste?

It prevents broad firewall changes, hard-coded addresses, unnecessary publication, port conflicts, stale DNS debugging, and diagnostic images added permanently to production workloads.

## Handbook Principle #84

> A reachable service is a verified path through names, namespaces, routes, policy, and a listening application—not a port number written in configuration.

## Practical Observation

Run the disposable engine lab where Docker is available, then record the peer endpoint and the host endpoint. Inspect the server namespace and host publication separately. Change only the application listener to loopback in a disposable copy, observe the resulting failure, and restore the working configuration before cleanup.

## Looking Ahead

One container can be reasoned about from a runtime command; a local system needs a reproducible declaration of several services, networks, volumes, dependencies, health signals, and teardown rules. Chapter 85 builds that declaration with Compose without confusing creation order with readiness.

## References

- [Docker Engine networking overview](https://docs.docker.com/engine/network/)
- [Docker Engine network drivers](https://docs.docker.com/engine/network/drivers/)
- [Docker Engine bridge network driver](https://docs.docker.com/engine/network/drivers/bridge/)
- [Docker Engine port publishing and mapping](https://docs.docker.com/engine/network/port-publishing/)
- [Docker Engine packet filtering and firewalls](https://docs.docker.com/engine/network/packet-filtering-firewalls/)
- [Docker Engine host network driver](https://docs.docker.com/engine/network/drivers/host/)
- [Docker CLI `docker network inspect`](https://docs.docker.com/reference/cli/docker/network/inspect/)
- [Linux `network_namespaces(7)` manual page](https://man7.org/linux/man-pages/man7/network_namespaces.7.html)
- [Linux `veth(4)` manual page](https://man7.org/linux/man-pages/man4/veth.4.html)
