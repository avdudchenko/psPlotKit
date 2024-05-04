from psPlotKit.data_plotter.fig_generator import figureGenerator
from psPlotKit.util.util_funcs import create_save_location
from psPlotKit.data_plotter.ps_line_plotter import linePlotter
import numpy as np

__author__ = "Alexander V. Dudchenko (SLAC)"


class mapPlotter:
    def __init__(
        self, psData, save_location="", save_folder=None, save_name=None, show_figs=True
    ):
        self.save_location = create_save_location(save_location, save_folder)
        self.show_figs = show_figs
        self.select_data_key_list = []
        self.psData = psData
        self.zunit = None
        self.xunit = None
        self.yunit = None
        self.xdata_label = None
        self.ydata_label = None
        self.zdata_label = None
        self.save_name = save_name
        self.data_index_to_label = {}

    def _select_data(self, keys):
        self.psData.select_data(keys, require_all_in_dir=False)

    def _get_axis_label(self, label, units):
        return "{} ({})".format(label, units)

    def plot_map(
        self,
        data_dir,
        xdata,
        ydata,
        zdata,
        zlevels=None,
        axis_options=None,
        generate_plot=True,
        fig_options=None,
    ):
        self.xdata = self.psData.get_data(data_dir, xdata)
        self.ydata = self.psData.get_data(data_dir, ydata)
        self.zdata = self.psData.get_data(data_dir, zdata)

        if zlevels is None:
            self.zlevels = np.linspace(
                np.min(self.zdata.data), np.max(self.zdata.data), 5
            )
        else:
            self.zlevels = zlevels
        self.index = 0
        if axis_options is None:
            self.axis_options = {}
        else:
            self.axis_options = axis_options
        if self.axis_options.get("xlabel") == None:
            self.axis_options["xlabel"] = self._get_axis_label(
                self.xdata.data_label, self.xdata.mpl_units
            )  # all lines shold share units
        if self.axis_options.get("ylabel") == None:
            self.axis_options["ylabel"] = self._get_axis_label(
                self.ydata.data_label, self.ydata.mpl_units
            )  # all lines shold share units
        if self.axis_options.get("zlabel") == None:
            self.axis_options["zlabel"] = self._get_axis_label(
                self.zdata.data_label, self.zdata.mpl_units
            )  # all lines shold share units
        self.plot_imported_data(fig_options)
        if generate_plot:
            self.generate_figure()

    def plot_imported_data(self, opts):
        if opts is not None:
            self.fig = figureGenerator(**opts)
            self.fig.init_figure(**opts)
        else:
            self.fig = figureGenerator()
            self.fig.init_figure()
        plotted_legend = []

        self.fig.plot_map(
            xdata=self.xdata.data,
            ydata=self.ydata.data,
            zdata=self.zdata.data,
            digitize_levels=self.zlevels,
            build_map=True,
            vmin=min(self.zlevels),
            vmax=max(self.zlevels),
            # zscale="log",
            # plot_contour_lines=self.zlevels,
            # plot_contour=self.zlevels,
        )

    def generate_figure(self):
        self.fig.add_colorbar(self.axis_options["zlabel"], zticks=self.zlevels)
        self.fig.set_axis_ticklabels(**self.axis_options)

        if self.save_name == None:
            save_name = "Map {}".format(self.xdata_label)
        else:
            save_name = "Map {} - {} {} {}".format(
                self.save_name, self.xdata_label, self.ydata_label, self.zdata_label
            )
        self.fig.save(self.save_location, save_name)
        self.fig.show()
