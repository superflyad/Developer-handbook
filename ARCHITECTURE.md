# Handbook Architecture

## Purpose

The Developer Handbook is a living, version-controlled engineering knowledge system. It is not a chronological transcript of conversations and not a static book that becomes obsolete after publication.

Its purpose is to preserve durable mental models, professional workflows, technical judgment, and lessons learned throughout a software engineering career.

> Understand systems. Build mental models. Automate everything worth repeating.

## Source of truth

Markdown in this repository is the canonical source.

PDF, Word, ebook, and website editions are generated publication formats. They must not become independent versions of the handbook.

## Content lifecycle

Every chapter follows this lifecycle:

```text
Learn → Refine → Publish → Apply → Revisit
```

### Learn

Explore the concept freely. Ask questions, challenge assumptions, and identify gaps.

### Refine

Turn the discussion into a coherent chapter. Remove conversational repetition, improve examples, verify the mental model, and connect it to earlier material.

### Publish

Create a focused feature branch, update the chapter and table of contents, and open a draft pull request.

### Apply

Use the concept in real engineering work, exercises, projects, debugging, or automation.

### Revisit

Update the existing chapter as practical experience deepens. Prefer improving the canonical chapter over creating duplicate explanations.

## Repository structure

```text
Developer-handbook/
├── README.md
├── PREFACE.md
├── PHILOSOPHY.md
├── HOW_TO_USE_THIS_HANDBOOK.md
├── LEARNING_ROADMAP.md
├── SUMMARY.md
├── ARCHITECTURE.md
├── EDITORIAL_GUIDE.md
├── DECISIONS.md
├── handbook/
│   ├── foundations/
│   ├── terminal/
│   ├── git/
│   ├── operating-systems/
│   ├── networking/
│   ├── automation/
│   ├── containers/
│   ├── cloud/
│   ├── system-design/
│   └── debugging-performance-observability/
└── appendices/
    └── engineering-patterns/
```

Directories may be introduced when their first chapter is published. Empty scaffolding is unnecessary.

## Book structure

The handbook is organized into Parts and Chapters.

- **Parts** define major areas of engineering capability.
- **Chapters** teach one coherent concept or tightly connected set of concepts.
- **Appendices** collect reusable references, patterns, checklists, and comparisons.

The repository should use **Chapter**, not **Lesson**, for published material. Conversation may still use the word lesson while learning.

## Part I — Foundations: Building the Machine

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

Part I builds the operating-system mental model before introducing command-focused productivity.

## Long-term roadmap

### Part II — Mastering the Unix Environment

- Chapter 12 — Command-Line Grammar and Getting Help
- Chapter 13 — Navigation and Path Resolution
- Chapter 14 — Safe File and Directory Operations
- Chapter 15 — Finding Files and Inspecting Metadata
- Chapter 16 — Searching Text and Working with Regular Expressions
- Chapter 17 — Reading and Transforming Text
- Chapter 18 — Quoting, Expansion, and Redirection in Practice
- Chapter 19 — Processes, Jobs, and Signals
- Chapter 20 — Permissions in Daily Work
- Chapter 21 — Installing and Managing Software
- Chapter 22 — Shell Startup, Configuration, and `PATH`
- Chapter 23 — Building an Efficient Command-Line Workflow

Part II converts the mental model from Part I into practical fluency. It progresses through command literacy, filesystem work, discovery, text processing, shell evaluation, runtime control, permissions, software management, environment ownership, and an integrated workflow. Detailed inclusion and deferral boundaries live in `LEARNING_ROADMAP.md`.

### Part III — Git Mastery

- Chapter 24 — Why Git Works: Repositories, Objects, and History
- Chapter 25 — The Working Tree, Index, and `HEAD`
- Chapter 26 — Staging and Making Coherent Commits
- Chapter 27 — Reading History and Investigating Changes
- Chapter 28 — Tracked Content, Ignore Rules, and Portability
- Chapter 29 — Branches, References, Tags, and Detached `HEAD`
- Chapter 30 — Remotes, Tracking, Fetching, and Pushing
- Chapter 31 — Merging and Resolving Conflicts
- Chapter 32 — Rebasing, Cherry-Picking, and History Rewriting
- Chapter 33 — Undoing Changes and Recovering Work
- Chapter 34 — Pull Requests, Review, and Merge Policy
- Chapter 35 — Worktrees and Parallel Development
- Chapter 36 — A Complete Git Change Lifecycle

