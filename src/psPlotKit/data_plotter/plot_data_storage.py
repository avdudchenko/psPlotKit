import csv
import os
import numpy as np

from psPlotKit.util.logger import define_logger

__author__ = "Alexander V. Dudchenko "

_logger = define_logger(__name__, "PlotDataStorage", level="INFO")


class PlotDataStorage:
    """Base class for storing plotted data and exporting to CSV.

    Provides common label management and CSV writing. Subclasses implement
    ``register_data`` for their specific data shape and ``_build_csv_data``
    to produce the row list written by ``save``.
    """

    def __init__(self):
        self.xlabel = None
        self.ylabel = None
        self.zlabel = None
        self._data = {}

    def update_labels(self, xlabel=None, ylabel=None, zlabel=None):
        """Update axis labels used as CSV column headers.

        Args:
            xlabel: Label for the x-axis / x data columns.
            ylabel: Label for the y-axis / y data columns.
            zlabel: Label for the z-axis / z data (map plots).
        """
        if xlabel is not None:
            self.xlabel = xlabel
        if ylabel is not None:
            self.ylabel = ylabel
        if zlabel is not None:
            self.zlabel = zlabel

    def _build_csv_data(self):
        """Build the row list for CSV export.

        Returns:
            List of lists, where each inner list is one CSV row.

        Raises:
            NotImplementedError: Subclasses must override this method.
        """
        raise NotImplementedError

    def save(self, file_name):
        """Save stored data to a CSV file.

        Args:
            file_name: Output file path. The ``.csv`` extension is appended
                automatically when not already present.
        """
        if not file_name.endswith(".csv"):
            file_name += ".csv"
        data = self._build_csv_data()
        directory = os.path.dirname(file_name)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        with open(file_name, "w", newline="") as csvfile:
            writer = csv.writer(csvfile, delimiter=",")
            for row in data:
                writer.writerow(row)
        _logger.info("Saved data to {}".format(file_name))


class LineDataStorage(PlotDataStorage):
    """Store line-plot x/y series for CSV export.

    Each registered series keeps its own x and y arrays, allowing
    different series to have independent x values and lengths. The CSV
    is written with paired columns ``(x_label, y_label)`` per series,
    padded with empty strings for shorter series.

    Example CSV layout::

        Series A, , Series B,
        x, y, x, y
        1.0, 2.0, 0.5, 3.0
        2.0, 4.0, 1.5, 6.0
        3.0, 6.0, ,
    """

    def __init__(self):
        super().__init__()
        self._series_order = []

    def register_data(self, label, xdata, ydata):
        """Register a line data series.

        Args:
            label: Unique name for the series (used as column header).
            xdata: Array-like of x values.
            ydata: Array-like of y values (same length as *xdata*).
        """
        xdata = np.asarray(xdata).flatten()
        ydata = np.asarray(ydata).flatten()
        if len(xdata) != len(ydata):
            raise ValueError(
                "xdata and ydata must have the same length for series '{}'".format(
                    label
                )
            )
        self._data[label] = {"x": xdata, "y": ydata}
        if label not in self._series_order:
            self._series_order.append(label)

    def _build_csv_data(self):
        rows = []
        x_label = self.xlabel if self.xlabel else "x"
        y_label = self.ylabel if self.ylabel else "y"

        # Row 1: series labels (span across each x/y column pair)
        label_row = []
        for label in self._series_order:
            label_row.append(label)
            label_row.append("")
        rows.append(label_row)

        # Row 2: axis labels for each column pair
        axis_row = []
        for _label in self._series_order:
            axis_row.append(x_label)
            axis_row.append(y_label)
        rows.append(axis_row)

        max_len = max((len(self._data[s]["x"]) for s in self._series_order), default=0)
        for i in range(max_len):
            row = []
            for label in self._series_order:
                series = self._data[label]
                if i < len(series["x"]):
                    row.append(series["x"][i])
                    row.append(series["y"][i])
                else:
                    row.append("")
                    row.append("")
            rows.append(row)
        return rows


