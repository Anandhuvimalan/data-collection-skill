# Where real data lives and how to get it

## Contents

1. How to search well
2. Catalogs the search script covers
3. Sources the script does not cover (use web search)
4. Country portals
5. Sector starting points
6. Company reports as data
7. When a source needs a login
8. Collecting from APIs
9. Licence, terms and ethics

Access notes in this file were checked by running the requests in November
2026. Sites change. If something here no longer works, trust what you observe
and say so in the report.

---

## 1. How to search well

One phrase is never enough. Datasets are titled by whoever uploaded them, so
search the same idea three ways:

| Angle | Example for "customer churn" | Example for "delivery delays" |
|---|---|---|
| Business term | customer churn, customer retention | late delivery, on-time delivery |
| Industry term | telecom subscriber cancellation, bank account closure | e-commerce logistics, last mile, freight |
| Data term | subscription dataset, customer transactions | order shipment dataset, delivery timestamps |

Also search for the **underlying records** rather than the analysis you want. A
"churn dataset" is usually a pre-flattened teaching table. A transactions or
subscriptions dataset lets the student *derive* churn, which is closer to real
work and usually has dates.

Prefer, in this order:

1. Data published by the organisation that generated it (a company's open data,
   a regulator, a statistics office, a hospital system, a city).
