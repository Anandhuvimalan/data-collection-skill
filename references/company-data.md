# Collecting public data about one company

## Contents

1. What public data can and cannot show
2. Choosing candidate companies
3. Judging a company's data footprint
4. The six layers, with sources
5. Company sources by country
6. Topic playbooks
7. Extracting figures from reports
8. Peers

Access notes were checked by running the requests in November 2026. Sites
change; trust what you observe and say so in the report.

---

## 1. What public data can and cannot show

Be honest with the user about this at Checkpoint 2, because it shapes the whole
project.

| Public data CAN give you | Public data almost never gives you |
|---|---|
| Financial statements by year or quarter | Records of individual customers or employees |
| KPIs the company chooses to disclose (headcount, attrition rate, subscribers, churn, ARPU, complaints, on-time rate) | Internal operational logs |
| Regulator records naming the company (complaints, recalls, punctuality, claims, safety incidents) | Costs of internal actions (what a retention offer costs) |
| Customer and employee voice (complaints, reviews, ratings) where terms allow | The company's own segmentation and targeting data |
| Peer and market figures from the same sources | Anything under NDA |
| Datasets the company itself released (rare, valuable) | |

So a single-company project usually works at **company-period grain** (company ×
year/quarter/month), plus whatever **record-level** public data exists about the
company (complaints, recalls, reviews, flights, company-published datasets).
When the topic needs per-customer or per-employee prediction and no such public
data exists for the company, say so and pair the company's real figures with a
record-level dataset from elsewhere (see `approaches.md`, "Company plus proxy
dataset"). Never present that proxy as the company's data.

## 2. Choosing candidate companies

Aim for four to six candidates, mixed on purpose:

- **Leaders in the industry**, in the user's preferred country if any. Listed
  companies are the safest: they must publish reports.
- **Companies a regulator reports on individually** for this topic. Regulator
  tables are real, regular, comparable across companies, and usually machine
  readable.
- **Companies that published their own data** - search catalogs for the company
  name and look for the company's own account or a paper co-authored with it.
- **One smaller or more specialised company** when it is unusually transparent
  (detailed sustainability report, monthly operating data).

Avoid candidates whose only data is third-party uploads of unknown origin, and
private companies with no filings unless a regulator covers them.

## 3. Judging a company's data footprint

`company_lookup.py` measures part of this automatically. Complete the picture
with web search and rate each candidate:

| Criterion | Strong | Weak |
|---|---|---|
| Topic KPI disclosed | The topic's own measure appears in reports (attrition rate, churn, complaints) | Only general financials |
| Time depth | 5+ years, ideally quarterly or monthly | One year, or a snapshot |
| Record-level data | Regulator records or a company-published dataset | None |
| Drivers available | Data on plausible causes (pricing, staffing, service levels, product mix) | Outcome only |
| Peers comparable | Same source covers competitors | Company-only source |
| Access | Open download or API | Login, paywall, PDF only |

The recommended company is the one strongest on the first four for *this*
topic, not the most famous.

## 4. The six layers, with sources

### Layer 1 - Company profile

Identity, legal name, structure, segments, geography, size, history.

- Wikidata (via `company_lookup.py`): legal name, country, industry, HQ, founded,
  website, stock listings, LEI.
- The company's own site: "About", "Investors", segment descriptions.
- GLEIF (`api.gleif.org`): legal entity and parent relationships.
- Business registers: India MCA, UK Companies House (free API key), US state
  registers.

### Layer 2 - Financial and operating KPIs

- **US-listed companies and foreign filers in the US** (including many Indian IT
  firms that file 20-F): SEC EDGAR. `sec-facts:<CIK>` gives every tagged
  financial figure; `structure_data.py` builds a fiscal-year table from it.
  `sec-filings:<CIK>` gives the filing list with links to each report.
- **Annual reports and investor presentations**: download the PDFs, extract the
  KPI tables (section 7).
- **Quarterly results and earnings call transcripts**: often hold the topic KPI
  (attrition, churn, net adds) every quarter.
- **Sustainability reports**: employee turnover, headcount by gender and level,
  training hours, safety incidents, complaints. In India, the Business
  Responsibility and Sustainability Report (BRSR), required of large listed
  companies, includes employee and worker turnover rates for three years and
  consumer complaint counts.
- **Stock prices**: exchange websites or a licensed data source. Free unofficial
  price APIs change often; note the source and date if one is used.

### Layer 3 - Operational and customer records

- Datasets the company published (catalog search with the company name).
- Regulator records naming the company. Examples: US CFPB consumer complaints
  (`cfpb:<name>`), NHTSA vehicle complaints and recalls (`api.nhtsa.gov`), openFDA
  recalls and adverse events (`api.fda.gov`), US DOT airline on-time data per
  carrier (BTS), CMS hospital quality data per hospital, OSHA inspections per
  establishment, FCC complaints.
- Open data from the company's sector: city transport and trip records name the
  operator; energy regulators publish per-utility data.

### Layer 4 - Voice of customer or employee

Complaints (layer 3 sources), app store reviews, review sites, social media,
employee review sites.

Check each source's terms before collecting. Many review and employer-rating
sites forbid scraping; for those, record summary figures you read on the page
(rating, number of reviews, date) as `[SOURCE]`, or have the student export what
the site allows. Official APIs, regulator data and openly licensed review
corpora are fine. Do not collect names or contact details of reviewers.

### Layer 5 - Peers and market

The same measures for two or three direct competitors, from the same sources,
for the same periods. Industry associations and regulators publish market
totals and shares. This layer turns "attrition is 14%" into "attrition is 3
points above the peer median", which is what diagnostic analysis needs.

### Layer 6 - External drivers

Macro and sector context that may explain the company's numbers: GDP, inflation,
wage growth, unemployment, interest rates, exchange rates, demand indicators,
policy changes, seasonality. World Bank, IMF, OECD, central banks (RBI DBIE for
India), statistics offices. Collect at the same period grain as the company
data so it can be joined.

## 5. Company sources by country

Confirm each address before citing it. Leads, not verified facts.

| Country | Company-level sources |
|---|---|
| India | BSE and NSE corporate filings (annual reports, quarterly results, shareholding, BRSR); MCA company master data; SEBI; TRAI per-operator subscriber and quality reports; DGCA per-airline punctuality, cancellations and complaints; RBI per-bank statistics and Ombudsman complaint reports; IRDAI per-insurer claim settlement and complaints; company investor-relations pages |
| United States | SEC EDGAR (filings, XBRL facts); CFPB complaints; BTS / DOT airline data per carrier and the Air Travel Consumer Report; NHTSA; openFDA; CMS; FCC; OSHA; FDIC and FFIEC bank data per institution; EIA per-utility data |
| United Kingdom | Companies House (free API key); FCA complaints data per firm; Ofcom complaints per provider; ORR rail operator performance; CAA airline punctuality |
| European Union | National business registers; ESMA; national regulators' per-firm complaint and quality reports |
| Global | Company investor-relations sites; GLEIF; stock exchanges; sustainability report registries |

## 6. Topic playbooks

Quick starting points. Verify every lead.

| Topic | Company KPI to find | Record-level public data | Peers and drivers |
|---|---|---|---|
| Employee attrition | Attrition / turnover rate, headcount, hiring, employee cost (quarterly results, BRSR, sustainability report) | Rarely any; employer-review summaries; job-posting counts | Peer attrition from the same reports; wage growth, IT demand, unemployment |
| Customer churn | Subscribers, net adds, churn rate, ARPU (quarterly results; telecom regulator per-operator data) | Regulator complaints; app reviews; company-published sets if any | Peer subscribers and ARPU from the regulator; price changes, network quality |
| Customer complaints | Complaints received and resolved (BRSR, regulator reports) | CFPB, Ofcom, FCA, banking ombudsman, DGCA records naming the company | Same regulator for peers; product launches, policy changes |
| Sales / demand | Revenue by segment and region, volumes, store counts | Company-published sales data (rare, e.g. competition datasets released by retailers) | Market sales statistics; prices, income, seasonality |
| Delivery / operations | On-time rate, cancellations, delivery times | Airline on-time records per carrier; trip records per operator | Peer carriers; weather, demand, capacity |
| Credit risk | Non-performing assets, provisions, loan book by segment (filings) | Loan-level data for some securitisations; complaints | Peer banks from the regulator; interest rates, unemployment |
| Product quality / safety | Recalls, warranty costs (filings) | NHTSA, FDA, product safety recall records | Peer recalls; production volumes |

## 7. Extracting figures from reports

1. Download each report with `fetch_dataset.py` (one id per company, e.g.
   `infosys-annual-reports`), so it is in the manifest.
2. Find the table: search the PDF text for the KPI name ("attrition", "turnover",
   "complaints", "subscribers").
3. Extract into a CSV in `data/raw/<id>/extracted/`, one row per company per
   period per measure:
   `company_id, period, measure, value, unit, definition_as_stated, source_file, source_page`.
4. Copy the company's own definition of the measure. Companies define
   "attrition" differently (voluntary only, trailing twelve months, excluding
   trainees), and peers are only comparable when definitions match. Record
   mismatches in the preparation plan.
5. Check every extracted number against the page once more. Label them
   `[SOURCE]` with the page.

## 8. Peers

Choose two or three direct competitors: same industry, similar size, ideally the
same country and reporting regime. Collect the same layers for them, at the same
grain and periods, with the same company id convention. Peer data is what lets
diagnostic analysis separate "industry-wide" from "company-specific", and it is
the honest benchmark for prescriptive targets.
