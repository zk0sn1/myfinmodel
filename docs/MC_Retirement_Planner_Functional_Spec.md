---
title: "Monte Carlo Retirement Planner — Functional Specification"
version: "v1.0"
date: "July 2026"
status: "Approved for Development"
audience: "Software Developers, Data Engineers"
scope: "Simulation engine, inputs, outputs — excludes deployment and infrastructure"
stack: "Python ≥ 3.11 · Streamlit ≥ 1.32 · NumPy ≥ 1.26 · Plotly ≥ 5.18 · Pandas ≥ 2.1"
---

# Monte Carlo Retirement Planner
Functional Specification — Software Development Reference

| Document Title | Monte Carlo Retirement Planner — Functional Specification |
| --- | --- |
| Document Type | Functional Specification |
| Version | v1.0 |
| Date | July 2026 |
| Status | APPROVED FOR DEVELOPMENT |
| Audience | Software Developers, Data Engineers |
| Classification | Confidential |
| Technology Stack | Python ≥ 3.11 · Streamlit ≥ 1.32 · NumPy ≥ 1.26 · Plotly ≥ 5.18 · Pandas ≥ 2.1 |
| Out of Scope | Deployment, infrastructure, authentication, general app scaffolding (covered in separate Deployment Specification) |

> **ℹ️ Scope Notice**

            This document specifies what the Monte Carlo Retirement Planner **calculates**, every required **input**, all **calculation rules and formulas**, and every **output, chart, and summary result**. It does not cover deployment, infrastructure, authentication, or general application scaffolding.

## Table of Contents
1. Overview
    1.1 Purpose
    1.2 Application Context
    1.3 Simulation Approach
    1.4 Key Design Principles
2. Inputs Tab Specification
    2.1 Tab Layout
    2.2 Input Sections and Parameters
    2.2.1 Portfolio Section
    2.2.2 Personal Information Section
    2.2.3 Spending Section
    2.2.4 Social Security Section
    2.2.5 Health Insurance Section
    2.2.6 Portfolio Style / Market Assumptions Section
    2.2.7 Guardrail Thresholds Section
    2.3 Input Validation Summary Table
    2.4 Scenario Management
3. Simulation Engine Specification
    3.1 Overview
    3.2 Random Draw Generation
    3.3 Per-Path, Per-Year Simulation Loop
    3.4 Spending Tier Lookup
    3.5 Guardrail Logic Specification
    3.6 Return Value Structure
    3.7 Performance Requirements
4. Results Tab Specification
    4.1 Tab Layout
    4.2 Summary Dashboard Metric Cards
    4.3 Success Metrics Table
    4.4 Percentile Fan Charts
    4.5 Detailed Results Tables (Downloadable)
    4.6 Scenario Comparison View
5. Calculation Rules Reference
6. Streamlit UI Component Mapping
    6.1 Inputs Tab Components
    6.2 Results Tab Components
    6.3 State Management
7. Error Handling and Edge Cases
8. Constants and Defaults Table
9. Future Enhancements (Out of Scope for V1)
10. Appendix
    A. Glossary of Terms
    B. Mathematical Notation Reference
    C. Streamlit Version Requirements
    D. File Structure Reference
---

         SECTION 1 — OVERVIEW

## Section 1 — Overview
### 1.1 Purpose
This document specifies the functional requirements for the Monte Carlo Retirement Planner module of the application. It defines all inputs the user must provide, the statistical simulation engine, the guardrail spending adjustment rules, and all output results and visualizations that must be displayed in the Streamlit UI.

This specification is intended for software developers and data engineers who will implement the application. All terminology, formulas, variable names, and constants in this document are normative and must be implemented as described unless a deviation is explicitly documented.

### 1.2 Application Context
The app is a Streamlit multi-tab web application. The retirement planning module is organized into two primary tabs:

- Inputs Tab:  All user-configurable parameters grouped into logical sections with inline validation.
- Results Tab:  All simulation outputs, summary statistics, charts, and data tables — computed on demand when the user submits the Inputs tab.

### 1.3 Simulation Approach
The app uses Monte Carlo simulation to model retirement portfolio outcomes across a configurable number of simulation paths (default 1,000; user-adjustable 100–10,000). Each path represents one possible sequence of portfolio returns and inflation rates drawn from a bivariate normal distribution spanning the full planning horizon. Results are presented as percentile distributions rather than single-point estimates, enabling the user to assess a range of plausible outcomes.

### 1.4 Key Design Principles
- All simulation is performed server-side in Python using NumPy; no simulation logic runs in the browser.
- Inputs and outputs are separated into distinct Streamlit tabs.
- All outputs are computed fresh on each simulation run; results are not persisted between sessions unless the user explicitly exports them.
- The random seed is user-configurable for reproducibility.
- No user-specific personal information (name, SSN, account numbers) is stored or transmitted by the application.
- Guardrail spending rules are applied deterministically each year within each simulation path, ensuring results are reproducible for the same seed and inputs.

---

         SECTION 2 — INPUTS TAB SPECIFICATION

## Section 2 — Inputs Tab Specification
### 2.1 Tab Layout
The Inputs tab is organized into collapsible sections using `st.expander` or grouped using `st.columns`. Each section has a clear heading. A "Run Simulation" button is fixed at the bottom of the Inputs tab or in a persistent sidebar. The tab renders sections in the following order: Portfolio → Personal Information → Spending → Social Security → Health Insurance → Portfolio Style / Market Assumptions → Guardrail Thresholds.

### 2.2 Input Sections and Parameters
### 2.2.1 Portfolio Section

| Parameter Name | Variable Name | Input Type | Default | Min | Max | Unit | Validation Rule | Description / Tooltip |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Starting Portfolio Value | port_start | Currency input | Required — no default | $10,000 | $50,000,000 | USD | Must be > 0; block run if absent | Total investable assets at retirement start |
| Taxable Account Value | taxable_value | Currency input | Derived | $0 | port_start | USD | Must be ≤ port_start ; sum check (see below) | Brokerage / taxable investment accounts |
| Tax-Deferred Account Value | tax_deferred_value | Currency input | Derived | $0 | port_start | USD | Sum check (see below) | Traditional IRA, 401k, 403b, etc. |
| Roth Account Value | roth_value | Currency input | Derived | $0 | port_start | USD | Sum check (see below) | Roth IRA, Roth 401k |
| Unrealized Gain % in Taxable Account | unrealized_gain_pct | Slider | 30% | 0% | 100% | Percent | — | Fraction of taxable account representing embedded capital gain |
| Long-Term Capital Gains Tax Rate | ltcg_rate | Dropdown | 15% | Options: 0%, 15%, 20%, 23.8% (incl. NIIT) | Percent | — | Federal LTCG rate applied to taxable account dispositions |
| Ordinary Income Tax Rate (marginal) | ord_income_rate | Dropdown | 22% | Options: 10%, 12%, 22%, 24%, 32%, 35%, 37% | Percent | — | Marginal rate applied to IRA/401k withdrawals |
⚠ Account Sum Validation`taxable_value + tax_deferred_value + roth_value` must equal `port_start` within $1 tolerance. Display an inline warning if the sum does not match. This validation does **not** block the simulation run — it is advisory only.

### 2.2.2 Personal Information Section

| Parameter Name | Variable Name | Input Type | Default | Min | Max | Unit | Validation Rule | Description / Tooltip |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Current Age | current_age | Integer input | Required | 18 | 85 | Years | Must be < planning_end_age ; block if absent | Client's age at simulation start |
| Retirement Start Age | retire_age | Integer input | current_age | current_age | 85 | Years | Must be ≥ current_age | Age at which portfolio withdrawals begin; can equal current_age if already retired |
| Social Security Start Age | ss_start_age | Slider | 67 | 62 | 70 | Years | Must be ≥ retire_age ; warn if equal | Age at which SS income begins: 62 = reduced benefit, 67 = FRA, 70 = maximum delayed benefit |
| Planning Horizon | plan_years | Integer input | 35 | 5 | 50 | Years | — | Number of years to simulate from retire_age |
| Filing Status | filing_status | Dropdown | Single | Options: Single, Married Filing Jointly | — | — | Affects tax brackets and ACA income thresholds |

