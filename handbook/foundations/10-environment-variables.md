# Chapter 10 — Environment Variables

Chapters 8 and 9 examined inherited data channels. A process also begins with a collection of named values called its environment.

The central idea is:

> The environment is process-scoped startup configuration: a child receives values from its launcher, then owns an independent environment for the rest of its lifetime.

## 1. The problem environment variables solve

Programs need configuration that can change without changing source code or rebuilding the executable.

Examples include:

- command search paths,
- locale and time-zone settings,
- service endpoints,
- feature modes,
- temporary-directory locations,
- tool-specific preferences,
- identifiers supplied by CI systems.

Embedding every value in code couples the program to one environment. Requiring a separate configuration file for every small value can add unnecessary coordination. Environment variables provide a lightweight configuration interface already supported by process creation.

```text
launcher configuration
        ↓
name=value environment
        ↓
new process
```

They are one configuration mechanism, not a universal configuration system.

## 2. What an environment contains

At the POSIX process interface, an environment is conceptually an array of strings:

```text
PATH=/usr/local/bin:/usr/bin:/bin
LANG=en_US.UTF-8
APP_MODE=development
```

Each entry has a name and a value separated by the first `=`.

The operating system does not give these values application-specific types. A program receives strings or byte sequences and decides whether a value represents:

- a number,
- a Boolean choice,
- a path,
- a list,
- an address,
- or ordinary text.

Parsing, validation, defaults, and error messages belong to the consuming application.

## 3. The environment belongs to a process

There is no single live global environment shared by the entire computer.

Each process has its own environment:

```text
shell process
├── its environment
├── child A → inherited environment A
└── child B → inherited environment B
```

A process can modify its own environment. That change can affect children it launches afterward, but it does not reach backward into its parent and does not rewrite the independent environment of an already-running sibling or child.

This is the same inheritance boundary introduced in Chapter 4.

## 4. Inheritance is a starting point, not shared state

Suppose a shell has:

```text
APP_MODE=development
```

It launches a server, which inherits that value. The shell later changes its own value to:

```text
APP_MODE=production
```

The already-running server normally remains in development mode. A newly launched process can receive the new value.

```text
time 1: shell development → launch server A → server A development
time 2: shell production  → server A still development
time 3: shell production  → launch server B → server B production
```

Environment variables are therefore poor tools for live dynamic configuration unless an application explicitly reloads values through another mechanism.

## 5. Shell variables and environment variables

A shell maintains variables as part of its own language state.

In a POSIX-style shell:

```bash
mode="development"
```

This creates or changes a shell variable. It is not necessarily included in the environment of external child processes.

Mark it for export:

```bash
export mode
```

Or assign and export together:

```bash
export mode="development"
```

The distinction is:

```text
shell variable → available to the current shell language
exported variable → included in environments created for child commands
```

`export` does not send a live update to processes that already exist.

## 6. Temporary command environments

A shell can provide a value to one command without permanently changing the shell's own value:

```bash
APP_MODE=test command
```

The assignment precedes the command name, so it becomes part of that command's environment.

This is useful for:

- one-off tests,
- comparing locale behavior,
- selecting a tool mode,
- overriding a default for one invocation.

For example:

```bash
LC_ALL=C sort names.txt
```

After the command exits, the shell's previous `LC_ALL` state remains.

Shell functions and special built-ins can have additional shell-specific assignment behavior. Shared scripts should not generalize from one interactive experiment without checking the intended shell.

## 7. Unset and empty are different states

These situations are distinct:

```text
APP_MODE is absent
APP_MODE is present with an empty value
APP_MODE is present with value production
```

In a POSIX-style shell:

```bash
unset APP_MODE
export APP_MODE=""
export APP_MODE="production"
```

An application may assign different meanings:

- absent → use a default,
- empty → explicitly disable a feature,
- nonempty → use the supplied value.

Treating absence and emptiness as identical can create configuration bugs. The application should document and validate the distinction.

