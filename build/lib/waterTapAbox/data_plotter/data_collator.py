from analysis_plot_kit.core import (
    fig_generator,
    data_import,
)
import quantities as qs
import numpy as np
import copy
import csv


class waterTAP_data_collator:
    def __init__(self, data_file, base_keys=None):
        if isinstance(data_file, str):
            self.data_manager = data_import.waterTAP_dataImport(
                data_file,
            )
            self.base_keys = base_keys
        else:
            self.data_manager = {}
            self.base_keys = {}
            for key, df in data_file.items():
                self.data_manager[key] = data_import.waterTAP_dataImport(
                    df["file"],
                )
                self.base_keys[key] = df["base_keys"]
            # print(self.base_keys)
        self.plot_indexes = None
        self.usd_base = "USD_2018"
        qs.USD = qs.UnitQuantity(self.usd_base)

        self.base_cost_unit = qs.USD / qs.m**3
        self.default_units = [qs.USD, qs.kWh]
        self.base_iter_key = None
        self.x_ref = None
        self.map_mode = False
        self.loop_map = None
        self.only_feasible = True
        self.return_absolute = False
        # self.updateKeySet()

    def setBaseCostUnit(self, base_unit):
        self.usd_base = usd_base
        qs.USD = qs.UnitQuantity(usd_base)

    def updateKeySet(self, data_manager=None, keys=None, new_key_set=True):
        """Updat key set for datamanager.

        Keyword arguments:
        data_manager -- specify a datamanager
        keys -- specify keys to add to base_key set
        new_key_set -- if true, replace existing set with new "keys" (default True)

        """
        base_keys = self.base_keys.copy()
        if isinstance(self.data_manager, dict):
            if data_manager is not None:
                if new_key_set:
                    self.base_keys[data_manager] = keys
                    base_keys[data_manager] = keys
                else:
                    base_keys[data_manager] = self.base_keys[data_manager] + keys

            for key, manager in self.data_manager.items():
                if self.base_iter_key is not None:
                    base_keys[key] = base_keys[key] + self.base_iter_key
                # print(base_keys)
                manager.set_data_keys(base_keys[key])
        else:
            if keys is not None:
                if new_key_set:
                    self.base_keys = keys
                    base_keys = keys
                else:
                    base_keys = self.base_keys + keys
            if self.base_iter_key is not None:
                base_keys = base_keys + self.base_iter_key
            # print("updated base_keys", base_keys, self.base_iter_key)
            self.data_manager.set_data_keys(base_keys)
        # print(base_keys)

    def get_unit(self, data_keys):
        if isinstance(data_keys, dict):
            unit = data_keys["unit"]
        else:
            unit = self.data_manager.get_data_set(
                data_keys,
                sub_key="units",
                only_feasible=False,
                convert=None,
                datatype=str,
            )
        # print("got unit", data_keys, unit)
        if "/a" in str(unit):
            unit = str(unit).replace("/a", "")
            if unit == "1":
                unit = "None"
        # print("unit is", data_keys, unit)
        if unit == "None" or unit == None:
            return 1
        else:
            return qs.CompoundUnit(str(unit))

    def get_scenarios(self, data_key, convert):
        """Function that either grabs directly, or grabs scenrarios
        specified by user. Scanrio info is gotten from global options
        dict (self.auto_gen_dict)

        Keyword arguments:
        data_key -- the variable key used for the data set
        convert -- value to convert grabed out put by

        """
        if "case_options" in self.auto_gen_dict.keys():
            case_idxs = []
            results = []
            for case, case_dict in self.auto_gen_dict["case_options"].items():
                # print("got case options", case_dict)
                if case_dict.get("data_keys") is not None:
                    self.updateKeySet(
                        keys=case_dict.get("data_keys"), new_key_set=False
                    )
                # print("--------------scenraio key", data_key)
                if isinstance(data_key, np.ndarray):
                    results.append(data_key)
                else:
                    result = self._grab_data(data_key, convert)
                    idx = []
                    # print(result.shape)
                    temp_results = copy.deepcopy(result)
                    # #print("temp_results.shape", temp_results.shape)
                    # print(case_dict)
                    fs_options = list(case_dict.keys())
                    try:
                        fs_options.remove("data_keys")
                        fs_options.remove("plot_options")
                    except ValueError:
                        pass
                    for case_key, case_value in case_dict.items():
                        if case_key != "data_keys" and case_key != "plot_options":
                            case_values = self.get_data(case_key)
                            if idx != []:
                                case_values = case_values[idx]
                            # print("cv", case_values)
                            # print("ck", case_key, case_value, case_values)
                            idx = np.where(np.abs(case_values - case_value) < 1e-8)
                            # print(idx, temp_results)
                            # print(
                            #     "temp_results.shape",
                            #     temp_results.shape,
                            #     np.array(idx).shape,
                            #     #print(idx),
                            # )
                            if (
                                len(temp_results.shape) == 1
                            ):  # and len(fs_options) == 1:
                                temp_results = temp_results[idx]
                            # elif len(temp_results.shape) == 1 and len(fs_options) > 1:
                            #     temp_results = temp_results
                            else:
                                tmp = []
                                for k in range(temp_results.shape[0]):
                                    try:
                                        if len(temp_results[k][idx]) == 1:
                                            tmp.append(temp_results[k][idx][0])
                                        else:
                                            tmp.append(temp_results[k][idx])
                                    except:
                                        tmp.append(temp_results[k][idx])
                                    # print(k, tmp)
                                temp_results = np.array(tmp)

                            # idx_all = np.array(idx_all)
                            # else:
                            #     temp_results = temp_results[idx]
                            # #print(temp_results)
                            # #print(
                            #     "temp_results.shape",
                            #     temp_results.shape,
                            #     np.array(idx_all).shape,
                            # )
                            # t##emp_results = temp_results[idx_all]
                        ###print(temp_results)
                    # print("#print(temp_results)", temp_results)

                    results.append(temp_results)
                    # if scenario_idxs == []:
                    #     scenario_idxs = idx
                    # else:
                    #     #print("kept", case_key, scenario_idxs, idx)

                    #     scenario_idxs = scenario_idxs[scenario_idxs == idx]
                    #     #print("kept", case_key, scenario_idxs, idx)
                    # case_idxs.append(scenario_idxs)
            # print(results)
            return results
        else:
            result = self._grab_data(data_key, convert)
            return result

    def _grab_data(self, data_key, convert=None):
        """Base function for getting data.

        Keyword arguments:
        data_key -- the variable key used for the data set
        convert -- value to convert grabed out put by

        """
        # print(
        #     "grab-data",
        #     data_key,
        #     isinstance(data_key, np.ndarray),
        #     isinstance(data_key, dict),
        # )
        if isinstance(data_key, dict):
            if "math_keys" in data_key.keys():
                data_dict = {}
                if "loop_list" in data_key["math_keys"].keys():
                    for key, item in data_key["math_keys"].items():
                        if key != "loop_list":
                            # print("-------------key", item)
                            if "{}" in item:
                                # #print(item)
                                data_array = []
                                for l in data_key["math_keys"]["loop_list"]:
                                    try:
                                        # print(l)
                                        result = self.get_data(item.format(l))
                                        # print(l, len(result))
                                        # result_data = []
                                        # for r in result:
                                        #     if isinstance(r, np.ndarray) or isinstance(
                                        #         r, list
                                        #     ):
                                        #         # #print(r, len(r))
                                        #         # #print(l,r)
                                        #         if len(r) > 1:
                                        #             result_data.append(r)
                                        #             # #print("any added")
                                        #         elif len(r) == 1 and r[0] == r[0]:
                                        #             result_data.append(r)
                                        #             # #print("any 2 added")
                                        #     else:
                                        #         if r == r:
                                        #             result_data.append(r)
                                        # #print(item.format(l), result_data)
                                        data_array.append(result)
                                    except KeyError:
                                        pass

                            elif isinstance(item, np.ndarray):
                                data_array = item
                            else:
                                data_array = self.get_data(item)
                            # print(data_array)
                            # for k in data_array:
                            #     #print(len(k))
                            # print("data_array", np.array(data_array).shape)
                            data_dict[key] = data_array
                elif "format_key" in data_key["math_keys"].keys():
                    data_dict = {}
                    result = []
                    for key, item in data_key["math_keys"].items():
                        result = []
                        if key not in ["format_key", "expression", "convert"]:
                            for k in self.auto_gen_dict["data_loops"]["import_keys"]:
                                try:
                                    re = self.get_data(item.format(k))
                                    result.append(re)
                                except (IndexError, KeyError):
                                    # #print("failed getting", item.format(k))
                                    result.append(np.zeros(result[-1].shape))
                                    pass
                        data_dict[key] = result
                    convert = data_key.get("convert")
                else:
                    for key, item in data_key["math_keys"].items():
                        data_dict[key] = self.get_data(item)

                # print(data_key, data_dict)
                if isinstance(data_key["expression"], str):
                    if "np." in data_key["expression"]:
                        data_dict["np"] = np
                    result = eval(data_key["expression"], data_dict)
                else:
                    result = data_key["expression"](
                        data_dict, data_key["math_keys"]["loop_list"]
                    )
                convert = data_key.get("convert")
            elif "loop_key" in data_key.keys():
                result = None
                for k in data_key["loop_list"]:
                    try:
                        if result is None:
                            result = self.get_data(data_key["loop_key"].format(str(k)))
                        else:
                            result = result + self.get_data(
                                data_key["loop_key"].format(str(k))
                            )

                        # #print(
                        #     "got key {} {}".format(
                        #         k, data_key["loop_key"].format(str(k))
                        #     )
                        # )
                    # #print(result)
                    except KeyError:
                        print(
                            "Not item {} for key {}".format(
                                k, data_key["loop_key"].format(str(k))
                            )
                        )
            elif "format_key" in data_key.keys():
                result = []
                for k in self.auto_gen_dict["data_loops"]["import_keys"]:
                    try:
                        d_key = data_key["key"]
                        re = self.get_data(d_key.format(k))
                        result.append(re)
                    except (IndexError, KeyError):
                        # print("failed getting", d_key.format(k))
                        result.append(np.zeros(result[-1].shape))
                        pass
                convert = data_key.get("convert")
                # #print(result)
            else:
                # #print(data_key)
                convert = data_key.get("convert")
                d_key = data_key["key"]
                result = self.get_data(d_key)
                # convert = data_key.get("convert")
        elif isinstance(data_key, np.ndarray):
            result = data_key
        else:
            result = self.get_data(data_key)
        result = np.nan_to_num(result, 0)
        if convert is not None:
            # for k in result:
            #     #print(len(k))
            # #print(result, convert)
            result = np.array(result, dtype=float) * convert
        # self.only_feasible = True
        # print(result)
        return result

    def grab_data(self, axis=None, data_key=None):
        if axis != None:
            data_key = self.auto_gen_dict.get(axis)
            # #print(data_key)
            if "xdata" in axis:
                convert = self.auto_gen_dict.get("xconvert")
            if "ydata" in axis:
                convert = self.auto_gen_dict.get("yconvert")
            if "zdata" in axis:
                convert = self.auto_gen_dict.get("zconvert")
        else:
            convert = self.auto_gen_dict.get("convert")

        result = self.get_scenarios(data_key, convert)

        if self.plot_indexes is not None:
            return result[self.plot_indexes]
        else:
            return result

    def get_data(self, data_key):
        if isinstance(data_key, np.ndarray):
            return data_key
        if "only_feasible" in self.auto_gen_dict:
            self.only_feasible = self.auto_gen_dict["only_feasible"]
            # print("only_feasible", self.only_feasible)
        if isinstance(self.data_manager, dict):
            # print(self.data_manager)
            # for mn in self.data_manager:
            # print(mn == "Softening")
            # print(self.data_manager[mn])
            data_manager = self.data_manager[self.cur_manager]
        else:
            data_manager = self.data_manager
        if "updateBaseKeys" in self.auto_gen_dict:
            # print("updateBaseKeys", self.auto_gen_dict["updateBaseKeys"])
            self.updateKeySet(
                data_manager, self.auto_gen_dict["updateBaseKeys"], new_key_set=False
            )
        if "loop_options" not in self.auto_gen_dict:
            if "diff_mode" in self.auto_gen_dict:
                result = data_manager.get_diff(
                    data_key, return_absolute=self.return_absolute
                )
            else:
                try:
                    result = data_manager.get_sweep(
                        data_key, only_feasible=self.only_feasible
                    )
                except:
                    result = data_manager.get_output(
                        data_key, only_feasible=self.only_feasible
                    )

        else:
            loop_options = self.auto_gen_dict["loop_options"]
            if "stack_data" in self.auto_gen_dict.keys():
                stack_data = self.auto_gen_dict["stack_data"]
            else:
                if self.map_mode:
                    stack_data = True
                else:
                    stack_data = False
            try:
                if data_key != "loop_key":
                    if "diff_mode" in self.auto_gen_dict:
                        result, self.loop_map = data_manager.retrive_loop_data(
                            loop_options["loop_key"],
                            loop_options["loop_values"],
                            data_key,
                            stack_data=stack_data,
                            get_diff=True,
                            return_loop_map=True,
                            only_feasible=self.only_feasible,
                            return_absolute=self.return_absolute,
                        )
                    else:
                        # print(
                        #     "data_key",
                        #     data_key,
                        #     loop_options["loop_key"],
                        #     loop_options["loop_values"],
                        #     "stack_data",
                        #     stack_data,
                        # )
                        result, self.loop_map = data_manager.retrive_loop_data(
                            loop_options["loop_key"],
                            loop_options["loop_values"],
                            data_key,
                            stack_data=stack_data,
                            get_sweep=False,
                            return_loop_map=True,
                            only_feasible=self.only_feasible,
                        )
                    # #print("result", result, self.loop_map, data_key)
                else:
                    result = self.loop_map
            except:
                result = data_manager.retrive_loop_data(
                    loop_options["loop_key"],
                    loop_options["loop_values"],
                    data_key,
                    stack_data=stack_data,
                    get_sweep=True,
                    only_feasible=self.only_feasible,
                )

        if "reduce_function" in self.auto_gen_dict:
            result = self.auto_gen_dict["reduce_function"](
                data_manager, self.auto_gen_dict, result, self.x_ref
            )
        # #print("result ", result)
        return result

    def plot_map(self, show):
        figure = fig_generator.figureGenerator(**self.auto_gen_dict)
        figure.init_figure(**self.auto_gen_dict)

        self.map_mode = True
        # print("assuming we are plotting map, auto generating!")
        self.auto_gen_dict["zdata"] = self.grab_data(axis="zdata")
        self.auto_gen_dict["xdata"] = self.grab_data(axis="xdata")
        self.auto_gen_dict["ydata"] = self.grab_data(axis="ydata")
        if "norm_z_axis" in self.auto_gen_dict:
            x = self.auto_gen_dict["norm_z_axis"]["x"]
            y = self.auto_gen_dict["norm_z_axis"]["y"]
            # print(self.auto_gen_dict["xdata"])
            b_idx = np.where(
                (abs(np.array(self.auto_gen_dict["xdata"]) - x) < 1e-8)
                & (abs(np.array(self.auto_gen_dict["ydata"]) - y) < 1e-8)
            )  # [0]
            # print(b_idx)
            norm_z = self.auto_gen_dict["zdata"][b_idx]
            self.auto_gen_dict["zdata"] = (
                (self.auto_gen_dict["zdata"] - norm_z) / norm_z * 100
            )
        # self.auto_gen_dict["zdata"] = self.grab_data("zdata")
        if "vmin" not in self.auto_gen_dict.keys():
            if "zticks" not in self.auto_gen_dict.keys():
                self.auto_gen_dict["vmin"] = min(self.auto_gen_dict["zdata"])
            else:
                self.auto_gen_dict["vmin"] = min(self.auto_gen_dict["zticks"])
        if "vmax" not in self.auto_gen_dict.keys():
            if "zticks" not in self.auto_gen_dict.keys():
                self.auto_gen_dict["vmax"] = max(self.auto_gen_dict["zdata"])
            else:
                self.auto_gen_dict["vmax"] = max(self.auto_gen_dict["zticks"])
        if self.auto_gen_dict.get("contour_plot"):
            self.auto_gen_dict["plot_contour"] = self.auto_gen_dict["zticks"]
            # self.auto_gen_dict["plot_contour_lines"] = self.auto_gen_dict["zticks"]
            # self.auto_gen_dict[plot_contour]=self.auto_gen_dict["zticks"]
        if self.auto_gen_dict.get("zoverlay"):
            self.auto_gen_dict["zoverlay"] = self.grab_data(
                data_key=self.auto_gen_dict.get("zoverlay")
            )
            # print(self.auto_gen_dict["zoverlay"])
            # asss
        if self.auto_gen_dict.get("digitize"):
            self.auto_gen_dict["digitize_levels"] = self.auto_gen_dict[
                "zticks"
            ]  #  'zticks'
        style = self.auto_gen_dict.get("plot_style", "map")
        if style == "map":
            figure.plot_map(**self.auto_gen_dict)
        else:
            figure.plot_scatter(**self.auto_gen_dict)
        # self.add_custom_legend(figure, plot_type="line")
        figure.add_colorbar(**self.auto_gen_dict)
        if style == "map":
            figure.set_axis_ticklabels(**self.auto_gen_dict)
        else:
            figure.set_axis(**self.auto_gen_dict)
        self.add_custom_legend(figure, plot_type="line")
        figure.save()
        if show:
            figure.show()

    def plot_cost_breakdown(self, show):
        figure = fig_generator.figureGenerator(**self.auto_gen_dict)
        figure.init_figure(**self.auto_gen_dict)
        self.x_ref = self.auto_gen_dict["xdata"]
        self.auto_gen_dict["xdata"] = self.grab_data("xdata")
        old_vals = 0 * qs.USD / qs.m**3
        for key, group_dict in self.auto_gen_dict["cost_options"][
            "cost_groups"
        ].items():
            if "use_line_plot_key_in_base_key" in self.auto_gen_dict.keys():
                if self.auto_gen_dict["use_line_plot_key_in_base_key"]:
                    self.base_iter_key = [key]
            for kt, key_type in enumerate(
                self.auto_gen_dict["cost_options"]["plot_cost_types"].keys()
            ):
                type_options = self.auto_gen_dict["cost_options"]["plot_cost_types"][
                    key_type
                ]
                if isinstance(old_vals, np.ndarray):
                    ydata = group_dict[key_type] + old_vals
                else:
                    ydata = group_dict[key_type]

                if kt == 0:
                    lb = key
                else:
                    lb = ""
                unit = str(ydata.units).strip("1.0 ")
                # if 'zorder' in group_dict["plot_options"]:
                #     zorder=group_dict["plot_options"]['zorder']
                # else:
                #     zorder=1
                # if 'linewidth' in group_dict["plot_options"]:
                #     linewidth= group_dict["plot_options"]['linewidth']
                # else:
                #     linewidth=1,
                figure.plot_area(
                    xdata=self.auto_gen_dict["xdata"],
                    ydata=ydata,
                    y2data=old_vals,
                    hatch=type_options.get("hatch"),
                    label=lb,
                    save_label="{} {} ({})".format(key, key_type, unit),
                    **group_dict["plot_options"],
                )
                old_vals = ydata
        if len(self.auto_gen_dict["cost_options"]["plot_cost_types"].keys()) > 1:
            for kt, key_type in enumerate(
                self.auto_gen_dict["cost_options"]["plot_cost_types"].keys()
            ):
                type_options = self.auto_gen_dict["cost_options"]["plot_cost_types"][
                    key_type
                ]
                figure.plot_area(
                    xdata=[],
                    ydata=[],
                    hatch=type_options["hatch"],
                    color="white",
                    label=key_type,
                )
        self.auto_gen_dict.update({"reverse_legend": True})
        self.add_custom_legend(figure, "line")
        figure.set_axis(**self.auto_gen_dict)
        figure.add_legend(**self.auto_gen_dict)

        figure.save()
        if show:
            figure.show()

    def plot_line(self, show):
        def check_legend(legend_dict):
            # print(legend_dict)
            if isinstance(legend_dict, str):
                legend_dict = {"label": legend_dict}
            else:
                legend_dict = legend_dict.copy()
            if "color" not in legend_dict.keys():
                legend_dict["color"] = "black"
            if "ls" not in legend_dict.keys():
                legend_dict["ls"] = "-"
            if "marker" not in legend_dict.keys():
                legend_dict["marker"] = ""
            return legend_dict

        def add_base_point(local_dict, xdata, ydata):
            if "basevalue" in local_dict:
                b_idx = np.where(
                    np.isclose(
                        np.array(xdata, dtype=float), float(local_dict["basevalue"])
                    )
                )[0]
                # [0]
                # print("bidx", b_idx)
                if len(b_idx) != 0:
                    plot_opt = {}
                    if "color" not in local_dict.keys():
                        plot_opt["color"] = "black"
                    else:
                        plot_opt["color"] = local_dict["color"]
                    plot_opt["markerfacecolor"] = "white"
                    plot_opt["marker"] = "*"
                    plot_opt["ls"] = None
                    plot_opt["log_data"] = False
                    plot_opt["markersize"] = 10
                    # #print(plot_opt)
                    if self.auto_gen_dict.get("norm_useing_basevalue") is None:
                        figure.plot_line(
                            [xdata[b_idx]], [ydata[b_idx]], zorder=10, **plot_opt
                        )
                    # if "norm_useing_basevalue" in self.auto_gen_dict.keys():
                    # if self.auto_gen_dict["norm_useing_basevalue"] == False:
                    #     figure.plot_line(
                    #         [xdata[b_idx]], [ydata[b_idx]], zorder=10, **plot_opt
                    #     )
                    return b_idx, xdata[b_idx[0]], ydata[b_idx[0]]
                else:
                    print(
                        "failed to find value",
                        b_idx,
                        float(local_dict["basevalue"]),
                        np.array(xdata, dtype=float),
                    )
            else:
                return None

        def plot_line(input_dict, xdata, ydata, gen_legend, marker_overlay):
            local_dict = input_dict.copy()
            if "xdata" in local_dict:
                local_dict.pop("xdata")
            if "ydata" in local_dict:
                local_dict.pop("ydata")
            if "marker_overlay" in local_dict:
                local_dict.pop("marker_overlay")
            norm_val = add_base_point(local_dict, xdata, ydata)
            if "color" not in local_dict:
                default_plot_opitons = self.auto_gen_dict.get("default_plot_options")
                # print("applitng dpo", default_plot_opitons)
                if default_plot_opitons is not None:
                    for key, item in default_plot_opitons.items():
                        if key not in local_dict:
                            local_dict[key] = item
            if "norm_useing_basevalue" in self.auto_gen_dict.keys():
                if self.auto_gen_dict["norm_useing_basevalue"]:
                    ydata = (ydata - norm_val[2]) / norm_val[2] * 100
            if gen_legend == False:
                local_dict["label"] = None
            # local_dict.pop("label")
            # local_dict["save_label"] = local_dict["ylabel"]
            # print("local dict", local_dict)
            # print(xdata, ydata)
            figure.plot_line(xdata, ydata, marker_overlay=marker_overlay, **local_dict)

        def plot_lines(m_key=None, m_options=None, gen_legend=True):
            # print("lg", line_group["ydata"])
            if isinstance(line_group["ydata"], list):
                custom_legend = None
                for ydata_dict in line_group["ydata"]:
                    # print(gen_legend)
                    # local_dict = ydata_dict.copy()
                    self.x_ref = line_group["xdata"]

                    ydata = self.grab_data(data_key=ydata_dict)
                    xdata = self.grab_data(data_key=line_group["xdata"])
                    if "marker_overlay" in local_dict:
                        local_dict["marker_overlay"] = self.grab_data(
                            data_key=local_dict["marker_overlay"]
                        )
                    else:
                        local_dict["marker_overlay"] = None
                    scenarios = self.auto_gen_dict.get("case_options")
                    if scenarios is not None:
                        scenarios = scenarios.keys()
                    else:
                        scenarios = [None]
                    for i, k in enumerate(scenarios):
                        local_dict = ydata_dict.copy()
                        if k == None:
                            ydatal = ydata
                            xdatal = xdata
                            marker_overlay = local_dict["marker_overlay"]
                            s_label = ""
                        else:
                            ydatal = ydata[i]
                            xdatal = xdata[i]
                            if local_dict["marker_overlay"] is None:
                                marker_overlay = None
                            marker_overlay = local_dict["marker_overlay"][i]
                            s_label = " " + k
                        if isinstance(ydatal, np.ndarray):
                            if m_options is not None:
                                local_dict.update(m_options)
                                local_dict.update(
                                    {
                                        "save_label": m_options["manager_label"]
                                        + " "
                                        + ydata_dict["label"]
                                        + " "
                                        + line_group["ylabel"]
                                        + s_label
                                    }
                                )
                            else:
                                # print(ydata_dict)
                                ylabel = ydata_dict.get("label")
                                if ylabel == None:
                                    ylabel = ""
                                else:
                                    ylabel = ylabel + " "
                                local_dict.update(
                                    {"save_label": ylabel + line_group["ylabel"]}
                                )
                            if k is not None:
                                # print("scenarios", scenarios, gen_legend)
                                # print(local_dict)
                                # assert False
                                for key, value in self.auto_gen_dict["case_options"][k][
                                    "plot_options"
                                ].items():
                                    if i == 0:
                                        if custom_legend is None:
                                            custom_legend = []
                                        custom_legend.append(copy.deepcopy(local_dict))
                                    if key not in local_dict:
                                        local_dict[key] = value
                                    local_dict["label"] = ""
                                    custom_legend
                            # print(m_key)
                            if m_key != None:
                                gl = False
                            else:
                                gl = gen_legend
                            plot_line(local_dict, xdatal, ydatal, gl, marker_overlay)
                if gen_legend and m_key != None:
                    for ydata_dict in line_group["ydata"]:
                        legend_dict = check_legend(ydata_dict)
                        figure.plot_line([], [], **legend_dict)
                if custom_legend is not None:
                    for ydata_dict in custom_legend:
                        legend_dict = check_legend(ydata_dict)
                        figure.plot_line([], [], **legend_dict)
                if scenarios is not None:
                    # print("-----------------checking gen")
                    # assert False
                    for scenario in self.auto_gen_dict.get("case_options"):
                        if (
                            "plot_options"
                            in self.auto_gen_dict["case_options"][scenario]
                        ):
                            legend_dict = check_legend(
                                self.auto_gen_dict["case_options"][scenario][
                                    "plot_options"
                                ]
                            )
                            figure.plot_line([], [], **legend_dict)
            else:
                local_dict = line_group.copy()
                self.x_ref = line_group["xdata"]
                local_dict["ydata"] = self.grab_data(data_key=local_dict["ydata"])
                local_dict["xdata"] = self.grab_data(data_key=local_dict["xdata"])
                if "marker_overlay" in local_dict:
                    local_dict["marker_overlay"] = self.grab_data(
                        data_key=local_dict["marker_overlay"]
                    )
                else:
                    local_dict["marker_overlay"] = None
                if isinstance(local_dict["ydata"], np.ndarray) or isinstance(
                    local_dict["ydata"], list
                ):
                    scenarios = self.auto_gen_dict.get("case_options")
                    if scenarios is not None:
                        scenarios = scenarios.keys()
                    else:
                        scenarios = [None]
                    # print(scenarios)
                    for i, k in enumerate(scenarios):
                        if k == None:
                            ydatal = local_dict["ydata"]
                            xdatal = local_dict["xdata"]
                            marker_overlay = local_dict["marker_overlay"]
                            s_label = line_group["ylabel"]
                        else:
                            ydatal = local_dict["ydata"][i]
                            xdatal = local_dict["xdata"][i]
                            if local_dict["marker_overlay"] is None:
                                marker_overlay = None
                            else:
                                marker_overlay = local_dict["marker_overlay"][i]
                            s_label = k + " " + line_group["ylabel"] + k
                        if k is not None:
                            sc = self.auto_gen_dict.get("case_options")[k]
                            # print(sc)
                            local_dict.update(sc.get("plot_options"))
                        local_dict.update({"save_label": s_label})
                        # print(local_dict)
                        if m_key != None:
                            gl = False
                        else:
                            gl = gen_legend
                        plot_line(local_dict, xdatal, ydatal, gl, marker_overlay)
                    # if scenarios is not None:
                    #     for scenario in self.auto_gen_dict.get("case_options"):
                    #         if "plot_options" not in scenario:
                    #             legend_dict = check_legend(scenario)
                    #             figure.plot_line([], [], **legend_dict)

        def manager_logic(m_key, m_options, gen_legend=True):
            self.cur_manager = m_key
            plot_lines(m_key, m_options, gen_legend)

        def reg_logic(m_key, m_options, gen_legend):
            m_options = None
            plot_lines()

        def loop_logic(
            loop_dict, plot_func, m_key=None, m_options_org=None, gen_legend=True
        ):
            # m_options = m_options.copy()
            for li, value in enumerate(loop_dict["loop_values"]):
                if m_options_org is not None:
                    m_options = m_options_org.copy()
                else:
                    m_options = None
                self.updateKeySet(
                    data_manager=m_key,
                    keys=[loop_dict["loop_key"], value],
                    new_key_set=False,
                )

                if "labels" in loop_dict.keys():
                    l_label = loop_dict["labels"][li]
                    if m_options is not None:
                        m_options["manager_label"] = (
                            m_options["manager_label"] + " " + l_label
                        )
                    line_group.update({"label": l_label})
                if "markers" in loop_dict.keys():
                    line_group.update({"marker": loop_dict["markers"][li]})
                if "colors" in loop_dict.keys():
                    line_group.update({"color": loop_dict["color"][li]})
                # print("pls", line_group, gen_legend, m_options)
                plot_func(m_key, m_options, gen_legend=gen_legend)

        def line_logic():
            gen_legend = True
            if "data_managers" in local_dict.keys():
                if "data_loops" in local_dict.keys():
                    for m_key, m_options in local_dict["data_managers"].items():
                        if "gen_sub_labels" in m_options:
                            gen_legend = m_options["gen_sub_labels"]
                        loop_dict = local_dict["data_loops"][m_key]
                        # print("m_opt", m_options)
                        if "color" in m_options.keys():
                            line_group.update({"color": m_options["color"]})

                        legend_dict = check_legend(m_options)
                        legend_dict["label"] = m_options["manager_label"]

                        figure.plot_line([], [], **legend_dict)
                        loop_logic(
                            loop_dict,
                            manager_logic,
                            m_key,
                            m_options,
                            gen_legend=gen_legend,
                        )
                        gen_legend = False
                else:
                    for m_key, m_options in local_dict["data_managers"].items():
                        if "gen_sub_labels" in m_options:
                            gen_legend = m_options["gen_sub_labels"]
                        if "color" in m_options.keys():
                            line_group.update({"color": m_options["color"]})
                        legend_dict = check_legend(m_options)
                        legend_dict["label"] = m_options["manager_label"]
                        figure.plot_line([], [], **legend_dict)

                        manager_logic(m_key, m_options, gen_legend=gen_legend)
                        gen_legend = False
            else:
                if "data_loops" in local_dict.keys():
                    loop_dict = local_dict["data_loops"]
                    loop_logic(loop_dict, plot_lines)
                else:
                    plot_lines()

        for group_key, line_group in self.auto_gen_dict["line_plots"].items():
            if "use_line_plot_key_in_base_key" in self.auto_gen_dict.keys():
                if self.auto_gen_dict["use_line_plot_key_in_base_key"]:
                    self.base_iter_key = [group_key]
                    self.updateKeySet()
            local_dict = self.auto_gen_dict.copy()
            local_dict.update({"file_name": group_key})
            figure = fig_generator.figureGenerator(**local_dict)
            figure.init_figure(**local_dict)
            gen_legend = True

            line_logic()
            self.add_custom_legend(figure, plot_type="line")
            if (
                "global_yticks" in self.auto_gen_dict.keys()
                and "yticks" not in line_group.keys()
            ):
                line_group["yticks"] = self.auto_gen_dict["global_yticks"]
                line_group["ylabel"] = self.auto_gen_dict["global_ylabel"]
            figure.set_axis(**line_group)
            figure.add_legend(**line_group)
            figure.save()
            if show:
                figure.show()

    def add_custom_legend(self, figure, plot_type="line"):
        if "custom_legend" in self.auto_gen_dict:
            for key, item in self.auto_gen_dict["custom_legend"].items():
                if "save_label" not in item:
                    item["save_label"] = False
                if "plot_type" in item:
                    pl = item.get("plot_type")
                else:
                    pl = plot_type
                if item.get("label") == None:
                    item.update({"label": key})
                if pl == "line":
                    # #print(item)
                    # item.update({"label": key})
                    x = item.get("x")
                    y = item.get("y")
                    if x == None:
                        x = []
                        y = []

                    figure.plot_line(x, y, **item)
                if pl == "bar":
                    x = item.get("x")
                    y = item.get("y")
                    if x == None:
                        x = [0]
                        y = [0]
                    figure.plot_bar(x, y, **item)
                if pl == "area":
                    x = item.get("x")
                    y = item.get("y")
                    if x == None:
                        x = []
                        y = []
                    figure.plot_area(x, y, **item)
            figure.add_legend()

    def plot_tornado_plot(self, show):
        def get_base_point(local_dict, xdata, ydata):
            if "basevalue" in local_dict:
                b_idx = np.where(
                    np.isclose(
                        np.array(xdata, dtype=float), float(local_dict["basevalue"])
                    )
                )[0]
                # print(xdata, ydata, b_idx)
                return xdata[b_idx], ydata[b_idx]
            else:
                return None

        def get_data(m_key=None, m_options=None, gen_legend=True):
            return_dict = {}
            if isinstance(tornado_group["ydata"], list):
                labels = []
                for ydata_dict in tornado_group["ydata"]:
                    local_dict = ydata_dict.copy()
                    self.x_ref = local_dict["xdata"]
                    self.return_absolute = False
                    ydata = self.grab_data(data_key=ydata_dict)
                    self.return_absolute = True
                    xdata = self.grab_data(data_key=tornado_group["xdata"])
                    scenarios = self.auto_gen_dict.get("case_options")
                    if scenarios is not None:
                        scenarios = scenarios.keys()
                    else:
                        scenarios = [None]

                    return_dict["xdata"] = xdata
                    for i, k in enumerate(scenarios):
                        local_dict = ydata_dict.copy()
                        if k == None:
                            ydatal = ydata
                            xdatal = xdata
                            s_label = ""
                        else:
                            ydatal = ydata[i]
                            xdatal = xdata[i]
                            s_label = " " + k
                        base_value = get_base_point(local_dict, xdatal, ydatal)
                        if "diff_mode" in self.auto_gen_dict:
                            max_filter = np.max(np.abs(ydata))
                            delta = abs(
                                local_dict["nominal_lb"] - local_dict["nominal_ub"]
                            )
                            return_dict["ydata"] = (ydata / (xdata * delta) * 100)[
                                ydata != max_filter
                            ]
                        else:
                            return_dict["ydata"] = ydata
                        if base_value is not None:
                            return_dict["ydata_norm"] = (
                                (ydata - base_value[1]) / base_value[1] * 100.0
                            )
                        else:
                            return_dict["ydata_norm"] = None

                        return_dict["label"] = tornado_group["xlabel"]
                        return_dict["color"] = tornado_group["color"]
            else:
                local_dict = tornado_group.copy()
                self.x_ref = local_dict["xdata"]
                self.return_absolute = False
                ydata = self.grab_data(data_key=local_dict["ydata"])
                self.return_absolute = True
                xdata = self.grab_data(data_key=local_dict["xdata"])
                scenarios = self.auto_gen_dict.get("case_options")

                if scenarios is not None:
                    scenarios = scenarios.keys()
                else:
                    scenarios = [None]
                # print(scenarios)
                # print(local_dict)
                for i, k in enumerate(scenarios):
                    return_dict["xdata"] = xdata
                    if k == None:
                        ydatal = ydata
                        xdatal = xdata
                        # s_label = line_group["ylabel"]
                    else:
                        ydatal = ydata[i]
                        xdatal = xdata[i]
                    base_value = get_base_point(local_dict, xdatal, ydatal)
                    # #print("bs", base_value)
                    if "diff_mode" in self.auto_gen_dict:
                        max_filter = np.max(np.abs(ydata))
                        delta = abs(local_dict["nominal_lb"] - local_dict["nominal_ub"])
                        outlier_max = local_dict.get("outlier_max")
                        if outlier_max is None:
                            outlier_max = [-1000, 1000]
                        y_data_n = ydatal / np.abs(xdatal / delta * 100)
                        # print(
                        # "max_filter",
                        # outlier_max,
                        # local_dict["xdata"],
                        # y_data_n[
                        #     (ydatal < outlier_max[0]) | (ydata > outlier_max[1])
                        # ],
                        # )
                        return_dict["ydata"] = y_data_n[
                            (ydatal > outlier_max[0]) & (ydata < outlier_max[1])
                        ]
                    else:
                        return_dict["ydata"] = ydata
                    if k == None:
                        if base_value is not None:
                            return_dict["ydata_norm"] = (
                                (ydatal - base_value[1]) / base_value[1] * 100.0
                            )
                        else:
                            return_dict["ydata_norm"] = None
                    else:
                        if "ydata_norm" not in return_dict:
                            return_dict["ydata_norm"] = []
                        if base_value is not None:
                            return_dict["ydata_norm"].append(
                                (ydatal - base_value[1]) / base_value[1] * 100.0
                            )
                        else:
                            return_dict["ydata_norm"].append(None)
                    return_dict["label"] = tornado_group["xlabel"]
                    return_dict["color"] = tornado_group["color"]
            return return_dict

        def manager_logic(m_key, m_options, gen_legend=True):
            self.cur_manager = m_key
            return get_data(m_key, m_options)

        def reg_logic(m_key=None, m_options=None):
            m_options = None
            self.updateKeySet()
            return get_data()

        def loop_logic(
            data_func, loop_dict, m_key=None, m_options_org=None, gen_legend=True
        ):
            return_dict = {}
            for li, value in enumerate(loop_dict["loop_values"]):
                self.updateKeySet(
                    data_manager=m_key,
                    keys=[loop_dict["loop_key"], value],
                    new_key_set=False,
                )
                return_dict[loop_dict["labels"][li]] = data_func(m_key, m_options_org)
            return return_dict

        def group_logic():
            tornado_dict = {}
            if "data_managers" in local_dict.keys():
                if "data_loops" in local_dict.keys():
                    for m_key, m_options in local_dict["data_managers"].items():
                        loop_dict = local_dict["data_loops"][m_key]
                        tornado_dict[m_key] = loop_logic(
                            manager_logic,
                            loop_dict,
                            m_key=m_key,
                            m_options_org=m_options,
                        )
                else:
                    for m_key, m_options in local_dict["data_managers"].items():
                        tornado_dict[m_key] = manager_logic(
                            m_key=m_key,
                            m_options_org=m_options,
                        )
            else:
                if "data_loops" in local_dict.keys():
                    loop_dict = local_dict["data_loops"]
                    tornado_dict = loop_logic(reg_logic, loop_dict)
                else:
                    tornado_dict = reg_logic()
            return tornado_dict

        def plot_bar(plot_post, data, data_norm, color, plot_figure, label):
            plot_range = None
            if "diff_mode" in self.auto_gen_dict:
                # #print(data)
                plot_range = np.percentile(data, [5, 95])
                if plot_figure:
                    figure.plot_box(
                        plot_post,
                        data,
                        self.auto_gen_dict["diff_mode"]["whiskers"],
                        vertical=False,
                        color=color,
                        width=bar_hegiht,
                        save_label=label,
                    )
                plot_range = np.median(data)
                return abs(plot_range)
            else:
                plot_range = [data_norm[0], data_norm[-1]]
                if plot_figure:
                    figure.plot_bar(
                        plot_post,
                        max(plot_range) - min(plot_range),
                        bottom=min(plot_range),
                        vertical=False,
                        color=color,
                        width=bar_hegiht,
                        save_label=label,
                    )
                return max(plot_range) - min(plot_range)

        def plot_logic(plot_post, plot_ticks, plot_labels, plot_figure=True):
            # plot_post = edge_offset
            bar_mags = []
            if "data_managers" in local_dict.keys():
                if "data_loops" in local_dict.keys():
                    for m_key, m_options in local_dict["data_managers"].items():
                        loop_dict = local_dict["data_loops"][m_key]
                        # #print(loop_dict)
                        for l_key in loop_dict["labels"]:
                            plot_post += bar_hegiht
                            sorted_x = np.argsort(
                                tornado_dict[group_key][m_key][l_key]["xdata"]
                            )
                            bar_data_norm = tornado_dict[group_key][m_key][l_key][
                                "ydata_norm"
                            ][sorted_x]

                            bar_data = tornado_dict[group_key][m_key][l_key]["ydata"][
                                sorted_x
                            ]
                            # #print(plot_post, bar_data_norm)

                            plot_ticks.append(plot_post)
                            plot_labels.append(group_key)
                            if plot_figure:
                                plot_bar(plot_post, bar_data, bar_data_norm)
                else:
                    for m_key, m_options in local_dict["data_managers"].items():
                        bar_data_norm = tornado_dict[group_key][m_key]["ydata_norm"]
                        bar_data = tornado_dict[group_key][m_key]["ydata_norm"]
                        plot_bar(plot_post, bar_data, bar_data_norm)
                        # plot_post += manager_offset
            else:
                if "data_loops" in local_dict.keys():
                    loop_dict = local_dict["data_loops"]
                    # #print(loop_dict)
                    for ki, l_key in enumerate(loop_dict["labels"]):
                        # #print(tornado_dict[group_key])
                        bar_data_norm = tornado_dict[group_key][l_key]["ydata_norm"]
                        bar_data = tornado_dict[group_key][l_key]["ydata"]
                        plot_ticks.append(plot_post)
                        plot_labels.append(tornado_dict[group_key][l_key]["label"])
                        if "colors" in loop_dict:
                            color = loop_dict["colors"][ki]
                        else:
                            color = "white"
                        label = tornado_dict[group_key][l_key]["label"] + " " + l_key
                        # #print(color)
                        # if bar_data_norm is not None:
                        #     bar_mags.append(max(plot_range) - min(plot_range))
                        # else:
                        #     bar_mags.append(max(bar_data) - min(bar_data))
                        # #print(tornado_dict, plot_range)
                        # i#f plot_figure:
                        bar_mag = plot_bar(
                            plot_post,
                            bar_data,
                            bar_data_norm,
                            color,
                            plot_figure,
                            label,
                        )
                        bar_mags.append(bar_mag)
                        plot_post -= bar_hegiht
                    # #print(plot_post)
                elif "case_options" in self.auto_gen_dict:
                    plot_post -= bar_hegiht
                    for i, scenario in enumerate(self.auto_gen_dict["case_options"]):
                        sc = self.auto_gen_dict["case_options"][scenario]
                        color = sc["plot_options"].get("color", "white")

                        # plot_post += bar_hegiht
                        plot_ticks.append(plot_post)
                        # #print(tornado_dict)
                        plot_labels.append(tornado_dict[group_key]["label"])
                        label = sc["plot_options"].get("label", "")
                        bar_data_norm = tornado_dict[group_key]["ydata_norm"][i]
                        bar_data = tornado_dict[group_key]["ydata"][i]
                        # print(bar_data, bar_data_norm)
                        bar_mag = plot_bar(
                            plot_post,
                            bar_data,
                            bar_data_norm,
                            color,
                            plot_figure,
                            label,
                        )
                        bar_mags.append(bar_mag)
                        plot_post -= bar_hegiht
                        # print(i, plot_post, bar_hegiht)
                else:
                    if tornado_dict[group_key].get("color") is None:
                        color = "white"
                    else:
                        color = tornado_dict[group_key].get("color")
                    # print(tornado_dict)
                    plot_post += bar_hegiht
                    plot_ticks.append(plot_post)

                    # plot_labels.append(group_key)
                    label = tornado_dict[group_key]["label"]
                    plot_labels.append(label)
                    bar_data_norm = tornado_dict[group_key]["ydata_norm"]
                    bar_data = tornado_dict[group_key]["ydata"]
                    bar_mag = plot_bar(
                        plot_post,
                        bar_data,
                        bar_data_norm,
                        color,
                        plot_figure,
                        label,
                    )

            bar_mags = np.array(bar_mags)
            # print(
            #     "bar_mags",
            #     bar_mags[np.abs(bar_mags) > 1e-10],
            #     np.average(bar_mags[np.abs(bar_mags) > 1e-10]),
            # )
            return plot_post, np.average(bar_mags[np.abs(bar_mags) > 1e-10])

        local_dict = self.auto_gen_dict.copy()
        figure = fig_generator.figureGenerator(**local_dict)
        figure.init_figure(**local_dict)
        tornado_dict = {}
        impact_order = None
        positions = None
        for group_key, tornado_group in self.auto_gen_dict["tornado_groups"].items():
            if "use_line_plot_key_in_base_key" in self.auto_gen_dict.keys():
                if self.auto_gen_dict["use_line_plot_key_in_base_key"]:
                    self.base_iter_key = [group_key]
                    # print("updated use_line_plot_key_in_base_key", group_key)
            if impact_order is None and "order" in tornado_group:
                impact_order = [tornado_group["order"]]
            elif "order" in tornado_group:
                impact_order.append(tornado_group["order"])
            if positions is None and "position" in tornado_group:
                positions = [tornado_group["position"]]
            elif "position" in tornado_group:
                positions.append(tornado_group["position"])
            results = group_logic()
            tornado_dict[group_key] = results
        mangers = 0
        if "data_managers" in self.auto_gen_dict.keys():
            managers = len(self.auto_gen_dict["data_managers"].keys())
        loops = 0
        if "data_loops" in self.auto_gen_dict.keys():
            loops = len(self.auto_gen_dict["data_loops"]["labels"])
            for ki, label in enumerate(self.auto_gen_dict["data_loops"]["labels"]):
                figure.plot_bar(
                    [0],
                    [0],
                    label=label,
                    vertical=False,
                    color=self.auto_gen_dict["data_loops"]["colors"][ki],
                )
        if "case_options" in self.auto_gen_dict.keys():
            # loops = len(self.auto_gen_dict["data_loops"]["labels"])
            for ki, case in enumerate(self.auto_gen_dict["case_options"]):
                figure.plot_bar(
                    [0],
                    [0],
                    label=self.auto_gen_dict["case_options"][case]["plot_options"][
                        "label"
                    ],
                    vertical=False,
                    color=self.auto_gen_dict["case_options"][case]["plot_options"][
                        "color"
                    ],
                )
        edge_offset = 0.05
        group_offset = 0.1
        if loops > 0:
            bar_hegiht = (1 - edge_offset - group_offset / 2) / (
                loops
            )  # - 0.025 * (managers - 1)
        elif "case_options" in self.auto_gen_dict:
            bar_hegiht = (1 - edge_offset - group_offset / 2) / (
                len(self.auto_gen_dict["case_options"])
            )
            # print("bar-H", bar_hegiht)
            # assert False
        else:
            bar_hegiht = 1 - edge_offset - group_offset / 2
        #  )  # 1 / (managers * loops)
        plot_ticks = []
        y_labels = []
        plot_post = edge_offset  # + bar_hegiht
        bar_magnitutes = []
        for gi, group_key in enumerate(tornado_dict.keys()):
            plot_post, bm = plot_logic(
                plot_post, plot_ticks, y_labels, plot_figure=False
            )
            bar_magnitutes.append(bm)
        # print(bar_magnitutes)
        # print(list(tornado_dict.keys()))
        if impact_order is None and positions is None:
            key_sort = np.argsort(bar_magnitutes)
            tornday_keys = np.array(list(tornado_dict.keys()))[key_sort][::-1]
        elif impact_order is not None:
            key_sort = np.argsort(impact_order)
            tornday_keys = np.array(list(tornado_dict.keys()))[
                key_sort
            ]  # [::-1]  # [::-1]
        elif positions is not None:
            key_sort = np.argsort(positions)
            sorted_positions = np.array(positions)[key_sort][::-1]
            tornday_keys = np.array(list(tornado_dict.keys()))[key_sort][::-1]
            # print("impact order", impact_order, list(range(len(tornado_dict.keys()))))
        # print(tornday_keys, key_sort)
        # tornday_keys = np.array(list(tornado_dict.keys()))[key_sort][::-1]
        plot_ticks = []
        y_labels = []
        plot_post = -edge_offset  # + bar_hegiht
        bar_magnitutes = []
        for gi, group_key in enumerate(tornday_keys):
            if positions != None:
                plot_post = -sorted_positions[gi]
            # plot_post = gi + edge_offset + bar_hegiht
            # plot_ticks.append(plot_post)
            # #print(plot_post, bar_hegiht, plot_post + bar_hegiht, loops)
            plot_post, _ = plot_logic(plot_post, plot_ticks, y_labels, plot_figure=True)
            plot_post -= group_offset
        # #print(plot_ticks, y_labels)
        unique_labels = np.unique(y_labels)
        # print(unique_labels)
        unique_pos = []
        for ul in unique_labels:
            tick_pos = np.average(np.array(plot_ticks)[np.array(y_labels) == ul])
            unique_pos.append(tick_pos)
        # print(unique_pos)
        sorted_dix = np.argsort(np.array(unique_pos))
        # print(sorted_dix)
        figure.set_axis(
            xticks=self.auto_gen_dict["xticks"], xlabel=self.auto_gen_dict["xlabel"]
        )
        y_pars = {
            "yticklabels": np.array(unique_labels)[sorted_dix],
            "yticks": np.array(unique_pos)[sorted_dix],
        }
        # print(y_pars)
        if "angle" in self.auto_gen_dict.keys():
            y_pars.update({"angle": self.auto_gen_dict["angle"]})
        figure.set_axis_ticklabels(**y_pars)  # **line_group)
        figure.add_legend()  # *line_group)
        figure.save()
        if show:
            figure.show()

    def extract_data(self, show=True):
        for key, item in self.auto_gen_dict["data_extract_groups"].items():
            # print(key)
            if isinstance(item, dict) and "data_key" in item:
                # print(item["data_key"])
                data = self.grab_data(data_key=item["data_key"])
                self.auto_gen_dict["data_extract_groups"][key]["data_key"] = data
            else:
                data = self.grab_data(data_key=item)
                self.auto_gen_dict["data_extract_groups"][key] = data

    def plot_table(self, show=True):
        save_location = (
            self.auto_gen_dict["save_location"] + "/" + self.auto_gen_dict["file_name"]
        )
        save_order = self.auto_gen_dict.get("table_plot_order")
        if save_order == None:
            if "case_options" in self.auto_gen_dict:
                save_order = ["case_options"]
            if "loop_options" in self.auto_gen_dict:
                save_order = ["loop_options"]
        save_iter = []
        for option in save_order:
            if option == "data_loops":
                iter_list = self.auto_gen_dict["data_loops"].get("import_keys")

            if option == "loop_options":
                iter_list = self.auto_gen_dict["loop_options"]["loop_values"]
            if option == "case_options":
                iter_list = list(self.auto_gen_dict["case_options"].keys())
            save_iter.append(iter_list)
        # print("save_iters", save_iter)
        data_save = []  # [] for i in range(len(save_iter))]
        iter_indexes = []
        if len(save_iter) == 1:
            width = 0.9  # / len(save_iter[1])
        else:
            width = 0.9 / len(save_iter[1])
        x_step = -width * 0.55  # TODO FIGURED OUT WH THIS IS 0.55
        if len(save_iter) > 1:
            x_pos = x_step + x_step * len(save_iter[1]) * 0.75
        else:
            x_pos = x_step
        positions = []
        labels = []
        save_label = []
        plot_options = []
        for k, i_zero_val in enumerate(save_iter[0]):
            if len(save_iter) > 1:
                for l, i_one_val in enumerate(save_iter[1]):
                    po = None
                    if save_order == ["loop_options", "case_options"]:
                        iter_indexes.append([l, k])
                        po = self.auto_gen_dict["case_options"][i_one_val].get(
                            "plot_options"
                        )
                    elif save_order == ["data_loops", "case_options"]:
                        iter_indexes.append([l, k])
                        po = self.auto_gen_dict["case_options"][i_one_val].get(
                            "plot_options"
                        )

                    else:
                        iter_indexes.append([k, l])
                    # x_pos += width
                    # positions.append(x_pos)
                    save_label.append(str(i_zero_val) + "_" + str(i_one_val))
                    # if position is not None:
                    # x_pos = x_step + position  # + 0.1
                    # else:
                    plot_options.append(po)

                    positions.append(x_pos)
                    x_pos += width  # + 0.1
                    if l + 1 == len(save_iter[1]):
                        x_pos += 0.1
            else:
                if "case_options" in self.auto_gen_dict:
                    if "plot_options" in self.auto_gen_dict["case_options"][i_zero_val]:
                        position = self.auto_gen_dict["case_options"][i_zero_val][
                            "plot_options"
                        ].get("position")
                        label = self.auto_gen_dict["case_options"][i_zero_val][
                            "plot_options"
                        ].get("label")
                        save_label.append(i_zero_val)
                        if label is not None:
                            labels.append(label)
                    iter_indexes.append([k, 0])
                else:
                    iter_indexes.append(k)
                if position is not None:
                    x_pos = x_step + position  # + 0.1
                else:
                    x_pos += width + 0.1
                positions.append(x_pos)
                plot_options.append(None)
        figure = fig_generator.figureGenerator(**self.auto_gen_dict)
        figure.init_figure(**self.auto_gen_dict)
        orientation = self.auto_gen_dict.get("orientation")
        if orientation is None:
            orientation = "vertical"
            edge = "edge"
        vert = True
        if orientation == "horizontal":
            vert = False
            iter_indexes = iter_indexes[::-1]
            labels = labels[::-1]
            edge = "center"
        plot_total = True
        plotted_labels = []
        # #print(self.auto_gen_dict["cost_options"]["cost_groups"])
        # assert False
        for ki, it in enumerate(iter_indexes):
            x_bottom = 0
            if "cost_options" in self.auto_gen_dict:
                if "total" not in self.auto_gen_dict["cost_options"]["cost_groups"]:
                    self.auto_gen_dict["cost_options"]["cost_groups"].update(
                        {"total": {}}
                    )
                    plot_total = False

                for key, dictdata in self.auto_gen_dict["cost_options"][
                    "cost_groups"
                ].items():
                    not_plotted = True
                    for sub_key, data in dictdata.items():
                        if isinstance(data, dict):
                            pass
                        else:
                            # #print(data, sub_key)
                            fig_opt = copy.deepcopy(dictdata.get("plot_options"))
                            plot_data = False
                            if sub_key != "total" or plot_total:
                                plot_data = True
                            if (
                                sub_key == "total"
                                and fig_opt.get("plot_cost_type") == "total"
                            ):
                                plot_data = True
                            elif (
                                sub_key != "total"
                                and fig_opt.get("plot_cost_type") == "total"
                            ):
                                plot_data = False
                            if plot_data:
                                if fig_opt.get("hatch") is None:
                                    fig_opt.update(
                                        {
                                            "hatch": self.auto_gen_dict["cost_options"][
                                                "plot_cost_types"
                                            ][sub_key].get("hatch")
                                        }
                                    )
                                # #print("dit", data, it)
                                if len(it) == 2:
                                    # #print(data.magnitude[3][1])
                                    x_value = data[it[0]][it[1]].magnitude
                                else:
                                    x_value = data[it].magnitude
                                # p#rint(fig_opt)
                                # print("dit", data, it, x_value)
                                if self.auto_gen_dict.get("plot_normalized_breakdown"):
                                    total_cost = self.auto_gen_dict["cost_options"][
                                        "total"
                                    ]
                                    # print("dit", data, it, x_value, total_cost)
                                    if len(it) == 2:
                                        x_value = (
                                            x_value / total_cost[it[0]][it[1]].magnitude
                                        )
                                    else:
                                        x_value = x_value / total_cost[it].magnitude
                                    x_value = x_value * self.auto_gen_dict.get(
                                        "xconvert", 1
                                    )
                                x_pos = positions[ki]
                                if (
                                    not_plotted
                                    and fig_opt.get("hatch") == ""
                                    and ki == 0
                                ):
                                    label = key
                                    not_plotted = False
                                else:
                                    label = ""
                                figure.plot_bar(
                                    x_pos,
                                    x_value,
                                    bottom=x_bottom,
                                    width=width,
                                    align=edge,
                                    label=label,
                                    vertical=vert,
                                    save_label=save_label[ki],
                                    **fig_opt,
                                )
                                x_bottom += x_value

            if "data_extract_groups" in self.auto_gen_dict:
                # print(self.auto_gen_dict["data_extract_groups"])
                for key, data in self.auto_gen_dict["data_extract_groups"].items():
                    # #print(data)
                    # print("data", data, it)
                    if isinstance(data, dict):
                        d = data["data_key"]
                        if len(it) == 2:
                            # #print(data.magnitude[3][1])
                            x_value = d[it[0]][it[1]]  # .magnitude
                        else:
                            x_value = d[it]  #
                    else:
                        if len(it) == 2:
                            # #print(data.magnitude[3][1])
                            x_value = data[it[0]][it[1]]  # .magnitude
                        else:
                            x_value = data[it]  # .magnitude
                    # print("data", data, it, plot_options)
                    fig_opt = copy.deepcopy(data.get("plot_options"))

                    if fig_opt == None and plot_options[ki] != None:
                        fig_opt = plot_options[ki]
                    elif plot_options[ki] != None:
                        fig_opt.update(plot_options[ki])
                    # if fig_opt.get("hatch") is None:
                    #     fig_opt.update(
                    #         {
                    #             "hatch": self.auto_gen_dict["cost_options"][
                    #                 "plot_cost_types"
                    #             ][sub_key].get("hatch")
                    #         }
                    #     )
                    if self.auto_gen_dict.get("stack_bars") == False:
                        x_bottom = 0
                    x_pos = positions[ki]
                    # print(fig_opt)

                    if "label" in fig_opt:
                        label = fig_opt["label"]
                        if label in plotted_labels:
                            fig_opt.pop("label")
                        else:
                            plotted_labels.append(label)
                    else:
                        if ki == 0:
                            fig_opt["label"] = key
                    # if ki == 0:
                    #     # fig_opt.pop("label")
                    #     label = key
                    # else:
                    #     label = ""
                    #     # fig_opt.pop("label")
                    figure.plot_bar(
                        x_pos,
                        x_value,
                        # label=label,
                        bottom=x_bottom,
                        width=width,
                        align=edge,
                        vertical=vert,
                        save_label=save_label[ki],
                        **fig_opt,
                    )
                    x_bottom += x_value
        if "cost_options" in self.auto_gen_dict:
            if len(self.auto_gen_dict["cost_options"]["plot_cost_types"].keys()) > 1:
                for kt, key_type in enumerate(
                    self.auto_gen_dict["cost_options"]["plot_cost_types"].keys()
                ):
                    type_options = self.auto_gen_dict["cost_options"][
                        "plot_cost_types"
                    ][key_type]
                    figure.plot_bar(
                        [0],
                        [0],
                        hatch=type_options["hatch"],
                        color="white",
                        label=key_type,
                    )
        if vert:
            if labels == []:
                labels = self.auto_gen_dict.get("xticklabels")
            x_pars = {}
            if labels is not None:
                x_pars = {
                    "xticklabels": labels,
                    "xticks": list(range(len(save_iter[0]))),
                    "xlabel": self.auto_gen_dict.get("xlabel"),
                }

                # print("xpars", x_pars)
                if "angle" in self.auto_gen_dict.keys():
                    x_pars.update({"angle": self.auto_gen_dict["angle"]})
                if "rotate" in self.auto_gen_dict.keys():
                    x_pars.update({"rotate": self.auto_gen_dict["rotate"]})
                figure.set_axis(
                    yticks=self.auto_gen_dict["yticks"],
                    ylabel=self.auto_gen_dict["ylabel"],
                )
                figure.set_axis_ticklabels(**x_pars)
            else:
                # x_pars['yticks']=
                figure.set_axis(**self.auto_gen_dict)
        else:
            x_pars = {}
            if labels == []:
                labels = self.auto_gen_dict["yticklabels"]
            # print(positions)
            y_pars = {
                "yticklabels": labels,
                "yticks": positions,  # list(range(len(positions))),
            }
            # print("ypars", y_pars)
            if "angle" in self.auto_gen_dict.keys():
                x_pars.update({"angle": self.auto_gen_dict["angle"]})
            figure.set_axis_ticklabels(**y_pars)
            figure.set_axis(
                xticks=self.auto_gen_dict["xticks"], xlabel=self.auto_gen_dict["xlabel"]
            )
        self.add_custom_legend(figure, plot_type="bar")
        figure.add_legend(**self.auto_gen_dict)
        figure.save()
        if show:
            figure.show()

    def save_table(self):
        save_location = (
            self.auto_gen_dict["save_location"] + "/" + self.auto_gen_dict["file_name"]
        )
        save_order = self.auto_gen_dict.get("table_plot_order")
        if save_order == None:
            if "case_options" in self.auto_gen_dict:
                save_order = ["case_options"]
            if "loop_options" in self.auto_gen_dict:
                save_order = ["loop_options"]
        save_iter = []
        for option in save_order:
            if option == "loop_options":
                iter_list = self.auto_gen_dict["loop_options"]["loop_values"]
            if option == "case_options":
                iter_list = list(self.auto_gen_dict["case_options"].keys())
            save_iter.append(iter_list)
        # print(save_iter)
        data_save = []  # [] for i in range(len(save_iter))]
        combos = len(save_iter[0])
        if len(save_iter) == 2:
            for it in save_iter[1:]:
                combos *= len(it)
        for it in save_iter:
            if len(save_iter) == 2:
                data_save.append(list(np.repeat(it, 2)))
            else:
                data_save.append([""] + it * int(combos / len(it)))
        # print(data_save, combos)
        if "cost_options" in self.auto_gen_dict:
            for key, dictdata in self.auto_gen_dict["cost_options"][
                "cost_groups"
            ].items():
                for sub_key, data in dictdata.items():
                    # print(data)
                    if isinstance(data, dict):
                        pass
                    else:
                        data_save.append(
                            [key + " " + sub_key]
                            + list(np.array(data.magnitude).flatten())
                        )
        if "data_extract_groups" in self.auto_gen_dict:
            for key, data in self.auto_gen_dict["data_extract_groups"].items():
                data_save.append([key] + list(np.array(data).flatten()))

        with open(save_location + ".csv", "w", newline="") as csvfile:
            writer = csv.writer(csvfile, dialect="excel")
            writer.writerow(["Extracted data table"])
            for d in data_save:
                writer.writerow(d)

    def build_fig(self, dict_build, show=True):
        self.updateKeySet()
        self.auto_gen_dict = dict_build.copy()
        if "zdata" in dict_build:
            self.plot_map(show)
        elif "cost_options" in dict_build:
            self.plot_cost_breakdown(show)
        elif "tornado_groups" in dict_build:
            self.plot_tornado_plot(show)
        elif "line_plots" in dict_build:
            self.plot_line(show)

    def gen_table(self, dict_build):
        self.updateKeySet()
        self.auto_gen_dict = dict_build.copy()
        if "cost_options" in dict_build:
            self.get_cost_break_down(self.auto_gen_dict)
        if "data_extract_groups" in dict_build:
            self.extract_data()
        # print("auto-gen_dict", self.auto_gen_dict)

    def default_costing(self, loc="fs.costing."):
        default_costing_params = [
            ["utilization_factor", "load_factor"],
            "specific_energy_consumption",
            "factor_total_investment",
            "factor_maintenance_labor_chemical",
            "factor_capital_annualization",
            "electricity_cost",
        ]
        self.default_costing_params = {}
        for key in default_costing_params:
            if isinstance(key, list):
                for sub_key in key:
                    try:
                        values = self.grab_data(data_key=loc + sub_key)
                        unit = self.get_unit(loc + sub_key)
                        self.default_costing_params[key[0]] = values * unit
                        break
                    except:
                        print("Failed getting key", sub_key)
            else:
                values = self.grab_data(data_key=loc + key)
                unit = self.get_unit(loc + key)
                # #print(key, values, str(unit), unit)
                self.default_costing_params[key] = values * unit
        print("------default costing params-------")
        for key, item in self.default_costing_params.items():
            print(key, item)
        print("------------------------------------")
        # #print(self.default_costing_params)

    def cost_loop(self, item):
        result = []
        for k in item["loop_list"]:
            try:
                if result == []:
                    result = self.get_costs(item["loop_key"].format(str(k)))
                else:
                    result = result + self.get_costs(item["loop_key"].format(str(k)))

                # print("got key {} {}".format(k, item["loop_key"].format(str(k))))
                # #print(result)
            except KeyError:
                print(
                    "Not item {} for key {}".format(k, item["loop_key"].format(str(k)))
                )
        return result

    def get_costs(self, item):
        if isinstance(item, dict):
            if "loop_key" in item:
                for i in item["loop_list"]:
                    try:
                        key = item["loop_key"].format(item["loop_list"][i])
                        unit = self.get_unit(key)
                        break
                    except:
                        pass
            else:
                key = item["key"]
                unit = self.get_unit(item)
        else:
            unit = self.get_unit(item)
        data = np.array(self.grab_data(data_key=item)) * unit
        # #print(data, item, "unit", unit)
        if unit != self.base_cost_unit:
            if unit == qs.USD:
                data = data  # / self.total_flow  # * yearly_up_time
                # data.units = self.base_cost_unit
            try:
                # #print("test", data, item, unit.rescale(qs.W))
                unit.rescale(qs.W)
                data = data * self.yearly_up_time
                data = data.rescale(qs.kWh)
                data = data * self.default_costing_params["electricity_cost"]
                # data.rescale()
                # data = data / self.total_flow
                data = data.rescale(qs.USD)
            except:
                pass
        return data

    def costing_math(self, math_dict):
        # #print(math_dict)
        # item = list(math_dict.keys())[0]
        # math_dict = math_dict[item]
        # #print(item, math_dict)
        data_dict = {}
        zero_key = None
        for key, item in math_dict["math_keys"].items():
            # #print(key, item)
            # if math_dict["math_keys"].get("loop_list") != None:
            #     item_dict = {
            #         "loop_key": item,
            #         "loop_list": math_dict["math_keys"]["loop_list"],
            #     }
            # else:
            item_dict = item
            # #print(item)
            data = self.get_costs(item_dict)
            if zero_key is None:
                zero_key = key
            data_dict[key] = data
        # if sum(data_dict[zero_key].magnitude) == 0:
        #     data = data_dict[zero_key]
        # #print(math_dict["expression"], data_dict)
        data = eval(math_dict["expression"], data_dict)
        # #print(data)
        if data.units != qs.USD:
            data = data * self.yearly_up_time  # / self.total_flow
            # #print(data)
            data = data.rescale(qs.USD)

        data[data_dict[zero_key].magnitude == 0] = 0 * data.units
        return data

    def get_cost_break_down(self, cost_key_set, include_indirects=True):
        self.auto_gen_dict = copy.deepcopy(cost_key_set)
        self.updateKeySet()
        self.default_costing()
        cost_keys = cost_key_set["cost_options"].copy()
        flow_unit = self.get_unit(cost_keys["total_flow"])
        # s.total_flow = self.grab_data(cost_keys["total_flow"]) * flow_unit
        self.yearly_up_time = (
            1 * qs.year * self.default_costing_params["utilization_factor"]
        )
        self.total_flow = (
            self.grab_data(data_key=cost_keys["total_flow"])
            * flow_unit
            * self.yearly_up_time
        )
        cost_results = {}
        for group_key, item in cost_keys["cost_groups"].items():
            # #print(group_key)
            if isinstance(item, str):
                data = self.get_costs(item)
                cost_results[group_key] = data
            elif isinstance(item, dict):
                cost_results[group_key] = {}
                for item_key in item.keys():
                    if item_key != "plot_options":
                        for k in item[item_key]:
                            if k is None:
                                cost_results[group_key][item_key] = [0] * qs.USD
                            else:
                                # #print("k", k, item[item_key])
                                if isinstance(k, str):
                                    data = self.get_costs(k)
                                elif isinstance(k, dict):
                                    if "math_keys" in k:
                                        data = self.costing_math(k)
                                    else:
                                        data = self.get_costs(k)
                                if item_key not in cost_results[group_key].keys():
                                    cost_results[group_key][item_key] = data
                                else:
                                    cost_results[group_key][item_key] += data

                if include_indirects:
                    # #print(cost_results[group_key]["CAPEX"])
                    # ass
                    cost_results[group_key]["CAPEX"] = (
                        cost_results[group_key].get("CAPEX", 0 * qs.USD)
                        * self.default_costing_params["factor_total_investment"]
                    )
                    cost_results[group_key]["OPEX"] = (
                        cost_results[group_key].get("OPEX", 0 * qs.USD)
                        + cost_results[group_key].get("CAPEX", 0 * qs.USD)
                        * self.default_costing_params[
                            "factor_maintenance_labor_chemical"
                        ]
                    )
                cost_results[group_key]["CAPEX"] = (
                    cost_results[group_key]["CAPEX"]
                    * self.default_costing_params["factor_capital_annualization"]
                )
                CAPEX = cost_results[group_key]["CAPEX"] / self.total_flow
                CAPEX = CAPEX.rescale(self.base_cost_unit)
                cost_results[group_key]["CAPEX"] = CAPEX
                OPEX = cost_results[group_key]["OPEX"] / self.total_flow
                OPEX = OPEX.rescale(self.base_cost_unit)
                cost_results[group_key]["OPEX"] = OPEX
                # print(group_key, CAPEX, OPEX)
                cost_results[group_key]["total"] = OPEX + CAPEX
                # print(cost_results[group_key]["total"])
                # assert False

        self.auto_gen_dict["cost_options"]["total"] = None

        for key in self.auto_gen_dict["cost_options"]["cost_groups"].keys():
            if key != "total":
                self.auto_gen_dict["cost_options"]["cost_groups"][key][
                    "OPEX"
                ] = cost_results[key]["OPEX"]
                self.auto_gen_dict["cost_options"]["cost_groups"][key][
                    "CAPEX"
                ] = cost_results[key]["CAPEX"]
                self.auto_gen_dict["cost_options"]["cost_groups"][key][
                    "total"
                ] = cost_results[key]["total"]
                # #print(key)
                if self.auto_gen_dict["cost_options"]["total"] is None:
                    self.auto_gen_dict["cost_options"]["total"] = copy.deepcopy(
                        cost_results[key]["total"]
                    )
                else:
                    self.auto_gen_dict["cost_options"]["total"] += cost_results[key][
                        "total"
                    ]
        return self.auto_gen_dict


#
