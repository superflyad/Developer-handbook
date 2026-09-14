# Chapter 18 — Quoting, Expansion, and Redirection in Practice

The shell command line is source code. Before a utility receives arguments, the shell parses syntax, performs expansions, removes quoting syntax, and establishes redirections.

The central idea is:

> Debug the command the shell constructs, not merely the text you typed: quoting controls interpretation, expansion creates values, and redirection changes process connections before execution.

## 1. The shell transforms words before invocation

Consider:

```bash
pattern='*.md'
printf '<%s>\n' $pattern
```

The utility does not necessarily receive the literal characters `*.md`. Bash expands `$pattern`, performs word splitting, and then pathname expansion on the resulting words.

With quotes:

```bash
printf '<%s>\n' "$pattern"
```

the value remains one argument and the `*` remains data.

## 2. Use an evaluation pipeline as a mental model

For ordinary Bash words, a useful simplified order is:

```text
parse shell syntax
→ brace expansion
→ tilde expansion
→ parameter, arithmetic, and command substitution
→ word splitting
→ pathname expansion
→ quote removal
→ invoke command with final arguments and redirections
```

Bash has context-specific exceptions, especially assignments, arrays, here-documents, and redirection words. The model is for prediction, not a substitute for the Bash manual.

The important distinction is that expansion can change both values and the number of arguments.

## 3. Single quotes preserve literal characters

Single quotes preserve every enclosed character until the closing quote:

```bash
printf '%s\n' '$HOME *.md $(date)'
```

The shell does not expand the dollar sign, wildcard, or command substitution.

A single quote cannot occur inside a single-quoted Bash string. Adjacent quoted and unquoted fragments can form one word:

```bash
printf '%s\n' 'don'"'"'t'
```

Prefer clarity over clever quoting. If data is complex, store it in a variable or file rather than constructing unreadable shell source.

## 4. Double quotes allow selected expansions

Double quotes permit parameter expansion, command substitution, and arithmetic expansion while generally preventing word splitting and pathname expansion of their results:

```bash
name='Ada Lovelace'
printf '<%s>\n' "$name"
```

This supplies one argument containing a space.

The durable rule is not “always quote everything.” It is:

> Quote every expansion whose value must remain one argument or preserve empty values and literal wildcard characters.

Some contexts, such as arithmetic expressions and Bash's `[[ ... ]]`, have different rules. Learn each context rather than applying slogans blindly.

## 5. Unquoted expansion can delete an argument

Compare:

```bash
value=''
printf '<%s>\n' $value
printf '<%s>\n' "$value"
```

The unquoted empty expansion may contribute no argument. The quoted expansion contributes one empty argument.

This distinction matters in configuration and APIs where absent, empty, and default are separate states.

## 6. Arrays preserve multiple argument boundaries

A scalar string is not an argument list. In Bash, use an array:

```bash
files=('first report.txt' 'second report.txt')
printf '<%s>\n' "${files[@]}"
```

`"${files[@]}"` expands each element as a separate argument while preserving its contents.

Avoid assembling a command as one string:

```bash
command_text="grep -F $needle $file"
```

Executing that string requires reparsing shell syntax and creates ambiguity or injection risk. Store arguments as an array instead:

```bash
args=(grep -F -- "$needle" "$file")
"${args[@]}"
```

## 7. Pathname expansion is performed by the shell

Patterns such as `*`, `?`, and bracket expressions can expand to matching pathnames:

```bash
printf '%s\n' ./*.md
```

The receiving command gets the expanded names, not the pattern. Quote a pattern intended for another interpreter:

```bash
find . -name '*.md' -print
```

Default Bash leaves an unmatched glob unchanged. Shell options such as `nullglob`, `failglob`, or `dotglob` change behavior. An interactive configuration can therefore alter commands copied into a script or another machine.

## 8. Brace expansion generates text

Bash brace expansion can generate words before other expansions:

```bash
printf '%s\n' report.{md,pdf}
printf '%s\n' chapter-{12..15}
```

Brace expansion does not inspect the filesystem. It produces textual alternatives even when no corresponding file exists.

Because it is a Bash feature with syntax and limits, do not confuse it with a portable loop or data generator.

## 9. Parameter expansion can encode requirements

Bash supports more than simple `$name` substitution:

```bash
printf '%s\n' "${name:-anonymous}"
: "${required_value:?required_value must be set}"
```

The first supplies a default when the parameter is unset or null. The second reports an error and, in many contexts, prevents continuation when the requirement is unmet.

The colon in these forms determines whether null is treated like unset. This connects directly to Chapter 10's distinction between an absent variable and an empty one.

## 10. Command substitution captures output with loss

Command substitution captures standard output:

```bash
root=$(git rev-parse --show-toplevel) || exit 1
cd -- "$root" || exit 1
```

Bash removes trailing newline characters from the captured result. Command substitution also cannot preserve NUL bytes in a shell variable.

It is suitable for small textual values, not arbitrary files or pathname lists:

```bash
# unsafe for arbitrary names and large results
files=$(find . -type f -print)
```

Prefer direct pipelines, arrays populated by a pathname-safe interface, or `find -exec`.

## 11. Arithmetic expansion is numeric shell evaluation

Bash can evaluate integer arithmetic:

```bash
count=4
printf '%s\n' "$((count + 1))"
```

This is shell arithmetic with shell-specific rules, not decimal mathematics for money and not arbitrary-precision data processing. Validate external input before treating it as an arithmetic expression.

## 12. Redirection is shell syntax

This command never asks `printf` to open `result.txt`:

```bash
printf '%s\n' 'complete' > result.txt
```

The shell opens or creates the file, connects standard output to it, and then runs the command.

Common forms include:

```bash
command < input.txt
command > output.txt
command >> output.txt
command 2> errors.txt
command > output.txt 2> errors.txt
```

Truncating `>` and appending `>>` are different state transitions. Redirection can alter a file even if command execution later fails.

## 13. Redirections are processed left to right

Compare:

```bash
command > combined.log 2>&1
command 2>&1 > output.log
```

In the first, standard error is duplicated onto the already redirected standard output destination. In the second, standard error is first duplicated onto the shell's current standard output, after which only standard output moves to the file.

Descriptor duplication copies a connection at that moment; it does not create a permanent relationship between descriptor numbers.

## 14. Protect important files from accidental truncation

Before using `>`:

- verify the destination,
- understand whether replacement is intended,
- consider writing to a temporary file,
- validate the temporary output,
- then publish with a same-filesystem rename.

Bash's `noclobber` option can refuse some overwrites:

```bash
set -o noclobber
```

It is a helpful guardrail, not a complete storage-safety policy. It has overrides and does not replace boundary validation, permissions, version control, or backups.

## 15. Here-documents supply inline input

A here-document attaches multiline shell source as standard input:

```bash
cat <<'EOF'
$HOME remains literal here
*.md remains literal too
EOF
```

Quoting the delimiter suppresses parameter expansion, command substitution, and arithmetic expansion in the body. An unquoted delimiter permits those expansions.

Here-documents are useful for small templates and test fixtures. Large structured artifacts are usually clearer as separate files or format-aware templates.

## 16. Data must not become shell source

This is dangerous:

```bash
eval "$untrusted_text"
```

`eval` asks the shell to parse data as new shell code. Quoting the first expansion does not protect the later parse.

Likewise, passing a constructed string to `sh -c` creates a new interpretation boundary. Prefer argument arrays, standard input, environment variables with documented semantics, or direct APIs.

Shell injection is fundamentally a confusion between code and data.

## 17. Observe the final arguments

Use a diagnostic helper:

```bash
show_args() {
  printf 'argc=%s\n' "$#"
  printf '<%q>\n' "$@"
}
```

Then compare:

```bash
value='one two *.md'
show_args $value
show_args "$value"
```

`%q` and functions are Bash-specific, but the technique reveals the actual argument count and boundaries more reliably than staring at source text.

## 18. Common misconceptions

### “Variables contain commands”

Variables contain strings. Reinterpreting a string as shell source is an additional hazardous step.

### “Double quotes prevent every expansion”

They still allow parameter, arithmetic, and command substitution.

### “A glob is expanded by `ls`”

The shell normally expands it before `ls` starts.

### “Command substitution preserves exact output”

It removes trailing newlines and cannot carry NUL through a Bash variable.

### “Redirection happens after the command succeeds”

The shell establishes redirections before execution; truncation can happen before the command body runs.

## 19. Platform comparison

| Concern | Bash | POSIX `sh` | PowerShell |
| --- | --- | --- | --- |
| Arrays of arguments | indexed arrays | no general array facility | native arrays |
| Brace expansion | supported | not specified | different syntax and semantics |
| Command substitution | `$(...)` | `$(...)` | `$(...)`, returning PowerShell output |
| Native redirection | descriptor-oriented | descriptor-oriented | multiple PowerShell streams plus native handles |
| Pipeline values | bytes/text | bytes/text | objects between cmdlets |

Syntax that looks similar can have different evaluation and type behavior. Translate concepts, not punctuation alone.

## Core Computer Science Concept

Shell evaluation is a small **language-processing pipeline**. Parsing identifies syntax; expansions compute values; splitting and globbing can change cardinality; execution crosses a process interface.

Code-injection defects occur when a value from one stage is accidentally fed back into a parser as trusted source.

## Engineering Connections

- Subprocess APIs should accept argument arrays rather than constructed shell strings.
- SQL injection, template injection, and shell injection share code-versus-data confusion.
- Deployment tools avoid partial configuration by validating temporary output before rename.
- CI failures often come from differences in shell selection or startup options.
- Secure systems minimize interpretation layers between input and effect.

## From the Field

A build wrapper stores `compiler --flag "$source"` in one string and executes it through `eval`. A source filename containing shell punctuation becomes executable syntax.

Replacing the string with an array does more than add quotes: it removes the second parse and preserves the intended argument boundaries structurally.

## Engineering Review

### What problem does this solve?

It makes shell interpretation predictable and preserves intended argument, stream, and code/data boundaries.

### Why was it designed this way?

Expansion and redirection let a compact interactive language construct flexible process invocations without changing each utility.

### When should I use it?

Apply this model whenever commands contain variables, patterns, substitutions, redirections, generated paths, or external input.

### When should I avoid it?

Avoid complicated shell evaluation when a direct process API, structured template, parser, or general-purpose language expresses the contract more safely.

### How does this make me a better engineer?

It teaches staged interpretation, argument cardinality, descriptor timing, and code-versus-data separation.

### How does this reduce waste?

Predictable evaluation prevents corrupted arguments, accidental truncation, injection defects, and environment-specific quoting repairs.

## Handbook Principle #18

> Preserve code and data as different things, make argument boundaries structural, and reason about redirections in the order the shell establishes them.

## Practical Observation

In Bash, define `show_args` from Section 17 and run:

```bash
mkdir -p expansion-demo
cd expansion-demo || exit 1
touch 'one file.md' two.md
pattern='*.md'

show_args $pattern
show_args "$pattern"
show_args ./*.md
```

For each call, record the exact argument count and explain which stage changed it. Then redirect the output of one call to a new file and explain when that file is opened relative to function execution.

## Looking Ahead

The shell now constructs predictable invocations. Chapter 19 uses those invocations to observe and control foreground processes, background jobs, process groups, and signals.
