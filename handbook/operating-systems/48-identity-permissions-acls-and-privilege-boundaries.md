# Chapter 48 — Identity, Permissions, ACLs, and Privilege Boundaries

Access belongs to an operation performed by a process, not to a username floating beside a file. The operating system evaluates the process's effective security context, the route through the namespace, the target object's policy, and additional platform controls.

The central idea is:

> Diagnose authorization from the requesting process outward; change the narrowest policy layer that is actually denying the required operation.

## 1. Authentication and authorization remain separate

Authentication establishes an identity. Authorization decides whether that identity, with its current groups, privileges, capabilities, session, and policy context, may perform a specific operation on an object.

An access request can be modeled as:

```text
process or thread security context
→ namespace traversal and mount/share boundary
→ object owner, mode, and ACL
→ privilege or capability override rules
→ mandatory policy or sandbox
→ application-level authorization
```

The error “permission denied” exposes the outcome, not the failing layer. Making the target world-writable or running as administrator tests several hypotheses at once and creates unnecessary authority.

## 2. Unix process credentials drive checks

Unix-like processes have user and group identifiers, including real and effective forms, plus supplementary groups. File access checks ordinarily use effective credentials under the relevant system-call rules. Linux adds capabilities that divide some traditional root authority, while namespaces and mandatory-access-control systems can impose further policy.

Inspect the current shell context:

```bash
id
umask
```

Inspect every path component on Linux with `namei -l /full/path` where available; on macOS, inspect each parent with `ls -ldeO@`. The process needs directory search permission along the route, not just permissions on the final file.

Changing effective identity in set-user-ID programs, service managers, containers, or privileged helpers creates additional boundaries. The identity shown by an interactive `whoami` may not match the failing service process.

## 3. Mode bits are an ordered classification

Traditional Unix mode bits classify access for the object's owner, owning group, and everyone else. The kernel selects the applicable class; permissions are not simply accumulated across all three. On directories:

- read permits listing names;
- write permits changing directory entries, subject to other rules;
- execute permits searching or traversing by name.

Directory write without search is unusual and limited; file write permission is not required to unlink a name when the parent directory policy permits it. Sticky directories add ownership restrictions to entry removal. Set-user-ID, set-group-ID, and sticky bits have context-dependent semantics.

The creation mode is filtered by a process's `umask`, but default ACLs and application calls can also influence results. A umask is not retroactive and is not a complete authorization policy.

## 4. POSIX-style ACLs add named entries

Filesystem ACLs can grant policy to named users and groups beyond the three mode classes. On Linux, the ACL mask limits effective rights for named users, named groups, and the owning group class. `ls -l` may show a `+`, but use ACL-aware tools for the real entries:

```bash
getfacl -- path       # Linux, when installed and supported
ls -le path           # macOS ACL view
```

Default or inherited ACL behavior differs by platform and filesystem. Copying between filesystems can drop, translate, or recalculate entries. An ACL display is also not the whole decision if a mandatory policy, read-only mount, immutable flag, or application sandbox denies the operation.

Avoid adding explicit deny entries unless policy requires them and their precedence is understood. Complex ACLs accumulate exceptions that are difficult to audit.

## 5. Windows uses tokens and security descriptors

A Windows process or thread operates with an access token containing a user SID, group SIDs and attributes, privileges, integrity information, and other context. Securable objects have security descriptors. A discretionary access control list (DACL) contains access-control entries (ACEs) that allow or deny specific rights to trustees.

For a requested access mask, Windows evaluates applicable ACEs against token SIDs according to canonical ordering and access-check rules. A **null DACL** grants broad access, while an **empty DACL** grants none; they are not the same. Object ownership grants authority to manage policy under defined rules but does not mean every access request automatically succeeds.

Read-only PowerShell inspection:

```powershell
whoami /all
Get-Acl -LiteralPath path | Format-List Owner, AccessToString, AreAccessRulesProtected
```

The shell pipeline is PowerShell syntax. Redact output before sharing because tokens and ACLs reveal account and group information.

## 6. Inheritance is policy generation

Windows child objects can inherit ACEs from containers, with flags controlling propagation and object type. Breaking inheritance can copy or remove inherited entries depending on the tool and chosen action. Moving an object within or across volumes can produce different inheritance outcomes.

Unix default ACLs can generate access ACLs for newly created children, while ordinary mode and umask still participate. Existing descendants are not necessarily rewritten when a parent default changes.

Treat inheritance as a rule for producing child policy, not a magical live pointer to the parent. Before changing a parent recursively, sample representative descendants, identify explicit exceptions, and define rollback.

## 7. Elevation changes authority, not correctness

