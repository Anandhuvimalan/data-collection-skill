"""Step 2 - Descriptive analytics: what is happening? Guide: guide/03-descriptive.md

Writes KPI tables and charts to outputs/descriptive/.
Run:  python 02_descriptive.py
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

import config as C
from common import feature_columns, load_clean, save_fig, save_json, save_table

df = load_clean()
numeric, categorical = feature_columns(df)
n = len(df)

# 1. headline KPIs ------------------------------------------------------------
kpis = {"records": n, "outcome_count": int(df["target"].sum()), "outcome_rate": round(float(df["target"].mean()), 4)}
if C.VALUE_COL and C.VALUE_COL in df.columns:
    kpis["total_value"] = round(float(df[C.VALUE_COL].sum()), 2)
    kpis["value_at_risk"] = round(float(df.loc[df["target"] == 1, C.VALUE_COL].sum()), 2)
    kpis["value_at_risk_share"] = round(kpis["value_at_risk"] / kpis["total_value"], 4)
print("Headline KPIs:", kpis)
save_json(kpis, "descriptive", "kpis")

# 2. outcome rate by every category ---------------------------------------------
rows = []
for col in categorical:
    g = df.groupby(col, dropna=False)["target"].agg(records="size", outcome_count="sum", outcome_rate="mean").reset_index()
    g.insert(0, "dimension", col)
    g = g.rename(columns={col: "segment"})
    g["share_of_records"] = g["records"] / n
    g["share_of_outcomes"] = g["outcome_count"] / max(df["target"].sum(), 1)
    g["small_segment"] = g["records"] < 30   # rates on fewer than 30 records are unreliable
    rows.append(g)
segments = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
if not segments.empty:
    segments["gap_vs_overall_pts"] = (segments["outcome_rate"] - kpis["outcome_rate"]) * 100
    segments = segments.sort_values(["dimension", "outcome_rate"], ascending=[True, False])
    save_table(segments, "descriptive", "segments")
    top = segments[~segments["small_segment"]].nlargest(10, "gap_vs_overall_pts")
    print("\nSegments with the highest outcome rate (min 30 records):")
    print(top[["dimension", "segment", "records", "outcome_rate"]].to_string(index=False))

    # chart: the 6 dimensions with the widest spread
    spread = segments.groupby("dimension")["outcome_rate"].agg(lambda s: s.max() - s.min()).nlargest(6).index
    fig, axes = plt.subplots(2, 3, figsize=(14, 7))
    for ax, dim in zip(axes.flat, spread):
        d = segments[segments["dimension"] == dim].sort_values("outcome_rate")
        ax.barh(d["segment"].astype(str), d["outcome_rate"] * 100, color="#4C78A8")
        ax.axvline(kpis["outcome_rate"] * 100, color="#E45756", ls="--", lw=1)
        ax.set_title(dim)
        ax.set_xlabel("outcome rate %")
    for ax in list(axes.flat)[len(spread):]:
        ax.axis("off")
    fig.suptitle("Outcome rate by segment (dashed line = overall)")
    save_fig(fig, "descriptive", "segments")

# 3. numeric measures: distribution and comparison by outcome ---------------------
if numeric:
    stats = df.groupby("target")[numeric].median().T
    stats.columns = [f"median_target_{c}" for c in stats.columns]
    stats["overall_mean"] = df[numeric].mean()
    stats["overall_median"] = df[numeric].median()
    stats["skew"] = df[numeric].skew()
    stats = stats.reset_index().rename(columns={"index": "measure"})
    save_table(stats, "descriptive", "numeric_summary")
    cols = numeric[:6]
    fig, axes = plt.subplots(1, len(cols), figsize=(4 * len(cols), 3.5), squeeze=False)
    for ax, col in zip(axes.flat, cols):
        for t, colr in ((0, "#4C78A8"), (1, "#E45756")):
            ax.hist(df.loc[df["target"] == t, col], bins=30, alpha=0.6, color=colr, label=f"target={t}", density=True)
        ax.set_title(col)
        ax.legend()
    save_fig(fig, "descriptive", "distributions")

    # banded view of the first numeric measure (for example tenure bands)
    col = (C.CONTROL_COL if C.CONTROL_COL in numeric else numeric[0])
    df["_band"] = pd.qcut(df[col], q=5, duplicates="drop")
    bands = df.groupby("_band", observed=True)["target"].agg(records="size", outcome_rate="mean").reset_index()
    bands["_band"] = bands["_band"].astype(str)
    save_table(bands.rename(columns={"_band": f"{col}_band"}), "descriptive", f"{col}_bands")

# 4. time trend, only when there is a real date ------------------------------------
if C.DATE_COL and C.DATE_COL in df.columns and df[C.DATE_COL].notna().any():
    m = df.set_index(C.DATE_COL).resample("MS")["target"].agg(["size", "sum", "mean"]).reset_index()
    m.columns = ["month", "records", "outcome_count", "outcome_rate"]
    m["outcome_rate_3m_avg"] = m["outcome_rate"].rolling(3).mean()
    m["yoy_change_pts"] = (m["outcome_rate"] - m["outcome_rate"].shift(12)) * 100
    save_table(m, "descriptive", "monthly_trend")
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(m["month"], m["outcome_rate"] * 100, label="monthly")
    ax.plot(m["month"], m["outcome_rate_3m_avg"] * 100, label="3-month average")
    ax.set_ylabel("outcome rate %")
    ax.legend()
    save_fig(fig, "descriptive", "monthly_trend")
else:
    print("\nNo date column: trend, month-on-month and year-on-year views are not possible from this table.")

print("\nDone. Read outputs/descriptive/ and write 3-5 'where is the problem concentrated' statements.")
