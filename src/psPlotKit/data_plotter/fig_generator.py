import csv
import yaml
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patheffects as PathEffects
import numpy as np
import sigfig
from decimal import Decimal
import matplotlib.ticker as ticker
from matplotlib.colors import LogNorm, NoNorm
import scipy
from scipy.interpolate import (
    griddata,
    RegularGridInterpolator,
    LinearNDInterpolator,
    CloughTocher2DInterpolator,
    NearestNDInterpolator,
    # RBFInterpolator,
)

from psPlotKit.util.logger import define_logger
from psPlotKit.data_plotter.plot_data_storage import (
    LineDataStorage,
    ErrorBarDataStorage,
    MapDataStorage,
    BarDataStorage,
    BoxDataStorage,
)
from matplotlib.colors import ListedColormap
import math
import copy
from matplotlib import cm

_logger = define_logger(__name__, "FigureGenerator", level="INFO")


class FigureGenerator:
    """Matplotlib wrapper for generating publication-quality figures.

    Provides methods for line, bar, scatter, box, area, and map/contour plots
    with automatic color cycling, data logging, and CSV export.
    """

    def __init__(
        self,
        font_size=10,
        label_size=12,
        colormap="qualitative_a",
        save_location="",
        file_name="figure",
        figure_description="Figure generated with AnalysisWaterTAP tools",
        svg_font_setting="none",
        save_data=False,
        **kwargs,
    ):
        """Initialize figure generator with default styling and color settings.

        Args:
            font_size: Base font size for text elements.
            label_size: Font size for axis labels.
            colormap: Name of the colormap to use for plot colors.
            save_location: Directory path for saving figures.
            file_name: Default file name for saved figures.
            figure_description: Description included in exported CSV files.
            svg_font_setting: SVG font type setting ('none' or 'path').
            save_data: If True, automatically create a data storage object
                on first plot call and export plotted data to CSV on save.
        """
        self.colorMaps = {
            "qualitative_a": [
                "#a6cee3",
                "#1f78b4",
                "#b2df8a",
                "#33a02c",
                "#fb9a99",
                "#e31a1c",
                "#fdbf6f",
                "#ff7f00",
                "#cab2d6",
                "#6a3d9a",
                "#ffff99",
                "#b15928",
            ],
            "qualitative_b": [
                "#8dd3c7",
                "#ffffb3",
                "#bebada",
                "#fb8072",
                "#80b1d3",
                "#fdb462",
                "#b3de69",
                "#fccde5",
                "#d9d9d9",
                "#bc80bd",
                "#ccebc5",
                "#ffed6f",
            ],
            "color_map": "viridis",
        }
        self.current_color_index = [0]

        self.set_default_figure_settings(
            font_size=font_size,
            label_size=label_size,
            svg_font_setting=svg_font_setting,
        )
        self.colormaps = colormap
        self.map_mode = False
        self.contour_mode = False
        self.box_mode = False
        self.map_x_width = None
        self.map_y_width = None
        self.plotted_data = {}
        self.save_data = save_data
        self.data_storage = None
        self.save_location = save_location
        self.file_name = file_name
        self.figure_description = figure_description
        self.twinx, self.twiny = False, False

    def _init_data_storage(self, storage_class):
        """Lazily initialise ``data_storage`` on first plot call.

        If *save_data* is ``True`` and no storage object exists yet, create
        one of *storage_class*.  If a storage of a different type already
        exists, log a warning and leave it unchanged so that the first
        plot type wins.

        Args:
            storage_class: One of the ``PlotDataStorage`` subclasses.
        """
        if not self.save_data:
            return
        if self.data_storage is None:
            self.data_storage = storage_class()
        elif not isinstance(self.data_storage, storage_class):
            _logger.warning(
                "data_storage is already a {}, ignoring request for {}".format(
                    type(self.data_storage).__name__, storage_class.__name__
                )
            )

    def gen_colormap(
        self, num_samples=10, vmin=0, vmax=1, map_name="viridis", return_map=False
    ):
        """Generate a colormap with a specified number of discrete color samples.

        Args:
            num_samples: Number of discrete colors to sample.
            vmin: Minimum value for scalar mapping normalization.
            vmax: Maximum value for scalar mapping normalization.
            map_name: Name of the matplotlib colormap.
            return_map: If True, return colors and ScalarMappable tuple.

        Returns:
            Colors and ScalarMappable tuple if return_map, else the colormap object.
        """
        map_object = matplotlib.colormaps.get_cmap(map_name)
        colors = map_object(list(range(num_samples)))
        self.colorMaps[map_name] = colors
        self.colormaps = map_name
        if return_map:
            return colors, cm.ScalarMappable(
                norm=matplotlib.colors.Normalize(vmin, vmax), cmap=map_object
            )
        else:
            return map_object

    def init_figure(
        self,
        width=3.25,
        height=3.25,
        dpi=150,
        nrows=1,
        ncols=1,
        sharex=False,
        sharey=False,
        twinx=False,
        twiny=False,
        grid=None,
        subplot_adjust=None,
        projection=None,
        **kwargs,
    ):
        """Initialize a matplotlib figure and axes.

        Args:
            width: Figure width in inches.
            height: Figure height in inches.
            dpi: Figure resolution in dots per inch.
            nrows: Number of subplot rows.
            ncols: Number of subplot columns.
            sharex: Whether subplots share the x-axis.
            sharey: Whether subplots share the y-axis.
            twinx: If True, create a twin x-axis.
            twiny: If True, create a twin y-axis.
            grid: If set, overrides ncols and enables shared y-axis.
            subplot_adjust: Horizontal spacing between subplots.
            projection: Axes projection type (e.g., '3d').
        """
        if grid is not None:
            sharey = True
            ncols = grid
        self.projection = projection
        if projection == None:
            self.mode_3d = False
            self.fig, self.ax = plt.subplots(
                nrows,
                ncols,
                sharex=sharex,
                sharey=sharey,
            )
        else:
            self.mode_3d = True
            self.projection = projection
            self.fig, self.ax = plt.subplots(
                nrows,
                ncols,
                sharex=sharex,
                sharey=sharey,
                subplot_kw={"projection": projection},
            )
        self.idx_totals = (nrows, ncols)
        self.sharex = sharex
        self.sharey = sharey
        if nrows == 1 and ncols == 1:
            self.ax = [self.ax]
        elif nrows > 1 and ncols > 1:
            self.current_color_index = np.zeros((nrows, ncols))
        else:
            self.current_color_index = []
            for ax in self.ax:
                self.current_color_index.append(0)
        if twinx:
            self.ax = [self.ax[0], self.ax[0].twiny()]
            self.twinx = True
        if twiny:
            self.ax = [self.ax[0], self.ax[0].twinx()]
            self.twiny = True
        if subplot_adjust is not None:
            self.fig.subplots_adjust(wspace=subplot_adjust)
        self.fig.set_dpi(dpi)
        self.fig.set_size_inches(width, height, forward=True)

    def get_color(self, ax, val_update=0):
        """Get the current color index for the given axis and optionally advance it.

        Args:
            ax: Axis index or (row, col) tuple for multi-dimensional subplots.
            val_update: Amount to advance the color index after retrieval.

        Returns:
            Integer color index into the current colormap.
        """
        if self.idx_totals[0] > 1 and self.idx_totals[1] > 1:
            self.current_color_index[ax[0]][ax[1]] += val_update
            return int(self.current_color_index[ax[0]][ax[1]])
        else:
            self.current_color_index[ax] += val_update
            return int(self.current_color_index[ax])

    def plot_bar(
        self,
        x_pos,
        x_value,
        xerr=None,
        yerr=None,
        bottom=None,
        width=0.2,
        edgecolor="black",
        color=None,
        align="center",
        ax_idx=0,
        hatch=None,
        label=None,
        vertical=True,
        linewidth=1,
        save_label=None,
        log_data=True,
        zorder=4,
        ecolor="black",
        capsize=4,
        **kwargs,
    ):
        """Plot a bar (vertical or horizontal) on the figure.

        Args:
            x_pos: Position(s) of the bar(s) along the category axis.
            x_value: Height(s) or width(s) of the bar(s).
            xerr: Error bar sizes in the x direction.
            yerr: Error bar sizes in the y direction.
            bottom: Starting position for stacked bars.
            width: Bar width (or height for horizontal bars).
            color: Bar fill color; auto-selected from colormap if None.
            ax_idx: Axis index to plot on.
            label: Legend label.
            vertical: If True, plot vertical bars; otherwise horizontal.
            save_label: Key for storing plotted data; defaults to label.
            log_data: If True, store plotted data for CSV export.
        """
        self.box_mode = True
        if color is None:
            color = self.colorMaps[self.colormaps][self.get_color(ax_idx)]
            self.get_color(ax_idx, 1)
        elif isinstance(color, int):
            color = self.colorMaps[self.colormaps][color]

        if vertical:
            self.get_axis(ax_idx).bar(
                x_pos,
                x_value,
                xerr=xerr,
                yerr=yerr,
                bottom=bottom,
                width=width,
                edgecolor=edgecolor,
                linewidth=linewidth,
                facecolor=color,
                align=align,
                hatch=hatch,
                label=label,
                zorder=zorder,
                ecolor=ecolor,
                capsize=capsize,
            )
        else:
            self.get_axis(ax_idx).barh(
                x_pos,
                x_value,
                xerr=xerr,
                yerr=yerr,
                left=bottom,
                height=width,
                edgecolor=edgecolor,
                linewidth=linewidth,
                facecolor=color,
                align=align,
                hatch=hatch,
                label=label,
                zorder=zorder,
                ecolor=ecolor,
                capsize=capsize,
            )
        if log_data:
            if save_label is None:
                save_label = label
            try:
                right_val = x_value + bottom
            except (TypeError, ValueError):
                right_val = None
            self._init_data_storage(BarDataStorage)
            if self.data_storage is not None and isinstance(
                self.data_storage, BarDataStorage
            ):
                self.data_storage.register_data(
                    save_label if save_label else str(x_pos),
                    bottom if bottom is not None else 0,
                    right_val if right_val is not None else x_value,
                )

    def plot_area(
        self,
        xdata=None,
        ydata=None,
        x2data=None,
        y2data=None,
        color=None,
        edgecolor="black",
        ax_idx=0,
        zorder=4,
        linewidth=1,
        label=None,
        hatch=None,
        clip_on=True,
        save_label=None,
        alpha=1,
        **kwargs,
    ):
        """Plot a filled area between curves.

        Args:
            xdata: X-coordinates for the boundary.
            ydata: Y-coordinates for the primary boundary.
            x2data: Second x-boundary for horizontal fill (fill_betweenx).
            y2data: Second y-boundary for vertical fill (fill_between).
            color: Fill color; auto-selected from colormap if None.
            edgecolor: Color of the area edges.
            ax_idx: Axis index to plot on.
            label: Legend label.
            save_label: Key for storing plotted data; defaults to label.
            alpha: Fill transparency (0-1).
        """
        if color is None:
            color = self.colorMaps[self.colormaps][self.get_color(ax_idx)]
            self.get_color(ax_idx, 1)
        elif isinstance(color, int):
            color = self.colorMaps[self.colormaps][color]
        if y2data is not None:
            self.get_axis(ax_idx).fill_between(
                xdata,
                ydata,
                y2=y2data,
                color=color,
                edgecolor=edgecolor,
                hatch=hatch,
                linewidth=linewidth,
                zorder=zorder,
                clip_on=clip_on,
                alpha=alpha,
            )
        if x2data is not None:
            self.get_axis(ax_idx).fill_betweenx(
                ydata,
                xdata,
                x2=x2data,
                color=color,
                edgecolor=edgecolor,
                hatch=hatch,
                linewidth=linewidth,
                zorder=zorder,
                clip_on=clip_on,
                alpha=alpha,
            )
        if edgecolor is None:
            edgecolor = "black"
        self.get_axis(ax_idx).fill_between(
            [],
            [],
            y2=0,
            color=color,
            edgecolor=edgecolor,
            hatch=hatch,
            linewidth=1,
            label=label,
            zorder=zorder,
            clip_on=clip_on,
            alpha=alpha,
        )

    def plot_line(
        self,
        xdata=None,
        ydata=None,
        marker_overlay=None,
        marker_ranges=[1, 2, 3, 4, 5, 6],
        marker_types=["o", "d", "s", ">", "<"],
        marker_overlay_labels=None,
        label="",
        marker="",
        markersize=3,
        markerfacecolor="white",
        ls="-",
        lw=1.5,
        color=None,
        ax_idx=0,
        zorder=4,
        clip_on=True,
        save_label=None,
        sort_data=True,
        log_data=True,
        **kwargs,
    ):
        """Plot a line with optional marker overlays.

        Args:
            xdata: X-coordinates.
            ydata: Y-coordinates.
            marker_overlay: Data array for assigning different markers to segments.
            marker_ranges: Boundaries for marker overlay binning.
            marker_types: Marker styles for each overlay bin.
            marker_overlay_labels: Labels for each marker overlay segment.
            label: Legend label.
            color: Line color; auto-selected from colormap if None.
            ax_idx: Axis index to plot on.
            sort_data: If True, sort data by x values before plotting.
            log_data: If True, store plotted data for CSV export.
        """
        if color is None:
            color = self.colorMaps[self.colormaps][self.get_color(ax_idx)]
            self.get_color(ax_idx, 1)
        elif isinstance(color, int):
            color = self.colorMaps[self.colormaps][color]
        if sort_data and len(xdata) > 2:
            sort_idx = np.argsort(xdata)
            xdata = np.array(xdata)[sort_idx]
            ydata = np.array(ydata)[sort_idx]
        if self.map_mode:
            try:
                xdata = self.map_func_x(xdata)
                ydata = self.map_func_y(ydata)
            except (AttributeError, TypeError):
                _logger.warning("No map functions available, using raw data")
        if marker_overlay is not None:
            self.get_axis(ax_idx).plot(
                xdata,
                ydata,
                label=label,
                marker="",
                markerfacecolor=markerfacecolor,
                color=color,
                lw=lw,
                ls=ls,
                clip_on=clip_on,
                zorder=zorder,
                markersize=markersize,
            )
            for i, k in enumerate(marker_ranges[1:]):
                plot_range = np.where(
                    (marker_overlay < k) & (marker_overlay >= marker_ranges[i])
                )[0]

                if len(plot_range) > 0:
                    if marker_overlay_labels == None:
                        label = label
                    else:
                        label = marker_overlay_labels[i]
                    self.get_axis(ax_idx).plot(
                        xdata[plot_range],
                        ydata[plot_range],
                        label=label,
                        marker=marker_types[i],
                        markerfacecolor=markerfacecolor,
                        color=color,
                        lw=lw,
                        ls="",
                        clip_on=clip_on,
                        zorder=zorder + 1,
                        markersize=markersize,
                    )
        else:
            self.get_axis(ax_idx).plot(
                xdata,
                ydata,
                label=label,
                marker=marker,
                markerfacecolor=markerfacecolor,
                color=color,
                lw=lw,
                ls=ls,
                clip_on=clip_on,
                zorder=zorder,
                markersize=markersize,
            )
        if save_label is None:
            save_label = label
        if log_data:
            self._init_data_storage(LineDataStorage)
            if self.data_storage is not None and isinstance(
                self.data_storage, LineDataStorage
            ):
                self.data_storage.register_data(save_label, xdata, ydata)

    def plot_scatter(
        self,
        xdata=None,
        ydata=None,
        zdata=None,
        ylabel=None,
        label="",
        marker="o",
        marker_size=10,
        vmin=None,
        vmax=None,
        edgecolor=None,
        ls="-",
        ax_idx=0,
        markerfacecolor=None,
        zorder=4,
        color=None,
        plot_flat_scatter=None,  # use 'xyz' to plot all
        zs=[0, 0, 0],
        log_data=True,
        save_label=None,
        digitize_levels=None,
        **kwargs,
    ):
        """Plot a scatter plot, optionally with color-mapped z-data.

        Args:
            xdata: X-coordinates.
            ydata: Y-coordinates.
            zdata: Z-data for color mapping or 3D scatter.
            ylabel: Y-axis label used as fallback save key.
            label: Legend label.
            marker: Marker style.
            marker_size: Marker size in points squared.
            vmin: Minimum value for color normalization.
            vmax: Maximum value for color normalization.
            color: Marker color; auto-selected if None and no zdata.
            plot_flat_scatter: Axes string ('xyz') for 3D flat projections.
            log_data: If True, store plotted data for CSV export.
            save_label: Key for storing plotted data.
            digitize_levels: Levels for discretizing zdata colors.
        """
        if self.projection == None:
            if zdata is None:
                if color is None:
                    color = self.colorMaps[self.colormaps][self.get_color(ax_idx)]
                    self.get_color(ax_idx, 1)
            else:
                if digitize_levels is not None:
                    zdata = self.digitize_map(zdata, digitize_levels)

                color = zdata

            self.colorFig = self.get_axis(ax_idx).scatter(
                xdata,
                ydata,
                c=color,
                cmap=self.colorMaps["color_map"],
                label=label,
                s=marker_size,
                ls=ls,
                facecolor=markerfacecolor,
                edgecolors=edgecolor,
                vmin=vmin,
                vmax=vmax,
                zorder=zorder,
                marker=marker,
            )
        elif self.projection == "3d":
            if color is None:
                color = self.colorMaps[self.colormaps][self.get_color(ax_idx)]
                self.get_color(ax_idx, 1)
            if plot_flat_scatter is None:
                self.colorFig = self.get_axis(ax_idx).scatter(
                    xdata,
                    ydata,
                    zdata,
                    c=color,
                    cmap=self.colorMaps["color_map"],
                    label=label,
                    s=marker_size,
                    ls=ls,
                    facecolors=markerfacecolor,
                    vmin=vmin,
                    vmax=vmax,
                    zorder=zorder,
                    marker=marker,
                )
            else:
                if "z" in plot_flat_scatter:
                    self.get_axis(ax_idx).scatter(
                        xdata,
                        ydata,
                        zs=zs[2],
                        c=color,
                        zdir="z",
                        cmap=self.colorMaps["color_map"],
                        label=label,
                        s=marker_size,
                        ls=ls,
                        facecolors=markerfacecolor,
                        vmin=vmin,
                        vmax=vmax,
                        zorder=zorder,
                        marker=marker,
                    )
                if "y" in plot_flat_scatter:
                    self.get_axis(ax_idx).scatter(
                        xdata,
                        zdata,
                        zs=zs[1],
                        c=color,
                        zdir="y",
                        cmap=self.colorMaps["color_map"],
                        label=label,
                        s=marker_size,
                        ls=ls,
                        facecolors=markerfacecolor,
                        vmin=vmin,
                        vmax=vmax,
                        zorder=zorder,
                        marker=marker,
                    )
                if "x" in plot_flat_scatter:
                    self.get_axis(ax_idx).scatter(
                        ydata,
                        zdata,
                        zs=zs[0],
                        c=color,
                        zdir="x",
                        cmap=self.colorMaps["color_map"],
                        label=label,
                        s=marker_size,
                        ls=ls,
                        facecolors=markerfacecolor,
                        vmin=vmin,
                        vmax=vmax,
                        zorder=zorder,
                        marker=marker,
                    )
        if log_data:
            if save_label is None and label != "":
                save_label = label
            elif save_label is None and ylabel != None:
                save_label = ylabel
            self._init_data_storage(LineDataStorage)
            if self.data_storage is not None and isinstance(
                self.data_storage, LineDataStorage
            ):
                self.data_storage.register_data(save_label, xdata, ydata)

    def plot_errorbar(
        self,
        xdata=None,
        ydata=None,
        xerr=None,
        yerr=None,
        label="",
        marker="o",
        markersize=10,
        vmin=None,
        vmax=None,
        ecolor="black",
        elinewidth=1,
        capsize=2,
        capthick=1,
        ls="-",
        ax_idx=0,
        markerfacecolor="white",
        color=None,
        log_data=True,
        save_label=None,
        zorder=1,
    ):
        """Plot data points with error bars.

        Args:
            xdata: X-coordinates.
            ydata: Y-coordinates.
            xerr: Error values in the x direction.
            yerr: Error values in the y direction.
            label: Legend label.
            marker: Marker style.
            markersize: Marker size in points.
            ecolor: Error bar color.
            elinewidth: Error bar line width.
            capsize: Error bar cap size.
            capthick: Error bar cap thickness.
            color: Data point color; auto-selected from colormap if None.
            log_data: If True, store plotted data for CSV export.
            save_label: Key for storing plotted data; defaults to label.
        """
        if color is None:
            color = self.colorMaps[self.colormaps][self.get_color(ax_idx)]
            self.get_color(ax_idx, 1)
        self.colorFig = self.get_axis(ax_idx).errorbar(
            xdata,
            ydata,
            xerr=xerr,
            yerr=yerr,
            color=color,
            ecolor=ecolor,
            marker=marker,
            markersize=markersize,
            label=label,
            markerfacecolor=markerfacecolor,
            elinewidth=elinewidth,
            capsize=capsize,
            capthick=capthick,
            ls=ls,
            vmin=vmin,
            vmax=vmax,
            zorder=zorder,
        )

        if save_label is None:
            save_label = label
        if log_data:
            self._init_data_storage(ErrorBarDataStorage)
            if self.data_storage is not None and isinstance(
                self.data_storage, ErrorBarDataStorage
            ):
                self.data_storage.register_data(
                    save_label, xdata, ydata, xerr=xerr, yerr=yerr
                )

    def plot_cdf(
        self, data, color=None, num_bins=100, label="", ls="-", lw=2, ax_idx=0
    ):
        """Plot a cumulative distribution function.

        Args:
            data: Input data array.
            color: Line color; auto-selected from colormap if None.
            num_bins: Number of histogram bins.
            label: Legend label.

        Returns:
            Tuple of (bin_edges, normalized_cdf).
        """
        bins = np.linspace(min(data), max(data), num_bins)
        counts, binedges = np.histogram(data, bins=bins)
        cdf = np.cumsum(counts)
        if color is None:
            color = self.colorMaps[self.colormaps][self.get_color(ax_idx)]
            self.get_color(ax_idx, 1)
        cdf = [0] + list(cdf)
        self.get_axis(ax_idx).plot(
            binedges, cdf / cdf[-1], color=color, label=label, ls=ls, lw=lw
        )
        return binedges, cdf / cdf[-1]

    def plot_hist(
        self,
        data,
        color=None,
        num_bins=100,
        label="",
        ls="-",
        lw=2,
        ax_idx=0,
        plot_line=True,
        norm=True,
    ):
        """Plot a histogram, optionally as a line plot.

        Args:
            data: Input data array.
            color: Bar/line color; auto-selected from colormap if None.
            num_bins: Number of histogram bins.
            label: Legend label.
            plot_line: If True, plot as a line; otherwise as a standard histogram.
            norm: If True, normalize counts by the maximum value.
        """
        if color is None:
            color = self.colorMaps[self.colormaps][self.get_color(ax_idx)]
            self.get_color(ax_idx, 1)
        if plot_line:
            bins = np.linspace(min(data), max(data), num_bins)
            counts, binedges = np.histogram(data, bins=bins)
            if norm:
                norm_sum = np.max(counts)
                counts = counts / norm_sum
            self.plot_line(binedges[1:], counts, color=color, label=label)
        else:
            self.get_axis(ax_idx).hist(
                data,
                bins=num_bins,
                color=color,
                label=label,
            )

    def plot_box(
        self,
        position,
        data,
        whiskers=[5, 95],
        width=1,
        vertical=False,
        showfliers=False,
        ax_idx=0,
        color=None,
        hatch=None,
        label=None,
        save_label=None,
        log_data=True,
    ):
        """Plot a box-and-whisker diagram.

        Args:
            position: Position of the box along the category axis.
            data: Data array for computing box statistics.
            whiskers: Percentiles for whisker extent (e.g., [5, 95]).
            width: Box width.
            vertical: If True, plot vertical boxes.
            showfliers: If True, show outlier points.
            ax_idx: Axis index to plot on.
            color: Box fill color; auto-selected from colormap if None.
            hatch: Hatch pattern for the box fill.
            label: Legend label.
            save_label: Key for storing plotted data.
            log_data: If True, store plotted data for CSV export.
        """
        self.box_mode = True
        medianprops = {"color": "black", "linewidth": 1}
        if color is None:
            color = self.colorMaps[self.colormaps][self.get_color(ax_idx)]
            self.get_color(ax_idx, 1)
        elif isinstance(color, int):
            color = self.colorMaps[self.colormaps][color]
        self.get_axis(ax_idx).boxplot(
            data,
            positions=[position],
            vert=vertical,
            whis=whiskers,
            showfliers=showfliers,
            patch_artist=True,
            medianprops=medianprops,
            widths=width,
            boxprops=dict(facecolor=color, hatch=hatch, color="black"),
        )
        if label is not None:
            self.plot_bar([0], [0], color=color, hatch=hatch, label=label)

        if log_data:
            self.percentiles = np.percentile(
                data, [whiskers[0], 25, 50, 75, whiskers[1]]
            )
            self._init_data_storage(BoxDataStorage)
            if self.data_storage is not None and isinstance(
                self.data_storage, BoxDataStorage
            ):
                _box_label = (
                    save_label if save_label else label if label else str(position)
                )
                self.data_storage.register_data(_box_label, data, whiskers=whiskers)

    def build_map_data(
        self,
        x=None,
        y=None,
        z=None,
        x_uniqu=None,
        y_uniqu=None,
        x_decimals=8,
        y_decimals=8,
    ):
        """Build a 2D map array from scatter x, y, z data.

        Args:
            x: X-coordinate array.
            y: Y-coordinate array.
            z: Z-value array or 2D array.
            x_uniqu: Pre-computed unique x values.
            y_uniqu: Pre-computed unique y values.
            x_decimals: Decimal precision for rounding x values.
            y_decimals: Decimal precision for rounding y values.

        Returns:
            Tuple of (z_map, x_unique, y_unique).
        """
        x = x.round(decimals=x_decimals)
        y = y.round(decimals=y_decimals)
        if x_uniqu is None:
            x_uniqu = np.unique(x)
            y_uniqu = np.unique(y)
        z_map = np.empty((y_uniqu.shape[0], x_uniqu.shape[0]))
        z_map[:] = np.nan
        z = np.array(z)
        if z.ndim == 1:
            for i, iz in enumerate(z):
                ix = np.where(abs(x[i] - np.array(x_uniqu)) < 1e-5)[0]
                iy = np.where(abs(y[i] - np.array(y_uniqu)) < 1e-5)[0]
                z_map[iy, ix] = iz
        else:
            z_map = z
        return z_map, x_uniqu, y_uniqu

    def fix_nan_in_map(self, input_map):
        """Interpolate NaN values in a 2D map using linear griddata.

        Args:
            input_map: 2D numpy array potentially containing NaN values.

        Returns:
            2D numpy array with NaN values filled by interpolation.
        """
        x = np.array(range(input_map.shape[1]))
        y = np.array(range(input_map.shape[0]))
        mesh_grid_overall = np.array(np.meshgrid(x, y))
        mesh_grid = mesh_grid_overall.reshape((len(x) * len(y), 2))
        input_m = input_map.reshape(1, len(x) * len(y))[0]
        if any((input_m == input_m) == False):
            new_map = griddata(
                (
                    mesh_grid_overall[0][input_map == input_map],
                    mesh_grid_overall[1][input_map == input_map],
                ),
                input_m[input_m == input_m],
                (mesh_grid_overall[0], mesh_grid_overall[1]),
                method="linear",
            )
        else:
            new_map = input_map
        return new_map

    def search_sequence_numpy(self, arr, seq):
        # source  https://stackoverflow.com/questions/36522220/searching-a-sequence-in-a-numpy-array

        """Find sequence in an array using NumPy only.

        Parameters
        ----------
        arr    : input 1D array
        seq    : input 1D array

        Output
        ------
        Output : 1D Array of indices in the input array that satisfy the
        matching of input sequence in the input array.
        In case of no match, an empty list is returned.
        """

        # Store sizes of input array and sequence
        Na, Nseq = arr.size, seq.size

        # Range of sequence
        r_seq = np.arange(Nseq)

        # Create a 2D array of sliding indices across the entire length of input array.
        # Match up with the input sequence & get the matching starting indices.
        M = (arr[np.arange(Na - Nseq + 1)[:, None] + r_seq] == seq).all(1)

        # Get the range of those indices as final output
        if M.any() > 0:
            return np.where(np.convolve(M, np.ones((Nseq), dtype=int)) > 0)[0]
        else:
            return []  # No match found

    def plot_contour(
        self, ax, input_map, levels, colors="black", norm=None, mode="mod"
    ):
        """Plot contour lines on the given axis.

        Args:
            ax: Matplotlib axes object.
            input_map: 2D data array.
            levels: Contour level values.
            colors: Contour line colors.
            norm: Color normalization instance.
            mode: Contour mode identifier.

        Returns:
            Matplotlib ContourSet object.
        """
        x = np.array(range(input_map.shape[1]))
        y = np.array(range(input_map.shape[0]))

        xx, yy = np.array(np.meshgrid(x, y))
        return ax.contour(
            xx, yy, input_map, levels, colors=colors, norm=norm, zlevel=12
        )

    def plot_linear_contours(self, ax, input_map, x, y, levels, upscale):
        """Plot contour lines using linear polynomial fits.

        Args:
            ax: Matplotlib axes object.
            input_map: 2D data array.
            x: X-axis data (overridden by computed values).
            y: Y-axis data (overridden by computed values).
            levels: Contour level values.
            upscale: Scale factor for axis coordinates.
        """
        x = np.array(range(input_map.shape[1])) * upscale / input_map.shape[1]
        y = np.array(range(input_map.shape[0])) * upscale / input_map.shape[0]

        xx, yy = np.array(np.meshgrid(x, y))
        for l in levels:
            temp_map = np.zeros(input_map.shape)
            temp_map[input_map == l] = 1
            temp_map[input_map > l] = 2
            loc_idxs = self.search_sequence_numpy(temp_map.flatten(), np.array([1, 2]))
            x_vals = xx.flatten()[loc_idxs]
            y_vals = yy.flatten()[loc_idxs]
            if len(x_vals) > 2:
                fit = np.polyfit(x_vals, y_vals, deg=2)
                xinterp = np.linspace(min(x), max(x), 100)
                yinterp = np.poly1d(fit)(xinterp)
                ax.plot(xinterp, yinterp, color="black", lw=1)

    def plot_contourf(
        self,
        ax,
        input_map,
        levels,
        colors=None,
        extend=None,
        extend_colors=None,
        norm=None,
    ):
        """Plot filled contours on the given axis.

        Args:
            ax: Matplotlib axes object.
            input_map: 2D data array.
            levels: Contour level values.
            colors: Explicit fill colors; uses colormap if None.
            extend: Extend coloring beyond levels ('min', 'max', or 'both').
            extend_colors: Colors for extended regions.
            norm: Color normalization instance.

        Returns:
            Matplotlib ContourSet object.
        """
        x = np.array(range(input_map.shape[1]))
        y = np.array(range(input_map.shape[0]))
        xx, yy = np.array(np.meshgrid(x, y))

        if colors is None:
            cmap = self.colorMaps["color_map"]
        else:
            cmap = None

        cs = ax.contourf(
            xx,
            yy,
            input_map,
            levels,
            colors=colors,
            cmap=cmap,
            extend=extend,
            norm=norm,
        )
        if extend == "max":
            cs.cmap.set_over(extend_colors)
        if extend == "min":
            cs.cmap.set_under(extend_colors)
        if extend == "both":
            cs.cmap.set_over(extend_colors[0])
            cs.cmap.set_under(extend_colors[1])
        cs.changed()
        return cs

    def digitize_map(self, map_data, levels, colors):
        """Discretize map data into level bins and assign colormap colors.

        Args:
            map_data: Data array to digitize.
            levels: Bin boundary values.
            colors: Colors for each bin; auto-generated from colormap if None.

        Returns:
            Tuple of (vmin, vmax) for the digitized data range.
        """
        for i, lu in enumerate(levels[1:]):
            lb, ub = levels[i], levels[i + 1]
            average_level = i
            if len(map_data.shape) == 1:
                idx = np.where((map_data < ub) & (map_data > lb))[0]
                map_data[idx] = average_level
            else:
                for m in map_data:
                    idx = np.where((m < ub) & (m > lb))[0]
                    m[idx] = average_level
        if colors is None:
            _colors = []
            for l, _ in enumerate(levels[1:]):
                _colors.append(
                    matplotlib.colormaps.get_cmap(self.colorMaps["color_map"])(
                        l / (len(levels) - 1)
                    )
                )
        else:
            _colors = colors
        self.colorMaps["color_map"] = ListedColormap(_colors)

        self.digitized = True
        return 0, i + 1

    def plot_map(
        self,
        xdata=None,
        ydata=None,
        zdata=None,
        zoverlay=None,
        vmin=None,
        vmax=None,
        aspect="auto",
        text=True,
        text_color="auto",
        textfontsize=6,
        sig_figs_text="auto",
        auto_sig_0_1=2,
        auto_sig_1_10=1,
        auto_sig_10_inf=0,
        ax_idx=0,
        build_map=True,
        zscale="norm",
        fix_nans=False,
        label="map",
        digitize_levels=None,
        digitize_colors=None,
        unique_x_decimals=5,
        unique_y_decimals=5,
        log_data=True,
        **kwargs,
    ):
        """Plot a 2D heatmap/image with optional text annotations.

        Args:
            xdata: X-coordinates.
            ydata: Y-coordinates.
            zdata: Z-values for color mapping.
            zoverlay: Optional overlay z-data for additional annotations.
            vmin: Minimum color scale value.
            vmax: Maximum color scale value.
            aspect: Axes aspect ratio.
            text: If True, annotate cells with values (for maps < 200 cells).
            text_color: Cell text color; 'auto' selects based on value.
            textfontsize: Font size for cell text.
            sig_figs_text: Number of significant figures for cell text.
            ax_idx: Axis index to plot on.
            build_map: If True, build map from scatter data; else use zdata directly.
            zscale: Color scale ('norm' or 'log').
            fix_nans: If True, interpolate NaN values in the map.
            label: Label for the map data.
            digitize_levels: Levels for discretizing the color map.
            digitize_colors: Colors for discretized levels.
        """
        self.map_mode = True
        datax, datay = None, None
        if build_map:
            map_data, datax, datay = self.build_map_data(
                xdata,
                ydata,
                zdata,
                x_decimals=unique_x_decimals,
                y_decimals=unique_y_decimals,
            )
            if zoverlay is not None:
                (
                    overlay_map,
                    _,
                    _,
                ) = self.build_map_data(xdata, ydata, zoverlay)

            else:
                overlay_map = zoverlay
            if fix_nans:
                map_data = self.fix_nan_in_map(map_data)
        else:
            map_data = np.array(zdata)
            datax, datay = xdata, ydata
        self.map_x_width = map_data.shape[1]
        self.map_y_width = map_data.shape[0]
        if datax is None:
            datax = list(range(self.map_x_width))
        if datay is None:
            datay = list(range(self.map_y_width))
        if vmin is None and vmax is None:
            vmin = np.nanmin(map_data)
            vmax = np.nanmax(map_data)
        if digitize_levels is not None:
            vmin, vmax = self.digitize_map(map_data, digitize_levels, digitize_colors)

        if zscale == "log":
            norm = LogNorm(vmin=vmin, vmax=vmax)
        else:
            norm = None

        if norm != None:
            vmin = None
            vmax = None
        self.colorFig = self.get_axis(ax_idx).imshow(
            map_data,
            vmin=vmin,
            vmax=vmax,
            cmap=self.colorMaps["color_map"],
            aspect=aspect,
            origin="upper",
            norm=norm,
        )
        if text and map_data.size < 200:
            for r, row in enumerate(map_data):
                for c, value in enumerate(row):
                    if value < ((vmax - vmin) / 2 + vmin):
                        text_color = "white"
                    else:
                        text_color = "black"
                    if str(value) != "nan":
                        if sig_figs_text == "auto":
                            if abs(value) >= 10:
                                sig_figs = auto_sig_10_inf
                            elif abs(value) < 1:
                                sig_figs = auto_sig_0_1
                            else:
                                sig_figs = auto_sig_1_10
                        else:
                            sig_figs = sig_figs_text
                        self.get_axis(ax_idx).text(
                            c,
                            r,
                            self.format_value(value, sig_figs),
                            ha="center",
                            va="center",
                            color=text_color,
                            fontsize=textfontsize,
                        )
        self._init_data_storage(MapDataStorage)
        if self.data_storage is not None and isinstance(
            self.data_storage, MapDataStorage
        ):
            self.data_storage.register_data(datax, datay, map_data)

    def gen_map_function(self, axisdata, scale="linear"):
        """Generate a mapping function from data values to pixel indices.

        Args:
            axisdata: Array of axis data values.
            scale: Interpolation method ('linear', 'interp', or 'log').

        Returns:
            Callable mapping data values to pixel coordinates.
        """
        indexes = np.array(range(len(axisdata)))
        if scale == "interp":
            return scipy.interpolate.interp1d(
                axisdata[axisdata == axisdata],
                indexes[axisdata == axisdata],
                bounds_error=False,
                fill_value="extrapolate",
            )
        if scale == "linear":
            return np.poly1d(np.polyfit(axisdata, indexes, deg=1))
        if scale == "log":

            def log_func(x, a, b):
                return a * np.log(x) - b

            fit_params = scipy.optimize.curve_fit(log_func, axisdata, indexes)
            a, b = fit_params[0]
            return lambda x: a * np.log(x) - b

    def gen_minor_ticks(self, axisticks, strides=10):
        """Generate minor tick positions for a logarithmic axis.

        Args:
            axisticks: Array of major tick values.
            strides: Number of minor tick subdivisions per decade.

        Returns:
            List of minor tick positions (excluding major tick positions).
        """
        minor_ticks = []
        return_ticks = []
        log_vmin = math.log(min(axisticks)) / math.log(10)
        log_vmax = math.log(max(axisticks)) / math.log(10)

        numdec = math.floor(log_vmax) - math.ceil(log_vmin)

        for k in np.arange(log_vmin, log_vmax, 1):
            minor_ticks += list(np.linspace(1, 10, strides) * 10**k)
        for m in minor_ticks:
            if m not in axisticks:
                return_ticks.append(m)
        return return_ticks

    def set_axis_ticklabels(
        self,
        xticklabels=None,
        yticklabels=None,
        xticks=None,
        yticks=None,
        xlabel=None,
        ylabel=None,
        xlims=None,
        ylims=None,
        angle=45,
        rotate=False,
        ha=None,
        va=None,
        rotation_mode="anchor",
        fontsize=10,
        ax_idx=0,
        xformat=None,
        yformat=None,
        xlabelpad=None,
        ylabelpad=None,
        set_aspect="auto",
        xscale="interp",
        yscale="interp",
        **kwargs,
    ):
        """Set custom tick labels and positions for map or categorical axes.

        Args:
            xticklabels: Labels for x-axis ticks.
            yticklabels: Labels for y-axis ticks.
            xticks: Explicit x-axis tick positions.
            yticks: Explicit y-axis tick positions.
            xlabel: X-axis label text.
            ylabel: Y-axis label text.
            xlims: X-axis limits as (min, max).
            ylims: Y-axis limits as (min, max).
            angle: Tick label rotation angle.
            rotate: If True, rotate tick labels.
            fontsize: Tick label font size.
            ax_idx: Axis index to configure.
            xformat: Format specification for x tick labels.
            yformat: Format specification for y tick labels.
            xscale: Scale for x-axis map function ('interp', 'linear', 'log').
            yscale: Scale for y-axis map function ('interp', 'linear', 'log').
        """
        if xticklabels is not None:
            if rotate == False:
                angle = 0
                if ha is None:
                    ha = "center"
                if va is None:
                    va = "top"
            if ha is None:
                ha = "right"
            if va is None:
                va = "top"
            if self.map_mode:

                xdata = self.data_storage._data["x"]
                self.map_func_x = self.gen_map_function(xdata, xscale)
                if self.contour_mode:
                    offset_x = 0
                    offset_y = -1
                else:
                    offset_x = -0.5
                    offset_y = 0.5

                ticks = self.map_func_x(xticklabels)
                self.get_axis(ax_idx).set_xlim(offset_x, ticks[-1] + offset_y)
                self.get_axis(ax_idx).set_xticks(ticks)
                if xscale == "log":
                    minor_ticks = self.gen_minor_ticks(xticklabels)
                    self.get_axis(ax_idx).xaxis.set_minor_locator(
                        ticker.FixedLocator(self.map_func_x(minor_ticks))
                    )
            else:
                if xticks is None:
                    xticks = list(range(len(xticklabels)))
                if xlims is None:
                    self.get_axis(ax_idx).set_xlim(-0.5 + xticks[0], xticks[-1] + 0.5)
                else:
                    self.get_axis(ax_idx).set_xlim(xlims[0], xlims[1])
                self.get_axis(ax_idx).set_xticks(xticks)

            if xformat is not None:
                xticklabels = self.format_ticks(xticklabels, xformat)
            self.get_axis(ax_idx).set_xticklabels(
                xticklabels,
                rotation=angle,
                ha=ha,
                va=va,
                rotation_mode=rotation_mode,
                fontsize=fontsize,
            )

        if yticklabels is not None:
            if rotate == False:
                angle = 0
                ha = "right"
                va = "center"
            if ha is None:
                ha = "right"
            if va is None:
                va = "center"
            if self.map_mode:
                if self.contour_mode:
                    offset_x = 0
                    offset_y = -1
                else:
                    offset_x = -0.5
                    offset_y = 0.5
                ydata = self.data_storage._data["y"]
                self.map_func_y = self.gen_map_function(ydata, yscale)
                ticks = self.map_func_y(yticklabels)
                self.get_axis(ax_idx).set_ylim(
                    offset_x + ticks[0], ticks[-1] + offset_y
                )
                self.get_axis(ax_idx).set_yticks(ticks)
                if yscale == "log":
                    minor_ticks = self.gen_minor_ticks(yticklabels)
                    self.get_axis(ax_idx).yaxis.set_minor_locator(
                        ticker.FixedLocator(self.map_func_y(minor_ticks))
                    )
            else:
                if yticks is None:
                    yticks = list(range(len(yticklabels)))
                if ylims is None:
                    self.get_axis(ax_idx).set_ylim(-0.5 + yticks[0], yticks[-1] + 0.5)
                else:
                    self.get_axis(ax_idx).set_ylim(ylims[0], ylims[1])
                self.get_axis(ax_idx).set_yticks(yticks)
            if yformat is not None:
                yticklabels = self.format_ticks(yticklabels, yformat)
            self.get_axis(ax_idx).set_yticklabels(
                yticklabels,
                rotation=angle,
                ha=ha,
                va=va,
                rotation_mode=rotation_mode,
                fontsize=fontsize,
            )
        if xlabel is not None:
            self.get_axis(ax_idx).set_xlabel(xlabel, labelpad=xlabelpad)
            if self.data_storage is not None:
                self.data_storage.update_labels(xlabel=xlabel)
        if ylabel is not None:
            self.get_axis(ax_idx).set_ylabel(ylabel, labelpad=ylabelpad)
            if self.data_storage is not None:
                self.data_storage.update_labels(ylabel=ylabel)
        self.get_axis(ax_idx).set_aspect(set_aspect)

    def set_fig_label(
        self, xlabel=None, ylabel=None, x_pad=-0.04, y_pad=0.05, label_size=12
    ):
        """Set figure-level x and y labels outside the subplot area.

        Args:
            xlabel: Text for the figure x-label.
            ylabel: Text for the figure y-label.
            x_pad: Vertical position for the x-label.
            y_pad: Horizontal position for the y-label.
            label_size: Font size for the labels.
        """
        if xlabel is not None:
            self.fig.text(
                0.5,
                x_pad,
                xlabel,
                ha="center",
                va="center",
                color="black",
                fontsize=label_size,
            )
        if ylabel is not None:
            self.fig.text(
                y_pad,
                0.5,
                ylabel,
                ha="center",
                va="center",
                color="black",
                rotation=90,
                fontsize=label_size,
            )

    def auto_gen_lims(self, data_stream):
        """Compute min and max across all plotted data for a given data stream.

        Args:
            data_stream: Key name in plotted data dicts (e.g., 'datax', 'datay').

        Returns:
            Tuple of (min_value, max_value).
        """
        data = []
        for key in self.plotted_data.keys():
            if key != "xlabel" and key != "ylabel":
                if len(self.plotted_data[key]["datax"]) > 0:
                    data += list(self.plotted_data[key][data_stream])
        v_min = min(data)
        v_max = max(data)
        return v_min, v_max

    def set_axis(
        self,
        xlims=None,
        ylims=None,
        zlims=None,
        xlabel=None,
        ylabel=None,
        zlabel=None,
        xticks=None,
        yticks=None,
        zticks=None,
        default_xticks=5,
        default_yticks=5,
        ax_idx=0,
        xlabelpad=None,
        ylabelpad=None,
        zlabelpad=None,
        xlabelrotate=0,
        ylabelrotate=90,
        zlabelrotate=90,
        xscale=None,
        yscale=None,
        format_ticks=True,
        xformat="fixed",
        yformat="fixed",
        set_aspect="auto",
        xaxiscolor="black",
        yaxiscolor="black",
        **kwargs,
    ):
        """Configure axis limits, ticks, labels, scales, and colors.

        Args:
            xlims: X-axis limits as (min, max).
            ylims: Y-axis limits as (min, max).
            zlims: Z-axis limits for 3D plots.
            xlabel: X-axis label text.
            ylabel: Y-axis label text.
            zlabel: Z-axis label text for 3D plots.
            xticks: Explicit x-axis tick positions.
            yticks: Explicit y-axis tick positions.
            zticks: Explicit z-axis tick positions for 3D plots.
            default_xticks: Number of auto-generated x ticks.
            default_yticks: Number of auto-generated y ticks.
            ax_idx: Axis index to configure.
            xscale: X-axis scale type (e.g., 'log').
            yscale: Y-axis scale type (e.g., 'log').
            format_ticks: If True, apply tick formatting for log scales.
            xformat: X tick format type ('fixed', 'scalar', 'g', '10').
            yformat: Y tick format type ('fixed', 'scalar', 'g', '10').
            xaxiscolor: Color for x-axis elements.
            yaxiscolor: Color for y-axis elements.
        """
        if xlims is not None:
            self.get_axis(ax_idx).set_xlim(xlims[0], xlims[1])
            if xticks is None:
                if xscale == "log":
                    xticks = np.geomspace(xlims[0], xlims[1], default_xticks)
                else:
                    xticks = np.linspace(xlims[0], xlims[1], default_xticks)

        if xticks is not None:
            self.get_axis(ax_idx).set_xticks(np.array(xticks))
            if xlims is None:
                self.get_axis(ax_idx).set_xlim(xticks[0], xticks[-1])
        if ylims is not None:
            self.get_axis(ax_idx).set_ylim(ylims[0], ylims[1])

            if yticks is None:
                yticks = np.linspace(ylims[0], ylims[1], default_yticks)
        if yticks is not None:
            self.get_axis(ax_idx).set_yticks(yticks)
            if ylims is None:
                self.get_axis(ax_idx).set_ylim(yticks[0], yticks[-1])
        if zticks is not None and self.mode_3d:
            self.get_axis(ax_idx).set_zticks(zticks)
            if zlims is None:
                self.get_axis(ax_idx).set_zlim(zticks[0], zticks[-1])
        if yticks is None and ylims is None:
            try:
                ylims = self.auto_gen_lims("datay")
                yticks = np.linspace(ylims[0], ylims[1], default_yticks)
                self.get_axis(ax_idx).set_yticks(yticks)
                self.get_axis(ax_idx).set_ylim(yticks[0], yticks[-1])
            except (ValueError, KeyError):
                _logger.warning("Failed to auto-generate y-axis ticks")
        if xticks is None and xlims is None:
            try:
                xlims = self.auto_gen_lims("datax")
                xticks = np.linspace(xlims[0], xlims[1], default_xticks)
                self.get_axis(ax_idx).set_xticks(np.array(xticks))
                self.get_axis(ax_idx).set_xlim(xticks[0], xticks[-1])
            except (ValueError, KeyError):
                _logger.warning("Failed to auto-generate x-axis ticks")

        if xscale is not None:
            self.get_axis(ax_idx).set_xscale(xscale)
            if xformat == "fixed":
                self.get_axis(ax_idx).xaxis.set_major_locator(
                    ticker.FixedLocator(xticks)
                )
                self.get_axis(ax_idx).xaxis.set_major_formatter(
                    ticker.ScalarFormatter()
                )

                self.get_axis(ax_idx).xaxis.set_minor_locator(ticker.NullLocator())
                self.get_axis(ax_idx).xaxis.set_minor_formatter(ticker.NullFormatter())
            if xformat == "scalar":
                self.get_axis(ax_idx).xaxis.set_major_formatter(
                    ticker.ScalarFormatter()
                )
            if xformat == "g":
                self.get_axis(ax_idx).xaxis.set_major_formatter(
                    ticker.FuncFormatter(lambda x, _: "{:g}".format(x))
                )

            if xformat == "10":
                self.get_axis(ax_idx).xaxis.set_major_formatter(
                    ticker.FuncFormatter(
                        lambda x, pos: (
                            "{{:.{:1d}f}}".format(int(np.maximum(-np.log10(x), 0)))
                        ).format(x)
                    )
                )
            self.get_axis(ax_idx).xaxis.set_minor_locator(
                ticker.LogLocator(numticks=999, subs="auto")
            )
        if yscale is not None:
            self.get_axis(ax_idx).set_yscale(yscale)
            if yscale == "log" and format_ticks:
                if yformat == "fixed":
                    self.get_axis(ax_idx).yaxis.set_major_locator(
                        ticker.FixedLocator(yticks)
                    )
                    self.get_axis(ax_idx).yaxis.set_major_formatter(
                        ticker.ScalarFormatter()
                    )
                    self.get_axis(ax_idx).yaxis.set_minor_locator(ticker.NullLocator())
                    self.get_axis(ax_idx).yaxis.set_minor_formatter(
                        ticker.NullFormatter()
                    )
                if yformat == "scalar":
                    self.get_axis(ax_idx).yaxis.set_major_formatter(
                        ticker.ScalarFormatter()
                    )
                if yformat == "g":
                    self.get_axis(ax_idx).yaxis.set_major_formatter(
                        ticker.FuncFormatter(lambda y, _: "{:g}".format(y))
                    )
                if yformat == "10":
                    self.get_axis(ax_idx).yaxis.set_major_formatter(
                        ticker.FuncFormatter(
                            lambda y, pos: (
                                "{{:.{:1d}f}}".format(int(np.maximum(-np.log10(y), 0)))
                            ).format(y)
                        )
                    )
                self.get_axis(ax_idx).yaxis.set_minor_locator(
                    ticker.LogLocator(numticks=999, subs="auto")
                )
        if xlabel is not None:
            self.get_axis(ax_idx).set_xlabel(
                xlabel, labelpad=xlabelpad, rotation=xlabelrotate
            )
            if self.data_storage is not None:
                self.data_storage.update_labels(xlabel=xlabel)
        if ylabel is not None:
            self.get_axis(ax_idx).set_ylabel(
                ylabel, labelpad=ylabelpad, rotation=ylabelrotate
            )
            if self.data_storage is not None:
                self.data_storage.update_labels(ylabel=ylabel)
        if zlabel is not None and self.mode_3d:
            self.get_axis(ax_idx).set_zlabel(
                zlabel, labelpad=zlabelpad, rotation=zlabelrotate
            )
            if self.data_storage is not None:
                self.data_storage.update_labels(zlabel=zlabel)
        self.get_axis(ax_idx).set_aspect(set_aspect)
        if xaxiscolor is not None:
            self.get_axis(ax_idx).xaxis.label.set_color(xaxiscolor)
            self.get_axis(ax_idx).tick_params(axis="x", colors=xaxiscolor)
            if self.twinx and ax_idx == 1:
                self.get_axis(ax_idx).spines["top"].set_color(xaxiscolor)
            else:
                self.get_axis(ax_idx).spines["bottom"].set_color(xaxiscolor)
        if yaxiscolor is not None:
            self.get_axis(ax_idx).yaxis.label.set_color(yaxiscolor)
            self.get_axis(ax_idx).tick_params(axis="y", colors=yaxiscolor)
            if self.twiny and ax_idx == 1:
                self.get_axis(ax_idx).spines["right"].set_color(yaxiscolor)
            else:
                self.get_axis(ax_idx).spines["left"].set_color(yaxiscolor)

    def add_colorbar(
        self, zlabel, zticks=None, zformat=1, zlabelpad=17, cbar=None, **kwargs
    ):
        """Add a colorbar to the figure.

        Args:
            zlabel: Label for the colorbar axis.
            zticks: Tick positions on the colorbar.
            zformat: Decimal format for colorbar tick labels.
            zlabelpad: Label padding for the colorbar.
            cbar: Optional pre-existing ScalarMappable; uses self.colorFig if None.
        """
        if cbar == None:
            cfig = self.colorFig
        else:
            cfig = cbar
        self.fig.subplots_adjust(right=0.85)

        cbar_ax = self.fig.add_axes([0.855, 0.125, 0.025, 0.75])
        cbar = self.fig.colorbar(
            cfig,
            cax=cbar_ax,
        )
        if hasattr(self, "digitized") and self.digitized:
            cbar.set_ticks(list(range(len(zticks))))
        else:
            cbar.set_ticks(zticks)
        cbar.set_ticklabels(self.format_ticks(zticks, zformat))
        cbar.set_label(zlabel, rotation=-90, labelpad=zlabelpad)
        if self.data_storage is not None:
            self.data_storage.update_labels(zlabel=zlabel)

    def add_legend(
        self,
        loc="best",
        fontsize=9,
        ax_idx=-1,
        bbox_to_anchor=None,
        ncol=1,
        handlelength=1.2,
        reverse_legend=False,
        **kwargs,
    ):
        """Add a legend to the figure.

        Args:
            loc: Legend location string.
            fontsize: Legend font size.
            ax_idx: Axis index to attach the legend to.
            bbox_to_anchor: Bounding box anchor for legend positioning.
            ncol: Number of legend columns.
            reverse_legend: If True, reverse the order of legend entries.
        """
        handles, labels = self.get_axis(ax_idx).get_legend_handles_labels()
        if reverse_legend:
            handles, labels = handles[::-1], labels[::-1]
        self.get_axis(ax_idx).legend(
            handles,
            labels,
            frameon=False,
            loc=loc,
            ncol=ncol,
            prop={"size": fontsize},
            labelspacing=0.2,
            columnspacing=0.4,
            handlelength=1,
            handleheight=1,
            bbox_to_anchor=bbox_to_anchor,
        )

    def get_axis(self, idx):
        """Return the matplotlib axes object for the given index.

        Args:
            idx: Integer axis index or (row, col) tuple.

        Returns:
            Matplotlib Axes object.
        """
        if self.idx_totals[0] > 1 and self.idx_totals[1] > 1:
            return self.ax[idx[0], idx[1]]
        else:
            return self.ax[idx]

    def remove_ticks(self, ax_idx=0, y_axis=None, x_axis=None):
        """Hide tick marks and labels for the specified axes.

        Args:
            ax_idx: Axis index.
            y_axis: If True, hide y-axis ticks and labels.
            x_axis: If True, hide x-axis ticks and labels.
        """
        if y_axis is True:
            self.get_axis(ax_idx).axes.yaxis.set_visible(False)
        if x_axis is True:
            self.get_axis(ax_idx).axes.xaxis.set_visible(False)

    def format_value(self, value, decimals):
        """Format a numeric value to the specified number of decimal places.

        Args:
            value: Numeric value to format.
            decimals: Number of decimal places (0 returns integer string).

        Returns:
            Formatted string representation.
        """
        if decimals == 0:
            return str(int(round(value, 0)))
        else:
            return str(round(value, decimals))

    def format_ticks(self, ticks, decimals):
        """Format a list of tick values to the specified decimal places.

        Args:
            ticks: List of numeric tick values.
            decimals: Number of decimal places for formatting.

        Returns:
            List of formatted tick label strings.
        """
        return [self.format_value(tick, decimals) for tick in ticks]

    def save_fig(self, save_jpg=True, save_svg=True, name="output_fig"):
        """Save the figure as both JPG and SVG files.

        Args:
            name: Output file path without extension.
        """
        if name.endswith(".jpg") or name.endswith(".svg") or name.endswith(".png"):
            self.fig.savefig(name, dpi=300, bbox_inches="tight", pad_inches=0.1)
        else:
            if save_jpg:
                self.fig.savefig(
                    name + ".jpg", dpi=300, bbox_inches="tight", pad_inches=0.1
                )
            if save_svg:
                self.fig.savefig(
                    name + ".svg", dpi=300, bbox_inches="tight", pad_inches=0.1
                )

    def save(
        self, save_location=None, file_name=None, figure_description=None, data=None
    ):
        """Save the figure and export plotted data to CSV.

        Args:
            save_location: Override directory path for saving.
            file_name: Override file name for saving.
            figure_description: Override description for CSV export.
            data: If provided, save this data directly instead of plotted data.
        """
        if save_location is not None:
            self.save_location = save_location
        if file_name is not None:
            self.file_name = file_name
        if figure_description is not None:
            self.figure_description = None
        self.save_fig(self.save_location + "\\" + self.file_name)
        if self.data_storage is not None:
            self.data_storage.save(self.save_location + "\\" + self.file_name)
        if data is not None:
            self.save_csv(self.save_location + "\\" + self.file_name, data)

    def show(self):
        """Display the figure in an interactive window."""
        plt.show()

    def close(self):
        """Close the current figure and release its resources."""
        plt.close()

    def set_default_figure_settings(
        self, font_size=10, label_size=12, svg_font_setting="none"
    ):
        """Configure global matplotlib font, label, math text, and SVG settings.

        Sets font family to serif/Arial, configures label sizes, enables regular
        math text rendering, and sets SVG font type.

        Args:
            font_size: Base font size for text elements.
            label_size: Font size for axis labels.
            svg_font_setting: SVG font type setting ('none' or 'path').
        """
        default_font = {
            "family": "serif",
            "serif": "Arial",
            "weight": "normal",
            "size": font_size,
        }
        default_label_size = {
            "labelsize": label_size,
        }

        matplotlib.rc("font", **default_font)
        matplotlib.rc("axes", **default_label_size)

        default_math_text = {"mathtext.default": "regular"}
        plt.rcParams.update(default_math_text)
        plt.rcParams.update({"svg.fonttype": svg_font_setting})

    def remove_math_text(self, string):
        """Strip matplotlib math-text delimiters from a string, preserving literal dollars.

        Args:
            string: Input string potentially containing '$' delimiters.

        Returns:
            Cleaned string with math-text delimiters removed.
        """
        replaceUSD = False
        if "\$" in string:
            string = string.replace("\$", "USD")
            replaceUSD = True
        if "$" in string:
            string = string.replace("$", "")
        if replaceUSD:
            string = string.replace("USD", "$")
        return string

    def save_csv(self, file_name, data):
        """Write data rows to a CSV file.

        Args:
            file_name: Output file path (.csv extension added if missing).
            data: List of rows, where each row is a list of values.
        """
        if not file_name.endswith(".csv"):
            file_name += ".csv"
        save_name = file_name
        with open(save_name, "w", newline="") as csvfile:
            spamwriter = csv.writer(csvfile, delimiter=",")
            for k in data:
                spamwriter.writerow(k)
