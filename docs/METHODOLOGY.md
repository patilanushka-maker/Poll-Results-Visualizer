# Analytical & Modeling Methodology

## 1. Overview
This document outlines the methodological framework applied across data validation, metrics computation, poll aggregation, statistical comparisons, and automated insights.

---

## 2. Data Validation & Quality Framework (Phase 2 Implemented)

### 2.1 Errors vs. Warnings Policy
The validation engine strictly separates structural data corruption (**Errors**) from non-fatal hygiene flags (**Warnings**):
- **Validation Errors (`is_valid = False`)**:
  - Missing mandatory schema columns (`response_id`, `respondent_id`, `survey_type`, `question_id`, `question_text`, `question_type`, `answer`, `response_timestamp`).
  - Missing or blank essential identifiers (`response_id`, `respondent_id`, `question_id`).
  - Duplicate `response_id` values.
  - Duplicate `(respondent_id, question_id)` rows for single-answer questions (`single_choice`, `rating`, `nps`, `text`).
  - Unsupported `question_type` values (allowed: `single_choice`, `rating`, `nps`, `multi_select`, `text`).
  - Rating values outside $[1, 5]$ or non-numeric rating strings.
  - NPS values outside $[0, 10]$ or non-numeric NPS strings.
  - Malformed multi-select entries that cannot be parsed as JSON arrays.
  - Unparseable date strings in `response_timestamp`.

- **Validation Warnings (`is_valid = True` if zero errors)**:
  - Missing or blank `answer` values (omitted/skipped questions).
  - Missing `response_timestamp` values (row remains usable for non-temporal analysis).
  - Zero-row datasets.

### 2.2 Missing Answers vs. Negative Values
- A numeric response of `0` in an NPS question is a valid score (**Detractor** rating) and is strictly preserved as an answered survey item.
- An answer of `"No"` in a binary choice question is a valid negative selection.
- Genuine omissions (null, empty strings, `"nan"`) are tracked in summary diagnostics as `missing_answers_count` without producing false negative values.

---

## 3. Metrics & Statistical Formulations (Phase 3 Implemented)

### 3.1 Response Frequency & Percentages
For a given question $Q$, valid answers are isolated from omitted/skipped answers.
The unweighted percentage $P_k$ for choice $k$ is calculated as:
$$P_k = \frac{n_k}{\sum_{j=1}^{K} n_j} \times 100$$
where $n_k$ is the count of respondents choosing option $k$, and the denominator is strictly the total number of **valid responses to that specific question**. Rows across unrelated questions are never included in the denominator.

### 3.2 Weighted Percentage Formulations
When post-stratification survey weights ($w_i$) are supplied:
$$P_{k,\text{weighted}} = \frac{\sum_{i \in \text{choice } k} w_i}{\sum_{i \in \text{valid}} w_i} \times 100$$
- **Weight Validation Policy**: Weights must be strictly positive real numbers ($w_i > 0$). Missing (null/NaN), non-numeric, zero, or negative weights raise an actionable `ValueError`. Weights are never silently imputed or substituted with `1.0`. Valid weights do not alter underlying unweighted integer counts.

### 3.3 Discrete Rating Statistics (Likert 1–5)
For questions classified as `rating`:
- **Mean ($\mu$)**: $\frac{1}{N} \sum_{i=1}^{N} x_i$
- **Median**: Middle value of sorted valid ratings.
- **Sample Standard Deviation ($s$)**: Computed with Bessel's correction ($N-1$ degrees of freedom, `ddof=1`):
  $$s = \sqrt{\frac{1}{N-1} \sum_{i=1}^{N} (x_i - \bar{x})^2} \quad \text{for } N \ge 2$$
  (Returns `None` if $N < 2$).
- **Likert Distribution**: Returns an ordered frequency table for all discrete points on the scale (1, 2, 3, 4, 5). Zero-count categories are explicitly included with count 0 and percentage 0.0%.

