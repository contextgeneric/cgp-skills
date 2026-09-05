# Skills for Context-Generic Programming (CGP) in Rust

This repository holds the [agent skills](https://agentskills.io/) for
[Context-Generic Programming](https://contextgeneric.dev/) (CGP) in Rust. A skill is a
self-contained guide that an LLM coding agent loads to read, write, debug, and explain CGP code. It
teaches enough to make the agent proficient without loading the whole knowledge base, and it is
organized for progressive disclosure, so the agent reads only the parts a task needs.

The skills are distilled from the [CGP knowledge base](https://github.com/contextgeneric/cgp-knowledge-base),
the consolidated documentation for every project in the CGP ecosystem. They live in their own
repository because a skill is deployed on its own: it is copied to wherever an agent runs, so it
cannot rely on any file outside its own directory. [sibling-projects.md](sibling-projects.md) lists
the related repositories, and [AGENTS.md](AGENTS.md) carries the rules for keeping a skill correct
and in sync with the base.

## The catalog

[`cgp`](cgp/SKILL.md) is the foundational skill for working with CGP in Rust, and the skill that
`/cgp` resolves to. Its `SKILL.md` establishes the paradigm (the consumer/provider trait split,
wiring, impl-side dependencies) and routes to the topic sub-skills under
[cgp/references/](cgp/references/). The sub-skills cover components, wiring, checking, functions and
getters, abstract types, higher-order providers, error handling, handlers, extensible data,
namespaces, the type-level primitives, the modern idioms, the macro grammar, error extraction, and
the modularity hierarchy.

## How a skill differs from the knowledge base

A skill is sized for an agent's context window, whereas a knowledge-base document is exhaustive. A
knowledge-base document explains one construct completely, one subsystem's internals, one worked
example, or one comparison with an outside paradigm. The skill draws on all of them and reproduces
none in full. It carries the mental model, the common constructs, and enough worked examples to act,
and it points to the online knowledge base for the corner cases it leaves out.

The relationship runs one way. The knowledge base is the source of truth, and a skill is a synthesis
kept in sync with it. Because the skill is the most distilled view, it is also the easiest to leave
stale. So a change to a CGP construct lands in the knowledge base and propagates to the matching
sub-skill in the same change, as [AGENTS.md](AGENTS.md) requires.

## Using a skill

Point your agent harness at this repository and expose `cgp/` as a skill directory. The `/cgp` skill
then loads on any task that involves CGP code. The skill assumes nothing but Rust. It teaches the
vocabulary that the rest of the CGP documentation uses (consumer trait, provider trait, provider,
wiring, impl-side dependency, context), so an agent that has read it can move into the knowledge base
without learning a second dialect.
