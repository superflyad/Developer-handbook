# Lesson 2 — The Unix Mental Model

Lesson 1 described how Unix developers compose tools. This lesson explains the operating-system model underneath those tools.

The central idea is:

> An operating system is a resource manager. Programs request access to resources; the kernel controls and coordinates that access.

## 1. The major layers

A useful simplified model is:

```text
User
  ↓
Terminal application
  ↓
Shell
  ↓
Programs and libraries
  ↓
Kernel
  ↓
CPU, memory, storage, network, and devices
```

These layers are related, but they are not interchangeable.

- The **terminal** displays text and carries keyboard input.
- The **shell** interprets command language and launches programs.
- A **program** is executable code stored on disk.
- A **process** is a running instance of a program.
- The **kernel** manages hardware and enforces system rules.

Confusing these layers makes errors feel mysterious. Separating them gives you places to investigate.

## 2. Files and directories

A file is a named sequence of data exposed through the filesystem. Source code, configuration, logs, executables, and many other forms of state are represented as files.

A directory is not merely a visual folder. Conceptually, it maps names to filesystem objects. Directories create a hierarchical namespace so humans and programs can locate resources predictably.

Unix-like systems expose one filesystem tree rooted at:

```text
/
```

Typical macOS paths include:

```text
/Users/michael
/Applications
/System
/Library
/tmp
```

Windows traditionally exposes multiple roots through drive letters:

```text
C:\
D:\
```

Linux and macOS instead attach storage devices and remote filesystems at locations inside the single tree. This operation is called mounting.

## 3. Programs and processes

A program on disk is passive. When the operating system loads and executes it, the program becomes a process.

```text
program file + execution context = process
```

A process has resources and identity, including:

- a process identifier,
- memory,
- open files,
- environment variables,
- a current working directory,
- credentials,
- input and output channels,
- execution state.

Multiple processes can run the same program simultaneously while maintaining separate execution state.

This distinction matters in real work. Installing Python places a program on disk. Running three Python scripts may create three separate Python processes.

## 4. Parent and child processes

Processes form relationships. When your shell launches `git`, the shell is the parent and the Git process is its child.

```text
Terminal
└── zsh
    └── git
```

A child commonly inherits parts of its parent's environment, current directory, credentials, and open channels. This is why setting an environment variable in a shell can affect commands launched from that shell.

The child cannot normally change the parent's environment after it has started. That detail explains several shell behaviors we will encounter later.

## 5. Users, groups, and permissions

Unix was designed as a multi-user system. Even a personal laptop preserves that model.

Every process runs under an identity. Files and directories have ownership and permissions. The operating system uses these facts to decide whether an operation is allowed.

The basic permission questions are:

- Who owns this resource?
- Which group is associated with it?
- May the requesting identity read it?
- May it write it?
- May it execute or traverse it?

This model limits accidental damage and isolates users and services from each other.

Using administrative privileges for routine work defeats that protection. `sudo` should be treated as a deliberate privilege boundary, not as a universal error-fixing prefix.

## 6. Memory

Processes request memory from the operating system. The kernel and hardware cooperate to provide each process with a protected virtual address space.

A process usually behaves as though it owns a large private range of memory even though physical RAM is shared among many processes.

This abstraction provides:

- isolation,
- simpler application design,
- controlled sharing,
- virtual memory,
- more flexible use of physical RAM.

Your 48 GB MacBook Pro can run many processes because the operating system schedules CPU time and manages memory across them. High memory capacity does not remove the need to understand leaks, pressure, caching, or process behavior; it merely raises the point at which poor behavior becomes visible.

## 7. Devices and file-like interfaces

Unix is often summarized as “everything is a file.” Taken literally, that is inaccurate. The useful principle is that many resources expose file-like operations or appear in the filesystem namespace.

A process can often interact with resources using familiar operations such as open, read, write, and close. The resource might represent:

- a regular file,
- a terminal,
- a pipe,
- a socket,
- a device,
- a virtual kernel interface.

A uniform interface reduces the number of concepts programs must learn.

macOS and Linux differ in the exact virtual filesystems and device interfaces they expose. For example, Linux heavily uses `/proc` for process and kernel information, while macOS does not provide the same Linux-style `/proc` hierarchy by default.

## 8. The shell

