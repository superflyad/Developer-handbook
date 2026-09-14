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

The object model, working tree, index, commits, branches, merging, rebasing, remotes, recovery, collaboration, and professional repository workflows.

## Part IV — Filesystems and Operating Systems

Storage, mounting, links, metadata, processes, scheduling, memory, services, startup, permissions, and platform differences across macOS, Linux, and Windows.

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
