# Chapter 65 — Reliable Shell Script Execution

An interactive command inherits a person's shell, current directory, environment, attention, and recovery decisions. A reliable shell script must make those dependencies explicit enough to run again without the original terminal session.

The central idea is:

> A shell script is a program with an interpreter, argument contract, process environment, streams, exit status, and owned state—not a saved transcript.

## 1. Choose the language before writing syntax

“Shell” names a family of languages. POSIX `sh`, Bash, Zsh, PowerShell, Fish, and Windows `cmd.exe` have different grammars and behavior. A script must select one implementation contract.

Use POSIX shell syntax when the required deployment environments provide a conforming `sh` and the smaller language is sufficient. Choose Bash when the program deliberately uses Bash arrays, `[[ ... ]]`, or other Bash features. Use PowerShell when its object pipeline and target environments fit. Do not create a cross-shell polyglot unless that complexity is itself a requirement.

Test on the oldest supported interpreter and operating system. “Works in my interactive Zsh” does not prove that `/bin/sh` on a server understands it.

Shell remains a good fit for short programs that compose commands and perform limited file orchestration. Move to a language with stronger data structures and libraries when parsing, state, concurrency, or error recovery dominates.

## 2. The shebang selects direct execution

On Unix-like systems, the first line can request an interpreter:

```bash
#!/usr/bin/env bash
```

When an executable file is invoked directly, the operating system and launcher use this line to find the interpreter. `/usr/bin/env bash` searches the current `PATH`, which helps with nonstandard installation paths but also makes `PATH` part of interpreter selection. A fixed path such as `#!/bin/bash` is more deterministic only where that path is guaranteed.

Invocation changes the contract:

```bash
./report.sh input.txt       # uses shebang; execute permission required
bash report.sh input.txt   # explicitly uses Bash; execute permission not required
sh report.sh input.txt     # explicitly uses sh and overrides the Bash shebang
```

Running a Bash script with `sh` is not a portability test. It selects another language and can fail or, worse, behave differently.

PowerShell scripts conventionally use a `.ps1` extension and an explicit `pwsh -File script.ps1` or platform-supported direct invocation. Windows execution policy and file association are separate from Unix executable permission.

## 3. Source files are not executed files

Executing a script creates a new shell process. Sourcing it with `. ./script.sh` or `source script.sh` runs its commands inside the current shell and can change the caller's directory, variables, options, functions, and traps.

Only source files designed as libraries. A standalone script that calls `exit` can terminate the caller when sourced. A library should document the shell it supports and avoid performing work merely because it was loaded.

For executable scripts in Git, record the executable bit where the target filesystem supports it:

```bash
chmod +x report.sh
git update-index --chmod=+x report.sh
```

Archive tools, Windows filesystems, and copy processes can lose mode metadata. Deployment should verify permissions rather than assuming the source checkout preserved them.

## 4. Arguments are an interface

The shell assigns positional parameters: `$0` names the invoked script, `$1` is the first argument, and `$#` is the count. Validate the count and meaning before doing work.

```bash
if (( $# != 2 )); then
    printf 'Usage: %s INPUT OUTPUT\n' "$0" >&2
    exit 64
fi

input_file=$1
output_file=$2
```

Quote expansions that represent one argument:

```bash
process_file "$input_file"
```

Without quotes, Bash can split expanded text and expand wildcard characters. A filename containing spaces, `*`, or a leading dash can turn into different arguments.

When forwarding all arguments, `"$@"` preserves each original boundary. `"$*"` joins them into one string. Neither is interchangeable with unquoted `$@`.

Use `--` before untrusted path operands when the called utility supports it:

```bash
rm -- "$temporary_file"
```

This prevents a leading-dash filename from becoming an option. It does not validate that the path is an intended target.

## 5. Exit status is machine-readable control data

Every command reports a numeric exit status. Zero conventionally means success; nonzero means some form of failure. The shell exposes the most recent status as `$?`, but another command immediately overwrites it.

Capture or branch on status at the operation:

```bash
if ! validate_input "$input_file"; then
    printf 'input validation failed: %s\n' "$input_file" >&2
    exit 65
fi
```

A script that prints an error and exits zero lies to schedulers and callers. A script that succeeds should explicitly reach a state its contract calls complete.

Define the statuses callers need to distinguish, keep them stable, and document them. Do not assume every nonzero code from a child program has the same meaning. Signal termination and platform launchers can also transform status values.

Chapter 66 examines pipelines, conditional contexts, and why one universal “strict mode” cannot replace deliberate status handling.

## 6. Keep data and diagnostics on different streams

Processes conventionally receive standard input and expose standard output and standard error. Use them consistently:

- standard output contains the promised result for a successful invocation;
- standard error contains diagnostics, warnings, and progress for a human or log;
- exit status describes success or failure;
- standard input carries data only when the interface declares it.

