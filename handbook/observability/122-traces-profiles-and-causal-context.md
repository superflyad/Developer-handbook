# Chapter 122 — Traces, Profiles, and Causal Context

Metrics show that a population changed. Logs describe individual events. A distributed trace connects the operations that participated in one logical journey. A profile samples where a process spends execution time or retains resources. These signals answer different questions and become more powerful when correlated without pretending they are interchangeable.

Tracing is about **causal work across boundaries**. Profiling is about **aggregate code and resource behavior inside running processes**. A slow trace can reveal which dependency consumed time; a CPU profile can reveal which call stacks consumed CPU across many requests. Neither alone proves the other.

This chapter covers signal choice, context, sampling, overhead, clock limits, and privacy. It does not configure a vendor, specify tracing protocols in depth, or catalog every runtime profiler.

## 1. Choose the signal from the question

Use a trace when the question is:

- Which services, queues, and dependencies participated in this request?
- Where did its end-to-end latency accumulate?
- Which retry, fan-out branch, or asynchronous continuation failed?
- Did context disappear at a boundary?
- How did a particular slow request differ from a fast one?

Use a profile when the question is:

- Which functions consume CPU across the workload?
- Which stacks allocate or retain memory?
- Where do threads block or contend?
- Which code paths dominate runtime cost after aggregation?
- Did a release change the distribution of stack samples?

Use metrics to discover population-level change and logs to recover discrete contextual facts. Move between signals through shared resource, version, trace, span, and time context.

Do not start a CPU profiler merely because a trace is slow; the span may be waiting on I/O. Do not add a span around every function to find CPU hotspots; that creates overhead and still lacks representative stack sampling.

## 2. Model a trace as causal operations

A trace is a graph of spans representing one logical operation. A span normally contains:

- trace and span identity;
- parent identity or causal links;
- stable operation name and kind;
- start and end timestamps;
- status;
- bounded attributes;
- timestamped events;
- resource and instrumentation identity.

Parent-child relationships often form a tree, but real workflows include fan-out, fan-in, batching, queues, and work linked across trace boundaries. Treat the trace as a causal graph rather than assuming a perfectly nested call stack.

Name spans by stable operation class such as `PATCH /tenants/{tenant}/tasks/{task}` or `task.search.project`, not a raw URL, task ID, or user string. High-cardinality instance data belongs in bounded attributes only when approved.

Every started span must end. Leaked spans distort duration, consume memory, and may never export.

## 3. Place spans around meaningful boundaries

Useful spans correspond to operations whose latency, failure, or ownership can differ:

- service entry and exit;
- outbound RPC or database call;
- queue publish, receive, and processing;
- cache lookup;
- significant internal phase such as authorization or rendering;
- scheduled job or batch stage.

Avoid spans for every helper, loop iteration, getter, or trivial function. Span volume, serialization, context management, and storage are not free. Profiles and local debuggers handle fine-grained code behavior better.

Add an internal span when it isolates a consequential phase or ownership boundary. A 300 ms `task.update` root span becomes actionable when it shows 20 ms authorization, 220 ms connection acquisition, 25 ms transaction, and 10 ms encoding—not when it contains 800 method spans.

Use semantic conventions for common protocols so cross-service queries retain consistent meaning.

## 4. Propagate context across execution units

Context binds a child operation to the work that caused it. In process, it must cross threads, tasks, callbacks, futures, and executors. Across processes, a propagator serializes approved trace context into protocol metadata and extracts it on receipt.

The common flow is:

1. Extract and validate incoming context.
2. Start the server or consumer span with the remote context or an explicit link.
3. Make the new context active only for the intended execution scope.
4. Start child spans from that context.
5. Inject context into outbound calls or messages.
6. End spans even on cancellation and exceptions.

Ambient thread-local state often fails in asynchronous runtimes where work changes threads. Use the runtime's context mechanism or pass context explicitly.

Trace context is correlation metadata, not authentication or authorization. Never trust tenant or subject authority merely because it arrived beside a valid trace identifier.

## 5. Treat incoming context as untrusted

External callers can supply malformed, repeated, colliding, or deliberately expensive tracing headers. Apply protocol limits, parsing validation, and trust-boundary policy. A service may restart a trace at a secure boundary and link to the upstream context when correlation value does not justify propagating the original identifier.

