"""Genere archive.html : liste de toutes les revues publiees sur gh-pages.

Usage : python scripts/build_archive_index.py <gh-pages-dir>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


PAGE_CSS = """
body { font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", sans-serif;
  font-size: 16px; line-height: 1.6; max-width: 820px; margin: 0 auto;
  padding: 24px 20px 80px; background: #0f1419; color: #e6edf3; }
h1 { font-size: 1.5rem; margin: 0 0 4px; }
.sub { color: #9aa8b5; font-size: 0.9rem; margin-bottom: 28px; }
ul { list-style: none; padding: 0; }
li { background: #1a1f26; border: 1px solid #2a3340; border-radius: 10px;
  padding: 14px 18px; margin-bottom: 10px; }
li a { color: #e6edf3; text-decoration: none; font-weight: 600; font-size: 1.05rem; }
li a:hover { color: #4aa3df; }
.meta { color: #9aa8b5; font-size: 0.85rem; margin-top: 4px; }
.pill { display: inline-block; background: #2a3340; color: #9aa8b5;
  font-size: 0.75rem; padding: 2px 8px; border-radius: 10px; margin-right: 6px; }
a.home { color: #4aa3df; text-decoration: none; font-size: 0.9rem; }
"""


def build(target: Path) -> None:
    archive_dir = target / "archive"
    entries: list[dict] = []
    if archive_dir.exists():
        for f in sorted(archive_dir.glob("*.html"), reverse=True):
            date = f.stem
            meta_path = archive_dir / f"{date}.meta.json"
            meta = {}
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    pass
            entries.append({"date": date, "file": f.name, "meta": meta})

    items = []
    for e in entries:
        m = e["meta"]
        pills = ""
        if m.get("n_articles") is not None:
            pills += f'<span class="pill">{m["n_articles"]} articles</span>'
        if m.get("n_scraped") is not None:
            pills += f'<span class="pill">{m["n_scraped"]} scrapés</span>'
        items.append(
            f'<li><a href="archive/{e["file"]}">{e["date"]}</a>'
            f'<div class="meta">{pills}</div></li>'
        )

    body = "".join(items) or "<li>Aucune revue publiée pour le moment.</li>"

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Archive — Revue MN</title>
<style>{PAGE_CSS}</style>
</head>
<body>
<p><a class="home" href="index.html">← Dernière revue</a></p>
<h1>🗂 Archive des revues</h1>
<p class="sub">Toutes les revues quotidiennes publiées par nuclear-med-review.</p>
<ul>
{body}
</ul>
</body>
</html>
"""
    (target / "archive.html").write_text(html, encoding="utf-8")
    print(f"archive.html ecrite : {len(entries)} entrees")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage : build_archive_index.py <target-dir>")
        sys.exit(1)
    build(Path(sys.argv[1]))
