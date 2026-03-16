import os
import csv
import numpy as np
import pytest
import matplotlib

matplotlib.use("Agg")  # non-interactive backend for CI

from psPlotKit.data_plotter.fig_generator import (
    FigureGenerator,
    PlotOptions,
    PlotOptionsManager,
)
from psPlotKit.data_manager.ps_data import PsData
from psPlotKit.data_plotter.plot_data_storage import (
    LineDataStorage,
    ErrorBarDataStorage,
    MapDataStorage,
    BarDataStorage,
    BoxDataStorage,
)

__author__ = "Alexander V. Dudchenko "

test_dir = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(test_dir, "test_fig_output")


def _read_csv(path):
    with open(path, "r", newline="") as f:
        return list(csv.reader(f))


@pytest.fixture(autouse=True)
def _clean_output():
    os.makedirs(output_dir, exist_ok=True)
    yield
    for fname in os.listdir(output_dir):
        os.remove(os.path.join(output_dir, fname))
    os.rmdir(output_dir)


# ---------------------------------------------------------------------------
# Line plot — storage auto-created
# ---------------------------------------------------------------------------


class TestLinePlotStorage:
    def test_line_plot_auto_creates_storage(self):
        fig = FigureGenerator(save_data=True)
        fig.init_figure()

        x1 = np.array([1.0, 2.0, 3.0])
        y1 = np.array([10.0, 20.0, 30.0])
        x2 = np.array([1.5, 2.5])
        y2 = np.array([15.0, 25.0])

        fig.plot_line(x1, y1, label="Series A")
        fig.plot_line(x2, y2, label="Series B")
        fig.set_axis(xlabel="Pressure (bar)", ylabel="Flow (L/h)")
        path = os.path.join(output_dir, "line_fig_2_datasets")
        fig.data_storage.save(path)
        assert isinstance(fig.data_storage, LineDataStorage)
        assert "Series A" in fig.data_storage._data
        assert "Series B" in fig.data_storage._data
        np.testing.assert_array_equal(fig.data_storage._data["Series A"]["x"], x1)
        np.testing.assert_array_equal(fig.data_storage._data["Series B"]["y"], y2)
        assert fig.data_storage.xlabel == "Pressure (bar)"
        assert fig.data_storage.ylabel == "Flow (L/h)"
        fig.close()

    def test_line_plot_saves_csv(self):
        fig = FigureGenerator(save_data=True)
        fig.init_figure()

        fig.plot_line([1, 2, 3], [4, 5, 6], label="L1")
        fig.set_axis(xlabel="x", ylabel="y")

        path = os.path.join(output_dir, "line_fig")
        fig.data_storage.save(path)

        rows = _read_csv(path + ".csv")
        assert rows[0] == ["L1", ""]
        assert rows[1] == ["x", "y"]
        assert len(rows) == 5  # 2 headers + 3 data rows
        assert float(rows[2][0]) == 1.0
        assert float(rows[2][1]) == 4.0
        fig.close()

    def test_line_storage_always_created(self):
        """FigureGenerator with save_data=False should still create storage for internal use."""
        fig = FigureGenerator()
        fig.init_figure()
        fig.plot_line([1, 2], [3, 4], label="test")
        assert fig.data_storage is not None
        assert isinstance(fig.data_storage, LineDataStorage)
        fig.close()

    def test_external_storage_still_works(self):
        """Users can still provide their own storage if desired."""
        storage = LineDataStorage()
        fig = FigureGenerator(save_data=True)
        fig.data_storage = storage
        fig.init_figure()
        fig.plot_line([1, 2], [3, 4], label="ext")
        # Should use the externally provided storage, not create a new one
        assert fig.data_storage is storage
        assert "ext" in storage._data
        fig.close()


# ---------------------------------------------------------------------------
# Scatter plot (auto-creates LineDataStorage)
# ---------------------------------------------------------------------------


class TestScatterPlotStorage:
    def test_scatter_auto_creates_storage(self):
        fig = FigureGenerator(save_data=True)
        fig.init_figure()

        x = np.array([1.0, 2.0, 3.0])
        y = np.array([10.0, 20.0, 30.0])
        fig.plot_scatter(xdata=x, ydata=y, label="Scatter1")

        assert isinstance(fig.data_storage, LineDataStorage)
        assert "Scatter1" in fig.data_storage._data
        np.testing.assert_array_equal(fig.data_storage._data["Scatter1"]["x"], x)
        fig.close()


# ---------------------------------------------------------------------------
# Error bar plot
# ---------------------------------------------------------------------------


