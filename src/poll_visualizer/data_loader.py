"""Data loader module for Poll Results Visualizer.

Provides robust CSV ingestion with encoding fallback, file integrity checks,
and clean separation of loading from validation and cleaning.
"""

from pathlib import Path
from typing import Any, Optional, Union
import pandas as pd


class DataLoaderError(Exception):
    """Base exception for all data loading errors."""

    pass


class MissingFileError(DataLoaderError, FileNotFoundError):
    """Raised when the specified file path does not exist."""

    pass


class EmptyFileError(DataLoaderError, ValueError):
    """Raised when the target CSV is empty or has no readable columns."""

    pass


def load_csv(
    filepath_or_buffer: Union[str, Path, Any],
    encoding: str = "utf-8",
    fallback_encodings: tuple[str, ...] = ("latin-1", "cp1252"),
    **kwargs: Any,
) -> pd.DataFrame:
    """Load a CSV file into a pandas DataFrame.

    Features:
    - Path existence check with actionable error messaging.
    - Zero-byte and empty file detection.
    - UTF-8 decoding with automatic fallback to secondary encodings.
    - Preserves data without silently modifying or discarding rows/columns.
    - Does not overwrite or mutate the source file.

    Parameters
    ----------
    filepath_or_buffer : Union[str, Path, Any]
        File path string, Path object, or file-like buffer.
    encoding : str, optional
        Primary character encoding to attempt, by default "utf-8".
    fallback_encodings : tuple[str, ...], optional
        Encodings to try sequentially if a UnicodeDecodeError occurs,
        by default ("latin-1", "cp1252").
    **kwargs : Any
        Additional keyword arguments forwarded directly to `pandas.read_csv`.

    Returns
    -------
    pd.DataFrame
        Loaded tabular data.

    Raises
    ------
    MissingFileError
        If the given file path does not exist.
    EmptyFileError
        If the file is 0 bytes or contains no columns/records.
    DataLoaderError
        If parsing fails or file cannot be decoded with any configured encoding.
    """
    # 1. Path existence and file size validation (for str/Path inputs)
    if isinstance(filepath_or_buffer, (str, Path)):
        path_obj = Path(filepath_or_buffer)
        if not path_obj.exists():
            raise MissingFileError(
                f"File not found: '{filepath_or_buffer}'. "
                "Please verify the file path and ensure the file exists."
            )
        if path_obj.is_file() and path_obj.stat().st_size == 0:
            raise EmptyFileError(
                f"The file '{filepath_or_buffer}' is completely empty (0 bytes). "
                "Cannot load an empty file."
            )

    # 2. Attempt reading with primary encoding, then fallbacks
    encodings_to_try = [encoding] + [enc for enc in fallback_encodings if enc != encoding]
    last_decode_err: Optional[UnicodeDecodeError] = None

    for enc in encodings_to_try:
        if hasattr(filepath_or_buffer, "seek"):
            try:
                filepath_or_buffer.seek(0)
            except Exception:
                pass
        try:
            df = pd.read_csv(
                filepath_or_buffer,
                encoding=enc,
                **kwargs,
            )
            # Check for empty dataframe without columns
            if df.empty and len(df.columns) == 0:
                raise EmptyFileError(
                    f"The file '{filepath_or_buffer}' contains no parseable columns or data."
                )
            return df
        except UnicodeDecodeError as err:
            last_decode_err = err
            continue
        except pd.errors.EmptyDataError as err:
            raise EmptyFileError(
                f"No data or columns could be parsed from '{filepath_or_buffer}'."
            ) from err
        except (MissingFileError, EmptyFileError):
            raise
        except Exception as err:
            raise DataLoaderError(
                f"Failed to parse CSV from '{filepath_or_buffer}': {err}"
            ) from err

    # If all encodings failed due to UnicodeDecodeError
    raise DataLoaderError(
        f"Unable to decode file '{filepath_or_buffer}' using encodings: {encodings_to_try}. "
        f"Last error: {last_decode_err}"
    )
