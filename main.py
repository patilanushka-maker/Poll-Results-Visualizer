"""Poll Results Visualizer - Interactive Streamlit Dashboard Application.

Launch command:
    streamlit run main.py

Phase 6 implementation providing multi-tab exploratory analytics, question-level
visualizations, demographic segment analysis, automated narrative insights,
data-quality diagnostics, and exportable reports for general-purpose survey data.
"""

from pathlib import Path
from typing import Any, Optional
import pandas as pd
import streamlit as st

from poll_visualizer.analysis import (
    cross_tabulate_by_segment,
    group_nps_summary,
    group_rating_summary,
)
from poll_visualizer.cleaning import clean_survey_data
from poll_visualizer.data_loader import DataLoaderError, EmptyFileError, MissingFileError, load_csv
from poll_visualizer.insights import (
    QuestionInsight,
    generate_question_insights,
)
from poll_visualizer.metrics import _is_missing_value
from poll_visualizer.reporting import (
    generate_markdown_report,
    generate_survey_report_data,
    generate_tabular_summary,
)
from poll_visualizer.validation import (
    REQUIRED_COLUMNS,
    ValidationResult,
    validate_survey_data,
)
from poll_visualizer.visualizations import (
    create_question_chart,
    plot_segment_comparison,
    plot_segment_heatmap,
)

# Canonical synthetic datasets mapping
CANONICAL_DATASETS: dict[str, str] = {
    "Customer Satisfaction (CSAT)": "customer_satisfaction.csv",
    "Employee Engagement (eNPS)": "employee_engagement.csv",
    "Product Preferences": "product_preferences.csv",
}

import re

SYNTHETIC_WARNING_TEXT: str = (
    "⚠️ **Simulated Data Notice**: This dataset was generated deterministically for testing, "
    "pipeline validation, and portfolio demonstration. Findings do not reflect empirical "
    "real-world opinions or organizations."
)

UNVERIFIED_DATA_TEXT: str = (
    "ℹ️ **Data Provenance Notice**: Analysis is performed on user-uploaded data with unverified "
    "real-world provenance. Findings describe the provided sample only and do not assert generalizability."
)


def sanitize_error_message(err: Any) -> str:
    """Sanitize error messages to prevent exposing local filesystem paths.

    Parameters
    ----------
    err : Any
        Exception object or error message string.

    Returns
    -------
    str
        Sanitized error string.
    """
    text = str(err)
    # Remove Windows file paths (e.g., C:\... or D:\...)
    text = re.sub(r"[a-zA-Z]:\\[^:\n\r\t\"']+", "[local_file_path]", text)
    # Remove POSIX/Unix file paths
    text = re.sub(r"/(?:Users|home|tmp|var|etc)/[^:\n\r\t\"']+", "[local_file_path]", text)
    return text


def get_synthetic_dataset_path(filename: str) -> Path:
    """Resolve absolute path to a canonical synthetic dataset.

    Parameters
    ----------
    filename : str
        Dataset filename.

    Returns
    -------
    Path
        Resolved Path object.
    """
    return Path(__file__).resolve().parent / "data" / "synthetic" / filename


def compute_overview_metrics(df: pd.DataFrame) -> dict[str, Any]:
    """Compute high-level survey completeness, item response rate, and respondent completion.

    Distinguishes:
    - Item Response Rate: proportion of answered long-format records (valid_answers / total_records).
    - Respondent Completion Rate: proportion of respondents who answered all questions without skipping.

    Parameters
    ----------
    df : pd.DataFrame
        Survey dataset in long-format.

    Returns
    -------
    dict[str, Any]
        Dictionary of overview metrics.
    """
    if df is None or df.empty:
        return {
            "total_records": 0,
            "total_respondents": 0,
            "total_questions": 0,
            "survey_type": "Unknown",
            "completion_rate": 0.0,
            "item_response_rate": 0.0,
            "respondent_completion_rate": 0.0,
            "complete_respondents": 0,
            "missing_answers": 0,
            "valid_answers": 0,
        }

    total_records = len(df)
    total_respondents = int(df["respondent_id"].nunique()) if "respondent_id" in df.columns else total_records
    total_questions = int(df["question_id"].nunique()) if "question_id" in df.columns else 0
    survey_type = str(df["survey_type"].iloc[0]) if "survey_type" in df.columns else "general_survey"

    missing_mask = df["answer"].apply(_is_missing_value) if "answer" in df.columns else pd.Series([False] * total_records)
    missing_count = int(missing_mask.sum())
    valid_count = total_records - missing_count
    item_response_rate = round((valid_count / total_records) * 100.0, 1) if total_records > 0 else 0.0

    # Calculate true respondent-level survey completion rate
    if "respondent_id" in df.columns and total_respondents > 0 and "answer" in df.columns:
        respondents_with_missing = set(df.loc[missing_mask, "respondent_id"].dropna().unique())
        complete_respondents = total_respondents - len(respondents_with_missing)
        respondent_completion_rate = round((complete_respondents / total_respondents) * 100.0, 1)
    else:
        complete_respondents = total_respondents
        respondent_completion_rate = 100.0 if total_records > 0 else 0.0

    return {
        "total_records": total_records,
        "total_respondents": total_respondents,
        "total_questions": total_questions,
        "survey_type": survey_type.replace("_", " ").title(),
        "completion_rate": item_response_rate,  # Retained for backward compatibility
        "item_response_rate": item_response_rate,
        "respondent_completion_rate": respondent_completion_rate,
        "complete_respondents": complete_respondents,
        "missing_answers": missing_count,
        "valid_answers": valid_count,
    }


