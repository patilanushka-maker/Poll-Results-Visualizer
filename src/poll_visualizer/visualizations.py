"""Reusable Plotly visualizations module for Poll Results Visualizer.

Provides standalone, publication-quality Plotly figures for categorical
frequencies, Likert scale distributions, Net Promoter Scores (NPS),
demographic segment comparisons, multi-select questions, and heatmaps.

Note:
All visualization functions return `plotly.graph_objects.Figure` instances
and remain strictly decoupled from Streamlit or browser rendering engines.
"""

from typing import Any, Optional, Union
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from poll_visualizer.analysis import cross_tabulate_by_segment
from poll_visualizer.metrics import (
    calculate_likert_distribution,
    calculate_multiselect_frequencies,
    calculate_nps,
    calculate_response_frequencies,
)

# Standard accessible color tokens
PRIMARY_COLOR: str = "#2563EB"  # Royal blue
SECONDARY_COLOR: str = "#4F46E5"  # Indigo
ACCENT_COLOR: str = "#0EA5E9"  # Sky blue

# Categorical sequential palette
CATEGORICAL_PALETTE: list[str] = [
    "#2563EB",  # Blue
    "#10B981",  # Emerald
    "#F59E0B",  # Amber
    "#8B5CF6",  # Purple
    "#EC4899",  # Pink
    "#14B8A6",  # Teal
    "#F97316",  # Orange
    "#6366F1",  # Indigo
]

# Likert 5-point divergent scale colors (1: Strongly Disagree -> 5: Strongly Agree)
LIKERT_5_COLORS: dict[int, str] = {
    1: "#EF4444",  # Crimson / Strong negative
    2: "#F97316",  # Coral / Negative
    3: "#94A3B8",  # Slate / Neutral
    4: "#34D399",  # Mint / Positive
    5: "#059669",  # Emerald / Strong positive
}

# NPS Category Colors
NPS_COLORS: dict[str, str] = {
    "Detractors": "#EF4444",  # Red (0 to 6)
    "Passives": "#F59E0B",    # Amber (7 to 8)
    "Promoters": "#10B981",   # Green (9 to 10)
}

# Base layout styling applied to all figures
BASE_LAYOUT: dict[str, Any] = {
    "font": {"family": "Inter, Segoe UI, -apple-system, sans-serif", "size": 13, "color": "#1E293B"},
    "paper_bgcolor": "#FFFFFF",
    "plot_bgcolor": "#F8FAFC",
    "margin": {"l": 50, "r": 40, "t": 60, "b": 50},
    "hoverlabel": {
        "bgcolor": "#1E293B",
        "font": {"family": "Inter, sans-serif", "size": 12, "color": "#FFFFFF"},
    },
}


def _create_empty_figure(message: str = "No data available for display.") -> go.Figure:
    """Helper returning a clean placeholder figure when input data is empty."""
    fig = go.Figure()
    fig.update_layout(
        **BASE_LAYOUT,
        xaxis={"visible": False},
        yaxis={"visible": False},
        annotations=[
            {
                "text": message,
                "xref": "paper",
                "yref": "paper",
                "showarrow": False,
                "font": {"size": 14, "color": "#64748B"},
            }
        ],
    )
    return fig