class TestErrorBarPlotStorage:
    def test_errorbar_auto_creates_storage(self):
        fig = FigureGenerator(save_data=True)
        fig.init_figure()

        x = np.array([1.0, 2.0, 3.0])
        y = np.array([10.0, 20.0, 30.0])
        yerr = np.array([0.5, 0.3, 0.4])

        fig.plot_errorbar(xdata=x, ydata=y, yerr=yerr, label="E1")

        assert isinstance(fig.data_storage, ErrorBarDataStorage)
        assert "E1" in fig.data_storage._data
        np.testing.assert_array_equal(fig.data_storage._data["E1"]["y"], y)
        np.testing.assert_array_equal(fig.data_storage._data["E1"]["yerr"], yerr)
        fig.close()

    def test_errorbar_with_xerr(self):
        fig = FigureGenerator(save_data=True)
        fig.init_figure()

        x = np.array([1.0, 2.0])
        y = np.array([5.0, 6.0])
        xerr = np.array([0.1, 0.2])
        yerr = np.array([0.3, 0.4])

        fig.plot_errorbar(xdata=x, ydata=y, xerr=xerr, yerr=yerr, label="E2")

        entry = fig.data_storage._data["E2"]
        assert "xerr" in entry
        assert "yerr" in entry
        fig.close()

    def test_errorbar_saves_csv(self):
        fig = FigureGenerator(save_data=True)
        fig.init_figure()

        fig.plot_errorbar(xdata=[1, 2], ydata=[3, 4], yerr=[0.1, 0.2], label="E1")
        fig.set_axis(xlabel="x_label", ylabel="y_label")

        path = os.path.join(output_dir, "err_fig")
        fig.data_storage.save(path)

        rows = _read_csv(path + ".csv")
        assert rows[0] == ["E1", "", ""]
        assert "y error" in rows[1]
        assert len(rows) == 4  # 2 headers + 2 data rows
        fig.close()


# ---------------------------------------------------------------------------
# Bar plot
# ---------------------------------------------------------------------------


class TestBarPlotStorage:
    def test_bar_auto_creates_storage(self):
        fig = FigureGenerator(save_data=True)
        fig.init_figure()

        fig.plot_bar(0, 20, bottom=-10, label="Bar A")
        fig.plot_bar(1, 40, bottom=-25, label="Bar B")

        assert isinstance(fig.data_storage, BarDataStorage)
        assert "Bar A" in fig.data_storage._data
        assert fig.data_storage._data["Bar A"]["lower"] == -10
        assert fig.data_storage._data["Bar A"]["upper"] == 10  # -10 + 20
        assert fig.data_storage._data["Bar B"]["lower"] == -25
        assert fig.data_storage._data["Bar B"]["upper"] == 15  # -25 + 40
        fig.close()

    def test_bar_no_bottom(self):
        fig = FigureGenerator(save_data=True)
        fig.init_figure()

        fig.plot_bar(0, 15, label="Bar C")

        assert fig.data_storage._data["Bar C"]["lower"] == 0
        assert fig.data_storage._data["Bar C"]["upper"] == 15
        fig.close()

    def test_bar_saves_csv(self):
        fig = FigureGenerator(save_data=True)
        fig.init_figure()

        fig.plot_bar(0, 20, bottom=-10, label="B1")
        fig.set_axis_ticklabels(xlabel="Category", ylabel="Cost")

        path = os.path.join(output_dir, "bar_fig")
        fig.data_storage.save(path)

        rows = _read_csv(path + ".csv")
        assert rows[0][0] == "label"
        assert rows[1][0] == "B1"
        fig.close()


# ---------------------------------------------------------------------------
# Box plot
# ---------------------------------------------------------------------------


class TestBoxPlotStorage:
    def test_box_auto_creates_storage(self):
        fig = FigureGenerator(save_data=True)
        fig.init_figure()

        data = np.random.normal(50, 10, 200)
        fig.plot_box(0, data, whiskers=[5, 95], save_label="Box A")

        assert isinstance(fig.data_storage, BoxDataStorage)
        assert "Box A" in fig.data_storage._data
        pcts = fig.data_storage._data["Box A"]["percentiles"]
        assert len(pcts) == 5
        # Median should be near 50 for normal(50,10)
        assert 30 < pcts[2] < 70
        fig.close()

    def test_box_uses_label_when_no_save_label(self):
        fig = FigureGenerator(save_data=True)
        fig.init_figure()

        data = [10, 20, 30, 40, 50]
        fig.plot_box(0, data, label="BoxL")

        assert "BoxL" in fig.data_storage._data
        fig.close()

    def test_box_saves_csv(self):
        fig = FigureGenerator(save_data=True)
        fig.init_figure()

        fig.plot_box(0, list(range(101)), whiskers=[5, 95], save_label="B1")
        fig.set_axis_ticklabels(ylabel="Recovery (%)")

        path = os.path.join(output_dir, "box_fig")
        fig.data_storage.save(path)

        rows = _read_csv(path + ".csv")
        assert "5th percentile" in rows[0][1]
        pcts = [float(v) for v in rows[1][1:]]
        assert pcts[0] == pytest.approx(5.0)
        assert pcts[2] == pytest.approx(50.0)
        fig.close()


