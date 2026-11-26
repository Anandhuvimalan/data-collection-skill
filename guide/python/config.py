"""Project settings shared by every analysis script. Edit this file first.

Each script in this folder reads these settings, so you change your column
names once, here, instead of in every script.

Fill in the names exactly as they appear in your cleaned file
(after 01_prepare.py, column names are lower_snake_case).
"""
from pathlib import Path

# ---------------------------------------------------------------- files
PROJECT = Path(__file__).resolve().parents[2]   # the project folder: <project>/guide/python/config.py
RAW_TABLE = PROJECT / "data" / "processed" / "customers.csv"   # the main record-level table
CLEAN_TABLE = PROJECT / "data" / "processed" / "analysis_table.csv"  # written by 01_prepare.py
OUTPUTS = PROJECT / "outputs"                           # charts and result tables go here

# ---------------------------------------------------------------- columns
ID_COL = "customer_id"          # one unique value per row
TARGET = "churn"                # the outcome you want to explain and predict
POSITIVE = "yes"                # the value of TARGET that means "it happened" (after lower-casing)
DATE_COL = None                 # a date column, e.g. "signup_date"; None if the table has no dates
VALUE_COL = "monthly_charges"   # money per row (revenue, balance, salary...); None if there is none

# Columns that must NOT be used to predict the outcome, because they are only
# known after the outcome happened, or are the outcome in another form.
# Think about each one: see guide/05-predictive.md, "Leakage".
LEAKAGE_COLS = ["total_charges"]

# Columns to ignore everywhere (free text, duplicates of other columns, identifiers).
IGNORE_COLS = []

# Optional: a factor you suspect confounds others (diagnostic step 4), e.g. "tenure" or "contract".
CONTROL_COL = "tenure"

# ---------------------------------------------------------------- prescriptive assumptions
# Every number here is an ASSUMPTION. Write where each one comes from in your
# report (a company report, an industry study, or "placeholder agreed with supervisor").
ASSUMPTIONS = {
    #                      low     base     high
    "months_of_value_saved": (6,     12,      24),    # months of revenue kept if a leaver is retained
    "action_cost":           (10.0,  25.0,    50.0),  # cost of one retention action per customer
    "success_rate":          (0.10,  0.25,    0.40),  # share of targeted would-be leavers the action keeps
}
BUDGET = 20000.0                # total budget for actions in one cycle
CAPACITY = 1500                 # most customers the team can contact in one cycle

# ---------------------------------------------------------------- company x period tables
# Used by kpi_panel.py for single-company projects (one row per company per period).
PANEL_TABLE = PROJECT / "data" / "processed" / "kpi_by_company_year.csv"
PANEL_COMPANY = "company_id"
PANEL_PERIOD = "fiscal_year_end"
PANEL_KPI = "attrition_rate"            # the topic's KPI
PANEL_DRIVERS = ["revenue_growth", "employee_cost_per_head", "headcount_growth"]  # possible explanations
FOCAL_COMPANY = "infosys"

RANDOM_STATE = 42
