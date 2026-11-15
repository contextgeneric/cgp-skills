# Versions: matching this skill to the project's CGP

Compare the project's versions with this table before you write, change, or debug CGP code in it,
and whenever the user asks. The skill is installed from the `main` branch of
[cgp-skills](https://github.com/contextgeneric/cgp-skills), which is updated between CGP releases
and supports every `cgp` release from the oldest one below:

| Item | Version |
| --- | --- |
| Oldest supported `cgp` | v0.8.0 |
| Newest `cgp` release described | v0.8.0 |
| Newest `cargo-cgp` release described | v0.1.0 |

Follow the section below that matches the project's versions, and tell the user what you found and
the command that would act on it. Run no update of the project, the tool, or this skill without the
user's approval. Read the project's `cgp` version from its `Cargo.lock` entry, or from the
requirement in `Cargo.toml` when there is no lock file, and the tool's from `cargo cgp --version`.

## The project's `cgp` is older than v0.8.0

This skill does not support it. Older releases accept different syntax, so treat the skill's
examples as unverified for that project. Where the code needs it, read the CGP source at the
project's version, the `cgp` crate's documentation on docs.rs for that version, or the
[CGP knowledge base](https://github.com/contextgeneric/cgp-knowledge-base), and trust the source
where it disagrees with this skill.

## The project's `cgp` is on a line a notice below drops

A breaking change can end this skill's support for an older line. Each such line gets a row here,
naming the tag of `cgp-skills` that last supported it. Tell the user to install the skill from that
tag for this project, replacing the current install, with their route's form of the tag:

- **Claude Code:** `/plugin marketplace add contextgeneric/cgp-skills#<tag>`, after removing the
  plugin and the marketplace.
- **Codex:** `codex plugin marketplace add contextgeneric/cgp-skills --ref <tag>`, after removing
  them.
- **Pi:** `pi install git:github.com/contextgeneric/cgp-skills@<tag>`.
- **`npx skills` and `gh skill`:** `npx skills add contextgeneric/cgp-skills#<tag> --skill cgp`, or
  `gh skill install contextgeneric/cgp-skills cgp --pin <tag>`.
- **A copy, or Gemini CLI, which cannot pin a tag:** copy `cgp/` from
  `git clone --depth 1 --branch <tag> https://github.com/contextgeneric/cgp-skills.git`.

| `cgp` line | Install the skill from tag |
| --- | --- |
| none | none |

## The project's `cgp` is older than the newest release described

A newer `cgp` exists. Tell the user once in the session, at the start of your answer and naming the
release, and not again once the user chooses to stay.

Give the user the command that matches the release. A patch release within the same minor line
updates with `cargo update -p cgp`. A newer minor release, such as v0.9.0 for a project on v0.8.x,
needs the requirement in `Cargo.toml` changed, for example with `cargo add cgp@0.9`, and may need
code changes, which the changes listed below describe.

Write code for the project's version, not the newest. Use no form that a change below marks as
added after the project's version, and use the older form it replaces.

## The project's `cgp` is newer than the newest release described

The installed skill may be behind `main`. This also covers an unreleased `cgp`, such as a Git
dependency. Fetch this file from `main`:

```text
https://raw.githubusercontent.com/contextgeneric/cgp-skills/main/cgp/references/versions.md
```

- **`main` describes the project's version:** tell the user that a newer skill exists, and give the
  update command for the route that installed it, from [Updating the skill](#updating-the-skill).
- **`main` does not describe it either:** say that the skill has not caught up with this `cgp` yet.
  Trust the code, and read the CGP source and the knowledge base where a construct behaves
  differently from what the skill says.
- **The fetch fails:** say that the check could not run, and give the user the URL above to check.

## `cargo-cgp`

Compare `cargo cgp --version` with the newest `cargo-cgp` release in the table in the same way.
When the tool is older, `cargo cgp update` upgrades a cargo install, and a Nix install updates by
refreshing the flake, as `nix flake update cargo-cgp` does in a project whose flake has it as an
input. When the tool is newer, fetch this file from `main` as above.

## Updating the skill

Give the update command for the route that installed the skill. Identify the route from where its
`SKILL.md` sits, then from the tools' own lists, and ask the user when neither settles it:

- **Claude Code plugin:** the skill sits under `plugins/cache/cgp-skills/` in Claude Code's
  configuration folder, `~/.claude` by default. Run
  `claude plugin marketplace update cgp-skills`, then `claude plugin update cgp@cgp-skills`, and
  start a new session.
- **Codex plugin:** the skill sits under `plugins/cache/cgp-skills/` in Codex's home, `~/.codex` by
  default. Run
  `codex plugin marketplace upgrade cgp-skills`, then `codex plugin add cgp@cgp-skills`.
- **`gh skill`:** `SKILL.md`'s frontmatter carries the metadata `gh skill` adds, and
  `gh skill list` shows it. Run `gh skill update cgp`.
- **`npx skills`:** `npx skills list`, or `npx skills list -g` for a global install, shows it. Run
  `npx skills update cgp`, adding `-g` for a global install.
- **Pi package:** `pi list` shows `cgp-skills`. Run `pi update --extensions`.
- **Gemini CLI:** `gemini skills list` shows it. It has no update command, so run
  `gemini skills uninstall cgp`, then install it again with `gemini skills install`.
- **A copy:** none of the above. Replace the skill's directory with a fresh copy of `cgp/` from
  `main`, removing the old directory first.

## Changes since v0.8.0

Guidance that differs between supported releases is marked where it appears with the release that
introduced it, as in "Since `cgp` v0.9.0:", beside the older form. Each such change is listed here,
newest first.

- none
