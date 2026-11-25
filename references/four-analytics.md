# The four kinds of analytics, planned against real data

## Contents

1. How the four stages connect
2. Descriptive - what happened?
3. Diagnostic - why did it happen?
4. Predictive - what might happen?
5. Prescriptive - what should we do?
6. Status labels and honest gaps
7. Mistakes to design out

---

## 1. How the four stages connect

The stages are one argument, not four separate chapters. Each one hands
something specific to the next:

| Stage | Question | Hands to the next stage |
|---|---|---|
| Descriptive | What happened? | The size and location of the problem: which segments, which periods |
| Diagnostic | Why? | The factors that hold up under testing, which become model features and candidate levers |
| Predictive | What will happen? | A risk, demand or value estimate per customer, product, order or period |
| Prescriptive | What should we do? | A decision rule: who or what gets which action, under which limits, and how success is measured |

Plan them as a chain. A descriptive finding nobody diagnoses, or a model whose
scores feed no decision, is the mark of a tutorial rather than a project. For
each stage, write down what it receives from the stage before.

Every planned item names the table and columns it uses. Take them from
`data/profiles/data_profile.md`, spelled exactly as in the file.

---

## 2. Descriptive - what happened?

**Needs:** a measure to count, sum or average; categories to split it by;
ideally a date.

**Plan these:**

- **KPIs.** Five to eight, each with name, business meaning, formula, the
  columns in the formula, and the grain it is computed at. One of them is the
  headline measure of the problem itself.
- **Segment views.** The headline KPI split by each meaningful category, with
  the segment's size shown alongside its rate. A 60% rate in a segment of twelve
  records is noise.
- **Time views.** Only if the profile found a real date column. Trend, month on
  month, year on year, seasonality. Say which date column defines the period.
- **Distributions.** For the main numeric measures: spread, skew, outliers.
- **Value at stake.** Translate the problem into money or volume where the data
  allows: revenue from the affected segment, hours lost, orders delayed.

**When there is no date column** the table is a snapshot. Say so and drop the
trend items. Do not improvise a time axis from a tenure, age or sequence column;
tenure tells you how long each record has existed, not when anything happened.
Cohort-style views by tenure band are legitimate and should be called that.

**Output:** a KPI table, the descriptive dashboard page, and a short list of
"where the problem is concentrated" statements that the diagnostic stage will
try to explain.

---

## 3. Diagnostic - why did it happen?

**Needs:** candidate causes that vary across the records, and enough records in
each group to compare.

**Start from the hypotheses** in `01_business_problem.md`. Each one becomes a
test:

| Hypothesis shape | Suitable test | Report alongside it |
|---|---|---|
| A rate differs between categories | Chi-square test of independence | The rates, group sizes, and an effect size such as Cramér's V |
| A numeric measure differs between two groups | t-test, or Mann-Whitney when skewed | Means or medians, and the size of the difference |
| It differs across several groups | ANOVA or Kruskal-Wallis | Which groups differ, after a post-hoc comparison |
| Two numeric measures move together | Pearson or Spearman correlation | The coefficient and a scatter plot |
| Several factors act at once | Logistic or linear regression with controls | Coefficients or odds ratios with confidence intervals |
| Something changed at a point in time | Before and after comparison, ideally with an unaffected comparison group | The dates, and what else changed then |

**Correlation is not cause, and the plan must show how the student will tell
the difference.** Include these checks explicitly:

- **Confounding.** Does the relationship survive when a third factor is held
  constant? Compare within strata, or add the factor to a regression. Customers
  on monthly contracts may leave more simply because they are newer.
