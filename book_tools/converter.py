"""Book conversion helpers for extracting plain text chapters."""
from __future__ import annotations

from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
import os
import posixpath
import re
from typing import Iterable, Iterator, List, Optional, Sequence
import unicodedata
import zipfile
import xml.etree.ElementTree as ET


# EPUB XML namespaces used within the OPF file.  The namespace mapping is kept
# in a dedicated constant to avoid repeating the URIs throughout the code.
OPF_NS = {
    "container": "urn:oasis:names:tc:opendocument:xmlns:container",
    "opf": "http://www.idpf.org/2007/opf",
}


@dataclass
class Chapter:
    """Representation of an extracted chapter."""

    index: int
    title: str
    text: str


class _HTMLToTextParser(HTMLParser):
    """A small HTML to plain text converter.

    EPUB chapters typically arrive as XHTML documents.  A fully fledged HTML
    renderer would be excessive, so we implement a light-weight parser that
    keeps track of block elements and headings in order to produce readable
    plain text output.  The parser also remembers the first heading encountered
    which is generally the chapter title.
    """

    _BLOCK_TAGS = {
        "address",
        "article",
        "aside",
        "blockquote",
        "br",
        "div",
        "dl",
        "dt",
        "dd",
        "figcaption",
        "figure",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "li",
        "main",
        "nav",
        "ol",
        "p",
        "pre",
        "section",
        "table",
        "tr",
        "ul",
    }

    _TITLE_TAGS = {"h1", "h2", "title"}

    def __init__(self) -> None:
        super().__init__()
        self._parts: List[str] = []
        self._pending_space = False
        self._title: Optional[str] = None
        self._capture_title = False

    @property
    def title(self) -> Optional[str]:
        return self._title

    def handle_starttag(self, tag: str, attrs: Sequence[tuple[str, str]]) -> None:
        tag = tag.lower()
        if tag in self._BLOCK_TAGS:
            self._ensure_newline()
        if tag in self._TITLE_TAGS:
            self._capture_title = True

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self._BLOCK_TAGS:
            self._ensure_newline()
        if tag in self._TITLE_TAGS:
            self._capture_title = False

    def handle_data(self, data: str) -> None:
        if not data.strip():
            self._pending_space = True
            return

        text = unescape(data)
        content = text.strip()
        if not content:
            return

        if self._pending_space and self._parts:
            if content[0] not in '.,;:!?)]}»”’':
                self._parts.append(" ")
        self._parts.append(content)
        self._pending_space = True

        if self._capture_title and content:
            if not self._title:
                self._title = content

    def get_text(self) -> str:
        raw = "".join(self._parts)
        # Replace multiple blank lines with two and strip trailing whitespace.
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()

    def _ensure_newline(self) -> None:
        if self._parts and not self._parts[-1].endswith("\n"):
            self._parts.append("\n")
        self._pending_space = False


def convert_book(input_path: str, output_dir: str) -> List[str]:
    """Convert a book at *input_path* into plain text chapters.

    Only EPUB files are currently supported.  The function returns a list of
    the generated file paths relative to *output_dir*.
    """

    input_path = os.path.abspath(input_path)
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Book not found: {input_path}")

    os.makedirs(output_dir, exist_ok=True)

    ext = os.path.splitext(input_path)[1].lower()
    if ext == ".epub":
        return list(_write_chapters(convert_epub_to_text(input_path), output_dir))

    raise ValueError(f"Unsupported book format: {ext or 'unknown'}")


def convert_epub_to_text(epub_path: str) -> Iterator[Chapter]:
    """Yield :class:`Chapter` instances extracted from *epub_path*."""

    with zipfile.ZipFile(epub_path, "r") as archive:
        container_info = _read_container_file(archive)
        opf_path = container_info["full-path"]
        opf_dir = posixpath.dirname(opf_path)

        manifest, spine = _read_package_document(archive, opf_path)

        for index, item_id in enumerate(spine, start=1):
            href = manifest.get(item_id)
            if href is None:
                continue
            chapter_path = posixpath.normpath(posixpath.join(opf_dir, href))
            try:
                with archive.open(chapter_path) as chapter_file:
                    html_bytes = chapter_file.read()
            except KeyError:
                continue

            text, title = _extract_text_from_html(html_bytes)
            yield Chapter(index=index, title=title or f"Chapter {index}", text=text)


def _read_container_file(archive: zipfile.ZipFile) -> dict[str, str]:
    try:
        with archive.open("META-INF/container.xml") as container:
            tree = ET.parse(container)
    except KeyError as exc:  # pragma: no cover - invalid EPUBs are rare in tests
        raise ValueError("Invalid EPUB: container.xml missing") from exc

    root = tree.getroot()
    element = root.find("container:rootfiles/container:rootfile", OPF_NS)
    if element is None or "full-path" not in element.attrib:
        raise ValueError("Invalid EPUB: unable to locate OPF package")
    return element.attrib


def _read_package_document(
    archive: zipfile.ZipFile, opf_path: str
) -> tuple[dict[str, str], List[str]]:
    try:
        with archive.open(opf_path) as opf_file:
            tree = ET.parse(opf_file)
    except KeyError as exc:  # pragma: no cover - invalid EPUBs are rare in tests
        raise ValueError(f"Invalid EPUB: package file {opf_path!r} missing") from exc

    root = tree.getroot()
    manifest: dict[str, str] = {}
    for item in root.findall("opf:manifest/opf:item", OPF_NS):
        item_id = item.attrib.get("id")
        href = item.attrib.get("href")
        if item_id and href:
            manifest[item_id] = href

    spine: List[str] = []
    for itemref in root.findall("opf:spine/opf:itemref", OPF_NS):
        item_idref = itemref.attrib.get("idref")
        if item_idref:
            spine.append(item_idref)

    return manifest, spine


def _extract_text_from_html(html_bytes: bytes) -> tuple[str, Optional[str]]:
    # Try UTF-8 first and fallback to latin-1 which is permissive while still
    # yielding readable results for most encodings.
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            html_text = html_bytes.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:  # pragma: no cover - unexpected encoding
        html_text = html_bytes.decode("utf-8", errors="ignore")

    parser = _HTMLToTextParser()
    parser.feed(html_text)
    parser.close()
    return parser.get_text(), parser.title


def _write_chapters(chapters: Iterable[Chapter], output_dir: str) -> Iterator[str]:
    for chapter in chapters:
        filename = _chapter_filename(chapter.index, chapter.title)
        path = os.path.join(output_dir, filename)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(chapter.text + "\n")
        yield path


def _chapter_filename(index: int, title: str) -> str:
    slug = _slugify(title)
    return f"chapter_{index:03d}_{slug}.txt"


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_text = ascii_text.lower()
    ascii_text = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    return ascii_text or "chapter"
