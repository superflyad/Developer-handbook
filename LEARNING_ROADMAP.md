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

Navigation, file operations, search, text processing, redirection, shell expansion, job control, permissions in practice, package management, shell configuration, and efficient command-line workflows.

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