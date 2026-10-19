"""Unit tests for src/poll_visualizer/cleaning.py."""

import numpy as np
import pandas as pd
import pytest

from poll_visualizer.cleaning import clean_survey_data, standardize_missing_values


def test_standardize_missing_values():
    """Verify that null, empty strings, and nan strings are converted to NaN while preserving zeros and 'No'."""
    s = pd.Series([None, "", "nan", "null", "No", 0, "0", 5, "Satisfied"])
    cleaned = standardize_missing_values(s)

    assert pd.isna(cleaned.iloc[0])
    assert pd.isna(cleaned.iloc[1])
    assert pd.isna(cleaned.iloc[2])
    assert pd.isna(cleaned.iloc[3])
    # Preserved values
    assert cleaned.iloc[4] == "No"
    assert cleaned.iloc[5] == 0
    assert cleaned.iloc[6] == "0"
    assert cleaned.iloc[7] == 5
    assert cleaned.iloc[8] == "Satisfied"


def test_clean_survey_data_whitespace_and_lowercase():
    """Verify whitespace stripping and question_type lowercase normalization."""
    df = pd.DataFrame([
        {
            "response_id": " 101 ",
            "question_id": " Q1 ",
            "question_text": " Rate your experience ",
            "question_type": " RATING ",
            "segment": None,
            "answer": " 5 ",
        }
    ])
    cleaned_df, audit = clean_survey_data(df)

    assert cleaned_df["question_id"].iloc[0] == "Q1"
    assert cleaned_df["question_type"].iloc[0] == "rating"
    assert cleaned_df["segment"].iloc[0] == "(Missing)"
    assert cleaned_df["answer"].iloc[0] == "5"

    assert audit["rows_total"] == 1
    assert len(audit["transformations"]) > 0


def test_clean_survey_data_empty():
    """Verify clean_survey_data handles empty input gracefully."""
    empty_df = pd.DataFrame()
    cleaned_df, audit = clean_survey_data(empty_df)

    assert cleaned_df.empty
    assert audit["rows_cleaned"] == 0


def test_clean_survey_data_immutability():
    """Verify source DataFrame is not mutated by clean_survey_data."""
    original_df = pd.DataFrame([
        {"question_id": " Q1 ", "question_type": " RATING ", "segment": None}
    ])
    copy_df = original_df.copy(deep=True)

    _ = clean_survey_data(original_df)
    pd.testing.assert_frame_equal(original_df, copy_df)