def plot_response_frequencies(
    data: pd.DataFrame,
    question_id: Optional[str] = None,
    question_text: Optional[str] = None,
    orientation: str = "horizontal",
    metric_type: str = "percentage",
    color: Optional[str] = None,
) -> go.Figure:
    """Create a bar chart of response frequencies or percentages for a single question.

    Parameters
    ----------
    data : pd.DataFrame
        Either a pre-computed frequencies DataFrame (with 'answer' and 'percentage'/'count')
        or a raw survey dataset in long-format.
    question_id : str, optional
        Target question identifier when data is a raw survey DataFrame.
    question_text : str, optional
        Chart title text. If None, question_id or column name is used.
    orientation : str, optional
        'horizontal' ('h') or 'vertical' ('v'), default 'horizontal'.
    metric_type : str, optional
        'percentage' (default) or 'count'.
    color : str, optional
        Hex bar color, default PRIMARY_COLOR.

    Returns
    -------
    go.Figure
        Plotly Figure object.
    """
    if data is None or data.empty:
        return _create_empty_figure()

    # Determine whether data is already frequency aggregated
    if "answer" in data.columns and ("percentage" in data.columns or "count" in data.columns):
        freq_df = data.copy()
    else:
        freq_df = calculate_response_frequencies(data, question_id=question_id)

    if freq_df.empty:
        return _create_empty_figure("No valid responses found for this question.")

    is_horizontal = orientation.lower() in ("horizontal", "h")
    value_col = "percentage" if metric_type == "percentage" else "count"
    bar_color = color or PRIMARY_COLOR

    # Format text annotations on bars
    text_labels = [
        f"{val:.1f}%" if metric_type == "percentage" else f"{int(val):,}"
        for val in freq_df[value_col]
    ]

    fig = go.Figure()

    if is_horizontal:
        # For horizontal bars, invert y so the highest value sits at the top
        plot_df = freq_df.iloc[::-1]
        plot_labels = text_labels[::-1]

        fig.add_trace(
            go.Bar(
                x=plot_df[value_col],
                y=plot_df["answer"],
                orientation="h",
                text=plot_labels,
                textposition="auto",
                marker={"color": bar_color, "line": {"width": 0}},
                hovertemplate="<b>%{y}</b><br>"
                + ("Percentage: %{x:.1f}%" if metric_type == "percentage" else "Count: %{x:,}")
                + "<extra></extra>",
            )
        )
        fig.update_xaxes(
            title=f"Response {metric_type.capitalize()}"
            + (" (%)" if metric_type == "percentage" else ""),
            gridcolor="#E2E8F0",
        )
        fig.update_yaxes(title="Choice / Option", showgrid=False)
    else:
        fig.add_trace(
            go.Bar(
                x=freq_df["answer"],
                y=freq_df[value_col],
                orientation="v",
                text=text_labels,
                textposition="auto",
                marker={"color": bar_color, "line": {"width": 0}},
                hovertemplate="<b>%{x}</b><br>"
                + ("Percentage: %{y:.1f}%" if metric_type == "percentage" else "Count: %{y:,}")
                + "<extra></extra>",
            )
        )
        fig.update_xaxes(title="Choice / Option", showgrid=False)
        fig.update_yaxes(
            title=f"Response {metric_type.capitalize()}"
            + (" (%)" if metric_type == "percentage" else ""),
            gridcolor="#E2E8F0",
        )

    title_text = question_text or (f"Question: {question_id}" if question_id else "Response Frequencies")
    fig.update_layout(
        **BASE_LAYOUT,
        title={"text": f"<b>{title_text}</b>", "font": {"size": 15}},
        showlegend=False,
    )
    return fig


