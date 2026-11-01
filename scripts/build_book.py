#!/usr/bin/env python3
"""Assemble and render canonical Developer Handbook publication artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "SUMMARY.md"
CSS = ROOT / "styles" / "handbook.css"
TITLE = "The Developer Handbook"
AUTHOR = "Developer Handbook contributors"
PROJECT_URL = "https://github.com/superflyad/Developer-handbook"
OUTPUT_STEM = "developer-handbook"
FIRST_EDITION_LAST_CHAPTER = 129

SUMMARY_LINK = re.compile(r"(?<!!)\[[^\]]+\]\((?P<destination>[^)]+)\)")
INLINE_LINK = re.compile(
    r"(?<!!)"
    r"(?P<prefix>\[[^\]]+\]\()"
    r"(?P<destination>[^)]+)"
    r"(?P<suffix>\))"
)
CHAPTER_FILE = re.compile(r"^(?P<number>\d{2,3})-.+\.md$")
FIRST_HEADING = re.compile(r"(?m)^# (?P<title>[^\r\n]+?)[ \t]*$")


class PublicationHTMLParser(HTMLParser):
    """Collect unique anchors and internal fragment links from rendered HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.identifiers: set[str] = set()
        self.fragments: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        values = dict(attrs)
        identifier = values.get("id")
        if identifier:
            if identifier in self.identifiers:
                raise RuntimeError(f"generated HTML has duplicate id: {identifier}")
            self.identifiers.add(identifier)
        href = values.get("href") or ""
        if href.startswith("#"):
            self.fragments.append(unquote(href[1:]))


def link_target(destination: str) -> str:
    """Return the URL or path portion of a Markdown link destination."""
    destination = destination.strip()
    if destination.startswith("<") and ">" in destination:
        return destination[1 : destination.index(">")]
    return destination.split(maxsplit=1)[0]


def canonical_sources() -> list[Path]:
    """Read publication order from SUMMARY.md and select book content."""
    sources: list[Path] = []
    for match in SUMMARY_LINK.finditer(SUMMARY.read_text(encoding="utf-8")):
        destination = link_target(match.group("destination"))
        parsed = urlsplit(unquote(destination))
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        candidate = (ROOT / parsed.path).resolve()
        relative = candidate.relative_to(ROOT)
        if relative.as_posix() in {
            "PREFACE.md",
            "PHILOSOPHY.md",
            "HOW_TO_USE_THIS_HANDBOOK.md",
        } or relative.parts[0] == "handbook":
            sources.append(candidate)

    if len(sources) != FIRST_EDITION_LAST_CHAPTER + 4:
        raise ValueError(
            "publication must contain three front-matter files, Chapters 1–129, "
            "and one appendix"
        )
    if len(set(sources)) != len(sources):
        raise ValueError("publication source order contains duplicate files")
    for source in sources:
        if not source.is_file():
            raise FileNotFoundError(f"publication source does not exist: {source}")

    chapter_numbers = [
        int(match.group("number"))
        for source in sources
        if (match := CHAPTER_FILE.match(source.name))
    ]
    if chapter_numbers != list(range(1, FIRST_EDITION_LAST_CHAPTER + 1)):
        raise ValueError("publication chapters are not ordered from 1 through 129")
    return sources


def anchor_for(source: Path) -> str:
    """Return a stable publication anchor for a source file."""
    if match := CHAPTER_FILE.match(source.name):
        return f"chapter-{int(match.group('number')):03d}"
    if source.is_relative_to(ROOT / "handbook" / "appendices"):
        return f"appendix-{source.stem}"
    return source.stem.lower().replace("_", "-")


