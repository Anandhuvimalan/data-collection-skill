"""Step 3 - Diagnostic analytics: why is it happening? Guide: guide/04-diagnostic.md

Tests every candidate factor against the outcome, corrects for testing many
factors at once, checks the leading factors together in one model, and checks
whether a factor still matters once a suspected confounder is held constant.

Run:  python 03_diagnostic.py
"""
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from statsmodels.stats.multitest import multipletests

import config as C
from common import feature_columns, load_clean, save_table

warnings.filterwarnings("ignore")
df = load_clean()
numeric, categorical = feature_columns(df)
y = df["target"]

# 1. one factor at a time ---------------------------------------------------------
rows = []
for col in categorical:
    table = pd.crosstab(df[col], y)
    if table.shape[0] < 2 or table.shape[1] < 2:
        continue
    chi2, p, dof, _ = stats.chi2_contingency(table)
    cramers_v = np.sqrt(chi2 / (table.values.sum() * (min(table.shape) - 1)))
    rates = df.groupby(col)["target"].mean()
    rows.append({"factor": col, "type": "categorical", "test": "chi-square", "p_value": p,
                 "effect_size": cramers_v, "effect_measure": "Cramer's V",
                 "detail": f"highest {rates.idxmax()} {rates.max():.1%}, lowest {rates.idxmin()} {rates.min():.1%}"})
for col in numeric:
    a, b = df.loc[y == 1, col].dropna(), df.loc[y == 0, col].dropna()
    if len(a) < 5 or len(b) < 5:
        continue
    u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
    rank_biserial = 1 - 2 * u / (len(a) * len(b))   # -1..1: how strongly the groups separate
    rows.append({"factor": col, "type": "numeric", "test": "Mann-Whitney U", "p_value": p,
                 "effect_size": abs(rank_biserial), "effect_measure": "rank-biserial r",
                 "detail": f"median when outcome {a.median():.2f} vs {b.median():.2f} when not"})
uni = pd.DataFrame(rows)
# many tests at once: control the false discovery rate
uni["p_adjusted"] = multipletests(uni["p_value"], method="fdr_bh")[1]
uni["significant"] = uni["p_adjusted"] < 0.05
uni["strength"] = pd.cut(uni["effect_size"], [-0.01, 0.1, 0.3, 0.5, 1.0], labels=["negligible", "small", "medium", "large"])
uni = uni.sort_values("effect_size", ascending=False)
save_table(uni, "diagnostic", "factor_tests")
print("Factors ranked by strength of association:")
print(uni[["factor", "test", "effect_size", "strength", "p_adjusted", "detail"]].head(12).to_string(index=False))

# 2. leading factors together: logistic regression with odds ratios ---------------
lead = uni[uni["significant"] & (uni["effect_size"] >= 0.1)]["factor"].tolist()[:8] or uni["factor"].tolist()[:5]
X = pd.get_dummies(df[lead], drop_first=True, dtype=float)
num_in = [c for c in lead if c in numeric]
X[num_in] = (X[num_in] - X[num_in].mean()) / X[num_in].std()   # per 1 standard deviation
X = X.loc[:, X.std() > 0]
# drop columns that repeat information already in the matrix (e.g. several
# "no internet service" dummies that are identical) - otherwise the model cannot be fitted
keep = []
for col in X.columns:
    trial = X[keep + [col]].to_numpy()
    if np.linalg.matrix_rank(trial) == len(keep) + 1:
        keep.append(col)
dropped = [c for c in X.columns if c not in keep]
if dropped:
    print(f"\nLeft out of the regression because they duplicate other columns: {dropped}")
X = sm.add_constant(X[keep])
try:
    model = sm.Logit(y, X).fit(disp=0, maxiter=200)
    ci = model.conf_int()
    odds = pd.DataFrame({"term": model.params.index, "odds_ratio": np.exp(model.params.values),
                         "ci_low": np.exp(ci[0].values), "ci_high": np.exp(ci[1].values),
                         "p_value": model.pvalues.values}).query("term != 'const'")
    odds["reading"] = np.where(odds["odds_ratio"] > 1, "raises the odds", "lowers the odds")
    odds = odds.sort_values("odds_ratio", ascending=False)
    save_table(odds, "diagnostic", "odds_ratios")
    print(f"\nMultivariable logistic regression on {len(lead)} leading factors (pseudo R2 {model.prsquared:.3f}):")
    print(odds.head(10).to_string(index=False))
except Exception as exc:  # perfect separation or too many categories
    print(f"\nLogistic regression could not be fitted ({type(exc).__name__}); reduce factors or merge rare categories.")

# 3. confounding check: does the top categorical factor still matter within bands of the control?
top_cat = next((f for f in uni["factor"] if f in categorical and f != C.CONTROL_COL), None)
if top_cat and C.CONTROL_COL and C.CONTROL_COL in df.columns:
    ctrl = df[C.CONTROL_COL]
    bands = pd.qcut(ctrl, 4, duplicates="drop") if C.CONTROL_COL in numeric else ctrl
    strat = df.assign(_band=bands).groupby(["_band", top_cat], observed=True)["target"].agg(records="size", outcome_rate="mean")
    strat = strat.reset_index()
    strat["_band"] = strat["_band"].astype(str)
    strat = strat.rename(columns={"_band": f"{C.CONTROL_COL}_band"})
    save_table(strat, "diagnostic", f"stratified_{top_cat}_by_{C.CONTROL_COL}")
    pivot = strat.pivot(index=f"{C.CONTROL_COL}_band", columns=top_cat, values="outcome_rate")
    pivot = pivot.reindex(strat[f"{C.CONTROL_COL}_band"].unique())   # keep bands in low-to-high order
    print(f"\nOutcome rate of '{top_cat}' within each band of '{C.CONTROL_COL}':")
    print((pivot * 100).round(1).to_string())
    print("If the gap between categories survives inside every band, it is not just the control factor in disguise.")

print("\nDone. Write each hypothesis as supported / not supported / inconclusive, with the test and effect size.")
