# Chapter 61 — SSH, Tunnels, and Remote Access Boundaries

Secure Shell (SSH) combines an encrypted transport, server host authentication, client user authentication, and multiplexed channels for remote commands, file transfer, and forwarding. Each function crosses a distinct trust boundary.

The central idea is:

> SSH is safe remote transport only when the client verifies the host, the server authenticates and authorizes the user, and every forwarded endpoint has an intentional exposure scope.

## 1. SSH authenticates two different parties

SSH first establishes a protected transport and authenticates the server using a host key. Inside that transport, the client authenticates a user account to the server. These are separate decisions:

```text
client -- verifies host key --> server identity
client identity -- authenticated and authorized --> remote account
```

A valid user key presented to the wrong host still exposes an authentication attempt to an unintended endpoint. A verified host does not imply that every user should receive a shell. Both directions need explicit policy.

After authentication, SSH's connection protocol multiplexes logical channels over the protected transport. An interactive shell, one remote command, an SFTP subsystem, and forwarded connections can share that transport while retaining separate channel state.

## 2. Host keys anchor server identity

A server holds one or more long-lived host private keys. During key exchange it proves possession of the selected host key, binding the ephemeral exchange to the server identity.

The client compares that identity with a trusted record, commonly in `known_hosts`. On first use, an interactive client may ask the user to accept a fingerprint. This trust-on-first-use model is only as strong as the first verification. Compare the fingerprint through an authenticated inventory, console, administrator, or other independent channel when the host matters.

A changed host-key warning can indicate legitimate rebuild or rotation, a stale alias, load-balanced hosts with inconsistent keys, or interception. Do not reflexively delete the old entry. Establish the expected new fingerprint and reason for change first, then update the narrow matching entry.

Host certificates can let a trusted SSH CA sign host identities, reducing per-host distribution. They move trust to the CA key and its issuance policy rather than eliminating verification.

## 3. User authentication is not authorization

SSH can authenticate users with public keys, passwords, hardware-backed credentials, certificates, or combinations chosen by server policy. With public-key authentication, the client proves possession of a private key; the private key is not sent to the server.

Authentication answers who controls a credential. Authorization decides which account, commands, files, forwarding, and privilege transitions are permitted. An entry in `authorized_keys` can be constrained by source, forced command, environment, and forwarding options. A service account rarely needs an unrestricted interactive shell.

Prefer individual identities, short-lived or hardware-backed credentials where appropriate, narrow account privileges, and auditable elevation. Shared private keys erase attribution and make revocation expensive.

## 4. Agents hold signing capability

An SSH agent keeps private-key operations available to a client so users need not repeatedly expose or unlock key files. Listing an identity in an agent does not send its private material during normal authentication; the agent performs a signature operation.

Agent forwarding makes the local agent reachable from the remote host. A privileged or compromised remote host can request signatures through that forwarded socket while the session exists, even though it cannot directly extract the key. Use jump-host transport instead where possible, avoid forwarding to untrusted systems, limit loaded keys, and require confirmation for sensitive agent operations when supported.

An agent is a credential broker, not a permission boundary. Malware running as the local user may be able to use the agent under its policy.

## 5. Remote commands have two interpreters

`ssh host command` asks the server to execute a command rather than start an interactive shell. Arguments can pass through a local shell, SSH serialization, and a remote shell. Quoting that is correct for one layer can be reinterpreted by another.

For automation, prefer fixed server-side commands, SFTP, structured input, or carefully tested argument handling. Avoid concatenating untrusted text into remote shell command strings. Capture the remote exit status and distinguish it from connection or authentication failure.

Allocating a pseudo-terminal changes buffering, signal, and input behavior. Use a terminal for interactive work, not by default for machine-to-machine commands.

## 6. File transfer is a separate protocol behavior

SFTP operates as an SSH subsystem with file-oriented operations. `scp` implementations commonly use SFTP in modern OpenSSH, but client and server versions and compatibility options can alter behavior.

File transfer still needs destination authorization, path validation, ownership, permissions, size limits, integrity expectations, and atomic publication. Encryption in transit does not prevent overwriting the wrong remote path or deploying untrusted content.

For repeatable deployment, transfer to a staging name, validate, then perform a controlled server-side replacement under the narrow account authorized for that path.

## 7. Local forwarding exposes a local listener

Local forwarding has the shape:

```text
ssh -L [local_bind:]local_port:destination_host:destination_port ssh_server
```

The SSH client listens locally. Each connection travels through SSH, and the SSH server side opens a connection to the named destination. Therefore, `destination_host` is resolved and reached from the remote side, not necessarily from the laptop.

Bind scope is critical. `127.0.0.1:local_port` limits ordinary access to the local host; a wildcard bind can expose the tunnel to the local network. The remote service sees its connection arriving from the SSH server or its network context, not directly from the original local application.

## 8. Remote forwarding exposes a remote listener

Remote forwarding reverses the listener location:

```text
ssh -R [remote_bind:]remote_port:destination_host:destination_port ssh_server
```

The SSH server arranges the remote listener, and accepted connections travel through SSH toward a destination reached from the client side. Server policy and `GatewayPorts` affect whether non-loopback remote clients can reach it.

