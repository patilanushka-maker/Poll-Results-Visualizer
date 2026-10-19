"""Automated narrative insights engine for Poll Results Visualizer.

Provides rule-based, deterministic narrative generation for categorical questions,
Likert ratings, Net Promoter Scores (NPS), multi-select choices, and demographic
segment comparisons. All findings are evidence-based, transparently bounded,
and strictly decoupled from unsupported causal claims.
"""

from dataclasses import dataclass, field
from typing import Any, Optional
import numpy as np
import pandas as pd

from poll_visualizer.analysis import (
    cross_tabulate_by_segment,
    group_nps_summary,
    group_rating_summary,
)
from poll_visualizer.metrics import (
    _filter_question,
    _is_missing_value,
    calculate_likert_distribution,
    calculate_multiselect_frequencies,
    calculate_nps,
    calculate_rating_metrics,
    calculate_response_frequencies,
)

# Project-defined NPS interpretation tiers (adapted from standard descriptive guidelines; norms vary by industry)
NPS_TIERS: list[tuple[float, str]] = [
    (50.0, "Excellent / High Loyalty"),
    (10.0, "Healthy / Favorable"),
    (-10.0, "Neutral / Mixed Sentiment"),
    (-50.0, "Needs Attention / Low Sentiment"),
    (-100.0, "Critical / High Dissatisfaction"),
]


