# Chapter 22 — Shell Startup, Configuration, and `PATH`

A shell session begins with program defaults, invocation mode, inherited environment, and selected startup files. Configuration is executable code that changes every later command.

The central idea is:

> Keep shell startup small, traceable, conditional on the right session type, and recoverable from a clean shell that does not load it.

## 1. Configuration creates implicit context

Shell configuration can change:

- environment variables,
- command resolution,
- aliases and functions,
- completion,
- line editing,
- prompt behavior,
- history policy,
- locale,
- and shell options.

This convenience becomes hidden coupling when a command works only because an undocumented startup file changed its environment.

## 2. Identify the shell and its mode

Do not infer the running shell solely from `$SHELL`. That environment variable commonly records a user's configured login shell, not necessarily the current process.

In Bash, inspect Bash-specific state:

```bash
printf 'Bash version: %s\n' "$BASH_VERSION"
case $- in
  *i*) printf '%s\n' 'interactive Bash' ;;
  *)   printf '%s\n' 'non-interactive Bash' ;;
esac
```

A shell may be:

- interactive or non-interactive,
- a login or non-login shell,
- invoked as `bash` or compatibility name `sh`,
- started normally or with files disabled,
- local, remote, embedded, or launched by another application.

Startup behavior depends on those facts.

## 3. Bash selects startup files by invocation mode

For a normal interactive login Bash shell, the documented sequence is broadly:

```text
/etc/profile
then the first readable one of:
  ~/.bash_profile
  ~/.bash_login
  ~/.profile
```

An interactive non-login Bash shell normally reads:

```text
~/.bashrc
```

A common arrangement has `~/.bash_profile` explicitly source `~/.bashrc`:

```bash
if test -f "$HOME/.bashrc"; then
  . "$HOME/.bashrc"
fi
```

This is a chosen configuration pattern, not a rule that Bash automatically applies in every mode.

## 4. Non-interactive shells are intentionally different

A Bash process running a script does not normally read interactive `~/.bashrc` in the same way. Bash documents `BASH_ENV` for non-interactive startup, with additional mode and remote-shell details.

Do not set `BASH_ENV` casually or rely on interactive aliases inside scripts. Automated execution should declare the environment it needs.

This explains many differences among:

```text
terminal command
shell script
CI step
cron or scheduler job
SSH remote command
IDE task
```

The command text can be identical while startup inputs differ.

## 5. `PATH` is ordered command-resolution policy

`PATH` is a colon-separated list in Unix-like environments:

```bash
printf '%s\n' "$PATH" | tr ':' '\n'
```

When Bash searches for an external command name without a slash, earlier matching directories win.

```text
PATH=/opt/team/bin:/usr/local/bin:/usr/bin:/bin
     first match wins ────────────────────────→
```

Order is behavior. Adding a directory can replace which implementation a familiar name resolves to.

## 6. Modify `PATH` without destroying it

To prepend one trusted directory:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

To append:

```bash
export PATH="$PATH:$HOME/.local/bin"
```

Prepending gives the new directory priority. Appending preserves priority for existing system locations.

Before changing it, verify:

- the directory exists,
- it is controlled by an appropriate identity,
- empty path entries are not introduced,
- duplication will not grow on repeated sourcing,
- and the desired precedence is explicit.

An empty path component can mean the current directory in common Unix behavior. Avoid leading, trailing, or doubled separators.

## 7. Command caches can preserve an older resolution

Bash can remember external command locations. After installing a replacement or changing filesystem state, inspect and clear resolution deliberately:

```bash
type -a tool
hash -t tool 2>/dev/null
hash -r
command -v tool
```

Assigning a new `PATH` clears Bash's remembered command locations, but filesystem changes can still make cached reasoning stale.

Always verify the selected command after configuration changes.

## 8. Aliases are interactive textual conveniences

An alias replaces an initial command token during shell parsing:

```bash
alias ll='ls -la'
```

