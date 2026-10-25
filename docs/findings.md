\# Findings (Phase 2, exploratory)



Status: draft. All figures were reproduced from the processed tables in `data/processed` on 2026-10-23 and cross-checked against `docs/validation\_report.txt`. Each statement is tagged:



\- \*\*\[Verified]\*\* reproduced from the data and described, with no causal claim.

\- \*\*\[Hypothesis]\*\* a possible explanation that has not been tested.

\- \*\*\[Limitation]\*\* something the data cannot tell us.



Rules applied: reliable values are grades A to D (plus exact values with no grade in table 14-10-0443); grade E is excluded from rankings; values flagged `is\_suspect` are excluded; trends start at 2015-04. All dollar figures are nominal (not adjusted for inflation). Offered wages are advertised minimums, not actual pay.



\## 1. Coverage and data quality



\- \[Verified] Only 1,250,123 of 6,018,496 cells in table 14-10-0444-01 (20.8%) have a published value. In the latest quarter (2026-04), 22,440 of 68,392 wage cells (32.8%) and 12,317 of 68,392 vacancy cells (18.0%) have a value.

\- \[Verified] The share of wage cells with a value rose from 18.5% (2015-04) to 34.5% (2022-04). Averaging over whichever cells have values would therefore mix real change with changing coverage. Trend comparisons use matched cells or published totals.

\- \[Verified] The first quarter, 2015-01, has only 277 vacancy values (273 graded E, 4 graded D), compared with 7,470 in 2015-04. It is excluded from trends (decision D9).

\- \[Unexplained] Wage coverage jumps from 21.9% (2019-10) to 27.3% (2020-01). The cause is not known.

\- \[Verified] Quality differs sharply between measures.



| Grade | Offered wage values | Job vacancy values |

|---|---|---|

| A | 42.1% | 1.0% |

| B | 25.5% | 5.3% |

| C | 9.1% | 11.7% |

| D | 6.4% | 38.3% |

| E | 16.9% | 43.6% |



\- \[Verified] Share of occupation groups with a reliable value (grades A to D), 2026-04. Level 2 = major groups (45), level 5 = unit groups (516).



| Geography | Wage, level 2 | Wage, level 5 | Vacancies, level 2 | Vacancies, level 5 |

|---|---|---|---|---|

| Canada | 98% | 88% | 98% | 61% |

| Ontario | 98% | 70% | 91% | 37% |

| Quebec | 93% | 67% | 89% | 36% |

| British Columbia | 96% | 56% | 78% | 20% |

| Alberta | 96% | 49% | 73% | 15% |

| Manitoba | 89% | 32% | 67% | 13% |

| Saskatchewan | 84% | 28% | 67% | 10% |

| Nova Scotia | 76% | 27% | 58% | 8% |

| New Brunswick | 73% | 24% | 60% | 9% |

| Newfoundland and Labrador | 64% | 10% | 33% | 2% |

| Prince Edward Island | 36% | 4% | 11% | 1% |

| Yukon | 27% | 1% | 0% | 0% |

| Northwest Territories | 38% | 1% | 0% | 0% |

| Nunavut | 11% | 0% | 4% | 0% |



\- \[Verified] Under the 50% rule (D10), unit-group wage views qualify only for Canada, Ontario, Quebec and British Columbia. Alberta is at 49%, one point under the rule.

\- \[Decision needed] Keep a hard threshold, or show the coverage percentage next to every ranking and test several thresholds in the sensitivity analysis.



\## 2. National trends (Canada, all occupations, table 0444)



\- \[Verified] Job vacancies: peak 1,032,215 in 2022-04; lowest since the peak 469,840 in 2025-10; 548,400 in 2026-04 (graded A).

\- \[Verified] Change versus the same quarter a year earlier: vacancies highest +62.8% (2021-10), lowest -25.6% (2023-07), +0.5% in 2026-04.

