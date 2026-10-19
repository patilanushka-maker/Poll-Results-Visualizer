"""Automated reporting and summary export module for Poll Results Visualizer.

Provides survey-level executive report compilation, Markdown document generation,
and tabular summary exports for downstream analysis, presentations, and CSV downloads.
"""

from datetime import datetime
from typing import Any, Optional, Union
import pandas as pd

from poll_visualizer.insights import generate_question_insights
from poll_visualizer.metrics import _is_missing_value

# Known synthetic survey domains
KNOWN_SYNTHETIC_TYPES: set[str] = {
    "customer_satisfaction",
    "employee_engagement",
    "product_preferences",
}

SYNTHETIC_DISCLAIMER: str = (
    "> [!NOTE]\n"
    "> **Simulated Data Notice**: This report was compiled from a deterministically "
    "> generated synthetic dataset created for algorithmic verification, pipeline testing, "
    "> and portfolio demonstration. Findings do not reflect empirical real-world public "
    "> or organizational sentiment."
)


def _detect_synthetic(df: pd.DataFrame, is_synthetic_override: Optional[bool]) -> bool:
    """Helper determining whether dataset is of synthetic origin."""
    if is_synthetic_override is not None:
        return bool(is_synthetic_override)
    if not df.empty and "survey_type" in df.columns:
        types_in_df = set(df["survey_type"].dropna().unique())
        if types_in_df.intersection(KNOWN_SYNTHETIC_TYPES):
            return True
    return False


def generate_survey_report_data(
    df: pd.DataFrame,
    survey_title: Optional[str] = None,
    is_synthetic: Optional[bool] = None,
) -> dict[str, Any]:
    """Compile survey-level insights, metadata, and quality summaries into a unified data structure.

    Parameters
    ----------
    df : pd.DataFrame
        Survey dataset in long-format.
    survey_title : str, optional
        Human-readable survey title.
    is_synthetic : bool, optional
        Flag explicitly declaring whether data is synthetic. If None, auto-detected.

    Returns
    -------
    dict[str, Any]
        Structured dictionary containing survey metadata, question insights,
        and data-quality summaries.
    """
    if df is None or df.empty:
        return {
            "survey_title": survey_title or "Survey Summary Report",
            "survey_type": "unknown",
            "total_rows": 0,
            "total_respondents": 0,
            "total_questions": 0,
            "is_synthetic": bool(is_synthetic),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "question_insights": [],
            "overall_data_quality": {"status": "EMPTY", "notes": ["Dataset contains 0 rows."]},
        }

    is_simulated = _detect_synthetic(df, is_synthetic)
    survey_type = str(df["survey_type"].iloc[0]) if "survey_type" in df.columns else "general_survey"
    default_title = survey_type.replace("_", " ").title() + " Analysis Report"
    title = survey_title or default_title

    total_rows = len(df)
    total_respondents = int(df["respondent_id"].nunique()) if "respondent_id" in df.columns else total_rows
    question_ids = list(df["question_id"].unique()) if "question_id" in df.columns else []

    # Compile individual question insights
    question_insights = []
    total_missing_answers = 0
    total_valid_answers = 0

    for q_id in question_ids:
        try:
            insight = generate_question_insights(df, str(q_id))
            question_insights.append(insight.to_dict())

            q_metrics = insight.metrics
            total_missing_answers += q_metrics.get("missing_count", 0)
            total_valid_answers += q_metrics.get("valid_count", 0)
        except Exception as err:
            question_insights.append(
                {
                    "question_id": str(q_id),
                    "question_text": "Error compiling question insight",
                    "question_type": "unknown",
                    "summary": f"Could not generate insights: {err}",
                    "key_findings": [],
                    "warnings": [str(err)],
                    "metrics": {},
                    "data_quality_notes": [],
                }
            )

    overall_completion_rate = (
        round((total_valid_answers / total_rows) * 100.0, 1) if total_rows > 0 else 0.0
    )

    quality_status = "HEALTHY" if overall_completion_rate >= 90.0 else ("MODERATE" if overall_completion_rate >= 75.0 else "POOR")
    quality_notes = [
        f"Overall dataset item response rate: {overall_completion_rate:.1f}% (answered records / total records)",
        f"Total answered response items: {total_valid_answers:,}",
        f"Total skipped/missing response items: {total_missing_answers:,}",
    ]

    return {
        "survey_title": title,
        "survey_type": survey_type,
        "total_rows": total_rows,
        "total_respondents": total_respondents,
        "total_questions": len(question_ids),
        "is_synthetic": is_simulated,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "question_insights": question_insights,
        "overall_data_quality": {
            "status": quality_status,
            "completion_rate": overall_completion_rate,
            "notes": quality_notes,
        },
    }


