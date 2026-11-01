# Chapter 58 — TCP Reliability, Flow Control, and Connection State

The Transmission Control Protocol (TCP) gives two endpoints a reliable, ordered, full-duplex byte stream over an unreliable packet network. It detects loss, retransmits data, rejects duplicates, restores order, and adapts how much data it sends.

The central idea is:

> TCP preserves an ordered stream of bytes, not application messages; delivery, capacity, and connection state must be interpreted at the correct layer.

## 1. A connection is shared protocol state

A TCP connection is identified by its protocol and local and remote IP address and port pairs. Each endpoint maintains state such as sequence numbers, acknowledged data, receive capacity, timers, and negotiated options.

The usual opening is a three-way handshake:

```text
client                         server
  | ------ SYN, seq=x --------> |
  | <--- SYN+ACK, seq=y, ack=x+1|
  | ------ ACK, ack=y+1 ------> |
```

The exchange demonstrates bidirectional reachability and synchronizes initial sequence numbers. It can also negotiate options such as maximum segment size, window scaling, timestamps, and selective acknowledgments. Simultaneous open and other edge cases exist, so the diagram is a reasoning model rather than every possible exchange.

A successful handshake proves that TCP state was established with an endpoint at that network tuple. It does not authenticate the peer, confirm application readiness, or guarantee that a later request will complete.

## 2. Sequence numbers describe bytes

TCP divides the stream into segments for transport, but sequence numbers count bytes. An acknowledgment normally reports the sequence number of the next byte the receiver expects. It is cumulative: acknowledging byte position 5001 means the receiver has accepted the contiguous stream through byte 5000.

Selective acknowledgment, when negotiated, can additionally describe noncontiguous ranges already received. This helps a sender retransmit missing data without resending every later segment.

An ACK is evidence about the peer's TCP implementation and receive buffers. It does not mean that:

- the application read the bytes;
- a request was parsed successfully;
- a database transaction committed;
- data reached durable storage;
- the business operation happened exactly once.

Applications need their own response, transaction, or idempotency semantics for those claims.

## 3. TCP repairs loss without preserving packets

IP packets can be lost, duplicated, or reordered. TCP retains unacknowledged data and retransmits when its algorithms infer loss, including through retransmission timers and acknowledgment patterns. The retransmission timeout is calculated from measured round-trip behavior rather than being one universal constant.

The receiver discards duplicate stream bytes and presents in-order data to the application. A later segment can arrive successfully while the application waits for an earlier missing segment. This is **head-of-line blocking**: ordered delivery intentionally withholds later bytes until the gap is repaired.

TCP reliability has limits. A connection can eventually time out, reset, lose all paths, or disappear with a host failure. TCP cannot tell a retrying client whether a server performed an operation just before the connection failed. State-changing application operations still need safe retry design.

## 4. Flow control protects the receiver

The receiver advertises how much additional stream data it can currently accept. This receive window reflects buffer availability and moves as the receiving application consumes data.

If the application reads slowly, the window can shrink to zero. The sender then pauses ordinary data and periodically checks whether capacity has reopened. This is backpressure across the connection, not packet loss.

Flow control answers:

> How much more data can this receiver buffer?

Increasing a socket buffer can postpone pressure, but it does not fix an application that never drains work or applies bounded admission control.

## 5. Congestion control protects the path

The sender separately maintains a congestion window based on evidence about network capacity and loss. Standard TCP behavior increases sending cautiously and reduces it when signals suggest congestion. The amount in flight is bounded by both receiver capacity and the sender's congestion-control state.

Congestion control answers:

> How much unacknowledged data should this sender place into the network now?

The distinction matters during diagnosis:

- a small advertised receive window points toward receiver-side consumption or buffering;
- a constrained congestion window points toward path feedback and sender behavior;
- application rate limits can constrain traffic even when both TCP windows permit more.

Do not disable or aggressively tune congestion behavior to hide a throughput problem. First measure round-trip time, loss, receiver capacity, application demand, and path characteristics.

## 6. TCP has no application message boundary

