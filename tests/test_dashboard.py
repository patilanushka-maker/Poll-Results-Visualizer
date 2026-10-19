"""Unit and integration tests for main.py (Streamlit Dashboard Application)."""

import io
from pathlib import Path
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from main import (
    CANONICAL_DATASETS,
    SYNTHETIC_WARNING_TEXT,
    UNVERIFIED_DATA_TEXT,
    build_question_inventory,
    compute_overview_metrics,
    get_available_segments,
    get_synthetic_dataset_path,
    load_selected_dataset,
    sanitize_error_message,
)


def test_canonical_datasets_exist():
    """Verify all 3 canonical synthetic datasets resolve to existing non-empty files."""
    for display_name, filename in CANONICAL_DATASETS.items():
        path = get_synthetic_dataset_path(filename)
        assert path.exists(), f"Missing dataset: {path}"
        assert path.stat().st_size > 0, f"Empty dataset: {path}"


def test_compute_overview_metrics_populated():
    """Verify overview metrics on a known DataFrame."""
    df = pd.DataFrame([
        {"response_id": 1, "respondent_id": "U1", "survey_type": "customer_pulse", "question_id": "Q1", "answer": "Yes"},
        {"response_id": 2, "respondent_id": "U2", "survey_type": "customer_pulse", "question_id": "Q1", "answer": "No"},
        {"response_id": 3, "respondent_id": "U1", "survey_type": "customer_pulse", "question_id": "Q2", "answer": None},
        {"response_id": 4, "respondent_id": "U2", "survey_type": "customer_pulse", "question_id": "Q2", "answer": ""},
    ])
    metrics = compute_overview_metrics(df)

    assert metrics["total_records"] == 4
    assert metrics["total_respondents"] == 2
    assert metrics["total_questions"] == 2
    assert metrics["survey_type"] == "Customer Pulse"
    assert metrics["valid_answers"] == 2
    assert metrics["missing_answers"] == 2
    assert metrics["completion_rate"] == 50.0


def test_compute_overview_metrics_empty():
    """Verify overview metrics return safe zeros on empty DataFrame."""
    metrics = compute_overview_metrics(pd.DataFrame())
    assert metrics["total_records"] == 0
    assert metrics["total_respondents"] == 0
    assert metrics["total_questions"] == 0
    assert metrics["completion_rate"] == 0.0


def test_build_question_inventory():
    """Verify question inventory aggregates counts and completion rates accurately."""
    df = pd.DataFrame([
        {"question_id": "Q1", "question_text": "Do you like it?", "question_type": "single_choice", "answer": "Yes"},
        {"question_id": "Q1", "question_text": "Do you like it?", "question_type": "single_choice", "answer": None},
        {"question_id": "Q2", "question_text": "Rate it", "question_type": "rating", "answer": 5},
    ])
    inv = build_question_inventory(df)

    assert len(inv) == 2
    q1_row = inv[inv["Question ID"] == "Q1"].iloc[0]
    assert q1_row["Total Rows"] == 2
    assert q1_row["Valid Answers"] == 1
    assert q1_row["Missing"] == 1
    assert q1_row["Completion Rate"] == "50.0%"

    q2_row = inv[inv["Question ID"] == "Q2"].iloc[0]
    assert q2_row["Total Rows"] == 1
    assert q2_row["Valid Answers"] == 1
    assert q2_row["Missing"] == 0
    assert q2_row["Completion Rate"] == "100.0%"


def test_get_available_segments():
    """Verify detection of candidate segment columns and prioritization of 'segment'."""
    df = pd.DataFrame({
        "response_id": [1],
        "respondent_id": ["U1"],
        "question_id": ["Q1"],
        "question_text": ["Q"],
        "question_type": ["rating"],
        "answer": [5],
        "response_timestamp": ["2026-01-01"],
        "region": ["North"],
        "segment": ["Enterprise"],
        "department": ["Engineering"],
    })
    segs = get_available_segments(df)

    assert segs[0] == "segment"
    assert "region" in segs
    assert "department" in segs
    assert "response_id" not in segs