# ---------------------------------------------------------------------------
# Map plot
# ---------------------------------------------------------------------------


class TestMapPlotStorage:
    def test_map_auto_creates_storage(self):
        fig = FigureGenerator(save_data=True)
        fig.init_figure()

        x = np.array([1, 2, 3, 1, 2, 3, 1, 2, 3], dtype=float)
        y = np.array([10, 10, 10, 20, 20, 20, 30, 30, 30], dtype=float)
        z = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9], dtype=float)

        fig.plot_map(xdata=x, ydata=y, zdata=z, text=False)

        assert isinstance(fig.data_storage, MapDataStorage)
        assert "x" in fig.data_storage._data
        assert "y" in fig.data_storage._data
        assert "z" in fig.data_storage._data
        assert fig.data_storage._data["z"].shape == (3, 3)
        fig.close()

    def test_map_saves_csv(self):
        fig = FigureGenerator(save_data=True)
        fig.init_figure()

        x = np.array([1, 2, 1, 2], dtype=float)
        y = np.array([10, 10, 20, 20], dtype=float)
        z = np.array([100, 200, 300, 400], dtype=float)

        fig.plot_map(xdata=x, ydata=y, zdata=z, text=False)
        fig.set_axis_ticklabels(
            xticklabels=[1.0, 2.0],
            yticklabels=[10.0, 20.0],
            xlabel="X",
            ylabel="Y",
        )
        fig.data_storage.update_labels(zlabel="Cost")

        path = os.path.join(output_dir, "map_fig")
        fig.data_storage.save(path)

        rows = _read_csv(path + ".csv")
        assert "first column: Y" in rows[0][0]
        assert "first row: X" in rows[0][0]
        assert "data: Cost" in rows[0][0]
        assert rows[1][0] == ""
        assert len(rows) == 4  # label desc + header + 2 y-rows
        fig.close()


# ---------------------------------------------------------------------------
# Label propagation
# ---------------------------------------------------------------------------


class TestLabelPropagation:
    def test_set_axis_propagates_labels(self):
        fig = FigureGenerator(save_data=True)
        fig.init_figure()

        fig.plot_line([1, 2], [3, 4], label="L")
        fig.set_axis(xlabel="X Label", ylabel="Y Label")

        assert fig.data_storage.xlabel == "X Label"
        assert fig.data_storage.ylabel == "Y Label"
        fig.close()

    def test_set_axis_ticklabels_propagates_labels(self):
        fig = FigureGenerator(save_data=True)
        fig.init_figure()

        fig.plot_line([1, 2], [3, 4], label="L")
        fig.set_axis_ticklabels(xlabel="Tick X", ylabel="Tick Y")

        assert fig.data_storage.xlabel == "Tick X"
        assert fig.data_storage.ylabel == "Tick Y"
        fig.close()


# ---------------------------------------------------------------------------
# Mixed: no storage set (backwards compat)
# ---------------------------------------------------------------------------


class TestNoStorageBackwardsCompat:
    def test_all_plots_create_storage_without_save(self):
        """All plot methods should create storage even when save_data=False (default)."""
        fig = FigureGenerator()
        fig.init_figure()

        fig.plot_line([1, 2], [3, 4], label="L1")
        fig.plot_scatter(xdata=[1, 2], ydata=[3, 4], label="S1")
        fig.plot_errorbar(xdata=[1, 2], ydata=[3, 4], yerr=[0.1, 0.2], label="E1")
        fig.plot_bar(0, 10, bottom=-5, label="B1")

        assert fig.data_storage is not None
        fig.close()

    def test_box_plot_creates_storage_without_save(self):
        fig = FigureGenerator()
        fig.init_figure()
        fig.plot_box(0, [1, 2, 3, 4, 5], save_label="Box1")
        assert fig.data_storage is not None
        assert isinstance(fig.data_storage, BoxDataStorage)
        fig.close()


# ---------------------------------------------------------------------------
# PsData unwrapping — plotting methods accept PsData objects
# ---------------------------------------------------------------------------


def _make_psdata(data_array, key="test_key"):
    """Helper to create a minimal PsData instance for testing."""
    return PsData(
        data_key=key,
        data_type="test",
        data_array=np.array(data_array, dtype=float),
    )


