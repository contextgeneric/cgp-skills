# Versions: matching this skill to the project's CGP

This skill is installed from the `main` branch of
[cgp-skills](https://github.com/contextgeneric/cgp-skills), which is updated between CGP releases
and keeps supporting every `cgp` release from the oldest one below. Compare the project's versions
with this table whenever version-specific guidance matters, such as when writing new code, when an
example fails to compile, or when the user asks:

| Item | Version |
| --- | --- |
| Oldest supported `cgp` | v0.8.0 |
| Newest `cgp` release described | v0.8.0 |
| Newest `cargo-cgp` release described | v0.1.0 |

Read the project's `cgp` version from its `Cargo.lock` entry, or from the requirement in
`Cargo.toml` when there is no lock file, and the tool's from `cargo cgp --version`. Then follow the
case that matches. Tell the user what you found and the command that would act on it, but run no
update of the project, the tool, or this skill without the user's approval.

## The project's `cgp` is older than v0.8.0

This skill does not support it. Much of its syntax differs from what the older release accepts, so
treat the skill's examples as unverified for that project. Read the CGP source at the project's
version, the `cgp` crate on docs.rs for that version, or the
[CGP knowledge base](https://github.com/contextgeneric/cgp-knowledge-base) where the code needs
them, and trust the source where they disagree with this skill.

## The project's `cgp` is on a line a notice below drops

A breaking change can end this skill's support for an older line. Each such line gets a row here,
naming the tag of `cgp-skills` that last supported it. Tell the user to install the skill from that
tag for this project, with their route's command and the tag in place of `main`.

| `cgp` line | Install the skill from tag |
| --- | --- |
| none | none |

## The project's `cgp` is older than the newest release described

A newer `cgp` exists. Mention it once in the session, in passing, and not again once the user
chooses to stay. A patch release within the same minor line updates with `cargo update -p cgp`; a
newer minor release, such as v0.9.0 for a project on v0.8.x, needs the requirement in `Cargo.toml`
changed, for example with `cargo add cgp@0.9`, and may need code changes, which the changes listed
below describe.

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

Tell which route installed the skill from where its `SKILL.md` sits, then from the tools' own lists,
and ask the user when neither settles it:

- **Claude Code plugin:** the skill sits under `~/.claude/plugins/cache/cgp-skills/`. Run
  `claude plugin marketplace update cgp-skills`, then `claude plugin update cgp@cgp-skills`, and
  start a new session.
- **Codex plugin:** the skill sits under `~/.codex/plugins/cache/cgp-skills/`. Run
  `codex plugin marketplace upgrade cgp-skills`, then `codex plugin add cgp@cgp-skills`.
- **`gh skill`:** `SKILL.md`'s frontmatter carries the metadata `gh skill` adds, and
  `gh skill list` shows it. Run `gh skill update cgp`.
- **`npx skills`:** `npx skills list`, or `npx skills list -g` for a global install, shows it. Run
  `npx skills update cgp`, adding `-g` for a global install.
- **Pi package:** `pi list` shows `cgp-skills`. Run `pi update --extensions`.
- **A copy:** none of the above. Replace the skill's directory with a fresh copy of `cgp/` from
  `main`, removing the old directory first.

## Changes since v0.8.0

Guidance that differs between supported releases is marked where it appears with the release that
introduced it, as in "Since `cgp` v0.9.0:", beside the older form. Each such change is listed here,
newest first.

- none
