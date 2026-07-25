# Skills for Context-Generic Programming (CGP) in Rust

This repository contains the [agent skills](https://agentskills.io/) for using
[Context-Generic Programming](https://contextgeneric.dev/) (CGP) with agentic coding in Rust. A skill
is a self-contained guide an LLM coding agent loads to read, write, debug, and explain CGP code —
enough to become proficient without loading a whole knowledge base, organized for progressive
disclosure so the agent reads only the parts a task needs.

The skills are built from the [CGP knowledge base](https://github.com/contextgeneric/cgp-knowledge-base),
the consolidated documentation for every project in the CGP ecosystem, and they live in their own
repository for one concrete reason: a skill is *deployed on its own*, copied out to wherever an agent
runs, so it cannot rely on any file outside its own directory.
[sibling-projects.md](sibling-projects.md) lists the related repositories, and
[AGENTS.md](AGENTS.md) carries the rules for keeping a skill correct and in sync with the base.

## The catalog

- [`cgp`](cgp/SKILL.md) — the foundational skill for working with CGP in Rust. Its `SKILL.md`
  establishes the paradigm (the consumer/provider trait split, wiring, impl-side dependencies) and
  routes to a set of topic sub-skills under [cgp/references/](cgp/references/) covering components,
  wiring, checking, functions and getters, abstract types, higher-order providers, error handling,
  handlers, extensible data, namespaces, the type-level primitives, the modern idioms, the macro
  grammar, error extraction, and the modularity hierarchy. It is the skill `/cgp` resolves to.

## How a skill differs from the knowledge base

A skill is a *teaching artifact optimized for an agent's context window*, whereas a knowledge-base
document is an *exhaustive record*: one construct explained completely, one subsystem's internals, one
worked example, one comparison with an outside paradigm. The skill draws on all of them and reproduces
none wholesale — it carries the mental model, the common constructs, and worked examples in enough
depth to act, and points to the online knowledge base for the corner cases it deliberately omits.

The relationship is one-directional: the knowledge base is the source of truth, and a skill is a
synthesis kept in sync with it. Because the skill is the most distilled view, it is also the easiest to
leave stale, so a change to a CGP construct lands in the knowledge base and propagates out to the
matching sub-skill in the same change — the rule [AGENTS.md](AGENTS.md) spells out.

## Using a skill

Point your agent harness at this repository and expose `cgp/` as a skill directory; the `/cgp` skill
then loads on any task involving CGP code. The skill assumes nothing but Rust: it teaches the
vocabulary — consumer trait, provider trait, provider, wiring, impl-side dependency, context — that the
rest of the CGP documentation is written in, so an agent that has read it can move into the knowledge
base without reconciling two dialects.
