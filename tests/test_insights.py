"""Unit tests for src/poll_visualizer/insights.py."""

import json
import numpy as np
import pandas as pd
import pytest

from poll_visualizer.insights import (
    QuestionInsight,
    generate_categorical_insights,
    generate_multiselect_insights,
    generate_nps_insights,
    generate_question_insights,
    generate_rating_insights,
    generate_segment_insights,
)


@pytest.fixture
def sample_survey_df() -> pd.DataFrame:
    """Fixture providing a diverse, hand-crafted survey dataset across question types."""
    records = [
        # Q1: Single choice (Yes: 6, No: 3, Maybe: 1, None: 2 -> Valid: 10)
        {"response_id": 1, "respondent_id": "U1", "survey_type": "test_poll", "question_id": "Q1", "question_text": "Do you use our product?", "question_type": "single_choice", "answer": "Yes", "segment": "North", "weight": 1.0},
        {"response_id": 2, "respondent_id": "U2", "survey_type": "test_poll", "question_id": "Q1", "question_text": "Do you use our product?", "question_type": "single_choice", "answer": "Yes", "segment": "North", "weight": 1.0},
        {"response_id": 3, "respondent_id": "U3", "survey_type": "test_poll", "question_id": "Q1", "question_text": "Do you use our product?", "question_type": "single_choice", "answer": "Yes", "segment": "North", "weight": 1.0},
        {"response_id": 4, "respondent_id": "U4", "survey_type": "test_poll", "question_id": "Q1", "question_text": "Do you use our product?", "question_type": "single_choice", "answer": "Yes", "segment": "South", "weight": 1.0},
        {"response_id": 5, "respondent_id": "U5", "survey_type": "test_poll", "question_id": "Q1", "question_text": "Do you use our product?", "question_type": "single_choice", "answer": "Yes", "segment": "South", "weight": 1.0},
        {"response_id": 6, "respondent_id": "U6", "survey_type": "test_poll", "question_id": "Q1", "question_text": "Do you use our product?", "question_type": "single_choice", "answer": "Yes", "segment": "South", "weight": 1.0},
        {"response_id": 7, "respondent_id": "U7", "survey_type": "test_poll", "question_id": "Q1", "question_text": "Do you use our product?", "question_type": "single_choice", "answer": "No", "segment": "North", "weight": 1.0},
        {"response_id": 8, "respondent_id": "U8", "survey_type": "test_poll", "question_id": "Q1", "question_text": "Do you use our product?", "question_type": "single_choice", "answer": "No", "segment": "South", "weight": 1.0},
        {"response_id": 9, "respondent_id": "U9", "survey_type": "test_poll", "question_id": "Q1", "question_text": "Do you use our product?", "question_type": "single_choice", "answer": "No", "segment": "South", "weight": 1.0},
        {"response_id": 10, "respondent_id": "U10", "survey_type": "test_poll", "question_id": "Q1", "question_text": "Do you use our product?", "question_type": "single_choice", "answer": "Maybe", "segment": "North", "weight": 1.0},
        {"response_id": 11, "respondent_id": "U11", "survey_type": "test_poll", "question_id": "Q1", "question_text": "Do you use our product?", "question_type": "single_choice", "answer": None, "segment": "North", "weight": 1.0},
        {"response_id": 12, "respondent_id": "U12", "survey_type": "test_poll", "question_id": "Q1", "question_text": "Do you use our product?", "question_type": "single_choice", "answer": "", "segment": "South", "weight": 1.0},

        # Q2: Rating 1-5 (5: 4, 4: 3, 3: 1, 2: 1, 1: 1 -> Valid: 10)
        # Sum = 20 + 12 + 3 + 2 + 1 = 38. Mean = 3.80. Median = 4.0. Top-box = 7/10 = 70.0%
        {"response_id": 13, "respondent_id": "U1", "survey_type": "test_poll", "question_id": "Q2", "question_text": "Rate satisfaction", "question_type": "rating", "answer": 5, "segment": "North", "weight": 1.0},
        {"response_id": 14, "respondent_id": "U2", "survey_type": "test_poll", "question_id": "Q2", "question_text": "Rate satisfaction", "question_type": "rating", "answer": 5, "segment": "North", "weight": 1.0},
        {"response_id": 15, "respondent_id": "U3", "survey_type": "test_poll", "question_id": "Q2", "question_text": "Rate satisfaction", "question_type": "rating", "answer": 5, "segment": "North", "weight": 1.0},
        {"response_id": 16, "respondent_id": "U4", "survey_type": "test_poll", "question_id": "Q2", "question_text": "Rate satisfaction", "question_type": "rating", "answer": 5, "segment": "South", "weight": 1.0},
        {"response_id": 17, "respondent_id": "U5", "survey_type": "test_poll", "question_id": "Q2", "question_text": "Rate satisfaction", "question_type": "rating", "answer": 4, "segment": "South", "weight": 1.0},
        {"response_id": 18, "respondent_id": "U6", "survey_type": "test_poll", "question_id": "Q2", "question_text": "Rate satisfaction", "question_type": "rating", "answer": 4, "segment": "South", "weight": 1.0},
        {"response_id": 19, "respondent_id": "U7", "survey_type": "test_poll", "question_id": "Q2", "question_text": "Rate satisfaction", "question_type": "rating", "answer": 4, "segment": "North", "weight": 1.0},
        {"response_id": 20, "respondent_id": "U8", "survey_type": "test_poll", "question_id": "Q2", "question_text": "Rate satisfaction", "question_type": "rating", "answer": 3, "segment": "North", "weight": 1.0},
        {"response_id": 21, "respondent_id": "U9", "survey_type": "test_poll", "question_id": "Q2", "question_text": "Rate satisfaction", "question_type": "rating", "answer": 2, "segment": "South", "weight": 1.0},
        {"response_id": 22, "respondent_id": "U10", "survey_type": "test_poll", "question_id": "Q2", "question_text": "Rate satisfaction", "question_type": "rating", "answer": 1, "segment": "South", "weight": 1.0},

        # Q3: NPS (10: 4, 9: 2, 8: 1, 7: 1, 6: 1, 3: 1 -> Valid: 10)
        # Promoters (9-10): 6 (60.0%), Passives (7-8): 2 (20.0%), Detractors (0-6): 2 (20.0%)
        # NPS = 60.0 - 20.0 = +40.0
        {"response_id": 23, "respondent_id": "U1", "survey_type": "test_poll", "question_id": "Q3", "question_text": "Likelihood to recommend", "question_type": "nps", "answer": 10, "segment": "North", "weight": 1.0},
        {"response_id": 24, "respondent_id": "U2", "survey_type": "test_poll", "question_id": "Q3", "question_text": "Likelihood to recommend", "question_type": "nps", "answer": 10, "segment": "North", "weight": 1.0},
        {"response_id": 25, "respondent_id": "U3", "survey_type": "test_poll", "question_id": "Q3", "question_text": "Likelihood to recommend", "question_type": "nps", "answer": 10, "segment": "North", "weight": 1.0},
        {"response_id": 26, "respondent_id": "U4", "survey_type": "test_poll", "question_id": "Q3", "question_text": "Likelihood to recommend", "question_type": "nps", "answer": 10, "segment": "South", "weight": 1.0},
        {"response_id": 27, "respondent_id": "U5", "survey_type": "test_poll", "question_id": "Q3", "question_text": "Likelihood to recommend", "question_type": "nps", "answer": 9, "segment": "South", "weight": 1.0},
        {"response_id": 28, "respondent_id": "U6", "survey_type": "test_poll", "question_id": "Q3", "question_id": "Q3", "question_text": "Likelihood to recommend", "question_type": "nps", "answer": 9, "segment": "South", "weight": 1.0},
        {"response_id": 29, "respondent_id": "U7", "survey_type": "test_poll", "question_id": "Q3", "question_text": "Likelihood to recommend", "question_type": "nps", "answer": 8, "segment": "North", "weight": 1.0},
        {"response_id": 30, "respondent_id": "U8", "survey_type": "test_poll", "question_id": "Q3", "question_text": "Likelihood to recommend", "question_type": "nps", "answer": 7, "segment": "North", "weight": 1.0},
        {"response_id": 31, "respondent_id": "U9", "survey_type": "test_poll", "question_id": "Q3", "question_text": "Likelihood to recommend", "question_type": "nps", "answer": 6, "segment": "South", "weight": 1.0},
        {"response_id": 32, "respondent_id": "U10", "survey_type": "test_poll", "question_id": "Q3", "question_text": "Likelihood to recommend", "question_type": "nps", "answer": 3, "segment": "South", "weight": 1.0},

        # Q4: Multi-select (Valid respondents: 4)
        # R1: ["Email", "Slack"]
        # R2: ["Slack", "In-App"]
        # R3: ["Slack"]
        # R4: ["Email"]
        # Counts: Slack = 3 (75.0%), Email = 2 (50.0%), In-App = 1 (25.0%)
        # Sum = 75 + 50 + 25 = 150.0%
        {"response_id": 33, "respondent_id": "U1", "survey_type": "test_poll", "question_id": "Q4", "question_text": "Preferred channels", "question_type": "multi_select", "answer": '["Email", "Slack"]', "segment": "North", "weight": 1.0},
        {"response_id": 34, "respondent_id": "U2", "survey_type": "test_poll", "question_id": "Q4", "question_text": "Preferred channels", "question_type": "multi_select", "answer": '["Slack", "In-App"]', "segment": "North", "weight": 1.0},
        {"response_id": 35, "respondent_id": "U3", "survey_type": "test_poll", "question_id": "Q4", "question_text": "Preferred channels", "question_type": "multi_select", "answer": '["Slack"]', "segment": "South", "weight": 1.0},
        {"response_id": 36, "respondent_id": "U4", "survey_type": "test_poll", "question_id": "Q4", "question_text": "Preferred channels", "question_type": "multi_select", "answer": '["Email"]', "segment": "South", "weight": 1.0},

        # Q5: Text
        {"response_id": 37, "respondent_id": "U1", "survey_type": "test_poll", "question_id": "Q5", "question_text": "Any feedback?", "question_type": "text", "answer": "Great interface!", "segment": "North", "weight": 1.0},
        {"response_id": 38, "respondent_id": "U2", "survey_type": "test_poll", "question_id": "Q5", "question_text": "Any feedback?", "question_type": "text", "answer": None, "segment": "South", "weight": 1.0},
    ]
    return pd.DataFrame(records)


