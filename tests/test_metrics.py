"""Unit tests for src/poll_visualizer/metrics.py."""

import json
import pandas as pd
import pytest

from poll_visualizer.metrics import (
    calculate_likert_distribution,
    calculate_multiselect_frequencies,
    calculate_nps,
    calculate_proportion_ci,
    calculate_rating_metrics,
    calculate_response_frequencies,
    calculate_weighted_frequencies,
    summarize_question_metrics,
)


def make_single_choice_df() -> pd.DataFrame:
    """Fixture: 10 respondents with known choices and 2 missing answers."""
    return pd.DataFrame(
        [
            {"question_id": "Q1", "respondent_id": "U1", "answer": "Yes", "weight": 1.0},
            {"question_id": "Q1", "respondent_id": "U2", "answer": "Yes", "weight": 1.5},
            {"question_id": "Q1", "respondent_id": "U3", "answer": "Yes", "weight": 1.0},
            {"question_id": "Q1", "respondent_id": "U4", "answer": "No", "weight": 0.5},
            {"question_id": "Q1", "respondent_id": "U5", "answer": "No", "weight": 2.0},
            {"question_id": "Q1", "respondent_id": "U6", "answer": "Maybe", "weight": 1.0},
            {"question_id": "Q1", "respondent_id": "U7", "answer": None, "weight": 1.0},   # missing
            {"question_id": "Q1", "respondent_id": "U8", "answer": "", "weight": 1.0},     # missing
            {"question_id": "Q2", "respondent_id": "U1", "answer": "Other", "weight": 1.0}, # different question
        ]
    )


def test_response_frequencies_unweighted():
    """Verify response counts, percentages, and exclusion of missing answers.

    Expected for Q1:
    - Total valid answers = 6 (3 'Yes', 2 'No', 1 'Maybe')
    - 'Yes': 3 / 6 = 50.0%
    - 'No': 2 / 6 = 33.33%
    - 'Maybe': 1 / 6 = 16.67%
    - Q2 is excluded because question_id='Q1' isolates the question.
    """
    df = make_single_choice_df()
    res = calculate_response_frequencies(df, question_id="Q1")

    assert len(res) == 3
    assert list(res.columns) == ["answer", "count", "percentage"]

    # Verify counts
    row_yes = res[res["answer"] == "Yes"].iloc[0]
    assert row_yes["count"] == 3
    assert row_yes["percentage"] == 50.0

    row_no = res[res["answer"] == "No"].iloc[0]
    assert row_no["count"] == 2
    assert row_no["percentage"] == 33.33

    row_maybe = res[res["answer"] == "Maybe"].iloc[0]
    assert row_maybe["count"] == 1
    assert row_maybe["percentage"] == 16.67


def test_weighted_percentages_calculation():
    """Verify weighted frequencies against hand-calculated values.

    Valid rows for Q1:
    - Yes (3 responses): weights = 1.0 + 1.5 + 1.0 = 3.5
    - No (2 responses): weights = 0.5 + 2.0 = 2.5
    - Maybe (1 response): weight = 1.0
    - Total valid weight = 3.5 + 2.5 + 1.0 = 7.0
    Weighted Percentages:
    - Yes: 3.5 / 7.0 = 50.0%
    - No: 2.5 / 7.0 = 35.71%
    - Maybe: 1.0 / 7.0 = 14.29%
    """
    df = make_single_choice_df()
    res = calculate_weighted_frequencies(df, question_id="Q1", weight_col="weight")

    assert len(res) == 3
    yes_row = res[res["answer"] == "Yes"].iloc[0]
    assert yes_row["count"] == 3
    assert yes_row["weighted_count"] == 3.5
    assert yes_row["percentage"] == 50.0
    assert yes_row["weighted_percentage"] == 50.0

    no_row = res[res["answer"] == "No"].iloc[0]
    assert no_row["count"] == 2
    assert no_row["weighted_count"] == 2.5
    assert no_row["weighted_percentage"] == 35.71

    maybe_row = res[res["answer"] == "Maybe"].iloc[0]
    assert maybe_row["count"] == 1
    assert maybe_row["weighted_count"] == 1.0
    assert maybe_row["weighted_percentage"] == 14.29


