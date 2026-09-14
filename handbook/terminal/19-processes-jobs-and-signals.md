# Chapter 19 — Processes, Jobs, and Signals

Chapter 4 introduced processes as running program instances. Interactive shells add a job-control layer that groups processes and coordinates their relationship with a terminal.

The central idea is:

> Observe identity and state before intervening, control the smallest correct process group, and escalate signals only when graceful cooperation fails.

## 1. A command can create more than one process

A simple external command often creates one child process. A pipeline can create several:

```bash
producer | transform | consumer
```

The interactive shell commonly places those related processes into a process group representing one job. Job control lets the shell foreground, background, stop, continue, or signal that group as a unit.

```text
shell session
├── shell process
└── foreground job / process group
    ├── producer
    ├── transform
    └── consumer
```

Process and job are therefore not synonyms.

## 2. PID, PGID, session, and job ID identify different scopes

- A **process ID** identifies one process at a point in time.
- A **process-group ID** identifies a group used for signaling and job control.
- A **session** contains related process groups and may own a controlling terminal.
- A shell **job ID**, written like `%1`, identifies an entry in that shell's job table.

Job IDs are local to one shell. Another terminal cannot generally use `%1` to refer to the first shell's job.

PIDs are eventually reused. A stale PID stored for too long may later identify an unrelated process.

## 3. Inspect before acting

Useful observations include:

```bash
ps
ps -ef                 # common portable-style request
ps -o pid,ppid,pgid,stat,tty,command -p "$$"
```

`ps` supports several syntax traditions, and accepted columns vary. Check the local manual before embedding a display format in automation.

Interactive monitors such as `top` provide changing system views. They are valuable for exploration but should not replace a recorded metric or reproducible diagnostic query.

## 4. Foreground means terminal control

A terminal has one foreground process group at a time. Terminal-generated signals are delivered to that foreground group.

Typically:

- `Ctrl-C` requests interruption with `SIGINT`,
- `Ctrl-Z` requests stopping with `SIGTSTP`,
- terminal input is available to the foreground group.

These key combinations are interpreted through terminal settings; they are not bytes necessarily delivered to the application as ordinary input.

A background process that tries to read from its controlling terminal may be stopped. Backgrounding does not make an interactive program noninteractive.

## 5. `&` starts an asynchronous job

In an interactive Bash shell:

```bash
long_running_command &
```

The shell returns a prompt without waiting for normal completion. The process may still inherit the terminal's output and error connections, so its messages can appear over later prompts.

Capture outputs deliberately:

```bash
long_running_command > run.log 2> run.err &
```

The shell can report a job number and the PID of the last process in the asynchronous job. `$!` exposes the most recently started background job's process identifier in Bash.

## 6. Jobs are shell-managed state

Inspect the current shell's jobs:

```bash
jobs
jobs -l
```

Bring a job to the foreground:

```bash
fg %1
```

Continue a stopped job in the background:

```bash
bg %1
```

Job specifications are convenient for interactive control. Automation should use explicit process-management APIs or carefully captured identifiers rather than assuming a shell job table persists.

## 7. Stopped, running, and terminated are different states

A stopped process still exists but is not scheduled to execute until continued. A terminated process has finished execution.

```text
running --SIGTSTP--> stopped --SIGCONT--> running
running --exit/signal--> terminated
```

Suspending a process does not release all resources. It can retain memory, open files, locks, sockets, and temporary state.

Use stopping for short-lived interactive control, not as a substitute for application-aware pause, checkpointing, or service management.

## 8. Signals are asynchronous notifications

A signal communicates an event to a process or process group. The target may:

- take the default action,
- ignore some signals,
- block delivery temporarily,
- or install a handler for catchable signals.

Signal names communicate intent more clearly than numbers:

```bash
kill -TERM "$pid"
kill -INT "$pid"
kill -HUP "$pid"
```

Meanings beyond the operating-system default can be application-specific. `SIGHUP` may request reload in one service and termination in another. Read the application's documentation.

## 9. `kill` sends a signal

Despite its name, `kill` is a signaling interface. With no signal specified, it normally sends `SIGTERM`:

```bash
kill "$pid"
```

`SIGTERM` asks a process to terminate and allows a handler to clean up. `SIGKILL` cannot be caught or ignored:

```bash
kill -KILL "$pid"
```

Use `SIGKILL` only after confirming identity, allowing a reasonable graceful period, and understanding the risk of partial writes, abandoned locks, incomplete child cleanup, or corrupted external workflows.

## 10. Signal the scope you intend

Sending a signal to one pipeline process may leave siblings running. Job control normally targets the process group.

In an interactive Bash shell:

```bash
kill -TERM %1
```

At lower-level interfaces, negative PID conventions can identify process groups, but command syntax is easy to confuse with signal options. Use documented, explicit forms and an option terminator where required.

Never use broad name-based termination as a first diagnostic step. Similar names, multiple users, containers, and reused processes make selection ambiguous.

## 11. Wait for completion and preserve status

Starting work in the background transfers responsibility for observing completion:

