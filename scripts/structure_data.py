#!/usr/bin/env python3
"""Turn downloaded raw files into tidy, analysis-ready tables plus a data dictionary.

Raw files stay untouched in data/raw/. This writes data/processed/*.csv and
data/processed/data_dictionary.csv, which is what SQL, Python and Power BI
load. Every processed table records which raw file it came from.

Usage:
    python structure_data.py --project ./my-project
    python structure_data.py --project ./my-project --company-id infosys

Known formats get purpose-built tables:
    SEC companyfacts JSON      -> financials_long.csv (every fact) and
                                  financials_annual.csv (one row per fiscal year,
                                  common measures as columns)
    SEC submissions JSON       -> filings.csv
    Wikipedia pageviews JSON   -> attention_monthly.csv
    CFPB complaint JSON pages  -> complaints.csv (all months stacked)
    any other JSON of records  -> <file>.csv (flattened)
CSV, Excel and parquet files are copied through with cleaned column names, so
every table sits in one folder for loading. Nothing is filtered or imputed:
cleaning decisions belong in the preparation plan, not here.

Needs pandas.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    print("pandas is required:  pip install pandas openpyxl pyarrow", file=sys.stderr)
    sys.exit(2)

# Common SEC concepts, first match wins. US-GAAP and IFRS names both appear because
# foreign filers (e.g. Indian IT companies filing 20-F) report under IFRS.
ANNUAL_MEASURES = {
    "revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet", "Revenue",
                "RevenueFromContractsWithCustomers"],
    "operating_income": ["OperatingIncomeLoss", "ProfitLossFromOperatingActivities"],
    "net_income": ["NetIncomeLoss", "ProfitLoss", "ProfitLossAttributableToOwnersOfParent"],
    "total_assets": ["Assets"],
    "total_liabilities": ["Liabilities"],
    "equity": ["StockholdersEquity", "Equity", "EquityAttributableToOwnersOfParent"],
    "cash": ["CashAndCashEquivalentsAtCarryingValue", "CashAndCashEquivalents"],
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities", "CashFlowsFromUsedInOperatingActivities"],
    "employee_benefits_expense": ["EmployeeBenefitsExpense", "LaborAndRelatedExpense"],
    "eps_basic": ["EarningsPerShareBasic", "BasicEarningsLossPerShare"],
}
ANNUAL_FORMS = {"10-K", "20-F", "40-F", "10-K/A", "20-F/A"}


def snake(name: str) -> str:
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(name).strip())
    name = re.sub(r"[^0-9a-zA-Z]+", "_", name).strip("_").lower()
    return name or "column"


def unique_cols(cols) -> list[str]:
    seen, out = {}, []
    for c in cols:
        c = snake(c)
        if c in seen:
            seen[c] += 1
            c = f"{c}_{seen[c]}"
        else:
            seen[c] = 0
        out.append(c)
    return out


def sec_facts(obj: dict, company_id: str, source: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    for taxo, concepts in (obj.get("facts") or {}).items():
        for concept, cdata in concepts.items():
            for unit, items in (cdata.get("units") or {}).items():
                for it in items:
                    rows.append({
                        "company_id": company_id, "cik": obj.get("cik"), "taxonomy": taxo, "concept": concept,
                        "label": cdata.get("label"), "unit": unit, "value": it.get("val"),
                        "period_start": it.get("start"), "period_end": it.get("end"), "fiscal_year": it.get("fy"),
                        "fiscal_period": it.get("fp"), "form": it.get("form"), "filed": it.get("filed"),
                        "frame": it.get("frame"), "accession": it.get("accn"), "source_file": source,
                    })
    long = pd.DataFrame(rows)
    if long.empty:
        return long, long
    # annual: full-year duration facts from annual forms; keep the latest filing for each period end
    a = long[long["form"].isin(ANNUAL_FORMS) & long["fiscal_period"].eq("FY")].copy()
    a["days"] = (pd.to_datetime(a["period_end"], errors="coerce") - pd.to_datetime(a["period_start"], errors="coerce")).dt.days
    a = a[(a["days"].isna()) | (a["days"].between(330, 400))]
    a = a.sort_values("filed").drop_duplicates(["concept", "unit", "period_end"], keep="last")
    wide = None
    for measure, concepts in ANNUAL_MEASURES.items():
        # companies switch concept names over the years; use the one covering the most fiscal years
        coverage = {c: a.loc[a["concept"] == c, "period_end"].nunique() for c in concepts}
        hit = max(coverage, key=coverage.get) if any(coverage.values()) else None
        if not hit:
            continue
        sub = a[a["concept"] == hit]
        unit = sub["unit"].value_counts().index[0]  # main currency / unit
        sub = sub[sub["unit"] == unit][["period_end", "value"]].rename(columns={"value": measure})
        sub[f"{measure}_unit"] = unit
        sub[f"{measure}_concept"] = hit
        wide = sub if wide is None else wide.merge(sub, on="period_end", how="outer")
    if wide is None:
        return long, pd.DataFrame()
    wide.insert(0, "company_id", company_id)
    wide["fiscal_year_end"] = pd.to_datetime(wide["period_end"], errors="coerce").dt.date
    wide = wide.drop(columns=["period_end"]).sort_values("fiscal_year_end")
    wide["source_file"] = source
    return long, wide


def sec_filings(obj: dict, company_id: str, source: str) -> pd.DataFrame:
    recent = (obj.get("filings") or {}).get("recent") or {}
    df = pd.DataFrame(recent)
    if df.empty:
        return df
    df.columns = unique_cols(df.columns)
    df.insert(0, "company_id", company_id)
    df["source_file"] = source
    return df


def pageviews(obj: dict, company_id: str, source: str) -> pd.DataFrame:
    df = pd.DataFrame(obj.get("items") or [])
    if df.empty:
        return df
    df["month"] = pd.to_datetime(df["timestamp"].str[:8], format="%Y%m%d").dt.date
    df = df[["month", "article", "views"]].rename(columns={"article": "wikipedia_article", "views": "pageviews"})
    df.insert(0, "company_id", company_id)
    df["source_file"] = source
    return df


def cfpb(obj: dict, company_id: str, source: str) -> pd.DataFrame:
    hits = ((obj.get("hits") or {}).get("hits")) or []
    df = pd.json_normalize([h.get("_source", {}) for h in hits])
    if df.empty:
        return df
    df.columns = unique_cols(df.columns)
    df.insert(0, "company_id", company_id)
    df["source_file"] = source
    return df


def generic_records(obj, source: str) -> pd.DataFrame | None:
    records = None
    if isinstance(obj, list) and obj and isinstance(obj[0], dict):
        records = obj
    elif isinstance(obj, list) and len(obj) == 2 and isinstance(obj[1], list):  # World Bank style
        records = obj[1]
    elif isinstance(obj, dict):
        lists = {k: v for k, v in obj.items() if isinstance(v, list) and v and isinstance(v[0], dict)}
        if lists:
            records = lists[max(lists, key=lambda k: len(lists[k]))]
    if not records:
        return None
    df = pd.json_normalize(records)
    df.columns = unique_cols(df.columns)
    df["source_file"] = source
    return df


def describe(df: pd.DataFrame, table: str) -> list[dict]:
    out = []
    for c in df.columns:
        s = df[c]
        ex = s.dropna().astype(str).head(3).tolist()
        out.append({"table": table, "column": c, "type": str(s.dtype), "non_null": int(s.notna().sum()),
                    "rows": len(df), "examples": " | ".join(x[:40] for x in ex), "description": ""})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Build tidy tables and a data dictionary from data/raw.")
    ap.add_argument("--project", required=True)
    ap.add_argument("--company-id", help="Short id put in a company_id column of company tables (default: from folder names).")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    project = Path(args.project)
    raw, out = project / "data" / "raw", project / "data" / "processed"
    if not raw.exists():
        print(f"No raw data at {raw}.", file=sys.stderr)
        return 1
    out.mkdir(parents=True, exist_ok=True)

    tables: dict[str, list[pd.DataFrame]] = {}
    notes = []

    def add(name, df):
        if df is not None and not df.empty:
            tables.setdefault(name, []).append(df)

    for f in sorted(raw.rglob("*")):
        if not f.is_file() or "__MACOSX" in f.as_posix() or f.name.startswith("._"):
            continue
        rel = f.relative_to(raw).as_posix()
        cid = args.company_id or rel.split("/")[0]
        low = f.name.lower()
        try:
            if low.endswith(".json"):
                obj = json.loads(f.read_text(encoding="utf-8", errors="replace"))
                if isinstance(obj, dict) and "facts" in obj and "entityName" in obj:
                    long, wide = sec_facts(obj, cid, rel)
                    add("financials_long", long)
                    add("financials_annual", wide)
                elif isinstance(obj, dict) and "filings" in obj and "cik" in obj:
                    add("filings", sec_filings(obj, cid, rel))
                elif isinstance(obj, dict) and isinstance(obj.get("items"), list) and obj["items"] and "views" in obj["items"][0]:
                    add("attention_monthly", pageviews(obj, cid, rel))
                elif isinstance(obj, dict) and "hits" in obj and "_shards" in obj:
                    add("complaints", cfpb(obj, cid, rel))
                else:
                    df = generic_records(obj, rel)
                    if df is None:
                        notes.append(f"{rel}: JSON with no record list; inspect it by hand")
                    else:
                        add(snake(f.stem), df)
            elif low.endswith((".csv", ".tsv")):
                df = pd.read_csv(f, sep=None, engine="python", encoding_errors="replace")
                df.columns = unique_cols(df.columns)
                add(snake(f.stem), df)
            elif low.endswith((".xlsx", ".xls")):
                for sheet, df in pd.read_excel(f, sheet_name=None).items():
                    if df.shape[1]:
                        df.columns = unique_cols(df.columns)
                        add(snake(f"{f.stem}_{sheet}"), df)
            elif low.endswith((".parquet", ".pq")):
                df = pd.read_parquet(f)
                df.columns = unique_cols(df.columns)
                add(snake(f.stem), df)
        except Exception as exc:
            notes.append(f"{rel}: could not structure ({type(exc).__name__}: {str(exc)[:120]})")

    dictionary = []
    print(f"Structured tables in {out}:")
    for name, parts in sorted(tables.items()):
        df = pd.concat(parts, ignore_index=True)
        if name == "complaints" and "complaint_id" in df.columns:
            df = df.drop_duplicates("complaint_id")
        path = out / f"{name}.csv"
        df.to_csv(path, index=False, encoding="utf-8")
        dictionary += describe(df, name)
        print(f"  {name}.csv  {len(df):,} rows x {df.shape[1]} columns")
    if dictionary:
        pd.DataFrame(dictionary).to_csv(out / "data_dictionary.csv", index=False, encoding="utf-8")
        print("  data_dictionary.csv  (fill in the description column from the publishers' documentation)")
    (out / "structure_log.json").write_text(json.dumps({
        "generated_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tables": {n: int(sum(len(p) for p in parts)) for n, parts in tables.items()}, "notes": notes}, indent=2), encoding="utf-8")
    for n in notes:
        print(f"  NOTE {n}")
    print(f"Next: python profile_data.py {out} --out {project / 'data' / 'profiles' / 'processed'}")
    return 0 if tables else 1


if __name__ == "__main__":
    sys.exit(main())