### 2.2.3 Spending Section

The spending section supports multiple age-range spending tiers, allowing front-loading (higher early spending) or any user-defined pattern. This replaces a single flat spending number.

**Spending Tier Configuration**

The user defines 1 to 5 spending tiers. Each tier has the following fields:

| Field | Variable Name | Type | Min | Max | Unit | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Start Age | tier_N_start_age | Integer | current_age | 100 | Years | Must be sequential and non-overlapping across tiers |
| End Age | tier_N_end_age | Integer | tier_N_start_age + 1 | 100 | Years | Tiers must be contiguous without gaps |
| Annual Spending Amount | tier_N_spend | Currency | $0 | $2,000,000 | USD/yr (real) | Base spending in today's dollars for this age range |

Example tier structure for a front-loaded retirement strategy:

- Tier 1:  Ages  retire_age  to  ss_start_age - 1  → higher spending (active early retirement, no SS supplement)
- Tier 2:  Ages  ss_start_age  onward → lower spending (SS income supplements portfolio withdrawals)
- Additional tiers  for late-retirement phases as desired (e.g., reduced discretionary spending in advanced age)

"Add Tier" and "Remove Tier" buttons allow dynamic tier management. At least one tier is required. Tier ranges must be contiguous and cover the full span from `retire_age` to `retire_age + plan_years` without gaps or overlaps.

**Spending Floor and Ceiling**

| Parameter Name | Variable Name | Type | Min | Max | Unit | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Minimum Annual Spending Floor | spend_floor | Currency | $0 | spend_ceiling | USD/yr (real) | Guardrail cuts cannot reduce spending below this level |
| Maximum Annual Spending Ceiling | spend_ceiling | Currency | spend_floor | $2,000,000 | USD/yr (real) | Guardrail raises cannot increase spending above this level |

> **ℹ️ Floor and Ceiling — Real Dollar Convention**

        Floor and Ceiling are expressed in today's (real) dollars. They are multiplied by the simulated cumulative inflation index `cum_inf[p, y]` each year during enforcement to convert to the equivalent nominal dollars.

### 2.2.4 Social Security Section

| Parameter Name | Variable Name | Input Type | Default | Min | Max | Unit | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Enable Social Security | ss_enabled | Toggle | True | — | — | Boolean | If disabled, SS income = $0 for all years; all other SS fields are hidden |
| Annual SS Benefit at Claiming Age | ss_annual | Currency | Required if SS enabled | $0 | $60,000 | USD/yr | Gross SS benefit in today's dollars at the user's selected claiming age |
| SS COLA Rate | ss_cola | Slider | 2.5% | 0% | 5% | Percent/yr | Annual cost-of-living adjustment applied to SS benefit after claiming begins |

> **ℹ️ SS Income Calculation Note**

        SS income in year `y` for path `p`:
`ss_income[y] = ss_annual × (1 + ss_cola)^(age[y] - ss_start_age)` for all years where `age[y] >= ss_start_age`, and 0 otherwise.

        SS income is treated as nominal dollars that grow at COLA. It is **NOT** additionally inflation-adjusted by the portfolio cumulative inflation index. The COLA rate substitutes for general inflation adjustment on SS income.

### 2.2.5 Health Insurance Section

| Parameter Name | Variable Name | Input Type | Default | Min | Max | Unit | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Medicare Start Age | medicare_age | Integer | 65 | 60 | 70 | Years | Age at which Medicare replaces marketplace/private insurance |
| Annual Medicare Premium | medicare_premium | Currency | $3,600 | $0 | $20,000 | USD/yr | Combined Part B + Part D annual premium in today's dollars; inflation-adjusted in simulation |
| Enable ACA MAGI Guardrail | aca_guardrail_enabled | Toggle | True | — | — | Boolean | When disabled, hides all ACA-related fields |
| ACA MAGI Hard Cliff | aca_magi_cliff | Currency | $62,000 | $20,000 | $200,000 | USD/yr | Only shown if ACA enabled. Income threshold above which all premium tax credits are lost (400% FPL). User must enter current-year value. |
| ACA Safe Target MAGI | aca_magi_target | Currency | $58,000 | $0 | aca_magi_cliff | USD/yr | Must be < aca_magi_cliff . Target MAGI for full subsidy preservation. |
| Annual Premium if Over Cliff | aca_premium_over | Currency | $18,000 | $0 | $60,000 | USD/yr | Full unsubsidized annual premium cost when MAGI exceeds cliff |
| Annual Premium if Under Cliff | aca_premium_under | Currency | $4,800 | $0 | aca_premium_over | USD/yr | Must be ≤ aca_premium_over . Subsidized annual premium cost. |

### 2.2.6 Portfolio Style / Market Assumptions Section

This section allows the user to choose a portfolio style preset OR manually enter return and volatility assumptions. Selecting a preset auto-populates the return/volatility sliders, which remain editable after selection.

**Portfolio Style Presets**

| Style Label | Expected Annual Return (Mean) | Annual Return Std Dev | Description |
| --- | --- | --- | --- |
| Conservative (Capital Preservation) | 4.5% | 7.0% | Mostly bonds/fixed income; low growth, low risk |
| Moderate (Balanced) | 5.5% | 9.5% | 40/60 to 50/50 equity/bond blend |
| Growth (Balanced Growth) | 6.5% | 12.0% | 60/40 equity/bond; classic retirement allocation |
| Aggressive Growth | 8.0% | 15.0% | 80%+ equity; higher upside, higher sequence-of-returns risk |
| Equity Only | 9.5% | 18.0% | 100% equities; maximum long-run growth, maximum volatility |
| Custom | (user-defined) | (user-defined) | User enters both values manually via sliders |

When a style is selected, display a brief description beneath the dropdown and the note: *"These are long-run historical approximations. Actual future returns may differ materially."*

**Market Parameter Inputs** (always visible; pre-filled by preset)

| Parameter Name | Variable Name | Input Type | Default | Min | Max | Unit | Validation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Expected Annual Portfolio Return (Mean) | ret_mean | Slider | From preset | 1% | 15% | Percent/yr | — |
| Annual Return Standard Deviation | ret_std | Slider | From preset | 1% | 30% | Percent/yr | Must be > 0 |
| Return–Inflation Correlation | ret_inf_corr | Slider | 0.10 | -0.50 | 0.80 | — | Must satisfy \|ρ\| < 1; covariance matrix must be positive semi-definite |
| Inflation Mean | inf_mean | Slider | 3.0% | 0% | 10% | Percent/yr | — |
| Inflation Standard Deviation | inf_std | Slider | 1.5% | 0% | 5% | Percent/yr | — |
| Inflation Floor | inf_floor | Slider | 1.0% | 0% | inf_mean | Percent/yr | Must be ≤ inf_mean ; warn if floor > mean. Set to 0% to allow full distribution including deflation scenarios. |
| Number of Simulation Paths | n_paths | Slider | 1,000 | 100 | 10,000 | Integer | Higher values increase accuracy but increase compute time; warn at 10,000 paths |
| Random Seed | random_seed | Integer input | 42 | 0 | 999,999 | Integer | Fix seed for reproducibility; changing seed produces alternative random draws |

### 2.2.7 Guardrail Thresholds Section

Guardrails are dynamic rules that adjust spending each year in response to portfolio or withdrawal rate conditions. The user may enable or disable each guardrail independently via toggle controls. Sub-parameters are hidden when the parent guardrail is disabled.

