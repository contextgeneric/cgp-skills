# AGENTS.md — the CGP agent skills

This file governs how to write and maintain the skills in this repository. Read [README.md](README.md)
first for what a skill is and how it relates to the knowledge base, and
[sibling-projects.md](sibling-projects.md) for the related repositories and where to find them.

A skill here is a distilled synthesis of the
[CGP knowledge base](https://github.com/contextgeneric/cgp-knowledge-base) — one `SKILL.md` carrying
the mental model and a router, plus a `references/` set of sub-skills, one per topic area, each giving
enough detail and worked examples to make an agent proficient in that area without further lookup. It
is deliberately lighter than a knowledge-base document: it teaches how to read and write CGP, not
every corner case.

## The knowledge base is the source of truth

**A skill must never teach syntax the code no longer has.** The CGP source is the single source of
truth, the knowledge base is the exhaustive record of what that source means, and a skill is the
distilled view of the base — so when the three disagree, the code wins and the skill is what gets
corrected. Because the skill is the most distilled view, it is also the easiest to leave stale.

When a construct's syntax, expansion, defaults, or recommended form changes, revise the skill in the
same change as the code and the knowledge base:

- the affected sub-skill under `cgp/references/`;
- the router and reading cheat-sheet in `cgp/SKILL.md`, when the change touches a core construct;
- the triggering `description` in the front matter, when you add or rename a construct an agent should
  recognize by name.

When a form becomes legacy — as `UseDelegate`/`#[derive_delegate]` did when the `open` statement became
the preferred dispatch — the skill leads with the current form and keeps the legacy one only as a
clearly-labeled note for *reading* existing code, mirroring how the knowledge base's reference
documents treat it. When the knowledge-base checkout is absent, state plainly what needs updating there.

## A skill must be self-contained

A skill is copied out of this repository and run on its own, so **no relative link may point outside
its own directory** — not to a knowledge-base path, not to a repository path, because those targets
will not exist where the skill runs. Cross-links between sub-skills are plain relative filenames
(`[wiring](wiring.md)`). For the exhaustive detail a skill deliberately omits, link to the online
knowledge base as an absolute URL
(`https://github.com/contextgeneric/cgp-knowledge-base/blob/main/<path>` for a file, `…/tree/main/<path>`
for a directory) and ask the agent to fetch it when needed, rather than assuming a local copy. The same
holds for the tool: link `cargo-cgp`'s documentation in the knowledge base, not a relative path.

## Verify against the source

Verify a skill against the code the same way a knowledge-base document is verified: every snippet must
reflect current CGP syntax, and when you doubt a form, compile a representative snippet against the
crates — a scratch test under
[crates/tests/cgp-tests](https://github.com/contextgeneric/cgp/tree/main/crates/tests/cgp-tests) is the
quickest check — rather than trusting memory or an older draft. A skill records the version it is
written for, so update that statement when the library moves and check the claims that depend on it.

## Vocabulary and prose

Use the knowledge base's vocabulary exactly — consumer trait, provider trait, provider, wiring,
impl-side dependency, component, context — so an agent moving between a skill and the documents never
reconciles two dialects. Write in the dual-reader prose style (the `/dual-reader-prose` skill): open
every section with a self-contained topic sentence, frame every list, and let the prose around a code
block carry the meaning on its own. Keep the backticks well formed — an inline code span opened and
closed on the same line, fenced blocks delimited by their own triple-backtick lines — and re-check them
after every edit, since a skill is read verbatim by the agent that loads it.

## Committing changes

Git commits are made **only when the user explicitly asks for one**, and each such request authorizes
exactly one commit of the changes then in the working tree. Do not commit as a side effect of finishing
a task, do not bring commits up yourself, and do not treat one commit request as a standing mode.
Commit onto whatever branch is checked out.
