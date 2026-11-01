#!/usr/bin/env python3
"""Validate handbook structure and local Markdown links."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
CHAPTERS = ROOT / "handbook"
CHAPTER_FILE = re.compile(r"^(?P<number>\d{2,3})-.+\.md$")
CHAPTER_TITLE = re.compile(r"^# Chapter (?P<number>\d+) — .+$")
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]+\]\((?P<destination>[^)]+)\)")


def markdown_files() -> list[Path]:
    return sorted(
        path
        for path in ROOT.rglob("*.md")
        if ".git" not in path.relative_to(ROOT).parts
    )


def link_target(destination: str) -> str:
    """Return the path portion of an inline Markdown link destination."""
    destination = destination.strip()
    if destination.startswith("<") and ">" in destination:
        destination = destination[1 : destination.index(">")]
    else:
        destination = destination.split(maxsplit=1)[0]
    return unquote(destination)


def check_chapter_titles(files: list[Path]) -> list[str]:
    errors: list[str] = []

    for path in files:
        if not path.is_relative_to(CHAPTERS):
            continue

        filename_match = CHAPTER_FILE.match(path.name)
        if not filename_match:
            errors.append(
                f"{path.relative_to(ROOT)}: chapter filename needs a two- or "
                "three-digit prefix"
            )
            continue

        lines = path.read_text(encoding="utf-8").splitlines()
        title = lines[0] if lines else ""
        title_match = CHAPTER_TITLE.match(title)
        if not title_match:
            errors.append(
                f"{path.relative_to(ROOT)}: first line must use '# Chapter N — Title'"
            )
            continue

        filename_number = int(filename_match.group("number"))
        title_number = int(title_match.group("number"))
        if filename_number != title_number:
            errors.append(
                f"{path.relative_to(ROOT)}: filename chapter {filename_number} "
                f"does not match title chapter {title_number}"
            )

    return errors


def check_local_links(files: list[Path]) -> list[str]:
    errors: list[str] = []

    for path in files:
        text = path.read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), start=1):
            for match in MARKDOWN_LINK.finditer(line):
                target = link_target(match.group("destination"))
                parsed = urlsplit(target)

                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue

                if parsed.path.startswith("/"):
                    resolved = ROOT / parsed.path.lstrip("/")
                else:
                    resolved = path.parent / parsed.path

                if not resolved.exists():
                    errors.append(
                        f"{path.relative_to(ROOT)}:{line_number}: "
                        f"local link target does not exist: {target}"
                    )

    return errors


def main() -> int:
    files = markdown_files()
    errors = check_chapter_titles(files) + check_local_links(files)

    if errors:
        print("Documentation checks failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Documentation checks passed for {len(files)} Markdown files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
