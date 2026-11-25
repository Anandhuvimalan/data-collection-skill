#!/usr/bin/env python3
"""Search public dataset catalogs and return real, linkable candidates.

Every row this prints came back from a live catalog API in this run, so the
title, URL, size and licence are what the catalog says right now - not what a
model remembers. That is the point: candidates that go into a data collection
report should start here (or from a page that was actually opened), never from
memory.

Usage:
    python find_datasets.py "customer churn" "telecom churn" --project ./my-project
    python find_datasets.py "road accidents" --sources kaggle,zenodo --limit 15
    python find_datasets.py "air quality" --ckan https://data.gov.uk --ckan https://open.canada.ca/data

Sources (no account needed): kaggle, huggingface, uci, zenodo, dataverse, plus
any CKAN open-data portal passed with --ckan.

Popularity is NOT provenance. A dataset with 500k downloads can still be a
fictional vendor sample. Open the landing page before classifying anything.

Standard library only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

USER_AGENT = "Mozilla/5.0 (compatible; dataset-research/1.0)"
TIMEOUT = 45
DEFAULT_SOURCES = ["kaggle", "huggingface", "uci", "zenodo", "dataverse"]


def get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def clean(text, limit: int = 220) -> str:
    """Collapse whitespace, strip HTML tags, and shorten."""
    if not text:
        return ""
    text = html.unescape(re.sub(r"<[^>]+>", " ", str(text)))
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def human_size(n) -> str:
    try:
        n = float(n)
    except (TypeError, ValueError):
        return ""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return ""


# --------------------------------------------------------------------------
# One function per catalog. Each returns a list of normalised dicts.
# --------------------------------------------------------------------------

def search_kaggle(query: str, limit: int, sort: str) -> list[dict]:
    out, page = [], 1
    while len(out) < limit and page <= 3:
        params = {"search": query, "page": page}
        if sort != "relevance":
            params["sortBy"] = sort
        data = get_json("https://www.kaggle.com/api/v1/datasets/list?" + urllib.parse.urlencode(params))
        if not data:
            break
        for d in data:
            ref = d.get("ref")
            if not ref:
                continue
            out.append({
                "source": "kaggle",
                "id": ref,
                "title": d.get("title") or ref,
                "landing_page": d.get("url") or f"https://www.kaggle.com/datasets/{ref}",
                "publisher": d.get("ownerName") or d.get("creatorName") or "",
                "size_bytes": d.get("totalBytes"),
                "license": d.get("licenseName") or "",
                "last_updated": (d.get("lastUpdated") or "")[:10],
                "popularity": f"{d.get('downloadCount', 0)} downloads, {d.get('voteCount', 0)} votes",
                "description": clean(d.get("subtitle") or d.get("description")),
                "fetch_ref": f"kaggle:{ref}",
                "access": "open (no login)",
            })
        page += 1
    return out[:limit]


def search_huggingface(query: str, limit: int, sort: str) -> list[dict]:
    params = {"search": query, "limit": limit, "full": "true", "sort": "downloads", "direction": "-1"}
    data = get_json("https://huggingface.co/api/datasets?" + urllib.parse.urlencode(params))
    out = []
    for d in data:
        ds_id = d.get("id")
        if not ds_id or d.get("private"):
            continue
        tags = d.get("tags") or []
        lic = next((t.split(":", 1)[1] for t in tags if t.startswith("license:")), "")
        size_cat = next((t.split(":", 1)[1] for t in tags if t.startswith("size_categories:")), "")
        gated = d.get("gated")
        out.append({
            "source": "huggingface",
            "id": ds_id,
            "title": ds_id,
            "landing_page": f"https://huggingface.co/datasets/{ds_id}",
            "publisher": d.get("author") or "",
            "size_bytes": None,
            "size_note": f"rows: {size_cat}" if size_cat else "",
            "license": lic,
            "last_updated": (d.get("lastModified") or "")[:10],
            "popularity": f"{d.get('downloads', 0)} downloads, {d.get('likes', 0)} likes",
            "description": clean(d.get("description")),
            "fetch_ref": f"hf:{ds_id}",
            "access": "gated (needs account + approval)" if gated else "open (no login)",
        })
    return out


def search_uci(query: str, limit: int, sort: str) -> list[dict]:
    listing = get_json("https://archive.ics.uci.edu/api/datasets/list?" + urllib.parse.urlencode({"search": query}))
    out = []
    for item in (listing.get("data") or [])[:limit]:
        uid = item.get("id")
        try:
            d = get_json(f"https://archive.ics.uci.edu/api/dataset?id={uid}").get("data") or {}
        except Exception:
            d = {}
        repo_url = d.get("repository_url") or f"https://archive.ics.uci.edu/dataset/{uid}"
        slug = repo_url.rstrip("/").rsplit("/", 1)[-1]
        rows, feats = d.get("num_instances"), d.get("num_features")
        out.append({
            "source": "uci",
            "id": str(uid),
            "title": d.get("name") or item.get("name") or str(uid),
            "landing_page": repo_url,
            "publisher": "UCI ML Repository" + (f" / {', '.join((d.get('creators') or [])[:3])}" if d.get("creators") else ""),
            "size_bytes": None,
            "size_note": f"{rows} rows x {feats} features (as stated by UCI)" if rows else "",
            "license": "see landing page (most UCI sets are CC BY 4.0)",
            "last_updated": str(d.get("year_of_dataset_creation") or ""),
            "popularity": "",
            "description": clean(d.get("abstract")),
            "fetch_ref": f"https://archive.ics.uci.edu/static/public/{uid}/{slug}.zip",
            "access": "open (no login)",
        })
    return out


def search_zenodo(query: str, limit: int, sort: str) -> list[dict]:
    params = {"q": query, "type": "dataset", "size": limit, "sort": "bestmatch"}
    data = get_json("https://zenodo.org/api/records?" + urllib.parse.urlencode(params))
    out = []
    for h in (data.get("hits") or {}).get("hits") or []:
        md = h.get("metadata") or {}
        files = h.get("files") or []
        creators = ", ".join(c.get("name", "") for c in (md.get("creators") or [])[:3])
        out.append({
            "source": "zenodo",
            "id": str(h.get("id")),
            "title": md.get("title") or h.get("title") or "",
            "landing_page": (h.get("links") or {}).get("self_html") or f"https://zenodo.org/records/{h.get('id')}",
            "publisher": creators,
            "size_bytes": sum(f.get("size") or 0 for f in files) or None,
            "size_note": f"{len(files)} file(s)" if files else "",
            "license": (md.get("license") or {}).get("id", ""),
            "last_updated": md.get("publication_date") or "",
            "popularity": f"{(h.get('stats') or {}).get('downloads', 0)} downloads",
            "description": clean(md.get("description")),
            "fetch_ref": f"zenodo:{h.get('id')}" if md.get("access_right") == "open" else "",
            "access": "open (no login)" if md.get("access_right") == "open" else f"{md.get('access_right')}",
        })
    return out


def search_dataverse(query: str, limit: int, sort: str) -> list[dict]:
    params = {"q": query, "type": "dataset", "per_page": limit}
    data = get_json("https://dataverse.harvard.edu/api/search?" + urllib.parse.urlencode(params))
    out = []
    for d in (data.get("data") or {}).get("items") or []:
        out.append({
            "source": "dataverse",
            "id": d.get("global_id") or "",
            "title": d.get("name") or "",
            "landing_page": d.get("url") or "",
            "publisher": d.get("publisher") or d.get("name_of_dataverse") or "",
            "size_bytes": None,
            "size_note": f"{d.get('fileCount')} file(s)" if d.get("fileCount") else "",
            "license": "see landing page",
            "last_updated": (d.get("published_at") or "")[:10],
            "popularity": "",
            "description": clean(d.get("description")),
            "fetch_ref": "",
            "access": "open; some files may be restricted (check landing page)",
        })
    return out


def search_ckan(base: str, query: str, limit: int) -> list[dict]:
    base = base.rstrip("/")
    params = urllib.parse.urlencode({"q": query, "rows": limit})
    data, last_err = None, None
    for path in ("/api/3/action/package_search", "/api/action/package_search"):
        try:
            data = get_json(f"{base}{path}?{params}")
            break
        except Exception as exc:  # try the other common mount point
            last_err = exc
    if data is None:
        raise last_err  # type: ignore[misc]
    host = urllib.parse.urlparse(base).netloc
    out = []
    for r in (data.get("result") or {}).get("results") or []:
        resources = [
            {"name": x.get("name") or "", "format": (x.get("format") or "").upper(), "url": x.get("url") or ""}
            for x in (r.get("resources") or [])
            if x.get("url")
        ]
        formats = sorted({x["format"] for x in resources if x["format"]})
        out.append({
            "source": f"ckan:{host}",
            "id": r.get("name") or r.get("id") or "",
            "title": r.get("title") or r.get("name") or "",
            "landing_page": f"{base}/dataset/{r.get('name')}",
            "publisher": (r.get("organization") or {}).get("title", ""),
            "size_bytes": None,
            "size_note": f"{len(resources)} resource(s): {', '.join(formats)}" if resources else "",
            "license": r.get("license_title") or "",
            "last_updated": (r.get("metadata_modified") or "")[:10],
            "popularity": "",
            "description": clean(r.get("notes")),
            "fetch_ref": "",
            "resources": resources[:15],
            "access": "open (official government portal)",
        })
    return out


SEARCHERS = {
    "kaggle": search_kaggle,
    "huggingface": search_huggingface,
    "uci": search_uci,
    "zenodo": search_zenodo,
    "dataverse": search_dataverse,
}


def main() -> int:
    ap = argparse.ArgumentParser(description="Search public dataset catalogs for real candidate datasets.")
    ap.add_argument("queries", nargs="+", help="One or more search phrases. Try several phrasings.")
    ap.add_argument("--sources", default=",".join(DEFAULT_SOURCES),
                    help=f"Comma-separated. Default: {','.join(DEFAULT_SOURCES)}")
    ap.add_argument("--ckan", action="append", default=[], metavar="URL",
                    help="Base URL of a CKAN open-data portal to search too (repeatable).")
    ap.add_argument("--limit", type=int, default=8, help="Max results per source per query (default 8).")
    ap.add_argument("--kaggle-sort", default="votes", choices=["votes", "relevance", "updated", "hottest"],
                    help="Kaggle ordering (default votes: well-documented sets surface first).")
    ap.add_argument("--project", help="Project folder; results are appended to <project>/data/search_log.json")
    ap.add_argument("--out", help="Explicit path for the JSON log (overrides --project).")
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    sources = [s.strip().lower() for s in args.sources.split(",") if s.strip()]
    unknown = [s for s in sources if s not in SEARCHERS]
    if unknown:
        print(f"Unknown source(s): {', '.join(unknown)}. Choose from: {', '.join(SEARCHERS)}", file=sys.stderr)
        return 2

    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    results, errors, seen = [], [], set()

    for query in args.queries:
        for src in sources:
            try:
                rows = SEARCHERS[src](query, args.limit, args.kaggle_sort)
            except Exception as exc:
                errors.append({"source": src, "query": query, "error": f"{type(exc).__name__}: {exc}"})
                continue
            for r in rows:
                key = (r["source"], r["id"])
                if key in seen:
                    continue
                seen.add(key)
                r["query"] = query
                r["retrieved_at_utc"] = now
                results.append(r)
        for base in args.ckan:
            try:
                rows = search_ckan(base, query, args.limit)
            except Exception as exc:
                errors.append({"source": f"ckan:{base}", "query": query, "error": f"{type(exc).__name__}: {exc}"})
                continue
            for r in rows:
                key = (r["source"], r["id"])
                if key in seen:
                    continue
                seen.add(key)
                r["query"] = query
                r["retrieved_at_utc"] = now
                results.append(r)

    # ---- human-readable output -------------------------------------------
    print(f"# Dataset search results ({now})")
    print(f"Queries: {', '.join(repr(q) for q in args.queries)}")
    print(f"{len(results)} candidate(s). These are leads: open each landing page before trusting or classifying it.\n")
    by_source: dict[str, list[dict]] = {}
    for r in results:
        by_source.setdefault(r["source"], []).append(r)
    for src, rows in by_source.items():
        print(f"## {src} ({len(rows)})")
        for r in rows:
            size = human_size(r.get("size_bytes")) or r.get("size_note") or "size n/a"
            print(f"- **{r['title']}**")
            print(f"  page: {r['landing_page']}")
            bits = [size, f"licence: {r['license'] or 'not stated'}", f"updated: {r['last_updated'] or 'n/a'}"]
            if r.get("popularity"):
                bits.append(r["popularity"])
            bits.append(r["access"])
            print(f"  {' | '.join(bits)}")
            if r.get("publisher"):
                print(f"  by: {r['publisher']}")
            if r.get("description"):
                print(f"  about: {r['description']}")
            if r.get("fetch_ref"):
                print(f"  fetch: {r['fetch_ref']}")
            for res in (r.get("resources") or [])[:6]:
                print(f"  resource [{res['format'] or '?'}] {res['name']}: {res['url']}")
        print()
    if errors:
        print("## Sources that failed (not searched - say so in the report)")
        for e in errors:
            print(f"- {e['source']} / {e['query']!r}: {e['error']}")
        print()

    # ---- JSON log ---------------------------------------------------------
    out_path = Path(args.out) if args.out else (Path(args.project) / "data" / "search_log.json" if args.project else None)
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        log = {"searches": []}
        if out_path.exists():
            try:
                log = json.loads(out_path.read_text(encoding="utf-8"))
            except Exception:
                log = {"searches": []}
        log.setdefault("searches", []).append({
            "run_at_utc": now,
            "queries": args.queries,
            "sources": sources + [f"ckan:{b}" for b in args.ckan],
            "result_count": len(results),
            "errors": errors,
            "results": results,
        })
        out_path.write_text(json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Search log written to: {out_path}")

    return 0 if results else 1


if __name__ == "__main__":
    sys.exit(main())
