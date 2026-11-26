# 1. Setup and loading

Goal for this week: tools installed, data in a SQL database, and a Power BI file
whose tables are related correctly. Mistakes in the model show up later as wrong
numbers, so this step pays for itself.

## 1.1 Install the tools

| Tool | Get it | Check it works |
|---|---|---|
| Python 3.10+ | python.org (tick "Add to PATH" on Windows) | `python --version` |
| Python libraries | `pip install -r guide/python/requirements.txt` | `python -c "import sklearn, statsmodels"` |
| An editor | VS Code with the Python and Jupyter extensions | open `guide/python/01_prepare.py` |
| SQL database | SQL Server Express + SSMS, **or** PostgreSQL + pgAdmin | connect and run `SELECT 1;` |
| Power BI Desktop | Microsoft Store or microsoft.com (Windows only) | open a blank report |

Tip: create a virtual environment so the project's libraries do not clash with
others: `python -m venv .venv`, then activate it (`.venv\Scripts\activate` on
Windows, `source .venv/bin/activate` on macOS/Linux).

## 1.2 Understand the project folder

```
<project>/
├── data/raw/          files exactly as downloaded - never edit these
├── data/processed/    tidy tables to analyse (+ data_dictionary.csv)
├── guide/             this guide and the Python scripts
├── outputs/           everything the scripts produce (created when you run them)
├── schema.sql         CREATE TABLE statements for your tables
└── 0X_*.md            the project documents (problem, data report, plan...)
```

Read `02_data_collection_report.md` and `data/processed/data_dictionary.csv`
before touching the data: they say what each table and column means, and what
the data cannot tell you.

## 1.3 Load the data into SQL

Why bother with SQL when Power BI can read CSV? Because the internship expects
it, because SQL checks your keys, and because the queries you write become part
of your deliverables.

**Option A - SQL Server (SSMS)**

1. Open SSMS, connect, right-click **Databases → New Database**, name it after
   your project.
2. Open `schema.sql` and run it (**Execute** or F5) to create the tables.
3. Load each CSV: right-click the database → **Tasks → Import Flat File**, pick
   the CSV, check the column types on the "Modify Columns" page, and finish.
4. Check row counts match the files:
   ```sql
   SELECT COUNT(*) AS rows_loaded FROM dbo.customers;
   ```

**Option B - PostgreSQL (pgAdmin)**

1. Create the database, open the Query Tool, run `schema.sql`.
2. Right-click the table → **Import/Export Data**, choose the CSV, set
   **Header** on, delimiter `,`.

**Option C - from Python (works for both)**

```python
import pandas as pd
from sqlalchemy import create_engine

# SQL Server (Windows login):
engine = create_engine("mssql+pyodbc://localhost\\SQLEXPRESS/MyProject"
                       "?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes")
# PostgreSQL:
# engine = create_engine("postgresql+psycopg2://user:password@localhost:5432/myproject")

df = pd.read_csv("data/processed/customers.csv")
df.to_sql("customers", engine, if_exists="replace", index=False)
print(pd.read_sql("SELECT COUNT(*) AS n FROM customers", engine))
```

(Install the driver first: `pip install pyodbc` for SQL Server, `pip install
psycopg2-binary` for PostgreSQL. Never put a real password in a file you share;
use an environment variable.)

**Key checks to run in SQL** - copy these into your SQL deliverable:

```sql
-- 1. Is the key really unique?
SELECT customer_id, COUNT(*) FROM customers GROUP BY customer_id HAVING COUNT(*) > 1;

-- 2. Do all foreign keys find a parent? (orphans)
SELECT COUNT(*) AS orphan_orders
FROM orders o LEFT JOIN customers c ON o.customer_id = c.customer_id
WHERE c.customer_id IS NULL;

-- 3. Missing values per important column
SELECT SUM(CASE WHEN monthly_charges IS NULL THEN 1 ELSE 0 END) AS missing_charges FROM customers;

-- 4. The headline KPI, as a first sanity check
SELECT AVG(CASE WHEN churn = 'Yes' THEN 1.0 ELSE 0 END) AS churn_rate FROM customers;
```

## 1.4 Build the Power BI model

1. **Get the data.** Home → **Get data** → **SQL Server** (server name, database,
   *Import* mode) or **Text/CSV** for files. Select the tables → **Transform
   Data** (not Load) so you can check them first.
2. **In Power Query**, for every table: check each column's type icon (ABC,
   123, calendar). Turn on **View → Column quality, Column distribution, Column
   profile**, and click "Column profiling based on top 1000 rows" in the status
   bar to switch to **entire data set**. Fix types, then **Close & Apply**.
3. **Model view** (left bar, third icon). Drag the key from the dimension
   table onto the matching column of the fact table. Double-click each
   relationship and check: **Cardinality** one-to-many from the dimension
   (customers, products, companies, dates) to the fact (orders, complaints,
   scores); **Cross filter direction** *Single*. Avoid many-to-many unless you
   understand why you need it.
4. **Add a date table** if any table has dates. **Modeling → New table**:
   ```DAX
   Date =
   ADDCOLUMNS (
       CALENDAR ( DATE ( 2015, 1, 1 ), DATE ( 2026, 12, 31 ) ),
       "Year", YEAR ( [Date] ),
       "Quarter", "Q" & QUARTER ( [Date] ),
       "Month", FORMAT ( [Date], "MMM" ),
       "Month No", MONTH ( [Date] ),
       "Year-Month", FORMAT ( [Date], "YYYY-MM" )
   )
   ```
   Set the range to cover your data. Select the table → **Table tools → Mark as
   date table** → choose `Date`. Sort `Month` by `Month No` (select Month →
   **Column tools → Sort by column**). Relate `Date[Date]` to each fact table's
   date column.
5. **Create a measures table** to keep things tidy: **Home → Enter data**, name it
   `_Measures`, load it, and create every measure in it (select it before
   **New measure**). Delete its dummy column afterwards.

The shape to aim for is a **star schema**: facts in the middle (one row per
event or per record), dimensions around them (customers, products, companies,
dates). For a company-period project the company table and the date table are
the dimensions, and each KPI table is a fact.

## 1.5 Done when

- [ ] Row counts in SQL and Power BI match `data_profile.md`
- [ ] Keys are unique where they should be; orphans counted and explained
- [ ] Relationships are one-to-many, single direction, and drawn correctly
- [ ] Date table marked, months sorted correctly
- [ ] `guide/python/config.py` filled in with your file and column names
