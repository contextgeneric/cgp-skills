# Sibling projects

The Context-Generic Programming ecosystem is split across several repositories that are developed
together. This file records where each one lives and which revision of it to read. An agent working
here often needs one of them, whether to verify a claim against another project's source, to revise
a document that a change here affects, or to keep a fixture and the prose that describes it in step.
Treat this table as the authoritative list of what exists alongside this repository.

The skills here distill the knowledge base, which is their source of truth. A change to a CGP
construct lands there first, and the matching sub-skill is revised in the same change.

| Project | Repository | Branch/tag to read | What it is |
|---|---|---|---|
| `cgp` | <https://github.com/contextgeneric/cgp> | `main` | The CGP library: the proc-macro suite and the runtime crates its expansions target. |
| `cargo-cgp` | <https://github.com/contextgeneric/cargo-cgp> | `main` | CGP's first-class toolchain: the cargo subcommand that makes CGP compile errors readable and expands CGP macros. |
| `cgp-knowledge-base` | <https://github.com/contextgeneric/cgp-knowledge-base> | `main` | The consolidated documentation for every CGP project, written by and for AI agents. |

## Finding a sibling

Look for a sibling in the parent directory first, at `../<project>`. Every project in this list,
including this one, should sit side by side under one parent directory in a local environment. So
`../cgp` is the fastest and most current reference, because it reflects uncommitted work that GitHub
does not. When the checkout is absent, fetch the file you need from the repository above instead, at
the revision the table records.

## Reading a sibling versus linking to one

Reading and linking follow different rules. When you **read** a document or a source file from a
sibling, use the branch or tag this table names, so every project sees the same revision of the
others. When you **link** to one from a committed file here, always write a GitHub URL on the `main`
branch (`https://github.com/contextgeneric/<project>/blob/main/<path>`), never a relative
`../<project>/...` path. The URL resolves for a reader who has only this repository checked out. A
bare mention of a checkout's location, like the path `../cgp`, is a filesystem reference rather than
a link, so it stays relative.

## Updating a revision

The branch or tag recorded above changes only on explicit instruction, such as when a project cuts
an official release and the ecosystem should pin it. During ordinary development every entry stays
`main`. It does not track a feature branch in progress, because work in flight is read from the
local sibling checkout, not from a revision recorded here. The same rule governs the `main` in a
cross-project link. Update it only when told to, as part of a release.
