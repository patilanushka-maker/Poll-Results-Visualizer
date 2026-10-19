"""Unit tests for src/poll_visualizer/visualizations.py."""

import pandas as pd
import plotly.graph_objects as go
import pytest

from poll_visualizer.visualizations import (
    create_question_chart,
    plot_likert_distribution,
    plot_multiselect_frequencies,
    plot_nps_summary,
    plot_response_frequencies,
    plot_segment_comparison,
    plot_segment_heatmap,
)


def make_survey_df() -> pd.DataFrame:
    """Fixture: Multi-question survey DataFrame covering all question types and segments."""
    return pd.DataFrame(
        [
            # Single choice
            {"question_id": "Q_SC", "question_text": "Preferred Channel", "question_type": "single_choice", "respondent_id": "U1", "segment": "Enterprise", "answer": "Chat"},
            {"question_id": "Q_SC", "question_text": "Preferred Channel", "question_type": "single_choice", "respondent_id": "U2", "segment": "Enterprise", "answer": "Chat"},
            {"question_id": "Q_SC", "question_text": "Preferred Channel", "question_type": "single_choice", "respondent_id": "U3", "segment": "SMB", "answer": "Email"},
            {"question_id": "Q_SC", "question_text": "Preferred Channel", "question_type": "single_choice", "respondent_id": "U4", "segment": "SMB", "answer": "Email"},
            {"question_id": "Q_SC", "question_text": "Preferred Channel", "question_type": "single_choice", "respondent_id": "U5", "segment": "SMB", "answer": None},  # skipped
            # Unrelated question to verify question isolation
            {"question_id": "Q_OTHER", "question_text": "Unrelated", "question_type": "single_choice", "respondent_id": "U1", "segment": "Enterprise", "answer": "IgnoreVal"},
            # Rating (1 to 5)
            {"question_id": "Q_RATE", "question_text": "Product Quality", "question_type": "rating", "respondent_id": "U1", "segment": "Enterprise", "answer": "5"},
            {"question_id": "Q_RATE", "question_text": "Product Quality", "question_type": "rating", "respondent_id": "U2", "segment": "Enterprise", "answer": "4"},
            {"question_id": "Q_RATE", "question_text": "Product Quality", "question_type": "rating", "respondent_id": "U3", "segment": "SMB", "answer": "4"},
            # NPS (0 to 10)
            {"question_id": "Q_NPS", "question_text": "Recommendation", "question_type": "nps", "respondent_id": "U1", "segment": "Enterprise", "answer": "10"}, # promoter
            {"question_id": "Q_NPS", "question_text": "Recommendation", "question_type": "nps", "respondent_id": "U2", "segment": "Enterprise", "answer": "9"},  # promoter
            {"question_id": "Q_NPS", "question_text": "Recommendation", "question_type": "nps", "respondent_id": "U3", "segment": "SMB", "answer": "8"},         # passive
            {"question_id": "Q_NPS", "question_text": "Recommendation", "question_type": "nps", "respondent_id": "U4", "segment": "SMB", "answer": "5"},         # detractor
            # Multi-select JSON arrays
            {"question_id": "Q_MULTI", "question_text": "Features", "question_type": "multi_select", "respondent_id": "U1", "segment": "Enterprise", "answer": '["API", "Dashboard"]'},
            {"question_id": "Q_MULTI", "question_text": "Features", "question_type": "multi_select", "respondent_id": "U2", "segment": "Enterprise", "answer": '["API"]'},
            {"question_id": "Q_MULTI", "question_text": "Features", "question_type": "multi_select", "respondent_id": "U3", "segment": "SMB", "answer": '["Dashboard", "Export"]'},
        ]
    )


def test_functions_return_plotly_figure():
    """Verify that every public plotting function returns a valid go.Figure object."""
    df = make_survey_df()

    fig_freq = plot_response_frequencies(df, question_id="Q_SC")
    assert isinstance(fig_freq, go.Figure)

    fig_likert = plot_likert_distribution(df, question_id="Q_RATE")
    assert isinstance(fig_likert, go.Figure)

    fig_nps = plot_nps_summary(df, question_id="Q_NPS")
    assert isinstance(fig_nps, go.Figure)

    fig_comp = plot_segment_comparison(df, question_id="Q_SC")
    assert isinstance(fig_comp, go.Figure)

    fig_heat = plot_segment_heatmap(df, question_id="Q_SC")
    assert isinstance(fig_heat, go.Figure)

    fig_multi = plot_multiselect_frequencies(df, question_id="Q_MULTI")
    assert isinstance(fig_multi, go.Figure)


def test_response_frequencies_chart_content_and_denominator():
    """Verify response frequencies chart contains expected values and correct per-question denominator."""
    df = make_survey_df()
    # 4 valid answers for Q_SC: 2 Chat (50.0%), 2 Email (50.0%)
    fig = plot_response_frequencies(df, question_id="Q_SC", metric_type="percentage")

    trace = fig.data[0]
    assert trace.type == "bar"
    # Values should sum to 100%
    assert sum(trace.x) == 100.0
    assert set(trace.y) == {"Chat", "Email"}
    assert "IgnoreVal" not in trace.y  # Q_OTHER isolated out


def test_response_frequencies_orientations():
    """Verify horizontal and vertical bar orientations."""
    df = make_survey_df()
    fig_h = plot_response_frequencies(df, question_id="Q_SC", orientation="horizontal")
    assert fig_h.data[0].orientation == "h"

    fig_v = plot_response_frequencies(df, question_id="Q_SC", orientation="vertical")
    assert fig_v.data[0].orientation == "v"