The shell is a user-space program that interprets command language.

On current macOS installations, the default interactive shell is typically `zsh`. Common alternatives include `bash`, `sh`, and `fish`.

The shell performs work such as:

1. reading your command,
2. parsing shell syntax,
3. expanding variables and wildcard expressions,
4. resolving command names,
5. configuring redirection and pipelines,
6. asking the kernel to start processes,
7. waiting for or managing those processes,
8. reporting completion status.

The shell is powerful because it is both an interactive interface and a programming environment.

## 9. The kernel and system calls

Normal applications do not directly control hardware. They request privileged operations from the kernel through system calls.

Examples include requests to:

- open a file,
- allocate memory,
- create a process,
- send network data,
- read keyboard input,
- obtain the current time.

The kernel validates the request, checks permissions, coordinates hardware, and returns a result.

This boundary provides stability and security. A faulty application should not be able to overwrite arbitrary disk sectors or read another process's memory merely because it wants to.

## 10. What happens during `git status`

Suppose you enter:

```bash
git status
```

A simplified sequence is:

1. The terminal sends your keystrokes to the shell.
2. The shell parses `git` as the command and `status` as an argument.
3. The shell searches its command path for the Git executable.
4. The shell asks the kernel to create a process.
5. Git starts with inherited environment, working directory, credentials, and I/O channels.
6. Git reads repository metadata and working-tree files.
7. Git writes normal output to standard output and diagnostics to standard error.
8. Git exits with a numeric status code.
9. The shell receives the completion status and presents another prompt.

This model gives you a debugging map. A failure could come from shell parsing, path resolution, permissions, the current directory, missing files, Git itself, or the underlying filesystem.

## 11. Platform comparison

| Concept | Windows | macOS | Linux |
|---|---|---|---|
| Kernel family | Windows NT | XNU | Linux |
| Common interactive shell | PowerShell | zsh | Often Bash; distribution-dependent |
| Filesystem roots | Drive letters and mounted volumes | One `/` tree | One `/` tree |
| User model | Users, groups, ACLs, access tokens | Unix users/groups plus ACLs and platform security layers | Unix users/groups plus capabilities, ACLs, and distribution security layers |
| Primary server presence | Significant, especially Microsoft ecosystems | Uncommon as a general-purpose server OS | Dominant in cloud, containers, and infrastructure |

PowerShell is not merely a Windows imitation of a Unix shell. It passes structured .NET objects through pipelines rather than treating text streams as the primary interchange format. That offers major advantages for Windows administration, though it creates different composition rules from traditional Unix tools.

## 12. Connection to modern engineering

This mental model reappears everywhere:

- A Docker container is primarily an isolated process environment, not a tiny virtual machine.
- SSH gives you access to a shell and processes on a remote system.
- CI jobs launch processes in prepared environments and judge success through exit codes.
- Web servers are processes listening on network sockets.
- Kubernetes schedules containerized processes across machines.
- AWS EC2 provides virtual machines on which the same users, files, processes, permissions, and networking concepts apply.

The tools change. The operating-system fundamentals remain.

## Engineering review

### What problem does this solve?

It gives you a consistent model for understanding how programs obtain and use system resources.

### Why was it designed this way?

Separating applications from privileged resource management improves isolation, security, portability, and system stability.

### When should I use it?

Use this model whenever you launch, configure, debug, monitor, secure, or deploy software.

### When should I avoid it?

Do not overcomplicate simple tasks by tracing every kernel interaction. Use the lowest level of detail that explains the problem. Descend into deeper layers when evidence points there.

### How does this make me a better engineer?

It replaces command memorization with causal reasoning. You can identify which layer owns a behavior and investigate systematically.

### How does this reduce waste?

A correct systems model prevents random troubleshooting. Instead of changing unrelated settings, you test the most likely layer and narrow the failure deliberately.

## Handbook principle #2

> The operating system manages resources; every developer tool ultimately operates through files, processes, identities, memory, devices, and kernel services.

## Practice

Open Terminal on the Mac and run:

```bash
ps
```

Do not memorize the output yet. Identify only:

- the shell process,
- the `ps` process created to inspect processes,
- the process identifiers shown beside them.

Then answer: which item is the stored program, which item is the running process, and which process launched the other?
