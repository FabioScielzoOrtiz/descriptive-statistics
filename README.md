# Descriptive Statistics

Course notes for **Descriptive Statistics**, written in [Quarto](https://quarto.org)
with examples in **Python** (Polars, NumPy, Matplotlib). Each topic combines
definitions and results, applications to data, and exercises with solutions.

## Structure

```
descriptive-statistics/
├── _quarto.yml          Website settings (sidebar lists every page)
├── index.qmd            Home page
├── topics/
│   ├── _setup.qmd       Shared setup for the remaining .qmd pages
│   ├── 01-introduction/ One folder per topic, split into short pages (Jupyter notebooks)
│   └── 03-….qmd         Topics in preparation (placeholders)
├── src/
│   ├── download/        Scripts that download the raw data (download_epf.py)
│   └── processing/      Scripts that build the clean datasets (prepare_epf.py)
├── data/
│   ├── raw/             Raw files as published by the INE (not in git)
│   └── processed/       Clean datasets used by the notes (+ README with the variables)
├── utils/style.py       Common plot style (Matplotlib)
└── references.bib       Bibliography
```

## Setup

1. Install the [Quarto CLI](https://quarto.org/docs/get-started/) (≥ 1.5).
2. Create the Python environment **inside the project folder**:

   ```powershell
   py -m venv .venv                # macOS/Linux: python3 -m venv .venv
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

3. Open the folder in VS Code, accept the recommended extensions (Quarto, Python,
   Jupyter) and select `.venv` as the Python interpreter.
4. Download and prepare the data (about 225 MB from the INE, only once):

   ```powershell
   .venv\Scripts\python.exe src\download\download_epf.py
   .venv\Scripts\python.exe src\processing\prepare_epf.py
   ```

## Daily use

| Task | How |
|---|---|
| Preview the open file | `Ctrl+Shift+B` in VS Code |
| Run cells | *Run Cell* or `Ctrl+Shift+Enter` (interactive window) |
| Render the website | `quarto render` → `_site/` |
| Publish on GitHub Pages | `quarto publish gh-pages` |

## Conventions

- Cite with `[@key]` using the keys in `references.bib`.
- Keep each page short (under ~25 KB): very long `.qmd` files make the VS Code
  Quarto extension slow and can block the Python and Jupyter extensions. When a
  placeholder topic is written, turn it into a folder with several pages and add
  them to the sidebar in `_quarto.yml`.
- Pages with code are Jupyter notebooks (`.ipynb`), so they can be edited and run
  in the VS Code notebook editor. Each notebook starts with a **raw cell** holding
  the YAML header (`title: …`) and a **setup code cell** with `#| include: false`
  (imports and plot style); then it loads the data it uses. Quarto runs the
  notebooks on render (`execute: enabled: true`), so the outputs saved in the
  files do not matter.
- To read well both in VS Code and on the website: put a table and its caption
  (`: …`) in the same cell, and do not use inline expressions (`` `{python} …` ``),
  which VS Code shows as plain code. Callout markers (`:::`) and cross-references
  (`@fig-…`) appear as plain text in VS Code but render properly on the website.
- Cross-references (`@fig-…`, `@exr-…`) only work within a page; link to other
  pages with ordinary links.
- Solutions go right after each exercise, in a collapsible callout:
  `::: {.callout-tip collapse="true"}` with the heading `## Solution`.