```bash
printf '%s\n' "$output_file"        # result on stdout
printf 'created output\n' >&2       # diagnostic on stderr
```

This lets a caller capture output without mixing in progress text:

```bash
result=$(./normalize.sh source.txt result.txt)
```

Redirecting or capturing a stream can contain sensitive data. Decide whether logs may contain paths, identifiers, command output, or input fragments. Do not enable indiscriminate tracing around credentials.

## 7. Current directory belongs to the caller

A script normally inherits its caller's current working directory. Relative arguments are resolved from there. The directory containing the script is not automatically the working directory.

```text
/project$ /opt/tools/report.sh data/input.txt
```

Here `data/input.txt` means `/project/data/input.txt`, not `/opt/tools/data/input.txt`.

Choose one rule:

- accept paths relative to the caller and never change directory;
- require absolute paths;
- resolve a known resource relative to the script's own directory;
- accept an explicit working-directory option.

Do not silently `cd` to the script directory unless that is the documented interface. If a directory change is required, check it:

```bash
if ! cd -- "$work_dir"; then
    printf 'cannot enter working directory: %s\n' "$work_dir" >&2
    exit 72
fi
```

In Bash, locating the script robustly across symlinks and sourcing is more complicated than reading `$0`. Avoid it unless packaged resources genuinely require it.

## 8. Treat the environment as input

Scripts inherit variables such as `PATH`, locale, timezone, proxy configuration, and tool-specific options. The interactive shell may also define functions and aliases, although noninteractive behavior differs.

Read only documented variables and validate them. Give optional configuration an explicit default:

```bash
log_level=${LOG_LEVEL:-info}
```

Set locale where byte-oriented behavior is required:

```bash
LC_ALL=C
export LC_ALL
```

Do not erase the entire environment blindly; authentication agents, platform identity, and required runtime variables may be legitimate dependencies. For privileged automation, construct a narrow known environment and an intentional `PATH`. Never place secrets directly in command arguments when they can appear in process listings or logs.

## 9. Temporary state needs ownership and cleanup

Do not invent a predictable temporary filename such as `/tmp/report.tmp`. Another process can race, replace, or pre-create it. Ask the platform to create a unique file or directory with restrictive permissions.

For an output replacement, create the temporary file in the destination directory when possible. A final rename on the same filesystem can avoid exposing a partially written output.

```bash
temp_file=$(mktemp "${output_dir}/.normalize.XXXXXX") || {
    printf 'cannot create temporary file\n' >&2
    exit 73
}
```

The script owns only the exact path returned by `mktemp`. Cleanup must never target an unresolved variable, wildcard, broad directory, or caller-owned input.

Temporary storage can still contain sensitive data. Choose its location, permissions, retention, and cleanup according to the data rather than assuming “temporary” means harmless.

## 10. Traps make best-effort cleanup explicit

Bash can run a trap when the shell exits or receives selected signals:

```bash
temp_file=''

cleanup() {
    if [[ -n $temp_file ]]; then
        rm -f -- "$temp_file"
    fi
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
```

Set the trap before work that might fail, and make cleanup safe to repeat. Clear or update ownership variables after the resource is successfully transferred.

Traps are not guaranteed. Forced termination, host loss, power failure, or a stuck process can leave state behind. Design startup reconciliation or bounded retention when abandoned temporary state matters.

Do not put complex recovery inside asynchronous signal traps. Record intent, stop new work, and let a normal exit path perform bounded cleanup where possible.

## 11. A complete bounded example

This Bash program uppercases one text file into an atomically replaced output on the same filesystem. It makes its narrow portability assumptions visible:

```bash
#!/usr/bin/env bash

usage() {
    printf 'Usage: %s INPUT OUTPUT\n' "$0" >&2
}

if (( $# != 2 )); then
    usage
    exit 64
fi

input_file=$1
output_file=$2
output_dir=$(dirname -- "$output_file") || exit 70
temp_file=''

cleanup() {
    if [[ -n $temp_file ]]; then
        rm -f -- "$temp_file"
    fi
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

if [[ ! -f $input_file ]]; then
    printf 'input is not a regular file: %s\n' "$input_file" >&2
    exit 66
fi

if [[ ! -d $output_dir ]]; then
    printf 'output directory does not exist: %s\n' "$output_dir" >&2
    exit 73
fi

temp_file=$(mktemp "${output_dir}/.normalize.XXXXXX") || {
    printf 'cannot create temporary file in: %s\n' "$output_dir" >&2
    exit 73
}

if ! LC_ALL=C tr '[:lower:]' '[:upper:]' \
    < "$input_file" > "$temp_file"; then
    printf 'transformation failed\n' >&2
    exit 74
fi

if ! mv -- "$temp_file" "$output_file"; then
    printf 'cannot replace output: %s\n' "$output_file" >&2
    exit 74
fi

temp_file=''
printf '%s\n' "$output_file"
```