### 3.4 Net Promoter Score (NPS)
For questions classified as `nps` with responses bounded in $[0, 10]$:
- **Detractors**: Respondents rating 0 to 6.
- **Passives**: Respondents rating 7 to 8.
- **Promoters**: Respondents rating 9 to 10.
- **Formula**:
  $$\text{NPS} = \% \text{Promoters} - \% \text{Detractors}$$
  The resulting score ranges from $-100.0$ to $+100.0$.
  The denominator is strictly the count (or weight sum) of valid NPS responses. Unanswered or missing records are excluded from the percentage denominator and reported as `missing_count`.

### 3.5 Multi-Select Response Frequencies
Multi-select responses are parsed from JSON array strings (e.g. `'["Email", "Phone"]'`).
- **Denominator Policy**: Total respondents providing a valid answer to the multi-select question ($N_{\text{resp}}$).
- **Option Percentage**:
  $$\text{Percentage}_{\text{opt}} = \frac{\text{Count of respondents selecting option}}{\text{Total respondents answering question}} \times 100$$
- **Sum of Percentages**: Because respondents may choose multiple options ($k \ge 1$), the sum of option percentages naturally exceeds 100%.
- **Deduplication**: If a single respondent's answer array repeats the same option, it is counted at most once for that respondent.
- **Malformed Handling**: Non-JSON strings or non-list values raise an actionable `ValueError`.

### 3.6 Confidence Intervals & Margin of Error
For unweighted categorical proportions, the **Wilson Score Interval** is implemented via `calculate_proportion_ci()`:
$$\tilde{p} = \frac{x + \frac{z^2}{2}}{n + z^2}, \quad \text{Margin} = \frac{z}{n + z^2} \sqrt{\frac{x(n - x)}{n} + \frac{z^2}{4}}$$
$$\text{CI}_{95\%} = \left[ \max(0.0, \tilde{p} - \text{Margin}), \ \min(100.0, \tilde{p} + \text{Margin}) \right]$$

- **Statistical Assumptions**:
  - Independent Simple Random Sampling (SRS).
  - Unweighted observations.
- **Unsupported & Deferred Statistical Scenarios**:
  - Clustered sampling, stratified survey designs, and weighted survey variance estimations are **explicitly deferred** and unsupported in Phase 3. Standard SRS formulas must not be blindly applied to complex weighted samples.
  - Confidence intervals calculated on synthetic datasets must **never** be cited as empirical evidence of real-world population sentiment.

---

## 4. Segment Analysis & Cross-Tabulations (Phase 3 Implemented)
- **Question Isolation**: Cross-tabulations strictly filter by `question_id` to guarantee unrelated survey items are never combined.
- **Normalization Semantics**:
  - `normalize='index'`: Row percentages showing the internal choice distribution within each demographic segment (summing to 100% per row).
  - `normalize='columns'`: Column percentages showing the demographic representation within each choice.
  - `normalize='all'`: Percentage of total valid survey responses.
  - `normalize=False`: Raw unweighted integer counts.
- **Missing Segment Handling**: Missing or null segment entries are explicitly classified and displayed under the label `"(Missing)"`. Missing answers are excluded from the contingency matrix so percentages reflect valid selections.
- **Group Summaries**: `group_rating_summary()` and `group_nps_summary()` calculate group-level descriptive metrics across demographic cohorts.

---

## 5. Visualizations & Design Framework (Phase 4 Implemented)

### 5.1 Architecture & Separation of Concerns
All visualization functions in `src/poll_visualizer/visualizations.py` return native `plotly.graph_objects.Figure` instances. They are completely decoupled from Streamlit and web servers, ensuring direct compatibility with CLI reporting, Jupyter notebooks, automated export scripts, and future interactive dashboard containers (`st.plotly_chart`).

