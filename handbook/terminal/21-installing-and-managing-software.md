# Chapter 21 — Installing and Managing Software

Installing software introduces executable code, files, dependencies, trust roots, update responsibilities, and sometimes privileged services. A package manager coordinates that lifecycle.

The central idea is:

> Before installing software, identify its source, trust chain, destination, dependencies, version policy, update path, authority, and removal story.

## 1. Installation is a system change

An installer may:

- place executable and library files,
- register package metadata,
- create users or groups,
- install services and startup configuration,
- modify shared configuration,
- run maintainer scripts,
- and introduce transitive dependencies.

The command may be one line; the state transition is not.

## 2. A package is more than an archive

A system package normally combines content with metadata:

```text
package identity and version
declared dependencies and conflicts
target files and permissions
installation or removal actions
source and integrity information
```

The package database records installed state. A repository publishes available packages and metadata. The package manager resolves a requested change into a transaction over that state.

This coordination is the main advantage over manually copying a binary into a shared directory.

## 3. Repositories are trust configuration

Adding a repository changes who may supply software under the package identities it covers. Transport encryption protects a connection, while signatures and trusted keys help verify that repository metadata or artifacts come through an accepted trust chain.

A valid signature does not prove that software is benevolent or high quality. It proves a relationship to a trusted signing identity under the system's verification rules.

Before adding a third-party source, ask:

- Who controls it?
- Which packages can it replace?
- How is its signing key established and rotated?
- Does it support this operating-system release?
- How is the source disabled and its packages removed?

## 4. Refreshing metadata is not upgrading packages

On Debian- and Ubuntu-family systems:

```bash
sudo apt update
apt list --upgradable
sudo apt upgrade
```

`apt update` refreshes knowledge of available packages. It does not itself install the available upgrades. `apt upgrade` computes and applies a package change according to APT policy.

An operating-system release upgrade is a larger procedure with separate tooling, compatibility review, backups, and often a required reboot. Do not infer distribution lifecycle from the shared word “upgrade.”

## 5. Search, inspect, then install

A responsible workflow observes before mutation:

```bash
apt search ripgrep
apt show ripgrep
sudo apt install ripgrep
```

On Fedora-family systems, the equivalent workflow commonly uses:

```bash
dnf search ripgrep
dnf info ripgrep
sudo dnf install ripgrep
```

Inspect the proposed transaction before confirming. Package names, repositories, available versions, and commands vary by distribution and release.

## 6. Installation scope changes authority and ownership

System package managers normally require elevation because they modify shared operating-system state. That authority also allows package scripts to make privileged changes.

Do not run an entire interactive shell as root merely to install one package. Elevate the narrow manager command through the platform's normal policy.

User-scoped tools reduce some system impact but still execute code as the user and can change shell startup files, home-directory configuration, or command resolution.

## 7. Homebrew has its own lifecycle

Homebrew manages formulae and casks on macOS and supported Linux environments. A common observation and update sequence is:

```bash
brew info ripgrep
brew update
brew outdated
brew upgrade
```

`brew update` refreshes Homebrew and package definitions; `brew upgrade` updates installed formulae or casks according to its rules.

Pinning can defer upgrades, but it can also withhold security fixes or conflict with dependent packages. Treat pins as explicit temporary policy with an owner and review date.

## 8. Windows package management follows the same questions

WinGet exposes sources and package identities through commands such as:

```powershell
winget search --id Git.Git
winget show --id Git.Git -e
winget install --id Git.Git -e --source winget
winget upgrade
```

Exact identifiers and source selection reduce ambiguity. Individual installers can still request elevation and have their own behavior.

The transferable model remains source, identity, version, authority, transaction, and lifecycle.

## 9. System packages and language dependencies have different scopes

Compare:

```text
APT/DNF/Homebrew  → operating environment or shared tools
npm/pip/Bundler   → language ecosystem and project/runtime dependencies
container image   → packaged filesystem and runtime configuration
```

Installing a Python library globally with a system interpreter can conflict with the operating system's package ownership. Installing a CLI as a project dependency can hide it from unrelated projects.

Choose the manager whose ownership boundary matches the software's role. Part VI will address repeatable project environments and dependency manifests.

## 10. Versions need an explicit policy

“Latest” is not a reproducibility strategy. A working environment needs answers to:

- Which versions are allowed?
- Who decides when to upgrade?
- How are security fixes received?
- What compatibility is tested?
- Can the previous state be restored?
- Is the package still available later?

System administrators may prefer supported distribution versions. Projects may use lockfiles, tool-version files, containers, or reproducible build systems. Each approach trades freshness, compatibility, and maintenance work.

## 11. Removal is not always reversal

Package removal commonly removes manager-owned files but may preserve:

- user data,
- modified configuration,
- caches,
- logs,
- generated state,
- services' external data,
- and dependencies still needed elsewhere.

Examples include:

```bash
sudo apt remove package-name
sudo dnf remove package-name
brew uninstall formula-name
```

Do not execute placeholders literally. Inspect the manager's proposed removal set and distinguish removing software from intentionally deleting application data.

