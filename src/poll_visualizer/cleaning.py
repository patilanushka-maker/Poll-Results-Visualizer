"""Data cleaning and normalization module for Poll Results Visualizer.

Provides safe, non-destructive data cleaning utilities for general-purpose
survey datasets, including whitespace trimming, missing segment normalization,
and transparent data transformation audits without altering source DataFrames.
"""

from typing import Any
import numpy as np
import pandas as pd

from poll_visualizer.metrics import _is_missing_value


def standardize_missing_values(series: pd.Series) -> pd.Series:
    """Normalize missing-value representations to standard NaN without altering valid zeros.

    Preserves valid zero ratings, 0 NPS scores, and 'No' answers.

    Parameters
    ----------
    series : pd.Series
        Input column series.

    Returns
    -------
    pd.Series
        Cleaned series with standardized missing markers.
    """
    cleaned = series.copy()
    mask = cleaned.apply(_is_missing_value)
    cleaned[mask] = np.nan
    return cleaned


def clean_survey_data(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Perform non-destructive standardization and cleaning on a survey DataFrame.

    Transformations:
    1. Strips leading and trailing whitespace from string columns.
    2. Standardizes 'question_type' to lowercase.
    3. Normalizes missing segment values to '(Missing)' for consistent group analysis.
    4. Tracks an audit log of all transformations applied.

    Parameters
    ----------
    df : pd.DataFrame
        Input survey dataset.

    Returns
    -------
    tuple[pd.DataFrame, dict[str, Any]]
        A tuple of (cleaned_df, audit_summary). The original DataFrame is not mutated.
    """
    if df is None or df.empty:
        return (
            df.copy() if df is not None else pd.DataFrame(),
            {"rows_cleaned": 0, "transformations": ["Dataset was empty; no cleaning applied."]},
        )

    cleaned = df.copy(deep=True)
    transformations: list[str] = []
    trimmed_cols = 0

    # 1. Whitespace stripping for object/string columns
    string_cols = cleaned.select_dtypes(include=["object"]).columns
    for col in string_cols:
        before = cleaned[col].astype(str)
        cleaned[col] = cleaned[col].apply(lambda x: x.strip() if isinstance(x, str) else x)
        after = cleaned[col].astype(str)
        diff_count = int((before != after).sum())
        if diff_count > 0:
            transformations.append(f"Trimmed whitespace in column '{col}' for {diff_count:,} row(s).")
            trimmed_cols += 1

    # 2. Normalize question_type to lowercase
    if "question_type" in cleaned.columns:
        cleaned["question_type"] = cleaned["question_type"].astype(str).str.strip().str.lower()
        transformations.append("Normalized 'question_type' entries to lowercase.")

    # 3. Missing segment normalization
    if "segment" in cleaned.columns:
        seg_missing_mask = cleaned["segment"].apply(_is_missing_value)
        seg_missing_cnt = int(seg_missing_mask.sum())
        if seg_missing_cnt > 0:
            cleaned.loc[seg_missing_mask, "segment"] = "(Missing)"
            transformations.append(
                f"Normalized {seg_missing_cnt:,} blank/null segment value(s) to '(Missing)'."
            )

    audit_summary: dict[str, Any] = {
        "rows_total": len(cleaned),
        "columns_processed": len(cleaned.columns),
        "trimmed_columns_count": trimmed_cols,
        "transformations": transformations if transformations else ["Data already adheres to hygiene standards."],
    }

    return cleaned, audit_summary