def test_categorical_insights_majority(sample_survey_df):
    """Verify categorical insights identify clear majority, margins, and data completeness."""
    insight = generate_categorical_insights(sample_survey_df, "Q1")

    assert isinstance(insight, QuestionInsight)
    assert insight.question_id == "Q1"
    assert insight.question_type == "single_choice"
    assert "Yes" in insight.summary
    assert "60.0%" in insight.summary

    metrics = insight.metrics
    assert metrics["valid_count"] == 10
    assert metrics["missing_count"] == 2
    assert metrics["leader"] == "Yes"
    assert metrics["leader_count"] == 6
    assert metrics["leader_percentage"] == 60.0

    # Key findings check
    assert any("majority" in f.lower() for f in insight.key_findings)
    assert any("Runner-up" in f for f in insight.key_findings)


def test_categorical_insights_tie():
    """Verify exact tie detection and deterministic ordering."""
    tie_df = pd.DataFrame([
        {"question_id": "T1", "question_text": "Pick color", "question_type": "single_choice", "answer": "Blue"},
        {"question_id": "T1", "question_text": "Pick color", "question_type": "single_choice", "answer": "Blue"},
        {"question_id": "T1", "question_text": "Pick color", "question_type": "single_choice", "answer": "Red"},
        {"question_id": "T1", "question_text": "Pick color", "question_type": "single_choice", "answer": "Red"},
    ])
    insight = generate_categorical_insights(tie_df, "T1")

    assert "tied between" in insight.summary.lower()
    assert insight.metrics["leader"] == "Tie"
    assert insight.metrics["leader_count"] == 2
    assert len(insight.warnings) >= 1
    assert "tie was observed" in insight.warnings[0].lower()


