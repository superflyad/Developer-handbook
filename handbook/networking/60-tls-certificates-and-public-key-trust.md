# Chapter 60 — TLS, Certificates, and Public-Key Trust

Transport Layer Security (TLS) protects application data against passive observation, undetected modification, and message forgery while authenticating one or both endpoints according to an application trust model. It does not decide whether the application or its data is trustworthy.

The central idea is:

> TLS protects a channel only when key agreement, certificate validation, service identity, and application policy all reach the intended endpoint.

## 1. The handshake creates protected traffic keys

Before carrying application data, a TLS client and server negotiate protocol parameters, establish shared secrets, authenticate handshake state, and confirm that both derived compatible keys. In a typical TLS 1.3 server-authenticated exchange, the client sends supported parameters and a key share; the server selects parameters, supplies its key share and certificate material, proves possession of the certificate's private key, and authenticates the transcript.

The public-key operations establish identity and fresh shared secrets. Symmetric traffic keys then protect records efficiently. Distinct keys and nonces are derived for different directions and handshake stages.

The handshake can also negotiate an application protocol through ALPN, such as HTTP/2. A completed TLS handshake proves only the negotiated TLS and identity properties; application authorization and request success happen later.

## 2. A certificate binds an identity to a public key

An X.509 certificate is a signed data structure containing a subject public key, issuer, validity interval, identifiers, usage constraints, and extensions. The corresponding private key is not inside the certificate and must remain controlled by its owner.

Possessing a certificate file does not prove identity. During the handshake, the endpoint signs transcript-related data to prove it controls the matching private key. The client then evaluates whether the certificate is acceptable for the intended service.

Protect private keys with narrow file and service permissions, managed secret storage, rotation, and audited access. Copying a production private key into a troubleshooting bundle turns observation into a credential incident.

## 3. Trust is a path, not one signature

A server usually presents an end-entity certificate and one or more intermediate CA certificates. The client attempts to construct a certification path toward a trust anchor in its configured trust store:

```text
locally trusted root CA
        signs
intermediate CA certificate
        signs
service certificate
        contains
service public key and identifiers
```

For each step, path validation considers signatures, validity, basic constraints, permitted key usage, name constraints, policy, and other profile rules. The root trust anchor is normally selected from local configuration and need not be sent by the server.

A chain can be cryptographically consistent yet untrusted because its root is absent from the client's trust store. Conversely, installing a new root delegates authority to that root within its constraints. Trust-store changes are security changes, not generic connectivity fixes.

Servers should present required intermediates. Sending only the leaf certificate can work on a client that cached or independently retrieves an intermediate and fail on a clean client.

## 4. Service identity must match the reference name

Path validation answers whether a trusted authority certified the presented key. Identity verification separately asks whether the certificate identifies the service the client intended to reach.

For a DNS-based service, the client constructs a reference identifier from its configured destination and matches it against appropriate certificate identifiers, normally `subjectAltName` entries. Connecting to an IP address while expecting a DNS certificate can fail because the reference identity changed.

DNS resolution and certificate identity are related but distinct. An attacker who redirects DNS still needs a certificate acceptable for the intended reference identity. A valid certificate for `other.example` does not authenticate `api.example`.

Wildcards have constrained matching behavior and broaden the scope of one private key. Prefer explicit names when operationally reasonable, and never replace hostname verification with a loose substring test.

## 5. Time and usage constraints are validation inputs

Certificates contain `notBefore` and `notAfter` times. An expired certificate, a not-yet-valid certificate, or a badly incorrect client clock can stop validation. Renewal must account for deployment, propagation, rollback, and every endpoint actually serving the name.

Key usage and extended key usage restrict what a certificate can authorize. CA certificates require appropriate CA constraints. A certificate issued for client authentication is not automatically suitable for server authentication.

When diagnosing time failures, compare clocks and the complete served chain before renewing anything. Replacing a valid certificate will not repair a stale load-balancer listener or an omitted intermediate.

## 6. Revocation has operational limits

A CA can publish revocation information through certificate revocation lists or OCSP. Clients differ in how they obtain, cache, staple, and enforce that information. Network failure while checking revocation can create a choice between availability and strict rejection, and some clients use soft-fail behavior.

Revocation is therefore not an instant universal delete switch. Short certificate lifetimes, rapid credential rotation, protected keys, stapled status where applicable, and incident-specific trust removal all contribute to response.

Do not infer “not revoked” merely because a client connected. Record the client, validation policy, status source, and observation time.

## 7. Mutual TLS authenticates both TLS endpoints

In ordinary HTTPS, the server presents a certificate and the client authenticates through an application mechanism such as a session or token. With mutual TLS (mTLS), the server also requests a client certificate and validates its path and identity.

mTLS establishes a cryptographic client identity at the TLS endpoint. The application still needs authorization: which operations may that identity perform? If a reverse proxy terminates mTLS, the backend sees the proxy's connection unless an authenticated, integrity-protected identity signal is forwarded under a strict trust contract.

Client private keys need the same protection as server keys. Sharing one client certificate across a fleet destroys individual attribution and complicates revocation.

## 8. Resumption changes cost, not trust requirements

TLS can resume earlier sessions using pre-shared key material, reducing handshake cost. Resumption state has a lifetime and security scope and must be protected like other authentication material.

TLS 1.3 can permit early application data before the handshake fully completes. That data has replay considerations and is unsuitable for operations that cannot safely repeat unless the application protocol provides defenses. Faster establishment does not suspend request semantics.

