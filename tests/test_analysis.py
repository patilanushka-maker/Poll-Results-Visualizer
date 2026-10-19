"""Unit tests for src/poll_visualizer/analysis.py."""

import pandas as pd
import pytest

from poll_visualizer.analysis import (
    cross_tabulate_by_segment,
    group_nps_summary,
    group_rating_summary,
)


def make_sample_dataset() -> pd.DataFrame:
    """Fixture: Multi-question dataset with segments and missing values."""
    return pd.DataFrame(
        [
            # Q_CAT: single choice
            {"question_id": "Q_CAT", "respondent_id": "U1", "segment": "Enterprise", "answer": "Yes"},
            {"question_id": "Q_CAT", "respondent_id": "U2", "segment": "Enterprise", "answer": "Yes"},
            {"question_id": "Q_CAT", "respondent_id": "U3", "segment": "Enterprise", "answer": "No"},
            {"question_id": "Q_CAT", "respondent_id": "U4", "segment": "SMB", "answer": "No"},
            {"question_id": "Q_CAT", "respondent_id": "U5", "segment": "SMB", "answer": "No"},
            {"question_id": "Q_CAT", "respondent_id": "U6", "segment": None, "answer": "Yes"},      # missing segment
            {"question_id": "Q_CAT", "respondent_id": "U7", "segment": "SMB", "answer": None},       # missing answer
            # Q_OTHER: different question to verify question isolation
            {"question_id": "Q_OTHER", "respondent_id": "U1", "segment": "Enterprise", "answer": "IgnoreMe"},
            # Q_RATE: rating
            {"question_id": "Q_RATE", "respondent_id": "U1", "segment": "Enterprise", "answer": "5"},
            {"question_id": "Q_RATE", "respondent_id": "U2", "segment": "Enterprise", "answer": "4"},
            {"question_id": "Q_RATE", "respondent_id": "U3", "segment": "SMB", "answer": "3"},
            {"question_id": "Q_RATE", "respondent_id": "U4", "segment": "SMB", "answer": "1"},
            {"question_id": "Q_RATE", "respondent_id": "U5", "segment": None, "answer": "2"},
            # Q_NPS: nps
            {"question_id": "Q_NPS", "respondent_id": "U1", "segment": "Enterprise", "answer": "10"}, # promoter
            {"question_id": "Q_NPS", "respondent_id": "U2", "segment": "Enterprise", "answer": "9"},  # promoter
            {"question_id": "Q_NPS", "respondent_id": "U3", "segment": "SMB", "answer": "5"},         # detractor
            {"question_id": "Q_NPS", "respondent_id": "U4", "segment": "SMB", "answer": "8"},         # passive
        ]
    )


def test_cross_tabulate_by_segment_row_percentages():
    """Verify cross-tab row percentages sum to 100% per segment.

    Expected for Q_CAT (normalize='index'):
    - Enterprise (3 valid answers: 2 'Yes', 1 'No'):
      - 'Yes' = 2/3 = 66.67%
      - 'No' = 1/3 = 33.33%
    - SMB (2 valid answers: 0 'Yes', 2 'No'):
      - 'Yes' = 0.0%
      - 'No' = 100.0%
    - (Missing) (1 valid answer: 1 'Yes'):
      - 'Yes' = 100.0%
      - 'No' = 0.0%
    """
    df = make_sample_dataset()
    ctab = cross_tabulate_by_segment(df, question_id="Q_CAT", normalize="index")

    assert "Enterprise" in ctab.index
    assert "SMB" in ctab.index
    assert "(Missing)" in ctab.index
    assert "Yes" in ctab.columns
    assert "No" in ctab.columns

    # Verify percentages
    assert ctab.loc["Enterprise", "Yes"] == 66.67
    assert ctab.loc["Enterprise", "No"] == 33.33
    assert ctab.loc["SMB", "No"] == 100.0
    assert ctab.loc["SMB", "Yes"] == 0.0
    assert ctab.loc["(Missing)", "Yes"] == 100.0

    # Verify row sums are approximately 100%
    for seg in ctab.index:
        assert round(ctab.loc[seg].sum(), 1) == 100.0


def test_cross_tabulate_raw_counts():
    """Verify cross-tab with normalize=False returns raw integer counts."""
    df = make_sample_dataset()
    ctab = cross_tabulate_by_segment(df, question_id="Q_CAT", normalize=False)

    assert ctab.loc["Enterprise", "Yes"] == 2
    assert ctab.loc["Enterprise", "No"] == 1
    assert ctab.loc["SMB", "No"] == 2
    assert ctab.loc["SMB", "Yes"] == 0


def test_cross_tabulate_isolates_question():
    """Verify cross-tabulation never combines answers from unrelated questions."""
    df = make_sample_dataset()
    ctab = cross_tabulate_by_segment(df, question_id="Q_CAT")
    # 'IgnoreMe' from Q_OTHER must not appear in columns
    assert "IgnoreMe" not in ctab.columns


def test_group_rating_summary():
    """Verify group rating descriptive statistics by segment.

    Data for Q_RATE:
    - Enterprise: [5, 4] -> count=2, mean=4.5, std=0.707, min=4, max=5
    - SMB: [3, 1] -> count=2, mean=2.0, std=1.414, min=1, max=3
    - (Missing): [2] -> count=1, mean=2.0, std=None, min=2, max=2
    """
    df = make_sample_dataset()
    res = group_rating_summary(df, question_id="Q_RATE")

    assert "Enterprise" in res.index
    assert "SMB" in res.index
    assert "(Missing)" in res.index

    ent = res.loc["Enterprise"]
    assert ent["valid_count"] == 2
    assert ent["mean"] == 4.5
    assert ent["min"] == 4
    assert ent["max"] == 5

    smb = res.loc["SMB"]
    assert smb["valid_count"] == 2
    assert smb["mean"] == 2.0
    assert smb["min"] == 1
    assert smb["max"] == 3


def test_group_nps_summary():
    """Verify group NPS summaries by segment.

    Data for Q_NPS:
    - Enterprise: [10, 9] -> 2 promoters (100.0%), 0 detractors -> NPS = +100.0
    - SMB: [5, 8] -> 1 detractor (50.0%), 1 passive (50.0%), 0 promoters -> NPS = -50.0
    """
    df = make_sample_dataset()
    res = group_nps_summary(df, question_id="Q_NPS")

    assert "Enterprise" in res.index
    assert "SMB" in res.index

    ent = res.loc["Enterprise"]
    assert ent["promoters_count"] == 2
    assert ent["promoter_pct"] == 100.0
    assert ent["nps_score"] == 100.0

    smb = res.loc["SMB"]
    assert smb["detractors_count"] == 1
    assert smb["passives_count"] == 1
    assert smb["detractor_pct"] == 50.0
    assert smb["promoter_pct"] == 0.0
    assert smb["nps_score"] == -50.0


def test_source_dataframe_immutability():
    """Verify that cross-tabulation and group summaries do not mutate the input DataFrame."""
    df = make_sample_dataset()
    df_copy = df.copy(deep=True)

    _ = cross_tabulate_by_segment(df, "Q_CAT")
    _ = group_rating_summary(df, "Q_RATE")
    _ = group_nps_summary(df, "Q_NPS")

    pd.testing.assert_frame_equal(df, df_copy)
