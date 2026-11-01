# Chapter 70 — Subprocesses, HTTP Clients, and External Boundaries

Calling a program or service crosses into a separately scheduled, versioned, authenticated, and failure-prone system. A function call cannot make that boundary local or reliable.

The central idea is:

> Preserve argument and protocol structure, bound every wait and response, validate every returned value, and assume timeout leaves the remote effect uncertain.

## 1. An external call has more than one outcome

A child process can fail before launch, run and return nonzero, time out, emit invalid output, or succeed after performing only part of its promised work. An HTTP call adds name resolution, connection, TLS, redirects, authentication, status, representation, and remote application state.

Model the boundary in stages:

```text
prepare request → start/send → wait → receive → classify status
                → decode → validate → reconcile effect
```

Each stage needs its own error context. “Command failed” and “API error” discard the evidence needed for recovery.

Success at one stage does not imply later success. A child exit status of zero can accompany malformed JSON. HTTP `200` can carry the wrong media type or schema. A timeout can happen after a mutation completed.

## 2. Pass subprocess arguments as a vector

Use a sequence whose elements are already separated arguments:

```python
import subprocess

completed = subprocess.run(
    ["tool", "inspect", "--format=json", target],
    check=False,
)
```

Do not interpolate values into one shell string:

```python
subprocess.run(f"tool inspect {target}", shell=True)  # unsafe boundary
```

With the default `shell=False`, Python launches the program without a shell interpreting spaces, wildcard characters, substitutions, pipes, or redirections. A value such as `a; delete-everything` remains one argument to the program.

This prevents shell injection; it does not make the target program interpret the argument safely. Validate identifiers, paths, URLs, and requested actions according to that program's contract.

## 3. Invoke a shell only for shell language

Pipelines, redirection, variable expansion, and shell builtins require a shell. Prefer expressing a simple operation with Python and explicit subprocesses. When shell language is genuinely the program, put it in a reviewed script with a declared interpreter and pass data as arguments or standard input.

`shell=True` delegates parsing to a platform-specific shell. POSIX quoting rules do not apply to Windows `cmd.exe`, and `shlex.quote` is not a universal cross-platform escape function. Batch files can introduce Windows shell parsing even when the Python call does not visibly request a shell.

Never use `eval` or an assembled shell string to support arbitrary command options. Parse an allowlisted operation into a fixed argument vector.

## 4. Executable discovery is a trust decision

The first argument can be resolved through `PATH`. The selected executable can differ under a scheduler, virtual environment, service account, or modified working directory.

Options include:

- require a configured absolute executable path;
- use `shutil.which` once, validate the result, and record it;
- construct a narrow `PATH` for a known toolchain;
- invoke the current Python interpreter through `sys.executable`.

Log the executable identity and version without leaking sensitive arguments. Do not place an untrusted directory before system tool directories.

`cwd` changes the child's working directory, not merely where Python searches for data. Pass it only when the child contract requires it and validate the directory first.

## 5. Control standard streams deliberately

`subprocess.run` can inherit, discard, redirect, supply, or capture standard streams:

```python
completed = subprocess.run(
    arguments,
    stdin=subprocess.DEVNULL,
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="strict",
    check=False,
)
```

`DEVNULL` prevents a background process from unexpectedly reading an inherited terminal. `capture_output=True` keeps stdout and stderr separate and buffers both in memory.

Capturing is not size-bounded. A noisy or malicious child can exhaust memory. For potentially large output, redirect to controlled files, stream with `Popen`, or use a protocol with explicit limits while continuously draining pipes.

Choose bytes when output is not declared text. When text is expected, set encoding and error policy rather than depending on the locale.

Do not combine stderr into stdout when the output format requires pure machine data.

## 6. Interpret launch, status, and output separately

`subprocess.run` can raise `OSError` when launch fails and `TimeoutExpired` when its wait expires. With `check=True`, a nonzero status raises `CalledProcessError`; with `check=False`, inspect `returncode` directly.

`check=True` is convenient when every nonzero status is one error category. Use explicit status handling when a command documents distinct results such as “not found,” “difference detected,” and operational failure.

Validate output only after acceptable status:

```python
if completed.returncode != 0:
    raise ToolError(
        f"tool exited with status {completed.returncode}: "
        f"{sanitize(completed.stderr)}"
    )

document = parse_and_validate(completed.stdout)
```