`sudo`, macOS authorization, Windows User Account Control, administrator tokens, Linux capabilities, and service identities cross privilege boundaries differently. Elevation may bypass one denial while leaving another—such as read-only storage, sandbox policy, encryption, or application authorization—intact.

Run the narrowest approved command with elevated authority and preserve a clear audit trail. Do not run an entire editor, shell, build, or package ecosystem as administrator when one controlled operation requires privilege. Elevated tools can create root- or administrator-owned artifacts that later break normal workflows.

Privileges should be separated from identity when the platform permits it. A service that binds one protected resource does not necessarily need unrestricted filesystem and process authority.

## 8. Remote storage evaluates more than local policy

NFS, SMB, cloud-synchronized folders, and enterprise shares add server-side identity mapping, share permissions, export policy, authentication tickets, caching, and network availability. Local ownership display may be translated or incomplete.

For Windows SMB, effective access can be the intersection of share and NTFS policy. For Unix network filesystems, numeric identity mapping and server export rules matter. A local administrator may not possess authority on the remote server.

Record client identity, server identity, protocol, share/export, target path, and server-side policy. Do not “fix” a remote denial by recursively opening local permissions.

## 9. A disciplined access investigation

1. State the exact operation: list, traverse, read, create, replace, delete, execute, or change policy.
2. Identify the actual process or thread token and service/container context.
3. Resolve the path and inspect every namespace boundary.
4. Inspect object ownership, modes, ACLs, attributes, and mount/share policy.
5. Check mandatory policy, sandbox, and application authorization evidence.
6. Reproduce with the same identity using a harmless target if possible.
7. Grant only the missing right at the layer that owns the decision.
8. Verify required access and confirm unintended identities did not gain it.

Effective-access tools can help but may not model dynamic application or remote policy completely. A controlled test of the exact operation remains important.

## Common Misconceptions

- “Owner can always do anything.” Additional policy and requested rights still matter.
- “Mode `777` fixes permissions.” It broadly changes one layer and ignores the cause.
- “Administrator is the same as root.” Their token, privilege, and policy models differ.
- “Parent ACL changes automatically rewrite all children.” Inheritance usually governs creation and propagation rules, not universal live linkage.

## Core Computer Science Concept

Authorization is **predicate evaluation over identity, object, operation, and context**. Least privilege minimizes the set of predicates that evaluate true, reducing both accidental damage and attacker capability.

## Engineering Connections

- Service identities make runtime ownership and compromise scope explicit.
- CI agents should receive repository and deployment rights separately.
- Container root can still be constrained by host namespaces and capabilities.
- Cloud IAM continues the same identity-operation-resource-context model at another layer.

## From the Field

A Windows service cannot write a report, so it is changed to run as LocalSystem. The write succeeds, but the service now has broad machine authority and still cannot reach a remote share using the expected user identity. The correct fix uses a dedicated service account, explicit local and remote grants, and documented credential handling.

## Engineering Review

### What problem does this solve?

It explains how operating systems decide whether a process may perform a specific operation on a filesystem object.

### Why was it designed this way?

Layered identity and policy support delegation, multiuser isolation, inheritance, auditing, and constrained privilege.

### When should I use it?

Use the model for access denials, service identities, shared directories, deployment permissions, and least-privilege design.

### When should I avoid it?

Avoid broad recursive grants, routine elevation, and policy changes made without reproducing the actual identity and operation.

### How does this make me a better engineer?

It turns permissions from memorized modes into a traceable authorization decision.

### How does this reduce waste?

It fixes the responsible policy once and avoids repeated denials or overbroad access that creates later cleanup and risk.

## Handbook Principle #48

> Grant the required operation to the correct runtime identity at the narrowest policy boundary.

## Practical Observation

Choose a disposable directory you own. Record your effective identity, parent traversal permissions, object owner, mode or DACL, and inheritance state. Explain which rule permits you to create and delete a test file. Do not elevate, alter system ACLs, or test another user's private data.

## Looking Ahead

Chapter 49 integrates the storage, process, memory, service, and authorization layers into one read-mostly operating-system investigation.

## References

- [Linux `credentials(7)`](https://man7.org/linux/man-pages/man7/credentials.7.html)
- [Linux `acl(5)`](https://man7.org/linux/man-pages/man5/acl.5.html)
- [Microsoft: How DACLs Control Access](https://learn.microsoft.com/en-us/windows/win32/secauthz/how-dacls-control-access-to-an-object)
- [Microsoft: Access Tokens](https://learn.microsoft.com/en-us/windows/win32/secauthz/access-tokens)
- [Apple: System Integrity Protection](https://support.apple.com/guide/security/system-integrity-protection-secb7ea06b49/web)