\- \[Verified] The average offered hourly wage rose from $18.70 (2015-04) to $28.55 (2026-04), +52.7% in nominal terms. Year-over-year growth ranged from 0.8% (2017-07) to 8.5% (2022-10) and was 2.0% in 2026-04.

\- \[Limitation] Q2 and Q3 2020 do not exist, so year-over-year change cannot be computed for 2021-04 and 2021-07.

\- Method note: these are published national totals, not sums of occupation cells, so they are not affected by the changing occupation-level coverage.



\## 3. Offered wages across occupations (Canada, 2026-04)



\- \[Verified] The median across unit groups with a reliable wage is $31.10. This is an unweighted median across occupations, not the national average wage.

\- \[Verified] Highest offered wages among unit groups: senior managers in financial, communications and other business services $94.50 (grade A, 325 vacancies); senior managers in construction, transportation, production and utilities $87.50 (B); dentists $83.15 (C, 295 vacancies); senior managers in health, education, social and community services $73.90 (C); senior managers in trade, broadcasting and other services $72.65 (C).

\- \[Verified] Lowest offered wages (all graded A): cashiers $17.45 (6,060 vacancies); weavers, knitters and other fabric making occupations $17.45; food and beverage servers $17.50 (10,120); maitres d'hotel and hosts/hostesses $17.55 (1,385); store shelf stockers, clerks and order fillers $17.55 (9,340).

\- \[Hypothesis] The lowest wages cluster in a narrow band ($17.45 to $17.55), which may reflect wage floors. Not tested.

\- \[Limitation] Several of the highest-paid groups have no published vacancy count.



\## 4. Offered wage and vacancies together



\- \[Verified] Across 312 unit groups with a reliable wage and a reliable vacancy count, the Spearman rank correlation between vacancies and offered wage is -0.27: a weak to modest tendency for higher-vacancy groups to have lower offered wages, with many exceptions.

\- \[Verified] The five unit groups with the most vacancies are food counter attendants and kitchen helpers, retail salespersons and visual merchandisers, registered nurses and registered psychiatric nurses, transport truck drivers, and cooks.

\- \[Verified] 65 unit groups are at or above the median on both measures. The largest by vacancies: registered nurses (17,275 vacancies, $36.35), carpenters (4,695, $33.00), software developers and programmers (3,545, $43.65), financial auditors and accountants (3,290, $37.10), financial managers (3,095, $53.15). This is a descriptive list, not a recommendation.

\- \[Limitation] The 312 groups are those with a reliable vacancy count (about 61% of unit groups), so the result describes that subset, not all occupations. No significance test is reported because the groups are not a random sample.

\- \[Hypothesis] Vacancy counts rise with occupation size, so a vacancy rate would be a fairer demand measure. That needs employment denominators that these tables do not provide at unit-group level.



\## 5. Job characteristics (table 0443, Canada, all occupations, 2026-04)



| Characteristic | Offered wage | Vacancies | Share of vacancies |

|---|---|---|---|

| No minimum education | $20.90 | 160,740 | 29.3% |

| High school diploma or equivalent | $23.85 | 135,015 | 24.6% |

| Non-university certificate or diploma | $31.05 | 150,310 | 27.4% |

| University certificate below bachelor's | $36.40 | 21,120 | 3.9% |

| Bachelor's degree | $44.05 | 65,095 | 11.9% |

| Above bachelor's | $48.85 | 16,110 | 2.9% |

| Experience: less than 1 year | $23.95 | 242,805 | 44.3% |

| 1 year to less than 3 years | $26.70 | 179,800 | 32.8% |

| 3 years to less than 5 years | $34.55 | 61,045 | 11.1% |

| 5 years to less than 8 years | $41.90 | 51,010 | 9.3% |

| 8 years or more | $59.15 | 13,740 | 2.5% |

| Full-time | $30.40 | 408,100 | 74.4% |

| Part-time | $23.20 | 140,300 | 25.6% |

