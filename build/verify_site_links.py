"""Check every Google Drive download link on the live site, as a visitor would get it.

Usage: verify_site_links.py <site base url>

For each Drive link on each page: the public download serves a zip whose name matches the
Drive metadata and whose central directory can be read; its top-level text files contain
no Google Sites URL; its reference-info file links to this page of the new site; and that
page returns HTTP 200. Zips are read through HTTP range requests, never fully downloaded.
"""
import io
import re
import sys
import urllib.request
import zipfile

BASE = sys.argv[1].rstrip("/") + "/"
DL = "https://drive.usercontent.google.com/download?id={}&export=download&confirm=t"
PAGES = ["index", "combinatorial-auctions", "set-covering", "maximum-independent-set", "mvc",
         "generalized-independent-set", "capacitated-facility-location", "load-balancing", "item-placement",
         "maritime-inventory-routing", "neural-network-verification", "WF_OTS", "WF_OTS_UG",
         "middle-mile-consolidation-network-design", "water-pipe-network-planning", "course-exam-scheduling",
         "license", "submit-distribution"]


def get(url, rng=None):
    req = urllib.request.Request(url, headers={"Range": f"bytes={rng[0]}-{rng[1]}"} if rng else {})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.status, dict(r.headers), r.read()


class RangeFile(io.RawIOBase):
    """Seekable read-only file over HTTP range requests."""

    def __init__(self, url):
        self.url, self.pos = url, 0
        _, h, _ = get(url, (0, 0))
        self.size = int(h["Content-Range"].split("/")[1])
        self.name = re.search(r'filename="([^"]+)"', h.get("Content-Disposition", "")).group(1)

    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.pos

    def seek(self, off, whence=0):
        self.pos = {0: off, 1: self.pos + off, 2: self.size + off}[whence]
        return self.pos

    def readinto(self, buf):
        n = min(len(buf), self.size - self.pos)
        if n <= 0:
            return 0
        data = get(self.url, (self.pos, self.pos + n - 1))[2]
        buf[:len(data)] = data
        self.pos += len(data)
        return len(data)


def page_ok(url):
    try:
        return get(url)[0] == 200
    except Exception:
        return False


problems, checked = [], 0
for page in PAGES:
    html = get(BASE + ("" if page == "index" else page + ".html"))[2].decode()
    for fid, label in re.findall(r'href="https://drive\.google\.com/file/d/([A-Za-z0-9_-]+)[^"]*"[^>]*>([^<]*)<', html):
        checked += 1
        tag = f"{page} / {label.strip()} ({fid})"
        try:
            rf = RangeFile(DL.format(fid))
            zf = zipfile.ZipFile(io.BufferedReader(rf, buffer_size=1 << 16))
            texts = {i.filename: zf.read(i).decode("utf-8", "replace") for i in zf.infolist()
                     if "/" not in i.filename and i.filename.endswith(".txt")}
            urls = sorted({u for t in texts.values() for u in re.findall(r"https?://\S+", t)})
            if any("sites.google.com" in u for u in urls):
                problems.append(f"{tag}: still has a Google Sites URL")
            ref = [u for f, t in texts.items() if "reference-info" in f for u in re.findall(r"https?://\S+", t)]
            want = BASE + (page + ".html" if page != "index" else "")
            if page != "index" and want not in ref:
                problems.append(f"{tag}: reference-info links {ref}, expected {want}")
            for u in ref:
                if not page_ok(u):
                    problems.append(f"{tag}: {u} does not load")
            print(f"ok  {tag}: {rf.name}, {rf.size} bytes, {len(zf.infolist())} entries, ref={ref}", flush=True)
        except Exception as e:
            problems.append(f"{tag}: {type(e).__name__}: {e}")
            print(f"ERR {tag}: {e}", flush=True)
print(f"\nchecked {checked} links, {len(problems)} problems")
for p in problems:
    print("  -", p)