Trace and vendor state can expose cross-request correlation. Generate identifiers from appropriate randomness without embedding IP addresses, user values, timestamps, or secrets. Do not include personally identifiable information in trace state.

Validate that response headers do not expose correlation context to unrelated cross-origin callers. Restrict telemetry access because a trace reveals architecture, timing, dependencies, errors, and user journeys.

An invalid upstream context should not usually reject the business request. Create a new trusted root, record the bounded propagation error, and continue according to policy.

## 6. Use baggage sparingly

Baggage propagates application-defined key-value context through downstream calls. It can help carry a bounded experiment cohort, workload class, or synthetic-test marker. It also multiplies risk:

- values may cross every downstream trust boundary;
- sensitive identifiers can leak;
- clients can forge values;
- size adds network and processing overhead;
- inconsistent mutation creates confusing evidence;
- downstream services may accidentally treat it as authority.

Use an allow list, type and size limits, explicit trust-boundary removal, and server-established values for decisions. Do not put access tokens, emails, task content, or authorization roles in baggage. If tenant class is needed for telemetry, derive it from verified server context and carry the least revealing bounded category.

Baggage is not required for ordinary trace linkage; trace context already supplies correlation identity.

## 7. Represent asynchronous causality correctly

Synchronous RPC has a natural parent-child relationship: the client span causes and usually encloses the server span. Queues complicate that model:

- a producer completes before a consumer starts;
- a message may be retried or replayed later;
- one batch contains messages from many traces;
- one message can fan out to several consumers;
- processing may start a long-running workflow.

Record producer, broker or queue delay where observable, receive, and process operations. Propagate context in message metadata under a versioned contract. Preserve durable message and event identity separately from trace identity.

Use links when one operation has several causes, such as a batch consumer, or when a new trace represents a long-running continuation. Do not select one arbitrary message as the parent of a 500-message batch and imply that the other 499 did not contribute.

Retries should be visible as attempts without changing the semantic operation identity.

## 8. Interpret timestamps as imperfect measurements

Span duration measured by one process can use a monotonic clock and be reliable. Comparing start and end wall times across machines is vulnerable to skew, drift, resolution, and clock adjustment. A waterfall can appear to show a child beginning before its parent or network time becoming negative.

Use causal relationships, local durations, and synchronized clocks together. Do not infer nanosecond cross-host ordering from timestamp precision alone.

For queue delay, compare a producer timestamp with consumer observation only when the clocks and error bounds are understood. Broker-provided enqueue time can be a better shared reference.

Record clock source or quality for specialized systems. Tracing visualizations may correct obvious skew heuristically; such correction is an inference, not original evidence.

## 9. Set span status from the operation contract

A span status describes whether the operation represented by that span met its contract. It is not a direct copy of an HTTP or database code.

- An expected `404` lookup may be successful.
- A stale-write conflict can be a correct terminal response.
- An HTTP `200` containing an invariant violation is an error.
- A cancelled request may be neutral, client-caused, or failed depending on boundary and timing.
- A dependency call can fail while the root operation succeeds through a valid fallback.

Record structured error type, stable code, retryability, and exception event where useful. Avoid putting unbounded messages or sensitive values into attributes.

Do not mark every ancestor error automatically. A parent should reflect its own result; otherwise one handled leaf error paints the entire system red.

## 10. Correlate traces, logs, and metrics

A practical investigation path is:

1. An SLO metric shows task-update latency budget burn in cell B.
2. A histogram exemplar or bounded query links to representative slow trace IDs.
3. A trace shows database connection acquisition consuming the deadline.
4. Span and request IDs find structured failure events with pool and deployment context.
5. Resource metrics show waiters rising after a connection-limit change.
6. A profile determines whether API CPU or lock contention also changed.

Shared resource attributes—service, version, environment, region, cell, instance—and trace/span identities enable this movement. Use the same semantic meaning across signals.

Do not duplicate every log field on every span and metric. Correlation should join complementary evidence, not multiply cost and sensitive data.

## 11. Understand head sampling

Head sampling decides near trace start, before the final outcome is known. It is simple, low-latency, and can make a consistent decision propagated through the trace. It cannot know that a request will later be slow or fail.

Strategies include:

- probabilistic sampling;
- parent-based decisions;
- higher rates for low-volume services or selected routes;
- deterministic selection from trace ID;
- approved synthetic or experiment cohorts.

