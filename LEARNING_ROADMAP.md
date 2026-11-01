# Learning Roadmap

The roadmap moves from operating-system fundamentals toward designing, operating, and improving production systems.

Published material is organized into Parts and Chapters. The sequence is directional rather than frozen: chapters may be revised or reorganized when stronger dependencies and better learning paths become clear.

## Part I — Foundations: Building the Machine

Part I explains the machine before teaching command-focused productivity.

1. Thinking Like a Unix Developer
2. The Unix Mental Model
3. The Unix Filesystem
4. Programs, Processes, and the Kernel
5. The Shell
6. Terminal Emulators: The Window into Unix
7. Identity, Authentication, Authorization, and Permissions
8. Standard Input, Standard Output, and Standard Error
9. Pipes: Composing Small Tools
10. Environment Variables
11. The Unix Way: Composability in Practice

## Part II — Mastering the Unix Environment

Part II turns the operating-system model from Part I into deliberate command-line practice. The sequence moves from understanding an invocation, through filesystem and data work, to controlling processes and owning a repeatable environment.

### Phase 1 — Command and filesystem fluency

#### Chapter 12 — Command-Line Grammar and Getting Help

- **Purpose:** Teach how to read an unfamiliar command instead of memorizing command strings.
- **Includes:** command names, options, operands, conventions, builtins versus external programs, command resolution, exit status, `type`, shell help, manual pages, and platform-specific documentation.
- **Defers:** shell control structures, script design, and exhaustive coverage of any command's options.
- **Outcome:** The reader can identify which component interprets each part of an invocation and independently investigate an unfamiliar tool.

#### Chapter 13 — Navigation and Path Resolution

- **Purpose:** Make movement through the filesystem predictable rather than trial and error.
- **Includes:** the working directory, absolute and relative paths, `.`, `..`, `~`, `pwd`, `cd`, `ls`, hidden entries, path normalization, and navigation practices that remain safe with unusual names.
- **Defers:** changing filesystem contents, storage implementation, mounting, and filesystem internals.
- **Outcome:** The reader can predict how a path resolves before executing a command and can navigate without losing location or context.

#### Chapter 14 — Safe File and Directory Operations

- **Purpose:** Teach filesystem changes with verification, reversibility, and precise scope.
- **Includes:** creating, copying, moving, renaming, and removing files and directories; recursive operations; overwrite behavior; quoting pathnames; option terminators; previews; backups; and safe handling of destructive commands.
- **Defers:** filesystem implementation, advanced link semantics, synchronization systems, and backup architecture.
- **Outcome:** The reader can perform routine filesystem mutations while recognizing when an operation is broad, destructive, or difficult to recover.

### Phase 2 — Discovery and text composition

#### Chapter 15 — Finding Files and Inspecting Metadata

- **Purpose:** Separate locating filesystem objects from searching inside their contents.
- **Includes:** name- and metadata-based discovery, `find`, `locate` where available, `stat`, `file`, timestamps, sizes, ownership, predicates, result actions, and safe handling of matched pathnames.
- **Defers:** text search, storage internals, indexing architecture, and advanced filesystem forensics.
- **Outcome:** The reader can express a precise filesystem query, inspect why an object matched, and pass results onward without corrupting pathnames.

#### Chapter 16 — Searching Text and Working with Regular Expressions

- **Purpose:** Turn content search into a precise, testable engineering activity.
- **Includes:** literal and regular-expression search, `grep`, recursive search, context, case handling, exclusions, binary-file behavior, match-oriented exit statuses, and `rg` as a practical extension after the native model is understood.
- **Defers:** full regular-expression language theory, parser construction, and structured-data query languages.
- **Outcome:** The reader can choose an appropriate search expression, constrain its scope, interpret no-match correctly, and make searches usable by people or automation.

#### Chapter 17 — Reading and Transforming Text

- **Purpose:** Teach selection and transformation based on the shape of data rather than command familiarity.
- **Includes:** streaming versus paging, lines and fields, `less`, `head`, `tail`, `wc`, `sort`, `uniq`, `cut`, `paste`, `tr`, and focused introductions to `sed` and `awk`.
- **Defers:** complete `sed` or `awk` programming, binary formats, robust CSV parsing, JSON query tools, and general-purpose scripting.
- **Outcome:** The reader can inspect a stream, identify its representation, select a small transformation, and recognize when text tools are no longer the right abstraction.

#### Chapter 18 — Quoting, Expansion, and Redirection in Practice

- **Purpose:** Make the shell's evaluation rules visible enough to predict and debug command behavior.
- **Includes:** evaluation order, quoting, pathname expansion, brace expansion, parameter expansion, command substitution, arithmetic expansion, word splitting, standard-stream redirection, append versus truncate, here-documents, and common injection or data-loss hazards.
- **Defers:** conditionals, loops, reusable shell programs, and advanced file-descriptor manipulation for application design.
- **Outcome:** The reader can explain which text the shell transforms, which arguments a program receives, and where each standard stream goes.

### Phase 3 — Runtime control and environment ownership

#### Chapter 19 — Processes, Jobs, and Signals

- **Purpose:** Turn the process model from Part I into safe interactive control.
- **Includes:** process inspection, foreground and background jobs, process identifiers, job identifiers, `ps`, `jobs`, `fg`, `bg`, `wait`, signals, `kill`, terminal interruption, hangup behavior, and cautious use of long-running commands.
- **Defers:** service managers, kernel scheduling internals, production orchestration, and concurrency programming.
- **Outcome:** The reader can observe, suspend, resume, wait for, and terminate work while choosing the least disruptive control mechanism.

#### Chapter 20 — Permissions in Daily Work

- **Purpose:** Apply the identity and authority model from Chapter 7 to routine filesystem and command-line tasks.
- **Includes:** reading permission displays, symbolic and octal modes, `chmod`, ownership, groups, `chown`, `chgrp`, `umask`, directory permissions, privilege escalation, and awareness of ACLs and platform differences.
- **Defers:** authentication systems, enterprise identity management, mandatory access control, and deep security-policy administration.
- **Outcome:** The reader can diagnose an access failure, make the narrowest appropriate change, and avoid treating elevated privilege as a default solution.

#### Chapter 21 — Installing and Managing Software

- **Purpose:** Explain package management as a trust, dependency, and lifecycle system rather than an installation shortcut.
- **Includes:** packages, repositories, metadata, signatures, dependency resolution, updates versus upgrades, version selection, removal, native package managers on common Unix environments, Homebrew, and a concise Windows comparison.
- **Defers:** publishing packages, language-specific dependency management, reproducible build systems, container images, and fleet configuration management.
- **Outcome:** The reader can identify where software comes from, what authority an installation needs, how it will be updated, and how to remove or reproduce it.

#### Chapter 22 — Shell Startup, Configuration, and `PATH`

- **Purpose:** Make the interactive environment understandable, portable, and recoverable.
- **Includes:** login and interactive shells, startup-file order, exported and local variables, `PATH`, aliases, functions, prompts, completion, dotfiles, guarded configuration, debugging startup failures, and testing changes in a fresh shell.
- **Defers:** large shell frameworks, full configuration-management systems, and general shell-script architecture.
- **Outcome:** The reader can trace where a setting came from, modify configuration without locking themselves out, and maintain a small reproducible shell environment.

### Phase 4 — Integration

#### Chapter 23 — Building an Efficient Command-Line Workflow

- **Purpose:** Integrate Part II into a repeatable workflow governed by feedback, safety, and appropriate automation boundaries.
- **Includes:** command history, reverse search, completion, scratch spaces, inspect-before-change habits, incremental pipelines, validation, recovery planning, reusable command notes, and deciding when a workflow should become a script.
- **Defers:** teaching shell scripting itself, CI/CD, task runners, and production automation, which belong to Part VI.
- **Outcome:** The reader can solve a realistic investigation-and-transformation task efficiently, explain each boundary, verify the result, and identify the next appropriate level of automation.

### Part II delivery boundary

Each chapter is implemented as a separate commit. Its commit includes the chapter file, its table-of-contents link, any necessary cross-references, and verification of runnable examples. Part II is complete when Chapter 23 demonstrates the combined workflow and identifies a clear handoff to Git mastery without prematurely teaching shell scripting.

## Part III — Git Mastery

Part III treats Git as a system for recording and integrating changes, not a collection of commands to memorize. The sequence starts with local state, then introduces shared history and integration, and ends with recovery and team practice.

### Phase 1 — Local state and history

#### Chapter 24 — Why Git Works: Repositories, Objects, and History

- **Purpose:** Establish the model behind Git before teaching a command workflow.
- **Includes:** distributed repositories; `init` versus `clone`; blobs, trees, and commits; object identity; parent links; snapshots versus patches; and the commit graph.
- **Defers:** packfile internals, cryptographic implementation details, and transport protocol mechanics.
- **Outcome:** The reader can explain what a commit records, why history is a graph, and what a clone owns locally.