def test_categorical_insights_empty_and_missing():
    """Verify handling when all answers are missing or null."""
    empty_df = pd.DataFrame([
        {"question_id": "E1", "question_text": "Empty question", "question_type": "single_choice", "answer": None},
        {"question_id": "E1", "question_text": "Empty question", "question_type": "single_choice", "answer": ""},
        {"question_id": "E1", "question_text": "Empty question", "question_type": "single_choice", "answer": "nan"},
    ])
    insight = generate_categorical_insights(empty_df, "E1")

    assert insight.metrics["valid_count"] == 0
    assert insight.metrics["missing_count"] == 3
    assert "No valid responses were recorded" in insight.summary
    assert len(insight.key_findings) == 0
    assert len(insight.warnings) > 0


def test_categorical_nonexistent_question_raises_keyerror(sample_survey_df):
    """Verify nonexistent question ID raises KeyError."""
    with pytest.raises(KeyError):
        generate_categorical_insights(sample_survey_df, "NONEXISTENT")


def test_rating_insights_metrics(sample_survey_df):
    """Verify rating insights correctly report mean, median, top-box, and mode."""
    insight = generate_rating_insights(sample_survey_df, "Q2")

    metrics = insight.metrics
    assert metrics["valid_count"] == 10
    assert metrics["missing_count"] == 0
    assert metrics["mean"] == 3.8
    assert metrics["median"] == 4.0
    assert metrics["top_box_pct"] == 70.0  # (4 + 3) / 10 = 70.0%
    assert metrics["bottom_box_pct"] == 20.0  # (1 + 1) / 10 = 20.0%
    assert metrics["neutral_pct"] == 10.0  # 1 / 10 = 10.0%
    assert metrics["modal_ratings"] == [5]

    assert "3.80" in insight.summary
    assert "70.0% favorable" in insight.summary