def plot_likert_distribution(
    data: pd.DataFrame,
    question_id: Optional[str] = None,
    question_text: Optional[str] = None,
    scale_min: int = 1,
    scale_max: int = 5,
) -> go.Figure:
    """Create an ordered distribution chart for a 5-point discrete Likert rating question.

    Guarantees:
    - Preserves logical rating order (1 to 5).
    - Explicitly displays zero-count categories.
    - Applies standardized divergent rating colors.

    Parameters
    ----------
    data : pd.DataFrame
        Survey dataset or precomputed Likert distribution table.
    question_id : str, optional
        Target rating question identifier.
    question_text : str, optional
        Chart title.
    scale_min : int, optional
        Minimum rating, default 1.
    scale_max : int, optional
        Maximum rating, default 5.

    Returns
    -------
    go.Figure
        Plotly Figure object.
    """
    if data is None or data.empty:
        return _create_empty_figure()

    if "rating" in data.columns and "percentage" in data.columns:
        likert_df = data.copy()
    else:
        likert_df = calculate_likert_distribution(
            data, question_id=question_id, scale_min=scale_min, scale_max=scale_max
        )

    if likert_df.empty:
        return _create_empty_figure("No rating data available.")

    # Sort strictly by rating step
    likert_df = likert_df.sort_values(by="rating", ascending=True).reset_index(drop=True)

    colors = [LIKERT_5_COLORS.get(int(r), "#64748B") for r in likert_df["rating"]]
    text_labels = [f"{pct:.1f}% ({int(cnt):,})" for pct, cnt in zip(likert_df["percentage"], likert_df["count"])]

    # Rating label descriptions
    scale_labels = {
        1: "1 - Strongly Disagree",
        2: "2 - Disagree",
        3: "3 - Neutral",
        4: "4 - Agree",
        5: "5 - Strongly Agree",
    }
    y_labels = [scale_labels.get(int(r), f"Rating {r}") for r in likert_df["rating"]]

    fig = go.Figure()
    # Invert order for top-to-bottom visual display
    fig.add_trace(
        go.Bar(
            y=y_labels[::-1],
            x=likert_df["percentage"][::-1],
            orientation="h",
            text=text_labels[::-1],
            textposition="auto",
            marker={"color": colors[::-1]},
            hovertemplate="<b>%{y}</b><br>Percentage: %{x:.1f}%<extra></extra>",
        )
    )

    title_text = question_text or (f"Likert Distribution: {question_id}" if question_id else "Likert Rating Distribution")
    fig.update_layout(
        **BASE_LAYOUT,
        title={"text": f"<b>{title_text}</b>", "font": {"size": 15}},
        xaxis={"title": "Percentage of Respondents (%)", "gridcolor": "#E2E8F0", "range": [0, max(likert_df['percentage'].max() * 1.15, 10)]},
        yaxis={"title": "Rating Score", "showgrid": False},
        showlegend=False,
    )
    return fig