#### Chapter 25 — The Working Tree, Index, and `HEAD`

- **Purpose:** Make Git's three local states observable before any history-changing operation.
- **Includes:** tracked and untracked files; the working tree; the index; `HEAD`; `status`; unstaged, staged, and committed comparisons; and the meaning of a clean tree.
- **Defers:** recovery commands, branch integration, and remote synchronization.
- **Outcome:** The reader can identify exactly where a change exists and predict which state an operation will affect.

#### Chapter 26 — Staging and Making Coherent Commits

- **Purpose:** Turn working changes into deliberate, reviewable snapshots.
- **Includes:** author identity and configuration scope; `add`, partial staging, `diff --cached`, commit messages, commit creation, amend-before-publication, and verification after a commit.
- **Defers:** rewriting shared history, detailed ignore policy, and pull-request review.
- **Outcome:** The reader can build one focused commit from a mixed working tree without accidentally including unrelated changes.

#### Chapter 27 — Reading History and Investigating Changes

- **Purpose:** Use Git history as evidence rather than a chronological list of messages.
- **Includes:** `log`, `show`, `diff`, revision ranges, path-limited history, blame with its limits, and `bisect` as a controlled regression search.
- **Defers:** using blame as a measure of responsibility, repository-wide forensic tooling, and automatic root-cause claims.
- **Outcome:** The reader can locate when behavior changed and inspect the exact change without rewriting recorded history, while recognizing that `bisect` temporarily changes checkout state.

#### Chapter 28 — Tracked Content, Ignore Rules, and Portability

- **Purpose:** Define what belongs in history and how content crosses machines reliably.
- **Includes:** `.gitignore` precedence and limits, tracked-versus-ignored behavior, `.gitattributes`, text and binary classification, line endings, generated files, large-file boundaries, and avoiding secrets in commits.
- **Defers:** deep Git LFS administration, artifact storage design, and secret-scanning operations.
- **Outcome:** The reader can set a reviewable content policy and diagnose why a file is tracked, ignored, or transformed on checkout.

### Phase 2 — References and integration

#### Chapter 29 — Branches, References, Tags, and Detached `HEAD`

- **Purpose:** Explain names as movable pointers into the commit graph.
- **Includes:** branch references, `HEAD`, `switch`, branch creation and deletion, detached `HEAD`, lightweight and annotated tags, and reachability.
- **Defers:** remote-tracking references, merge policy, and release-management processes.
- **Outcome:** The reader can draw how a branch or tag refers to commits and switch contexts without mistaking a branch for a separate directory.

#### Chapter 30 — Remotes, Tracking, Fetching, and Pushing

- **Purpose:** Separate local history from the state advertised by another repository.
- **Includes:** remote names and URLs, remote-tracking refs, upstream configuration, `fetch`, `push`, the composed behavior of `pull`, fast-forward and non-fast-forward updates, and authentication boundaries.
- **Defers:** hosting-provider administration, Git transport internals, and pull-request policy.
- **Outcome:** The reader can synchronize intentionally, explain ahead/behind state, and inspect a remote update before integrating it.

#### Chapter 31 — Merging and Resolving Conflicts

- **Purpose:** Teach integration through commit ancestry and explicit conflict resolution.
- **Includes:** merge bases, fast-forward versus merge commits, three-way merges, conflicted index entries, conflict-marker interpretation, resolution, abort, and post-merge verification.
- **Defers:** rebase mechanics, octopus merges, and automatic conflict-resolution policy.
- **Outcome:** The reader can integrate two branches in a disposable repository and explain every resulting parent relationship.

#### Chapter 32 — Rebasing, Cherry-Picking, and History Rewriting

- **Purpose:** Show when replaying changes clarifies history and when it endangers collaboration.
- **Includes:** commit replay, interactive rebase, `cherry-pick`, conflicts during replay, `continue` and `abort`, changed commit identities, and the published-history boundary.
- **Defers:** broad repository-history surgery, filter tools, and force-push as a routine synchronization method.
- **Outcome:** The reader can reorganize unpublished work, verify the result, and identify when a merge or revert is safer.

#### Chapter 33 — Undoing Changes and Recovering Work

- **Purpose:** Replace vague “undo” advice with state-specific and recoverability-aware choices.
- **Includes:** `restore`, `reset` modes, `revert`, reflogs, lost commits, staged versus working-tree recovery, and the limits of recovery for untracked or expired data.
- **Defers:** disaster recovery for corrupted object databases and backup administration.
- **Outcome:** The reader can choose a recovery action by identifying what must be preserved and whether the affected history was shared.

### Phase 3 — Collaboration and professional practice

#### Chapter 34 — Pull Requests, Review, and Merge Policy

- **Purpose:** Connect local Git state to collaborative change review without confusing Git with a hosting service.
- **Includes:** feature branches, focused pull requests, review feedback, required checks, branch protection, merge/squash/rebase merge outcomes, and the repository's own publication workflow.
- **Defers:** hosting-provider administration, CI implementation, and organization-wide governance design.
- **Outcome:** The reader can prepare a reviewable change, interpret checks and feedback, and choose an integration method with its history consequences understood.

#### Chapter 35 — Worktrees and Parallel Development

- **Purpose:** Manage concurrent work without mixing unrelated changes or treating stashes as a durable filing system.
- **Includes:** `git worktree`, shared versus per-worktree state, safe branch ownership, temporary stashes and their limits, parallel feature work, and branch cleanup after integration.
- **Defers:** submodule-heavy architectures, monorepo scaling techniques, and complex release trains.
- **Outcome:** The reader can keep two independent tasks isolated and cleanly retire temporary Git state after completion.

#### Chapter 36 — A Complete Git Change Lifecycle

- **Purpose:** Integrate Part III into a realistic, inspectable workflow from a new change through review, integration, and recovery.
- **Includes:** a disposable local repository and bare remote; focused commits; branch synchronization; a deliberate merge conflict; review of the resulting diff and graph; a safe rollback; and final repository verification.
- **Defers:** live publication to a hosted service, CI/CD implementation, and production release orchestration.
- **Outcome:** The reader can explain the state and recovery path at every point in a collaborative Git change.

### Part III delivery boundary

Chapters 24–36 are drafted, one chapter per commit with its own table-of-contents link. Examples that change Git history should be verified in disposable repositories, never against this handbook's live history. Maintain the distinction between local Git mechanics and hosted review policy when revising this part.

## Part IV — Filesystems and Operating Systems

Part IV moves beneath shell commands into the operating-system mechanisms that give files, processes, and services their meaning. The sequence separates namespace from storage, then connects execution, resource management, startup, and access control across Linux, macOS, and Windows.

### Phase 1 — Filesystem identity and storage

#### Chapter 37 — Filesystems as Namespaces and Persistent State

- **Purpose:** Build a first-principles model of file objects, directory namespaces, filesystem boundaries, and persistence.
- **Includes:** files versus names, directory entries, roots, path resolution, file descriptors and handles, filesystem responsibilities, and platform terminology.
- **Defers:** links, mounting mechanics, storage allocation, and detailed permissions.
- **Outcome:** The reader can distinguish a path, an open handle, an object, and the storage system that persists it.

#### Chapter 38 — The Storage Stack: Devices, Volumes, Filesystems, and Mounts

- **Purpose:** Explain how raw storage becomes an accessible namespace without treating a drive letter or mount point as the device itself.
- **Includes:** physical and virtual devices, partitions, volumes, filesystem formats, mounting, Windows drive letters and volume mount paths, Linux/macOS mount trees, removable media, and safe observation.
- **Defers:** RAID design, storage-area networks, encryption administration, and destructive formatting exercises.
- **Outcome:** The reader can trace an accessible path down through its mount, filesystem, volume, and backing device.

#### Chapter 39 — File Identity, Hard Links, and Symbolic Links

- **Purpose:** Separate object identity from pathname aliases and references.
- **Includes:** inode/file-ID mental models, hard links, symbolic links, link counts, rename and unlink behavior, dangling links, Windows link variants, and deployment consequences.
- **Defers:** filesystem deduplication, overlay filesystems, and advanced reparse-point administration.
- **Outcome:** The reader can predict what survives rename or deletion and choose a link type without confusing identity with navigation.

#### Chapter 40 — Metadata, Timestamps, Attributes, and Extended Data

- **Purpose:** Show that file content is only one part of filesystem state.
- **Includes:** type, size, ownership, timestamps, flags, attributes, ACL presence, extended attributes, alternate data streams, metadata preservation, and portable-copy limits.
- **Defers:** digital forensics, full ACL policy design, and application-specific metadata formats.
- **Outcome:** The reader can inventory relevant metadata and explain why copying bytes alone may not reproduce a file's behavior.

#### Chapter 41 — Space, Allocation, Caching, and Durability

