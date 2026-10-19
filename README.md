# Poll Results Visualizer

[![Tests](https://github.com/patilanushka-maker/Poll-Results-Visualizer/actions/workflows/tests.yml/badge.svg)](https://github.com/patilanushka-maker/Poll-Results-Visualizer/actions/workflows/tests.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A modular, production-structured survey and polling analytics platform designed for automated schema validation, exploratory analysis, statistical margin estimation, demographic cross-tabulation, interactive Plotly visualizations, deterministic narrative insight generation, and executive report compilation.

---

## Target Audience and Professional Competencies

This repository demonstrates applied end-to-end data analytics and software engineering competencies for the following roles:

* Data Analyst and Business Intelligence Engineer: Ingestion, schema validation, demographic cross-tabulations, automated narrative generation, data quality audits, and executive summaries.
* Survey Analyst and Insights Researcher: Methodologically sound denominator accounting, multi-select deduplication, Net Promoter Score evaluation, discrete Likert scaling, and non-causal cohort comparisons.
* Python and Analytics Engineer: Clean modular architecture, non-destructive data pipelines, comprehensive unit testing with pytest (111 passing tests), continuous integration with GitHub Actions, and interactive dashboard engineering with Streamlit.

---

## Executive Summary and Key Capabilities

Organizations frequently collect survey feedback across customer experience (CSAT), employee engagement (eNPS), and product research. However, survey data analysis frequently suffers from common methodological errors:
* Applying whole-dataset respondent counts as denominators for skipped questions.
* Conflating multi-select option totals with respondent populations.
* Presenting Net Promoter Score as a simple mean rating.
* Treating unweighted sample observations as statistically significant or causal findings.
* Failing to distinguish genuine missing answers from valid negative ratings (such as a 0 NPS score or a "No" answer).

The Poll Results Visualizer eliminates these pitfalls by embedding strict statistical governance and data hygiene into every layer of the analytics workflow.

### Core Capabilities

1. Multi-Format Survey Ingestion: Robust CSV loading with automatic character encoding fallback (UTF-8, Latin-1, CP1252), stream-buffer compatibility, and path existence verification.
2. Automated Schema Validation: Rigid validation of required long-format columns, unique identifiers, allowed question types, rating bounds [1, 5], NPS bounds [0, 10], JSON array multi-select parsing, and ISO-8601 timestamp integrity.
3. Statistical Metrics Engine: Exact response frequencies, post-stratification survey weighting, sample standard deviation with Bessel correction (ddof=1), complete ordered Likert distributions with zero-count preservation, Net Promoter Score on the standard [-100, +100] scale, and Wilson score 95% confidence intervals.
4. Demographic Segment Analysis: Contingency cross-tabulations normalized by row percentage, group rating and NPS summaries, small cohort variance warnings (n < 10), and explicit non-causal disclaimers.
5. Reusable Visualizations Engine: Decoupled Plotly figures for horizontal/vertical frequency bars, ordered divergent Likert distributions, dual-component NPS gauges with audience breakdowns, demographic comparisons, and cross-tabulation heatmaps.
6. Deterministic Narrative Insights Engine: Automated, rule-based narrative generation producing executive summaries, plurality/majority declarations, lead margins, Likert top-box/bottom-box shares, project-defined NPS tiers, and data quality notes without fabricated text.
7. Executive Reporting and Downloads: Automatic compilation of structured Markdown executive reports and flat tabular summary CSVs ready for spreadsheet analysis.
8. Interactive Streamlit Dashboard: Multi-tab desktop application providing real-time dataset exploration, custom CSV upload, question deep-dives, demographic cross-filtering, and report exports.

---

## System Architecture

The application is engineered with strict separation of concerns. The Streamlit dashboard acts purely as an interaction and display layer, delegating all data transformations, statistical calculations, and figure generation to reusable core modules.

```text
+-------------------------------------------------------------------------+
|                        Streamlit Web Application                        |
|                                (main.py)                                |
+--------------------+-------------------+-------------------+------------+
                     |                   |                   |
                     v                   v                   v
+--------------------+----+    +---------+---------+   +-----+------------+
| Ingestion & Validation  |    | Reusable Analysis |   | Narrative Engine |
|                         |    |  & Visualizations |   |   & Reporting    |
| - data_loader.py        |    | - metrics.py      |   | - insights.py    |
| - validation.py         |    | - analysis.py     |   | - reporting.py   |
| - cleaning.py           |    | - visualizations  |   |                  |
+--------------------+----+    +---------+---------+   +-----+------------+
                     |                   |                   |
                     +-------------------+-------------------+
                                         |
                                         v
                         +---------------+---------------+
                         |   Standard Survey Datasets    |
                         |   data/synthetic/*.csv        |
                         +-------------------------------+
```

---

## Interactive Dashboard Walkthrough

The Streamlit dashboard application organizes the analytical workflow across six specialized tabs.

```text
[Sidebar: Data Source]
  |-- Built-in Datasets: CSAT, eNPS, Product Preferences
  |-- Upload Custom CSV: In-memory validation, zero disk writes
  |
[Main Navigation Tabs]
  |-- Tab 1: Overview (KPI cards, item response rate, inventory)
  |-- Tab 2: Question Analysis (Plotly charts, metrics, narrative insights)
  |-- Tab 3: Segment Analysis (Grouped bars, heatmaps, small cohort alerts)
  |-- Tab 4: Automated Insights (Executive survey findings, caveats)
  |-- Tab 5: Data Quality (Validation status, completeness audit, cleaning preview)
  |-- Tab 6: Export Reports (Markdown document download, tabular CSV download)
```

### Dashboard Visual Previews

Screenshots and interface captures are maintained in the `images/` directory:

* Executive Overview and KPI Metrics: `images/P5 Out S1.jpg`
* Question Deep-Dive and Likert Distributions: `images/P5 Out S2.jpg`
* Net Promoter Score Gauge and Audience Breakdown: `images/P5 Out S3.jpg`
* Demographic Cohort Comparisons and Heatmaps: `images/P5 Out S4.jpg`
* Data Quality Diagnostics and Export Downloads: `images/P5 Out S5.jpg`

![Overview Interface](images/P5%20Out%20S1.jpg)
*Figure 1: Executive Overview tab displaying scale metrics, survey inventory, and provenance notices.*

![Question Deep-Dive](images/P5%20Out%20S2.jpg)
*Figure 2: Question Analysis tab featuring Plotly distributions and automated narrative summaries.*

![NPS and Gauges](images/P5%20Out%20S3.jpg)
*Figure 3: Net Promoter Score dual-component gauge and category share visualization.*

![Demographic Heatmaps](images/P5%20Out%20S4.jpg)
*Figure 4: Demographic segment cross-tabulations and contingency heatmaps.*

![Data Quality Diagnostics](images/P5%20Out%20S5.jpg)
*Figure 5: Schema validation diagnostics, item completeness audit, and export download panel.*

---

## Data Schema Specification

The platform utilizes a normalized long-format survey schema where each record represents a single respondent's answer to an individual survey item.

| Column Name | Type | Mandatory | Description |
| :--- | :--- | :---: | :--- |
| `response_id` | String / Integer | Yes | Globally unique identifier for the response record. |
| `respondent_id` | String / Integer | Yes | Unique participant identifier; links questions to respondents. |
| `survey_type` | String | Yes | Categorical domain (e.g., `customer_satisfaction`, `employee_engagement`). |
| `question_id` | String | Yes | Standardized item code (e.g., `CSAT_OVERALL`, `EE_ENPS`). |
| `question_text` | String | Yes | Verbatim question prompt presented to the respondent. |
| `question_type` | String | Yes | Functional type: `single_choice`, `rating`, `nps`, `multi_select`, `text`. |
| `answer` | Any | Yes | Recorded response. Null or blank values represent omitted answers. |
| `response_timestamp` | String (ISO-8601) | Yes | Submission timestamp (e.g., `2026-03-15T09:30:00Z`). |
| `segment` | String | No | Demographic group (e.g., `SMB`, `Enterprise`, `Engineering`). |
| `weight` | Float | No | Post-stratification sampling weight. Must be strictly positive. |

### Supported Question Types

* `single_choice`: Mutually exclusive categorical selections.
* `rating`: Discrete ordinal Likert ratings bounded strictly between 1 and 5.
* `nps`: Net Promoter Score recommendation scale bounded strictly between 0 and 10.
* `multi_select`: Multiple-option selections formatted as valid JSON array strings (e.g., `'["Slack", "Email"]'`).
* `text`: Free-form qualitative comments.

---

## Statistical Formulations and Governance

### 1. Per-Question Denominators
Response frequency percentages strictly isolate the question being evaluated. For any choice $k$ in question $Q$:

$$P_k = \frac{n_k}{\sum_{j=1}^{K} n_j} \times 100$$

The denominator comprises only respondents who provided a valid answer to question $Q$. Unrelated questions or skipped records are never pooled into the denominator.

### 2. Multi-Select Accounting
Multi-select choices are evaluated using unique answering respondents as the denominator ($N_{\text{resp}}$):

$$\text{Option Share} = \frac{\text{Count of respondents selecting option}}{N_{\text{resp}}} \times 100$$

Because respondents may select multiple items, option percentages naturally sum to greater than 100%. If an option is duplicated within a single respondent array, it is deduplicated and counted at most once per respondent.

### 3. Net Promoter Score Formulation
Valid numeric scores in [0, 10] are categorized into:
* Detractors: Scores 0 through 6
* Passives: Scores 7 and 8
* Promoters: Scores 9 and 10

$$\text{NPS} = \% \text{Promoters} - \% \text{Detractors}$$

The resulting score ranges from -100.0 to +100.0. Scores are interpreted via project-defined descriptive tiers:
* NPS >= +50.0: Excellent / High Loyalty
* NPS >= +10.0: Healthy / Favorable
* NPS >= -10.0: Neutral / Mixed Sentiment
* NPS >= -50.0: Needs Attention / Low Sentiment
* NPS < -50.0: Critical / High Dissatisfaction

### 4. Completion Rate Disambiguation
The overview tab strictly distinguishes two separate metrics:
* Item Response Rate: $\frac{\text{Total Valid Answer Records}}{\text{Total Long-Format Records}} \times 100$
* Respondent Completion Rate: $\frac{\text{Respondents with Zero Skipped Questions}}{\text{Total Distinct Respondents}} \times 100$

### 5. Wilson Score Confidence Interval
For unweighted categorical proportions, the Wilson score interval is implemented via `calculate_proportion_ci()`:

$$\tilde{p} = \frac{x + \frac{z^2}{2}}{n + z^2}, \quad \text{Margin} = \frac{z}{n + z^2} \sqrt{\frac{x(n - x)}{n} + \frac{z^2}{4}}$$

$$\text{CI}_{95\%} = \left[ \max(0.0, \tilde{p} - \text{Margin}), \ \min(100.0, \tilde{p} + \text{Margin}) \right]$$

---

## Data Security and Privacy Principles

* Zero Disk Persistence: User-uploaded files are processed strictly in memory via byte streams. Uploaded data is never written to `data/raw/` or `data/processed/`.
* Path Sanitization: All runtime error handlers filter out internal server file paths before presenting error banners.
* Zero Hardcoded Credentials: The platform operates with no database credentials, API tokens, or external authentication secrets. An `.env.example` file is provided for optional server configuration.
* Non-Destructive Cleaning: The `cleaning.py` module produces audit summaries and new standardized DataFrame instances without altering original input data.

---

## Technology Stack

| Layer | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| Programming Language | Python | 3.10+ | Core language environment |
| Data Processing | Pandas | >= 2.0.0 | Tabular manipulation, aggregations, cross-tabs |
| Numerical Computing | NumPy | >= 1.24.0 | Numerical vectors and missing-value sentinels |
| Visualizations | Plotly | >= 5.15.0 | Interactive, publication-ready charts and heatmaps |
| Web Application | Streamlit | >= 1.25.0 | Multi-tab interactive analytics user interface |
| Configuration | PyYAML | >= 6.0 | Structured configuration parsing |
| Test Framework | pytest | >= 7.4.0 | Unit, property, and AppTest integration test suites |
| Continuous Integration | GitHub Actions | Ubuntu / Python 3.10 | Automated test verification on push and pull requests |

---

## Repository Structure

```text
Poll-Results-Visualizer/
|-- .env.example                  # Environment configuration template
|-- .gitignore                    # Git exclusions (caches, environments, outputs)
|-- .github/
|   `-- workflows/
|       `-- tests.yml             # Automated CI workflow
|-- data/
|   |-- raw/                      # Original datasets (git-ignored)
|   |-- processed/                # Normalized datasets (git-ignored)
|   `-- synthetic/                # Canonical reproducible benchmark datasets
|       |-- customer_satisfaction.csv
|       |-- employee_engagement.csv
|       `-- product_preferences.csv
|-- docs/                         # Technical documentation hub
|   |-- DATA_DICTIONARY.md        # Variable definitions and validation rules
|   |-- METHODOLOGY.md            # Statistical formulations and standards
|   |-- USER_GUIDE.md             # Execution instructions and API guide
|   |-- architecture.md           # System design and decoupling patterns
|   |-- data_pipeline.md          # Data transformations and lifecycle
|   |-- execution_log.md          # Development history and phase audits
|   |-- model_specifications.md   # Mathematical modeling details
|   |-- modules_breakdown.md      # Individual module API contracts
|   `-- README.md                 # Documentation navigation index
|-- images/                       # Interface captures and architectural diagrams
|-- notebooks/                    # Prototyping and exploratory notebooks
|-- outputs/
|   |-- exports/                  # Generated CSV summaries (git-ignored)
|   `-- reports/                  # Generated Markdown reports (git-ignored)
|-- scripts/
|   `-- generate_synthetic_data.py # Deterministic synthetic survey generator
|-- src/
|   `-- poll_visualizer/          # Core analytics package
|       |-- __init__.py           # Package namespace and version
|       |-- analysis.py           # Cross-tabulations and segment metrics
|       |-- cleaning.py           # Non-destructive standardization rules
|       |-- data_loader.py        # Safe CSV loading and encoding fallbacks
|       |-- insights.py           # Automated narrative generation engine
|       |-- metrics.py            # Frequencies, Likert, NPS, and Wilson CIs
|       |-- reporting.py          # Markdown document and CSV report exports
|       |-- validation.py         # Schema and numerical bound verification
|       `-- visualizations.py     # Standalone Plotly figure builders
|-- tests/                        # Comprehensive test suite (111 tests)
|   |-- __init__.py
|   |-- test_analysis.py          # Segment summaries and cross-tabs tests
|   |-- test_cleaning.py          # Standardization and audit log tests
|   |-- test_dashboard.py         # AppTest and Streamlit integration tests
|   |-- test_data_loader.py       # File loading and encoding fallback tests
|   |-- test_insights.py          # Deterministic narrative engine tests
|   |-- test_metrics.py           # Statistical metrics and Wilson CI tests
|   |-- test_reporting.py         # Survey reporting and export schema tests
|   |-- test_structure.py         # Package structure and import tests
|   |-- test_synthetic_data.py    # Synthetic survey generation tests
|   |-- test_validation.py        # Schema verification and bound tests
|   `-- test_visualizations.py    # Plotly figure generation tests
|-- main.py                       # Streamlit application entry point
|-- pyproject.toml                # Project packaging configuration
`-- requirements.txt              # Production dependency specifications
```

---

## Installation and Local Setup

### Prerequisites
* Python 3.10 or higher
* Git command line tools

### Setup Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/patilanushka-maker/Poll-Results-Visualizer.git
   cd Poll-Results-Visualizer
   ```

2. Create and activate an isolated virtual environment:
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # macOS / Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install project dependencies and editable package:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   pip install -e .
   ```

4. Launch the Streamlit dashboard:
   ```bash
   streamlit run main.py
   ```
   The application will open automatically in your browser at `http://localhost:8501`.

---

## Testing and Quality Verification

The test suite comprises 111 automated tests covering schema validation, numeric bounds, statistical formulas, edge cases, Plotly figures, narrative generation, report generation, non-destructive cleaning, and Streamlit AppTest simulation.

Run the full test suite with verbose output:
```bash
pytest -v
```

Execution Summary:
```text
tests/test_analysis.py ......                                            [  5%]
tests/test_cleaning.py ....                                              [  9%]
tests/test_dashboard.py ................                                 [ 23%]
tests/test_data_loader.py .......                                        [ 29%]
tests/test_insights.py .............                                     [ 41%]
tests/test_metrics.py ............                                       [ 52%]
tests/test_reporting.py .........                                        [ 60%]
tests/test_structure.py ..........                                       [ 69%]
tests/test_synthetic_data.py .....                                       [ 73%]
tests/test_validation.py ...............                                 [ 87%]
tests/test_visualizations.py ..............                              [100%]

============================= 111 passed in 4.5s =============================
```

---

## Documentation Hub Index

Comprehensive technical documentation is maintained under `docs/`:

* Variable Dictionary and Rules: [docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md)
* Statistical Methodology and Standards: [docs/METHODOLOGY.md](docs/METHODOLOGY.md)
* Execution and API Reference Guide: [docs/USER_GUIDE.md](docs/USER_GUIDE.md)
* Architecture and Component Design: [docs/architecture.md](docs/architecture.md)
* End-to-End Data Lifecycle: [docs/data_pipeline.md](docs/data_pipeline.md)
* Module Contracts and Return Schemas: [docs/modules_breakdown.md](docs/modules_breakdown.md)
* Mathematical Modeling Specifications: [docs/model_specifications.md](docs/model_specifications.md)
* Audit History and Log: [docs/execution_log.md](docs/execution_log.md)

---

## Pre-Configured Synthetic Datasets

For testing and portfolio demonstrations, three synthetic datasets are generated deterministically in `data/synthetic/`:

1. `customer_satisfaction.csv`: 750 records from 150 respondents evaluating CSAT ratings, NPS likelihood, support channels, and product pain points across SMB and Enterprise segments.
2. `employee_engagement.csv`: 750 records from 150 respondents evaluating role satisfaction, eNPS scores, remote work arrangements, and company benefits across departments.
3. `product_preferences.csv`: 750 records from 150 respondents evaluating software usability, recommendation likelihood, subscription tiers, and feature requests.

*Notice: Synthetic benchmark datasets are strictly simulated for algorithmic testing and demonstration. They do not represent empirical real-world opinions or organizations.*

---

## Limitations and Future Extensions

* Post-Stratification Weights in Interface: While `metrics.py` fully supports survey weighting formulas, the dashboard displays unweighted descriptive sample metrics. Weighted dashboard filtering is a roadmap item.
* Inferential Hypothesis Testing: Cohort comparisons report observed distribution differences and flag small cohorts (n < 10); formal inferential significance tests (such as Chi-squared tests of independence and two-sample t-tests) are planned for future versions.
* Qualitative NLP: Free-form text questions summarize response volumes and sample comments; natural language sentiment classification and topic modeling are deferred.

---

## License and Author

* Project: Poll Results Visualizer
* Author: Anushka
* Academic Context: IIT Data Science Portfolio Project
* License: MIT License
