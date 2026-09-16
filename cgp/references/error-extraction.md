# Extracting CGP compile errors

Use manual error extraction when `cargo-cgp` is unavailable or leaves a CGP error largely
unrewritten. The goal is a compact summary that identifies the error class, whether its cause is
visible, and what to do next. Read [the error shapes](#the-two-shapes-to-recognize), then follow the
instructions for [extracting](#extracting-an-error-yourself) or
[delegating](#delegating-the-extraction-to-a-sub-agent) the analysis.

Prefer [`cargo-cgp`](https://github.com/contextgeneric/cargo-cgp) for diagnosis. It rewrites
recognized errors into a `[CGP-Exxx]` headline and a dependency tree that already provide the
summary described here. See the [main skill’s tooling section](../SKILL.md) for installation and
usage. The remaining instructions apply to raw compiler output.

## Why extraction is a skill of its own

Separate reading a long error from fixing the code. [Lazy wiring](checking.md) can report one
missing dependency at every use that requires it, producing repeated failures involving
`IsProviderFor`, `DelegateComponent`, `CanUseComponent`, and expanded `Symbol`/`Chars`/`PathCons`
types. A single missing field can therefore generate many error blocks.

Some CGP errors omit the failed dependency entirely. Reading more of that output cannot reveal the
cause and may lead to an unsupported diagnosis. Classify the error before tracing its bounds.

## The two shapes to recognize

Read the trait named in the error before decoding nested types. Determine whether the diagnostic
exposes the failed dependency or stops at a consumer or provider trait. The [macro-grammar
decoder](macro-grammar.md) and [checking guide](checking.md) describe the full error classes;
extraction begins with this distinction.

A **surfaced error** includes the root cause. It is an `E0277` note chain, often headed by
`CanUseComponent` or `IsProviderFor`, that names a concrete missing bound such as
`HasField<Symbol!("name")>`. A [`check_components!`](checking.md) assertion exposes this bound by
requiring `IsProviderFor` directly and forcing evaluation of the provider’s `where` clause. Extract
the missing bound from the `help:` or “is not implemented” note, then follow the `required for …`
notes back to the check.

A **hidden error** omits the root cause. It may be an `E0599` reporting that `greet` exists on
`Person` but its bounds are unsatisfied, or an `E0277` reporting an unmet consumer bound such as
`Person: CanGreet`. The diagnostic stops at the consumer or provider trait without identifying the
missing dependency.

Direct consumer-trait calls can produce hidden errors because Rust suppresses the nested bound that
made a blanket impl inapplicable. Add `check_components!` for the failing component at the wiring
site and rerun the build to expose that bound. Do not search the original error for a cause it does
not contain.

## The cheap first move: grep for the suspected line

Search a captured log first when you have a specific hypothesis. A suspected missing field,
duplicate key, or `UseContext` cycle can often be confirmed with a few matching lines. This avoids
reading the full log or delegating a question that a targeted search can answer.

Search error headlines to classify the failure. `rg -n '^error' /tmp/cgp-error.txt` prints each
error code and named trait, helping identify the [shape](#the-two-shapes-to-recognize) and [error
class](macro-grammar.md).

Search the class’s signature to test the suspected cause. Use `help:` for a surfaced dependency,
`conflicting implementation` for a duplicate key, `overflow evaluating` for a cycle,
`does not contain any DelegateComponent entry` for absent wiring, or `is not constrained` for an
unconstrained generic. A `HasField<Symbol<…>>` line spells out the field name character by
character. The [debugging guide’s search
table](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/guides/debugging.md#grep-for-the-suspected-line-instead-of-reading-the-whole-log)
lists signatures for the full set of classes.

Add a check before searching further when the error is hidden. An `E0599` headline without a nested
dependency requires a new diagnostic, not a broader search.

Delegate a long, open-ended analysis when targeted searches cannot resolve it. Several unrelated
error classes or a relevant type abbreviated as `...` may require the full log and its
`long-type-….txt` files. Give that material to a
[sub-agent](#delegating-the-extraction-to-a-sub-agent) for a compact summary.

## Extracting an error yourself

Return a [compact summary](#reduce-to-the-compact-summary) when reading raw output yourself. This
applies both to a sub-agent assigned the analysis and to a main agent reading a short error. Do not
return the raw log.

### Capture the output without flooding context

Capture the smallest build or test that reproduces the failure. A single crate, test, example, or
small scratch module limits repeated errors across unrelated code. Save its compiler output to a
file for targeted reading and keep the full log out of the agent transcript. These commands use
`tee` to save and print the output; use direct file redirection when terminal output would enter
the transcript:

```bash
# Target the smallest failing unit and redirect everything to a scratch file.
cargo check -p <your-crate> 2>&1 | tee /tmp/cgp-error.txt

# or a single test / example that exercises the failing wiring:
cargo test -p <your-crate> --test <target> 2>&1 | tee /tmp/cgp-error.txt
```

Read the compiler’s long-type file when an abbreviated type hides a relevant context or path. Rust
names the file in a final note such as “the full name for the type has been written to …”. The
missing middle of the type may distinguish the failing dependency.

Treat a contradictory-looking `help:` note as evidence of conditional or ambiguous impls. If the
error says `X` is not implemented for `T` while a note lists such an impl, that impl may have an
unmet nested bound or compete with another candidate. The note does not establish that the
requirement is satisfied.

Inspect the macro expansion when the failure depends on generated code. Prefer `cargo cgp expand`,
which restores readable CGP notation such as `Symbol!("height")` in place of expanded `Chars` lists.
Filter the expansion to the relevant item or save it to a file:

```sh
cargo cgp expand --lib --item AreaCalculator     # a trait: every impl of it (what a component generated)
cargo cgp expand --lib --item contexts::MockApp  # a type: its HasField impls and its wiring entries
cargo cgp expand --lib > /tmp/expanded.rs        # or redirect the whole thing and grep it
```

Select `--lib` or `--bin NAME` when the package has several targets. Use plain `cargo expand` if
`cargo cgp expand` is unavailable; it shows the expansion without restoring CGP notation. In
projects using CGP test utilities, `snapshot_*!` helpers from `cgp-macro-test-util` also record
expansions for review. See [macro-grammar](macro-grammar.md) for interpreting the generated impls.

### Reduce to the compact summary

Summarize the diagnostic with the facts needed to decide the next action:

- **Class and code:** Record the error codes and named traits, such as `E0277` through
  `CanUseComponent`, `E0119` on `DelegateComponent`, or `E0207` for an unconstrained generic.
- **Hidden or surfaced:** State whether the output contains the root cause.
- **Root cause and location:** Name the concrete failed bound and where it appears, such as a
  `help:` note, a later error block, or a long-type file. State explicitly when the cause is hidden.
- **Next action:** Identify the relevant fix or diagnostic step: supply a dependency, add a check,
  break a cycle, or remove a duplicate key.

Keep the summary to a few lines. Include the relevant bound and evidence without reproducing the
compiler transcript.

## Delegating the extraction to a sub-agent

Delegate long error logs to a sub-agent and request only the [compact
summary](#reduce-to-the-compact-summary). This applies to deep dependency failures, errors repeated
across crates, and output too long to justify reading in the main context.

Give the sub-agent the captured log’s path or the exact reproduction command, this reference, and
the required summary format. The same workflow supports documenting an error class and diagnosing a
failure during development. If the summary identifies a hidden error, add a check and rerun; that
follow-up can also be delegated.

## Further reference

Use these references to interpret the error and choose a follow-up:

- [Checking](checking.md): Lazy wiring and checks that expose missing dependencies.
- [Macro grammar](macro-grammar.md): Error classes and generated impls.
- [Wiring](wiring.md): Delegation rules behind conflicts and cycles.
- [Error catalog](https://github.com/contextgeneric/cgp-knowledge-base/tree/main/cgp/errors):
  Documented error classes and the locations of their root causes.
- [Debugging guide](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/guides/debugging.md):
  The complete procedure for tracing failures.
