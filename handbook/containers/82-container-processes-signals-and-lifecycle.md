# Chapter 82 — Container Processes, Signals, and Lifecycle

A container can start successfully while hiding its real service behind a shell, ignoring termination, leaking zombie children, or converting failures into exit status zero. The runtime manages processes, not application intent.

The central idea is:

> Make the intended service the observable foreground process, deliver and handle lifecycle signals explicitly, and let its exit status tell the truth.

## 1. Follow the container state machine

An OCI-style runtime moves a container through states such as:

```text
create -> created -> start -> running -> process exits -> stopped -> delete
```

The image supplies filesystem content and process defaults. Creating a container adds runtime configuration and state. Starting it executes the configured initial process. The container becomes stopped when that process exits, even if unrelated host processes or durable storage remain.

A stopped container is not a paused virtual machine. Its process has ended; the runtime may retain metadata and a writable snapshot until deletion.

## 2. Distinguish build commands from runtime commands

Dockerfile-like recipes use different instructions for different times:

- `RUN` executes during the image build and records filesystem changes;
- `ENTRYPOINT` defines the stable executable for a container invocation;
- `CMD` supplies a default executable or default arguments at runtime.

`CMD` does not execute while building. `RUN` does not become the service command merely because it started a process during a layer build.

Only the effective final `ENTRYPOINT` and `CMD` matter after base-image inheritance and overrides.

## 3. Compose entrypoint and arguments deliberately

An exec-form entrypoint with exec-form default arguments is predictable:

```dockerfile
ENTRYPOINT ["/app/server"]
CMD ["--config", "/etc/app/config.toml"]
```

The default runtime command becomes:

```text
/app/server --config /etc/app/config.toml
```

User-supplied command arguments replace `CMD` while retaining the entrypoint. Overriding the entrypoint replaces a different part of the contract.

Document which portion operators are expected to change. An image that acts as one application usually benefits from a stable entrypoint and overridable defaults. A general tool image may need different behavior.

## 4. Prefer exec form for the main process

Exec form is a JSON array:

```dockerfile
ENTRYPOINT ["python", "-m", "service"]
```

Shell form inserts a command interpreter:

```dockerfile
ENTRYPOINT python -m service
```

On Linux, the second form commonly becomes `/bin/sh -c ...`. The shell is now the initial process, and the application is its child. If the shell does not forward termination signals and reap descendants correctly, the application can outlive the grace period or exit without its status reaching the runtime.

Exec form does not perform shell expansion, pipelines, redirection, or wildcard expansion. If those features are required, invoke and manage a shell explicitly.

## 5. Use `exec` at the end of simple wrappers

An entrypoint wrapper can perform bounded initialization and then replace itself with the service:

```bash
#!/usr/bin/env sh
set -eu

/app/validate-config --file "${APP_CONFIG:?APP_CONFIG is required}"
exec "$@"
```

With:

```dockerfile
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["/app/server", "--foreground"]
```

`exec` replaces the shell without creating another process layer. The service receives the shell's PID and signals, and its exit status becomes the container's exit status.

Do not use `exec $@` without quotes; it destroys argument boundaries. Do not let initialization start a daemon that remains in the background after the wrapper exits.

## 6. Keep the service in the foreground

Traditional server packages may daemonize: fork, detach from the terminal, write a PID file, and let the parent exit. That model conflicts with a runtime that supervises the initial process.

Configure the service's foreground mode. Send logs to stdout and stderr or an explicit logging boundary rather than a daemon-owned file that no external collector sees.

If the initial process exits after launching a background daemon, the runtime considers the container stopped and can terminate the remaining namespace processes.

“Detached container” means the client is not attached to its I/O. It does not mean the service should daemonize inside the container.

## 7. PID 1 has special behavior

The first process in a Linux PID namespace appears as PID 1 inside it. It has two important differences from an ordinary application process:

