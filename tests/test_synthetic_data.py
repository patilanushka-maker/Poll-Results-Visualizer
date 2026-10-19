"""Unit tests for scripts/generate_synthetic_data.py."""

from pathlib import Path
import tempfile
import pandas as pd
import pytest

from poll_visualizer.data_loader import load_csv
from poll_visualizer.validation import validate_survey_data
from scripts.generate_synthetic_data import (
    SURVEY_DEFINITIONS,
    generate_all_synthetic_datasets,
    generate_dataset,
)


def test_generated_synthetic_datasets_pass_validation():
    """Verify that generated synthetic datasets for all domains pass validation cleanly."""
    for survey_key in SURVEY_DEFINITIONS.keys():
        df = generate_dataset(survey_key, n_respondents=50, seed=42)
        res = validate_survey_data(df)
        assert res.is_valid is True, f"Validation failed for {survey_key}: {res.errors}"
        assert len(res.errors) == 0


def test_identical_seed_produces_identical_data():
    """Verify that identical parameters and seed produce exact, reproducible data."""
    df1 = generate_dataset("customer_satisfaction", n_respondents=40, seed=123)
    df2 = generate_dataset("customer_satisfaction", n_respondents=40, seed=123)

    pd.testing.assert_frame_equal(df1, df2)


def test_different_seeds_produce_different_data():
    """Verify that changing random seed produces different synthetic responses."""
    df1 = generate_dataset("employee_engagement", n_respondents=40, seed=10)
    df2 = generate_dataset("employee_engagement", n_respondents=40, seed=99)

    # Values in answer or timestamps should differ
    assert not df1["answer"].equals(df2["answer"])


def test_generator_safety_guard_blocks_raw_and_processed():
    """Verify that the generator raises a ValueError if directed to raw or processed folders."""
    with pytest.raises(ValueError) as exc1:
        generate_all_synthetic_datasets(output_dir="data/raw")
    assert "Safety guard" in str(exc1.value)

    with pytest.raises(ValueError) as exc2:
        generate_all_synthetic_datasets(output_dir="data/processed")
    assert "Safety guard" in str(exc2.value)


def test_generate_all_creates_files_in_custom_dir():
    """Verify generate_all_synthetic_datasets writes all 3 datasets into a custom directory."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        created_files = generate_all_synthetic_datasets(
            output_dir=tmp_dir,
            n_respondents=20,
            seed=42,
        )

        assert len(created_files) == 3
        for key, filepath in created_files.items():
            path_obj = Path(filepath)
            assert path_obj.exists()
            assert path_obj.stat().st_size > 0

            # Verify it loads and validates
            df = load_csv(path_obj)
            assert len(df) == 20 * 5  # 20 respondents * 5 questions each
            res = validate_survey_data(df)
            assert res.is_valid is True
