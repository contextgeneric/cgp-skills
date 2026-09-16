# Skills for Context-Generic Programming (CGP) in Rust

This repository provides [agent skills](https://agentskills.io/) for reading, writing, debugging,
and explaining [Context-Generic Programming](https://contextgeneric.dev/) (CGP) in Rust. Each
skill is a self-contained guide that an LLM coding agent loads as needed. It teaches the core
concepts and directs the agent to topic references, so the agent can work without loading the
whole knowledge base.

The skills summarize the [CGP knowledge base](https://github.com/contextgeneric/cgp-knowledge-base),
which documents the CGP ecosystem. Each skill can be copied to wherever an agent runs, so it must
work without files outside its own directory. [sibling-projects.md](sibling-projects.md) lists the
related repositories, and [AGENTS.md](AGENTS.md) defines how to keep skills accurate and current.

## The catalog

[`cgp`](cgp/SKILL.md) is the foundational skill for CGP in Rust and the skill that `/cgp` resolves
to. Its `SKILL.md` explains consumer and provider traits, wiring, and impl-side dependencies, then
directs the agent to the relevant [topic references](cgp/references/).

The references cover these areas:

- **Core constructs:** Components, wiring, checking, functions and getters, abstract types, and
  higher-order providers.
- **Supporting constructs:** Error handling, handlers, extensible data, namespaces, and type-level
  primitives.
- **Syntax and diagnosis:** Modern idioms, macro grammar, and error extraction.
- **Design choices:** The modularity hierarchy and how much CGP a problem needs.

## How a skill differs from the knowledge base

A skill gives an agent enough guidance to act within its context window. It combines core concepts,
common constructs, and worked examples from across the knowledge base, then links to the online
reference for details it omits. Knowledge-base documents provide exhaustive accounts of individual
constructs, subsystem internals, worked examples, and comparisons with other paradigms.

The knowledge base supplies the documentation from which skills are derived. Keep each skill in
sync with it: when a CGP construct changes, update the knowledge base and the matching topic
reference in the same change, as [AGENTS.md](AGENTS.md) requires. The CGP source remains authoritative
when the code and documentation disagree.

## Using a skill

Point your agent harness at this repository and expose `cgp/` as a skill directory. The `/cgp`
skill then loads for tasks involving CGP code.

The skill assumes only Rust knowledge and teaches the vocabulary used throughout the CGP
documentation: consumer trait, provider trait, provider, wiring, impl-side dependency, and context.
An agent can then consult the knowledge base using the same terms.
