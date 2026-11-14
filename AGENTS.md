# AGENTS.md: the CGP agent skills

Follow these rules for every change to this repository. Read [README.md](README.md) for what the
skills are and their checks, and [sibling-projects.md](sibling-projects.md) for the related
repositories.

## Universal rules

These rules hold in every CGP repository. The
[knowledge base's AGENTS.md](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/AGENTS.md)
holds their canonical wording: read it first, and change a rule there before updating this block:

- Learn CGP and its tools from the `/cgp` skill and the knowledge base; never restate them in this
  file.
- Prefer the local sibling checkout when reading another project.
- Write a cross-project link as a GitHub URL on `main`.
- Name official release versions only, never a pre-release.
- Commit only when the user explicitly asks, on the current branch.
- Verify a claim against the source before writing it.
- Keep every view of the same truth in sync in the same change.
- Ask the user when a decision is ambiguous.
- Apply point-first writing to internal prose.

## Task guides

The skill summarizes the knowledge base, so each kind of change starts from the document it
summarizes. Read it before the task:

- **Changing what the skill says about a construct:** the construct's document in the knowledge
  base's [construct reference](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/README.md).
- **Changing what the skill says about `cargo-cgp`:** the knowledge base's
  [cargo-cgp section](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cargo-cgp/README.md).
- **Checking the skill:** [README.md](README.md#checks).

## Headings

Each file is one Markdown document with one title:

- Use exactly one `#` per file, with `##` or deeper headings for sections.
- Count headings with a check that ignores fenced code blocks.

## Alignment

The skill changes with the code and the knowledge base, and teaches current syntax first:

- Update the affected sub-skill under `cgp/references/`, the routing guidance and reading cheat sheet
  in `cgp/SKILL.md`, and the front matter's `description` in the same change as the code and knowledge
  base.
- Lead with the current syntax and keep a legacy form only in a clearly labeled note for reading
  existing code.
- Follow the knowledge base's treatment of a legacy form.
- State what needs updating in the knowledge base when its checkout is absent.

## Self-containment

The skill is deployed on its own, so it links outside itself only by URL:

- Keep every relative link inside the skill's own directory.
- Link between sub-skills with plain relative filenames.
- Use absolute knowledge-base URLs for details, with `blob/main` for a file and `tree/main` for a
  directory, and instruct the agent to fetch them when needed.

## Verification

Each snippet and the version statement match the code the skill describes:

- Compile a representative snippet when syntax is uncertain.
- Record the CGP version the skill describes, and update the statement when the library advances.

## Prose

Markdown must render the same in every harness that loads the skill:

- Check Markdown after every edit: keep inline code spans on one line and delimit fenced blocks with
  triple backticks on their own lines.

## Committing

A commit request covers the working tree as it stands:

- Treat a commit request as one commit of the changes then in the working tree.