```bash
worker &
pid=$!

wait "$pid"
status=$?
printf 'worker status=%s\n' "$status"
```

`wait` lets the shell collect a child's termination status. Without an appropriate parent wait, a terminated child can remain briefly as a zombie: execution is over, but bookkeeping remains until collected.

Concurrency is not “free speed.” It introduces lifecycle, output, status, ordering, and cancellation responsibilities.

## 12. Shell exit and terminal loss are lifecycle events

Closing a terminal can produce hangup behavior for attached jobs. Bash options, job state, `nohup`, and `disown` influence what happens, but they do not create a supervised production service.

`nohup` commonly adjusts hangup handling and redirects terminal output when needed:

```bash
nohup long_running_command > run.log 2>&1 &
```

For durable work, prefer a service manager, scheduler, terminal multiplexer, CI system, or workload orchestrator with explicit restart, logging, ownership, and health semantics.

## 13. Process discovery has races

This sequence is inherently time-sensitive:

```text
inspect PID → decide → signal PID
```

The process can exit between steps, and the identifier may eventually be reused. Modern operating systems and supervisors offer stronger handles or lifecycle ownership, but a casual shell sequence often does not.

Reduce risk by acting promptly, checking user and command context, preferring shell job IDs for current interactive work, and using the supervisor that launched production work.

## 14. Diagnose an apparently stuck command

Before terminating it, ask:

1. Is it waiting for input?
2. Is output redirected or buffered?
3. Is it blocked on a file, network, lock, or child process?
4. Is it stopped rather than running?
5. Is it doing valid CPU- or I/O-intensive work?
6. Which process group and parent own it?
7. What cleanup guarantee does the application provide?

Observation tools can include `ps`, logs, open-file inspection, system-call tracing, and supervisor status. Later parts develop these debugging techniques more deeply.

## 15. Common misconceptions

### “A job is one process”

A shell job may contain an entire pipeline process group.

### “Background means detached”

A background job can still belong to the terminal session and inherit its streams.

### “`Ctrl-C` types a character into the program”

Terminal handling normally converts it into a signal for the foreground process group.

### “`kill -9` is the reliable first choice”

It prevents application cleanup and can increase operational damage.

### “A PID permanently identifies one program”

PIDs are scoped to a running system or namespace and are reused.

## 16. Platform comparison

| Concern | Linux/macOS with Bash | PowerShell on Windows |
| --- | --- | --- |
| Interactive job table | Bash job control | PowerShell jobs are a distinct abstraction |
| Process inspection | `ps`, `top` and platform tools | `Get-Process`, Task Manager |
| Graceful request | POSIX signals and app protocols | console events, service controls, app protocols |
| Force termination | `SIGKILL` where available | forceful process termination APIs |
| Durable lifecycle | service manager or orchestrator | Windows services, Task Scheduler, orchestrators |

Process control concepts transfer, but signal sets and terminal semantics do not map one-to-one.

## Core Computer Science Concept

Job control combines **process groups, sessions, and asynchronous events** to coordinate concurrent processes through a terminal.

This is a small instance of lifecycle orchestration: identify a unit of work, observe its state, send control events, and collect completion.

## Engineering Connections

- Service managers own process groups and restart policy.
- Containers need a correct PID 1 that forwards signals and reaps children.
- CI cancellation depends on terminating process trees, not only one PID.
- Graceful shutdown allows servers to drain requests and flush state.
- Distributed job systems generalize waiting, cancellation, retry, and status collection.

## From the Field

A CI timeout kills only the shell process that launched a test runner. Worker descendants continue holding ports and consuming CPU, interfering with the next job.

The fix is lifecycle ownership at the correct scope: the runner or supervisor must terminate and reap the whole process group or container workload.

## Engineering Review

### What problem does this solve?

It provides safe interactive control over concurrent processes and related pipeline jobs.

### Why was it designed this way?

Process groups let the terminal and shell control related processes as one foreground or background unit.

### When should I use it?

Use job control for interactive work and signals for documented lifecycle requests to precisely identified processes or groups.

### When should I avoid it?

Avoid ad hoc background jobs for durable production services and avoid forceful signals before graceful application-aware control.

### How does this make me a better engineer?

It teaches lifecycle ownership, asynchronous control, scope selection, and graceful escalation.

### How does this reduce waste?

Correct process-group control prevents orphaned work, lost statuses, corrupted cleanup, and repeated terminal sessions.

## Handbook Principle #19

> Observe the process relationship, control the smallest correct group, request graceful shutdown first, and keep responsibility for completion.

## Practical Observation

In an interactive Bash shell, run:

```bash
sleep 120 &
jobs -l
fg %1
```

Press `Ctrl-Z`, then inspect `jobs -l`. Continue it with:

```bash
bg %1
kill -TERM %1
wait %1
printf 'status=%s\n' "$?"
```

Record the job ID, PID, state transitions, signal target, and final status. Do not substitute `SIGKILL`; graceful termination is part of the observation.

## Looking Ahead

Process control depends on authority. Chapter 20 applies Unix ownership, modes, groups, and privilege boundaries to daily filesystem work and access failures.
