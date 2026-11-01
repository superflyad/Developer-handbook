# Chapter 92 — IAM: Principals, Policies, Roles, and Temporary Credentials

An application receives `AccessDenied` while reading one object. Adding `s3:*` appears to fix it. That change also lets the application delete unrelated buckets, alter access controls, and retrieve data it never needed. The symptom disappeared because the authority boundary disappeared with it.

The central idea is:

> Identify the principal and exact request first, then grant the smallest authority for the shortest useful session through a traceable policy path.

## 1. Start with a request, not a job title

AWS authorization evaluates a concrete request. Useful questions are:

- Which principal is making the request?
- Which API action is requested?
- Which resource or resources does the action address?
- In which account and Region?
- Which request context is present?
- Which identity, resource, session, boundary, and organization policies apply?
- Is there an explicit deny?

“The application needs S3” is not an access requirement. A requirement looks like:

```text
principal: assumed role session for invoice-worker
action: s3:GetObject
resource: arn:aws:s3:::example-invoices/ready/*
context: TLS request, approved organization, expected object prefix
duration: one-hour renewable workload session
evidence: CloudTrail data event and application request identifier
```

IAM policies implement authorization. Authentication proves which credentials signed the request; it does not imply that the request is allowed.

## 2. A principal is the authenticated actor

AWS principals include:

- an AWS account or its root user;
- an IAM user;
- an IAM role;
- an assumed-role session;
- a federated user session;
- an AWS service principal;
- a supported external identity provider.

An IAM group is not a principal. It is a way to attach identity policies to multiple IAM users. A workload or person authenticates as an identity or session, not as a group.

Distinguish durable configuration from the runtime actor. An IAM role is a durable identity definition; after assumption, the caller uses a temporary role session principal with an STS ARN and session context.

## 3. Prefer federation for people

Workforce users should normally authenticate through an identity provider and receive temporary access to roles, commonly through IAM Identity Center. This provides a place to manage workforce lifecycle and authentication controls without creating a long-lived IAM password and access key for each person in every account.

The AWS account still owns authorization:

- which role or permission set can be used;
- what that role permits;
- session duration;
- required attributes, MFA, network, or other conditions;
- which account and resources are reachable;
- audit and review.

Federation does not make broad administrator roles least privilege. It improves credential lifecycle and centralizes identity, while authorization still needs design.

## 4. Reserve IAM users for exceptional cases

An IAM user is an account-scoped identity that can have long-term credentials. AWS recommends using federation and roles where possible, and using IAM users only for cases not supported by federation or temporary workload identity.

If an IAM user is unavoidable:

- document why a role cannot work;
- create one identity per system or exceptional use, not a shared key;
- grant narrow permissions;
- store the credential in an approved secret system;
- never embed it in source, images, AMIs, tickets, or documentation;
- monitor use and last-accessed evidence;
- rotate when required by risk or lifecycle events;
- define migration and deletion criteria.

Rotation reduces the lifetime of a copied key only after the old key is deactivated. It does not make a broadly distributed static credential safe.

## 5. Roles separate identity definition from sessions

An IAM role has no standard long-term password or access key. It has two distinct policy concerns:

1. **Trust:** Who may assume the role, and under what conditions?
2. **Permissions:** What may a resulting role session do?

Confusing these questions creates dangerous policies. A role permission policy that allows `s3:GetObject` does not identify who can assume the role. A trust policy that names a principal does not grant the role permission to read an object.

When a principal assumes a role, AWS Security Token Service returns temporary credentials for a role session. The caller then signs requests using that session's access key, secret key, and session token until they expire.

## 6. Trust is not permission to use every resource

A role trust policy is a resource-based policy attached to the role. It identifies trusted principals and conditions for role assumption.

For cross-account role assumption, both sides commonly participate:

- the target role trust policy trusts the source principal or account;
- the source principal has permission to call `sts:AssumeRole` where required;
- organization, boundary, and session controls permit the call;
- trust-policy conditions are satisfied.

