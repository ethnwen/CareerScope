# CareerScope: Project Scope and Research Plan (Phase 1 output)

Draft v1, written after inspecting the real files. Decisions in section 4 are defaults that can be changed before Phase 2 starts.

## 1. Purpose

CareerScope compares Canadian occupations using official labour-market statistics. It reports descriptive evidence to support career exploration. It does not predict an individual's salary or guarantee employment, and it does not imply causation.

## 2. Source roles

| Source | Role | Main limitation |
|---|---|---|
| 14-10-0444-01 | Offered wages and vacancy counts by occupation, province and economic region, 2015 to 2026 | About 79% of cells are empty. About 82% of published vacancy values are graded D or E. |
| 14-10-0443-01 | Vacancies, shares and offered wages by education, experience, type of work and type of position | 14 GB file, read in chunks. About 72% of cells are empty. Territories nearly empty below broad categories. |
| 14-10-0417-01 | Employee wages (actual, not inflation adjusted), 1997 to 2025, 59 occupation groups, provinces | Different concept from offered wages. Level shift in 2006. No territories. No quality grades. |
| Job Bank wages | Deferred | Not inspected |

## 3. Research questions and grain

1. Wage comparison. Offered wages by unit group for Canada, with a quality filter. Provincial comparison at major or sub-major group level. Employee wages (0417) shown in a separate view. Every ranking states quarter, geography, occupation level and the number of occupations with data.
2. Demand. Reported vacancy counts for Canada at unit group level with quality warnings, and for provinces at major group level. High wage plus high vacancy is shown as two measures side by side, not a composite. Vacancies are reported vacancies, not total jobs, applicants or probability of employment.
3. Trends. (a) Offered wages and vacancies, 2015 to 2026: same quarter year over year, using a matched panel (only cells with values in both periods). Q2 and Q3 2020 do not exist. Vacancy values for 2015-01 are suspect. Detailed unit groups only from 2023 Q4, broader groups for earlier history. (b) Employee wages, 1997 to 2025: separate analysis, nominal dollars, with a break marker at 2006. The two are never joined.
4. Characteristics. Type of work, education, experience and type of position, for Canada and provinces. Territories only for totals. Seasonal uses its own denominator. Associations are described, not explained.
5. Opportunity comparison. Measures shown separately, with the user choosing priorities. No composite score in version 1.

## 4. Decisions (defaults)

- D1. Quality rule: grades A to D are treated as reliable. E is kept but flagged. F, x and .. are missing. Rankings are checked for sensitivity to including and excluding E.
- D2. Geography: rankings use Canada and provinces. Territories are limited to totals and broad categories. Economic regions are limited to broad categories and major groups, with a visible data-coverage warning.
- D3. Occupation level: unit groups only for Canada. Provinces use major or sub-major groups. A level selector must show how many cells have data.
- D4. Trends: same-quarter year-over-year, matched panel, no interpolation across the 2020 gap.
- D5. Employee wage trend: shown from 2006 onward by default, earlier years optional with a break marker.
- D6. Cross-source comparison: side by side only, at major groups that exist in both sources, using a crosswalk built from the metadata. Never one series.
- D7. No composite score in version 1. If added later, document formula, weights and sensitivity.
- D8. Job Bank is deferred until the core project is complete.

## 5. Known limitations (for the README and the dashboard methodology page)

- Offered wages are advertised minimums, not actual pay.
- Vacancy estimates are mostly low quality (graded D or E). Fine-grained rankings are noisy.
- Most cells are empty at detailed occupation and region levels. Coverage is part of every result.
- Historical occupation codes before 2023 Q4 were converted from earlier NOC versions.
- Q2 and Q3 2020 are missing. 2015-01 vacancy coverage is unusually low.
- 0417 wages are not inflation adjusted and have a 2006 level shift.
- The three sources measure different things and use different definitions.

## 6. Open items for Phase 2 validation

- Explain the blank-STATUS vacancy counts in 0443 and count true zeros in 0443 and 0417.
- Test key uniqueness in 0443 and 0417.
- Investigate the low 2015-01 vacancy coverage in 0444.
- Measure coverage for Alberta, Ontario and British Columbia specifically.
- Check the first quarter with data for continuity of recruitment in 0443.
- Build the 0444 to 0417 occupation crosswalk.
- Verify licence terms for the Statistics Canada tables.

## 7. Decisions added during Phase 2

- D9. Trend analysis starts at 2015-04. The 2015-01 quarter is excluded because only 277 of its vacancy cells have a value (273 of them graded E). The first usable Q1 year-over-year comparison is 2017-01 vs 2016-01.
- D10. An occupation-by-province view is shown only when at least 50 percent of the cells at that level have a reliable (A to D) value in the latest quarter. Otherwise the dashboard shows an "insufficient data" message. To be re-tested across quarters.
- D11. In 0443, a blank STATUS (an exact zero or a 100 percent total) counts as reliable. 0417 has no quality grades, so D1 does not apply there and only suppression limits what is shown.
- D12. Continuity of recruitment is analysed from 2020 Q1 only (24 quarters), and any chart using it says so.
- D13. Hourly wage values outside 5 to 200 dollars are flagged is_suspect with a reason, kept in the processed files, and excluded from analysis by default. In Phase 2 this affected 17 rows in 0443 (several repeat one value at different occupation levels) and none in 0444 or 0417. Bounds only catch extreme errors, so grade filters and sensitivity checks are still needed.

- D14 (revises D10). Coverage is shown next to every ranking and view, with 50 percent as the well-covered marker rather than a hard cut-off.
- D15. The dashboard offers a quality-rule selector (A to C, A to D, A to E) with A to D as the default. Step 4.1 showed rankings are stable across the rules but coverage is not.
