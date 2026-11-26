# 7. Reporting and presenting - how to do it better

Goal: a dashboard a manager can use, a report a supervisor can trust, and a
presentation that ends in a decision. Most marks are won or lost here: good
analysis presented badly reads as weak analysis.

## 7.1 The dashboard: one page per question

| Page | Answers | Must contain |
|---|---|---|
| 1. Overview | What is the problem, how big, what do we recommend? | 3-4 KPI cards, one trend or segment chart, the recommendation in one sentence, the expected impact |
| 2. Descriptive | Where is it happening? | segment bars with counts, heat-map matrix, trend (if dates), slicers |
| 3. Diagnostic | Why? | key influencers or decomposition tree, confounder matrix, evidence table (effect sizes) |
| 4. Predictive | Who or what is next? | risk-band chart, model performance cards (vs baseline), top drivers, high-risk list or forecast with range |
| 5. Prescriptive | What should we do, and what is it worth? | what-if slicers, cards for targeted / spend / net benefit, scenario table, sensitivity chart |
| 6. Data & method | Can I trust this? | sources and their provenance class, period, row counts, refresh date, limitations |

**Design rules**

1. **One message per visual, written as its title.** "Month-to-month customers
   churn 4× more than annual" beats "Churn by contract".
2. **Layout follows reading order:** KPIs top-left, detail lower down, slicers
   along one edge.
3. **The right chart:** comparison → sorted bars; trend → line; part-to-whole
   with few parts → stacked bar; relationship → scatter; exact values → table or
   matrix. Avoid pies with more than three slices, 3-D charts, gauges without a
   target.
4. **Colour has meaning.** One neutral colour for everything, one highlight
   colour for the problem (and use it consistently). Do not rely on red/green
   alone; many readers are colour-blind.
5. **Always show the base.** Rates next to counts; percentages with the
   denominator in the tooltip.
6. **Consistent number formats:** percentages with one decimal, currencies with
   thousand separators, the same units everywhere.
7. **Interaction that helps:** sync slicers across pages (**View → Sync
   slicers**), drill-through from a segment to its detail page (add the field to
   the target page's **Drill through** well), tooltips pages for extra context,
   bookmarks for the presentation story (**View → Bookmarks**).
8. **Performance:** measures instead of calculated columns where you can,
   remove unused columns in Power Query, avoid many-to-many relationships.

Test the dashboard on someone who has not seen the project: if they cannot say
what the problem is in 30 seconds from page 1, simplify it.

To share: **File → Export → Export to PDF** for the report appendix, or
**Home → Publish** if your organisation uses the Power BI service.

## 7.2 The written report

Use this structure. Keep the main body to about 15-25 pages; push detail to
appendices.

| # | Section | Contents | Length |
|---|---|---|---|
| 1 | Executive summary | problem, key findings (3), recommendation, expected impact, main limitation | 1 page, written last |
| 2 | Business context and problem | company/industry, process, problem statement, objectives, hypotheses | 2-3 pages |
| 3 | Data | sources, provenance class of each, period, volume, quality issues and treatment, **data disclosure statement** | 2-3 pages |
| 4 | Method | tools, the four stages, tests and models used and why | 1-2 pages |
| 5 | Descriptive findings | KPIs, where the problem is concentrated, value at stake | 2-3 pages |
| 6 | Diagnostic findings | hypothesis table with verdicts, top factors, confounding checks | 2-3 pages |
| 7 | Predictive findings | model vs baseline, metrics, drivers, what the scores mean | 2-3 pages |
| 8 | Recommendations | decision framework, recommended actions, impact ranges, sensitivity, test plan | 2-3 pages |
| 9 | Limitations and next steps | what the data cannot show, assumptions, what to do next | 1 page |
| 10 | Appendices | data dictionary, SQL queries, code listing, full outputs, dashboard screenshots | as needed |

**How to write a finding** - claim, evidence, size, meaning:

> Customers on month-to-month contracts churn at 42.7% against 2.8% on two-year
> contracts (7,043 customers, [FILE]). The gap holds within every tenure band
> (chi-square, Cramér's V = 0.41, adjusted p < 0.001), so it is not explained by
> newer customers alone. Converting even a small share of month-to-month
> customers to annual contracts is therefore the main lever.

Rules for numbers in the text: round sensibly (42.7%, not 42.7097%); give the
comparison; give the base; label sources; never present an assumption as a
finding.

**Every chart in the report** has a numbered caption that states the finding,
labelled axes with units, and a source line ("Source: CFPB complaints,
2023-2025, retrieved 2026-11-20").

## 7.3 The presentation (10-12 slides, 10-15 minutes)

1. Title - project, company, your name, date
2. The problem and why it matters (one number)
3. The data - sources, period, and the disclosure in one line
4. What is happening - the one descriptive chart that matters
5. Where it is concentrated
6. Why - the tested factors, with the confounder check
7. What will happen - model vs baseline, in business terms (lift)
8. What we should do - the recommendation and its expected impact
9. What it depends on - the sensitivity chart, the critical assumption
10. How to prove it works - the test plan
11. Limitations and next steps
12. Questions (keep a backup slide for method details)

Lead every slide with its conclusion as the title. Demo the dashboard live only
if it is fast and you have rehearsed it; otherwise use screenshots.

## 7.4 How to do better: common mistakes and fixes

| Mistake | Fix |
|---|---|
| Starting with charts instead of the problem | Write the problem statement and hypotheses first; every chart answers one of them |
| Dataset described as a company's real data when it is a sample | State the provenance class and the disclosure statement on page 1 |
| Numbers that do not match between dashboard and report | One source of truth: compute in Python or SQL, check Power BI against it |
| "X causes Y" from correlations | "X is associated with Y, even after controlling for Z" |
| Accuracy reported for a rare outcome | ROC-AUC, PR-AUC, lift, precision/recall at a stated threshold |
| No baseline | Always show what "no model" or "same as last period" achieves |
| Recommendations without cost, impact or measurement | Use the decision framework and the recommendation template (guide 6) |
| Assumptions hidden in the numbers | Assumptions table with sources and ranges; sensitivity chart |
| Too many visuals | One message per visual; cut anything that does not support a finding |
| Limitations buried or missing | A clear limitations section; it raises trust |
| No reproducibility | Scripts in order, raw data untouched, README explaining how to rerun |

## 7.5 Final quality checklist

**Data**
- [ ] Every source listed with link, retrieval date and provenance class
- [ ] Raw files untouched; cleaning repeatable from scripts
- [ ] Row counts consistent across SQL, Python, Power BI and the report

**Analysis**
- [ ] KPIs defined with formulas
- [ ] Each hypothesis has a test, an effect size and a verdict
- [ ] Model evaluated on unseen data against a baseline; leakage checked
- [ ] Recommendations follow the decision framework, with ranges and a test plan

**Dashboard**
- [ ] Page 1 tells the story in 30 seconds
- [ ] Titles state findings; counts shown with rates; consistent formats
- [ ] Data & method page with sources and limitations

**Report and presentation**
- [ ] Executive summary written last, fits one page
- [ ] Every chart captioned with its finding and source
- [ ] Limitations and data disclosure stated plainly
- [ ] Appendices: data dictionary, SQL, code, outputs

**Submission folder**
- [ ] `README.md` explaining how to rerun everything
- [ ] `data/`, `guide/python/` (or your own scripts), `outputs/`, `.pbix` file, report, slides