- **Reversal on aggregation.** Check whether a pattern in the total holds inside
  each segment. It sometimes reverses (Simpson's paradox).
- **Direction.** Was the supposed cause in place before the outcome? Without
  dates this usually cannot be shown, and the plan should say so.
- **Size, not only significance.** With thousands of rows, trivial differences
  are statistically significant. Report effect sizes and what they mean in
  business terms.
- **Many tests.** Testing twenty variables will turn up a "significant" one by
  chance. Tie tests to the stated hypotheses, and treat anything found by
  trawling as a new hypothesis, not a finding.

**Wording matters.** From observational data the honest conclusion is "is
associated with" or "is consistent with", plus what evidence would establish
cause: an experiment, a policy change with a comparison group, or data the
project does not have. Name that missing evidence.

**Output:** a table of hypotheses with test, result and verdict (supported, not
supported, inconclusive), and a ranked list of contributing factors.

---

## 4. Predictive - what might happen?

**Needs:** an outcome to predict, features that would be known before the
outcome happens, and enough rows and enough cases of the outcome.

**Define the prediction precisely before choosing a model:**

- **Target.** The column, what its values mean, and the business event it
  stands for. If it has to be derived (for example "churned = no purchase in 90
  days"), give the rule and why that threshold.
- **Prediction moment.** When would the business make this prediction, and what
  would it know then? This decides which columns are allowed.
- **Unit.** One row per customer, per order, per store-week?

**Leakage** is the commonest way a student model looks excellent and is useless.
List every column that must be excluded and why:

- anything recorded after the outcome (a cancellation reason, a closing balance),
- anything that is the outcome in another form (a status code, a satisfaction
  score collected at exit),
- totals that accumulate over the period being predicted,
- identifiers,
- for call-outcome data, things like call duration that are only known once the
  call - and therefore the outcome - is over.

Also keep preprocessing inside the training fold: fit scalers, encoders and
imputers on training data only.

**Choose the method by the task:**

| Task | Start with | Then consider | Judge by |
|---|---|---|---|
| Yes/no outcome | Logistic regression | Decision tree, random forest, gradient boosting | ROC-AUC, PR-AUC when the outcome is rare, precision and recall at the operating threshold, lift in the top decile, calibration |
| Numeric outcome | Linear regression | Regularised regression, tree ensembles | MAE, RMSE, R², residual plots |
| Time series | Seasonal naive forecast | ETS, ARIMA/SARIMA, Prophet, boosted trees on lag features | MAE, sMAPE or MASE on a rolling-origin backtest |
| Groups with no label | k-means on scaled features | Hierarchical clustering, RFM scoring | Silhouette, and above all whether the groups make business sense |

**Always include a baseline** - predict the majority class, last period's value,
or the overall mean. A model is only worth anything by how far it beats that.

**Splitting.** With dates, train on earlier periods and test on later ones;
shuffling lets the model see the future. Without dates, use a stratified split
and cross-validation. Hold the test set back until the end.

**Rare outcomes.** Do not use accuracy. Use class weights or resampling inside
the training fold only, and pick the threshold from costs, not from 0.5.

**Selection criteria.** Not only the score: can the business understand it, is
it stable across folds, and does it use information that will really be
available when it has to run? State which model is expected to be chosen and
why a simpler one may be preferable.

**If the data is thin** - a few hundred rows, a handful of positive cases, no
legitimate features - say the predictive stage is limited and plan what is
defensible: a simple interpretable model with cross-validation, presented as
indicative.

**Output:** a model evaluation table against the baseline, the main drivers
(coefficients or importances), and a score per unit that the prescriptive stage
will use.

---

## 5. Prescriptive - what should we do?

**Needs:** a lever the business controls, and figures for value and cost.

Public data almost never contains the costs, so this stage is where projects
collapse into generic advice ("improve customer service", "offer discounts").
Replace advice with a **decision framework**:

1. **Decision.** What exactly is being chosen, for which unit, how often?
   ("Which customers receive a retention offer each month.")
2. **Decision variables.** What can be set: who is targeted, which action,
   which threshold, how much stock, which price.
3. **Objective.** What is being maximised or minimised, written as a formula.
4. **Constraints.** Budget, capacity, contact limits, service levels, policy.
5. **Inputs.** Which come from the data and the model (risk score, order
   value), and which are **assumptions**.
6. **Rule or optimisation.** The simplest method that fits.
7. **Sensitivity.** How the recommendation changes across the plausible range
   of each assumption.
8. **Measurement.** How the business would find out whether it worked.

**Assumptions get a table of their own:** the value, its source (a company
report, a regulator figure, an industry study, or "placeholder to be replaced by
the business"), and the low and high values used for sensitivity. An assumption
with a source and a range is analysis. An unstated one is a guess.

**Methods, simplest first:**

| Situation | Method |
|---|---|
| Act or not, per unit | Expected value: act when probability × value saved × success rate exceeds the cost of acting |
| Limited budget or capacity | Rank by expected net value and take the top until the limit is reached |
| Several actions, several limits | Linear or integer programming (`scipy.optimize`, PuLP, Excel Solver) |
| Stock and reorder decisions | Newsvendor or reorder-point model driven by the forecast and its error |
| Price or discount level | Estimated demand response, then maximise margin under the constraint |
| Setting a threshold | Cost matrix: weigh a missed case against a false alarm |

**A caution worth stating in the plan:** a risk model tells you who is likely to
leave, default or fail, not who will respond to the intervention. The highest
risk units are not always the ones worth acting on. Targeting by response needs
experimental data; without it, say the response rate is an assumption.

**Measurement plan.** Recommend a controlled test: a randomly held-out control
group, the metric, the duration, and roughly how many units are needed to detect
the expected effect. Add the KPIs to monitor afterwards and what result would
mean the recommendation should be withdrawn.

**Output:** the decision rule, a scenario table (base, optimistic, pessimistic)
with expected impact, and the measurement plan.

---

## 6. Status labels and honest gaps

Every planned item gets a status so the student knows what is real:

| Status | Meaning |
|---|---|
| `READY` | The collected data supports it. Columns named. |
| `LIMITED` | Possible with a stated caveat or assumption. |
| `BLOCKED` | Not possible with the collected data. State what data would unblock it. |

A plan with a few `BLOCKED` items clearly explained is stronger than one that
pretends everything works. If a whole stage is blocked, raise it in the
feasibility review and propose a fix: another dataset, a derived measure, or a
narrower question.

---

## 7. Mistakes to design out

- Trend charts planned on a dataset with no dates.
- KPIs with no formula, or a formula whose columns do not exist.
- "Root causes" that are just the largest bars in a chart.
- A model trained with a column that is only known after the outcome.
- Accuracy reported on a rare outcome.
- A random split on time-ordered data.
- Fitting scalers or encoders before splitting.
- Recommendations with no lever, no cost and no way to measure them.
- Joining datasets that merely share a column name.
- Describing a fictional sample as a company's real records.
- Generalising from one organisation, country or year to an industry.
