import os
import csv
import numpy as np
import pytest
import matplotlib

matplotlib.use("Agg")  # non-interactive backend for CI

from psPlotKit.data_plotter.fig_generator import FigureGenerator
from psPlotKit.data_plotter.plot_data_storage import (
    LineDataStorage,
    ErrorBarDataStorage,
    MapDataStorage,
    BarDataStorage,
    BoxDataStorage,
)

__author__ = "Alexander V. Dudchenko (SLAC)"

test_dir = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(test_dir, "test_fig_output")


def _read_csv(path):
    with open(path, "r", newline="") as f:
        return list(csv.reader(f))


# @pytest.fixture(autouse=True)
# def _clean_output():
#     os.makedirs(output_dir, exist_ok=True)
#     yield
#     for fname in os.listdir(output_dir):
#         os.remove(os.path.join(output_dir, fname))
#     os.rmdir(output_dir)


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

    def test_line_no_storage_when_save_data_false(self):
        """FigureGenerator with save_data=False should not create storage."""
        fig = FigureGenerator()
        fig.init_figure()
        fig.plot_line([1, 2], [3, 4], label="test")
        assert fig.data_storage is None
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
    def test_all_plots_work_without_storage(self):
        """All plot methods should work when save_data=False (default)."""
        fig = FigureGenerator()
        fig.init_figure()

        fig.plot_line([1, 2], [3, 4], label="L1")
        fig.plot_scatter(xdata=[1, 2], ydata=[3, 4], label="S1")
        fig.plot_errorbar(xdata=[1, 2], ydata=[3, 4], yerr=[0.1, 0.2], label="E1")
        fig.plot_bar(0, 10, bottom=-5, label="B1")

        assert fig.data_storage is None
        fig.close()

    def test_box_plot_works_without_storage(self):
        fig = FigureGenerator()
        fig.init_figure()
        fig.plot_box(0, [1, 2, 3, 4, 5], save_label="Box1")
        assert fig.data_storage is None
        fig.close()
