# AGENTS.md: the CGP agent skills

Read [README.md](README.md) and [sibling-projects.md](sibling-projects.md) before editing.

## Universal rules

The [knowledge base's AGENTS.md](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/AGENTS.md)
is the canonical wording. Read it first; change a universal rule there first, then update this
block to match. These are the actionable rules here:

- Prefer the local sibling checkout when reading another project.
- Write a cross-project link as a GitHub URL on `main`.
- Name official release versions only, never a pre-release.
- Commit only when the user explicitly asks, on the current branch.
- Verify a claim against the source before writing it.
- Keep every view of the same truth in sync in the same change.
- Ask the user when a decision is ambiguous.
- Apply point-first writing to internal prose.

## Versions

- The skill describes `cgp` v0.8.0 and `cargo-cgp` v0.1.0.
- Write as though the official versions shipped, and pin install commands and flake tags to them.

## Headings

- Use exactly one `#` per file, with `##` or deeper headings for sections.
- Count headings with a check that ignores fenced code blocks.

## Alignment

- Treat the CGP source as authoritative when the code, the knowledge base, and the skills disagree.
- Update the affected sub-skill under `cgp/references/`, the routing guidance and reading cheat sheet
  in `cgp/SKILL.md`, and the front matter's `description` in the same change as the code and knowledge
  base.
- Lead with the current syntax and keep a legacy form only in a clearly labeled note for reading
  existing code.
- Follow the knowledge base's treatment of a legacy form.
- State what needs updating in the knowledge base when its checkout is absent.

## Self-containment

- Keep every relative link inside the skill's own directory.
- Link between sub-skills with plain relative filenames.
- Use absolute knowledge-base URLs for details, with `blob/main` for a file and `tree/main` for a
  directory, and instruct the agent to fetch them when needed.

## Verification

- Verify each skill's claims and snippets against the current CGP code.
- Compile a representative snippet when syntax is uncertain.
- Record the CGP version the skill describes, and update the statement when the library advances.

## Prose

- Use the knowledge base's vocabulary: consumer trait, provider trait, provider, wiring, impl-side
  dependency, component, and context.
- Apply the `/point-first-writing` skill.
- Open each section with a self-contained topic sentence, introduce each list, and explain the code
  around a block.
- Check Markdown after every edit: keep inline code spans on one line and delimit fenced blocks with
  triple backticks on their own lines.

## Committing

- Treat a commit request as one commit of the changes then in the working tree.
- Do not commit as a side effect, suggest a commit unprompted, or treat a request as standing
  authorization.