### 5.2 Color Tokens & Semantic Palettes
- **Likert 5-Point Divergent Palette**:
  - `1 - Strongly Disagree`: Crimson (`#EF4444`)
  - `2 - Disagree`: Coral (`#F97316`)
  - `3 - Neutral`: Slate Gray (`#94A3B8`)
  - `4 - Agree`: Mint Green (`#34D399`)
  - `5 - Strongly Agree`: Deep Emerald (`#059669`)
- **NPS Category Palette**:
  - `Detractors (0–6)`: Coral Red (`#EF4444`)
  - `Passives (7–8)`: Warm Amber (`#F59E0B`)
  - `Promoters (9–10)`: Vibrant Green (`#10B981`)
- **General Categorical Palette**: High-contrast, accessible 8-color sequential and discrete hex palette (`#2563EB`, `#10B981`, `#F59E0B`, etc.).

### 5.3 NPS Representation & Promoter Distinction
The NPS visualization explicitly avoids conflating Net Promoter Score with raw promoter percentage:
- **Net Score Gauge**: Renders the net metric on the standard $[-100, +100]$ axis with detractor, neutral, and loyalty zones.
- **Audience Breakdown Bar**: Accompanies the gauge to independently report the exact percentage share and respondent count for Detractors, Passives, and Promoters.

### 5.4 Multi-Select Chart Denominators
- Each option bar reflects the proportion of valid respondents who selected that specific option.
- Charts include prominent subtitles stating: `"% of respondents selecting option; percentages may sum to > 100%"`.

### 5.5 Handling Zero-Counts and Empty States
- Rating charts preserve zero-count Likert steps so that scale absence is immediately apparent.
- When an empty DataFrame or a question with zero valid answers is passed, visualizations return an annotated figure with an explicit diagnostic message rather than failing or raising unhandled exceptions.

---

## 6. Automated Narrative Insights & Reporting Framework (Phase 5 Implemented)

### 6.1 Deterministic Narrative Insight Generation
The narrative insights engine (`src/poll_visualizer/insights.py`) transforms validated survey metrics into concise, structured observations formatted through the `QuestionInsight` dataclass. Every insight strictly decouples descriptive observations from raw metrics and analytical caveats:
- **Categorical Questions**:
  - Automatically identifies whether the leading choice represents a strict majority ($> 50\%$) or a plurality ($\le 50\%$).
  - Quantifies lead margin over runner-up option in percentage points.
  - Detects and handles exact ties deterministically, reporting tied options sorted alphabetically without fabricating a singular leader.
  - Restricts denominator strictly to valid responses for that question.
