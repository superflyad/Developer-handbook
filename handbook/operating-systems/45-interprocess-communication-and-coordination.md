# Chapter 45 — Interprocess Communication and Coordination

Process isolation prevents one program from casually reading or changing another's memory. Useful systems still need processes to exchange data, signal events, and coordinate ownership. Interprocess communication (IPC) creates explicit channels across that isolation boundary.

The central idea is:

> Choose IPC by data shape, lifetime, trust, flow control, and failure behavior—not by raw speed alone.

## 1. Communication and synchronization are separate needs

Communication transfers information. Synchronization controls ordering or exclusive access. One mechanism may provide both, but do not assume that shared access implies safe coordination.

Examples:

- a pipe transports bytes and blocks when capacity is exhausted;
- shared memory exposes common bytes but needs a protocol for concurrent access;
- a lock coordinates ownership but does not describe application messages;
- a signal or event announces a condition but may carry little data;
- a file persists data but does not by itself prevent conflicting writers.

Start with the protocol: who owns the endpoint, how peers discover it, how messages are framed, what happens under load, and how each side detects closure or crash.

## 2. Pipes compose streams

Anonymous pipes commonly connect related processes and shell pipelines. They provide a byte stream with a read end and write end. End-of-file becomes observable only when every relevant writer is closed; accidentally inherited write descriptors can therefore keep a reader waiting forever.

```bash
producer | consumer
```

The shell creates the pipe, gives endpoints to child processes, and closes its unused copies. The pipe has finite capacity. When readers fall behind, a blocking writer waits; this is **backpressure**, not necessarily failure.

Byte streams do not preserve application message boundaries. If a writer sends two records, one read can return part of one or several together. Define framing with lengths, delimiters, or a higher-level serialization protocol, and bound accepted message size.

Named pipes or FIFOs allow independently started processes to meet through a name. Windows named pipes can support duplex and message-oriented modes depending on API configuration; POSIX FIFOs retain stream semantics. Similar names do not guarantee identical behavior.

## 3. Local sockets provide bidirectional endpoints

Unix-domain sockets and Windows AF_UNIX support local socket communication without using an external network path. Depending on type and platform, sockets can provide byte streams or preserve datagram/message boundaries. They support bidirectional communication and can integrate with event loops.

Local socket endpoints have a namespace and access policy. On Unix, a pathname socket's directory permissions matter, but peer-credential facilities are platform-specific. On Windows, support and security details differ from named pipes. Authenticate the peer at the strongest available boundary; possession of an endpoint name is not always sufficient.

TCP loopback is another local option and can reuse network protocols, but it brings port allocation, firewall, authentication, and network-stack behavior. Choose it when protocol portability or remote extension matters, not because all IPC is secretly networking.

## 4. Shared memory trades copying for coordination complexity

Shared memory maps the same underlying pages into multiple processes. It can support high throughput and large data, but readers and writers must agree on layout, version, synchronization, and memory-ordering rules.

```text
process A address → shared pages ← process B address
                     ↑
             locks / atomics / protocol
```

A crashed writer can leave partially updated state or a lock held. Robust synchronization facilities can help in some environments, but recovery must be designed. Pointer values from one process generally cannot be stored as portable references for another because mappings can appear at different virtual addresses.

Use shared memory when profiling proves copying or kernel transitions are material and the team can own the concurrency protocol. A pipe or socket is often safer for modest control traffic.

## 5. Files and databases provide durable exchange

A file can decouple producers and consumers across time, and a database can add transactions, indexing, locking, and recovery. This can be the simplest correct IPC when durability and inspectability matter more than immediate notification.

Do not invent coordination by repeatedly checking for a file without defining atomic publication, ownership, stale-file cleanup, and crash recovery. Write-then-rename can publish one complete file on a compatible local filesystem, but cross-filesystem, network, and durability semantics still apply.

File locks are advisory on many Unix systems and have platform- and filesystem-specific semantics. All participants must use compatible locking. A lock does not make a multi-file business transaction atomic.

## 6. Signals and events carry small control information

POSIX signals notify a process of asynchronous events. Most carry only a signal identity and limited associated information; delivery, masking, coalescing, and handler restrictions make them unsuitable as a general message bus. Signal handlers must perform only operations permitted in that context and commonly set a flag or write to a safe notification channel.

