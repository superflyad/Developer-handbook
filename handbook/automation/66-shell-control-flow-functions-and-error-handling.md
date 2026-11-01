# Chapter 66 — Shell Control Flow, Functions, and Error Handling

Shell control flow is built around command exit status. That makes small programs expressive, but it also means expected false conditions, operational failures, pipelines, and language context can look deceptively similar.

The central idea is:

> Handle every expected outcome where it occurs, propagate unexpected failure deliberately, and never outsource the program's error model to one shell option.

## 1. Commands are conditions

In shell, `if` tests a command's exit status rather than a Boolean expression object:

```bash
if validate_config "$config_file"; then
    printf 'configuration is valid\n'
else
    status=$?
    printf 'configuration failed validation: status=%d\n' "$status" >&2
    exit "$status"
fi
```

The `then` branch runs after status zero; `else` runs after nonzero. A utility's contract determines what nonzero means. For `grep`, status 1 ordinarily means no selected lines, while a larger status indicates an error. Treating both as “the command crashed” loses information.

Capture `$?` immediately. Assignment, `printf`, or any other command replaces it.

Use `! command` when the branch only needs success versus failure. If the original numeric status matters, capture it in an `else` branch rather than after `!`, whose status has been inverted.

## 2. Choose the right test language

POSIX `test` and its `[` form support file, string, and integer tests:

```bash
if [ -f "$path" ] && [ -r "$path" ]; then
    printf 'readable regular file\n'
fi
```

The closing `]` is an argument, so spacing is syntax. Quote expansions inside `[` to preserve empty and multiword values.

Bash `[[ ... ]]` is a shell keyword with safer expansion rules and features such as pattern and regular-expression matching:

```bash
if [[ $mode == read-* ]]; then
    printf 'read-only mode\n'
fi
```

Do not quote the entire pattern when pattern matching is intended. Quote literal variable expansions on the right when their content must not become a pattern.

Use arithmetic context for integers:

```bash
if (( attempts < 1 || attempts > 10 )); then
    printf 'attempts must be between 1 and 10\n' >&2
    exit 64
fi
```

`[[ ... ]]` and `(( ... ))` are not POSIX `sh`. Select them only in a declared Bash script.

## 3. Branches should expose the policy

Use `case` when one value has a closed set of meaningful forms:

```bash
case $action in
    inspect) inspect_target ;;
    apply)   apply_target ;;
    *)
        printf 'unsupported action: %s\n' "$action" >&2
        exit 64
        ;;
esac
```

This makes the unknown case visible. A default that silently treats every new value as `apply` turns an interface extension into an unsafe action.

Short command lists can express simple dependencies:

```bash
mkdir -- "$output_dir" && write_report "$output_dir/report.json"
```

Do not build long business logic from `&&` and `||`. Precedence, the status of the last command, and contextual `errexit` behavior become difficult to review. Use named functions and `if` blocks when failure needs explanation or recovery.

## 4. Preserve loop item boundaries

Iterate over arguments with `"$@"`:

```bash
for path in "$@"; do
    inspect_path "$path"
done
```

Do not use `for path in $(find ...)`. Command substitution strips trailing newlines, then unquoted expansion splits and expands patterns. Filenames can contain spaces, tabs, newlines, and wildcard characters.

When a supporting tool offers null-delimited records, consume them explicitly:

```bash
while IFS= read -r -d '' path; do
    inspect_path "$path"
done < <(find "$root" -type f -print0)
```

This example is Bash-specific because it uses `read -d` and process substitution. Chapter 67 develops record and pathname formats in depth.

A loop must have an exit condition that remains true under failure. Bound polling by attempts or deadline, and make an empty input set an intentional result rather than an accidental infinite wait.

## 5. Functions create contracts, not isolation

Shell functions run in the current shell unless deliberately placed in a subshell. They can change global variables, directory, options, traps, and positional parameters.

Use `local` for Bash function state:

```bash
describe_file() {
    local path=$1
    local size

    if ! size=$(wc -c < "$path"); then
        printf 'cannot measure file: %s\n' "$path" >&2
        return 1
    fi

    printf '%s\t%s\n' "$size" "$path"
}
```

`return` reports a function status; `exit` terminates the whole shell process. A reusable function should normally return failure and let the entry point decide whether the program stops.

Assign and capture command substitution separately when status matters. In declarations such as `local value=$(command)`, the declaration command can obscure the substitution's status on some shells.

Document whether a function prints data, emits diagnostics, mutates state, changes directory, or sets globals. A name alone does not contain its side effects.

## 6. Pipelines have several statuses

By default, a pipeline's status is the status of its last command:

```bash
producer | transformer | consumer
```

If `producer` fails but `consumer` exits zero after reading an empty stream, the pipeline can appear successful. Bash's `pipefail` option makes the pipeline nonzero when a component fails, using defined Bash rules:

```bash
set -o pipefail
```

`pipefail` is useful but not a complete policy. Some producers intentionally receive `SIGPIPE` when a consumer such as `head` stops early. Some filters use nonzero to express an expected empty selection. Decide whether those outcomes are errors for this pipeline.

