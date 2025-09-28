"""Command line interface for the book conversion helpers."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Iterable

from book_tools.converter import convert_book


def _find_candidate_books(paths: Iterable[Path]) -> list[Path]:
    candidates: list[Path] = []
    for path in paths:
        if not path.exists():
            continue
        if path.is_file():
            candidates.append(path)
            continue
        for extension in ("*.epub",):
            candidates.extend(path.rglob(extension))
    return sorted({candidate.resolve() for candidate in candidates})


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert ebooks into chapter text files.")
    parser.add_argument(
        "input",
        nargs="?",
        help="Path to the ebook. If omitted the script looks for EPUB files under ./book or ./data.",
    )
    parser.add_argument(
        "--output",
        default="converted_chapters",
        help="Directory that will receive the generated chapter text files (default: converted_chapters).",
    )
    args = parser.parse_args()

    if args.input:
        book_path = Path(args.input).expanduser()
        candidates = [book_path]
    else:
        search_roots = [Path("book"), Path("data"), Path(".")]
        candidates = _find_candidate_books(search_roots)
        if not candidates:
            parser.error("No EPUB files were found. Provide the path explicitly or place the book under ./book or ./data.")
        if len(candidates) > 1:
            parser.error(
                "Multiple EPUB files found. Please specify the desired file explicitly.\n" +
                "\n".join(str(candidate) for candidate in candidates)
            )
        book_path = candidates[0]

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    created = convert_book(str(book_path), str(output_dir))
    rel_paths = [os.path.relpath(path, os.getcwd()) for path in created]
    for rel in rel_paths:
        print(rel)

    return 0


if __name__ == "__main__":  # pragma: no cover - manual execution entrypoint
    raise SystemExit(main())
