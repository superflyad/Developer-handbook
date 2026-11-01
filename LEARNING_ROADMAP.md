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

Protocols, addressing, routing, DNS, ports, sockets, HTTP, TLS, SSH, firewalls, troubleshooting, and cloud networking.

## Part VI — Automation and Scripting

Shell scripting, Python automation, task runners, repeatable environment setup, scheduling, CI/CD, and replacing manual workflows with reliable systems.

## Part VII — Docker and Containers

Images, layers, registries, namespaces, control groups, networking, volumes, security, orchestration foundations, and production container practices.

## Part VIII — AWS and Cloud-Native Development

Identity, networking, compute, storage, databases, observability, infrastructure as code, deployment patterns, reliability, cost, and operational ownership.

## Part IX — System Design

Requirements, tradeoffs, interfaces, data models, scalability, consistency, caching, messaging, resilience, security, and architecture decision records.

## Part X — Performance, Debugging, and Observability

Systematic debugging, profiling, metrics, logs, traces, failure analysis, capacity planning, incident response, and continuous engineering improvement.

## Planned Appendix — Engineering Patterns

A reusable catalog of patterns that recur across technologies:

- Layered systems
- Separation of concerns
- Composition over complexity
- Stable interfaces
- Least privilege
- Identity before authority
- Small tools, loosely coupled
- Automate repetitive work
- Explicit state and ownership
- Failure containment

## Roadmap maintenance

Major structural changes should update:

- `ARCHITECTURE.md`
- `LEARNING_ROADMAP.md`
- `SUMMARY.md`
- `DECISIONS.md` when the change reflects a durable decision

This keeps the plan visible and prevents the curriculum from depending on conversation memory.