def build_question_inventory(df: pd.DataFrame) -> pd.DataFrame:
    """Build a summary inventory table for all questions in the survey.

    Parameters
    ----------
    df : pd.DataFrame
        Survey dataset in long-format.

    Returns
    -------
    pd.DataFrame
        Summary table with question details and response rates.
    """
    if df is None or df.empty or "question_id" not in df.columns:
        return pd.DataFrame(
            columns=["Question ID", "Question Text", "Type", "Total Rows", "Valid Answers", "Missing", "Completion Rate"]
        )

    rows: list[dict[str, Any]] = []
    for q_id in df["question_id"].unique():
        sub = df[df["question_id"] == q_id]
        total_q = len(sub)
        missing_cnt = int(sub["answer"].apply(_is_missing_value).sum()) if "answer" in sub.columns else 0
        valid_cnt = total_q - missing_cnt
        pct = round((valid_cnt / total_q) * 100.0, 1) if total_q > 0 else 0.0

        q_text = str(sub["question_text"].iloc[0]) if "question_text" in sub.columns else str(q_id)
        q_type = str(sub["question_type"].iloc[0]) if "question_type" in sub.columns else "unknown"

        rows.append(
            {
                "Question ID": str(q_id),
                "Question Text": q_text,
                "Type": q_type,
                "Total Rows": total_q,
                "Valid Answers": valid_cnt,
                "Missing": missing_cnt,
                "Completion Rate": f"{pct:.1f}%",
            }
        )

    return pd.DataFrame(rows)


def get_available_segments(df: pd.DataFrame) -> list[str]:
    """Identify candidate demographic segment columns in the dataset.

    Parameters
    ----------
    df : pd.DataFrame
        Survey dataset.

    Returns
    -------
    list[str]
        List of column names suitable for demographic segmentation.
    """
    if df is None or df.empty:
        return []

    excluded = {
        "response_id",
        "respondent_id",
        "question_id",
        "question_text",
        "question_type",
        "answer",
        "response_timestamp",
        "weight",
    }
    candidates = [col for col in df.columns if col not in excluded]
    # Prioritize 'segment' first if present
    if "segment" in candidates:
        candidates.remove("segment")
        return ["segment"] + candidates
    return candidates


