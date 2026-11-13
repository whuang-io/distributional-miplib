"""Render converted page fragments into a static GitHub Pages site."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import refs  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402

SRC = Path(sys.argv[1])
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)

SYNTHETIC = ["combinatorial-auctions", "set-covering", "maximum-independent-set", "mvc",
             "generalized-independent-set", "capacitated-facility-location", "load-balancing",
             "item-placement"]
REAL = ["maritime-inventory-routing", "neural-network-verification",
        "WF_OTS", "WF_OTS_UG", "middle-mile-consolidation-network-design", "water-pipe-network-planning",
        "course-exam-scheduling"]
pages = {p.stem: json.loads(p.read_text()) for p in SRC.glob("*.json")}


def nav(current):
    def item(slug, label):
        cur = ' aria-current="page"' if slug == current else ""
        href = "index.html" if slug == "home" else f"{slug}.html"
        return f'<a href="{href}"{cur}>{label}</a>'

    def group(label, slugs):
        links = "".join(f"<li>{item(s, pages[s]['title'])}</li>" for s in slugs)
        return f'<div class="dd-group"><span>{label}</span><ul>{links}</ul></div>'

    in_domain = current in SYNTHETIC + REAL
    return f"""<nav class="site-nav" aria-label="Main">
  <a class="brand" href="index.html">Distributional MIPLIB</a>
  <input type="checkbox" id="nav-toggle" hidden><label for="nav-toggle" class="nav-toggle" aria-label="Menu">&#9776;</label>
  <div class="nav-links">
    {item("home", "Home")}
    <details class="dd"{' data-active' if in_domain else ''}><summary>Domains</summary>
      <div class="dd-menu">{group("Synthetic", SYNTHETIC)}{group("Real-world", REAL)}</div>
    </details>
    {item("submit-distribution", "Submit Distribution")}
    {item("license", "License")}
  </div>
