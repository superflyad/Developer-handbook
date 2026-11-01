# Chapter 102 — Lambda, API Gateway, and Serverless Execution

A serverless function removes server provisioning from the application team. It does not remove runtime lifecycle, capacity, identity, networking, failure, cost, or ownership. A function that can scale to a thousand concurrent invocations can also open a thousand database connections, retry one poisoned batch indefinitely, or turn a malformed response into a public `502`.

The central idea is:

> Bound a function by its invocation contract, deadline, concurrency, downstream capacity, identity, and terminal failure path before relying on automatic scale.

## 1. Define which Lambda execution model you mean

AWS Lambda's current product surface includes more than the original short-lived function model. AWS documentation distinguishes Event Functions, Durable Functions, and additional managed or web-oriented execution modes with different lifecycle and quota behavior.

This chapter centers **Lambda Event Functions**: handlers invoked directly, asynchronously, or through event source mappings. They are the common foundation for API Gateway backends, S3 notifications, SQS consumers, and stream processors. A standard Event Function invocation runs for at most 15 minutes.

Durable Functions add checkpointed, code-first workflows that can span waits and resume for up to one year. Lambda Managed Instances and other newer modes alter execution duration, isolation, or concurrency assumptions. Treat those as distinct design choices and verify their current documentation, availability, quotas, and cost. Do not copy an Event Function assumption—such as one active invocation per execution environment—onto every Lambda mode.

For any function, record:

- function type and Region;
- trigger or caller and invocation mode;
- input and output schema;
- handler deadline and upstream deadline;
- retry and duplicate behavior;
- peak rate, duration, and concurrency;
- downstream limits;
- execution role and resource policy;
- package, runtime, architecture, and version;
- configuration, secrets, network path, logs, and failure destination.

“It is serverless” answers none of those questions.

## 2. An Event Function is a handler plus configuration

Lambda creates an isolated execution environment, loads the configured runtime and deployment artifact, runs initialization code, and invokes a named handler with an event and context. Configuration is part of the release:

- runtime and instruction-set architecture;
- handler entry point;
- memory, which also affects CPU allocation;
- timeout and ephemeral storage;
- environment variables, layers, and file systems;
- execution role;
- VPC subnets and security groups;
- logging, tracing, encryption, and code signing;
- concurrency, asynchronous invocation, and event-source settings.

Keep the handler thin. Parse and validate the event, construct a request-scoped context, call testable domain code, translate results into the trigger's response format, and emit a structured outcome. Business code should not require a real Lambda context object to run in a unit test.

Validate untrusted events at the boundary. AWS service events evolve and may contain optional or new fields. Accept forward-compatible additions, reject missing invariants, cap collection and payload sizes, and avoid logging complete request bodies or credentials.

## 3. Invocation mode determines retry ownership

Lambda Event Functions have three important invocation paths:

| Path | Who waits? | Who retries? | Typical examples |
| --- | --- | --- | --- |
| Synchronous | caller waits for the result | caller or front door | API Gateway, SDK `RequestResponse` |
| Asynchronous | caller receives acceptance after Lambda queues the event | Lambda asynchronous queue | S3, SNS, SDK `Event` |
| Event source mapping | Lambda pollers read and batch records, then invoke synchronously | source and mapping policy | SQS, Kinesis, DynamoDB Streams, Kafka |

A `202` from asynchronous invocation means Lambda accepted the event into its internal queue. It does not mean the handler ran or the business effect succeeded. A successful event-source-mapping invocation normally causes Lambda to checkpoint or delete source records according to that source's protocol.

Document the actual source, not merely “Lambda trigger.” S3-to-Lambda retry differs from SQS-to-Lambda retry; a synchronous API client sees errors that an asynchronous producer never receives. The same handler code can have different operational guarantees under different invokers.

## 4. Build and pin the deployment artifact

Event Functions use a `.zip` archive or a container image. Package type is fixed for an existing function; moving between them requires a new function.

A `.zip` package is a good default for ordinary handlers. Include application code and pinned dependencies built for the target runtime, operating system, and architecture. Do not rely accidentally on an SDK version present in the managed runtime. A container image helps when native dependencies, build control, or an existing image toolchain justify it, but Lambda still applies its runtime contract and quotas; it is not a general long-running container host.

Produce artifacts once in CI, then promote the identical digest through environments. Generate a software bill of materials, scan dependencies and images, sign where policy requires it, and retain provenance. Never rebuild “the same” version separately for production.

