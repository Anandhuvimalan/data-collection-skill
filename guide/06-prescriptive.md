# 6. Prescriptive analytics - what should be done?

Goal: turn the findings into a decision the business can take, with its
expected value, the limits it must respect, how sensitive it is to your
assumptions, and how the business would prove it worked.

This is where most student projects fall back to generic advice ("improve
customer service", "offer discounts"). Avoid that by building a **decision
framework**.

## 6.1 The decision framework (write it first)

| Part | Question | Churn example |
|---|---|---|
| Decision | What exactly is chosen, for whom, how often? | which customers get a retention offer each month |
| Lever | What can the business change? | offer a discounted one-year contract |
| Objective | What is maximised or minimised? | expected revenue kept minus offer cost |
| Constraints | What limits apply? | budget 20,000 per month; team can contact 1,500 customers |
| Inputs from data | What comes from the analysis? | each customer's churn probability and monthly charges |
| Assumptions | What must be assumed? | months of revenue kept, offer cost, share of offers that work |
| Rule | How is the choice made? | act where expected net value > 0, best first, until budget or capacity runs out |
| Measurement | How will we know it worked? | randomised control group, churn rate after one cycle |

The lever should come from the diagnostic stage: the worked example found
contract type strongly associated with churn even within tenure bands, so a
contract-conversion offer is a lever the evidence supports.

## 6.2 Assumptions need sources and ranges

Public data rarely contains costs and response rates, so you will assume them.
That is fine if you are open about it:

| Assumption | Low | Base | High | Source |
|---|---|---|---|---|
| Months of revenue kept per saved customer | 6 | 12 | 24 | typical contract length; company report |
| Cost per offer | 10 | 25 | 50 | discount × months, plus contact cost |
| Success rate (share of would-be leavers kept) | 10% | 25% | 40% | industry study, or placeholder agreed with supervisor |

Write them in `ASSUMPTIONS` in `config.py`, with `BUDGET` and `CAPACITY`.

## 6.3 Python: run `05_prescriptive.py`

```bash
python 05_prescriptive.py
```

The core calculation, per customer:

```
expected benefit  = churn probability × success rate × months kept × monthly value
expected net value = expected benefit − cost of the action
```

Then it chooses who to act on by solving a small optimisation: maximise the
total expected net value, subject to the budget and the capacity (a 0/1
integer programme solved with `scipy.optimize.milp`). With the same cost for
everyone this equals "take the highest expected net value first until a limit
is hit"; the optimiser also handles different costs per customer or several
actions.

Outputs in `outputs/prescriptive/`:

| File | Use it for |
|---|---|
| `action_list.csv` | every record with expected net value and `act` / `no action` - the list the business would use |
| `strategy_comparison.csv` | model + optimisation vs simpler rules (top by risk, top by value, random). Proves the analysis adds value |
| `scenarios.csv` | low / base / high assumptions together |
| `sensitivity.csv` | one assumption at a time - which assumption the decision depends on most |
| `test_plan.json` | how many customers a randomised test needs to detect the expected effect |

Worked example (base assumptions): act on 800 customers, using the full budget
of 20,000, for an expected net benefit of about 172,000. Targeting the same
number by risk alone gave 159,000, by value alone 81,000, at random 54,000.
The result was most sensitive to the success rate and the months of value kept.
A test needs about 630 customers per group to detect a fall from 26.5% to 19.9%.
(These are illustrative numbers on a fictional dataset with assumed costs.)

**Other prescriptive methods**, when your decision is different:

| Decision | Method | Python |
|---|---|---|
| Act or not, per record | expected value (above) | the script |
| Several actions, several limits | linear / integer programming | `scipy.optimize.milp`, or `pulp` |
| How much stock to order | newsvendor / reorder point from the forecast and its error | `scipy.stats.norm.ppf(service_level)` |
| Which price or discount | demand response curve, then maximise margin | fit elasticity, then `scipy.optimize.minimize_scalar` |
| Where to set a threshold | cost matrix: cost of a miss vs cost of a false alarm | sweep thresholds, pick the lowest total cost |
| Company-level target | benchmark against peers + scenario model | guide 8 |

## 6.4 Power BI: the what-if page

Let managers change the assumptions themselves.

1. **Create parameters.** **Modeling → New parameter → Numeric range** for each
   assumption: `Success Rate` (0 to 1, increment 0.05, default 0.25),
   `Months Saved` (1 to 36, default 12), `Action Cost` (0 to 100, default 25),
   `Budget` (0 to 100000, increment 1000, default 20000). Tick **Add slicer to
   this page**. Each creates a table and a measure such as
   `[Success Rate Value]`.
2. **Measures** (scores related to customers as in guide 5):
   ```DAX
   Customers To Act =
   VAR Cost = [Action Cost Value]
   VAR MaxByBudget = INT ( DIVIDE ( [Budget Value], Cost ) )
   VAR Positive =
       FILTER (
           ADDCOLUMNS ( Scores, "@env",
               Scores[risk_probability] * [Success Rate Value] * [Months Saved Value]
                   * RELATED ( Customers[monthly_charges] ) - Cost ),
           [@env] > 0 )
   RETURN MIN ( COUNTROWS ( Positive ), MaxByBudget )

   Expected Net Benefit =
   VAR Cost = [Action Cost Value]
   VAR N = [Customers To Act]
   VAR Scored =
       ADDCOLUMNS ( Scores, "@env",
           Scores[risk_probability] * [Success Rate Value] * [Months Saved Value]
               * RELATED ( Customers[monthly_charges] ) - Cost )
   RETURN SUMX ( TOPN ( N, Scored, [@env], DESC ), [@env] )

   Spend = [Customers To Act] * [Action Cost Value]
   ```
   (`TOPN` can return a few extra rows when values tie; for a report that is
   fine.)
3. **Visuals:** the parameter slicers; cards for Customers To Act, Spend and
   Expected Net Benefit; a table of the scenarios from `scenarios.csv`; a bar
   chart of `sensitivity.csv` (change vs base, one bar per assumption and
   direction - a "tornado" chart); the action list as a table filtered to
   `act`.

Check that the Power BI result at base settings matches the Python base case
(it will, give or take ties, when capacity is not the binding limit; add
`MIN( ..., 1500)` for capacity if needed).

## 6.5 Recommendations that hold up

Write each recommendation in this shape:

> **Action:** offer a discounted one-year contract to the 800 month-to-month
> customers with the highest expected net value each month.
> **Why:** contract type remains strongly associated with churn within every
> tenure band (diagnostic H3); the model ranks these customers at 2.8× average risk.
> **Expected impact:** about X kept customers and Y net benefit per month
> (base case; range A to B across scenarios). **Cost:** Z.
> **Depends on:** the success rate - below N% the action does not pay.
> **How to measure:** hold back a random 50% of the list for one cycle and
> compare churn; about 630 customers per group are needed.
> **Risks:** discount cost for customers who would have stayed anyway.

**A caution to state:** a risk model says who is likely to leave, not who will
respond to an offer. Targeting by response needs experimental data; until then,
the success rate is an assumption, and the test plan is how you replace it with
evidence.

## 6.6 Done when

- [ ] Decision framework table complete
- [ ] Assumptions table with low/base/high and sources
- [ ] Recommended rule beats simple alternatives (strategy comparison)
- [ ] Scenarios and sensitivity reported; the critical assumption named
- [ ] Test plan with sample size
- [ ] What-if page in Power BI
