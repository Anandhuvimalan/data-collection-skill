# Project documents: what goes in each file

These outlines keep projects comparable across students, so a supervisor always
finds the same thing in the same place. Follow the headings. Fill them with
specifics from this project; drop a sub-point that truly does not apply and say
why in one line rather than padding it.

Keep each document focused. Tables beat paragraphs for anything a student will
look up later. Every fact about a dataset carries its evidence label:
`[FILE]`, `[SOURCE]` or `[UNVERIFIED]`.

## Contents

- README.md
- 00_company_selection.md
- 01_business_problem.md
- 02_data_collection_report.md
- 03_data_model.md and schema.sql
- 04_data_preparation_plan.md
- 05_analytics_plan.md
- 06_roadmap_and_deliverables.md
- 07_feasibility_review.md

---

## README.md

The page someone reads if they read nothing else.

```markdown
# <Project title>

**Topic:** ...   **Industry:** ...   **Prepared:** <date>   **Verdict:** Feasible | Feasible with revised scope | Not feasible as posed

## The problem in brief
Two or three sentences: who has the problem, what it costs, what the project will decide.

## Data at a glance
| Dataset | Role | Class | Rows | Period | Collected? | Source |
|---|---|---|---:|---|---|---|
(primary / supporting; actual / anonymized / simulated / synthetic / unverified; rows and period with evidence label; yes, or "no - see manual steps")

## Data disclosure
The paragraph the student copies into their report (see provenance.md for wording).

## What the four stages will deliver
One line each for descriptive, diagnostic, predictive, prescriptive, with status READY / LIMITED / BLOCKED.

## What is in this folder
File index, one line per file.

## Start here
The first five things the student should do, in order.

## Things you must check yourself
Anything left [UNVERIFIED], anything not collected, any assumption that needs the supervisor's agreement.
```

---

## 00_company_selection.md

Why this company, so a supervisor can see the choice was made on evidence.

1. **Topic and approach** - the topic, and the approach chosen from
   `approaches.md` (or the combination), with one line on why.
2. **Candidates** - every company considered:

   | Company | Country, sector | Listed | Topic KPI disclosed? | Record-level public data | Peers comparable | Time depth | Footprint score | Main limitation |
   |---|---|---|---|---|---|---|---:|---|

   Footprint figures come from `data/company_scan.md` (measured) plus what web
   search found (with links).
3. **Choice** - the company selected, who chose it (the user, or the default
   because the user asked you to decide), and the reasons.
4. **Details agreed** - problem angle, period, scope within the company, peers,
   tools, duration. Mark which were defaults.
5. **What public data can and cannot show about this company** - two short lists.
6. **Company profile** - legal name, country, HQ, industry, segments, size,
   listings, identifiers (Wikidata, LEI, CIK or exchange codes), website, with
   sources.

---

## 01_business_problem.md

**Part A - Industry and process**

1. Industries the topic applies to, compared in a table on business relevance
   and **data availability**, and the one chosen with the reason.
2. How the process works in a real organisation - the steps, in order.
3. Departments involved and what each owns.
4. Why the problem matters to the business, with sourced figures where found.
5. Operational and financial challenges.
6. Decisions that data analytics could improve.
7. Example companies, if useful. State that the project does not use their
   private data.

**Part B - The business problem**

1. Business background.
2. The existing process and where it breaks.
3. Problem identification - what is observed.
4. Problem statement - one tight paragraph: who, what, where, how much, and the
   decision it blocks. Include measured facts from the profile, worded as facts
   about the dataset.
5. Root causes to investigate, as numbered hypotheses:

   | # | Hypothesis | Why it is plausible | Columns that can test it | Status |
   |---|---|---|---|---|

6. Documented facts versus hypotheses - two separate lists. Each documented
   fact has a link you opened. Anything without one belongs in the other list.
7. Business consequences if nothing changes.
8. Project objectives - specific and measurable.
9. Research questions, each tagged with its analytics stage and status:

   | # | Research question | Stage | Status | Data used |
   |---|---|---|---|---|

10. Expected business outcomes.

---

## 02_data_collection_report.md

The most important document. A reader must be able to repeat the collection.