def plot_nps_summary(
    nps_results: Union[dict[str, Any], pd.DataFrame],
    question_id: Optional[str] = None,
    question_text: Optional[str] = None,
) -> go.Figure:
    """Create a structured Net Promoter Score (NPS) indicator and breakdown chart.

    Displays:
    1. Overall Net Promoter Score on the -100 to +100 scale (distinguishing
       NPS score from raw promoter percentage).
    2. Detractor (0-6), Passive (7-8), and Promoter (9-10) breakdown percentages.

    Parameters
    ----------
    nps_results : Union[dict[str, Any], pd.DataFrame]
        Either a dictionary returned by `calculate_nps()` or a raw survey DataFrame.
    question_id : str, optional
        Target NPS question identifier (if passing a DataFrame).
    question_text : str, optional
        Chart title text.

    Returns
    -------
    go.Figure
        Plotly Figure object.
    """
    if isinstance(nps_results, pd.DataFrame):
        stats = calculate_nps(nps_results, question_id=question_id)
    elif isinstance(nps_results, dict):
        stats = nps_results
    else:
        return _create_empty_figure("Invalid NPS data format provided.")

    valid_count = stats.get("valid_count", 0)
    nps_score = stats.get("nps_score")

    if valid_count == 0 or nps_score is None:
        return _create_empty_figure("No valid NPS responses found to calculate score.")

    promoter_pct = stats.get("promoter_pct", 0.0)
    passive_pct = stats.get("passive_pct", 0.0)
    detractor_pct = stats.get("detractor_pct", 0.0)

    # 2-Row Subplot: Top = Indicator Gauge, Bottom = Category Breakdown Bars
    fig = make_subplots(
        rows=2,
        cols=1,
        row_heights=[0.55, 0.45],
        vertical_spacing=0.15,
        specs=[[{"type": "indicator"}], [{"type": "bar"}]],
    )

    # Top Trace: Gauge Indicator for NPS (-100 to +100)
    gauge_bar_color = "#10B981" if nps_score > 0 else ("#EF4444" if nps_score < 0 else "#64748B")
    fig.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=nps_score,
            number={"suffix": " NPS", "font": {"size": 28, "color": gauge_bar_color}},
            gauge={
                "axis": {"range": [-100, 100], "tickwidth": 1, "tickcolor": "#94A3B8"},
                "bar": {"color": gauge_bar_color, "thickness": 0.3},
                "bgcolor": "#F1F5F9",
                "borderwidth": 0,
                "steps": [
                    {"range": [-100, 0], "color": "#FEE2E2"},   # Detractor zone (subtle red)
                    {"range": [0, 50], "color": "#FEF3C7"},     # Passive / Moderate zone (subtle amber)
                    {"range": [50, 100], "color": "#D1FAE5"},   # High loyalty zone (subtle emerald)
                ],
                "threshold": {
                    "line": {"color": "#1E293B", "width": 3},
                    "thickness": 0.8,
                    "value": nps_score,
                },
            },
        ),
        row=1,
        col=1,
    )

    # Bottom Trace: Stacked Horizontal Category Breakdown
    categories = ["Detractors (0-6)", "Passives (7-8)", "Promoters (9-10)"]
    pcts = [detractor_pct, passive_pct, promoter_pct]
    counts = [
        stats.get("detractors_count", 0),
        stats.get("passives_count", 0),
        stats.get("promoters_count", 0),
    ]
    bar_colors = [NPS_COLORS["Detractors"], NPS_COLORS["Passives"], NPS_COLORS["Promoters"]]

    for cat, pct, cnt, c in zip(categories, pcts, counts, bar_colors):
        fig.add_trace(
            go.Bar(
                name=cat,
                y=["Audience Breakdown"],
                x=[pct],
                orientation="h",
                text=[f"<b>{pct:.1f}%</b> ({cnt:,})" if pct > 5 else ""],
                textposition="inside",
                marker={"color": c},
                hovertemplate=f"<b>{cat}</b><br>Percentage: {pct:.1f}%<br>Count: {cnt:,}<extra></extra>",
            ),
            row=2,
            col=1,
        )

    title_text = question_text or (f"Net Promoter Score: {question_id}" if question_id else "Net Promoter Score (NPS)")
    fig.update_layout(
        **BASE_LAYOUT,
        title={"text": f"<b>{title_text}</b>", "font": {"size": 15}},
        barmode="stack",
        height=450,
        legend={"orientation": "h", "yanchor": "bottom", "y": -0.25, "xanchor": "center", "x": 0.5},
    )
    fig.update_xaxes(title="Category Share (%)", range=[0, 100], showgrid=True, gridcolor="#E2E8F0", row=2, col=1)
    fig.update_yaxes(visible=False, row=2, col=1)
    return fig


