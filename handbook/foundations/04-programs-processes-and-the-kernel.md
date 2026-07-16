# Lesson 4 — Programs, Processes, and the Kernel

So far, the handbook has established three ideas:

- Unix favors small, composable tools.
- The operating system manages resources.
- The filesystem organizes those resources into a predictable tree.

This chapter explains what actually happens when software runs.

> A program is static code on disk. A process is that program in motion.

## 1. Program vs. process

A **program** is a file containing executable instructions. A **process** is a running instance of that program.

```text
program + execution state = process
```

Execution state includes:

- memory,
- open files,
- environment variables,
- current working directory,
- process identifier,
- user identity,
- input and output channels,
- CPU execution state.

A program is passive. A process is active.

## 2. One program can create many processes

Running three Python scripts may create three independent Python processes:

```text
python3 script_a.py
python3 script_b.py
python3 script_c.py
```

They use the same Python executable, but each process has its own memory, variables, files, working directory, and lifecycle.

This isolation is why one process can fail without automatically destroying the others.

## 3. Why processes exist

Processes give the operating system a manageable unit of execution.

### Isolation

One process cannot normally read or overwrite another process's memory.

### Resource tracking

The operating system can measure CPU, memory, files, and network usage per process.

### Security

Each process runs under a user identity and permission boundary.

### Scheduling

The operating system decides when and where each process receives CPU time.

### Failure containment

A crash can often be contained to one process.

This mirrors good production architecture: isolation reduces blast radius.

## 4. The kernel manages processes

Applications do not directly control the machine. They request services from the kernel.

A simplified process start looks like this:

```text
Shell
  ↓
Requests a new process
  ↓
Kernel creates process state
  ↓
Kernel loads the program
  ↓
Process begins running
```

The kernel assigns a process identifier, memory space, security context, access to resources, and scheduling time.

## 5. Process identifiers

Every process receives a numeric **process identifier**, or PID.

```text
PID 4127
```

A PID lets the operating system and its tools refer to one specific process for inspection, tracing, measurement, or termination.

A PID is temporary. After the process exits, the number may eventually be reused.

## 6. Parent and child processes

Processes form a hierarchy.

```text
Terminal
└── zsh
    └── git
        └── helper process
```

The process that starts another process is the **parent**. The newly created process is the **child**.

A child commonly inherits parts of its parent's state, including:

- environment variables,
- current working directory,
- user identity,
- standard input, output, and error channels,
- selected open resources.

This explains why the same command can behave differently when launched from different shells, IDEs, services, or CI environments.

## 7. Inheritance is not shared ownership

A child process may inherit an environment variable such as:

```text
API_URL=https://example.com
```

The child usually receives its own environment. Changing the variable inside the child does not rewrite the parent's environment.

This principle matters later when studying shell configuration, `export`, subshells, virtual environments, Docker, and CI pipelines.

## 8. The current working directory belongs to the process

Every process has a current working directory. Relative paths are resolved from that location.

```text
config/settings.json
```

This does not identify one universal file. It means:

> Begin at this process's current working directory, then follow `config/settings.json`.

A program may work in your terminal but fail in an IDE, container, scheduled task, CI runner, or production service because the working directory differs.

This is a common source of avoidable bugs.

## 9. Processes hold open resources

A running process may hold:

- files,
- pipes,
- sockets,
- database connections,
- terminal handles,
- network ports.

These resources are often represented through file descriptors or platform-specific handles.

A process interacts with an open resource, not merely with the visible filename. That is why a deleted log file can continue consuming disk space until the process closes it.

## 10. Process lifecycle

A simplified process lifecycle is:

```text
created
  ↓
ready
  ↓
running
  ↓
waiting
  ↓
running
  ↓
terminated
```

### Created

The operating system is building the process.

### Ready

The process can run but is waiting for CPU time.

### Running

A CPU is executing its instructions.

### Waiting or blocked

The process is waiting for an event such as disk input, network data, user input, a lock, or another process.

### Terminated

The process has completed or been stopped.

A process can exist while using little or no CPU because it may be waiting.

## 11. CPU scheduling

A computer may have hundreds of processes but far fewer CPU cores. The kernel scheduler decides which runnable process receives CPU time.

```text
Process A runs
Process B waits
Process C runs
Process A resumes
```

Two related concepts must remain distinct:

- **Concurrency** means multiple tasks are in progress.
- **Parallelism** means multiple tasks execute at the same instant.

Your Mac can perform true parallel work across cores, but the scheduler still coordinates execution.

## 12. User space and kernel space

Normal applications run in **user space**. The operating system kernel runs in **kernel space** with elevated privileges.