def load_selected_dataset(
    source_type: str,
    dataset_name: Optional[str] = None,
    uploaded_file: Optional[Any] = None,
    marked_synthetic: bool = False,
) -> tuple[Optional[pd.DataFrame], Optional[str], bool, Optional[ValidationResult]]:
    """Safe dataset loading and validation handler.

    Parameters
    ----------
    source_type : str
        'Built-in Example Dataset' or 'Upload Custom CSV File'.
    dataset_name : str, optional
        Name of built-in dataset.
    uploaded_file : Any, optional
        Streamlit UploadedFile buffer.
    marked_synthetic : bool, optional
        Flag indicating if user marked uploaded file as synthetic.

    Returns
    -------
    tuple[Optional[pd.DataFrame], Optional[str], bool, Optional[ValidationResult]]
        Tuple of (df, error_message, is_synthetic, validation_result).
    """
    if source_type == "Built-in Example Dataset":
        target_file = CANONICAL_DATASETS.get(dataset_name or "", "customer_satisfaction.csv")
        file_path = get_synthetic_dataset_path(target_file)
        try:
            df = load_csv(file_path)
            val_res = validate_survey_data(df)
            return df, None, True, val_res
        except Exception as err:
            return None, f"Failed to load built-in dataset '{target_file}': {sanitize_error_message(err)}", True, None

    # User uploaded file
    if uploaded_file is None:
        return None, None, False, None

    try:
        df = load_csv(uploaded_file)
        val_res = validate_survey_data(df)
        if not val_res.is_valid:
            err_msg = "Uploaded file failed schema validation. Please review the errors in the Data Quality tab."
            return df, err_msg, marked_synthetic, val_res
        return df, None, marked_synthetic, val_res
    except EmptyFileError as err:
        return None, f"Empty File Error: {sanitize_error_message(err)}", marked_synthetic, None
    except DataLoaderError as err:
        return None, f"Data Loading Error: {sanitize_error_message(err)}", marked_synthetic, None
    except Exception as err:
        return None, f"Unexpected error parsing uploaded CSV: {sanitize_error_message(err)}", marked_synthetic, None


def render_overview_tab(df: pd.DataFrame, is_synthetic: bool) -> None:
    """Render the Overview tab with key metrics, provenance notices, and inventory."""
    st.subheader("📊 Executive Overview & Survey Inventory")

    if is_synthetic:
        st.warning(SYNTHETIC_WARNING_TEXT)
    else:
        st.info(UNVERIFIED_DATA_TEXT)

    metrics = compute_overview_metrics(df)

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total Records", f"{metrics['total_records']:,}", help="Total long-format response rows in dataset.")
    c2.metric("Distinct Respondents", f"{metrics['total_respondents']:,}", help="Unique participants based on respondent_id.")
    c3.metric("Total Questions", f"{metrics['total_questions']:,}", help="Unique survey items evaluated.")
    c4.metric("Survey Domain", metrics["survey_type"], help="Domain classification recorded in dataset.")
    c5.metric("Item Response Rate", f"{metrics['item_response_rate']}%", help="Proportion of answered response items (valid_answers / total_records).")
    c6.metric("Respondent Completion", f"{metrics['respondent_completion_rate']}%", help="Proportion of respondents who answered all questions without skipping.")

    st.markdown("---")
    st.markdown("### 📋 Survey Question Inventory")
    st.caption("Detailed inventory of all questions, functional types, response volumes, and completion completeness.")

    inventory_df = build_question_inventory(df)
    st.dataframe(inventory_df, use_container_width=True, hide_index=True)