class TestPsDataUnwrap:
    """Verify that every plotting method transparently unwraps PsData objects."""

    def test_unwrap_psdata_returns_data(self):
        ps = _make_psdata([1, 2, 3])
        result = FigureGenerator._unwrap_psdata(ps)
        np.testing.assert_array_equal(result, np.array([1.0, 2.0, 3.0]))

    def test_unwrap_psdata_passthrough(self):
        raw = np.array([4.0, 5.0])
        assert FigureGenerator._unwrap_psdata(raw) is raw

    def test_unwrap_psdata_none(self):
        assert FigureGenerator._unwrap_psdata(None) is None


# ---------------------------------------------------------------------------
# PlotOptionsManager
# ---------------------------------------------------------------------------


class TestPlotOptionsManager:
    def test_add_returns_plot_options(self):
        pom = PlotOptionsManager()
        opt = pom.add("Series A")
        assert isinstance(opt, PlotOptions)
        assert opt.label == "Series A"

    def test_dict_access_by_label(self):
        pom = PlotOptionsManager()
        pom.add("Series A")
        assert pom["Series A"].label == "Series A"

    def test_items_iteration(self):
        pom = PlotOptionsManager()
        pom.add("A")
        pom.add("B")
        labels = [label for label, _ in pom.items()]
        assert labels == ["A", "B"]

    def test_auto_index_increments(self):
        pom = PlotOptionsManager()
        pom.add("A")
        pom.add("B")
        pom.add("C")
        assert pom["A"].option_index == 0
        assert pom["B"].option_index == 1
        assert pom["C"].option_index == 2

    def test_auto_color_assigned(self):
        pom = PlotOptionsManager()
        pom.add("A")
        pom.add("B")
        assert pom["A"].color == PlotOptions.get_color(0)
        assert pom["B"].color == PlotOptions.get_color(1)

    def test_explicit_color_preserved(self):
        pom = PlotOptionsManager()
        pom.add("A", color="red")
        assert pom["A"].color == "red"

    def test_explicit_index_preserved(self):
        pom = PlotOptionsManager()
        pom.add("A", option_index=5)
        assert pom["A"].option_index == 5

    def test_explicit_index_drives_color(self):
        pom = PlotOptionsManager()
        pom.add("A", option_index=3)
        assert pom["A"].color == PlotOptions.get_color(3)

    def test_kwargs_forwarded(self):
        pom = PlotOptionsManager()
        pom.add("A", marker="s", lw=3, ls="--", zorder=10)
        opt = pom["A"]
        assert opt.marker == "s"
        assert opt.lw == 3
        assert opt.ls == "--"
        assert opt.zorder == 10

    def test_len(self):
        pom = PlotOptionsManager()
        assert len(pom) == 0
        pom.add("A")
        pom.add("B")
        assert len(pom) == 2

    def test_color_wraps_around(self):
        pom = PlotOptionsManager()
        n = len(PlotOptions._default_colors)
        for i in range(n + 2):
            pom.add(f"S{i}")
        assert pom[f"S{n}"].color == PlotOptions.get_color(0)
        assert pom[f"S{n+1}"].color == PlotOptions.get_color(1)

    def test_contains(self):
        pom = PlotOptionsManager()
        pom.add("A")
        assert "A" in pom
        assert "B" not in pom

    def test_keys_values(self):
        pom = PlotOptionsManager()
        pom.add("X")
        pom.add("Y")
        assert list(pom.keys()) == ["X", "Y"]
        assert all(isinstance(v, PlotOptions) for v in pom.values())

    def test_register_from_list(self):
        pom = PlotOptionsManager()
        pom.register(["A", "B", "C"])
        assert len(pom) == 3
        assert list(pom.keys()) == ["A", "B", "C"]
        assert pom["A"].option_index == 0
        assert pom["B"].option_index == 1
        assert pom["C"].option_index == 2
        assert pom["A"].color == PlotOptions.get_color(0)

    def test_register_from_dict(self):
        pom = PlotOptionsManager()
        pom.register(
            {
                "RO": {"marker": "s", "lw": 2},
                "UF": {"ls": "--"},
                "NF": {},
            }
        )
        assert len(pom) == 3
        assert pom["RO"].marker == "s"
        assert pom["RO"].lw == 2
        assert pom["UF"].ls == "--"
        assert pom["NF"].option_index == 2

    def test_register_dict_with_explicit_color(self):
        pom = PlotOptionsManager()
        pom.register(
            {
                "A": {"color": "red"},
                "B": {},
            }
        )
        assert pom["A"].color == "red"
        assert pom["B"].color == PlotOptions.get_color(1)

    def test_register_appends_to_existing(self):
        pom = PlotOptionsManager()
        pom.add("X")
        pom.register(["Y", "Z"])
        assert len(pom) == 3
        assert pom["Y"].option_index == 1
        assert pom["Z"].option_index == 2

    def test_unpack_plot_options(self):
        opt = PlotOptions("Series A", color="red", marker="s", lw=3)
        d = {**opt}
        assert d["label"] == "Series A"
        assert d["color"] == "red"
        assert d["marker"] == "s"
        assert d["lw"] == 3
        assert d["option_index"] == 0
        assert "save_label" in d

    def test_unpack_into_function(self):
        opt = PlotOptions("B", color="blue", zorder=10)

        def check(**kwargs):
            return kwargs

        result = check(**opt)
        assert result["label"] == "B"
        assert result["color"] == "blue"
        assert result["zorder"] == 10

    def test_plot_line_with_psdata(self):
        fig = FigureGenerator(save_data=True)
        fig.init_figure()

        x = _make_psdata([1, 2, 3])
        y = _make_psdata([10, 20, 30])
        fig.plot_line(x, y, label="ps_line")

        assert isinstance(fig.data_storage, LineDataStorage)
        np.testing.assert_array_equal(fig.data_storage._data["ps_line"]["x"], x.data)
        np.testing.assert_array_equal(fig.data_storage._data["ps_line"]["y"], y.data)
        fig.close()

    def test_plot_scatter_with_psdata(self):
        fig = FigureGenerator(save_data=True)
        fig.init_figure()

        x = _make_psdata([1, 2, 3])
        y = _make_psdata([4, 5, 6])
        fig.plot_scatter(xdata=x, ydata=y, label="ps_scatter")

        assert "ps_scatter" in fig.data_storage._data
        np.testing.assert_array_equal(fig.data_storage._data["ps_scatter"]["x"], x.data)
        fig.close()

    def test_plot_scatter_with_zdata_psdata(self):
        fig = FigureGenerator(save_data=True)
        fig.init_figure()

        x = _make_psdata([1, 2, 3])
        y = _make_psdata([4, 5, 6])
        z = _make_psdata([7, 8, 9])
        fig.plot_scatter(xdata=x, ydata=y, zdata=z, label="ps_scatter_z")

        assert "ps_scatter_z" in fig.data_storage._data
        fig.close()

    def test_plot_errorbar_with_psdata(self):
        fig = FigureGenerator(save_data=True)
        fig.init_figure()

        x = _make_psdata([1, 2, 3])
        y = _make_psdata([10, 20, 30])
        yerr = _make_psdata([0.5, 0.3, 0.4])
        fig.plot_errorbar(xdata=x, ydata=y, yerr=yerr, label="ps_err")

        assert isinstance(fig.data_storage, ErrorBarDataStorage)
        np.testing.assert_array_equal(fig.data_storage._data["ps_err"]["y"], y.data)
        np.testing.assert_array_equal(
            fig.data_storage._data["ps_err"]["yerr"], yerr.data
        )
        fig.close()

    def test_plot_bar_with_psdata(self):
        fig = FigureGenerator(save_data=True)
        fig.init_figure()

        val = _make_psdata([20])
        bottom = _make_psdata([-10])
        fig.plot_bar(0, val.data[0], bottom=bottom.data[0], label="ps_bar")

        assert isinstance(fig.data_storage, BarDataStorage)
        assert "ps_bar" in fig.data_storage._data
        fig.close()

    def test_plot_box_with_psdata(self):
        fig = FigureGenerator(save_data=True)
        fig.init_figure()

        data = _make_psdata(list(range(100)))
        fig.plot_box(0, data, whiskers=[5, 95], save_label="ps_box")

        assert isinstance(fig.data_storage, BoxDataStorage)
        assert "ps_box" in fig.data_storage._data
        pcts = fig.data_storage._data["ps_box"]["percentiles"]
        assert len(pcts) == 5
        fig.close()

    def test_plot_area_with_psdata(self):
        fig = FigureGenerator()
        fig.init_figure()

        x = _make_psdata([1, 2, 3])
        y = _make_psdata([0, 1, 0])
        y2 = _make_psdata([1, 2, 1])
        # Should not raise
        fig.plot_area(xdata=x, ydata=y, y2data=y2, label="ps_area")
        fig.close()

    def test_plot_cdf_with_psdata(self):
        fig = FigureGenerator()
        fig.init_figure()

        data = _make_psdata(np.random.normal(0, 1, 200))
        bins, cdf = fig.plot_cdf(data, label="ps_cdf")
        assert len(bins) > 0
        assert cdf[-1] == pytest.approx(1.0)
        fig.close()

    def test_plot_hist_with_psdata(self):
        fig = FigureGenerator()
        fig.init_figure()

        data = _make_psdata(np.random.normal(0, 1, 200))
        # Should not raise
        fig.plot_hist(data, label="ps_hist")
        fig.close()

    def test_plot_map_with_psdata(self):
        fig = FigureGenerator(save_data=True)
        fig.init_figure()

        x = _make_psdata([1, 2, 3, 1, 2, 3, 1, 2, 3])
        y = _make_psdata([10, 10, 10, 20, 20, 20, 30, 30, 30])
        z = _make_psdata([1, 2, 3, 4, 5, 6, 7, 8, 9])

        fig.plot_map(xdata=x, ydata=y, zdata=z, text=False)

        assert isinstance(fig.data_storage, MapDataStorage)
        assert fig.data_storage._data["z"].shape == (3, 3)
        fig.close()

    def test_mixed_psdata_and_raw(self):
        """PsData and raw arrays can be mixed in the same call."""
        fig = FigureGenerator(save_data=True)
        fig.init_figure()

        x_ps = _make_psdata([1, 2, 3])
        y_raw = np.array([10.0, 20.0, 30.0])
        fig.plot_line(x_ps, y_raw, label="mixed")

        np.testing.assert_array_equal(fig.data_storage._data["mixed"]["x"], x_ps.data)
        np.testing.assert_array_equal(fig.data_storage._data["mixed"]["y"], y_raw)
        fig.close()