One application `write` does not imply one peer `read`. A write can be split across many reads; several writes can arrive in one read; and APIs may complete with only part of the requested byte count.

Applications must frame messages above the stream. Common strategies include:

- a fixed-length record;
- a length-prefixed record;
- a delimiter with defined escaping rules;
- a self-describing grammar with explicit termination;
- closing one stream direction to mark an end where the protocol permits it.

The parser must handle partial and multiple messages, enforce size limits, and retain only bounded incomplete state. Assuming packet or write boundaries are message boundaries produces intermittent failures that appear only under different timing or load.

## 7. Closing is directional

TCP is full duplex, so each direction closes independently. A `FIN` says that its sender has no more stream bytes to send. The peer can receive that end-of-stream while still sending its own data, creating a valid half-closed connection.

A graceful close can therefore involve separate FIN and ACK exchanges in each direction. An application must continue reading if its protocol expects a final response after it stops writing.

A reset (`RST`) aborts connection state instead of completing an orderly stream close. It can indicate that no socket owns the destination tuple, an endpoint rejected unexpected state, or an application used an abortive close. Bytes buffered but not delivered to the application can be lost when a reset occurs.

“Connection reset” is a transport symptom, not a root cause. Correlate it with endpoint logs, time, tuple, preceding protocol activity, and middlebox behavior.

## 8. State names explain lifecycle position

Operating systems expose TCP states that locate a socket in the protocol lifecycle:

| State | Practical meaning |
| --- | --- |
| `LISTEN` | A local socket is waiting for new connection attempts. |
| `SYN-SENT` | An active opener sent a SYN and awaits a valid reply. |
| `SYN-RECEIVED` | An endpoint received a SYN and awaits the final handshake acknowledgment. |
| `ESTABLISHED` | Both directions are established; this does not prove application health. |
| `FIN-WAIT-1/2` | The local endpoint initiated an orderly close and is progressing through it. |
| `CLOSE-WAIT` | The peer closed its sending direction; the local application has not closed its side. |
| `LAST-ACK` | The local endpoint sent its FIN after receiving the peer's FIN and awaits acknowledgment. |
| `TIME-WAIT` | The active closer retains state temporarily after the final exchange. |

Persistent growth in `CLOSE-WAIT` often means an application learned that its peer closed but failed to close the local socket. `TIME-WAIT`, by contrast, is normally part of correct protocol operation. It lets delayed segments expire and allows retransmission of the final acknowledgment if needed.

A large `TIME-WAIT` count can expose excessive connection churn or resource pressure, but the state itself is not a leak. Connection reuse and application architecture are safer levers than indiscriminately shortening protocol timers.

## 9. Timeouts answer different questions

Applications should distinguish at least:

- **connect timeout:** how long to wait for connection establishment;
- **read or idle timeout:** how long to wait without required stream progress;
- **write timeout:** how long to wait for local sending progress;
- **operation deadline:** the total time allowed for the application result.

A TCP timeout does not prove that the peer never received or processed a request. If the response was lost after a committed operation, a client can time out and retry a request that already succeeded. Use protocol-defined idempotency, request identifiers, or reconciliation for ambiguous outcomes.

TCP keepalive is an optional mechanism for probing a connection after a period of inactivity. Platform defaults are often long, and successful probes only show that the TCP peer responds. Keepalive does not replace application deadlines, health checks, heartbeats with domain meaning, or recovery behavior.

## 10. Observe state before changing it

| Goal | Linux | macOS | Windows PowerShell |
| --- | --- | --- | --- |
| TCP sockets and state | `ss -tanp` | `netstat -anv -p tcp` | `Get-NetTCPConnection` |
| Listener ownership | `ss -ltnp` | `lsof -nP -iTCP -sTCP:LISTEN` | `Get-NetTCPConnection -State Listen` |
| Established connections | `ss -tn state established` | `lsof -nP -iTCP -sTCP:ESTABLISHED` | `Get-NetTCPConnection -State Established` |
| Transport details | `ss -tin` | `netstat -anv -p tcp` | `netstat -s -p tcp` for counters |

