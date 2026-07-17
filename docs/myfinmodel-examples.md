# MyFinModel Example Walkthroughs

> [!WARNING]
> ## Disclaimer
> This Monte Carlo Retirement Planning Model is provided for EDUCATIONAL AND PLANNING PURPOSES ONLY. It is NOT financial advice, investment advice, tax advice, or legal advice. All projections are hypothetical and based on assumptions that may not reflect future market conditions. Past performance of investment markets does not guarantee future results. Actual outcomes will differ, possibly significantly, from modeled projections. Monte Carlo simulation cannot predict sequence-of-returns risk, legislative changes, health emergencies, or personal circumstances that may materially affect your financial situation.
>
> **Consult a qualified professional:** Work with a Certified Financial Planner (CFP), Certified Public Accountant (CPA), or other licensed professional before making major financial decisions based on this model. ACA subsidy eligibility, tax treatment of withdrawals, and Social Security claiming strategy should be reviewed annually and verified with current law.

All values in the examples below are for illustration and education only.

## 1. Worked Example Scenario

Use this section as a baseline walkthrough from inputs to interpretation.

### Goal

Build a balanced retirement plan and evaluate whether it has durable full-horizon survival under moderate assumptions.

### Example Inputs (starting point)

| Area | Value |
|---|---|
| Starting Portfolio | $1,200,000 |
| Taxable / Tax-Deferred / Roth | $300,000 / $700,000 / $200,000 |
| Current Age / Retirement Age | 60 / 65 |
| Planning Horizon | 35 years |
| Spending Tier 1 (65-79) | $78,000 |
| Spending Tier 2 (80-99) | $62,000 |
| Spending Floor / Ceiling | $45,000 / $95,000 |
| Portfolio Style | Growth (Balanced Growth) |
| Return Mean / Std Dev | 6.5% / 12.0% |
| Inflation Mean / Std Dev / Floor | 3.0% / 1.2% / 1.0% |
| Simulation Paths | 1,000 |
| Social Security | Enabled, start 67, annual benefit $36,000 |
| ACA Guardrail | Enabled |

### Steps

1. Enter the values above in the Inputs tab.
2. Confirm there are no blocking validation errors.
3. Click Run Simulation.
4. Review dashboard cards first, then Portfolio and Spending tabs.
5. Save the scenario with a clear name (for example: Baseline-35y-growth).

### What to Check

- Full Horizon Survival Rate: use the guide's bands as a first pass. `>= 90%` is strong durability, `80-89%` is moderate and worth reviewing, `70-79%` is elevated risk, and `< 70%` means the plan likely needs material changes.
- 10th percentile final portfolio: this is the stress-case anchor, so the key question is whether it stays above `$0`. If the 10th percentile ends below zero or very near zero, the plan is fragile even if the median looks acceptable.
- Median Final Portfolio: use this as the typical-path reference, but do not let it override the downside view. A healthy median with a weak 10th percentile usually means the plan is too exposed to sequence risk.
- Median withdrawal-rate trend in Tax Efficiency: check whether the line stays relatively stable or repeatedly bumps into the upper tail. Rising pressure early in retirement often means spending is too aggressive or returns are too volatile for the current plan.
- Guardrail activity concentration by age in Analysis: look for clusters in early retirement or around major spending transitions. Frequent triggers in one age band usually point to a mismatch between spending, horizon, or guardrail settings.
- Spending versus floor/ceiling constraints: confirm the modeled spending path is not living at the floor too often, because that usually means the plan is being forced downward. Repeated ceiling hits can mean the plan is leaving usable flexibility on the table.

### Interpretation Prompt

If survival is below your target, adjust spending tiers first, then return/risk assumptions, then guardrail thresholds.

## 2. Sensitivity Playbook

Use this section to run controlled variations from a saved baseline so you can see which assumptions drive outcomes most.

### Method

1. Load your baseline scenario and run it.
2. Save a copy per change so each test differs by one variable only.
3. Use Compare to evaluate deltas against baseline.

### High-Impact Variations (recommended order)

1. Spending stress: increase each spending tier by 5% and 10%.
2. Horizon stress: extend planning horizon by 3 and 5 years.
3. Return stress: lower expected return by 0.5% and 1.0%.
4. Volatility stress: increase return std dev by 2 points.
5. Guardrail stress: tighten GR2 warn/critical thresholds or increase cut percentages.

### Readout Checklist

- Change in survival rate vs baseline. Use the user guide's banding to decide whether a change moved the plan from strong to moderate, or from moderate into elevated/high risk.
- Change in 10th percentile final portfolio. This is the best quick check for downside fragility; if the value drops toward or below `$0`, the change meaningfully weakens the plan even if the median remains steady.
- Change in average surviving spending. If spending only improves by pushing the tail results down, the change is probably not worth it.
- Increase/decrease in guardrail trigger frequency. More triggers usually means more behavioral friction and a plan that is less stable in practice.
- Whether outcomes are robust across multiple stress cases. A good plan should not collapse when only one input moves by a small amount.

## 3. Compare Tab Method Notes

Use this section to interpret scenario overlays correctly and avoid false conclusions.

### Delta Interpretation

- Compare focuses on directional differences in outcomes, not certainty.
- A higher median line can still have worse tail outcomes; always check percentile spread.
- Similar survival rates can mask different spending comfort levels.
- Treat the 10th percentile and depletion frequency as the main durability check. If one scenario looks better in the middle but worse in the tail, the tail usually matters more for retirement planning.

### Horizon Alignment

- Scenarios with different horizons can be padded to align chart overlays.
- Focus comparison on the shared age range first.
- Treat padded tail segments as visualization support, not additional simulated evidence.

### Good Comparison Hygiene

1. Keep one scenario as fixed baseline.
2. Change one input cluster at a time.
3. Name scenarios to encode what changed.
4. Save notes on why a scenario was considered better or worse.

### Common Pitfalls

- Comparing scenarios where multiple assumptions changed at once.
- Prioritizing median outcomes without checking downside percentiles.
- Ignoring guardrail frequency shifts that indicate practical spending friction.
- Assuming that a visually higher line means a better plan even when the downside band is worse.