## 8. Naming conventions and portability

Environment entries can be more permissive at the operating-system interface than shell assignment syntax. Portable shell variable names use a conservative form:

```text
[A-Za-z_][A-Za-z0-9_]*
```

Environment variables intended for broad use are conventionally uppercase:

```text
APP_MODE
DATABASE_URL
LOG_LEVEL
```

Lowercase names are valid in common shells, but uppercase reduces collisions with ordinary shell variables and follows long-standing utility conventions.

Environment names are case-sensitive in POSIX environments. Windows commonly treats environment-variable names case-insensitively. Cross-platform applications should avoid defining names that differ only by case.

## 9. Values are strings, not shell code

An environment value is data. A child program does not automatically perform shell expansion on it.

If a value contains:

```text
$HOME/config
```

the receiving application may see those literal characters. Expansion happens only if a shell or application deliberately interprets the value.

This is a security boundary. Passing untrusted text through an environment variable is not automatically dangerous; evaluating that text as shell code is.

Avoid patterns such as:

```bash
eval "$UNTRUSTED_VALUE"
```

The environment stores configuration. It does not require executable semantics.

## 10. Quote expansions when using them as arguments

When a shell expands an environment-backed variable into a command line, normal shell parsing rules apply.

```bash
CONFIG_PATH="Engineering Notes/config.json"
command --config "$CONFIG_PATH"
```

Quoting preserves the expanded value as one argument.

This unsafe form can split the value or expand wildcard characters:

```bash
command --config $CONFIG_PATH
```

The variable stored one string. The shell changed it while creating arguments. Keep environment semantics and shell-expansion semantics separate.

## 11. `PATH` connects configuration to command resolution

`PATH` is a list of directories the shell and other launch mechanisms search when a command name does not contain a path separator.

A simplified Unix value is:

```text
/usr/local/bin:/usr/bin:/bin
```

Search order matters. If two directories contain an executable with the same name, the earlier match normally wins.

This can cause:

- the wrong tool version to run,
- interactive and CI behavior to differ,
- a malicious executable to shadow a trusted one,
- a command to disappear when startup configuration changes.

Debug command resolution by inspecting both the process environment and the shell's resolution rules. Do not solve every missing command by appending more directories blindly.

Least privilege applies to search paths: avoid writable or untrusted directories in privileged execution contexts.

## 12. Locale variables change program behavior

Variables such as `LANG`, `LC_ALL`, and specific `LC_*` categories influence behavior including:

- character encoding,
- collation and sorting,
- case conversion,
- date and number formatting,
- regular-expression character classes,
- diagnostic language.

The same command can produce different ordering or matching results under different locales.

This is why environment capture matters when debugging non-reproducible text processing. A command line is only part of the execution context.

Setting `LC_ALL=C` requests simple byte-oriented POSIX locale behavior from conforming tools. Use it deliberately when those semantics match the requirement, not as a ritual fix for every text problem.

## 13. Other widely used environment roles

Common Unix-like environments may contain variables such as:

| Variable | Typical role |
| --- | --- |
| `HOME` | user's home-directory path |
| `PATH` | executable search path |
| `PWD` | shell's logical current working directory |
| `SHELL` | configured user shell path in many environments |
| `TERM` | terminal capability type |
| `TMPDIR` | preferred temporary-file directory for supporting programs |
| `LANG`, `LC_*` | locale selection |

Availability and exact meaning depend on the platform and launcher. An application should not assume every variable exists or is trustworthy merely because it is common.

`PWD` is environment data maintained by a shell, while the kernel also tracks the process's actual working directory. If correctness depends on the real directory, use an operating-system or language API designed to query it.

## 14. Environment size is limited

The argument list and environment supplied when executing a process consume bounded space. POSIX exposes this through limits including `ARG_MAX`.

Environment variables are unsuitable for:

- large documents,
- binary assets,
- unbounded lists,
- bulk data transfer,
- datasets that grow with workload size.