The program requires Bash plus utilities supporting the options shown. It does not preserve source permissions or metadata, refuse an existing output, detect symlink races in a hostile writable directory, or promise Unicode case conversion. Those are contract decisions, not details to hide.

For high-consequence files, use a language and platform API that can open paths with stronger race protections, apply and verify metadata, synchronize durable data where required, and report richer failures.

## 12. Test invocation, not only the happy path

In a disposable directory, test:

- a filename containing spaces and wildcard characters;
- a missing input;
- a missing or unwritable output directory;
- an existing output;
- interruption before the final rename;
- redirected standard output and standard error;
- invocation from a directory other than the script's directory;
- the minimum supported Bash version;
- absence of a required external utility.

After every failure, inspect exit status, output integrity, and leftover temporary files. Never perform these tests against important data.

Syntax checking such as `bash -n script.sh` finds parsing errors but does not execute expansions, commands, cleanup, or failure paths. Static analysis and runtime tests complement it.

## 13. Mark the portability boundary

Portability is a declared target matrix, not the absence of obvious extensions. Document:

- interpreter and minimum version;
- required commands and options;
- operating systems and filesystems;
- text encoding and locale;
- path and filename assumptions;
- signal and process behavior;
- installation and executable permissions.

If a script is Bash-specific, say so and use a Bash shebang. If it must be POSIX `sh`, test with the actual supported shells and remove Bash syntax deliberately. If it must run on Windows, decide whether the supported environment is PowerShell, WSL, Git Bash, or another runtime; those are not interchangeable.

## Common Misconceptions

- “The `.sh` extension chooses a shell.” Invocation and the shebang choose the interpreter.
- “Quoting is only needed for spaces.” It also prevents wildcard expansion, splitting, and empty-argument loss.
- “The script starts in its own directory.” It normally inherits the caller's working directory.
- “A temporary filename is safe because it is in `/tmp`.” Predictability and shared permissions create races.
- “An exit trap always runs.” Several termination and host-failure conditions bypass it.

## Core Computer Science Concept

A shell script is a **process interface**. Its argument vector, environment, file descriptors, working directory, credentials, and exit status form the boundary through which a parent process creates and observes it.

## Engineering Connections

- Argument boundaries are the process-level counterpart of message framing in networking.
- Standard streams make shell programs composable without mixing machine data and diagnostics.
- Temporary-file ownership applies the same exact-target discipline used for safe filesystem changes.
- Explicit exit status lets schedulers and later pipeline stages distinguish success from failure.

## From the Field

A nightly script works when an engineer runs it from the project directory but fails under a scheduler because the scheduler starts elsewhere and supplies a smaller `PATH`. Replacing implicit relative paths with documented arguments, validating required commands, and emitting a nonzero exit status turns a silent environment dependency into a reliable interface.

## Engineering Review

### What problem does this solve?

It turns a command sequence into a repeatable process whose interpreter, inputs, outputs, environment, cleanup, and completion are explicit.

### Why was it designed this way?

Shell programs inherit operating-system process state, so reliability requires controlling or documenting that state rather than relying on an interactive session.

### When should I use it?

Use a shell script for small, bounded command orchestration when the supported shell and external utilities are known.

### When should I avoid it?

Avoid shell when complex structured data, concurrency, large state models, or strong filesystem guarantees dominate the program.

### How does this make me a better engineer?

It makes you see invocation and cleanup as public interfaces rather than incidental syntax.

### How does this reduce waste?

It prevents environment-only successes, corrupted outputs, leaked temporary files, broken argument boundaries, and false-success scheduler runs.

## Handbook Principle #65

> Make every shell program declare its interpreter, preserve argument boundaries, own only exact temporary state, and report truth through streams and exit status.

## Practical Observation

Create a disposable directory and save the bounded example there using an editor. Run `bash -n` first, then test it with an input named `source * file.txt`, redirected standard output and error, a missing input, and a missing output directory. Record exit status and temporary files after each run, then delete the disposable directory.

## Looking Ahead

A reliable invocation boundary is necessary but not sufficient. Chapter 66 examines tests, branches, loops, functions, pipelines, retries, traps, and explicit error handling inside the shell program.

## References

- [GNU Bash Reference Manual](https://www.gnu.org/software/bash/manual/bash.html)
- [POSIX Shell Command Language](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html)
- [Microsoft PowerShell automatic variables](https://learn.microsoft.com/powershell/module/microsoft.powershell.core/about/about_automatic_variables)
- [Microsoft PowerShell invocation documentation](https://learn.microsoft.com/powershell/module/microsoft.powershell.core/about/about_pwsh)
