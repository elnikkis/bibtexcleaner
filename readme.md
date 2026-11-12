# BibTeX Cleaner

A web app and CLI tool that strips unnecessary fields from BibTeX entries and normalizes formatting.

Live at: https://bibtexcleaner.onrender.com/

## What it does

BibTeX entries exported from tools like Google Scholar or Zotero often contain many extra fields (abstract, URL, ISSN, etc.) that are irrelevant for citation purposes. BibTeX Cleaner keeps only the fields needed to identify each reference (author, title, venue, year, volume/number/pages, …) and normalizes common formatting issues.

**Cleaning options:**

- **Strip extra fields** — keeps a minimal set of fields per entry type (article, inproceedings, book, etc., plus the BibLaTeX types online, software, and dataset). Fields whose rendering varies by style, such as `month`, `note`, `doi`, `url`, and conference `address`/`publisher`, are dropped by default (`url` is kept for `@misc`)
- **Save title case** — wraps titles in `{}` to preserve capitalization in LaTeX
- **Replace citation keys** — regenerates keys in `Author2024` format from author and year fields
- **Japanese author names** — removes the comma separator in `姓, 名` formatted Japanese names
- **Reverse Japanese author order** — swaps to `名 姓` order
- **Choose kept fields** — in the "残すフィールドの設定" panel, toggle fields per entry type, or for all types at once (e.g. keep `doi` / `url`, drop `note`). Settings are saved in the browser
- **Output order** — keep the input order (default) or sort entries by citation key

**Formatting normalizations applied automatically:**

- Page ranges are standardized to double-hyphen (`100--110`)
- Line breaks are removed from author, title, journal, and booktitle fields
- Entry types the tool does not know (e.g. `@electronic`) are passed through with all their fields; only the formatting normalizations are applied
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
# sort entries by citation key instead of keeping the input order
python cleaner.py --sort id input.bib output.bib
# keep extra fields / drop default fields ("type:field" applies to one entry type only)
python cleaner.py --keep doi,url,inproceedings:publisher --drop note input.bib output.bib
```

## Development

```bash
uv sync
uv run pytest
```