def render_question_tab(df: pd.DataFrame) -> None:
    """Render the Question Analysis tab with interactive charts and narrative summaries."""
    st.subheader("🔍 Single Question Deep-Dive")

    if "question_id" not in df.columns or df["question_id"].nunique() == 0:
        st.warning("No question identifiers found in dataset.")
        return

    q_ids = list(df["question_id"].unique())

    # Build question selector labels
    def format_q_label(qid: str) -> str:
        sub = df[df["question_id"] == qid]
        if sub.empty:
            return qid
        q_text = str(sub["question_text"].iloc[0])
        q_type = str(sub["question_type"].iloc[0]).upper()
        truncated = q_text if len(q_text) <= 60 else q_text[:57] + "..."
        return f"[{q_type}] {qid} — {truncated}"

    selected_qid = st.selectbox(
        "Select Question to Analyze",
        options=q_ids,
        format_func=format_q_label,
        key="question_select_box",
    )

    q_sub = df[df["question_id"] == selected_qid]
    if q_sub.empty:
        if q_ids:
            selected_qid = q_ids[0]
            q_sub = df[df["question_id"] == selected_qid]
        else:
            st.warning("No questions found in dataset.")
            return
    q_text = str(q_sub["question_text"].iloc[0]) if "question_text" in q_sub.columns else str(selected_qid)
    q_type = str(q_sub["question_type"].iloc[0]).strip().lower() if "question_type" in q_sub.columns else "unknown"

    st.markdown(f"### {selected_qid}: {q_text}")
    st.caption(f"**Functional Question Type:** `{q_type}` | **Total Records:** {len(q_sub):,}")

    # Generate insights and metrics
    try:
        insight = generate_question_insights(df, selected_qid)
    except Exception as err:
        st.error(f"Could not compile insights for question '{selected_qid}': {err}")
        return

    # 1. Plotly Visualization
    st.markdown("#### Interactive Distribution")
    try:
        fig = create_question_chart(df, selected_qid)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as err:
        st.error(f"Failed to generate visualization for question '{selected_qid}': {err}")

    # 2. Key Numeric Metrics Cards
    st.markdown("#### Primary Metric Summary")
    q_metrics = insight.metrics

    if q_type == "rating":
        m1, m2, m3, m4 = st.columns(4)
        mean_val = q_metrics.get("mean")
        median_val = q_metrics.get("median")
        top_box = q_metrics.get("top_box_pct", 0.0)
        bot_box = q_metrics.get("bottom_box_pct", 0.0)
        m1.metric("Mean Rating (1-5)", f"{mean_val:.2f}" if mean_val is not None else "N/A")
        m2.metric("Median Rating", f"{median_val:.1f}" if median_val is not None else "N/A")
        m3.metric("Favorable (Top-Box: 4-5)", f"{top_box:.1f}%")
        m4.metric("Unfavorable (Bottom-Box: 1-2)", f"{bot_box:.1f}%")

    elif q_type == "nps":
        m1, m2, m3, m4, m5 = st.columns(5)
        nps_score = q_metrics.get("nps_score")
        sign = "+" if (nps_score is not None and nps_score > 0) else ""
        tier = q_metrics.get("tier_label", "Neutral")
        m1.metric("Net Promoter Score", f"{sign}{nps_score:.1f}" if nps_score is not None else "N/A")
        m2.metric("Sentiment Tier", tier)
        m3.metric("Promoters (9-10)", f"{q_metrics.get('promoter_pct', 0.0):.1f}%")
        m4.metric("Passives (7-8)", f"{q_metrics.get('passive_pct', 0.0):.1f}%")
        m5.metric("Detractors (0-6)", f"{q_metrics.get('detractor_pct', 0.0):.1f}%")

    elif q_type == "single_choice":
        m1, m2, m3 = st.columns(3)
        leader = q_metrics.get("leader", "Tie")
        leader_pct = q_metrics.get("leader_percentage", 0.0)
        valid_cnt = q_metrics.get("valid_count", 0)
        m1.metric("Plurality / Majority Choice", str(leader))
        m2.metric("Selection Share", f"{leader_pct:.1f}%")
        m3.metric("Valid Answering Count", f"{valid_cnt:,}")

    elif q_type == "multi_select":
        m1, m2, m3 = st.columns(3)
        top_opt = q_metrics.get("top_option", "N/A")
        top_pct = q_metrics.get("top_percentage", 0.0)
        pct_sum = q_metrics.get("percentage_sum", 0.0)
        m1.metric("Top Selected Option", str(top_opt))
        m2.metric("Selection Share", f"{top_pct:.1f}%")
        m3.metric("Option Percentages Sum", f"{pct_sum:.1f}%", help="Percentages sum to > 100% because respondents can select multiple options.")

    elif q_type == "text":
        m1, m2 = st.columns(2)
        valid_cnt = q_metrics.get("valid_count", 0)
        missing_cnt = q_metrics.get("missing_count", 0)
        m1.metric("Text Submissions", f"{valid_cnt:,}")
        m2.metric("Omitted / Skipped", f"{missing_cnt:,}")

    # 3. Narrative Insight Card
    st.markdown("#### Automated Narrative Insight")
    st.info(f"**Executive Summary:** {insight.summary}")

    if insight.key_findings:
        st.markdown("**Key Observations:**")
        for finding in insight.key_findings:
            st.markdown(f"- {finding}")

    if insight.warnings:
        st.markdown("**Analytical Caveats & Data Hygiene Notes:**")
        for warn in insight.warnings:
            st.warning(f"⚠️ {warn}")

    st.caption(
        "**Per-Question Denominator Note:** Percentages are strictly calculated out of respondents who provided "
        "a valid answer to this question. Missing/skipped records are excluded from denominators."
    )


