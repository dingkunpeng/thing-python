from __future__ import annotations

import zipfile
from pathlib import Path

from book_tools.converter import convert_epub_to_text, convert_book


def _create_epub(path: Path) -> None:
    # Build a very small EPUB file with two chapters.
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip")
        zf.writestr(
            "META-INF/container.xml",
            """<?xml version='1.0' encoding='utf-8'?>
            <container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
              <rootfiles>
                <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
              </rootfiles>
            </container>
            """,
        )
        zf.writestr(
            "OEBPS/content.opf",
            """<?xml version='1.0' encoding='utf-8'?>
            <package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="BookId">
              <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
                <dc:title>Sample Book</dc:title>
              </metadata>
              <manifest>
                <item id="chap1" href="chapter1.xhtml" media-type="application/xhtml+xml" />
                <item id="chap2" href="chapters/chapter2.xhtml" media-type="application/xhtml+xml" />
              </manifest>
              <spine>
                <itemref idref="chap1" />
                <itemref idref="chap2" />
              </spine>
            </package>
            """,
        )
        zf.writestr(
            "OEBPS/chapter1.xhtml",
            """<?xml version='1.0' encoding='utf-8'?>
            <html xmlns="http://www.w3.org/1999/xhtml">
              <head><title>Chapter One</title></head>
              <body>
                <h1>Chapter One</h1>
                <p>Once upon a time in a land far away.</p>
                <p>There lived a developer.</p>
              </body>
            </html>
            """,
        )
        zf.writestr(
            "OEBPS/chapters/chapter2.xhtml",
            """<?xml version='1.0' encoding='utf-8'?>
            <html xmlns="http://www.w3.org/1999/xhtml">
              <body>
                <h1>Another Chapter</h1>
                <p>More content follows with <strong>formatting</strong>.</p>
              </body>
            </html>
            """,
        )


def test_convert_epub_to_text(tmp_path: Path) -> None:
    epub_path = tmp_path / "book.epub"
    _create_epub(epub_path)

    chapters = list(convert_epub_to_text(str(epub_path)))
    assert [chapter.title for chapter in chapters] == ["Chapter One", "Another Chapter"]
    assert chapters[0].text.startswith("Chapter One")
    assert "More content follows" in chapters[1].text


def test_convert_book_writes_files(tmp_path: Path) -> None:
    epub_path = tmp_path / "book.epub"
    _create_epub(epub_path)

    output_dir = tmp_path / "out"
    written_files = convert_book(str(epub_path), str(output_dir))

    assert len(written_files) == 2
    contents = [Path(path).read_text(encoding="utf-8") for path in written_files]
    assert "developer" in contents[0]
    assert contents[1].strip().endswith("formatting.")
