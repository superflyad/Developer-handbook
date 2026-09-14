# Chapter 12 — Command-Line Grammar and Getting Help

Part I explained what the shell, processes, streams, and environment are. Part II begins by learning how to investigate commands without treating their syntax as magic.

The central idea is:

> Read a command as an interface contract: identify the interpreter, command, options, operands, inputs, outputs, and completion status before relying on it.

## 1. The problem memorization does not solve

No engineer can memorize every utility and option. Even familiar command names vary across operating systems, releases, and implementations.

What transfers is the ability to answer:

- What will the shell interpret?
- Which command will run?
- Which arguments will it receive?
- What input does it read?
- What output and diagnostics does it produce?
- How does it report success, absence, or failure?

A copied command may solve today's task. The ability to inspect an interface solves the next unfamiliar task too.

## 2. A simple command becomes an argument vector

Consider this Bash command:

```bash
grep -n -- 'error' application.log
```

After parsing, quoting, and expansion, the shell invokes `grep` with an ordered argument vector conceptually like this:

```text
argument 0: grep
argument 1: -n
argument 2: --
argument 3: error
argument 4: application.log
```

The quote characters are shell syntax; they protect text during parsing and are removed before invocation. The `grep` program receives `error`, not `'error'`.

This boundary matters whenever debugging a command: first determine what the shell produced, then determine how the receiving program interprets it.

## 3. Command names, options, option arguments, and operands

Command documentation usually distinguishes four roles:

```text
utility [options] [operands]
```

- The **utility name** selects an interface.
- An **option** modifies behavior, such as `-n`.
- An **option argument** supplies a value to an option, such as the number in `head -n 5`.
- An **operand** names the object to process, such as `application.log`.

These are conventions, not syntax enforced universally by the shell. Each program parses its own arguments. POSIX defines utility syntax guidelines, while GNU and other ecosystems add conventions such as long options.

Common forms include:

```bash
wc -l README.md
head -n 5 README.md
grep --ignore-case 'warning' application.log
```

Do not assume that every command accepts combined short options, `--long-options`, or options after operands. Read the documentation for the implementation you are actually using.

## 4. `--` ends option parsing when supported

A pathname may begin with `-`. A utility could mistake it for an option:

```bash
printf '%s\n' 'draft' > ./-notes
cat -- ./-notes
```

For utilities that follow the convention, `--` means “treat following arguments as operands.” Prefixing a relative pathname with `./` also prevents the first character from being `-`.

Use both ideas deliberately:

```bash
rm -- ./-obsolete
```

`--` is not a global shell feature. It is an argument interpreted by supporting utilities. Some historical or specialized tools use different interfaces.

## 5. The shell may not run an external file

The word in command position can resolve to several kinds of command:

- an alias,
- a shell keyword,
- a shell function,
- a shell builtin,
- a hashed external command,
- or an executable found through `PATH`.

Inspect resolution in Bash with:

```bash
type cd
type printf
type -a python 2>/dev/null
command -v grep
```

`cd` must affect the current shell's working directory, so it is a builtin. An external child process could change only its own directory and then exit.

Prefer `command -v` or the shell's `type` builtin when reasoning about shell command resolution. `which` is an external utility on many systems and may not understand aliases, functions, or all shell rules.

## 6. A pathname bypasses `PATH` search

If a command name contains a slash, Bash treats it as a pathname rather than searching `PATH`:

```bash
./tools/check
/usr/bin/env
```

This explains why a program in the current directory does not normally run merely by typing its name. The current directory is searched only if `PATH` contains it, which is often undesirable because an untrusted directory could then supply an unexpected executable.

Chapter 22 examines `PATH` and cached command locations in detail. For now, distinguish:

```text
name without slash → shell resolution and PATH search
name with slash    → explicit pathname
```

## 7. Ask the right documentation layer

Different command kinds have different authoritative help.

For a Bash builtin:

```bash
help cd
help type
```

For an external utility:

```bash
man grep
grep --help
```

For a broader topic:

```bash
man 7 signal
info coreutils
```

Not every system installs manual or Info pages, and not every command implements `--help`. On macOS, BSD-derived utilities can differ from GNU examples found online. On minimal containers, local documentation may be absent. In those cases, identify the implementation and consult its official manual.

## 8. Learn to read a synopsis

Documentation uses a compact notation. A typical synopsis might resemble:

```text
tool [OPTION]... PATTERN [FILE]...
```

Common conventions are:

- brackets indicate optional material,
- an ellipsis means an item may repeat,
- unbracketed words indicate required roles,
- alternatives may be separated by `|`,
- italic or placeholder words represent values you supply.

The punctuation describes the interface; it is not usually typed literally.

Read the detailed `OPTIONS`, `OPERANDS`, `STDIN`, `STDOUT`, `STDERR`, and `EXIT STATUS` sections after the synopsis. Syntax alone does not explain semantics.

## 9. Help output is evidence, not a portability guarantee

Record the environment when behavior matters:

```bash
printf 'shell=%s\n' "$BASH_VERSION"
uname -s
grep --version 2>/dev/null | head -n 1
```

The same command name can refer to different implementations. An option working in GNU `sed` does not prove it works in BSD `sed`. A script working interactively does not prove it has the same shell, `PATH`, locale, or tools in CI.

Portable engineering begins by separating:

```text
standardized behavior
implementation extension
local configuration
accidental observation
```

## 10. Exit status is part of the interface

After a foreground command finishes, Bash exposes its status through `$?`:

```bash
grep -q 'needle' haystack.txt
status=$?
printf 'status=%s\n' "$status"
```

Many commands use zero for success and nonzero for failure, but meanings are command-specific. For `grep`, zero means a match was selected, one means no match, and a larger value indicates an error in common implementations.

“Nonzero” therefore does not always mean “the tool malfunctioned.” It can represent a useful negative result. Read the documented exit-status contract before placing a command in automation.

## 11. Build a short investigation loop

When meeting an unfamiliar command:

1. Inspect its resolution with `type -a` or `command -v`.
2. Read its synopsis and operand definitions.
3. Identify defaults, side effects, and overwrite behavior.
4. Check its input, output, diagnostics, and exit statuses.
5. Test a minimal case in a disposable directory.
6. Test empty input, a missing object, and an unusual name.
7. Compare the observed implementation with the environment where it will run.

This is faster than debugging a copied command after it touches production data.

## 12. Common misconceptions

### “The shell understands every option”

The shell generally constructs arguments. The invoked utility normally interprets its own options.

### “A space always separates arguments”

Unquoted shell syntax can split words, but quoting and expansion determine the final argument boundaries. Chapter 18 makes that process explicit.

### “`man` and `--help` are interchangeable”

Help output is often a concise reminder. Manual pages normally document semantics, environment, files, diagnostics, and exit status more fully.

### “If a command printed the expected line, it succeeded”

Output and completion status are separate interfaces. Inspect both when correctness matters.

### “The command online is the command on my machine”

Names persist across implementations. Options and defaults may not.

## 13. Platform comparison

| Question | Bash on Linux | macOS default environment | PowerShell |
| --- | --- | --- | --- |
| What resolves a name? | aliases, functions, builtins, then `PATH` | shell rules plus BSD-oriented system tools | aliases, functions, cmdlets, applications |
| Primary local help | `help`, `man`, `info` | shell help and `man` | `Get-Help`, `Get-Command` |
| Typical pipeline contract | bytes or text | bytes or text | objects between cmdlets |
| Long GNU options guaranteed? | no, but common with GNU tools | no | not applicable to cmdlets |

The transferable method is to identify the interpreter and implementation before reasoning from syntax.

## Core Computer Science Concept

Command invocation is an example of an **interface boundary**. The caller supplies an ordered vector of strings plus standard streams and an environment. The callee interprets those inputs according to its own contract.

This resembles a function call, but the process boundary adds independent failure, environment, filesystem state, permissions, and operating-system scheduling.

## Engineering Connections

- CI jobs fail when local and runner implementations differ.
- Containers make command paths and available documentation intentionally smaller.
- Subprocess APIs require explicit argument boundaries to avoid shell injection.
- CLI design benefits from consistent options, diagnostics, and exit statuses.
- Incident response depends on identifying the exact binary and configuration in use.

## From the Field

An engineer sees `test` in a deployment script and searches for `/usr/bin/test`. In Bash, however, `test` may resolve to a builtin. Adding an external executable earlier in `PATH` does not change which implementation runs.

The repair begins with `type -a test`, not with more path changes. Resolution is part of the behavior.

## Engineering Review

### What problem does this solve?

It provides a repeatable way to understand unfamiliar command interfaces and implementation differences.

### Why was it designed this way?

The shell and utilities have separate responsibilities: the shell constructs an invocation, and the selected command interprets its arguments and streams.

### When should I use it?

Use this method before running unfamiliar commands, writing automation, debugging environment differences, or documenting operational procedures.

### When should I avoid it?

Do not substitute endless documentation reading for a small controlled experiment. Use both documentation and observation.

### How does this make me a better engineer?

It replaces syntax memorization with interface reasoning, implementation awareness, and testable assumptions.

### How does this reduce waste?

Correctly identifying the interpreter, command, and contract prevents option errors, portability failures, and unsafe copy-and-paste debugging.

## Handbook Principle #12

> Before trusting a command, identify who interprets each part, which implementation runs, and how the interface reports results and failure.

## Practical Observation

In Bash, compare these commands:

```bash
type -a printf
help printf | head -n 8
command -V printf
command -v printf
```

Then run:

```bash
builtin printf '%s\n' 'from the Bash builtin'
command printf '%s\n' 'resolved without functions'
```

Record which forms are Bash-specific, which command implementation each form selects, and what would need to change in another shell.

## Looking Ahead

Commands operate relative to a location and on pathnames. Chapter 13 makes working directories and path resolution predictable before Part II begins changing filesystem state.
