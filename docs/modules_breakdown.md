# Modules & Components Breakdown

## 1. Directory Structure

```text
Poll Results Visualizer/
├── .github/
│   └── workflows/
│       └── tests.yml         # GitHub Actions CI workflow
├── data/
│   ├── raw/                  # Immutable original survey/poll datasets
│   ├── processed/            # Cleaned, standardized datasets
│   └── synthetic/            # Sample synthetic datasets for testing/demo
├── docs/                     # Technical documentation & project knowledge
│   ├── DATA_DICTIONARY.md
│   ├── METHODOLOGY.md
│   ├── USER_GUIDE.md
│   ├── README.md
│   ├── architecture.md
│   ├── data_pipeline.md
│   ├── modules_breakdown.md
│   ├── model_specifications.md
│   └── execution_log.md
├── images/                   # Badges, screenshots, and architecture diagrams
├── notebooks/                # Exploratory Data Analysis & experiments
├── outputs/
│   ├── reports/              # Exported summary reports
│   └── exports/              # Exported charts and processed data slices
├── scripts/                  # Utility and standalone operational scripts
├── src/
│   └── poll_visualizer/      # Main Python package
│       ├── __init__.py       # Package initializer & versioning
│       ├── data_loader.py    # CSV ingestion and file handling
│       ├── validation.py     # Schema verification & data-quality checks
│       ├── cleaning.py       # Cleaning rules & normalization
│       ├── metrics.py        # Frequency, percentage, and statistical calculations
│       ├── analysis.py       # Group comparisons & cross-tabulations
│       ├── visualizations.py # Reusable Plotly charts
│       ├── insights.py       # Automated data-driven summaries
│       └── reporting.py      # Report and export preparation
├── tests/                    # Pytest test suite
│   ├── __init__.py
│   └── test_structure.py     # Structure, import, and configuration checks
├── .gitignore                # Git exclusions
├── main.py                   # Primary Streamlit application entry point
├── pyproject.toml            # Project packaging & pytest configuration
├── README.md                 # Root portfolio README
└── requirements.txt          # Python dependencies
```

---

## 2. Module Responsibilities & Design Contracts

| Module | Primary Responsibility | Planned Key Interfaces |
| :--- | :--- | :--- |
| `data_loader.py` | CSV ingestion & file management | `load_csv(filepath_or_buffer)` |
| `validation.py` | Schema validation, missingness checks, type assertions | `validate_schema(df)`, `check_data_quality(df)` |
| `cleaning.py` | Data normalization, handling missing values, filtering | `clean_poll_data(df)` |
| `metrics.py` | Response percentages, margins of error, sample statistics | `calculate_frequencies(df, column)`, `compute_moe(p, n)` |
| `analysis.py` | Demographic cross-tabulations, comparative analysis | `compare_groups(df, group_col, target_col)` |
| `visualizations.py` | Reusable, interactive Plotly charts | `plot_distribution()`, `plot_comparison()`, `plot_timeline()` |
| `insights.py` | Rule-based summaries, lead calculations, trend detection | `generate_insights(summary_df)` |
| `reporting.py` | Exporting reports, markdown/PDF/CSV report packaging | `export_report()`, `save_summary()` |
| `main.py` | Streamlit dashboard user interface & session state controller | Application entry point (`streamlit run main.py`) |
