# User Guide

## 1. Quick Start

### 1.1 Prerequisites
- Python 3.10 or higher
- Git

### 1.2 Installation
Clone the repository and set up a virtual environment:
```bash
git clone <repository-url>
cd "Poll Results Visualizer"

# Create and activate virtual environment
python -m venv venv
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Linux / macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -e .
```

---

## 2. Generating Synthetic Survey Data

The project includes a deterministic generator producing realistic datasets across three domains:
- Customer Satisfaction (`customer_satisfaction.csv`)
- Employee Engagement (`employee_engagement.csv`)
- Product Preferences (`product_preferences.csv`)

### 2.1 Default Generation Command
Generate all three datasets with 150 respondents each using default seed `42`:
```bash
python scripts/generate_synthetic_data.py
```
Output files are written directly to `data/synthetic/`.

### 2.2 Custom Parameters
Configure respondent count, custom random seed, or output directory:
```bash
python scripts/generate_synthetic_data.py --output-dir data/synthetic --respondents 250 --seed 123
```

---

## 3. Python API Usage

### 3.1 Loading & Validating Survey Data
```python
from poll_visualizer.data_loader import load_csv
from poll_visualizer.validation import validate_survey_data

# Load CSV
df = load_csv("data/synthetic/customer_satisfaction.csv")

# Validate structure and bounds
result = validate_survey_data(df)
print(result.summary_report())
```

### 3.2 Calculating Question Metrics
```python
from poll_visualizer.metrics import (
    calculate_response_frequencies,
    calculate_weighted_frequencies,
    calculate_rating_metrics,
    calculate_likert_distribution,
    calculate_nps,
    calculate_multiselect_frequencies,
    calculate_proportion_ci,
)

# A. Categorical Response Frequencies & Percentages
freq_df = calculate_response_frequencies(df, question_id="CSAT_CHANNEL")
print(freq_df)

# B. Weighted Frequencies (optional survey weight column)
weighted_df = calculate_weighted_frequencies(df, question_id="CSAT_CHANNEL", weight_col="weight")
print(weighted_df)

# C. Rating Descriptive Statistics (Mean, Median, Std, Min, Max)
rating_stats = calculate_rating_metrics(df, question_id="CSAT_OVERALL")
print("CSAT Overall Rating Mean:", rating_stats["mean"])

# D. Likert Distribution (All categories 1-5 preserved)
likert_df = calculate_likert_distribution(df, question_id="CSAT_OVERALL")
print(likert_df)

# E. Net Promoter Score (NPS)
nps_results = calculate_nps(df, question_id="CSAT_NPS")
print("NPS Score:", nps_results["nps_score"])
print("Promoter %:", nps_results["promoter_pct"], "| Detractor %:", nps_results["detractor_pct"])

# F. Multi-Select Frequencies (from JSON arrays)
multiselect_df = calculate_multiselect_frequencies(df, question_id="CSAT_PAIN_POINTS")
print(multiselect_df)

# G. Wilson Score 95% Confidence Interval for a Proportion
low, high = calculate_proportion_ci(count=60, total=150, confidence=0.95)
print(f"95% CI: [{low}%, {high}%]")
```

### 3.3 Demographic & Segment Analysis
```python
from poll_visualizer.analysis import (
    cross_tabulate_by_segment,
    group_rating_summary,
    group_nps_summary,
)

# A. Cross-Tabulation (Row percentages within each segment)
ctab = cross_tabulate_by_segment(df, question_id="CSAT_CHANNEL", normalize="index")
print(ctab)

# B. Group Rating Descriptive Statistics by Segment
group_ratings = group_rating_summary(df, question_id="CSAT_OVERALL", group_col="segment")
print(group_ratings)

# C. Group NPS Breakdown by Segment
group_nps = group_nps_summary(df, question_id="CSAT_NPS", group_col="segment")
print(group_nps)
```

### 3.4 Reusable Plotly Visualizations
All plotting functions return standard `plotly.graph_objects.Figure` instances that can be inspected, exported, or embedded in Streamlit:

```python
from poll_visualizer.visualizations import (
    plot_response_frequencies,
    plot_likert_distribution,
    plot_nps_summary,
    plot_segment_comparison,
    plot_segment_heatmap,
    plot_multiselect_frequencies,
    create_question_chart,
)

# A. Categorical Bar Chart (Horizontal or Vertical)
fig_freq = plot_response_frequencies(df, question_id="CSAT_CHANNEL", orientation="horizontal")

# B. Ordered Likert Rating Distribution (1 to 5)
fig_likert = plot_likert_distribution(df, question_id="CSAT_OVERALL")

# C. NPS Indicator Gauge & Audience Breakdown
fig_nps = plot_nps_summary(df, question_id="CSAT_NPS")

# D. Segment Grouped Bar Comparison
fig_comp = plot_segment_comparison(df, question_id="CSAT_CHANNEL", segment_col="segment")

# E. Demographic Cross-Tabulation Heatmap
fig_heat = plot_segment_heatmap(df, question_id="CSAT_CHANNEL", segment_col="segment")

# F. Multi-Select Frequency Chart
fig_multi = plot_multiselect_frequencies(df, question_id="CSAT_PAIN_POINTS")

# G. Universal Dispatcher (routes based on question_type)
fig_auto = create_question_chart(df, question_id="CSAT_OVERALL")
```

