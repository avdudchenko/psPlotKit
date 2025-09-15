from psPlotKit.data_plotter.fig_generator import figureGenerator
from psPlotKit.util.util_funcs import create_save_location
from psPlotKit.data_plotter.ps_line_plotter import linePlotter
import numpy as np

__author__ = "Alexander V. Dudchenko (SLAC)"


class boxPlotter:
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

    def _select_data(self, xkeys, ykeys):
        print(ykeys)
        self.psData.select_data(xkeys, require_all_in_dir=False)
        self.psData.select_data(ykeys, require_all_in_dir=False, add_to_existing=True)

    def define_line_groups(self, line_groups=None):
        self.line_groups = line_groups
        self.line_indexes = {}

    def define_index_labels(self, index_labels):
        self.data_index_to_label = index_labels

    def specify_line_colors(self, line_colors):
        self.line_indexes = {}
        for l in line_colors:
            self.line_indexes[l] = {"idx": line_colors[l], "auto": False}

    def _get_color(self, label, single_group=False):
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
                # print("auto", label)
                if single_group:
                    auto_label = "single_group"
                else:
                    auto_label = "auto_{}".format(label)

                if auto_label in self.line_indexes:
                    self.line_indexes[auto_label]["idx"] += 1
                    idx = self.line_indexes[auto_label]["idx"]

                else:
                    idx = 0
                    self.line_indexes[auto_label] = {"idx": 0}
                print(idx, label, auto_label)
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

                print(key, dkey, data)
                data_keys.append(tuple(skeys))
                data_list.append(data)
        return data_keys, data_list

    def _get_axis_label(self, label, units):
        return "{} ({})".format(label, units)

    def _get_ydata(self, selected_keys, ydata):
        ykey_data = []
        for skey in selected_keys:
            # print(skey, ydata)
            if isinstance(ydata, list) or isinstance(ydata, tuple):
                all_test = all(str(ykey) in str(skey) for ykey in ydata)
            else:
                all_test = ydata in str(skey)
            if all_test:
                ykey_data.append(skey)
                # print(ydata, skey)
        # print(ykey_data)
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

    def _test_key_in_key(self, test_key, key):
        if isinstance(test_key, (list, tuple)):
            all_test = all(str(yk) in str(key) for yk in test_key)
        else:
            all_test = str(test_key) in str(key)
        return all_test

    def _get_group_options(self, selected_keys, xdata, ydata):
        self.box_groups = {}
        self.boxes = {}
        self.box_positions = []
        # print("line_groups", self.line_groups)
        box_index = 0
        for ykey in ydata:
            for skey in self._get_ydata(selected_keys, ykey):
                for sk in skey:
                    if self._test_key_in_key(ykey, skey):
                        print("sk", skey, sk, ykey)
                        _label = None
                        max_delta = None
                        for key in self.data_index_to_label:

                            if self._test_key_in_key(key, skey):  #    key in skey:
                                _label = self.data_index_to_label[key]["label"]
                                if (
                                    self.data_index_to_label[key].get("position")
                                    != None
                                ):
                                    box_index = self.data_index_to_label[key].get(
                                        "position"
                                    )
                                if (
                                    self.data_index_to_label[key].get("max_delta")
                                    != None
                                ):
                                    max_delta = self.data_index_to_label[key].get(
                                        "max_delta"
                                    )
                        if _label is None:
                            if isinstance(sk, tuple):
                                _label = list(sk)[:]
                                if isinstance(ydata, list) or isinstance(ydata, tuple):
                                    for yd in ydata:
                                        print("t", _label, yd)
                                        if yd in _label:
                                            _label.remove(yd)

                                else:
                                    if ydata in _label:
                                        _label.remove(ydata)
                                if len(_label) == 1:
                                    _label = _label[0]
                                print(_label)
                                if isinstance(_label, str) == False:
                                    _label = " ".join(map(str, _label))
                            else:
                                _label = sk

                        plot_label = _label
                        # print("self.plot_lines", self.plot_lines)
                        cur_box = {}
                        raw_ydata = self.selected_data[skey]
                        raw_xdata = self.selected_data[self._replace_key(skey, xdata)]
                        min_range, max_range = np.min(raw_ydata.data), np.max(
                            raw_ydata.data
                        )

                        if (
                            abs(abs(min_range) - abs(max_range))
                            > np.max(raw_ydata.data) / 100
                        ) or max_delta is not None:

                            if max_delta is not None:
                                mx = max_delta
                            else:
                                mx = np.min([abs(min_range), abs(max_range)])
                            min_delta, max_delta = np.interp(
                                [-mx, mx], raw_ydata.data, raw_xdata.data
                            )
                            print(
                                "uniqual range",
                                skey,
                                min_range,
                                max_range,
                                "out",
                                min_delta,
                                max_delta,
                            )
                        else:
                            min_delta, max_delta = np.min(min_range), np.max(max_range)
                        _order = np.argsort([min_delta, max_delta])
                        if _order[0] > _order[1]:
                            cur_box["reversed"] = True
                        else:
                            cur_box["reversed"] = False
                        cur_box["x_pos"] = box_index
                        self.box_positions.append(box_index)
                        vals = np.array([min_delta, max_delta])[_order]
                        cur_box["x_value"] = vals[1] - vals[0]
                        cur_box["bottom"] = vals[0]
                        cur_box["width"] = 0.9
                        if self.xunit == None:
                            self.xunit = raw_xdata.mpl_units
                        if self.xdata_label == None:
                            self.xdata_label = raw_xdata.data_label
                        if self.yunit == None:
                            self.yunit = raw_ydata.mpl_units
                        if self.ydata_label == None:
                            self.ydata_label = raw_ydata.data_label
                        # if opts != None:
                        #     for key, val in opts.items():
                        #         cur_line[key] = val

                        if self.line_groups != {}:

                            for g_key in self.line_groups:
                                print("g_key", skey, g_key, g_key in str(skey))
                                if g_key in str(skey):
                                    _label = tuple([g_key, _label])
                                    plot_label.replace(g_key, "")
                                    if "color" in self.line_groups[g_key]:
                                        cur_box["color"] = self.line_groups[g_key][
                                            "color"
                                        ]
                                    else:
                                        cur_box["color"] = self._get_color(g_key)
                        else:
                            cur_box["color"] = self._get_color(
                                plot_label, single_group=True
                            )
                            if cur_box.get("marker") == None:
                                cur_box["marker"] = "o"
                        # cur_box["label"] = plot_label
                        self.boxes[_label] = cur_box
                        box_index += 1
                        break
        print("boxes", self.boxes)
        print("box_groups", self.box_groups)

    def plot_tornado_plot(
        self, xdata, ydata, axis_options=None, generate_plot=True, fig_options=None
    ):
        self._select_data(xdata, ydata)
        self.selected_data = self.psData.get_selected_data()
        self.psData.display()
        print("sk", self.selected_data.keys())
        self.generate_groups_lines = self._get_group_options(
            self.selected_data.keys(), xdata, ydata
        )
        self.index = 0
        if axis_options is None:
            self.axis_options = {}
        else:
            self.axis_options = axis_options
            self.axis_ticklabels = axis_options
        if self.axis_options.get("xlabel") == None:
            self.axis_options["xlabel"] = self._get_axis_label(
                self.xdata_label, self.xunit
            )
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

        self.ylabels = []
        idx = len(self.boxes.keys()) - 1
        print(self.boxes)
        for box_label, box in self.boxes.items():
            if box_label != self.ylabels:
                self.ylabels.append(box_label)
            box["vertical"] = False
            box["x_pos"] = idx - box["x_pos"]
            self.fig.plot_bar(**box)
        self.axis_ticklabels["yticklabels"] = self.ylabels[::-1]
        self.axis_ticklabels["yticks"] = np.array(self.box_positions) - 0.5

    def generate_figure(self):
        print(self.axis_options)
        self.fig.set_axis(**self.axis_options)
        self.fig.set_axis_ticklabels(**self.axis_ticklabels)
        self.fig.add_legend()
        if self.save_name == None:
            save_name = "Tornado {}".format(self.xdata_label)
        else:
            save_name = "Tornado {} - {} vs {}".format(self.save_name, self.xdata_label)
        self.fig.save(self.save_location, save_name)
        self.fig.show()