**Guardrail 1 — Portfolio Value Guardrail (GR1)**

| Parameter Name | Variable Name | Type | Default | Min | Max | Unit | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Enable GR1 | gr1_enabled | Toggle | True | — | — | Boolean | — |
| Portfolio Floor (% of starting portfolio) | gr1_floor_pct | Slider | 50% | 10% | 90% | Percent | Converts to gr1_floor = port_start × gr1_floor_pct . If portfolio falls below this, cut spending by GR1 step. |
| Portfolio Ceiling (% of starting portfolio) | gr1_ceil_pct | Slider | 150% | 110% | 300% | Percent | Converts to gr1_ceil = port_start × gr1_ceil_pct . If portfolio rises above this, raise spending by GR1 step. |
| Spending Cut Amount (GR1 floor breach) | gr1_cut_pct | Slider | 10% | 5% | 30% | Percent | Multiplicative reduction applied to current spending when floor is breached |
| Spending Raise Amount (GR1 ceiling breach) | gr1_raise_pct | Slider | 10% | 5% | 30% | Percent | Multiplicative increase applied to current spending when ceiling is breached |

**Guardrail 2 — Withdrawal Rate Guardrail (GR2)**

| Parameter Name | Variable Name | Type | Default | Min | Max | Unit | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Enable GR2 | gr2_enabled | Toggle | True | — | — | Boolean | — |
| Low Withdrawal Rate | gr2_low_rate | Slider | 3.0% | 1.0% | gr2_warn_rate | Percent | Must be < gr2_warn_rate . Triggers a modest spending raise. |
| Warning Withdrawal Rate | gr2_warn_rate | Slider | 5.0% | 3.0% | 8.0% | Percent | Must be < gr2_crit_rate . Triggers a modest spending cut. |
| Critical Withdrawal Rate | gr2_crit_rate | Slider | 6.5% | gr2_warn_rate | 12.0% | Percent | Must be > gr2_warn_rate . Triggers a larger spending cut. |
| Low Raise Amount | gr2_low_raise | Slider | 5% | 2% | 20% | Percent | Multiplicative raise when WR is in low zone (below gr2_low_rate ) |
| Warning Cut Amount | gr2_warn_cut | Slider | 5% | 2% | 20% | Percent | Multiplicative cut when WR is in warning zone |
| Critical Cut Amount | gr2_crit_cut | Slider | 15% | 5% | 40% | Percent | Multiplicative cut when WR is in critical zone |

**Guardrail 3 — ACA MAGI Guardrail (GR3)** Conditional

Shown only when `aca_guardrail_enabled = True`. When enabled, the simulation tracks estimated MAGI each year for ages `retire_age` through `medicare_age - 1`. If projected MAGI would exceed `aca_magi_cliff`, the simulation re-routes withdrawals away from taxable/IRA sources toward Roth to suppress MAGI. If the cliff breach is unavoidable, the higher premium (`aca_premium_over`) is applied; otherwise the lower premium (`aca_premium_under`) applies.

| Parameter | Variable | Type | Default | Notes |
| --- | --- | --- | --- | --- |
| Enable GR3 | gr3_enabled | Toggle | True | Toggle off if client does not qualify for ACA subsidies |

**Guardrail 4 — Inflation Guardrail (GR4)**

| Parameter Name | Variable Name | Type | Default | Min | Max | Unit | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Enable GR4 | gr4_enabled | Toggle | True | — | — | Boolean | — |
| Inflation Trigger Rate | gr4_inf_trigger | Slider | 4.5% | 2.0% | 10.0% | Percent | Must be > inf_mean . If simulated annual inflation exceeds this, apply discretionary spending cut. |
| Inflation Cut Amount | gr4_cut_pct | Slider | 5% | 2% | 20% | Percent | Multiplicative cut when inflation exceeds trigger rate |

### 2.3 Input Validation Summary Table
| Input / Rule | Validation Rule | Error / Warning Message | Behavior |
| --- | --- | --- | --- |
| port_start | Must be > 0 and provided | "Starting portfolio value is required and must be greater than $0." | BLOCK RUN |
| Account sum | taxable + tax_deferred + roth must equal port_start ± $1 | "Account values do not sum to starting portfolio. Difference: $[X]. Simulation will proceed with stated totals." | WARN ONLY |
| Spending tier coverage | Tiers must cover full plan horizon from retire_age to retire_age + plan_years without gaps or overlaps | "No spending tier covers ages [X] to [Y]. Add a tier or extend an existing tier." | BLOCK RUN |
| Floor / Ceiling ordering | spend_floor < spend_ceiling | "Spending floor must be less than spending ceiling." | BLOCK RUN |
| SS start age | ss_start_age should be > retire_age when SS enabled | "Social Security start age equals retirement age. SS income begins immediately in Year 1." | WARN ONLY |
| GR2 rate ordering | gr2_low_rate < gr2_warn_rate < gr2_crit_rate | "Withdrawal rate thresholds are out of order. Low rate must be less than Warning rate, which must be less than Critical rate." | BLOCK RUN |
| Memory guard | n_paths × plan_years must not exceed 500,000 total cell-years | "Large simulation requested (≥ 10,000 paths). This may be slow. Proceed?" | WARN ONLY |
| Inflation floor | inf_floor must be ≤ inf_mean | "Inflation floor exceeds inflation mean. Most draws will be clipped; distribution will be artificially compressed." | WARN ONLY |
| ACA ordering | aca_magi_target < aca_magi_cliff | "ACA safe target must be less than ACA cliff." | BLOCK RUN |
| Covariance matrix | \|ret_inf_corr\| < 1; ret_std > 0; inf_std > 0 | "Covariance matrix is not positive semi-definite. Adjust the return–inflation correlation." | BLOCK RUN |

### 2.4 Scenario Management
- The user may save the current input state as a named scenario using a text field + "Save Scenario" button.
- Up to 5 scenarios may be stored in  st.session_state  during a session.
- A "Load Scenario" dropdown lets the user restore any saved scenario's inputs.
- A "Compare Scenarios" view (described in Section 4.6) overlays key summary metrics across all saved scenarios.
- Scenarios are  not  persisted to disk between sessions unless an export feature is implemented in a future version.
- Each saved scenario stores both the input dict and the most recent result dict for that scenario.

---

         SECTION 3 — SIMULATION ENGINE SPECIFICATION

## Section 3 — Simulation Engine Specification
### 3.1 Overview
The simulation engine is a Python function that accepts all validated inputs, generates `n_paths × plan_years` random draws, and returns a structured result dictionary. It must be deterministic for a given seed and set of inputs. The engine resides in a dedicated module (`simulation.py`) separate from the Streamlit UI layer.

### 3.2 Random Draw Generation
Returns and inflation are drawn jointly from a bivariate normal distribution parameterized by the user's market assumptions, with correlation controlled by `ret_inf_corr`:

```

# Covariance matrix from correlated bivariate normal
cov = [
    [ret_std**2,                              ret_inf_corr * ret_std * inf_std],
    [ret_inf_corr * ret_std * inf_std,        inf_std**2]
]
means = [ret_mean, inf_mean]

np.random.seed(random_seed)
draws = np.random.multivariate_normal(means, cov, size=(n_paths, plan_years))

ret_draws = draws[:, :, 0]                           # shape: (n_paths, plan_years)
inf_draws = np.clip(draws[:, :, 1], inf_floor, None) # apply floor; shape: (n_paths, plan_years)
```
⚠ Covariance Matrix Validity
        The covariance matrix must be positive semi-definite. Validate that `|ret_inf_corr| < 1`, `ret_std > 0`, and `inf_std > 0` before constructing the matrix. Raise a validation error and block the simulation if these conditions are not met.

