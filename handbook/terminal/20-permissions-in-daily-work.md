# Chapter 20 — Permissions in Daily Work

[Chapter 7](../foundations/07-identity-authentication-authorization-and-permissions.md) separated identity, authentication, authorization, and permissions. This chapter applies that model to ordinary Unix filesystem work.

The central idea is:

> Diagnose access from the requesting process through every directory to the target object, then make the narrowest change that satisfies the requirement.

## 1. “Permission denied” is a conclusion, not a diagnosis

An access attempt involves more than the final file's visible mode:

```text
process credentials
→ namespace and mount boundary
→ search permission on each directory
→ ownership, mode, and ACL evaluation
→ operation-specific checks
→ application policy
```

Changing the final object to mode `777` addresses only one possible layer and often creates an unnecessary exposure.

## 2. Inspect the requesting identity

Start with the process context:

```bash
id
whoami
```

`id` can show the effective user and group memberships available to the current process. Group changes made by an administrator may not appear in an already running login session.

For services, containers, CI jobs, and scheduled tasks, do not assume the identity matches your interactive shell. Inspect the actual launcher and process credentials.

## 3. Read a long listing as fields

A typical listing resembles:

```text
-rw-r----- 1 ada developers 240 Sep 14 10:30 report.txt
```

The leading fields communicate:

```text
-           object type indicator
rw-         owner-class permissions
r--         group-class permissions
---         other-class permissions
ada         owning user
developers  owning group
```

The displayed text is a summary. ACLs, extended attributes, mandatory-access-control systems, mount flags, and platform-specific markers may add constraints.

## 4. File permission bits describe operations

For a regular file:

- read permits reading content,
- write permits modifying content,
- execute permits requesting execution as a program, subject to format and other checks.

Write permission on a file does not necessarily grant permission to remove its directory entry. Removal modifies the containing directory.

Likewise, read permission does not guarantee meaningful interpretation, and execute permission does not turn arbitrary bytes into a valid executable.

## 5. Directory permission bits have different meanings

For a directory:

- read permits listing entry names,
- write permits creating or removing directory entries, subject to additional rules,
- execute means **search**: resolving names through that directory.

These combinations produce behavior that surprises people. A process may know a pathname but be unable to resolve it without search permission on a parent. It may search a directory without being allowed to list every name.

To open `/srv/app/config/settings`, the process needs appropriate search access through `/srv`, `/srv/app`, and `/srv/app/config`, plus access to the final object.

## 6. Symbolic `chmod` expresses a relative policy

Symbolic modes name a class, operation, and permissions:

```bash
chmod u+x -- tool
chmod g-w -- report.txt
chmod o= -- secret.txt
chmod u=rw,g=r,o= -- report.txt
```

Classes are:

```text
u  owner
g  group
o  other
a  all classes
```

Operators add (`+`), remove (`-`), or set exactly (`=`). Symbolic forms are often clearer during review because they communicate the intended change.

## 7. Octal modes encode complete bit sets

The familiar values are:

```text
read     4
write    2
execute  1
```

Add them within each class:

```text
7 = read + write + execute
6 = read + write
5 = read + execute
4 = read
```

Examples:

```bash
chmod 600 -- private-key
chmod 644 -- public-document
chmod 750 -- team-tool
```

Numeric modes compactly set a complete policy. They can also erase bits unintentionally when used without inspecting current state. Never cargo-cult a number without translating it into required operations.

## 8. Execute is not a general “fix access” bit

Adding execute permission to data files rarely solves a legitimate need:

```bash
chmod +x data.json
```

Executable scripts also need a valid interpreter directive, readable content under relevant rules, a usable filesystem, and an environment that can locate the interpreter.

Prefer granting only the operation required. Read access and execution authority are distinct.

## 9. Ownership and mode solve different problems

Inspect before changing ownership:

```bash
ls -ld -- shared
id
```

Administrative commands may include:

```bash
chown user -- file
chgrp developers -- file
```

Changing ownership affects who controls future permission changes and may have security consequences. Recursive ownership changes are broad mutations and can break applications whose files intentionally have different owners.

Use group-based collaboration or application-specific service ownership instead of repeatedly transferring files between individual users.

## 10. `umask` filters permissions at creation

The process creation mask influences permission bits requested for new objects:

```bash
umask
umask 027
```

A useful model is:

```text
requested creation mode
minus bits prohibited by umask
= initial permission bits
```

It is not always correct to describe this as ordinary decimal or octal subtraction. The operation clears masked bits from the requested mode.

Files are commonly created without execute bits even under a permissive mask because the creating application did not request execution. Existing files are not retroactively changed when `umask` changes.

## 11. Privilege escalation crosses a security boundary

`sudo` can run an authorized command with another identity, commonly root:

```bash
sudo command
```

It is not a prefix for making unexplained errors disappear. Before elevation, ask:

- Which protected object requires the operation?
- Why should this identity perform it?
- Can ownership, group membership, or destination design avoid elevation?
- Exactly which command and expansions execute with increased authority?
- What files will become owned by the elevated account?

Shell redirection can occur before `sudo` runs. For example, `sudo printf ... > protected-file` may attempt the redirection as the original shell identity. Understanding the interpreter boundary prevents misleading fixes.

## 12. Shared directories need directory policy