Remote forwarding can unintentionally publish a developer service into a protected network or expose an internal service through the server. Record the bind address, listener owner, allowed clients, destination, lifetime, and monitoring before enabling it.

Dynamic forwarding (`-D`) creates a local SOCKS proxy whose application-selected destinations are reached through the SSH server. It is broader than one fixed port and requires equally explicit client and destination policy.

## 9. Jump hosts are connection paths, not implicit trust

`ProxyJump` or `ssh -J` carries the SSH connection through an intermediate host to the final destination. The client still verifies the final host key and authenticates to the final server; the jump host is a transport waypoint.

This is safer than logging into a bastion and launching a second ad hoc SSH client because final credentials and verification can remain on the origin client. The jump host still observes connection metadata and can disrupt traffic, so it needs hardening, logging, and narrow access.

A port forward is not a general VPN. It exposes selected TCP or Unix-domain endpoints. Dynamic forwarding proxies compatible application traffic. Layer-3 tunneling has different routing, DNS, policy, and administrative implications.

## 10. Inspect the effective plan before connecting

Useful observations include:

| Goal | Command |
| --- | --- |
| Show client version | `ssh -V` |
| Show effective configuration | `ssh -G host-alias` |
| Find a known-host entry | `ssh-keygen -F host.example` |
| Show a public-key fingerprint | `ssh-keygen -lf host-key.pub` |
| Diagnose one authorized connection | `ssh -vv host-alias` |

`ssh -G` expands configuration without opening the network connection, making it useful for reviewing destination, user, port, jump route, identities, and forwarding. Debug output can reveal hostnames, usernames, paths, and network topology; sanitize it before sharing.

Do not use `StrictHostKeyChecking=no`, an empty known-hosts file, or automatic key deletion to suppress identity errors. Do not test forwarding by binding wildcard listeners on production systems. Use an authorized disposable endpoint and close tunnels when the observation ends.

## Common Misconceptions

- “Encryption means I reached the right server.” Host-key verification establishes that identity.
- “Public-key authentication grants administrator access.” Server authorization determines the account and allowed actions.
- “Agent forwarding sends my private key.” It exposes signing capability, which is still powerful and risky.
- “`localhost` in `-L` always means my laptop.” The destination is interpreted from the SSH server side.
- “A tunnel is private because SSH is encrypted.” Its listener can still be broadly exposed at either endpoint.

## Core Computer Science Concept

SSH demonstrates **multiplexed capabilities across explicit trust boundaries**. One authenticated transport carries channels with different powers, while host identity, user credentials, remote authorization, and listener scope constrain each capability.

## Engineering Connections

- Host-key verification resembles certificate identity validation but commonly uses explicit keys, fingerprints, or SSH-specific CAs.
- Local and remote forwards create sockets whose ownership and bind scope can be inspected with Chapter 56's tools.
- Jump hosts alter the path without eliminating end-to-end final-host verification.
- Remote automation inherits shell parsing, process exit, file permission, and least-privilege concerns.

## From the Field

An engineer uses `ssh -L 0.0.0.0:5432:db.internal:5432 bastion` to reach a database. The tunnel works, but every host on the engineer's local network can now attempt the forwarded database connection. Binding to loopback and using database authentication fixes different layers of the exposure; SSH encryption alone never limited the local listener.

## Engineering Review

### What problem does this solve?

It provides authenticated protected remote login, command, file-transfer, and forwarding channels over an untrusted network.

### Why was it designed this way?

Separating transport, user authentication, and multiplexed connections allows multiple remote capabilities to share one secure session under distinct policies.

### When should I use it?

Use SSH for authorized remote administration and narrowly scoped transport when host verification, user identity, and endpoint exposure are explicit.

### When should I avoid it?

Avoid ad hoc SSH tunnels as undocumented permanent infrastructure or unrestricted shared accounts as an access-management substitute.

### How does this make me a better engineer?

It teaches you to name both authenticated parties and trace where every command, credential operation, and forwarded connection actually executes.

### How does this reduce waste?

It prevents bypassed host checks, exposed listeners, shared-key churn, fragile nested sessions, and debugging the wrong tunnel endpoint.

## Handbook Principle #61

> Verify the host, authorize the user narrowly, and describe every SSH tunnel by both listeners and both connection endpoints.

## Practical Observation

Run `ssh -G` for an existing host alias without connecting. Record the effective hostname, user, port, jump route, identity files, host-key policy, and any forward directives; redact personal paths before sharing. Draw the listener and destination side of each configured forward and identify which machine resolves the destination name.

## Looking Ahead

SSH can intentionally proxy selected traffic. Chapter 62 broadens the view to firewalls, NAT devices, proxies, and load balancers that filter, transform, terminate, or distribute traffic throughout a path.

## References

- [RFC 4251 — The Secure Shell (SSH) Protocol Architecture](https://www.rfc-editor.org/rfc/rfc4251)
- [RFC 4252 — The Secure Shell (SSH) Authentication Protocol](https://www.rfc-editor.org/rfc/rfc4252)
- [RFC 4253 — The Secure Shell (SSH) Transport Layer Protocol](https://www.rfc-editor.org/rfc/rfc4253)
- [OpenBSD `ssh(1)` manual](https://man.openbsd.org/ssh)
- [OpenBSD `ssh_config(5)` manual](https://man.openbsd.org/ssh_config)