Use files, standard input, storage services, or another explicit data channel for large content.

The environment is a small configuration interface, not a transport for arbitrary application state.

## 15. Environment variables are not automatically secret

An environment value can be exposed through:

- debug logs,
- process inspection permitted by the operating system,
- crash reports and diagnostics,
- child processes that inherit more than they need,
- CI configuration and artifacts,
- container inspection,
- accidental output from commands such as `env`,
- copied terminal transcripts.

The correct conclusion is not that secrets can never enter an environment. Many deployment systems intentionally inject them there. The conclusion is that the environment provides configuration delivery, not confidentiality by itself.

Apply least privilege:

- expose a secret only to the process that requires it,
- avoid printing complete environments,
- prefer short-lived credentials,
- use the platform's secret-management mechanism,
- prevent inheritance into unrelated children,
- rotate credentials after suspected exposure.

## 16. Build-time and runtime configuration differ

Container workflows make this boundary visible.

A build argument configures image construction. An image environment instruction can persist configuration in image metadata and affect later containers. Runtime injection configures a particular container process.

These stages have different lifetimes and audiences:

```text
build configuration → image
image defaults       → container definition
runtime environment  → container process
```

Secrets should not be baked into image layers or durable build metadata. Use build-secret mechanisms for build-time credentials and runtime secret delivery for running workloads.

Always ask when the value is needed, who can inspect the resulting artifact, and how the value will be rotated.

## 17. `.env` files are a tool convention

A file named `.env` has no universal operating-system behavior. A shell does not automatically load it merely because the file exists.

Frameworks and development tools commonly parse `.env` files, but they can differ in:

- quoting rules,
- escape handling,
- variable expansion,
- precedence,
- supported syntax,
- file search location.

Treat the file format as part of the specific tool's contract.

A dot-prefixed name makes the file less visible in ordinary listings; it does not make secret values secure. Do not commit real credentials to source control.

## 18. Configuration needs explicit precedence

Applications often accept configuration from several sources:

- built-in defaults,
- configuration files,
- environment variables,
- command-line arguments,
- remote configuration services.

Without documented precedence, operators cannot predict which value wins.

A possible policy is:

```text
built-in default
  overridden by configuration file
    overridden by environment
      overridden by command-line argument
```

That order is not universally correct. The important qualities are that precedence is intentional, observable, documented, and testable.

Sensitive values may need a separate source and policy rather than participating in ordinary precedence.

## 19. Launchers define environments

An interactive shell is only one process launcher.

Programs can also be started by:

- an IDE,
- `launchd` on macOS,
- `systemd` on Linux,
- Windows services,
- a container runtime,
- Kubernetes,
- a CI runner,
- an SSH service,
- a test harness.

Each launcher decides which environment the child receives.

This explains why adding a value to `~/.zshrc` can fix a terminal invocation while leaving an IDE, background service, or CI job unchanged. Those processes may not start through an interactive zsh session.

Configure the actual launcher instead of relying on an unrelated shell startup file.

## 20. Debug environment problems systematically

When configuration appears missing or wrong, ask:

1. Which process consumes the value?
2. Which process launched it?
3. Was the variable present at launch time?
4. Was it exported or only stored as shell state?
5. Did a later configuration source override it?
6. Is the name spelled with the correct case?
7. Is the value absent, empty, or malformed?
8. Did shell expansion alter it before use?
9. Does the process need to be restarted?
10. Can the value be inspected without exposing a secret?

This model is more reliable than repeatedly editing profile files and reopening terminals.

## 21. Inspect without dumping everything

On macOS or Linux, inspect one known non-secret value:

```bash
printenv PATH
```

Check whether a name is present while distinguishing it from an empty value:

```bash
if printenv APP_MODE > /dev/null; then
  printf '%s\n' "APP_MODE is present"
else
  printf '%s\n' "APP_MODE is absent"
fi
```