Bound diagnostic length and redact credentials. A child can echo its arguments, environment, or input on stderr.

## 7. A timeout is not complete cancellation

`subprocess.run(..., timeout=seconds)` kills and waits for the direct child when communication times out, then raises `TimeoutExpired`. Process creation itself is not interruptible on every platform, and descendants or externally started work can survive.

A child can submit a remote job and time out before reporting its identifier. Killing it does not cancel the job. A program that launches a process group, service, container, or scheduled task needs domain-specific cancellation and reconciliation.

Use an operation identifier and query observed state after ambiguity. Do not retry a mutating child merely because its wrapper timed out.

For long-running process trees, define graceful termination, deadline, escalation, and ownership for orphan cleanup. Platform process-group behavior differs.

## 8. Environment inheritance can leak and destabilize

By default, a child inherits the Python process environment, including proxy settings, locale, credentials, debugging flags, and executable search paths.

Pass `env` only after deciding whether to inherit and override or construct a minimal mapping:

```python
import os

child_env = {
    "PATH": controlled_path,
    "LANG": "C.UTF-8",
}
```

A fully minimal environment can break required platform behavior; full inheritance can leak secrets. Document the allowlist for privileged automation.

Prefer protected file descriptors, standard input, or a credential provider over command-line secrets. Process arguments and some environment data can be visible to local inspection and crash reporting.

## 9. HTTP requests preserve method and representation

Build URLs with URL libraries rather than string concatenation. Encode query parameters with `urllib.parse.urlencode`, and keep secrets out of URLs because histories, proxies, and access logs commonly record them.

With the standard library:

```python
from urllib.request import Request, urlopen

request = Request(
    "https://api.example.test/items",
    method="GET",
    headers={"Accept": "application/json"},
)

with urlopen(request, timeout=5.0) as response:
    body = response.read()
```

Default HTTPS handling verifies certificates and service identity through the platform's configured trust behavior. Do not install an unverified TLS context to “fix” a trust error.

The timeout covers blocking operations as implemented by the client; it is not a universal end-to-end deadline across DNS, every redirect, retries, body processing, and application work. Measure and bound the entire operation at the appropriate layer.

## 10. Status is part of the response contract

HTTP clients can expose non-success responses in different ways. `urllib.request` raises `HTTPError` for many HTTP error statuses; that exception also contains status, headers, and a response body.

Classify specific statuses:

- `2xx` still requires representation validation;
- `3xx` requires a redirect policy;
- `400` often means the request contract is invalid;
- `401` and `403` are different authentication and authorization evidence;
- `404` can be an expected absence or an error by domain;
- `409` or `412` can signal state/precondition conflict;
- `429` or `503` can be transient only under a bounded retry policy;
- `5xx` does not prove a retry is safe.

Read only a bounded error body and redact it before logging. It can contain user data, internal details, or an HTML proxy page rather than the API's JSON error schema.

## 11. Bound and validate the response

Check the effective URL, status, media type, byte size, encoding, syntax, schema, and domain invariants.

`Content-Length` can reject an obviously oversized response early but is not sufficient: it can be absent, incorrect, or describe encoded rather than expanded size. Read at most `limit + 1` bytes and reject overflow.

For JSON APIs, require the documented media type and decode with the declared character rules. Reject duplicate object members and non-finite numbers when interoperability matters. Schema validation does not authorize referenced resources.

Compressed bodies need both compressed and expanded size controls. Deeply nested structured data can consume excessive CPU or recursion even when byte size is bounded.

## 12. Redirects cross authority boundaries

A redirect can change scheme, host, port, path, method, and where credentials or content are sent. General-purpose clients often follow some redirects automatically.

For automation, define:

- allowed schemes and downgrade policy;
- same-origin or allowlisted destination policy;
- maximum redirect count;
- method and body behavior for each redirect status;
- whether authorization, cookies, and client identity can cross;
- final effective URL validation.

Do not send bearer credentials to a new host merely because the original host redirected there. Reject redirects before the redirected request is sent when secrets or sensitive content are present.

## 13. Authentication is least privilege plus containment

Acquire credentials from an approved secret reference or runtime identity. Scope them to the service, operation, resources, and lifetime required.

