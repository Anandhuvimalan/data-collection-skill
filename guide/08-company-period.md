# 8. Company × period data - analysing one company (and its peers)

Single-company projects often have tables like this: one row per company per
year (or quarter, or month), with the topic's KPI and possible drivers.

| company_id | fiscal_year_end | attrition_rate | headcount | revenue | employee_cost |
|---|---|---|---|---|---|
| infosys | 2023-03-31 | ... | ... | ... | ... |
| tcs | 2023-03-31 | ... | ... | ... | ... |

The four stages still apply, with methods suited to few rows. Use this guide
alongside guides 3-6.

## 8.1 Build the panel table

1. Start from `data/processed/financials_annual.csv` (built from SEC filings)
   and the KPI tables extracted from annual or quarterly reports
   (`data/raw/<id>/extracted/*.csv`).
2. Put every source into the same long shape: `company_id, period, measure, value`.
3. Pivot to one row per company per period, one column per measure:

```python
import pandas as pd

kpis = pd.concat([pd.read_csv(f) for f in [
    "data/raw/infosys-reports/extracted/attrition.csv",
    "data/raw/peer-reports/extracted/attrition.csv"]])
panel = kpis.pivot_table(index=["company_id", "period"], columns="measure", values="value").reset_index()
fin = pd.read_csv("data/processed/financials_annual.csv")      # one company per run of structure_data.py
panel = panel.merge(fin, left_on=["company_id", "period"], right_on=["company_id", "fiscal_year_end"], how="left")

# derived drivers
panel = panel.sort_values(["company_id", "period"])
panel["revenue_growth"] = panel.groupby("company_id")["revenue"].pct_change() * 100
panel["employee_cost_per_head"] = panel["employee_benefits_expense"] / panel["headcount"]
panel["headcount_growth"] = panel.groupby("company_id")["headcount"].pct_change() * 100
panel.to_csv("data/processed/kpi_by_company_year.csv", index=False)
```

Check before analysing:

- **Same definition?** Companies define the KPI differently (voluntary vs total
  attrition, trailing twelve months vs annualised quarter). Note differences;
  compare only like with like.
- **Same fiscal year?** Indian companies usually end in March, US companies in
  December. Label periods by fiscal year end and say so.
- **Same currency and units?** Convert, or compare ratios instead of amounts.
- **Restatements?** If a later report changes an earlier figure, use the latest
  and note it.

## 8.2 Python: run `kpi_panel.py`

Set the `PANEL_*` settings and `FOCAL_COMPANY` in `config.py`, then:

```bash
python kpi_panel.py
```

| Output | Stage | What it shows |
|---|---|---|
| `kpi_panel_enriched.csv` | Descriptive | change, % change, index (first period = 100), peer median, gap to peers |
| `kpi_trend_and_gap.png` | Descriptive | KPI by company (focal company bold) and the focal company's gap to the peer median |
| `driver_correlations.csv` | Diagnostic | correlation of **changes** between the KPI and each driver |
| `forecast.json` | Predictive | backtest of a damped trend model vs "same as last period", and a 3-period forecast with an 80% range |

## 8.3 Stage by stage

**Descriptive.** Trend of the KPI, growth rates, the company indexed against
peers, the gap to the peer median, the best and worst periods. Phrase findings
relative to peers: "Attrition rose from A% to B%, while the peer median rose
from C% to D%: most of the rise was industry-wide."

**Diagnostic.** With few rows, keep it simple and modest:

- compare **changes**, not levels - two series that both grow over time always
  correlate (the script does this);
- separate industry-wide from company-specific movement: the gap to peers is
  the company-specific part;
- line up events (reorganisations, pay revisions, price changes, regulation)
  with turning points, and look for the same change at peers;
- with enough company-years (say 30+), a panel regression with company and
  year effects: `statsmodels.formula.api.ols("kpi ~ driver + C(company_id) + C(year)", data=panel)`.

Say "indicative" whenever you have fewer than about 15 observations.

**Predictive.** Forecast the KPI with a naive baseline, a damped trend model,
or a regression on drivers across the panel. Backtest on the last periods. If
the model does not beat "same as last period", report the naive forecast and
say why. Quarterly data gives four times the points - collect it if the company
publishes it.

**Prescriptive.** Set a target from the peer benchmark (e.g. "reach the peer
median within two years"), then link the lever to the KPI to money in a scenario
model, with sourced assumptions:

```
cost of attrition = leavers × replacement cost per leaver
leavers           = headcount × attrition rate
saving            = (current rate − target rate) × headcount × replacement cost
```

Show low / base / high, and what the target would require (for example the
spend on retention programmes it would justify).

## 8.4 Power BI for company × period data

- Model: a `Company` table (one row per company, with a "Focal" flag) and the
  `Date` table, both related to the KPI table. If you only have years, create a
  `Year` table with one row per fiscal year instead.
- Measures:
  ```DAX
  KPI = AVERAGE ( Panel[attrition_rate] )

  Peer Median =
  CALCULATE (
      MEDIANX ( VALUES ( Company[company_id] ), [KPI] ),
      REMOVEFILTERS ( Company ),          -- ignore the company on the current row...
      Company[is_focal] = FALSE ()        -- ...and take the median of the peers only
  )

  Gap to Peers (pts) = [KPI] - [Peer Median]

  KPI Change (pts) =
  VAR Prev = CALCULATE ( [KPI], DATEADD ( 'Date'[Date], -1, YEAR ) )
  RETURN IF ( NOT ISBLANK ( Prev ), [KPI] - Prev )
  ```
- Visuals: line chart of the KPI by company (highlight the focal company with a
  strong colour, peers in grey); column chart of the gap to peers; scatter of
  the KPI against a driver with company as the legend and a trend line; small
  multiples (Format → Small multiples) for several measures; a what-if parameter
  for the target rate driving the savings measure.

## 8.5 Combining with record-level data

If the project also has record-level data about the company (complaints,
reviews, recalls), aggregate it to the same period and join on company and
period: complaints per million customers per year is often the driver the
company-level diagnostic needs. The record-level data can also be analysed on
its own with guides 3-6.