- **Purpose:** Explain why reported file size, free space, and successful writes do not by themselves prove durable storage.
- **Includes:** logical versus allocated size, sparse files, free-space accounting, deleted-open files, caches and buffers, flush boundaries, atomic replace patterns, quotas, and backup boundaries.
- **Defers:** filesystem implementation internals, database write-ahead logging, and storage-hardware benchmarking.
- **Outcome:** The reader can distinguish logical data, allocated blocks, cached writes, and durable state while diagnosing space anomalies safely.

### Phase 2 — Processes and resource management

#### Chapter 42 — Process Creation, Execution, and Lifecycle

- **Purpose:** Extend shell job control into the operating system's process model.
- **Includes:** program images, process creation, arguments and environment, inherited resources, current directory, exit status, parent-child relationships, Unix fork/exec and Windows process creation, and zombie/orphan concepts.
- **Defers:** threads, containers, debuggers, and kernel implementation details.
- **Outcome:** The reader can explain what state a new process receives and what must be collected or cleaned up when it exits.

#### Chapter 43 — Scheduling, Priorities, and Resource Accounting

- **Purpose:** Explain how runnable work competes for finite CPU and how engineers observe that competition.
- **Includes:** runnable versus waiting state, preemption, priority and niceness, CPU time versus wall time, load concepts, affinity boundaries, resource limits, and safe diagnostic tools.
- **Defers:** real-time scheduling design, NUMA tuning, and production capacity planning.
- **Outcome:** The reader can distinguish delay caused by CPU contention from waiting on another resource and avoid priority changes based on guesswork.

#### Chapter 44 — Virtual Memory and Process Address Spaces

- **Purpose:** Replace the idea that a process directly owns a fixed slice of physical RAM with a virtual-memory model.
- **Includes:** address spaces, pages, mappings, resident versus virtual size, anonymous and file-backed memory, sharing, copy-on-write, paging, memory pressure, and out-of-memory behavior.
- **Defers:** allocator internals, garbage collectors, kernel memory, and performance tuning recipes.
- **Outcome:** The reader can interpret common memory measurements without adding them naively or equating virtual size with physical use.

#### Chapter 45 — Interprocess Communication and Coordination

- **Purpose:** Show how isolated processes exchange data and synchronize without sharing arbitrary memory.
- **Includes:** pipes, sockets, files, shared memory, signals/events, locks, message boundaries, blocking and backpressure, ownership, cleanup, and failure containment.
- **Defers:** distributed consensus, message brokers, and network protocol design.
- **Outcome:** The reader can choose a local communication mechanism by data shape, lifetime, trust boundary, and failure behavior.

### Phase 3 — Managed execution and access control

#### Chapter 46 — Services, Daemons, and Background Work

- **Purpose:** Distinguish an operating-system-managed service from an interactive background process.
- **Includes:** service managers, declared dependencies, identities, working directories, environment, restart policy, logging, health versus liveness, systemd, launchd, and Windows Services.
- **Defers:** container orchestration, hosted-service administration, and production deployment design.
- **Outcome:** The reader can inspect how a service is launched and diagnose its execution context before changing its configuration.

#### Chapter 47 — Boot, Startup, and Shutdown

- **Purpose:** Connect firmware, kernel initialization, user-space startup, login, and orderly shutdown as a dependency sequence.
- **Includes:** firmware and boot loaders, kernel handoff, init/service managers, targets and run states, login startup, recovery boundaries, shutdown ordering, and platform comparisons.
- **Defers:** firmware modification, boot-loader repair procedures, secure-boot key administration, and kernel building.
- **Outcome:** The reader can locate a failure by startup phase and avoid changing later layers when an earlier dependency never completed.

#### Chapter 48 — Identity, Permissions, ACLs, and Privilege Boundaries

- **Purpose:** Extend basic file modes into process credentials, ACLs, inheritance, privilege, and cross-platform authorization.
- **Includes:** users and groups, effective credentials, Unix modes and ACLs, Windows access tokens and DACLs, inheritance, elevated authority, service identities, network filesystems, and least privilege.
- **Defers:** enterprise directory administration, mandatory access-control policy authoring, and cloud IAM.
- **Outcome:** The reader can trace an access decision from process identity through namespace traversal to object policy and make the narrowest safe correction.

#### Chapter 49 — A Cross-Platform Operating-System Investigation

- **Purpose:** Integrate Part IV through a read-mostly investigation of storage, process, memory, service, and access state.
- **Includes:** a portable evidence plan, Linux/macOS/Windows command mappings, path-to-volume tracing, process context, memory interpretation, service launch context, permission diagnosis, and a final system model.
- **Defers:** destructive remediation, live incident response, kernel debugging, and performance benchmarking.
- **Outcome:** The reader can gather comparable evidence on one operating system, explain each boundary, and identify the next safe diagnostic step.

### Part IV delivery boundary

Chapters 37–49 are drafted, one chapter per commit with its own table-of-contents link. Commands that modify mounts, services, startup, permissions, or storage are not routine exercises; revisions should prefer observation, disposable files, and explicit rollback. Preserve the distinction between comparable responsibilities and nonidentical Linux, macOS, and Windows abstractions.

## Part V — Networking

Part V follows data from one process to another across local, routed, and cloud networks. It builds from frames and addressing to application protocols, security boundaries, and evidence-driven troubleshooting.

### Phase 1 — Local delivery and internetworking

#### Chapter 50 — A Packet's Journey Through the Network Stack

- **Purpose:** Establish a layered model of encapsulation, forwarding, and endpoint processing before individual protocols.
- **Includes:** hosts, interfaces, links, packets, frames, segments, encapsulation, protocol headers, control versus data plane, and the limits of OSI/TCP-IP diagrams.
- **Defers:** detailed addressing, routing algorithms, packet capture syntax, and cloud-provider implementation.
- **Outcome:** The reader can trace one application message through layers and name which device or process owns each decision.

#### Chapter 51 — Links, Frames, Ethernet, and Wi-Fi

- **Purpose:** Explain delivery on one local link and the constraints beneath IP.
- **Includes:** frames, MAC addresses, switches, broadcast domains, VLAN purpose, Ethernet, Wi-Fi association, MTU, errors, and physical versus logical links.
- **Defers:** radio engineering, switch administration, spanning-tree design, and data-center fabrics.
- **Outcome:** The reader can distinguish a local-link failure from an IP or application failure and explain where a frame can travel.

#### Chapter 52 — IP Addressing and Subnetting

- **Purpose:** Make IPv4 and IPv6 prefixes, host addresses, and subnet membership predictable.
- **Includes:** binary prefix reasoning, CIDR, network and host portions, private and special-use ranges, IPv6 notation and scopes, unicast and multicast, and subnet planning.
- **Defers:** address-assignment protocols, route selection, provider allocation policy, and exhaustive IPv6 transition mechanisms.
- **Outcome:** The reader can determine whether two addresses share a subnet and calculate a usable prefix without relying on memorized classful rules.

#### Chapter 53 — Host Configuration, DHCP, ARP, and Neighbor Discovery

- **Purpose:** Explain how a host acquires configuration and finds a next-hop link-layer destination.
- **Includes:** static and dynamic configuration, DHCP leases, default gateways, DNS settings, ARP, IPv6 Neighbor Discovery, duplicate-address concerns, and cache inspection.
- **Defers:** enterprise DHCP architecture, router advertisements in depth, and hostile-link attack tooling.
- **Outcome:** The reader can separate address assignment from neighbor resolution and diagnose stale or missing local configuration.

#### Chapter 54 — Routing, Gateways, and Path Selection

- **Purpose:** Show how hosts and routers select the next hop across multiple networks.
- **Includes:** routing tables, longest-prefix match, default routes, metrics, forwarding, asymmetric paths, TTL/hop limit, traceroute limits, and policy boundaries.
- **Defers:** dynamic routing protocol administration, BGP policy design, MPLS, and software-defined networking internals.
- **Outcome:** The reader can predict the selected route for a destination and identify where a path stops matching expectations.

### Phase 2 — Names, endpoints, and transport

#### Chapter 55 — DNS and Name Resolution

- **Purpose:** Treat DNS as a distributed, cached naming system rather than a single lookup command.
- **Includes:** stub and recursive resolvers, authoritative servers, zones, common record types, delegation, caching, TTLs, negative answers, search domains, hosts files, and split-horizon behavior.
- **Defers:** authoritative-server operation, DNSSEC administration, registrar workflows, and large-scale traffic steering.
- **Outcome:** The reader can follow a name-resolution path, distinguish resolver layers, and interpret cached success or failure correctly.

#### Chapter 56 — Sockets, Ports, and Endpoint Ownership

- **Purpose:** Connect process communication to network endpoints without treating a port as a program.
- **Includes:** sockets, address families, local and remote tuples, bind, listen, connect, accept, ephemeral ports, wildcard addresses, loopback, socket state, and process ownership.
- **Defers:** transport reliability details, asynchronous I/O frameworks, raw sockets, and socket programming language APIs.
- **Outcome:** The reader can map a listening or connected endpoint to its process and explain why the same port number can appear in several contexts.

