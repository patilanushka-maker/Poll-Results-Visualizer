"""Statistical metrics module for Poll Results Visualizer.

Provides reusable, deterministic functions for computing response counts,
unweighted and weighted percentages, Likert distributions, rating metrics,
Net Promoter Scores (NPS), and multi-select frequencies.
"""

import json
import math
from typing import Any, Optional
import numpy as np
import pandas as pd


def _is_missing_value(val: Any) -> bool:
    """Determine whether a value represents an omitted or missing answer.

    Distinguishes genuine missing answers (None, NaN, blank string, 'nan', 'null')
    from valid negative answers (e.g. '0', 0, 'No', False).
    """
    if pd.isna(val) or val is None:
        return True
    if isinstance(val, str) and val.strip().lower() in ("", "nan", "none", "null"):
        return True
    return False


def _filter_question(df: pd.DataFrame, question_id: Optional[str]) -> pd.DataFrame:
    """Filter DataFrame to a specific question_id if supplied."""
    if question_id is not None:
        if "question_id" not in df.columns:
            raise KeyError("DataFrame is missing required column: 'question_id'.")
        filtered = df[df["question_id"] == question_id]
        if filtered.empty:
            # Return empty DataFrame with identical columns
            return filtered.copy()
        return filtered.copy()
    return df.copy()


def calculate_response_frequencies(
    df: pd.DataFrame,
    question_id: Optional[str] = None,
) -> pd.DataFrame:
    """Calculate unweighted response counts and percentages for a single question.

    The percentage denominator is strictly the number of valid (non-missing)
    answers for the specific question under analysis.

    Parameters
    ----------
    df : pd.DataFrame
        Survey dataset in long-format.
    question_id : str, optional
        Specific question identifier to isolate. If None, df is assumed
        to already contain responses for a single question.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns ['answer', 'count', 'percentage'],
        sorted by count descending.
    """
    sub_df = _filter_question(df, question_id)
    if sub_df.empty or "answer" not in sub_df.columns:
        return pd.DataFrame(columns=["answer", "count", "percentage"])

    valid_mask = ~sub_df["answer"].apply(_is_missing_value)
    valid_answers = sub_df.loc[valid_mask, "answer"].astype(str).str.strip()

    valid_total = len(valid_answers)
    if valid_total == 0:
        return pd.DataFrame(columns=["answer", "count", "percentage"])

    counts = valid_answers.value_counts()
    result = pd.DataFrame(
        {
            "answer": counts.index,
            "count": counts.values,
            "percentage": np.round((counts.values / valid_total) * 100.0, 2),
        }
    )
    return result


def calculate_weighted_frequencies(
    df: pd.DataFrame,
    question_id: Optional[str] = None,
    weight_col: str = "weight",
) -> pd.DataFrame:
    """Calculate unweighted and weighted response counts and percentages.

    Policy on Weights:
    - Weights must be strictly positive numeric values ($w > 0$).
    - Missing, non-numeric, zero, or negative weights raise a ValueError with
      actionable diagnostics.
    - Valid weights alter weighted percentage distributions without modifying
      unweighted respondent counts.
    - Denominator is the sum of positive weights among valid answers.

    Parameters
    ----------
    df : pd.DataFrame
        Survey dataset in long-format.
    question_id : str, optional
        Specific question identifier to isolate.
    weight_col : str, optional
        Column containing post-stratification weights, default 'weight'.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns:
        ['answer', 'count', 'percentage', 'weighted_count', 'weighted_percentage'].

    Raises
    ------
    KeyError
        If weight_col is missing from df.
    ValueError
        If weight_col contains null, non-numeric, zero, or negative values for valid responses.
    """
    sub_df = _filter_question(df, question_id)
    if sub_df.empty:
        return pd.DataFrame(
            columns=["answer", "count", "percentage", "weighted_count", "weighted_percentage"]
        )

    if weight_col not in sub_df.columns:
        raise KeyError(f"Weight column '{weight_col}' was not found in the DataFrame.")

    valid_mask = ~sub_df["answer"].apply(_is_missing_value)
    valid_df = sub_df[valid_mask].copy()

    if valid_df.empty:
        return pd.DataFrame(
            columns=["answer", "count", "percentage", "weighted_count", "weighted_percentage"]
        )

    # Validate weight values for all valid response rows
    raw_weights = valid_df[weight_col]
    numeric_weights = pd.to_numeric(raw_weights, errors="coerce")

    # Check for NaN / non-numeric weights
    nan_weights_count = int(numeric_weights.isna().sum())
    if nan_weights_count > 0:
        raise ValueError(
            f"Weight validation error: Found {nan_weights_count} missing or non-numeric weight(s) "
            f"in column '{weight_col}'. Weights cannot be null or non-numeric."
        )

    # Check for non-positive weights (<= 0)
    non_positive_count = int((numeric_weights <= 0).sum())
    if non_positive_count > 0:
        raise ValueError(
            f"Weight validation error: Found {non_positive_count} non-positive weight(s) (<= 0) "
            f"in column '{weight_col}'. Survey weights must be strictly positive (> 0)."
        )

    valid_df["_clean_weight"] = numeric_weights
    valid_df["_clean_answer"] = valid_df["answer"].astype(str).str.strip()

    total_valid_count = len(valid_df)
    total_valid_weight = valid_df["_clean_weight"].sum()

    grouped = valid_df.groupby("_clean_answer", as_index=False).agg(
        count=("_clean_answer", "count"),
        weighted_count=("_clean_weight", "sum"),
    )

    grouped["percentage"] = np.round((grouped["count"] / total_valid_count) * 100.0, 2)
    grouped["weighted_percentage"] = np.round(
        (grouped["weighted_count"] / total_valid_weight) * 100.0, 2
    )
    grouped["weighted_count"] = np.round(grouped["weighted_count"], 2)

    grouped = grouped.rename(columns={"_clean_answer": "answer"})
    grouped = grouped.sort_values(by=["count", "weighted_count"], ascending=[False, False])
    return grouped.reset_index(drop=True)[
        ["answer", "count", "percentage", "weighted_count", "weighted_percentage"]
    ]


