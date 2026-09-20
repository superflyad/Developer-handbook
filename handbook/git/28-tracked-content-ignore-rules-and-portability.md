# Chapter 28 — Tracked Content, Ignore Rules, and Portability

A repository is not a mirror of every file in its directory. It is a curated record. Deciding what belongs in that record affects review quality, security, clone size, and cross-platform behavior.

The central idea is:

> Track the sources needed to reproduce work; exclude local and generated state deliberately; describe content transformations explicitly when platforms differ.

## 1. Classify a file before staging it

A useful inventory distinguishes:

| Class | Typical treatment |
| --- | --- |
| Source and tests | Track |
| Human-maintained configuration templates | Track |
| Lockfiles and manifests | Decide by ecosystem and reproducibility policy |
| Build output and caches | Usually generate, not track |
| Editor and machine-local state | Ignore locally or by project policy |
| Secrets and credentials | Do not commit; use a secret-management boundary |
| Large binary artifacts | Evaluate a package, artifact, or large-file store |

These are defaults, not laws. Some generated files are intentionally versioned when consumers cannot generate them or a release process requires them. The decision should be explicit and documented.

## 2. Ignore rules affect untracked paths

A `.gitignore` file contains pathname patterns that tell Git which **untracked** files not to report or add by default:

```gitignore
build/
*.log
!.keep-log
```

The syntax has details: anchored patterns, directory-only trailing slashes, negation, and nested rule precedence. A negated path cannot be re-included if an excluded parent directory prevents traversal. Test nontrivial patterns instead of guessing.

An ignore rule is not an access-control rule. It does not hide data from the filesystem, Git object history, backups, or a person who explicitly opens the file.

## 3. Tracked files stay tracked

Adding a tracked file to `.gitignore` does not remove it from the index or prior commits. Inspect the tracked state:

```bash
git ls-files -- path/to/file
```

If project policy changes and the file should remain locally but stop being tracked in future commits, a carefully scoped operation is:

```bash
git rm --cached -- path/to/file
```

This stages removal from the next snapshot while leaving the working-tree file. The file remains in earlier history. If it contained a credential, first revoke or rotate the credential; history cleanup is a separate coordinated operation.

## 4. Put rules at the right scope

Project-wide generated paths belong in a tracked `.gitignore` so collaborators share the policy. Personal editor patterns can live in a user-level excludes file. One-off exclusions can live in the repository's local exclude file.

Use the narrowest policy that matches the reason. Adding one person's editor cache to every project may be noise; failing to ignore a project build directory burdens every contributor.

Inspect the deciding rule:

```bash
git check-ignore -v -- build/output.bin
```

For a tracked path, the default command may not display an ignore result because tracked paths are not subject to normal ignore behavior; consult `git check-ignore --help` for diagnostic flags when needed.

## 5. Force-add is an exception, not a policy

Git can stage an ignored file explicitly:

```bash
git add -f -- deliberately-versioned.log
```

Do this only when the exception is understood. A force-add can accidentally publish secrets or bulky output. If an entire category is intentionally tracked, revising the ignore policy may communicate intent better.

## 6. Attributes control how paths are treated

`.gitattributes` assigns properties to path patterns. For example:

```gitattributes
* text=auto
*.sh text eol=lf
*.png -text
```

Attributes can influence text normalization, working-tree line endings, diff treatment, merge behavior, and archive behavior. Unlike ignore rules, attributes apply to tracked content and may affect how bytes enter or leave the index.

Treat a new attributes policy as a repository migration: inspect its effects on existing files before staging a large normalization change.

## 7. Line endings are a representation boundary

Linux and macOS commonly use LF line endings. Windows tools often use CRLF. Git can normalize text in the repository while presenting platform-specific endings in a working tree.

This explains warnings such as “LF will be replaced by CRLF” on a Windows checkout. The warning is about a potential working-tree conversion, not proof that the stored blob is wrong.

Check the effective policy and representation:

```bash
git check-attr text eol -- script.sh
git ls-files --eol -- script.sh
```

An executable shell script usually needs LF in environments where a CR character would break interpreter recognition. Set path-specific policy when the requirement is real, rather than relying only on each contributor's global `core.autocrlf` setting.

## 8. Renormalization deserves its own review

After intentionally introducing text attributes, Git may need to update indexed representations:

```bash
git add --renormalize -- .
git diff --cached --stat
git diff --cached --check
```

Run this only after inspecting the exact repository and expected files. A broad normalization commit can obscure unrelated code changes. Keep it separate from behavior changes and review which paths actually changed.

