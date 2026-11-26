# 3. Descriptive analytics - what is happening?

Goal: measure the problem precisely, find **where** it is concentrated, and put
a value on it. The output is a set of KPIs, segment views, trends (if you have
dates), and three to five "where is the problem" statements that the diagnostic
stage will try to explain.

## 3.1 Decide your KPIs first

Write five to eight KPIs before making any chart. For each: name, meaning,
formula, columns used, and the grain (per customer, per month, per company-year).

| KPI | Formula | Example (churn) |
|---|---|---|
| Headline rate | outcomes ÷ records | churn rate = churned customers ÷ all customers |
| Volume | count of outcomes | churned customers |
| Value at risk | sum of value for records with the outcome | monthly revenue of churned customers |
| Share of value at risk | value at risk ÷ total value | 30.5% of monthly revenue |
| Segment rate | the headline rate inside each segment | churn rate by contract type |
| Trend | the rate per period, change vs last period / last year | monthly churn rate, YoY change |

## 3.2 Python: run `02_descriptive.py`

```bash
python 02_descriptive.py
```

It writes to `outputs/descriptive/`:

| File | What it shows | How to read it |
|---|---|---|
| `kpis.json` | records, outcome count, rate, value at risk | Your headline numbers |
| `segments.csv` | rate, size and share of outcomes for every category of every column | Sort by `gap_vs_overall_pts`; ignore rows flagged `small_segment` (<30 records) |
| `segments.png` | the six dimensions with the widest spread | The dashed line is the overall rate |
| `numeric_summary.csv`, `distributions.png` | medians by outcome, skew | Big gaps between the two medians are leads for diagnostics |
| `<measure>_bands.csv` | rate across five bands of a numeric measure | Shows shape: steady rise, cliff, or U-shape |
| `monthly_trend.csv/.png` | rate per month, 3-month average, YoY | Only if `DATE_COL` is set |

Worked example output: churn rate 26.5% (1,869 of 7,043); churned customers
carry 30.5% of monthly revenue; highest-rate segments are electronic-check
payers (45.3%), month-to-month contracts (42.7%) and fibre-optic customers
(41.9%); no date column, so no trend analysis was possible.

**Write the "where" statements** - specific, sized, and with the comparison:

> Month-to-month customers are 55% of the base but churn at 42.7%, against
> 11.3% on one-year and 2.8% on two-year contracts.

Not: "Contract type affects churn" - that is a diagnostic claim, and it is not
tested yet.

Extra views worth adding by hand when relevant:

```python
# Pareto: which few segments hold most of the outcomes?
seg = df.groupby("payment_method")["target"].sum().sort_values(ascending=False)
print((seg.cumsum() / seg.sum()).round(2))

# two dimensions at once
print(pd.crosstab(df["contract"], df["internet_service"], values=df["target"], aggfunc="mean").round(3))
```

## 3.3 Power BI: the descriptive page

**Measures** (select `_Measures` → **New measure**; replace table and column
names with yours):

```DAX
Customers = COUNTROWS ( Customers )

Churned = CALCULATE ( [Customers], Customers[churn] = "Yes" )

Churn Rate = DIVIDE ( [Churned], [Customers] )

Monthly Revenue = SUM ( Customers[monthly_charges] )

Revenue at Risk = CALCULATE ( [Monthly Revenue], Customers[churn] = "Yes" )

Revenue at Risk % = DIVIDE ( [Revenue at Risk], [Monthly Revenue] )

Overall Churn Rate = CALCULATE ( [Churn Rate], ALLSELECTED ( Customers ) )

Gap vs Overall (pts) = ( [Churn Rate] - [Overall Churn Rate] ) * 100
```

With a date table, add time intelligence:

```DAX
Churn Rate LY = CALCULATE ( [Churn Rate], SAMEPERIODLASTYEAR ( 'Date'[Date] ) )

Churn Rate YoY (pts) = ( [Churn Rate] - [Churn Rate LY] ) * 100

Churn Rate 3M Avg =
AVERAGEX ( DATESINPERIOD ( 'Date'[Date], MAX ( 'Date'[Date] ), -3, MONTH ), [Churn Rate] )
```

Format rates as percentages: select the measure → **Measure tools → Format →
Percentage**.

**Build the page**, top to bottom:

1. **KPI cards** across the top: Customers, Churned, Churn Rate, Revenue at
   Risk %. (Visualizations → **Card**; one measure each.)
2. **Clustered bar chart**: Y-axis = a segment column (contract), X-axis =
   Churn Rate. Sort by Churn Rate. Add **Gap vs Overall** to the tooltip.
   Add a constant line at the overall rate: **Analytics pane → Constant line**,
   value = the overall rate (or use an X-axis constant line with the
   `Overall Churn Rate` measure via **fx**).
3. **Matrix** for two dimensions: Rows = contract, Columns = internet service,
   Values = Churn Rate. **Format → Cell elements → Background color** (on) for
   a heat map.
4. **Line chart** for trends (only with dates): X-axis = `Date[Year-Month]` or
   the date hierarchy, Y-axis = Churn Rate and Churn Rate 3M Avg.
5. **Slicers** for the main dimensions (contract, region, period) on the left
   or top edge.
6. **Histogram-like view** for a numeric measure: create bands in Power Query
   (conditional column) or **right-click the column → New group → Bin**, then a
   column chart of Customers and Churn Rate by band.

Check the dashboard against `kpis.json`: the same filters must give the same
numbers in Python and Power BI. If they differ, one of them has a cleaning or
relationship difference - find it before moving on.

## 3.4 Common mistakes

- Rates on tiny segments ("100% churn" from 3 customers). Show the count next
  to every rate.
- Averages of averages. Compute rates from counts (`DIVIDE` of sums), never by
  averaging percentages across groups.
- Trend charts without dates, or on a tenure column. Tenure is age, not time.
- Pie charts with many slices. Use sorted bars.
- Calling a segment difference a cause. That is the next stage's job.

## 3.5 Done when

- [ ] KPI table with formulas and values, matching between Python and Power BI
- [ ] Three to five "where" statements, each with sizes and comparisons
- [ ] Value at stake estimated
- [ ] Descriptive dashboard page built