</nav>"""


KEY_RENAMES = {"Pollack24": "Pollack25"}  # keys whose year changed after publication


def standardize_refs(blocks):
    """Re-render every entry under the References heading from the canonical bibliography."""
    out, in_refs = [], False
    for b in blocks:
        for old, new in KEY_RENAMES.items():
            b = b.replace(old, new)
        m = re.match(r'<h2([^>]*)>\s*Reference(s)?(.*?)</h2>', b)
        if m:
            in_refs = True
            out.append(f"<h2{m.group(1)}>References{m.group(3)}</h2>")
            continue
        if in_refs:
            key = re.match(r"<p>\[\s*([^\]]+?)\s*\]", b)
            if key:
                out.append(refs.render(key.group(1).replace(" ", "")))
            elif b not in ("<p>APA</p>",):  # stray text on the MMCN page
                raise ValueError(f"unexpected block in references: {b[:80]}")
            continue
        out.append(b)
    return out


# Literature added after the port: (page, hardness level) -> "Task [Key]" for the
# Related Literature column; each key is also appended to that page's references.
RELATED_LIT = {
    ("combinatorial-auctions", "Easy"): "Backdoor [Cai24, Cai25]",
    ("combinatorial-auctions", "Very hard"): "PaS [Huang24, Cai25]; Configuration [Cai25]",
    ("maximum-independent-set", "Medium"): "Backdoor [Cai25]",
    ("mvc", "Medium"): "Backdoor [Cai25]",
}


def add_related_lit(slug, blocks):
    additions = {level: text for (page, level), text in RELATED_LIT.items() if page == slug}
    if not additions:
        return blocks
    out, done = [], set()
    for b in blocks:
        if "<table" in b and "Related Literature" in b:
            soup = BeautifulSoup(b, "html.parser")
            col = [th.get_text(" ", strip=True) for th in soup.find_all("th")].index("Related Literature")
            for tr in soup.find("tbody").find_all("tr"):
                cells = tr.find_all("td")
                level = cells[0].get_text(" ", strip=True)
                if level in additions:
                    cell = cells[col]
                    old = cell.get_text(" ", strip=True)
                    cell.clear()
                    cell.append(additions[level] if old in ("", "N/A") else f"{old}; {additions[level]}")
                    done.add(level)
            b = str(soup)
        out.append(b)
    missing = set(additions) - done
    if missing:
        raise ValueError(f"{slug}: rows not found {missing}")
    keys = sorted({k for text in additions.values() for k in re.findall(r"\[(\w+)\]", text)})
    for key in keys:
        if f'id="ref-{key}"' not in "".join(out):
            out.append(refs.render(key))
    return out


# Subsections added after the port, inserted just before the page's Citation section.
EXTRA_SECTIONS = {
    "combinatorial-auctions": [
        '<h3 id="backdoor">Backdoor</h3>',
        "<p>For learning backdoors, CA has been used as a benchmark in [Cai25], which trains on "
        "instances with 175 items and 850 bids, and tests on instances of the same size as well as on "
        "larger instances with 200 items and 1,000 bids (the Easy distribution in Distributional MIPLIB). "
        "[Cai24] trains on instances with 150 items and 750 bids, and tests on instances of the same size as "
        "well as on larger instances with 200 items and 1,000 bids (the Easy distribution).</p>",
        '<h3 id="pas">Predict-and-Search (PaS)</h3>',
        "<p>For predict-and-search, CA has been used as a benchmark in [Huang24] and [Cai25], which train on "
        "instances with 2,000 items and 4,000 bids (the Very hard distribution in Distributional MIPLIB), "
        "and test on instances of the same size as well as on larger instances with 3,000 items and "
        "6,000 bids.</p>",
        '<h3 id="configuration">Solver Configuration</h3>',
        "<p>For solver configuration, CA has been used as a benchmark in [Cai25], which trains on "
        "instances with 2,000 items and 4,000 bids (the Very hard distribution in Distributional MIPLIB), "
        "and tests on instances of the same size as well as on larger instances with 3,000 items and "
        "6,000 bids.</p>",
    ],
    "mvc": [
        '<h3 id="backdoor">Backdoor</h3>',
        "<p>For learning backdoors, MVC has been used as a benchmark in [Cai25], which trains on "
        "Barabasi-Albert graphs with 1,500 nodes and affinity set to 5, and tests on graphs of the same "
        "size as well as on larger graphs with 2,000 nodes and affinity set to 5 (the Medium distribution "
        "in Distributional MIPLIB).</p>",
        '<h3 id="pas">Predict-and-Search</h3>',
        "<p>For predict-and-search, MVC has been used as a benchmark in [Huang24] and [Cai25], which train on "
        "Barabasi-Albert graphs with 6,000 nodes and affinity set to 5, and test on graphs of the same size as "
        "well as on larger graphs with 9,000 nodes and affinity set to 5 (the Very hard 3 distribution in "
        "Distributional MIPLIB).</p>",
    ],
    "maximum-independent-set": [
        '<h3 id="backdoor">Backdoor</h3>',
        "<p>For learning backdoors, IS has been used as a benchmark in [Cai25], which trains on "
        "Barabasi-Albert graphs with 1,250 nodes and affinity set to 4, and tests on graphs of the same "
        "size as well as on larger graphs with 1,500 nodes and affinity set to 4 (the Medium distribution "
        "in Distributional MIPLIB).</p>",
    ],
}

# Text renames, as (pattern, replacement) applied to every block of the listed pages.
RENAMES = {
    # The License paragraph linked an older copy of LB-hard.zip (no license files); use the table's file.
    "load-balancing": [(r"1BBIYkAhTf7-Nxd7BOrhejS8X692honCT", "1vhoEN9jb8sxgjOxEa3Wvnfe_fq0SzxCJ")],
    # GISP Ext hard was regenerated (the previous set had duplicate instances per graph).
    "generalized-independent-set": [(r"12675\.83", "12608.59")],
    # Full-set (train+val+test) statistics: MIRP binaries had been counted as integers,
    # and WF_OTS has exactly 32455 continuous variables in every instance.
    "maritime-inventory-routing": [(r"<td>0</td>(\s*)<td>15080\.57</td>", r"<td>13532.91</td>\1<td>1547.66</td>")],
    "WF_OTS": [(r"<td>32456</td>", "<td>32455</td>")],
    # Hard2 linked a copy outside the shared drive; this one in hardness_classified/ has the same instances.
    "WF_OTS_UG": [(r"1kF3MrVBeO1DvzWseDIPFVVzJn9VzFoCU", "13uN6QBVqwmOgUD85QkXys9a-BahTa_7V"),
                  # the one-day Texas7k distribution (Hard) was withdrawn; its zip stays on Drive
                  (r"(?s)<tr>\s*<td><a href=\"[^\"]*1mvERiCGpiFu5BItdswD6PjajbkyypuC9[^\"]*\">Hard</a></td>.*?</tr>\s*", ""),
                  # with the one-day set gone, the two-day Texas7k set is the Hard distribution
                  (r"(13uN6QBVqwmOgUD85QkXys9a-BahTa_7V/view\?usp=drive_link\">)Hard2<", r"\1Hard<"),
                  # five-day Texas7k set added as Very hard (instances to be uploaded; no download link yet)
                  (r"(?s)(<tr>\s*<td><a href=\"[^\"]*13uN6QBVqwmOgUD85QkXys9a-BahTa_7V[^\"]*\">Hard</a></td>.*?</tr>)",
                   r"""\1
