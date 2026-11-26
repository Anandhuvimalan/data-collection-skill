"""Step 1 - Prepare the analysis table. Guide: guide/02-data-preparation.md

Reads RAW_TABLE, fixes the problems every raw file has, writes CLEAN_TABLE and a
data-quality log you can paste into your report. It never deletes rows silently:
every change is counted in outputs/preparation/quality_log.json.

Run:  python 01_prepare.py
"""
import numpy as np
import pandas as pd

import config as C
from common import save_json, save_table, snake

MISSING_TOKENS = {"", "na", "n/a", "nan", "null", "none", "?", "-", "unknown", "missing"}

log = {"source": str(C.RAW_TABLE.relative_to(C.PROJECT)), "steps": []}


def note(step, detail):
    log["steps"].append({"step": step, "detail": detail})
    print(f"- {step}: {detail}")


df = pd.read_csv(C.RAW_TABLE)
log["rows_in"], log["columns_in"] = len(df), df.shape[1]
print(f"Loaded {len(df):,} rows x {df.shape[1]} columns")

# 1. consistent column names -------------------------------------------------
df.columns = [snake(c) for c in df.columns]
note("column names", "converted to lower_snake_case")

# 2. text clean-up: trim spaces, unify case, turn disguised blanks into real missing values
for col in df.select_dtypes(include=["object", "string"]).columns:
    s = df[col].astype("string").str.strip()
    disguised = s.str.lower().isin(MISSING_TOKENS)
    if disguised.any():
        note("disguised missing", f"{col}: {int(disguised.sum())} blank or NA-like values set to missing")
    s = s.mask(disguised)
    df[col] = s

# 3. numbers stored as text --------------------------------------------------
for col in df.select_dtypes(include="string").columns:
    if col == C.ID_COL:
        continue
    as_num = pd.to_numeric(df[col].str.replace(",", "", regex=False), errors="coerce")
    if df[col].notna().sum() and as_num.notna().sum() / df[col].notna().sum() > 0.95:
        df[col] = as_num
        note("type fix", f"{col}: text converted to number")

# 4. dates --------------------------------------------------------------------
if C.DATE_COL:
    df[C.DATE_COL] = pd.to_datetime(df[C.DATE_COL], errors="coerce")
    note("type fix", f"{C.DATE_COL}: parsed as date ({int(df[C.DATE_COL].isna().sum())} could not be parsed)")

# 5. categories: same spelling for the same thing -----------------------------
for col in df.select_dtypes(include="string").columns:
    if col == C.ID_COL:
        continue
    before = df[col].nunique()
    df[col] = df[col].str.lower().str.replace(r"\s+", " ", regex=True)
    after = df[col].nunique()
    if after < before:
        note("standardise", f"{col}: {before} spellings merged into {after} categories")

# 6. duplicates ----------------------------------------------------------------
full_dups = int(df.duplicated().sum())
df = df.drop_duplicates()
note("duplicates", f"{full_dups} fully duplicated rows removed")
if C.ID_COL in df.columns:
    key_dups = int(df[C.ID_COL].duplicated().sum())
    note("duplicate keys", f"{key_dups} rows share an {C.ID_COL} with another row"
         + (" - investigate before analysis" if key_dups else ""))

# 7. missing values: report, then treat ----------------------------------------
missing = df.isna().sum()
missing = missing[missing > 0]
log["missing_before_treatment"] = {k: int(v) for k, v in missing.items()}
for col, n in missing.items():
    share = n / len(df)
    if col in (C.TARGET, C.ID_COL):
        df = df[df[col].notna()]
        note("missing", f"{col}: {n} rows without {col} dropped (cannot be analysed)")
    elif share > 0.4:
        note("missing", f"{col}: {share:.0%} missing - kept as is; consider dropping the column")
    elif pd.api.types.is_numeric_dtype(df[col]):
        df[f"{col}_was_missing"] = df[col].isna().astype(int)
        df[col] = df[col].fillna(df[col].median())
        note("missing", f"{col}: {n} filled with the median, flag column {col}_was_missing added")
    else:
        df[col] = df[col].fillna("missing")
        note("missing", f"{col}: {n} labelled 'missing' (kept as its own category)")

# 8. outliers: flag, do not delete ---------------------------------------------
for col in df.select_dtypes(include=np.number).columns:
    if col.endswith("_was_missing") or df[col].nunique() <= 2:
        continue
    q1, q3 = df[col].quantile([0.25, 0.75])
    iqr = q3 - q1
    if iqr == 0:
        continue
    out = (df[col] < q1 - 3 * iqr) | (df[col] > q3 + 3 * iqr)
    if out.any():
        df[f"{col}_outlier"] = out.astype(int)
        note("outliers", f"{col}: {int(out.sum())} extreme values flagged in {col}_outlier (kept)")

# 9. target as 0/1 --------------------------------------------------------------
if C.TARGET in df.columns:
    t = df[C.TARGET].astype("string").str.lower()
    df["target"] = (t == str(C.POSITIVE).lower()).astype(int)
    rate = df["target"].mean()
    note("target", f"'{C.TARGET}' = '{C.POSITIVE}' coded as target=1; rate {rate:.1%}")
    if rate == 0 or rate == 1:
        raise SystemExit(f"Target has one value only. Check POSITIVE in config.py (values: {t.unique()[:5]})")

# 10. validation rules ------------------------------------------------------------
problems = []
for col in df.select_dtypes(include=np.number).columns:
    if any(w in col for w in ("charge", "amount", "price", "revenue", "salary", "age", "tenure", "count", "qty")):
        neg = int((df[col] < 0).sum())
        if neg:
            problems.append(f"{col}: {neg} negative values")
log["validation_problems"] = problems
note("validation", "; ".join(problems) if problems else "no negative amounts, ages or counts")

log["rows_out"], log["columns_out"] = len(df), df.shape[1]
df.to_csv(C.CLEAN_TABLE, index=False)
print(f"\nWrote {C.CLEAN_TABLE.relative_to(C.PROJECT)}: {len(df):,} rows x {df.shape[1]} columns")
save_json(log, "preparation", "quality_log")
summary = pd.DataFrame({"column": df.columns, "type": df.dtypes.astype(str).values,
                        "missing_after": df.isna().sum().values, "distinct": df.nunique().values})
save_table(summary, "preparation", "column_summary")
