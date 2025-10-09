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
from matplotlib.colors import ListedColormap
import math
import copy
from matplotlib import cm


class figureGenerator:
    def __init__(
        self,
        font_size=10,
        label_size=12,
        colormap="qualitative_a",
        save_location="",
        file_name="figure",
        figure_description="Figure generated with AnalysisWaterTAP tools",
        svg_font_setting="none",
        **kwargs,
    ):
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
        self.save_location = save_location
        self.file_name = file_name
        self.figure_description = figure_description
        self.twinx, self.twiny = False, False

    def gen_colormap(
        self, num_samples=10, vmin=0, vmax=1, map_name="viridis", return_map=False
    ):
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
        # Creat figure and axist to plot on
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
                # subplot_kw={"projection": projection},
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
        # Set figrue DPI
        if twinx:
            self.ax = [self.ax[0], self.ax[0].twiny()]
            self.twinx = True
        if twiny:
            self.ax = [self.ax[0], self.ax[0].twinx()]
            self.twiny = True
        if subplot_adjust is not None:
            self.fig.subplots_adjust(wspace=subplot_adjust)
        self.fig.set_dpi(dpi)
        # Set figure size
        self.fig.set_size_inches(width, height, forward=True)

    def get_color(self, ax, val_update=0):
        if self.idx_totals[0] > 1 and self.idx_totals[1] > 1:
            self.current_color_index[ax[0]][ax[1]] += val_update
            # print(self.current_color_index)
            return int(self.current_color_index[ax[0]][ax[1]])
        else:
            print(ax, self.current_color_index)
            self.current_color_index[ax] += val_update
            return int(self.current_color_index[ax])

    def plot_all_tables(
        self,
        table_data,
        type_data,
        sub_tables=[
            [
                "operating condition",
                ["Operating metrics", "Lower Limit", "Upper Limit"],
            ],
            ["cost metric", ["Cost metrics", "Lower Limit", "Upper Limit"]],
            [
                "performance metric",
                ["Performance metrics", "Lower Limit", "Upper Limit"],
            ],
        ],
        column_positions=[1.75, 2.125, 2.655],
    ):
        table_y_offset = 0
        ylims, xlims = table_data.shape
        ylims += len(sub_tables) * 2 - 2
        for st, sub_table in enumerate(sub_tables):
            table_type = sub_table[0]
            print(table_type, type_data)
            data_idxs = np.where(table_type == type_data)[0]
            print(data_idxs)
            self.plot_table(
                table_data[data_idxs],
                colLabels=sub_table[1],
                xlims=xlims,
                ylims=ylims,
                table_y_offset=table_y_offset,
                column_positions=column_positions,
            )
            table_y_offset += len(data_idxs) + 2
            print(table_y_offset)

    def plot_table(
        self,
        data,
        rowLabels=None,
        colLabels=None,
        types=None,
        column_positions=[1.75, 2.125, 2.655],
        xlims=None,
        ylims=None,
        table_y_offset=0,
    ):
        size = data.shape
        self.ax[-1].set_axis_off()

        def power_offset_adjust(strings):
            offset = 0
            for s in strings:
                if "^" in s:
                    offset = 0.175
                    break
            return offset

        if xlims is None:
            self.ax[-1].set_xlim(0, size[1])
        else:
            self.ax[-1].set_xlim(0, xlims)

        if ylims is None:
            self.ax[-1].set_ylim(size[0], 0)
        else:
            self.ax[-1].set_ylim(ylims, 0)
        global_offset = 0.225
        global_offset += power_offset_adjust(colLabels)

        for c, colLable in enumerate(colLabels):
            if c == 0:
                ha = "right"
            else:
                ha = "center"

            self.ax[-1].text(
                column_positions[c],
                0 + table_y_offset + global_offset,
                colLable,
                ha=ha,
                va="baseline",
                color="black",
                fontsize=12,
                fontstyle="italic",
            )

        self.ax[-1].plot(
            [0, size[1]],
            [1 - 0.5 + table_y_offset, 1 - 0.5 + table_y_offset],
            lw=1.5,
            color="black",
        )
        # global_offset+=0.1
        for d, data_row in enumerate(data):
            global_offset += power_offset_adjust(data_row)
            for r, val in enumerate(data_row):
                if r == 0:
                    ha = "right"
                else:
                    ha = "center"

                self.ax[-1].text(
                    column_positions[r],
                    d + 1 + table_y_offset + global_offset,
                    val,
                    ha=ha,
                    va="center",
                    color="black",
                    fontsize=11,
                )

    def generated_stats(
        self, parameters, data_manager, mask, percentiles=[5, 25, 50, 75, 95]
    ):
        output_dict = {}
        # print(parameters)
        for key in parameters:
            # print(key)
            data = data_manager.get_data_set(
                "sweep_params", parameters[key]["model_value"]
            )[mask]
            stats = np.percentile(data, percentiles)
            # print('STATS',data)
            output_dict[key] = {}
            output_dict[key]["model_value"] = parameters[key]["model_value"]
            for i, p in enumerate(percentiles):
                output_dict[key][str(p)] = stats[i]
        # print(output_dict)
        return output_dict

    def dict_to_table(self, dict, column_values, metadata_function=None, sigfigs=3):
        data = []
        types = []
        for key in dict:
            data.append([])
            for cv in column_values:
                if cv == "model_value":
                    if metadata_function is not None:
                        # print(dict[key][cv])
                        val = metadata_function(dict[key][cv])
                        types.append(metadata_function(dict[key][cv], type="type"))
                        conversion = metadata_function(
                            dict[key][cv], type="unit_conversion"
                        )
                else:
                    val = dict[key][cv]
                    if metadata_function is not None:
                        # print(val,conversion)
                        val = str(float(val) * float(conversion))
                        val = sigfig.round(val, sigfigs)
                        print(val)
                        if len(str(val)) > sigfigs * 2:
                            val = str(Decimal(val)).lower()
                        print(val)
                        if "e" in val:
                            power = str(int(val.split("e")[-1]))
                            val = val.split("e")[0] + "x10$^{" + power + "}$"
                        if val.split(".")[-1] == "0":
                            val = self.format_value(
                                float(val), len(val.split(".")[-1]) - 1
                            )
                data[-1].append(val)
        return np.array(data), np.array(types)

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
        zorder=4,
        ecolor="black",
        capsize=4,
        **kwargs,
    ):
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
                # elinewidth=elinewidth,
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
                # elinewidth=elinewidth,
                capsize=capsize,
            )
        if save_label is None:
            save_label = label
        try:
            right_val = x_value + bottom
        except:
            right_val = None
        self.plotted_data.update({save_label: {"box_data": [bottom, right_val]}})

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
        if color is None:
            color = self.colorMaps[self.colormaps][self.get_color(ax_idx)]
            self.get_color(ax_idx, 1)
        elif isinstance(color, int):
            color = self.colorMaps[self.colormaps][color]
        else:
            color = color
        if y2data is not None:
            self.get_axis(ax_idx).fill_between(
                xdata,
                ydata,
                y2=y2data,
                color=color,
                edgecolor=edgecolor,
                hatch=hatch,
                linewidth=linewidth,
                # label=label,
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
                # label=label,
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
        if save_label is None:
            save_label = label
        if save_label != False:
            if y2data is not None:
                self.plotted_data.update(
                    {
                        save_label: {
                            "datax": xdata,
                            "datay": np.array(ydata) - np.array(y2data),
                        }
                    }
                )
            else:
                self.plotted_data.update(
                    {
                        save_label: {
                            "datax": np.array(xdata) - np.array(x2data),
                            "datay": np.array(ydata),
                        }
                    }
                )

    # def plot_scatter_3D(
    #     self,
    #     xdata,
    #     ydata,
    #     zdata=None,
    #     label="",
    #     marker="o",
    #     marker_size=10,
    #     vmin=None,
    #     vmax=None,
    #     ls="-",
    #     ax_idx=0,
    #     markerfacecolor=None,
    #     zorder=4,
    #     color=None,
    #     **kwargs,
    # ):
    #     if zdata is None:
    #         if color is None:
    #             color = self.colorMaps[self.colormaps][self.get_color(ax_idx)]
    #             self.get_color(ax_idx, 1)
    #     else:
    #         color = zdata
    #     self.colorFig = self.get_axis(ax_idx).scatter(
    #         xdata,
    #         ydata,
    #         c=color,
    #         cmap=self.colorMaps["color_map"],
    #         label=label,
    #         s=marker_size,
    #         ls=ls,
    #         facecolors=markerfacecolor,
    #         vmin=vmin,
    #         vmax=vmax,
    #         zorder=zorder,
    #         marker=marker,
    #
    def plot_arrow(
        self,
        x,
        y,
        dx,
        dy,
        ax_idx=0,
        color=None,
        head_starts_at_zero=False,
        lw=1,
        hw=20,
        hl=15,
    ):
        if color is None:
            color = self.colorMaps[self.colormaps][self.get_color(ax_idx)]
            self.get_color(ax_idx, 1)
        self.get_axis(ax_idx).arrow(
            x,
            y,
            dx,
            dy,
            width=lw,
            length_includes_head=True,
            head_width=hw,
            head_length=hl,
            color=color,
            head_starts_at_zero=head_starts_at_zero,
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
        ylabel=None,
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
        if color is None:
            color = self.colorMaps[self.colormaps][self.get_color(ax_idx)]
            self.get_color(ax_idx, 1)
        elif isinstance(color, int):
            color = self.colorMaps[self.colormaps][color]
        if sort_data and len(xdata) > 2:
            sort_idx = np.argsort(xdata)
            # print(sort_idx, xdata, ydata)
            xdata = np.array(xdata)[sort_idx]
            ydata = np.array(ydata)[sort_idx]
        # print(ax_idx, ydata)
        if self.map_mode:
            try:
                xdata = self.map_func_x(xdata)
                ydata = self.map_func_y(ydata)
            except:
                print("no map funcs, useing raw data")
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
                print("overlay", marker_overlay, k, marker_ranges[i])
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
        elif save_label is None and ylabel != None:
            save_label = ylabel
        if log_data:
            self.plotted_data.update(
                {
                    save_label: {
                        "datax": xdata,
                        "datay": ydata,
                    }
                }
            )

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
        # print(xdata, ydata, zdata)
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
            print(label, ylabel)
            if save_label is None and label != "":
                save_label = label
            elif save_label is None and ylabel != None:
                save_label = ylabel
            print(save_label, label, ylabel)
            # assert False
            self.plotted_data.update(
                {
                    save_label: {
                        "datax": xdata,
                        "datay": ydata,
                        "dataz": zdata,
                    }
                }
            )

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
        if color is None:
            color = self.colorMaps[self.colormaps][self.get_color(ax_idx)]
            self.get_color(ax_idx, 1)
        else:
            color = color
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
            # facecolors=markerfacecolor,
            vmin=vmin,
            vmax=vmax,
            zorder=zorder,
        )

        if save_label is None:
            save_label = label
        elif save_label is None and ylabel != None:
            save_label = ylabel
        if log_data:
            self.plotted_data.update(
                {
                    save_label: {
                        "datax": xdata,
                        "datay": ydata,
                    }
                }
            )
            if xerr is not None:
                self.plotted_data[save_label]["xerr"] = xerr
            if yerr is not None:
                self.plotted_data[save_label]["yerr"] = yerr

    def plot_cdf(
        self, data, color=None, num_bins=100, label="", ls="-", lw=2, ax_idx=0
    ):
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
        # bins = np.linspace(min(data), max(data), num_bins)
        # counts, binedges = np.histogram(data, bins=bins)
        # cdf = np.cumsum(counts)
        # if color  is None:
        #     color = self.colorMaps[self.colormaps][self.get_color(ax_idx)]
        #     self.get_color(ax_idx, 1)
        # cdf = [0] + list(cdf)
        # self.get_axis(ax_idx).plot(
        #     binedges, cdf / cdf[-1], color=color, label=label, ls=ls, lw=lw
        # )

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
    ):
        self.box_mode = True
        medianprops = {"color": "black", "linewidth": 1}
        if color is None:
            color = self.colorMaps[self.colormaps][self.get_color(ax_idx)]
            self.get_color(ax_idx, 1)
        elif isinstance(color, int):
            color = self.colorMaps[self.colormaps][color]
            print(color)
        dt = self.get_axis(ax_idx).boxplot(
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
        percentiles = np.percentile(data, [whiskers[0], 25, 50, 75, whiskers[1]])
        if save_label is not None:
            self.plotted_data.update({save_label: {"box_data": percentiles}})

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
        x = x.round(decimals=x_decimals)
        y = y.round(decimals=y_decimals)
        print(x.shape)
        if x_uniqu is None:
            x_uniqu = np.unique(x)
            y_uniqu = np.unique(y)
        z_map = np.empty((y_uniqu.shape[0], x_uniqu.shape[0]))
        z_map[:] = np.nan

        xdata = []
        ydata = []
        print(x_uniqu, y_uniqu)
        z = np.array(z)
        print(z.ndim, y.ndim, x.ndim)
        if z.ndim == 1:
            for i, iz in enumerate(z):
                print(x[i], y[i])
                ix = np.where(abs(x[i] - np.array(x_uniqu)) < 1e-5)[0]
                iy = np.where(abs(y[i] - np.array(y_uniqu)) < 1e-5)[0]
                z_map[iy, ix] = iz
                print(ix, iy, iz, x[i], y[i])
        else:
            z_map = z
        print(z_map)
        print(x_uniqu, y_uniqu)
        return z_map, x_uniqu, y_uniqu

    def fix_nan_in_map(self, input_map):
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

    def upscale_map(
        self,
        input_map,
        upscale=1000,
        x=None,
        y=None,
        upscale_x_range=None,
        upscale_y_range=None,
        mode="linear",
    ):
        if x is None:
            x = np.array(range(input_map.shape[1]))
            y = np.array(range(input_map.shape[0]))
        # mesh_grid_overall = np.array(np.meshgrid(x, y))
        # print(y)
        if upscale_x_range is None:
            ux = np.linspace(x[0], x[-1], upscale)
            uy = np.linspace(y[0], y[-1], upscale)
        else:
            ux = upscale_x_range
            uy = upscale_y_range

        xy = np.array(np.meshgrid(ux, uy)).T.reshape((upscale * upscale, 2))
        # print(input_map.shape, len(x), len(y))
        # print(np.array(input_map))  # [np.array(input_map) == np.array(input_map)],
        xx, yy = np.meshgrid(x, y)

        # print(xx)
        z = input_map[input_map == input_map]
        nx = xx[input_map == input_map]
        ny = yy[input_map == input_map]
        if mode == "linear":
            interp = LinearNDInterpolator(list(zip(nx, ny)), z)
        if mode == "nearest":
            interp = NearestNDInterpolator(list(zip(nx, ny)), z)
        if mode == "cubic":
            interp = CloughTocher2DInterpolator(
                list(zip(nx, ny)), z, maxiter=1000, rescale=True, tol=1e-8
            )
        # if mode == "RBF":
        #     interp = RBFInterpolator(list(zip(nx, ny)), z)
        #
        # NearestNDInterpolator
        # interp = RegularGridInterpolator(
        #     (x, y),
        #     np.array(input_map)[np.array(input_map) == np.array(input_map)],
        #     method="linear",
        #     fill_value=None,
        #     bounds_error=False,
        # )
        interp_points = interp(xy)

        interp_map, uux, uuy = self.build_map_data(
            x=xy[:, 0], y=xy[:, 1], x_uniqu=ux, y_uniqu=uy, z=interp_points
        )
        print(interp_map.shape)
        print(interp_map)
        return interp_map, uux, uuy

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
        x = np.array(range(input_map.shape[1]))
        y = np.array(range(input_map.shape[0]))

        xx, yy = np.array(np.meshgrid(x, y))
        print(xx, levels)

        return ax.contour(
            xx, yy, input_map, levels, colors=colors, norm=norm, zlevel=12
        )

    def plot_linear_contours(self, ax, input_map, x, y, levels, upscale):
        x = np.array(range(input_map.shape[1])) * upscale / input_map.shape[1]
        y = np.array(range(input_map.shape[0])) * upscale / input_map.shape[0]

        # xx, yy = np.array(np.meshgrid(x,
        xx, yy = np.array(np.meshgrid(x, y))
        for l in levels:
            temp_map = np.zeros(input_map.shape)
            temp_map[input_map == l] = 1
            temp_map[input_map > l] = 2
            loc_idxs = self.search_sequence_numpy(temp_map.flatten(), np.array([1, 2]))
            x_vals = xx.flatten()[loc_idxs]
            y_vals = yy.flatten()[loc_idxs]
            print(x_vals, y_vals)
            if len(x_vals) > 2:
                fit = np.polyfit(x_vals, y_vals, deg=2)
                xinterp = np.linspace(min(x), max(x), 100)
                yinterp = np.poly1d(fit)(xinterp)
                ax.plot(xinterp, yinterp, color="black", lw=1)
                print(self.search_sequence_numpy(temp_map.flatten(), np.array([1, 2])))
                print(temp_map)
            # print(pos_x_h)
            # assas

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
        x = np.array(range(input_map.shape[1]))
        y = np.array(range(input_map.shape[0]))
        xx, yy = np.array(np.meshgrid(x, y))

        if colors is None:
            cmap = self.colorMaps["color_map"]
        else:
            cmap = None
        # extend = None
        # ("mas", np.nanmax(input_map))
        # assaextend = "max"
        # # extend = "max"
        # if np.nanmin(input_map) < np.nanmin(levels):
        #     extend = "min"
        #     # cs.cmap.set_over(colors[0])
        # if np.nanmax(input_map) > np.nanmax(levels):
        #     extend = "max"
        #     # cs.cmap.set_over(colors[-1])
        # if np.nanmax(input_map) > np.nanmax(levels) and np.nanmin(
        #     input_map
        # ) < np.nanmin(levels):
        #     extend = "both"
        #     # cs.cmap.set_over(colors[0])
        #     # cs.cmap.set_over(colors[-1])
        print("lvels", levels)
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
        print(levels)
        for i, lu in enumerate(levels[1:]):
            lb, ub = levels[i], levels[i + 1]
            average_level = i  # levels[i] * 0.5 + levels[i + 1] * 0.5
            # print(len(map_data.shape))
            if len(map_data.shape) == 1:
                idx = np.where((map_data < ub) & (map_data > lb))[0]
                # print(idx)
                print(ub, lb, average_level)
                map_data[idx] = average_level
            else:
                for m in map_data:
                    idx = np.where((m < ub) & (m > lb))[0]
                    # print(idx)
                    print(ub, lb, average_level)
                    m[idx] = average_level
        if colors is None:
            _colors = []
            for l, _ in enumerate(levels):
                _colors.append(
                    matplotlib.colormaps.get_cmap(self.colorMaps["color_map"])(
                        l / len(levels)
                    )
                )
            print(colors)
        else:
            _colors = colors
            # for c in colors:
            #     if isinstance(c, str) and "#" in c:
            #         c = c.strip("#")
            #         _colors.append(tuple(int(c[i : i + 2], 16) for i in (0, 2, 4)))
            #     else:
            #         _colors.append(c)
        print(_colors)
        # assert False
        self.colorMaps["color_map"] = ListedColormap(_colors)  # len(levels))
        # print(self.colorMaps["color_map"])
        # assert False
        print(map_data)
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
        plot_contour_lines=None,
        contour_line_colors="black",
        plot_contour=None,
        contour_colors=None,
        overlay_levels=None,
        upscale=None,
        extend=None,
        extend_colors=None,
        digitize=False,
        digitize_levels=None,
        digitize_colors=None,
        unique_x_decimals=5,
        unique_y_decimals=5,
        **kwargs,
    ):
        # print(zoverlay, ydata, zdata)
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

            # print("build map",     map)
        else:
            map_data = np.array(zdata)
            datax, datay = xdata, ydata
            overlay_map = zoverlay
        if upscale is not None:
            datax_o, datay_o = copy.deepcopy(datax), copy.deepcopy(datay)
            map_data, datax, datay = self.upscale_map(
                map_data,
                upscale=upscale,
                x=datax,
                y=datay,
                upscale_x_range=None,
                upscale_y_range=None,
            )
            # if overlay_map is not None:
            #     # print("overlay_map", overlay_map)
            #     overlay_map, _, _ = self.upscale_map(
            #         overlay_map,
            #         upscale=upscale,
            #         x=datax_o,
            #         y=datay_o,
            #         upscale_x_range=None,
            #         upscale_y_range=None,
            #     )
            #     print("overlay_map", overlay_map)
        # print("mao shape", map.shape)
        self.map_x_width = map_data.shape[1]
        self.map_y_width = map_data.shape[0]
        if datax is None:
            datax = list(range(self.map_x_width))
        if datay is None:
            datay = list(range(self.map_y_width))
        if vmin is None and vmax is None:
            vmin = np.nanmin(map_data)
            vmax = np.nanmax(map_data)
        # if fix_nans:
        #     map = self.fix_nan_in_map(xdata, ydata, zdata,)
        # if fix_nans:
        #     map = self.fix_nan_in_map(np.unique(xdata), np.unique(ydata), map)
        if digitize_levels is not None:
            vmin, vmax = self.digitize_map(map_data, digitize_levels, digitize_colors)

        if zscale == "log":
            norm = LogNorm(vmin=vmin, vmax=vmax)
        else:
            norm = None
            # self.colorFig = self.get_axis(ax_idx).imshow(
            #     map_data,
            #     cmap=self.colorMaps["color_map"],
            #     aspect=aspect,
            #     norm=norm,
            #     origin="upper",
            # )
        # else:
        if plot_contour is not None:
            print("plotting countou")
            self.contour_mode = True
            self.colorFig = self.plot_contourf(
                self.get_axis(ax_idx),
                map_data,
                plot_contour,
                contour_colors,
                extend=extend,
                extend_colors=extend_colors,
                norm=norm,
            )
            print(norm)
            self.plot_contour(
                self.get_axis(ax_idx), map_data, plot_contour, "black", norm=norm
            )
        else:
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
        if plot_contour_lines is not None:
            self.plot_contour(
                self.get_axis(ax_idx), map_data, plot_contour_lines, contour_line_colors
            )
        if overlay_map is not None:
            self.plot_linear_contours(
                self.get_axis(ax_idx),
                overlay_map,
                datax,
                datay,
                overlay_levels,
                upscale,
            )
            # self.plot_contour(self.get_axis(ax_idx), overlay_map, overlay_levels, "black")
        if text and map_data.size < 200:
            for r, row in enumerate(map_data):
                for c, value in enumerate(row):
                    print(abs(value), ((vmax - vmin) / 2 + vmin))
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
        self.plotted_data.update(
            {
                "label": label,
                "datax": datax,
                "datay": datay,
                "dataz": map_data,
            }
        )

    def gen_map_function(self, axisdata, scale="linear"):
        indexes = list(range(len(axisdata)))
        print(axisdata, indexes, scale)

        # print("axis data", axisdata, indexes, scale)
        if scale == "interp":
            return scipy.interpolate.interp1d(
                axisdata, indexes, bounds_error=False, fill_value="extrapolate"
            )
        if scale == "linear":
            # print(np.polyfit(axisdata, indexes, deg=1))
            return np.poly1d(np.polyfit(axisdata, indexes, deg=1))
        if scale == "log":

            def log_func(x, a, b):
                return a * np.log(x) - b

            fit_params = scipy.optimize.curve_fit(log_func, axisdata, indexes)
            a, b = fit_params[0]
            # print(a, b)
            return lambda x: a * np.log(x) - b

    def gen_minor_ticks(self, axisticks, strides=10):
        minor_ticks = []
        return_ticks = []
        log_vmin = math.log(min(axisticks)) / math.log(10)
        log_vmax = math.log(max(axisticks)) / math.log(10)

        numdec = math.floor(log_vmax) - math.ceil(log_vmin)
        # print(numdec, log_vmin, log_vmax, np.linspace(log_vmin, log_vmax, numdec))

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
                # print(
                #     "dst",
                #     self.plotted_data["datax"],
                #     np.min(self.plotted_data["datax"]),
                #     np.max(self.plotted_data["datax"]),
                # )
                # assert False
                self.map_func_x = self.gen_map_function(
                    self.plotted_data["datax"], xscale
                )
                if self.contour_mode:
                    offset_x = 0
                    offset_y = -1
                else:
                    offset_x = -0.5
                    offset_y = 0.5

                ticks = self.map_func_x(xticklabels)
                print(offset_x, ticks[-1], ticks[-1] + offset_y)
                self.get_axis(ax_idx).set_xlim(offset_x, ticks[-1] + offset_y)
                # offset = 0.5 / self.map_x_width  # / 2
                # print(offset)
                # print(xticklabels)
                print("xticks", ticks)
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
            # print(self.map_mode)
            if self.map_mode:
                if self.contour_mode:
                    offset_x = 0
                    offset_y = -1
                else:
                    offset_x = -0.5
                    offset_y = 0.5
                    # offset = -0.5
                self.map_func_y = self.gen_map_function(
                    self.plotted_data["datay"], yscale
                )
                ticks = self.map_func_y(yticklabels)
                self.get_axis(ax_idx).set_ylim(
                    offset_x + ticks[0], ticks[-1] + offset_y
                )
                # self.get_axis(ax_idx).set_ylim(offset_x, self.map_y_width + offset_y)
                # print(self.plotted_data["datay"])

                # ticks = self.map_func_y(yticklabels)
                print("tiks", ticks)
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
            # if add_minor_ticks:
            #     self.get_axis(ax_idx).yaxis.set_minor_locator(
            #     ticker.FixedLocator([0.1, 0.2, 0.5])
            # )
        #   # self.get_axis(ax_idx).yaxis.set_minor_locator(ticker.ScalarFormatter())
        #  self.get_axis(ax_idx).set_minor_xticks(ticks)
        if xlabel is not None:
            self.get_axis(ax_idx).set_xlabel(xlabel, labelpad=xlabelpad)
            self.plotted_data.update({"xlabel": xlabel})
        if ylabel is not None:
            self.get_axis(ax_idx).set_ylabel(ylabel, labelpad=ylabelpad)
            self.plotted_data.update({"ylabel": ylabel})
        self.get_axis(ax_idx).set_aspect(set_aspect)

    def set_fig_label(
        self, xlabel=None, ylabel=None, x_pad=-0.04, y_pad=0.05, label_size=12
    ):
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
        data = []
        # print(self.plotted_data)
        for key in self.plotted_data.keys():
            if key != "xlabel" and key != "ylabel":
                if len(self.plotted_data[key]["datax"]) > 0:
                    # print(key)
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
        print("got xticks", xticks)
        if xlims is not None:
            self.get_axis(ax_idx).set_xlim(xlims[0], xlims[1])
            if xticks is None:
                if xscale == "log":
                    xticks = np.geomspace(xlims[0], xlims[1], default_xticks)
                else:
                    xticks = np.linspace(xlims[0], xlims[1], default_xticks)
                # rint(xticks)

        if xticks is not None:
            self.get_axis(ax_idx).set_xticks(np.array(xticks))
            print("set xticks lims", xticks)
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
            # p#rint(yticks)
        if yticks is None and ylims is None:
            try:
                ylims = self.auto_gen_lims("datay")
                yticks = np.linspace(ylims[0], ylims[1], default_yticks)
                self.get_axis(ax_idx).set_yticks(yticks)
                self.get_axis(ax_idx).set_ylim(yticks[0], yticks[-1])
                print("set y lims", yticks)
            except:
                print("failed to auto gen yticks")
        if xticks is None and xlims is None:
            try:
                xlims = self.auto_gen_lims("datax")
                xticks = np.linspace(xlims[0], xlims[1], default_xticks)
                self.get_axis(ax_idx).set_xticks(np.array(xticks))
                self.get_axis(ax_idx).set_xlim(xticks[0], xticks[-1])
            except:
                print("failed to auto gen xticks")

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
        # self.get_axis(ax_idx).yaxis.set_major_locator(ticker.FixedLocator(yticks))
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
            self.plotted_data.update({"xlabel": xlabel})
        if ylabel is not None:
            self.get_axis(ax_idx).set_ylabel(
                ylabel, labelpad=ylabelpad, rotation=ylabelrotate
            )
            self.plotted_data.update({"ylabel": ylabel})
        if zlabel is not None and self.mode_3d:
            self.get_axis(ax_idx).set_zlabel(
                zlabel, labelpad=zlabelpad, rotation=zlabelrotate
            )
            self.plotted_data.update({"ylabel": ylabel})
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
        xaxiscolor = ("black",)
        yaxiscolor = ("black",)

    def add_colorbar(
        self, zlabel, zticks=None, zformat=1, zlabelpad=17, cbar=None, **kwargs
    ):
        # if ticks is None:
        #     ticks = np.linspace(zlims[0], zlims[1], 5)
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
        self.plotted_data.update({"zlabel": zlabel})

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
        # print(self.ax)
        # if self.idx_totals[0] == 1 and self.idx_totals[1] == 1:
        #     return self.ax[idx]
        if self.idx_totals[0] > 1 and self.idx_totals[1] > 1:
            print(self, self.ax, idx)
            return self.ax[idx[0], idx[1]]
        else:
            return self.ax[idx]

    def remove_sub_fig_space(self):
        if self.idx_totals[0] > 1 and self.idx_totals[1] > 1:
            # i#f self.sharex:
            for i in range(self.idx_totals[0] - 1):
                for j in range(self.idx_totals[1]):
                    self.remove_ticks(ax_idx=(i, j), x_axis=True)
            # if self.sharey:
            for i in range(self.idx_totals[1]):
                for j in range(1, self.idx_totals[1]):
                    self.remove_ticks(ax_idx=(i, j), y_axis=True)

        else:
            # if self.sharex:
            for i in range(self.idx_totals[0] - 1):
                self.remove_ticks(ax_idx=i, x_axis=True)
            # if self.sharey:
            for i in range(1, self.idx_totals[1]):
                self.remove_ticks(ax_idx=i, y_axis=True)
        self.fig.subplots_adjust(wspace=0, hspace=0)

    def remove_ticks(self, ax_idx=0, y_axis=None, x_axis=None):
        if y_axis is True:
            self.get_axis(ax_idx).axes.yaxis.set_visible(False)
        if x_axis is True:
            self.get_axis(ax_idx).axes.xaxis.set_visible(False)

    def format_value(self, value, decimals):
        if decimals == 0:
            return str(int(round(value, 0)))
        else:
            return str(round(value, decimals))

    def onclick(self, event):
        ix, iy = event.xdata, event.ydata
        print(dir(event))
        print(event.inaxes)
        print(event.canvas)
        print("x = %d, y = %d" % (ix, iy))

        coords = [ix, iy]
        self.click_positions["x"].append(event.xdata)
        self.click_positions["y"].append(event.ydata)
        self.click_positions["axis"].append(str(event.inaxes))
        self.click_positions["c_num"].append(self.click_number)
        self.click_number += 1
        event.inaxes.scatter(
            [event.xdata], [event.ydata], c=None, facecolors=None, edgecolors="red"
        )
        self.fig.canvas.draw()

    def add_mouse_click_logging(self):
        self.click_positions = {"x": [], "y": [], "axis": [], "c_num": []}
        self.click_number = 0
        self.fig.canvas.mpl_connect("button_press_event", self.onclick)

    def format_ticks(self, ticks, decimals):
        return [self.format_value(tick, decimals) for tick in ticks]

    def save_fig(self, name="output_fig"):
        self.fig.savefig(name + ".jpg", dpi=300, bbox_inches="tight", pad_inches=0.1)
        self.fig.savefig(name + ".svg", dpi=300, bbox_inches="tight", pad_inches=0.1)

    def save(self, save_location=None, file_name=None, figure_description=None):
        if save_location is not None:
            self.save_location = save_location
        if file_name is not None:
            self.file_name = file_name
        if figure_description is not None:
            self.figure_description = None
        self.save_fig(self.save_location + "\\" + self.file_name)
        self.export_data_to_csv(
            self.save_location + "\\" + self.file_name, self.figure_description
        )

    def show(self):
        # plt.open(self.fig)
        plt.show()

    def set_default_figure_settings(
        self, font_size=10, label_size=12, svg_font_setting="none"
    ):
        """Set global font and text size to 10"""
        default_font = {
            "family": "serif",
            "serif": "Arial",
            "weight": "normal",
            "size": font_size,
        }
        """Set global label size"""
        default_label_size = {
            "labelsize": label_size,
        }

        matplotlib.rc("font", **default_font)
        matplotlib.rc("axes", **default_label_size)

        """Set global math text to regular"""
        default_math_text = {"mathtext.default": "regular"}
        plt.rcParams.update(default_math_text)
        plt.rcParams.update({"svg.fonttype": svg_font_setting})
        """Set global backend
            The backend that is used to plot can greatly influence
            how your figure looks, in general best resutls are obtained
            with TkAgg backend
        """
        # plt.switch_backend('TkAgg')

    def remove_math_text(self, string):
        replaceUSD = False
        if "\$" in string:
            string = string.replace("\$", "USD")
            replaceUSD = True
        if "$" in string:
            string = string.replace("$", "")
        if replaceUSD:
            string = string.replace("USD", "$")
        return string

    def export_data_to_csv(self, file_name="none", figure_description=None):
        data = []
        if figure_description is not None:
            data.append([figure_description])
        if self.map_mode:
            zlabel = self.plotted_data.get("zlabel")
            if zlabel is not None:
                data.append(
                    [
                        "Map data for {}".format(
                            self.remove_math_text(zlabel),
                        ),
                        "",
                    ]
                )
                data.append(
                    [
                        "First column is {}".format(
                            self.remove_math_text(self.plotted_data["ylabel"])
                        ),
                    ]
                )
                data.append(
                    [
                        "First row is {}".format(
                            self.remove_math_text(self.plotted_data["xlabel"])
                        ),
                    ]
                )
                data.append(
                    [
                        "Internal data is {}".format(
                            self.remove_math_text(self.plotted_data["zlabel"])
                        ),
                    ]
                )
                rows_label = [self.plotted_data["ylabel"], "|", "|", "v"]
                # print(data)
                data.append([""] + list(self.plotted_data["datax"]))
                # print(
                #     self.plotted_data["datax"].shape,
                #     self.plotted_data["datay"].shape,
                #     self.plotted_data["dataz"].shape,
                # )
                for ik, k in enumerate(self.plotted_data["datay"]):
                    try:
                        lb = rows_label[ik]
                    except IndexError:
                        lb = ""
                    data.append([k] + list(self.plotted_data["dataz"][ik]))
        elif self.box_mode:
            # print("box_mode", self.plotted_data)
            # data.append(["key", "low_val", "high_val"])
            header_added = False
            for key, item in self.plotted_data.items():
                # print(item)
                if isinstance(item, dict):
                    if item["box_data"][0] != None:
                        if len(item["box_data"]) == 2 and header_added == False:
                            data.append(["key", "low_val", "high_val"])
                            header_added = True
                        elif header_added == False:
                            data.append(["key", "LW", "25", "50", "75", "HW"])
                            header_added = True
                        data.append([key] + list(item["box_data"]))
            # print(data)

        else:
            if "xlabel" in self.plotted_data:
                header = [self.plotted_data["xlabel"]]
            else:
                header = [""]
            x_data = []
            y_data = []
            x_err_data = []
            y_err_data = []
            z_data = []
            x_flat = []
            for key in self.plotted_data.keys():
                if key != "xlabel" and key != "ylabel" and key != "zlabel":
                    # print(self.plotted_data, key)
                    if len(self.plotted_data[key]["datax"]) > 0:
                        header.append(key)

                        x_flat += list(self.plotted_data[key]["datax"])
                        x_data.append(self.plotted_data[key]["datax"])
                        y_data.append(self.plotted_data[key]["datay"])
                        if self.plotted_data[key].get("dataz") is not None:
                            z_data.append(self.plotted_data[key]["dataz"])
                            header.append(self.plotted_data["zlabel"])
                        if self.plotted_data[key].get("xerr") is not None:
                            x_err_data.append(self.plotted_data[key]["xerr"])
                            header.append("x error in" + key)
                        if self.plotted_data[key].get("yerr") is not None:
                            y_err_data.append(self.plotted_data[key]["yerr"])
                            header.append("y error in" + key)
            data.append(header)
            # print(header)

            x_uq = np.unique(np.array(x_flat).flatten())
            for x in x_uq:
                row = [x]
                for i, k in enumerate(x_data):
                    y_ix = np.where(k == x)[0]  # abs(k - x) < 1e-10
                    # print(y_ix,k,x)
                    if len(y_ix) == 1:
                        # print(y_ix, k, x)
                        try:
                            row.append(float(y_data[i][y_ix]))
                            if len(z_data) > 0:
                                row.append(float(z_data[i][y_ix]))
                            if len(x_err_data) > 0:
                                row.append(float(x_err_data[i][y_ix]))
                            if len(y_err_data) > 0:
                                row.append(float(y_err_data[i][y_ix]))
                        except TypeError:
                            row.append("")
                            if len(x_err_data) > 0:
                                row.append("")
                            if len(y_err_data) > 0:
                                row.append("")
                    else:
                        row.append("")
                        if len(x_err_data) > 0:
                            row.append("")
                        if len(y_err_data) > 0:
                            row.append("")
                data.append(row)
        # print(self.plotted_data)
        save_name = file_name + ".csv"
        with open(save_name, "w", newline="") as csvfile:
            spamwriter = csv.writer(csvfile, delimiter=",")
            # spamwriter.writerow(header)
            for k in data:
                spamwriter.writerow(k)