Smaller packages and selective imports generally reduce initialization work, but size is not the only latency factor. Measure initialization with the real runtime, dependencies, architecture, extensions, network configuration, and traffic shape.

## 5. Own runtime and architecture upgrades

Managed runtimes receive security and functional updates. Published function versions preserve most function configuration, but runtime management controls can still affect how runtime updates are applied. Inventory runtime versions and end-of-support dates, test updates in a representative environment, and retain a rollback version.

Changing between `x86_64` and `arm64` requires compatible native dependencies and a new build. Compare price and performance with real traffic; architecture is not a text-only configuration flip when compiled libraries exist.

Layers can share libraries or extensions, but they also hide dependency resolution across releases. Pin layer versions, scan them, include them in provenance, and avoid one mutable “common” layer that can break unrelated functions. Duplication in independent artifacts is often safer than runtime coupling.

## 6. Understand Init, Invoke, reset, and Shutdown

For an on-demand Event Function, Lambda initializes a new execution environment when no reusable environment is available. Initialization downloads or prepares code, starts the runtime and extensions, and executes code outside the handler. Lambda then invokes the handler.

After success, Lambda may freeze and later reuse that environment. On a crash or timeout, Lambda resets it; later invocation can include a suppressed reinitialization. Lambda eventually shuts environments down for maintenance or capacity management. No environment lifetime is guaranteed.

Safe reuse includes:

- initialize immutable configuration and SDK clients outside the handler;
- reuse healthy network connections with keep-alive and reconnect logic;
- cache public or tenant-neutral immutable data with validation;
- finish background work before returning;
- reset request-scoped logging, tracing, and authentication context.

Do not retain one user's secrets or mutable request data in globals. Warm reuse is a performance optimization, never a durability or correctness mechanism.

## 7. `/tmp` and memory are ephemeral state

Each Event Function environment has configurable ephemeral `/tmp` storage. Files can survive warm reuse in the same environment, but another concurrent environment starts with a different directory and any environment can disappear.

Use `/tmp` for bounded scratch data or a validated cache. Name files safely, enforce size limits, remove sensitive material, verify checksums, and handle cache misses. Use S3, DynamoDB, a database, or EFS when state must survive environment replacement or be shared.

Global variables have the same rule. They can cache clients or immutable lookup data; they cannot count events reliably, coordinate locks, or remember that a business action completed. Concurrent execution environments do not share memory.

## 8. Cold starts are one part of latency

A cold start includes environment preparation and user initialization before handler work. Its impact depends on arrival pattern, package and imports, runtime, VPC and extension behavior, initialization code, and latency objective.

Optimize in this order:

1. measure end-to-end latency and initialization separately;
2. remove unnecessary initialization and dependencies;
3. initialize reusable clients once;
4. choose suitable memory and architecture by benchmark;
5. keep downstream handshakes and DNS healthy;
6. use provisioned concurrency only when the latency objective justifies its cost.

Do not send artificial requests merely to “keep a function warm.” That does not guarantee capacity for a burst and creates cost and operational noise. Provisioned concurrency pre-initializes a defined number of environments and exposes utilization and spillover metrics; it is the explicit control for latency-sensitive Event Functions.

## 9. Timeouts form a descending budget

Set the function timeout from a measured worst-case budget, not the platform maximum. A public request path should satisfy:

```text
client deadline
> API Gateway integration allowance
> Lambda timeout plus invocation overhead
> downstream request deadline plus local cleanup
```

If the Lambda timeout exceeds the caller's wait, the client can abandon the request while the function continues changing state. A client retry can then overlap the first invocation. Use idempotency keys for mutating APIs and propagate a remaining deadline to dependencies.

Set connection, request, and total deadlines on every outbound call. Leave time to record an outcome and return a valid response. Do not launch background work and return: the environment can freeze immediately, and resumed callbacks can contaminate a later invocation. Publish durable work to a queue or workflow before returning.

For tasks routinely near 15 minutes, split work into idempotent units, use Step Functions or a Durable Function when appropriate, or select batch or container compute. Increasing the timeout conceals an unsuitable execution model.

## 10. Memory also buys CPU

Lambda allocates CPU in proportion to configured memory. More memory can shorten a CPU-bound invocation enough to reduce both latency and total cost. Too little memory can cause garbage collection, paging behavior in dependencies, or out-of-memory termination; too much may waste money when work is idle on a remote service.

