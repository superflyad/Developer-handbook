# Chapter 9 — Pipes: Composing Small Tools

Chapter 8 separated a process's standard input, standard output, standard error, and exit status. A pipe lets the shell connect those interfaces between processes.

The central idea is:

> A pipe is a bounded byte-stream channel between concurrently running processes; composition works only when both sides agree on the data contract.

## 1. The problem pipes solve

Without pipes, connecting two programs often requires an intermediate file:

```text
program A → temporary file → program B
```

That can be useful when the intermediate data must be retained, inspected, reused, or processed later. It is unnecessary friction when one program can consume the data while another produces it.

A pipe creates a direct channel:

```text
program A → pipe → program B
```

The programs remain independent. They share an interface, not implementation knowledge.

## 2. What the shell does for `|`

Consider:

```bash
producer | consumer
```

A simplified sequence is:

1. the shell creates a pipe with a read end and a write end,
2. it prepares a process for `producer`,
3. it connects the producer's standard output to the pipe's write end,
4. it prepares a process for `consumer`,
5. it connects the consumer's standard input to the pipe's read end,
6. it closes unneeded descriptor copies,
7. it lets both processes run,
8. it waits according to the shell's pipeline rules.

Conceptually:

```text
producer process              consumer process
stdout descriptor             stdin descriptor
        │                            ▲
        └── write end → read end ────┘
                    pipe
```

The vertical bar is shell syntax. Neither external program needs to understand the character `|`.

## 3. A pipe is not a temporary file

A pipe is a sequential communication channel. It normally does not provide:

- a persistent pathname,
- random access,
- the ability to seek backward,
- durable storage after the processes finish,
- an unlimited buffer.

Data is read in the order it is written. Once consumed, it is no longer available from that pipe.

Use a regular file when persistence, replay, independent timing, random access, or post-failure inspection matters. Use a pipe when streaming connection and low coordination overhead matter.

## 4. Pipeline stages run concurrently

A pipeline is not normally executed as “finish the first program, then start the second.” Its stages run as separate, overlapping process work.

```text
time ──────────────────────────────────────→
producer:  write write wait write ... exit
consumer:       read work read work ... exit
```

This has important consequences:

- the consumer can begin before the producer finishes,
- a slow consumer can delay the producer,
- several stages can use CPU at the same time,
- failures can occur in more than one process,
- observed output timing may differ from a file-based workflow.

Concurrency is part of the mechanism, even when the pipeline is typed as one line.

## 5. Pipes have bounded capacity

The operating system buffers a limited amount of pipe data. The exact capacity is implementation-dependent and should not be treated as an application contract.

When the pipe is empty, a blocking reader waits for data or end-of-file. When the pipe is full, a blocking writer waits for space.

```text
fast producer → [ bounded pipe buffer ] → slow consumer
                     fills up
fast producer eventually waits
```

This feedback is **backpressure**. It prevents an ordinary pipeline from requiring enough memory to hold the producer's entire output.

Backpressure is useful, but it also explains apparent hangs. A process may be blocked because the next stage stopped reading, not because the process itself is defective.

## 6. A pipe carries bytes, not records

The operating system pipe provides an ordered byte stream. It does not inherently understand:

- lines,
- words,
- CSV rows,
- JSON objects,
- log records,
- filenames.

Programs impose structure through an agreed format and delimiter.

Many Unix tools use newline-delimited text because it is readable and widely interoperable:

```text
alpha\n
beta\n
gamma\n
```

That convention is powerful but not universal. A filename can legally contain a newline on Unix-like filesystems, binary data may contain any byte, and pretty-printed JSON can span several lines.

Composition is reliable only when the producer's output contract matches the consumer's input contract.

## 7. A first practical pipeline

This POSIX-style example counts repeated whole-line values:

```bash
printf '%s\n' api web api worker web api |
  sort |
  uniq -c |
  sort -nr
```

Each stage has one responsibility:

```text
printf  → emit records
sort    → place equal records next to each other
uniq -c → count adjacent equal records
sort -nr → order counts numerically, largest first
```

The `uniq` stage is a useful lesson in contracts: it combines only adjacent duplicate lines. The preceding `sort` is not cosmetic; it establishes the precondition `uniq` needs.

## 8. Standard error is not piped by default

In a conventional shell pipeline:

```bash
producer | consumer
```

only the producer's standard output is connected to the consumer's standard input. The producer's standard error normally remains connected to its previous destination, often the terminal.

This preserves diagnostics without injecting them into the data stream.

To combine both channels deliberately in Bash or zsh:

```bash
producer 2>&1 | consumer
```

This may be appropriate for searching or saving a combined human-readable transcript. It is dangerous when `consumer` expects a strict data format because diagnostics can corrupt the stream.

## 9. Redirection and pipe ordering

The shell establishes a pipeline connection and then applies a command's explicit redirections according to its language rules.

```bash
producer > saved.txt | consumer
```

Here the producer's explicit standard-output redirection replaces its pipe connection. The producer writes to `saved.txt`, while the consumer normally receives end-of-file without that data.