Team collaboration involves more than changing individual files. A shared directory may need:

- a deliberate owning group,
- group write and search permissions,
- a creation mask compatible with collaboration,
- group inheritance behavior where supported,
- and possibly a default ACL.

The set-group-ID bit on a directory commonly makes new entries inherit the directory's group. The sticky bit on shared writable directories restricts who can remove or rename entries under platform rules.

These special bits solve specific shared-directory problems. Apply them only after reading the local documentation and threat model.

## 13. ACLs extend the basic mode model

Access control lists can grant or restrict permissions for additional users and groups. Tools such as `getfacl` and `setfacl` are common on Linux but not universal.

An ACL indicator may appear beside the mode in a long listing. Effective access can differ from a naive reading of nine mode characters because an ACL mask limits named user or group entries.

Do not erase ACLs with a broad `chmod` operation while diagnosing. Inspect the extended policy first.

## 14. Other enforcement layers remain possible

An operation permitted by discretionary mode bits can still be denied by:

- a read-only mount,
- SELinux or AppArmor policy,
- container namespace mapping,
- network filesystem identity mapping,
- immutable flags,
- application sandboxing,
- or the application itself.

The correct response is to identify the denying layer, not to keep broadening Unix mode bits.

## 15. A systematic access diagnosis

Use a narrow sequence:

1. Reproduce the exact operation and record the diagnostic.
2. Identify the actual process user and groups.
3. Resolve the exact pathname.
4. Inspect every parent directory and the final object.
5. Inspect ACLs or security labels when indicated.
6. Check mount and namespace context.
7. State the minimum operation required: read, write, search, execute, create, remove, or rename.
8. Change the narrowest policy layer that should authorize it.
9. Retest as the real requesting identity.

This turns permission repair into causal debugging.

## 16. Common misconceptions

### “`chmod 777` proves whether permissions are the problem”

It changes exposure broadly and may not affect ACLs, mounts, labels, identity mapping, or application policy.

### “The file's write bit controls deletion”

Removal changes the containing directory entry and depends largely on directory permissions and special rules.

### “`sudo` applies to the entire line”

The current shell may perform expansions, pipelines, and redirections outside the elevated process.

### “`umask 022` subtracts 22 from every mode”

The mask clears requested permission bits; applications choose the original requested mode.

### “Group membership changes instantly everywhere”

Existing processes retain their credential state until an appropriate new session or process is created.

## 17. Platform comparison

| Concern | Linux | macOS | Windows |
| --- | --- | --- | --- |
| Basic Unix modes | supported | supported | not the primary native ACL model |
| Extended ACL tools | POSIX ACL tools commonly available | macOS ACL syntax and tools differ | Windows security descriptors and ACLs |
| Privilege boundary | root/capabilities and `sudo` policy | root and `sudo` policy | access tokens and UAC elevation |
| Additional controls | SELinux/AppArmor, namespaces, mounts | sandboxing, flags, system protections | integrity levels, Defender controls, sharing rules |

Git can store an executable bit, but it does not preserve a complete cross-platform permission policy.

## Core Computer Science Concept

Permission checking is **authorization over a request context**:

```text
subject + operation + object + policy + environment → allow or deny
```

Least privilege means granting the minimum subject only the operations it needs over the narrowest objects and duration.

## Engineering Connections

- Containers map host and container identities through namespace boundaries.
- CI runners need workspace permissions without permanent administrator authority.
- Cloud IAM generalizes subject, action, resource, and policy evaluation.
- Deployment services use dedicated identities to constrain blast radius.
- Shared repositories need collaboration policy separate from source-control history.

## From the Field

A build executed once with `sudo` creates root-owned outputs in a developer workspace. Later ordinary builds fail and the team responds by running every build with `sudo`.

The initial elevation changed ownership and created a self-reinforcing authority problem. Repair ownership on the exact generated boundary and run the build under the intended identity.

## Engineering Review

### What problem does this solve?

It explains how to diagnose and make routine Unix access decisions without indiscriminately broadening authority.

### Why was it designed this way?

Owner, group, and other modes provide compact discretionary policy, while directories control namespace traversal and mutation.

### When should I use it?

Use it when sharing files, running tools under service identities, preparing executables, or diagnosing access failures.

### When should I avoid it?

Avoid basic mode changes when the actual policy belongs to ACLs, containers, mounts, mandatory controls, or application-level authorization.

### How does this make me a better engineer?

It teaches operation-specific authorization, layered diagnosis, and least-privilege change design.

### How does this reduce waste?

Precise fixes prevent recurring elevation, broken ownership, overexposure, and repeated “permission denied” guesswork.

## Handbook Principle #20

> Diagnose the subject, operation, object, and every enclosing boundary before changing policy; grant only the authority the real workflow requires.

## Practical Observation

In a disposable directory on macOS or Linux:

```bash
mkdir private
printf '%s\n' 'draft' > private/report.txt
chmod 600 private/report.txt
chmod 700 private
ls -ld private private/report.txt
umask
```

Translate every mode into owner, group, and other operations. Then explain separately what another user would need to list `private`, resolve `private/report.txt`, read it, replace its contents, and remove its name.

## Looking Ahead

Permissions determine whether software installation is authorized. Chapter 21 adds the trust, dependency, version, and lifecycle questions needed before bringing new code into an environment.
