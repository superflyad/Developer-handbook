# Lesson 5 — The Shell

Lesson 4 established that a process is a running program with identity, state, resources, and a lifecycle. The shell is one such process, but it has a special role: it interprets command language and coordinates other processes.

The central idea is:

> The shell is a command interpreter, process launcher, stateful workspace, and small programming language.

## 1. Where the shell fits

A simplified stack is:

```text
You
  ↓
Terminal emulator
  ↓
Shell
  ↓
Programs
  ↓
Kernel
```

The terminal provides the text interface. The shell interprets what you type. Programs perform work. The kernel manages processes and resources.

The shell is neither the terminal nor the kernel.

## 2. What the shell does

When you enter:

```bash
git status
```

the shell:

1. reads the command line,
2. parses shell syntax,
3. expands variables and patterns,
4. resolves the command name,
5. prepares arguments and environment,
6. configures input and output,
7. asks the kernel to start a process,
8. waits for or manages that process,
9. receives its exit status.

The shell is therefore a coordination layer, not merely a text box.

## 3. Built-ins and external commands

Some commands are implemented inside the shell. These are **built-ins**.

Examples include:

```text
cd
export
alias
```

Others are separate executable programs:

```text
git
python3
grep
find
```

The distinction follows from process state. The current working directory belongs to the shell process. If `cd` were an external child process, it could change only its own directory and then exit. The parent shell would remain unchanged. Therefore, `cd` must run inside the shell.

The same reasoning explains why `export` is a built-in: it modifies the environment that future child processes inherit from the shell.

## 4. The shell is a language

The shell understands syntax for:

- variables,
- conditions,
- loops,
- functions,
- pipelines,
- redirection,
- command substitution,
- exit-code-based control flow.

For example:

```bash
name="Michael"
echo "$name"
```

The shell expands `$name` before `echo` receives its arguments.

This makes the shell a programming language, but a specialized one. It is strongest when orchestrating programs, files, and operating-system tasks. It is usually a poor choice for large application logic.

## 5. Parsing happens before execution

Consider:

```bash
echo "$HOME"
```

Conceptually:

```text
echo "$HOME"
      ↓ shell expansion
echo "/Users/michael"
```

The command receives the expanded result, not necessarily the text you originally typed.

This same rule applies to:

- variables,
- wildcard patterns,
- command substitution,
- redirection operators,
- pipelines,
- quoting.

Many apparent command bugs are actually shell-parsing bugs.

## 6. Command resolution and PATH

When you enter:

```bash
python3
```

the shell must determine what `python3` means. It commonly checks shell functions, aliases, built-ins, and then executable files in directories listed by the `PATH` environment variable.

A simplified `PATH` might contain:

```text
/usr/local/bin:/usr/bin:/bin
```

The shell searches from left to right. The first match wins.

This explains several common problems:

- `command not found`,
- the wrong program version running,
- a command working in one shell but not another,
- local tools shadowing system tools.

The command name alone does not identify an executable. The shell state and search order help determine the result.

## 7. Current working directory

The shell is a long-running process with a current working directory.

When you run:

```bash
cd ~/Projects
```

the shell changes its own working directory. Child processes launched afterward normally inherit that directory.

This is why relative paths depend on where the shell is currently located.

A command may work in Terminal but fail in CI, an IDE, Docker, or a scheduled task because those processes start from different working directories.

## 8. Shell variables and environment variables

A shell variable belongs to the shell:

```bash
name="Michael"
```

An exported variable is included in the environment passed to future child processes:

```bash
export name="Michael"
```

The distinction is:

```text
shell variable → state used by the current shell
environment variable → state inherited by child processes
```

A child receives its own environment. Changing it does not normally rewrite the parent shell's environment.

This connects directly to application configuration, AWS profiles, language runtimes, virtual environments, Docker, and CI systems.

## 9. Startup files and shell modes

A shell can start in different modes, including:

- login,
- interactive,
- noninteractive.

For `zsh`, common configuration files include:

```text
~/.zshenv
~/.zprofile
~/.zshrc
```

They load under different conditions.

This explains why a command or variable may exist in Terminal but disappear in:

- an IDE,
- a script,
- SSH,
- CI,
- a system service.

The application may be fine. The shell may simply have followed a different initialization path.

## 10. Interactive and noninteractive shells

An interactive shell expects a person and may provide:

- a prompt,
- history,
- aliases,
- completion,
- interactive shortcuts.

A noninteractive shell executes commands from a script or automation system.

Reliable scripts should not depend on personal aliases, prompts, or interactive-only configuration. Automation should declare its requirements explicitly.

## 11. Redirection and pipelines are shell syntax

Consider:

```bash
python3 app.py > output.txt
```

Python does not interpret `>`. The shell opens `output.txt` and connects the new process's standard output to that file before Python starts.

Likewise:

```bash
command1 | command2
```

The shell creates a pipe and connects the output of one process to the input of another.

Symbols such as these belong to the shell language:

```text
>  <  |  &&  ||  *  $
```

Understanding which layer owns the syntax is essential for debugging.

## 12. Quoting controls interpretation

Suppose:

```bash
file="My Notes.txt"
```

This is unsafe:

```bash
cat $file
```

The expanded text may be split into multiple arguments.

