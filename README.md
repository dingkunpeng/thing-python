# thing-python

Think Python: How to Think Like a Computer Scientist

## Book conversion helpers

This repository now includes a small utility for extracting the textual content
of an EPUB book into individual chapter files.  The tool lives in
`scripts/convert_book.py` and wraps the logic provided by
`book_tools.converter`.

```bash
# convert a specific file
python scripts/convert_book.py path/to/book.epub --output converted_chapters

# or place a single EPUB inside ./book or ./data and run without arguments
python scripts/convert_book.py
```

The converter will create one UTF-8 encoded `.txt` file per chapter in the
output directory.