### 3.3 Per-Path, Per-Year Simulation Loop
For each path `p` in `range(n_paths)` and each year `y` in `range(plan_years)`, execute the following eight steps in order:

**Step 1 — Age and Period Setup**

```

age      = retire_age + y
ret      = ret_draws[p, y]
inf      = inf_draws[p, y]
cum_inf  = cumulative product of (1 + inf_draws[p, 0 : y+1])  # compounded from year 0
```

**Step 2 — Social Security Income**

```

if ss_enabled and age >= ss_start_age:
    years_since_ss = age - ss_start_age
    ss_income = ss_annual * (1 + ss_cola) ** years_since_ss
    # SS income grows at COLA only — NOT multiplied by cum_inf
else:
    ss_income = 0.0

```

**Step 3 — Medicare / Health Insurance Cost**

```

if age >= medicare_age:
    health_cost = medicare_premium * cum_inf   # inflation-adjusted nominal
elif aca_guardrail_enabled and gr3_enabled:
    health_cost = computed by GR3 logic (see Section 3.5)
else:
    health_cost = 0.0   # embed health costs in spending tiers
```

**Step 4 — Base Spending (from Spending Tiers)**

```

base_spend_real = get_base_spend(age, tiers)  # lookup real-dollar amount from tier
base_spend      = base_spend_real * cum_inf   # convert real to nominal using sim inflation path
spend           = base_spend                  # guardrails may modify this value in Step 5
```

**Step 5 — Apply Guardrails (in order)**

Apply guardrails sequentially: GR1 → GR2 → GR3 → GR4. Only the first guardrail that fires is logged as the primary event code. Subsequent guardrails may still adjust spending but do not overwrite the primary event code. After all guardrails, enforce floor/ceiling clamp unconditionally. Full logic is specified in Section 3.5.

**Step 6 — Withdrawal Calculation**

```

net_withdrawal = max(0.0, spend - ss_income)

# Gross up for taxes using blended effective rate
# More precise: weight by account source (Roth=0%, taxable=ltcg_rate, IRA=ord_income_rate)
roth_fraction    = roth_value / port_start      # static approximation
taxable_fraction = taxable_value / port_start
ira_fraction     = tax_deferred_value / port_start
effective_rate   = (roth_fraction * 0.0
                    + taxable_fraction * ltcg_rate
                    + ira_fraction * ord_income_rate)

if net_withdrawal > 0:
    gross_withdrawal = net_withdrawal / (1 - effective_rate)
else:
    gross_withdrawal = 0.0

```

**Step 7 — Portfolio Update**

```

portfolio_start = portfolio       # value at start of this year (before deduction)
# Deduct gross withdrawal and health cost, then apply return
# Cap gross_withdrawal at portfolio_start to avoid negative values
gross_withdrawal = min(gross_withdrawal, portfolio_start)
portfolio = max(0.0, portfolio_start - gross_withdrawal - health_cost) * (1 + ret)

# Once zero (ruin state), portfolio stays at zero for all subsequent years
```

**Step 8 — Store Results**

```

portfolio_arr[p, y]  = portfolio           # end-of-year nominal value
real_port_arr[p, y]  = portfolio / cum_inf # inflation-adjusted value
spend_arr[p, y]      = spend               # guardrail-adjusted nominal spending
real_spend_arr[p, y] = spend / cum_inf     # real spending
gross_wd_arr[p, y]   = gross_withdrawal
net_wd_arr[p, y]     = net_withdrawal
wr_arr[p, y]         = (gross_withdrawal / portfolio_start
                        if portfolio_start > 0 else 0.0)
cum_inf_arr[p, y]    = cum_inf
ss_arr[p, y]         = ss_income
health_arr[p, y]     = health_cost
event_arr[p, y]      = event               # guardrail event code string
```

### 3.4 Spending Tier Lookup
```

def get_base_spend(age: int, tiers: list) -> float:
    for tier in tiers:
        if tier.start_age <= data-id="1071" age <= tier.end_age:
            return tier.annual_spend
    raise ValueError(f"No tier covers age {age}. Validate tier coverage before simulation.")

```

Tiers must be validated at input time to be contiguous and fully cover the plan horizon. The `ValueError` is a defensive guard; it should not be reachable if validation passes.

### 3.5 Guardrail Logic Specification
Apply guardrails in order GR1 → GR2 → GR3 → GR4 each year. Initialize `event = "NONE"` at the start of each year-path cell before applying any guardrail.

**GR1 — Portfolio Value Guardrail** (if `gr1_enabled`):

```

gr1_floor = port_start * gr1_floor_pct
gr1_ceil  = port_start * gr1_ceil_pct

if portfolio_start < gr1_floor:
    spend *= (1 - gr1_cut_pct)
    event  = "PV-DOWN"
elif portfolio_start > gr1_ceil:
    spend *= (1 + gr1_raise_pct)
    event  = "PV-UP"

```

**GR2 — Withdrawal Rate Guardrail** (if `gr2_enabled`):

```

est_wr = (max(0.0, spend - ss_income) / portfolio_start
          if portfolio_start > 0 else 1.0)

if est_wr >= gr2_crit_rate:
    spend *= (1 - gr2_crit_cut)
    if event == "NONE":
        event = "WR-CRIT"
elif est_wr >= gr2_warn_rate:
    spend *= (1 - gr2_warn_cut)
    if event == "NONE":
        event = "WR-WARN"
elif est_wr < gr2_low_rate:
    spend *= (1 + gr2_low_raise)
    if event == "NONE":
        event = "WR-LOW"

```

**GR3 — ACA MAGI Guardrail** (if `gr3_enabled and aca_guardrail_enabled and retire_age <= age < medicare_age`):

```

# Simplified MAGI estimate — see note below
roth_fraction     = roth_value / port_start   # static approximation
estimated_magi    = (net_withdrawal * (1 - roth_fraction))

if estimated_magi > aca_magi_cliff:
    health_cost = aca_premium_over * cum_inf
    if event == "NONE":
        event = "ACA-BREACH"
else:
    health_cost = aca_premium_under * cum_inf

```

> **ℹ️ MAGI Simplification Notice**

        The MAGI estimation in this model is a simplified heuristic. A complete MAGI calculation requires tracking basis, Roth conversion amounts, dividend income, and realized gains — beyond the scope of V1. This simplification must be disclosed in the UI with a tooltip on the GR3 toggle and in the results output near ACA-BREACH statistics.

**GR4 — Inflation Guardrail** (if `gr4_enabled`):

```

if inf > gr4_inf_trigger:
    spend *= (1 - gr4_cut_pct)
    if event == "NONE":
        event = "INF"

```

**Floor / Ceiling Enforcement** (always applied, after all guardrails):

```

spend = max(spend_floor * cum_inf,
            min(spend_ceiling * cum_inf, spend))

```

**Guardrail Event Code Reference**

| Code | Guardrail | Trigger Condition | Spending Effect |
| --- | --- | --- | --- |
| NONE | — | No guardrail triggered this year | No change (subject only to floor/ceiling clamp) |
| PV-DOWN | GR1 | Portfolio < gr1_floor | Cut by gr1_cut_pct |
| PV-UP | GR1 | Portfolio > gr1_ceil | Raise by gr1_raise_pct |
| WR-WARN | GR2 | WR ∈ [ gr2_warn_rate , gr2_crit_rate ) | Cut by gr2_warn_cut |
| WR-CRIT | GR2 | WR ≥ gr2_crit_rate | Cut by gr2_crit_cut |
| WR-LOW | GR2 | WR < gr2_low_rate | Raise by gr2_low_raise |
| ACA-BREACH | GR3 | Estimated MAGI > aca_magi_cliff | Higher health premium applied ( aca_premium_over ) |
| INF | GR4 | Simulated inflation > gr4_inf_trigger | Cut by gr4_cut_pct |