After assumption, the resulting session uses the role's permissions, not a union of the caller's old permissions and the role's permissions.

Trust an exact principal or a deliberately constrained account boundary. Avoid an unconstrained wildcard principal. When trusting an account, remember that the account can potentially delegate its side of access to its own identities unless your conditions narrow it.

## 7. Use temporary credentials for workloads

AWS compute services can deliver and refresh role credentials for workloads, including common EC2, ECS, EKS, and Lambda patterns. AWS SDK credential-provider chains can retrieve them without application code storing access keys.

For workloads outside AWS, supported approaches include:

- OpenID Connect and `AssumeRoleWithWebIdentity`;
- SAML federation;
- IAM Roles Anywhere with an X.509 trust model;
- service-specific hybrid identity integrations.

Choose the method whose issuer, audience, subject, certificate, and revocation model you can validate. A temporary credential obtained from an untrustworthy long-lived bootstrap secret merely moves the problem.

## 8. Expiration limits exposure, not authority

Temporary credentials contain:

- an access key ID;
- a secret access key;
- a session token;
- an expiration time.

They can make authorized AWS requests until expiration or another control prevents use. They are bearer-like secrets: possession enables signing within their authority.

Temporary credentials help because:

- they expire automatically;
- platforms can deliver and rotate them;
- sessions can carry identity context and tags;
- each assumption can be logged;
- long-lived keys need not be distributed.

They do not help if an application logs them, exposes its credential endpoint, grants them unnecessary power, or allows an attacker to refresh sessions indefinitely.

## 9. Use the provider chain instead of copying keys

AWS SDKs and tools use standardized credential providers. A workload should normally let the SDK obtain credentials from the platform-specific provider rather than reading a hard-coded key.

Development and deployment rules should reject:

- access key literals in source and configuration;
- credentials copied into container images;
- shared credentials mounted into every workload;
- logs containing authorization headers or session tokens;
- an EC2 instance role shared by unrelated applications when task- or pod-level identity is available;
- CI secrets containing permanent AWS access keys when OIDC federation is supported.

Environment variables are a supported provider in many tools, but they are still a secret-delivery mechanism. They can leak through debugging, subprocesses, crash reports, or build logs. Prefer an identity provider that issues a short session directly to the workload.

## 10. Policy statements describe decisions

An IAM JSON policy contains one or more statements. Common elements include:

- `Version`: policy language version;
- `Statement`: one statement or a list;
- `Sid`: optional statement identifier;
- `Effect`: `Allow` or `Deny`;
- `Action` or `NotAction`: API operations;
- `Resource` or `NotResource`: affected resources;
- `Principal` or `NotPrincipal`: actors in resource-based policies;
- `Condition`: constraints evaluated from request context.