#### Displaying Figures in Streamlit (Future Phase 6 Preview)
In your Streamlit application, render any returned figure with container width enabled:
```python
import streamlit as st
st.plotly_chart(fig_nps, use_container_width=True)
```

### 3.5 Automated Narrative Insights & Reporting
The automated insights and reporting engine translates validated metrics into executive-ready narratives and downloadable formats:

```python
from poll_visualizer.insights import (
    generate_question_insights,
    generate_categorical_insights,
    generate_rating_insights,
    generate_nps_insights,
    generate_multiselect_insights,
    generate_segment_insights,
)
from poll_visualizer.reporting import (
    generate_survey_report_data,
    generate_markdown_report,
    generate_tabular_summary,
)

# A. Generate Structured Narrative Insights for a Question
insight = generate_question_insights(df, question_id="CSAT_OVERALL")
print(f"Summary: {insight.summary}")
for finding in insight.key_findings:
    print(f"- {finding}")

# Access metrics independently from narrative text
mean_score = insight.metrics.get("mean")
top_box_pct = insight.metrics.get("top_box_pct")

# B. Demographic Segment Comparison
seg_res = generate_segment_insights(df, question_id="CSAT_OVERALL", segment_col="segment")
print(seg_res["summary"])

# C. Compile Complete Survey Data Package
survey_data = generate_survey_report_data(df, survey_title="Customer Pulse 2026")
print(f"Overall Completion Rate: {survey_data['overall_data_quality']['completion_rate']}%")

# D. Generate Formatted Markdown Executive Report
markdown_report = generate_markdown_report(df, survey_title="Customer Satisfaction Executive Report")
with open("outputs/reports/csat_report.md", "w", encoding="utf-8") as f:
    f.write(markdown_report)

# E. Generate Flat Tabular Summary for CSV Export
summary_df = generate_tabular_summary(df)
summary_df.to_csv("outputs/exports/survey_summary.csv", index=False)
```

---

## 4. Running the Test Suite
Run the full pytest suite (111 unit and integration tests covering Phases 1 to 6):
```bash
pytest -v
```

---

## 5. Running the Interactive Streamlit Dashboard

### 5.1 Launching the Application
Launch the production Streamlit analytics dashboard:
```bash
streamlit run main.py
```
Open your browser to the local URL (default: `http://localhost:8501`).

### 5.2 Data Ingestion & Source Selection
In the sidebar, choose between:
1. **Built-in Example Dataset**:
   - `Customer Satisfaction (CSAT)` (`data/synthetic/customer_satisfaction.csv`)
   - `Employee Engagement (eNPS)` (`data/synthetic/employee_engagement.csv`)
   - `Product Preferences` (`data/synthetic/product_preferences.csv`)
   *Displays a prominent Simulated Data Notice declaring that findings do not reflect real populations.*
2. **Upload Custom CSV File**:
   - Drag and drop or browse for any long-format survey CSV.
   - Files are validated in memory against the required schema columns (`response_id`, `respondent_id`, `survey_type`, `question_id`, `question_text`, `question_type`, `answer`, `response_timestamp`).
   - Actionable error banners report any missing columns, out-of-bounds ratings/NPS, or duplicate response IDs without crashing the application.
   - An optional checkbox allows users to declare whether the uploaded data is synthetic.

### 5.3 Dashboard Navigation & Features

| Tab | Key Functionality |
| :--- | :--- |
| **📊 Overview** | High-level KPI cards (Total Records, Unique Respondents, Total Questions, Completion Rate %), provenance notice banner, and full survey question inventory table. |
| **🔍 Question Analysis** | Question selector with formatted labels, question type badge, interactive Plotly visualization, primary metric highlight cards (Mean/Median, NPS Breakdown, Top Choice, Multi-Select Sum), and rule-based narrative summary cards. |
| **👥 Segment Analysis** | Demographic segment dimension selector, question comparator, grouped/stacked bar charts, cross-tabulation heatmaps, contingency tables, small cohort warnings ($n < 10$), and non-causal observation policy notices. |
| **💡 Automated Insights** | Executive analytical narrative for the full survey, data quality statuses, and collapsible question-by-question finding cards. |
| **🛡️ Data Quality** | Schema validation badge (`PASSED` / `FAILED`), diagnostics breakdown (skipped answers, duplicates, bounds), question-level completeness breakdown table, and non-destructive cleaning preview (`cleaning.py`) with transformation audit log. |
| **📥 Export Reports** | One-click downloads for executive Markdown reports (`.md`) and flat tabular question summary spreadsheets (`.csv`) with full provenance disclaimers preserved. |