Head sampling can miss every example of a rare failure. A service that records 1% of traffic without special rules has only about a 1% chance of retaining any particular request, assuming unbiased selection.

Record the sampling configuration and effective rate. Unsampled does not mean the request did not exist; it means detailed trace evidence was not retained.

## 12. Understand tail sampling

Tail sampling waits until enough spans or time reveal the outcome, then keeps traces matching rules such as:

- errors or invariant violations;
- latency above a threshold;
- rare routes or tenant tiers;
- unusual span attributes;
- representative baseline successes.

It improves retention of interesting outcomes but requires buffering, trace assembly, deadlines, memory, and routing. Long-running or fragmented traces may be incomplete when the decision occurs. Collector failure can disproportionately lose large or slow traces.

Tail rules can bias analysis. If all errors and 0.1% of successes are kept, raw trace counts cannot estimate the population without weights and policy knowledge. Preserve representative success traces for comparison.

Sampling is part of the evidence model and cost architecture, not merely a storage switch.

## 13. Recognize partial and broken traces

A trace can be incomplete because:

- a service lacks instrumentation;
- context was not propagated through a thread or message;
- head-sampling decisions differ or are ignored;
- a span was never ended;
- export buffers dropped data;
- a collector timed out before late spans arrived;
- clocks or IDs were invalid;
- trust-boundary policy deliberately restarted the trace;
- retention removed one portion.

Instrument dropped-span, export failure, queue, and collector health metrics. Mark known boundaries. Test propagation across HTTP, queues, scheduled work, retries, and cancellation.

Absence of a span does not prove absence of a call. It may mean the call was not instrumented or retained. Cross-check logs, dependency metrics, message identity, and source behavior before concluding.

## 14. Keep tracing overhead bounded

Cost comes from span creation, clock reads, context operations, attribute extraction, serialization, buffering, network transfer, collection, indexing, storage, and query. High-volume internal spans and unbounded attributes can change the system being observed.

Budget:

- spans per journey;
- attribute count and encoded bytes;
- events and links per span;
- sampling by service and route;
- exporter queue and memory;
- acceptable CPU and latency overhead;
- retained bytes and query cost.

Benchmark representative workloads with tracing disabled, recording but unsampled, and sampled/exported. Test overload behavior. Telemetry must drop or degrade according to a bounded policy rather than exhaust application capacity.

Do not disable propagation when dropping recording; downstream services may still need the sampling decision and causal identity.

## 15. Understand what a profile contains

A profile is a set of stack traces associated with measured values or sample counts. Depending on the profiler, it can represent:

- on-CPU samples;
- wall-clock or elapsed samples;
- allocations by bytes or objects;
- retained heap at a snapshot;
- lock contention or blocking delay;
- thread, task, or goroutine state;
- I/O or scheduler events;
- hardware performance events.

Each sample attributes resource behavior to a stack, often with labels such as process, thread, runtime, deployment, and build identity. Aggregating samples creates top tables, call graphs, or flame graphs.

The profile type and units are essential. A wide stack in a CPU flame graph means many CPU samples, not necessarily long wall latency. A wide allocation stack means allocation volume, not retained memory.

## 16. Distinguish CPU, wall, and off-CPU evidence

**CPU profiling** samples code while it executes on a CPU. It finds computation, runtime work, serialization, compression, and busy loops. It does not explain time waiting on locks, network, storage, or scheduling when the thread is not running.

**Wall-clock profiling** samples elapsed state and can reveal time across execution and waiting, but interpretation depends on how threads and blocked stacks are captured.

**Off-CPU or blocking profiling** attributes waiting to locks, I/O, sleep, scheduling, or other blocked states when supported.

A request with 2 seconds of latency and 20 ms of CPU will barely appear in a CPU profile even though it is slow. The trace localizes the wait to database acquisition; a blocking or lock profile may then attribute the internal wait path.

Always match the profile to the resource question.

## 17. Choose continuous or on-demand profiling

Continuous profiling collects bounded samples over time. Benefits include:

- evidence before an alert or rare event;
- comparison across releases, cells, and workloads;
- low-frequency regressions that disappear before manual attachment;
- population views rather than one selected process.

Costs include persistent overhead, storage, symbol management, privacy review, sampling bias, and operational ownership.

