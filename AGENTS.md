# AGENTS.md: the CGP agent skills

This file governs how to write and maintain the skills in this repository. Read
[README.md](README.md) first for what a skill is and how it relates to the knowledge base, and
[sibling-projects.md](sibling-projects.md) for the related repositories and where to find them.

A skill here is a distilled synthesis of the
[CGP knowledge base](https://github.com/contextgeneric/cgp-knowledge-base). It has one `SKILL.md`
that carries the mental model and a router, plus a `references/` set of sub-skills, one per topic
area. Each sub-skill gives enough detail and worked examples to make an agent proficient in that area
without further lookup. A skill is lighter than a knowledge-base document on purpose. It teaches how
to read and write CGP, not every corner case.

## One `#` per file

Each file carries exactly one top-level heading, its title, and everything below it is `##` or
deeper. This is ordinary Markdown hygiene, and here it also matters for publishing. These files are
published on <https://contextgeneric.dev>, whose renderer generates heading anchors for `h2` and `h3`
only. A section written as `#` gets neither an anchor nor a table-of-contents entry, so it cannot be
linked to.

Check it with a fence-aware count rather than `grep -c '^# '`. The plain grep counts the `#` comments
inside shell code blocks and reports a clean file as broken.

## The knowledge base is the source of truth

**A skill must never teach syntax the code no longer has.** The CGP source is the single source of
truth, the knowledge base is the exhaustive record of what that source means, and a skill is the
distilled view of the base. So when the three disagree, the code wins and the skill is corrected.
Because the skill is the most distilled view, it is also the easiest to leave stale.

When a construct's syntax, expansion, defaults, or recommended form changes, revise the skill in the
same change as the code and the knowledge base. The revision covers:

- the affected sub-skill under `cgp/references/`;
- the router and reading cheat-sheet in `cgp/SKILL.md`, when the change touches a core construct;
- the triggering `description` in the front matter, when you add or rename a construct an agent
  should recognize by name.

When a form becomes legacy, the skill leads with the current form and keeps the legacy one only as a
clearly labeled note for *reading* existing code. `UseDelegate` and `#[derive_delegate]` became legacy
this way when the `open` statement became the preferred dispatch. This mirrors how the knowledge
base's reference documents treat a legacy form. When the knowledge-base checkout is absent, state
plainly what needs updating there.

## A skill must be self-contained

A skill is copied out of this repository and run on its own, so **a relative link must never point
outside the skill's own directory**. A link to a knowledge-base path or a repository path will not
resolve where the skill runs. Cross-links between sub-skills are plain relative filenames, such as
`[wiring](wiring.md)`. For the exhaustive detail a skill leaves out, link to the online knowledge base
as an absolute URL (`https://github.com/contextgeneric/cgp-knowledge-base/blob/main/<path>` for a
file, `…/tree/main/<path>` for a directory) and ask the agent to fetch it when needed, rather than
assuming a local copy. The same holds for the tool: link `cargo-cgp`'s documentation in the
knowledge base, not a relative path.

## Verify against the source

Verify a skill against the code the same way a knowledge-base document is verified. Every snippet
must reflect current CGP syntax. When you doubt a form, compile a representative snippet against the
crates rather than trusting memory or an older draft. A scratch test under
[crates/tests/cgp-tests](https://github.com/contextgeneric/cgp/tree/main/crates/tests/cgp-tests) is
the quickest check. A skill records the version it is written for, so update that statement when the
library moves and check the claims that depend on it.

## Vocabulary and prose

Use the knowledge base's vocabulary exactly: consumer trait, provider trait, provider, wiring,
impl-side dependency, component, context. An agent moving between a skill and the documents should
never have to reconcile two dialects. Write in the point-first prose style (the
`/point-first-writing` skill): open every section with a self-contained topic sentence, frame every
list, and let the prose around a code block carry the meaning on its own. Keep the backticks well
formed, with an inline code span opened and closed on the same line and fenced blocks delimited by
their own triple-backtick lines. Re-check them after every edit, because the agent that loads a skill
reads it verbatim.

## Committing changes

Git commits are made **only when the user explicitly asks for one**, and each such request authorizes
exactly one commit of the changes then in the working tree. Do not commit as a side effect of
finishing a task, do not bring commits up yourself, and do not treat one commit request as a standing
mode. Commit onto whatever branch is checked out.