class ErrorBarDataStorage(PlotDataStorage):
    """Store error-bar plot data for CSV export.

    Extends the line-data approach with optional ``xerr`` and ``yerr``
    columns per series. Each series is independent (may differ in x values
    and length).

    Example CSV layout::

        Series A, , , Series B,
        x, y, y error, x, y
        1.0, 2.0, 0.1, 0.5, 3.0
        2.0, 4.0, 0.2, 1.5, 6.0
    """

    def __init__(self):
        super().__init__()
        self._series_order = []

    def register_data(self, label, xdata, ydata, xerr=None, yerr=None):
        """Register an error-bar data series.

        Args:
            label: Unique name for the series (used as column header).
            xdata: Array-like of x values.
            ydata: Array-like of y values.
            xerr: Optional array-like of x-direction errors.
            yerr: Optional array-like of y-direction errors.
        """
        xdata = np.asarray(xdata).flatten()
        ydata = np.asarray(ydata).flatten()
        if len(xdata) != len(ydata):
            raise ValueError(
                "xdata and ydata must have the same length for series '{}'".format(
                    label
                )
            )
        entry = {"x": xdata, "y": ydata}
        if xerr is not None:
            entry["xerr"] = np.asarray(xerr).flatten()
        if yerr is not None:
            entry["yerr"] = np.asarray(yerr).flatten()
        self._data[label] = entry
        if label not in self._series_order:
            self._series_order.append(label)

    def _build_csv_data(self):
        rows = []
        x_label = self.xlabel if self.xlabel else "x"
        y_label = self.ylabel if self.ylabel else "y"

        # Row 1: series labels (span across all columns for that series)
        label_row = []
        for label in self._series_order:
            entry = self._data[label]
            ncols = 2 + ("xerr" in entry) + ("yerr" in entry)
            label_row.append(label)
            label_row.extend([""] * (ncols - 1))
        rows.append(label_row)

        # Row 2: per-column axis / error labels
        axis_row = []
        for label in self._series_order:
            entry = self._data[label]
            axis_row.append(x_label)
            axis_row.append(y_label)
            if "xerr" in entry:
                axis_row.append("x error")
            if "yerr" in entry:
                axis_row.append("y error")
        rows.append(axis_row)

        max_len = max((len(self._data[s]["x"]) for s in self._series_order), default=0)
        for i in range(max_len):
            row = []
            for label in self._series_order:
                entry = self._data[label]
                if i < len(entry["x"]):
                    row.append(entry["x"][i])
                    row.append(entry["y"][i])
                    if "xerr" in entry:
                        row.append(entry["xerr"][i])
                    if "yerr" in entry:
                        row.append(entry["yerr"][i])
                else:
                    row.append("")
                    row.append("")
                    if "xerr" in entry:
                        row.append("")
                    if "yerr" in entry:
                        row.append("")
            rows.append(row)
        return rows


class MapDataStorage(PlotDataStorage):
    """Store map/contour grid data for CSV export.

    Data is written in a grid layout matching the visual map orientation:
    x values span the top row, y values fill the first column, and z data
    occupies the interior cells.

    Example CSV layout::

        first column: y_label, first row: x_label, data: z_label
        z_label, x1, x2, x3
        y1, z11, z12, z13
        y2, z21, z22, z23
        y3, z31, z32, z33
    """

    def __init__(self):
        super().__init__()

    def register_data(self, xdata, ydata, zdata):
        """Register map grid data.

        Args:
            xdata: 1-D array-like of x-axis values (columns).
            ydata: 1-D array-like of y-axis values (rows).
            zdata: 2-D array-like of shape ``(len(ydata), len(xdata))``
                containing the mapped values.
        """
        xdata = np.asarray(xdata).flatten()
        ydata = np.asarray(ydata).flatten()
        zdata = np.asarray(zdata)
        if zdata.ndim != 2:
            raise ValueError("zdata must be a 2-D array")
        if zdata.shape != (len(ydata), len(xdata)):
            raise ValueError(
                "zdata shape {} does not match (len(ydata), len(xdata)) = ({}, {})".format(
                    zdata.shape, len(ydata), len(xdata)
                )
            )
        self._data = {"x": xdata, "y": ydata, "z": zdata}

    def _build_csv_data(self):
        rows = []
        xdata = self._data["x"]
        ydata = self._data["y"]
        zdata = self._data["z"]

        x_label = self.xlabel if self.xlabel else "x"
        y_label = self.ylabel if self.ylabel else "y"
        z_label = self.zlabel if self.zlabel else "z"

        # Row 0: label description header
        rows.append(
            [
                "first column: {}, first row: {}, data: {}".format(
                    y_label, x_label, z_label
                )
            ]
        )

        # Row 1: corner + x values
        corner_label = z_label
        rows.append([""] + list(xdata))

        # Row 2+: y value + z data per row
        for i, yval in enumerate(ydata):
            rows.append([yval] + list(zdata[i]))
        return rows