Printing the entire environment may expose credentials or private configuration. Prefer targeted inspection and redact diagnostic output before sharing it.

## 22. Platform comparison

| Concept | POSIX-style shell | PowerShell on Windows |
| --- | --- | --- |
| Read process environment | `$NAME` through shell expansion | `$env:NAME` |
| Set for current shell process | `export NAME=value` | `$env:NAME = 'value'` |
| Remove from current process | `unset NAME` | `$env:NAME = $null` |
| Name case | case-sensitive | commonly case-insensitive |
| Persistent user or machine setting | launcher or platform configuration | user/machine environment APIs and settings |

Both models create a process environment inherited by children. Platform tools differ in how they also persist values for future processes.

Changing a persistent user setting does not magically rewrite the environment of processes that are already running. They may need to be restarted from a launcher that reads the new setting.

## Core Computer Science Concept

The environment is an example of **inherited context**.

```text
parent context
    ↓ copy selected values at process creation
child context
    ↓ child may modify its own copy
future descendants
```

Inheritance makes common configuration convenient, but implicit context can hide dependencies. A program that depends on an undocumented variable is harder to test and reproduce.

Strong interfaces make required variables explicit, validate them at startup, and avoid inheriting unrelated state.

## Engineering Connections

Environment reasoning appears in:

- executable search through `PATH`,
- application configuration,
- CI job metadata,
- container runtime settings,
- Kubernetes ConfigMaps and Secrets,
- cloud credentials and regions,
- language-runtime behavior,
- locale-dependent data processing,
- test isolation,
- service launch configuration,
- subprocess security,
- reproducible builds.

The syntax is simple. The engineering work lies in scope, lifetime, precedence, validation, and exposure.

## From the Field

A web service works when launched from Terminal but fails under `launchd` because `DATABASE_URL` is absent.

The developer added the variable to `~/.zshrc`. That file configures an interactive zsh session; it is not the service's launch configuration.

The failure belongs to the process tree:

```text
interactive shell → receives variable → manual service works
launchd           → lacks variable    → managed service fails
```

Moving the value into the managed service's supported configuration or secret-delivery mechanism fixes the actual boundary.

## Engineering Review

### What problem does this solve?

Environment variables let a launcher provide small named configuration values to a process without changing the program's code.

### Why was it designed this way?

Process inheritance supplies configuration through an interface already present during program execution, while keeping each process's state independent.

### When should I use it?

Use environment variables for small process-start configuration that varies across invocations or deployment environments.

### When should I avoid it?

Avoid using the environment for large data, live shared state, complex nested configuration, or secrets that require guarantees the launcher and runtime do not provide.

### How does this make me a better engineer?

It teaches you to identify configuration scope, launcher ownership, inheritance, precedence, validation, and security exposure.

### How does this reduce waste?

Explicit environment contracts prevent machine-specific behavior and replace random profile edits with targeted inspection of the process that actually consumes the value.

## Handbook Principle #10

> Treat the environment as an explicit, bounded startup contract: inherit only what is needed, validate it once, and never confuse configuration delivery with secrecy.

## Practical Observation

In a POSIX-style shell, run:

```bash
HANDBOOK_MODE="shell-only"
sh -c 'printf "child sees: <%s>\n" "$HANDBOOK_MODE"'

export HANDBOOK_MODE
sh -c 'printf "child sees: <%s>\n" "$HANDBOOK_MODE"'

HANDBOOK_MODE="one-command" \
  sh -c 'printf "child sees: <%s>\n" "$HANDBOOK_MODE"'

printf 'parent still sees: <%s>\n' "$HANDBOOK_MODE"
unset HANDBOOK_MODE
```

Explain why the first child receives no exported value, the second inherits `shell-only`, the third receives a temporary override, and the parent retains its own value.

## Looking Ahead

Part I has now established files, processes, identities, streams, pipes, and inherited configuration. Chapter 11 combines those mechanisms into a practical method for designing reliable, composable engineering workflows.
