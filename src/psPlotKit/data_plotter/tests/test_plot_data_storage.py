import os
import csv
import numpy as np
import pytest

from psPlotKit.data_plotter.plot_data_storage import (
    PlotDataStorage,
    LineDataStorage,
    ErrorBarDataStorage,
    MapDataStorage,
    BarDataStorage,
    BoxDataStorage,
)

__author__ = "Alexander V. Dudchenko (SLAC)"

test_dir = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(test_dir, "test_output")


def _read_csv(path):
    """Read a CSV file and return rows as list of lists."""
    with open(path, "r", newline="") as f:
        return list(csv.reader(f))


@pytest.fixture(autouse=True)
def _clean_output():
    """Create and clean the temporary output directory."""
    os.makedirs(output_dir, exist_ok=True)
    yield
    # cleanup written files after each test
    for fname in os.listdir(output_dir):
        os.remove(os.path.join(output_dir, fname))
    os.rmdir(output_dir)


# ---------------------------------------------------------------------------
# PlotDataStorage (base)
# ---------------------------------------------------------------------------


class TestPlotDataStorage:
    def test_update_labels(self):
        s = PlotDataStorage()
        assert s.xlabel is None
        s.update_labels(xlabel="Pressure (bar)", ylabel="Flow (L/h)")
        assert s.xlabel == "Pressure (bar)"
        assert s.ylabel == "Flow (L/h)"
        assert s.zlabel is None
        s.update_labels(zlabel="Cost (USD)")
        assert s.zlabel == "Cost (USD)"

    def test_build_csv_data_raises(self):
        with pytest.raises(NotImplementedError):
            PlotDataStorage()._build_csv_data()


# ---------------------------------------------------------------------------
# LineDataStorage
# ---------------------------------------------------------------------------


class TestLineDataStorage:
    def test_register_and_save(self):
        s = LineDataStorage()
        s.update_labels(xlabel="Pressure (bar)")
        s.register_data("LCOW", [1, 2, 3], [10, 20, 30])
        s.register_data("Flux", [1.5, 2.5], [15, 25])

        path = os.path.join(output_dir, "line_test")
        s.save(path)

        rows = _read_csv(path + ".csv")
        # row 0: series labels
        assert rows[0] == ["LCOW", "", "Flux", ""]
        # row 1: axis labels
        assert rows[1] == ["Pressure (bar)", "y", "Pressure (bar)", "y"]
        # 3 data rows (max length)
        assert len(rows) == 5  # 2 headers + 3 data rows
        # row 2, series 1
        assert float(rows[2][0]) == 1.0
        assert float(rows[2][1]) == 10.0
        # row 4, series 2 should be empty (shorter)
        assert rows[4][2] == ""
        assert rows[4][3] == ""

    def test_mismatched_lengths_raises(self):
        s = LineDataStorage()
        with pytest.raises(ValueError, match="same length"):
            s.register_data("bad", [1, 2], [10])

    def test_default_xlabel(self):
        s = LineDataStorage()
        s.register_data("A", [1], [2])
        rows = s._build_csv_data()
        assert rows[0][0] == "A"  # series label row
        assert rows[1][0] == "x"  # axis label row

    def test_overwrite_series(self):
        s = LineDataStorage()
        s.register_data("A", [1, 2], [3, 4])
        s.register_data("A", [5, 6], [7, 8])
        rows = s._build_csv_data()
        # 2 headers + 2 data rows
        assert len(rows) == 4
        assert float(rows[2][0]) == 5.0


# ---------------------------------------------------------------------------
# ErrorBarDataStorage
# ---------------------------------------------------------------------------


class TestErrorBarDataStorage:
    def test_register_with_yerr(self):
        s = ErrorBarDataStorage()
        s.update_labels(xlabel="x", ylabel="y")
        s.register_data("S1", [1, 2], [10, 20], yerr=[0.1, 0.2])
        rows = s._build_csv_data()
        assert rows[0] == ["S1", "", ""]
        assert rows[1] == ["x", "y", "y error"]
        assert len(rows) == 4  # 2 headers + 2 data rows
        assert float(rows[2][2]) == pytest.approx(0.1)

    def test_register_with_xerr_and_yerr(self):
        s = ErrorBarDataStorage()
        s.register_data("S1", [1], [10], xerr=[0.5], yerr=[0.1])
        rows = s._build_csv_data()
        assert rows[0] == ["S1", "", "", ""]
        assert rows[1] == ["x", "y", "x error", "y error"]
        assert float(rows[2][2]) == pytest.approx(0.5)
        assert float(rows[2][3]) == pytest.approx(0.1)

    def test_no_errors(self):
        s = ErrorBarDataStorage()
        s.register_data("S1", [1, 2], [10, 20])
        rows = s._build_csv_data()
        assert rows[0] == ["S1", ""]
        assert rows[1] == ["x", "y"]

    def test_mixed_series(self):
        s = ErrorBarDataStorage()
        s.register_data("A", [1], [10], yerr=[0.5])
        s.register_data("B", [2, 3], [20, 30])
        rows = s._build_csv_data()
        # row 0: series labels — A spans 3 cols, B spans 2 cols
        assert rows[0] == ["A", "", "", "B", ""]
        # row 1: axis/error labels
        assert rows[1] == ["x", "y", "y error", "x", "y"]
        # 2 data rows (max len) + 2 headers
        assert len(rows) == 4
        # second data row — A is empty
        assert rows[3][0] == ""
        assert rows[3][1] == ""
        assert rows[3][2] == ""

    def test_save_csv_file(self):
        s = ErrorBarDataStorage()
        s.register_data("S1", [1, 2], [3, 4], yerr=[0.1, 0.2])
        path = os.path.join(output_dir, "err_test.csv")
        s.save(path)
        assert os.path.exists(path)
        rows = _read_csv(path)
        assert len(rows) == 4  # 2 headers + 2 data rows