On-demand profiling targets a known window and can use richer or higher-frequency data. It risks missing transient behavior and may be unsafe to enable during overload.

Use continuous low-overhead profiling where the runtime and policy support it, then bounded on-demand captures for deeper questions. Verify overhead under peak load and create automatic expiry for high-detail sessions.

## 18. Preserve symbols and build identity

Raw addresses and optimized stacks are hard to interpret without:

- exact executable or artifact digest;
- debug symbols or symbol server;
- source revision;
- compiler and optimization settings;
- runtime and library versions;
- mapping or load addresses;
- container and deployment identity.

Inlining, tail calls, frame-pointer omission, just-in-time compilation, stripped binaries, and native/runtime transitions can alter stacks. A profiler may report `[unknown]`, runtime trampolines, or incomplete unwinding.

Store symbols under access control for at least the profile investigation window. Treat source paths and symbols as sensitive intellectual property. Test symbolization before the incident, not after the artifact is gone.

## 19. Interpret stack samples statistically

Sampling does not trace every execution. If 30% of representative CPU samples contain stack `encode_task`, estimate that the stack accounts for roughly 30% of sampled CPU under that workload and window. Accuracy depends on sample count, frequency, workload stationarity, profiler bias, and correct unwinding.

Distinguish:

- **inclusive value:** samples in a function or any descendant;
- **exclusive value:** samples attributed directly to the function frame;
- **call-site relationship:** how work arrived at the stack;
- **sample count and duration:** evidence strength and time window.

Small differences in rare stacks may be noise. Repeat captures, compare matched workloads, and report sample counts. A flame graph visualizes distribution; it does not establish causality or improvement by itself.

Chapter 123 will apply these rules to CPU and concurrency bottlenecks.

## 20. Correlate profiles with traces carefully

Some systems attach trace and span context to profile samples, enabling questions such as “Which stacks consumed CPU during slow task-update spans?” This is valuable but has limits:

- profile and trace sampling decisions differ;
- context may be absent on worker or runtime threads;
- one thread can execute work from many requests over the window;
- background CPU may have no request context;
- labels can increase cardinality and privacy exposure;
- correlation support and profile standards may be immature.

Use shared service, version, instance, and time windows as the baseline correlation. Add direct trace/span linkage only when the profiler supports it with measured overhead and bounded labels.

As of this chapter's research, the OpenTelemetry profiles specification is alpha. Design the evidence around stable concepts and keep transport or storage choices replaceable.

## 21. Protect privacy and security

Spans and profiles can expose:

- URLs, queries, database statements, and object names;
- tenant, user, device, and geographic identifiers;
- error messages and stack paths;
- service topology and dependency names;
- source symbols and proprietary algorithms;
- timing patterns that correlate user actions;
- baggage copied across trust boundaries.

Use allow-listed attributes, route templates, statement sanitization, pseudonymous references, field and event limits, access control, retention, and audited exports. Apply tenant deletion and privacy policy where applicable.

Do not attach function arguments, request bodies, SQL literals, tokens, or customer content to spans. Do not put secrets or identity authority into baggage. Review third-party exporters and collectors as data processors.

Restart or filter context at trust boundaries when correlation risk exceeds value, while documenting the resulting trace break.

## 22. Apply both signals to Atlas Tasks

An SLO alert shows elevated task-update latency in cell B.

The representative slow trace contains:

```text
task.update server                         2,041 ms
  authorization.check                        18 ms
  database.connection.acquire             1,892 ms
  database.transaction                        41 ms
  response.encode                              7 ms
```

The trace identifies the phase and shows no slow database query. Resource metrics reveal pool waiters and the configuration timeline. A CPU profile for the same version and cell shows normal CPU distribution, so optimizing encoding would not affect the primary symptom.

A blocking profile then attributes wait samples to the connection-pool condition variable, consistent with the trace and metrics. The combined evidence supports the Chapter 118 hypothesis without treating any single signal as proof.

For asynchronous search projection, producer and consumer spans carry message identity; a link represents the continuation. Queue delay is separated from consumer execution. Batch processing links all contributing messages rather than selecting an arbitrary parent.