def git_value(*arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def source_identity() -> tuple[str, int]:
    revision = (
        os.environ.get("SOURCE_REVISION")
        or os.environ.get("GITHUB_SHA")
        or git_value("rev-parse", "HEAD")
    )
    epoch_text = os.environ.get("SOURCE_DATE_EPOCH")
    epoch = int(epoch_text) if epoch_text else int(git_value("show", "-s", "--format=%ct", "HEAD"))
    return revision, epoch


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rewrite_links(
    text: str,
    source: Path,
    anchors: dict[Path, str],
    revision: str,
) -> str:
    """Rewrite local source links for a single combined publication."""

    def replace(match: re.Match[str]) -> str:
        destination = link_target(match.group("destination"))
        parsed = urlsplit(unquote(destination))
        if parsed.scheme or parsed.netloc or not parsed.path:
            return match.group(0)

        target = (source.parent / parsed.path).resolve()
        if not target.exists():
            raise FileNotFoundError(
                f"{source.relative_to(ROOT)} links to missing target {destination}"
            )
        if target in anchors:
            rewritten = f"#{parsed.fragment or anchors[target]}"
        else:
            relative = target.relative_to(ROOT).as_posix()
            rewritten = (
                f"{PROJECT_URL}/blob/{revision}/{quote(relative)}"
                f"{f'#{parsed.fragment}' if parsed.fragment else ''}"
            )
        return f"{match.group('prefix')}{rewritten}{match.group('suffix')}"

    return INLINE_LINK.sub(replace, text)


def assemble_markdown(
    sources: list[Path],
    output: Path,
    revision: str,
    epoch: int,
) -> list[dict[str, str]]:
    anchors = {source: anchor_for(source) for source in sources}
    publication_date = datetime.fromtimestamp(epoch, UTC).date().isoformat()
    sections = [
        "---",
        f'title: "{TITLE}"',
        f'author: "{AUTHOR}"',
        f'date: "{publication_date}"',
        'lang: "en-US"',
        f'identifier: "{revision}"',
        "---",
        "",
    ]
    manifest_sources: list[dict[str, str]] = []

    for index, source in enumerate(sources):
        text = source.read_text(encoding="utf-8").strip()
        heading = FIRST_HEADING.search(text)
        if not heading:
            raise ValueError(f"publication source lacks a level-one title: {source}")
        title = heading.group("title")
        text = FIRST_HEADING.sub(
            f"# {title} {{#{anchors[source]}}}", text, count=1
        )
        text = rewrite_links(text, source, anchors, revision)
        if index:
            sections.extend(('<div class="page-break"></div>', ""))
        sections.extend((text.strip(), ""))
        manifest_sources.append(
            {
                "path": source.relative_to(ROOT).as_posix(),
                "anchor": anchors[source],
                "sha256": sha256(source),
            }
        )

    output.write_text("\n".join(sections).rstrip() + "\n", encoding="utf-8")
    return manifest_sources


def tool_version(command: str) -> str | None:
    executable = shutil.which(command)
    if not executable:
        return None
    result = subprocess.run(
        [executable, "--version"], check=True, capture_output=True, text=True
    )
    return result.stdout.splitlines()[0].strip()


def run_pandoc(source: Path, output: Path, output_format: str) -> None:
    pandoc = shutil.which("pandoc")
    if not pandoc:
        raise RuntimeError("pandoc is required for HTML, EPUB, and DOCX output")

    command = [
        pandoc,
        str(source),
        "--from=markdown",
        "--standalone",
        "--toc",
        "--toc-depth=2",
        "--wrap=none",
        f"--resource-path={ROOT}",
        f"--output={output}",
    ]
    if output_format == "html":
        command.extend(("--embed-resources", f"--css={CSS}"))
    elif output_format == "epub":
        command.append(f"--css={CSS}")
    subprocess.run(command, cwd=ROOT, check=True)


def verify_artifact(path: Path, kind: str) -> None:
    if not path.is_file() or path.stat().st_size < 1000:
        raise RuntimeError(f"generated {kind} artifact is missing or unexpectedly small")
    signatures = {
        "pdf": b"%PDF",
        "epub": b"PK",
        "docx": b"PK",
    }
    if signature := signatures.get(kind):
        with path.open("rb") as stream:
            if stream.read(len(signature)) != signature:
                raise RuntimeError(f"generated {kind} artifact has an invalid signature")
    if kind in {"epub", "docx"}:
        with ZipFile(path) as archive:
            if corrupt_member := archive.testzip():
                raise RuntimeError(
                    f"generated {kind} artifact has corrupt member: {corrupt_member}"
                )
    if kind == "html":
        parser = PublicationHTMLParser()
        parser.feed(path.read_text(encoding="utf-8"))
        missing = sorted(set(parser.fragments) - parser.identifiers)
        if missing:
            raise RuntimeError(
                "generated HTML has missing fragment targets: "
                + ", ".join(missing[:20])
            )


def render_formats(source: Path, output_dir: Path, formats: set[str]) -> list[Path]:
    artifacts: list[Path] = []
    if "pdf" in formats:
        formats.add("html")
    for output_format in ("html", "epub", "docx"):
        if output_format not in formats:
            continue
        output = output_dir / f"{OUTPUT_STEM}.{output_format}"
        run_pandoc(source, output, output_format)
        verify_artifact(output, output_format)
        artifacts.append(output)

    if "pdf" in formats:
        weasyprint = shutil.which("weasyprint")
        if not weasyprint:
            raise RuntimeError("weasyprint is required for PDF output")
        html = output_dir / f"{OUTPUT_STEM}.html"
        pdf = output_dir / f"{OUTPUT_STEM}.pdf"
        subprocess.run([weasyprint, str(html), str(pdf)], cwd=ROOT, check=True)
        verify_artifact(pdf, "pdf")
        artifacts.append(pdf)
    return artifacts


def write_manifest(
    path: Path,
    revision: str,
    epoch: int,
    sources: list[dict[str, str]],
    artifacts: list[Path],
) -> None:
    data = {
        "schema_version": 1,
        "title": TITLE,
        "source_revision": revision,
        "source_date": datetime.fromtimestamp(epoch, UTC).isoformat(),
        "sources": sources,
        "artifacts": [
            {
                "path": artifact.name,
                "bytes": artifact.stat().st_size,
                "sha256": sha256(artifact),
            }
            for artifact in artifacts
        ],
        "tools": {
            "python": sys.version.split()[0],
            "pandoc": tool_version("pandoc"),
            "weasyprint": tool_version("weasyprint"),
        },
    }
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "build",
        help="directory for generated publication artifacts",
    )
    parser.add_argument(
        "--formats",
        nargs="*",
        choices=("html", "epub", "docx", "pdf"),
        default=(),
        help="render formats in addition to canonical combined Markdown",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    revision, epoch = source_identity()
    sources = canonical_sources()
    markdown = output_dir / f"{OUTPUT_STEM}.md"
    manifest_sources = assemble_markdown(sources, markdown, revision, epoch)
    artifacts = [markdown]
    artifacts.extend(render_formats(markdown, output_dir, set(args.formats)))
    manifest = output_dir / "publication-manifest.json"
    write_manifest(manifest, revision, epoch, manifest_sources, artifacts)
    print(
        f"Built {len(artifacts)} publication artifact(s) from "
        f"{len(sources)} canonical source files in {output_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