<tr>
<td>Very hard</td>
<td>New</td>
<td>11624</td>
<td>0</td>
<td>116056</td>
<td>271619</td>
<td>Large</td>
<td>5</td>
</tr>""")],
    # SRPN statistics recomputed over the full instance set (train+val+test) after removing duplicate
    # instances (Easy 219 -> 171, Hard 206 -> 161).
    "water-pipe-network-planning": [(r"11485\.33", "11147.68"), (r"22430\.84", "21779.18"),
                                    (r"3016\.42", "3157.65"), (r"5917\.27", "6192.59")],
    "course-exam-scheduling": [(r"\b(?:CES|COURSE)\b", "EXAM"),
                               # the second distribution was mislabeled "Hard" on the original site
                               (r"(1PWVANayA8S6iZd3evjRJrllMEdLiJB8W/view\?usp=sharing\">)Hard<", r"\1Hard2<")],
    "license": [(r"\b(?:CES|COURSE)\b", "EXAM")],
    # MIS Very hard was regenerated (the previous set had duplicate instances); average over all 1000.
    "maximum-independent-set": [(r"23994\.82", "23996.57")],
    # CA Very hard 2 was regenerated (the previous set had duplicate instances).
    "combinatorial-auctions": [(r"5354\.08", "5351.95")],
    # Very hard 3: the 9,000-node test set of [Huang24], added to the library.
    "mvc": [(r"(?s)(Very hard 2</a></td>.*?</tr>)",
             r"""\1
<tr>
<td><a href="https://drive.google.com/file/d/1Y_d9Z3WhPlD6i0hXkkOkLID89ePf-tKZ/view?usp=drive_link">Very hard 3</a></td>
<td>[Huang24]</td>
<td>9000</td>
<td>0</td>
<td>0</td>
<td>44975</td>
<td>9,000</td>
<td>5</td>
<td>Barabasi-Albert</td>
<td>PaS [Huang24, Cai25]; LNS [Huang23b]</td>
</tr>"""),
            (r"\s*Huang et al\. \[Huang23b\] use Barabasi-Albert graphs with 9,000 nodes and affinity set to 5 to test a heuristic\.",
             " Huang et al. [Huang23b] use the Very hard 3 distribution (Barabasi-Albert graphs with 9,000 nodes and "
             "affinity set to 5) to test a heuristic.")],
    "home": [  # performance metrics from the updated paper tables (GISP Ext hard regenerated; WF_OTS)
             (r"(?s)<tr>\s*<td></td>\s*<td>Hard</td>\s*<td>New</td>\s*<td>3982</td>.*?</tr>\s*", ""),  # WF_OTS_UG Hard withdrawn
             (r"<td>2\.01</td>(\s*)<td>8139\.33</td>", r"<td>1.95</td>\1<td>7881.61</td>"),
             (r"<td>1\.28</td>(\s*)<td>9500\.5</td>", r"<td>0.49</td>\1<td>2205.27</td>"),
             (r"12675\.83", "12608.59"), (r"<td>0</td>(\s*)<td>15080\.57</td>", r"<td>13532.91</td>\1<td>1547.66</td>"), (r"<td>32456</td>", "<td>32455</td>"),
             (r"11485\.33", "11147.68"), (r"22430\.84", "21779.18"), (r"3016\.42", "3157.65"), (r"5917\.27", "6192.59"),
             (r"SRPN contains 22 and 20 test instances", "SRPN contains 22 and 19 test instances"),
             (r"23994\.82", "23996.57"), (r"5354\.08", "5351.95"),
             # WF_OTS_UG: five-day Texas7k distribution (Very hard) after the two-day one
             (r"(?s)(<td>Hard2</td>\s*<td>New</td>\s*<td>6546</td>.*?</tr>)",
              r"""\1
<tr>
<td></td>
<td>Very hard</td>
<td>New</td>
<td>11624</td>
<td>0</td>
<td>116056</td>
<td>271619</td>
<td>0</td>
<td></td>
<td>0.69</td>
<td>2800.73</td>
</tr>"""),
             (r"(?s)(<td>very hard2</td>\s*<td>\[Huang23\]</td>\s*<td>2000</td>.*?</tr>)",
              r"""\1