Benchmark representative payloads across memory sizes and architectures. Compare:

- initialization and handler percentiles;
- maximum memory used;
- billed duration and request cost;
- error and timeout rate;
- downstream calls and connection count;
- ephemeral storage high-water mark.

Tune batch size together with memory and timeout. Ten records can amortize invocation overhead but require enough memory for the entire decoded batch and enough time for the slowest record.

## 11. Concurrency is rate multiplied by duration

For an Event Function with one active invocation per environment, approximate concurrency as:

```text
concurrency = requests per second × average duration in seconds
```

At 2,000 requests per second and 250 milliseconds, average concurrency is about 500. Plan with peak rate and high duration percentiles, plus headroom—not only averages. A dependency slowdown increases duration, which increases concurrency, which can increase dependency load further.

Regional account concurrency is shared. New accounts can start with reduced quotas, and current quotas vary by Region and execution mode. Inspect Service Quotas before launch and load-test the full path.

Concurrency is not request rate. Lambda also applies scaling and request-rate controls. A function that needs 100 environments immediately after being idle may see a different ramp than one already serving steady traffic.

## 12. Reserved and provisioned concurrency solve different problems

**Reserved concurrency** dedicates part of Regional concurrency to one Event Function and caps that function at the same value. It has no separate charge. Use it to protect critical capacity and, equally important, to keep a function from overwhelming a database or partner.

**Provisioned concurrency** pre-initializes environments for a version or alias. It reduces initialization latency and adds cost. Traffic above it can spill into on-demand capacity unless reserved-concurrency configuration prevents that.

Set a cap from both sides:

```text
required concurrency = peak rate × target duration
safe concurrency <= downstream connection or throughput budget
```

If required exceeds safe, automatic scale cannot solve the design. Reduce duration, batch safely, add a queue, cache reads, use RDS Proxy where appropriate, partition the dependency, or reject excess synchronous load. Never let each invocation create an unbounded database pool.

Setting reserved concurrency to zero is an emergency stop for runaway recursion or a broken consumer. The runbook must also address queued work and safe re-enable; zero does not erase events waiting elsewhere.

## 13. Asynchronous invocation has its own queue

For asynchronous invocation, Lambda stores the event before returning acceptance. By default, a handler error is retried two more times with delays. Throttling and system errors can be retried from the internal queue for up to six hours by default with increasing backoff. Duplicate delivery can occur even without a handler error.

Configure maximum event age and retry attempts from the business deadline. Capture exhausted or expired events:

- an on-failure **destination** receives an invocation record with request and response context;
- a function **DLQ** retains the original event in SQS or SNS.

Choose deliberately; they contain different information. Alarm on `AsyncEventAge`, errors, throttles, destination delivery failure, and DLQ delivery failure. A configured failure target is not useful if its resource policy or KMS key blocks Lambda.

Do not stack Lambda asynchronous queuing in front of a workflow that needs visible backlog control. An explicit SQS queue provides retention, depth, age, redrive, and consumer scaling controls owned by the application.

## 14. Event source mappings are pollers and batch coordinators

An event source mapping is a Lambda resource that polls a queue or stream and synchronously invokes the Event Function with a batch. It controls source, batch size, batching window, filtering, concurrency or pollers, retry, record age, bisect behavior for supported streams, and terminal destinations.

Mappings process at least once. The handler must be idempotent. For streams, partition or shard order constrains recovery; a failing batch can pause later records. For SQS, messages remain in the queue but invisible until the mapping deletes them after success.

Choose batch size by payload bytes, per-record work, memory, deadline, and failure cost. A larger batch reduces invocation overhead but increases the blast radius of an unhandled exception. Test a maximum-size batch, not only one record.

Filtering at the mapping can reduce invocations, but filtered records are not an application backlog waiting for a future code change. Version and test filter patterns like routing code.

## 15. Report partial batch failure

Without partial batch response, one SQS record failure makes the entire batch visible again after the visibility timeout, including records already processed successfully. Enable `ReportBatchItemFailures` and return the identifiers of failed records so Lambda can delete successful ones.

Catch exceptions per record and make each record's effect idempotent. If the handler throws outside that logic, Lambda treats the whole batch as failed. For FIFO queues, stop after the first failure and report that record plus later unprocessed records so ordering is preserved.