Automatic dependency cleanup also deserves review. A package manager's “no longer required” calculation is based on recorded dependency relationships, not knowledge of every manual workflow.

## 12. Inventory is part of ownership

Useful read-only questions include:

```bash
command -v tool
tool --version
```

Then ask the responsible manager:

```bash
apt list --installed 2>/dev/null
dnf list installed
brew list --versions
winget list
```

These interfaces and output formats differ. For fleet-wide inventory, use structured management or asset tooling rather than parsing human-oriented terminal listings indefinitely.

## 13. Avoid unaudited download-and-execute shortcuts

A pattern such as:

```bash
curl URL | sh
```

combines network retrieval and code execution without a review boundary. The executed content can change between runs, the transport result may be unexpected, and elevated use magnifies impact.

A stronger process is:

1. obtain instructions from the official source,
2. download a versioned artifact,
3. verify identity and integrity through the documented mechanism,
4. inspect relevant behavior,
5. execute with the minimum authority,
6. and record the installed version and update path.

Package managers automate parts of this process but do not eliminate trust decisions.

## 14. Updates are operational changes

An update can change:

- configuration defaults,
- file formats,
- service behavior,
- dependencies,
- command options,
- security policy,
- or restart requirements.

Production updates need testing, maintenance windows where appropriate, backups, rollback planning, monitoring, and ownership. “Security update” can make the change urgent; it does not make the change operationally consequence-free.

## 15. A practical decision sequence

Before installation:

```text
need → available native package? → inspect source and version
→ review transaction and authority → install
→ verify resolution and behavior → record lifecycle owner
```

Before upgrade:

```text
refresh metadata → review changes → assess compatibility
→ protect important state → apply → restart if required
→ verify service and version → monitor
```

This is change management at workstation scale.

## 16. Common misconceptions

### “A signed package is safe”

A valid signature supports provenance and integrity under a trust policy. It does not prove absence of malicious logic or defects.

### “`update` and `upgrade` always mean the same thing”

Managers define these verbs differently. In APT, metadata refresh and package upgrade are separate operations.

### “Uninstall restores the exact previous machine”

User data, configuration, dependencies, and side effects may remain.

### “User-level installation has no security impact”

Code running as a user can access that user's data and modify their environment.

### “Pinning eliminates upgrade risk”

It exchanges change risk for staleness, compatibility, and security risk.

## 17. Platform comparison

| Environment | Common manager | Repository refresh | Package upgrade |
| --- | --- | --- | --- |
| Debian/Ubuntu | APT | `apt update` | `apt upgrade` |
| Fedora-family | DNF | automatic or explicit cache refresh | `dnf upgrade` |
| macOS | Homebrew plus system mechanisms | `brew update` | `brew upgrade` |
| Windows | WinGet plus system mechanisms | source update behavior | `winget upgrade` |

These commands are orientation points, not interchangeable production runbooks. Read the manager and operating-system documentation for the exact release.

## Core Computer Science Concept

Package management is **dependency resolution plus transactional state management under a trust policy**.

A requested package implies a graph of constraints. The manager attempts to choose versions and actions that produce a consistent installed state.

## Engineering Connections

- Software supply-chain security depends on provenance, integrity, and trust-root management.
- Container images snapshot package state but still need rebuild and update ownership.
- CI should declare tool versions instead of relying on runner accidents.
- Fleet management adds staged rollout, policy, inventory, and compliance.
- Reproducible builds strengthen guarantees beyond “same package name.”

## From the Field

A developer adds a third-party repository to obtain one newer tool. Months later, that source publishes replacements for shared libraries and changes unrelated applications during a routine upgrade.

The original decision was broader than one installation. Repository priority and package namespace made the source part of the machine's future update authority.

## Engineering Review

### What problem does this solve?

It coordinates installation, dependency resolution, updates, inventory, and removal across shared software state.

### Why was it designed this way?

Central metadata and repositories let the system reason about relationships and apply consistent lifecycle policy.

### When should I use it?

Use the platform's trusted manager when its ownership boundary and available version fit the software's role.

### When should I avoid it?

Avoid forcing system managers to own project-specific dependencies or using ad hoc installers when a supported, verifiable channel exists.

### How does this make me a better engineer?

It teaches supply-chain trust, dependency graphs, lifecycle ownership, and controlled operational change.

### How does this reduce waste?

Managed inventory and updates reduce manual copying, conflicting versions, abandoned installations, and irreproducible workstations.

## Handbook Principle #21

> Installation grants code a place in your system's future; choose its source, authority, version, update path, and removal policy deliberately.

## Practical Observation

Choose one installed development tool and answer without changing the system:

1. Which pathname does the shell resolve?
2. Which manager, installer, or bundled component owns it?
3. What version is installed?
4. Which source would provide an update?
5. Would an update require elevation or restart anything?
6. Which user data or configuration would remain after removal?

Use `command -v`, the tool's version interface, and your platform manager's read-only inspection commands as evidence.

## Looking Ahead

Installed commands are useful only when the shell can resolve and configure them predictably. Chapter 22 explains startup files, `PATH`, aliases, functions, prompts, completion, and recoverable dotfile changes.