def calculate_rating_metrics(
    df: pd.DataFrame,
    question_id: Optional[str] = None,
    scale_min: int = 1,
    scale_max: int = 5,
) -> dict[str, Any]:
    """Calculate summary statistics for discrete numeric rating questions.

    Computes valid count, missing count, mean, median, sample standard deviation
    (ddof=1), min, and max.

    Parameters
    ----------
    df : pd.DataFrame
        Survey dataset in long-format.
    question_id : str, optional
        Specific rating question identifier.
    scale_min : int, optional
        Minimum allowed rating, default 1.
    scale_max : int, optional
        Maximum allowed rating, default 5.

    Returns
    -------
    dict[str, Any]
        Dictionary with keys:
        ['valid_count', 'missing_count', 'mean', 'median', 'std', 'min', 'max']

    Raises
    ------
    ValueError
        If an answered row contains non-numeric text or rating values outside [scale_min, scale_max].
    """
    sub_df = _filter_question(df, question_id)
    if sub_df.empty or "answer" not in sub_df.columns:
        return {
            "valid_count": 0,
            "missing_count": 0,
            "mean": None,
            "median": None,
            "std": None,
            "min": None,
            "max": None,
        }

    missing_mask = sub_df["answer"].apply(_is_missing_value)
    missing_count = int(missing_mask.sum())
    valid_answers = sub_df.loc[~missing_mask, "answer"]

    if len(valid_answers) == 0:
        return {
            "valid_count": 0,
            "missing_count": missing_count,
            "mean": None,
            "median": None,
            "std": None,
            "min": None,
            "max": None,
        }

    # Safe conversion to numeric
    numeric_ratings = pd.to_numeric(valid_answers, errors="coerce")
    nan_count = int(numeric_ratings.isna().sum())
    if nan_count > 0:
        raise ValueError(
            f"Rating calculation error: Found {nan_count} non-numeric rating answer(s). "
            f"Expected numeric values between {scale_min} and {scale_max}."
        )

    # Check bounds
    out_of_bounds = (numeric_ratings < scale_min) | (numeric_ratings > scale_max)
    if out_of_bounds.any():
        bad_count = int(out_of_bounds.sum())
        sample_bads = list(numeric_ratings[out_of_bounds].head(3))
        raise ValueError(
            f"Rating calculation error: Found {bad_count} rating value(s) outside [{scale_min}, {scale_max}]. "
            f"Sample invalid values: {sample_bads}."
        )

    values = numeric_ratings.values
    valid_count = len(values)
    mean_val = float(np.mean(values))
    median_val = float(np.median(values))
    # Sample standard deviation (ddof=1) if N >= 2, else None
    std_val = float(np.std(values, ddof=1)) if valid_count >= 2 else None
    min_val = float(np.min(values))
    max_val = float(np.max(values))

    return {
        "valid_count": valid_count,
        "missing_count": missing_count,
        "mean": round(mean_val, 3),
        "median": round(median_val, 3),
        "std": round(std_val, 3) if std_val is not None else None,
        "min": int(min_val),
        "max": int(max_val),
    }