def test_rating_insights_empty_ratings():
    """Verify empty rating questions return empty state without crashing."""
    df = pd.DataFrame([
        {"question_id": "R_EMPTY", "question_text": "Rating empty", "question_type": "rating", "answer": None},
    ])
    insight = generate_rating_insights(df, "R_EMPTY")
    assert insight.metrics["valid_count"] == 0
    assert "No valid ratings were recorded" in insight.summary


def test_nps_insights_metrics(sample_survey_df):
    """Verify NPS calculation, tier assignment, and distribution."""
    insight = generate_nps_insights(sample_survey_df, "Q3")

    metrics = insight.metrics
    assert metrics["valid_count"] == 10
    assert metrics["nps_score"] == 40.0
    assert metrics["promoter_pct"] == 60.0
    assert metrics["passive_pct"] == 20.0
    assert metrics["detractor_pct"] == 20.0
    assert metrics["promoters_count"] == 6
    assert metrics["passives_count"] == 2
    assert metrics["detractors_count"] == 2
    assert metrics["tier_label"] == "Healthy / Favorable"

    assert "+40.0" in insight.summary
    assert "Healthy / Favorable" in insight.summary


def test_nps_insights_negative_warning():
    """Verify warning is added when detractors exceed promoters."""
    neg_nps_df = pd.DataFrame([
        {"question_id": "N1", "question_text": "Recommend?", "question_type": "nps", "answer": 1},
        {"question_id": "N1", "question_text": "Recommend?", "question_type": "nps", "answer": 2},
        {"question_id": "N1", "question_text": "Recommend?", "question_type": "nps", "answer": 3},
        {"question_id": "N1", "question_text": "Recommend?", "question_type": "nps", "answer": 10},
    ])
    insight = generate_nps_insights(neg_nps_df, "N1")
    assert insight.metrics["nps_score"] == -50.0
    assert len(insight.warnings) >= 1
    assert "Detractors" in insight.warnings[0]


def test_multiselect_insights_respondent_denominator(sample_survey_df):
    """Verify multi-select percentage calculation using respondent denominators and sum > 100% note."""
    insight = generate_multiselect_insights(sample_survey_df, "Q4")

    metrics = insight.metrics
    assert metrics["valid_respondents"] == 4
    assert metrics["top_option"] == "Slack"
    assert metrics["top_percentage"] == 75.0
    assert metrics["top_count"] == 3
    assert metrics["percentage_sum"] == 150.0

    # Ensure warning / methodology note is present
    assert any("sum to 150.0%" in f for f in insight.key_findings)
    assert any("proportion of respondents" in w.lower() for w in insight.warnings)


def test_segment_insights_rating(sample_survey_df):
    """Verify segment breakdown compares groups without asserting causality."""
    seg_insight = generate_segment_insights(sample_survey_df, "Q2", segment_col="segment")

    assert seg_insight["question_id"] == "Q2"
    assert "North" in seg_insight["group_data"]
    assert "South" in seg_insight["group_data"]
    assert len(seg_insight["key_findings"]) >= 2
    assert any("statistical significance" in w for w in seg_insight["warnings"])


def test_segment_insights_missing_col(sample_survey_df):
    """Verify handling when requested segment column is absent."""
    seg_insight = generate_segment_insights(sample_survey_df, "Q2", segment_col="nonexistent_col")
    assert "not present in dataset" in seg_insight["summary"]


def test_dispatcher_generate_question_insights(sample_survey_df):
    """Verify dispatcher routes correctly for all question types."""
    q1 = generate_question_insights(sample_survey_df, "Q1")
    assert q1.question_type == "single_choice"
    assert "leader" in q1.metrics

    q2 = generate_question_insights(sample_survey_df, "Q2")
    assert q2.question_type == "rating"
    assert "mean" in q2.metrics

    q3 = generate_question_insights(sample_survey_df, "Q3")
    assert q3.question_type == "nps"
    assert "nps_score" in q3.metrics

    q4 = generate_question_insights(sample_survey_df, "Q4")
    assert q4.question_type == "multi_select"
    assert "top_option" in q4.metrics

    q5 = generate_question_insights(sample_survey_df, "Q5")
    assert q5.question_type == "text"
    assert "valid_count" in q5.metrics


def test_dataframe_immutability(sample_survey_df):
    """Verify insight generation does not mutate the source DataFrame."""
    df_copy = sample_survey_df.copy(deep=True)
    _ = generate_question_insights(sample_survey_df, "Q1")
    _ = generate_question_insights(sample_survey_df, "Q2")
    _ = generate_question_insights(sample_survey_df, "Q3")
    _ = generate_question_insights(sample_survey_df, "Q4")
    _ = generate_question_insights(sample_survey_df, "Q5")

    pd.testing.assert_frame_equal(sample_survey_df, df_copy)
