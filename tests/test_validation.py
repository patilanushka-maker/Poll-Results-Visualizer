"""Unit tests for src/poll_visualizer/validation.py."""

import pandas as pd
import pytest

from poll_visualizer.validation import (
    ValidationResult,
    is_valid_survey_data,
    validate_survey_data,
)


def make_valid_record(**kwargs) -> dict:
    """Helper creating a baseline valid record for testing."""
    base = {
        "response_id": "RESP-001",
        "respondent_id": "USER-001",
        "survey_type": "customer_satisfaction",
        "question_id": "Q1",
        "question_text": "How satisfied are you?",
        "question_type": "rating",
        "answer": "5",
        "response_timestamp": "2026-02-01T10:00:00Z",
    }
    base.update(kwargs)
    return base


def test_valid_dataset_passes():
    """Verify that a standard valid record passes validation with no errors."""
    df = pd.DataFrame([make_valid_record()])
    res = validate_survey_data(df)
    assert res.is_valid is True
    assert len(res.errors) == 0
    assert is_valid_survey_data(df) is True


def test_missing_required_columns():
    """Verify that omitting a mandatory column fails validation with diagnostic message."""
    record = make_valid_record()
    del record["question_type"]
    df = pd.DataFrame([record])

    res = validate_survey_data(df)
    assert res.is_valid is False
    assert any("Missing required column(s)" in err and "question_type" in err for err in res.errors)


def test_invalid_question_type():
    """Verify that an unsupported question_type triggers a validation error."""
    df = pd.DataFrame([make_valid_record(question_type="free_essay")])
    res = validate_survey_data(df)
    assert res.is_valid is False
    assert any("invalid 'question_type'" in err and "free_essay" in err for err in res.errors)


def test_valid_rating_values():
    """Verify that rating values from 1 through 5 pass validation."""
    records = [
        make_valid_record(
            response_id=f"R-{v}",
            respondent_id=f"USER-{v}",
            answer=str(v),
            question_type="rating",
        )
        for v in [1, 2, 3, 4, 5]
    ]
    df = pd.DataFrame(records)
    res = validate_survey_data(df)
    assert res.is_valid is True
    assert len(res.errors) == 0


def test_rating_outside_allowed_bounds():
    """Verify that ratings < 1 or > 5 trigger bound violation errors."""
    df_low = pd.DataFrame([make_valid_record(answer="0", question_type="rating")])
    res_low = validate_survey_data(df_low)
    assert res_low.is_valid is False
    assert any("outside allowed bounds [1, 5]" in err for err in res_low.errors)

    df_high = pd.DataFrame([make_valid_record(answer="6", question_type="rating")])
    res_high = validate_survey_data(df_high)
    assert res_high.is_valid is False
    assert any("outside allowed bounds [1, 5]" in err for err in res_high.errors)


def test_invalid_nonnumeric_rating_values():
    """Verify that non-numeric rating strings trigger errors without crashing."""
    df = pd.DataFrame([make_valid_record(answer="five_stars", question_type="rating")])
    res = validate_survey_data(df)
    assert res.is_valid is False
    assert any("non-numeric" in err for err in res.errors)


def test_valid_nps_values():
    """Verify that NPS values from 0 to 10 pass validation."""
    records = [
        make_valid_record(
            response_id=f"R-NPS-{v}",
            respondent_id=f"USER-NPS-{v}",
            answer=str(v),
            question_type="nps",
        )
        for v in [0, 5, 7, 10]
    ]
    df = pd.DataFrame(records)
    res = validate_survey_data(df)
    assert res.is_valid is True
    assert len(res.errors) == 0


def test_nps_outside_allowed_bounds():
    """Verify that NPS < 0 or > 10 triggers bound violation errors."""
    df_neg = pd.DataFrame([make_valid_record(answer="-1", question_type="nps")])
    res_neg = validate_survey_data(df_neg)
    assert res_neg.is_valid is False
    assert any("outside allowed bounds [0, 10]" in err for err in res_neg.errors)

    df_over = pd.DataFrame([make_valid_record(answer="11", question_type="nps")])
    res_over = validate_survey_data(df_over)
    assert res_over.is_valid is False
    assert any("outside allowed bounds [0, 10]" in err for err in res_over.errors)