Add an `Authorization` header only after validating the destination origin. Never log the header or put it in an exception. Ensure debugging hooks, proxy traces, and retry libraries also redact it.

Differentiate authentication failure from network failure. Repeating the same rejected credential can trigger lockout or load without changing the result.

Mutual TLS, signed requests, OAuth tokens, cookies, and API keys have distinct replay and delegation properties. Follow the service protocol rather than inventing one shared “auth” wrapper.

## 14. Retry by semantics, not exception class alone

Retry only when all of these hold:

- the operation is safe to repeat or has a scoped idempotency key;
- the failure is classified as transient;
- attempts and total elapsed time are bounded;
- delay uses backoff and jitter;
- server `Retry-After` is interpreted under a maximum policy;
- every attempt is observable under one operation identifier;
- ambiguous effects are reconciled before repetition.

Do not retry validation failures, authentication denial, most authorization failures, or every `4xx`. Do not automatically retry a state-changing `POST` without application guarantees.

A timeout says the client stopped waiting. The server may still complete. This is the same ambiguity seen at TCP and HTTP layers, now owned by the automation.

## 15. A bounded external-boundary module

This Python 3.11+ example calls a JSON-producing program and fetches an unauthenticated JSON resource. It rejects cross-origin redirects and bounds HTTP response bytes:

```python
from __future__ import annotations

import json
import subprocess
from collections.abc import Sequence, Set
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class BoundaryError(Exception):
    """A controlled external-boundary failure."""


def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise BoundaryError(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def reject_constant(value: str) -> object:
    raise BoundaryError(f"non-finite JSON number: {value}")


def parse_json(data: bytes, source: str) -> object:
    try:
        text = data.decode("utf-8", errors="strict")
        return json.loads(
            text,
            object_pairs_hook=unique_object,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BoundaryError(f"invalid JSON from {source}: {exc}") from exc


def run_json_program(
    arguments: Sequence[str],
    *,
    timeout_seconds: float,
    maximum_captured_bytes: int,
) -> object:
    if not arguments:
        raise ValueError("arguments must not be empty")

    try:
        completed = subprocess.run(
            list(arguments),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise BoundaryError(
            f"program timed out after {timeout_seconds} seconds"
        ) from exc
    except OSError as exc:
        raise BoundaryError(f"program could not start: {exc}") from exc

    if len(completed.stdout) > maximum_captured_bytes or \
            len(completed.stderr) > maximum_captured_bytes:
        raise BoundaryError("captured program output exceeds policy")
    if completed.returncode != 0:
        diagnostic = completed.stderr.decode("utf-8", errors="replace")[:500]
        raise BoundaryError(
            f"program exited with status {completed.returncode}: {diagnostic}"
        )

    return parse_json(completed.stdout, "program stdout")


def origin(url: str) -> tuple[str, str, int | None]:
    parts = urlsplit(url)
    return parts.scheme.casefold(), (parts.hostname or "").casefold(), parts.port


class SameOriginRedirects(HTTPRedirectHandler):
    def redirect_request(
        self,
        req: Request,
        fp: object,
        code: int,
        msg: str,
        headers: object,
        newurl: str,
    ) -> Request | None:
        destination = urljoin(req.full_url, newurl)
        if origin(req.full_url) != origin(destination):
            raise BoundaryError("cross-origin redirect rejected")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_json(
    url: str,
    *,
    timeout_seconds: float,
    maximum_bytes: int,
    allowed_schemes: Set[str] = frozenset({"https"}),
) -> object:
    parts = urlsplit(url)
    if parts.scheme.casefold() not in allowed_schemes or not parts.hostname:
        raise BoundaryError("URL scheme or host is not allowed")
    if parts.username is not None or parts.password is not None:
        raise BoundaryError("credentials in URLs are not allowed")

    request = Request(
        url,
        method="GET",
        headers={
            "Accept": "application/json",
            "User-Agent": "handbook-boundary-example/1",
        },
    )
    opener = build_opener(SameOriginRedirects())

    try:
        with opener.open(request, timeout=timeout_seconds) as response:
            if response.headers.get_content_type() != "application/json":
                raise BoundaryError("response is not application/json")
            data = response.read(maximum_bytes + 1)
    except HTTPError as exc:
        raise BoundaryError(f"HTTP status {exc.code}") from exc
    except URLError as exc:
        raise BoundaryError(f"HTTP transport failed: {exc.reason}") from exc

    if len(data) > maximum_bytes:
        raise BoundaryError("HTTP response exceeds size policy")
    return parse_json(data, url)
```

