"""Data validation module for Poll Results Visualizer.

Provides schema verification, data-quality diagnostics, value bound checks,
and structured validation results for general-purpose survey data.
"""

from dataclasses import dataclass, field
import json
from typing import Any, Optional
import pandas as pd

# Allowed question types supported by the general-purpose schema
ALLOWED_QUESTION_TYPES: frozenset[str] = frozenset(
    {"single_choice", "rating", "nps", "multi_select", "text"}
)

# Mandatory columns that must exist in the input DataFrame
REQUIRED_COLUMNS: list[str] = [
    "response_id",
    "respondent_id",
    "survey_type",
    "question_id",
    "question_text",
    "question_type",
    "answer",
    "response_timestamp",
]

# Rating and NPS numerical bounds
RATING_MIN: int = 1
RATING_MAX: int = 5
NPS_MIN: int = 0
NPS_MAX: int = 10


@dataclass
class ValidationResult:
    """Structured report returned by the survey data validation process.

    Attributes
    ----------
    is_valid : bool
        True if zero validation errors were encountered, False otherwise.
    errors : list[str]
        Actionable error descriptions indicating critical data violations.
    warnings : list[str]
        Diagnostic warnings indicating missing optional fields, skipped answers,
        or data hygiene issues that do not invalidate the schema.
    summary : dict[str, Any]
        High-level dataset metadata and metrics collected during validation.
    """

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert the validation result to a serializable dictionary."""
        return {
            "is_valid": self.is_valid,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "summary": dict(self.summary),
        }

    def summary_report(self) -> str:
        """Produce a human-readable text summary of the validation outcome."""
        status = "PASSED" if self.is_valid else "FAILED"
        lines = [
            f"Validation Status: {status}",
            f"Total Errors: {len(self.errors)}",
            f"Total Warnings: {len(self.warnings)}",
        ]
        if self.errors:
            lines.append("Errors:")
            for err in self.errors:
                lines.append(f"  - [ERROR] {err}")
        if self.warnings:
            lines.append("Warnings:")
            for warn in self.warnings:
                lines.append(f"  - [WARNING] {warn}")
        return "\n".join(lines)


def _is_missing_value(val: Any) -> bool:
    """Check if a value represents an omitted or missing answer.

    Distinguishes genuine missing/unanswered states from valid negative answers
    such as '0', 0, False, or 'No'.
    """
    if pd.isna(val) or val is None:
        return True
    if isinstance(val, str) and val.strip().lower() in ("", "nan", "none", "null"):
        return True
    return False


def validate_survey_data(df: pd.DataFrame) -> ValidationResult:
    """Validate a long-format survey response DataFrame.

    Checks:
    1. Schema conformity: required columns presence.
    2. Essential identifiers completeness: response_id, respondent_id, question_id.
    3. Uniqueness: unique response_id, no duplicate respondent/question answers.
    4. Allowed question types: single_choice, rating, nps, multi_select, text.
    5. Rating value bounds: integer in [1, 5] (non-numeric reports error).
    6. NPS value bounds: integer in [0, 10] (non-numeric reports error).
    7. Multi-select format: valid JSON array string.
    8. Timestamp integrity: datetime parseability check.
    9. Missing answer auditing: missing answers tracked separately from negative responses.

    Parameters
    ----------
    df : pd.DataFrame
        Input survey dataset in long-format.

    Returns
    -------
    ValidationResult
        Structured validation outcome with validity status, errors, warnings,
        and diagnostic summary.
    """
    errors: list[str] = []
    warnings: list[str] = []
    summary: dict[str, Any] = {}

    if not isinstance(df, pd.DataFrame):
        return ValidationResult(
            is_valid=False,
            errors=[f"Expected a pandas DataFrame, but received {type(df).__name__}."],
            warnings=[],
            summary={"total_rows": 0},
        )

    summary["total_rows"] = len(df)

    # 1. Required Columns Check
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        errors.append(
            f"Missing required column(s): {', '.join(sorted(missing_cols))}. "
            f"Required columns are: {', '.join(REQUIRED_COLUMNS)}."
        )
        return ValidationResult(
            is_valid=False,
            errors=errors,
            warnings=warnings,
            summary=summary,
        )

    if len(df) == 0:
        warnings.append("Dataset contains 0 rows.")
        return ValidationResult(
            is_valid=True,
            errors=[],
            warnings=warnings,
            summary={"total_rows": 0, "total_respondents": 0, "total_questions": 0},
        )

    # 2. Missing Essential Identifiers
    for id_col in ("response_id", "respondent_id", "question_id"):
        null_count = df[id_col].apply(_is_missing_value).sum()
        if null_count > 0:
            errors.append(
                f"Column '{id_col}' contains {null_count} missing or empty value(s). "
                "Essential identifiers cannot be null."
            )

    # 3. Duplicate Checks
    # 3a. Response ID uniqueness
    dup_resp_ids = df["response_id"].dropna().duplicated().sum()
    if dup_resp_ids > 0:
        errors.append(
            f"Found {dup_resp_ids} duplicate 'response_id' entry/entries. "
            "Every response_id must be globally unique."
        )

    # 3b. Duplicate respondent-question pairs for single-answer types
    single_answer_types = {"single_choice", "rating", "nps", "text"}
    single_mask = df["question_type"].astype(str).str.strip().isin(single_answer_types)
    single_df = df[single_mask]
    dup_pairs = single_df.duplicated(subset=["respondent_id", "question_id"]).sum()
    if dup_pairs > 0:
        errors.append(
            f"Found {dup_pairs} duplicate (respondent_id, question_id) row(s) "
            "for single-answer question types. Each respondent should answer each "
            "single-response question at most once."
        )

    # 4. Question Type Validation
    type_series = df["question_type"].astype(str).str.strip()
    invalid_types = set(type_series) - ALLOWED_QUESTION_TYPES
    if invalid_types:
        invalid_count = type_series.isin(invalid_types).sum()
        errors.append(
            f"Found {invalid_count} row(s) with invalid 'question_type': {sorted(invalid_types)}. "
            f"Allowed types are: {sorted(ALLOWED_QUESTION_TYPES)}."
        )

    summary["question_types"] = dict(type_series.value_counts())
    summary["total_respondents"] = int(df["respondent_id"].nunique())
    summary["total_questions"] = int(df["question_id"].nunique())

    # 5. Missing Answers Tracking (Separate from negative answers)
    missing_answer_mask = df["answer"].apply(_is_missing_value)
    missing_answers_count = int(missing_answer_mask.sum())
    summary["missing_answers_count"] = missing_answers_count
    if missing_answers_count > 0:
        warnings.append(
            f"Dataset contains {missing_answers_count} unanswered/skipped response(s). "
            "These will be treated as non-responses rather than negative answers."
        )

    # 6. Value Bounds and Format Checks
    # Iterate over answered rows
    valid_answers_df = df[~missing_answer_mask]

    # 6a. Rating Bounds Check [1, 5]
    rating_rows = valid_answers_df[valid_answers_df["question_type"] == "rating"]
    rating_non_numeric = 0
    rating_out_of_bounds = 0
    for val in rating_rows["answer"]:
        try:
            num = float(val)
            if not num.is_integer() or num < RATING_MIN or num > RATING_MAX:
                rating_out_of_bounds += 1
        except (ValueError, TypeError):
            rating_non_numeric += 1

    if rating_non_numeric > 0:
        errors.append(
            f"Found {rating_non_numeric} 'rating' answer(s) with non-numeric values. "
            f"Rating questions require integers between {RATING_MIN} and {RATING_MAX}."
        )
    if rating_out_of_bounds > 0:
        errors.append(
            f"Found {rating_out_of_bounds} 'rating' answer(s) outside allowed bounds "
            f"[{RATING_MIN}, {RATING_MAX}]."
        )

    # 6b. NPS Bounds Check [0, 10]
    nps_rows = valid_answers_df[valid_answers_df["question_type"] == "nps"]
    nps_non_numeric = 0
    nps_out_of_bounds = 0
    for val in nps_rows["answer"]:
        try:
            num = float(val)
            if not num.is_integer() or num < NPS_MIN or num > NPS_MAX:
                nps_out_of_bounds += 1
        except (ValueError, TypeError):
            nps_non_numeric += 1

    if nps_non_numeric > 0:
        errors.append(
            f"Found {nps_non_numeric} 'nps' answer(s) with non-numeric values. "
            f"NPS questions require integers between {NPS_MIN} and {NPS_MAX}."
        )
    if nps_out_of_bounds > 0:
        errors.append(
            f"Found {nps_out_of_bounds} 'nps' answer(s) outside allowed bounds "
            f"[{NPS_MIN}, {NPS_MAX}]."
        )

    # 6c. Multi-Select JSON Array Check
    multi_rows = valid_answers_df[valid_answers_df["question_type"] == "multi_select"]
    malformed_multi = 0
    for val in multi_rows["answer"]:
        if isinstance(val, (list, tuple)):
            continue
        try:
            parsed = json.loads(str(val))
            if not isinstance(parsed, list):
                malformed_multi += 1
        except (json.JSONDecodeError, TypeError, ValueError):
            malformed_multi += 1

    if malformed_multi > 0:
        errors.append(
            f"Found {malformed_multi} 'multi_select' answer(s) that are not valid JSON arrays. "
            "Multi-select answers must be formatted as JSON array strings, e.g., '[\"A\", \"B\"]'."
        )

    # 7. Timestamp Parseability Check
    if "response_timestamp" in df.columns:
        ts_missing = df["response_timestamp"].apply(_is_missing_value).sum()
        if ts_missing > 0:
            warnings.append(
                f"Column 'response_timestamp' has {ts_missing} missing value(s). "
                "Time-series visualizations may exclude these rows."
            )
        # Check non-missing timestamps
        non_missing_ts = df["response_timestamp"][~df["response_timestamp"].apply(_is_missing_value)]
        if len(non_missing_ts) > 0:
            try:
                parsed_ts = pd.to_datetime(non_missing_ts, errors="coerce")
                malformed_ts_count = int(parsed_ts.isna().sum())
                if malformed_ts_count > 0:
                    errors.append(
                        f"Found {malformed_ts_count} malformed 'response_timestamp' value(s) "
                        "that could not be parsed as valid datetimes."
                    )
            except Exception as err:
                errors.append(f"Error parsing 'response_timestamp': {err}")

    is_valid = len(errors) == 0
    return ValidationResult(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
        summary=summary,
    )


def is_valid_survey_data(df: pd.DataFrame) -> bool:
    """Convenience boolean helper returning True if dataset passes all validation checks."""
    return validate_survey_data(df).is_valid
