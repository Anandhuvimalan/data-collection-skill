# How to analyse your project: a step-by-step guide

This guide takes you from the collected data to a finished project: cleaned
data, four kinds of analysis, a Power BI dashboard, and a report that leads to a
decision. Every stage has two tracks you can follow side by side:

- **Python** - ready-made scripts in `guide/python/` that you configure once and run.
- **Power BI** - click-by-click steps and DAX measures you type in.

Use both. Python is better for statistics and models; Power BI is better for
exploring and presenting. The usual flow is: Python computes, Power BI shows.

## The four questions every project answers

| Stage | Question | What you produce | Guide |
|---|---|---|---|
| Descriptive | What is happening? | KPIs, segment and trend views, size of the problem | [03-descriptive.md](03-descriptive.md) |
| Diagnostic | Why is it happening? | Tested causes, ranked by strength, with confounders checked | [04-diagnostic.md](04-diagnostic.md) |
| Predictive | What will happen? | A model or forecast, honestly evaluated, scores per record | [05-predictive.md](05-predictive.md) |
| Prescriptive | What should be done? | A decision rule, expected benefit, scenarios, test plan | [06-prescriptive.md](06-prescriptive.md) |

They are one argument, not four chapters. Descriptive finds **where** the
problem is; diagnostic explains **why** there; predictive says **who or what
next**; prescriptive says **what to do about it and what it is worth**.

## All the guides, in order

| # | Guide | Time (8-week project) |
|---|---|---|
| 1 | [Setup and loading](01-setup-and-loading.md) - tools, SQL database, Power BI model | Week 1 |
| 2 | [Data preparation](02-data-preparation.md) - cleaning in Python and Power Query | Week 2 |
| 3 | [Descriptive analytics](03-descriptive.md) | Week 3 |
| 4 | [Diagnostic analytics](04-diagnostic.md) | Week 4 |
| 5 | [Predictive analytics](05-predictive.md) | Week 5 |
| 6 | [Prescriptive analytics](06-prescriptive.md) | Week 6 |
| 7 | [Reporting and presenting](07-reporting.md) - dashboard, report, presentation, checklist | Weeks 7-8 |
| 8 | [Company × period data](08-company-period.md) - when your data is one row per company per year or quarter | Use alongside 3-6 |

**Which data shape do you have?** Open your main table and look at one row.

- One row = one customer, employee, order, complaint, loan... → **record-level**.
  Follow guides 3-6 directly.
- One row = one company in one year/quarter/month → **company × period**. Read
  guide 8 first, then use guides 3-6 for the parts that apply.
- Both (common in single-company projects) → do both, and join them on company
  and period.

## The Python scripts

| Script | Stage | Reads | Writes to `outputs/` |
|---|---|---|---|
| `config.py` | - | - | Your settings: file, columns, assumptions. **Edit this first.** |
| `01_prepare.py` | Preparation | your main table | `analysis_table.csv`, `preparation/quality_log.json` |
| `02_descriptive.py` | Descriptive | analysis table | `descriptive/` KPIs, segments, distributions, trend |
| `03_diagnostic.py` | Diagnostic | analysis table | `diagnostic/` factor tests, odds ratios, confounder check |
| `04_predictive.py` | Predictive | analysis table | `predictive/` model comparison, test metrics, scores |
| `05_prescriptive.py` | Prescriptive | scores | `prescriptive/` action list, scenarios, sensitivity, test plan |
| `kpi_panel.py` | All, for company × period | panel table | `company_period/` trend, peer gap, drivers, forecast |

Run them in order from the `guide/python` folder:

```bash
cd guide/python
pip install -r requirements.txt
python 01_prepare.py
python 02_descriptive.py
python 03_diagnostic.py
python 04_predictive.py
python 05_prescriptive.py
```

The scripts are written for a **yes/no outcome** (churned or not, left or not,
defaulted or not). For a numeric outcome or a time series, the guides explain
what to change.

**A worked example** runs through every guide: the IBM *Telco Customer Churn*
sample (7,043 customers). It is a fictional dataset, used here only because many
students know it; the numbers quoted are what the scripts produced on it. Your
numbers will differ, and your project should use the data collected for it.

## Rules that make a project credible

1. **Every number traces back to a file or a source.** Keep `outputs/` and cite
   it.
2. **Association is not cause.** Diagnostic findings say "is associated with"
   unless you have a test or experiment.
3. **A model is only as good as its baseline.** Always report what "no model"
   would achieve.
4. **Every recommendation names a lever, a cost, a benefit and how to measure
   it.** "Improve customer service" is not a recommendation.
5. **Say what you could not do and why.** Limitations stated plainly earn more
   trust than claims that overreach.