Part III progresses from local state and history to references and integration, then to recovery and collaboration. Detailed purpose, inclusion, deferral, and outcome boundaries are in `LEARNING_ROADMAP.md`.

### Part IV — Filesystems and Operating Systems

- Chapter 37 — Filesystems as Namespaces and Persistent State
- Chapter 38 — The Storage Stack: Devices, Volumes, Filesystems, and Mounts
- Chapter 39 — File Identity, Hard Links, and Symbolic Links
- Chapter 40 — Metadata, Timestamps, Attributes, and Extended Data
- Chapter 41 — Space, Allocation, Caching, and Durability
- Chapter 42 — Process Creation, Execution, and Lifecycle
- Chapter 43 — Scheduling, Priorities, and Resource Accounting
- Chapter 44 — Virtual Memory and Process Address Spaces
- Chapter 45 — Interprocess Communication and Coordination
- Chapter 46 — Services, Daemons, and Background Work
- Chapter 47 — Boot, Startup, and Shutdown
- Chapter 48 — Identity, Permissions, ACLs, and Privilege Boundaries
- Chapter 49 — A Cross-Platform Operating-System Investigation

Part IV progresses from filesystem identity and storage to process resources, managed startup, and authorization. It ends with a read-mostly investigation that preserves comparable questions without pretending Linux, macOS, and Windows expose identical implementations. Detailed boundaries are in `LEARNING_ROADMAP.md`.

### Part V — Networking

- Chapter 50 — A Packet's Journey Through the Network Stack
- Chapter 51 — Links, Frames, Ethernet, and Wi-Fi
- Chapter 52 — IP Addressing and Subnetting
- Chapter 53 — Host Configuration, DHCP, ARP, and Neighbor Discovery
- Chapter 54 — Routing, Gateways, and Path Selection
- Chapter 55 — DNS and Name Resolution
- Chapter 56 — Sockets, Ports, and Endpoint Ownership
- Chapter 57 — UDP, Datagrams, and Message Boundaries
- Chapter 58 — TCP Reliability, Flow Control, and Connection State
- Chapter 59 — HTTP Semantics and API Behavior
- Chapter 60 — TLS, Certificates, and Public-Key Trust
- Chapter 61 — SSH, Tunnels, and Remote Access Boundaries
- Chapter 62 — Firewalls, NAT, Proxies, and Traffic Distribution
- Chapter 63 — A Complete Network Troubleshooting Workflow

### Part VI — Automation and Scripting

- Chapter 64 — Deciding What to Automate
- Chapter 65 — Reliable Shell Script Execution
- Chapter 66 — Shell Control Flow, Functions, and Error Handling
- Chapter 67 — Structured Inputs, Outputs, and Data Formats
- Chapter 68 — Python Programs, Modules, and the Standard Library
- Chapter 69 — Files, Paths, Text, and Structured Data in Python
- Chapter 70 — Subprocesses, HTTP Clients, and External Boundaries
- Chapter 71 — Python Environments, Dependencies, and Packaging
- Chapter 72 — Configuration, Secrets, Logging, and Observability
- Chapter 73 — Testing, Linting, and Type Checking Automation
- Chapter 74 — Idempotency, State, Retries, and Recovery
- Chapter 75 — Task Runners, Builds, and Repeatable Environments
- Chapter 76 — Scheduling, Concurrency, and Work Queues
- Chapter 77 — A Complete CI/CD Automation Lifecycle

### Part VII — Docker and Containers

- Chapter 78 — Why Containers Work: Isolation, Not Tiny Virtual Machines
- Chapter 79 — Images, Layers, Build Contexts, and Caches
- Chapter 80 — Reproducible and Efficient Container Builds
- Chapter 81 — Registries, Tags, Digests, and Image Provenance
- Chapter 82 — Container Processes, Signals, and Lifecycle
- Chapter 83 — Container Filesystems, Volumes, and Persistent Data
- Chapter 84 — Container Networking, Ports, and Service Discovery
- Chapter 85 — Multi-Container Applications with Compose
- Chapter 86 — Resource Limits, Health, Logs, and Runtime Diagnosis
- Chapter 87 — Container Security and Least Privilege
- Chapter 88 — Orchestration Foundations and Kubernetes Mental Models
- Chapter 89 — A Complete Container Delivery Workflow