### 3.6 Return Value Structure
The simulation function returns a single dictionary with the following structure and types. All array shapes are `(n_paths, plan_years)` unless noted.

```

results = {
    # Core arrays — shape: (n_paths, plan_years)
    "portfolio":      np.ndarray,   # nominal portfolio value, end-of-year
    "real_portfolio": np.ndarray,   # inflation-adjusted portfolio value
    "spend":          np.ndarray,   # guardrail-adjusted nominal spending
    "real_spend":     np.ndarray,   # inflation-adjusted spending
    "gross_wd":       np.ndarray,   # gross withdrawal (tax-grossed)
    "net_wd":         np.ndarray,   # net withdrawal (pre-gross-up)
    "wr":             np.ndarray,   # withdrawal rate (gross_wd / portfolio_start)
    "cum_inf":        np.ndarray,   # cumulative inflation index
    "ss_income":      np.ndarray,   # Social Security income (nominal, COLA-adjusted)
    "health_cost":    np.ndarray,   # health insurance cost
    "events":         np.ndarray,   # guardrail event codes (dtype=object / str)
    "ret_draws":      np.ndarray,   # raw return draws used
    "inf_draws":      np.ndarray,   # inflation draws (post inf_floor clipping)

    # Metadata
    "ages":           list[int],    # [retire_age, ..., retire_age + plan_years - 1]
    "n_paths":        int,
    "plan_years":     int,
    "inputs":         dict,         # deep copy of all validated inputs for this run
}

```

### 3.7 Performance Requirements
- Simulation must complete in under 5 seconds for  n_paths ≤ 1,000  and  plan_years ≤ 35  on a standard cloud instance.
- Use vectorized NumPy operations wherever possible; avoid Python-level loops over paths.
- The per-year guardrail logic requires a Python loop over years (state-dependent), but the inner path dimension must be vectorized across all  n_paths  simultaneously.

Recommended vectorized loop pattern:

```

for y in range(plan_years):
    # All operations act on vectors of shape (n_paths,)
    spend_vec = np.where(
        portfolio_vec < gr1_floor,
        spend_vec * (1 - gr1_cut_pct),
        spend_vec
    )
    # ... additional guardrail np.where calls ...
    spend_vec = np.clip(spend_vec,
                        spend_floor * cum_inf_vec,
                        spend_ceiling * cum_inf_vec)

```

---

         SECTION 4 — RESULTS TAB SPECIFICATION

## Section 4 — Results Tab Specification
### 4.1 Tab Layout
The Results tab renders the following elements in order from top to bottom:

1. Run Status / Metadata Row:  Displays  n_paths ,  plan_years , runtime in seconds, seed, and a "Re-run" button.
2. Summary Dashboard Panel:  Compact color-coded metric cards across the top row(s).
3. Tabbed sub-sections  using  st.tabs :
  - Success Metrics
  - Portfolio Fan Chart
  - Spending Fan Chart
  - Guardrail Analysis
  - Inflation Analysis
  - Tax Efficiency
  - Raw Data Tables

### 4.2 Summary Dashboard Metric Cards
Display as a horizontal row of `st.metric` cards or styled `st.columns` blocks. Include delta comparisons when a second scenario is loaded for comparison.

| Card Label | Computation | Color Coding / Notes |
| --- | --- | --- |
| 35-Year Survival Rate | np.mean(portfolio[:, -1] > 0) | Green ≥ 85%; Yellow 70–85%; Red < 70% |
| Median Final Portfolio | np.median(portfolio[:, -1]) | Nominal dollars |
| 10th Pct Final Portfolio | np.percentile(portfolio[:, -1], 10) | Adverse scenario indicator |
| 90th Pct Final Portfolio | np.percentile(portfolio[:, -1], 90) | Favorable scenario indicator |
| Avg Annual Spending | np.mean(spend[portfolio > 0]) | Mean across surviving path-years only |
| Median Withdrawal Rate | np.median(wr[wr > 0]) | Excludes depleted-year entries |
| Active Guardrails | Count of enabled guardrails (GR1–GR4) | Badge display (e.g., "3 of 4 enabled") |
| Inflation Floor | inf_floor input value | Reminder of key model assumption |

### 4.3 Success Metrics Table
A full-width, non-editable `st.dataframe` with formatted columns. All required rows are listed below by category.

**Portfolio Outcomes**

| Metric | Computation |
| --- | --- |
| Survival Rate (% of paths surviving to final year) | np.mean(portfolio[:, -1] > 0) × 100 |
| Number of Paths Depleted | np.sum(portfolio[:, -1] == 0) |
| Median Portfolio at Final Year (nominal) | np.median(portfolio[:, -1]) |
| Median Portfolio at Final Year (real) | np.median(real_portfolio[:, -1]) |
| 10th Percentile Portfolio at Final Year | np.percentile(portfolio[:, -1], 10) |
| 25th Percentile Portfolio at Final Year | np.percentile(portfolio[:, -1], 25) |
| 75th Percentile Portfolio at Final Year | np.percentile(portfolio[:, -1], 75) |
| 90th Percentile Portfolio at Final Year | np.percentile(portfolio[:, -1], 90) |
| Median Year of Depletion (among failing paths; expressed as age) | See Section 5.6; report as retire_age + median_depletion_year |
| Median Peak Portfolio Value (across all years, then median across paths) | np.median(np.max(portfolio, axis=1)) |
| Median Age of Peak Portfolio Value | retire_age + np.median(np.argmax(portfolio, axis=1)) |
| Maximum Portfolio Value Observed (any path, any year) | np.max(portfolio) |

**Spending Outcomes**

| Metric | Computation |
| --- | --- |
| Average Annual Spending — All Path-Years (nominal) | np.mean(spend) |
| Average Annual Spending — Surviving Path-Years Only (nominal) | np.mean(spend[portfolio > 0]) |
| Average Annual Spending — Surviving Path-Years (real) | np.mean(real_spend[portfolio > 0]) |
| Median Year-1 Spending (nominal) | np.median(spend[:, 0]) |
| Median Year-10 Spending (nominal and real) | np.median(spend[:, 9]) and np.median(real_spend[:, 9]) |
| Median Year-20 Spending (nominal and real) | np.median(spend[:, 19]) and np.median(real_spend[:, 19]) |

**Guardrail Trigger Frequencies**

| Metric | Computation |
| --- | --- |
| % of paths triggering GR1 PV-DOWN at least once | np.mean(np.any(events == "PV-DOWN", axis=1)) × 100 |
| % of paths triggering GR1 PV-UP at least once | np.mean(np.any(events == "PV-UP", axis=1)) × 100 |
| % of paths triggering GR2 WR-WARN at least once | np.mean(np.any(events == "WR-WARN", axis=1)) × 100 |
| % of paths triggering GR2 WR-CRIT at least once | np.mean(np.any(events == "WR-CRIT", axis=1)) × 100 |
| % of paths triggering GR2 WR-LOW at least once | np.mean(np.any(events == "WR-LOW", axis=1)) × 100 |
| % of paths triggering GR3 ACA-BREACH at least once (if enabled) | np.mean(np.any(events == "ACA-BREACH", axis=1)) × 100 |
| % of paths triggering GR4 INF at least once | np.mean(np.any(events == "INF", axis=1)) × 100 |
| % of paths never triggering any guardrail | np.mean(np.all(events == "NONE", axis=1)) × 100 |

**Withdrawal Rate Statistics**

| Metric | Computation |
| --- | --- |
| Median WR across all surviving path-years | np.median(wr[portfolio > 0]) |
| Average WR (surviving path-years) | np.mean(wr[portfolio > 0]) |
| 90th percentile WR (median across years of annual 90th percentile) | np.median(np.percentile(wr, 90, axis=0)) |
| % of path-years where WR > 5% | np.mean(wr > 0.05) × 100 |
| % of path-years where WR > 6.5% | np.mean(wr > 0.065) × 100 |

