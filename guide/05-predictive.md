# 5. Predictive analytics - what will happen?

Goal: a model or forecast that is honestly evaluated against a baseline, whose
drivers you can explain, and that produces a score per record (or a forecast
per period) for the prescriptive stage and the dashboard.

## 5.1 Define the prediction before touching a model

Write these three lines in your plan:

- **Target** - the column and what 1 means ("churn = Yes: the customer left
  within the last month").
- **Prediction moment** - when the business would use the prediction, and what
  it would know then ("at the start of each month, using everything known about
  the customer up to then").
- **Unit** - one prediction per what (customer, order, store-week).

The prediction moment decides which columns are allowed.

## 5.2 Leakage: the check that matters most

A model that sees the answer looks brilliant and is useless. Go through every
column and ask: *would I know this value at the prediction moment?*

| Leaks | Why |
|---|---|
| Columns recorded after the outcome | exit reason, final bill, closure date |
| The outcome in another form | account status, "days until churn" |
| Totals that keep growing until the outcome | lifetime revenue, total charges |
| Call or event outcomes known only afterwards | call duration in a call-outcome dataset |
| Identifiers and row numbers | they can encode time or order |

Put them in `LEAKAGE_COLS` in `config.py`. Warning sign after training: one
feature far more important than the rest, or ROC-AUC above about 0.95 on a
messy business problem.

## 5.3 Python: run `04_predictive.py`

```bash
python 04_predictive.py
```

What it does, in order:

1. **Split.** With a date column: train on the earliest 80%, test on the latest
   20% (shuffling time lets the model see the future). Without dates: a
   stratified random 80/20 split.
2. **Pipeline.** Imputing, scaling and one-hot encoding are inside the model
   pipeline, so they are learned from training data only.
3. **Compare four models with 5-fold cross-validation** on the training data:
   a baseline that always predicts the average, logistic regression, random
   forest, gradient boosting.
4. **Choose.** The best cross-validated ROC-AUC, but logistic regression if it
   is within 0.01 - an explainable model that is almost as good is the better
   business choice.
5. **Test once** on the held-back 20%.
6. **Explain** with permutation importance: how much ROC-AUC drops when each
   feature is shuffled.
7. **Score every record** → `outputs/predictive/scores.csv` with
   `risk_probability` and `risk_band` (five equal-sized bands).

## 5.4 Reading the metrics

| Metric | Meaning | Good to know |
|---|---|---|
| ROC-AUC | chance the model ranks a random positive above a random negative | 0.5 = guessing; 0.7-0.8 useful; 0.8-0.9 strong; >0.95 suspect leakage |
| PR-AUC | precision-recall balance across thresholds | compare with the outcome rate: a rate of 0.27 means 0.27 is "no skill" |
| Precision | of those flagged, how many really had the outcome | matters when acting is expensive |
| Recall | of all real outcomes, how many were flagged | matters when missing one is expensive |
| Lift (top 10%) | how many times more outcomes in the riskiest 10% than on average | the easiest number for managers |
| Brier score | average squared error of the probabilities | lower is better; use with the calibration chart |
| Calibration chart | do predicted 30% risks really happen 30% of the time? | needed before using probabilities in money calculations |

**Do not use accuracy** for a rare outcome: predicting "nobody churns" is 73%
accurate on a 27% churn rate.

**The threshold** turns probabilities into "act / do not act". The script flags
the riskiest 20% as a starting point; the prescriptive stage chooses the
threshold from costs and benefits instead.

Worked example: all three models scored about 0.85 cross-validated ROC-AUC
against 0.50 for the baseline; logistic regression was chosen (within 0.01 of
the best). On the test set: ROC-AUC 0.84, PR-AUC 0.63 (against a 0.27 base
rate), and the riskiest 10% of customers churned at 2.8 times the average rate.
Flagging the top 20% caught half of all churners with 66% precision. Tenure,
internet service, contract and monthly charges drove the predictions.

## 5.5 Other kinds of prediction

**Numeric outcome** (sales amount, claim cost, days late): swap the classifiers
for regressors and the metrics for MAE and RMSE.

```python
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
# baseline: predict the training mean; report MAE and RMSE for baseline and models
```

**Time series** (monthly sales, complaints per month, a company KPI per quarter):

```python
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

s = monthly.set_index("month")["complaints"].asfreq("MS")
train, test = s[:-6], s[-6:]
naive = [train.iloc[-1]] * len(test)                       # baseline: same as last month
seasonal_naive = s.shift(12)[-6:]                           # baseline: same month last year
model = ExponentialSmoothing(train, trend="add", seasonal="add", seasonal_periods=12).fit()
forecast = model.forecast(len(test))
mae = lambda a, f: (abs(pd.Series(a).values - pd.Series(f).values)).mean()
print("naive", mae(test, naive), "seasonal naive", mae(test, seasonal_naive), "model", mae(test, forecast))
```

Rules: test on the most recent periods (a backtest), always against the naive
and seasonal-naive baselines, and present forecasts as ranges. Seasonal models
need at least two full seasons (24 months). For company × year data see guide 8.

**Segmentation without a target** (customer groups): k-means on scaled
features, choose k with the silhouette score and, above all, whether each group
can be described and acted on.

## 5.6 Power BI: the predictive page

1. **Load the scores.** Get data → Text/CSV → `outputs/predictive/scores.csv`.
   Relate `Scores[customer_id]` to `Customers[customer_id]` (one-to-one).
2. **Measures:**
   ```DAX
   Expected Churners = SUM ( Scores[risk_probability] )

   High Risk Customers =
   CALCULATE ( COUNTROWS ( Scores ), Scores[risk_band] IN { "high", "very high" } )

   Revenue at Risk (Predicted) =
   SUMX ( Scores, Scores[risk_probability] * RELATED ( Customers[monthly_charges] ) )
   ```
3. **Visuals:**
   - column chart: Customers and actual churn rate by `risk_band` - shows the
     model separates risk (rates should climb steadily across bands);
   - table of the highest-risk customers with their key attributes;
   - bar chart of `feature_importance.csv`;
   - cards with ROC-AUC, lift and recall from `test_metrics.json` (enter them in
     a small table, or load the JSON);
   - for time series: a **line chart** with **Analytics pane → Forecast**
     (choose forecast length and confidence interval; needs a continuous date
     axis). Compare it with your Python backtest; report the Python one.
4. Add a slicer on `in_test_set` so you can show performance on unseen data only.

Power BI can run Python inside Power Query (**Transform → Run Python script**)
or as a Python visual, but loading the scores CSV is simpler and refreshes
reliably.

## 5.7 Done when

- [ ] Target, prediction moment and unit written down
- [ ] Leakage list justified column by column
- [ ] Model compared with a baseline using cross-validation; tested once
- [ ] Metrics chosen for the business question, threshold explained
- [ ] Drivers explained; calibration checked
- [ ] Scores loaded into Power BI; predictive page built
