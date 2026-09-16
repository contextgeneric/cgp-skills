# AGENTS.md: the CGP agent skills

Follow this file when writing or maintaining skills in this repository. Read
[README.md](README.md) for the purpose and structure of a skill, then
[sibling-projects.md](sibling-projects.md) for the related repositories and their locations.

Each skill summarizes the [CGP knowledge base](https://github.com/contextgeneric/cgp-knowledge-base)
in a form that teaches an agent to read and write CGP. Its `SKILL.md` explains the core concepts
and directs the agent to topic sub-skills under `references/`. Each sub-skill provides enough detail
and worked examples for routine work without further lookup. The knowledge base supplies the
exhaustive details and corner cases.

## One `#` per file

Use exactly one top-level heading for the file's title, with `##` or deeper headings for sections.
These files are published on <https://contextgeneric.dev>, whose renderer generates heading anchors
only for `h2` and `h3`. A section written as `#` lacks both an anchor and a table-of-contents entry,
so readers cannot link to it.

Count headings with a check that ignores fenced code blocks. A plain `grep -c '^# '` also counts
shell comments inside those blocks and can incorrectly report extra headings.

## Keep skills aligned with the source and knowledge base

The CGP source is authoritative when code, knowledge-base documents, and skills disagree. The
knowledge base records what the source means, and skills summarize that record. Correct a skill
when it teaches syntax the code no longer supports.

Update the skill in the same change as the code and knowledge base whenever a construct's syntax,
expansion, defaults, or recommended form changes. Review these locations:

- **Topic reference:** Update the affected sub-skill under `cgp/references/`.
- **Primer and index:** Update the routing guidance and reading cheat sheet in `cgp/SKILL.md` when a
  core construct changes.
- **Trigger description:** Update the front matter's `description` when adding or renaming a
  construct an agent should recognize.

Lead with the current syntax and retain legacy forms only in clearly labeled notes for reading
existing code. For example, `UseDelegate` and `#[derive_delegate]` became legacy forms when `open`
became the preferred dispatch syntax. Follow the knowledge base's treatment of such forms. If its
checkout is absent, state what needs updating there.

## A skill must be self-contained

Keep every relative link within the skill's own directory because skills are copied and run
independently. Link between sub-skills with plain relative filenames, such as
`[wiring](wiring.md)`.

Use absolute URLs for details in the online knowledge base, including `cargo-cgp` documentation.
Link to files with `https://github.com/contextgeneric/cgp-knowledge-base/blob/main/<path>` and to
directories with `https://github.com/contextgeneric/cgp-knowledge-base/tree/main/<path>`. Instruct the
agent to fetch those details when needed without assuming a local checkout exists.

## Verify against the source

Verify each skill's claims and snippets against the current CGP code. When syntax is uncertain,
compile a representative snippet against the crates. A scratch test under
[crates/tests/cgp-tests](https://github.com/contextgeneric/cgp/tree/main/crates/tests/cgp-tests)
provides a quick check.

Record the CGP version the skill describes. When the library advances, update that statement and
verify the claims that depend on the version.

## Vocabulary and prose

Use the knowledge base's terms consistently: consumer trait, provider trait, provider, wiring,
impl-side dependency, component, and context. Consistent vocabulary lets agents move between a
skill and the knowledge base without reconciling different terms for the same concept.

Apply the `/point-first-writing` skill. Open each section with a self-contained topic sentence,
introduce each list, and make the prose around a code block explain its meaning without requiring
the reader to inspect the code.

Check Markdown syntax after every edit because agents read skill files verbatim. Open and close
each inline code span on the same line, and delimit fenced blocks with triple backticks on their
own lines.

## Committing changes

Commit only when the user explicitly requests it. Each request authorizes exactly one commit of
the changes then in the working tree, on the currently checked-out branch. Do not commit as a side
effect of completing a task, suggest a commit unprompted, or treat a previous request as continuing
authorization.
