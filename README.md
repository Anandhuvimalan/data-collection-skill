# data-collection

A skill for Claude Code that turns a project topic into a real-data analytics
project.

You give it a topic, such as *Customer Churn Analysis*. It researches the
industry and the business problem, finds and downloads real public datasets,
records where each one came from, profiles the files, and plans the work through
the four kinds of analytics: descriptive, diagnostic, predictive and
prescriptive. The project starts from a business problem and ends with
recommendations.

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

Open Claude Code in the folder where you want the project created and give it
your topic:

```
Project topic: Customer Churn Analysis
```

Optional preferences can be added on the same message:

```
Project topic: Employee attrition analysis
Preferred industry: IT services
Preferred location: India
Preferred technology: Python, SQL Server, Power BI
```

Only the topic is required.

## What you get

```
<topic>/
├── README.md                       summary, verdict, data disclosure, next steps
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
# search Kaggle, Hugging Face, UCI, Zenodo and Harvard Dataverse
python scripts/find_datasets.py "customer churn" "telecom subscriber cancellation" --project ./my-project

# download and log (Kaggle datasets need no account; Kaggle competitions do)
python scripts/fetch_dataset.py kaggle:owner/dataset-slug --project ./my-project --id my-dataset

# profile everything that was downloaded
python scripts/profile_data.py --project ./my-project
```

## Layout of this repository

| Path | Purpose |
|---|---|
| `SKILL.md` | The workflow Claude follows |
| `references/` | Data sources, provenance rules, the four analytics stages, document outlines |
| `scripts/` | Search, download and profiling helpers |
| `evals/` | Test cases used to check the skill |