def test_invalid_weights_raise_actionable_errors():
    """Verify that null, non-numeric, zero, or negative weights raise a ValueError."""
    # Negative weight
    df_neg = pd.DataFrame(
        [
            {"question_id": "Q1", "answer": "Yes", "weight": -0.5},
            {"question_id": "Q1", "answer": "No", "weight": 1.0},
        ]
    )
    with pytest.raises(ValueError) as exc1:
        calculate_weighted_frequencies(df_neg, question_id="Q1")
    assert "non-positive weight(s)" in str(exc1.value)

    # Zero weight
    df_zero = pd.DataFrame(
        [
            {"question_id": "Q1", "answer": "Yes", "weight": 0.0},
            {"question_id": "Q1", "answer": "No", "weight": 1.0},
        ]
    )
    with pytest.raises(ValueError) as exc2:
        calculate_weighted_frequencies(df_zero, question_id="Q1")
    assert "non-positive weight(s)" in str(exc2.value)

    # Missing / NaN weight
    df_nan = pd.DataFrame(
        [
            {"question_id": "Q1", "answer": "Yes", "weight": None},
            {"question_id": "Q1", "answer": "No", "weight": 1.0},
        ]
    )
    with pytest.raises(ValueError) as exc3:
        calculate_weighted_frequencies(df_nan, question_id="Q1")
    assert "missing or non-numeric weight(s)" in str(exc3.value)


def test_rating_metrics_calculation():
    """Verify rating metrics calculation against hand-calculated values.

    Data: [5, 4, 3, 4, 4] with 1 missing answer.
    - valid_count = 5
    - missing_count = 1
    - mean = (5 + 4 + 3 + 4 + 4) / 5 = 20 / 5 = 4.0
    - median = 4.0
    - sample std (ddof=1): values - mean = [1, 0, -1, 0, 0] -> sum sq = 2 -> 2/4 = 0.5 -> sqrt(0.5) = 0.7071
    - min = 3, max = 5
    """
    df = pd.DataFrame(
        [
            {"question_id": "RATE_1", "answer": "5"},
            {"question_id": "RATE_1", "answer": "4"},
            {"question_id": "RATE_1", "answer": "3"},
            {"question_id": "RATE_1", "answer": "4"},
            {"question_id": "RATE_1", "answer": "4"},
            {"question_id": "RATE_1", "answer": None},  # skipped
        ]
    )
    metrics = calculate_rating_metrics(df, question_id="RATE_1")

    assert metrics["valid_count"] == 5
    assert metrics["missing_count"] == 1
    assert metrics["mean"] == 4.0
    assert metrics["median"] == 4.0
    assert metrics["std"] == 0.707
    assert metrics["min"] == 3
    assert metrics["max"] == 5


def test_invalid_ratings_raise_clear_error():
    """Verify that non-numeric or out-of-bound ratings raise a ValueError."""
    # Out of bounds (e.g. 6)
    df_oob = pd.DataFrame([{"question_id": "R1", "answer": "6"}])
    with pytest.raises(ValueError) as exc1:
        calculate_rating_metrics(df_oob, question_id="R1")
    assert "outside [1, 5]" in str(exc1.value)

    # Non-numeric
    df_str = pd.DataFrame([{"question_id": "R1", "answer": "high"}])
    with pytest.raises(ValueError) as exc2:
        calculate_rating_metrics(df_str, question_id="R1")
    assert "non-numeric" in str(exc2.value)


def test_likert_distribution_includes_zero_count_categories():
    """Verify Likert distribution preserves 1-5 order and represents zero counts."""
    df = pd.DataFrame(
        [
            {"question_id": "R1", "answer": "4"},
            {"question_id": "R1", "answer": "4"},
            {"question_id": "R1", "answer": "5"},
        ]
    )
    dist = calculate_likert_distribution(df, question_id="R1")

    assert len(dist) == 5
    assert list(dist["rating"]) == [1, 2, 3, 4, 5]
    assert list(dist["count"]) == [0, 0, 0, 2, 1]
    assert list(dist["percentage"]) == [0.0, 0.0, 0.0, 66.67, 33.33]


def test_nps_calculation_and_boundaries():
    """Verify NPS classification at boundary values:

    Boundary values:
    - 0, 6 -> Detractors
    - 7, 8 -> Passives
    - 9, 10 -> Promoters
    Data:
    - Detractors: 0, 6 (2 responses)
    - Passives: 7, 8 (2 responses)
    - Promoters: 9, 10, 10 (3 responses)
    - Total valid = 7
    - % Promoters = 3/7 = 42.86%
    - % Detractors = 2/7 = 28.57%
    - NPS Score = 42.86 - 28.57 = +14.29
    """
    df = pd.DataFrame(
        [
            {"question_id": "NPS_1", "answer": "0"},   # detractor
            {"question_id": "NPS_1", "answer": "6"},   # detractor
            {"question_id": "NPS_1", "answer": "7"},   # passive
            {"question_id": "NPS_1", "answer": "8"},   # passive
            {"question_id": "NPS_1", "answer": "9"},   # promoter
            {"question_id": "NPS_1", "answer": "10"},  # promoter
            {"question_id": "NPS_1", "answer": "10"},  # promoter
            {"question_id": "NPS_1", "answer": ""},    # missing
        ]
    )
    res = calculate_nps(df, question_id="NPS_1")

    assert res["valid_count"] == 7
    assert res["missing_count"] == 1
    assert res["detractors_count"] == 2
    assert res["passives_count"] == 2
    assert res["promoters_count"] == 3
    assert res["promoter_pct"] == 42.86
    assert res["detractor_pct"] == 28.57
    assert res["passive_pct"] == 28.57
    assert res["nps_score"] == 14.29
    assert -100.0 <= res["nps_score"] <= 100.0


