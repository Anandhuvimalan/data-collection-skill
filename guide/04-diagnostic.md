# 4. Diagnostic analytics - why is it happening?

Goal: test your hypotheses about causes, rank the factors that hold up, and be
honest about what the data can and cannot prove. The output is a hypothesis
table (supported / not supported / inconclusive) and a ranked list of
contributing factors that feed the model and the recommendations.

## 4.1 Start from hypotheses, not from charts

Copy the hypotheses from `01_business_problem.md` into a table and add the test
for each before running anything:

| # | Hypothesis | Variables | Test | Supported if... |
|---|---|---|---|---|
| H1 | Customers without long contracts leave more | contract, target | chi-square + rates | month-to-month rate clearly higher, effect size ≥ small |
| H2 | Newer customers leave more | tenure, target | Mann-Whitney + bands | leavers' median tenure clearly lower |
| H3 | Contract matters even for customers of the same tenure | contract, tenure, target | stratified rates | the gap survives inside every tenure band |

Deciding the test in advance stops you from fishing through every column until
something looks significant.

## 4.2 Which test for which question

| Question shape | Test | Effect size to report | Python |
|---|---|---|---|
| Does a rate differ across categories? | Chi-square test of independence | Cramér's V (0.1 small, 0.3 medium, 0.5 large) | `scipy.stats.chi2_contingency` |
| Does a number differ between two groups? | Mann-Whitney U (or t-test if roughly normal) | rank-biserial r, or difference in medians | `scipy.stats.mannwhitneyu` |
| ...across several groups? | Kruskal-Wallis (or ANOVA) | eta squared | `scipy.stats.kruskal` |
| Do two numbers move together? | Spearman (or Pearson) correlation | the coefficient itself | `df[[a, b]].corr("spearman")` |
| Which factors matter together? | Logistic regression (yes/no outcome) or linear regression (numeric) | odds ratios / coefficients with 95% CI | `statsmodels` |
| Did something change after an event? | Before/after with a comparison group | difference in differences | group means by period |

**p-value vs effect size.** With thousands of rows almost everything is
"significant" (tiny p-value). The effect size tells you whether it matters.
Report both, and lead with the effect size.

## 4.3 Python: run `03_diagnostic.py`

Set `CONTROL_COL` in `config.py` to the factor you most suspect is behind
others (often tenure, age, size or region). Then:

```bash
python 03_diagnostic.py
```

Outputs in `outputs/diagnostic/`:

| File | What it is | How to use it |
|---|---|---|
| `factor_tests.csv` | every factor tested on its own: test, p-value, **p_adjusted** (corrected for testing many factors), effect size and strength, a one-line detail | Your evidence table. Use `p_adjusted`, not `p_value` |
| `odds_ratios.csv` | the leading factors in one logistic regression: odds ratio, 95% CI | Which factors still matter **when the others are held constant** |
| `stratified_<factor>_by_<control>.csv` | the top factor's rates inside each band of the control | The confounding check |

**Reading odds ratios.** An odds ratio of 2.7 for `internet_service_fiber optic`
means fibre customers have 2.7 times the odds of churning compared with the
reference category, with the other factors in the model held fixed. If the 95%
interval includes 1, the factor is not distinguishable from no effect. Numeric
factors are scaled, so their odds ratio is "per one standard deviation".

Worked example: tenure (r = 0.48) and contract (V = 0.41) were the strongest
single factors. In the joint model, fibre optic (OR 2.7) and electronic-check
payment (OR 1.5) raised the odds, while longer tenure (OR 0.51 per SD) and a
one-year contract (OR 0.49) lowered them. The confounding check showed
month-to-month customers churn far more than two-year customers **within every
tenure band** (52.9% vs 0.0% for the newest, 22.1% vs 3.2% for the longest) -
so contract is not just tenure in disguise.

## 4.4 Correlation is not cause: the five checks

Write these into the diagnostic report for your top factors.

1. **Confounding** - does the relationship survive when a third factor is held
   constant? (The stratified table and the regression.)
2. **Reversal on aggregation** - does the pattern hold inside each major
   segment, not just overall? (Simpson's paradox.)
3. **Direction** - did the supposed cause come first? Without dates you usually
   cannot show this; say so.
4. **Size** - is the effect big enough to matter for the business?
5. **Mechanism** - is there a believable business reason? A factor with no
   plausible mechanism is a lead, not a finding.

Use careful wording: "is associated with", "is consistent with", "remains
associated after controlling for tenure". Say what evidence would establish
cause (an experiment, a policy change with a comparison group).

## 4.5 Power BI: the diagnostic page

1. **Key influencers visual** (Visualizations → Key influencers). *Analyze* =
   the outcome column (e.g. churn), *Explain by* = candidate factors. Set the
   value to analyse to "Yes". It ranks factors and shows segments. Treat it as
   exploration - it is a quick model, not a statistical test - and confirm its
   top factors with your Python results.
2. **Decomposition tree** (Visualizations → Decomposition tree). *Analyze* =
   Churn Rate, *Explain by* = the dimensions. Click **+** to split by the next
   dimension, or choose **High value** to let Power BI pick the split with the
   highest rate. Great for showing the path to the worst segment in a meeting.
3. **Confounder matrix** - a matrix with Rows = tenure band, Columns = contract,
   Values = Churn Rate and Customers, heat-map formatting. This is the Power BI
   version of the stratified check.
4. **Scatter chart** for two numeric factors per segment (e.g. per region or
   per product: average price vs churn rate), with **Analytics → Trend line**.
5. **Import the evidence** - load `factor_tests.csv` and `odds_ratios.csv` and
   show them as a table or a bar chart of effect sizes, so the statistics are on
   the dashboard, not only in the report.

A useful measure for comparing a segment with everyone else:

```DAX
Churn Rate Rest =
VAR SelectedContracts = VALUES ( Customers[contract] )
RETURN
    CALCULATE ( [Churn Rate], REMOVEFILTERS ( Customers[contract] ),
                NOT Customers[contract] IN SelectedContracts )

Gap vs Rest (pts) = ( [Churn Rate] - [Churn Rate Rest] ) * 100
```

## 4.6 Common mistakes

- Treating the largest bar in a chart as the root cause.
- Testing twenty factors and reporting the one with p < 0.05 (use the adjusted
  p-values and your pre-written hypotheses).
- Ignoring effect size.
- Putting two versions of the same information in one model (e.g. three
  "no internet service" dummies) - the script removes exact duplicates and tells
  you which.
- Writing "X causes Y" from observational data.

## 4.7 Done when

- [ ] Every hypothesis has a verdict, the test, the effect size and the adjusted p-value
- [ ] Top factors checked for confounding and reversal
- [ ] Ranked list of contributing factors handed to the predictive stage
- [ ] Diagnostic dashboard page built