The subprocess helper checks captured length only after `run` has buffered it; this is an acceptance limit, not a memory-safety bound. Use streaming `Popen` logic or file redirection when the child is not trusted to remain small.

The HTTP helper is deliberately unauthenticated. An authenticated client should build an opener whose redirect and credential policy is specific to its protocol, and it should validate the response schema after parsing.

## 16. Test both boundaries locally

In a disposable test:

- invoke the current `sys.executable` with a small `-c` program that emits valid JSON;
- invoke a program that returns nonzero and one that sleeps past the timeout;
- emit invalid, duplicate-key, non-UTF-8, and oversized output;
- run a loopback HTTP server returning valid JSON, wrong media type, oversized content, redirects, and error statuses;
- assert status categories, size limits, effective redirect policy, and absence of secrets in diagnostics.

Loopback tests prove client behavior without depending on an external service. They do not prove production DNS, TLS, proxy, identity, or service policy. Add authorized integration tests for those boundaries separately.

## Common Misconceptions

- “A list of arguments makes the child safe.” It prevents shell parsing; the target program still needs validated values and permissions.
- “`timeout` cancels the operation.” Descendants or remote effects can continue after the direct wait ends.
- “HTTP `200` means valid data.” Media type, size, syntax, schema, and domain rules still apply.
- “Retries fix transient failures.” They are safe only with bounded timing and repeatable effects.
- “Authorization headers stay at the original host.” Redirect and client behavior need an explicit credential-containment policy.

## Core Computer Science Concept

External calls are **distributed state transitions with partial observation**. The caller controls a request and a waiting policy but observes only returned status and data; interruption can leave the callee's state unknown.

## Engineering Connections

- Argument vectors preserve process framing just as JSON preserves record structure.
- HTTP method and idempotency semantics determine whether transport retry is safe.
- Timeouts bound waiting, while reconciliation resolves uncertain effects.
- Least-privilege credentials and same-origin redirect policy contain authority at the external boundary.

## From the Field

An automation sends `POST /create-user`, times out, and immediately retries. The first request completed but its response was lost, creating two accounts. Adding a client-generated idempotency key, status lookup, total deadline, and reconciliation path fixes the boundary; increasing the socket timeout only changes how often ambiguity appears.

## Engineering Review

### What problem does this solve?

It lets Python automation invoke programs and HTTP services without losing argument, status, timeout, trust, or response-validation boundaries.

### Why was it designed this way?

External systems execute independently and fail partially, so callers need structured requests, bounded waits, and explicit outcome classification.

### When should I use it?

Use these patterns whenever automation crosses into a child process, command-line tool, or HTTP API.

### When should I avoid it?

Avoid a generic wrapper when the target protocol requires richer streaming, authentication, cancellation, or transaction semantics than the wrapper models.

### How does this make me a better engineer?

It makes you preserve the exact boundary contract instead of treating every external failure as an exception to retry.

### How does this reduce waste?

It prevents shell injection, hangs, silent status loss, memory surprises, leaked credentials, invalid-response propagation, and duplicate effects.

## Handbook Principle #70

> Cross every process and HTTP boundary with structured inputs, bounded waiting and output, least authority, validated responses, and a plan for ambiguous effects.

## Practical Observation

Place the example module in a disposable directory and build the loopback tests listed above. Record which failures occur before launch, after process status, during HTTP transport, at HTTP status, and during representation validation. Verify that timeout and redirect diagnostics contain no sensitive request data, then delete the directory.

## Looking Ahead

External calls depend on the exact interpreter and libraries available. Chapter 71 separates Python installations, virtual environments, dependency declarations, lock strategies, indexes, project metadata, entry points, and upgrade policy.

## References

- [Python `subprocess` documentation](https://docs.python.org/3.14/library/subprocess.html)
- [Python `urllib.request` documentation](https://docs.python.org/3.14/library/urllib.request.html)
- [Python `urllib.error` documentation](https://docs.python.org/3.14/library/urllib.error.html)
- [RFC 9110 — HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110)
