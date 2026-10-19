"""Unit tests for src/poll_visualizer/reporting.py."""

import pandas as pd
import pytest

from poll_visualizer.reporting import (
    SYNTHETIC_DISCLAIMER,
    generate_markdown_report,
    generate_survey_report_data,
    generate_tabular_summary,
)


@pytest.fixture
def mock_survey_df() -> pd.DataFrame:
    """Fixture providing a multi-question survey for reporting verification."""
    records = [
        # Q1: Single choice
        {"response_id": 1, "respondent_id": "U1", "survey_type": "customer_satisfaction", "question_id": "CSAT_Q1", "question_text": "Overall experience?", "question_type": "single_choice", "answer": "Satisfied", "segment": "SMB", "weight": 1.0},
        {"response_id": 2, "respondent_id": "U2", "survey_type": "customer_satisfaction", "question_id": "CSAT_Q1", "question_text": "Overall experience?", "question_type": "single_choice", "answer": "Satisfied", "segment": "Enterprise", "weight": 1.0},
        {"response_id": 3, "respondent_id": "U3", "survey_type": "customer_satisfaction", "question_id": "CSAT_Q1", "question_text": "Overall experience?", "question_type": "single_choice", "answer": "Neutral", "segment": "SMB", "weight": 1.0},
        {"response_id": 4, "respondent_id": "U4", "survey_type": "customer_satisfaction", "question_id": "CSAT_Q1", "question_text": "Overall experience?", "question_type": "single_choice", "answer": None, "segment": "Enterprise", "weight": 1.0},

        # Q2: Rating
        {"response_id": 5, "respondent_id": "U1", "survey_type": "customer_satisfaction", "question_id": "CSAT_Q2", "question_text": "Feature usefulness?", "question_type": "rating", "answer": 5, "segment": "SMB", "weight": 1.0},
        {"response_id": 6, "respondent_id": "U2", "survey_type": "customer_satisfaction", "question_id": "CSAT_Q2", "question_text": "Feature usefulness?", "question_type": "rating", "answer": 4, "segment": "Enterprise", "weight": 1.0},
        {"response_id": 7, "respondent_id": "U3", "survey_type": "customer_satisfaction", "question_id": "CSAT_Q2", "question_text": "Feature usefulness?", "question_type": "rating", "answer": 4, "segment": "SMB", "weight": 1.0},
        {"response_id": 8, "respondent_id": "U4", "survey_type": "customer_satisfaction", "question_id": "CSAT_Q2", "question_text": "Feature usefulness?", "question_type": "rating", "answer": 3, "segment": "Enterprise", "weight": 1.0},

        # Q3: NPS
        {"response_id": 9, "respondent_id": "U1", "survey_type": "customer_satisfaction", "question_id": "CSAT_Q3", "question_text": "Recommend service?", "question_type": "nps", "answer": 10, "segment": "SMB", "weight": 1.0},
        {"response_id": 10, "respondent_id": "U2", "survey_type": "customer_satisfaction", "question_id": "CSAT_Q3", "question_text": "Recommend service?", "question_type": "nps", "answer": 9, "segment": "Enterprise", "weight": 1.0},
        {"response_id": 11, "respondent_id": "U3", "survey_type": "customer_satisfaction", "question_id": "CSAT_Q3", "question_text": "Recommend service?", "question_type": "nps", "answer": 8, "segment": "SMB", "weight": 1.0},
        {"response_id": 12, "respondent_id": "U4", "survey_type": "customer_satisfaction", "question_id": "CSAT_Q3", "question_text": "Recommend service?", "question_type": "nps", "answer": 6, "segment": "Enterprise", "weight": 1.0},
    ]
    return pd.DataFrame(records)


def test_generate_survey_report_data_structure(mock_survey_df):
    """Verify metadata compilation, completion rates, and question insight packaging."""
    report_data = generate_survey_report_data(mock_survey_df)

    assert report_data["total_rows"] == 12
    assert report_data["total_respondents"] == 4
    assert report_data["total_questions"] == 3
    assert report_data["survey_type"] == "customer_satisfaction"
    assert report_data["is_synthetic"] is True  # Auto-detected from customer_satisfaction

    quality = report_data["overall_data_quality"]
    assert quality["status"] in {"HEALTHY", "MODERATE"}
    assert quality["completion_rate"] > 90.0

    assert len(report_data["question_insights"]) == 3
    q_ids = [q["question_id"] for q in report_data["question_insights"]]
    assert q_ids == ["CSAT_Q1", "CSAT_Q2", "CSAT_Q3"]