def plot_segment_comparison(
    df: pd.DataFrame,
    question_id: str,
    segment_col: str = "segment",
    question_text: Optional[str] = None,
    barmode: str = "group",
    normalize: str = "index",
) -> go.Figure:
    """Create a grouped or stacked bar chart comparing a question across demographic segments.

    Parameters
    ----------
    df : pd.DataFrame
        Survey dataset in long-format.
    question_id : str
        Target question identifier to isolate.
    segment_col : str, optional
        Demographic segment column, default 'segment'.
    question_text : str, optional
        Chart title text.
    barmode : str, optional
        'group' (default) or 'stack'.
    normalize : str, optional
        'index' (row percentages summing to 100% per segment) or False/None for raw counts.

    Returns
    -------
    go.Figure
        Plotly Figure object.
    """
    if df is None or df.empty:
        return _create_empty_figure()

    ctab = cross_tabulate_by_segment(
        df,
        question_id=question_id,
        segment_col=segment_col,
        normalize=normalize,
    )

    if ctab.empty:
        return _create_empty_figure("No segment comparison data available.")

    fig = go.Figure()
    for idx, answer_choice in enumerate(ctab.columns):
        col_color = CATEGORICAL_PALETTE[idx % len(CATEGORICAL_PALETTE)]
        values = ctab[answer_choice]

        text_labels = [
            f"{v:.1f}%" if normalize == "index" else f"{int(v):,}"
            for v in values
        ]

        fig.add_trace(
            go.Bar(
                name=str(answer_choice),
                x=list(ctab.index),
                y=values,
                text=text_labels,
                textposition="auto",
                marker={"color": col_color},
                hovertemplate=f"<b>Segment: %{{x}}</b><br>Choice: {answer_choice}<br>"
                + ("Share: %{y:.1f}%" if normalize == "index" else "Count: %{y:,}")
                + "<extra></extra>",
            )
        )

    title_text = question_text or f"Segment Comparison: {question_id}"
    y_title = "Response Share within Segment (%)" if normalize == "index" else "Response Count"

    fig.update_layout(
        **BASE_LAYOUT,
        title={"text": f"<b>{title_text}</b>", "font": {"size": 15}},
        barmode=barmode,
        xaxis={"title": segment_col.capitalize(), "showgrid": False},
        yaxis={"title": y_title, "gridcolor": "#E2E8F0"},
        legend={"title": {"text": "Choice"}, "orientation": "h", "yanchor": "bottom", "y": -0.3, "xanchor": "center", "x": 0.5},
    )
    return fig


def plot_segment_heatmap(
    data: pd.DataFrame,
    question_id: Optional[str] = None,
    segment_col: str = "segment",
    normalize: str = "index",
    question_text: Optional[str] = None,
) -> go.Figure:
    """Create a demographic cross-tabulation heatmap.

    Parameters
    ----------
    data : pd.DataFrame
        Either a precomputed contingency DataFrame or raw survey DataFrame.
    question_id : str, optional
        Target question identifier (required if data is raw survey DataFrame).
    segment_col : str, optional
        Segment column name, default 'segment'.
    normalize : str, optional
        Normalization mode: 'index' (row percentages) or False for raw counts.
    question_text : str, optional
        Chart title text.

    Returns
    -------
    go.Figure
        Plotly Figure object.
    """
    if data is None or data.empty:
        return _create_empty_figure()

    if question_id is not None:
        ctab = cross_tabulate_by_segment(
            data,
            question_id=question_id,
            segment_col=segment_col,
            normalize=normalize,
        )
    else:
        ctab = data.copy()

    if ctab.empty:
        return _create_empty_figure("No cross-tabulation data available for heatmap.")

    z_values = ctab.values
    x_labels = [str(c) for c in ctab.columns]
    y_labels = [str(r) for r in ctab.index]

    # Cell text annotations
    text_annotations = [
        [f"{v:.1f}%" if normalize == "index" else f"{int(v):,}" for v in row]
        for row in z_values
    ]

    fig = go.Figure(
        data=go.Heatmap(
            z=z_values,
            x=x_labels,
            y=y_labels,
            text=text_annotations,
            texttemplate="%{text}",
            colorscale="Blues",
            colorbar={"title": "%" if normalize == "index" else "Count"},
            hovertemplate="<b>Segment:</b> %{y}<br><b>Option:</b> %{x}<br><b>Value:</b> %{text}<extra></extra>",
        )
    )

    title_text = question_text or (f"Cross-Tabulation Heatmap: {question_id}" if question_id else "Segment Cross-Tabulation Heatmap")
    fig.update_layout(
        **BASE_LAYOUT,
        title={"text": f"<b>{title_text}</b>", "font": {"size": 15}},
        xaxis={"title": "Response Option", "showgrid": False},
        yaxis={"title": segment_col.capitalize(), "showgrid": False},
    )
    return fig