User-space examples include Git, Python, VS Code, browsers, and application services.

The kernel can manage hardware, memory, processes, filesystems, permissions, and networking.

A user-space process must request privileged operations from the kernel rather than accessing hardware arbitrarily.

## 13. System calls

A system call is a controlled request from a process to the kernel.

Common requests include:

- opening a file,
- reading or writing data,
- allocating memory,
- creating a process,
- opening a network connection,
- sleeping,
- terminating.

```text
Application
  ↓
System call
  ↓
Kernel validates request
  ↓
Kernel performs operation
  ↓
Result returns to application
```

This boundary protects system stability and security.

## 14. What happens when you run a command

Suppose you enter:

```bash
python3 app.py
```

A simplified sequence is:

1. The terminal sends text to the shell.
2. The shell parses the command.
3. The shell searches for `python3`.
4. The shell asks the kernel to create a process.
5. The kernel establishes the process state.
6. Python is loaded into memory.
7. The child inherits the shell's working directory and environment.
8. Python opens `app.py`.
9. Python executes the script.
10. The process writes output.
11. The process exits with a status code.
12. The shell resumes control.

One command crosses several layers of the operating system.

## 15. Exit codes

When a process ends, it returns an exit status.

By convention:

```text
0 = success
nonzero = failure or exceptional result
```

This is essential for automation.

```text
tests pass → exit 0
tests fail → exit 1
```

A process does not only print text for humans. It also reports a machine-readable result.

## 16. Why applications freeze

A frozen application is not necessarily consuming too much CPU. It may be:

- waiting on disk,
- waiting for network data,
- blocked on a lock,
- deadlocked,
- stuck in an infinite loop,
- starved of resources,
- waiting for another process.

A better debugging question is not:

> Why is the app frozen?

It is:

> What is this process waiting on?

That question leads to evidence instead of guessing.

## 17. Engineering connections

This process model appears throughout professional software engineering.

### Docker

A container primarily isolates processes using kernel features. It is not simply a lightweight virtual machine.

### Web servers

Servers use processes, threads, or asynchronous execution to handle concurrent work.

### CI/CD

Build steps launch processes and use exit codes to determine success or failure.

### AWS and cloud platforms

EC2 instances run operating-system processes. ECS tasks and Kubernetes pods ultimately run containerized processes.

### Databases

A database server is a long-running process managing memory, files, locks, and network connections.

### IDEs

Editors launch compilers, language servers, test runners, and debuggers as child processes. The graphical interface hides the tree but does not remove it.

## Platform comparison

| Concept | Windows | macOS | Linux |
|---|---|---|---|
| Process identifier | PID | PID | PID |
| Kernel | NT | XNU | Linux |
| Graphical viewer | Task Manager | Activity Monitor | Desktop system monitor varies |
| Service manager | Windows Services | `launchd` | Commonly `systemd` |
| Executable format | PE | Mach-O | ELF |

The implementation differs, but the transferable model remains the same: running software is represented as processes managed by the operating system.

## Common misconceptions

### “The program is running”

More precisely, one or more processes created from that program are running.

### “My application owns the CPU”

It does not. The scheduler grants it execution time.

### “A process is just memory”

Memory is only one part of process state.

### “Low CPU means healthy”

A process may be blocked, deadlocked, or waiting forever.

### “Docker replaces the operating system”

Containers depend on the host kernel's process isolation mechanisms.

## From the field

A service works locally but fails in production with:

```text
FileNotFoundError: config/settings.json
```

The file exists, but the production process starts from a different working directory.

The bug is not primarily about the file. It is about process state.

Recognizing that distinction prevents hours of random debugging.

## Engineering review

### What problem does this solve?

Processes give the operating system an isolated unit for executing programs and tracking resources.

### Why was it designed this way?

Separating running programs into processes improves security, scheduling, resource control, and failure containment.

### When should I use it?

Use this model whenever you run, debug, deploy, monitor, or automate software.

### When should I avoid it?

Do not use **process** as a vague synonym for all running work. Threads, coroutines, containers, and services are related but distinct abstractions.

### How does this make me a better engineer?

It gives you a concrete model for execution, inheritance, isolation, failures, and resource use.

### How does this reduce waste?

It turns debugging into a sequence of questions: Which process exists? What state did it inherit? What is it waiting on? Which resources does it hold? How did it terminate?

## Handbook principle #4

> A program is code. A process is code plus identity, state, resources, and a lifecycle managed by the kernel.

## Practical observation

Open several applications on macOS and inspect Activity Monitor. Notice that one visible application may correspond to several processes.

The interface shows applications. The operating system manages the process tree underneath.