### 4.4 Percentile Fan Charts
All charts implemented using Plotly (`plotly.graph_objects` or `plotly.express`) rendered via `st.plotly_chart(fig, use_container_width=True)`.

**Chart 1 — Portfolio Value Fan Chart**

- Title:  "Portfolio Value by Age — Percentile Fan ( n_paths  paths)"
- X-axis:  Age ( retire_age  to  retire_age + plan_years - 1 ), labeled as integers
- Y-axis:  Portfolio Value (nominal $), formatted as "$X.XM" or "$X,XXX,XXX"
- Series:  10th (red), 25th (orange), 50th median — thicker line (green), 75th (blue), 90th (purple)
- Shaded band:  Between 10th and 90th using Plotly  fill='tonexty' , semi-transparent
- Annotations:  Vertical dashed line at  ss_start_age  labeled "SS Begins"; vertical dashed line at  medicare_age  labeled "Medicare"
- Hover:  Show age and all 5 percentile values on hover
- Legend:  Top-right position
- Toggle:   st.radio  above the chart to switch between nominal and real (inflation-adjusted) view

Computed as: `pcts = np.percentile(portfolio, [10, 25, 50, 75, 90], axis=0)` → shape `(5, plan_years)`

**Chart 2 — Annual Spending Fan Chart**

- Title:  "Annual Spending by Age — Guardrail-Adjusted ( n_paths  paths)"
- Same 5-percentile structure  as Chart 1, using  spend  array
- Horizontal dashed lines:  at  spend_floor  and  spend_ceiling  (real, scaled by median  cum_inf  for each year)
- Annotations:  SS start age and Medicare age vertical lines
- Toggle:  nominal vs. real spending via  st.radio

**Chart 3 — Guardrail Event Frequency (Stacked Bar Chart)**

- Title:  "Guardrail Events by Age (count of paths triggered out of  n_paths )"
- X-axis:  Age;  Y-axis:  Count (0 to  n_paths )
- Stacked bars:  PV-DOWN (red), PV-UP (green), WR-WARN (orange), WR-CRIT (crimson), WR-LOW (teal), ACA-BREACH (purple, if GR3 enabled), INF (amber), NONE (light gray — toggleable)
- Hover:  Exact count and % of paths for each segment at that age
- Computed as:  np.sum(events[:, y] == code)  for each event code and each year  y

**Chart 4 — Survival Rate Donut Chart**

- Title:  "Portfolio Survival Rate at Year  [plan_years]  (Age  [retire_age + plan_years - 1] )"
- Two segments:  Survived (green) and Depleted (red)
- Center annotation:  Survival percentage displayed in center of donut
- Note:  "Based on  n_paths  simulation paths"

**Chart 5 — Withdrawal Rate Over Time**

- Title:  "Withdrawal Rate by Age — Distribution Across Paths"
- X-axis:  Age;  Y-axis:  Withdrawal Rate (%), range 0–15% with outlier clipping
- Display:  Box plots (median, IQR, whiskers) at each age OR fan chart; selectable via  st.radio  above the chart
- Horizontal reference lines:  4.0% (common safe rate benchmark), 5.0% (GR2 warning threshold), 6.5% (GR2 critical threshold)

**Chart 6 — Inflation Path Distribution**

- Title:  "Simulated Annual Inflation Rates — Distribution by Age"
- X-axis:  Age;  Y-axis:  Inflation Rate (%)
- Fan chart:  10th / 50th / 90th percentile inflation paths
- Horizontal reference lines:   inf_floor  (labeled "Inflation Floor"),  inf_mean  (labeled "Mean Assumption"),  gr4_inf_trigger  (labeled "GR4 Trigger")
- Note when  inf_floor > 0 :  "Inflation draws clipped at [ inf_floor ]% — deflation scenarios excluded"

### 4.5 Detailed Results Tables (Downloadable)
Each table rendered in `st.dataframe` with a `st.download_button` for CSV export.

| Table | Columns | Rows | Computation |
| --- | --- | --- | --- |
| Table 1 — Percentile Portfolio Paths | Age \| Year \| 10th Pct \| 25th Pct \| Median \| 75th Pct \| 90th Pct (nominal $) | One per plan year | np.percentile(portfolio, [10,25,50,75,90], axis=0).T |
| Table 2 — Percentile Spending Paths | Age \| Year \| 10th Pct \| 25th Pct \| Median \| 75th Pct \| 90th Pct \| Median Real | One per plan year | Same structure using spend ; add real median column |
| Table 3 — Guardrail Event Frequency | Age \| PV-DOWN \| PV-UP \| WR-WARN \| WR-CRIT \| WR-LOW \| ACA-BREACH \| INF \| NONE | One per plan year | np.sum(events[:, y] == code) for each code and year y |
| Table 4 — Inflation Statistics | Age \| Year \| Min Inf \| 10th Pct Inf \| Median Inf \| 90th Pct Inf \| Max Inf \| Median Cum. Inflation Index | One per plan year | Computed from inf_draws and cum_inf arrays |
| Table 5 — Full Path Data Export (on-demand) | Path \| Age \| Portfolio \| Spending \| WR \| SS Income \| Health Cost \| Event Code \| Cum. Inflation \| Real Portfolio | One per path × year | Full n_paths × plan_years matrix; large for high n_paths — show size warning before generating |

### 4.6 Scenario Comparison View
Available when 2 or more scenarios are saved in session state. Accessible via a "Compare Scenarios" button or tab.

- Side-by-side metrics table:  Columns — Metric | Scenario A | Scenario B | ... | Delta (A→B). Rows include all metrics from Section 4.3 plus key input differences (portfolio style, spending tiers, guardrails enabled,  inf_floor ).
- Overlaid median fan chart:  Two scenarios' 50th percentile portfolio paths plotted on the same chart for visual comparison, with distinct colors and a legend identifying each scenario by name.

---

         SECTION 5 — CALCULATION RULES REFERENCE

## Section 5 — Calculation Rules Reference
This section is a condensed normative reference for developers implementing the mathematical core.

| Rule | Formula / Definition |
| --- | --- |
| 5.1 Bivariate Normal Draw | draws ~ MVN([ret_mean, inf_mean], Σ) where Σ = [[ret_std², ρ·ret_std·inf_std], [ρ·ret_std·inf_std, inf_std²]] . Inflation clipped: inf = max(draw_inf, inf_floor) |
| 5.2 Cumulative Inflation Index | cum_inf[p, y] = ∏(1 + inf[p, k]) for k = 0 to y inclusive — cumulative product from year 0 through year y |
| 5.3 Real ↔ Nominal Conversion | Nominal→Real: real = nominal / cum_inf[p, y] . Real→Nominal: nominal = real × cum_inf[p, y] . Tier amounts are specified in real dollars; multiply by cum_inf each year. Floor/ceiling are real dollars; multiply by cum_inf for enforcement. |
| 5.4 Social Security COLA Growth | ss_income[p, y] = ss_annual × (1 + ss_cola)^(age - ss_start_age) for age ≥ ss_start_age . SS income does NOT use the simulation's cum_inf index. |
| 5.5 Survival Rate | survival_rate = np.mean(portfolio[:, -1] > 0) — fraction of paths where end-of-horizon portfolio exceeds zero |
| 5.6 Depletion Year | For each path p : depletion_year = first y where portfolio[p, y] == 0 , or None if the path never depletes. median_depletion = np.median([d for d in depletion_years if d is not None]) . Report as age: retire_age + median_depletion . |
| 5.7 Guardrail Application Order | GR1 → GR2 → GR3 → GR4 → Floor/Ceiling clamp (always applied last, unconditionally) |
| 5.8 Effective Tax Rate Approximation | effective_rate = roth_fraction × 0 + taxable_fraction × ltcg_rate + ira_fraction × ord_income_rate . Fractions are static approximations using initial account values relative to port_start . A future version may track per-account balances dynamically. |

