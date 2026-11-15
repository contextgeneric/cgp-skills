#!/usr/bin/env python3
"""Check the rules `AGENTS.md` and the Agent Skills specification set for this repository.

These rules are checked:

- Every Markdown file carries exactly one `#` heading, with `##` or deeper
  headings for its sections. Fenced code blocks are skipped, so a `#` comment
  inside an example does not count.
- Every relative link resolves, and a link in the skill directory stays inside
  `cgp/`, so the skill stays self-contained.
- The skill's frontmatter names the skill after its directory, keeps its
  `description` within the specification's 1024 characters, and sets `license`.
- The plugin manifests and `package.json`, where they exist, parse as JSON and
  agree with the skill: `plugin.json` and `package.json` carry the same
  `version`, each `skills` path names a directory holding a `SKILL.md`, and
  each manifest's description is the first sentence of the skill's.

The script uses only the Python standard library, so a runner needs no install.
It reads the frontmatter's simple `key: value` lines and folded `>` or `|`
blocks itself rather than through a YAML library.
Run it from the repository root or from anywhere: it locates the root itself.

Usage: python3 scripts/check.py
"""

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / "cgp"
MANIFESTS = [
    ROOT / ".claude-plugin" / "plugin.json",
    ROOT / ".claude-plugin" / "marketplace.json",
    ROOT / "package.json",
]
MAX_DESCRIPTION = 1024

FENCE = re.compile(r"^(\s*>?\s*)(```|~~~)")
H1 = re.compile(r"^# ")
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
KEY = re.compile(r"^([A-Za-z][\w-]*):\s*(.*)$")


def prose_lines(text):
    """Yield (line number, line) for the lines outside fenced code blocks."""
    in_fence = False
    for number, line in enumerate(text.splitlines(), start=1):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            yield number, line


def check_headings(path, failures):
    count = sum(1 for _, line in prose_lines(path.read_text()) if H1.match(line))
    if count != 1:
        failures.append(
            f"{path.relative_to(ROOT)}: {count} `#` headings, expected exactly 1"
        )


def check_links(path, failures):
    inside = SKILL if SKILL in path.parents else ROOT
    for number, line in prose_lines(path.read_text()):
        for target in LINK.findall(line):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            resolved = (path.parent / target.split("#")[0]).resolve()
            where = f"{path.relative_to(ROOT)}:{number}"
            if not resolved.exists():
                failures.append(f"{where}: broken link {target}")
            elif resolved != inside and inside not in resolved.parents:
                failures.append(f"{where}: link leaves {inside.name}/: {target}")


def frontmatter(text):
    """Return the frontmatter's top-level keys and values, or None without one.

    A folded block (`>`, `>-`) joins its lines with spaces and a literal block
    (`|`, `|-`) with newlines, as YAML does for single-paragraph text.
    """
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        return None
    try:
        end = lines.index("---", 1)
    except ValueError:
        return None
    fields = {}
    key = None
    block = []
    style = None

    def close():
        if key is not None and style is not None:
            fields[key] = (" " if style == ">" else "\n").join(block)

    for line in lines[1:end]:
        if style is not None and (line.startswith((" ", "\t")) or not line.strip()):
            if line.strip():
                block.append(line.strip())
            continue
        close()
        key, style, block = None, None, []
        match = KEY.match(line)
        if not match:
            continue
        key, value = match.groups()
        if value[:1] in (">", "|"):
            style = value[0]
        else:
            fields[key] = value.strip().strip("\"'")
    close()
    return fields


def check_frontmatter(failures):
    """Check the skill's frontmatter and return its fields, or None without any."""
    path = SKILL / "SKILL.md"
    where = path.relative_to(ROOT)
    fields = frontmatter(path.read_text())
    if fields is None:
        failures.append(f"{where}: no frontmatter")
        return None
    if fields.get("name") != SKILL.name:
        failures.append(
            f"{where}: name {fields.get('name')!r} differs from its directory {SKILL.name!r}"
        )
    description = fields.get("description", "")
    if not description:
        failures.append(f"{where}: no description")
    elif len(description) > MAX_DESCRIPTION:
        failures.append(
            f"{where}: description has {len(description)} characters, "
            f"over the limit of {MAX_DESCRIPTION}"
        )
    if not fields.get("license"):
        failures.append(f"{where}: no license")
    return fields


def first_sentence(text):
    end = text.find(". ")
    return text if end < 0 else text[: end + 1]


def check_manifests(fields, failures):
    loaded = {}
    for path in MANIFESTS:
        if not path.exists():
            continue
        try:
            loaded[path] = json.loads(path.read_text())
        except json.JSONDecodeError as error:
            failures.append(f"{path.relative_to(ROOT)}: invalid JSON: {error}")
    plugin = loaded.get(MANIFESTS[0])
    marketplace = loaded.get(MANIFESTS[1])
    package = loaded.get(MANIFESTS[2])

    if plugin and package and plugin.get("version") != package.get("version"):
        failures.append(
            f"version differs: plugin.json {plugin.get('version')!r}, "
            f"package.json {package.get('version')!r}"
        )

    skill_paths = []
    if plugin:
        skill_paths += [("plugin.json", p) for p in plugin.get("skills", [])]
    if package:
        skill_paths += [("package.json", p) for p in package.get("pi", {}).get("skills", [])]
    for name, target in skill_paths:
        if not (ROOT / target / "SKILL.md").is_file():
            failures.append(f"{name}: skills path {target!r} holds no SKILL.md")

    if not fields or not fields.get("description"):
        return
    expected = first_sentence(fields["description"])
    descriptions = []
    if plugin:
        descriptions.append(("plugin.json", plugin.get("description")))
    if package:
        descriptions.append(("package.json", package.get("description")))
    if marketplace:
        for entry in marketplace.get("plugins", []):
            descriptions.append(
                (f"marketplace.json plugin {entry.get('name')!r}", entry.get("description"))
            )
    for name, description in descriptions:
        if description != expected:
            failures.append(
                f"{name}: description {description!r} differs from the skill's first "
                f"sentence {expected!r}"
            )


def main():
    failures = []
    files = sorted(p for p in ROOT.rglob("*.md") if ".git" not in p.parts)
    for path in files:
        check_headings(path, failures)
        check_links(path, failures)
    fields = check_frontmatter(failures)
    check_manifests(fields, failures)
    for failure in failures:
        print(failure)
    print(
        f"{len(files)} Markdown files and the skill's frontmatter checked, "
        f"{len(failures)} problems"
    )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