Aliases are useful for short interactive abbreviations. They are limited for arguments and can make copied commands behave differently.

Avoid changing safety semantics invisibly:

```bash
alias rm='rm -i'
```

Such an alias may encourage habits that fail in scripts or other machines. Safety should live in the workflow, not depend on an optional prompt alias.

## 9. Functions express reusable shell behavior

A function can accept arguments and compose commands:

```bash
croot() {
  local root
  root=$(git rev-parse --show-toplevel) || return
  cd -- "$root" || return
}
```

Functions run in the current shell, so they can intentionally change its state. They are suitable for small interactive workflows.

When logic grows, requires tests, needs portability, or performs consequential automation, move it into a versioned script with an explicit interface.

## 10. The prompt should reveal useful state cheaply

Bash uses variables such as `PS1` and may run `PROMPT_COMMAND` before displaying a primary prompt.

A prompt can show location, version-control state, environment, or prior status. Every prompt render occurs in the interactive loop, so expensive commands create persistent latency.

Do not place secrets in prompts, terminal titles, or command arguments. Do not treat prompt color as proof of production or privilege context; verify the real environment before consequential work.

## 11. Completion improves correctness as well as speed

Readline provides command-line editing and basic completion. Bash programmable completion can supply command-specific candidates.

Completion reduces spelling mistakes and reveals available objects, but it is not authorization or validation. A completed pathname can still identify the wrong environment or destructive target.

Treat completion output as suggestions derived from current shell state.

## 12. History is sensitive persistent state

Bash can store interactive commands in a history list and later write them to a history file. Configuration variables influence size, filtering, timestamps, and synchronization.

History is valuable for retrieval and incident reconstruction, but commands can contain:

- tokens,
- passwords supplied incorrectly as arguments,
- private URLs,
- customer identifiers,
- and sensitive filesystem paths.

Do not rely on history filters as a secret-management system. Prevent secrets from entering command lines and rotate any credential that does.

## 13. Dotfiles are executable configuration assets

Files such as `.bashrc`, `.bash_profile`, and `.profile` deserve source control, review, and portability discipline when they become important.

A good configuration is:

- small enough to understand,
- split only when boundaries are clear,
- guarded when optional commands may be absent,
- free of machine-specific secrets,
- safe when sourced more than once,
- and testable without replacing the current working setup.

Avoid cloning a large framework into startup merely to obtain one alias or prompt feature. Every dependency adds startup and debugging surface.

## 14. Make repeated sourcing predictable

Users often reload a configuration with:

```bash
. "$HOME/.bashrc"
```

If each load blindly prepends the same directory, `PATH` grows duplicates. If it starts background agents or appends hooks, repeated sourcing can create multiple processes or handlers.

Prefer idempotent initialization or clearly distinguish one-time login work from repeatable interactive setup.

Configuration reload is not always equivalent to starting a fresh shell because old variables, functions, aliases, and options may remain.

## 15. Keep a recovery entrance

Bash can start without normal startup files:

```bash
bash --noprofile --norc
```

This provides a clean diagnostic shell when configuration prevents ordinary startup. From there, inspect files and introduce sections incrementally.

Other useful techniques include:

```bash
bash -n ~/.bashrc
bash -x --noprofile --rcfile ~/.bashrc -i
```

`bash -n` checks shell syntax without executing commands, though it cannot prove runtime correctness. Trace mode can expose sensitive expanded values, so capture and share traces cautiously.

## 16. Debug configuration by subtraction

When startup is slow or broken:

1. reproduce with a clean shell,
2. identify the exact invocation mode,
3. confirm which startup files should be read,
4. syntax-check the relevant files,
5. disable half of the configuration,
6. repeat until the responsible section is isolated,
7. inspect command resolution and environment changes,
8. test in a new shell before closing the recovery shell.

This is the same controlled-experiment method used for application debugging.

## 17. macOS and other shells require their own model

Modern macOS commonly uses Zsh as the default login shell. Zsh has its own startup-file sequence and configuration conventions. Bash installed separately can have a different version and location from the system Bash.