The queue visibility timeout must exceed the function's maximum processing and deletion path with adequate retry margin. Lambda's configuration checks do not replace workload testing. Coordinate:

- function timeout;
- batch window;
- queue visibility and retention;
- source redrive count and DLQ retention;
- maximum mapping concurrency;
- downstream capacity.

Chapter 101's duplicate and DLQ rules still apply; Lambda does not remove them.

## 16. API Gateway is a public contract and policy point

API Gateway creates REST, HTTP, and WebSocket APIs. For a request-response Lambda backend, start by comparing HTTP APIs and REST APIs:

- HTTP APIs offer a smaller feature set and lower-cost path with routes, JWT authorizers, CORS, and Lambda or HTTP integrations.
- REST APIs add features such as API keys, per-client usage controls, request validation, AWS WAF integration, private endpoints, caching, and richer transformation or monitoring options.

Choose from required features, not the product name. API keys identify usage plans; they are not end-user authentication. A Lambda function URL can be a simpler HTTPS front door when its authentication, routing, throttling, validation, custom domain, and observability capabilities are sufficient. Do not rebuild API Gateway poorly inside the handler.

Define the API before code: methods, paths, status codes, error body, authentication, authorization, idempotency, pagination, payload limit, timeout, rate policy, and compatibility.

## 17. Proxy integration still has a schema

In Lambda proxy integration, API Gateway passes request method, path, headers, query values, body, and request context to the function. The function returns a structured response containing a status code, headers, body string, and optional base64 flag.

“Proxy” does not mean schema-free. Payload format versions and REST versus HTTP API events differ. Bind the integration and tests to one documented format. Treat `requestContext` as input from the gateway, not a stable application-wide user model, and do not trust client-supplied headers that resemble authorizer context.

Return deliberate HTTP semantics:

- `400` for malformed syntax;
- `401` when authentication is absent or invalid;
- `403` for an authenticated principal lacking authority;
- `404` when the addressed resource is not visible;
- `409` for a state or idempotency conflict;
- `429` for explicit admission control;
- `5xx` for server failures safe to expose generically.

An unhandled exception or malformed proxy response often becomes a generic gateway error. Log the internal cause with correlation, but never send stack traces or secrets to clients.

## 18. Authentication is not authorization

API Gateway can use IAM authorization, Cognito or JWT authorizers, Lambda authorizers, mutual TLS, and product-specific resource policies. Validate issuer, audience, signature, expiry, and required scopes for tokens. Cache authorizer results only with a key and lifetime that preserve revocation and tenant boundaries.

The handler must still authorize the principal against the requested resource and action. A valid token for tenant A must not read tenant B because a path parameter was trusted.

Configure CORS narrowly for browser clients. CORS controls which browser origins can read a response; it does not authenticate callers or stop non-browser requests. Apply throttling and quotas as admission control, not as the only denial-of-service protection. For REST APIs requiring WAF or resource policies, select that product intentionally.

## 19. Separate invoke permission from execution permission

Two IAM directions matter:

- A **resource-based policy** on the function controls which service or principal may invoke it. Constrain service permissions with source ARN and account where supported.
- The **execution role** is assumed by Lambda and controls what handler code may access.

Give each security boundary its own role rather than sharing one broad role across unrelated functions. Scope actions and resources, constrain KMS encryption context where useful, and include only required logging, tracing, VPC, and data permissions.

The execution role uses temporary credentials made available to the runtime. Do not embed access keys or call `AssumeRole` merely to re-assume the same role. If a function needs cross-account access, assume a narrowly trusted target role and bound the session.

An event source mapping may need service-side permissions in addition to handler permissions. Trace who polls, who invokes, and who reads the source rather than adding wildcards until the trigger works.

## 20. VPC attachment changes the network path

Every Event Function runs in a Lambda-managed VPC. Attach it to subnets and security groups in your VPC only when it needs private resources such as RDS, ElastiCache, or an internal endpoint.

Select subnets across Availability Zones and security-group egress toward exact dependencies. A function attached to a public subnet does not receive a public IP address. Internet access requires a valid route through NAT or another egress design; AWS service access can use interface or gateway endpoints where supported.

Plan address and connection capacity. High concurrency can exhaust database connections, NAT ports, partner rate limits, or subnet and VPC quotas even though Lambda's networking implementation scales efficiently. Prefer private service endpoints when they improve security and cost, but include their policies, DNS, and Availability Zone behavior in tests.

