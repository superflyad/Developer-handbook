# Chapter 8 — Standard Input, Standard Output, and Standard Error

The previous chapters established that the shell launches processes and that each process begins with open communication channels. This chapter makes the three conventional channels explicit.

The central idea is:

> Standard input, standard output, and standard error separate a program's data source, normal results, and diagnostics from the destinations connected to them.

## 1. The problem standard streams solve

A program often needs to receive data and report results. Hard-coding one keyboard, filename, window, or network connection into the program would make it difficult to reuse.

Unix gives a new process conventional channels that are already open:

```text
standard input  → program → standard output
                     ↘ standard error
```

The program can read and write without needing to know whether the other end is:

- a terminal,
- a regular file,
- a pipe,
- another process,
- a device,
- or a service that launched it.

This separation is a form of dependency injection at the operating-system boundary. The launcher supplies the connections; the program focuses on its transformation.

## 2. The three conventional channels

The channels have distinct responsibilities.

### Standard input

**Standard input**, or `stdin`, is the conventional source of primary input.

An interactive program may receive keystrokes through it. A noninteractive program may receive bytes from a file or another process.

### Standard output

**Standard output**, or `stdout`, is the conventional destination for normal results.

Data written there should be suitable for display, capture, or use by another program when the command is designed as a filter.

### Standard error

**Standard error**, or `stderr`, is the conventional destination for diagnostics.

Warnings, progress information, and failure explanations belong there when mixing them into normal output would corrupt the program's data contract.

These are conventions, not truth detectors. A program can write the wrong information to any channel. Good tools use the separation consistently.

## 3. Streams and file descriptors

Two related layers are often collapsed in casual explanations.

At the operating-system level, a process refers to open resources using small integers called **file descriptors**. The conventional descriptors are initially:

```text
0  standard input
1  standard output
2  standard error
```

At the language-library level, programs may use buffered stream objects such as C's `stdin`, `stdout`, and `stderr`, Python's `sys.stdin`, `sys.stdout`, and `sys.stderr`, or equivalent abstractions.

A useful model is:

```text
language stream
      ↓
file descriptor
      ↓
open file, terminal, pipe, socket, or device
```

The layers are connected but not identical. File descriptors are kernel-facing process resources. Language streams can add encoding, formatting, and buffering.

## 4. The descriptors are inherited connections

When a shell launches a program, the child normally inherits the shell's open standard descriptors after any requested redirections are applied.

The child does not ask, “Which Terminal window should I print to?” It writes to descriptor 1. The connection already determines where those bytes go.

```text
shell connected to terminal
├── descriptor 0 → terminal input
├── descriptor 1 → terminal display
└── descriptor 2 → terminal display
          ↓ launch child
child inherits those connections
```

Standard output and standard error often appear in the same terminal, but they remain separate channels. A shared visible destination does not make them the same descriptor.

## 5. Redirection changes connections

Redirection is shell syntax that changes a command's file-descriptor connections before the command executes.

This sends standard output to a file:

```bash
printf '%s\n' "build complete" > build.log
```

The `printf` program writes normally to standard output. The shell arranged for descriptor 1 to refer to `build.log` rather than the terminal.

This reads standard input from a file:

```bash
wc -l < README.md
```

This sends standard error to a separate file:

```bash
command_that_may_fail 2> errors.log
```

The numbers identify descriptors. They are not arbitrary decorations added by the command.

## 6. Create, truncate, and append are different operations

Output redirection with `>` creates the destination if necessary and normally truncates an existing regular file before the command runs:

```bash
printf '%s\n' "new contents" > report.txt
```

Append redirection with `>>` writes at the end instead:

```bash
printf '%s\n' "another record" >> report.txt
```

This is a meaningful state change. A harmless-looking inspection command can destroy previous file contents if its redirection is wrong.

Before pressing Enter, read a redirection as an operation performed by the shell:

```text
open destination
choose truncate or append behavior
connect descriptor
launch command
```

## 7. Duplicating descriptors

Sometimes two descriptors should refer to the same current destination.

```bash
command > combined.log 2>&1
```

Read this from left to right:

1. connect standard output to `combined.log`,
2. make standard error refer to the current standard-output destination.

Both channels now reach the file.

The order matters:

```bash
command 2>&1 > output.log
```

Here standard error first becomes a copy of the original standard output, which may still be the terminal. Standard output is then moved to the file. The two descriptors end at different destinations.