Example identity policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ReadReadyInvoices",
      "Effect": "Allow",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::example-invoices/ready/*"
    }
  ]
}
```

The principal is implicit because this policy is attached to an identity. A resource-based policy instead uses `Principal` to identify who receives its allow or deny.

## 11. Actions are API operations

IAM action names usually combine a service prefix and operation, such as:

```text
s3:GetObject
dynamodb:UpdateItem
sqs:ReceiveMessage
ec2:RunInstances
iam:PassRole
```

Console workflows often call multiple APIs. Granting the one write action visible in a user story might not make the console usable because it also lists or describes resources. Determine required actions from service authorization documentation and observed calls, then separate read, write, permission-management, and tagging authority.

Wildcards simplify policies but expand future authority. A new service action can begin matching an existing wildcard without a policy edit. Prefer exact actions or reviewed, bounded action families.

## 12. Resources require service-specific precision

Amazon Resource Names identify many resources:

```text
arn:partition:service:region:account-id:resource
```

The exact format varies. S3 bucket and object ARNs differ; some actions do not support resource-level permissions and require `Resource: "*"`; some actions need more than one resource type.

Do not replace a correct `*` required by a service with a fake ARN. Narrow the statement through supported actions and conditions, and isolate it from statements that can use precise resources.

Review both the container and contained objects where the service distinguishes them. Permission to list a bucket is not permission to read its objects, and the reverse is also true.

## 13. Conditions constrain request context

Conditions can evaluate supported global or service-specific keys, including aspects of:

- principal identity or organization;
- source account or resource;
- requested and resource tags;
- network path or source address;
- transport security;
- authentication age or MFA context;
- Region;
- token audience, issuer, or subject;
- time;
- encryption or service-specific request parameters.

Condition operators have types and missing-key behavior. Set operators, `IfExists`, negated operators, and multiple values can change results in non-obvious ways. Use the documented key for the specific action and policy type, then test both matching and non-matching requests.

Network conditions are not identity. An approved source address may be shared, translated, or compromised. Use it as one bound, not the sole proof of actor intent.

## 14. Identity policies attach authority to identities

Identity-based policies attach to IAM users, groups, or roles. They state what the attached identity may do. They can be:

- AWS managed;
- customer managed and reusable;
- inline and embedded in one identity.

AWS managed policies are convenient starting points, but they can be broader than a workload needs and can evolve. Move production roles toward customer-managed, reviewed least-privilege policies.

An identity policy does not include `Principal`; attachment determines the principal.

## 15. Resource policies attach decisions to resources

Supported services can attach policies to resources such as S3 buckets, SQS queues, KMS keys, or IAM role trust. A resource policy identifies principals and can authorize cross-account access or impose an explicit deny.

Resource-policy behavior interacts with principal type, account relationship, boundaries, and session policies. In some same-account cases, a resource policy that grants directly to a user or session principal is not limited by an implicit deny in an identity policy or boundary. Explicit denies still matter.

This is why the shorthand “identity allow intersect resource allow” is not universally correct. Trace the exact service, principal ARN form, account relationship, and policy type using AWS's evaluation documentation.

## 16. Permissions boundaries delegate safely

A permissions boundary is a managed policy attached to an IAM user or role that limits the maximum permissions its identity policies can grant. It does not grant permissions.

Boundaries are useful when a platform team lets developers create roles but requires every created role to stay inside an approved ceiling. The delegating policy must also prevent users from removing the boundary, replacing it with a broader one, or passing an unbounded role.

For the common identity-policy path:

```text
effective identity permission
    = identity policy allow
    intersected with permissions boundary allow
```

An explicit deny in either policy still denies. Resource-based policy exceptions require separate analysis.

## 17. Session policies narrow an issued session

Some STS operations accept inline or managed session policies. A session policy limits the permissions available to that session; it cannot grant more than the role or federated identity otherwise permits.

Session policies are useful when one brokered role supports multiple narrowly scoped jobs. The broker can issue a session restricted to one tenant, repository, or deployment target.

The broker becomes security-sensitive. It must validate the requested scope, prevent a caller from choosing arbitrary session policies or tags, preserve attribution, and avoid confused-deputy behavior.

## 18. Organization policies remain outer guardrails

For principals in member accounts, service control policies can limit the maximum permissions available. Chapter 91 established that SCPs do not grant permissions and do not restrict management-account principals.

Authorization can therefore fail even when the role policy appears to allow the action. Trace inherited SCPs from the organization root through parent OUs to the account, along with applicable resource control policies and service-specific controls.

Do not “fix” an SCP denial by moving the account to an ungoverned OU. Reconcile the workload requirement with the organization invariant.

## 19. Explicit deny has precedence

IAM begins from implicit denial. An applicable allow is required, and an applicable explicit deny overrides an allow.

Explicit denies are valuable for invariants but dangerous when their scope or condition logic is misunderstood. Test:

- requests that must be denied;
- requests that must remain allowed;
- automation and service principals;
- break-glass behavior;
- new resource and Region cases;
- rollback.

When diagnosing denial, find the policy type named by enhanced error messages when available, but remember that not every cross-account or service path provides the same detail.

## 20. Cross-account access is two-sided

Cross-account access generally needs authority from both the principal's side and the resource-owning side. Common patterns are:

- assume a role in the target account, then use that role's permissions;
- grant a source principal access through a supported resource policy.

Record:

- source principal and account;
- target account and resource;
- trust or resource policy;
- source-side permission;
- organization constraints on both sides;
- session name, source identity, tags, and duration;
- audit ownership and revocation path.

An account ID in a trust policy delegates trust to an administrative boundary. Narrow it further when only particular roles or attributes should qualify.

## 21. Defend against confused deputies

A confused deputy is a more-privileged intermediary tricked into using its authority for the wrong caller or resource.

For a third party that assumes roles for multiple customers, require a unique external ID in the trust policy and the `AssumeRole` request. The third party should generate and consistently supply it. AWS does not treat an external ID as a secret; it distinguishes the customer context.

For AWS service principals acting on behalf of resources, use documented source-account and source-resource conditions where supported. The correct condition keys and ARN shape are service-specific.

Trust alone does not establish tenant isolation. The deputy must bind the authenticated caller to the exact customer scope used in its AWS request.

## 22. Treat `iam:PassRole` as delegation

Many AWS APIs create a service resource and accept a role that the service will use. The caller needs `iam:PassRole` for that role in addition to the service API permission.

Broad `iam:PassRole` can let a principal attach a highly privileged role to compute it controls, turning indirect service creation into privilege escalation. Restrict:

- which role ARNs may be passed;
- which services may receive them through supported conditions;
- who can modify those roles and trust policies;
- which resource-creation actions the caller has.

Review the combined path, not `PassRole` in isolation.

## 23. Least privilege is an iterative control loop

Least privilege means enough authority for required work under expected conditions—no more, and no longer than necessary.

A practical loop is:

1. define exact workflows and failure recovery;
2. begin with a bounded provisional policy in non-production;
3. observe CloudTrail and service behavior;
4. validate the policy and external access;
5. split unrelated responsibilities;
6. narrow actions, resources, and conditions;
7. test allowed and denied paths;
8. deploy through review;
9. monitor unused access and new access;
10. remove authority when the workflow changes.

Access Analyzer can validate policy grammar and best practices, identify external access, and generate a policy template from observed CloudTrail activity. Observed activity is not a complete specification: rare recovery actions may be absent, and past use may include unnecessary access.

## 24. Diagnose authorization without broadening blindly

For an access-denied request, collect:

- caller identity from a trusted `GetCallerIdentity` result or runtime context;
- role session and source identity;
- action and exact resource ARN;
- account, Region, endpoint, and request parameters;
- relevant identity and resource policies;
- trust policy for role assumption;
- permissions boundary and session policy;
- inherited organization policies;
- endpoint, key, and service-specific policies;
- condition context;
- CloudTrail event when logged;
- recent policy or tag changes.

Then reproduce the smallest safe request. Do not add administrator access as a diagnostic probe. A successful overly broad request proves only that some missing authority was included in the expansion.

## 25. Audit identity as a lifecycle

Identity controls need continuing evidence:

- who or what owns the identity;
- why it exists;
- credential and federation source;
- trust-policy scope;
- attached and inline policies;
- boundary and organization ceilings;
- last assumption and last accessed services;
- external-access findings;
- active sessions and expected duration;
- rotation, revocation, and incident procedure;
- expiration or review date.

Delete abandoned roles and policies after proving dependencies are gone. Recreating a role or user with the same name does not necessarily restore resource-policy relationships because AWS can store internal principal identifiers.

## 26. Practical model: trace a constrained role request

This standard-library example models one deliberately narrow case: an assumed role in the resource account, using simple identity, boundary, session, SCP, and resource-deny statements. It supports only exact or suffix-wildcard action and resource patterns and `StringEquals` context.

It is a teaching aid, not an IAM simulator. It intentionally rejects policy features it cannot model and cannot represent resource-policy grants, cross-account evaluation, `NotAction`, multivalued conditions, service-specific authorization, or every explicit-deny source.

Save as `test_iam_trace.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatchcase
import unittest


@dataclass(frozen=True)
class Statement:
    effect: str
    actions: tuple[str, ...]
    resources: tuple[str, ...]
    string_equals: tuple[tuple[str, str], ...] = ()

    def matches(self, action: str, resource: str, context: dict[str, str]) -> bool:
        if self.effect not in {"Allow", "Deny"}:
            raise ValueError("effect must be Allow or Deny")
        if not any(fnmatchcase(action, pattern) for pattern in self.actions):
            return False
        if not any(fnmatchcase(resource, pattern) for pattern in self.resources):
            return False
        return all(context.get(key) == value for key, value in self.string_equals)


@dataclass(frozen=True)
class PolicyLayer:
    name: str
    statements: tuple[Statement, ...]
    required_allow: bool

    def decision(
        self, action: str, resource: str, context: dict[str, str]
    ) -> str:
        matching = [
            statement
            for statement in self.statements
            if statement.matches(action, resource, context)
        ]
        if any(statement.effect == "Deny" for statement in matching):
            return "EXPLICIT_DENY"
        if any(statement.effect == "Allow" for statement in matching):
            return "ALLOW"
        return "NO_MATCH"


@dataclass(frozen=True)
class CredentialPlan:
    source: str
    maximum_session_seconds: int
    embedded_access_key: bool

    def validate(self) -> None:
        allowed_sources = {
            "compute-role",
            "federated-human",
            "oidc-workload",
            "roles-anywhere",
        }
        if self.source not in allowed_sources:
            raise ValueError("credential source is not an approved temporary provider")
        if not 900 <= self.maximum_session_seconds <= 43200:
            raise ValueError("session duration is outside this plan's bounds")
        if self.embedded_access_key:
            raise ValueError("workload embeds a long-lived access key")


def trace_request(
    action: str,
    resource: str,
    context: dict[str, str],
    layers: tuple[PolicyLayer, ...],
) -> tuple[str, tuple[str, ...]]:
    decisions = tuple(
        f"{layer.name}={layer.decision(action, resource, context)}"
        for layer in layers
    )
    if any(item.endswith("=EXPLICIT_DENY") for item in decisions):
        return "DENY", decisions
    for layer, item in zip(layers, decisions, strict=True):
        if layer.required_allow and not item.endswith("=ALLOW"):
            return "DENY", decisions
    return "ALLOW", decisions


IDENTITY = PolicyLayer(
    name="identity",
    required_allow=True,
    statements=(
        Statement(
            effect="Allow",
            actions=("s3:GetObject",),
            resources=("arn:aws:s3:::example-invoices/ready/*",),
            string_equals=(("aws:PrincipalTag/workload", "invoice-worker"),),
        ),
    ),
)
BOUNDARY = PolicyLayer(
    name="boundary",
    required_allow=True,
    statements=(
        Statement("Allow", ("s3:Get*",), ("arn:aws:s3:::example-invoices/*",)),
    ),
)
SESSION = PolicyLayer(
    name="session",
    required_allow=True,
    statements=(
        Statement("Allow", ("s3:GetObject",), ("arn:aws:s3:::example-invoices/ready/*",)),
    ),
)
SCP = PolicyLayer(
    name="scp",
    required_allow=True,
    statements=(Statement("Allow", ("s3:*",), ("*",)),),
)
RESOURCE_GUARD = PolicyLayer(
    name="resource-explicit-deny",
    required_allow=False,
    statements=(
        Statement(
            "Deny",
            ("s3:*",),
            ("arn:aws:s3:::example-invoices/*",),
            (("aws:SecureTransport", "false"),),
        ),
    ),
)
LAYERS = (IDENTITY, BOUNDARY, SESSION, SCP, RESOURCE_GUARD)


class IamTraceTests(unittest.TestCase):
    def test_narrow_temporary_role_request_is_allowed(self) -> None:
        CredentialPlan("compute-role", 3600, False).validate()
        decision, trace = trace_request(
            action="s3:GetObject",
            resource="arn:aws:s3:::example-invoices/ready/invoice-42.json",
            context={
                "aws:PrincipalTag/workload": "invoice-worker",
                "aws:SecureTransport": "true",
            },
            layers=LAYERS,
        )
        self.assertEqual("ALLOW", decision, trace)

    def test_explicit_resource_deny_wins(self) -> None:
        decision, trace = trace_request(
            action="s3:GetObject",
            resource="arn:aws:s3:::example-invoices/ready/invoice-42.json",
            context={
                "aws:PrincipalTag/workload": "invoice-worker",
                "aws:SecureTransport": "false",
            },
            layers=LAYERS,
        )
        self.assertEqual("DENY", decision, trace)

    def test_boundary_without_matching_allow_denies(self) -> None:
        narrow_boundary = PolicyLayer(
            name="boundary",
            required_allow=True,
            statements=(
                Statement("Allow", ("s3:ListBucket",), ("*",)),
            ),
        )
        decision, trace = trace_request(
            action="s3:GetObject",
            resource="arn:aws:s3:::example-invoices/ready/invoice-42.json",
            context={"aws:PrincipalTag/workload": "invoice-worker"},
            layers=(IDENTITY, narrow_boundary, SESSION, SCP, RESOURCE_GUARD),
        )
        self.assertEqual("DENY", decision, trace)

    def test_embedded_static_key_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "long-lived"):
            CredentialPlan("compute-role", 3600, True).validate()


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

Run it:

```bash
python -m unittest -v test_iam_trace.py
```

Print the returned trace while experimenting. Then compare every assumption with AWS policy evaluation documentation before using a real policy. A production test should validate policies with IAM Access Analyzer and exercise allowed and denied requests in an isolated account using temporary credentials.

## 27. Review an access path

Require this evidence for a workload or operator path:

```text
human or workload identity owner:
authentication and credential provider:
principal and session ARN shape:
session duration, refresh, revocation, and failure behavior:
role trust policy and assumption conditions:
required actions and service authorization references:
exact resources and unavoidable wildcards:
identity and resource policies:
permissions boundary and session policy:
organization and endpoint guardrails:
context keys and missing-key behavior:
cross-account sides and confused-deputy controls:
PassRole paths and downstream service roles:
allowed-path and denied-path tests:
CloudTrail and application attribution:
last-accessed, external-access, and policy-validation evidence:
review, expiration, and deletion owner:
```

The access path is incomplete when a reviewer cannot explain both why the required call succeeds and why a neighboring prohibited call fails.

## Common Misconceptions

- “Authentication grants access.” Authentication establishes a principal; policies decide authorization.
- “A role is a group.” A role is an assumable identity that produces sessions; a group only aggregates IAM-user permissions.
- “The trust policy grants S3 access.” It controls role assumption, not the role's service permissions.
- “Temporary credentials are low privilege.” Their lifetime is bounded; their permissions can still be administrative.
- “A permissions boundary grants its listed actions.” It is a ceiling and grants nothing by itself.
- “An SCP allow makes an API available.” It only leaves the action within the maximum permissions a member-account principal might receive.
- “Resource and identity policies always intersect.” Resource-policy grants have principal- and account-specific evaluation rules.
- “An external ID is a password.” It is non-secret customer context for confused-deputy defense.
- “PassRole only passes a name.” It delegates a role to a service and can create an escalation path.
- “Unused in CloudTrail means unnecessary.” Rare recovery paths may not have occurred during the observation window.

## Core Computer Science Concept

IAM applies **capability restriction through policy composition**. A signed request presents an authenticated actor and operation. Multiple policy layers contribute grants, ceilings, and vetoes over that operation. Temporary sessions add time-bounded derived authority: a durable role definition produces a short-lived principal whose effective capability is no broader than the policies and context permit.

## Engineering Connections

- IAM separates identity, authentication, and authorization introduced in Chapter 7.
- Role sessions resemble short-lived process credentials rather than permanent users.
- Policy conditions are predicates over request context, and explicit deny is a veto in composed logic.
- Trust policies and resource policies cross the account boundaries designed in Chapter 91.
- Credential-provider chains apply Chapter 10's rule that environment and configuration sources have precedence and leakage risks.
- Least-privilege refinement uses Part VI's observe, test, narrow, deploy, and monitor loop.
- Session expiration is a lease; refresh and revocation behavior are part of distributed-system correctness.

## From the Field

A CI pipeline stores an IAM user's access key as a repository secret. The user can deploy to every environment and pass any role. A pull-request workflow is compromised, the key is exfiltrated, and the attacker creates compute with an administrator service role. Rotating the repository secret later does not undo the created access. OIDC federation with repository and branch conditions, a short deployment session, narrow target resources, restricted `PassRole`, environment approval, and audit attribution would reduce both reachable authority and exposure time.

## Engineering Review

### What problem does this solve?

It provides a repeatable way to identify an AWS principal, trace an authorization decision across policy types, and give people and workloads renewable temporary access without embedded long-lived keys.

### Why was it designed this way?

AWS must authorize many principals across accounts and services while supporting delegation. Separate trust, permission, resource, boundary, session, and organization policies let owners compose authority at different boundaries.

### When should I use it?

Use this model for every AWS API access path, policy review, cross-account integration, workload identity, CI deployment, access-denied investigation, and privilege-removal decision.

### When should I avoid it?

Avoid relying on the chapter's constrained local evaluator for production decisions. Use it to learn the layers, then validate exact service behavior with authoritative documentation, Access Analyzer, and isolated allowed and denied tests.

### How does this make me a better engineer?

It replaces trial-and-error permission broadening with explicit reasoning about actor, action, resource, context, policy provenance, credential lifetime, and evidence.

### How does this reduce waste?

It reduces leaked-key response, duplicated IAM users, unexplained access failures, oversized policies, manual rotation, privilege accumulation, and incidents caused by ambiguous delegation.

## Handbook Principle #92

> Grant a named principal the smallest tested request path through a short-lived session—never solve uncertainty by erasing the boundary.

## Practical Observation

Run the IAM trace tests and inspect each layer's result. Change the workload tag, object prefix, transport context, session allow, and SCP allow one at a time. For each denial, name the missing or vetoing policy layer before changing it. Then design the same path for a real workload on paper, including how credentials arrive without source code, how they refresh, and which call proves the neighboring resource remains inaccessible.

## Looking Ahead

Identity determines who may request network changes, but it does not determine where packets can travel. Chapter 93 builds VPCs, IPv4 and IPv6 address plans, subnets, route tables, gateways, and multi-AZ network structure from explicit traffic and growth requirements.

## References

- [AWS IAM — Security best practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [AWS IAM — IAM roles](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles.html)
- [AWS IAM — Temporary security credentials](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_temp.html)
- [AWS IAM — Policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)
- [AWS IAM — How enforcement evaluates allow or deny](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic_policy-eval-denyallow.html)
- [AWS IAM — JSON policy element reference](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements.html)
- [AWS IAM — Permissions boundaries](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_boundaries.html)
- [AWS IAM — Access to AWS accounts owned by third parties](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_common-scenarios_third-party.html)
- [AWS IAM — Validate policies with IAM Access Analyzer](https://docs.aws.amazon.com/IAM/latest/UserGuide/access-analyzer-policy-validation.html)
- [AWS IAM — Troubleshoot access denied errors](https://docs.aws.amazon.com/IAM/latest/UserGuide/troubleshoot_access-denied.html)
