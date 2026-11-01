#!/usr/bin/env python3
"""Build the searchable Developer Handbook website with MkDocs Material."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

import yaml


ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "SUMMARY.md"
BUILD = ROOT / "build"
STAGING = BUILD / "site-src"
OUTPUT = BUILD / "site"
CONFIG = BUILD / "mkdocs.generated.yml"
PROJECT_URL = "https://github.com/superflyad/Developer-handbook"
SITE_URL = "https://superflyad.github.io/Developer-handbook/"

SECTION = re.compile(r"^## (?P<title>.+?)\s*$")
LINK = re.compile(r"^\s*(?:[-*]|\d+\.)\s+\[(?P<title>[^]]+)]\((?P<target>[^)]+)\)")
INLINE_LINK = re.compile(
    r"(?<!!)"
    r"(?P<prefix>\[[^]]+]\()"
    r"(?P<destination>[^)]+)"
    r"(?P<suffix>\))"
)

COMMUNITY_PAGES = [
    ("Contributing", "CONTRIBUTING.md"),
    ("Governance", "GOVERNANCE.md"),
    ("Support", "SUPPORT.md"),
    ("Security", "SECURITY.md"),
    ("Code of Conduct", "CODE_OF_CONDUCT.md"),
    ("Changelog", "CHANGELOG.md"),
    ("Authors and Contributors", "AUTHORS.md"),
]


def local_path(destination: str) -> Path | None:
    """Resolve a local Markdown destination from SUMMARY.md."""
    destination = destination.strip()
    parsed = urlsplit(unquote(destination))
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None
    candidate = (ROOT / parsed.path).resolve()
    try:
        candidate.relative_to(ROOT)
    except ValueError:
        return None
    return candidate


def summary_navigation() -> tuple[list[dict[str, object]], list[Path]]:
    """Return MkDocs navigation and every source referenced by SUMMARY.md."""
    sections: list[tuple[str, list[dict[str, str]]]] = []
    sources: list[Path] = []
    current: tuple[str, list[dict[str, str]]] | None = None

    for line in SUMMARY.read_text(encoding="utf-8").splitlines():
        if match := SECTION.match(line):
            current = (match.group("title"), [])
            sections.append(current)
            continue
        if not current or not (match := LINK.match(line)):
            continue
        source = local_path(match.group("target"))
        if source is None or source.suffix.lower() != ".md":
            continue
        if not source.is_file():
            raise FileNotFoundError(f"SUMMARY links to missing source: {source}")
        relative = source.relative_to(ROOT).as_posix()
        current[1].append({match.group("title"): relative})
        sources.append(source)

    if len(sources) != 137:
        raise ValueError(
            f"expected 137 Markdown sources in SUMMARY.md, found {len(sources)}"
        )
    if len(set(sources)) != len(sources):
        raise ValueError("SUMMARY.md contains duplicate website sources")

    navigation: list[dict[str, object]] = [{"Home": "index.md"}]
    for title, entries in sections:
        if title == "Handbook":
            entries.insert(0, {"Complete Table of Contents": "SUMMARY.md"})
        navigation.append({title: entries})
    navigation.append(
        {
            "Community": [
                {title: path}
                for title, path in COMMUNITY_PAGES
            ]
        }
    )
    return navigation, sources


def staged_text(source: Path) -> str:
    """Return source text adjusted only for the staged website tree."""
    text = source.read_text(encoding="utf-8")

    def replace(match: re.Match[str]) -> str:
        destination = match.group("destination").strip()
        parsed = urlsplit(unquote(destination))
        if parsed.scheme or parsed.netloc or not parsed.path:
            return match.group(0)
        target = (source.parent / parsed.path).resolve()
        try:
            relative = target.relative_to(ROOT)
        except ValueError:
            return match.group(0)
        if target.suffix.lower() == ".md":
            return match.group(0)
        if not target.exists():
            return match.group(0)
        url = f"{PROJECT_URL}/blob/main/{quote(relative.as_posix())}"
        if parsed.fragment:
            url += f"#{parsed.fragment}"
        return f"{match.group('prefix')}{url}{match.group('suffix')}"

    text = INLINE_LINK.sub(replace, text)
    return text.replace(
        "](LICENSE)", f"]({PROJECT_URL}/blob/main/LICENSE)"
    ).replace(
        "](CITATION.cff)", f"]({PROJECT_URL}/blob/main/CITATION.cff)"
    )


def copy_source(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(staged_text(source), encoding="utf-8")


def prepare_sources(summary_sources: list[Path]) -> None:
    """Create an isolated MkDocs input tree from canonical repository sources."""
    if STAGING.exists():
        shutil.rmtree(STAGING)
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    STAGING.mkdir(parents=True)

    copy_source(ROOT / "README.md", STAGING / "index.md")
    copy_source(SUMMARY, STAGING / "SUMMARY.md")
    for source in summary_sources:
        copy_source(source, STAGING / source.relative_to(ROOT))
    for _, relative in COMMUNITY_PAGES:
        source = ROOT / relative
        copy_source(source, STAGING / relative)

    asset_destination = STAGING / "assets" / "social-preview.png"
    asset_destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "assets" / "social-preview.png", asset_destination)


def write_config(navigation: list[dict[str, object]]) -> None:
    """Write a deterministic generated MkDocs configuration."""
    config = {
        "site_name": "The Developer Handbook",
        "site_description": (
            "A systems-first guide to Unix, Git, networking, containers, "
            "cloud architecture, system design, and production debugging."
        ),
        "site_author": "Michael Adeniken and contributors",
        "site_url": SITE_URL,
        "repo_name": "superflyad/Developer-handbook",
        "repo_url": PROJECT_URL,
        "edit_uri": "edit/main/",
        "copyright": (
            "Copyright © 2026 Michael Adeniken · Published under the MIT License"
        ),
        "docs_dir": str(STAGING),
        "site_dir": str(OUTPUT),
        "use_directory_urls": True,
        "strict": True,
        "theme": {
            "name": "material",
            "custom_dir": str(ROOT / "site" / "overrides"),
            "language": "en",
            "logo": "material/book-open-page-variant",
            "favicon": "material/book-open-page-variant",
            "features": [
                "announce.dismiss",
                "content.action.edit",
                "content.code.annotate",
                "content.code.copy",
                "navigation.footer",
                "navigation.indexes",
                "navigation.instant",
                "navigation.instant.prefetch",
                "navigation.sections",
                "navigation.top",
                "navigation.tracking",
                "search.highlight",
                "search.share",
                "search.suggest",
                "toc.follow",
            ],
            "palette": [
                {
                    "media": "(prefers-color-scheme: light)",
                    "scheme": "default",
                    "primary": "custom",
                    "accent": "custom",
                    "toggle": {
                        "icon": "material/weather-night",
                        "name": "Switch to dark mode",
                    },
                },
                {
                    "media": "(prefers-color-scheme: dark)",
                    "scheme": "slate",
                    "primary": "custom",
                    "accent": "custom",
                    "toggle": {
                        "icon": "material/weather-sunny",
                        "name": "Switch to light mode",
                    },
                },
            ],
        },
        "plugins": [
            {
                "search": {
                    "lang": "en",
                    "separator": r"[\s\-\.]+",
                }
            }
        ],
        "markdown_extensions": [
            "abbr",
            "admonition",
            "attr_list",
            "def_list",
            "md_in_html",
            "tables",
            {"toc": {"permalink": True, "toc_depth": 3}},
            "pymdownx.details",
            "pymdownx.inlinehilite",
            "pymdownx.keys",
            "pymdownx.smartsymbols",
            "pymdownx.superfences",
            {"pymdownx.highlight": {"anchor_linenums": True}},
            {"pymdownx.tasklist": {"custom_checkbox": True}},
        ],
        "extra_css": ["styles/site.css"],
        "extra": {
            "generator": False,
            "social": [
                {
                    "icon": "fontawesome/brands/github",
                    "link": "https://github.com/superflyad",
                    "name": "Michael Adeniken on GitHub",
                }
            ],
        },
        "nav": navigation,
    }
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(
        yaml.safe_dump(config, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def build() -> None:
    navigation, sources = summary_navigation()
    prepare_sources(sources)
    style_destination = STAGING / "styles" / "site.css"
    style_destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "styles" / "site.css", style_destination)
    write_config(navigation)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "mkdocs",
            "build",
            "--config-file",
            str(CONFIG),
            "--strict",
        ],
        cwd=ROOT,
        check=True,
    )
    index = OUTPUT / "index.html"
    search = OUTPUT / "search" / "search_index.json"
    if not index.is_file() or not search.is_file():
        raise RuntimeError("website build did not produce its index and search data")
    print(
        f"Built searchable website from {len(sources) + len(COMMUNITY_PAGES) + 2} "
        f"Markdown pages in {OUTPUT}"
    )


if __name__ == "__main__":
    build()