def plot_multiselect_frequencies(
    data: pd.DataFrame,
    question_id: Optional[str] = None,
    question_text: Optional[str] = None,
    color: Optional[str] = None,
) -> go.Figure:
    """Create a frequency bar chart for multi-select JSON array questions.

    Explicitly annotates that percentages represent the proportion of unique
    respondents choosing each option, and explains why total percentages may
    sum to more than 100%.

    Parameters
    ----------
    data : pd.DataFrame
        Raw survey DataFrame or pre-computed multi-select frequency DataFrame.
    question_id : str, optional
        Target multi-select question identifier.
    question_text : str, optional
        Chart title text.
    color : str, optional
        Bar color, default SECONDARY_COLOR.

    Returns
    -------
    go.Figure
        Plotly Figure object.
    """
    if data is None or data.empty:
        return _create_empty_figure()

    if "option" in data.columns and "percentage" in data.columns:
        multi_df = data.copy()
    else:
        multi_df = calculate_multiselect_frequencies(data, question_id=question_id)

    if multi_df.empty:
        return _create_empty_figure("No multi-select data available.")

    plot_df = multi_df.iloc[::-1]  # Highest at top
    bar_color = color or SECONDARY_COLOR

    text_labels = [f"{pct:.1f}% ({int(cnt):,})" for pct, cnt in zip(plot_df["percentage"], plot_df["count"])]

    fig = go.Figure(
        go.Bar(
            x=plot_df["percentage"],
            y=plot_df["option"],
            orientation="h",
            text=text_labels,
            textposition="auto",
            marker={"color": bar_color},
            hovertemplate="<b>%{y}</b><br>Selected by: %{x:.1f}% of respondents<extra></extra>",
        )
    )

    title_text = question_text or (f"Multi-Select Selections: {question_id}" if question_id else "Multi-Select Frequency Distribution")
    fig.update_layout(
        **BASE_LAYOUT,
        title={
            "text": f"<b>{title_text}</b><br><span style='font-size: 11px; color: #64748B;'>% of respondents selecting option; percentages may sum to > 100%</span>",
            "font": {"size": 15},
        },
        xaxis={"title": "Percentage of Respondents Selecting Option (%)", "gridcolor": "#E2E8F0"},
        yaxis={"title": "Option", "showgrid": False},
        showlegend=False,
    )
    return fig


def create_question_chart(
    df: pd.DataFrame,
    question_id: str,
    **kwargs: Any,
) -> go.Figure:
    """Convenience dispatcher selecting the appropriate chart type by question_type.

    Parameters
    ----------
    df : pd.DataFrame
        Survey dataset in long-format.
    question_id : str
        Target question identifier.
    **kwargs : Any
        Keyword arguments forwarded to the specific plotting function.

    Returns
    -------
    go.Figure
        Plotly Figure object.
    """
    if df is None or df.empty:
        return _create_empty_figure()

    q_df = df[df["question_id"] == question_id]
    if q_df.empty:
        return _create_empty_figure(f"Question '{question_id}' not found in dataset.")

    q_type = str(q_df["question_type"].iloc[0]).strip().lower()
    q_text = str(q_df["question_text"].iloc[0])

    if q_type == "rating":
        return plot_likert_distribution(df, question_id=question_id, question_text=q_text, **kwargs)
    elif q_type == "nps":
        return plot_nps_summary(df, question_id=question_id, question_text=q_text, **kwargs)
    elif q_type == "single_choice":
        return plot_response_frequencies(df, question_id=question_id, question_text=q_text, **kwargs)
    elif q_type == "multi_select":
        return plot_multiselect_frequencies(df, question_id=question_id, question_text=q_text, **kwargs)
    elif q_type == "text":
        valid_texts = q_df[~q_df["answer"].isna()]["answer"].tolist()
        return _create_empty_figure(
            f"Open Text Question: {len(valid_texts):,} responses recorded.<br>"
            "Open-ended text responses are summarized in the analysis view."
        )
    else:
        return plot_response_frequencies(df, question_id=question_id, question_text=q_text, **kwargs)
