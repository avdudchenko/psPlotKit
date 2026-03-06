import pytest
import os
import csv
import numpy as np
from psPlotKit.data_manager.ps_data_manager import PsDataManager
from psPlotKit.data_manager.ps_data import PsData
from psPlotKit.data_manager.ps_data_exporter import PsDataExporter, psDataExporter

__author__ = "Alexander V. Dudchenko"

_this_file_path = os.path.dirname(os.path.abspath(__file__))
_test_file = os.path.join(_this_file_path, "multi_dir_test.h5")
_test_single_file = os.path.join(_this_file_path, "single_dir_test.h5")


# ---------- fixtures ----------


@pytest.fixture
def single_dir_dm():
    """PsDataManager with single-directory data loaded."""
    dm = PsDataManager(_test_single_file)
    dm.register_data_key("output_c", "LCOW")
    dm.register_data_key("output_c", "LCOW2")
    dm.load_data()
    return dm


@pytest.fixture
def multi_dir_dm():
    """PsDataManager with multi-directory data loaded."""
    dm = PsDataManager(_test_file)
    dm.register_data_key("LCOW", "LCOW")
    dm.load_data()
    return dm


@pytest.fixture
def manual_single_dm():
    """Manually constructed single-directory PsDataManager."""
    dm = PsDataManager()
    dm.PsDataImportInstances = []
    dm.add_data(
        "dir_a",
        "metric_1",
        PsData("metric_1", "test", [1.0, 2.0, 3.0], import_units="m"),
    )
    dm.add_data(
        "dir_a",
        "metric_2",
        PsData("metric_2", "test", [4.0, 5.0, 6.0], import_units="kg"),
    )
    return dm


@pytest.fixture
def manual_multi_dm():
    """Manually constructed multi-directory PsDataManager."""
    dm = PsDataManager()
    dm.PsDataImportInstances = []
    dm.add_data(
        "dir_a",
        "metric_1",
        PsData("metric_1", "test", [1.0, 2.0, 3.0], import_units="m"),
    )
    dm.add_data(
        "dir_a",
        "metric_2",
        PsData("metric_2", "test", [4.0, 5.0, 6.0], import_units="kg"),
    )
    dm.add_data(
        "dir_b",
        "metric_1",
        PsData("metric_1", "test", [7.0, 8.0], import_units="m"),
    )
    dm.add_data(
        "dir_b",
        "metric_2",
        PsData("metric_2", "test", [9.0, 10.0], import_units="kg"),
    )
    return dm


# ---------- single directory export ----------


class TestSingleDirectoryExport:
    def test_export_creates_csv_file(self, manual_single_dm, tmp_path):
        save_path = str(tmp_path / "output.csv")
        exporter = PsDataExporter(manual_single_dm, save_path)
        written = exporter.export()

        assert len(written) == 1
        assert os.path.exists(written[0])

    def test_export_appends_csv_extension(self, manual_single_dm, tmp_path):
        save_path = str(tmp_path / "output")
        exporter = PsDataExporter(manual_single_dm, save_path)
        written = exporter.export()

        assert written[0].endswith(".csv")

    def test_export_headers_contain_label_and_units(self, manual_single_dm, tmp_path):
        save_path = str(tmp_path / "output.csv")
        exporter = PsDataExporter(manual_single_dm, save_path)
        exporter.export()

        with open(save_path, "r") as f:
            reader = csv.reader(f)
            headers = next(reader)

        assert len(headers) == 2
        assert "metric_1" in headers[0]
        assert "m" in headers[0]
        assert "metric_2" in headers[1]
        assert "kg" in headers[1]

    def test_export_data_values_correct(self, manual_single_dm, tmp_path):
        save_path = str(tmp_path / "results.csv")
        exporter = PsDataExporter(manual_single_dm, save_path)
        exporter.export()

        with open(save_path, "r") as f:
            reader = csv.reader(f)
            headers = next(reader)
            rows = list(reader)

        assert len(rows) == 3
        assert float(rows[0][0]) == pytest.approx(1.0)
        assert float(rows[2][1]) == pytest.approx(6.0)

    def test_export_with_real_h5_single_dir(self, single_dir_dm, tmp_path):
        save_path = str(tmp_path / "single_dir.csv")
        exporter = PsDataExporter(single_dir_dm, save_path)
        written = exporter.export()

        assert len(written) == 1
        assert os.path.exists(written[0])

        with open(written[0], "r") as f:
            reader = csv.reader(f)
            headers = next(reader)
            rows = list(reader)

        assert len(headers) >= 2
        assert len(rows) > 0


# ---------- multi-directory export ----------


class TestMultiDirectoryExport:
    def test_export_creates_folder_and_files(self, manual_multi_dm, tmp_path):
        save_folder = str(tmp_path / "export_folder")
        exporter = PsDataExporter(manual_multi_dm, save_folder)
        written = exporter.export()

        assert os.path.isdir(save_folder)
        assert len(written) == 2
        for path in written:
            assert os.path.exists(path)
            assert path.endswith(".csv")

    def test_export_each_file_has_correct_data(self, manual_multi_dm, tmp_path):
        save_folder = str(tmp_path / "export_folder")
        exporter = PsDataExporter(manual_multi_dm, save_folder)
        written = exporter.export()

        # Find the file for dir_a (should have 3 rows) and dir_b (should have 2 rows)
        for path in written:
            with open(path, "r") as f:
                reader = csv.reader(f)
                headers = next(reader)
                rows = list(reader)

            assert len(headers) == 2
            if "dir_a" in path:
                assert len(rows) == 3
            elif "dir_b" in path:
                assert len(rows) == 2

    def test_export_with_real_h5_multi_dir(self, multi_dir_dm, tmp_path):
        save_folder = str(tmp_path / "multi_export")
        exporter = PsDataExporter(multi_dir_dm, save_folder)
        written = exporter.export()

        assert len(written) > 0
        for path in written:
            assert os.path.exists(path)


