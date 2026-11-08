#!/usr/bin/env python3
"""Check the rules `AGENTS.md` states for the Markdown in this repository.

Two rules are checked:

- Every file carries exactly one `#` heading, with `##` or deeper headings for
  its sections. Fenced code blocks are skipped, so a `#` comment inside an
  example does not count.
- Every relative link resolves, and a link in the skill directory stays inside
  `cgp/`, so the skill stays self-contained.

The script uses only the Python standard library, so a runner needs no install.
Run it from the repository root or from anywhere: it locates the root itself.

Usage: python3 scripts/check.py
"""

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / "cgp"

FENCE = re.compile(r"^(\s*>?\s*)(```|~~~)")
H1 = re.compile(r"^# ")
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


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


def main():
    failures = []
    files = sorted(p for p in ROOT.rglob("*.md") if ".git" not in p.parts)
    for path in files:
        check_headings(path, failures)
        check_links(path, failures)
    for failure in failures:
        print(failure)
    print(f"{len(files)} files checked, {len(failures)} problems")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
