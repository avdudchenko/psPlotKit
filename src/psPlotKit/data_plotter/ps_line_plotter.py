from psPlotKit.data_plotter.fig_generator import figureGenerator
from psPlotKit.util.util_funcs import create_save_location

__author__ = "Alexander V. Dudchenko "


class linePlotter:
    def __init__(
        self, PsData, save_location="", save_folder=None, save_name=None, show_fig=True
    ):
        self.save_location = create_save_location(save_location, save_folder)
        self.show_fig = show_fig
        self.select_data_key_list = []
        self.PsData = PsData
        self.define_line_colors()
        self.line_indexes = {}
        self.line_groups = {}
        self.xunit = None
        self.yunit = None
        self.xdata_label = None
        self.ydata_label = None
        self.save_name = save_name
        self.data_index_to_label = {}

    def _select_data(self, xdata, ydata):
        self.PsData.select_data(xdata, require_all_in_dir=False)
        self.PsData.select_data(ydata, require_all_in_dir=False, add_to_existing=True)

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
            if isinstance(label, str):
                label = [label]
            for key in label:
                if key in self.line_indexes:
                    idx = self.line_indexes[key]["idx"]
                    # print("lk", key, self.line_indexes[key])
                    break
            # print("idx", idx)
            if idx == None or single_group == False:
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

                # print(
                #     "color auto",
                #     auto_label,
                #     self.line_indexes[auto_label],
                #     idx,
                #     count_idx,
                #     self.line_indexes["count_idxs"],
                # )
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

        # print("line_groups", self.line_groups)
        for skey in self._get_ydata(selected_keys, ydata):
            # print("skey", skey)
            opts = None
            key = None
            for key in self.line_groups:
                if str(key) in str(skey):
                    opts = self.line_groups[key]
                    if opts.get("label") == None:
                        opts["label"] = key
                    if opts.get("color") == None and opts.get("marker") == None:
                        opts["color"] = "black"
                    if opts.get("marker") == None:
                        opts["marker"] = "o"
                    if key not in self.line_indexes:
                        self.line_indexes[key] = {"idx": 0, "auto": True}
                    # print("line_indexes", self.line_indexes)
            for sk in skey:
                # print("sk", sk)
                if isinstance(ydata, list) or isinstance(ydata, tuple):
                    all_test = all(ykey in str(skey) for ykey in ydata)
                else:
                    all_test = ydata in str(sk)
                if all_test:
                    _label = None

                    cur_line = {}

                    for key, item in self.data_index_to_label.items():
                        # print(key, key in skey)
                        if str(key) in str(skey):
                            if isinstance(item, dict):
                                _label = item["label"]
                                if item.get("marker") is not None:
                                    cur_line["marker"] = item.get("marker")
                                if item.get("markersize") is not None:
                                    cur_line["markersize"] = item.get("markersize")
                                if item.get("color") is not None:
                                    cur_line["color"] = item.get("color")
                            else:
                                _label = item
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
                            if str(g_key) in str(skey):

                                plot_label.replace(str(g_key), "")
                                # print(cur_line.get("color"), "curcolor")
                                if (
                                    cur_line.get("color") is None
                                    and cur_line.get("color") != "black"
                                ):
                                    cur_line["color"] = self._get_color(
                                        g_key, count_idx=_label
                                    )
                                    # print("getting coor")
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
        # print("line_groups", self.line_groups)
        # print("plot_lines", self.plot_lines)

    def plot_line(
        self, xdata, ydata, axis_options=None, fig_options={}, generate_plot=True
    ):

        self._select_data(xdata, ydata)
        self.selected_data = self.PsData.get_selected_data()
        self.selected_data.display()
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

        self.plot_imported_data(fig_options)

        if generate_plot:
            self.generate_figure()

        if self.save_name is not None:
            self.fig.save(self.save_location, self.save_name)

        if self.show_fig:
            self.fig.show()

        self.fig.close()

    def plot_imported_data(self, fig_options):
        if "fig_object" in fig_options:
            self.fig = fig_options.get("fig_object")
        else:
            self.fig = figureGenerator()

            self.fig.init_figure(**fig_options)
        plotted_legend = []
        # print("gen linegroups", self.line_groups)
        for group, items in self.line_groups.items():
            if "ax_idx" in fig_options:
                items["ax_idx"] = fig_options.get("ax_idx")
            if items.get("color") == None:
                items["color"] = "black"
            self.fig.plot_line([], [], **items)
        for linelabel, line in self.plot_lines.items():
            if "ax_idx" in fig_options:
                line["ax_idx"] = fig_options.get("ax_idx")
            if line.get("label") in plotted_legend:
                line.pop("label")
            else:
                plotted_legend.append(line["label"])
            # print(line)
            self.fig.plot_line(**line)

    def generate_figure(self):
        self.fig.set_axis(**self.axis_options)
        self.fig.add_legend(**self.axis_options)