| Permanent | $29.55 | 428,200 | 78.1% |

| Temporary (seasonal and non-seasonal) | $25.00 | 120,200 | 21.9% |

| Seasonal | $23.50 | 84,385 | 70.2% of temporary |



\- \[Verified] Offered wages rise with required education and experience, while vacancies concentrate in the lower-requirement categories: 53.9% of vacancies need no more than high school, 77.1% need under three years of experience, and 14.8% require a bachelor's degree or above.

\- \[Limitation] These are differences between groups of vacancies. They partly reflect which occupations require what, and they do not show that education or experience causes higher pay. Each wage is the lowest value of an advertised range.



\## 6. Employee wages (table 0417, average hourly wage, all occupations, current dollars)



| Year | Canada | Alberta | Ontario | British Columbia |

|---|---|---|---|---|

| 1997 | $15.59 | $14.80 | $16.34 | $16.91 |

| 2005 | $19.09 | $19.79 | $20.03 | $19.36 |

| 2006 | $20.16 | $21.74 | $21.10 | $20.31 |

| 2025 | $36.40 | $37.35 | $37.72 | $37.95 |



\- \[Verified] Nominal growth from 1997 to 2025: Canada x2.33, Alberta x2.52, Ontario x2.31, British Columbia x2.24. These figures include inflation.

\- \[Verified] The 2005 to 2006 increase is +5.6% for Canada (Alberta +9.9%, Ontario +5.3%, British Columbia +4.9%). Canada's average growth was about 2.6% per year from 1997 to 2005 and about 3.2% per year from 2006 to 2025.

\- \[Hypothesis] The 2006 step is consistent with the documented level shift from processing changes, but Alberta's larger step may also include real wage growth. The table cannot separate the two.

\- \[Limitation] Employee wages (table 0417) and offered wages (tables 0444 and 0443) are different measures with different definitions and are never combined.



\## 7. Integrity checks



\- 87 validation checks pass with 0 warnings and 0 failures (`docs/validation\_report.txt`).

\- Tables 0444 and 0443 agree


## 10. Sensitivity to the quality rule (step 4.1, latest quarter 2026Q2)

Three rules were compared: A to C, A to D (the project rule) and A to E. The rule changes which groups are included, not their values. Source: docs/sensitivity_quality_rule.txt.

- [Verified] Rankings are stable. The top 10 unit groups by vacancies are identical under all three rules. The top 10 by offered wage differs by one group under each alternative rule (9 of 10 the same): computer and information systems managers ($63.20, grade A) enter under A to C and telecommunication carriers managers ($66.75, grade E) enter under A to E.
- [Verified] Grade E affects coverage far more than volume. 78 of the 393 unit groups with a vacancy count (19.8%) are grade E only, but they hold 18,900 vacancies, 3.6% of the vacancy total in the A to E set. For wages, 19 of 472 groups are grade E only.
- [Verified] The wage-vacancy rank correlation keeps its sign but changes in size with the rule: -0.41 (A to C, 178 groups), -0.27 (A to D, 312 groups), -0.22 (A to E, 391 groups).
- [Hypothesis] The weaker correlation under looser rules may reflect noisier vacancy estimates for smaller occupations, which tend to weaken any association. Not tested.
- [Verified] The 50 percent coverage marker is sensitive to the quality rule at unit-group level. Wage views reach 50 percent in Canada, Ontario, Quebec and British Columbia under A to C and A to D, and also in Alberta (57.9 percent, versus 48.8 percent under A to D) under A to E. Vacancy views reach 50 percent only in Canada under A to D, and in Canada, Ontario and Quebec under A to E.
- [Verified] At major-group level, wage views reach 50 percent in ten geographies under every rule. Vacancy views reach 50 percent in 4 (A to C), 9 (A to D) and 10 geographies (A to E, adding Newfoundland and Labrador).
- [Limitation] One quarter (2026Q2) only. No significance test is reported.