2. Data deposited with a paper or a DOI (UCI, Zenodo, Dataverse, Mendeley Data,
   a journal's data article) - the paper explains how it was produced.
3. A community upload that links back to one of the above. Follow the link and
   treat the original as the source.
4. A community upload with no stated origin. Usable for practice, but its
   provenance is `unverified`.

Popularity is not evidence. The most-downloaded dataset for a topic is often a
fictional sample.

## 2. Catalogs the search script covers

`find_datasets.py` queries these without an account:

| Catalog | What it is good for | Download |
|---|---|---|
| Kaggle (datasets) | Widest range of business datasets; quality and provenance vary enormously | `kaggle:owner/slug` works with no login |
| Hugging Face | Growing set of tabular data; many are mirrors of Kaggle or UCI | `hf:owner/name` for public, ungated repos |
| UCI ML Repository | Classic, documented, citable; each has a paper or donor | direct zip URL (printed by the script) |
| Zenodo | Research data with DOIs; often real operational data from studies | `zenodo:<record id>` for open records |
| Harvard Dataverse | Replication data for published research | file URLs from the landing page |
| CKAN portals (`--ckan URL`) | Government open data; resources come with direct file URLs | the resource URL |

Kaggle's search ordering defaults to votes here because well-used datasets have
discussion threads that often reveal where the data came from. Use
`--kaggle-sort relevance` when the popular results are off-topic.

**Kaggle competitions are different from Kaggle datasets.** Competition data
(Rossmann, M5, Home Credit, Favorita, IEEE-CIS fraud and others) needs a logged-in
account that has accepted the competition rules. The no-login download returns
HTTP 401. These are often excellent real data, so list them with manual steps
rather than dropping them.

## 3. Sources the script does not cover

Use the session's web search for these. They are where the most credible data is.

- **Google Dataset Search** (`datasetsearch.research.google.com`) - an index
  across publishers. Use it through a browser or web search; it has no open API.
- **Statistics offices and regulators** - sector regulators publish operational
  data that companies do not: telecom subscriptions and complaints, banking
  aggregates, insurance claims, aviation punctuality, energy load, road
  accidents, hospital activity.
- **International bodies** - World Bank, IMF, OECD, Eurostat, UN Data, WHO, ILO,
  FAO. Good for macro context and country comparisons.
- **City and state portals** - many run Socrata or CKAN and expose every dataset
  as CSV or JSON.
- **Data journals** - *Data in Brief*, *Scientific Data*: a paper whose whole
  purpose is to describe one dataset.
- **Mendeley Data, Figshare, OpenML, AWS Open Data Registry, Google BigQuery
  public datasets, data.world.**
- **Company open data and annual reports** (section 6).

Checked access patterns:

| Source | Request that works without a key |
|---|---|
| World Bank indicators | `https://api.worldbank.org/v2/country/<ISO3>/indicator/<code>?format=json&per_page=1000` |
| Eurostat | `https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/<dataset>?format=JSON&...` |
| Socrata portals | `https://<portal>/resource/<id>.csv?$limit=50000&$offset=0` (page with `$offset`) |
| CKAN portals | `https://<portal>/api/3/action/package_search?q=<words>&rows=10` |
| UCI | `https://archive.ics.uci.edu/api/dataset?id=<id>` for metadata, `.../static/public/<id>/<slug>.zip` for files |
| Zenodo | `https://zenodo.org/api/records?q=<words>&type=dataset` |
| OpenML | `https://www.openml.org/api/v1/json/data/<id>` |

## 4. Country portals

When the user names a location, search that country's official sources before
anything else. Confirm each address resolves before citing it.

| Country / region | Starting points |
|---|---|
| India | `data.gov.in` (Open Government Data platform; its API needs a free key, file downloads may need a sign-in), RBI Database on Indian Economy, MoSPI / National Statistics Office, NITI Aayog NDAP, TRAI (telecom subscription and performance reports), NPCI (payment statistics), IRDAI (insurance), SEBI, NCRB (crime), AGMARKNET (market prices), IMD (weather), MoRTH (road accidents), DGCA (aviation), UDISE+ (schools), NFHS (health surveys) |
| United States | `data.gov`, Census Bureau, BLS, BEA, FRED, CFPB Consumer Complaint Database, CMS (Medicare), BTS (airline on-time data), SEC EDGAR, NYC / Chicago / other city portals, NYC TLC trip records |
| United Kingdom | `data.gov.uk` (CKAN), ONS, NHS England statistics, HM Land Registry Price Paid Data, DfT road safety data, Ofcom, FCA |
| European Union | `data.europa.eu`, Eurostat, ECB Data Portal, national statistics offices |
| Canada / Australia / Singapore | `open.canada.ca`, Statistics Canada; `data.gov.au`, ABS; `data.gov.sg` |
| Global | World Bank Open Data, IMF Data, OECD Data Explorer, UN Data, Our World in Data (cites its original sources - go to those) |

A regulator's report is often a PDF or Excel workbook, not a tidy table. That is
still real data. Download the workbook, or record the report, page and table
you took figures from.

If a location preference cannot be met with row-level data, say so directly and
offer the realistic alternatives: (a) row-level data from another country plus
local official aggregates for context, or (b) a narrower project built on the
local aggregates.

## 5. Sector starting points

These are leads from general knowledge to speed up the search, **not verified
facts**. Search for them, open the page, and confirm name, link, size, period and
provenance yourself before any of it goes in a report. Provenance notes on the
well-known ones are in `provenance.md`.

| Topic area | Leads worth checking |
|---|---|
| Customer churn / retention | Telecom and subscription datasets; transaction logs from which churn can be derived (online retail, e-commerce orders); KDD Cup 2009 (Orange); regulator complaint and switching statistics |
| Sales / demand forecasting | Store and item sales competitions (Rossmann, Walmart M5, Favorita - login needed); UCI Online Retail and Online Retail II; city open data on licences or permits |
| E-commerce, orders, delivery | Olist Brazilian E-Commerce (multi-table); Instacart orders; REES46 behaviour logs; DataCo supply chain (Mendeley Data) |
| Credit risk / loan default | Default of Credit Card Clients (UCI); Give Me Some Credit; LendingClub loan data; Home Credit (login); Fannie Mae and Freddie Mac loan-level data (registration) |
| Fraud | ULB credit card fraud; IEEE-CIS (login); PaySim (a simulator - see `provenance.md`) |
| Marketing / campaigns | UCI Bank Marketing; Criteo datasets; online advertising click logs |
| HR / attrition | Row-level real HR data is rare. Official labour statistics (turnover, quits), public-sector workforce data, and company annual-report attrition figures are real but aggregate |
| Healthcare | Diabetes 130-US Hospitals (UCI); CMS public use files; hospital appointment no-shows; WHO and national health statistics. Clinical record sets such as MIMIC need credentialed access |
| Supply chain / inventory | Sales and inventory competition data; port, freight and customs statistics; DataCo |
| Customer complaints / service | CFPB Consumer Complaint Database; city 311 service requests; regulator complaint statistics |
| Transport / mobility | NYC TLC trips; airline on-time performance; bike-share system data; national road accident data |
| Energy | UCI household power consumption; grid operator load data; national energy statistics |
| Manufacturing / maintenance | SECOM (UCI); most others are simulators or synthetic - check |
| Real estate | Land registry price data; Ames housing; King County sales; listing datasets |
| Education | Open University Learning Analytics Dataset (multi-table); UCI Student Performance; national school statistics |
| Hospitality / travel | Hotel booking demand (two hotels, published in *Data in Brief*); airline and tourism statistics |
| Reviews / sentiment | Amazon review corpora; Yelp Open Dataset |

Multi-table sets are worth extra effort: they let the student build a real
relational model, write real joins and derive their own measures.

## 6. Company reports as data

When the user prefers a company, or the industry has no open row-level data,
public filings are real, citable evidence:

- Annual and quarterly reports, investor presentations, sustainability reports.
- Stock-exchange and regulator filings.
- Operating metrics companies disclose routinely (subscribers, churn or
  attrition rate, average revenue per user, store counts, on-time performance).

Use them for business context, for benchmark KPIs, and for the cost and value
assumptions that prescriptive analytics needs. Record the document, its date,
the page and the table. They are `actual` data at aggregate level, labelled
`[SOURCE]`.

Never present a public dataset as that company's internal records. "Benchmarked
against figures the company reports publicly" is honest; "the company's customer
data" is not.

Some filing systems (SEC EDGAR, for example) require automated clients to send
a contact address in the request header. Do not invent one and do not use the
user's details without asking; ask the user, or have them download the file.

## 7. When a source needs a login

Do not work around access controls, and never ask for or store a password or
API token in the project folder. Record the dataset as not collected and write
manual steps the student can follow:

1. The page to open (the landing page you verified).
2. What they need (free account, terms to accept, API key request).
3. The exact button or file to download.
4. Where to save it: `data/raw/<dataset-id>/`.
5. The command to run afterwards: `python <skill>/scripts/profile_data.py --project <project>`.

For Kaggle competition data, the student can alternatively install the official
`kaggle` command-line tool and configure their own API token in their own user
profile, then run `kaggle competitions download -c <name>` after accepting the
rules on the website.

A plan may still be built around a dataset that was not collected, but every
fact about it is `[SOURCE]` at best, and the feasibility verdict must say the
plan is conditional on the student obtaining and profiling the file.

## 8. Collecting from APIs

`fetch_dataset.py` takes any URL, so a single API call that returns CSV or JSON
is collected like a file, with the full query recorded in the manifest.

When collection needs pagination or many calls, write a small script into
`<project>/collect/` that:

- saves raw responses into `data/raw/<dataset-id>/` unchanged,
- waits politely between requests and stops on repeated errors,
- prints how many records it retrieved,
- can be re-run by the student from the command line.

Then profile the result as usual. State the retrieval date: API data changes,
and a report should say which day's snapshot it used.

## 9. Licence, terms and ethics

- Record the licence or terms as written on the source page. "Not stated" is a
  valid and useful finding.
- Educational use of open data is normally fine. Redistribution and commercial
  use may not be - flag it when the licence restricts them.
- Prefer the official download or API. Scrape only where the site's terms allow
  it, and never behind a login.
- Do not collect data about identifiable private individuals. If a dataset
  contains names, phone numbers, emails or national IDs, tell the user, and
  recommend dropping or masking those columns before any analysis.
- Cite datasets the way the publisher asks. A DOI or a requested citation goes
  in the data collection report.
