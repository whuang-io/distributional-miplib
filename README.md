# Distributional MIPLIB website

Static GitHub Pages version of the [Distributional MIPLIB](https://www.arxiv.org/abs/2406.06954) website
(originally hosted on Google Sites).

- One HTML file per page; shared styles in `assets/style.css`, small scripts in `assets/site.js`.
- Math is rendered with MathJax on pages that contain it.
- To edit a page, change its HTML file and push to `main`; GitHub Pages redeploys automatically.

## Building the pages

The HTML files are generated; edit the inputs in `build/` and rebuild rather than editing the HTML by hand.

- `build/source/*.json`: page content converted from the original Google Sites pages (one list of HTML blocks per page).
- `build/content/*.json`: verified problem descriptions/formulations and the domain-parameter table columns, one file per domain page.
- `build/refs.py`: the bibliography; every reference on the site is rendered from it.
- `build/build.py`: renders the pages. Later corrections (statistics, renamed distributions, related literature, extra sections) are listed in it as explicit edits with comments.
- `build/verify_site_links.py`: checks every Google Drive download link on the live site (zip name, readable archive, reference-info file pointing to the right page).

```sh
pip install beautifulsoup4
python build/build.py build/source .          # regenerate all pages in the repository root
python build/verify_site_links.py https://whuang-io.github.io/distributional-miplib/
```