def test_invalid_nonnumeric_nps_values():
    """Verify that non-numeric NPS strings trigger errors without crashing."""
    df = pd.DataFrame([make_valid_record(answer="promoter", question_type="nps")])
    res = validate_survey_data(df)
    assert res.is_valid is False
    assert any("non-numeric" in err for err in res.errors)


def test_duplicate_response_ids():
    """Verify that non-unique response_id entries are detected as errors."""
    r1 = make_valid_record(response_id="RESP-SAME", question_id="Q1")
    r2 = make_valid_record(response_id="RESP-SAME", question_id="Q2")
    df = pd.DataFrame([r1, r2])

    res = validate_survey_data(df)
    assert res.is_valid is False
    assert any("duplicate 'response_id'" in err for err in res.errors)


def test_duplicate_respondent_question_pairs_for_single_answer():
    """Verify that a respondent answering the same single-answer question twice triggers an error."""
    r1 = make_valid_record(response_id="RESP-01", respondent_id="U1", question_id="Q1")
    r2 = make_valid_record(response_id="RESP-02", respondent_id="U1", question_id="Q1")
    df = pd.DataFrame([r1, r2])

    res = validate_survey_data(df)
    assert res.is_valid is False
    assert any("duplicate (respondent_id, question_id)" in err for err in res.errors)


def test_missing_answers_separate_from_negative_responses():
    """Verify that missing answers produce warnings, and are not conflated with negative responses."""
    # "0" is a valid NPS score (negative sentiment, but valid answer)
    df_zero = pd.DataFrame([make_valid_record(answer="0", question_type="nps")])
    res_zero = validate_survey_data(df_zero)
    assert res_zero.is_valid is True
    assert res_zero.summary.get("missing_answers_count", 0) == 0

    # "No" is a valid single-choice response
    df_no = pd.DataFrame([make_valid_record(answer="No", question_type="single_choice")])
    res_no = validate_survey_data(df_no)
    assert res_no.is_valid is True
    assert res_no.summary.get("missing_answers_count", 0) == 0

    # Missing answer (None/NaN) produces a warning, not a fatal error
    df_missing = pd.DataFrame([make_valid_record(answer=None, question_type="rating")])
    res_missing = validate_survey_data(df_missing)
    assert res_missing.is_valid is True
    assert res_missing.summary["missing_answers_count"] == 1
    assert any("unanswered/skipped" in warn for warn in res_missing.warnings)


def test_multi_select_format_json_array():
    """Verify that valid JSON arrays pass, and malformed strings trigger errors."""
    valid_record = make_valid_record(
        question_type="multi_select",
        answer='["Email", "Chat"]',
    )
    df_valid = pd.DataFrame([valid_record])
    res_valid = validate_survey_data(df_valid)
    assert res_valid.is_valid is True

    bad_record = make_valid_record(
        question_type="multi_select",
        answer="Email, Chat",  # Not a JSON array
    )
    df_bad = pd.DataFrame([bad_record])
    res_bad = validate_survey_data(df_bad)
    assert res_bad.is_valid is False
    assert any("not valid JSON arrays" in err for err in res_bad.errors)


def test_timestamp_validation():
    """Verify timestamp parsing and malformed timestamp detection."""
    bad_ts_record = make_valid_record(response_timestamp="not-a-timestamp")
    df_bad = pd.DataFrame([bad_ts_record])
    res_bad = validate_survey_data(df_bad)
    assert res_bad.is_valid is False
    assert any("malformed 'response_timestamp'" in err for err in res_bad.errors)


def test_validation_does_not_mutate_input_dataframe():
    """Verify that validation leaves the input DataFrame unaltered."""
    df = pd.DataFrame([make_valid_record()])
    df_copy = df.copy(deep=True)

    _ = validate_survey_data(df)
    pd.testing.assert_frame_equal(df, df_copy)
