# Chapter 59 — HTTP Semantics and API Behavior

HTTP is an application protocol for asking a recipient to act on a resource and return a response. Its familiar text-like vocabulary can hide precise rules about methods, representations, caching, retries, and intermediaries.

The central idea is:

> An HTTP exchange has method, target, fields, content, and status semantics; transport success or a single status number never tells the whole story.

## 1. A request expresses intent toward a resource

An HTTP request identifies a target and applies a method to it. A URI such as:

```text
https://api.example.test:443/orders/42?view=summary
```

contains a scheme, authority, path, and query. The URI identifies the target; it does not prescribe how a server stores or implements that resource. The fragment portion of a URI, when present, is interpreted by a user agent and is not sent as the request target.

A request carries control data in its method and fields and can carry content. The response carries a status code, fields, and optional content. Fields such as `Content-Type` describe the representation being transferred, not necessarily the resource's internal type.

HTTP is stateless in the protocol sense: each request's semantics can be understood independently. Applications can still create sessions using cookies, authorization credentials, server-side data, or explicit tokens.

## 2. Methods carry contracts

Common methods express different intentions:

| Method | Intended semantics | Safe | Idempotent |
| --- | --- | --- | --- |
| `GET` | Retrieve a current representation | Yes | Yes |
| `HEAD` | Retrieve response metadata without response content | Yes | Yes |
| `POST` | Ask the target to process supplied content | No | Not inherently |
| `PUT` | Create or replace target resource state with supplied representation | No | Yes |
| `PATCH` | Apply a defined partial modification | No | Not inherently |
| `DELETE` | Remove the association with the target resource | No | Yes |
| `OPTIONS` | Discover communication options | Yes | Yes |

**Safe** means the client does not request a state change, although logging and billing side effects can occur. **Idempotent** means multiple identical requests have the same intended effect as one request; responses can still differ.

These are protocol contracts, not automatic implementation properties. A `GET` endpoint that deletes data violates safe semantics. A `PUT` handler that charges on every attempt violates its idempotent intent.

Automatic retries should follow both method semantics and application knowledge. A failed `POST` can have completed before its response was lost. An idempotency key can let a server recognize repeat attempts, but only if its scope, retention, request matching, and stored result are designed explicitly.

## 3. Status codes classify outcomes

The first digit groups the response:

- `1xx` reports an interim response;
- `2xx` reports that the request was successfully received, understood, and accepted according to the specific code;
- `3xx` indicates redirection or another action needed to complete the request;
- `4xx` indicates a condition associated with the client request;
- `5xx` indicates the server failed to fulfill an apparently valid request.

The specific code matters. `201 Created` differs from `204 No Content`; `401 Unauthorized` normally challenges for authentication while `403 Forbidden` refuses the request; `404 Not Found` does not prove the resource never existed; `409 Conflict` and `412 Precondition Failed` describe different forms of state disagreement; `429 Too Many Requests` differs from `503 Service Unavailable` in scope and likely ownership.

A non-`2xx` response is still a successfully transported HTTP response. Conversely, `200 OK` can contain an application-level failure if an API ignores HTTP semantics. Clients should evaluate status, relevant fields, representation type, and bounded response content.

## 4. Fields are typed protocol metadata

HTTP field names are case-insensitive, but field values follow each field's grammar. Treating all fields as arbitrary strings loses semantics and can create parsing vulnerabilities.

Important categories include:

- representation metadata such as `Content-Type` and `Content-Encoding`;
- negotiation fields such as `Accept` and `Accept-Language`;
- validators such as `ETag` and `Last-Modified`;
- preconditions such as `If-Match` and `If-None-Match`;
- cache controls such as `Cache-Control`, `Age`, and `Vary`;
- authentication fields such as `Authorization` and `WWW-Authenticate`;
- routing and intermediary fields such as `Host`, `Forwarded`, and `Via`.

Do not log credentials, session cookies, authorization fields, or full sensitive URLs by default. Query strings commonly reach browser history, access logs, monitoring systems, and intermediary logs.

## 5. Content negotiation selects a representation

A resource can have multiple representations. A client advertises acceptable media types, languages, encodings, or other dimensions; the server selects a response and identifies its format.

`Content-Type: application/json` says how to interpret the content. It does not guarantee that the bytes are valid JSON or match the application's schema. A robust client limits body size, validates the media type and syntax, and handles an error representation that differs from the success schema.

If a response varies based on request fields, `Vary` helps caches incorporate those fields into cache selection. Omitting a necessary variation dimension can serve the wrong language, encoding, or personalized representation.

## 6. Redirects create another request

A `Location` field can direct the client to another URI. The status code determines how the next request relates to the original. `303 See Other` explicitly directs retrieval with `GET`; `307 Temporary Redirect` and `308 Permanent Redirect` preserve the method and content.

Redirect handling crosses security boundaries. A client should bound redirect count, resolve relative locations correctly, restrict acceptable schemes, and avoid forwarding credentials to an unrelated authority. A redirect loop is an application or configuration failure, not a reason for unlimited retry.

Permanent redirects can be cached. Deploy them carefully because clients and intermediaries can continue using an incorrect destination after the origin is fixed.

## 7. Cookies add ambient state

A server can send `Set-Cookie`; a user agent later includes applicable values in `Cookie` requests according to domain, path, expiry, security, and same-site rules. Cookies are attached by the user agent, so they can affect requests that application code did not explicitly decorate.

Security attributes have distinct purposes:

- `Secure` limits transmission to secure transport contexts;
- `HttpOnly` prevents ordinary script access but not network use;
- `SameSite` restricts some cross-site sending behavior;
- narrow domain and path scope reduce unintended exposure.