---

         SECTION 6 — STREAMLIT UI COMPONENT MAPPING

## Section 6 — Streamlit UI Component Mapping
### 6.1 Inputs Tab Components
| Parameter Group | Streamlit Component | Implementation Notes |
| --- | --- | --- |
| Portfolio values | st.number_input (currency mode) | Format with "$" prefix and thousands separator; step=1000 |
| Age inputs | st.number_input (integer) or st.slider | Validate ranges inline with st.warning / st.error |
| Spending tiers | Dynamic list with st.form + st.columns | "Add Tier" / "Remove Tier" buttons; render each tier as a row of 3 inputs |
| Portfolio style preset | st.selectbox with description block | On change, auto-fill return/volatility sliders via st.session_state callbacks |
| Market parameters | st.slider | Show formatted current value next to slider label |
| Guardrail toggles | st.toggle | Show/hide dependent sub-parameters using if gr1_enabled: conditional rendering |
| Guardrail thresholds | st.slider | Show formatted current value next to each slider |
| Scenario save/load | st.text_input + st.button + st.selectbox | Store/load from st.session_state["scenarios"] |
| Run button | st.button("Run Simulation") | Trigger simulation on click; wrap computation in st.spinner("Running simulation...") |

### 6.2 Results Tab Components
| Output Element | Streamlit Component | Implementation Notes |
| --- | --- | --- |
| Survival rate card | st.metric with delta | Color-code via conditional st.markdown HTML wrapper |
| Summary dashboard | st.columns with metric cards | 4 cards per row; wrap in st.container |
| Success metrics table | st.dataframe | Non-editable; use column_config for formatted number columns |
| Fan charts (Portfolio, Spending, Inflation) | st.plotly_chart | use_container_width=True ; include nominal/real toggle via st.radio |
| Stacked bar chart (Guardrail events) | st.plotly_chart | Use Plotly go.Bar with barmode='stack' |
| Donut chart (Survival rate) | st.plotly_chart | Use go.Pie with hole=0.5 ; center annotation for % |
| WR box plot / fan | st.plotly_chart | Toggle between box plot and fan chart via st.radio above chart |
| Data tables | st.dataframe + st.download_button | CSV export; show row count and file size estimate before Table 5 generation |
| Scenario comparison | st.tabs or st.columns | Side-by-side layout; overlaid median fan chart |

### 6.3 State Management
| State Key | Type | Contents / Lifecycle |
| --- | --- | --- |
| st.session_state["inputs"] | dict | All validated inputs; updated on each successful validation pass |
| st.session_state["results"] | dict | Full result dictionary from simulation engine; set after successful run |
| st.session_state["scenarios"] | list[dict] | List of {name, inputs, results} dicts; max 5 entries |
| st.session_state["results_stale"] | bool | Set to True whenever any input changes; cleared after a run. Results tab shows stale banner when True : "Inputs changed — click Run Simulation to refresh results." |

> **ℹ️ Stale Results Banner**

        When `results_stale = True`, the Results tab must display a prominent banner at the top: *"Inputs changed — click Run Simulation to refresh results."* Results from the previous run remain visible for reference but are visually marked as potentially outdated.

---

         SECTION 7 — ERROR HANDLING AND EDGE CASES

## Section 7 — Error Handling and Edge Cases
| Case | Condition | Required Behavior |
| --- | --- | --- |
| 7.1 Portfolio Depletion | portfolio[p, y] == 0 | Portfolio stays at 0 for all subsequent years in that path. Negative portfolio values are not permitted. After depletion, spending is set to 0 (or ss_income only if SS is enabled and active). Path is counted in depletion statistics. |
| 7.2 Very High Withdrawal Rates | gross_withdrawal > portfolio_start | Cap gross_withdrawal at portfolio_start (consume entire remaining portfolio). This triggers ruin state for that path in that year. |
| 7.3 Zero SS Income | ss_enabled = False | ss_income = 0 for all years and all paths. All spending must come from portfolio. Withdrawal rates will be higher; guardrails respond accordingly. |
| 7.4 All Paths Survive | np.all(portfolio[:, -1] > 0) | Display "N/A — All paths survived to final year" for depletion year statistics. This is a positive outcome; display a success indicator in the dashboard. |
| 7.5 All Paths Deplete | np.all(portfolio[:, -1] == 0) | Display a prominent st.error warning card. Suggest: reducing spending tiers, increasing inf_floor , adjusting portfolio style to higher expected return, or verifying inputs. |
| 7.6 Invalid Covariance Matrix | \|ret_inf_corr\| >= 1 or degenerate matrix | Show validation error before simulation runs: "Covariance matrix is not positive semi-definite. Adjust the return–inflation correlation." Block run. |
| 7.7 Spending Tier Gaps | Age not covered by any tier | Show specific error identifying gap: "No spending tier covers ages [X] to [Y]. Add a tier or extend an existing tier." Block run. |
| 7.8 Results Tab with No Run | "results" not in st.session_state | Display a centered prompt: "No simulation results yet. Configure inputs and click Run Simulation." Do not render any charts or tables. |

---

         SECTION 8 — CONSTANTS AND DEFAULTS TABLE

## Section 8 — Constants and Defaults Table
Complete normative reference of all built-in constants and default values. These values must match the UI defaults unless overridden by user input.