#### Chapter 57 — UDP, Datagrams, and Message Boundaries

- **Purpose:** Explain connectionless datagram transport and the reliability work left to applications.
- **Includes:** datagram boundaries, checksums, loss, duplication, reordering, size and fragmentation concerns, timeouts, amplification risk, multicast uses, and appropriate workloads.
- **Defers:** real-time media protocols, QUIC internals, reliable-UDP designs, and congestion-control algorithms.
- **Outcome:** The reader can decide when UDP semantics fit and state which delivery guarantees the application must add.

#### Chapter 58 — TCP Reliability, Flow Control, and Connection State

- **Purpose:** Explain TCP as an ordered byte stream governed by state, acknowledgment, and capacity feedback.
- **Includes:** handshake and teardown, sequence and acknowledgment reasoning, retransmission, flow versus congestion control, stream framing, resets, time-wait, keepalive limits, and common state displays.
- **Defers:** congestion-control algorithm tuning, kernel implementation, high-performance networking, and QUIC.
- **Outcome:** The reader can interpret a TCP connection lifecycle and distinguish stream semantics from application messages.

### Phase 3 — Application protocols and security boundaries

#### Chapter 59 — HTTP Semantics and API Behavior

- **Purpose:** Teach HTTP as a request-response protocol with cache, method, status, and representation semantics.
- **Includes:** URLs, methods, status classes, headers, bodies, content negotiation, redirects, cookies, caching, idempotency, HTTP/1.1 versus HTTP/2 and HTTP/3 boundaries, and API failure behavior.
- **Defers:** framework-specific API construction, browser rendering, advanced CDN configuration, and exhaustive standards coverage.
- **Outcome:** The reader can inspect an HTTP exchange, reason about safe retries and caching, and avoid treating every non-200 response alike.

#### Chapter 60 — TLS, Certificates, and Public-Key Trust

- **Purpose:** Explain how TLS establishes peer identity and protects transport without implying that encryption proves application trustworthiness.
- **Includes:** handshake goals, certificates, names, chains, roots, private keys, signatures, session keys, hostname verification, expiration, revocation limits, mutual TLS, and inspection tools.
- **Defers:** cryptographic proofs, cipher implementation, certificate-authority operation, and automated PKI administration.
- **Outcome:** The reader can trace certificate validation, separate encryption from authentication, and diagnose common trust failures safely.

#### Chapter 61 — SSH, Tunnels, and Remote Access Boundaries

- **Purpose:** Treat SSH as authenticated remote transport with explicit host and user trust.
- **Includes:** host keys, user authentication, agents, known-hosts verification, command execution, file transfer, local and remote forwarding, jump hosts, VPN comparison, and least-privilege access.
- **Defers:** fleet key management, bastion administration, VPN protocol internals, and production zero-trust architecture.
- **Outcome:** The reader can establish remote access without bypassing host verification and explain what each tunnel endpoint exposes.

#### Chapter 62 — Firewalls, NAT, Proxies, and Traffic Distribution

- **Purpose:** Map the middleboxes and policies that transform, filter, terminate, or distribute traffic.
- **Includes:** stateful and stateless filtering, ingress and egress, NAT and port translation, forward and reverse proxies, load balancers, health checks, cloud security groups, network ACLs, and client-address preservation.
- **Defers:** vendor rule syntax, web-application firewalls in depth, service meshes, and global traffic engineering.
- **Outcome:** The reader can identify which component owns a traffic decision and avoid collapsing every blocked connection into “the firewall.”

### Phase 4 — Integration

#### Chapter 63 — A Complete Network Troubleshooting Workflow

- **Purpose:** Integrate link, address, route, name, transport, TLS, and application evidence into a safe diagnostic sequence.
- **Includes:** symptom definition, scope and timing, endpoint ownership, path tracing, DNS comparison, socket tests, packet-capture boundaries, HTTP/TLS inspection, cloud-path mapping, and evidence handoff.
- **Defers:** destructive network changes, active offensive testing, provider-specific incident response, and production packet capture without authorization.
- **Outcome:** The reader can locate a failure layer, support one causal hypothesis, and select the next narrow diagnostic step.

### Part V delivery boundary

Keep one chapter per commit and prefer read-only inspection or isolated labs. Part V is complete when Chapter 63 can diagnose a path without assuming every failure is DNS, firewall, or “the network.”

## Part VI — Automation and Scripting

Part VI turns understood manual work into tested, observable automation. It begins with the automation decision, develops shell and Python implementation skills, and ends with scheduled and CI/CD execution.

### Phase 1 — From commands to programs

#### Chapter 64 — Deciding What to Automate

- **Purpose:** Apply the handbook's Observe → Understand → Remove Waste → Stabilize → Automate → Measure sequence.
- **Includes:** task frequency, variability, risk, reversibility, human judgment, interfaces, inputs and outputs, runbooks, success metrics, and automation cost.
- **Defers:** implementation languages, orchestration platforms, and return-on-investment accounting models.
- **Outcome:** The reader can reject premature automation and write a stable contract for work worth automating.

#### Chapter 65 — Reliable Shell Script Execution

- **Purpose:** Turn an interactive command sequence into an explicit shell program with predictable invocation.
- **Includes:** shebangs, shell selection, executable files, arguments, exit status, standard streams, working directories, environment control, quoting, temporary files, traps, and portability boundaries.
- **Defers:** advanced shell language, cross-shell polyglots, and production deployment systems.
- **Outcome:** The reader can write a small shell script that preserves argument boundaries, reports failure, and cleans up its owned temporary state.

#### Chapter 66 — Shell Control Flow, Functions, and Error Handling

- **Purpose:** Build understandable shell programs without relying on folklore such as one universal “strict mode.”
- **Includes:** tests, conditionals, loops, functions, positional parameters, command lists, pipelines, status propagation, explicit error handling, retries, traps, and diagnostics.
- **Defers:** large shell applications, parallel execution frameworks, and complete Bash language coverage.
- **Outcome:** The reader can explain every control-flow decision and handle expected failures without hiding unexpected ones.

#### Chapter 67 — Structured Inputs, Outputs, and Data Formats

- **Purpose:** Choose representations that automation can parse without corrupting data.
- **Includes:** line and record boundaries, JSON, CSV limitations, YAML risks, null-delimited pathnames, encodings, schemas, validation, machine-readable output, and backward compatibility.
- **Defers:** binary protocol design, schema registries, and large-scale data engineering.
- **Outcome:** The reader can define an input/output contract and recognize when shell text processing is no longer safe.

### Phase 2 — Python automation

#### Chapter 68 — Python Programs, Modules, and the Standard Library

- **Purpose:** Establish Python as a readable automation language after the shell boundary is understood.
- **Includes:** execution, modules, functions, types, collections, iteration, context managers, exceptions, imports, command-line entry points, and standard-library discovery.
- **Defers:** web frameworks, numerical computing, language implementation, and advanced object-oriented design.
- **Outcome:** The reader can structure a small Python automation program into testable functions and a clear entry point.

#### Chapter 69 — Files, Paths, Text, and Structured Data in Python

- **Purpose:** Manipulate filesystem and data inputs with explicit encoding and lifecycle handling.
- **Includes:** `pathlib`, context-managed I/O, encodings, JSON and CSV libraries, temporary directories, atomic replacement, metadata awareness, traversal, and validation.
- **Defers:** database frameworks, large datasets, asynchronous file I/O, and archival-format internals.
- **Outcome:** The reader can transform a directory of structured files safely without assuming paths or text are trivial strings.

#### Chapter 70 — Subprocesses, HTTP Clients, and External Boundaries

- **Purpose:** Interact with programs and services while preserving argument, timeout, status, and trust boundaries.
- **Includes:** `subprocess`, argument vectors, captured streams, timeouts, cancellation limits, HTTP requests, status handling, retries, authentication boundaries, and response validation.
- **Defers:** browser automation, distributed task queues, asynchronous networking frameworks, and API-specific SDK coverage.
- **Outcome:** The reader can call an external command or HTTP API without shell injection, silent status loss, or unbounded waiting.

#### Chapter 71 — Python Environments, Dependencies, and Packaging

- **Purpose:** Make automation reproducible without confusing interpreter installation, environments, packages, and applications.
- **Includes:** interpreter discovery, virtual environments, dependency declarations, lock strategies, package indexes and trust, editable development, project metadata, entry points, and upgrade policy.
- **Defers:** publishing public libraries, monorepo tooling, alternative build backends in depth, and supply-chain signing operations.
- **Outcome:** The reader can recreate an isolated automation environment and explain where each dependency came from.

#### Chapter 72 — Configuration, Secrets, Logging, and Observability