- orphaned descendants can be reparented to it, so it must call a wait function to reap exited children;
- the kernel treats some default signal actions differently for the namespace's init process.

An application that never creates descendants may not need a separate init helper. An application that launches workers, shells, or subprocesses must ensure they are reaped and stopped.

Test actual PID 1 behavior. Running the executable directly in a developer shell gives it a parent init and can hide defects.

## 8. Reap child processes

When a child exits, the kernel retains minimal status until its parent waits for it. An unreaped exited child is a zombie. Zombies consume process-table entries and can eventually exhaust a PID limit.

The main process should:

- retain child identities;
- wait for their completion;
- collect and classify exit status;
- stop remaining children during shutdown;
- avoid spawning detached grandchildren it cannot control.

Libraries and language runtimes often provide correct subprocess waiting when used as documented. A wrapper that starts a child with `&` and never waits does not.

## 9. Add a minimal init only for a real need

Some runtimes can insert a small init process as PID 1. Its job is commonly to forward signals and reap orphaned children, then report the main child's exit status.

An init helper is useful when:

- the application cannot safely act as PID 1;
- third-party code double-forks or leaves orphaned children;
- a wrapper genuinely coordinates more than one process.

It is not a substitute for application shutdown logic. The service still needs to stop accepting work, finish or checkpoint active work, flush durable state, and exit before the deadline.

Do not install a full host-style init system merely because the image resembles a machine.

## 10. Understand the stop sequence

A typical graceful stop is:

```text
runtime sends configured stop signal to the initial process
-> waits up to the stop timeout
-> sends an uncatchable kill if the process remains
-> records the resulting exit state
```

On Linux, `SIGTERM` is a common default. An image can declare another `STOPSIGNAL`, and runtime configuration can override it.

Choose a signal the application handles and a timeout long enough for bounded cleanup. A larger timeout does not fix an application that never receives or acts on the signal.

Forced kill provides no cleanup opportunity. Design durable state so correctness does not depend on graceful shutdown always occurring.

## 11. Handle termination as a state transition

A service receiving termination should usually:

1. mark itself unready so new traffic or work stops;
2. stop admitting new requests or queue jobs;
3. cancel or finish work under a deadline;
4. checkpoint resumable operations;
5. close listeners and child processes;
6. flush required durable output and telemetry;
7. exit with a documented status.

Signal handlers themselves should do minimal safe work, such as setting an event. Perform complex cleanup in ordinary control flow.

Make repeated termination requests safe. A second signal might shorten the deadline or force exit under policy, but it must not start a second cleanup sequence that corrupts state.

## 12. Propagate signals through the process tree

If the initial process supervises children rather than replacing itself, it must forward relevant signals and wait for every child.

Process groups can help, but group membership and shell job-control behavior must be tested. Sending a signal only to the immediate child may leave grandchildren running.

Forwarding every signal blindly is also wrong. Decide which signals represent termination, reload, diagnostic dump, or user interrupt and how each child should receive them.

When the runtime's grace period ends, it can kill the container's remaining processes. That recovers capacity but does not make partially completed effects safe.

## 13. Report exit status truthfully

The initial process's exit status is the runtime's primary completion signal. Establish a small contract:

- zero means the intended work completed successfully or the service stopped normally;
- nonzero means startup, runtime, or shutdown failed;
- distinct codes may classify stable operational failures when callers use them;
- signal termination is recorded distinctly by the platform where supported.

Wrappers must preserve the service's status:

```bash
"$@"
status=$?
cleanup
exit "$status"
```

Under `set -e`, capture failure in an explicit conditional or disable automatic exit for the exact wait operation; otherwise cleanup and status propagation can be skipped.

Never append `|| true` to the main service merely to prevent a restart loop. That turns failure into false success.

## 14. Separate running, ready, and healthy

A running initial process proves only that it has not exited. It may still be:

- loading configuration;
- waiting for a dependency;
- deadlocked;
- unable to serve requests;
- draining during shutdown;
- returning errors for every operation.

Startup, readiness, and liveness answer different questions. Chapter 86 develops their design and connection to resource limits and diagnosis.

Do not put a service in the background merely so a wrapper can poll it forever. Use the runtime or orchestrator's health interface and keep the real service observable.

## 15. Use restart policies as recovery policy

A restart policy decides whether the runtime creates another attempt after exit or daemon restart. It does not repair the cause.

Choose based on semantics:

- no restart for one-shot work whose caller owns retry;
- bounded failure restart for transient startup or service faults;
- service restart after unexpected exit under a supervisor contract;
- no automatic restart after an intentional administrative stop where supported.

Protect against crash loops with delay, backoff, attempt history, and alerts. A process that exits instantly with invalid configuration should not consume unlimited CPU and log storage.

Product policies differ. For Docker Engine, `on-failure`, `always`, and `unless-stopped` have documented distinctions around exit status, manual stops, and daemon restart. Do not project those exact semantics onto another platform.

## 16. Align retries across layers

An application, container runtime, job controller, and deployment system can each retry. Uncoordinated policies multiply attempts and obscure ownership.

Define:

- which layer retries startup;
- which layer retries individual requests or jobs;
- maximum attempts and elapsed deadline;
- idempotency key and checkpoint behavior;
- which failures are terminal;
- what evidence survives replacement;
- who alerts and who can stop the loop.

Restarting a container resets process memory. It does not undo external effects or make non-idempotent startup safe.

## 17. Treat exec sessions as diagnostic processes

An exec command starts an additional process in a running container's namespaces and filesystem view. It is not the initial process and normally exists only while the container remains running.

Use exec sessions for bounded diagnosis when policy allows. Record the actor and command, avoid exposing secrets, and prefer read-only inspection.

Do not:

- patch production files and call the container fixed;
- start a replacement daemon by hand;
- assume an interactive shell exists in a minimal image;
- rely on terminal behavior to reproduce noninteractive execution;
- leave untracked diagnostic processes consuming resources.

Fix source or runtime configuration, build a new image digest, and replace the container.

## 18. Attach and exec answer different questions

Attaching connects a client to the initial process's configured I/O. Executing creates another process. Viewing logs reads captured output under the logging contract.

Confusing them can cause damage. An attached terminal may send signals or input to the service. An exec shell can mutate the writable layer. A log view may omit direct terminal output not captured by the driver.

Choose the least invasive mechanism that answers the diagnostic question.

## 19. Replace immutable runtime instances

Configuration, image digest, mounts, ports, capabilities, and resource limits form the container specification. Many changes require replacement rather than in-place mutation.

A replacement flow should:

1. create a new instance from the intended immutable image and configuration;
2. verify startup and readiness;
3. shift work or traffic under a bounded policy;
4. stop the old instance gracefully;
5. reconcile durable work and state;
6. remove ephemeral writable state when no longer needed;
7. retain deployment and exit evidence.

Manual changes inside a running container create snowflake state that disappears on replacement and cannot be traced to the image provenance from Chapter 81.

## 20. Complete example: a signal-aware service

This standard-library example uses an event to move signal handling into normal control flow. It reports startup, returns a nonzero status for a synthetic service failure, and includes a POSIX integration test that sends `SIGTERM` to the real process:

```python
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path


class ShutdownState:
    def __init__(self) -> None:
        self.event = threading.Event()
        self.lock = threading.Lock()
        self.first_signal: int | None = None
        self.requests = 0

    def request(self, signum: int) -> bool:
        with self.lock:
            first = not self.event.is_set()
            if first:
                self.first_signal = signum
            self.requests += 1
            self.event.set()
            return first


def run_service(*, fail_after_start: bool = False) -> int:
    shutdown = ShutdownState()

    def request_stop(signum: int, _frame: object) -> None:
        first = shutdown.request(signum)
        print(f"STOP_REQUESTED signal={signum} first={first}", flush=True)

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)

    print(f"READY pid={os.getpid()}", flush=True)
    if fail_after_start:
        print("synthetic service failure", file=sys.stderr, flush=True)
        return 7

    while not shutdown.event.wait(timeout=0.1):
        pass

    print("STOPPING admission=closed", flush=True)
    # Finish or checkpoint bounded work here.
    print("STOPPED clean=true", flush=True)
    return 0


class LifecycleTests(unittest.TestCase):
    def test_service_failure_returns_nonzero(self) -> None:
        self.assertEqual(run_service(fail_after_start=True), 7)

    @unittest.skipIf(os.name == "nt", "POSIX signal delivery required")
    def test_sigterm_stops_real_process_cleanly(self) -> None:
        process = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--serve"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert process.stdout is not None
        ready = process.stdout.readline().strip()
        self.assertRegex(ready, r"^READY pid=\d+$")

        process.send_signal(signal.SIGTERM)
        remaining_stdout, stderr = process.communicate(timeout=5)

        self.assertEqual(process.returncode, 0, stderr)
        self.assertIn("STOP_REQUESTED", remaining_stdout)
        self.assertIn("STOPPED clean=true", remaining_stdout)

    def test_stop_handler_is_idempotent_at_the_state_boundary(self) -> None:
        shutdown = ShutdownState()

        self.assertTrue(shutdown.request(signal.SIGTERM))
        self.assertFalse(shutdown.request(signal.SIGINT))

        self.assertTrue(shutdown.event.is_set())
        self.assertEqual(shutdown.first_signal, signal.SIGTERM)
        self.assertEqual(shutdown.requests, 2)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--fail", action="store_true")
    arguments = parser.parse_args()
    if arguments.serve:
        return run_service(fail_after_start=arguments.fail)

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(LifecycleTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

Save it as `test_service_lifecycle.py` and run:

```bash
python test_service_lifecycle.py
python test_service_lifecycle.py --serve --fail
```

On POSIX, the test launches the saved file, waits for readiness, delivers a real `SIGTERM`, and verifies clean exit. The test is explicitly skipped on Windows because Windows process termination and console-control events have different semantics.

In an approved disposable container environment, use a digest-pinned Python base and this runtime configuration:

```dockerfile
STOPSIGNAL SIGTERM
COPY --chown=65532:65532 test_service_lifecycle.py /app/service.py
USER 65532:65532
ENTRYPOINT ["python", "/app/service.py", "--serve"]
```

Start it, wait for `READY`, issue the platform's graceful stop, and measure the interval to `STOPPED`. Then start with `--fail`, verify exit status 7, and inspect—not guess—how the selected restart policy responds.

## 21. Test every lifecycle boundary

Test the final image for:

- command and argument overrides;
- missing and malformed configuration;
- PID 1 identity and child reaping;
- termination before readiness;
- termination during active work;
- repeated termination requests;
- cleanup finishing within the grace period;
- forced kill and restart recovery;
- correct success and failure exit codes;
- restart-loop bounds;
- exec-session cleanup;
- writable-state removal on replacement.

Capture monotonic timing and process trees. A test that only calls the signal handler does not prove the runtime delivers the signal to the intended process.

## 22. Diagnose a container that will not stop

Inspect in order:

1. effective entrypoint and arguments;
2. process tree and PID 1;
3. configured stop signal and timeout;
4. whether PID 1 has a handler for that signal;
5. wrapper use of shell form versus exec;
6. child process groups and orphaned descendants;
7. application drain and cleanup progress;
8. blocked system calls or uninterruptible I/O;
9. remaining external work or leases;
10. final exit status and forced-kill evidence.

Increasing the timeout can be appropriate for legitimate bounded work. It should follow evidence, not replace diagnosis.

## Common Misconceptions

- “Detached mode means the app should daemonize.” Detach describes the client connection; the service should remain in the foreground.
- “Shell form and exec form are cosmetic.” They change argument parsing, process trees, and signal delivery.
- “PID 1 is just the first PID.” It has namespace-init signal and child-reaping responsibilities.
- “A restart policy makes a service reliable.” It can amplify deterministic failures and does not recover external state.
- “Exit zero keeps the container healthy.” It reports completion and can conceal a crash from supervisors.
- “An exec shell permanently fixes a container.” Its changes are unreviewed writable-instance state.

## Core Computer Science Concept

A container lifecycle is **process supervision over an explicit state machine**. Signals request transitions, wait operations collect child state, exit status reports completion, and restart policy creates another attempt rather than continuing the old process.

## Engineering Connections

- PID namespaces refine the process model introduced in Chapter 78.
- Signal-safe state transitions apply the event and state-machine reasoning from Chapter 74.
- Graceful shutdown must cooperate with queue leases and checkpoints from Chapter 76.
- Truthful exit status is a structured interface between the process and CI/CD or runtime supervision.
- Immutable replacement preserves image provenance from Chapter 81.

## From the Field

A shell-form entrypoint launches a server as its child. The runtime sends `SIGTERM` to the shell, which exits without forwarding it. The server keeps accepting work until the grace period ends, then receives a forced kill during a write. Exec form and a bounded application shutdown path would have delivered termination to the service and preserved recovery evidence.

## Engineering Review

### What problem does this solve?

It makes container startup, supervision, shutdown, failure, retry, diagnosis, and replacement reflect the real service process.

### Why was it designed this way?

The runtime supervises the initial process, so command composition, PID 1 behavior, signals, child status, and exit codes must remain observable across that boundary.

### When should I use it?

Use this lifecycle model for every long-running service, worker, scheduled job, migration, and one-shot command packaged as a container.

### When should I avoid it?

Avoid adding wrappers or init systems when the application can already run in the foreground, reap its children, handle signals, and exit truthfully.

### How does this make me a better engineer?

It teaches you to debug containers as process trees and state transitions rather than opaque running boxes.

### How does this reduce waste?

It prevents forced shutdowns, zombie accumulation, hidden failures, restart storms, manual container patching, and unreproducible lifecycle bugs.

## Handbook Principle #82

> Keep the real service in the foreground, make PID 1 own its children and signals, and let the final exit status describe what actually happened.

## Practical Observation

Run the lifecycle tests on a POSIX host and then inside the final image. Record the effective command, PID tree, `SIGTERM` delivery, shutdown duration, emitted state transitions, and exit status. Repeat with one child process and prove it is reaped before the container exits.

## Looking Ahead

Process replacement is safe only when state has a deliberate home. Chapter 83 separates ephemeral writable layers, temporary filesystems, bind mounts, managed volumes, and external storage so container deletion does not become accidental data deletion.

## References

- [Dockerfile reference — `ENTRYPOINT`, `CMD`, and `STOPSIGNAL`](https://docs.docker.com/reference/dockerfile/)
- [Docker Engine — Running containers](https://docs.docker.com/engine/containers/run/)
- [Docker Engine — Start containers automatically](https://docs.docker.com/engine/containers/start-containers-automatically/)
- [Docker CLI — `docker container exec`](https://docs.docker.com/reference/cli/docker/container/exec/)
- [OCI Runtime Specification — Runtime and lifecycle](https://specs.opencontainers.org/runtime-spec/runtime/)
- [Linux `pid_namespaces(7)` manual page](https://man7.org/linux/man-pages/man7/pid_namespaces.7.html)
- [Linux `signal(7)` manual page](https://man7.org/linux/man-pages/man7/signal.7.html)
- [Linux `wait(2)` manual page](https://man7.org/linux/man-pages/man2/wait.2.html)
