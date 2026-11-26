#!/usr/bin/env python3
"""Measure how much public data exists about each candidate company.

Give it the companies you are considering for a topic. For each one it
identifies the company (Wikidata), then checks live, no-login sources and
reports what it found, so the user can pick a company on evidence instead of
fame. A famous company with no public data makes a worse project than a
smaller one whose regulator publishes its complaints every month.

Usage:
    python company_lookup.py "Infosys" "Wipro" "Tata Consultancy Services" --topic "employee attrition" --project ./p
    python company_lookup.py "Capital One" "Discover Financial" --topic "customer complaints" --checks all

What it checks (each is skipped gracefully if the source is down):
    identity   Wikidata: legal name, country, industry, HQ, founded, website,
               stock listings, employees, LEI
    sec        SEC EDGAR: CIK, filing counts by form, XBRL financial facts and
               the years they cover (US-listed companies and foreign filers)
    datasets   Kaggle, Hugging Face and Zenodo listings that mention the company
    attention  Wikipedia monthly pageviews (a public-interest time series)
    cfpb       US consumer complaints naming the company (banks, lenders, cards)
    fda        openFDA recall records naming the company (drugs, devices, food)

Not checked automatically (search the web for these, see
references/company-data.md): annual reports, stock-exchange filings outside the
US (BSE/NSE, LSE...), regulator reports that rank companies, app-store reviews,
job postings, investor presentations.

Standard library only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

USER_AGENT = "Mozilla/5.0 (compatible; dataset-research/1.0)"
TIMEOUT = 60
ALL_CHECKS = ["identity", "sec", "datasets", "attention", "cfpb", "fda"]
DEFAULT_CHECKS = ["identity", "sec", "datasets", "attention"]
COMPANY_WORDS = re.compile(r"(company|corporation|business|enterprise|bank|firm|conglomerate|manufacturer|retailer|airline|"
                           r"operator|provider|insurer|brand|subsidiary|group|limited|inc\b|plc|startup|chain|multinational)", re.I)

_SEC_TICKERS: list[dict] | None = None


def get_json(url: str, ua: str = USER_AGENT):
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def norm(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[.,&'()]", " ", name)
    name = re.sub(r"\b(inc|incorporated|corp|corporation|co|company|ltd|limited|plc|llc|lp|holdings?|group|the|sa|ag|nv|se|de)\b", " ", name)
    return re.sub(r"\s+", " ", name).strip()


# --------------------------------------------------------------------------
# identity (Wikidata)
# --------------------------------------------------------------------------

def _claim_values(claims: dict, prop: str) -> list:
    out = []
    for st in claims.get(prop, []):
        dv = (st.get("mainsnak") or {}).get("datavalue", {}).get("value")
        quals = st.get("qualifiers") or {}
        out.append((dv, quals))
    return out


def _labels(ids: list[str]) -> dict[str, str]:
    ids = [i for i in dict.fromkeys(ids) if i]
    if not ids:
        return {}
    out = {}
    for k in range(0, len(ids), 40):
        chunk = "|".join(ids[k:k + 40])
        data = get_json(f"https://www.wikidata.org/w/api.php?action=wbgetentities&ids={chunk}&props=labels&languages=en&format=json")
        for qid, ent in (data.get("entities") or {}).items():
            out[qid] = ((ent.get("labels") or {}).get("en") or {}).get("value", qid)
    return out


def identify(name: str, country_hint: str | None) -> dict:
    params = urllib.parse.urlencode({"action": "wbsearchentities", "search": name, "language": "en",
                                     "type": "item", "format": "json", "limit": 7})
    hits = get_json("https://www.wikidata.org/w/api.php?" + params).get("search") or []
    if not hits:
        return {"found": False}
    # prefer a hit whose description reads like a company (and mentions the hinted country)
    def score(h):
        d = (h.get("description") or "")
        s = 2 if COMPANY_WORDS.search(d) else 0
        if country_hint and country_hint.lower() in d.lower():
            s += 1
        return -s
    hit = sorted(hits, key=score)[0]
    qid = hit["id"]
    ent = get_json(f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json")["entities"][qid]
    c = ent.get("claims") or {}

    def ids(prop):
        return [v.get("id") for v, _ in _claim_values(c, prop) if isinstance(v, dict) and v.get("id")]

    listings = []
    for v, quals in _claim_values(c, "P414"):
        if isinstance(v, dict) and v.get("id"):
            tickers = [((q.get("datavalue") or {}).get("value")) for q in quals.get("P249", [])]
            listings.append({"exchange_id": v["id"], "tickers": [t for t in tickers if t]})
    employees = []
    for v, quals in _claim_values(c, "P1128"):
        if isinstance(v, dict) and v.get("amount"):
            when = ((quals.get("P585") or [{}])[0].get("datavalue") or {}).get("value", {}).get("time", "")
            employees.append((when[1:5] if when else "", int(float(v["amount"]))))
    employees.sort()
    inception = next((v.get("time", "")[1:11] for v, _ in _claim_values(c, "P571") if isinstance(v, dict)), "")
    lab = _labels(ids("P17") + ids("P452") + ids("P159") + [l["exchange_id"] for l in listings])
    sitelinks = ent.get("sitelinks") or {}
    return {
        "found": True,
        "wikidata_id": qid,
        "wikidata_url": f"https://www.wikidata.org/wiki/{qid}",
        "label": ((ent.get("labels") or {}).get("en") or {}).get("value", name),
        "description": hit.get("description", ""),
        "country": [lab.get(i, i) for i in ids("P17")],
        "industry": [lab.get(i, i) for i in ids("P452")],
        "headquarters": [lab.get(i, i) for i in ids("P159")],
        "founded": inception,
        "website": next((v for v, _ in _claim_values(c, "P856") if isinstance(v, str)), ""),
        "listings": [{"exchange": lab.get(l["exchange_id"], l["exchange_id"]), "tickers": l["tickers"]} for l in listings],
        "employees_latest": employees[-1] if employees else None,
        "lei": next((v for v, _ in _claim_values(c, "P1278") if isinstance(v, str)), ""),
        "enwiki_title": (sitelinks.get("enwiki") or {}).get("title", ""),
        "wikipedia_languages": len([k for k in sitelinks if k.endswith("wiki")]),
        "other_matches": [f"{h.get('label')} ({h.get('description', '')})" for h in hits if h["id"] != qid][:3],
    }


# --------------------------------------------------------------------------
# SEC EDGAR
# --------------------------------------------------------------------------

def sec_check(name: str, ident: dict, ua: str) -> dict:
    global _SEC_TICKERS
    if _SEC_TICKERS is None:
        data = get_json("https://www.sec.gov/files/company_tickers.json", ua)
        _SEC_TICKERS = list(data.values())
    tickers = {t.upper() for l in ident.get("listings", []) for t in l.get("tickers", [])
               if re.search(r"nyse|nasdaq|new york|american stock", l.get("exchange", ""), re.I)}
    want = {norm(name), norm(ident.get("label", name))}
    match = next((r for r in _SEC_TICKERS if r["ticker"].upper() in tickers), None)
    if not match:
        match = next((r for r in _SEC_TICKERS if norm(r["title"]) in want), None)
    if not match:
        return {"found": False, "note": "not in SEC's list of listed companies (normal for companies not listed in the US)"}
    cik = int(match["cik_str"])
    cik10 = f"{cik:010d}"
    out = {"found": True, "cik": cik, "sec_name": match["title"], "ticker": match["ticker"],
           "filings_page": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik10}"}
    try:
        sub = get_json(f"https://data.sec.gov/submissions/CIK{cik10}.json", ua)
        recent = (sub.get("filings") or {}).get("recent") or {}
        forms = recent.get("form") or []
        dates = recent.get("filingDate") or []
        counts = {}
        for f in forms:
            if f in ("10-K", "10-Q", "20-F", "40-F", "6-K", "8-K", "DEF 14A"):
                counts[f] = counts.get(f, 0) + 1
        out.update({"sic": sub.get("sicDescription", ""), "recent_filing_counts": counts,
                    "filings_from": min(dates) if dates else "", "filings_to": max(dates) if dates else ""})
    except Exception as exc:
        out["submissions_error"] = f"{type(exc).__name__}: {exc}"
    try:
        facts = get_json(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik10}.json", ua).get("facts") or {}
        n_concepts, years = 0, set()
        for taxo, concepts in facts.items():
            if taxo == "dei":
                continue
            for cdata in concepts.values():
                n_concepts += 1
                for unit_rows in (cdata.get("units") or {}).values():
                    for row in unit_rows:
                        if row.get("fy"):
                            years.add(int(row["fy"]))
        out.update({"xbrl_concepts": n_concepts,
                    "xbrl_fiscal_years": f"{min(years)}-{max(years)}" if years else "",
                    "taxonomies": [t for t in facts if t != "dei"]})
    except Exception as exc:
        out["facts_error"] = f"{type(exc).__name__}: {exc}"
    out["fetch"] = [f"sec-facts:{cik}", f"sec-filings:{cik}"]
    return out


# --------------------------------------------------------------------------
# dataset catalogs (reuses find_datasets.py)
# --------------------------------------------------------------------------

def datasets_check(name: str, topic: str | None) -> dict:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import find_datasets as fd  # noqa: E402
    out, errors = [], []
    queries = [name] + ([f"{name} {topic}"] if topic else [])
    key = norm(name).split(" ")[0] if norm(name) else name.lower()
    seen = set()
    for q in queries:
        for src, fn in (("kaggle", fd.search_kaggle), ("huggingface", fd.search_huggingface), ("zenodo", fd.search_zenodo)):
            try:
                rows = fn(q, 10, "votes")
            except Exception as exc:
                errors.append(f"{src}: {type(exc).__name__}")
                continue
            for r in rows:
                text = f"{r.get('title', '')} {r.get('id', '')} {r.get('description', '')}".lower()
                if key and key not in text:
                    continue  # catalog matched on something else
                k = (r["source"], r["id"])
                if k in seen:
                    continue
                seen.add(k)
                owner = norm(f"{r.get('publisher', '')} {r.get('id', '').split('/')[0]}").replace(" ", "")
                by_company = bool(key) and key.replace(" ", "") in owner
                out.append({"source": r["source"], "title": r["title"], "page": r["landing_page"], "by_company": by_company,
                            "fetch": r.get("fetch_ref", ""), "license": r.get("license", ""),
                            "popularity": r.get("popularity", "")})
    out.sort(key=lambda d: not d["by_company"])
    return {"count": len(out), "by_company": sum(d["by_company"] for d in out), "items": out[:12], "errors": errors}


# --------------------------------------------------------------------------
# attention, CFPB, FDA
# --------------------------------------------------------------------------

def attention_check(ident: dict) -> dict:
    title = ident.get("enwiki_title")
    if not title:
        return {"found": False, "note": "no English Wikipedia article"}
    end = dt.date.today().replace(day=1) - dt.timedelta(days=1)
    url = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/"
           f"{urllib.parse.quote(title.replace(' ', '_'), safe='')}/monthly/20150701/{end:%Y%m%d}")
    items = get_json(url).get("items") or []
    if not items:
        return {"found": False}
    views = [i["views"] for i in items]
    return {"found": True, "months": len(items), "from": items[0]["timestamp"][:6], "to": items[-1]["timestamp"][:6],
            "avg_monthly_views": int(sum(views) / len(views)), "fetch": [f"wiki-pageviews:{title}"]}


def cfpb_check(name: str, ident: dict) -> dict:
    """Find the exact company name CFPB uses (it files complaints under legal names) and count complaints."""
    base = "https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1/"
    term = ident.get("label") or name
    try:
        data = get_json(base + "?" + urllib.parse.urlencode({"search_term": term, "field": "company", "size": 0}))
    except urllib.error.HTTPError as exc:
        return {"found": False, "note": f"CFPB API refused the request (HTTP {exc.code}); wait a minute and retry, or use the website"}
    agg = ((data.get("aggregations") or {}).get("company") or {})
    buckets = (agg.get("company") or agg).get("buckets") or []
    key = norm(term)
    matches = [b for b in buckets if key and key in norm(b.get("key", ""))]
    if not matches:
        return {"found": False, "note": f"no CFPB company name contains {term!r}" +
                (f"; closest: {', '.join(b['key'] for b in buckets[:3])}" if buckets else "")}
    best = max(matches, key=lambda b: b.get("doc_count", 0))
    return {"found": True, "company_name_in_cfpb": best["key"], "complaints": best["doc_count"],
            "other_names": [b["key"] for b in matches if b is not best][:3],
            "page": "https://www.consumerfinance.gov/data-research/consumer-complaints/search/?company=" + urllib.parse.quote(best["key"]),
            "fetch": [f"cfpb:{best['key']}"]}


def fda_check(name: str, ident: dict) -> dict:
    term = norm(ident.get("label") or name)  # whole name: a first word like "capital" matches unrelated firms
    counts = {}
    for kind in ("drug", "device", "food"):
        url = f"https://api.fda.gov/{kind}/enforcement.json?search=recalling_firm:%22{urllib.parse.quote(term)}%22&limit=1"
        time.sleep(0.3)
        try:
            counts[kind] = ((get_json(url).get("meta") or {}).get("results") or {}).get("total", 0)
        except urllib.error.HTTPError as exc:
            counts[kind] = 0 if exc.code == 404 else f"HTTP {exc.code}"
        except Exception as exc:
            counts[kind] = type(exc).__name__
    found = any(isinstance(v, int) and v > 0 for v in counts.values())
    return {"found": found, "search_term": term, "recall_records": counts,
            "fetch": [f"https://api.fda.gov/{k}/enforcement.json?search=recalling_firm:%22{urllib.parse.quote(term)}%22&limit=1000"
                      for k, v in counts.items() if isinstance(v, int) and v > 0]}


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------

def richness(rec: dict) -> tuple[int, list[str]]:
    """Rough score of how analysable the public footprint is. Higher is better."""
    pts, why = 0, []
    ds = rec.get("datasets") or {}
    if ds.get("by_company"):
        pts += 4
        why.append(f"{ds['by_company']} dataset(s) published under the company's own account")
    if ds.get("count", 0) > ds.get("by_company", 0):
        pts += 2
        why.append(f"{ds['count'] - ds.get('by_company', 0)} third-party dataset listing(s) name it (provenance unknown until checked)")
    sec = rec.get("sec") or {}
    if sec.get("found") and sec.get("xbrl_concepts"):
        pts += 3
        why.append(f"SEC financial facts {sec.get('xbrl_fiscal_years', '')}")
    cf = rec.get("cfpb") or {}
    if cf.get("found"):
        pts += 3
        why.append(f"{cf['complaints']:,} US consumer complaints")
    fda = rec.get("fda") or {}
    if fda.get("found"):
        pts += 2
        why.append("FDA recall records")
    at = rec.get("attention") or {}
    if at.get("found"):
        pts += 1
        why.append(f"{at['months']} months of Wikipedia attention")
    ident = rec.get("identity") or {}
    if ident.get("listings"):
        pts += 1
        why.append("publicly listed (annual reports and stock prices exist)")
    return pts, why


def to_markdown(results: list[dict], topic: str | None, now: str) -> str:
    out = [f"# Company data scan ({now})", ""]
    if topic:
        out += [f"Topic: **{topic}**", ""]
    out += ["Measured from live public sources in this run. The score counts which kinds of open data exist; it does not "
            "judge the company. Sources that need web search (annual reports, non-US exchange filings, regulator reports, "
            "reviews) are not scored here and can change the ranking.", "",
            "| Rank | Company | Country | Industry | Listed | Score | What exists |", "|---:|---|---|---|---|---:|---|"]
    ranked = sorted(results, key=lambda r: -r["score"])
    for i, r in enumerate(ranked, 1):
        ident = r.get("identity") or {}
        listed = "; ".join(f"{l['exchange']} {','.join(l['tickers'])}".strip() for l in ident.get("listings", [])[:3]) or "no"
        out.append(f"| {i} | {ident.get('label', r['query'])} | {', '.join(ident.get('country', [])[:2])} | "
                   f"{', '.join(ident.get('industry', [])[:2])} | {listed} | {r['score']} | {'; '.join(r['why']) or 'little found'} |")
    out.append("")
    for r in ranked:
        ident = r.get("identity") or {}
        out += [f"## {ident.get('label', r['query'])}", ""]
        if not ident.get("found"):
            out += [f"Not found on Wikidata under {r['query']!r}. Check the spelling or use the legal name.", ""]
        else:
            emp = ident.get("employees_latest")
            out += [f"- Identity: {ident.get('description', '')} ({ident['wikidata_url']})",
                    f"- Country / HQ: {', '.join(ident.get('country', []))} / {', '.join(ident.get('headquarters', []))}",
                    f"- Industry: {', '.join(ident.get('industry', []))}; founded {ident.get('founded', '') or 'n/a'}",
                    f"- Website: {ident.get('website', '') or 'n/a'}; LEI: {ident.get('lei', '') or 'n/a'}",
                    f"- Employees (Wikidata, may be dated): {f'{emp[1]:,} ({emp[0]})' if emp else 'n/a'}"]
            if ident.get("other_matches"):
                out.append(f"- Other Wikidata matches for the name (check you have the right one): {'; '.join(ident['other_matches'])}")
        sec = r.get("sec")
        if sec:
            if sec.get("found"):
                out.append(f"- SEC EDGAR: {sec['sec_name']} (CIK {sec['cik']}, {sec.get('sic', '')}); recent filings "
                           f"{sec.get('recent_filing_counts', {})}; XBRL concepts {sec.get('xbrl_concepts', 'n/a')} "
                           f"for fiscal years {sec.get('xbrl_fiscal_years', 'n/a')}. Fetch: {', '.join(sec.get('fetch', []))}")
            else:
                out.append(f"- SEC EDGAR: {sec.get('note', 'not found')}")
        cf = r.get("cfpb")
        if cf:
            out.append(f"- CFPB complaints: {cf['complaints']:,} under {cf['company_name_in_cfpb']!r}. Fetch: cfpb:{cf['company_name_in_cfpb']}"
                       if cf.get("found") else f"- CFPB complaints: {cf.get('note', 'none')}")
        fda = r.get("fda")
        if fda:
            out.append(f"- openFDA recalls (firm name contains {fda['search_term']!r}): {fda['recall_records']}")
        at = r.get("attention")
        if at:
            out.append(f"- Wikipedia attention: {at['months']} months {at['from']}→{at['to']}, avg {at['avg_monthly_views']:,} views/month. "
                       f"Fetch: {at['fetch'][0]}" if at.get("found") else f"- Wikipedia attention: {at.get('note', 'none')}")
        ds = r.get("datasets")
        if ds:
            out.append(f"- Dataset listings naming the company: {ds['count']}")
            for d in ds["items"][:8]:
                tag = " **published by the company**" if d.get("by_company") else ""
                out.append(f"  - [{d['source']}] {d['title']}{tag} - {d['page']}" + (f" (fetch: {d['fetch']})" if d["fetch"] else ""))
        if r.get("errors"):
            out.append(f"- Checks that failed: {'; '.join(r['errors'])}")
        out.append("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description="Measure the public data footprint of candidate companies.")
    ap.add_argument("companies", nargs="+", help="Company names (2-8 candidates is typical).")
    ap.add_argument("--topic", help="The project topic; also searched together with each company name.")
    ap.add_argument("--country", help="Country hint used to pick the right company when names clash.")
    ap.add_argument("--checks", default=",".join(DEFAULT_CHECKS),
                    help=f"Comma list or 'all'. Default: {','.join(DEFAULT_CHECKS)}. Available: {','.join(ALL_CHECKS)}")
    ap.add_argument("--contact", help="Contact address for the SEC user-agent, ONLY if the user provided one for this purpose.")
    ap.add_argument("--project", help="Project folder; writes <project>/data/company_scan.md and .json")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    checks = ALL_CHECKS if args.checks.strip() == "all" else [c.strip() for c in args.checks.split(",") if c.strip()]
    if "identity" not in checks:
        checks = ["identity"] + checks
    sec_ua = f"dataset-research {args.contact}" if args.contact else USER_AGENT
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    results = []
    for name in args.companies:
        rec, errors = {"query": name}, []
        try:
            rec["identity"] = identify(name, args.country)
        except Exception as exc:
            rec["identity"] = {"found": False}
            errors.append(f"identity: {type(exc).__name__}: {exc}")
        ident = rec["identity"]
        for chk, fn in (("sec", lambda: sec_check(name, ident, sec_ua)),
                        ("datasets", lambda: datasets_check(ident.get("label") if ident.get("found") else name, args.topic)),
                        ("attention", lambda: attention_check(ident)),
                        ("cfpb", lambda: cfpb_check(name, {**ident, **{"sec_name": (rec.get("sec") or {}).get("sec_name", "")}})),
                        ("fda", lambda: fda_check(name, ident))):
            if chk not in checks:
                continue
            try:
                rec[chk] = fn()
            except Exception as exc:
                errors.append(f"{chk}: {type(exc).__name__}: {str(exc)[:120]}")
        rec["errors"] = errors
        rec["score"], rec["why"] = richness(rec)
        results.append(rec)
        print(f"scanned {name}: score {rec['score']} - {'; '.join(rec['why']) or 'little found'}")

    md = to_markdown(results, args.topic, now)
    print()
    print(md)
    if args.project:
        d = Path(args.project) / "data"
        d.mkdir(parents=True, exist_ok=True)
        (d / "company_scan.md").write_text(md, encoding="utf-8")
        (d / "company_scan.json").write_text(json.dumps({"run_at_utc": now, "topic": args.topic, "checks": checks,
                                                         "results": results}, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Written: {d / 'company_scan.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