## 9. Binary and large files need a different cost model

Git can track binary blobs, but ordinary text diffs and repeated large binary revisions are often poor review and storage interfaces. Alternatives include release artifacts, package registries, object storage, or Git LFS where the team explicitly adopts its storage and access model.

Do not assume that adding a large file once has only a one-time cost. Every version may affect clone, fetch, hosting quota, and retention behavior. Choose a lifecycle owner for artifacts.

## 10. A committed secret is an incident

`.gitignore` prevents some accidental future additions; it cannot retract a secret already committed or copied. If a credential enters history:

1. revoke or rotate it promptly,
2. assess exposure and use,
3. coordinate with repository owners,
4. decide whether history rewriting is warranted,
5. address clones, forks, caches, and pull requests where possible,
6. add prevention checks.

Do not make a solo force-push of rewritten shared history and declare the problem solved. Copies can retain or reintroduce the data.

## 11. Portability is more than line endings

Cross-platform repositories can encounter differences in:

- case sensitivity,
- executable bits,
- symlink support,
- filename restrictions,
- text encoding,
- path length behavior,
- and tool availability.

Two paths distinguished only by case may work on one filesystem and collide on another. A symlink committed on Unix may be checked out differently in a Windows environment depending on configuration and privileges.

Repository content policy should be tested on supported platforms, not inferred from one machine's working tree.

## 12. A small policy exercise

In a disposable repository:

```bash
printf '%s\n' 'build/' > .gitignore
mkdir build
printf '%s\n' 'generated' > build/result.txt
printf '%s\n' 'source' > source.txt
git status --short
git check-ignore -v -- build/result.txt
```

The status should report `.gitignore` and `source.txt` as untracked while omitting the generated result. The exact output format may vary; the selection rule should not.

## 13. Common misconceptions

### “Ignored means private”

Ignore is a Git selection rule for untracked paths, not encryption or access control.

### “Ignoring a tracked file removes it from history”

It remains tracked until removed from the index and remains in prior commits afterward.

### “Line-ending conversion changes the code everywhere”

It can make the working tree differ in bytes from normalized repository content under an explicit policy.

### “Git cannot store binary files”

It can; the question is whether Git provides the right review and lifecycle cost model.

### “Removing a secret from the latest commit ends the exposure”

Older commits and external copies may still contain it. Rotate first and coordinate remediation.

## Core Computer Science Concept

This chapter is about **representation policy**. The repository stores selected canonical content; the working tree may be a platform-specific representation. Ignore rules choose untracked inputs, while attributes influence content handling. Confusing these layers creates security and portability defects.

## Engineering Connections

- Reproducible builds need tracked inputs and explicit dependency versions.
- Artifact registries separate build outputs from source history.
- Secret scanners and push protection complement, but do not replace, human staged-diff review.
- Cross-platform CI exposes case, line-ending, and executable-bit assumptions early.

## From the Field

A team adds `.env` to `.gitignore` after discovering that a developer committed a token. New `.env` files stop appearing in status, but the old commit remains on the remote and in clones. The immediate safety action is credential rotation; repository-history repair requires coordination.

## Engineering Review

### What problem does this solve?

It defines which content belongs in Git and how tracked files are represented across platforms.

### Why was it designed this way?

Git separates path selection for untracked files from attributes that govern tracked content transformations.

### When should I use it?

Use these policies when creating a repository, adding generated outputs, supporting multiple platforms, or handling large or sensitive files.

### When should I avoid it?

Do not use ignore rules as a substitute for secrets management or attributes as a casual fix for unexplained content changes.

### How does this make me a better engineer?

It teaches explicit source-of-truth selection, canonical representation, and supply-chain boundaries.

### How does this reduce waste?

Clear policy prevents noisy diffs, costly clones, accidental secret exposure, and cross-platform churn.

## Handbook Principle #28

> Curate what enters history, diagnose ignore rules separately from tracked state, and define canonical content when working-tree representations differ.

## Practical Observation

Run Section 12, then add and commit `source.txt`. Add `source.txt` to `.gitignore`. Verify that it is still tracked with `git ls-files -- source.txt`. Explain why changing an ignore rule cannot alter a prior commit.

## Looking Ahead

With content policy established, Chapter 29 explains how branch and tag names select positions in the commit graph.

## References

- [Git ignore rules](https://git-scm.com/docs/gitignore)
- [Git attributes](https://git-scm.com/docs/gitattributes)
- [GitHub guidance on sensitive data](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
