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
    first_key : str, optional
        Data key that should always appear as the first column in the exported
        CSV files. If provided and the key exists in the data, it will be
        moved to the front of the column order.
    export_keys : list, optional
        List of keys to include in export. Each key is matched against data keys:
        - For string keys, a match occurs if the key is in the list
        - For tuple keys, a match occurs if any element of the tuple is in the list
        If None, all non-internal keys are exported.
    exact_keys : list, optional
        List of keys to include in export with exact matching. The entire key
        (including all tuple elements) must match exactly. If specified, this
        takes precedence over export_keys.

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
    * Internal keys (e.g., ``_zero_sentinel``) are automatically excluded
      from export.
    * For tuple data keys (e.g., ``("costing", "pump")``), multi-row headers
      are generated with each tuple element in a separate row, making the
      structure clearer when reading CSVs in spreadsheet applications.
    """

    def __init__(
        self,
        ps_data_manager,
        save_location,
        first_key=None,
        export_keys=None,
        exact_keys=None,
    ):
        self.ps_data_manager = ps_data_manager
        self.save_location = save_location
        self.first_key = first_key
        self.export_keys = export_keys
        self.exact_keys = exact_keys

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

        Internal keys like ``_zero_sentinel`` are excluded from export.

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

            # Skip internal keys like _zero_sentinel
            if self._is_internal_key(data_key):
                continue

            # Skip keys not in export filter
            if not self._should_export_key(data_key):
                continue

            if dir_key not in grouped:
                grouped[dir_key] = []
            grouped[dir_key].append((data_key, ps_data))

        return grouped

    def _should_export_key(self, data_key):
        """Check if a data key should be exported based on export_keys/exact_keys filters.

        Parameters
        ----------
        data_key : str or tuple
            The data key to check (may contain nested tuples).

        Returns
        -------
        bool
            True if the key should be included in export.
        """
        # Flatten nested tuples for matching
        flat_key = (
            self._flatten_key(data_key) if isinstance(data_key, tuple) else data_key
        )

        if self.exact_keys is not None:
            return data_key in self.exact_keys

        if self.export_keys is not None:
            if isinstance(flat_key, tuple):
                # For tuple keys, match if ANY element is in export_keys
                return any(elem in self.export_keys for elem in flat_key)
            else:
                return flat_key in self.export_keys

        return True

    def _is_internal_key(self, data_key):
        """Check if a data key is an internal (non-exportable) key.

        Parameters
        ----------
        data_key : str or tuple
            The data key to check (may contain nested tuples).

        Returns
        -------
        bool
            True if the key should be excluded from export.
        """

        def check_item(item):
            if isinstance(item, tuple):
                return any("_zero_sentinel" in str(part) for part in item)
            return "_zero_sentinel" in str(item)

        if isinstance(data_key, tuple):
            # Check all elements including nested ones
            for elem in data_key:
                if check_item(elem):
                    return True
            return False
        return check_item(data_key)

    def _reorder_with_first(self, data_items):
        """Reorder data items to place first_key at the front if specified.

        Parameters
        ----------
        data_items : list[tuple]
            List of (data_key, PsData) pairs.

        Returns
        -------
        list[tuple]
            Reordered list with first_key at the front if applicable.
        """
        if not self.first_key:
            return data_items

        reordered = []
        first_item = None
        for item in data_items:
            data_key = item[0]
            # For tuple keys, also check flattened version for matching
            key_to_check = (
                self._flatten_key(data_key) if isinstance(data_key, tuple) else data_key
            )
            if data_key == self.first_key or (
                isinstance(key_to_check, tuple) and self.first_key in key_to_check
            ):
                first_item = item
            else:
                reordered.append(item)

        if first_item:
            reordered.insert(0, first_item)
            _logger.info("Placed '{}' as first column".format(self.first_key))
        else:
            _logger.warning(
                "first_key '{}' not found in data keys".format(self.first_key)
            )

        return reordered

    def _build_header(self, data_items):
        """Build CSV header rows from a list of (data_key, PsData) pairs.

        For string data keys, returns a single header row. For tuple data keys,
        returns multiple header rows with the tuple components in separate rows,
        making multi-level keys easier to read.

        Parameters
        ----------
        data_items : list[tuple]
            List of (data_key, PsData) pairs.

        Returns
        -------
        list[list[str]]
            List of header rows (each row is a list of strings).
            Single row if all keys are strings, multiple rows for tuple keys.
        """
        has_tuple_keys = any(isinstance(key, tuple) for key, _ in data_items)

        if not has_tuple_keys:
            return self._build_single_row_header(data_items)

        return self._build_multi_row_header(data_items)

    def _build_single_row_header(self, data_items):
        """Build a single header row from data items.

        Parameters
        ----------
        data_items : list[tuple]
            List of (data_key, PsData) pairs.

        Returns
        -------
        list[list[str]]
            Single row as a list containing one list of header strings.
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
        return [headers]

    @staticmethod
    def _flatten_key(data_key):
        """Flatten nested tuples into a single-level tuple.

        For example, ("costing", ("stage 1", "pump"), "LCOW") becomes
        ("costing", "stage 1", "pump", "LCOW").

        Parameters
        ----------
        data_key : tuple
            The data key potentially containing nested tuples.

        Returns
        -------
        tuple
            Flattened tuple with all elements at single level.
        """
        flattened = []
        for elem in data_key:
            if isinstance(elem, tuple):
                flattened.extend(elem)
            else:
                flattened.append(elem)
        return tuple(flattened)

    def _build_multi_row_header(self, data_items):
        """Build multi-row headers for tuple data keys.

        Parameters
        ----------
        data_items : list[tuple]
            List of (data_key, PsData) pairs.

        Returns
        -------
        list[list[str]]
            List of header rows. Shorter tuples are aligned to the bottom,
            so all labels appear in the final row.
        """
        # Flatten nested tuples to determine max depth
        flattened_keys = []
        for key, _ in data_items:
            if isinstance(key, tuple):
                flattened_keys.append(self._flatten_key(key))
            else:
                flattened_keys.append(key)

        max_depth = max(
            (len(key) for key in flattened_keys if isinstance(key, tuple)), default=1
        )

        header_rows = [[] for _ in range(max_depth)]

        for idx, (data_key, ps_data) in enumerate(data_items):
            label = ps_data.data_label
            units = getattr(ps_data, "mpl_units", "-")

            flat_key = flattened_keys[idx]

            # If label equals data_key, use the last tuple element as label
            if label == data_key and isinstance(data_key, tuple):
                label = flat_key[-1]

            if units and units != "-":
                full_label = "{} ({})".format(label, units)
            else:
                full_label = str(label)

            if isinstance(flat_key, tuple):
                key_len = len(flat_key)
                # Calculate starting row (align shorter tuples to bottom)
                start_row = max_depth - key_len
                for row_idx in range(max_depth):
                    if row_idx < start_row:
                        header_rows[row_idx].append("")
                    elif row_idx == max_depth - 1:
                        # Last row gets the full label
                        header_rows[row_idx].append(full_label)
                    else:
                        # Middle rows get tuple elements starting from start_row
                        elem_idx = row_idx - start_row
                        header_rows[row_idx].append(str(flat_key[elem_idx]))
            else:
                # String keys go in the last row only
                for row_idx in range(max_depth):
                    if row_idx == max_depth - 1:
                        header_rows[row_idx].append(full_label)
                    else:
                        header_rows[row_idx].append("")

        return header_rows

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

    def _write_csv(self, file_path, header_rows, rows):
        """Write headers and rows to a CSV file.

        Parameters
        ----------
        file_path : str
            Destination file path.
        header_rows : list[list[str]]
            List of header row lists (supports multi-level headers).
        rows : list[list]
            Row-major data.
        """
        directory = os.path.dirname(file_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        with open(file_path, "w", newline="") as f:
            writer = csv.writer(f)
            for header_row in header_rows:
                writer.writerow(header_row)
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
        data_items = self._reorder_with_first(data_items)
        header_rows = self._build_header(data_items)
        rows = self._build_rows(data_items)
        _logger.info(
            "Writing {} columns and {} rows to {}".format(
                len(header_rows[0]), len(rows), save_path
            )
        )
        self._write_csv(save_path, header_rows, rows)
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
            data_items = self._reorder_with_first(data_items)
            header_rows = self._build_header(data_items)
            rows = self._build_rows(data_items)
            _logger.info(
                "Directory '{}': writing {} columns and {} rows to {}".format(
                    dir_key, len(header_rows[0]), len(rows), filename
                )
            )
            self._write_csv(file_path, header_rows, rows)
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
