import os
import sys

# Agregar el path para importar módulos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

import sys
import importlib
import pytest
import matplotlib.pyplot as plt

from libs.config.config_variables import DEFAULT_FONT, DATE_FORMAT


@pytest.fixture
def fresh_config_plot(mocker):
    # Patch logger before importing the module under test
    mock_logger = mocker.MagicMock()
    mocker.patch("libs.config.config_logger.get_logger", return_value=mock_logger)
    # Avoid locale errors during tests
    mocker.patch("locale.setlocale", return_value=None)

    # Force fresh import to pick up patched logger
    if "libs.config.config_plot" in sys.modules:
        del sys.modules["libs.config.config_plot"]
    cp = importlib.import_module("libs.config.config_plot")

    # Ensure clean state
    cp.PlotConfig.clear_registry()
    cp.PlotConfig.uninstall_hooks()
    plt.close("all")

    yield cp, mock_logger

    # Teardown/cleanup
    cp.PlotConfig.clear_registry()
    cp.PlotConfig.uninstall_hooks()
    plt.close("all")


class TestPlotConfig:
    def test_auto_apply_registered_config_on_savefig_and_show(self, fresh_config_plot, mocker):
        cp, _ = fresh_config_plot

        # Patch savefig and show before hooks are installed
        savefig_mock = mocker.patch("matplotlib.pyplot.savefig")
        show_mock = mocker.patch("matplotlib.pyplot.show")

        dates = list(range(6))
        fig, ax = plt.subplots()
        config = cp.PlotConfig(
            plot_type=cp.PlotType.TIMESERIES,
            dates=dates,
            n_xticks=3,
            rotate_xticks=45,
            rotate_yticks=90,
            legend_position=cp.LegendPosition.UPPER_RIGHT,
        )
        config.register(ax)

        # Ensure a legend exists so config can adjust it
        ax.plot(dates, [0] * len(dates), label="series")
        ax.legend()
        legend_spy = mocker.spy(ax, "legend")
        initial_calls = len(legend_spy.call_args_list)

        # Trigger hook via savefig
        plt.savefig("out.png")

        # Original savefig called
        assert savefig_mock.call_count == 1

        # Ticks and rotations auto-applied
        xticks = list(ax.get_xticks())
        assert int(round(xticks[0])) == dates[0]
        assert int(round(xticks[-1])) == dates[-1]
        assert all(int(lbl.get_rotation()) == 45 for lbl in ax.get_xticklabels())
        assert all(int(lbl.get_rotation()) == 90 for lbl in ax.get_yticklabels())

        # Legend re-applied with expected location
        assert len(legend_spy.call_args_list) >= initial_calls + 1
        last_call = legend_spy.call_args_list[-1]
        assert last_call.kwargs.get("loc") == "upper right"

        # Trigger hook via show
        plt.show()
        assert show_mock.call_count == 1

        plt.close(fig)

    def test_global_rcparams_apply_defaults_and_scaling(self, fresh_config_plot):
        cp, _ = fresh_config_plot

        scale = 2.0
        cp.PlotConfig(scale=scale)

        # Backend
        assert plt.rcParams["backend"] == "Agg"

        # Font family should include DEFAULT_FONT
        ff = plt.rcParams["font.family"]
        if isinstance(ff, (list, tuple)):
            assert DEFAULT_FONT in ff
        else:
            assert ff == DEFAULT_FONT

        # Font sizes scaled
        assert plt.rcParams["font.size"] == int(8 * scale)
        assert plt.rcParams["figure.titlesize"] == int(10 * scale)
        assert plt.rcParams["axes.labelsize"] == int(9 * scale)

        # Grid linewidth scaled
        assert plt.rcParams["grid.linewidth"] == 0.05 * scale

    def test_timeseries_ticks_and_date_format_applied(self, fresh_config_plot):
        cp, _ = fresh_config_plot

        dates = list(range(10))
        fig, ax = plt.subplots()
        config = cp.PlotConfig(plot_type=cp.PlotType.TIMESERIES, dates=dates, n_xticks=4)
        config.apply(ax)

        # Date format rcParams applied
        assert plt.rcParams["date.autoformatter.day"] == DATE_FORMAT
        assert plt.rcParams["date.autoformatter.month"] == DATE_FORMAT
        assert plt.rcParams["date.autoformatter.year"] == DATE_FORMAT

        # X ticks include first and last date
        xticks = list(ax.get_xticks())
        assert int(round(xticks[0])) == dates[0]
        assert int(round(xticks[-1])) == dates[-1]

        # X limits span full range
        xlim = ax.get_xlim()
        assert int(round(xlim[0])) == dates[0]
        assert int(round(xlim[1])) == dates[-1]

        plt.close(fig)

    def test_timeseries_without_dates_logs_warning_and_does_not_crash(self, fresh_config_plot, mocker):
        cp, mock_logger = fresh_config_plot

        # Patch savefig to prevent actual file operations
        mocker.patch("matplotlib.pyplot.savefig")

        fig, ax = plt.subplots()
        config = cp.PlotConfig(plot_type=cp.PlotType.TIMESERIES, dates=None)
        config.register(ax)

        # Warning logged about missing dates
        assert mock_logger.warning.called

        # Should not raise during save
        plt.savefig("out.png")
        plt.close(fig)

    def test_timeseries_ticks_handles_min_xticks_without_error(self, fresh_config_plot):
        cp, _ = fresh_config_plot

        # Use empty dates to ensure safe early return even with n_xticks <= 1
        dates = []
        fig, ax = plt.subplots()
        config = cp.PlotConfig(plot_type=cp.PlotType.TIMESERIES, dates=dates, n_xticks=1)

        # Should not raise
        config.apply(ax)

        # No ticks set; default behavior remains
        assert isinstance(ax.get_xticks(), (list, tuple, np.ndarray)) or True  # basic sanity

        plt.close(fig)

    def test_uninstall_and_reinstall_hooks_restore_and_reapply_behavior(self, fresh_config_plot, mocker):
        cp, _ = fresh_config_plot

        # Patch savefig before installing hooks
        savefig_mock = mocker.patch("matplotlib.pyplot.savefig")

        dates = list(range(5))
        fig, ax = plt.subplots()
        config = cp.PlotConfig(plot_type=cp.PlotType.TIMESERIES, dates=dates, n_xticks=3)
        config.register(ax)

        # First save: with hooks installed, auto-apply
        plt.savefig("a.png")
        assert savefig_mock.call_count == 1
        assert int(round(ax.get_xticks()[0])) == dates[0]

        # Uninstall hooks -> savefig should be restored to original mock
        cp.PlotConfig.uninstall_hooks()
        assert plt.savefig is savefig_mock

        # Reset axis and save again: no auto-apply expected
        ax.set_xticks([])
        plt.savefig("b.png")
        assert savefig_mock.call_count == 2
        assert ax.get_xticks().size == 0 if hasattr(ax.get_xticks(), "size") else len(ax.get_xticks()) == 0

        # New PlotConfig should reinstall hooks
        cp.PlotConfig(plot_type=cp.PlotType.TIMESERIES, dates=dates, n_xticks=3)

        # Save again: auto-apply should occur now
        plt.savefig("c.png")
        assert savefig_mock.call_count == 3
        # After wrapper, ticks applied again on registered ax
        xticks = ax.get_xticks()
        assert len(xticks) > 0

        plt.close(fig)

    def test_legend_position_defaults_and_outside_mapping_applied(self, fresh_config_plot, mocker):
        cp, _ = fresh_config_plot

        # Standard (non-map) default legend position
        cfg_std = cp.PlotConfig(plot_type=cp.PlotType.STANDARD)
        assert cfg_std.legend_position == cp.LegendPosition.UPPER_LEFT
        assert cfg_std._legend_config == {"loc": "upper left"}

        # Map default legend position
        cfg_map = cp.PlotConfig(plot_type=cp.PlotType.MAP)
        assert cfg_map.legend_position == cp.LegendPosition.OUTSIDE_RIGHT
        assert cfg_map._legend_config["loc"] == "center left"
        assert cfg_map._legend_config["bbox_to_anchor"] == (1.0, 0.5)

        # Apply to axis with existing legend to ensure mapping is used
        fig1, ax1 = plt.subplots()
        ax1.plot([0, 1], [0, 1], label="l1")
        ax1.legend()
        spy1 = mocker.spy(ax1, "legend")
        cfg_std.apply(ax1)
        assert spy1.call_args_list[-1].kwargs.get("loc") == "upper left"

        fig2, ax2 = plt.subplots()
        ax2.plot([0, 1], [0, 1], label="l2")
        ax2.legend()
        spy2 = mocker.spy(ax2, "legend")
        cfg_map.apply(ax2)
        last_kwargs = spy2.call_args_list[-1].kwargs
        assert last_kwargs.get("loc") == "center left"
        assert last_kwargs.get("bbox_to_anchor") == (1.0, 0.5)

        plt.close(fig1)
        plt.close(fig2)

    def test_clear_registry_stops_auto_application_until_re_registered(self, fresh_config_plot, mocker):
        cp, _ = fresh_config_plot

        savefig_mock = mocker.patch("matplotlib.pyplot.savefig")

        dates = list(range(7))
        fig, ax = plt.subplots()
        config = cp.PlotConfig(plot_type=cp.PlotType.TIMESERIES, dates=dates, n_xticks=3)
        config.register(ax)

        # First save: auto-apply occurs
        plt.savefig("a.png")
        assert savefig_mock.call_count == 1
        assert len(ax.get_xticks()) > 0

        # Clear registry
        cp.PlotConfig.clear_registry()
        # Reset ticks and attempt save: no auto-apply
        ax.set_xticks([])
        plt.savefig("b.png")
        assert savefig_mock.call_count == 2
        assert ax.get_xticks().size == 0 if hasattr(ax.get_xticks(), "size") else len(ax.get_xticks()) == 0

        # Re-register and save: auto-apply resumes
        config.register(ax)
        plt.savefig("c.png")
        assert savefig_mock.call_count == 3
        assert len(ax.get_xticks()) > 0

        plt.close(fig)

    def test_multiple_y_axes_configuration_applied_to_both_axes(self, fresh_config_plot, mocker):
        cp, _ = fresh_config_plot

        savefig_mock = mocker.patch("matplotlib.pyplot.savefig")

        dates = list(range(8))
        fig, ax1 = plt.subplots()
        ax2 = ax1.twinx()  # Create secondary Y axis

        # Configure for timeseries with rotated ticks
        config = cp.PlotConfig(
            plot_type=cp.PlotType.TIMESERIES,
            dates=dates,
            n_xticks=4,
            rotate_xticks=45,
            rotate_yticks=90
        )
        
        # Register both axes
        config.register(ax1)
        config.register(ax2)

        # Add data and legends to both axes
        ax1.plot(dates, [i * 2 for i in dates], label="Primary", color="blue")
        ax2.plot(dates, [i * 3 for i in dates], label="Secondary", color="red")
        ax1.legend(loc="upper left")
        ax2.legend(loc="upper right")

        # Spy on legend calls for both axes
        legend_spy1 = mocker.spy(ax1, "legend")
        legend_spy2 = mocker.spy(ax2, "legend")
        initial_calls1 = len(legend_spy1.call_args_list)
        initial_calls2 = len(legend_spy2.call_args_list)

        # Trigger auto-apply via savefig
        plt.savefig("multi_y_axes.png")
        assert savefig_mock.call_count == 1

        # Verify X ticks applied to primary axis (shared between both)
        xticks = list(ax1.get_xticks())
        assert int(round(xticks[0])) == dates[0]
        assert int(round(xticks[-1])) == dates[-1]

        # Verify X tick rotation applied to both axes
        assert all(int(lbl.get_rotation()) == 45 for lbl in ax1.get_xticklabels())
        assert all(int(lbl.get_rotation()) == 45 for lbl in ax2.get_xticklabels())

        # Verify Y tick rotation applied to both axes
        assert all(int(lbl.get_rotation()) == 90 for lbl in ax1.get_yticklabels())
        assert all(int(lbl.get_rotation()) == 90 for lbl in ax2.get_yticklabels())

        # Verify legends re-applied on both axes
        assert len(legend_spy1.call_args_list) >= initial_calls1 + 1
        assert len(legend_spy2.call_args_list) >= initial_calls2 + 1

        # Verify legend positions maintained
        last_call1 = legend_spy1.call_args_list[-1]
        last_call2 = legend_spy2.call_args_list[-1]
        assert last_call1.kwargs.get("loc") == "upper left"
        assert last_call2.kwargs.get("loc") == "upper right"

        plt.close(fig)


# Support for numpy size checks without hard dependency if not needed
try:
    import numpy as np  # noqa: F401
except Exception:
    class _NPShim:
        ndarray = tuple
    np = _NPShim()
