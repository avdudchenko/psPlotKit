from psPlotKit.data_plotter.fig_generator import figureGenerator
from psPlotKit.util.util_funcs import create_save_location
from psPlotKit.data_plotter.ps_line_plotter import linePlotter
import numpy as np

from psPlotKit.util import logger

__author__ = "Alexander V. Dudchenko (SLAC)"


_logger = logger.define_logger(__name__, "MapPlotter", level="INFO")


class MapPlotter:
    def __init__(
        self, PsData, save_location="", save_folder=None, save_name=None, show_fig=True
    ):
        self.save_location = create_save_location(save_location, save_folder)
        self.show_fig = show_fig
        self.select_data_key_list = []
        self.PsData = PsData
        self.zunit = None
        self.xunit = None
        self.yunit = None
        self.xdata_label = None
        self.ydata_label = None
        self.zdata_label = None
        self.save_name = save_name
        self.data_index_to_label = {}

    def _select_data(self, keys):
        self.PsData.select_data(keys, require_all_in_dir=False)

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
        plot_options=None,
        zformat=1,
    ):
        self.xdata = self.PsData.get_data(data_dir, xdata)
        self.ydata = self.PsData.get_data(data_dir, ydata)
        self.zdata = self.PsData.get_data(data_dir, zdata)

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
        if plot_options is None:
            self.plot_options = {}
        else:
            self.plot_options = plot_options
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

        if self.axis_options.get("zformat") != None:
            zformat = self.axis_options["zformat"]
        
        self.plot_imported_data(fig_options)

        if generate_plot:
            self.generate_figure(zformat)

        if self.save_name is not None:
            self.fig.save(self.save_location, self.save_name)

        if self.show_fig:
            self.fig.show()
        
        self.fig.close()

    def plot_imported_data(self, opts):
        if opts is not None:
            self.fig = figureGenerator(**opts)
            self.fig.init_figure(**opts)
        else:
            self.fig = figureGenerator()
            self.fig.init_figure()

        self.fig.plot_map(
            xdata=self.xdata.data,
            ydata=self.ydata.data,
            zdata=self.zdata.data,
            build_map=True,
            vmin=min(self.zlevels),
            vmax=max(self.zlevels),
            **self.plot_options
        )

    def generate_figure(self, zformat=1):
        self.fig.add_colorbar(
            self.axis_options["zlabel"], zticks=self.zlevels, zformat=zformat
        )
        self.fig.set_axis_ticklabels(**self.axis_options)