def test_multiselect_frequencies_and_deduplication():
    """Verify multi-select option parsing, percentages, and within-respondent deduplication."""
    df = pd.DataFrame(
        [
            {"question_id": "M1", "answer": '["Feature A", "Feature B"]'},
            {"question_id": "M1", "answer": '["Feature A"]'},
            # Respondent repeats "Feature A" within their answer:
            {"question_id": "M1", "answer": '["Feature A", "Feature A", "Feature C"]'},
            {"question_id": "M1", "answer": None},  # skipped
        ]
    )
    res = calculate_multiselect_frequencies(df, question_id="M1")

    # Total valid respondents = 3
    # Feature A: 3 respondents (100.0%)
    # Feature B: 1 respondent (33.33%)
    # Feature C: 1 respondent (33.33%)
    assert len(res) == 3
    a_row = res[res["option"] == "Feature A"].iloc[0]
    assert a_row["count"] == 3
    assert a_row["percentage"] == 100.0

    b_row = res[res["option"] == "Feature B"].iloc[0]
    assert b_row["count"] == 1
    assert b_row["percentage"] == 33.33


def test_multiselect_malformed_json_raises_error():
    """Verify malformed JSON multi-select strings raise a clear ValueError."""
    df = pd.DataFrame([{"question_id": "M1", "answer": '["Unclosed bracket'}])
    with pytest.raises(ValueError) as exc:
        calculate_multiselect_frequencies(df, question_id="M1")
    assert "Malformed multi-select answer" in str(exc.value)


def test_empty_and_all_missing_inputs():
    """Verify defined behavior for empty DataFrames and questions with 100% missing values."""
    empty_df = pd.DataFrame(columns=["question_id", "answer"])
    assert calculate_response_frequencies(empty_df).empty
    assert calculate_likert_distribution(empty_df)["count"].sum() == 0

    all_missing_df = pd.DataFrame([{"question_id": "Q1", "answer": None}])
    assert calculate_response_frequencies(all_missing_df, "Q1").empty
    rate_res = calculate_rating_metrics(all_missing_df, "Q1")
    assert rate_res["valid_count"] == 0
    assert rate_res["missing_count"] == 1
    assert rate_res["mean"] is None


def test_proportion_ci_wilson():
    """Verify Wilson score confidence interval calculations and edge cases."""
    # 50 out of 100 (50.0%)
    low, high = calculate_proportion_ci(50, 100, confidence=0.95)
    assert 40.0 < low < 50.0
    assert 50.0 < high < 60.0
    assert low <= high

    # Edge cases: n=0
    assert calculate_proportion_ci(0, 0) == (0.0, 0.0)

    # Edge cases: p=0 and p=1
    low_0, high_0 = calculate_proportion_ci(0, 100)
    assert low_0 == 0.0 and high_0 > 0.0

    low_1, high_1 = calculate_proportion_ci(100, 100)
    assert low_1 < 100.0 and high_1 == 100.0

    # Small sample: n=1
    low_n1, high_n1 = calculate_proportion_ci(1, 1)
    assert 0.0 < low_n1 < 100.0 and high_n1 == 100.0

    # Invalid confidence levels
    with pytest.raises(ValueError):
        calculate_proportion_ci(5, 10, confidence=0.0)
    with pytest.raises(ValueError):
        calculate_proportion_ci(5, 10, confidence=1.0)
    with pytest.raises(ValueError):
        calculate_proportion_ci(5, 10, confidence=-0.5)

    # Invalid count and total
    with pytest.raises(ValueError):
        calculate_proportion_ci(-1, 10)
    with pytest.raises(ValueError):
        calculate_proportion_ci(15, 10)
    with pytest.raises(ValueError):
        calculate_proportion_ci(5, -10)


def test_summarize_question_metrics_dispatcher():
    """Verify summarize_question_metrics correctly dispatches based on question_type."""
    df = pd.DataFrame(
        [
            {
                "question_id": "R1",
                "question_text": "Rate product",
                "question_type": "rating",
                "answer": "5",
            },
            {
                "question_id": "R1",
                "question_text": "Rate product",
                "question_type": "rating",
                "answer": "4",
            },
        ]
    )
    summary = summarize_question_metrics(df, "R1")
    assert summary["question_id"] == "R1"
    assert summary["question_type"] == "rating"
    assert "metrics" in summary
    assert "distribution" in summary
    assert summary["metrics"]["mean"] == 4.5