# ---------------------------------------------------------------------------
# Auto-label from PsData
# ---------------------------------------------------------------------------


def _make_psdata_with_units(data_array, key="test_key", units="m", label=None):
    """Helper to create PsData with explicit units and label."""
    return PsData(
        data_key=key,
        data_type="test",
        data_array=np.array(data_array, dtype=float),
        import_units=units,
        data_label=label,
    )


class TestAutoLabel:
    def test_format_psdata_label_with_units(self):
        ps = _make_psdata_with_units([1], key="LCOW", units="USD/m**3", label="LCOW")
        label = FigureGenerator._format_psdata_label(ps)
        assert label == "LCOW ($\$$/$m^3$)"

    def test_format_psdata_label_dimensionless(self):
        ps = _make_psdata_with_units(
            [1], key="recovery", units="dimensionless", label="Recovery"
        )
        label = FigureGenerator._format_psdata_label(ps)
        assert label == "Recovery"

    def test_capture_psdata_label_stores_on_instance(self):
        fig = FigureGenerator()
        ps = _make_psdata_with_units(
            [1, 2], key="flow", units="m**3/s", label="Flow Rate"
        )
        fig._capture_psdata_label(ps, "x")
        assert fig._auto_labels["x"] is not None
        assert "Flow Rate" in fig._auto_labels["x"]

    def test_capture_psdata_label_ignores_non_psdata(self):
        fig = FigureGenerator()
        fig._capture_psdata_label(np.array([1, 2]), "x")
        assert fig._auto_labels["x"] is None

    def test_resolve_auto_label_returns_stored(self):
        fig = FigureGenerator()
        fig._auto_labels["x"] = "Pressure (bar)"
        assert fig._resolve_auto_label("auto", "x") == "Pressure (bar)"

    def test_resolve_auto_label_passes_through_string(self):
        fig = FigureGenerator()
        assert fig._resolve_auto_label("My Label", "x") == "My Label"

    def test_resolve_auto_label_returns_none_when_unset(self):
        fig = FigureGenerator()
        assert fig._resolve_auto_label("auto", "y") is None

    def test_plot_line_captures_xy_labels(self):
        fig = FigureGenerator()
        fig.init_figure()
        x = _make_psdata_with_units(
            [1, 2, 3], key="pressure", units="bar", label="Pressure"
        )
        y = _make_psdata_with_units(
            [10, 20, 30], key="flow", units="m**3/s", label="Flow"
        )
        fig.plot_line(xdata=x, ydata=y, label="test")
        assert "Pressure" in fig._auto_labels["x"]
        assert "Flow" in fig._auto_labels["y"]
        fig.close()

    def test_plot_scatter_captures_xyz_labels(self):
        fig = FigureGenerator()
        fig.init_figure()
        x = _make_psdata_with_units([1, 2, 3], key="x", units="m", label="X")
        y = _make_psdata_with_units([4, 5, 6], key="y", units="kg", label="Y")
        z = _make_psdata_with_units([7, 8, 9], key="z", units="USD", label="Cost")
        fig.plot_scatter(xdata=x, ydata=y, zdata=z, label="sc")
        assert "X" in fig._auto_labels["x"]
        assert "Y" in fig._auto_labels["y"]
        assert "Cost" in fig._auto_labels["z"]
        fig.close()

    def test_plot_errorbar_captures_xy_labels(self):
        fig = FigureGenerator()
        fig.init_figure()
        x = _make_psdata_with_units([1, 2, 3], key="t", units="s", label="Time")
        y = _make_psdata_with_units(
            [10, 20, 30], key="v", units="m/s", label="Velocity"
        )
        fig.plot_errorbar(xdata=x, ydata=y, label="err")
        assert "Time" in fig._auto_labels["x"]
        assert "Velocity" in fig._auto_labels["y"]
        fig.close()

    def test_plot_bar_captures_xy_labels(self):
        fig = FigureGenerator()
        fig.init_figure()
        pos = _make_psdata_with_units(
            [0], key="cat", units="dimensionless", label="Category"
        )
        val = _make_psdata_with_units([5], key="cost", units="USD", label="Cost")
        fig.plot_bar(pos, val.data[0], label="bar")
        assert fig._auto_labels["x"] == "Category"
        fig.close()

    def test_plot_area_captures_xy_labels(self):
        fig = FigureGenerator()
        fig.init_figure()
        x = _make_psdata_with_units([1, 2, 3], key="x", units="m", label="Distance")
        y = _make_psdata_with_units([0, 1, 0], key="y", units="m", label="Height")
        y2 = np.array([1, 2, 1])
        fig.plot_area(xdata=x, ydata=y, y2data=y2, label="area")
        assert "Distance" in fig._auto_labels["x"]
        assert "Height" in fig._auto_labels["y"]
        fig.close()

    def test_set_axis_auto_xlabel(self):
        fig = FigureGenerator()
        fig.init_figure()
        x = _make_psdata_with_units([1, 2, 3], key="p", units="bar", label="Pressure")
        y = _make_psdata_with_units([10, 20, 30], key="f", units="L/min", label="Flow")
        fig.plot_line(xdata=x, ydata=y, label="test")
        fig.set_axis(xlabel="auto", ylabel="auto")
        ax = fig.get_axis(0)
        assert "Pressure" in ax.get_xlabel()
        assert "Flow" in ax.get_ylabel()
        fig.close()

    def test_set_axis_explicit_label_not_overridden(self):
        fig = FigureGenerator()
        fig.init_figure()
        x = _make_psdata_with_units([1, 2, 3], key="p", units="bar", label="Pressure")
        y = np.array([10, 20, 30])
        fig.plot_line(xdata=x, ydata=y, label="test")
        fig.set_axis(xlabel="My Custom X", ylabel="My Custom Y")
        ax = fig.get_axis(0)
        assert ax.get_xlabel() == "My Custom X"
        assert ax.get_ylabel() == "My Custom Y"
        fig.close()

    def test_set_axis_ticklabels_auto_xlabel(self):
        fig = FigureGenerator()
        fig.init_figure()
        x = _make_psdata_with_units([1, 2, 3], key="p", units="bar", label="Pressure")
        y = _make_psdata_with_units([10, 20, 30], key="f", units="L/min", label="Flow")
        fig.plot_line(xdata=x, ydata=y, label="test")
        fig.set_axis_ticklabels(xlabel="auto", ylabel="auto")
        ax = fig.get_axis(0)
        assert "Pressure" in ax.get_xlabel()
        assert "Flow" in ax.get_ylabel()
        fig.close()

    def test_add_colorbar_auto_zlabel(self):
        fig = FigureGenerator()
        fig.init_figure()
        x = _make_psdata_with_units(
            [1, 2, 3, 1, 2, 3, 1, 2, 3], key="x", units="m", label="X"
        )
        y = _make_psdata_with_units(
            [10, 10, 10, 20, 20, 20, 30, 30, 30], key="y", units="m", label="Y"
        )
        z = _make_psdata_with_units(
            [1, 2, 3, 4, 5, 6, 7, 8, 9], key="cost", units="USD", label="Cost"
        )
        fig.plot_scatter(xdata=x, ydata=y, zdata=z, vmin=1, vmax=9, label="sc")
        fig.add_colorbar(zlabel="auto", zticks=[1, 3, 5, 7, 9])
        assert "Cost" in fig._auto_labels["z"]
        fig.close()

    def test_later_plot_overwrites_auto_label(self):
        fig = FigureGenerator()
        fig.init_figure()
        x1 = _make_psdata_with_units([1, 2, 3], key="p", units="bar", label="Pressure")
        y1 = np.array([10, 20, 30])
        fig.plot_line(xdata=x1, ydata=y1, label="first")
        assert "Pressure" in fig._auto_labels["x"]

        x2 = _make_psdata_with_units([4, 5, 6], key="t", units="s", label="Time")
        y2 = np.array([40, 50, 60])
        fig.plot_line(xdata=x2, ydata=y2, label="second")
        assert "Time" in fig._auto_labels["x"]
        fig.close()

    def test_raw_data_does_not_clear_auto_label(self):
        fig = FigureGenerator()
        fig.init_figure()
        x = _make_psdata_with_units([1, 2, 3], key="p", units="bar", label="Pressure")
        y = np.array([10, 20, 30])
        fig.plot_line(xdata=x, ydata=y, label="first")
        assert "Pressure" in fig._auto_labels["x"]

        # Plotting with raw data should not clear the stored label
        fig.plot_line(
            xdata=np.array([4, 5, 6]), ydata=np.array([40, 50, 60]), label="second"
        )
        assert "Pressure" in fig._auto_labels["x"]
        fig.close()


