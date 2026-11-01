# Engineering Patterns

Technologies change faster than the reasoning structures beneath them. A shell pipeline, Git workflow, network protocol, container platform, cloud architecture, distributed system, and incident response can look unrelated while depending on the same ideas: boundaries, identity, explicit state, bounded failure, and stable contracts.

This appendix names eleven patterns that recur throughout the handbook. They are not laws or architecture brands. Each is a reusable question set for understanding an unfamiliar system, reviewing a design, diagnosing a failure, or deciding what to automate.

Use the entries in either direction:

- when a chapter introduces a tool, ask which pattern explains its useful shape;
- when a new technology appears, use the patterns to locate its identities, interfaces, state, ownership, and failure boundaries;
- when a design feels complicated, identify which pattern is missing or being over-applied;
- when an incident recurs, ask whether the local fix left a cross-cutting pattern unresolved.

Patterns interact. Least privilege depends on identity before authority. Composition depends on stable interfaces. Automation depends on explicit state and ownership. Failure containment depends on separation of concerns and bounded interfaces. Convention reduces configuration only when the default remains visible and changeable.

## Pattern map

| Pattern | Primary question | Typical failure when absent |
| --- | --- | --- |
| [Layered Systems](#layered-systems) | Which boundary owns this behavior? | symptoms are blamed on the wrong layer |
| [Separation of Concerns](#separation-of-concerns) | Which concerns must change independently? | one change silently alters unrelated policy or lifecycle |
| [Composition over Complexity](#composition-over-complexity) | Can bounded parts express the larger behavior? | one opaque component owns too many reasons to change |
| [Stable Interfaces](#stable-interfaces) | What contract protects consumers from internal change? | implementation change becomes ecosystem breakage |
| [Least Privilege](#least-privilege) | What is the minimum authority for this operation? | compromise or error has an unnecessary blast radius |
| [Identity Before Authority](#identity-before-authority) | Which principal, artifact, object, or state is this exactly? | permission is reasoned about for the wrong identity |
| [Small Tools, Loosely Coupled](#small-tools-loosely-coupled) | Can focused capabilities connect through explicit data? | reuse requires adopting an entire coupled system |
| [Automate Repetitive Work](#automate-repetitive-work) | Is the manual contract understood and stable enough? | automation reproduces confusion faster and at scale |
| [Explicit State and Ownership](#explicit-state-and-ownership) | What is true now, what should be true, and who reconciles it? | drift, duplicate work, and abandoned cleanup |
| [Failure Containment](#failure-containment) | Where are time, work, resources, and blast radius bounded? | one fault amplifies across the system |
| [Convention over Unnecessary Configuration](#convention-over-unnecessary-configuration) | Is a documented default sufficient for the common case? | every user must rediscover and maintain the same choice |

## Layered Systems

### Intent

Organize a system as abstraction boundaries in which each layer offers a contract upward and relies on a contract below. Diagnose behavior at the narrowest layer that can own it without losing the end-to-end journey.

### Forces

Engineers need to reason about complex systems without loading every implementation detail at once. Layers make local reasoning possible, but real requests cross them and failures can surface far from their source. Encapsulation competes with the need for cross-layer evidence.

### Apply the pattern

1. Draw the journey from user intent to the final state or effect.
2. Name each boundary, its inputs, outputs, owner, and guarantees.
3. Distinguish a layer's service from its implementation.
4. Locate the first layer where observed behavior diverges from the contract.
5. Test that boundary while checking assumptions immediately above and below it.
6. Preserve a correlation identity across layers when one operation spans them.

A web timeout may involve DNS, TCP, TLS, a load balancer, application admission, a connection pool, a query, storage, and response delivery. “The network is slow” skips the layered model. A trace and latency budget identify which boundary accumulated time.

### Warning signs

- a symptom is assigned to a layer before the request path is drawn;
- the same responsibility exists at several layers with unclear precedence;
- an abstraction hides the evidence needed to verify its contract;
- local success is treated as end-to-end success;
- responders collect every layer's metrics without a discriminating hypothesis.

Layering becomes harmful when it creates pass-through tiers, hides necessary control, or forces a change through every layer. Remove boundaries that own no distinct contract.

### Handbook examples

- [Programs, Processes, and the Kernel](../foundations/04-programs-processes-and-the-kernel.md) separates program, process, and kernel responsibility.
- [A Packet's Journey Through the Network Stack](../networking/50-a-packets-journey-through-the-network-stack.md) follows data across protocol layers.
- [Why Containers Work](../containers/78-why-containers-work-isolation-not-tiny-virtual-machines.md) distinguishes process isolation from virtual machines.
- [A Complete Cross-Layer Engineering Investigation](../observability/129-a-complete-cross-layer-engineering-investigation.md) reconnects the layers through one user-visible failure.

### Related patterns

[Separation of Concerns](#separation-of-concerns), [Stable Interfaces](#stable-interfaces), and [Failure Containment](#failure-containment).

## Separation of Concerns

### Intent

Keep responsibilities that change for different reasons independently understandable and testable. Separate policy from mechanism, identity from authority, data from presentation, build from runtime, declaration from execution, and mitigation from durable repair.

### Forces

Combining concerns can make the first implementation shorter. Over time, different owners, risk levels, lifecycles, and rates of change turn that convenience into coupling. Excessive separation creates coordination overhead and pass-through abstractions.

### Apply the pattern

For each concern, ask:

- What decision or mechanism does it own?
- What information does it require?
- Who may change it and how often?
- What security and failure boundary applies?
- Can it be tested without unrelated behavior?
- What explicit contract connects it to the rest?

Separate when the answers materially differ. Keep together when the behavior is one cohesive invariant and splitting it would create a distributed transaction or duplicated state.

An authorization policy can be evaluated separately from HTTP routing, but enforcement must remain close to the protected operation. A pipeline can build an artifact separately from deployment, while immutable identity connects the two.

### Warning signs

- changing presentation changes durable data or authority;
- a retry policy is buried inside business logic and cannot be bounded centrally;
- build-time secrets leak into runtime artifacts;
- incident analysis cannot distinguish mitigation from repair;
- a microservice boundary separates code but not data ownership or failure.

### Handbook examples

- [Identity, Authentication, Authorization, and Permissions](../foundations/07-identity-authentication-authorization-and-permissions.md) separates related security decisions.
- [Configuration, Secrets, Logging, and Observability](../automation/72-configuration-secrets-logging-and-observability.md) separates operational concerns from program logic.
- [Interfaces, Contracts, and Evolution](../system-design/107-interfaces-contracts-and-evolution.md) makes connection contracts explicit.
- [Incident Response and Operational Coordination](../observability/127-incident-response-and-operational-coordination.md) separates command, operations, communication, and learning.

### Related patterns

[Layered Systems](#layered-systems), [Identity Before Authority](#identity-before-authority), and [Explicit State and Ownership](#explicit-state-and-ownership).

## Composition over Complexity

### Intent

Build larger behavior by combining bounded components with inspectable contracts instead of enlarging one component until its behavior becomes implicit and inseparable.

### Forces

Composition enables reuse, replacement, testing, and parallel understanding. Every seam also adds a contract, failure mode, and coordination cost. The goal is not the maximum number of pieces; it is the smallest set of cohesive parts that makes the system's behavior legible.

### Apply the pattern

- Give each component one coherent responsibility.
- Connect components through typed or well-defined inputs, outputs, and errors.
- Make ordering, buffering, cancellation, and partial failure explicit.
- Keep intermediate state observable when it affects correctness.
- Test components locally and the composed journey end to end.
- Prefer deterministic composition before adding orchestration or distributed coordination.

Unix pipelines compose processes through byte streams. Automation composes functions and commands through structured data. A distributed workflow composes services through APIs and messages, but it must also define retries, idempotency, ordering, and ownership.

### Warning signs

- a “reusable” component requires global mutable state;
- the caller must know internal steps to use the abstraction safely;
- dozens of tiny remote services turn one local call into a fragile network graph;
- errors are flattened until the failing component cannot be identified;
- replacing one part requires changing every consumer.

Composition is not automatically simpler. A monolith with clear modules may be more composable than a fleet of tightly coupled services.

### Handbook examples

- [Pipes: Composing Small Tools](../foundations/09-pipes-composing-small-tools.md) introduces data-flow composition.
- [Shell Control Flow, Functions, and Error Handling](../automation/66-shell-control-flow-functions-and-error-handling.md) adds explicit program structure.
- [Multi-Container Applications with Compose](../containers/85-multi-container-applications-with-compose.md) composes runtime services while exposing dependencies.
- [Messaging, Events, and Asynchronous Workflows](../system-design/112-messaging-events-and-asynchronous-workflows.md) covers composition across time and failure.

### Related patterns

[Small Tools, Loosely Coupled](#small-tools-loosely-coupled), [Stable Interfaces](#stable-interfaces), and [Failure Containment](#failure-containment).

## Stable Interfaces

### Intent

Protect consumers from unnecessary internal change through a deliberate contract, while providing an explicit path for compatible evolution, deprecation, and removal.

### Forces

Consumers need predictability; providers need freedom to improve internals. Frozen interfaces accumulate obsolete decisions, while casual changes externalize migration cost and break trust. Stability concerns semantics, not merely syntax.

### Apply the pattern

Define:

- operation names and resource identity;
- input and output schemas, defaults, and validation;
- error, timeout, retry, cancellation, and idempotency behavior;
- ordering, consistency, and durability guarantees;
- authentication and authorization context;
- compatibility policy and supported versions;
- observability and retirement signals;
- migration, deprecation, and removal sequence.

Prefer additive evolution when semantics remain compatible. Test consumers against the contract, not undocumented implementation detail. Version only when two meanings cannot safely share one contract; a version number does not excuse an undefined migration.

### Warning signs

- optional fields change from absent to a surprising default;
- error or retry semantics change without a schema change;
- consumers scrape human output or depend on ordering the provider never promised;
- “internal” identifiers escape and become permanent external keys;
- old behavior can never be removed because usage is unobservable.

### Handbook examples

- [Standard Input, Standard Output, and Standard Error](../foundations/08-standard-input-standard-output-and-standard-error.md) presents durable process interfaces.
- [HTTP Semantics and API Behavior](../networking/59-http-semantics-and-api-behavior.md) distinguishes protocol meaning from endpoint implementation.
- [Structured Inputs, Outputs, and Data Formats](../automation/67-structured-inputs-outputs-and-data-formats.md) makes machine contracts explicit.
- [Interfaces, Contracts, and Evolution](../system-design/107-interfaces-contracts-and-evolution.md) develops the system-design form of the pattern.

### Related patterns

[Composition over Complexity](#composition-over-complexity), [Convention over Unnecessary Configuration](#convention-over-unnecessary-configuration), and [Explicit State and Ownership](#explicit-state-and-ownership).

## Least Privilege

### Intent

Grant only the operations, resources, scope, conditions, and duration required for the current responsibility, then remove the grant when that responsibility ends.

### Forces

Broad permanent authority is convenient during setup and expensive during compromise, error, or automation failure. Fine-grained authority reduces blast radius but increases policy design, testing, and operational recovery work.

### Apply the pattern

1. Identify the principal and the exact operation.
2. Name resources with the narrowest stable scope.
3. Add necessary conditions such as tenant, environment, network, or artifact identity.
4. Prefer short-lived, delegated credentials over copied long-lived secrets.
5. separate human, workload, deployment, and break-glass roles.
6. make denial the default and test both permitted and prohibited paths.
7. log decisions safely and review unused authority.
8. revoke temporary grants and rotate exposed credentials.

Design recovery before tightening access. A policy that prevents authorized rollback or evidence collection will be bypassed during an incident.

### Warning signs

- one shared administrator identity serves people and automation;
- a wildcard was added to fix one denial and never revisited;
- development, CI, and production use the same credentials;
- a container runs privileged because one capability was needed;
- authorization is enforced only in presentation or routing code;
- emergency access has no expiry, audit, or review.

### Handbook examples

- [Identity, Permissions, ACLs, and Privilege Boundaries](../operating-systems/48-identity-permissions-acls-and-privilege-boundaries.md) grounds local authority.
- [IAM: Principals, Policies, Roles, and Temporary Credentials](../aws/92-iam-principals-policies-roles-and-temporary-credentials.md) applies the pattern in cloud governance.
- [Container Security and Least Privilege](../containers/87-container-security-and-least-privilege.md) limits runtime authority.
- [Security, Privacy, and Multi-Tenant Boundaries](../system-design/115-security-privacy-and-multi-tenant-boundaries.md) connects authority to service and tenant invariants.

### Related patterns

[Identity Before Authority](#identity-before-authority), [Failure Containment](#failure-containment), and [Explicit State and Ownership](#explicit-state-and-ownership).

## Identity Before Authority

### Intent

Establish exactly which principal, object, artifact, endpoint, revision, or state is involved before reasoning about what it may do or what happened to it.

### Forces

Names are convenient but ambiguous. Usernames, tags, branches, hostnames, paths, ports, and display names can move, collide, or refer through indirection. Authority and evidence attach to a concrete identity, not a label interpreted differently by each layer.

### Apply the pattern

Ask:

- Is this a human, workload, service, session, or delegated principal?
- Which authentication event and credential established it?
- Which immutable artifact digest, source revision, policy revision, or object ID is running?
- Which namespace gives the name meaning?
- Can the identifier be reused, renamed, or reassigned?
- Which tenant, account, region, environment, and time window qualify it?
- Does the enforcement point receive the verified identity or a caller-supplied claim?

Resolve indirection before changing authority. A file path may name a symbolic link; a container tag may name a different digest tomorrow; an IP address may host several identities; a project ID may repeat across tenants.

### Warning signs

- permission is discussed before the acting principal is known;
- a mutable tag is treated as provenance;
- logs contain a display name but no stable subject or tenant identifier;
- cache keys omit identity dimensions that change a decision;
- a hostname or port is mistaken for an authenticated peer;
- rollback names a release label but not an immutable artifact.

### Handbook examples

- [File Identity, Hard Links, and Symbolic Links](../operating-systems/39-file-identity-hard-links-and-symbolic-links.md) separates names from filesystem objects.
- [Sockets, Ports, and Endpoint Ownership](../networking/56-sockets-ports-and-endpoint-ownership.md) separates endpoint coordinates from process and peer identity.
- [Registries, Tags, Digests, and Image Provenance](../containers/81-registries-tags-digests-and-image-provenance.md) establishes artifact identity.
- [A Complete Cross-Layer Engineering Investigation](../observability/129-a-complete-cross-layer-engineering-investigation.md) shows an authorization cache failure caused by incomplete decision identity.

### Related patterns

[Least Privilege](#least-privilege), [Stable Interfaces](#stable-interfaces), and [Explicit State and Ownership](#explicit-state-and-ownership).

## Small Tools, Loosely Coupled

### Intent

Prefer focused capabilities that connect through explicit, replaceable data and failure boundaries. Keep coupling low enough that a tool can be understood, tested, and reused without importing an entire environment.

### Forces

Small tools reduce local cognitive load and encourage reuse. A useful workflow still needs coordination, error propagation, shared formats, and performance. Too many subprocesses, services, or adapters can move complexity into glue and operations.

### Apply the pattern

- Give a tool one coherent job and a clear name.
- Accept inputs explicitly; avoid hidden global state.
- emit stable machine-readable output separately from diagnostics.
- use exit status or typed errors consistently.
- make partial output and retry behavior clear.
- keep policy at the composition boundary when several tools share it.
- measure whether process or network boundaries are justified.

The pattern is about coupling, not line count. A substantial library with a narrow contract can be a small tool in architectural terms. A ten-line script that assumes a particular directory, shell state, credential, and unversioned output is tightly coupled.

### Warning signs

- output intended for humans is scraped as an API;
- every tool parses and reimplements the same policy;
- one failure is swallowed and the pipeline continues with incomplete data;
- a helper mutates global state without declaring ownership;
- a distributed service exists only because a local module felt insufficiently fashionable.

### Handbook examples

- [The Unix Way: Composability in Practice](../foundations/11-the-unix-way-composability-in-practice.md) establishes the tool philosophy.
- [Reading and Transforming Text](../terminal/17-reading-and-transforming-text.md) composes focused command-line transformations.
- [Subprocesses, HTTP Clients, and External Boundaries](../automation/70-subprocesses-http-clients-and-external-boundaries.md) makes integration failure explicit.
- [From Requirements to a System Model](../system-design/106-from-requirements-to-a-system-model.md) prevents premature service decomposition.

### Related patterns

[Composition over Complexity](#composition-over-complexity), [Stable Interfaces](#stable-interfaces), and [Separation of Concerns](#separation-of-concerns).

## Automate Repetitive Work

### Intent

Observe, simplify, define, and test a repeated manual process, then automate it so the same inputs produce controlled, reviewable, recoverable outcomes.

### Forces

Automation reduces toil, variation, and delay while increasing execution speed and reach. It can also scale an incorrect assumption, destructive default, or hidden credential. The more authority automation has, the stronger its identity, validation, observability, and recovery contract must be.

### Apply the pattern

1. Perform and observe the manual workflow.
2. remove unnecessary steps and decisions.
3. define inputs, preconditions, outputs, side effects, and ownership.
4. make repeated execution idempotent or explicitly state otherwise.
5. validate and plan before mutation.
6. use least privilege and isolate untrusted inputs.
7. test success, partial failure, interruption, retry, and cleanup.
8. emit structured evidence and a useful exit status.
9. provide pause, abort, rollback, and safe resumption where risk requires them.
10. measure whether the automation still saves effort and preserves its assumptions.

Automate a decision only when the decision rule is stable and observable. Keep human judgment where context remains material; automate evidence collection and reversible preparation around it.

### Warning signs

- the manual process is not understood but is called toil;
- success means the script exited zero rather than the user outcome being verified;
- retries duplicate side effects;
- a scheduled task has no owner or expiry;
- failures require editing state manually before rerun;
- generated output becomes an unreviewed independent source of truth.

### Handbook examples

- [Deciding What to Automate](../automation/64-deciding-what-to-automate.md) defines the selection boundary.
- [Idempotency, State, Retries, and Recovery](../automation/74-idempotency-state-retries-and-recovery.md) handles repeated and interrupted execution.
- [A Complete CI/CD Automation Lifecycle](../automation/77-a-complete-ci-cd-automation-lifecycle.md) automates a trusted delivery chain.
- [Infrastructure as Code and a Complete AWS Delivery Lifecycle](../aws/105-infrastructure-as-code-and-a-complete-aws-delivery-lifecycle.md) reconciles cloud state through reviewed automation.

### Related patterns

[Explicit State and Ownership](#explicit-state-and-ownership), [Least Privilege](#least-privilege), and [Failure Containment](#failure-containment).

## Explicit State and Ownership

### Intent

Make current state, desired state, transition, authority, and cleanup responsibility visible. Ensure every durable resource, queue, incident action, temporary grant, and configuration deviation has an owner and lifecycle.

### Forces

Implicit state makes simple interfaces convenient but produces drift, race conditions, and abandoned resources. Fully explicit state requires more modeling and records. Distributed systems add partial observation and concurrent actors, so ownership must include who may reconcile conflict.

### Apply the pattern

Represent:

- observed state and its time or revision;
- desired state and who declared it;
- transition status, generation, and last result;
- exclusive or shared ownership rules;
- concurrency and conflict behavior;
- terminal, failed, paused, and unknown states;
- cleanup, expiry, and transfer of ownership;
- evidence that the intended outcome exists.

Use state machines when transitions matter. Use immutable events when history matters, but define how current state is derived. A queue needs ownership of in-flight messages; an incident needs one active commander; infrastructure code needs an authoritative reconciler.

### Warning signs

- two controllers believe they own the same field or resource;
- “running” does not distinguish starting, ready, draining, failed, or stale;
- temporary resources have no expiry or cost owner;
- a handoff transfers responsibility without current state;
- cleanup depends on the person who remembers creating something;
- dashboards show desired replicas but not ready or serving capacity.

### Handbook examples

- [The Working Tree, Index, and `HEAD`](../git/25-the-working-tree-index-and-head.md) names distinct repository states.
- [Process Creation, Execution, and Lifecycle](../operating-systems/42-process-creation-execution-and-lifecycle.md) follows operating-system state transitions.
- [Orchestration Foundations and Kubernetes Mental Models](../containers/88-orchestration-foundations-and-kubernetes-mental-models.md) introduces reconciliation and ownership.
- [Incident Response and Operational Coordination](../observability/127-incident-response-and-operational-coordination.md) applies explicit state under time pressure.

### Related patterns

[Identity Before Authority](#identity-before-authority), [Automate Repetitive Work](#automate-repetitive-work), and [Stable Interfaces](#stable-interfaces).

## Failure Containment

### Intent

Bound the time, work, resources, dependency reach, retry amplification, data exposure, and operational blast radius of a fault so the system degrades predictably and can recover.

### Forces

Distributed and concurrent systems experience partial failure. Retries, queues, caches, replicas, and autoscaling improve normal operation but can amplify overload or extend stale state. Hard bounds may reject legitimate work; missing bounds turn one slow dependency into system-wide collapse.

### Apply the pattern

- set end-to-end deadlines and allocate bounded child timeouts;
- cancel abandoned downstream work;
- bound retries by attempts, time, budget, and idempotency;
- cap queue length and age, concurrency, payload, batch, and memory;
- isolate tenants, priorities, workloads, and failure domains;
- shed work before resources become unrecoverable;
- use circuit breaking only with measurable recovery behavior;
- preserve redundancy and headroom for credible loss;
- make degraded modes explicit and correctness-safe;
- inject bounded failures and verify recovery, not only survival.

Containment includes security: tenant scope, least privilege, network boundaries, and evidence access limit the impact of compromise or error.

### Warning signs

- every caller retries independently with no shared budget;
- queues are “temporary” but unbounded;
- timeouts exceed the caller's remaining deadline;
- autoscaling callers overload a fixed downstream service;
- one tenant or bulk job consumes all shared capacity;
- a failure test has no abort threshold or recovery objective;
- graceful degradation silently weakens correctness or authorization.

### Handbook examples

- [TCP Reliability, Flow Control, and Connection State](../networking/58-tcp-reliability-flow-control-and-connection-state.md) shows bounded flow and recovery at transport.
- [Scheduling, Concurrency, and Work Queues](../automation/76-scheduling-concurrency-and-work-queues.md) bounds automated work.
- [Resilience, Timeouts, Retries, and Failure Containment](../system-design/114-resilience-timeouts-retries-and-failure-containment.md) develops the system-design pattern.
- [Load Testing, Capacity Planning, and Failure Injection](../observability/126-load-testing-capacity-planning-and-failure-injection.md) validates limits before real failure.

### Related patterns

[Least Privilege](#least-privilege), [Explicit State and Ownership](#explicit-state-and-ownership), and [Layered Systems](#layered-systems).

## Convention over Unnecessary Configuration

### Intent

Provide a documented, safe, unsurprising default for the common case so users configure only meaningful differences. Keep the default observable and offer an intentional escape path when requirements differ.

### Forces

Configuration supports diverse environments but transfers design work to every user and multiplies states to test. Convention reduces decisions and improves consistency but can hide assumptions, exclude uncommon needs, or become accidental policy.

### Apply the pattern

- choose the simplest default that is safe for the intended context;
- document its semantics, scope, security posture, and lifecycle;
- make the effective value inspectable at runtime;
- validate overrides and reject contradictory combinations;
- distinguish omission from an explicit zero, false, empty, or inherit value;
- keep secrets and environment-specific identity out of source defaults;
- deprecate old options with usage evidence and migration paths;
- add configuration only when a real requirement cannot be expressed by composition or a stable convention.

Security-sensitive defaults should fail closed. Performance defaults should be conservative and bounded. A convention must not silently infer tenant, environment, or authority from an ambiguous name.

### Warning signs

- every deployment copies the same large configuration file;
- an option exists because one historical caller once needed it;
- the runtime cannot report which default became effective;
- changing a library default silently changes security or durability;
- boolean flags interact into an undocumented state machine;
- users must override an unsafe default before first use.

Convention also has a stopping condition: when contexts have genuinely different requirements, one universal default becomes hidden coupling. Split profiles or require an explicit decision.

### Handbook examples

- [Shell Startup, Configuration, and `PATH`](../terminal/22-shell-startup-configuration-and-path.md) makes inherited convention and override order visible.
- [Python Environments, Dependencies, and Packaging](../automation/71-python-environments-dependencies-and-packaging.md) uses ecosystem conventions while preserving reproducibility.
- [Configuration, Secrets, Logging, and Observability](../automation/72-configuration-secrets-logging-and-observability.md) separates defaults from environment state and secrets.
- [Architecture Decisions, Tradeoffs, and Evolution](../system-design/116-architecture-decisions-tradeoffs-and-evolution.md) records when requirements justify a departure from convention.

### Related patterns

[Stable Interfaces](#stable-interfaces), [Separation of Concerns](#separation-of-concerns), and [Explicit State and Ownership](#explicit-state-and-ownership).

## Using the patterns together

A useful review sequence is:

1. **Identity before authority:** establish the exact user, workload, artifact, object, revision, and environment.
2. **Layered systems:** draw the journey and locate each responsibility and failure boundary.
3. **Separation of concerns:** distinguish policy, mechanism, data, presentation, and lifecycle.
4. **Stable interfaces:** state the contracts and compatibility obligations at each boundary.
5. **Composition over complexity:** assemble cohesive parts without hiding ordering or failure.
6. **Small tools, loosely coupled:** minimize assumptions between parts.
7. **Convention over unnecessary configuration:** make the safe common path easy and visible.
8. **Least privilege:** narrow every principal's authority to the required operation and duration.
9. **Explicit state and ownership:** show what exists, what should exist, and who reconciles it.
10. **Failure containment:** bound time, work, resources, dependencies, and blast radius.
11. **Automate repetitive work:** encode the stable, reviewed process with evidence and recovery.

The sequence is not mandatory. It reveals dependencies between patterns. Automating before state and ownership are explicit scales ambiguity. Granting privilege before identity is established authorizes the wrong subject. Composing components before interfaces are stable spreads implementation detail. Adding configuration before a convention is tested distributes the design burden to every user.

When a pattern conflicts with another, make the tradeoff explicit. A stable interface may preserve a poor convention temporarily while a migration proceeds. Failure containment may require rejecting work that composition could technically accept. Least privilege may add operational steps that automation must safely carry. The goal is not pattern purity; it is a system whose choices, boundaries, and consequences can be understood and defended.

## Appendix review checklist

- Can each important object and principal be identified without an ambiguous mutable label?
- Can one user journey be followed across named layers and correlation boundaries?
- Are policy, mechanism, data, presentation, and lifecycle separated where they change differently?
- Do components have cohesive responsibilities and explicit error contracts?
- Can interfaces evolve without surprising consumers?
- Is authority minimal, temporary where possible, and denied by default?
- Are tools reusable without hidden global state or human-output scraping?
- Was automation built from a stable, observable, recoverable manual contract?
- Are current state, desired state, controller, owner, and cleanup visible?
- Are time, retries, queues, concurrency, resources, tenants, and blast radius bounded?
- Does the common case use a documented safe default with inspectable overrides?
- Are exceptions and tradeoffs recorded with the evidence that justified them?

The patterns are successful when they improve questions and decisions, not when every design document repeats their names.
