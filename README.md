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
│   ├── _setup.qmd       Shared setup (Python imports and plot style), included by every page
│   ├── 01-introduction/ One folder per topic, split into short pages (index.qmd = part 1)
│   └── 03-….qmd         Topics in preparation (placeholders)
├── data/                Datasets (+ generate_households.py)
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
- Every page starts with `{{< include ../_setup.qmd >}}` (or `_setup.qmd` for
  pages directly in `topics/`) and loads the data it uses.
- Cross-references (`@fig-…`, `@exr-…`) only work within a page; link to other
  pages with ordinary links.
- Solutions go right after each exercise, in a collapsible callout:
  `::: {.callout-tip collapse="true"}` with the heading `## Solution`.