Do not paste Bash startup instructions into `.zshrc` merely because some individual commands look similar. Identify the actual shell and consult its documentation.

Likewise, Fish intentionally differs from POSIX shell syntax, and PowerShell profiles are PowerShell scripts selected by host and user scope.

## 18. Common misconceptions

### “`$SHELL` is the current interpreter”

It usually indicates configured login-shell preference, not definitive current-process identity.

### “`.bash_profile` and `.bashrc` are always both loaded”

Bash selects files by invocation mode; one file may explicitly source another.

### “Putting a directory first in `PATH` only adds commands”

It can shadow every same-named command in later directories.

### “Aliases make scripts safer”

Scripts generally should not depend on interactive aliases, and alias presence varies by shell configuration.

### “Reloading `.bashrc` recreates a clean session”

It executes more configuration in the current state and may leave prior definitions behind.

## 19. Platform comparison

| Concern | Bash | Zsh | PowerShell |
| --- | --- | --- | --- |
| Interactive configuration | commonly `~/.bashrc` | commonly `~/.zshrc` | profile paths exposed by `$PROFILE` |
| Login configuration | profile selection rules | Zsh-specific startup sequence | host and scope profiles |
| Command search variable | `PATH` | `PATH` and shell array facilities | `$env:PATH` plus command precedence |
| Completion | Readline and programmable completion | Zsh completion system | PowerShell completers |
| Clean startup | `--noprofile --norc` | Zsh-specific flags | `-NoProfile` |

The durable practice is to identify mode, source files, and command precedence for the actual shell.

## Core Computer Science Concept

Shell startup is **configuration layering and precedence**. Defaults, system files, user files, inherited environment, and interactive changes combine into effective state.

Layering provides customization. Without provenance and precedence rules, it creates configuration drift.

## Engineering Connections

- Application configuration needs explicit source precedence for the same reason.
- CI environments should minimize dependence on interactive user state.
- Dotfile repositories are configuration-as-code at personal scale.
- `PATH` shadowing resembles dependency confusion and namespace precedence defects.
- Fast prompts illustrate latency budgets on frequently executed hooks.

## From the Field

A tool works in a developer's terminal but fails in an IDE task. The terminal is an interactive shell that loads a version-manager function; the IDE launches the executable directly with a different `PATH`.

The durable fix is to configure the toolchain at the launcher boundary or use an explicit executable path, not to keep adding startup files and hoping every launcher reads them.

## Engineering Review

### What problem does this solve?

It makes interactive shell behavior, command resolution, and persistent customization traceable and recoverable.

### Why was it designed this way?

Layered startup allows system defaults and user customization across different invocation modes.

### When should I use it?

Use shell configuration for small interactive environment settings, trusted path additions, completion, and carefully scoped conveniences.

### When should I avoid it?

Avoid hiding project dependencies, production automation, secrets, or large untested programs in interactive startup files.

### How does this make me a better engineer?

It teaches configuration precedence, provenance, idempotence, recovery, and command-resolution security.

### How does this reduce waste?

Small reproducible configuration reduces startup latency, machine drift, and time spent debugging terminal-versus-automation differences.

## Handbook Principle #22

> Treat shell startup as executable configuration: keep it minimal, make precedence visible, verify command resolution, and preserve a clean recovery path.

## Practical Observation

Without editing your configuration, open Bash and record:

```bash
printf 'flags=%s\n' "$-"
printf 'login='; shopt -q login_shell && printf 'yes\n' || printf 'no\n'
printf '%s\n' "$PATH" | tr ':' '\n'
type -a git
```

Predict which Bash startup files apply to that mode. Then start `bash --noprofile --norc`, repeat the observations, and explain every difference you can attribute to inherited environment versus startup code.

## Looking Ahead

Chapter 23 combines Part II into an efficient workflow: retrieve commands, investigate safely, compose incrementally, verify results, and recognize when interactive work should become automation.