def generate_markdown_report(
    df: pd.DataFrame,
    survey_title: Optional[str] = None,
    is_synthetic: Optional[bool] = None,
) -> str:
    """Generate an executive Markdown summary report from survey responses.

    Parameters
    ----------
    df : pd.DataFrame
        Survey dataset in long-format.
    survey_title : str, optional
        Report heading title.
    is_synthetic : bool, optional
        Explicit simulated data declaration flag.

    Returns
    -------
    str
        Formatted Markdown text report.
    """
    data = generate_survey_report_data(df, survey_title=survey_title, is_synthetic=is_synthetic)

    lines: list[str] = [
        f"# {data['survey_title']}",
        "",
        f"**Generated:** {data['generated_at']} | **Domain / Type:** `{data['survey_type']}`",
        "",
    ]

    if data["is_synthetic"]:
        lines.extend([SYNTHETIC_DISCLAIMER, ""])

    # Executive Metadata Table
    lines.extend(
        [
            "## 1. Executive Summary & Overview",
            "",
            "| Metric | Value |",
            "| :--- | :--- |",
            f"| **Total Response Records** | {data['total_rows']:,} |",
            f"| **Distinct Survey Respondents** | {data['total_respondents']:,} |",
            f"| **Total Analyzed Questions** | {data['total_questions']:,} |",
            f"| **Data Quality Status** | `{data['overall_data_quality']['status']}` |",
            "",
            "### Data Hygiene & Completeness",
        ]
    )
    for note in data["overall_data_quality"]["notes"]:
        lines.append(f"- {note}")
    lines.append("")

    if not data["question_insights"]:
        lines.extend(["*No question-level records were found to evaluate.*", ""])
        return "\n".join(lines)

    # Detailed Question Findings
    lines.extend(["## 2. Question-by-Question Detailed Findings", ""])

    for idx, q_item in enumerate(data["question_insights"], start=1):
        lines.extend(
            [
                f"### {idx}. {q_item['question_id']} — {q_item['question_text']}",
                f"**Type:** `{q_item['question_type']}`",
                "",
                f"> **Summary**: {q_item['summary']}",
                "",
            ]
        )

        if q_item["key_findings"]:
            lines.append("**Key Observations:**")
            for finding in q_item["key_findings"]:
                lines.append(f"- {finding}")
            lines.append("")

        # Metrics breakdown table or details if available
        metrics = q_item.get("metrics", {})
        if "segment_summary" in metrics:
            lines.extend(
                [
                    "**Demographic Segment Comparison:**",
                    f"- {metrics['segment_summary']}",
                    "",
                ]
            )

        if q_item.get("warnings"):
            lines.append("**Analytical Notes & Caveats:**")
            for warn in q_item["warnings"]:
                lines.append(f"- *Note*: {warn}")
            lines.append("")

    # Methodological Appendix
    lines.extend(
        [
            "## 3. Methodology & Governance Notes",
            "- **Per-Question Denominators**: Percentages reflect the proportion of respondents who provided a valid answer to that specific question.",
            "- **Sample Descriptions**: Stated observations reflect sample metrics and do not assert statistical significance or causal relationships without inferential testing.",
            "- **Multi-Select Percentages**: Option totals may sum to > 100% because respondents can select multiple answers.",
            "",
            "---",
            "*Report compiled automatically by Poll Results Visualizer.*",
        ]
    )

    return "\n".join(lines)


def generate_tabular_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Generate a structured, tabular summary DataFrame suitable for CSV export.

    Parameters
    ----------
    df : pd.DataFrame
        Survey dataset in long-format.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns:
        ['question_id', 'question_text', 'question_type', 'valid_responses',
         'missing_responses', 'primary_metric', 'metric_value', 'key_finding',
         'data_quality_status'].
    """
    columns = [
        "question_id",
        "question_text",
        "question_type",
        "valid_responses",
        "missing_responses",
        "primary_metric",
        "metric_value",
        "key_finding",
        "data_quality_status",
    ]

    if df is None or df.empty or "question_id" not in df.columns:
        return pd.DataFrame(columns=columns)

    rows: list[dict[str, Any]] = []

    for q_id in df["question_id"].unique():
        try:
            insight = generate_question_insights(df, str(q_id))
            q_metrics = insight.metrics
            q_type = insight.question_type

            valid_resp = q_metrics.get("valid_count", q_metrics.get("valid_respondents", 0))
            missing_resp = q_metrics.get("missing_count", q_metrics.get("missing_respondents", 0))

            primary_metric = "Count"
            metric_value = str(valid_resp)

            if q_type == "rating":
                primary_metric = "Mean Rating (1-5)"
                mean_val = q_metrics.get("mean")
                metric_value = f"{mean_val:.2f}" if mean_val is not None else "N/A"
            elif q_type == "nps":
                primary_metric = "Net Promoter Score"
                nps_val = q_metrics.get("nps_score")
                sign = "+" if (nps_val is not None and nps_val > 0) else ""
                metric_value = f"{sign}{nps_val:.1f}" if nps_val is not None else "N/A"
            elif q_type == "single_choice":
                primary_metric = "Top Choice"
                leader = q_metrics.get("leader", "N/A")
                pct = q_metrics.get("leader_percentage", 0.0)
                metric_value = f"{leader} ({pct:.1f}%)"
            elif q_type == "multi_select":
                primary_metric = "Top Option"
                top_opt = q_metrics.get("top_option", "N/A")
                top_pct = q_metrics.get("top_percentage", 0.0)
                metric_value = f"{top_opt} ({top_pct:.1f}%)"
            elif q_type == "text":
                primary_metric = "Text Submissions"
                metric_value = f"{valid_resp:,} responses"

            finding_text = insight.key_findings[0] if insight.key_findings else insight.summary
            quality_status = "Complete" if missing_resp == 0 else f"{missing_resp} missing"

            rows.append(
                {
                    "question_id": insight.question_id,
                    "question_text": insight.question_text,
                    "question_type": q_type,
                    "valid_responses": valid_resp,
                    "missing_responses": missing_resp,
                    "primary_metric": primary_metric,
                    "metric_value": metric_value,
                    "key_finding": finding_text,
                    "data_quality_status": quality_status,
                }
            )
        except Exception as err:
            rows.append(
                {
                    "question_id": str(q_id),
                    "question_text": "Error",
                    "question_type": "unknown",
                    "valid_responses": 0,
                    "missing_responses": 0,
                    "primary_metric": "Error",
                    "metric_value": "N/A",
                    "key_finding": str(err),
                    "data_quality_status": "Error",
                }
            )

    return pd.DataFrame(rows, columns=columns)