Process details can require elevated permission. On Windows, pass a connection's `OwningProcess` value to `Get-Process -Id`; on Unix-like systems, use the PID shown by `ss` or `lsof` when authorized.

Interpret a snapshot carefully. A connection can change state between commands, cumulative counters need before-and-after measurements, and `ESTABLISHED` can describe an application that is deadlocked or waiting indefinitely.

Packet capture can reveal flags, sequence ranges, acknowledgments, retransmissions, and window advertisements. It can also expose sensitive endpoints and payload data. Capture only with authorization, narrow filters, bounded duration, secure storage, and a deletion plan.

## Common Misconceptions

- “TCP delivers messages.” TCP delivers ordered bytes; the application protocol defines messages.
- “An ACK means the server completed my request.” It means TCP accepted stream bytes, not that application work succeeded.
- “`ESTABLISHED` means healthy.” It describes transport state, not application responsiveness.
- “Every `TIME-WAIT` socket is a leak.” The state is a normal correctness mechanism after active close.
- “Keepalive guarantees prompt failure detection.” Its timing and meaning are too limited to replace explicit deadlines.

## Core Computer Science Concept

TCP is a **distributed state machine under uncertain delivery**. Each endpoint advances state from local events and received segments while sequence numbers, acknowledgments, and timers reconcile imperfect observations of the network.

## Engineering Connections

- HTTP/1.1 message framing operates above the TCP byte stream and enables connection reuse.
- TLS records are carried within the stream and add confidentiality and peer authentication; TCP alone provides neither.
- Database clients need operation-level retry rules because transport failure leaves commit outcome ambiguous.
- Load balancers and NAT devices maintain their own connection state and can expire an otherwise established flow.

## From the Field

A service reads a four-byte length and then calls `read` once for the advertised body size. It works in local tests, but production sometimes returns fewer bytes because TCP reports currently available stream data rather than reconstructing the sender's write. The correct implementation loops until it has the complete bounded frame, reaches end-of-stream, or hits its operation deadline.

## Engineering Review

### What problem does this solve?

It provides an ordered, duplicate-free byte stream with loss recovery and adaptive capacity control across an unreliable packet network.

### Why was it designed this way?

A general byte stream lets many application protocols define their own messages while transport handles ordering, retransmission, receiver pressure, and shared-path congestion.

### When should I use it?

Use TCP when an application needs reliable ordered bytes and can define framing, deadlines, authentication, and safe retry behavior above them.

### When should I avoid it?

Avoid treating TCP as a complete application protocol or assuming its ordered stream fits traffic where stale data should be abandoned independently.

### How does this make me a better engineer?

It lets you separate transport evidence from application outcomes and diagnose lifecycle, receiver pressure, path congestion, and framing failures precisely.

### How does this reduce waste?

It prevents futile socket tuning, unsafe retries, false leak investigations, and parsers built around nonexistent message boundaries.

## Handbook Principle #58

> Treat TCP as an ordered byte stream with shared state—never as proof of application completion, identity, or message boundaries.

## Practical Observation

Open a documentation page in a browser, then inspect established TCP connections owned by that browser. Record one local and remote tuple and its state without capturing payloads. Refresh the page and observe whether the browser reuses the connection or creates another. Explain what `ESTABLISHED` proves and name at least three things it does not prove.

## Looking Ahead

TCP supplies an ordered stream but does not define requests, responses, cache behavior, or resource meaning. Chapter 59 examines how HTTP adds those application semantics.

## References

- [RFC 9293 — Transmission Control Protocol](https://www.rfc-editor.org/rfc/rfc9293)
- [RFC 5681 — TCP Congestion Control](https://www.rfc-editor.org/rfc/rfc5681)
- [RFC 6298 — Computing TCP's Retransmission Timer](https://www.rfc-editor.org/rfc/rfc6298)
- [Linux `tcp(7)`](https://man7.org/linux/man-pages/man7/tcp.7.html)
