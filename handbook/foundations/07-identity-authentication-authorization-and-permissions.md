# Lesson 7 — Identity, Authentication, Authorization, and Permissions

The previous chapters explained how Unix runs software. This chapter explains how Unix decides whether running software is allowed to act.

The central idea is:

> Every secure system must know who is acting, how that identity was verified, what authority it has, and which operations are permitted.

Unix expresses this through users, groups, process credentials, ownership, permissions, and kernel enforcement. The same model appears later in AWS IAM, databases, containers, Kubernetes, APIs, OAuth, and enterprise identity systems.

## 1. Why identity exists

Imagine an operating system with no identity model. Every process could read every file, modify every configuration, kill every process, and access every device.

That would be convenient until the first bug, typo, compromised application, or malicious program.

Identity gives the kernel a basis for making security decisions. When a process requests access to a file, device, socket, or other protected resource, the kernel does not ask whether the application has a friendly name. It evaluates the credentials attached to the process.

Conceptually:

```text
process request
      ↓
process identity and credentials
      ↓
kernel authorization check
      ↓
allow or deny
```

## 2. Identity

Identity answers:

> Who or what is acting?

An identity may represent a human, but it does not have to.

Examples include:

- a local developer account,
- `root`,
- a web-server account such as `nginx`,
- a database account such as `postgres`,
- a CI runner,
- a container process,
- an AWS IAM role,
- a Kubernetes service account.

In Unix, users are represented internally by numeric user IDs, or **UIDs**. Names such as `michael` are human-readable mappings to those identifiers.

The kernel reasons primarily about identifiers and credentials, not display names.

## 3. Processes carry identity

A user account does not directly access a file. A process acting under that user's credentials requests access.

Recall that a process has:

- a PID,
- memory,
- environment variables,
- a working directory,
- open resources,
- a lifecycle.

It also has security credentials, including user and group identities.

This means the more precise question is not:

> Can Michael read this file?

It is:

> Can this process, running with Michael's credentials, read this file?

That distinction matters for shells, services, containers, scheduled jobs, CI systems, and remote sessions.

## 4. Authentication

Authentication answers:

> Can you prove the identity you claim?

Identity is a claim. Authentication verifies the claim.

Examples include:

- a password,
- Touch ID or another biometric mechanism,
- an SSH private key,
- a hardware security key,
- an OAuth login,
- temporary cloud credentials,
- a signed token.

Authentication does not decide what an identity may do. It only establishes confidence that the actor is who or what it claims to be.

A valid SSH key may prove that a connection belongs to a particular account. File permissions still determine what the resulting shell process may access.

## 5. Authorization

Authorization answers:

> What is this authenticated identity allowed to do?

Examples include:

- read a source file,
- modify a configuration,
- bind to a network port,
- start a service,
- retrieve an S3 object,
- execute a database query,
- deploy to production.

Authentication and authorization must remain conceptually separate.

A user may authenticate successfully and still be denied an operation. That is normal and desirable security behavior.

## 6. Permissions

Permissions are concrete rules used to implement authorization decisions.

Traditional Unix file permissions revolve around three operations:

- **read** — inspect file contents or list a directory,
- **write** — modify a file or directory entry,
- **execute** — run a file as a program or traverse a directory.

Other systems use different permission vocabularies:

```text
Unix:      read, write, execute
SQL:       SELECT, INSERT, UPDATE, DELETE
AWS IAM:   s3:GetObject, ec2:StartInstances
GitHub:    read, triage, write, maintain, admin
```

The vocabulary changes. The model does not.

## 7. Users are not necessarily people

A Unix user is an operating-system identity.

Service accounts such as these are not humans:

```text
nginx
postgres
mysql
www-data
```

They exist so services can run with limited authority.

A web server may need to:

- read website files,
- write logs,
- accept network traffic.

It does not need permission to read personal SSH keys or rewrite the operating system.

Giving each service a separate identity limits the damage caused by bugs or compromise.

## 8. Groups

Groups solve authorization at scale.

Without groups, permissions would need to be assigned separately to every user. A group creates a reusable collection of identities.

```text
developers
├── alice
├── michael
└── sarah
```

A resource can grant access to the `developers` group once instead of maintaining several individual rules.

The same pattern appears in:

- Unix groups,
- Active Directory groups,
- AWS IAM groups,
- GitHub teams,
- database roles,
- Kubernetes RBAC groups.

Groups reduce administrative duplication, but poorly designed groups can also accumulate excessive authority. Membership must remain intentional.

## 9. Ownership

Traditional Unix filesystem objects have:

- an owning user,
- an owning group,
- permissions for the owner,
- permissions for the group,
- permissions for everyone else.

Conceptually:

```text
resource
├── owner
├── group
└── others
```

When a process requests access, the kernel compares the process credentials with the resource's ownership and permission metadata.

We will later decode representations such as:

```text
rwxr-xr--
```

The important point for now is that permissions are evaluated relative to identity and ownership.

## 10. Root

`root` is the traditional Unix superuser, normally represented by UID `0`.

It is often described as the administrator account, but a more useful mental model is:

> Root is a highly privileged identity that bypasses or overrides most ordinary permission boundaries.

Root is powerful because the operating system treats its credentials specially.

Running as root does not make a program correct or safe. It merely gives the process enough authority to cause much greater damage when something goes wrong.

## 11. `sudo`

`sudo` allows an authorized user to run a command with another identity, commonly root.

It is best understood as controlled temporary elevation, not as a universal prefix for fixing errors.

```text
normal identity
      ↓
approved elevation
      ↓
privileged command
      ↓
return to normal identity
```