1. **Collection plan** - the matrix from Step 4: each source, its layer, and
   what it contributes to problem identification, cause, prediction and solution,
   with grain and period. Mark sources planned but not obtained.
2. **How the search was done** - date, catalogs and portals searched, the
   search phrases, and sources that failed or could not be reached.
3. **Candidates considered** - every shortlisted dataset, including rejected ones:

   | Dataset | Publisher | Link | Class | Rows / period | Decision | Reason |
   |---|---|---|---|---|---|---|

4. **Selected datasets** - one card each, all eleven points, each with its
   evidence label:

   | # | Item | Detail |
   |---|---|---|
   | 1 | Dataset name | |
   | 2 | Source / download link | landing page, and the direct link or reference used |
   | 3 | Publisher or organisation | |
   | 4 | Industry and context | what real-world activity it records |
   | 5 | Number of records | per file |
   | 6 | Historical period covered | or "no time dimension" |
   | 7 | Columns | list, or point to the data model |
   | 8 | Data types | as stored, and as they should be |
   | 9 | Format | CSV, Excel, JSON, API ... and size |
   | 10 | Class | actual / anonymized / simulated / synthetic / unverified, with the evidence |
   | 11 | Limitations and biases | coverage, age, selection, missing variables |

   Add the licence or terms, and how the publisher asks to be cited.

5. **Coverage of the four stages** - one table: datasets down the side, the
   four stages across, each cell saying what it supports and what is missing.
6. **Collection log** - copied from `data/manifest.json`: file, size, SHA-256
   (first 12 characters), retrieved at, requested link.
7. **Not collected** - each failed or login-gated dataset, why, and the manual
   steps to obtain it.
8. **Licence and ethics** - terms, personal data present or not, anything the
   student must not redistribute.
9. **Structured tables** - each table in `data/processed/`: what one row is,
   rows `[FILE]`, keys (company, period, record id), and the raw files it came
   from. Point to `data_dictionary.csv`.
10. **How to reproduce** - the exact commands that were run, and the scripts in
   `collect/`.

---

## 03_data_model.md and schema.sql

**Section 1 - Tables that exist** (from the profile, nothing invented)

For each table:

- name, the file it comes from, and its **grain** (what one row is);
- row count `[FILE]`;
- primary key - a column the profile found unique, or a composite key you
  checked, or "none";
- foreign keys, with the measured overlap from the profile;
- a column table: name, stored type, target SQL type, description, notes.

Column descriptions come from the publisher's data dictionary where one exists
(`[SOURCE]`). Where you inferred the meaning from the name and values, mark it
`inferred` so the student checks it.

**Section 2 - Relationships**

A table of relationships with cardinality and the measured match rate, and an
entity-relationship diagram in Mermaid (`erDiagram`). Call out anything
surprising the profile showed: keys that are not unique, orphan rows, a
"customer id" that is really one per order.

**Section 3 - Using several datasets**

Whether supporting datasets can be joined to the primary one, and on what. Join
only on a real shared key at a compatible grain (the same customer, the same
store and date, the same region and month), confirmed by overlap. Otherwise keep
them separate and say how each is used: benchmark, context, or assumption
source. Do not force unrelated datasets into one database.

State whether comparable data exists from more than one company or
organisation, and whether a multi-organisation comparison is realistic.

**Section 4 - Proposed extension (not available)**

The tables a real company would also hold for this problem - with columns, keys
and how they would connect - under a clear banner that **none of this is in the
collected data**. This shows the student what a production data model looks
like and what they would ask the business for. Include how often each table
would be collected in practice (per transaction, daily, monthly), labelled as
typical practice.

**Section 5 - Collection frequency**

For the collected data: a static snapshot as of the retrieval date, or a source
that updates (say how often and how to refresh).

**schema.sql** - `CREATE TABLE` statements for the tables that exist, in the
chosen SQL dialect, with primary and foreign keys, in an order that loads
without constraint errors. Comment any constraint the data violates.

---

## 04_data_preparation_plan.md

Lead with what the profile found, then cover the rest.

**Section 1 - Issues found in this data**

