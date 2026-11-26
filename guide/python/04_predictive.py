"""Step 4 - Predictive analytics: what will happen? Guide: guide/05-predictive.md

Trains a baseline and three models, compares them with cross-validation,
evaluates the chosen one once on a held-back test set, explains it, and writes
a score for every record that Power BI and the prescriptive step use.

Run:  python 04_predictive.py
"""
import warnings

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, brier_score_loss, confusion_matrix, f1_score,
                             precision_score, recall_score, roc_auc_score, roc_curve)
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

import config as C
from common import feature_columns, load_clean, save_fig, save_json, save_table

warnings.filterwarnings("ignore")
df = load_clean()
numeric, categorical = feature_columns(df)
print(f"Features: {len(numeric)} numeric, {len(categorical)} categorical")
print(f"Excluded for leakage: {C.LEAKAGE_COLS or 'none listed - are you sure?'}")
X, y = df[numeric + categorical], df["target"]

# 1. split: by time when there is a date, otherwise stratified ----------------------
if C.DATE_COL and C.DATE_COL in df.columns and df[C.DATE_COL].notna().any():
    cutoff = df[C.DATE_COL].quantile(0.8)
    train_idx, test_idx = df.index[df[C.DATE_COL] <= cutoff], df.index[df[C.DATE_COL] > cutoff]
    split_note = f"time-based: train up to {cutoff:%Y-%m-%d}, test after"
else:
    train_idx, test_idx = train_test_split(df.index, test_size=0.2, stratify=y, random_state=C.RANDOM_STATE)
    split_note = "stratified random 80/20 (no date column)"
X_train, X_test, y_train, y_test = X.loc[train_idx], X.loc[test_idx], y.loc[train_idx], y.loc[test_idx]
print(f"Split: {split_note}. Train {len(X_train):,}, test {len(X_test):,}, outcome rate {y.mean():.1%}")

# 2. preprocessing lives INSIDE the pipeline, so it is fitted on training folds only
prep = ColumnTransformer([
    ("num", Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), numeric),
    ("cat", Pipeline([("impute", SimpleImputer(strategy="most_frequent")),
                      ("onehot", OneHotEncoder(handle_unknown="ignore", min_frequency=20))]), categorical),
])
models = {
    "baseline (majority class)": DummyClassifier(strategy="prior"),
    "logistic regression": LogisticRegression(max_iter=2000, class_weight="balanced"),
    "random forest": RandomForestClassifier(n_estimators=300, min_samples_leaf=20, class_weight="balanced",
                                            random_state=C.RANDOM_STATE, n_jobs=-1),
    "gradient boosting": HistGradientBoostingClassifier(learning_rate=0.05, max_leaf_nodes=15,
                                                        class_weight="balanced", random_state=C.RANDOM_STATE),
}

# 3. compare with 5-fold cross-validation on the training data only ------------------
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=C.RANDOM_STATE)
rows = []
for name, est in models.items():
    pipe = Pipeline([("prep", prep), ("model", est)])
    s = cross_validate(pipe, X_train, y_train, cv=cv, scoring=["roc_auc", "average_precision"], n_jobs=1)
    rows.append({"model": name, "cv_roc_auc": s["test_roc_auc"].mean(), "cv_roc_auc_sd": s["test_roc_auc"].std(),
                 "cv_pr_auc": s["test_average_precision"].mean()})
comparison = pd.DataFrame(rows).sort_values("cv_roc_auc", ascending=False)
save_table(comparison, "predictive", "model_comparison")
print("\nCross-validated comparison (training data only):")
print(comparison.round(3).to_string(index=False))

# choose: best ROC-AUC, but prefer logistic regression if within 0.01 (easier to explain)
best = comparison.iloc[0]["model"]
lr_auc = comparison.set_index("model").loc["logistic regression", "cv_roc_auc"]
if best != "logistic regression" and comparison.iloc[0]["cv_roc_auc"] - lr_auc < 0.01:
    best = "logistic regression"
print(f"Chosen model: {best}")
final = Pipeline([("prep", prep), ("model", models[best])]).fit(X_train, y_train)

# 4. evaluate ONCE on the test set ------------------------------------------------------
p_test = final.predict_proba(X_test)[:, 1]
threshold = 0.5
# a business-friendly threshold: flag the riskiest 20% of records
threshold_top20 = float(np.quantile(p_test, 0.8))
pred = (p_test >= threshold_top20).astype(int)
order = np.argsort(-p_test)
top_decile = order[: max(1, len(order) // 10)]
metrics = {
    "split": split_note, "model": best, "test_records": int(len(y_test)), "test_outcome_rate": float(y_test.mean()),
    "roc_auc": roc_auc_score(y_test, p_test), "pr_auc": average_precision_score(y_test, p_test),
    "brier_score": brier_score_loss(y_test, p_test),
    "threshold_used": threshold_top20, "threshold_rule": "top 20% highest risk flagged",
    "precision": precision_score(y_test, pred), "recall": recall_score(y_test, pred), "f1": f1_score(y_test, pred),
    "lift_top_decile": float(y_test.iloc[top_decile].mean() / y_test.mean()),
    "confusion_matrix [[tn, fp], [fn, tp]]": confusion_matrix(y_test, pred).tolist(),
}
save_json(metrics, "predictive", "test_metrics")
print("\nTest-set results:")
for k, v in metrics.items():
    print(f"  {k}: {round(v, 3) if isinstance(v, float) else v}")

# charts: ROC curve and calibration
fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
fpr, tpr, _ = roc_curve(y_test, p_test)
axes[0].plot(fpr, tpr, label=f"{best} (AUC {metrics['roc_auc']:.2f})")
axes[0].plot([0, 1], [0, 1], "k--", label="random guess")
axes[0].set(xlabel="false positive rate", ylabel="true positive rate", title="ROC curve")
axes[0].legend()
frac, mean_pred = calibration_curve(y_test, p_test, n_bins=10, strategy="quantile")
axes[1].plot(mean_pred, frac, "o-")
axes[1].plot([0, 1], [0, 1], "k--")
axes[1].set(xlabel="predicted probability", ylabel="actual rate", title="Calibration (on the diagonal = trustworthy)")
save_fig(fig, "predictive", "roc_and_calibration")

# 5. explain: which features drive predictions (permutation importance on test data)
imp = permutation_importance(final, X_test, y_test, scoring="roc_auc", n_repeats=5, random_state=C.RANDOM_STATE)
importance = pd.DataFrame({"feature": X_test.columns, "importance_mean": imp.importances_mean,
                           "importance_sd": imp.importances_std}).sort_values("importance_mean", ascending=False)
save_table(importance, "predictive", "feature_importance")
print("\nMost important features (drop in ROC-AUC when shuffled):")
print(importance.head(10).round(4).to_string(index=False))
if importance["importance_mean"].iloc[0] > 0.15:
    print("WARNING: one feature dominates. Check it is not leaking the outcome (guide/05-predictive.md).")

# 6. score every record for Power BI and the prescriptive step -----------------------------
scores = df[[C.ID_COL]].copy() if C.ID_COL in df.columns else pd.DataFrame(index=df.index)
scores["risk_probability"] = final.predict_proba(X)[:, 1]
scores["risk_band"] = pd.qcut(scores["risk_probability"].rank(method="first"), 5,
                              labels=["very low", "low", "medium", "high", "very high"])
scores["in_test_set"] = scores.index.isin(test_idx).astype(int)
scores["actual_outcome"] = y.values
save_table(scores, "predictive", "scores")
print("\nDone. Load outputs/predictive/scores.csv into Power BI and relate it on the id column.")