- **Purpose:** Separate code from runtime configuration while keeping sensitive values and operational evidence under control.
- **Includes:** configuration precedence, environment and file boundaries, secret references, validation, structured logs, correlation IDs, metrics for batch work, redaction, and dry-run reporting.
- **Defers:** enterprise secret-manager administration, distributed tracing platforms, and organization-wide telemetry standards.
- **Outcome:** The reader can configure one program predictably, protect secrets, and produce evidence that explains each run.

### Phase 3 — Reliability and execution systems

#### Chapter 73 — Testing, Linting, and Type Checking Automation

- **Purpose:** Treat automation as production code proportional to its blast radius.
- **Includes:** unit and integration boundaries, fixtures, temporary resources, mocks and fakes, property cases, shell linting, Python linting and types, deterministic tests, and failure-path verification.
- **Defers:** exhaustive formal verification, UI testing, and organization-wide test infrastructure.
- **Outcome:** The reader can build a fast test suite that proves important behavior and recovery paths before automation touches real systems.

#### Chapter 74 — Idempotency, State, Retries, and Recovery

- **Purpose:** Make repeated or interrupted runs converge safely rather than duplicate effects.
- **Includes:** desired versus observed state, idempotent operations, checkpoints, deduplication keys, retry classification, exponential backoff and jitter, partial failure, compensation, and resumability.
- **Defers:** distributed consensus, exactly-once claims across arbitrary systems, and workflow-engine internals.
- **Outcome:** The reader can describe what happens after interruption and rerun an automation without guessing which effects already occurred.

#### Chapter 75 — Task Runners, Builds, and Repeatable Environments

- **Purpose:** Encode developer workflows as named, discoverable tasks with dependency and cache boundaries.
- **Includes:** task runners, build graphs, inputs and outputs, incremental work, environment bootstrapping, tool versions, local versus CI parity, generated artifacts, and cleanup.
- **Defers:** compiler construction, remote build farms, and one prescribed task-runner product.
- **Outcome:** The reader can replace tribal command sequences with a small task interface that remains inspectable and reproducible.

#### Chapter 76 — Scheduling, Concurrency, and Work Queues

- **Purpose:** Run automation at the right time and rate without overlapping unsafely or losing ownership.
- **Includes:** cron and platform schedulers, service timers, time zones, missed runs, locks, concurrency limits, worker queues, backpressure, deadlines, leases, and run history.
- **Defers:** distributed scheduler administration, real-time systems, and message-broker product deep dives.
- **Outcome:** The reader can schedule work with explicit overlap, retry, and ownership policy and diagnose a missed or duplicated run.

#### Chapter 77 — A Complete CI/CD Automation Lifecycle

- **Purpose:** Integrate code, tests, artifacts, approvals, deployment, and rollback into a trustworthy pipeline.
- **Includes:** triggers, immutable revisions, runners, caches, artifacts, credentials, environments, required checks, promotion, deployment strategies, rollback, auditability, and post-deployment verification.
- **Defers:** one vendor's complete syntax, production platform administration, and organization-wide release governance.
- **Outcome:** The reader can move a manual workflow into CI/CD while explaining identity, evidence, failure, and recovery at every stage.

### Part VI delivery boundary

Examples must run in disposable directories or isolated test systems and expose dry-run or preview behavior where meaningful. Part VI is complete when Chapter 77 automates a stable workflow rather than merely relocating unexplained commands into YAML.

## Part VII — Docker and Containers

Part VII explains containers as constrained processes packaged with filesystem content. It progresses from image construction through runtime state, security, multi-container systems, and orchestration.

### Phase 1 — Images and execution

#### Chapter 78 — Why Containers Work: Isolation, Not Tiny Virtual Machines

- **Purpose:** Build the process, namespace, control-group, and filesystem model beneath container tools.
- **Includes:** host kernels, namespaces, resource control, capabilities, images versus containers, virtual-machine comparison, rootless boundaries, and portability limits.
- **Defers:** kernel implementation, alternate runtimes in depth, and orchestrator administration.
- **Outcome:** The reader can explain what a container isolates, what it shares, and why an image cannot guarantee identical behavior everywhere.

#### Chapter 79 — Images, Layers, Build Contexts, and Caches

- **Purpose:** Explain image identity and construction as content-addressed, layered filesystem state.
- **Includes:** layers, manifests, configuration, build context, cache keys, copy-on-write, image history, architecture variants, and the difference between image and container state.
- **Defers:** registry operation, Dockerfile design, and snapshotter internals.
- **Outcome:** The reader can predict which source change invalidates a build step and locate unexpected image content.

#### Chapter 80 — Reproducible and Efficient Container Builds

- **Purpose:** Turn a Dockerfile or equivalent build recipe into a deterministic, reviewable supply-chain step.
- **Includes:** base-image selection, pinned identities, instruction ordering, multi-stage builds, dependency caching, `.dockerignore`, noninteractive builds, metadata, small-runtime images, and build verification.
- **Defers:** language-specific optimization catalogs, custom builders, and hermetic build research.
- **Outcome:** The reader can build a minimal image whose source, dependencies, and runtime entry point are explainable.

#### Chapter 81 — Registries, Tags, Digests, and Image Provenance

- **Purpose:** Separate convenient names from immutable image identity and distribution trust.
- **Includes:** repositories, registries, tags, digests, push and pull, authentication, retention, multi-platform indexes, vulnerability scanning boundaries, signatures, attestations, SBOM purpose, and promotion.
- **Defers:** registry administration, policy-engine implementation, and complete software-supply-chain frameworks.
- **Outcome:** The reader can deploy by verified identity, trace an image to its build, and avoid treating a mutable tag as evidence.

#### Chapter 82 — Container Processes, Signals, and Lifecycle

- **Purpose:** Apply process lifecycle and service principles inside a container runtime.
- **Includes:** entrypoints and commands, PID 1 behavior, foreground processes, signal forwarding, exit status, stop timeouts, restart policy, init helpers, exec sessions, and immutable replacement.
- **Defers:** orchestration controllers, application framework shutdown details, and process-supervisor product comparisons.
- **Outcome:** The reader can design a container that starts, reports failure, and stops cleanly without hiding its main process.

### Phase 2 — Runtime state and composition

#### Chapter 83 — Container Filesystems, Volumes, and Persistent Data

- **Purpose:** Separate ephemeral writable layers, bind mounts, managed volumes, and external storage.
- **Includes:** mount ownership, copy-up behavior, persistence lifecycle, host-path coupling, permissions, backup boundaries, read-only roots, temporary storage, and database considerations.
- **Defers:** storage-driver internals, Kubernetes storage administration, and database backup design in depth.
- **Outcome:** The reader can place each kind of state deliberately and predict what survives container replacement.

#### Chapter 84 — Container Networking, Ports, and Service Discovery

- **Purpose:** Map container interfaces and published ports onto the host and surrounding network.
- **Includes:** network namespaces, bridge networks, port publishing, loopback scope, DNS-based discovery, ingress and egress, host networking, IPv6 considerations, and troubleshooting from both namespaces.
- **Defers:** CNI plugin internals, service meshes, overlay implementation, and cloud load-balancer administration.
- **Outcome:** The reader can trace a connection from client to host to container and identify where address translation or name resolution occurs.

#### Chapter 85 — Multi-Container Applications with Compose

- **Purpose:** Describe a local multi-service system without turning startup order into false readiness.
- **Includes:** services, networks, volumes, environment, secrets boundaries, dependencies, health checks, profiles, overrides, logs, teardown, and development versus production limits.
- **Defers:** Compose specification exhaustiveness, orchestrator migration recipes, and production cluster management.
- **Outcome:** The reader can run a reproducible local system and explain every service's identity, dependency, state, and endpoint.

#### Chapter 86 — Resource Limits, Health, Logs, and Runtime Diagnosis

- **Purpose:** Operate containers as constrained processes with observable failure modes.
- **Includes:** CPU and memory limits, OOM behavior, process and filesystem inspection, health versus readiness, logs, runtime events, metrics, exec boundaries, and host-versus-container evidence.
- **Defers:** full observability stacks, kernel tracing, and performance benchmarking.
- **Outcome:** The reader can distinguish application failure from runtime policy, host pressure, or health-check design.

### Phase 3 — Security and production direction

#### Chapter 87 — Container Security and Least Privilege

- **Purpose:** Reduce the authority and supply-chain risk of containerized workloads.
- **Includes:** non-root users, capabilities, seccomp and mandatory-policy awareness, read-only filesystems, secret injection, image provenance, device and socket exposure, rootless execution, patching, and escape boundaries.
- **Defers:** offensive container security, custom policy authoring, and compliance certification.
- **Outcome:** The reader can produce a threat-informed hardening plan without assuming a container is a security boundary by default.

#### Chapter 88 — Orchestration Foundations and Kubernetes Mental Models