def test_load_selected_dataset_builtin():
    """Verify loading built-in datasets automatically marks them as synthetic with valid schema."""
    df, err, is_syn, val_res = load_selected_dataset(
        source_type="Built-in Example Dataset",
        dataset_name="Customer Satisfaction (CSAT)",
    )
    assert err is None
    assert df is not None
    assert is_syn is True
    assert val_res is not None
    assert val_res.is_valid is True
    assert len(df) == 750


def test_load_selected_dataset_upload_valid():
    """Verify loading a valid uploaded in-memory CSV buffer."""
    csv_content = (
        "response_id,respondent_id,survey_type,question_id,question_text,question_type,answer,response_timestamp,segment\n"
        "1,U1,test_survey,Q1,Satisfied?,single_choice,Yes,2026-01-01T10:00:00Z,SMB\n"
        "2,U2,test_survey,Q1,Satisfied?,single_choice,No,2026-01-01T10:01:00Z,Enterprise\n"
    )
    buf = io.BytesIO(csv_content.encode("utf-8"))

    df, err, is_syn, val_res = load_selected_dataset(
        source_type="Upload Custom CSV File",
        uploaded_file=buf,
        marked_synthetic=False,
    )
    assert err is None
    assert df is not None
    assert len(df) == 2
    assert is_syn is False
    assert val_res is not None
    assert val_res.is_valid is True


def test_load_selected_dataset_upload_invalid_schema():
    """Verify loading an uploaded CSV with missing schema columns produces an actionable error message."""
    csv_content = (
        "id,respondent,question,answer\n"
        "1,U1,Q1,Yes\n"
    )
    buf = io.BytesIO(csv_content.encode("utf-8"))

    df, err, is_syn, val_res = load_selected_dataset(
        source_type="Upload Custom CSV File",
        uploaded_file=buf,
    )
    assert err is not None
    assert "validation" in err.lower()
    assert val_res is not None
    assert val_res.is_valid is False
    assert any("Missing required column" in e for e in val_res.errors)


def test_load_selected_dataset_upload_empty():
    """Verify empty uploaded file is handled gracefully without crashing."""
    buf = io.BytesIO(b"")
    df, err, is_syn, val_res = load_selected_dataset(
        source_type="Upload Custom CSV File",
        uploaded_file=buf,
    )
    assert df is None
    assert err is not None
    assert "Empty" in err


MAIN_PATH = str(Path(__file__).resolve().parent.parent / "main.py")


def test_streamlit_apptest_runs_cleanly():
    """Verify that Streamlit AppTest launches main.py without unhandled exceptions."""
    at = AppTest.from_file(MAIN_PATH)
    at.run()

    assert not at.exception
    # Verify title is rendered
    assert len(at.title) >= 1
    assert "Poll Results Visualizer" in at.title[0].value


def test_streamlit_apptest_switch_builtin_dataset():
    """Verify switching to a different built-in dataset via AppTest sidebar interaction."""
    at = AppTest.from_file(MAIN_PATH)
    at.run()
    assert not at.exception

    # Select Employee Engagement (eNPS)
    select_box = at.sidebar.selectbox(key="builtin_dataset_select")
    select_box.select("Employee Engagement (eNPS)").run()

    assert not at.exception
    # Verify synthetic disclosure warning is present
    warning_texts = [w.value for w in at.warning]
    assert any("Simulated Data Notice" in t for t in warning_texts)


def test_no_writes_to_raw_or_processed():
    """Verify that dashboard operations do not write or pollute data/raw or data/processed."""
    raw_dir = Path("data/raw")
    processed_dir = Path("data/processed")

    raw_files = list(raw_dir.glob("*")) if raw_dir.exists() else []
    processed_files = list(processed_dir.glob("*")) if processed_dir.exists() else []

    # Neither directory should contain any lingering generated files from Phase 6
    assert all(f.is_file() and f.name == ".gitkeep" for f in raw_files) or len(raw_files) == 0
    assert all(f.is_file() and f.name == ".gitkeep" for f in processed_files) or len(processed_files) == 0


