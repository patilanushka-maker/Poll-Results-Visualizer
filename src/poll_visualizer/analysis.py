"""Segment analysis and cross-tabulation module for Poll Results Visualizer.

Provides group comparisons, demographic cross-tabulations, and segment-level
statistical summaries for ratings, NPS, and categorical survey questions.
"""

from typing import Any, Optional, Union
import numpy as np
import pandas as pd

from poll_visualizer.metrics import (
    _filter_question,
    _is_missing_value,
    calculate_nps,
    calculate_rating_metrics,
)


def cross_tabulate_by_segment(
    df: pd.DataFrame,
    question_id: str,
    segment_col: str = "segment",
    normalize: Union[str, bool] = "index",
    missing_segment_label: str = "(Missing)",
) -> pd.DataFrame:
    """Generate a cross-tabulation of categorical survey responses by demographic segment.

    Parameters
    ----------
    df : pd.DataFrame
        Survey dataset in long-format.
    question_id : str
        Specific question identifier to isolate.
    segment_col : str, optional
        Column representing respondent segment or demographic, default 'segment'.
    normalize : Union[str, bool], optional
        Normalization mode for pd.crosstab:
        - 'index': row percentages (distribution of answers within each segment, summing to 100%).
        - 'columns': column percentages (distribution of segments within each answer).
        - 'all': percentage of total valid responses.
        - False or 'none': raw unweighted response counts.
        Default is 'index'.
    missing_segment_label : str, optional
        Label assigned to rows where segment is null or blank, default '(Missing)'.

    Returns
    -------
    pd.DataFrame
        Contingency matrix with segments on the index and answer options on columns.

    Raises
    ------
    KeyError
        If question_id or segment_col is not found in df.
    """
    sub_df = _filter_question(df, question_id)
    if sub_df.empty:
        raise KeyError(f"Question ID '{question_id}' was not found in dataset.")

    if segment_col not in sub_df.columns:
        raise KeyError(f"Segment column '{segment_col}' was not found in DataFrame.")

    # Exclude missing answers from the contingency table
    valid_mask = ~sub_df["answer"].apply(_is_missing_value)
    valid_df = sub_df[valid_mask].copy()

    if valid_df.empty:
        return pd.DataFrame()

    # Fill missing segment values explicitly
    segment_series = valid_df[segment_col].apply(
        lambda x: missing_segment_label if _is_missing_value(x) else str(x).strip()
    )
    answer_series = valid_df["answer"].astype(str).str.strip()

    # Normalize parameter handling
    norm_arg: Any = False
    if normalize in ("index", "columns", "all"):
        norm_arg = normalize
    elif normalize is True:
        norm_arg = "all"

    ctab = pd.crosstab(
        index=segment_series,
        columns=answer_series,
        normalize=norm_arg,
    )

    if norm_arg is not False:
        ctab = np.round(ctab * 100.0, 2)

    ctab.index.name = segment_col
    ctab.columns.name = "answer"
    return ctab


def group_rating_summary(
    df: pd.DataFrame,
    question_id: str,
    group_col: str = "segment",
    scale_min: int = 1,
    scale_max: int = 5,
    missing_group_label: str = "(Missing)",
) -> pd.DataFrame:
    """Calculate rating descriptive statistics grouped by segment.

    Computes valid count, missing count, mean, median, sample std, min, and max
    for each group.

    Parameters
    ----------
    df : pd.DataFrame
        Survey dataset in long-format.
    question_id : str
        Specific rating question identifier.
    group_col : str, optional
        Grouping column, default 'segment'.
    scale_min : int, optional
        Minimum rating scale bound, default 1.
    scale_max : int, optional
        Maximum rating scale bound, default 5.
    missing_group_label : str, optional
        Label for records with missing group values, default '(Missing)'.

    Returns
    -------
    pd.DataFrame
        DataFrame indexed by segment with rating metric columns:
        ['valid_count', 'missing_count', 'mean', 'median', 'std', 'min', 'max'].
    """
    sub_df = _filter_question(df, question_id)
    if sub_df.empty:
        raise KeyError(f"Question ID '{question_id}' was not found in dataset.")

    if group_col not in sub_df.columns:
        raise KeyError(f"Group column '{group_col}' was not found in DataFrame.")

    clean_df = sub_df.copy()
    clean_df["_clean_group"] = clean_df[group_col].apply(
        lambda x: missing_group_label if _is_missing_value(x) else str(x).strip()
    )

    results = []
    for group_name, group_data in clean_df.groupby("_clean_group"):
        stats = calculate_rating_metrics(
            group_data,
            question_id=None,
            scale_min=scale_min,
            scale_max=scale_max,
        )
        stats[group_col] = group_name
        results.append(stats)

    res_df = pd.DataFrame(results)
    if res_df.empty:
        return pd.DataFrame(
            columns=[group_col, "valid_count", "missing_count", "mean", "median", "std", "min", "max"]
        ).set_index(group_col)

    res_df = res_df.set_index(group_col)
    col_order = ["valid_count", "missing_count", "mean", "median", "std", "min", "max"]
    return res_df[col_order].sort_index()


def group_nps_summary(
    df: pd.DataFrame,
    question_id: str,
    group_col: str = "segment",
    missing_group_label: str = "(Missing)",
) -> pd.DataFrame:
    """Calculate Net Promoter Score (NPS) and category breakdowns grouped by segment.

    Parameters
    ----------
    df : pd.DataFrame
        Survey dataset in long-format.
    question_id : str
        Specific NPS question identifier.
    group_col : str, optional
        Grouping column, default 'segment'.
    missing_group_label : str, optional
        Label for records with missing group values, default '(Missing)'.

    Returns
    -------
    pd.DataFrame
        DataFrame indexed by segment with columns:
        ['valid_count', 'missing_count', 'promoters_count', 'passives_count',
         'detractors_count', 'promoter_pct', 'passive_pct', 'detractor_pct', 'nps_score'].
    """
    sub_df = _filter_question(df, question_id)
    if sub_df.empty:
        raise KeyError(f"Question ID '{question_id}' was not found in dataset.")

    if group_col not in sub_df.columns:
        raise KeyError(f"Group column '{group_col}' was not found in DataFrame.")

    clean_df = sub_df.copy()
    clean_df["_clean_group"] = clean_df[group_col].apply(
        lambda x: missing_group_label if _is_missing_value(x) else str(x).strip()
    )

    results = []
    for group_name, group_data in clean_df.groupby("_clean_group"):
        nps_stats = calculate_nps(group_data, question_id=None)
        nps_stats[group_col] = group_name
        results.append(nps_stats)

    res_df = pd.DataFrame(results)
    if res_df.empty:
        cols = [
            group_col,
            "valid_count",
            "missing_count",
            "promoters_count",
            "passives_count",
            "detractors_count",
            "promoter_pct",
            "passive_pct",
            "detractor_pct",
            "nps_score",
        ]
        return pd.DataFrame(columns=cols).set_index(group_col)

    res_df = res_df.set_index(group_col)
    col_order = [
        "valid_count",
        "missing_count",
        "promoters_count",
        "passives_count",
        "detractors_count",
        "promoter_pct",
        "passive_pct",
        "detractor_pct",
        "nps_score",
    ]
    return res_df[col_order].sort_index()
