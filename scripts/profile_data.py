#!/usr/bin/env python3
"""Profile the data files that were actually collected.

Row counts, column names, types, missing values, date ranges and join keys in a
data collection report must come from this output (evidence label [FILE]), not
from a catalog page and never from memory. Published descriptions are often
wrong, outdated, or describe a different version of the file.

Usage:
    python profile_data.py --project ./churn-project
    python profile_data.py ./some/folder --out ./profiles
    python profile_data.py ./file.csv

Reads .csv .tsv .txt(delimited) .xlsx .xls .json .jsonl .parquet (and .gz of the
text formats). Writes data_profile.md (read this) and data_profile.json.

Besides the usual per-column statistics it reports what decides whether a
four-stage analytics project is possible:
  * time columns and the period they span   -> trends, cohorts, forecasting
  * candidate outcome columns               -> predictive target
  * numeric measures and category columns   -> KPIs and segment comparisons
  * candidate keys and cross-file overlaps  -> a real relational model
  * disguised missing values, numbers stored as text, duplicate rows

Needs pandas (openpyxl for Excel, pyarrow for parquet).
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import sys
import warnings
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    print("pandas is required:  pip install pandas openpyxl pyarrow", file=sys.stderr)
    sys.exit(2)

warnings.filterwarnings("ignore")

TEXT_EXT = {".csv", ".tsv", ".txt", ".dat"}
EXCEL_EXT = {".xlsx", ".xlsm", ".xls"}
JSON_EXT = {".json", ".jsonl", ".ndjson"}
PARQUET_EXT = {".parquet", ".pq"}
MISSING_TOKENS = {"", "na", "n/a", "nan", "null", "none", "nil", "?", "-", "--", "unknown", "missing", "not available", "#n/a"}
# case-sensitive on purpose: customerID / customer_id / OrderKey are ids, "paid" and "valid" are not
ID_NAME_HINT = re.compile(r"(^[Ii][Dd]$|_[Ii][Dd]$|^[Ii][Dd]_|[a-z]I[Dd]$|ID$|_key$|^key$|Key$|KEY$|_code(_|$)|Code$|CODE$|uuid|UUID|guid|GUID|_no$|_number$|Number$)")
OUTCOME_NAME_HINT = re.compile(
    r"(churn|attrit|default|fraud|target|label|outcome|response|convert|cancel|exited|left|status|"
    r"success|fail|delay|late|return|readmi|survived|approved|is_|^y$|flag|won|lost|renew|click|purchas)", re.I)
DOC_NAME_HINT = re.compile(r"(readme|names|dictionary|description|codebook|metadata|license|licence|notes|about)", re.I)
DOC_EXT = {".md", ".pdf", ".docx", ".doc", ".html", ".htm", ".rtf", ".names"}
BIG_FILE_BYTES = 400 * 1024 * 1024
CHUNK_ROWS = 500_000


def real_suffix(path: Path) -> str:
    suffixes = [s.lower() for s in path.suffixes]
    if suffixes and suffixes[-1] in (".gz", ".bz2", ".xz") and len(suffixes) > 1:
        return suffixes[-2]
    return suffixes[-1] if suffixes else ""


def is_tabular(path: Path) -> bool:
    return real_suffix(path) in TEXT_EXT | EXCEL_EXT | JSON_EXT | PARQUET_EXT


def sniff_text(path: Path) -> tuple[str, str]:
    """Return (encoding, delimiter) for a delimited text file."""
    import gzip
    opener = gzip.open if path.suffix.lower() == ".gz" else open
    with opener(path, "rb") as fh:
        raw = fh.read(200_000)
    encoding = "utf-8"
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            raw.decode(enc)
            encoding = enc
            break
        except UnicodeDecodeError:
            continue
    text = raw.decode(encoding, "replace")
    lines = [ln for ln in text.splitlines()[:60] if ln.strip()]
    delimiter = ","
    if lines:
        # the delimiter that splits the first lines most consistently wins
        best = (0, 0.0)
        for cand in (",", ";", "\t", "|"):
            counts = [ln.count(cand) for ln in lines]
            if not counts or min(counts) == 0:
                continue
            consistency = sum(1 for c in counts if c == counts[0]) / len(counts)
            score = (counts[0], consistency)
            if consistency >= 0.7 and score > best:
                best, delimiter = score, cand
        if best == (0, 0.0):
            try:
                delimiter = csv.Sniffer().sniff("\n".join(lines[:20]), delimiters=",;\t|").delimiter
            except Exception:
                delimiter = ","
    return encoding, delimiter


def is_documentation(path: Path) -> bool:
    """README-like files and prose .txt files: worth reading, not worth profiling."""
    ext = real_suffix(path)
    if ext in DOC_EXT:
        return True
    if ext in (".txt", ".dat"):
        try:
            with open(path, "rb") as fh:
                text = fh.read(40_000).decode("utf-8", "replace")
        except Exception:
            return False
        lines = [ln for ln in text.splitlines()[:80] if ln.strip()]
        if len(lines) < 2:
            return True
        for cand in (",", ";", "\t", "|"):
            counts = [ln.count(cand) for ln in lines]
            if min(counts) > 0 and sum(1 for c in counts if c == counts[0]) / len(counts) >= 0.7:
                return False
        return True
    return False


def load_tables(path: Path) -> list[dict]:
    """Return one dict per table: {name, df, rows_total, sampled, read_notes}."""
    ext = real_suffix(path)
    notes: list[str] = []
    if ext in TEXT_EXT:
        encoding, delim = sniff_text(path)
        notes.append(f"encoding {encoding}, delimiter {delim!r}")
        if path.stat().st_size > BIG_FILE_BYTES:
            total, first = 0, None
            for chunk in pd.read_csv(path, sep=delim, encoding=encoding, chunksize=CHUNK_ROWS,
                                     low_memory=False, on_bad_lines="skip"):
                total += len(chunk)
                if first is None:
                    first = chunk
            notes.append(f"large file: statistics use the first {len(first):,} rows; row count is the full file")
            return [{"name": path.name, "df": first, "rows_total": total, "sampled": True, "read_notes": notes}]
        try:
            df = pd.read_csv(path, sep=delim, encoding=encoding, low_memory=False)
        except Exception as exc:
            notes.append(f"strict parse failed ({type(exc).__name__}); re-read skipping malformed lines")
            df = pd.read_csv(path, sep=delim, encoding=encoding, on_bad_lines="skip", engine="python")
        return [{"name": path.name, "df": df, "rows_total": len(df), "sampled": False, "read_notes": notes}]
    if ext in EXCEL_EXT:
        sheets = pd.read_excel(path, sheet_name=None)
        return [{"name": f"{path.name} [{sheet}]", "df": df, "rows_total": len(df), "sampled": False,
                 "read_notes": [f"Excel sheet {sheet!r}"]} for sheet, df in sheets.items() if df.shape[1] > 0]
    if ext in PARQUET_EXT:
        df = pd.read_parquet(path)
        return [{"name": path.name, "df": df, "rows_total": len(df), "sampled": False, "read_notes": ["parquet"]}]
    if ext in JSON_EXT:
        if ext in (".jsonl", ".ndjson"):
            df = pd.read_json(path, lines=True)
            return [{"name": path.name, "df": df, "rows_total": len(df), "sampled": False, "read_notes": ["JSON lines"]}]
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            obj = json.load(fh)
        records, where = None, "top-level list"
        if isinstance(obj, list):
            records = obj
        elif isinstance(obj, dict):
            lists = {k: v for k, v in obj.items() if isinstance(v, list) and v and isinstance(v[0], dict)}
            if lists:
                key = max(lists, key=lambda k: len(lists[k]))
                records, where = lists[key], f"list under key {key!r}"
        # World Bank style: [metadata, [records]]
        if isinstance(obj, list) and len(obj) == 2 and isinstance(obj[1], list) and obj[1] and isinstance(obj[1][0], dict):
            records, where = obj[1], "second element (API metadata + records)"
        if not records or not isinstance(records[0], dict):
            raise ValueError("JSON is not a list of records; inspect it by hand")
        df = pd.json_normalize(records)
        return [{"name": path.name, "df": df, "rows_total": len(df), "sampled": False,
                 "read_notes": [f"JSON flattened from {where}"]}]
    raise ValueError(f"unsupported file type {ext}")


def fmt_num(x) -> str:
    try:
        if pd.isna(x):
            return ""
    except Exception:
        pass
    if isinstance(x, (int,)) or (hasattr(x, "is_integer") and float(x).is_integer() and abs(float(x)) < 1e15):
        return f"{int(x):,}"
    try:
        return f"{float(x):,.4g}"
    except Exception:
        return str(x)


def short(val, limit: int = 28) -> str:
    s = str(val).replace("\n", " ").replace("|", "/").strip()
    return s if len(s) <= limit else s[: limit - 1] + "…"


def try_dates(series: "pd.Series") -> tuple["pd.Series | None", float]:
    """Parse a text column as dates if it plausibly is one. Returns (parsed, share parsed)."""
    sample = series.dropna().astype(str).head(3000)
    if sample.empty:
        return None, 0.0
    looks = sample.str.contains(r"\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4}|[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}|\d{4}-\d{2}$",
                                regex=True).mean()
    if looks < 0.8:
        return None, 0.0
    parsed = pd.to_datetime(series, errors="coerce")
    share = parsed.notna().sum() / max(series.notna().sum(), 1)
    if share < 0.9:
        try:
            parsed = pd.to_datetime(series, errors="coerce", format="mixed")
            share = parsed.notna().sum() / max(series.notna().sum(), 1)
        except Exception:
            pass
    return (parsed, share) if share >= 0.9 else (None, share)


def span_text(lo, hi) -> str:
    try:
        days = (hi - lo).days
    except Exception:
        return ""
    if days < 1:
        return "under 1 day"
    if days < 62:
        return f"{days} days"
    months = days / 30.44
    return f"{months:.0f} months" if months < 30 else f"{months / 12:.1f} years"


def profile_table(tbl: dict) -> dict:
    df: pd.DataFrame = tbl["df"]
    df.columns = [str(c).strip() for c in df.columns]
    n = len(df)
    cols = []
    for name in df.columns:
        s = df[name]
        missing = int(s.isna().sum())
        non_null = n - missing
        try:
            distinct = int(s.nunique(dropna=True))
        except TypeError:  # unhashable values such as lists
            distinct = int(s.astype(str).nunique(dropna=True))
        info = {
            "name": name, "dtype": str(s.dtype), "non_null": non_null, "missing": missing,
            "missing_pct": round(100 * missing / n, 2) if n else 0.0, "distinct": distinct,
            "role": "", "notes": [], "stats": "", "examples": [],
        }
        is_text = s.dtype == object or str(s.dtype).startswith(("string", "str"))
        unique_full = non_null == n and distinct == n and n > 0

        if pd.api.types.is_bool_dtype(s):
            info["role"] = "binary"
        elif pd.api.types.is_datetime64_any_dtype(s):
            info["role"] = "datetime"
            if non_null:
                lo, hi = s.min(), s.max()
                info["stats"] = f"{lo:%Y-%m-%d} → {hi:%Y-%m-%d} ({span_text(lo, hi)})"
                info["date_min"], info["date_max"] = f"{lo:%Y-%m-%d}", f"{hi:%Y-%m-%d}"
        elif pd.api.types.is_numeric_dtype(s):
            if non_null:
                info["stats"] = f"min {fmt_num(s.min())}, median {fmt_num(s.median())}, mean {fmt_num(s.mean())}, max {fmt_num(s.max())}"
            is_int = pd.api.types.is_integer_dtype(s) or (non_null and (s.dropna() % 1 == 0).all())
            if distinct <= 1:
                info["role"] = "constant"
            elif distinct == 2:
                info["role"] = "binary"
            elif unique_full and is_int:
                info["role"] = "id (unique)"
            elif ID_NAME_HINT.search(name) and is_int:
                info["role"] = "id / foreign key"
            elif is_int and distinct <= 20:
                info["role"] = "category (coded number)"
            else:
                info["role"] = "numeric measure"
            if is_int and re.search(r"year", name, re.I) and non_null and 1900 <= s.min() and s.max() <= 2100:
                info["role"] = "time (year)"
                info["stats"] = f"{int(s.min())} → {int(s.max())}"
        elif is_text:
            txt = s.dropna().astype(str)
            stripped = txt.str.strip()
            disguised = int(stripped.str.lower().isin(MISSING_TOKENS).sum())
            if disguised:
                info["disguised_missing"] = disguised
                info["notes"].append(f"{disguised:,} disguised missing (blank / NA-like text)")
            if (txt != stripped).any():
                info["notes"].append("leading/trailing spaces")
            real = stripped[~stripped.str.lower().isin(MISSING_TOKENS)]
            numeric_share = 0.0
            if len(real):
                as_num = pd.to_numeric(real.str.replace(",", "", regex=False).str.replace(r"^[$€£₹]\s*", "", regex=True),
                                       errors="coerce")
                numeric_share = float(as_num.notna().mean())
            parsed, date_share = (None, 0.0)
            if numeric_share < 0.9:
                parsed, date_share = try_dates(s)
            if parsed is not None:
                lo, hi = parsed.min(), parsed.max()
                info["role"] = "datetime (stored as text)"
                info["stats"] = f"{lo:%Y-%m-%d} → {hi:%Y-%m-%d} ({span_text(lo, hi)})"
                info["date_min"], info["date_max"] = f"{lo:%Y-%m-%d}", f"{hi:%Y-%m-%d}"
                if date_share < 1:
                    info["notes"].append(f"{(1 - date_share) * 100:.1f}% of values do not parse as dates")
            elif numeric_share >= 0.9 and not (ID_NAME_HINT.search(name) and distinct > 0.5 * max(non_null, 1)):
                info["role"] = "numeric stored as text"
                info["notes"].append(f"{numeric_share * 100:.1f}% of non-blank values are numbers: convert the type")
            elif distinct <= 1:
                info["role"] = "constant"
            elif distinct == 2:
                info["role"] = "binary"
            elif unique_full:
                info["role"] = "id (unique)"
            elif ID_NAME_HINT.search(name) and distinct > 50:
                info["role"] = "id / foreign key"
            elif distinct <= 50 or (n and distinct / n < 0.05 and distinct <= 1000):
                info["role"] = "category"
                low = stripped.str.lower()
                if low.nunique() < stripped.nunique():
                    info["notes"].append("same category in different letter case")
            else:
                avg_len = float(stripped.str.len().mean()) if len(stripped) else 0
                info["role"] = "free text" if avg_len > 40 else "high-cardinality text"
        else:
            info["role"] = "other"

        try:
            if info["role"] in ("category", "binary", "category (coded number)", "constant"):
                top = s.value_counts(dropna=True).head(5)
                info["examples"] = [f"{short(k)} ({v / max(non_null, 1) * 100:.0f}%)" for k, v in top.items()]
            else:
                info["examples"] = [short(v) for v in s.dropna().unique()[:3]]
        except Exception:
            info["examples"] = []
        if missing and info["missing_pct"] >= 40:
            info["notes"].append("mostly empty")
        cols.append(info)

    try:
        dup_rows = int(df.duplicated().sum())
    except TypeError:
        dup_rows = int(df.astype(str).duplicated().sum())

    key_cols = [c["name"] for c in cols if c["role"].startswith("id (unique)")]
    time_cols = [c for c in cols if c["role"].startswith(("datetime", "time"))]
    targets = [c for c in cols if c["role"] == "binary"]
    targets.sort(key=lambda c: 0 if OUTCOME_NAME_HINT.search(c["name"]) else 1)
    likely = [c for c in targets if OUTCOME_NAME_HINT.search(c["name"])]
    measures = [c["name"] for c in cols if c["role"] in ("numeric measure", "numeric stored as text")]
    categories = [c["name"] for c in cols if c["role"] in ("category", "category (coded number)")]

    readiness = []
    if time_cols:
        readiness.append("TIME: " + "; ".join(f"`{c['name']}` {c['stats']}" for c in time_cols[:6])
                         + ". Trends, period comparisons and time-based train/test splits are possible.")
    else:
        readiness.append("TIME: no date/time column in this table. If it joins to a table that has dates (see the "
                         "relationships section), time analysis comes from there. If it stands alone it is a snapshot: "
                         "no trends, no month-on-month or year-on-year comparison, no forecasting.")
    if targets:
        lead = ("likely by name: " + "; ".join(f"`{c['name']}` [{', '.join(c['examples'][:2])}]" for c in likely[:4]) + ". "
                if likely else "")
        others = [c for c in targets if c not in likely]
        readiness.append("OUTCOME CANDIDATES (two-valued columns): " + lead
                         + ("Other two-valued columns: " + ", ".join(f"`{c['name']}`" for c in others[:10]) + ". " if others else "")
                         + "Confirm from the documentation which one is a real business outcome and what its values mean.")
    else:
        readiness.append("OUTCOME CANDIDATES: no two-valued column. A prediction target would have to be a numeric "
                         "measure (regression/forecast) or be derived, and the derivation must be defensible.")
    readiness.append(f"MEASURES ({len(measures)}): " + (", ".join(f"`{m}`" for m in measures[:15]) or "none"))
    readiness.append(f"SEGMENT DIMENSIONS ({len(categories)}): " + (", ".join(f"`{m}`" for m in categories[:20]) or "none"))
    rows_total = tbl["rows_total"]
    if rows_total < 500:
        readiness.append(f"VOLUME: only {rows_total:,} rows. Fine for description; too thin for a credible predictive model.")
    elif rows_total < 5000:
        readiness.append(f"VOLUME: {rows_total:,} rows. Enough for simple models; keep them simple and cross-validate.")
    else:
        readiness.append(f"VOLUME: {rows_total:,} rows. Enough for train/validation/test splits.")

    return {
        "table": tbl["name"], "rows": rows_total, "columns": len(cols), "sampled": tbl["sampled"],
        "read_notes": tbl["read_notes"], "duplicate_rows": dup_rows, "candidate_keys": key_cols,
        "column_profiles": cols, "readiness": readiness,
    }


def relationships(tables: list[dict]) -> tuple[list[dict], list[dict]]:
    """Find real join keys between files, and spot files that are copies/subsets of each other.

    Returns (joins, same_structure). A shared column name is only treated as a
    candidate key when it looks like an identifier or is unique in one of the
    files, and it is only reported when the values genuinely overlap.
    """
    joins, same = [], []
    for i, a in enumerate(tables):
        for b in tables[i + 1:]:
            da, db = a["df"], b["df"]
            la = {str(c).lower(): c for c in da.columns}
            lb = {str(c).lower(): c for c in db.columns}
            common = la.keys() & lb.keys()
            union = la.keys() | lb.keys()
            if len(common) >= 3 and len(common) / len(union) >= 0.8:
                same.append({"table_a": a["name"], "table_b": b["name"], "rows_a": a["rows_total"],
                             "rows_b": b["rows_total"], "shared_columns": len(common), "total_columns": len(union)})
                continue
            for low in sorted(common):
                ca, cb = la[low], lb[low]
                sa, sb = da[ca], db[cb]
                ua = bool(sa.notna().all() and sa.is_unique)
                ub = bool(sb.notna().all() and sb.is_unique)
                if not (ID_NAME_HINT.search(str(ca)) or ua or ub):
                    continue
                if pd.api.types.is_float_dtype(sa) and not ID_NAME_HINT.search(str(ca)):
                    continue
                try:
                    va, vb = set(sa.dropna().astype(str)), set(sb.dropna().astype(str))
                except Exception:
                    continue
                if len(va) < 2 or len(vb) < 2:
                    continue
                inter = len(va & vb)
                if inter == 0:
                    continue
                card = ("one-to-one" if ua and ub else f"one ({a['name']}) to many ({b['name']})" if ua
                        else f"one ({b['name']}) to many ({a['name']})" if ub else "many-to-many (no unique side)")
                joins.append({
                    "column": str(ca), "table_a": a["name"], "table_b": b["name"],
                    "distinct_a": len(va), "distinct_b": len(vb),
                    "a_values_found_in_b_pct": round(100 * inter / len(va), 1),
                    "b_values_found_in_a_pct": round(100 * inter / len(vb), 1),
                    "cardinality": card,
                })
    return joins, same


def to_markdown(profiles: list[dict], rels: list[dict], same: list[dict], docs: list[str], skipped: list[str], root: Path) -> str:
    out = ["# Data profile", "",
           f"Generated {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC by profile_data.py from files under `{root}`.",
           "Numbers here are measured from the files themselves, so they may be cited with the evidence label **[FILE]**.", ""]
    out += ["## Summary", "", "| Table | Rows | Columns | Duplicate rows | Unique key column(s) | Time span |", "|---|---:|---:|---:|---|---|"]
    for p in profiles:
        spans = [f"{c['date_min']} → {c['date_max']}" for c in p["column_profiles"] if c.get("date_min")]
        years = [c["stats"] for c in p["column_profiles"] if c["role"] == "time (year)"]
        span = spans[0] if spans else (years[0] if years else "none (snapshot)")
        keys = ", ".join(f"`{k}`" for k in p["candidate_keys"][:3]) or "none found"
        rows = f"{p['rows']:,}" + (" *" if p["sampled"] else "")
        out.append(f"| {p['table']} | {rows} | {p['columns']} | {p['duplicate_rows']:,} | {keys} | {span} |")
    if any(p["sampled"] for p in profiles):
        out.append("\n\\* row count is exact; column statistics come from the first rows only.")
    out.append("")

    if docs:
        out += ["## Documentation shipped with the data", "",
                "Read these before interpreting any column: they hold the publisher's own definitions, units, "
                "collection period and caveats, which the numbers below cannot tell you.", ""]
        out += [f"- `{d}`" for d in docs] + [""]

    if same:
        out += ["## Files with the same structure", "",
                "These pairs share (almost) all columns, so they are versions, samples or train/test splits of ONE table, "
                "not related tables. Do not join them. Pick the right one (usually the fullest) or stack them, and say which.", "",
                "| File A | Rows | File B | Rows | Shared columns |", "|---|---:|---|---:|---:|"]
        for x in same:
            out.append(f"| {x['table_a']} | {x['rows_a']:,} | {x['table_b']} | {x['rows_b']:,} | {x['shared_columns']} of {x['total_columns']} |")
        out.append("")

    if len(profiles) > 1:
        out += ["## Cross-file relationships (measured)", ""]
        if rels:
            out += ["A shared column name is only a real join if the values overlap. Low overlap means the files do not belong together.", "",
                    "| Column | Table A | Table B | A values found in B | B values found in A | Cardinality |", "|---|---|---|---:|---:|---|"]
            for r in rels:
                out.append(f"| `{r['column']}` | {r['table_a']} | {r['table_b']} | {r['a_values_found_in_b_pct']}% | "
                           f"{r['b_values_found_in_a_pct']}% | {r['cardinality']} |")
        else:
            out.append("No shared key columns with overlapping values were found between different tables. "
                       "Do not invent a join; treat unrelated files as separate datasets.")
        out.append("")

    for p in profiles:
        out += [f"## {p['table']}", "",
                f"- Rows: **{p['rows']:,}**, columns: **{p['columns']}**, fully duplicated rows: **{p['duplicate_rows']:,}**",
                f"- Read as: {'; '.join(p['read_notes'])}",
                f"- Unique key column(s): {', '.join('`' + k + '`' for k in p['candidate_keys']) or 'none (check for a composite key)'}",
                "", "**What this table can support**", ""]
        out += [f"- {line}" for line in p["readiness"]]
        out += ["", "| # | Column | Stored type | Role | Missing | Distinct | Statistics / range | Examples | Flags |",
                "|---:|---|---|---|---:|---:|---|---|---|"]
        for i, c in enumerate(p["column_profiles"], 1):
            miss = f"{c['missing']:,} ({c['missing_pct']}%)" if c["missing"] else "0"
            out.append(f"| {i} | `{c['name']}` | {c['dtype']} | {c['role']} | {miss} | {c['distinct']:,} | {c['stats']} | "
                       f"{'; '.join(c['examples'])} | {'; '.join(c['notes'])} |")
        out.append("")
    if skipped:
        out += ["## Files not profiled", ""] + [f"- {s}" for s in skipped] + [""]
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description="Profile collected data files.")
    ap.add_argument("path", nargs="?", help="File or folder to profile (default: <project>/data/raw).")
    ap.add_argument("--project", help="Project folder; profiles go to <project>/data/profiles/")
    ap.add_argument("--out", help="Output folder (overrides --project).")
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    if not args.path and not args.project:
        ap.error("give a path to profile, or --project")
    root = Path(args.path) if args.path else Path(args.project) / "data" / "raw"
    if not root.exists():
        print(f"Nothing to profile: {root} does not exist. Was anything downloaded?", file=sys.stderr)
        return 1
    out_dir = Path(args.out) if args.out else (Path(args.project) / "data" / "profiles" if args.project else root if root.is_dir() else root.parent)
    out_dir.mkdir(parents=True, exist_ok=True)

    everything = [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.is_file())
    junk = ("__MACOSX", ".DS_Store")
    everything = [p for p in everything if not any(j in p.as_posix() for j in junk) and not p.name.startswith("._")]
    docs = [(p.name if root.is_file() else p.relative_to(root).as_posix()) for p in everything
            if is_documentation(p) or (DOC_NAME_HINT.search(p.stem) and real_suffix(p) in {".txt", ".md", ".pdf", ".docx", ".html"})]
    files = [p for p in everything if is_tabular(p) and not is_documentation(p)]
    if not files:
        print(f"No tabular files found under {root}.", file=sys.stderr)
        return 1

    tables, skipped = [], []
    for f in files:
        label = f.name if root.is_file() else f.relative_to(root).as_posix()
        try:
            for t in load_tables(f):
                t["name"] = label if t["name"] == f.name else t["name"].replace(f.name, label)
                tables.append(t)
        except Exception as exc:
            skipped.append(f"{label}: {type(exc).__name__}: {str(exc)[:160]}")

    profiles = [profile_table(t) for t in tables]
    rels, same = relationships(tables) if len(tables) > 1 else ([], [])

    md = to_markdown(profiles, rels, same, docs, skipped, root)
    (out_dir / "data_profile.md").write_text(md, encoding="utf-8")
    (out_dir / "data_profile.json").write_text(
        json.dumps({"generated_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "root": str(root), "tables": profiles, "relationships": rels,
                    "same_structure_files": same, "documentation_files": docs, "skipped": skipped},
                   indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    print(f"Profiled {len(profiles)} table(s) from {len(files)} file(s).")
    for p in profiles:
        print(f"  {p['table']}: {p['rows']:,} rows x {p['columns']} columns, {p['duplicate_rows']:,} duplicate rows")
        for line in p["readiness"][:2]:
            print(f"      {line[:230]}")
    for s in skipped:
        print(f"  SKIPPED {s}")
    if docs:
        print("  Documentation to read first: " + ", ".join(docs[:8]))
    if same:
        print(f"  {len(same)} file pair(s) have the same structure (versions/samples of one table) - see the profile.")
    print(f"Read this next: {out_dir / 'data_profile.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