def test_sanitize_error_message():
    """Verify that internal filesystem paths are scrubbed from error messages."""
    win_err = "Failed to load CSV at D:\\Anushka\\IIT\\DS\\data.csv: File corrupted"
    sanitized_win = sanitize_error_message(win_err)
    assert "D:\\" not in sanitized_win
    assert "[local_file_path]" in sanitized_win

    unix_err = "Failed to open /Users/anushka/secret/survey.csv"
    sanitized_unix = sanitize_error_message(unix_err)
    assert "/Users/" not in sanitized_unix
    assert "[local_file_path]" in sanitized_unix


def test_compute_overview_metrics_item_vs_respondent_rate():
    """Verify hand-calculated separation of item response rate and respondent completion rate.

    Scenario:
    - 3 unique respondents (U1, U2, U3)
    - 2 questions (Q1, Q2) -> 6 records
    - U1 answered Q1 (Yes) and Q2 (5) -> Complete
    - U2 answered Q1 (No) and skipped Q2 (None) -> Incomplete
    - U3 answered Q1 (Yes) and Q2 (4) -> Complete
    - Valid records: 5 out of 6 -> Item Response Rate = 83.3%
    - Complete respondents: 2 out of 3 -> Respondent Completion Rate = 66.7%
    """
    df = pd.DataFrame([
        {"response_id": 1, "respondent_id": "U1", "survey_type": "hr_survey", "question_id": "Q1", "answer": "Yes"},
        {"response_id": 2, "respondent_id": "U1", "survey_type": "hr_survey", "question_id": "Q2", "answer": 5},
        {"response_id": 3, "respondent_id": "U2", "survey_type": "hr_survey", "question_id": "Q1", "answer": "No"},
        {"response_id": 4, "respondent_id": "U2", "survey_type": "hr_survey", "question_id": "Q2", "answer": None},
        {"response_id": 5, "respondent_id": "U3", "survey_type": "hr_survey", "question_id": "Q1", "answer": "Yes"},
        {"response_id": 6, "respondent_id": "U3", "survey_type": "hr_survey", "question_id": "Q2", "answer": 4},
    ])
    metrics = compute_overview_metrics(df)

    assert metrics["total_records"] == 6
    assert metrics["total_respondents"] == 3
    assert metrics["valid_answers"] == 5
    assert metrics["missing_answers"] == 1
    assert metrics["item_response_rate"] == 83.3
    assert metrics["complete_respondents"] == 2
    assert metrics["respondent_completion_rate"] == 66.7


def test_nps_tier_classification_project_guideline():
    """Verify narrative insight key findings explicitly cite project-defined interpretive guidelines."""
    from poll_visualizer.insights import generate_nps_insights

    df = pd.DataFrame([
        {"question_id": "N1", "question_text": "Rate NPS", "question_type": "nps", "answer": 10},
        {"question_id": "N1", "question_text": "Rate NPS", "question_type": "nps", "answer": 9},
        {"question_id": "N1", "question_text": "Rate NPS", "question_type": "nps", "answer": 7},
    ])
    insight = generate_nps_insights(df, "N1")
    assert any("project-defined interpretive thresholds" in f for f in insight.key_findings)


def test_apptest_switch_all_builtin_datasets():
    """Verify sequentially switching between all built-in datasets in AppTest without exceptions."""
    at = AppTest.from_file(MAIN_PATH)
    at.run()
    assert not at.exception

    for ds_name in CANONICAL_DATASETS.keys():
        select_box = at.sidebar.selectbox(key="builtin_dataset_select")
        select_box.select(ds_name).run()
        assert not at.exception
        assert len(at.title) >= 1

