"""Step 5 - Prescriptive analytics: what should be done? Guide: guide/06-prescriptive.md

Turns risk scores into a decision: which records get the action, under the
budget and capacity limits, with the expected net benefit, a scenario table
and a sensitivity check on every assumption, plus the size of the test needed
to prove the action works.

Run:  python 05_prescriptive.py   (after 04_predictive.py)
"""
import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize

import config as C
from common import load_clean, out_dir, save_json, save_table

scores_path = C.OUTPUTS / "predictive" / "scores.csv"
if not scores_path.exists():
    raise SystemExit("Run 04_predictive.py first.")
scores = pd.read_csv(scores_path)
df = load_clean()
if C.VALUE_COL and C.VALUE_COL in df.columns:
    scores = scores.merge(df[[C.ID_COL, C.VALUE_COL]], on=C.ID_COL, how="left")
    value = scores[C.VALUE_COL].fillna(scores[C.VALUE_COL].median())
else:
    value = pd.Series(1.0, index=scores.index)   # no money column: value = 1 unit per record
A = {k: dict(zip(("low", "base", "high"), v)) for k, v in C.ASSUMPTIONS.items()}


def plan(case: str):
    """Expected net value of acting on each record, then the best set under budget and capacity."""
    saved = A["months_of_value_saved"][case] * value                      # what keeping one leaver is worth
    benefit = scores["risk_probability"] * A["success_rate"][case] * saved
    cost = A["action_cost"][case]
    env = benefit - cost                                                  # expected net value per record
    # decision: x_i = 1 if record i gets the action. maximise sum(env * x) subject to
    #   sum(cost * x) <= BUDGET and sum(x) <= CAPACITY. Solved exactly as a 0/1 programme.
    candidates = env[env > 0]
    n = len(candidates)
    if n == 0:
        return env, pd.Series(0, index=scores.index), 0.0
    res = milp(c=-candidates.values, integrality=np.ones(n), bounds=Bounds(0, 1),
               constraints=[LinearConstraint(np.vstack([np.full(n, cost), np.ones(n)]), -np.inf, [C.BUDGET, C.CAPACITY])])
    chosen = pd.Series(0, index=scores.index)
    chosen.loc[candidates.index] = np.round(res.x).astype(int) if res.success else 0
    return env, chosen, float(env[chosen == 1].sum())


# 1. base case decision list ----------------------------------------------------
env, chosen, total = plan("base")
scores["expected_net_value"] = env.round(2)
scores["recommended_action"] = np.where(chosen == 1, "act", "no action")
save_table(scores.sort_values("expected_net_value", ascending=False), "prescriptive", "action_list")
n_act = int(chosen.sum())
print(f"Base case: act on {n_act:,} records, cost {n_act * A['action_cost']['base']:,.0f} "
      f"of budget {C.BUDGET:,.0f}, expected net benefit {total:,.0f}")

# 2. compare with simple rules (is the model worth using?) ------------------------------
rules = []
k = n_act or 1
cost = A["action_cost"]["base"]
for name, mask in {
    "model + optimisation (recommended)": chosen == 1,
    f"top {k} by risk only": scores["risk_probability"].rank(ascending=False) <= k,
    f"top {k} by value only": value.rank(ascending=False, method="first") <= k,
    f"random {k}": scores.index.isin(scores.sample(k, random_state=C.RANDOM_STATE).index),
}.items():
    rules.append({"strategy": name, "records_targeted": int(mask.sum()),
                  "expected_net_benefit": float(env[mask].sum()), "cost": float(mask.sum() * cost)})
rules = pd.DataFrame(rules)
save_table(rules, "prescriptive", "strategy_comparison")
print("\nStrategy comparison (base assumptions):")
print(rules.round(0).to_string(index=False))

# 3. scenarios and one-at-a-time sensitivity -----------------------------------------
scen = []
for case in ("low", "base", "high"):
    e, ch, t = plan(case)
    scen.append({"scenario": case, "records_targeted": int(ch.sum()), "expected_net_benefit": t})
save_table(pd.DataFrame(scen), "prescriptive", "scenarios")
sens = []
for key in A:
    for case in ("low", "high"):
        A_backup = A[key]["base"]
        A[key]["base"] = A[key][case]
        e, ch, t = plan("base")
        A[key]["base"] = A_backup
        sens.append({"assumption": key, "set_to": case, "value": A[key][case], "records_targeted": int(ch.sum()),
                     "expected_net_benefit": t, "change_vs_base": t - total})
sens = pd.DataFrame(sens)
save_table(sens, "prescriptive", "sensitivity")
print("\nSensitivity (one assumption at a time):")
print(sens.round(1).to_string(index=False))

# 4. how to prove it works: size of a randomised test ------------------------------------
base_rate = float(scores["actual_outcome"].mean())
expected_rate = base_rate * (1 - A["success_rate"]["base"])
effect = proportion_effectsize(base_rate, expected_rate)
n_per_group = int(np.ceil(NormalIndPower().solve_power(effect_size=effect, alpha=0.05, power=0.8, ratio=1.0)))
test_plan = {"metric": "outcome rate after the action cycle", "control_outcome_rate": base_rate,
             "expected_rate_with_action": expected_rate, "records_needed_per_group": n_per_group,
             "design": "randomly hold back a control group from the 'act' list; compare outcome rates after one cycle",
             "assumptions_used": {k: v["base"] for k, v in A.items()}, "budget": C.BUDGET, "capacity": C.CAPACITY}
save_json(test_plan, "prescriptive", "test_plan")
print(f"\nTo detect a drop from {base_rate:.1%} to {expected_rate:.1%} you need about {n_per_group:,} records per group.")
print("Done. Every number above rests on ASSUMPTIONS in config.py: state their sources in the report.")