Do not attach a VPC merely as a security ritual. It adds configuration and failure surfaces without restricting public service access unless routing and policy actually do so.

## 21. Configuration is versioned; secrets are retrieved

Environment variables are literal, version-specific configuration and have a small aggregate size limit. Use them for non-secret identifiers and behavior such as table name, log level, or feature mode. Validate required values during initialization and fail clearly.

Use Secrets Manager or an appropriate protected parameter service for credentials and tokens. Retrieve through the execution role, cache for a bounded time, handle rotation overlap, and never log secret values. Encryption of an environment variable at rest does not prevent code, operators with configuration access, or debug output from revealing it.

Configuration changes should flow through infrastructure code and the same review path as code. Publish a new version when version-specific configuration changes, test it, and move an alias. Avoid editing production `$LATEST` or environment variables manually.

## 22. Versions and aliases make releases addressable

`$LATEST` is mutable. Publishing creates a numbered version with immutable code and most configuration. An alias is a movable name pointing to a version and can split traffic between two versions.

Point production triggers and API integrations at an alias, not unqualified `$LATEST`. A delivery can then:

1. build and scan one artifact;
2. update and test `$LATEST` in a delivery boundary;
3. publish a numbered version;
4. run smoke tests against that version;
5. shift a small alias weight;
6. compare errors, latency, business outcomes, and cost;
7. advance or move the alias back.

Weighted traffic is not a database migration strategy. Old and new versions can run concurrently and receive retries later, so schema and side effects must remain compatible throughout the rollback window.

## 23. Observe invocation, business outcome, and lag

Emit structured logs with request ID, correlation ID, trigger type, function version, cold-start indicator, operation, outcome, duration, and safe entity identifiers. Redact authorization headers, cookies, tokens, secrets, and sensitive payloads. Set log retention explicitly.

Monitor at least:

- invocations, errors, throttles, duration percentiles, and timeouts;
- concurrent executions and claimed account concurrency;
- provisioned-concurrency utilization and spillover;
- asynchronous event age, received events, and dropped events;
- destination and DLQ delivery failures;
- stream iterator age or source lag;
- queue age and DLQ depth for SQS;
- API Gateway request count, `4xx`, `5xx`, integration latency, and total latency;
- domain success, rejection, duplicate, and reconciliation metrics.

`Errors` excludes requests rejected before function invocation, such as throttles, so alert across metrics. A low Lambda error rate does not prove API success if API Gateway is rejecting requests or a queue backlog is growing.

Use traces to separate gateway, initialization, handler, SDK, and downstream time. Sampling must retain enough errors and high-latency requests to diagnose incidents without capturing sensitive payloads.

## 24. Model cost as traffic times work

Event Function cost includes requests and duration as a function of memory, with additional charges possible for provisioned concurrency, ephemeral storage, event-source pollers, extensions, logs, traces, network transfer, NAT, API Gateway, and downstream services.

Estimate by workload:

```text
monthly invokes = arrival rate × time
compute = invokes × billed duration × configured memory
fan-out and retries multiply invokes
```

Optimize the total system, not Lambda in isolation. A larger memory setting can reduce duration. Batching can reduce invocation overhead but increase latency and retry work. Provisioned concurrency can meet a user latency objective but waste money on a sporadic background consumer. Excess debug logs can cost more than execution.

Tag ownership, allocate shared API and network cost, alarm on invocation anomalies, and review cost per successful business operation. Recursive invocation or an unintended event loop is both a reliability and cost incident.

## 25. Know when not to use an Event Function

Event Functions fit bounded, stateless, event- or request-driven work that can tolerate environment replacement and explicit retry semantics. Choose another model when work needs:

- a continuously running process or listener;
- stable local state or specialized host control;
- execution beyond the mode's deadline;
- sustained compute where containers are simpler or cheaper;
- very large memory, disk, GPU, or unusual kernel capabilities;
- a complex workflow whose state and compensation should be visible.

Durable Functions now offer code-first checkpointed workflows; Step Functions offers explicit state-machine orchestration and broad service integrations. Compare visibility, language and replay constraints, state history, integration patterns, execution guarantees, testing, operations, and cost. Do not turn a standard Event Function into an implicit workflow by recursively invoking functions and storing progress in global memory.

## 26. Build a serverless contract checker

This standard-library model checks deadline, capacity, retry, batch, and public API invariants:

```python
from dataclasses import dataclass
from math import ceil


@dataclass(frozen=True)
class FunctionContract:
    invocation: str
    timeout_seconds: int
    peak_requests_per_second: float
    p95_duration_seconds: float
    reserved_concurrency: int
    downstream_concurrency_limit: int
    idempotent: bool
    failure_destination: bool
    log_retention_days: int
    least_privilege_reviewed: bool

    def required_concurrency(self) -> int:
        return ceil(self.peak_requests_per_second * self.p95_duration_seconds)


@dataclass(frozen=True)
class TriggerContract:
    kind: str
    upstream_timeout_seconds: int = 0
    visibility_timeout_seconds: int = 0
    partial_batch_response: bool = False
    access_policy_declared: bool = False


@dataclass(frozen=True)
class ServerlessContract:
    function: FunctionContract
    trigger: TriggerContract

    def validate(self) -> None:
        function = self.function
        trigger = self.trigger
        if function.timeout_seconds <= 0 or function.timeout_seconds > 900:
            raise ValueError("Event Function timeout must be between 1 and 900 seconds")
        if function.reserved_concurrency < function.required_concurrency():
            raise ValueError("reserved concurrency cannot carry the declared peak")
        if function.reserved_concurrency > function.downstream_concurrency_limit:
            raise ValueError("function concurrency exceeds downstream capacity")
        if function.invocation in {"async", "event-source"} and not function.idempotent:
            raise ValueError("retriable invocation requires an idempotent handler")
        if function.invocation == "async" and not function.failure_destination:
            raise ValueError("asynchronous invocation requires a terminal destination")
        if function.log_retention_days <= 0:
            raise ValueError("log retention must be explicit")
        if not function.least_privilege_reviewed:
            raise ValueError("execution role requires a least-privilege review")
        if trigger.kind == "api":
            if trigger.upstream_timeout_seconds <= function.timeout_seconds:
                raise ValueError("API timeout must leave margin beyond function timeout")
            if not trigger.access_policy_declared:
                raise ValueError("API requires an explicit access policy")
        if trigger.kind == "sqs":
            if trigger.visibility_timeout_seconds <= function.timeout_seconds + 10:
                raise ValueError("SQS visibility must exceed function timeout plus margin")
            if not trigger.partial_batch_response:
                raise ValueError("SQS batches require partial batch response")
```

Tests expose the design assumptions:

```python
import unittest

from serverless_contract import FunctionContract, ServerlessContract, TriggerContract


def api_contract() -> ServerlessContract:
    function = FunctionContract(
        "sync", 10, 80, 0.2, 20, 50, True, False, 30, True
    )
    return ServerlessContract(function, TriggerContract("api", 15, access_policy_declared=True))


class ServerlessContractTests(unittest.TestCase):
    def test_bounded_api_is_accepted(self) -> None:
        api_contract().validate()

    def test_short_upstream_deadline_is_rejected(self) -> None:
        contract = api_contract()
        trigger = TriggerContract("api", 10, access_policy_declared=True)
        with self.assertRaisesRegex(ValueError, "leave margin"):
            ServerlessContract(contract.function, trigger).validate()

    def test_peak_above_reserved_concurrency_is_rejected(self) -> None:
        function = FunctionContract(
            "sync", 10, 200, 0.2, 20, 50, True, False, 30, True
        )
        with self.assertRaisesRegex(ValueError, "declared peak"):
            trigger = TriggerContract("api", 15, access_policy_declared=True)
            ServerlessContract(function, trigger).validate()

    def test_downstream_overload_is_rejected(self) -> None:
        contract = api_contract()
        function = FunctionContract(
            "sync", 10, 80, 0.2, 20, 12, True, False, 30, True
        )
        with self.assertRaisesRegex(ValueError, "downstream capacity"):
            ServerlessContract(function, contract.trigger).validate()

    def test_async_requires_idempotency_and_destination(self) -> None:
        function = FunctionContract(
            "async", 60, 10, 1, 10, 10, False, False, 14, True
        )
        with self.assertRaisesRegex(ValueError, "idempotent"):
            ServerlessContract(function, TriggerContract("async")).validate()

    def test_async_requires_terminal_destination(self) -> None:
        function = FunctionContract(
            "async", 60, 10, 1, 10, 10, True, False, 14, True
        )
        with self.assertRaisesRegex(ValueError, "terminal destination"):
            ServerlessContract(function, TriggerContract("async")).validate()

    def test_sqs_batch_requires_partial_response(self) -> None:
        function = FunctionContract(
            "event-source", 30, 5, 1, 5, 10, True, True, 14, True
        )
        trigger = TriggerContract("sqs", visibility_timeout_seconds=90)
        with self.assertRaisesRegex(ValueError, "partial batch"):
            ServerlessContract(function, trigger).validate()


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

Save the blocks as `serverless_contract.py` and `test_serverless_contract.py`, then run:

```bash
python -m unittest -v test_serverless_contract.py
```

A production checker should inspect authorized read-only inventory for package digest, runtime, architecture, versions, aliases, memory, timeout, storage, concurrency, asynchronous policies, mappings, execution and resource policies, VPC configuration, API routes and authorizers, logs, alarms, tracing, KMS, code signing, quotas, and tags. It must not invoke functions, shift aliases, redrive events, change concurrency, or alter infrastructure during validation.

## 27. Review a serverless design

```text
Lambda function type, Region, trigger, invocation mode, and owner:
input/output schemas, payload limits, validation, and compatibility:
artifact digest, package type, runtime, architecture, dependencies, and SBOM:
Init work, cold-start objective, reuse, global data, and /tmp behavior:
handler timeout, upstream deadline, downstream deadlines, and cancellation:
memory/CPU/storage benchmarks and maximum-size event or batch:
peak rate, p95 duration, required concurrency, quota, and scaling ramp:
reserved cap, provisioned concurrency, downstream capacity, and backpressure:
retry owner, duplicate behavior, idempotency key, age, and failure destination:
mapping source, batch/window/filter, partial failure, lag, and DLQ:
API product, routes, proxy version, statuses, errors, CORS, and throttling:
authentication, resource authorization, invoke policy, and execution role:
VPC subnets, security groups, DNS, endpoints, egress, and connection budget:
environment configuration, secret retrieval, rotation, and redaction:
version, alias, canary, compatibility, comparison, and rollback:
logs, retention, metrics, traces, alarms, runbooks, and cost per outcome:
```

## Common Misconceptions

- “Serverless means no infrastructure.” The provider owns hosts; the application still owns configuration, quotas, security, and operations.
- “Lambda always runs only one request per environment.” That Event Function assumption does not apply automatically to every newer Lambda execution mode.
- “A warm environment preserves state.” Reuse is optional and isolated; durable state belongs elsewhere.
- “A successful asynchronous invoke means the work succeeded.” It means the event entered Lambda's queue.
- “Automatic scaling protects the database.” Uncapped concurrency can exhaust downstream connections faster.
- “Reserved concurrency removes cold starts.” It reserves and caps capacity; provisioned concurrency pre-initializes environments.
- “One failed record retries only that record.” Without partial batch response, an entire SQS batch can return.
- “API keys authenticate users.” They support usage identification and plans, not user authentication by themselves.
- “VPC attachment gives a function a public IP.” Public-subnet placement alone does not provide internet access.
- “Encrypted environment variables are a secret store.” Runtime code and authorized configuration readers can still access their plaintext values.

## Core Computer Science Concept

Lambda Event Functions apply **process isolation, demand-driven scheduling, queueing, leases, and Little's Law**. Rate multiplied by service time predicts concurrent work. Reused environments are caches, not shared memory. Retry turns invocation into at-least-once processing unless stable identity and atomic effects make repeats harmless.

## Engineering Connections

- Concurrency applies Chapter 76's worker and queue-capacity model.
- Idempotency, partial batches, and destinations extend Chapter 101's delivery contracts.
- API status codes and deadlines implement Chapter 59's HTTP semantics.
- Execution and resource policies apply Chapter 92's identity directions.
- VPC egress and private endpoints build on Chapters 93 and 94.
- Versions and weighted aliases apply Chapter 77's canary and rollback lifecycle.

## From the Field

An API function averages 100 milliseconds in testing, so its team leaves concurrency unbounded. A slow database query raises duration to five seconds during launch traffic. Concurrency expands fiftyfold, each environment opens a database connection, and the database collapses. Reserved concurrency sized to the connection budget, short query deadlines, RDS Proxy where suitable, admission control, and an asynchronous queue for deferrable work would have turned the same slowdown into controlled rejection or backlog.

## Engineering Review

### What problem does this solve?

It converts a Lambda and API Gateway design into testable contracts for invocation, lifecycle, deadline, capacity, identity, networking, failure, deployment, observability, and cost.

### Why was it designed this way?

Event Functions scale by creating isolated environments in response to demand. The application's correctness therefore depends on stateless handlers, bounded concurrency, duplicate-safe effects, and explicit external state.

### When should I use it?

Use this model for bounded API handlers, file and service events, queue consumers, stream processors, scheduled tasks, and other request- or event-driven work.

### When should I avoid it?

Avoid a standard Event Function for continuously running services, sustained host-oriented compute, work beyond its deadline, large specialized resources, or complex hidden workflows. Evaluate containers, batch, Step Functions, or Durable Functions.

### How does this make me a better engineer?

It teaches you to translate traffic and duration into capacity, separate execution permission from invoke permission, scope retry to the trigger, and treat configuration as release state.

### How does this reduce waste?

It reduces idle servers, oversized packages, repeated cold-start folklore, duplicate batch work, runaway scale, database exhaustion, unused provisioned concurrency, excessive logs, and unsafe manual releases.

## Handbook Principle #102

> A serverless function is safe to scale only when its deadline, duplicate behavior, concurrency, and downstream budget are all bounded.

## Practical Observation

Choose one production Event Function. Calculate peak concurrency from measured rate and p95 duration, then compare it with reserved concurrency, Regional quota, database or API capacity, and the trigger's retry behavior. Trace one timeout from client or queue through every retry and terminal destination. Any unexplained multiplier is both a reliability and cost risk.

## Looking Ahead

Functions fit bounded event work, but many services need long-running processes, portable images, sidecars, schedulers, and richer runtime control. Chapter 103 compares ECR artifacts, ECS tasks and services, Fargate and EC2 capacity, and EKS ownership boundaries.

## References

- [AWS Lambda — Functions and durable functions](https://docs.aws.amazon.com/lambda/latest/dg/lambda-functions-chapter.html)
- [AWS Lambda — Event Function invocation methods](https://docs.aws.amazon.com/lambda/latest/dg/lambda-invocation.html)
- [AWS Lambda — Execution environment lifecycle](https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtime-environment.html)
- [AWS Lambda — Event Function scaling](https://docs.aws.amazon.com/lambda/latest/dg/lambda-concurrency.html)
- [AWS Lambda — Reserved concurrency](https://docs.aws.amazon.com/lambda/latest/dg/configuration-concurrency.html)
- [AWS Lambda — Asynchronous invocation errors and retries](https://docs.aws.amazon.com/lambda/latest/dg/invocation-async-error-handling.html)
- [AWS Lambda — Event source mappings](https://docs.aws.amazon.com/lambda/latest/dg/invocation-eventsourcemapping.html)
- [AWS Lambda — Using Lambda with Amazon SQS](https://docs.aws.amazon.com/lambda/latest/dg/with-sqs.html)
- [AWS Lambda — SQS error handling and partial batch response](https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-errorhandling.html)
- [AWS Lambda — Deployment packages](https://docs.aws.amazon.com/lambda/latest/dg/configuration-function-zip.html)
- [AWS Lambda — Event Function versions](https://docs.aws.amazon.com/lambda/latest/dg/configuration-versions.html)
- [AWS Lambda — Aliases](https://docs.aws.amazon.com/lambda/latest/dg/configuration-aliases.html)
- [AWS Lambda — Execution roles](https://docs.aws.amazon.com/lambda/latest/dg/lambda-intro-execution-role.html)
- [AWS Lambda — VPC access](https://docs.aws.amazon.com/lambda/latest/dg/configuration-vpc.html)
- [AWS Lambda — Environment variables](https://docs.aws.amazon.com/lambda/latest/dg/configuration-envvars.html)
- [AWS Lambda — Metrics](https://docs.aws.amazon.com/lambda/latest/dg/monitoring-metrics-types.html)
- [AWS Lambda — Quotas](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html)
- [AWS Lambda — Durable Function concepts](https://docs.aws.amazon.com/lambda/latest/dg/durable-basic-concepts.html)
- [Amazon API Gateway — Choose between REST APIs and HTTP APIs](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-vs-rest.html)
- [Amazon API Gateway — Lambda proxy integrations](https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html)
- [Chapter 101 — SQS, SNS, EventBridge, and Asynchronous Workflows](101-sqs-sns-eventbridge-and-asynchronous-workflows.md)