## 23. Encode a signal-choice contract

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class TelemetryInvestigation:
    question: str
    signal: str
    resource_identity: bool
    causal_context: bool
    sampling_policy: str
    missing_evidence_policy: str
    bounded_attributes: bool
    trust_boundaries_defined: bool
    overhead_budget_percent: float
    build_identity: str
    profile_type: str | None = None

    def validate(self) -> None:
        if not self.question.strip():
            raise ValueError("investigation has no question")
        if self.signal not in {"trace", "profile", "trace_and_profile"}:
            raise ValueError("signal choice is invalid")
        if not self.resource_identity:
            raise ValueError("evidence lacks service and deployment identity")
        if self.signal in {"trace", "trace_and_profile"} and not self.causal_context:
            raise ValueError("trace lacks causal context")
        if not self.sampling_policy.strip() or not self.missing_evidence_policy.strip():
            raise ValueError("sampling or absence cannot be interpreted")
        if not self.bounded_attributes or not self.trust_boundaries_defined:
            raise ValueError("telemetry can leak or grow without bound")
        if not 0 < self.overhead_budget_percent <= 5:
            raise ValueError("telemetry overhead budget is unsafe or absent")
        if not self.build_identity.strip():
            raise ValueError("evidence cannot be tied to an artifact")
        if self.signal in {"profile", "trace_and_profile"} and self.profile_type not in {
            "cpu", "wall", "allocation", "retained_heap", "blocking"
        }:
            raise ValueError("profile lacks resource type and units")
```

Tests reject ambiguous evidence plans:

```python
from dataclasses import replace
import unittest

from telemetry_investigation import TelemetryInvestigation


def valid_plan() -> TelemetryInvestigation:
    return TelemetryInvestigation(
        question="Where does task-update latency and CPU accumulate in cell B?",
        signal="trace_and_profile",
        resource_identity=True,
        causal_context=True,
        sampling_policy="retain errors and slow traces plus 1% baseline; CPU sample at 99Hz",
        missing_evidence_policy="cross-check exporter loss and resource metrics",
        bounded_attributes=True,
        trust_boundaries_defined=True,
        overhead_budget_percent=2.0,
        build_identity="task-api@sha256:abc123",
        profile_type="cpu",
    )


class TelemetryInvestigationTests(unittest.TestCase):
    def test_complete_plan_is_accepted(self):
        valid_plan().validate()

    def test_missing_question_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "question"):
            replace(valid_plan(), question="").validate()

    def test_trace_without_context_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "causal"):
            replace(valid_plan(), causal_context=False).validate()

    def test_unknown_sampling_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "sampling"):
            replace(valid_plan(), sampling_policy="").validate()

    def test_unbounded_attributes_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "leak"):
            replace(valid_plan(), bounded_attributes=False).validate()

    def test_missing_trust_boundary_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "leak"):
            replace(valid_plan(), trust_boundaries_defined=False).validate()

    def test_excessive_overhead_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "overhead"):
            replace(valid_plan(), overhead_budget_percent=8.0).validate()

    def test_unsymbolizable_build_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "artifact"):
            replace(valid_plan(), build_identity="").validate()

    def test_profile_without_type_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "resource type"):
            replace(valid_plan(), profile_type=None).validate()


if __name__ == "__main__":
    unittest.main()