This preserves one argument:

```bash
cat "$file"
```

Quoting is not decoration. It controls how text becomes arguments.

A strong default habit is to quote variable expansions unless you intentionally need splitting or pattern expansion.

## 13. Globbing

The shell expands wildcard patterns such as:

```bash
*.log
```

into matching filenames before launching the target program.

The program may receive:

```text
app.log
error.log
server.log
```

rather than the literal pattern.

This is why destructive commands involving wildcards deserve deliberate inspection. The shell decides the matched argument list before the command runs.

## 14. Exit codes and control flow

Processes return exit statuses. By convention:

```text
0 = success
nonzero = failure or exceptional result
```

The shell uses those statuses for control flow:

```bash
command1 && command2
```

Run `command2` only if `command1` succeeds.

```bash
command1 || command2
```

Run `command2` only if `command1` fails.

This is a clean interface: the shell does not need to understand the program's internal logic. It only needs a stable result code.

## 15. Foreground and background work

A foreground process normally owns the terminal interaction while the shell waits.

A background process allows the shell to continue accepting commands.

This model supports development servers, long-running tasks, build jobs, and remote work, but a shell is not a full production process supervisor. Long-lived services should usually be managed by tools such as `launchd`, `systemd`, containers, or an orchestration platform.

## 16. Aliases, functions, and scripts

These solve different problems.

### Alias

Use for short interactive substitutions:

```bash
alias gs='git status'
```

### Shell function

Use for small reusable interactive workflows with parameters or logic.

### Script

Use for repeatable, version-controlled automation.

A useful decision rule is:

```text
keystroke reduction → alias
small interactive workflow → function
shared repeatable workflow → script
complex application logic → general-purpose language
```

Do not let shell scripts grow into accidental enterprise applications.

## 17. Common shells

### `sh`

The historical foundation and basis for POSIX shell scripting.

### `bash`

A widely deployed Bourne-style shell, common on Linux and in automation.

### `zsh`

The default interactive shell on modern macOS, with strong completion, globbing, and customization.

### `fish`

A user-friendly interactive shell with excellent defaults, but intentionally not POSIX-compatible.

For this handbook:

- use `zsh` as the primary interactive shell on macOS,
- understand and read `bash`,
- learn portable POSIX shell concepts,
- use shell-specific features only when their value outweighs portability costs.

## 18. When shell scripting is appropriate

Use shell for:

- connecting existing command-line tools,
- filesystem automation,
- build and deployment entry points,
- environment setup,
- short system tasks,
- CI orchestration.

Avoid shell for:

- large business logic,
- complex data structures,
- heavy error handling,
- cross-platform application code,
- long-lived systems with many contributors.

The shell is excellent glue. It is a poor foundation for a skyscraper.

## Platform comparison

| Platform | Common shell | Key characteristic |
|---|---|---|
| Windows | PowerShell | Pipelines pass structured objects and integrate deeply with Windows |
| macOS | `zsh` | Unix shell with strong interactive features |
| Linux | commonly `bash` | Broad deployment across servers, containers, and automation |

The syntax differs, but the transferable ideas remain command parsing, state, process creation, environment inheritance, redirection, and exit status.

## Common misconceptions

### “The terminal runs commands”

The shell interprets commands and launches processes. The terminal provides the interface.

### “Every command is a program”

Some commands are shell built-ins because they must modify shell state.

### “My shell configuration applies everywhere”

Different shell modes and process startup paths load different configuration.

### “Aliases are automation”

Aliases are personal convenience. Scripts are repeatable automation.

### “Bash and zsh are identical”

They share much syntax and behavior, especially for basic interactive work, but differ in startup files, options, completion, arrays, globbing, and extensions.

## Engineering connections

This chapter connects to:

- process inheritance,
- environment variables,
- current working directories,
- file descriptors,
- pipelines,
- CI/CD,
- Docker entrypoints,
- SSH sessions,
- command-line tooling,
- developer environment setup.

## From the field

A developer adds this to `~/.zshrc`:

```bash
export DATABASE_URL="..."
```

The application works from Terminal but fails when launched by an IDE.

The likely issue is not the database. The IDE may not have started from an interactive `zsh` session, so `.zshrc` was never loaded.

The failure is an environment-initialization problem disguised as an application problem.

## Engineering review

### What problem does this solve?

The shell provides a programmable interface for launching processes, managing session state, and composing tools.

### Why was it designed this way?

A command language gives users and automation flexible access to operating-system capabilities without requiring a custom graphical application for every workflow.

### When should I use it?

Use the shell for interactive system work, tool orchestration, short automation, environment management, and build entry points.

### When should I avoid it?

Avoid using shell as the primary implementation language for large, complex, stateful, or cross-platform applications.

### How does this make me a better engineer?

It teaches you to distinguish shell parsing, process execution, inherited state, and application behavior.

### How does this reduce waste?

A well-designed shell workflow converts repeated manual work into fast, consistent, inspectable automation.

## Handbook principle #5

> The shell is a programmable coordinator that interprets commands, manages session state, and launches processes.

## Practice

On macOS, inspect the current shell:

```bash
echo "$SHELL"
ps -p "$$"
```

The first command displays the configured shell path. The second inspects the running shell process. Compare the configured program with the process that is actually executing.