from psPlotKit.data_plotter.fig_generator import figureGenerator
from psPlotKit.util.util_funcs import create_save_location

__author__ = "Alexander V. Dudchenko (SLAC)"


class linePlotter:
    def __init__(
        self, psData, save_location="", save_folder=None, save_name=None, show_figs=True
    ):
        self.save_location = create_save_location(save_location, save_folder)
        self.show_figs = show_figs
        self.select_data_key_list = []
        self.psData = psData
        self.define_line_colors()
        self.line_indexes = {}
        self.line_groups = {}
        self.xunit = None
        self.yunit = None
        self.xdata_label = None
        self.ydata_label = None
        self.save_name = save_name
        self.data_index_to_label = {}

    def _select_data(self, keys):
        self.psData.select_data(keys, require_all_in_dir=False)

    def define_line_groups(self, line_groups=None):
        self.line_groups = line_groups
        self.line_indexes = {}

    def define_index_labels(self, index_labels):
        self.data_index_to_label = index_labels

    def specify_line_colors(self, line_colors):
        self.line_indexes = {}
        for l in line_colors:
            self.line_indexes[l] = {"idx": line_colors[l], "auto": False}

    def _get_color(self, label, count_idx=None, single_group=False):
        if isinstance(self.line_colors, dict):
            return self.line_colors[label]
        else:
            idx = None
            for key in label:
                if key in self.line_indexes:
                    idx = self.line_indexes[key]["idx"]
                    print(key, self.line_indexes[key])
                    break
            if idx == None:
                if single_group:
                    auto_label = "single_group"
                else:
                    auto_label = "auto_{}".format(label)

                if auto_label in self.line_indexes:
                    if str(count_idx) in self.line_indexes["count_idxs"]:
                        for idx, l in enumerate(self.line_indexes["count_idxs"]):
                            if str(count_idx) == str(l):
                                break
                    else:
                        self.line_indexes[auto_label]["idx"] += 1
                        idx = self.line_indexes[auto_label]["idx"]
                        self.line_indexes["count_idxs"].append(count_idx)
                else:
                    idx = 0
                    self.line_indexes[auto_label] = {"idx": 0}
                    if "count_idxs" not in self.line_indexes:
                        self.line_indexes["count_idxs"] = [count_idx]
                    else:
                        if str(count_idx) in self.line_indexes["count_idxs"]:
                            for idx, l in enumerate(self.line_indexes["count_idxs"]):
                                if str(count_idx) == str(l):
                                    break

                print(
                    auto_label,
                    self.line_indexes[auto_label],
                    idx,
                    count_idx,
                    self.line_indexes["count_idxs"],
                )
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
        self.plot_lines = {}

        print("line_groups", self.line_groups)
        for skey in self._get_ydata(selected_keys, ydata):
            opts = None
            key = None
            for key in self.line_groups:
                if key in str(skey):
                    opts = self.line_groups[key]
                    if opts.get("label") == None:
                        opts["label"] = key
                    if opts.get("color") == None:
                        opts["color"] = "black"
                    if opts.get("marker") == None:
                        opts["marker"] = "o"
                    if key not in self.line_indexes:
                        self.line_indexes[key] = {"idx": 0, "auto": True}
            for sk in skey:
                if isinstance(ydata, list) or isinstance(ydata, tuple):
                    all_test = all(ykey in str(skey) for ykey in ydata)
                else:
                    all_test = ydata in str(sk)
                if all_test:
                    _label = None
                    for key in self.data_index_to_label:
                        if key in skey:
                            _label = self.data_index_to_label[key]
                    if _label is None:
                        if isinstance(sk, tuple):
                            _label = list(sk)[:]
                            if isinstance(ydata, list) or isinstance(ydata, tuple):
                                for yd in ydata:
                                    if yd in _label:
                                        _label.remove(yd)

                            else:
                                if ydata in _label:
                                    _label.remove(ydata)
                            if len(_label) == 1:
                                _label = _label[0]
                            if isinstance(_label, str) == False:
                                _label = " ".join(map(str, _label))
                        else:
                            _label = sk

                    plot_label = _label
                    cur_line = {}

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

                    if self.line_groups != {}:
                        for g_key in self.line_groups:
                            if g_key in str(skey):

                                plot_label.replace(g_key, "")
                                cur_line["color"] = self._get_color(
                                    g_key, count_idx=_label
                                )
                                _label = tuple([g_key, _label])
                    else:
                        cur_line["color"] = self._get_color(
                            plot_label, single_group=True
                        )
                        if cur_line.get("marker") == None:
                            cur_line["marker"] = "o"
                    cur_line["label"] = plot_label
                    self.plot_lines[_label] = cur_line
                    break
        print("line_groups", self.line_groups)
        print("plot_lines", self.plot_lines)

    def plot_line(self, xdata, ydata, axis_options=None, generate_plot=True):

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
        for group, items in self.line_groups.items():
            self.fig.plot_line([], [], **items)
        for linelabel, line in self.plot_lines.items():

            if line.get("label") in plotted_legend:
                line.pop("label")
            else:
                plotted_legend.append(line["label"])
            self.fig.plot_line(**line)

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