This follows the principle of least privilege: operate with ordinary authority by default and elevate only for a specific task that requires it.

Repeatedly solving permission errors with `sudo` can hide ownership mistakes, unsafe installation practices, or a flawed workflow.

## 12. Principle of least privilege

The **principle of least privilege** says:

> Give an identity only the authority required to perform its current responsibility, and no more.

A build process may need to:

- read source code,
- execute compilers,
- write build artifacts.

It should not automatically have authority to delete production databases.

Least privilege reduces blast radius. It protects systems not only from malicious behavior, but also from ordinary mistakes and defective software.

## 13. Identity, authority, and capability

These three ideas are related but distinct.

### Identity

Who or what is acting?

### Authority

What operations is that identity permitted to perform?

### Capability

What operations can the system actually perform with the tools and resources available?

Examples:

- A user may be authorized to compile C++ but have no compiler installed.
- Docker may be installed, but the user may lack permission to access the Docker socket.
- A process may have database credentials but no network route to the database.

This distinction prevents vague debugging. A failure may come from missing authority, missing capability, or the wrong identity.

## 14. Authentication is not authorization

A common security mistake is treating successful login as permission to do everything.

```text
successful authentication ≠ unlimited authorization
```

Examples:

- An employee can log in to AWS but cannot modify production resources.
- A database user can connect but cannot run `DELETE`.
- A developer can access a repository but cannot change branch protection.
- A Unix user can log in but cannot edit `/etc/hosts` without elevation.

Secure systems authenticate first and authorize each protected operation afterward.

## 15. Permission debugging model

When access fails, ask these questions in order:

1. **What process is making the request?**
2. **Which identity and groups does it have?**
3. **How was that identity established?**
4. **Which resource is it actually accessing?**
5. **Which operation is being attempted?**
6. **Which rule grants or denies that operation?**
7. **Is an additional security layer involved?**

The final question matters because modern macOS and Linux systems may enforce controls beyond traditional file permissions, including access-control lists, sandboxing, mandatory access controls, privacy protections, and service policies.

## 16. Why “permission denied” is useful

A denial is not merely an obstacle. It is evidence that a security boundary is working.

The goal is not to eliminate permission checks. The goal is to determine whether:

- the wrong identity is acting,
- the resource has incorrect ownership,
- a required permission is missing,
- the workflow is attempting an unsafe operation,
- temporary elevation is appropriate.

Bypassing the boundary without understanding it trades a visible failure for a hidden risk.

## 17. macOS, Linux, and Windows

All three platforms implement identity and authorization, but expose them differently.

| Concept | Windows | macOS | Linux |
|---|---|---|---|
| User identity | Security identifier (SID) | UID plus Apple security layers | UID |
| Group identity | Group SID | GID and directory-service groups | GID |
| Elevated authority | Administrator token and UAC | `sudo`, authorization services | `sudo`, root, policy tools |
| Basic filesystem security | NTFS ACLs | POSIX permissions and ACLs | POSIX permissions and ACLs |
| Additional controls | Integrity levels, Defender, policy | sandboxing, TCC, SIP | SELinux, AppArmor, capabilities |

Traditional Unix permissions are foundational, but they are not the entire modern security model.

## Core Computer Science Concept

A secure system separates four questions:

1. **Identity** — Who or what is acting?
2. **Authentication** — How is that claim verified?
3. **Authorization** — What may the verified identity do?
4. **Permissions** — Which concrete operations implement that authority?

This model transfers across operating systems, cloud platforms, databases, APIs, and distributed systems.

## Engineering Connections

This chapter connects directly to:

- file ownership and mode bits,
- process credentials,
- SSH login and key authentication,
- AWS IAM users and roles,
- database users and roles,
- Docker container users,
- Kubernetes service accounts and RBAC,
- OAuth scopes,
- GitHub repository permissions,
- CI/CD execution identities,
- secrets management,
- zero-trust architecture.

## From the Field

A deployment pipeline can authenticate to AWS successfully but receives an access-denied response when uploading an artifact.

The credentials are valid. Authentication succeeded.

The failure is authorization: the assumed role lacks the required `s3:PutObject` permission for the target resource.

Treating the issue as a login problem wastes time. Separating authentication from authorization points directly to the policy evaluation.

## Engineering Review

### What problem does this solve?

It gives the operating system a reliable basis for protecting resources and containing the actions of users, services, and applications.

### Why was it designed this way?

Identity and permission boundaries allow multiple users and processes to share a machine without granting every actor unrestricted authority.

### When should I use it?

Use this model whenever designing, deploying, debugging, or reviewing access to any protected resource.

### When should I avoid it?

Do not reduce modern security to basic Unix mode bits alone. Filesystem ACLs, sandboxing, cloud policies, network controls, and application-level authorization may also participate in the decision.

### How does this make me a better engineer?

It replaces vague access troubleshooting with a structured analysis of actor, proof, resource, operation, and policy.

### How does this reduce waste?

It prevents trial-and-error privilege escalation and helps locate the actual failing security layer quickly.

## Handbook Principle #7

> Every secure system must answer four questions: Who are you, how was that identity verified, what are you authorized to do, and which permissions implement that authority?

## Practical observation

On a Unix-like system, the following concepts can be inspected separately:

- the current user's identity,
- the groups associated with that identity,
- the identity attached to a process,
- the ownership of a file,
- the permissions attached to that file.

The commands for inspecting them come later. For now, keep the model clear: a process acts, credentials identify it, the kernel evaluates authority, and the resource is either exposed or protected.