```

The model does not select a profiler or tracing platform. It ensures the evidence can answer a question, be interpreted under sampling and loss, remain bounded at trust boundaries, and map back to the exact artifact.

## 24. Review traces and profiles

Before approving instrumentation or an investigation, ask:

### Trace design

- Do spans represent meaningful operations rather than every function?
- Are names stable and attributes bounded?
- Does context cross threads, tasks, queues, retries, and scheduled work?
- Are batching, fan-in, and long-running continuation represented with links where appropriate?
- Is incoming context validated and separated from authorization?

### Sampling and evidence

- Are head or tail choices documented with effective rates and bias?
- Are rare failures and representative successes retained?
- Can exporter loss, missing instrumentation, and deliberate trace restart be distinguished?
- Are clocks and cross-host ordering interpreted honestly?

### Profiling

- Does the profile type match CPU, wall, allocation, retention, or blocking question?
- Are units, workload, duration, sample count, runtime, build, and symbols captured?
- Is continuous or on-demand overhead measured under representative load?
- Are inclusive and exclusive samples interpreted statistically?

### Protection

- Are trace state, baggage, attributes, stacks, symbols, access, and retention reviewed for privacy and security?
- Can telemetry failure or volume harm the application?
- Can an investigator move among SLO, trace, log, resource metric, and profile using shared context?

## Common Misconceptions

- **“A trace is a distributed log.”** It is a causal operation graph with timing and context; logs record discrete events.
- **“More spans always improve visibility.”** Excessive spans add overhead and obscure meaningful boundaries.
- **“The trace header proves identity.”** It carries correlation, not authorization.
- **“No span means no call occurred.”** Sampling, propagation, instrumentation, export, or retention may be missing.
- **“CPU profiles explain slow requests.”** Waiting can dominate wall latency while using little CPU.
- **“A flame graph shows exact execution history.”** It aggregates samples under a workload and time window.
- **“Tail sampling keeps all important traces.”** Rules, buffers, timeouts, and incomplete assembly still bias or lose evidence.
- **“Baggage is a convenient place for user context.”** It propagates broadly and can create privacy, security, and overhead risk.

## Core Computer Science Concept

This chapter applies **causal graphs, execution context, partial orders, sampling theory, stack aggregation, distributed clocks, information loss, and observer effects**. Traces reconstruct logical work; profiles estimate resource attribution across a population.

## Engineering Connections

- Process, thread, and network boundaries build on Chapters 43, 45, 58, and 61.
- Distributed ordering and asynchronous causality extend Chapters 112 and 113.
- Security and privacy controls follow Chapters 115 and 120.
- Metrics and exemplars begin with Chapter 121.
- Chapters 123 and 124 apply profiles to CPU, contention, allocation, retention, and resource leaks.

## From the Field

A team sees a two-second request trace and begins optimizing the widest application span. CPU profiles show that the code consumes only 20 ms of CPU; the span is wide because it waits on a connection pool. A blocking profile and pool metrics confirm contention. The visualization looked like application work, but choosing the resource-specific signal prevented an irrelevant rewrite.

## Engineering Review

### What problem does this solve?

It connects one logical journey across distributed boundaries and attributes aggregate runtime resource behavior to code stacks without confusing the two forms of evidence.

### Why was it designed this way?

Causal context explains request structure, while statistical stack sampling finds code-level concentration at lower volume than tracing every function.

### When should I use it?

Use tracing for cross-boundary request and workflow questions; use profiling for CPU, allocation, retention, blocking, and code-path distribution questions.

### When should I avoid it?

Do not add high-detail tracing or profiling without a question, overhead budget, data policy, sampling model, and artifact identity.

### How does this make me a better engineer?

You learn to match evidence to the mechanism, interpret missing and sampled data honestly, and cross-check causal, population, and resource views.

### How does this reduce waste?

It avoids function-level span explosions, CPU optimization of I/O waits, retention of every trace, privacy leaks through baggage, and profiles that cannot be symbolized or tied to a build.

## Handbook Principle #122

> Trace causal work across meaningful boundaries, profile the resource whose consumption you need to attribute, and preserve enough sampling, artifact, clock, and trust context to know what the missing evidence cannot prove.

## Practical Observation

Pick one slow trace and calculate its total on-CPU time from an appropriate profile or runtime measure. If wall duration and CPU differ substantially, list the waits that tracing, blocking profiles, and resource metrics must distinguish before any code optimization.

## Looking Ahead

Chapter 123 uses sampling profiles, call trees, flame graphs, scheduler evidence, and controlled benchmarks to distinguish CPU hot paths from lock, thread-pool, and runnable contention.

## References

- [OpenTelemetry — Tracing API](https://opentelemetry.io/docs/specs/otel/trace/api/)
- [OpenTelemetry — Context](https://opentelemetry.io/docs/specs/otel/context/)
- [OpenTelemetry — Sampling](https://opentelemetry.io/docs/concepts/sampling/)
- [OpenTelemetry — Profiles](https://opentelemetry.io/docs/specs/otel/profiles/)
- [W3C — Trace Context](https://www.w3.org/TR/trace-context/)
- [W3C — Baggage](https://www.w3.org/TR/baggage/)
- [Chapter 120 — Logs and Structured Events](120-logs-and-structured-events.md)
- [Chapter 121 — Metrics, SLIs, SLOs, and Actionable Alerts](121-metrics-slis-slos-and-actionable-alerts.md)
