# Alternative approaches to a data analytics project

The default in this skill is a **single-company deep dive**. It is not always the
best fit. Offer the two most suitable alternatives at Checkpoint 2, and switch
when the chosen company's public data cannot carry the analysis.

## Summary

| # | Approach | Data is | Strongest stages | Weakest stages | Choose it when |
|---|---|---|---|---|---|
| A | Single-company deep dive | Real, mostly company-period aggregates plus regulator records | Descriptive, diagnostic (with peers) | Record-level prediction | The company discloses the topic KPI over several years |
| B | Focal company plus peers | Real, same measures for 3-5 companies | Diagnostic, benchmarking, prescriptive targets | Record-level prediction | A regulator or reports cover several companies the same way |
| C | Company-published dataset first | Real or anonymized, record-level | All four | Choice of company is limited | A company has released row-level data for the topic |
| D | Company plus proxy dataset | Real company figures + record-level data from elsewhere | All four, with a disclosed gap | Claims about the company's own customers | The topic needs per-customer or per-employee modelling and the company has no public record-level data |
| E | Best public dataset for the topic | Whatever is best documented, any organisation | All four | Tie to a named company | The user cares about method more than about a company |
| F | Primary data collection | Real, collected by the student | Diagnostic, descriptive | Volume, representativeness | The question is about perceptions or a local market |
| G | Internship host's own data | Real internal data | All four | Access, confidentiality | The student is placed at a company willing to share anonymized data |
| H | Synthetic data calibrated on public figures | Synthetic | Teaching the method | Every real-world claim | Only when the user explicitly asks |

## A. Single-company deep dive (default)

One company, all six layers of `company-data.md`, at company × period grain,
plus any record-level regulator data naming the company.

- **Descriptive**: the KPI over time, by segment and region where disclosed.
- **Diagnostic**: relate the KPI to its drivers over time (staff costs, pricing,
  demand, service levels), and to peers. With few periods, keep tests simple and
  conclusions modest.
- **Predictive**: forecast the KPI (time series, regression on drivers). With
  five to ten annual points, say plainly that forecasts are indicative; quarterly
  or monthly data is much better.
- **Prescriptive**: targets and levers framed against peer benchmarks, with
  sourced cost assumptions.

Limitation to disclose: no record-level view of individual customers or
employees.

## B. Focal company plus peers

Collect identical measures for the focal company and three or four competitors.
Turns a time series of ten points into a panel of forty or fifty, which makes
diagnostic and predictive work far more credible. Best when the source is a
regulator table or a mandated report format (for example BRSR in India, airline
on-time data, CFPB complaints). Usually the strongest real-data option for
company topics; recommend it whenever peers are covered by the same source.

## C. Company-published dataset first

Start from the data: find companies that have released row-level data for the
topic (an e-commerce marketplace's orders, a retailer's sales competition data,
a bank's research dataset, a transport operator's trip records) and choose among
those. Record-level, real or anonymized, often multi-table, so every stage
works. The trade-off is that the user cannot pick any company they like.

## D. Company plus proxy dataset

Real figures for the chosen company (layers 1, 2, 5, 6) for the business case
and benchmarks, plus a record-level dataset from another organisation, or a
fictional sample, for the predictive model. The report must say which parts rest
on which source, and that the model demonstrates the method rather than
describing the chosen company's customers or staff. Useful when a student must
build a classification model on a company topic like attrition or churn.

## E. Best public dataset for the topic

The industry-first approach: find the best documented real dataset for the
topic regardless of company (see `data-sources.md`). Simple and robust; the
analysis is tied to the dataset's organisation and period rather than to a
company the student chose.

## F. Primary data collection

The student collects data: a survey of customers or employees, structured
interviews, observation, or collection from an official API or a site whose
terms allow it. Plan the instrument (questions tied to hypotheses), the sample
size, consent and anonymisation. Good for perception and local-market questions,
weak on volume and representativeness. Combine with A or E for scale.

## G. The internship host's own data

If the student is placed at a company, its own data, anonymized and released
under the company's approval, is the most realistic option. The skill then
plans the request: which tables, which fields, the period, the anonymisation
required, and a data-sharing note for the supervisor to approve. Do not collect
anything until the company has agreed in writing.

## H. Synthetic data calibrated on public figures

Only when the user explicitly asks. Generate records whose totals and rates
match the company's real published figures (for example its attrition rate and
headcount by function), save them under `data/synthetic/`, label them
`SYNTHETIC`, and record the seed and the figures used. Useful for practising a
pipeline; never evidence about the company.

## Combining approaches

The strongest projects usually combine:

- **A + B**: focal company and peers from the same sources - the default
  recommendation when peers are covered.
- **A/B + D**: when record-level modelling is required.
- **C + B**: a company-published dataset, benchmarked with peers' public figures.
- **A + F**: company figures plus a small survey for the "why".

State the combination in `00_company_selection.md` and in the data disclosure.