def calculate_likert_distribution(
    df: pd.DataFrame,
    question_id: Optional[str] = None,
    scale_min: int = 1,
    scale_max: int = 5,
) -> pd.DataFrame:
    """Generate complete Likert category frequency distribution.

    Preserves the logical ordered sequence of ratings (scale_min to scale_max)
    and guarantees that zero-count categories are explicitly included.

    Parameters
    ----------
    df : pd.DataFrame
        Survey dataset in long-format.
    question_id : str, optional
        Specific rating question identifier.
    scale_min : int, optional
        Minimum rating score, default 1.
    scale_max : int, optional
        Maximum rating score, default 5.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns ['rating', 'count', 'percentage'],
        indexed 0 to (scale_max - scale_min).
    """
    sub_df = _filter_question(df, question_id)
    all_scale_values = [str(i) for i in range(scale_min, scale_max + 1)]

    if sub_df.empty or "answer" not in sub_df.columns:
        return pd.DataFrame(
            {
                "rating": [int(x) for x in all_scale_values],
                "count": [0] * len(all_scale_values),
                "percentage": [0.0] * len(all_scale_values),
            }
        )

    valid_mask = ~sub_df["answer"].apply(_is_missing_value)
    valid_answers = sub_df.loc[valid_mask, "answer"].astype(str).str.strip()

    valid_total = len(valid_answers)
    counts_map = valid_answers.value_counts().to_dict()

    rows = []
    for val_str in all_scale_values:
        cnt = counts_map.get(val_str, 0)
        pct = round((cnt / valid_total) * 100.0, 2) if valid_total > 0 else 0.0
        rows.append(
            {
                "rating": int(val_str),
                "count": cnt,
                "percentage": pct,
            }
        )

    return pd.DataFrame(rows)