- **Rating & Likert Questions**:
  - Summarizes valid count, sample mean ($\mu$), median, sample standard deviation ($s$, with Bessel's correction `ddof=1`), and modal rating score.
  - Computes top-box favorable share (ratings 4–5), bottom-box unfavorable share (ratings 1–2), and neutral share (rating 3).
  - Flags multi-modal ties where two or more ratings share identical maximum frequencies.
- **Net Promoter Score (NPS)**:
  - Reports Net Promoter Score on $[-100.0, +100.0]$, promoter %, passive %, and detractor %.
  - Classifies sentiment into transparent, documented industry tiers:
    - $\ge +50.0$: *Excellent / High Loyalty*
    - $\ge +10.0$: *Healthy / Favorable*
    - $\ge -10.0$: *Neutral / Mixed Sentiment*
    - $\ge -50.0$: *Needs Attention / Low Sentiment*
    - $< -50.0$: *Critical / High Dissatisfaction*
  - Emits an explicit warning when detractors exceed promoters, resulting in negative net sentiment.
  - Never conflates NPS with mean rating or simple promoter percentages.
- **Multi-Select Questions**:
  - Extracts options from valid JSON array strings.
  - Calculates option selection rates using answering respondents as the denominator ($N_{\text{resp}}$).
  - Explicitly documents that option percentage sums naturally exceed 100% because respondents can select multiple choices.
- **Segment Comparisons**:
  - Ranks demographic cohorts to report highest and lowest observed averages/NPS.
  - Automatically flags small cohorts or missing segment labels.
  - Never asserts statistical significance or causality without formal inferential hypothesis testing.

### 6.2 Data Quality & Empty State Safeguards
- When a question has zero valid observations, functions return empty-state summaries (`"No valid responses were recorded..."`) with zero-value metrics rather than fabricating data or failing with unhandled exceptions.
- Missing values are explicitly distinguished from valid negative values (e.g. `0` score in NPS or `"No"` in single-choice).
- Unstructured open-ended text questions return submission counts and sample comments while warning that automated qualitative sentiment coding is required.

### 6.3 Executive Reporting & Export Formats
The reporting layer (`src/poll_visualizer/reporting.py`) reuses existing insights and metrics without duplicate calculations:
- `generate_survey_report_data()`: Packages overall survey metadata, data quality status (`HEALTHY`, `MODERATE`, `POOR`, `EMPTY`), overall completion rate, and list of per-question insight records.
- `generate_markdown_report()`: Generates an executive Markdown document with:
  1. Synthetic data notice (automatically included for simulated datasets).
  2. Executive summary table (records, respondents, questions, quality status).
  3. Question-by-question detailed findings, summaries, and analytical notes.
  4. Methodological appendix documenting per-question denominators and non-causal observation policies.
- `generate_tabular_summary()`: Compiles a flat `pandas.DataFrame` with standardized columns (`question_id`, `question_text`, `question_type`, `valid_responses`, `missing_responses`, `primary_metric`, `metric_value`, `key_finding`, `data_quality_status`) ready for direct CSV export (`df.to_csv()`).

### 6.4 Synthetic Provenance Notices
Whenever data is known to originate from synthetic simulation (auto-detected via known synthetic survey types or specified via `is_synthetic=True`), reports prominently display:
> **Simulated Data Notice**: This report was compiled from a deterministically generated synthetic dataset created for algorithmic verification, pipeline testing, and portfolio demonstration. Findings do not reflect empirical real-world public or organizational sentiment.

---

## 7. Interactive Analytics Dashboard Architecture & Design (Phase 6 Implemented)

### 7.1 Decoupled Application Architecture
The interactive Streamlit interface (`main.py`) acts strictly as a presentation and interaction layer. All analytical computations, schema checks, Plotly chart builds, narrative formulations, and data exports are delegated to the underlying reusable modules:
- Data validation: `poll_visualizer.validation`
- Cleaning & standardization: `poll_visualizer.cleaning`
- Metrics & statistical intervals: `poll_visualizer.metrics`
- Segment & cohort analyses: `poll_visualizer.analysis`
- Visualizations: `poll_visualizer.visualizations`
- Narrative insights: `poll_visualizer.insights`
- Reporting: `poll_visualizer.reporting`

### 7.2 Non-Destructive In-Memory Uploads
- Uploaded CSV files are processed entirely in memory via `io.BytesIO` streams.
- The dashboard never persists uploaded files to `data/raw/` or `data/processed/`, preventing filesystem contamination and data corruption.
- Uploaded files undergo rigorous schema validation before any analytical rendering occurs.

### 7.3 Small Cohort Safeguards & Inferential Restraint
- **Small Cohort Alert**: If any demographic segment contains fewer than 10 respondents ($n < 10$), the dashboard displays an explicit sampling variance warning: *"Small Sample Alert: One or more demographic cohorts contain fewer than 10 respondents. Sample metrics in small cohorts exhibit high sampling variance."*
- **Non-Causal Disclaimer**: Cohort comparisons prominently state that observed differences reflect sample descriptions rather than statistical significance or causal relationships.

### 7.4 Honest Provenance Tracking
The application maintains strict transparency regarding data provenance:
- **Built-in Canonical Datasets**: Always labeled as *Simulated Data* with clear disclaimers.
- **Uploaded Datasets**: Labeled as *Unverified Provenance* (or *Uploaded Simulated Data* if marked synthetic by the user). The dashboard explicitly avoids claiming real-world representation for unverified uploads.