def render_segment_tab(df: pd.DataFrame) -> None:
    """Render the Segment Analysis tab with cross-tabulations, heatmaps, and group comparisons."""
    st.subheader("👥 Demographic Segment Analysis")

    candidate_segments = get_available_segments(df)
    if not candidate_segments:
        st.warning(
            "No demographic segmentation column was detected in this dataset. "
            "To enable cohort comparisons, ensure your survey dataset contains a 'segment' column."
        )
        return

    c1, c2, c3 = st.columns([1, 2, 1])
    selected_seg = c1.selectbox("Demographic Column", candidate_segments, key="seg_col_select")
    q_ids = list(df["question_id"].unique()) if "question_id" in df.columns else []

    def format_q_label(qid: str) -> str:
        sub = df[df["question_id"] == qid]
        if sub.empty:
            return qid
        q_text = str(sub["question_text"].iloc[0])
        return f"{qid} — {q_text[:45]}..."

    selected_qid = c2.selectbox("Question to Compare", q_ids, format_func=format_q_label, key="seg_q_select")
    q_sub = df[df["question_id"] == selected_qid]
    if q_sub.empty:
        if q_ids:
            selected_qid = q_ids[0]
            q_sub = df[df["question_id"] == selected_qid]
        else:
            st.warning("No questions found in dataset.")
            return

    view_type = c3.radio("Visualization Mode", ["Grouped Bar Chart", "Stacked Bar Chart", "Cross-Tab Heatmap"], key="seg_view_type")

    st.info(
        "📌 **Descriptive Observation Safeguard**: Group comparisons reflect observed sample distributions. "
        "They do not assert causality or statistical significance without formal inferential hypothesis testing."
    )

    # Check for small cohort sizes
    seg_counts = df[df["question_id"] == selected_qid][selected_seg].value_counts()
    small_cohorts = seg_counts[seg_counts < 10]
    if not small_cohorts.empty:
        small_names = ", ".join(f"'{name}' (n={cnt})" for name, cnt in small_cohorts.items())
        st.warning(
            f"⚠️ **Small Sample Alert**: One or more demographic cohorts contain fewer than 10 respondents: "
            f"{small_names}. Sample metrics in small cohorts exhibit high sampling variance."
        )

    # Render Visualizations
    st.markdown("#### Demographic Visualization")
    try:
        if view_type == "Grouped Bar Chart":
            fig = plot_segment_comparison(df, selected_qid, segment_col=selected_seg, barmode="group", normalize="index")
            st.plotly_chart(fig, use_container_width=True)
        elif view_type == "Stacked Bar Chart":
            fig = plot_segment_comparison(df, selected_qid, segment_col=selected_seg, barmode="stack", normalize="index")
            st.plotly_chart(fig, use_container_width=True)
        else:
            fig = plot_segment_heatmap(df, selected_qid, segment_col=selected_seg, normalize="index")
            st.plotly_chart(fig, use_container_width=True)
    except Exception as err:
        st.error(f"Failed to generate segment chart: {err}")

    # Render Tabular Group Breakdown
    st.markdown("#### Contingency Table & Group Descriptive Summary")
    q_type = str(df[df["question_id"] == selected_qid]["question_type"].iloc[0]).strip().lower()

    try:
        if q_type == "rating":
            group_stats = group_rating_summary(df, selected_qid, group_col=selected_seg)
            st.dataframe(group_stats, use_container_width=True)
        elif q_type == "nps":
            group_stats = group_nps_summary(df, selected_qid, group_col=selected_seg)
            st.dataframe(group_stats, use_container_width=True)
        else:
            ctab = cross_tabulate_by_segment(df, selected_qid, segment_col=selected_seg, normalize="index")
            st.dataframe(ctab, use_container_width=True)
    except Exception as err:
        st.error(f"Failed to compute group summary table: {err}")