| # | Table.column | Issue (with count) | Treatment | Tool | Why this treatment |
|---|---|---|---|---|---|

Typical findings: numbers stored as text, disguised missing values, duplicate
rows, non-unique keys, orphan foreign keys, inconsistent category spelling,
dates stored as text, impossible values, date ranges with stray outliers.

**Section 2 - Preparation steps**

Cover each of these as it applies to this data, naming the technique and tool:

1. Missing value analysis - how much, where, random or systematic, and the
   treatment per column.
2. Duplicate detection - full-row and key-level.
3. Incorrect data types - and the conversion.
4. Outlier detection - method (IQR, z-score, business rule) and what to do with them.
5. Standardisation - category labels, units, date formats, text case.
6. Validation rules - ranges, allowed values, logical checks between columns.
7. Referential integrity - every foreign key resolves.
8. Feature engineering - each new feature tied to a hypothesis or a model need.
9. Data integration - the join order and the expected row count after each join.
10. Data leakage prevention - the list of columns excluded from modelling and why.

**Section 3 - Outputs**

The cleaned tables the student will produce, where they are saved, and a short
data-quality log template so every change is recorded.

---

## 05_analytics_plan.md

Read `four-analytics.md` first. One section per stage. Each opens with one line
on what it receives from the previous stage.

**A. Descriptive - what happened?**

| KPI | Meaning | Formula | Columns | Grain | Status |
|---|---|---|---|---|---|

| # | Question | Measure | Split by | Visual | Status |
|---|---|---|---|---|---|

**B. Diagnostic - why did it happen?**

| # | Hypothesis | Variables | Test | What would support it | Confounders to control | Status |
|---|---|---|---|---|---|---|

Then: how causes will be validated rather than assumed, and what evidence the
project lacks for a causal claim.

**C. Predictive - what might happen?**

- Target, prediction moment, unit.
- Features, grouped, with any that need engineering.
- Leakage register: excluded columns and why.
- Baseline, candidate models, selection criteria.
- Train/validation/test method.
- Evaluation metrics and why these.
- Status, and what limits the stage.

**D. Prescriptive - what should we do?**

- Decision, decision variables, objective, constraints.
- Assumptions table: value, source, low and high.
- Decision rule or optimisation method.
- Scenario table with expected impact.
- Measurement plan: control group, metric, duration, monitoring KPIs.

Close with a one-paragraph summary of how the four stages form one argument for
this problem.

---

## 06_roadmap_and_deliverables.md

**Implementation roadmap** - sequenced steps sized to the project duration:

| Step | Week | What to do | Why it is needed | Tools | Output | How it feeds the final project |
|---|---|---|---|---|---|---|

Typical sequence: confirm and obtain data → load to SQL → profile and clean →
build the model → descriptive → diagnostic → predictive → prescriptive →
dashboard → documentation and presentation. Adapt it: drop or shrink stages the
feasibility review limited.

**Deliverables checklist** - each tied to the step that produces it:

1. Project proposal
2. Business problem statement
3. Data collection report
4. Original datasets and source documentation
5. Database schema
6. Data cleaning and preprocessing scripts
7. SQL queries
8. Exploratory data analysis
9. Descriptive analytics dashboard
10. Diagnostic analysis report
11. Predictive model and evaluation report (if applicable)
12. Prescriptive recommendations
13. Final Power BI dashboard
14. Final project documentation
15. Business presentation

Mark which ones this folder already gives a draft of (usually 1 to 5).

---

## 07_feasibility_review.md

**Scorecard**

| Criterion | Rating | Evidence |
|---|---|---|
| Data availability | Strong / Adequate / Weak | |
| Data quality | | |
| Data volume | | |
| Business relevance | | |
| Analytical depth | | |
| Feasible within the internship | | |
| All four analytics types applicable | | |
| Actionable recommendations possible | | |

Rate from evidence in the profile and the collection report, not optimism.

**Missing information and limitations** - what the data cannot show.

**Risks and mitigations** - a short table.

**Verdict** - feasible, feasible with a revised scope (state it), or not
feasible as posed (state the alternative data or topic). If data is
insufficient, the recommendation to change scope comes before any further work.