# ---------------------------------------------------------------------------
# MapDataStorage
# ---------------------------------------------------------------------------


class TestMapDataStorage:
    def test_register_and_build(self):
        s = MapDataStorage()
        s.update_labels(zlabel="Cost (USD/m3)")
        x = [10, 20, 30]
        y = [1, 2]
        z = [[11, 12, 13], [21, 22, 23]]
        s.register_data(x, y, z)
        rows = s._build_csv_data()
        # row 0: label description header
        assert "first column: y" in rows[0][0]
        assert "first row: x" in rows[0][0]
        assert "data: Cost (USD/m3)" in rows[0][0]
        # row 1: corner_label, x1, x2, x3
        assert rows[1][0] == ""
        assert float(rows[1][1]) == 10
        # data rows
        assert float(rows[2][0]) == 1
        assert float(rows[2][1]) == 11
        assert float(rows[3][3]) == 23

    def test_wrong_z_shape_raises(self):
        s = MapDataStorage()
        with pytest.raises(ValueError, match="does not match"):
            s.register_data([1, 2], [3, 4, 5], [[1, 2], [3, 4]])

    def test_non_2d_z_raises(self):
        s = MapDataStorage()
        with pytest.raises(ValueError, match="2-D"):
            s.register_data([1, 2], [3], [10, 20])

    def test_save(self):
        s = MapDataStorage()
        s.register_data([1, 2], [3, 4], [[5, 6], [7, 8]])
        path = os.path.join(output_dir, "map_test")
        s.save(path)
        assert os.path.exists(path + ".csv")
        rows = _read_csv(path + ".csv")
        assert len(rows) == 4  # label desc + header + 2 y rows


# ---------------------------------------------------------------------------
# BarDataStorage
# ---------------------------------------------------------------------------


class TestBarDataStorage:
    def test_register_and_build(self):
        s = BarDataStorage()
        s.update_labels(ylabel="LCOW (USD/m3)")
        s.register_data("RO", -10, 10)
        s.register_data("MF", -25, 15)
        rows = s._build_csv_data()
        assert rows[0] == [
            "label",
            "lower (LCOW (USD/m3))",
            "upper (LCOW (USD/m3))",
        ]
        assert rows[1] == ["RO", -10, 10]
        assert rows[2] == ["MF", -25, 15]

    def test_default_ylabel(self):
        s = BarDataStorage()
        s.register_data("A", 0, 5)
        rows = s._build_csv_data()
        assert "value" in rows[0][1]

    def test_ordering_preserved(self):
        s = BarDataStorage()
        s.register_data("C", 1, 2)
        s.register_data("A", 3, 4)
        s.register_data("B", 5, 6)
        rows = s._build_csv_data()
        assert [r[0] for r in rows[1:]] == ["C", "A", "B"]

    def test_save(self):
        s = BarDataStorage()
        s.register_data("X", 0, 10)
        path = os.path.join(output_dir, "bar_test")
        s.save(path)
        assert os.path.exists(path + ".csv")


# ---------------------------------------------------------------------------
# BoxDataStorage
# ---------------------------------------------------------------------------


class TestBoxDataStorage:
    def test_register_and_build(self):
        s = BoxDataStorage()
        s.update_labels(ylabel="Recovery (%)")
        data = list(range(101))  # 0 .. 100
        s.register_data("Scenario A", data, whiskers=[5, 95])
        rows = s._build_csv_data()
        assert rows[0] == [
            "label (Recovery (%))",
            "5th percentile",
            "25th percentile",
            "50th percentile",
            "75th percentile",
            "95th percentile",
        ]
        pcts = [float(v) for v in rows[1][1:]]
        assert pcts[0] == pytest.approx(5.0)
        assert pcts[1] == pytest.approx(25.0)
        assert pcts[2] == pytest.approx(50.0)
        assert pcts[3] == pytest.approx(75.0)
        assert pcts[4] == pytest.approx(95.0)

    def test_custom_whiskers(self):
        s = BoxDataStorage()
        data = list(range(101))
        s.register_data("B", data, whiskers=[10, 90])
        rows = s._build_csv_data()
        assert "10th percentile" in rows[0][1]
        assert "90th percentile" in rows[0][-1]
        pcts = [float(v) for v in rows[1][1:]]
        assert pcts[0] == pytest.approx(10.0)
        assert pcts[4] == pytest.approx(90.0)

    def test_default_whiskers(self):
        s = BoxDataStorage()
        s.register_data("C", [1, 2, 3, 4, 5])
        rows = s._build_csv_data()
        assert "5th percentile" in rows[0][1]

    def test_multiple_boxes(self):
        s = BoxDataStorage()
        s.register_data("A", [1, 2, 3])
        s.register_data("B", [4, 5, 6])
        rows = s._build_csv_data()
        assert len(rows) == 3  # header + 2 boxes
        assert rows[1][0] == "A"
        assert rows[2][0] == "B"

    def test_save(self):
        s = BoxDataStorage()
        s.register_data("A", [10, 20, 30, 40, 50])
        path = os.path.join(output_dir, "box_test.csv")
        s.save(path)
        assert os.path.exists(path)
        rows = _read_csv(path)
        assert len(rows) == 2