def test_generate_survey_report_data_empty():
    """Verify empty DataFrame handling."""
    empty_df = pd.DataFrame()
    report_data = generate_survey_report_data(empty_df)

    assert report_data["total_rows"] == 0
    assert report_data["total_respondents"] == 0
    assert report_data["total_questions"] == 0
    assert report_data["overall_data_quality"]["status"] == "EMPTY"
    assert len(report_data["question_insights"]) == 0


def test_synthetic_data_detection(mock_survey_df):
    """Verify synthetic auto-detection and explicit manual override."""
    # Auto-detected as True because 'customer_satisfaction' is known synthetic
    data_auto = generate_survey_report_data(mock_survey_df)
    assert data_auto["is_synthetic"] is True

    # Override with False
    data_real = generate_survey_report_data(mock_survey_df, is_synthetic=False)
    assert data_real["is_synthetic"] is False

    # Custom non-synthetic survey type without override defaults to False
    real_df = mock_survey_df.copy()
    real_df["survey_type"] = "empirical_study"
    data_custom = generate_survey_report_data(real_df)
    assert data_custom["is_synthetic"] is False


def test_generate_markdown_report_sections(mock_survey_df):
    """Verify Markdown report formatting, sections, and synthetic disclaimer."""
    md = generate_markdown_report(mock_survey_df, survey_title="Customer Pulse 2026")

    assert "# Customer Pulse 2026" in md
    assert "Simulated Data Notice" in md
    assert "## 1. Executive Summary & Overview" in md
    assert "## 2. Question-by-Question Detailed Findings" in md
    assert "## 3. Methodology & Governance Notes" in md

    # Check question entries
    assert "CSAT_Q1 — Overall experience?" in md
    assert "CSAT_Q2 — Feature usefulness?" in md
    assert "CSAT_Q3 — Recommend service?" in md


def test_generate_markdown_report_no_synthetic_disclaimer(mock_survey_df):
    """Verify non-synthetic report omits the synthetic disclaimer."""
    md = generate_markdown_report(mock_survey_df, is_synthetic=False)
    assert "Simulated Data Notice" not in md


def test_generate_markdown_report_empty():
    """Verify Markdown report handles empty dataset cleanly."""
    md = generate_markdown_report(pd.DataFrame())
    assert "# Survey Summary Report" in md
    assert "No question-level records were found" in md


def test_generate_tabular_summary_schema(mock_survey_df):
    """Verify tabular summary column names, row counts, and primary metric formatting."""
    summary_df = generate_tabular_summary(mock_survey_df)

    expected_cols = [
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
    assert list(summary_df.columns) == expected_cols
    assert len(summary_df) == 3

    # Check Q1 (single choice)
    q1_row = summary_df[summary_df["question_id"] == "CSAT_Q1"].iloc[0]
    assert q1_row["valid_responses"] == 3
    assert q1_row["missing_responses"] == 1
    assert q1_row["primary_metric"] == "Top Choice"
    assert "Satisfied" in q1_row["metric_value"]

    # Check Q2 (rating)
    q2_row = summary_df[summary_df["question_id"] == "CSAT_Q2"].iloc[0]
    assert q2_row["primary_metric"] == "Mean Rating (1-5)"
    assert q2_row["metric_value"] == "4.00"

    # Check Q3 (nps)
    q3_row = summary_df[summary_df["question_id"] == "CSAT_Q3"].iloc[0]
    assert q3_row["primary_metric"] == "Net Promoter Score"
    assert "+25.0" in q3_row["metric_value"]


def test_generate_tabular_summary_empty():
    """Verify tabular summary on empty input produces zero-row DataFrame with correct columns."""
    summary_df = generate_tabular_summary(pd.DataFrame())
    assert len(summary_df) == 0
    assert "question_id" in summary_df.columns
    assert "primary_metric" in summary_df.columns


def test_dataframe_immutability(mock_survey_df):
    """Verify that reporting generation functions never mutate the input DataFrame."""
    df_copy = mock_survey_df.copy(deep=True)
    _ = generate_survey_report_data(mock_survey_df)
    _ = generate_markdown_report(mock_survey_df)
    _ = generate_tabular_summary(mock_survey_df)

    pd.testing.assert_frame_equal(mock_survey_df, df_copy)