Bash exposes component statuses in `PIPESTATUS`, but another command replaces that array. Copy it immediately:

```bash
producer | transformer | consumer
statuses=("${PIPESTATUS[@]}")
```

Avoid a pipeline when intermediate status and data need complex handling. Temporary controlled files or a language with explicit process APIs can be clearer.

## 7. Pipeline processes can hide state changes

Shells may run pipeline elements in subshell processes. A variable changed inside a pipeline-fed loop might not exist afterward:

```bash
count=0
printf '%s\n' a b | while IFS= read -r item; do
    ((count += 1))
done
printf '%s\n' "$count"  # can still be 0
```

In Bash, redirecting into the loop keeps the loop in the current shell:

```bash
count=0
while IFS= read -r item; do
    ((count += 1))
done < input.txt
```

Do not depend on optional shell settings that change pipeline execution unless the interpreter configuration is part of the program contract.

## 8. There is no universal strict mode

The frequently copied line `set -euo pipefail` combines three independent Bash behaviors:

- `-e` (`errexit`) requests exit after some unhandled nonzero statuses, with context-dependent exceptions;
- `-u` (`nounset`) treats many unset expansions as errors, with syntax and version edge cases;
- `pipefail` changes pipeline status selection.

Each can be useful when its behavior is understood and tested. Together they do not define correct recovery, distinguish expected statuses, add timeouts, clean external state, or explain failure.

`errexit` is disabled or modified in several syntactic contexts because commands used by `if`, `while`, `until`, `&&`, `||`, and `!` must be allowed to return nonzero. Functions and command substitutions can inherit or alter the effect in surprising ways across settings and versions.

Choose options individually near program startup, document them, and still handle important commands explicitly. Test the exact supported shell versions and failure contexts.

## 9. Expected failure belongs in a branch

Classify operations before choosing a response:

| Outcome | Example | Response |
| --- | --- | --- |
| success | object already in desired state | continue and report no change |
| expected absence | optional file not present | choose documented default or skip |
| input rejection | invalid identifier | stop with usage or validation status |
| transient failure | bounded service overload | retry only if safe |
| permanent operational failure | permission denied | stop and preserve evidence |
| ambiguous effect | timeout after mutation request | reconcile before retry |

Do not append `|| true` merely to keep a script running. That converts all failures into success, including conditions never considered. If one status is acceptable, inspect and normalize that status only.

Likewise, redirecting standard error to `/dev/null` removes evidence; it does not handle the error.

## 10. Retries require a safety contract

Retry only when the operation is safe to repeat or has a deduplication mechanism. Classify the failure as plausibly transient, bound attempts and total time, and include delay with jitter for shared services.

A reusable Bash retry skeleton can preserve the final status:

```bash
retry() {
    local max_attempts=$1
    shift
    local attempt=1
    local status

    while true; do
        if "$@"; then
            return 0
        else
            status=$?
        fi

        if (( attempt >= max_attempts )); then
            return "$status"
        fi

        printf 'attempt %d/%d failed with status %d; retrying\n' \
            "$attempt" "$max_attempts" "$status" >&2
        sleep "$attempt"
        ((attempt += 1))
    done
}
```

This function deliberately does not decide which statuses are transient, impose a total deadline, add jitter, or reconcile ambiguous effects. A production wrapper must supply those domain decisions. Never pass an assembled command string for `eval`; pass command arguments as `"$@"`.

## 11. Traps are lifecycle hooks

Use an `EXIT` trap for exact resources owned by the script, as Chapter 65 demonstrated. Signal traps should preserve a meaningful exit and avoid launching unbounded work:

```bash
interrupted=0

on_interrupt() {
    interrupted=1
}

trap on_interrupt INT TERM
```

Long-running loops can check `interrupted` at safe boundaries, stop accepting work, and let normal cleanup run. External commands may receive signals before or instead of the parent shell, so test the process tree rather than assuming one trap controls every child.

An `ERR` trap is Bash-specific and follows many of the same contextual rules as `errexit`. It can add diagnostics but is not an exception mechanism. Avoid recursive trap failures and preserve the original status before logging.

## 12. Add diagnostics at decision boundaries

A useful failure message answers:

- what operation failed;
- which sanitized target was involved;
- which attempt or phase was active;
- what status or category was observed;
- what state may remain;
- what the caller should do next.

```bash
printf 'publish failed: target=%s status=%d; staging file retained=%s\n' \
    "$target" "$status" "$staging_file" >&2
```

Do not print secrets, full credential-bearing URLs, or sensitive content. Shell tracing with `set -x` expands commands and can expose values; enable it only in a controlled scope with redaction-aware inputs.

Line numbers and function names can help developers, but operational messages need domain context more than a stack-like trace.

## 13. A bounded polling example

This Bash program waits for a regular readable file without mutating it. It demonstrates argument validation, a function, a bounded loop, explicit statuses, and signal-aware interruption:

```bash
#!/usr/bin/env bash

usage() {
    printf 'Usage: %s ATTEMPTS PATH\n' "$0" >&2
}

if (( $# != 2 )); then
    usage
    exit 64
fi

attempts=$1
path=$2

if [[ ! $attempts =~ ^[0-9]+$ ]] || \
    (( attempts < 1 || attempts > 10 )); then
    printf 'ATTEMPTS must be an integer from 1 through 10\n' >&2
    exit 64
fi

interrupted=0
trap 'interrupted=1' INT TERM

is_ready() {
    [[ -f $path && -r $path ]]
}

for (( attempt = 1; attempt <= attempts; attempt += 1 )); do
    if (( interrupted )); then
        printf 'interrupted while waiting for: %s\n' "$path" >&2
        exit 130
    fi

    if is_ready; then
        printf '%s\n' "$path"
        exit 0
    fi

    if (( attempt < attempts )); then
        printf 'not ready: attempt=%d/%d path=%s\n' \
            "$attempt" "$attempts" "$path" >&2
        sleep 1
    fi
done

printf 'not ready after %d attempts: %s\n' "$attempts" "$path" >&2
exit 75
```

The file can change immediately after the check; this program reports an observation, not a durable lock. A real consumer must open and validate the file under its own race and trust model.

## 14. Test every control-flow edge

In a disposable directory, test the example with:

- zero, one, and too many arguments;
- nonnumeric, zero, and excessive attempt counts;
- a file that already exists;
- a missing file that remains missing;
- a file created during the wait;
- `INT` during the loop;
- a path containing whitespace and wildcard characters.

Assert standard output, standard error, exit status, elapsed bound, and residual processes. Syntax checking cannot prove branch behavior. Static analysis can find suspicious quoting and status patterns, but it cannot supply the domain meaning of a retry.

## Common Misconceptions

- “`set -e` exits on every error.” Its behavior depends on syntax context, functions, substitutions, options, and shell version.
- “`pipefail` identifies which command failed.” It changes aggregate status; inspect component evidence when identity matters.
- “`|| true` handles a known failure.” It hides every failure from that command unless statuses are classified first.
- “A retry fixes reliability.” Unsafe or unbounded retries multiply effects and load.
- “Functions isolate variables.” They share the shell unless state is made local or a subshell is chosen.

## Core Computer Science Concept

Shell control flow is **algebra over process outcomes**. Commands produce statuses and streams; branches, loops, lists, and pipelines combine them. Correctness depends on preserving each outcome's domain meaning through that composition.

## Engineering Connections

- Bounded retries apply the timeout and idempotency lessons from TCP and HTTP at the automation layer.
- Functions expose interfaces just as commands do: arguments in, streams and status out, side effects documented.
- Pipeline record boundaries determine whether filenames and structured data survive composition.
- Signal handling coordinates process lifecycle but cannot guarantee transactional rollback.

## From the Field

A backup script uses `database_dump | gzip > backup.gz` and checks only the default pipeline status. The dump command fails immediately, while `gzip` successfully writes a valid empty compressed stream and exits zero. The job reports success. Explicit pipeline policy, artifact validation, and a temporary output prevent the empty file from becoming a trusted backup.

## Engineering Review

### What problem does this solve?

It makes branches, loops, functions, pipelines, retries, and cleanup preserve the intended meaning of command outcomes.

### Why was it designed this way?

Shell composes processes through statuses and streams, so control flow must interpret those values in their command-specific context.

### When should I use it?

Use these patterns in bounded shell programs whose supported interpreter and failure cases can be tested comprehensively.

### When should I avoid it?

Avoid growing shell into a large stateful application when richer types, process APIs, or transactional recovery would be clearer.

### How does this make me a better engineer?

It makes you classify failure and recovery at each operation rather than relying on folklore options or optimistic continuation.

### How does this reduce waste?

It prevents false-success pipelines, infinite retries, hidden status loss, subshell surprises, and repeated debugging of silent branches.

## Handbook Principle #66

> Interpret status at the command boundary, bound every loop and retry, and use shell options as tools—not as a substitute for an error model.

## Practical Observation

Save the bounded polling example in a disposable directory and syntax-check it. Exercise every case in its test list, capturing stdout, stderr, status, and elapsed time separately. Explain which failures are expected control flow and which indicate a broken invocation, then delete the directory.

## Looking Ahead

Correct control flow still fails when records are represented ambiguously. Chapter 67 defines line, null-delimited, JSON, CSV, YAML, encoding, schema, and compatibility boundaries for automation data.

## References

- [GNU Bash Reference Manual — Conditional Constructs](https://www.gnu.org/software/bash/manual/html_node/Conditional-Constructs.html)
- [GNU Bash Reference Manual — Pipelines](https://www.gnu.org/software/bash/manual/html_node/Pipelines.html)
- [GNU Bash Reference Manual — The Set Builtin](https://www.gnu.org/software/bash/manual/html_node/The-Set-Builtin.html)
- [POSIX Shell Command Language](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html)