def render_insights_tab(df: pd.DataFrame, is_synthetic: bool) -> None:
    """Render the Automated Narrative Insights tab."""
    st.subheader("💡 Automated Narrative Insights Engine")

    if is_synthetic:
        st.warning(SYNTHETIC_WARNING_TEXT)
    else:
        st.info(UNVERIFIED_DATA_TEXT)

    try:
        report_data = generate_survey_report_data(df, is_synthetic=is_synthetic)
    except Exception as err:
        st.error(f"Failed to compile survey-level insight data: {err}")
        return

    st.markdown("### 📋 Executive Summary")
    st.write(
        f"**Survey Domain:** `{report_data['survey_type']}` | "
        f"**Quality Status:** `{report_data['overall_data_quality']['status']}` | "
        f"**Completion Rate:** `{report_data['overall_data_quality']['completion_rate']}%`"
    )

    for note in report_data["overall_data_quality"]["notes"]:
        st.markdown(f"- {note}")

    st.markdown("---")
    st.markdown("### 🔎 Question-by-Question Narrative Findings")

    insights_list = report_data.get("question_insights", [])
    if not insights_list:
        st.info("No question insights were compiled.")
        return

    for idx, q_item in enumerate(insights_list, start=1):
        with st.expander(f"{idx}. [{q_item['question_type'].upper()}] {q_item['question_id']} — {q_item['question_text']}", expanded=(idx <= 2)):
            st.markdown(f"> **Executive Summary:** {q_item['summary']}")

            if q_item.get("key_findings"):
                st.markdown("**Key Observations:**")
                for f in q_item["key_findings"]:
                    st.markdown(f"- {f}")

            if q_item.get("warnings"):
                st.markdown("**Analytical Notes & Caveats:**")
                for w in q_item["warnings"]:
                    st.warning(f"⚠️ {w}")

            metrics = q_item.get("metrics", {})
            if "segment_summary" in metrics:
                st.markdown(f"**Demographic Segment Insight:** {metrics['segment_summary']}")


def render_quality_tab(df: pd.DataFrame, val_res: Optional[ValidationResult]) -> None:
    """Render the Data Quality and Hygiene tab with validation diagnostics and cleaning preview."""
    st.subheader("🛡️ Data Quality & Schema Hygiene Diagnostics")

    if val_res is None:
        val_res = validate_survey_data(df)

    # 1. Validation Status Badge
    if val_res.is_valid:
        st.success(f"✅ **Validation Status: PASSED** — Dataset complies with the survey schema ({len(df):,} rows evaluated).")
    else:
        st.error(f"❌ **Validation Status: FAILED** — Encountered {len(val_res.errors)} structural error(s).")
        for err in val_res.errors:
            st.error(f"- [ERROR] {err}")

    if val_res.warnings:
        with st.expander("⚠️ Validation Warnings & Hygiene Flags", expanded=True):
            for warn in val_res.warnings:
                st.markdown(f"- {warn}")

    st.markdown("---")
    st.markdown("### 📊 Question-Level Data Completeness Breakdown")

    inventory_df = build_question_inventory(df)
    st.dataframe(inventory_df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### 🧼 Non-Destructive Data Cleaning & Standardization")
    st.caption(
        "Preview non-destructive standardization rules (whitespace trimming, lowercase question types, "
        "and missing segment label normalization). The original loaded dataset remains immutable in memory."
    )

    if st.button("Preview Cleaned Dataset & Audit Log", key="clean_preview_btn"):
        cleaned_df, audit = clean_survey_data(df)
        st.markdown("**Cleaning Audit Log:**")
        for step in audit["transformations"]:
            st.markdown(f"- {step}")

        st.markdown("**Standardized Data Preview (First 5 rows):**")
        st.dataframe(cleaned_df.head(5), use_container_width=True)


def render_export_tab(df: pd.DataFrame, is_synthetic: bool) -> None:
    """Render the Export Reports tab providing Markdown report and CSV summary downloads."""
    st.subheader("📥 Export Survey Reports & Tabular Summaries")

    if is_synthetic:
        st.warning(SYNTHETIC_WARNING_TEXT)
    else:
        st.info(UNVERIFIED_DATA_TEXT)

    survey_type = str(df["survey_type"].iloc[0]) if (df is not None and not df.empty and "survey_type" in df.columns) else "survey"
    default_title = f"{survey_type.replace('_', ' ').title()} Executive Report"

    report_title = st.text_input("Report Title", value=default_title, key="report_title_input")

    c1, c2 = st.columns(2)

    # 1. Markdown Survey Report Export
    with c1:
        st.markdown("#### 📄 Executive Markdown Report")
        st.write("Complete executive analytical summary including executive tables, findings, and methodology.")

        try:
            report_md = generate_markdown_report(df, survey_title=report_title, is_synthetic=is_synthetic)
            with st.expander("Preview Markdown Document"):
                st.text_area("Report Markdown Preview", value=report_md[:1500] + "\n\n... (truncated preview)", height=250, disabled=True)

            st.download_button(
                label="⬇️ Download Markdown Report (.md)",
                data=report_md,
                file_name=f"{survey_type}_executive_report.md",
                mime="text/markdown",
                key="dl_markdown_btn",
            )
        except Exception as err:
            st.error(f"Failed to generate Markdown report: {err}")

    # 2. CSV Tabular Summary Export
    with c2:
        st.markdown("#### 📊 Tabular Summary Table (CSV)")
        st.write("Flat question-by-question summary table suitable for spreadsheet review, presentations, or BI tools.")

        try:
            summary_df = generate_tabular_summary(df)
            with st.expander("Preview Tabular Summary"):
                st.dataframe(summary_df, use_container_width=True)

            csv_bytes = summary_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇️ Download Summary Table (.csv)",
                data=csv_bytes,
                file_name=f"{survey_type}_summary.csv",
                mime="text/csv",
                key="dl_csv_btn",
            )
        except Exception as err:
            st.error(f"Failed to generate tabular CSV summary: {err}")


