# 2. Data preparation

Goal: one clean analysis table (and clean supporting tables), with every change
written down. Analysts typically spend more time here than anywhere else, and
every later number depends on it.

Two rules:

- **Never edit the raw files.** Clean into new files, with a script, so anyone
  can repeat it.
- **Count before you change.** "11 blank values in `total_charges` filled with
  the median" belongs in your report; "cleaned the data" does not.

## 2.1 Python: run and read `01_prepare.py`

1. Open `guide/python/config.py` and set:
   - `RAW_TABLE` - your main table in `data/processed/`
   - `ID_COL`, `TARGET`, `POSITIVE` - the id, the outcome column, and the value
     that means "it happened" (lower case)
   - `DATE_COL`, `VALUE_COL` - a date column and a money column, or `None`
   - `LEAKAGE_COLS` - leave for now; you fill it in at the predictive stage
2. Run `python 01_prepare.py`.
3. Read what it printed and `outputs/preparation/quality_log.json`.

What the script does, step by step, and what you decide:

| # | Step | What the script does | What you decide or check |
|---|---|---|---|
| 1 | Column names | lower_snake_case | - |
| 2 | Disguised missing | blanks, "NA", "?", "unknown" → real missing | Is "unknown" really missing, or a real answer? |
| 3 | Numbers stored as text | converts when >95% of values are numbers | Check the column in the data dictionary |
| 4 | Dates | parses `DATE_COL` | How many failed, and why? |
| 5 | Category spelling | lower case, single spaces | Merge real synonyms by hand ("Cust. Service" = "customer service") |
| 6 | Duplicates | removes exact duplicate rows; counts duplicate ids | Duplicate ids need investigation, not deletion |
| 7 | Missing values | numeric → median + a `_was_missing` flag; text → "missing" category; >40% missing → kept and reported | Is the missingness random? A flag lets the model learn if it is not |
| 8 | Outliers | flags values beyond 3×IQR in an `_outlier` column, keeps them | Error, or a real extreme customer? Never delete without a reason |
| 9 | Target | adds `target` = 1/0 | Check the rate against the data report |
| 10 | Validation | negative amounts, ages, counts | Write rules that fit your data (e.g. end date after start date) |

On the worked example it reported: 11 blank `total_charges` values (customers
with zero tenure), converted `total_charges` from text to number, no duplicates,
churn rate 26.5%.

**Feature engineering.** Add new columns only when a hypothesis or the model
needs them, and add them in a small extra script (or at the end of
`01_prepare.py`) so they are repeatable. Useful patterns:

```python
df["tenure_band"] = pd.cut(df["tenure"], [0, 6, 12, 24, 48, 72], include_lowest=True)
df["charges_per_month_of_tenure"] = df["total_charges"] / df["tenure"].clip(lower=1)
df["services_count"] = (df[["online_security", "tech_support", "online_backup"]] == "yes").sum(axis=1)
# with dates:
df["signup_month"] = df["signup_date"].dt.to_period("M").astype(str)
df["days_since_last_order"] = (snapshot_date - df["last_order_date"]).dt.days
```

**Joining tables** (record-level projects with several tables): join step by
step and check the row count after each join. A row count that grows after a
"many-to-one" join means the key was not unique.

```python
before = len(orders)
orders = orders.merge(customers, on="customer_id", how="left", validate="many_to_one")
assert len(orders) == before, "join multiplied rows: check customer_id is unique in customers"
```

To get one row per customer from an event table, aggregate first:

```python
per_customer = (orders.groupby("customer_id")
                .agg(orders=("order_id", "nunique"), revenue=("amount", "sum"),
                     last_order=("order_date", "max"))
                .reset_index())
```

## 2.2 Power BI: Power Query steps

Do the light cleaning in Power Query too, so the dashboard and Python agree.
**Home → Transform data**, then for each table:

| Task | Where |
|---|---|
| See problems | **View** → Column quality / distribution / profile (switch profiling to *entire data set*) |
| Fix a type | Click the type icon in the column header → choose the type. Use **Using locale** for dates like 31/12/2024 |
| Trim spaces, fix case | **Transform → Format → Trim**, **Lowercase** or **Capitalize each word** |
| Disguised blanks | Right-click column → **Replace values** (e.g. replace " " with `null`) |
| Remove duplicates | Select the key column(s) → right-click → **Remove duplicates** (only after you have counted them) |
| Missing values | **Transform → Fill down**, or **Replace values** `null` → a value. Prefer flagging over filling for analysis |
| Group values | **Add column → Conditional column** (e.g. tenure bands) |
| Join tables | **Home → Merge queries** (Left outer) |
| Stack monthly files | **Home → Append queries**, or **Get data → Folder** to combine every file in a folder |

Each step appears under **Applied steps** on the right: rename them so the list
reads like a recipe ("Trimmed text", "Replaced blank charges"). That list is your
Power BI cleaning documentation.

## 2.3 Leakage starts here

**Leakage** is when a column contains information you would not have at the
moment you need the prediction, so the model "cheats". Look through every column
now and mark candidates in `LEAKAGE_COLS`:

- recorded after the outcome (cancellation reason, exit interview score, final balance)
- the outcome in disguise (status code, "days until churn")
- totals that grow over the period you predict (`total_charges` grows with
  tenure and stops when a customer leaves)

You will confirm the list in guide 5.

## 2.4 Done when

- [ ] `analysis_table.csv` exists and its row count is explained
- [ ] The quality log lists every change with counts
- [ ] Power Query steps are renamed and match the Python cleaning
- [ ] A first `LEAKAGE_COLS` list is written in `config.py`
- [ ] `04_data_preparation_plan.md` is updated with what you actually did