Descriptor duplication copies a connection at that moment. It does not create a permanent promise that the descriptors will follow each other through later changes.

## 8. Output is not success

Standard output, standard error, and exit status communicate different facts:

| Interface | Primary meaning |
| --- | --- |
| `stdout` | normal result data |
| `stderr` | diagnostics, warnings, or progress |
| exit status | machine-readable completion result |

A command may:

- succeed and write nothing,
- succeed while writing a warning to standard error,
- fail after producing partial standard output,
- fail silently with only a nonzero exit status,
- print the word “error” as ordinary data and succeed.

Automation must inspect the exit status rather than guessing from output text.

In a POSIX-style shell, the most recent foreground pipeline status is available through `$?`:

```bash
command_that_may_fail
status=$?
printf 'status=%s\n' "$status"
```

Capture it immediately. Running another command replaces `$?` with that command's status.

## 9. Diagnostics must not corrupt data

Imagine a program whose standard output is JSON:

```json
{"status":"healthy"}
```

If it writes a progress message into the same channel:

```text
Checking database...
{"status":"healthy"}
```

the result is no longer one valid JSON document.

A composable program sends machine-consumable results to standard output and human-oriented diagnostics to standard error. This lets a caller capture one without losing the other.

The exact choice is part of the command's interface. Some tools intentionally produce human reports rather than structured data. The requirement is clarity, not JSON everywhere.

## 10. The source or destination may be a terminal

A program can test whether a descriptor is attached to a terminal. Many tools use that information to adapt behavior:

- prompts appear only during interactive use,
- colors may be enabled for a terminal and disabled for a file,
- progress displays may update one screen line,
- output may become simpler when another program will consume it.

Terminal detection is evidence about the connection, not proof that a person is present. A pseudoterminal can be controlled by automation, and a person can read redirected output later.

Reliable automation should request a stable output format explicitly when the tool provides one rather than depending entirely on terminal detection.

## 11. Buffering changes when output becomes visible

Language runtimes and libraries often buffer output for efficiency. They may collect several writes and send them as a larger operation.

A common policy is:

- line-buffer output connected to an interactive terminal,
- use larger buffers for output connected to a file or pipe,
- keep diagnostic output less buffered.

Exact behavior depends on the language, library, program, and configuration.

This explains a common surprise: a long-running program prints updates promptly in a terminal but appears silent when its output is piped or captured. The data may still be waiting in a user-space buffer.

Do not assume the pipe itself lost the output. Identify whether buffering belongs to the application, its language library, the operating system, or the receiving program.

## 12. End of input is part of the protocol

A reader needs to know when no more input will arrive. For a regular file, reaching its end provides that signal. For a terminal, an interactive user can request end-of-input. For a pipe, end-of-file appears after all write ends are closed.

End-of-file is a condition returned by a read operation, not a byte that must be stored in the data.

This distinction matters for programs that wait forever. The reader may be correct to keep waiting because some process still has a write descriptor open.

## 13. `/dev/null` is an intentional sink and empty source

Unix-like systems commonly provide `/dev/null`, a device-like interface that:

- discards bytes written to it,
- immediately reports end-of-file when read.

Discard normal output:

```bash
command > /dev/null
```

Discard diagnostics separately:

```bash
command 2> /dev/null
```

Silencing output is not error handling. If the command matters, preserve or inspect its exit status and keep enough diagnostic evidence to understand failures.

## 14. Capture and observe with `tee`

Sometimes output should continue downstream while also being saved:

```bash
command | tee command.log
```

`tee` reads standard input and writes copies to standard output and one or more files. It acts like a junction in a data flow.

This is useful for:

- observing a pipeline stage,
- retaining build output,
- comparing intermediate data,
- creating an audit artifact.

It also changes the workflow: disk writes can fail, sensitive data may be persisted, and the pipeline now has another output to manage.

## 15. A safe observation

The following POSIX-style shell command creates one normal result, one diagnostic, and a failing status inside a child shell:

```bash
sh -c 'printf "%s\n" "result"; printf "%s\n" "diagnostic" >&2; exit 7'
```

Both lines may appear in the terminal. Redirect them separately:

```bash
sh -c 'printf "%s\n" "result"; printf "%s\n" "diagnostic" >&2; exit 7' \
  > result.log 2> diagnostic.log
status=$?
```