- **Purpose:** Explain why controllers, desired state, scheduling, and service discovery appear when containers span hosts.
- **Includes:** clusters, nodes, pods, deployments, services, configuration and secrets, reconciliation, health probes, scheduling, rolling updates, stateful boundaries, and Kubernetes vocabulary.
- **Defers:** cluster installation, YAML encyclopedias, advanced controllers, service meshes, and production Kubernetes administration.
- **Outcome:** The reader can translate a multi-container application into orchestration responsibilities and decide whether the complexity is justified.

#### Chapter 89 — A Complete Container Delivery Workflow

- **Purpose:** Integrate build, provenance, test, registry, runtime, networking, persistence, security, and rollback.
- **Includes:** a small application, multi-stage build, dependency and vulnerability checks, immutable tagging, Compose validation, runtime limits, health, logs, secret boundaries, publication simulation, and replacement rollback.
- **Defers:** live production deployment, public registry mutation, and cluster administration.
- **Outcome:** The reader can explain and verify a container artifact from source revision to a safely retired runtime instance.

### Part VII delivery boundary

Labs use disposable images, networks, volumes, and local registries or simulations with explicit cleanup. Part VII is complete when Chapter 89 demonstrates containers as an operated supply chain and process lifecycle, not just `docker run` commands.

## Part VIII — AWS and Cloud-Native Development

Part VIII applies prior operating-system, network, automation, and container models to AWS. It emphasizes shared responsibility, identity-first design, managed-service tradeoffs, infrastructure as code, reliability, cost, and operational ownership.

### Phase 1 — Cloud boundaries and identity

#### Chapter 90 — Cloud Computing, Shared Responsibility, and Service Models

- **Purpose:** Establish what changes—and what does not—when infrastructure becomes an API-driven service.
- **Includes:** IaaS/PaaS/SaaS boundaries, elasticity, regions and Availability Zones, control and data planes, shared responsibility, quotas, failure domains, metering, and managed-service tradeoffs.
- **Defers:** specific AWS service configuration, multicloud strategy, and procurement policy.
- **Outcome:** The reader can assign ownership for security, reliability, data, and cost instead of treating “managed” as “someone else handles everything.”

#### Chapter 91 — AWS Accounts, Organizations, Regions, and Governance

- **Purpose:** Make account and region boundaries deliberate units of ownership, isolation, and cost.
- **Includes:** accounts, Organizations, organizational units, service control policies concept, region selection, Availability Zones, tagging, quotas, budgets, consolidated billing, environments, and break-glass boundaries.
- **Defers:** enterprise landing-zone implementation, tax and contract management, and Control Tower administration.
- **Outcome:** The reader can propose an account and region structure with explicit blast radius, authority, and cost ownership.

#### Chapter 92 — IAM: Principals, Policies, Roles, and Temporary Credentials

- **Purpose:** Apply identity-before-authority to AWS access decisions.
- **Includes:** users, roles, federation, temporary credentials, policy statements, actions and resources, conditions, identity and resource policies, permission boundaries, explicit deny, role assumption, and least privilege.
- **Defers:** external identity-provider administration, every AWS policy type, and automated entitlement-governance products.
- **Outcome:** The reader can trace an AWS authorization decision and design workloads without long-lived embedded credentials.

### Phase 2 — Networking and compute

#### Chapter 93 — VPCs, Subnets, Routes, and Address Planning

- **Purpose:** Map AWS virtual networking to the addressing and routing model from Part V.
- **Includes:** VPC CIDRs, public and private subnets, route tables, internet and NAT gateways, elastic network interfaces, IPv4/IPv6 planning, Availability Zone placement, and route inspection.
- **Defers:** transit architectures, hybrid routing protocols, network-firewall administration, and global enterprise IPAM.
- **Outcome:** The reader can trace an instance path and explain why a subnet is not inherently public or private without its routes and addresses.

#### Chapter 94 — VPC Security, DNS, and Hybrid Connectivity

- **Purpose:** Combine network policy, name resolution, and connections beyond one VPC.
- **Includes:** security groups, network ACLs, VPC endpoints, Route 53 Resolver concepts, peering and Transit Gateway boundaries, VPN and Direct Connect purpose, flow logs, and shared-VPC tradeoffs.
- **Defers:** production hybrid-network implementation, advanced routing, Network Firewall policy, and multi-region mesh design.
- **Outcome:** The reader can locate which AWS control filters or resolves traffic and choose a connectivity pattern by scope and trust.

#### Chapter 95 — EC2, AMIs, and Elastic Compute

- **Purpose:** Treat virtual machines as replaceable, policy-managed compute rather than manually curated servers.
- **Includes:** instance types, AMIs, user data, metadata-service security, roles, EBS attachment, placement, purchase models, Auto Scaling concepts, launch templates, patching, and immutable versus in-place operations.
- **Defers:** every instance family, deep autoscaling tuning, bare metal, and fleet-management administration.
- **Outcome:** The reader can launch and operate an instance with explicit identity, network, storage, bootstrap, replacement, and cost assumptions.

#### Chapter 96 — Elastic Load Balancing, Route 53, and CloudFront

- **Purpose:** Explain how AWS distributes, names, and caches traffic across failure domains.
- **Includes:** load-balancer families, listeners and target groups, health checks, TLS termination, DNS records and routing policy, CDN origins and caching, client identity, session state, and multi-AZ design.
- **Defers:** edge compute, advanced global failover, WAF rule authoring, and detailed cache optimization.
- **Outcome:** The reader can trace an external request to a healthy target and identify where naming, TLS, caching, and load decisions occur.

### Phase 3 — Storage and data

#### Chapter 97 — S3 Object Storage and Data Lifecycle

- **Purpose:** Teach object storage semantics instead of treating buckets as remote disks.
- **Includes:** buckets and keys, request authorization, versioning, consistency model, storage classes, lifecycle rules, encryption, replication, events, multipart operations, static content, and public-access controls.
- **Defers:** data-lake architecture, cross-account enterprise policy, and petabyte-scale transfer operations.
- **Outcome:** The reader can design an S3 data lifecycle with ownership, recovery, access, durability, and cost boundaries.

#### Chapter 98 — EBS, EFS, and Choosing Cloud Storage

- **Purpose:** Compare block, shared file, object, and ephemeral storage by semantics rather than brand.
- **Includes:** EBS volumes and snapshots, attachment and Availability Zone scope, EFS shared filesystems, instance storage, performance dimensions, encryption, backup, resizing, and failure behavior.
- **Defers:** FSx families in depth, storage-gateway administration, RAID tuning, and database-specific storage optimization.
- **Outcome:** The reader can choose storage by access model, latency, sharing, lifecycle, recovery, and cost and explain migration consequences.

#### Chapter 99 — RDS, Aurora, and Managed Relational Databases

- **Purpose:** Separate relational data requirements from the operational work a managed database assumes.
- **Includes:** engines, instances and storage, Multi-AZ, read replicas, backups and point-in-time recovery, parameter boundaries, connections, failover, maintenance, monitoring, encryption, and schema ownership.
- **Defers:** SQL instruction, engine-specific tuning, data warehousing, and zero-downtime migration recipes.
- **Outcome:** The reader can design a relational service with explicit availability, recovery, scaling, connection, and change-management assumptions.

#### Chapter 100 — DynamoDB, Caching, and NoSQL Access Patterns

- **Purpose:** Design key-value and document storage from known access patterns rather than relational habits.
- **Includes:** partition and sort keys, items, indexes, capacity modes, consistency choices, transactions, conditional writes, streams, TTL, hot partitions, DAX/cache boundaries, and cost reasoning.
- **Defers:** single-table design dogma, every NoSQL service, search engines, and analytics platforms.
- **Outcome:** The reader can model a workload's reads and writes, avoid unbounded scans and hot keys, and state consistency tradeoffs.

### Phase 4 — Events, platforms, and operations

#### Chapter 101 — SQS, SNS, EventBridge, and Asynchronous Workflows

- **Purpose:** Choose AWS messaging and event services by delivery, ordering, fan-out, routing, and ownership semantics.
- **Includes:** queues, topics, event buses, visibility timeouts, dead-letter queues, retries, duplicate delivery, ordering boundaries, filters, schemas, backpressure, and Step Functions purpose.
- **Defers:** Kafka/MSK administration, complex workflow language, and organization-wide event governance.
- **Outcome:** The reader can design consumers that tolerate duplicates and failure and select a service without assuming “event-driven” guarantees exactly once.

#### Chapter 102 — Lambda, API Gateway, and Serverless Execution

- **Purpose:** Explain request- and event-driven compute with explicit concurrency, identity, and lifecycle constraints.
- **Includes:** function packages, execution roles, invocation models, cold starts, concurrency, timeouts, retries, destinations, API Gateway integration, configuration, ephemeral state, observability, and cost.
- **Defers:** every serverless service, framework-specific deployment, edge functions, and large serverless architectures.
- **Outcome:** The reader can design a bounded serverless function and predict retry, scaling, state, and failure behavior.

#### Chapter 103 — ECS, EKS, ECR, and Container Platforms on AWS