def calculate_nps(
    df: pd.DataFrame,
    question_id: Optional[str] = None,
    weight_col: Optional[str] = None,
) -> dict[str, Any]:
    """Calculate Net Promoter Score (NPS) and category breakdowns.

    Classification:
    - Detractors: scores 0 to 6
    - Passives: scores 7 to 8
    - Promoters: scores 9 to 10

    Formula:
    $$NPS = % Promoters - % Detractors$$ (scale: -100 to +100).

    Parameters
    ----------
    df : pd.DataFrame
        Survey dataset in long-format.
    question_id : str, optional
        Specific NPS question identifier.
    weight_col : str, optional
        Optional post-stratification weight column. If provided, calculates
        weighted percentages and weighted NPS score.

    Returns
    -------
    dict[str, Any]
        Dictionary with keys:
        ['valid_count', 'missing_count', 'promoters_count', 'passives_count',
         'detractors_count', 'promoter_pct', 'passive_pct', 'detractor_pct', 'nps_score']

    Raises
    ------
    ValueError
        If an answered row contains non-numeric text or NPS scores outside [0, 10].
    """
    sub_df = _filter_question(df, question_id)
    if sub_df.empty or "answer" not in sub_df.columns:
        return {
            "valid_count": 0,
            "missing_count": 0,
            "promoters_count": 0,
            "passives_count": 0,
            "detractors_count": 0,
            "promoter_pct": 0.0,
            "passive_pct": 0.0,
            "detractor_pct": 0.0,
            "nps_score": None,
        }

    missing_mask = sub_df["answer"].apply(_is_missing_value)
    missing_count = int(missing_mask.sum())
    valid_df = sub_df[~missing_mask].copy()

    valid_count = len(valid_df)
    if valid_count == 0:
        return {
            "valid_count": 0,
            "missing_count": missing_count,
            "promoters_count": 0,
            "passives_count": 0,
            "detractors_count": 0,
            "promoter_pct": 0.0,
            "passive_pct": 0.0,
            "detractor_pct": 0.0,
            "nps_score": None,
        }

    # Safe numeric validation
    numeric_nps = pd.to_numeric(valid_df["answer"], errors="coerce")
    nan_count = int(numeric_nps.isna().sum())
    if nan_count > 0:
        raise ValueError(
            f"NPS calculation error: Found {nan_count} non-numeric NPS answer(s). "
            "NPS answers must be integers between 0 and 10."
        )

    out_of_bounds = (numeric_nps < 0) | (numeric_nps > 10)
    if out_of_bounds.any():
        bad_count = int(out_of_bounds.sum())
        sample_bads = list(numeric_nps[out_of_bounds].head(3))
        raise ValueError(
            f"NPS calculation error: Found {bad_count} score(s) outside [0, 10]. "
            f"Sample invalid scores: {sample_bads}."
        )

    valid_df["_nps_num"] = numeric_nps

    # Classify responses
    promoters_mask = valid_df["_nps_num"] >= 9
    passives_mask = (valid_df["_nps_num"] >= 7) & (valid_df["_nps_num"] <= 8)
    detractors_mask = valid_df["_nps_num"] <= 6

    promoters_cnt = int(promoters_mask.sum())
    passives_cnt = int(passives_mask.sum())
    detractors_cnt = int(detractors_mask.sum())

    if weight_col is not None:
        if weight_col not in valid_df.columns:
            raise KeyError(f"Weight column '{weight_col}' was not found in DataFrame.")
        num_w = pd.to_numeric(valid_df[weight_col], errors="coerce")
        if num_w.isna().any() or (num_w <= 0).any():
            raise ValueError(
                f"Weight validation error in NPS: Invalid weights in '{weight_col}'."
            )
        total_weight = num_w.sum()
        promoter_pct = round((num_w[promoters_mask].sum() / total_weight) * 100.0, 2)
        passive_pct = round((num_w[passives_mask].sum() / total_weight) * 100.0, 2)
        detractor_pct = round((num_w[detractors_mask].sum() / total_weight) * 100.0, 2)
    else:
        promoter_pct = round((promoters_cnt / valid_count) * 100.0, 2)
        passive_pct = round((passives_cnt / valid_count) * 100.0, 2)
        detractor_pct = round((detractors_cnt / valid_count) * 100.0, 2)

    nps_score = round(promoter_pct - detractor_pct, 2)

    return {
        "valid_count": valid_count,
        "missing_count": missing_count,
        "promoters_count": promoters_cnt,
        "passives_count": passives_cnt,
        "detractors_count": detractors_cnt,
        "promoter_pct": promoter_pct,
        "passive_pct": passive_pct,
        "detractor_pct": detractor_pct,
        "nps_score": nps_score,
    }


def calculate_multiselect_frequencies(
    df: pd.DataFrame,
    question_id: Optional[str] = None,
) -> pd.DataFrame:
    """Calculate frequencies and percentages for multi-select JSON array questions.

    Policy on Multi-Select:
    - Denominator = total unique respondents who provided a valid answer to the question.
    - Percentages reflect the proportion of respondents selecting each option.
    - Percentages across options naturally sum to >= 100% when respondents pick > 1 option.
    - Duplicate selections within a single respondent's answer (e.g. ['A', 'A'])
      are counted only once per respondent.
    - Malformed JSON strings or non-list answers raise a ValueError with diagnostics.

    Parameters
    ----------
    df : pd.DataFrame
        Survey dataset in long-format.
    question_id : str, optional
        Specific multi-select question identifier.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns ['option', 'count', 'percentage'],
        sorted by count descending.
    """
    sub_df = _filter_question(df, question_id)
    if sub_df.empty or "answer" not in sub_df.columns:
        return pd.DataFrame(columns=["option", "count", "percentage"])

    missing_mask = sub_df["answer"].apply(_is_missing_value)
    valid_rows = sub_df[~missing_mask]

    total_respondents = len(valid_rows)
    if total_respondents == 0:
        return pd.DataFrame(columns=["option", "count", "percentage"])

    option_counts: dict[str, int] = {}

    for idx, raw_val in enumerate(valid_rows["answer"]):
        if isinstance(raw_val, (list, tuple)):
            parsed = list(raw_val)
        else:
            try:
                parsed = json.loads(str(raw_val))
                if not isinstance(parsed, list):
                    raise ValueError(f"Expected a JSON list, got {type(parsed).__name__}")
            except Exception as err:
                raise ValueError(
                    f"Malformed multi-select answer at row index {idx}: '{raw_val}'. "
                    f"Error: {err}"
                ) from err

        # Deduplicate per respondent so an option is counted at most once per respondent
        unique_options_for_resp = set(str(opt).strip() for opt in parsed if str(opt).strip())
        for opt in unique_options_for_resp:
            option_counts[opt] = option_counts.get(opt, 0) + 1

    if not option_counts:
        return pd.DataFrame(columns=["option", "count", "percentage"])

    rows = []
    for opt, cnt in sorted(option_counts.items(), key=lambda x: x[1], reverse=True):
        pct = round((cnt / total_respondents) * 100.0, 2)
        rows.append({"option": opt, "count": cnt, "percentage": pct})

    return pd.DataFrame(rows)