To save data while continuing to pass it downstream, use a program designed to duplicate the stream:

```bash
producer | tee saved.txt | consumer
```

Read the complete descriptor graph rather than assuming the presence of `|` guarantees a connection.

## 10. End-of-file depends on closing writers

A reader sees end-of-file only after every descriptor referring to the pipe's write end has been closed.

An accidentally inherited or forgotten write descriptor can keep a consumer waiting even after the intended producer exits.

This is why shells and systems programs close unused pipe ends. Resource lifetime is part of the communication protocol.

At the command-line level, the shell normally manages this correctly. The model becomes valuable when debugging custom subprocess code or a pipeline that never terminates.

## 11. When the reader exits early

Some consumers intentionally stop before reading all input:

```bash
producer | head -n 10
```

After `head` has ten lines, it can exit. If the producer continues writing after no read end remains, the operating system reports a broken pipe, commonly through `SIGPIPE` or an `EPIPE` error.

This can be normal control flow rather than an application defect: the consumer obtained everything it requested.

Failure-handling policy must understand the pipeline's intent. Treating every upstream broken-pipe status as a production incident can create false alarms.

## 12. Which status represents the pipeline?

Several processes can return different exit statuses. A shell still needs one status for the pipeline as a whole.

Without `pipefail`, POSIX-style shells normally derive the pipeline status from the last command:

```bash
failing_producer | successful_consumer
```

The pipeline may appear successful because the consumer exited successfully.

Bash and zsh provide a `pipefail` option, and POSIX.1-2024 also specifies it:

```bash
set -o pipefail
```

With it enabled, a failure in an earlier stage can make the pipeline fail. Exact status selection and access to individual stage statuses remain shell-specific details that shared scripts should qualify.

`pipefail` improves visibility, but it is not complete error handling. A pipeline can still produce partial output, a tool can return zero despite semantically wrong data, and an expected `SIGPIPE` can look like an upstream failure.

## 13. Data correctness is larger than exit status

A successful status says that a program believes it completed according to its contract. It does not prove that:

- the input was the intended dataset,
- the selected fields had the expected meaning,
- locale rules produced the intended ordering,
- every record was valid,
- partial output was not consumed before a later failure,
- the pipeline answered the business question correctly.

Robust workflows validate assumptions at boundaries.

For example, before treating a column as an HTTP status code, verify the log format rather than relying on one sample line.

## 14. Filenames are not ordinary lines

This is unsafe for arbitrary filenames:

```bash
find . -type f | while read -r path; do
  printf '%s\n' "$path"
done
```

Newlines can occur inside Unix filenames, so a newline-delimited path stream can be ambiguous.

GNU and BSD/macOS tools commonly support null-delimited extensions:

```bash
find . -type f -print0 | xargs -0 command
```

The null byte cannot occur inside a Unix pathname, making it an unambiguous separator. These options are widely available but are not part of every historical or minimal toolset, so portability requirements still matter.

When possible, avoid serializing filenames at all. `find -exec` can pass discovered paths directly as arguments:

```bash
find . -type f -name '*.md' -exec wc -l {} +
```

## 15. Arguments and standard input are different interfaces

A pipeline sends bytes to standard input. It does not automatically turn lines into filename arguments.

This command searches the text of filenames emitted by `find`:

```bash
find . -name '*.log' | grep 'ERROR'
```

It does not open those paths and search the log contents.

To give files to `grep`, pass them as arguments:

```bash
find . -type f -name '*.log' -exec grep -h 'ERROR' {} +
```

Always ask what the receiving program expects:

```text
bytes on standard input?
pathnames as command arguments?
configuration in the environment?
```

These interfaces are not interchangeable.

## 16. Text is a contract, not magic

Text works well when it is:

- encoded consistently,
- delimited unambiguously,
- stable enough for consumers,
- explicit about escaping,
- precise about missing and malformed values.

Whitespace-oriented parsing becomes fragile when fields can contain whitespace. Ad hoc comma splitting fails when CSV quoting matters. Human-formatted tables change when widths, colors, or headings change.

Prefer a tool's documented machine-readable format when correctness matters. JSON, CSV, and null-delimited records are useful only when both sides implement the format correctly.

Binary and structured formats are not violations of Unix design. The important property is a documented, composable interface.

## 17. Locale can change a pipeline

Text tools may use locale settings for:

- character classification,
- collation and sort order,
- case conversion,
- regular-expression behavior,
- diagnostic language.

Two machines can run the same text pipeline and order records differently.

When byte-oriented deterministic behavior is required, a workflow may set a locale deliberately:

```bash
LC_ALL=C sort input.txt
```

That choice changes semantics and should be documented. It is not a universal performance switch to apply without understanding the data.

Chapter 10 explains how locale reaches a process through its environment.

## 18. Pipeline state and subshells

Pipeline stages commonly execute in separate process or subshell environments. A variable changed inside a stage may not modify the parent interactive shell.