A cookie is client-controlled input, even if the server originally issued it. Protect integrity where required, rotate session identifiers, expire server-side sessions, and never place secrets in a cookie merely because it is marked `HttpOnly`.

## 8. Caching is correctness logic

A cache can reuse a stored response only when method, target, selected request fields, freshness, and directives permit it. A **fresh** response can normally be reused without contacting the origin. A **stale** response may require validation with a validator such as an entity tag.

```text
client:  If-None-Match: "revision-17"
server:  304 Not Modified
```

The `304` response tells the cache to reuse its stored representation with updated metadata; it is not an empty version of an ordinary `200` response.

`Cache-Control: no-store` asks caches not to store the response. `no-cache` allows storage but requires validation before reuse. `private` restricts reuse by shared caches. These directives are not interchangeable.

Cache keys and invalidation are application design. Personalized responses need correct authorization and cache controls. `Vary: *` prevents reuse, while an incomplete `Vary` can mix representations across request contexts.

## 9. HTTP versions preserve semantics

HTTP/1.1 serializes message syntax over connections and requires unambiguous framing. HTTP/2 uses binary frames, compressed fields, and concurrent streams over one connection. HTTP/3 maps the same HTTP semantics onto QUIC, with independent transport streams and integrated TLS protection.

The version changes framing and transport behavior, not the meaning of `GET`, `404`, `Content-Type`, or cache directives. An intermediary can receive one version and forward another.

Multiplexing improves concurrency but adds new capacity limits and failure scopes. HTTP/2 still inherits TCP connection-level head-of-line blocking after packet loss. HTTP/3 avoids that across independent QUIC streams, though congestion and endpoint failures can still affect the connection.

## 10. Diagnose the complete exchange

Useful read-only inspection commands include:

| Goal | Command |
| --- | --- |
| Response fields only | `curl --head https://example.com/` |
| Request and response protocol detail | `curl --verbose https://example.com/` |
| Bounded response with redirects | `curl --location --max-redirs 5 --max-time 10 https://example.com/` |
| Windows response object | `Invoke-WebRequest -Method Head -Uri https://example.com/` |

Verbose output can expose cookies, authorization fields, client certificates, and URLs. Redact before sharing it. Do not use options that disable certificate verification to make a failing request appear healthy.

Record the method, effective URI, selected protocol version, status, redirect chain, relevant fields, timing, and a bounded sanitized body. Compare the direct origin only when authorized; bypassing a proxy or gateway can change both security and behavior.

## Common Misconceptions

- “HTTP success means status 200.” Several `2xx` codes express success, and the application contract still matters.
- “`no-cache` means do not store.” It means validate before reuse; `no-store` controls storage.
- “PUT and POST differ only by naming style.” Their method semantics and retry properties differ.
- “HTTP/2 changes API semantics.” It changes framing and multiplexing while retaining HTTP semantics.
- “A transport error means the server did nothing.” The operation can complete before the response path fails.

## Core Computer Science Concept

HTTP is a **uniform interface over representations**. A small vocabulary of methods, status codes, and metadata composes across many resource implementations while caches and intermediaries preserve defined semantics.

## Engineering Connections

- TCP supplies HTTP/1.1 and HTTP/2 with ordered bytes, but HTTP defines message framing and meaning.
- TLS protects HTTPS transport and authenticates a service identity; it does not validate response business logic.
- Conditional requests provide optimistic concurrency control through validators and preconditions.
- Observability systems need structured status and timing data without collecting credentials or personal content.

## From the Field

An API client retries every failed request, including `POST /payments`, after a read timeout. The server committed a payment but its response was lost, so the retry charges again. A request-scoped idempotency key and durable result record make the ambiguous transport outcome reconcilable; merely increasing the timeout does not.

## Engineering Review

### What problem does this solve?

It standardizes requests, responses, representations, metadata, caching, and intermediaries across distributed applications.

### Why was it designed this way?

Stable, extensible semantics let clients and servers evolve independently and allow generic intermediaries to route, cache, and transform messages under explicit rules.

### When should I use it?

Use HTTP when resource-oriented request-response semantics, broad tooling, and interoperable intermediaries fit the application.

### When should I avoid it?

Avoid forcing HTTP vocabulary onto a protocol whose interaction, latency, or delivery model fundamentally conflicts with request-response behavior.

### How does this make me a better engineer?

It lets you design retryable operations, interpret failures precisely, and use caching and negotiation without accidental behavior.

### How does this reduce waste?

It prevents duplicate effects, unnecessary origin work, incompatible clients, cache leaks, and debugging based only on one status number.

## Handbook Principle #59

> Preserve HTTP's method, status, representation, and cache semantics; an API is a protocol contract, not a collection of URLs.

## Practical Observation

Use `curl --head` or an equivalent read-only client against a public documentation page you are authorized to access. Record the effective URI, status, `Content-Type`, cache directives, validators, and any redirect. Explain whether a cache may store and reuse the response; do not include cookie or authorization values in your notes.

## Looking Ahead

HTTPS carries HTTP through a protected channel, but protection depends on cryptographic keys and verified identity. Chapter 60 traces the TLS handshake, certificate path, and trust decisions behind that channel.

## References

- [RFC 9110 — HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110)
- [RFC 9111 — HTTP Caching](https://www.rfc-editor.org/rfc/rfc9111)
- [RFC 9112 — HTTP/1.1](https://www.rfc-editor.org/rfc/rfc9112)
- [RFC 9113 — HTTP/2](https://www.rfc-editor.org/rfc/rfc9113)
- [RFC 9114 — HTTP/3](https://www.rfc-editor.org/rfc/rfc9114)
- [RFC 9205 — Building Protocols with HTTP](https://www.rfc-editor.org/rfc/rfc9205)
