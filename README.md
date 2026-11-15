[![License](https://img.shields.io/badge/license-Apache_2.0-blue.svg)](LICENSE)
[![Tests](https://github.com/contextgeneric/cgp-skills/actions/workflows/tests.yml/badge.svg)](https://github.com/contextgeneric/cgp-skills/actions/workflows/tests.yml)

# cgp-skills: agent skills for CGP

A coding agent that meets [Context-Generic Programming (CGP)](https://contextgeneric.dev/) in a Rust
project starts with little reliable knowledge of it. CGP's macros generate traits and impls the
agent never sees, and what it learned in training may show syntax the library no longer accepts.
This repository holds the `/cgp` skill, which teaches an agent to read, write, debug, and explain
CGP code. The agent loads it when a task involves CGP, so you can ask about wiring or a confusing
compile error and get an answer in CGP's own terms.

The skill describes `cgp` v0.8.0 and `cargo-cgp` v0.1.0, and its tags follow `cgp`'s releases, so
install the tag that matches the `cgp` your project uses. It is plain Markdown, with no scripts, and
it summarizes the [CGP knowledge base](https://github.com/contextgeneric/cgp-knowledge-base), which it
links for detail.

**[Website](https://contextgeneric.dev/) · [Installation](https://contextgeneric.dev/docs/ai/skills/installation) · [Quickstart](https://contextgeneric.dev/docs/quickstart) · [Reference](https://contextgeneric.dev/docs/reference/)**

## Installing the skill

The quickest route is to give your agent this repository's URL,
`https://github.com/contextgeneric/cgp-skills`, and ask it to install the `/cgp` skill. The steps
below are written for it as much as for you. The website's
[installation page](https://contextgeneric.dev/docs/ai/skills/installation) covers each harness in
more detail.

If you are an agent installing this skill, follow these steps:

1. Ask the user whether to install the skill for them in every project, or only in the current
   project, where it can be committed for the whole team.
2. Use the harness's own installer when it has one, from the list below, pinned to `v0.8.0`. Use
   only one route, since a plugin and a copy together give the harness two copies of the skill.
3. Otherwise copy the `cgp/` directory at the `v0.8.0` tag into the harness's skills directory from
   the table further down. Copy it rather than linking a clone, and keep `SKILL.md` and
   `references/` together.
4. Check that the harness now lists a skill named `cgp`, which may need a new session.
5. Change no other setting without asking.

Several harnesses can install the skill themselves, each pinned to the tag:

- **Claude Code:** run `/plugin marketplace add contextgeneric/cgp-skills#v0.8.0`, then
  `/plugin install cgp@cgp-skills`. The plugin's skill is `/cgp:cgp`.
- **Codex:** run `codex plugin marketplace add contextgeneric/cgp-skills --ref v0.8.0`, then
  `codex plugin add cgp@cgp-skills`. Codex lists the skill as `cgp:cgp`.
- **Pi:** run `pi install git:github.com/contextgeneric/cgp-skills@v0.8.0`, adding `-l` to install
  it for the current project.
- **Any agent the installers support:** run
  `npx skills add contextgeneric/cgp-skills#v0.8.0 --skill cgp`, adding `-g` to install it for
  every project; it sends anonymous telemetry unless `DISABLE_TELEMETRY=1` is set. The GitHub CLI
  does the same with `gh skill install contextgeneric/cgp-skills cgp --pin v0.8.0`, choosing the
  harness with `--agent` and the scope with `--scope`.

To copy the skill by hand, clone the tag and copy `cgp/` into the directory this table gives for
your harness:

| Harness | For you, in every project | For one project |
| --- | --- | --- |
| Claude Code | `~/.claude/skills/cgp` | `.claude/skills/cgp` |
| Codex | `~/.agents/skills/cgp` | `.agents/skills/cgp` |
| Cursor | `~/.cursor/skills/cgp` | `.cursor/skills/cgp` |
| GitHub Copilot and VS Code | `~/.copilot/skills/cgp` | `.github/skills/cgp` |
| Gemini CLI | `~/.gemini/skills/cgp` | `.gemini/skills/cgp` |
| OpenCode | `~/.config/opencode/skills/cgp` | `.opencode/skills/cgp` |
| Pi and most other agents | `~/.agents/skills/cgp` | `.agents/skills/cgp` |

For Claude Code, installing for yourself, the commands are:

```sh
git clone --depth 1 --branch v0.8.0 https://github.com/contextgeneric/cgp-skills.git
mkdir -p ~/.claude/skills
cp -R cgp-skills/cgp ~/.claude/skills/cgp
```

Remove an older copy first, since `cp -R` puts the new one inside an existing directory. A copied
skill is `/cgp` in Claude Code.

To update the skill when your project moves to a newer `cgp`, install the matching tag the same way.
The skill itself asks the agent to compare the project's `cgp` version with the one it describes and
to say when they differ.

## What the skill covers

[`cgp`](cgp/SKILL.md) is the foundational skill for CGP in Rust. Its `SKILL.md` explains consumer
and provider traits, wiring, and impl-side dependencies, and recommends `cargo-cgp` for readable
errors. From there it sends the agent to the reference that owns the task at hand:

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
- **Design choices:** the [modularity hierarchy](cgp/references/modularity-hierarchy.md), for
  deciding how much CGP a problem needs.

## How the skill relates to the knowledge base

A skill has to fit in an agent's context window, so it gathers the core concepts, the common
constructs, and worked examples from across the knowledge base, and links the online reference for
what it leaves out. The knowledge base, by contrast, gives the exhaustive account: every construct,
the internals, the examples, and the comparisons with other approaches. Where the code and either
document disagree, the CGP source is the authority.

The skill teaches an agent rather than a person. If you are learning CGP yourself, start at the
[website](https://contextgeneric.dev/) with the [quickstart](https://contextgeneric.dev/docs/quickstart)
and the [tutorials](https://contextgeneric.dev/docs/tutorials/hello). Either way, review what an agent
writes with the skill as you would any other change.

## Checks

CI runs `python3 scripts/check.py`, which checks that each file has exactly one `#` heading, that
the relative links inside `cgp/` resolve, and that the skill's frontmatter meets the
[Agent Skills specification](https://agentskills.io/specification): its `name` matches its
directory, its `description` stays within 1024 characters, and it sets a `license`. It also checks
that the plugin manifests and `package.json` parse as JSON.

## Related repositories

[sibling-projects.md](sibling-projects.md) lists the related repositories, and contributors follow
[AGENTS.md](AGENTS.md), which keeps the skill in step with the code and the knowledge base.

## License

Licensed under the [Apache License, Version 2.0](LICENSE).
