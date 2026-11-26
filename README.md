# data-collection

A skill for Claude Code that turns a project topic into a real-data analytics
project built around one real company.

1. **It asks for your topic**, for example *employee attrition* or *customer churn*.
2. **It proposes real companies** for that topic, ranked by how much public data
   actually exists about each one (measured live, not guessed), and offers
   alternative approaches.
3. **You pick a company**, and it asks a few details: problem angle, period,
   scope, peers, tools.
4. **It collects that company's data thoroughly**: financial filings, the KPIs the
   company discloses, regulator records that name it, complaints and reviews,
   company-published datasets, peer and market data. Every file is logged with its
   source and classified as actual, anonymized, simulated or synthetic.
5. **It structures the data** into analysis-ready tables with a data dictionary,
   and plans the four kinds of analytics: descriptive (what is happening),
   diagnostic (why), predictive (what will happen) and prescriptive (what should
   be done), through to recommendations.

## Install

Clone this repository into your Claude Code skills folder, keeping the folder
name `data-collection`.

Windows (PowerShell):

```powershell
git clone https://github.com/Anandhuvimalan/data-collection-skill "$env:USERPROFILE\.claude\skills\data-collection"
```

macOS / Linux:

```bash
git clone https://github.com/Anandhuvimalan/data-collection-skill ~/.claude/skills/data-collection
```

Start a new Claude Code session afterwards so the skill is picked up.

### Requirements

- Python 3.8 or later
- `pip install pandas openpyxl pyarrow`
- Internet access for searching and downloading

## Use

Open Claude Code in the folder where you want the project created and say what
you need, for example:

```
I need a data analytics project for my internship. Help me collect real data.
```

It will ask for the topic, then show you the companies to choose from. You can
also give everything at once:

```
Topic: employee attrition analysis. Company: Infosys.
Tools: Python, SQL Server, Power BI. 8-week internship.
```

### Alternative approaches it can offer

| Approach | When it fits |
|---|---|
| Single-company deep dive (default) | The company discloses the topic's KPI over several years |
| Focal company plus peers | A regulator or a report format covers several companies the same way |
| Company-published dataset first | A company has released row-level data for the topic |
| Company plus proxy dataset | Per-customer or per-employee modelling is needed but the company's records are not public |
| Best public dataset for the topic | Method matters more than a named company |
| Primary data collection | Surveys or interviews for perception questions |
| Internship host's own data | The host company agrees to share anonymized data |
| Synthetic data calibrated on public figures | Only on request, for practice |

## What you get

```
<company>-<topic>/
├── README.md                       summary, verdict, data disclosure, next steps
├── 00_company_selection.md         candidates, measured data footprint, choice
├── 01_business_problem.md          industry, process, problem, hypotheses, research questions
├── 02_data_collection_report.md    what was searched, considered, chosen and collected
├── 03_data_model.md                tables, keys, measured relationships
├── 04_data_preparation_plan.md     quality issues found and how to treat each
├── 05_analytics_plan.md            descriptive, diagnostic, predictive, prescriptive
├── 06_roadmap_and_deliverables.md  step-by-step plan and deliverables checklist
├── 07_feasibility_review.md        scorecard, limitations, verdict
├── schema.sql
└── data/
    ├── raw/                        files exactly as downloaded
    ├── processed/                  tidy tables + data_dictionary.csv
    ├── manifest.json               download log: link, size, checksum, time
    ├── search_log.json             catalog search results
    └── profiles/                   measured row counts, columns, date ranges, keys
```

The skill stops at the plan. Cleaning, queries, models and dashboards are the
student's work.

## The rules it follows

1. **Evidence labels.** Every fact about a dataset is marked `[FILE]` (measured
   from the downloaded file), `[SOURCE]` (stated on the publisher's page) or
   `[UNVERIFIED]`.
2. **Provenance.** Every dataset is classified as actual, anonymized, simulated
   or synthetic, with the evidence. Fictional sample datasets are never
   presented as a real company's records.
3. **No invented data.** Gaps are reported, not filled. If a download needs a
   login, the dataset is listed as not collected, with manual steps.

## The helper scripts

They can also be run on their own.

```bash
# measure the public data footprint of candidate companies
python scripts/company_lookup.py "Infosys" "Wipro" "TCS" --topic "employee attrition" --project ./my-project

# search Kaggle, Hugging Face, UCI, Zenodo and Harvard Dataverse
python scripts/find_datasets.py "customer churn" "telecom subscriber cancellation" --project ./my-project

# download and log (Kaggle datasets need no account; Kaggle competitions do)
python scripts/fetch_dataset.py kaggle:owner/dataset-slug --project ./my-project --id my-dataset
python scripts/fetch_dataset.py sec-facts:1067491 sec-filings:1067491 wiki-pageviews:Infosys --project ./my-project --id infosys
python scripts/fetch_dataset.py "cfpb:CAPITAL ONE FINANCIAL CORPORATION" --since 2025-01-01 --project ./my-project --id capital-one

# build tidy tables and a data dictionary
python scripts/structure_data.py --project ./my-project

# profile everything that was downloaded
python scripts/profile_data.py --project ./my-project
```

## Layout of this repository

| Path | Purpose |
|---|---|
| `SKILL.md` | The workflow Claude follows |
| `references/` | Company data sources, alternative approaches, catalogs and portals, provenance rules, the four analytics stages, document outlines |
| `scripts/` | Company scan, search, download, structuring and profiling helpers |
| `evals/` | Test cases used to check the skill |