# ---------- edge cases ----------


class TestEdgeCases:
    def test_empty_manager_returns_empty(self, tmp_path):
        dm = PsDataManager()
        dm.PsDataImportInstances = []
        save_path = str(tmp_path / "empty.csv")
        exporter = PsDataExporter(dm, save_path)
        written = exporter.export()

        assert written == []

    def test_nan_values_exported_as_empty(self, tmp_path):
        dm = PsDataManager()
        dm.PsDataImportInstances = []
        dm.add_data(
            "dir_a",
            "with_nan",
            PsData("with_nan", "test", [1.0, np.nan, 3.0]),
        )
        save_path = str(tmp_path / "nan_test.csv")
        exporter = PsDataExporter(dm, save_path)
        exporter.export()

        with open(save_path, "r") as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            rows = list(reader)

        assert rows[1][0] == ""  # NaN → empty string

    def test_uneven_array_lengths_padded(self, tmp_path):
        dm = PsDataManager()
        dm.PsDataImportInstances = []
        dm.add_data(
            "dir_a",
            "short",
            PsData("short", "test", [1.0, 2.0]),
        )
        dm.add_data(
            "dir_a",
            "long",
            PsData("long", "test", [10.0, 20.0, 30.0, 40.0]),
        )
        save_path = str(tmp_path / "uneven.csv")
        exporter = PsDataExporter(dm, save_path)
        exporter.export()

        with open(save_path, "r") as f:
            reader = csv.reader(f)
            next(reader)
            rows = list(reader)

        assert len(rows) == 4
        # Row index 2 should have empty for short column
        assert rows[2][0] == ""
        assert float(rows[2][1]) == pytest.approx(30.0)

    def test_dimensionless_units_no_parentheses(self, tmp_path):
        dm = PsDataManager()
        dm.PsDataImportInstances = []
        dm.add_data(
            "dir_a",
            "ratio",
            PsData("ratio", "test", [0.5, 0.6]),
        )
        save_path = str(tmp_path / "dimensionless.csv")
        exporter = PsDataExporter(dm, save_path)
        exporter.export()

        with open(save_path, "r") as f:
            reader = csv.reader(f)
            headers = next(reader)

        # Dimensionless data should not have "(units)" in header
        assert "(" not in headers[0]


# ---------- PsDataManager.export_data_to_csv convenience method ----------


class TestSaveLocationSanitization:
    def test_single_dir_without_csv_gets_extension(self, manual_single_dm, tmp_path):
        """Single-dir export: path without .csv should get .csv appended."""
        save_path = str(tmp_path / "no_extension")
        written = manual_single_dm.export_data_to_csv(save_path)

        assert len(written) == 1
        assert written[0].endswith(".csv")
        assert os.path.isfile(written[0])

    def test_single_dir_with_csv_keeps_extension(self, manual_single_dm, tmp_path):
        """Single-dir export: path already ending in .csv stays the same."""
        save_path = str(tmp_path / "with_ext.csv")
        written = manual_single_dm.export_data_to_csv(save_path)

        assert len(written) == 1
        assert written[0] == save_path
        assert os.path.isfile(written[0])

    def test_multi_dir_with_csv_strips_extension(self, manual_multi_dm, tmp_path):
        """Multi-dir export: if user passes 'output.csv', folder should be
        'output' (not 'output.csv/')."""
        save_path = str(tmp_path / "multi_output.csv")
        written = manual_multi_dm.export_data_to_csv(save_path)

        expected_folder = str(tmp_path / "multi_output")
        assert os.path.isdir(expected_folder)
        assert not os.path.exists(save_path)  # no file called multi_output.csv
        for path in written:
            assert os.path.exists(path)
            assert expected_folder in path

    def test_multi_dir_without_csv_uses_as_folder(self, manual_multi_dm, tmp_path):
        """Multi-dir export: path without .csv is used directly as folder."""
        save_folder = str(tmp_path / "plain_folder")
        written = manual_multi_dm.export_data_to_csv(save_folder)

        assert os.path.isdir(save_folder)
        assert len(written) == 2
        for path in written:
            assert save_folder in path


class TestExportDataToCsvMethod:
    def test_single_dir_via_manager(self, single_dir_dm, tmp_path):
        save_path = str(tmp_path / "from_manager.csv")
        written = single_dir_dm.export_data_to_csv(save_path)

        assert len(written) == 1
        assert os.path.exists(written[0])

        with open(written[0], "r") as f:
            reader = csv.reader(f)
            headers = next(reader)
            rows = list(reader)

        assert len(headers) >= 2
        assert len(rows) > 0

    def test_multi_dir_via_manager(self, multi_dir_dm, tmp_path):
        save_folder = str(tmp_path / "manager_export")
        written = multi_dir_dm.export_data_to_csv(save_folder)

        assert os.path.isdir(save_folder)
        assert len(written) > 1
        for path in written:
            assert os.path.exists(path)

    def test_manual_single_via_manager(self, manual_single_dm, tmp_path):
        save_path = str(tmp_path / "manual.csv")
        written = manual_single_dm.export_data_to_csv(save_path)

        assert len(written) == 1
        with open(written[0], "r") as f:
            reader = csv.reader(f)
            headers = next(reader)
            rows = list(reader)

        assert len(headers) == 2
        assert len(rows) == 3
        assert float(rows[0][0]) == pytest.approx(1.0)
