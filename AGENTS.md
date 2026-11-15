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
- Apply point-first writing to internal prose, and natural writing to public-facing documents
  such as READMEs.

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

Each snippet matches the code the skill describes, and each installation path matches the website:

- Compile a representative snippet when syntax is uncertain.
- Keep the README's installation paths and the website's installation page in agreement.

## Versions

Readers install the skill from `main`, so keep `main` correct for every `cgp` release from the
oldest that [cgp/references/versions.md](cgp/references/versions.md) names:

- Where a release changes a form, mark the newer form with the release that introduced it, as in
  "Since `cgp` v0.9.0:", keep the older form beside it, and list the change in the reference.
- At each `cgp` or `cargo-cgp` release, update the reference's table, the versions `SKILL.md`
  states, and the `cargo-cgp` tag in its Nix commands. At each `cgp` release, also tag the skill as
  `vX.Y.Z`.
- Ask the user before dropping support for an older line. Then raise the oldest supported version,
  and add a notice row naming the tag of the last commit that supported that line.
- Name `main` in every installation instruction, never a tag; only a notice row names one.
- Leave `version` out of `.claude-plugin/plugin.json` and `package.json`, so a plugin install takes
  every commit as an update.

## Prose

Markdown must render the same in every harness that loads the skill:

- Check Markdown after every edit: keep inline code spans on one line and delimit fenced blocks with
  triple backticks on their own lines.

## Committing

A commit request covers the working tree as it stands:

- Treat a commit request as one commit of the changes then in the working tree.