- **Purpose:** Map container artifacts and orchestration responsibilities onto AWS-managed platforms.
- **Includes:** ECR identity, ECS tasks and services, Fargate versus EC2, EKS responsibility boundaries, networking, roles, load balancing, secrets, logs, scaling, and platform-selection criteria.
- **Defers:** production EKS administration, service meshes, custom controllers, and every ECS deployment option.
- **Outcome:** The reader can choose an AWS container platform and trace image, identity, network, runtime, scaling, and operational ownership.

#### Chapter 104 — Encryption, Secrets, Configuration, and Cloud Observability

- **Purpose:** Connect key management and runtime configuration to logs, metrics, traces, audit, and security evidence.
- **Includes:** KMS concepts, envelope encryption, Secrets Manager, Parameter Store, rotation boundaries, CloudWatch, CloudTrail, AWS Config purpose, alarms, log retention, correlation, and redaction.
- **Defers:** cryptographic key ceremonies, SIEM administration, organization-wide telemetry platforms, and compliance certification.
- **Outcome:** The reader can keep secrets out of artifacts, trace control-plane and workload events, and define evidence retention without exposing sensitive values.

#### Chapter 105 — Infrastructure as Code and a Complete AWS Delivery Lifecycle

- **Purpose:** Integrate governance, identity, network, compute, data, observability, deployment, reliability, and cost through reviewed infrastructure code.
- **Includes:** declarative state, plans and change sets, CloudFormation/CDK/Terraform boundaries, state ownership, modules, policy checks, drift, environment promotion, deployment strategies, rollback, backups, SLOs, cost review, and teardown.
- **Defers:** one tool's complete language, live production deployment, enterprise platform engineering, and multicloud abstraction.
- **Outcome:** The reader can review and safely apply a small AWS system, verify service and business outcomes, and account for security, reliability, recovery, and cost.

### Part VIII delivery boundary

AWS examples favor local validation, emulation where faithful, free or low-cost isolated accounts, budgets, and explicit teardown. Part VIII is complete when Chapter 105 treats cloud infrastructure as owned, reviewed software with continuing operational and cost responsibility.

## Part IX — System Design

Part IX develops a repeatable design method for systems whose requirements exceed one component. It emphasizes explicit constraints, tradeoffs, failure modes, evolution, and decision records over interview-style memorization.

### Phase 1 — Requirements and boundaries

#### Chapter 106 — From Requirements to a System Model

- **Purpose:** Turn an ambiguous product request into measurable functional and quality requirements.
- **Includes:** actors, use cases, workloads, data, latency, availability, durability, security, compliance, cost, growth, constraints, assumptions, and success measures.
- **Defers:** component selection, diagramming notation catalogs, and estimation interview tricks.
- **Outcome:** The reader can produce a bounded problem statement and identify the uncertainties that could change the architecture.

#### Chapter 107 — Interfaces, Contracts, and Evolution

- **Purpose:** Design boundaries that components and teams can change without coordinated rewrites.
- **Includes:** APIs and events, preconditions and postconditions, schemas, errors, idempotency, versioning, compatibility, deprecation, consumer ownership, and contract testing.
- **Defers:** protocol-specific API tutorials, governance bureaucracy, and formal specification languages.
- **Outcome:** The reader can define a stable interface, predict breaking changes, and plan an evidence-based migration.

#### Chapter 108 — Data Models and Storage Selection

- **Purpose:** Choose representations and storage engines from access, consistency, lifecycle, and operational requirements.
- **Includes:** entities and relationships, keys, normalization and denormalization, relational, key-value, document, graph, search, object, and time-series models, indexing, retention, and migration.
- **Defers:** database product administration, query-language instruction, and one universal polyglot-persistence recipe.
- **Outcome:** The reader can map each critical access pattern to a data model and explain the cost of duplicated or derived state.

### Phase 2 — Scale, state, and coordination

#### Chapter 109 — Capacity, Partitioning, and Horizontal Scale

- **Purpose:** Derive scale decisions from workload estimates and bottleneck evidence.
- **Includes:** throughput and concurrency estimates, Little's Law intuition, vertical versus horizontal scale, partition keys, sharding, hotspots, replication purpose, stateless tiers, autoscaling lag, and rebalancing.
- **Defers:** precise capacity planning, distributed-database internals, and vendor-specific scaling limits.
- **Outcome:** The reader can estimate an order-of-magnitude design, identify its first bottleneck, and choose a partition strategy with known failure modes.

#### Chapter 110 — Consistency, Transactions, and Concurrent Change

- **Purpose:** Make correctness guarantees explicit when state is read and written concurrently or across replicas.
- **Includes:** invariants, isolation anomalies, optimistic and pessimistic control, transactions, replication lag, linearizability and eventual consistency intuition, conflict resolution, and read-your-writes.
- **Defers:** formal distributed-systems proofs, database-engine implementation, and consensus algorithms in depth.
- **Outcome:** The reader can state the consistency required by each invariant and recognize when an asynchronous design violates it.

#### Chapter 111 — Caching as a Consistency Tradeoff

- **Purpose:** Use caches deliberately without treating them as free speed.
- **Includes:** cache locations, keys, TTLs, invalidation, cache-aside and write strategies, stampedes, negative caching, eviction, consistency, observability, and bypass/failure behavior.
- **Defers:** CPU cache architecture, CDN product configuration, and one prescribed caching library.
- **Outcome:** The reader can explain which source is authoritative, when cached data may be stale, and how the system behaves when the cache fails.

#### Chapter 112 — Messaging, Events, and Asynchronous Workflows

- **Purpose:** Design work that crosses time and service boundaries with explicit delivery and ownership.
- **Includes:** commands versus events, queues and logs, ordering, partitioning, duplicate delivery, outbox pattern, sagas and compensation, dead letters, backpressure, schema evolution, and replay.
- **Defers:** broker administration, event-sourcing dogma, stream-processing internals, and distributed transactions across arbitrary systems.
- **Outcome:** The reader can create an asynchronous workflow whose retries, duplicates, ordering, and partial failures preserve business invariants.

#### Chapter 113 — Coordination, Leadership, and Distributed Time

- **Purpose:** Explain why clocks, leases, locks, and membership become difficult across machines.
- **Includes:** partial failure, clock skew, logical ordering, leases, fencing tokens, leader election purpose, quorum intuition, consensus boundaries, split brain, and managed-coordination services.
- **Defers:** implementing consensus algorithms, formal proofs, and custom distributed-lock services.
- **Outcome:** The reader can identify when coordination is necessary, reject unsafe timestamp or lock assumptions, and prefer proven managed primitives.

### Phase 3 — Resilience, security, and decisions

#### Chapter 114 — Resilience, Timeouts, Retries, and Failure Containment

- **Purpose:** Keep a local failure from becoming an unbounded system failure.
- **Includes:** failure modes, deadlines, timeout budgets, retry storms, backoff and jitter, circuit breakers, bulkheads, load shedding, graceful degradation, health, redundancy, recovery objectives, and chaos experiments.
- **Defers:** disaster-recovery runbooks for one platform, formal reliability modeling, and chaos-tool administration.
- **Outcome:** The reader can design bounded failure behavior and prove that recovery mechanisms do not amplify the incident.

#### Chapter 115 — Security, Privacy, and Multi-Tenant Boundaries

- **Purpose:** Integrate threat, identity, data, and tenant isolation into architecture rather than add controls afterward.
- **Includes:** assets, actors, trust boundaries, threat modeling, authentication and authorization, least privilege, encryption, secret lifecycle, audit, privacy and retention, abuse cases, and tenant isolation.
- **Defers:** compliance-framework implementation, cryptographic engineering, penetration testing, and legal advice.
- **Outcome:** The reader can produce a threat-informed design and connect each control to a concrete risk and owner.

#### Chapter 116 — Architecture Decisions, Tradeoffs, and Evolution

- **Purpose:** Preserve why a design was chosen and how it can change as evidence improves.
- **Includes:** ADRs, options, forces, assumptions, reversibility, migration seams, build-versus-buy, technical debt, deprecation, fitness functions, review cadence, and diagram maintenance.
- **Defers:** enterprise architecture governance, portfolio management, and one diagramming standard.
- **Outcome:** The reader can write a decision record that enables future engineers to revise the design without rediscovering its constraints.

#### Chapter 117 — A Complete System Design Review

- **Purpose:** Integrate requirements, interfaces, data, scale, consistency, messaging, resilience, security, operations, and cost into one reviewable proposal.
- **Includes:** a realistic service scenario, estimates, diagrams, API and data contracts, failure analysis, deployment model, observability, recovery, threat model, alternatives, ADRs, risks, and staged evolution.
- **Defers:** production implementation, vendor procurement, and claims that one reference design is universally correct.
- **Outcome:** The reader can defend a design with evidence, identify its weakest assumptions, and propose the next validation experiment.

### Part IX delivery boundary