@dataclass
class QuestionInsight:
    """Structured report returned by the narrative insight generation engine.

    Attributes
    ----------
    question_id : str
        Target question identifier.
    question_text : str
        Full question prompt text.
    question_type : str
        Functional question type (e.g. 'single_choice', 'rating', 'nps', 'multi_select', 'text').
    summary : str
        High-level executive narrative summary.
    key_findings : list[str]
        Specific bulleted data findings and descriptive observations.
    warnings : list[str]
        Notices regarding missing data, ties, small sample sizes, or quality hygiene.
    metrics : dict[str, Any]
        Raw numeric metrics preserved separately for independent dashboard rendering.
    data_quality_notes : list[str]
        Sample completeness, response rate notes, and missingness tallies.
    """

    question_id: str
    question_text: str
    question_type: str
    summary: str
    key_findings: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    data_quality_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert the insight report to a serializable dictionary."""
        return {
            "question_id": self.question_id,
            "question_text": self.question_text,
            "question_type": self.question_type,
            "summary": self.summary,
            "key_findings": list(self.key_findings),
            "warnings": list(self.warnings),
            "metrics": dict(self.metrics),
            "data_quality_notes": list(self.data_quality_notes),
        }


def _get_nps_tier_label(score: float) -> str:
    """Classify an NPS score into project-defined interpretive sentiment tiers."""
    for threshold, label in NPS_TIERS:
        if score >= threshold:
            return label
    return "Critical / High Dissatisfaction"


def generate_categorical_insights(
    df: pd.DataFrame,
    question_id: str,
) -> QuestionInsight:
    """Generate deterministic narrative insights for a single-choice categorical question.

    Identifies the plurality/majority leader, response counts, percentage shares,
    handles ties deterministically, and documents per-question denominators.

    Parameters
    ----------
    df : pd.DataFrame
        Survey dataset in long-format.
    question_id : str
        Target question identifier.

    Returns
    -------
    QuestionInsight
        Structured insight report.
    """
    sub_df = _filter_question(df, question_id)
    if sub_df.empty:
        raise KeyError(f"Question ID '{question_id}' not found in dataset.")

    q_text = str(sub_df["question_text"].iloc[0])
    q_type = str(sub_df["question_type"].iloc[0]).strip().lower()

    missing_mask = sub_df["answer"].apply(_is_missing_value)
    total_records = len(sub_df)
    missing_count = int(missing_mask.sum())
    valid_count = total_records - missing_count

    data_quality = [
        f"Total question records: {total_records:,}",
        f"Valid responses: {valid_count:,} ({round((valid_count / total_records) * 100, 1) if total_records > 0 else 0}%)",
    ]
    if missing_count > 0:
        data_quality.append(f"Omitted/unanswered: {missing_count:,} responses")

    if valid_count == 0:
        return QuestionInsight(
            question_id=question_id,
            question_text=q_text,
            question_type=q_type,
            summary="No valid responses were recorded for this question.",
            key_findings=[],
            warnings=["No valid answered records available."],
            metrics={"valid_count": 0, "missing_count": missing_count},
            data_quality_notes=data_quality,
        )

    freq_df = calculate_response_frequencies(sub_df, question_id=None)
    max_count = freq_df["count"].max()
    top_rows = freq_df[freq_df["count"] == max_count]

    key_findings = []
    warnings = []

    # Check for ties
    if len(top_rows) > 1:
        tied_answers = sorted(top_rows["answer"].tolist())
        tied_pct = top_rows["percentage"].iloc[0]
        tied_str = ", ".join(f"'{ans}'" for ans in tied_answers)
        summary = (
            f"Response plurality is tied between {tied_str}, each receiving "
            f"{max_count:,} responses ({tied_pct:.1f}% of valid answers)."
        )
        key_findings.append(f"Exact tie observed across {len(top_rows)} options: {tied_str}.")
        warnings.append("A response tie was observed; no single dominant answer emerged.")
    else:
        leader = str(top_rows["answer"].iloc[0])
        leader_pct = float(top_rows["percentage"].iloc[0])
        is_majority = leader_pct > 50.0

        summary = (
            f"'{leader}' is the most frequent choice, selected by {leader_pct:.1f}% of respondents "
            f"({max_count:,} of {valid_count:,} valid answers)."
        )
        status_label = "majority (> 50%)" if is_majority else "plurality (< 50%)"
        key_findings.append(f"Leading choice: '{leader}' holds a {status_label} with {leader_pct:.1f}% share.")

        if len(freq_df) > 1:
            second_row = freq_df.iloc[1]
            second_ans = str(second_row["answer"])
            second_pct = float(second_row["percentage"])
            margin = round(leader_pct - second_pct, 1)
            key_findings.append(
                f"Runner-up: '{second_ans}' holds {second_pct:.1f}% share (lead margin: +{margin:.1f}%)."
            )

    # Document distribution breakdown
    breakdown_items = [f"{row['answer']} ({row['percentage']:.1f}%)" for _, row in freq_df.iterrows()]
    key_findings.append(f"Full distribution: {'; '.join(breakdown_items)}.")

    metrics_dict: dict[str, Any] = {
        "valid_count": valid_count,
        "missing_count": missing_count,
        "leader": top_rows["answer"].iloc[0] if len(top_rows) == 1 else "Tie",
        "leader_percentage": float(top_rows["percentage"].iloc[0]),
        "leader_count": int(max_count),
        "options_count": len(freq_df),
        "distribution": freq_df.to_dict(orient="records"),
    }

    return QuestionInsight(
        question_id=question_id,
        question_text=q_text,
        question_type=q_type,
        summary=summary,
        key_findings=key_findings,
        warnings=warnings,
        metrics=metrics_dict,
        data_quality_notes=data_quality,
    )


def generate_rating_insights(
    df: pd.DataFrame,
    question_id: str,
    scale_min: int = 1,
    scale_max: int = 5,
) -> QuestionInsight:
    """Generate narrative insights for discrete Likert rating questions.

    Summarizes mean, median, sample standard deviation, modal score,
    positive (top-box: 4-5) vs negative (bottom-box: 1-2) sentiment proportions.

    Parameters
    ----------
    df : pd.DataFrame
        Survey dataset in long-format.
    question_id : str
        Target rating question identifier.
    scale_min : int, optional
        Minimum rating bound, default 1.
    scale_max : int, optional
        Maximum rating bound, default 5.

    Returns
    -------
    QuestionInsight
        Structured insight report.
    """
    sub_df = _filter_question(df, question_id)
    if sub_df.empty:
        raise KeyError(f"Question ID '{question_id}' not found in dataset.")

    q_text = str(sub_df["question_text"].iloc[0])
    q_type = str(sub_df["question_type"].iloc[0]).strip().lower()

    stats = calculate_rating_metrics(sub_df, question_id=None, scale_min=scale_min, scale_max=scale_max)
    valid_count = stats["valid_count"]
    missing_count = stats["missing_count"]
    total_records = len(sub_df)

    data_quality = [
        f"Total question records: {total_records:,}",
        f"Valid ratings: {valid_count:,} ({round((valid_count / total_records) * 100, 1) if total_records > 0 else 0}%)",
    ]
    if missing_count > 0:
        data_quality.append(f"Omitted/unanswered: {missing_count:,} ratings")

    if valid_count == 0:
        return QuestionInsight(
            question_id=question_id,
            question_text=q_text,
            question_type=q_type,
            summary="No valid ratings were recorded for this question.",
            key_findings=[],
            warnings=["No valid answered records available."],
            metrics=stats,
            data_quality_notes=data_quality,
        )

    likert_df = calculate_likert_distribution(sub_df, question_id=None, scale_min=scale_min, scale_max=scale_max)
    mean_val = stats["mean"]
    median_val = stats["median"]
    std_val = stats["std"]

    # Top-box (4, 5) and Bottom-box (1, 2)
    top_box_count = int(likert_df[likert_df["rating"].isin([4, 5])]["count"].sum())
    top_box_pct = round((top_box_count / valid_count) * 100.0, 1)

    bottom_box_count = int(likert_df[likert_df["rating"].isin([1, 2])]["count"].sum())
    bottom_box_pct = round((bottom_box_count / valid_count) * 100.0, 1)

    neutral_count = int(likert_df[likert_df["rating"] == 3]["count"].sum())
    neutral_pct = round((neutral_count / valid_count) * 100.0, 1)

    # Most frequent rating
    max_rating_cnt = likert_df["count"].max()
    modal_ratings = likert_df[likert_df["count"] == max_rating_cnt]["rating"].tolist()

    key_findings = [
        f"Mean rating: {mean_val:.2f} out of {scale_max} (median: {median_val:.1f}, sample std: {std_val:.2f})."
        if std_val is not None
        else f"Mean rating: {mean_val:.2f} out of {scale_max} (median: {median_val:.1f}).",
        f"Favorable (ratings 4-5): {top_box_pct:.1f}% ({top_box_count:,} respondents).",
        f"Unfavorable (ratings 1-2): {bottom_box_pct:.1f}% ({bottom_box_count:,} respondents).",
        f"Neutral (rating 3): {neutral_pct:.1f}% ({neutral_count:,} respondents).",
    ]

    warnings = []
    if len(modal_ratings) == 1:
        mode_val = modal_ratings[0]
        key_findings.append(f"Modal rating: {mode_val} was the single most common score.")
    else:
        warnings.append(f"Multiple modal ratings observed: {modal_ratings}.")

    summary = (
        f"Average rating is {mean_val:.2f} / {scale_max} (median {median_val:.1f}), with "
        f"{top_box_pct:.1f}% favorable responses (ratings 4-5) and {bottom_box_pct:.1f}% unfavorable."
    )

    stats["top_box_pct"] = top_box_pct
    stats["bottom_box_pct"] = bottom_box_pct
    stats["neutral_pct"] = neutral_pct
    stats["modal_ratings"] = modal_ratings
    stats["likert_distribution"] = likert_df.to_dict(orient="records")

    return QuestionInsight(
        question_id=question_id,
        question_text=q_text,
        question_type=q_type,
        summary=summary,
        key_findings=key_findings,
        warnings=warnings,
        metrics=stats,
        data_quality_notes=data_quality,
    )


def generate_nps_insights(
    df: pd.DataFrame,
    question_id: str,
) -> QuestionInsight:
    """Generate narrative insights for Net Promoter Score (NPS) questions.

    Explicitly reports the Net Promoter Score on the -100 to +100 scale,
    details Promoter, Passive, and Detractor percentages, and classifies
    the score into documented industry sentiment tiers.

    Parameters
    ----------
    df : pd.DataFrame
        Survey dataset in long-format.
    question_id : str
        Target NPS question identifier.

    Returns
    -------
    QuestionInsight
        Structured insight report.
    """
    sub_df = _filter_question(df, question_id)
    if sub_df.empty:
        raise KeyError(f"Question ID '{question_id}' not found in dataset.")

    q_text = str(sub_df["question_text"].iloc[0])
    q_type = str(sub_df["question_type"].iloc[0]).strip().lower()

    nps_stats = calculate_nps(sub_df, question_id=None)
    valid_count = nps_stats["valid_count"]
    missing_count = nps_stats["missing_count"]
    total_records = len(sub_df)

    data_quality = [
        f"Total question records: {total_records:,}",
        f"Valid NPS responses: {valid_count:,} ({round((valid_count / total_records) * 100, 1) if total_records > 0 else 0}%)",
    ]
    if missing_count > 0:
        data_quality.append(f"Omitted/unanswered: {missing_count:,} responses")

    if valid_count == 0 or nps_stats["nps_score"] is None:
        return QuestionInsight(
            question_id=question_id,
            question_text=q_text,
            question_type=q_type,
            summary="No valid NPS responses were recorded for this question.",
            key_findings=[],
            warnings=["No valid answered records available."],
            metrics=nps_stats,
            data_quality_notes=data_quality,
        )

    score = float(nps_stats["nps_score"])
    promoter_pct = float(nps_stats["promoter_pct"])
    passive_pct = float(nps_stats["passive_pct"])
    detractor_pct = float(nps_stats["detractor_pct"])

    promoter_cnt = int(nps_stats["promoters_count"])
    passive_cnt = int(nps_stats["passives_count"])
    detractor_cnt = int(nps_stats["detractors_count"])

    tier_label = _get_nps_tier_label(score)
    sign_str = "+" if score > 0 else ""

    summary = (
        f"Net Promoter Score is {sign_str}{score:.1f} ({tier_label}), comprising "
        f"{promoter_pct:.1f}% Promoters, {passive_pct:.1f}% Passives, and {detractor_pct:.1f}% Detractors."
    )

    key_findings = [
        f"Net Promoter Score: {sign_str}{score:.1f} (scale: -100 to +100).",
        f"Sentiment classification: {tier_label} (based on project-defined interpretive thresholds; industry norms vary).",
        f"Promoters (scores 9-10): {promoter_pct:.1f}% ({promoter_cnt:,} respondents).",
        f"Passives (scores 7-8): {passive_pct:.1f}% ({passive_cnt:,} respondents).",
        f"Detractors (scores 0-6): {detractor_pct:.1f}% ({detractor_cnt:,} respondents).",
    ]

    warnings = []
    if detractor_pct > promoter_pct:
        warnings.append(
            f"Detractors ({detractor_pct:.1f}%) exceed Promoters ({promoter_pct:.1f}%), yielding a negative net score."
        )

    nps_stats["tier_label"] = tier_label
    return QuestionInsight(
        question_id=question_id,
        question_text=q_text,
        question_type=q_type,
        summary=summary,
        key_findings=key_findings,
        warnings=warnings,
        metrics=nps_stats,
        data_quality_notes=data_quality,
    )


def generate_multiselect_insights(
    df: pd.DataFrame,
    question_id: str,
) -> QuestionInsight:
    """Generate narrative insights for multi-select JSON array questions.

    Identifies top selected options, reports selection counts, and explicitly
    documents why option percentages reflect unique respondent proportions
    and may sum to greater than 100%.

    Parameters
    ----------
    df : pd.DataFrame
        Survey dataset in long-format.
    question_id : str
        Target multi-select question identifier.

    Returns
    -------
    QuestionInsight
        Structured insight report.
    """
    sub_df = _filter_question(df, question_id)
    if sub_df.empty:
        raise KeyError(f"Question ID '{question_id}' not found in dataset.")

    q_text = str(sub_df["question_text"].iloc[0])
    q_type = str(sub_df["question_type"].iloc[0]).strip().lower()

    missing_mask = sub_df["answer"].apply(_is_missing_value)
    total_records = len(sub_df)
    missing_count = int(missing_mask.sum())
    valid_count = total_records - missing_count

    data_quality = [
        f"Total question records: {total_records:,}",
        f"Valid respondents: {valid_count:,} ({round((valid_count / total_records) * 100, 1) if total_records > 0 else 0}%)",
    ]
    if missing_count > 0:
        data_quality.append(f"Omitted/unanswered: {missing_count:,} responses")

    if valid_count == 0:
        return QuestionInsight(
            question_id=question_id,
            question_text=q_text,
            question_type=q_type,
            summary="No valid multi-select responses were recorded for this question.",
            key_findings=[],
            warnings=["No valid answered records available."],
            metrics={"valid_count": 0, "missing_count": missing_count},
            data_quality_notes=data_quality,
        )

    multi_df = calculate_multiselect_frequencies(sub_df, question_id=None)

    if multi_df.empty:
        return QuestionInsight(
            question_id=question_id,
            question_text=q_text,
            question_type=q_type,
            summary="No options were selected by respondents in this multi-select question.",
            key_findings=[],
            warnings=["All answered records contained empty option selections."],
            metrics={"valid_count": valid_count, "missing_count": missing_count},
            data_quality_notes=data_quality,
        )

    top_option = str(multi_df["option"].iloc[0])
    top_pct = float(multi_df["percentage"].iloc[0])
    top_cnt = int(multi_df["count"].iloc[0])
    total_pct_sum = round(float(multi_df["percentage"].sum()), 1)

    summary = (
        f"'{top_option}' is the most commonly selected option, chosen by {top_pct:.1f}% of respondents "
        f"({top_cnt:,} of {valid_count:,} answering respondents)."
    )

    key_findings = [
        f"Top choice: '{top_option}' lead with {top_pct:.1f}% respondent selection rate.",
        f"Option percentages sum to {total_pct_sum:.1f}% (exceeds 100% because respondents may select multiple options).",
    ]

    for _, row in multi_df.head(5).iterrows():
        key_findings.append(f"• {row['option']}: {row['percentage']:.1f}% ({int(row['count']):,} respondents)")

    warnings = [
        "Denominator note: Percentages represent proportion of respondents who answered this question, not proportion of total selections."
    ]

    metrics_dict: dict[str, Any] = {
        "valid_respondents": valid_count,
        "missing_respondents": missing_count,
        "top_option": top_option,
        "top_percentage": top_pct,
        "top_count": top_cnt,
        "percentage_sum": total_pct_sum,
        "option_frequencies": multi_df.to_dict(orient="records"),
    }

    return QuestionInsight(
        question_id=question_id,
        question_text=q_text,
        question_type=q_type,
        summary=summary,
        key_findings=key_findings,
        warnings=warnings,
        metrics=metrics_dict,
        data_quality_notes=data_quality,
    )


def generate_segment_insights(
    df: pd.DataFrame,
    question_id: str,
    segment_col: str = "segment",
) -> dict[str, Any]:
    """Generate comparative demographic segment insights for a question.

    Identifies highest and lowest segment values, reports cohort sizes,
    and handles missing segment values explicitly without making unsupported
    causal or inferential claims.

    Parameters
    ----------
    df : pd.DataFrame
        Survey dataset in long-format.
    question_id : str
        Target question identifier.
    segment_col : str, optional
        Demographic segment column name, default 'segment'.

    Returns
    -------
    dict[str, Any]
        Dictionary with keys:
        ['question_id', 'segment_col', 'summary', 'key_findings', 'warnings', 'group_data']
    """
    sub_df = _filter_question(df, question_id)
    if sub_df.empty:
        raise KeyError(f"Question ID '{question_id}' not found in dataset.")

    if segment_col not in sub_df.columns:
        return {
            "question_id": question_id,
            "segment_col": segment_col,
            "summary": f"Segment column '{segment_col}' is not present in dataset.",
            "key_findings": [],
            "warnings": [f"Column '{segment_col}' not found."],
            "group_data": {},
        }

    q_type = str(sub_df["question_type"].iloc[0]).strip().lower()
    key_findings = []
    warnings = []
    group_data: dict[str, Any] = {}

    if q_type == "rating":
        group_df = group_rating_summary(sub_df, question_id=None, group_col=segment_col)
        # Filter groups with valid count > 0
        active_groups = group_df[group_df["valid_count"] > 0]
        if active_groups.empty:
            return {
                "question_id": question_id,
                "segment_col": segment_col,
                "summary": "No valid ratings available across demographic segments.",
                "key_findings": [],
                "warnings": ["No valid data."],
                "group_data": {},
            }

        highest_group = active_groups["mean"].idxmax()
        highest_mean = float(active_groups.loc[highest_group, "mean"])
        lowest_group = active_groups["mean"].idxmin()
        lowest_mean = float(active_groups.loc[lowest_group, "mean"])

        summary = (
            f"Across {len(active_groups)} demographic segments, '{highest_group}' reported the highest "
            f"average rating ({highest_mean:.2f}), while '{lowest_group}' reported the lowest ({lowest_mean:.2f})."
        )
        key_findings.append(f"Highest segment: '{highest_group}' with mean rating of {highest_mean:.2f}.")
        key_findings.append(f"Lowest segment: '{lowest_group}' with mean rating of {lowest_mean:.2f}.")
        group_data = group_df.to_dict(orient="index")

    elif q_type == "nps":
        group_df = group_nps_summary(sub_df, question_id=None, group_col=segment_col)
        active_groups = group_df[group_df["valid_count"] > 0]
        if active_groups.empty:
            return {
                "question_id": question_id,
                "segment_col": segment_col,
                "summary": "No valid NPS responses across demographic segments.",
                "key_findings": [],
                "warnings": ["No valid data."],
                "group_data": {},
            }

        highest_group = active_groups["nps_score"].idxmax()
        highest_nps = float(active_groups.loc[highest_group, "nps_score"])
        lowest_group = active_groups["nps_score"].idxmin()
        lowest_nps = float(active_groups.loc[lowest_group, "nps_score"])

        sign_h = "+" if highest_nps > 0 else ""
        sign_l = "+" if lowest_nps > 0 else ""
        summary = (
            f"Across {len(active_groups)} demographic segments, '{highest_group}' recorded the highest "
            f"NPS ({sign_h}{highest_nps:.1f}), while '{lowest_group}' recorded the lowest ({sign_l}{lowest_nps:.1f})."
        )
        key_findings.append(f"Top NPS segment: '{highest_group}' at {sign_h}{highest_nps:.1f}.")
        key_findings.append(f"Lowest NPS segment: '{lowest_group}' at {sign_l}{lowest_nps:.1f}.")
        group_data = group_df.to_dict(orient="index")

    else:
        # Categorical cross-tabulation
        ctab = cross_tabulate_by_segment(sub_df, question_id=None, segment_col=segment_col, normalize="index")
        if ctab.empty:
            return {
                "question_id": question_id,
                "segment_col": segment_col,
                "summary": "No valid categorical data available across demographic segments.",
                "key_findings": [],
                "warnings": ["No valid data."],
                "group_data": {},
            }

        summary = f"Categorical breakdown evaluated across {len(ctab)} demographic segment cohorts."
        for seg in ctab.index:
            top_choice = ctab.loc[seg].idxmax()
            top_val = ctab.loc[seg, top_choice]
            key_findings.append(f"Segment '{seg}': plurality choice is '{top_choice}' ({top_val:.1f}% of cohort).")
        group_data = ctab.to_dict(orient="index")

    warnings.append(
        "Observation policy: Observed group differences reflect descriptive sample comparisons; "
        "they do not assert statistical significance or causal relationships."
    )

    return {
        "question_id": question_id,
        "segment_col": segment_col,
        "summary": summary,
        "key_findings": key_findings,
        "warnings": warnings,
        "group_data": group_data,
    }


def generate_question_insights(
    df: pd.DataFrame,
    question_id: str,
    segment_col: Optional[str] = "segment",
) -> QuestionInsight:
    """Universal dispatcher generating structured narrative insights for any question.

    Routes dynamically by question_type, ensuring metric separation and data hygiene.

    Parameters
    ----------
    df : pd.DataFrame
        Survey dataset in long-format.
    question_id : str
        Target question identifier.
    segment_col : str, optional
        Segment column for supplementary demographic comparisons, default 'segment'.

    Returns
    -------
    QuestionInsight
        Structured insight report.
    """
    sub_df = _filter_question(df, question_id)
    if sub_df.empty:
        raise KeyError(f"Question ID '{question_id}' not found in dataset.")

    q_type = str(sub_df["question_type"].iloc[0]).strip().lower()

    if q_type == "rating":
        insight = generate_rating_insights(df, question_id)
    elif q_type == "nps":
        insight = generate_nps_insights(df, question_id)
    elif q_type == "single_choice":
        insight = generate_categorical_insights(df, question_id)
    elif q_type == "multi_select":
        insight = generate_multiselect_insights(df, question_id)
    elif q_type == "text":
        valid_texts = sub_df[~sub_df["answer"].apply(_is_missing_value)]["answer"].tolist()
        total_records = len(sub_df)
        missing_count = total_records - len(valid_texts)

        data_quality = [
            f"Total question records: {total_records:,}",
            f"Valid responses: {len(valid_texts):,} ({round((len(valid_texts)/total_records)*100, 1) if total_records > 0 else 0}%)",
        ]
        if missing_count > 0:
            data_quality.append(f"Omitted/unanswered: {missing_count:,} responses")

        summary = f"Open-ended text question with {len(valid_texts):,} submitted comments."
        findings = [f"Recorded {len(valid_texts):,} text submissions ({missing_count:,} omitted)."]
        if valid_texts:
            findings.append(f"Sample response: \"{valid_texts[0]}\"")

        insight = QuestionInsight(
            question_id=question_id,
            question_text=str(sub_df["question_text"].iloc[0]),
            question_type="text",
            summary=summary,
            key_findings=findings,
            warnings=["Unstructured text answers require qualitative coding or sentiment analysis."],
            metrics={"valid_count": len(valid_texts), "missing_count": missing_count},
            data_quality_notes=data_quality,
        )
    else:
        insight = generate_categorical_insights(df, question_id)

    # Attach supplementary segment insight if segment_col is available
    if segment_col and segment_col in df.columns:
        seg_res = generate_segment_insights(df, question_id, segment_col=segment_col)
        if seg_res.get("summary") and "not found" not in seg_res["summary"].lower():
            insight.metrics["segment_summary"] = seg_res["summary"]
            insight.metrics["segment_findings"] = seg_res["key_findings"]

    return insight