def calculate_proportion_ci(
    count: int,
    total: int,
    confidence: float = 0.95,
) -> tuple[float, float]:
    """Calculate the Wilson Score confidence interval for an unweighted proportion.

    Assumptions:
    - Independent simple random sampling (SRS).
    - Unweighted observations.
    - Yields accurate coverage probabilities even for small sample sizes or extreme proportions.

    Parameters
    ----------
    count : int
        Number of positive occurrences (0 <= count <= total).
    total : int
        Total sample size (total >= 0).
    confidence : float, optional
        Confidence level, strictly between 0.0 and 1.0, default 0.95.

    Returns
    -------
    tuple[float, float]
        (lower_bound, upper_bound) as percentages between 0.0 and 100.0.

    Raises
    ------
    ValueError
        If confidence is not strictly between 0 and 1, if total < 0, or if count < 0 or count > total.
    """
    if confidence <= 0.0 or confidence >= 1.0:
        raise ValueError(
            f"Confidence level must be strictly between 0.0 and 1.0, got {confidence}."
        )

    if total < 0:
        raise ValueError(f"Total sample size cannot be negative, got {total}.")

    if total == 0:
        return (0.0, 0.0)

    if count < 0 or count > total:
        raise ValueError(
            f"Invalid count: count ({count}) must satisfy 0 <= count <= total ({total})."
        )

    from statistics import NormalDist

    # Two-tailed standard normal critical value z
    z = NormalDist().inv_cdf(1.0 - (1.0 - confidence) / 2.0)

    n = float(total)
    p = float(count) / n

    denom = 1.0 + (z**2) / n
    center = (p + (z**2) / (2.0 * n)) / denom
    half_width = (z * math.sqrt((p * (1.0 - p) / n) + (z**2) / (4.0 * (n**2)))) / denom

    lower = max(0.0, (center - half_width) * 100.0)
    upper = min(100.0, (center + half_width) * 100.0)

    return (round(lower, 2), round(upper, 2))


def summarize_question_metrics(df: pd.DataFrame, question_id: str) -> dict[str, Any]:
    """Dispatch summary metrics calculation based on question_type.

    Parameters
    ----------
    df : pd.DataFrame
        Survey dataset in long-format.
    question_id : str
        Target question identifier.

    Returns
    -------
    dict[str, Any]
        Structured dictionary containing question metadata and metric outputs.
    """
    q_df = _filter_question(df, question_id)
    if q_df.empty:
        raise KeyError(f"Question ID '{question_id}' not found in dataset.")

    q_type = str(q_df["question_type"].iloc[0]).strip().lower()
    q_text = str(q_df["question_text"].iloc[0])

    summary: dict[str, Any] = {
        "question_id": question_id,
        "question_text": q_text,
        "question_type": q_type,
        "total_records": len(q_df),
    }

    if q_type == "rating":
        summary["metrics"] = calculate_rating_metrics(q_df)
        summary["distribution"] = calculate_likert_distribution(q_df)
    elif q_type == "nps":
        summary["metrics"] = calculate_nps(q_df)
    elif q_type == "single_choice":
        summary["distribution"] = calculate_response_frequencies(q_df)
    elif q_type == "multi_select":
        summary["distribution"] = calculate_multiselect_frequencies(q_df)
    elif q_type == "text":
        valid_texts = q_df[~q_df["answer"].apply(_is_missing_value)]["answer"].tolist()
        summary["valid_count"] = len(valid_texts)
        summary["missing_count"] = len(q_df) - len(valid_texts)
        summary["sample_responses"] = valid_texts[:5]
    else:
        summary["distribution"] = calculate_response_frequencies(q_df)

    return summary