<tr>
<td></td>
<td>very hard3</td>
<td>[Huang24]</td>
<td>9000</td>
<td>0</td>
<td>0</td>
<td>44975</td>
<td>0</td>
<td></td>
<td>0.02</td>
<td>100.05</td>
</tr>"""),
             (r"with a RAM allocation of 5G\s+\(For SRPN-Hard,\s+MMCN-Very\s+Hard, and OTS-Hard instances, "
              r"we increased the RAM to 15G, due to memory errors at 5GB\.\)",
              "with a RAM allocation of 5G. For SRPN-Hard, MMCN-Very Hard, WF_OTS_UG-Hard and EXAM "
              "instances that had memory errors at 5GB, we increased the RAM to 15G."),
             # Hardness labels capitalized; the home page shows no 2/3 suffixes (the domain pages keep them).
             (r"<td>medium</td>", "<td>Medium</td>"), (r"<td>hard\d?</td>", "<td>Hard</td>"),
             (r"<td>Hard\d</td>", "<td>Hard</td>"), (r"<td>[Vv]ery hard ?\d?</td>", "<td>Very hard</td>"),
             (r"(Network</a></td>\s*)<td>Very easy</td>", r"\1<td>Very easy-BI</td>"),
             (r"(<td>[A-Z][a-z]*(?: hard)?-B[CI])\d</td>", r"\1</td>")],  # MMCN: no 2/3/4 suffixes
}


def apply_edits(slug, blocks):
    for pattern, repl in RENAMES.get(slug, []):
        blocks = [re.sub(pattern, repl, b) for b in blocks]
    if slug in EXTRA_SECTIONS:
        i = next(i for i, b in enumerate(blocks) if re.match(r"<h2[^>]*>Citation</h2>", b))
        blocks = blocks[:i] + EXTRA_SECTIONS[slug] + blocks[i:]
    return blocks


# Verified problem descriptions/formulations and domain-parameter columns, one JSON file per page.
CONTENT = {p.stem: json.loads(p.read_text()) for p in (Path(__file__).parent / "content").glob("*.json")}
# TeX regions in which a literal < or > would be parsed by the browser as HTML.
MATH_SPAN = re.compile(r"\\\(.*?\\\)|\\\[.*?\\\]|\\begin\{(align\*?|array|equation)\}.*?\\end\{\1\}", re.S)
STAT_COLUMNS = {"# Var B", "# Var I", "# Var C", "# Constr"}


def apply_content(slug, blocks):
    content = CONTENT.get(slug)
    if not content:
        return blocks
    # Replace everything between the "Problem Description" heading and the next h2.
    start = next(i for i, b in enumerate(blocks) if re.match(r"<h2[^>]*>\s*Problem Description", b))
    end = next(i for i in range(start + 1, len(blocks)) if blocks[i].startswith("<h2"))
    desc = MATH_SPAN.sub(lambda m: m.group(0).replace("<", r"\lt ").replace(">", r"\gt "), content["description_html"])
    blocks = blocks[:start + 1] + [f'<div class="embed">{desc}</div>'] + blocks[end:]

    # Swap the domain-parameter columns (those after # Constr other than Related Literature).
    for n, b in enumerate(blocks):
        if not ("<table" in b and "Hardness" in b and "# Constr" in b):
            continue
        soup = BeautifulSoup(b, "html.parser")
        heads = [th.get_text(" ", strip=True) for th in soup.find("thead").find_all("th")]
        keep_after = [i for i, h in enumerate(heads) if h == "Related Literature"]
        drop = [i for i, h in enumerate(heads) if i > heads.index("# Constr") and i not in keep_after]
        new_cols = content["table_columns"][1:]
        for tr in [soup.find("thead").find("tr")] + soup.find("tbody").find_all("tr"):
            cells = tr.find_all(["th", "td"])
            label = cells[0].get_text(" ", strip=True)
            if tr.parent.name == "thead":
                values, tag = new_cols, "th"
            else:
                if label not in content["table_rows"]:
                    raise ValueError(f"{slug}: no parameter values for row {label!r}")
                values, tag = content["table_rows"][label], "td"
            for i in sorted(drop, reverse=True):
                cells[i].decompose()
            anchor = tr.find_all(["th", "td"])[heads.index("# Constr")]
            for v in reversed(values):
                cell = soup.new_tag(tag)
                cell.append(BeautifulSoup(str(v), "html.parser"))
                anchor.insert_after(cell)
        blocks[n] = str(soup)
    return blocks


def complete_refs(blocks):
    """Append bibliography entries for keys cited on the page but missing from its reference list."""
    if not any(re.match(r"<h2[^>]*>References", b) for b in blocks):
        return blocks
    text = "".join(b for b in blocks if 'class="ref"' not in b)
    cited = []
    for group in re.findall(r"\[([^\]]+)\]", text):
        for key in (k.strip() for k in group.split(",")):
            if key in refs.REFS and key not in cited:
                cited.append(key)
    listed = "".join(blocks)
    return blocks + [refs.render(k) for k in cited if f'id="ref-{k}"' not in listed]


def group_domain_rows(blocks):
    """In tables whose continuation rows leave the first (domain) cell empty, merge that column into one
    cell per domain and mark the first row of each domain, so domains have visible boundaries."""
    out = []
    for b in blocks:
        if "<table" in b and re.search(r"<tr>\s*<td></td>", b):
            soup = BeautifulSoup(b, "html.parser")
            for tbody in soup.find_all("tbody"):
                head = None
                for tr in tbody.find_all("tr", recursive=False):
                    first = tr.find("td")
                    if head is not None and not first.get_text(strip=True) and not first.find(True):
                        first.decompose()
                        head["rowspan"] = int(head.get("rowspan", 1)) + 1
                    else:
                        head = first
                        head["class"] = head.get("class", []) + ["domain"]
                        tr["class"] = tr.get("class", []) + ["domain-start"]
            b = str(soup)
        out.append(b)
    return out


LEVELS = ["Very easy", "Easy", "Medium", "Hard", "Very hard", "Ext hard"]


def sort_mmcn_rows(slug, blocks):
    """MMCN table: SM (-BI) distributions first, then MM (-BC), each from easiest to hardest."""
    if slug != "middle-mile-consolidation-network-design":
        return blocks
    out = []
    for b in blocks:
        if "<table" in b and "Model (modes)" in b:
            soup = BeautifulSoup(b, "html.parser")
            tbody = soup.find("tbody")
            rows = tbody.find_all("tr", recursive=False)

            def key(tr):
                level, variant = re.fullmatch(r"(.+)-(B[CI])(\d*)", tr.find("td").get_text(strip=True)).groups()[:2]
                suffix = re.search(r"\d*$", tr.find("td").get_text(strip=True)).group(0)
                return (variant != "BI", LEVELS.index(level), int(suffix or 1))

            for tr in sorted(rows, key=key):
                tbody.append(tr.extract())
            b = str(soup)
        out.append(b)
    return out


def render(slug):
    page = pages[slug]
    blocks = apply_content(slug, apply_edits(slug, add_related_lit(slug, standardize_refs(page["blocks"]))))
    blocks = group_domain_rows(complete_refs(sort_mmcn_rows(slug, blocks)))
    if slug == "home":
        title, subtitle = blocks[0], blocks[1]
        blocks = blocks[2:]
        tagline = subtitle.replace("<p>", '<p class="tagline">', 1)
        header = f'<header class="hero"><div class="wrap">{title}{tagline}</div></header>'
        doc_title = "Distributional MIPLIB"
    else:
        header = f'<header class="page-head"><div class="wrap">{blocks[0]}</div></header>'
        blocks = blocks[1:]
        doc_title = f"{page['title']} · Distributional MIPLIB"
    body = "\n".join(blocks)
    mathjax = ""
    if any(m in body for m in ("\\(", "\\[", "\\begin{", "$$")):
        mathjax = ('<script>window.MathJax = {tex: {tags: "ams"}};</script>\n'
                   '<script async src="https://cdn.jsdelivr.net/npm/mathjax@3.2.2/es5/tex-mml-chtml.js"></script>')
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{doc_title}</title>
<meta name="description" content="Distributional MIPLIB: a multi-domain library of MILP distributions for advancing ML-guided MILP methods.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Lato:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/style.css">
{mathjax}
</head>
<body>
{nav(slug)}
{header}
<main class="wrap content">
{body}
</main>
<footer class="site-footer"><div class="wrap">Distributional MIPLIB · <a href="https://www.arxiv.org/abs/2406.06954">arXiv</a> · <a href="https://huggingface.co/datasets/weiminhu/D-MIPLIB">Hugging Face</a> · Contact: <a href="mailto:dilkina@usc.edu">dilkina@usc.edu</a></div></footer>
<script src="assets/site.js"></script>
</body>
</html>
"""


for slug in pages:
    name = "index.html" if slug == "home" else f"{slug}.html"
    (OUT / name).write_text(render(slug))
    print("wrote", name)
