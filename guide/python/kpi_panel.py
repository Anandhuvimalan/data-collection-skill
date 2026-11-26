"""Company x period analysis for single-company projects. Guide: guide/08-company-period.md

For tables with one row per company per year/quarter/month (for example a
company's attrition rate and its peers'). Does descriptive (trend, index, peer
gap), diagnostic (drivers, on changes not levels) and predictive (forecast with
a backtest against a naive baseline) work in one script.

Run:  python kpi_panel.py
"""
import warnings

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

import config as C
from common import save_fig, save_json, save_table

warnings.filterwarnings("ignore")
p = pd.read_csv(C.PANEL_TABLE)
p[C.PANEL_PERIOD] = pd.to_datetime(p[C.PANEL_PERIOD], errors="coerce")
p = p.sort_values([C.PANEL_COMPANY, C.PANEL_PERIOD])
kpi, co = C.PANEL_KPI, C.PANEL_COMPANY
companies = p[co].unique().tolist()
print(f"{len(p)} rows, {len(companies)} companies, {p[C.PANEL_PERIOD].min():%Y} to {p[C.PANEL_PERIOD].max():%Y}")

# 1. descriptive: level, change, index, gap to peers ----------------------------------
p["change"] = p.groupby(co)[kpi].diff()
p["pct_change"] = p.groupby(co)[kpi].pct_change() * 100
first = p.groupby(co)[kpi].transform("first")
p["index_first_period_100"] = p[kpi] / first * 100
peer_median = p[p[co] != C.FOCAL_COMPANY].groupby(C.PANEL_PERIOD)[kpi].median().rename("peer_median")
p = p.merge(peer_median, on=C.PANEL_PERIOD, how="left")
p["gap_to_peer_median"] = p[kpi] - p["peer_median"]
save_table(p, "company_period", "kpi_panel_enriched")

fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
for c in companies:
    d = p[p[co] == c]
    lw = 3 if c == C.FOCAL_COMPANY else 1.2
    axes[0].plot(d[C.PANEL_PERIOD], d[kpi], lw=lw, label=c)
axes[0].set_title(f"{kpi} by company")
axes[0].legend()
f = p[p[co] == C.FOCAL_COMPANY]
axes[1].bar(f[C.PANEL_PERIOD].dt.year.astype(str), f["gap_to_peer_median"], color="#E45756")
axes[1].axhline(0, color="k", lw=0.8)
axes[1].set_title(f"{C.FOCAL_COMPANY}: gap to peer median")
save_fig(fig, "company_period", "kpi_trend_and_gap")

# 2. diagnostic: drivers, correlated on CHANGES (levels that both trend upward always correlate)
drivers = [d for d in C.PANEL_DRIVERS if d in p.columns]
rows = []
for d in drivers:
    dchg = p.groupby(co)[d].diff()
    both = pd.DataFrame({"kpi_change": p["change"], "driver_change": dchg}).dropna()
    if len(both) >= 5:
        rows.append({"driver": d, "observations": len(both),
                     "corr_of_changes": both["kpi_change"].corr(both["driver_change"]),
                     "corr_of_levels": p[[kpi, d]].dropna().corr().iloc[0, 1]})
drv = pd.DataFrame(rows)
if not drv.empty:
    drv["note"] = np.where(drv["observations"] < 15, "few observations: indicative only", "")
    save_table(drv.sort_values("corr_of_changes", key=abs, ascending=False), "company_period", "driver_correlations")
    print("\nDrivers (correlation of period-to-period changes):")
    print(drv.round(3).to_string(index=False))
else:
    print("\nNo driver columns found (set PANEL_DRIVERS in config.py).")

# 3. predictive: forecast the focal company's KPI, backtested against a naive forecast
s = f.set_index(C.PANEL_PERIOD)[kpi].dropna()
result = {"periods_available": len(s)}
if len(s) >= 6:
    h = 2
    train, test = s.iloc[:-h], s.iloc[-h:]
    naive_mae = float(np.mean(np.abs(test.values - train.iloc[-1])))
    holt = ExponentialSmoothing(train.values, trend="add", damped_trend=True).fit()
    holt_mae = float(np.mean(np.abs(test.values - holt.forecast(h))))
    result.update({"backtest_periods": h, "naive_mae": naive_mae, "damped_holt_mae": holt_mae,
                   "better_than_naive": holt_mae < naive_mae})
    full = ExponentialSmoothing(s.values, trend="add", damped_trend=True).fit()
    fc = full.forecast(3)
    resid_sd = float(np.std(full.resid, ddof=1))
    result["forecast_next_3"] = [{"step": i + 1, "forecast": float(v), "low_80": float(v - 1.28 * resid_sd),
                                  "high_80": float(v + 1.28 * resid_sd)} for i, v in enumerate(fc)]
    print(f"\nBacktest on last {h} periods: naive MAE {naive_mae:.3f}, damped Holt MAE {holt_mae:.3f}")
    if holt_mae >= naive_mae:
        result["advice"] = "the model does not beat 'same as last period'; report the naive forecast and say why"
        print("The model does NOT beat the naive forecast. Report the naive forecast (last value) and say so.")
    print("Forecast:", [round(x["forecast"], 3) for x in result["forecast_next_3"]])
else:
    result["note"] = "fewer than 6 periods: describe the trend, do not forecast; collect quarterly data if possible"
    print("\n" + result["note"])
save_json(result, "company_period", "forecast")