### Part VIII — AWS and Cloud-Native Development

- Chapter 90 — Cloud Computing, Shared Responsibility, and Service Models
- Chapter 91 — AWS Accounts, Organizations, Regions, and Governance
- Chapter 92 — IAM: Principals, Policies, Roles, and Temporary Credentials
- Chapter 93 — VPCs, Subnets, Routes, and Address Planning
- Chapter 94 — VPC Security, DNS, and Hybrid Connectivity
- Chapter 95 — EC2, AMIs, and Elastic Compute
- Chapter 96 — Elastic Load Balancing, Route 53, and CloudFront
- Chapter 97 — S3 Object Storage and Data Lifecycle
- Chapter 98 — EBS, EFS, and Choosing Cloud Storage
- Chapter 99 — RDS, Aurora, and Managed Relational Databases
- Chapter 100 — DynamoDB, Caching, and NoSQL Access Patterns
- Chapter 101 — SQS, SNS, EventBridge, and Asynchronous Workflows
- Chapter 102 — Lambda, API Gateway, and Serverless Execution
- Chapter 103 — ECS, EKS, ECR, and Container Platforms on AWS
- Chapter 104 — Encryption, Secrets, Configuration, and Cloud Observability
- Chapter 105 — Infrastructure as Code and a Complete AWS Delivery Lifecycle

### Part IX — System Design

- Chapter 106 — From Requirements to a System Model
- Chapter 107 — Interfaces, Contracts, and Evolution
- Chapter 108 — Data Models and Storage Selection
- Chapter 109 — Capacity, Partitioning, and Horizontal Scale
- Chapter 110 — Consistency, Transactions, and Concurrent Change
- Chapter 111 — Caching as a Consistency Tradeoff
- Chapter 112 — Messaging, Events, and Asynchronous Workflows
- Chapter 113 — Coordination, Leadership, and Distributed Time
- Chapter 114 — Resilience, Timeouts, Retries, and Failure Containment
- Chapter 115 — Security, Privacy, and Multi-Tenant Boundaries
- Chapter 116 — Architecture Decisions, Tradeoffs, and Evolution
- Chapter 117 — A Complete System Design Review

### Part X — Performance, Debugging, and Observability

- Chapter 118 — Debugging as Hypothesis Testing
- Chapter 119 — Reproducing Failures and Building Minimal Cases
- Chapter 120 — Logs and Structured Events
- Chapter 121 — Metrics, SLIs, SLOs, and Actionable Alerts
- Chapter 122 — Traces, Profiles, and Causal Context
- Chapter 123 — CPU Profiling and Concurrency Bottlenecks
- Chapter 124 — Memory, Allocation, and Resource-Leak Diagnosis
- Chapter 125 — I/O, Network, and Database Performance
- Chapter 126 — Load Testing, Capacity Planning, and Failure Injection
- Chapter 127 — Incident Response and Operational Coordination
- Chapter 128 — Post-Incident Learning and Continuous Improvement
- Chapter 129 — A Complete Cross-Layer Engineering Investigation

Parts V–X contain 80 planned chapters. The first edition contains 129 chapters total plus the Engineering Patterns appendix. The detailed purpose, inclusion, deferral, outcome, and delivery boundaries live in `LEARNING_ROADMAP.md`.

## Engineering Patterns appendix

The handbook maintains an appendix of recurring patterns that appear across technologies:

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
- Convention over unnecessary configuration

Chapters and integration reviews should link to these patterns when the connection improves navigation or reasoning.

## Publishing workflow

```text
Discuss → Approve → Branch → Commit → Draft PR → Review → Squash merge
```

Repository conventions:

- Branch: `agent/<focused-description>`
- Commit: concise Conventional Commit style, usually `docs: ...`
- Pull request: draft by default
- Merge: squash unless preserving separate commits has clear value
- Scope: one coherent chapter, revision, or structural change per PR

## Versioning

Git history is the primary revision history.

Explicit chapter version numbers are optional and should only be introduced when they provide value beyond Git history. Major conceptual rewrites should be clearly described in commit and pull-request messages.

## Quality boundary

Conversation is exploratory. The repository is curated.

Do not publish raw dialogue, unsupported claims, unnecessary repetition, or tool-specific trivia that lacks durable engineering value.
