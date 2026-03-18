# BibTeX Cleaner

A web app and CLI tool that strips unnecessary fields from BibTeX entries and normalizes formatting.

Live at: https://bibtexcleaner.onrender.com/

## What it does

BibTeX entries exported from tools like Google Scholar or Zotero often contain many extra fields (abstract, URL, ISSN, etc.) that are irrelevant for citation purposes. BibTeX Cleaner keeps only the fields defined as standard for each entry type and normalizes common formatting issues.

**Cleaning options:**

- **Strip extra fields** — keeps only standard BibTeX fields per entry type (article, inproceedings, book, etc.)
- **Save title case** — wraps titles in `{}` to preserve capitalization in LaTeX
- **Replace citation keys** — regenerates keys in `Author2024` format from author and year fields
- **Japanese author names** — removes the comma separator in `姓, 名` formatted Japanese names
- **Reverse Japanese author order** — swaps to `名 姓` order
- **Keep DOI** — optionally retain the `doi` field even when stripping other extras

**Formatting normalizations applied automatically:**

- Page ranges are standardized to double-hyphen (`100--110`)
- Line breaks are removed from author, title, journal, and booktitle fields
- Duplicate citation keys are made unique by appending `a`, `b`, `c`, …

## Running locally

```bash
uv sync
gunicorn endpoint:app
```

Then open http://localhost:8000.

## CLI usage

```bash
python cleaner.py input.bib output.bib
# or
python cleaner.py < input.bib > output.bib
```

## Development

```bash
uv sync
uv run pytest
```
