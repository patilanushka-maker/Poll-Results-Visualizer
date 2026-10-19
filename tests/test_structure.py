"""Sanity tests verifying package structure and module importability."""

import importlib
import pytest


def test_package_import():
    """Verify that poll_visualizer package can be imported."""
    import poll_visualizer
    assert hasattr(poll_visualizer, "__version__")
    assert poll_visualizer.__version__ == "0.1.0"


@pytest.mark.parametrize(
    "module_name",
    [
        "data_loader",
        "validation",
        "cleaning",
        "metrics",
        "analysis",
        "visualizations",
        "insights",
        "reporting",
    ],
)
def test_submodules_import(module_name: str):
    """Verify that all core submodules can be imported without errors."""
    mod = importlib.import_module(f"poll_visualizer.{module_name}")
    assert mod is not None


def test_main_entrypoint_callable():
    """Verify that main.py defines the callable application entry point."""
    import main
    assert callable(main.main)