Each design chapter must show competing options and failure consequences, not only a preferred pattern. Part IX is complete when Chapter 117 can be reviewed by product, application, security, data, and operations stakeholders using one shared model.

## Part X — Performance, Debugging, and Observability

Part X turns uncertainty into evidence. It moves from reproducible debugging through telemetry and profiling to incident response, learning, and a complete cross-layer investigation.

### Phase 1 — Reproduction and observability

#### Chapter 118 — Debugging as Hypothesis Testing

- **Purpose:** Replace random changes with a scientific loop of observation, hypothesis, prediction, experiment, and revision.
- **Includes:** symptom definition, scope, timelines, known-good comparisons, invariants, binary search, evidence preservation, controlled variables, confidence, and stopping criteria.
- **Defers:** language-specific debuggers, performance profiling, and incident command.
- **Outcome:** The reader can maintain a ranked hypothesis set and design the smallest experiment that distinguishes alternatives.

#### Chapter 119 — Reproducing Failures and Building Minimal Cases

- **Purpose:** Separate the failing behavior from incidental environment and data.
- **Includes:** deterministic reproduction, environment capture, input minimization, bisection, feature flags, race and timing concerns, record/replay boundaries, disposable environments, and regression fixtures.
- **Defers:** formal delta debugging, production traffic replay, and vendor-specific test labs.
- **Outcome:** The reader can produce a safe minimal reproduction or state precisely why the failure remains production-only.

#### Chapter 120 — Logs and Structured Events

- **Purpose:** Design logs as bounded operational evidence rather than narrative print statements.
- **Includes:** event schemas, severity, timestamps, correlation and request IDs, context, structured fields, errors and stack traces, redaction, sampling, retention, cardinality, and log-level change policy.
- **Defers:** log-vendor administration, organization-wide schemas, and SIEM operation.
- **Outcome:** The reader can instrument a workflow so one failed request can be reconstructed without exposing secrets or drowning in noise.

#### Chapter 121 — Metrics, SLIs, SLOs, and Actionable Alerts

- **Purpose:** Measure system behavior against user outcomes and alert only when action is required.
- **Includes:** counters, gauges, histograms, rates, dimensions, cardinality, RED/USE methods, SLIs, SLOs, error budgets, burn rates, dashboards, alert ownership, and missing-data behavior.
- **Defers:** one metrics platform, statistical process control in depth, and organization-wide reliability governance.
- **Outcome:** The reader can define a service objective, choose valid measurements, and create an alert with a clear response.

#### Chapter 122 — Traces, Profiles, and Causal Context

- **Purpose:** Connect work across threads and services while distinguishing request tracing from resource profiling.
- **Includes:** spans and context propagation, sampling, baggage risks, trace-log-metric correlation, continuous versus on-demand profiling, stack samples, overhead, clock issues, and privacy.
- **Defers:** telemetry vendor configuration, tracing protocol internals, and profiling every language runtime.
- **Outcome:** The reader can choose tracing or profiling for the question and interpret missing or sampled evidence honestly.

### Phase 2 — Performance investigation

#### Chapter 123 — CPU Profiling and Concurrency Bottlenecks

- **Purpose:** Locate where execution time and runnable contention accumulate before optimizing code.
- **Includes:** sampling versus instrumentation, wall versus CPU time, call trees and flame graphs, hot paths, locks, context switches, thread pools, parallelism limits, benchmark distortion, and before/after validation.
- **Defers:** assembly optimization, compiler internals, real-time scheduling, and language-specific profiler catalogs.
- **Outcome:** The reader can identify a CPU or contention bottleneck and demonstrate an improvement in workload-level terms.

#### Chapter 124 — Memory, Allocation, and Resource-Leak Diagnosis

- **Purpose:** Distinguish retained application objects, resident growth, fragmentation, caches, handles, and true leaks.
- **Includes:** heap and native memory, allocation rate, object retention, garbage collection, RSS/working set, file descriptors and handles, snapshots, growth experiments, OOM evidence, and containment limits.
- **Defers:** allocator implementation, garbage-collector tuning catalogs, kernel leaks, and memory forensics.
- **Outcome:** The reader can attribute resource growth to an owner and avoid calling every high-water mark a leak.

#### Chapter 125 — I/O, Network, and Database Performance

- **Purpose:** Diagnose latency beyond CPU by following queues and waits through storage, network, and data services.
- **Includes:** latency decomposition, throughput, concurrency, queue depth, batching, cache effects, disk and filesystem waits, network round trips, connection pools, query plans, indexes, lock waits, and downstream limits.
- **Defers:** storage firmware tuning, network benchmark engineering, database-engine internals, and vendor-specific performance recipes.
- **Outcome:** The reader can locate the dominant wait boundary and choose an experiment that changes one capacity or latency variable.

#### Chapter 126 — Load Testing, Capacity Planning, and Failure Injection

- **Purpose:** Validate behavior under expected and exceptional demand before users discover the limit.
- **Includes:** workload models, open versus closed load, warm-up, coordinated omission, percentiles, saturation, capacity headroom, scaling lag, soak tests, fault injection, recovery verification, safety limits, and cost.
- **Defers:** internet-scale traffic generation, destructive production chaos, and precise forecasting models.
- **Outcome:** The reader can run a bounded representative test, identify the first limit, and connect capacity to an SLO and recovery objective.

### Phase 3 — Incidents and learning

#### Chapter 127 — Incident Response and Operational Coordination

- **Purpose:** Stabilize service while preserving evidence, ownership, communication, and safe decision-making.
- **Includes:** severity, roles, command, timelines, containment, mitigation versus repair, change control, communication, handoffs, evidence, escalation, recovery verification, and security-incident boundaries.
- **Defers:** one organization's incident policy, legal notification advice, and emergency-service procedures.
- **Outcome:** The reader can participate in or lead a technical incident without multiplying changes or losing accountability.

#### Chapter 128 — Post-Incident Learning and Continuous Improvement

- **Purpose:** Convert failures and near misses into durable improvements without blame or shallow action items.
- **Includes:** timelines, contributing conditions, counterfactual caution, five-whys limits, systemic causes, detection gaps, action ownership, priority, verification, runbook changes, recurring-pattern analysis, and knowledge maintenance.
- **Defers:** human-resources processes, legal investigation, and universal postmortem templates.
- **Outcome:** The reader can produce an evidence-based review whose actions reduce recurrence or impact and are later verified.

#### Chapter 129 — A Complete Cross-Layer Engineering Investigation

- **Purpose:** Complete the first-edition curriculum by investigating a realistic failure from user symptom through application, network, operating system, cloud, and design layers.
- **Includes:** reproduction, hypothesis management, Git history, automation evidence, container and cloud context, logs/metrics/traces, CPU/memory/I/O profiles, authorization, mitigation, root contributors, design revision, and post-incident actions.
- **Defers:** live production intervention and the claim that one lab represents every incident.
- **Outcome:** The reader can lead an end-to-end investigation, defend conclusions with evidence, recover safely, and feed learning back into the handbook.

### Part X delivery boundary

Performance claims require reproducible measurements and debugging claims must distinguish observation from inference. Part X and the first-edition chapter sequence are complete when Chapter 129 integrates the handbook into one evidence-driven engineering workflow.

## Planned Appendix — Engineering Patterns

A reusable catalog of patterns that recur across technologies. These are unnumbered reference entries rather than additional chapters:

- **Layered Systems:** locate responsibility and failure at the narrowest abstraction boundary.
- **Separation of Concerns:** keep policy, mechanism, data, presentation, and lifecycle independently understandable.
- **Composition over Complexity:** build larger behavior from bounded components with inspectable contracts.
- **Stable Interfaces:** protect consumers from internal change while evolving contracts deliberately.
- **Least Privilege:** grant the minimum operation, resource, scope, and duration required.
- **Identity Before Authority:** establish which principal is acting before analyzing what it may do.
- **Small Tools, Loosely Coupled:** prefer focused capabilities connected through explicit data and failure boundaries.
- **Automate Repetitive Work:** automate only after observing, simplifying, and stabilizing the manual process.
- **Explicit State and Ownership:** make current state, desired state, authority, and cleanup responsibility visible.
- **Failure Containment:** bound time, retries, queues, resources, dependencies, and blast radius.
- **Convention over Unnecessary Configuration:** use a documented default until requirements justify another choice.

### First-edition completion boundary

The first edition comprises Chapters 1–129 plus the Engineering Patterns appendix. Completion requires all planned chapters, cross-part links, tested or reasoned examples, primary-source references, one integration chapter per part, a whole-book editorial and technical audit, generated publication formats, and a tagged release. Completion establishes a maintained baseline; it does not freeze the content.

## Roadmap maintenance

Major structural changes should update:

- `ARCHITECTURE.md`
- `LEARNING_ROADMAP.md`
- `SUMMARY.md`
- `DECISIONS.md` when the change reflects a durable decision

This keeps the plan visible and prevents the curriculum from depending on conversation memory.