# ---------------------------------------------------------------------------
# auto_gen_lims with data_storage
# ---------------------------------------------------------------------------


class TestAutoGenLims:
    def test_line_data_x_limits(self):
        fig = FigureGenerator(save_data=True)
        fig.init_figure()
        fig.plot_line(
            xdata=np.array([2.0, 5.0, 8.0]),
            ydata=np.array([10.0, 20.0, 30.0]),
            label="s1",
        )
        vmin, vmax = fig.auto_gen_lims("datax")
        assert vmin == pytest.approx(2.0)
        assert vmax == pytest.approx(8.0)
        fig.close()

    def test_line_data_y_limits(self):
        fig = FigureGenerator(save_data=True)
        fig.init_figure()
        fig.plot_line(
            xdata=np.array([1.0, 2.0]),
            ydata=np.array([-5.0, 15.0]),
            label="s1",
        )
        vmin, vmax = fig.auto_gen_lims("datay")
        assert vmin == pytest.approx(-5.0)
        assert vmax == pytest.approx(15.0)
        fig.close()

    def test_multiple_series(self):
        fig = FigureGenerator(save_data=True)
        fig.init_figure()
        fig.plot_line(
            xdata=np.array([3.0, 4.0]),
            ydata=np.array([10.0, 20.0]),
            label="a",
        )
        fig.plot_line(
            xdata=np.array([1.0, 6.0]),
            ydata=np.array([5.0, 25.0]),
            label="b",
        )
        vmin, vmax = fig.auto_gen_lims("datax")
        assert vmin == pytest.approx(1.0)
        assert vmax == pytest.approx(6.0)
        vmin, vmax = fig.auto_gen_lims("datay")
        assert vmin == pytest.approx(5.0)
        assert vmax == pytest.approx(25.0)
        fig.close()

    def test_errorbar_data_limits(self):
        fig = FigureGenerator(save_data=True)
        fig.init_figure()
        fig.plot_errorbar(
            xdata=np.array([0.0, 10.0]),
            ydata=np.array([100.0, 200.0]),
            label="err",
        )
        vmin, vmax = fig.auto_gen_lims("datax")
        assert vmin == pytest.approx(0.0)
        assert vmax == pytest.approx(10.0)
        fig.close()

    def test_map_data_limits(self):
        fig = FigureGenerator(save_data=True)
        fig.init_figure()
        x = np.array([1.0, 2.0, 3.0, 1.0, 2.0, 3.0])
        y = np.array([10.0, 10.0, 10.0, 20.0, 20.0, 20.0])
        z = np.array([5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
        fig.plot_map(xdata=x, ydata=y, zdata=z, text=False)
        vmin, vmax = fig.auto_gen_lims("datax")
        assert vmin == pytest.approx(1.0)
        assert vmax == pytest.approx(3.0)
        vmin, vmax = fig.auto_gen_lims("datay")
        assert vmin == pytest.approx(10.0)
        assert vmax == pytest.approx(20.0)
        fig.close()

    def test_no_data_raises_value_error(self):
        fig = FigureGenerator()
        fig.init_figure()
        with pytest.raises(ValueError, match="No data available"):
            fig.auto_gen_lims("datax")
        fig.close()

    def test_set_axis_auto_ticks_from_data_storage(self):
        """set_axis with no xlims/xticks should auto-generate from data_storage."""
        fig = FigureGenerator(save_data=True)
        fig.init_figure()
        fig.plot_line(
            xdata=np.array([2.0, 8.0]),
            ydata=np.array([10.0, 50.0]),
            label="test",
        )
        fig.set_axis()
        ax = fig.get_axis(0)
        xlim = ax.get_xlim()
        assert xlim[0] == pytest.approx(2.0)
        assert xlim[1] == pytest.approx(8.0)
        ylim = ax.get_ylim()
        assert ylim[0] == pytest.approx(10.0)
        assert ylim[1] == pytest.approx(50.0)
        fig.close()