The files preserve the two output roles, while `status` preserves the completion result.

This experiment changes only the two named files in the current directory. Run it in a disposable practice directory if those names already matter.

## 16. Common misconceptions

### “Standard output means the screen”

It means descriptor 1 or the corresponding language stream. The connected destination may be a terminal, file, pipe, or something else.

### “Standard error means the command failed”

It is a diagnostic channel. Only the exit status communicates programmatic success or failure by convention.

### “`2>&1` sends errors to standard output forever”

It duplicates the current descriptor connection for that command at that point in the redirection sequence.

### “Redirecting output happens inside the program”

The shell normally opens and connects the destination before launching the external program.

### “No visible output means the command is stuck”

The program may be quiet by design, waiting for input, blocked, buffering output, or writing to another descriptor.

## 17. Platform comparison

| Concept | POSIX-style shells | PowerShell |
| --- | --- | --- |
| Primary pipeline output | byte or text stream for native tools | objects between PowerShell commands |
| Conventional native descriptors | 0, 1, and 2 | native processes still expose standard handles |
| Additional shell output roles | usually expressed through descriptors | success, error, warning, verbose, debug, information, and progress streams |
| Redirection ownership | shell | PowerShell engine |

PowerShell's additional streams and object pipeline solve related problems with different contracts. When PowerShell invokes a native program, translation between object-oriented shell behavior and native byte streams becomes an interoperability boundary.

The transferable question is always: which logical channel contains the data, and what is connected to it here?

## Core Computer Science Concept

Standard streams demonstrate **interface decoupling**.

```text
producer contract: write results to the normal output interface
consumer contract: read data from the normal input interface
launcher responsibility: connect the interfaces
```

The producer and consumer do not need direct knowledge of each other. Stable interfaces let the surrounding system decide how data moves.

This same pattern appears in dependency injection, network sockets, message brokers, storage abstractions, and service interfaces.

## Engineering Connections

Standard streams appear throughout professional work:

- CI systems capture output and diagnostics from build processes.
- Containers attach or collect process descriptors.
- logging agents consume application output streams.
- language runtimes expose stream objects over operating-system descriptors.
- test harnesses capture output while examining exit status.
- SSH transports a remote process's input and output.
- service managers redirect output into logs or journals.
- command-line APIs preserve machine-readable output separately from diagnostics.

A tool that respects these channels is easier to automate, test, observe, and integrate.

## From the Field

A deployment script expects a command to emit JSON and sends its standard output into a parser. A new release adds a progress message to standard output. The deployment now fails with a JSON syntax error even though the underlying operation succeeded.

The parser is not the root cause. The producer broke its stream contract by mixing diagnostics with data.

Moving the progress message to standard error restores compatibility without hiding it from an interactive user.

## Engineering Review

### What problem does this solve?

Standard streams let programs receive input, return normal results, and report diagnostics without hard-coding the connected source or destination.

### Why was it designed this way?

Stable inherited channels make programs reusable in terminals, files, pipelines, services, tests, and automation.

### When should I use it?

Use the separation whenever building or operating command-line programs, scripts, CI jobs, containers, services, or subprocess integrations.

### When should I avoid it?

Do not force complex bidirectional protocols, random-access data, durable messaging, or rich structured interactions through three simple sequential streams when a more suitable interface exists.

### How does this make me a better engineer?

It teaches you to distinguish data, diagnostics, completion status, descriptor connections, and presentation behavior.

### How does this reduce waste?

Clear stream contracts prevent parsing failures, preserve useful diagnostics, and let the same program operate in many environments without special integrations.

## Handbook Principle #8

> Separate input, results, diagnostics, and completion status so each can be connected, captured, and reasoned about independently.

## Practical Observation

In a disposable directory on macOS or Linux, run the observation from Section 15. Then inspect:

```bash
cat result.log
cat diagnostic.log
printf 'status=%s\n' "$status"
```

Repeat the command with the redirections reversed:

```bash
sh -c 'printf "%s\n" "result"; printf "%s\n" "diagnostic" >&2; exit 7' \
  2>&1 > result.log
```

Explain why the terminal and file receive different information even though the same descriptors are mentioned.

## Looking Ahead

Standard streams define the interfaces. Chapter 9 explains how the shell connects the standard output of one process to the standard input of another through a real interprocess channel: the pipe.
