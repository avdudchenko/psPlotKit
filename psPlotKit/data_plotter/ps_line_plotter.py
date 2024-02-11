from psPlotKit.data_plotter.fig_generator import figureGenerator
from psPlotKit.data_manager import data_importer
import copy


class linePlotter:
    def __init__(self, psData, save_location="", show_figs=True):
        self.save_location = save_location
        self.show_figs = show_figs
        self.select_data_key_list = []
        self.psData = psData
        self.define_line_colors()
        self.line_indexes = {}
        self.line_groups = None

    def _select_data(self, keys):
        self.psData.select_data(keys)

    def define_line_groups(self, line_groups=None):
        self.line_groups = line_groups
        self.line_indexes = {}

    def specify_line_colors(self, line_colors):
        self.line_indexes = {}
        for l in line_colors:
            self.line_indexes[l] = {"idx": line_colors[l], "auto": False}

    def _get_color(self, label):
        if isinstance(self.line_colors, dict):
            return self.line_colors[label]
        else:
            idx = None
            for key in label:
                if key in self.line_indexes:
                    idx = self.line_indexes[key]["idx"]
                    break
            # if idx == None:
            #     for key in datakey:
            #         if key in self.line_indexes:
            #             idx = self.line_indexes[key]["idx"]
            #             break
            if idx == None:
                # _logger.info("Did not find line color group")
                # print("auto", label, datakey)
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

    def define_line_colors(self, line_color_list=None):
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
            print(dkey, data)
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

    def _get_axis_label(self, label, data):
        return "{} ({})".format(label, data.mpl_units)

    def _get_ydata(self, selected_keys, ydata):
        ykey_data = []
        for skey in selected_keys:
            if ydata in str(skey):
                ykey_data.append(skey)
        return ykey_data

    def _replace_key(self, skey, xdata):
        dir_key = list(skey)
        dir_key[-1] = xdata
        return tuple(dir_key)

    def _get_group_options(self, selected_keys, xdata, ydata):
        self.plot_lines = {}

        print("line_groups", self.line_groups)
        for skey in self._get_ydata(selected_keys, ydata):
            # check if we have line_groups
            opts = None
            key = None
            for key in self.line_groups:
                if key in str(skey):
                    opts = self.line_groups[key]
                    if opts.get("label") == None:
                        opts["label"] = key
                    if opts.get("color") == None:
                        opts["color"] = "black"
                    if key not in self.line_indexes:
                        self.line_indexes[key] = {"idx": 0, "auto": True}
                    if key not in self.plot_lines:
                        self.plot_lines[key] = {}
            for sk in skey:
                if ydata in sk:
                    if isinstance(sk, tuple):
                        _label = list(sk)[:]
                        _label.remove(ydata)
                        _label = " ".join(_label)
                    else:
                        _label = sk
                    print("self.plot_lines", self.plot_lines)
                    cur_line = {}

                    cur_line = {}
                    cur_line["ydata"] = self.selected_data[skey]
                    cur_line["xdata"] = self.selected_data[
                        self._replace_key(skey, xdata)
                    ]
                    if opts != None:
                        for key, val in opts.items():
                            cur_line[key] = val
                    cur_line["color"] = self._get_color(_label)
                    if self.plot_lines != {}:
                        for g_key in self.plot_lines:
                            if g_key in str(skey):
                                self.plot_lines[g_key][_label] = cur_line
                    else:
                        self.plot_lines[_label] = cur_line
        print("line_groups", self.line_groups)
        print("plot_lines", self.plot_lines)

    def _get_line_options(self, group, label, datakeys, ydata, xdata, group_options):
        ld_options_list = []

        for k, key in enumerate(datakeys):
            if group_options is not None:
                for g_key in group:
                    if g_key in group_options:
                        ld_options = copy.deepcopy(group_options[g_key])
                for k_key in key:
                    if k_key in group_options:
                        ld_options = copy.deepcopy(group_options[k_key])
                print(group_options, group, key)
            else:
                ld_options = {}
                ld_options["marker"] = "o"
            if isinstance(ydata[k].data_label, tuple):
                label_list = []
                for xl in ydata[k].data_label:
                    if label not in xl:
                        label_list.append(xl)
                rlabel = "_".join(label_list)
            else:
                rlabel = ydata[k].data_label
            l_color, fkey = self._get_color(group, key)
            if fkey != key:

                ld_options["label"] = str(group)  # " ".join(group)
                print(ld_options["label"])
            else:
                ld_options["label"] = rlabel
            ld_options["color"] = l_color
            ld_options["ydata"] = ydata[k].data
            ld_options["xdata"] = xdata[
                0
            ].data  # We should only have a single data set in the array
            ld_options_list.append(copy.deepcopy(ld_options))
        return ld_options_list

    def plot_line(self, xdata, ydata, axis_options=None):

        self._select_data([xdata, ydata])
        self.selected_data = self.psData.get_selected_data()
        self.generate_groups_lines = self._get_group_options(
            self.selected_data.keys(), xdata, ydata
        )

        self.index = 0
        group_order = []
        line_order = []

        if axis_options is None:
            axis_options = {}
        if axis_options.get("xlabel") == None:
            axis_options["xlabel"] = self._get_axis_label(
                xdata, x[0]
            )  # all lines shold share units
        if axis_options.get("ylabel") == None:
            axis_options["ylabel"] = self._get_axis_label(
                ydata, y[0]
            )  # all lines shold share units
        self._generate_line_figure(self.line_groups, axis_options)

    def _generate_line_figure(self, group_order, axis_dict):
        fig = figureGenerator()
        fig.init_figure()
        plotted_legend = []
        for group, items in group_order.items():
            fig.plot_line([], [], **group)
        for line in line_order:
            for sub_line in line:
                if sub_line.get("label") in plotted_legend:
                    sub_line.pop("label")
                else:
                    plotted_legend.append(sub_line["label"])
                fig.plot_line(**sub_line)
        fig.set_axis(**axis_dict)
        fig.add_legend()
        fig.show()
