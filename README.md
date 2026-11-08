[![License](https://img.shields.io/badge/license-Apache_2.0-blue.svg)](LICENSE)
[![Tests](https://github.com/contextgeneric/cgp-skills/actions/workflows/tests.yml/badge.svg)](https://github.com/contextgeneric/cgp-skills/actions/workflows/tests.yml)

# cgp-skills: agent skills for CGP

**Agent skills for reading, writing, debugging, and explaining
[Context-Generic Programming (CGP)](https://contextgeneric.dev/) in Rust.**

Each skill is a self-contained guide that an LLM coding agent loads as needed. It teaches the core
concepts and directs the agent to topic references, so the agent can work without loading the whole
knowledge base. The skills summarize the
[CGP knowledge base](https://github.com/contextgeneric/cgp-knowledge-base), which documents the CGP
ecosystem.

**[Website](https://contextgeneric.dev/) · [Quickstart](https://contextgeneric.dev/docs/quickstart) · [Reference](https://contextgeneric.dev/docs/reference/) · [Agent skill pages](https://contextgeneric.dev/docs/ai/skills/)**

## The catalog

[`cgp`](cgp/SKILL.md) is the foundational skill for CGP in Rust and the skill that `/cgp` resolves
to. Its `SKILL.md` explains consumer and provider traits, wiring, and impl-side dependencies, then
directs the agent to the relevant topic references.

The references cover these areas:

- **Core constructs:** [components](cgp/references/components.md), [wiring](cgp/references/wiring.md),
  [checking](cgp/references/checking.md),
  [functions and getters](cgp/references/functions-and-getters.md),
  [abstract types](cgp/references/abstract-types.md), and
  [higher-order providers](cgp/references/higher-order-providers.md).
- **Supporting constructs:** [error handling](cgp/references/error-handling.md), the
  [error backends](cgp/references/error-backends.md), [handlers](cgp/references/handlers.md),
  [extensible data](cgp/references/extensible-data.md), [namespaces](cgp/references/namespaces.md),
  and [type-level primitives](cgp/references/type-level-primitives.md).
- **Syntax and diagnosis:** [modern idioms](cgp/references/modern-idioms.md),
  [macro grammar](cgp/references/macro-grammar.md), and
  [error extraction](cgp/references/error-extraction.md).
- **Design choices:** the [modularity hierarchy](cgp/references/modularity-hierarchy.md) and how much
  CGP a problem needs.

## How a skill differs from the knowledge base

A skill gives an agent enough guidance to act within its context window. It combines core concepts,
common constructs, and worked examples from across the knowledge base, then links to the online
reference for details it omits. Knowledge-base documents provide exhaustive accounts of individual
constructs, subsystem internals, worked examples, and comparisons with other paradigms.

The knowledge base supplies the documentation from which skills are derived. Keep each skill in sync
with it: when a CGP construct changes, update the knowledge base and the matching topic reference in
the same change, as [AGENTS.md](AGENTS.md) requires. The CGP source remains authoritative when the
code and documentation disagree.

## Using a skill

Point your agent harness at this repository and expose `cgp/` as a skill directory. The `/cgp` skill
then loads for tasks involving CGP code.

The skill assumes only Rust knowledge and teaches the vocabulary used throughout the CGP
documentation: consumer trait, provider trait, provider, wiring, impl-side dependency, and context.
An agent can then consult the knowledge base using the same terms.

A person learning CGP should start at the [website](https://contextgeneric.dev/) instead: the
[quickstart](https://contextgeneric.dev/docs/quickstart), the
[tutorials](https://contextgeneric.dev/docs/tutorials/hello), and the
[reference](https://contextgeneric.dev/docs/reference/) are written for readers, where these skills
are written for agents.

## Checks

CI runs `python3 scripts/check.py`, which checks that each file has exactly one `#` heading and that
the relative links inside `cgp/` resolve.

## Related repositories

[sibling-projects.md](sibling-projects.md) lists the related repositories, and
[AGENTS.md](AGENTS.md) defines how to keep skills accurate and current.

## License

Licensed under the [Apache License, Version 2.0](LICENSE).