Key updates and new connections limit how long one set of traffic secrets is used. Forward secrecy reduces what later private-key compromise can reveal about previously recorded sessions when ephemeral key agreement and surrounding assumptions hold; it does not protect a currently compromised endpoint.

## 9. Encryption ends where TLS terminates

A browser might establish TLS to a CDN, gateway, or load balancer rather than directly to an application process. That component decrypts the request and may create a separate protected or unprotected connection upstream.

Map each segment explicitly:

```text
client == TLS A ==> edge proxy == TLS B ==> application
```

TLS A and TLS B can use different names, certificates, trust stores, client identities, and policies. A valid public certificate on the edge says nothing about the security of the backend hop.

TLS also does not hide every observable property. IP addresses, timing, sizes, and some negotiation metadata can remain visible depending on protocol features and deployment. Nor does TLS make malicious content safe once it reaches an authenticated endpoint.

## 10. Inspect without disabling validation

Useful read-only observations include:

| Goal | Command or tool |
| --- | --- |
| TLS and HTTP summary | `curl --verbose --head https://example.com/` |
| Presented certificates | `openssl s_client -connect example.com:443 -servername example.com -showcerts` |
| Certificate details from a file | `openssl x509 -in certificate.pem -noout -text` |
| Windows TLS summary | `curl.exe -vI https://example.com/` |
| Interactive validation | Browser connection and certificate viewer |

Always send the intended server name when using a generic TLS client; virtual hosts can select certificates by that name. `s_client` is an inspection tool, and its successful socket connection is not by itself proof that hostname and trust validation passed. Read its verification result and independently preserve the reference name.

Do not normalize `--insecure`, `-k`, disabled hostname verification, or a blanket trust-store import as fixes. Those switches remove the control under investigation. If an isolated lab uses an untrusted test CA, scope that trust to the disposable lab and document its removal.

A useful failure record includes client and version, destination name and address, observation time, negotiated TLS and application protocol, served leaf and intermediates, validation error, trust-store context, and the TLS termination point. Never collect private keys or session secrets unless a separately authorized diagnostic explicitly requires them.

## Common Misconceptions

- “Encryption proves the website is legitimate.” TLS can authenticate a service name; it cannot judge the service's business intent or content.
- “The server sends the trusted root.” Trust anchors normally come from the client's configured trust store.
- “A valid chain means the hostname matches.” Path and service-identity validation are distinct requirements.
- “mTLS authorizes the client.” It authenticates a TLS identity; application policy grants permissions.
- “Disabling verification is a connectivity fix.” It converts a trust failure into an unauthenticated connection.

## Core Computer Science Concept

TLS uses **composed proofs with explicit trust anchors**. Key agreement establishes shared secrets, signatures prove possession and protect the transcript, certificate paths delegate identity assertions, and local policy decides which roots and names are acceptable.

## Engineering Connections

- DNS finds an address, while TLS verifies that the reached endpoint represents the intended service identity.
- HTTP semantics remain above TLS; an encrypted `500` response is still an application failure.
- Reverse proxies create multiple trust boundaries when they terminate and re-establish TLS.
- Reliable time, secret management, and deployment inventory are prerequisites for certificate operations.

## From the Field

A certificate is renewed on the origin servers, but some clients still report expiration. Inspection by destination address shows one load-balancer listener serving the old leaf certificate. Renewing again changes nothing; identifying every TLS termination point and its deployed certificate resolves the split behavior.

## Engineering Review

### What problem does this solve?

It creates confidential, integrity-protected application channels and authenticates endpoints according to configured identities and trust anchors.

### Why was it designed this way?

Public-key authentication can establish identity and fresh shared secrets across an untrusted network, while symmetric record protection handles bulk traffic efficiently.

### When should I use it?

Use TLS whenever application traffic crosses a boundary where observation, modification, or endpoint impersonation must be resisted.

### When should I avoid it?

Do not treat TLS as a substitute for application authorization, secure endpoints, data validation, or an explicit trust model.

### How does this make me a better engineer?

It lets you trace a trust decision from reference name through certificate path and private-key proof to the actual termination point.

### How does this reduce waste?

It prevents blind certificate replacement, dangerous verification bypasses, incomplete-chain failures, and misplaced trust in an encrypted hop.

## Handbook Principle #60

> A protected channel is only as trustworthy as its reference identity, certificate path, private-key control, and actual termination point.

## Practical Observation

Inspect a public documentation site with a browser certificate viewer or a validating command-line client. Record the reference name, leaf identifiers, issuer chain, validity interval, negotiated protocol, and termination clues. Do not export private material or disable verification. Explain separately why the path is trusted and why the service name matches.

## Looking Ahead

TLS provides a general protected channel. Chapter 61 examines SSH, which combines protected transport with explicit host identity, user authentication, remote execution, file transfer, and forwarding.

## References

- [RFC 9846 — The Transport Layer Security (TLS) Protocol Version 1.3](https://www.rfc-editor.org/rfc/rfc9846)
- [RFC 5280 — Internet X.509 Public Key Infrastructure Certificate and CRL Profile](https://www.rfc-editor.org/rfc/rfc5280)
- [RFC 9525 — Service Identity in TLS](https://www.rfc-editor.org/rfc/rfc9525)
- [RFC 9325 — Recommendations for Secure Use of TLS and DTLS](https://www.rfc-editor.org/rfc/rfc9325)