def main() -> None:
    """Render the primary Streamlit application."""
    st.set_page_config(
        page_title="Poll Results Visualizer",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("📊 Poll Results Visualizer")
    st.markdown(
        "A beginner-friendly, evidence-based survey and poll analytics platform. "
        "Delivers automated data validation, statistical metrics, Plotly visualizations, "
        "demographic comparisons, and automated narrative reporting."
    )

    # Sidebar: Data Source Selection
    st.sidebar.header("📁 Data Source Selection")
    source_type = st.sidebar.radio(
        "Choose Data Source",
        options=["Built-in Example Dataset", "Upload Custom CSV File"],
        index=0,
        key="source_type_radio",
    )

    dataset_name: Optional[str] = None
    uploaded_file: Optional[Any] = None
    marked_synthetic: bool = False

    if source_type == "Built-in Example Dataset":
        dataset_name = st.sidebar.selectbox(
            "Select Example Dataset",
            options=list(CANONICAL_DATASETS.keys()),
            index=0,
            key="builtin_dataset_select",
        )
        st.sidebar.caption("Canonical synthetic datasets covering CSAT, eNPS, and Product Preferences.")
    else:
        uploaded_file = st.sidebar.file_uploader(
            "Upload Long-Format Survey CSV",
            type=["csv"],
            help="Upload a CSV file conforming to the long-format survey schema.",
            key="survey_file_uploader",
        )
        marked_synthetic = st.sidebar.checkbox(
            "Mark uploaded data as synthetic / simulated",
            value=False,
            help="Check if this dataset was generated or simulated for testing.",
            key="marked_synthetic_checkbox",
        )
        with st.sidebar.expander("Required Schema Columns"):
            st.markdown(
                "- `response_id`: Unique response ID\n"
                "- `respondent_id`: Participant ID\n"
                "- `survey_type`: Survey domain tag\n"
                "- `question_id`: Question ID\n"
                "- `question_text`: Prompt text\n"
                "- `question_type`: Functional type (`single_choice`, `rating`, `nps`, `multi_select`, `text`)\n"
                "- `answer`: Response value\n"
                "- `response_timestamp`: ISO 8601 timestamp\n"
                "- `segment`: Optional demographic label\n"
                "- `weight`: Optional numeric weight"
            )

    # Load and validate dataset
    df, err_msg, is_synthetic, val_res = load_selected_dataset(
        source_type=source_type,
        dataset_name=dataset_name,
        uploaded_file=uploaded_file,
        marked_synthetic=marked_synthetic,
    )

    if err_msg:
        st.error(err_msg)
        if val_res and not val_res.is_valid:
            with st.expander("View Schema Validation Errors", expanded=True):
                for e in val_res.errors:
                    st.error(f"- {e}")
        return

    if df is None:
        st.info("👆 Please select a built-in dataset or upload a survey CSV from the sidebar to begin analysis.")
        return

    # Render primary application tabs
    tab_overview, tab_question, tab_segment, tab_insights, tab_quality, tab_export = st.tabs(
        [
            "📊 Overview",
            "🔍 Question Analysis",
            "👥 Segment Analysis",
            "💡 Automated Insights",
            "🛡️ Data Quality",
            "📥 Export Reports",
        ]
    )

    with tab_overview:
        render_overview_tab(df, is_synthetic=is_synthetic)

    with tab_question:
        render_question_tab(df)

    with tab_segment:
        render_segment_tab(df)

    with tab_insights:
        render_insights_tab(df, is_synthetic=is_synthetic)

    with tab_quality:
        render_quality_tab(df, val_res=val_res)

    with tab_export:
        render_export_tab(df, is_synthetic=is_synthetic)


if __name__ == "__main__":
    main()