| Constant / Default | Value | Source / Rationale |
| --- | --- | --- |
| Default plan years | 35 | Covers ages 58–93 in a typical early retirement scenario |
| Default SS COLA rate | 2.5% | Historical average Social Security COLA |
| Default inflation mean | 3.0% | Long-run US CPI average |
| Default inflation std dev | 1.5% | Historical volatility of annual CPI |
| Default inflation floor | 1.0% | Eliminates unrealistic deflation scenarios; user-adjustable to 0% |
| Default return–inflation correlation | 0.10 | Modest positive relationship; varies by economic regime |
| Default n_paths | 1,000 | Balance of statistical accuracy and compute time |
| Default random seed | 42 | Reproducibility convention |
| GR1 default floor % | 50% of starting portfolio | Signals severe drawdown requiring spending intervention |
| GR1 default ceiling % | 150% of starting portfolio | Signals major portfolio surplus allowing spending increase |
| GR1 default cut % | 10% | Moderate, sustainable spending reduction; symmetric with raise |
| GR1 default raise % | 10% | Symmetric with cut; conservative upside spend adjustment |
| GR2 default warn rate | 5.0% | Common "caution zone" threshold in practitioner literature |
| GR2 default critical rate | 6.5% | High-risk depletion territory; larger cut warranted |
| GR2 default low rate | 3.0% | Well below safe withdrawal benchmark; spending raise appropriate |
| GR2 warn cut | 5% | Light-touch early intervention before critical threshold |
| GR2 critical cut | 15% | More significant reduction at high-risk withdrawal rate |
| GR2 low raise | 5% | Conservative upside spend increase when portfolio is performing well |
| GR4 inflation trigger | 4.5% | Approximately 50% above 3.0% baseline mean |
| GR4 cut % | 5% | Small discretionary reduction during high-inflation years |
| Default LTCG rate | 15% | Applies to most taxpayers in the 15% LTCG bracket |
| Default ordinary income rate | 22% | Common middle federal bracket for retirees |
| Default Medicare age | 65 | Current US Medicare eligibility age |
| Default Medicare premium | $3,600/yr | Approximate combined Part B + Part D annual cost (today's dollars) |
| Default ACA cliff (single filer) | $62,000/yr | 400% FPL for single filer, 2026 approximation; user must verify current-year value |

---

         SECTION 9 — FUTURE ENHANCEMENTS

## Section 9 — Future Enhancements (Out of Scope for V1)

> **ℹ️ V1 Boundary**

        The following items are known future work. They are documented here for completeness and roadmap planning. None of these items are required for the initial V1 implementation.

| Enhancement | Description |
| --- | --- |
| Per-account balance tracking | Track Roth, IRA, and taxable balances independently as they evolve over the simulation horizon; enables precise tax sequencing |
| Roth conversion modeling | Allow user to specify annual Roth conversion amounts and tax cost; model MAGI impact on ACA subsidies precisely |
| Required Minimum Distributions (RMDs) | Model mandatory withdrawals from tax-deferred accounts beginning at age 73; apply IRS uniform lifetime table factors |
| Sequence-of-returns stress testing | Test portfolio against historical worst-case sequences (1966, 2000, and 2008 onset periods) as deterministic comparison scenarios |
| Long-term care cost modeling | Stochastic LTC event probability with age-dependent cost distributions; modeled as an additional random spending shock |
| Spousal / joint life modeling | Joint life expectancy, survivor benefit fractions for SS, and blended spending adjustment at first death |
| SS claiming age optimization | Side-by-side comparison of claiming at ages 62, 67, and 70 within a single simulation run |
| Fat-tailed return distributions | Student-t distribution for returns to model fat tails and extreme events; compare vs. normal assumption |
| PDF report export | Export full simulation results including charts and summary tables as a formatted PDF document |
| Annuity income integration | Model fixed or variable annuity income as an alternative floor income source alongside Social Security |
| IRMAA surcharge modeling | Medicare Income-Related Monthly Adjustment Amount (IRMAA) surcharges based on income lookback period |

---

         SECTION 10 — APPENDIX

## Section 10 — Appendix
### Appendix A — Glossary of Terms
| Term | Definition |
| --- | --- |
| Monte Carlo Simulation | A computational method that generates a large number of random scenarios (paths) to model the probability distribution of possible outcomes for a stochastic process |
| Bivariate Normal Distribution | A joint probability distribution of two correlated normally distributed random variables; used here to model the joint distribution of annual portfolio returns and inflation rates |
| Sequence-of-Returns Risk | The risk that poor investment returns early in retirement permanently impair a portfolio even if long-run average returns are adequate; a central concern of retirement planning |
| Withdrawal Rate (WR) | The annual gross portfolio withdrawal expressed as a percentage of the portfolio value at the start of that year; the primary metric used to assess depletion risk |
| Guardrail | A dynamic spending adjustment rule triggered by observable portfolio or withdrawal rate conditions; designed to reduce depletion risk by lowering spending when conditions deteriorate |
| Percentile Fan Chart | A chart showing multiple percentile bands (e.g., 10th/25th/50th/75th/90th) of a distribution over time, revealing the range of possible outcomes rather than a single projection |
| MAGI | Modified Adjusted Gross Income; the IRS income measure used to determine ACA premium tax credit eligibility and phase-out thresholds |
| ACA Cliff | The income threshold (400% of Federal Poverty Level) above which all ACA premium tax credits are lost in a single step, creating a sharp discontinuity in net healthcare costs |
| COLA | Cost-of-Living Adjustment; the annual percentage increase applied to Social Security benefits to partially offset inflation |
| Cumulative Inflation Index ( cum_inf ) | The compounded product of annual inflation factors from retirement start through a given year; used to convert between real (today's) dollars and nominal (future) dollars |
| Real vs. Nominal | Real dollars are inflation-adjusted to a base year (typically today); nominal dollars are future face values not adjusted for inflation. Real values reflect actual purchasing power. |
| Ruin / Ruin State | The condition where a simulation path's portfolio value reaches zero; the path remains at zero for all subsequent years and is counted as a failed or depleted path |
| Simulation Path | One complete sequence of random annual returns and inflation rates from retirement start to the end of the planning horizon; the fundamental unit of Monte Carlo analysis |
| Planning Horizon | The total number of years simulated, beginning at retire_age ; controls the length of each simulation path |
| Portfolio Style | A preset configuration of expected return and volatility parameters reflecting a target asset allocation, from Conservative to Equity Only |

### Appendix B — Mathematical Notation Reference
| Symbol | Meaning | Unit / Domain |
| --- | --- | --- |
| p | Path index | Integer ∈ [0, n_paths) |
| y | Year index (0-based from retire_age ) | Integer ∈ [0, plan_years) |
| μ_r | Expected annual portfolio return mean ( ret_mean ) | Decimal (e.g., 0.065) |
| σ_r | Annual return standard deviation ( ret_std ) | Decimal (e.g., 0.12) |
| μ_π | Expected annual inflation mean ( inf_mean ) | Decimal (e.g., 0.03) |
| σ_π | Annual inflation standard deviation ( inf_std ) | Decimal (e.g., 0.015) |
| ρ | Return–inflation Pearson correlation ( ret_inf_corr ) | Scalar ∈ (-1, 1) |
| Σ | 2×2 covariance matrix for bivariate normal draw | Matrix (positive semi-definite) |
| r[p, y] | Realized return for path p , year y | Decimal |
| π[p, y] | Realized inflation for path p , year y (post floor clipping) | Decimal ≥ inf_floor |
| CPI[p, y] | Cumulative inflation index ( cum_inf ) | Scalar ≥ 1.0 |
| W[p, y] | Portfolio value at end of year y for path p | USD ≥ 0 |
| S[p, y] | Guardrail-adjusted nominal spending for path p , year y | USD ≥ 0 |
| WR[p, y] | Withdrawal rate for path p , year y | Decimal ∈ [0, 1] |
| τ_eff | Blended effective tax rate ( effective_rate ) | Decimal ∈ [0, 1) |
| ∏ | Product notation (used for cumulative inflation index) | — |
| MVN | Multivariate Normal distribution | — |

### Appendix C — Streamlit Version Requirements
| Package | Minimum Version | Purpose |
| --- | --- | --- |
| Python | ≥ 3.11 | Runtime language; match-statement syntax and performance improvements |
| streamlit | ≥ 1.32 | UI framework; st.toggle , column_config , and st.tabs required |
| numpy | ≥ 1.26 | Simulation engine; all vectorized computation |
| plotly | ≥ 5.18 | All interactive charts; fan charts, donut, bar, box plots |
| pandas | ≥ 2.1 | Data table formatting for st.dataframe and CSV exports |

### Appendix D — File Structure Reference
The application must be organized into the following module structure to enforce separation of concerns, enable unit testing of the simulation engine independently of Streamlit, and allow the simulation module to be reused in non-UI contexts (e.g., batch runs, API endpoints).

```

project-root/
 app.py                  # Streamlit entry point — UI only; imports simulation, charts, validators
 simulation.py           # Monte Carlo engine — no Streamlit imports; accepts validated inputs dict
 validators.py           # Input validation logic — returns {valid: bool, errors: list, warnings: list}
 charts.py               # Plotly chart construction — accepts results dict; returns go.Figure objects
 requirements.txt        # Package versions (see Appendix C)
└ tests/
     test_simulation.py  # Unit tests for simulation.py (determinism, edge cases, guardrails)
     test_validators.py  # Unit tests for validators.py
    └ test_charts.py      # Smoke tests for chart construction
```

> **ℹ️ Module Dependency Rule`simulation.py` and `validators.py` must have **zero** Streamlit imports. `charts.py` must have zero Streamlit imports (it returns Plotly figure objects). Only `app.py` imports from Streamlit. This ensures the simulation engine is unit-testable without a running Streamlit server.**

---

        Monte Carlo Retirement Planner — Functional Specification v1.0  |  Confidential  |  July 2026  |  Page 1
