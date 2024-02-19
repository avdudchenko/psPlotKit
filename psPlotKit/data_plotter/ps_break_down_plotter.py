from psPlotKit.data_plotter.fig_generator import figureGenerator
from psPlotKit.data_manager import data_importer
from psPlotKit.util.util_funcs import create_save_location
import os
import copy

__author__ = "Alexander V. Dudchenko (SLAC)"


class breakDownPlotter:
    def __init__(
        self,
        psData,
        save_location=None,
        save_folder=None,
        save_name=None,
        show_figs=True,
    ):

        self.save_location = create_save_location(save_location, save_folder)
        self.show_figs = show_figs
        self.select_data_key_list = []
        self.psData = psData
        self.define_plot_styles()
        self.line_indexes = {}
        self.line_groups = None
        self.xunit = None
        self.yunit = None
        self.xdata_label = None
        self.ydata_label = None
        self.save_name = save_name

    def _select_data(self, keys):
        self.psData.select_data(keys, False)

    def define_hatch_groups(self, groups=None):
        self.hatch_groups = groups

    def define_area_groups(self, groups):
        self.area_groups = groups

    def _get_color(self, label):
        if isinstance(self.line_colors, dict):
            return self.line_colors[label]
        else:
            idx = None
            for key in label:
                if key in self.line_indexes:
                    idx = self.line_indexes[key]["idx"]
                    break
            if idx == None:
                # _logger.info("Did not find line color group")

                auto_label = "auto_{}".format(label)

                if auto_label in self.line_indexes:
                    self.line_indexes[auto_label]["idx"] += 1
                    idx = self.line_indexes[auto_label]["idx"]

                else:
                    idx = 0
                    self.line_indexes[auto_label] = {"idx": 0}
            if isinstance(idx, int):
                color = self.line_colors[idx]
            else:
                color = idx
            return color

    def define_plot_styles(self, hatch_options=None, line_color_list=None):
        if hatch_options is None:
            self.hatch_options = ["", "////", "///\\\\"]
        if line_color_list is None:
            self.line_colors = [
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
            ]
        else:
            self.line_colors = line_color_list

    def _get_data(self, data, key):
        data_keys = []
        data_list = []
        for dkey, data in data.items():
            if key in dkey:

                if isinstance(dkey, tuple):
                    skeys = []
                    for k in dkey:
                        if k != key:
                            skeys.append(k)
                else:
                    skeys = [dkey]
                data_keys.append(tuple(skeys))
                data_list.append(data)
        return data_keys, data_list

    def _get_axis_label(self, label, units):
        return "{} ({})".format(label, units)

    def _get_ydata(self, selected_keys, ydata):
        ykey_data = []
        for skey in selected_keys:

            if isinstance(ydata, list) or isinstance(ydata, tuple):
                all_test = all(ykey in str(skey) for ykey in ydata)
            else:
                all_test = ydata in str(skey)
            if all_test:
                ykey_data.append(skey)
        return ykey_data

    def _replace_key(self, skey, xdata):
        dir_key = list(skey)
        dir_key[-1] = xdata
        return tuple(dir_key)

    def check_key_in_dir(self, udir, key):
        for d in udir:
            if isinstance(d, str):
                if d == key:
                    return True
            else:
                for di in d:
                    if key == di:
                        return True
        return False

    def _get_group_options(self, selected_keys, xdata, ydata):
        self.plot_areas = {}
        # self.area_groups = {}
        for skey in self._get_ydata(selected_keys, ydata):
            opts = None
            key = None
            for i, key in enumerate(self.hatch_groups):
                if key in str(skey):
                    opts = self.hatch_groups[key]
                    if opts.get("label") == None:
                        opts["label"] = key
                    if opts.get("color") == None:
                        opts["color"] = "white"
                    if opts.get("hatch") == None:
                        opts["hatch"] = self.hatch_options[i]

                    self.hatch_groups[key] = copy.deepcopy(opts)
                    # if key not in self.line_indexes:
                    #     self.line_indexes[key] = {"idx": 0, "auto": True}
            for akey in self.area_groups:
                if self.check_key_in_dir(skey, akey):
                    _label = akey
                    plot_label = _label
                    cur_line = {}
                    raw_ydata = self.selected_data[skey]
                    raw_xdata = self.selected_data[self._replace_key(skey, xdata)]
                    cur_line["ydata"] = raw_ydata.data
                    cur_line["xdata"] = raw_xdata.data

                    if self.xunit == None:
                        self.xunit = raw_xdata.mpl_units
                    if self.xdata_label == None:
                        self.xdata_label = raw_xdata.data_label
                    if self.yunit == None:
                        self.yunit = raw_ydata.mpl_units
                    if self.ydata_label == None:
                        self.ydata_label = raw_ydata.data_label
                    if opts != None:
                        for key, val in opts.items():
                            cur_line[key] = val

                    if self.hatch_groups != {}:
                        for h_key in self.hatch_groups:
                            # print("ss", h_key, akey, skey)
                            if h_key in str(skey):

                                _label = tuple([h_key, akey])
                                plot_label.replace(h_key, "")
                                cur_line["color"] = self._get_color(h_key)
                                cur_line["label"] = plot_label
                                self.plot_areas[_label] = cur_line
                    else:
                        cur_line["color"] = self._get_color(akey)
                        cur_line["label"] = plot_label
                        self.plot_areas[_label] = cur_line
        # print("line_groups", self.line_groups)
        print("plot_lines", self.plot_areas)
        print("hatch_groups", self.hatch_groups)
        # assert False

    def plotbreakdown(self, xdata, ydata, axis_options=None, generate_plot=True):

        self._select_data([xdata, ydata])
        self.selected_data = self.psData.get_selected_data()
        self.generate_groups_lines = self._get_group_options(
            self.selected_data.keys(), xdata, ydata
        )
        self.index = 0
        if axis_options is None:
            self.axis_options = {}
        else:
            self.axis_options = axis_options
        if self.axis_options.get("xlabel") == None:
            self.axis_options["xlabel"] = self._get_axis_label(
                self.xdata_label, self.xunit
            )  # all lines shold share units
        if self.axis_options.get("ylabel") == None:
            self.axis_options["ylabel"] = self._get_axis_label(
                self.ydata_label, self.yunit
            )  # all lines shold share units
        self.plot_imported_data()
        if generate_plot:
            self.generate_figure()

    def plot_imported_data(self):
        self.fig = figureGenerator()
        self.fig.init_figure()
        plotted_legend = []
        for group, items in self.hatch_groups.items():
            self.fig.plot_area([], [], **items)
        old_data = 0
        current_data = None
        for linelabel, line in self.plot_areas.items():
            if line.get("label") in plotted_legend:
                line.pop("label")
            else:
                plotted_legend.append(line["label"])
            line["y2data"] = old_data
            if current_data is None:
                current_data = line["ydata"]
            else:
                current_data = line["ydata"] + old_data
            line["ydata"] = current_data
            self.fig.plot_area(**line)
            old_data = line["ydata"]

    def generate_figure(self):
        self.fig.set_axis(**self.axis_options)
        self.fig.add_legend()
        if self.save_name == None:
            save_name = "{} vs {}".format(self.xdata_label, self.ydata_label)
        else:
            save_name = "{} - {} vs {}".format(
                self.save_name, self.xdata_label, self.ydata_label
            )
        self.fig.save(self.save_location, save_name)
        self.fig.show()