Windows event objects can signal state between threads or processes; named objects require namespace and ACL design. Other Windows mechanisms include semaphores, mutexes, and waitable handles. Their lifetime is tied to kernel-object references, not a Unix signal model.

Use signals or events to announce “state may have changed,” then read authoritative state through a suitable channel. Avoid encoding a complex protocol in notifications that can be lost, coalesced, or observed out of order.

## 7. Backpressure is part of correctness

If a producer can outpace a consumer indefinitely, memory, disk, or queue depth grows without bound. A protocol must choose among blocking, rejecting, dropping, batching, spilling to durable storage, or applying a deadline.

Backpressure can propagate: a full pipe blocks a worker, which holds a lock, which delays requests. Observe queue depth and blocked duration alongside throughput. Timeouts must state whether work was canceled, may still complete, or became ambiguous.

Bound buffers and messages based on operational capacity and attacker-controlled input. Local IPC crosses a trust boundary whenever peers have different identities, privileges, or compromise risk.

## 8. Design cleanup and restart behavior

For every endpoint or shared object, define:

1. who creates and owns it;
2. how peers locate and authenticate it;
3. who closes or removes it;
4. how EOF, timeout, and peer crash appear;
5. whether data survives process or host restart;
6. how stale state is distinguished from a live owner;
7. how protocol versions remain compatible.

PID files alone are weak ownership evidence because PIDs are reused. Combine process identity with service-manager state, locked resources, or protocol-level liveness.

## Common Misconceptions

- “One write equals one read.” Stream transports do not preserve those call boundaries.
- “Shared memory needs no IPC overhead.” It shifts cost into synchronization and recovery.
- “Local means trusted.” Different local identities and sandboxes can still be adversarial.
- “A timeout cancels the operation.” It may only stop waiting while work continues.

## Core Computer Science Concept

IPC is **protocol design across failure boundaries**. The operating system transports bytes or notifications, but applications must define framing, ownership, ordering, backpressure, authentication, and recovery.

## Engineering Connections

- Shell pipelines rely on close discipline and bounded pipe buffers.
- Browser and mobile sandboxes use IPC to isolate privileged components.
- Database clients need request IDs and cancellation semantics across sockets.
- Supervisors use process exit and control channels to coordinate restart.

## From the Field

A parent launches a child and reads its standard output to completion. The child launches a helper that accidentally inherits the pipe's write end. The child exits, but the parent never sees EOF because the helper still owns a writer. Closing unrelated inherited descriptors at launch fixes the lifecycle protocol; adding a longer timeout only hides it.

## Engineering Review

### What problem does this solve?

It provides explicit channels for isolated processes to exchange data, coordinate ownership, and report events.

### Why was it designed this way?

Process isolation improves safety; multiple IPC mechanisms offer different tradeoffs for copying, persistence, framing, and trust.

### When should I use it?

Use IPC when a system is intentionally split across processes or needs durable handoff between independently running components.

### When should I avoid it?

Avoid shared memory or bespoke file protocols when a simpler framed channel or transactional store meets the requirement.

### How does this make me a better engineer?

It makes failure, ownership, flow control, and trust explicit in component boundaries.

### How does this reduce waste?

It prevents deadlocks, unbounded queues, stale endpoints, and protocol rewrites caused by choosing only for benchmark speed.

## Handbook Principle #45

> An IPC mechanism transports state; a correct protocol defines its boundaries, pressure, ownership, and failure.

## Practical Observation

Run a harmless pipeline that produces several lines and a consumer that counts them. Identify who owns each pipe end, when EOF occurs, and where backpressure would appear if the consumer slowed. Use built-in tools only; do not create globally accessible named IPC endpoints.

## Looking Ahead

Processes that must survive logouts and restart consistently need more than IPC and shell backgrounding. Chapter 46 explains operating-system-managed services and their declared execution context.

## References

- [Linux `pipe(7)`](https://man7.org/linux/man-pages/man7/pipe.7.html)
- [Linux `unix(7)`](https://man7.org/linux/man-pages/man7/unix.7.html)
- [Linux POSIX shared memory overview](https://man7.org/linux/man-pages/man7/shm_overview.7.html)
- [Microsoft: Interprocess Communications](https://learn.microsoft.com/en-us/windows/win32/ipc/interprocess-communications)
