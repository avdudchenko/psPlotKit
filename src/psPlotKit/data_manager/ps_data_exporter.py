import os
import csv
import numpy as np
from psPlotKit.util.logger import define_logger

__author__ = "Alexander V. Dudchenko"

_logger = define_logger(__name__, "PsDataExporter", level="INFO")


class PsDataExporter:
    """Export data from a :class:`PsDataManager` instance to CSV files.

    Parameters
    ----------
    ps_data_manager : PsDataManager
        The data manager instance containing loaded data.
    save_location : str
        File path (single directory) or folder path (multiple directories)
        where the CSV output will be written.

    Notes
    -----
    * If the manager contains a **single directory**, data is written to a
      single CSV file at *save_location* (e.g. ``"results.csv"``).
    * If the manager contains **multiple directories**, a folder is created
      at *save_location* and each directory's data is saved as a separate
      CSV file inside that folder.
    * Column headers are built from each :class:`PsData` object's
      ``data_label`` and ``mpl_units`` attributes (set by
      :meth:`PsData.set_label`).
    """

    def __init__(self, ps_data_manager, save_location):
        self.ps_data_manager = ps_data_manager
        self.save_location = save_location

    @staticmethod
    def _ensure_csv_extension(path):
        """Return *path* with a ``.csv`` extension appended if missing."""
        if not path.endswith(".csv"):
            return path + ".csv"
        return path

    @staticmethod
    def _strip_csv_extension(path):
        """Return *path* with a trailing ``.csv`` extension removed if present."""
        if path.endswith(".csv"):
            return path[:-4]
        return path

    def export(self):
        """Export the data manager contents to CSV.

        Returns
        -------
        list[str]
            List of file paths that were written.
        """
        grouped = self._group_data_by_directory()
        total_keys = sum(len(items) for items in grouped.values())
        _logger.info(
            "Found {} data key(s) across {} directory(ies)".format(
                total_keys, len(grouped)
            )
        )

        if len(grouped) <= 1:
            return self._export_single(grouped)
        else:
            return self._export_multiple(grouped)

    def _group_data_by_directory(self):
        """Group PsData objects by their directory key.

        Uses the ``data_directory`` attribute stored on each
        :class:`PsData` instance (set by :meth:`PsDataManager.add_data`)
        so the grouping works for both single-directory managers (where
        composite keys are plain strings) and multi-directory managers
        (where composite keys are tuples).

        Returns
        -------
        dict
            Mapping of directory key -> list of (data_key, PsData) tuples.
        """
        dm = self.ps_data_manager
        grouped = {}

        for composite_key in dm.keys():
            ps_data = dm[composite_key]
            dir_key = getattr(ps_data, "data_directory", None)
            # Lists are unhashable — convert to tuple for use as dict key
            if isinstance(dir_key, list):
                dir_key = tuple(dir_key)
            data_key = dm._get_data_key(composite_key)

            if dir_key not in grouped:
                grouped[dir_key] = []
            grouped[dir_key].append((data_key, ps_data))

        return grouped

    def _build_header(self, data_items):
        """Build a CSV header row from a list of (data_key, PsData) pairs.

        Each column header is formatted as ``"label (units)"`` using the
        ``data_label`` and ``mpl_units`` attributes produced by
        :meth:`PsData.set_label`.

        Parameters
        ----------
        data_items : list[tuple]
            List of (data_key, PsData) pairs.

        Returns
        -------
        list[str]
            Column header strings.
        """
        headers = []
        for _, ps_data in data_items:
            label = ps_data.data_label
            units = getattr(ps_data, "mpl_units", "-")
            if units and units != "-":
                header = "{} ({})".format(label, units)
            else:
                header = str(label)
            headers.append(header)
        return headers

    def _build_rows(self, data_items):
        """Build row data from a list of (data_key, PsData) pairs.

        All data arrays are aligned by index.  If arrays have different
        lengths, shorter columns are padded with empty strings.

        Parameters
        ----------
        data_items : list[tuple]
            List of (data_key, PsData) pairs.

        Returns
        -------
        list[list]
            Row-major list of values.
        """
        arrays = [ps_data.data for _, ps_data in data_items]
        max_len = max((len(a) for a in arrays), default=0)

        rows = []
        for i in range(max_len):
            row = []
            for arr in arrays:
                if i < len(arr):
                    val = arr[i]
                    # Represent NaN as empty string for cleaner CSVs
                    if isinstance(val, (float, np.floating)) and np.isnan(val):
                        row.append("")
                    else:
                        row.append(val)
                else:
                    row.append("")
            rows.append(row)
        return rows

    def _write_csv(self, file_path, headers, rows):
        """Write headers and rows to a CSV file.

        Parameters
        ----------
        file_path : str
            Destination file path.
        headers : list[str]
            Column header strings.
        rows : list[list]
            Row-major data.
        """
        directory = os.path.dirname(file_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        with open(file_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)

        _logger.info("Saved CSV: {}".format(file_path))

    def _export_single(self, grouped):
        """Export data from a single directory (or empty manager) to one CSV.

        Parameters
        ----------
        grouped : dict
            Output from :meth:`_group_data_by_directory`.

        Returns
        -------
        list[str]
            List containing the single file path written.
        """
        save_path = self._ensure_csv_extension(self.save_location)

        if not grouped:
            _logger.warning("No data to export, the data manager is empty.")
            return []

        _logger.info("Single directory detected, exporting to single CSV file")
        data_items = list(grouped.values())[0]
        headers = self._build_header(data_items)
        rows = self._build_rows(data_items)
        _logger.info(
            "Writing {} columns and {} rows to {}".format(
                len(headers), len(rows), save_path
            )
        )
        self._write_csv(save_path, headers, rows)
        return [save_path]

    def _dir_key_to_filename(self, dir_key):
        """Convert a directory key (string or tuple) to a safe filename.

        Parameters
        ----------
        dir_key : str or tuple
            The directory key from the data manager.

        Returns
        -------
        str
            A sanitized filename string (without extension).
        """
        if isinstance(dir_key, tuple):
            parts = []
            for element in dir_key:
                if isinstance(element, tuple):
                    parts.append("_".join(str(e) for e in element))
                else:
                    parts.append(str(element))
            name = "_".join(parts)
        else:
            name = str(dir_key)

        # Sanitize: replace characters that are unsafe in filenames
        for char in ["/", "\\", ":", "*", "?", '"', "<", ">", "|", " "]:
            name = name.replace(char, "_")
        return name

    def _export_multiple(self, grouped):
        """Export data from multiple directories into separate CSV files.

        A folder is created at :attr:`save_location` and each directory's
        data is written to its own CSV file inside.

        Parameters
        ----------
        grouped : dict
            Output from :meth:`_group_data_by_directory`.

        Returns
        -------
        list[str]
            List of file paths written.
        """
        folder = self._strip_csv_extension(self.save_location)
        os.makedirs(folder, exist_ok=True)
        _logger.info(
            "Multiple directories detected, creating folder: {}".format(folder)
        )

        written = []
        for dir_key, data_items in grouped.items():
            filename = self._dir_key_to_filename(dir_key) + ".csv"
            file_path = os.path.join(folder, filename)
            headers = self._build_header(data_items)
            rows = self._build_rows(data_items)
            _logger.info(
                "Directory '{}': writing {} columns and {} rows to {}".format(
                    dir_key, len(headers), len(rows), filename
                )
            )
            self._write_csv(file_path, headers, rows)
            written.append(file_path)

        _logger.info(
            "Export complete, {} CSV files saved to: {}".format(len(written), folder)
        )
        return written


class psDataExporter(PsDataExporter):
    """Deprecated alias — use :class:`PsDataExporter` instead."""

    def __init__(self, *args, **kwargs):
        import warnings

        warnings.warn(
            "psDataExporter is deprecated; use PsDataExporter instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)
