"""Unit tests for src/poll_visualizer/data_loader.py."""

from pathlib import Path
import tempfile
import pandas as pd
import pytest

from poll_visualizer.data_loader import (
    DataLoaderError,
    EmptyFileError,
    MissingFileError,
    load_csv,
)


def test_load_valid_csv():
    """Test successful loading of a valid CSV file."""
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as tmp:
        tmp.write("response_id,respondent_id,answer\nRESP-1,USER-1,Yes\nRESP-2,USER-2,No\n")
        tmp_path = tmp.name

    try:
        df = load_csv(tmp_path)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert list(df.columns) == ["response_id", "respondent_id", "answer"]
        assert df.iloc[0]["answer"] == "Yes"
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_missing_file_handling():
    """Test that MissingFileError is raised for non-existent paths."""
    non_existent = Path("data/synthetic/definitely_not_here_12345.csv")
    with pytest.raises(MissingFileError) as exc_info:
        load_csv(non_existent)
    assert "File not found" in str(exc_info.value)


def test_empty_file_zero_bytes():
    """Test that EmptyFileError is raised when file has 0 bytes."""
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as tmp:
        tmp_path = tmp.name

    try:
        with pytest.raises(EmptyFileError) as exc_info:
            load_csv(tmp_path)
        assert "empty (0 bytes)" in str(exc_info.value)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_empty_file_no_columns():
    """Test that EmptyFileError is raised when file contains only whitespace/empty lines."""
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as tmp:
        tmp.write("   \n\n  \n")
        tmp_path = tmp.name

    try:
        with pytest.raises(EmptyFileError):
            load_csv(tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_supported_encoding_fallback_latin1():
    """Test that latin-1 encoded CSV is automatically loaded when UTF-8 decoding fails."""
    with tempfile.NamedTemporaryFile("wb", suffix=".csv", delete=False) as tmp:
        # Byte \xe9 is 'é' in latin-1 / ISO-8859-1 (invalid as standalone byte in UTF-8)
        content = "response_id,respondent_id,answer\nRESP-1,USER-1,Caf\xe9\n".encode("latin-1")
        tmp.write(content)
        tmp_path = tmp.name

    try:
        df = load_csv(tmp_path)
        assert len(df) == 1
        assert df.iloc[0]["answer"] == "Café"
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_csv_preserves_text_with_commas_quotes_and_unicode():
    """Test round-tripping preserves text with commas, quotation marks, and Unicode characters."""
    sample_text = 'Representative said, "Everything is resolved!"; café rating: ★★★★★'
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as tmp:
        df_in = pd.DataFrame(
            [
                {
                    "response_id": "RESP-100",
                    "respondent_id": "USER-100",
                    "answer": sample_text,
                }
            ]
        )
        df_in.to_csv(tmp.name, index=False, encoding="utf-8")
        tmp_path = tmp.name

    try:
        df_out = load_csv(tmp_path)
        assert len(df_out) == 1
        assert df_out.iloc[0]["answer"] == sample_text
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_source_file_not_modified_by_loading():
    """Test that loading a CSV does not mutate or modify the source file on disk."""
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as tmp:
        tmp.write("response_id,answer\nRESP-1,Val\n")
        tmp_path = tmp.name

    try:
        before_mtime = Path(tmp_path).stat().st_mtime_ns
        before_bytes = Path(tmp_path).read_bytes()

        _ = load_csv(tmp_path)

        after_mtime = Path(tmp_path).stat().st_mtime_ns
        after_bytes = Path(tmp_path).read_bytes()

        assert before_bytes == after_bytes
        assert before_mtime == after_mtime
    finally:
        Path(tmp_path).unlink(missing_ok=True)