Portable scripts should not depend on a pipeline loop mutating parent-shell state:

```bash
count=0
producer | while read -r line; do
  count=$((count + 1))
done
```

The value of `count` after the pipeline can vary with shell execution rules and options. Prefer a design that returns the computed result explicitly through output or a deliberately managed file.

This is the process-inheritance model from Chapters 4 and 5 appearing inside a compact command line.

## 19. Debug one stage at a time

A pipeline is a small program. Debug it like one.

Useful techniques include:

1. begin with a small known input,
2. run the first stage and inspect its exact output,
3. add one stage at a time,
4. use `tee` to capture an intermediate stream,
5. preserve standard error,
6. inspect exit statuses,
7. test empty, malformed, and unusually large input,
8. confirm locale and shell assumptions.

For example:

```bash
producer |
  tee stage-1.txt |
  transformer |
  tee stage-2.txt |
  consumer
```

Do not leave diagnostic captures containing secrets or sensitive data after the investigation.

## 20. When not to use a pipe

Prefer another interface when the workflow needs:

- durable delivery,
- retries with acknowledgment,
- transactions,
- random access,
- multiple independent consumers,
- rich bidirectional interaction,
- strict schemas and version negotiation,
- data larger or more complex than the tools can safely parse,
- long-lived service coordination.

Files, databases, queues, sockets, APIs, and workflow engines solve different problems. Pipes are powerful because their contract is small, not because they replace every communication mechanism.

## 21. Platform comparison

| Property | Unix native pipeline | PowerShell pipeline |
| --- | --- | --- |
| Normal payload | byte stream interpreted by programs | .NET objects between PowerShell commands |
| Typical structure | line-oriented text convention | typed properties and methods |
| Native process boundary | standard input and output descriptors | conversion to or from native streams |
| Common strength | broad interoperability among small tools | property-aware administration and transformation |

PowerShell pipelines preserve structure between PowerShell commands, reducing some text-parsing problems. Native executables still communicate through standard byte streams, so a mixed pipeline crosses a representation boundary.

The engineering principle is broader than either shell: composition requires stable interfaces and compatible contracts.

## Core Computer Science Concept

A pipe combines **interprocess communication**, **streaming**, and **backpressure**.

```text
independent process
      ↓ stable output contract
bounded communication channel
      ↓ stable input contract
independent process
```

The bounded channel couples throughput without coupling implementation. The consumer controls how quickly space becomes available; the producer can remain unaware of the consumer's internal logic.

The same broad pattern appears in network streams, reactive systems, iterators, message processing, and dataflow architectures, though their delivery guarantees differ.

## Engineering Connections

Pipe reasoning transfers directly to:

- subprocess management in application code,
- CI job logs and command chains,
- container entrypoints,
- streaming HTTP bodies,
- log processors,
- build systems,
- extract-transform-load workflows,
- backpressure in distributed systems,
- producer-consumer queues,
- observability pipelines.

The local pipe is a compact laboratory for reasoning about contracts, buffering, concurrency, failure, and flow control.

## From the Field

A test runner produces thousands of lines on both standard output and standard error. A parent program captures both streams but waits for the child to exit before reading either one.

One pipe buffer fills. The child blocks while trying to write. The parent keeps waiting for the child. Neither can progress.

The bug is not “subprocesses are unreliable.” It is a flow-control deadlock caused by bounded buffers and an incorrect consumption strategy.

Subprocess libraries commonly provide a communication method that drains both streams while waiting. Understanding the pipe model explains why that method exists.

## Engineering Review

### What problem does this solve?

Pipes let independently implemented processes exchange sequential data without intermediate persistent storage or direct knowledge of each other.

### Why was it designed this way?

A small read/write interface makes composition cheap while the operating system handles buffering, blocking, descriptor inheritance, and process isolation.

### When should I use it?

Use pipes for bounded streaming workflows whose stages share a clear sequential-data contract.

### When should I avoid it?

Avoid pipes when the workflow requires persistence, transactions, acknowledgments, random access, rich schemas, independent consumers, or complex bidirectional coordination.

### How does this make me a better engineer?

It trains you to reason about process boundaries, data contracts, concurrency, backpressure, failure propagation, and representation.

### How does this reduce waste?

Well-designed pipelines reuse proven tools and avoid intermediate plumbing, while explicit contracts and staged debugging prevent fragile automation.

## Handbook Principle #9

> A pipeline is a concurrent system: compose contracts, preserve failure signals, and respect the bounded stream between processes.

## Practical Observation

Run the counting pipeline from Section 7 one stage at a time. After each stage, describe the exact record contract it produces.

Then run:

```bash
printf '%s\n' api web api worker web api |
  sort |
  tee sorted.txt |
  uniq -c |
  sort -nr
```

Confirm that `tee` preserves the downstream result while recording the intermediate sorted stream. Explain why removing `sort` changes the meaning of `uniq -c`.

## Looking Ahead

Pipes carry data between process interfaces. Chapter 10 examines a different inherited interface: the environment, which supplies named configuration values when a process starts.