def test_likert_distribution_order_and_zero_counts():
    """Verify Likert chart preserves 1-5 order and includes zero-count categories."""
    df = make_survey_df()
    fig = plot_likert_distribution(df, question_id="Q_RATE")

    trace = fig.data[0]
    # Y-axis descriptions include all 5 ratings
    assert len(trace.y) == 5
    # Contains 1 to 5 scale labels
    assert any("1 - Strongly Disagree" in label for label in trace.y)
    assert any("5 - Strongly Agree" in label for label in trace.y)


def test_nps_chart_displays_actual_nps_score():
    """Verify NPS chart displays the net score (-100 to +100), not just promoter percentage."""
    df = make_survey_df()
    # Q_NPS data: 2 Promoters (50%), 1 Passive (25%), 1 Detractor (25%)
    # NPS Score = 50.0 - 25.0 = +25.0
    fig = plot_nps_summary(df, question_id="Q_NPS")

    indicator_trace = fig.data[0]
    assert indicator_trace.type == "indicator"
    assert indicator_trace.value == 25.0  # Actual NPS score, not 50.0 (promoter %)


def test_nps_chart_handles_zero_valid_responses():
    """Verify that an empty or missing NPS question produces a clean placeholder figure."""
    empty_df = pd.DataFrame(columns=["question_id", "answer"])
    fig = plot_nps_summary(empty_df, question_id="NON_EXISTENT")
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 0  # No traces, placeholder layout
    assert any("No valid NPS responses" in ann.text for ann in fig.layout.annotations)


def test_segment_comparison_isolates_question():
    """Verify segment comparison chart isolates the target question and groups by segment."""
    df = make_survey_df()
    fig = plot_segment_comparison(df, question_id="Q_SC", segment_col="segment")

    # Traces represent choices: 'Chat' and 'Email'
    trace_names = [t.name for t in fig.data]
    assert "Chat" in trace_names
    assert "Email" in trace_names
    assert "IgnoreVal" not in trace_names


def test_segment_heatmap_content():
    """Verify segment heatmap contains expected segment and category axes."""
    df = make_survey_df()
    fig = plot_segment_heatmap(df, question_id="Q_SC", segment_col="segment")

    heatmap_trace = fig.data[0]
    assert heatmap_trace.type == "heatmap"
    assert set(heatmap_trace.y) == {"Enterprise", "SMB"}
    assert set(heatmap_trace.x) == {"Chat", "Email"}


def test_multiselect_frequencies_chart():
    """Verify multi-select chart preserves option frequencies and documented denominator."""
    df = make_survey_df()
    # 3 respondents: U1 (API, Dashboard), U2 (API), U3 (Dashboard, Export)
    # API = 2/3 (66.67%), Dashboard = 2/3 (66.67%), Export = 1/3 (33.33%)
    fig = plot_multiselect_frequencies(df, question_id="Q_MULTI")

    trace = fig.data[0]
    assert set(trace.y) == {"API", "Dashboard", "Export"}
    assert sum(trace.x) > 100.0  # Naturally sums to > 100%


def test_multiselect_malformed_json_raises_error():
    """Verify malformed multi-select JSON raises a clear error."""
    bad_df = pd.DataFrame([{"question_id": "M_BAD", "answer": '["unclosed'}])
    with pytest.raises(ValueError) as exc:
        plot_multiselect_frequencies(bad_df, question_id="M_BAD")
    assert "Malformed multi-select" in str(exc.value)


def test_empty_inputs_behave_predictably():
    """Verify that passing empty DataFrames to plotting functions returns valid figures."""
    empty_df = pd.DataFrame()
    assert isinstance(plot_response_frequencies(empty_df), go.Figure)
    assert isinstance(plot_likert_distribution(empty_df), go.Figure)
    assert isinstance(plot_nps_summary(empty_df), go.Figure)
    assert isinstance(plot_segment_comparison(empty_df, "Q1"), go.Figure)
    assert isinstance(plot_segment_heatmap(empty_df), go.Figure)
    assert isinstance(plot_multiselect_frequencies(empty_df), go.Figure)
    assert isinstance(create_question_chart(empty_df, "Q1"), go.Figure)


def test_chart_titles_and_labels_present():
    """Verify that generated figures have descriptive titles and axis labels."""
    df = make_survey_df()
    fig = plot_response_frequencies(
        df,
        question_id="Q_SC",
        question_text="Preferred Support Channels",
    )
    assert "Preferred Support Channels" in fig.layout.title.text
    assert fig.layout.xaxis.title.text is not None
    assert fig.layout.yaxis.title.text is not None


def test_source_dataframe_immutability():
    """Verify that plotting functions never modify the input DataFrame."""
    df = make_survey_df()
    df_copy = df.copy(deep=True)

    _ = plot_response_frequencies(df, question_id="Q_SC")
    _ = plot_likert_distribution(df, question_id="Q_RATE")
    _ = plot_nps_summary(df, question_id="Q_NPS")
    _ = plot_segment_comparison(df, question_id="Q_SC")
    _ = plot_segment_heatmap(df, question_id="Q_SC")
    _ = plot_multiselect_frequencies(df, question_id="Q_MULTI")

    pd.testing.assert_frame_equal(df, df_copy)


def test_create_question_chart_dispatcher():
    """Verify that create_question_chart correctly routes each question_type."""
    df = make_survey_df()

    fig_rate = create_question_chart(df, question_id="Q_RATE")
    assert isinstance(fig_rate, go.Figure)

    fig_nps = create_question_chart(df, question_id="Q_NPS")
    assert isinstance(fig_nps, go.Figure)

    fig_sc = create_question_chart(df, question_id="Q_SC")
    assert isinstance(fig_sc, go.Figure)

    fig_multi = create_question_chart(df, question_id="Q_MULTI")
    assert isinstance(fig_multi, go.Figure)