class BarDataStorage(PlotDataStorage):
    """Store bar-plot data (lower and upper bounds) for CSV export.

    Each registered bar records the bottom (lower) value and the top
    (upper) value of the bar.

    Example CSV layout::

        label, lower, upper
        Bar A, -10, 10
        Bar B, -25, 15
    """

    def __init__(self):
        super().__init__()
        self._bar_order = []

    def register_data(self, label, lower, upper):
        """Register a single bar's range.

        Args:
            label: Bar identifier / category name.
            lower: Lower (bottom) value of the bar.
            upper: Upper (top) value of the bar.
        """
        self._data[label] = {"lower": lower, "upper": upper}
        if label not in self._bar_order:
            self._bar_order.append(label)

    def _build_csv_data(self):
        rows = []
        y_label = self.ylabel if self.ylabel else "value"
        rows.append(
            ["label", "lower ({})".format(y_label), "upper ({})".format(y_label)]
        )
        for label in self._bar_order:
            entry = self._data[label]
            rows.append([label, entry["lower"], entry["upper"]])
        return rows


class BoxDataStorage(PlotDataStorage):
    """Store box-plot percentile data for CSV export.

    Each registered box records five percentile values: the user-defined
    lower whisker, 25th, 50th (median), 75th percentile, and the
    user-defined upper whisker.

    Example CSV layout::

        label, 5th percentile, 25th percentile, 50th percentile, 75th percentile, 95th percentile
        Box A, 1.2, 2.5, 3.1, 4.0, 5.3
    """

    def __init__(self):
        super().__init__()
        self._box_order = []

    def register_data(self, label, data, whiskers=None):
        """Register box-plot data from raw values.

        Computes the five percentile values (lower whisker, 25th, 50th,
        75th, upper whisker) from *data*.

        Args:
            label: Box identifier / category name.
            data: Array-like of raw data values.
            whiskers: Two-element list ``[lower_pct, upper_pct]`` defining
                the whisker percentiles. Defaults to ``[5, 95]``.
        """
        if whiskers is None:
            whiskers = [5, 95]
        data = np.asarray(data).flatten()
        percentiles = np.percentile(data, [whiskers[0], 25, 50, 75, whiskers[1]])
        self._data[label] = {
            "percentiles": percentiles,
            "whiskers": whiskers,
        }
        if label not in self._box_order:
            self._box_order.append(label)

    def _build_csv_data(self):
        rows = []
        # Use whisker values from first entry for column headers
        first = self._data[self._box_order[0]] if self._box_order else None
        if first is not None:
            w = first["whiskers"]
        else:
            w = [5, 95]
        y_label = self.ylabel if self.ylabel else "value"
        rows.append(
            [
                "label ({})".format(y_label),
                "{}th percentile".format(w[0]),
                "25th percentile",
                "50th percentile",
                "75th percentile",
                "{}th percentile".format(w[1]),
            ]
        )
        for label in self._box_order:
            entry = self._data[label]
            pcts = entry["percentiles"]
            rows.append([label] + list(pcts))
        return rows
