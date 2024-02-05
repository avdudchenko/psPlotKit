import h5py
import numpy as np
import glob
import copy
import re
from psPlotKit.util import logger
from psPlotKit.data_manager.ps_data import psData
import difflib

__author__ = "Alexander V. Dudchenko (SLAC)"

_logger = logger.define_logger(__name__, "psDataImport")


class psDataImport:
    def __init__(self, data_location, extensive_indexing=True):
        _logger.info("data import v0.1")
        if ".h5" not in data_location:
            data_location = data_location + ".h5"
        self.h5_fileLocation = data_location
        self.get_h5_file(self.h5_fileLocation)
        self.terminating_key = "outputs"
        self.search_keys = True
        self.cur_dir = None
        self.selected_directory = None

        self.file_index = {}
        self.directory_indexes = {}
        self.get_file_directories()
        # if extensive_indexing:
        self.get_directory_contents()
        self.directory_keys = []
        self.only_feasible = True
        """ specified cut off for searching for near keys """
        self.search_cut_off = 0.6
        """ number of near keys to return """
        self.num_keys = 10

    def get_file_directories(self, term_key="outputs"):
        self.directories = []

        def get_directory(current_file_loc, cur_dir=""):
            cur_dir_original = cur_dir
            if "outputs" in current_file_loc.keys():
                if cur_dir not in self.directories:
                    self.directories.append(cur_dir)
                    return True
            for key in current_file_loc.keys():
                if cur_dir == "":
                    cur_dir = key
                else:
                    cur_dir = cur_dir_original + "/" + key
                get_directory(current_file_loc[key], cur_dir=cur_dir)

        get_directory(self.raw_data_file)
        for d in self.directories:
            self.file_index[d] = {}
        self.get_unique_directories()
        for directory in self.directories:
            _logger.info("Found directory: {}".format(directory))

    def get_unique_directories(self):
        key_arr = []
        for d in self.directories:
            keys = d.split("/")
            key_arr.append(keys)
        key_arr = np.array(key_arr)
        unique_dir = []
        for row in key_arr.T:
            uq_dirs = np.unique(row)
            unique_dir.append(uq_dirs)
        self.global_unique_directories = []
        for ud in unique_dir:
            if len(ud) > 1:
                for k in ud:
                    self.directory_indexes[k] = []
                    for d in self.directories:
                        if k in d:
                            self.directory_indexes[k].append(d)
                            if "unique_directory" not in self.file_index[d]:
                                self.file_index[d]["unique_directory"] = [k]
                            else:
                                self.file_index[d]["unique_directory"].append(k)
                    self.global_unique_directories.append(k)
        _logger.info(
            "global unique directory keys: {}".format(self.global_unique_directories)
        )
        for d in self.directories:
            _logger.info(
                "{} contains unique directory {}".format(
                    d, self.file_index[d]["unique_directory"]
                )
            )

    def get_directory_contents(self):
        self.sub_contents = []
        for d in self.file_index:
            file_data = self.raw_data_file[d]

            for k, sub_data in file_data.items():
                if k not in self.sub_contents:
                    self.sub_contents.append(k)
                self.file_index[d][k] = []
                for key in sub_data.keys():
                    self.file_index[d][k].append(key)
                    _logger.info("{} {} {}".format(d, k, key))
        _logger.info("Data types found: {}".format(self.sub_contents))

    def get_selected_directories(self):
        selected_directories = []

        if self.directory_keys == []:
            _logger.info("Searching in all directories")
            return self.directories
        else:
            for d in self.directories:
                if all(sdk in d for sdk in self.directory_keys):
                    selected_directories.append(d)
                    _logger.info("User selected {}".format(d))
            return selected_directories

    def get_data(self, data_key_list):
        selected_directories = self.get_selected_directories()
        collected_data = {}
        for directory in selected_directories:
            unique_labels = ":".join(self.file_index[directory]["unique_directory"])
            collected_data[unique_labels] = {}
            for i, dkl in enumerate(data_key_list):
                data_keys, data_type = self._get_nearest_key(directory, dkl)
                for dk in data_keys:
                    data = self._get_data_set_auto(directory, data_type, dk)
                    collected_data[unique_labels][dk] = data
        return collected_data

    def get_h5_file(self, location):
        self.data_file = h5py.File(location, "r")
        self.raw_data_file = self.data_file

    def get_output(
        self,
        key,
        only_feasible=True,
    ):
        self._get_data()

        return self._get_data_set(
            key,
            main_loc="outputs",
            sub_key="value",
            only_feasible=only_feasible,
        )

    def get_sweep(
        self,
        key,
        only_feasible=True,
    ):
        self._get_data()
        return self._get_data_set(
            key,
            main_loc="sweep_params",
            sub_key="value",
            only_feasible=only_feasible,
        )

    def get_diff(
        self,
        key,
        return_absolute=False,
        diff_loc="differential_idx",
        diff_key="differential_idx",
        nom_loc="nominal_idx",
        nom_key="nominal_idx",
        filter_nans=True,
    ):
        sweep_reference_raw = self._get_data_set(
            nom_key,
            main_loc=nom_loc,
            sub_key="value",
        )
        sweep_reference = np.array(
            sweep_reference_raw[sweep_reference_raw == sweep_reference_raw], dtype=int
        )
        diff_reference_raw = self._get_data_set(
            diff_key,
            main_loc=diff_loc,
            sub_key="value",
        )
        try:
            absolute_data = self.get_output(key)
        except:
            absolute_data = self.get_sweep(key)

        delta_result = np.zeros(diff_reference_raw.shape) * np.nan
        for i in sweep_reference:
            sweep_idx = np.where(i == sweep_reference_raw)[0][0]
            diff_idx = np.where(i == diff_reference_raw)[0]  # [0]
            if return_absolute:
                delta_result[diff_idx] = (
                    absolute_data[diff_idx] - absolute_data[sweep_idx]
                )
            else:
                delta_result[diff_idx] = (
                    (absolute_data[sweep_idx] - absolute_data[diff_idx])
                    / absolute_data[sweep_idx]
                    * 100
                )
        if filter_nans:
            return delta_result[delta_result == delta_result]
        else:
            return delta_result

    def _get_data_set_auto(self, directory, data_type, data_key):
        self._get_data(directory)
        try:
            data = self.raw_data_file[data_type][data_key]["value"][()]
        except (KeyError, ValueError, TypeError):
            data = self.raw_data_file[data_type][data_key][()]
        try:
            units = str(self.raw_data_file[data_type][data_key]["units"][()])

        except (KeyError, ValueError, TypeError):
            units = "dimensionless"

        if len(data) == 0:
            raise ValueError(
                "No data found for directory {} data type {} data key {}".format(
                    directory, data_type, data_key
                )
            )
        result = np.array(data, dtype=np.float64)
        data_object = psData(result, units, self.get_feasible_idxs())

        return data_object
        # except TypeError:
        #     return None

    def _get_nearest_key(self, directory, data_key):
        for data_type in self.sub_contents:
            available_keys = self.file_index[directory][data_type]
            if data_key in available_keys:
                return [data_key], data_type

            near_keys = difflib.get_close_matches(
                data_key, available_keys, cutoff=self.search_cut_off, n=self.num_keys
            )  # , n=0.8)
            if near_keys != []:
                return near_keys, data_type
        if near_keys == []:
            raise ValueError(
                "Did not find {} in directory {}".format(data_key, directory)
            )

    def _get_data_set(
        self,
        key=None,
        main_loc="outputs",
        sub_key="value",
        only_feasible=True,
        datatype=np.float64,
    ):
        self._get_data()
        if "m.fs." in sub_key:
            sub_key = sub_key[2:]
        try:
            try:
                data = self.raw_data_file[main_loc][key][sub_key][()]
            except (KeyError, ValueError):
                data = self.raw_data_file[main_loc][key][()]
            result = np.array(data, dtype=datatype)
            if only_feasible:
                feasible = self.get_feasible_idxs()
                result = result[feasible]
            return result
        except TypeError:
            return None

    def get_dir_keys(self, main_key):
        self._get_data()
        return self.raw_data_file[main_key].keys()

    def get_raw_data(self):
        self._get_data()
        return np.array(self.raw_data_file[()])

    def get_feasible_idxs(self, data=None, val=None):
        if val is None:
            filtered = np.array(
                self.raw_data_file["solve_successful"]["solve_successful"][()],
                dtype=bool,
            )
        else:
            feasible = np.zeros(len(data), dtype=bool)
            filtered = np.where(np.array(data) != val)
            feasible[filtered] = True
        return filtered

    def check_bounds(self, nearness_test=0.1):
        self._get_data()
        for v in list(self.raw_data_file.keys()):
            for k in list(self.raw_data_file[v].keys()):
                try:
                    if "lower bound" in list(self.raw_data_file[v][k].keys()):
                        lb = self.raw_data_file[v][k]["lower bound"][()]
                        ub = self.raw_data_file[v][k]["upper bound"][()]
                        # print(lb, ub)
                        if v == "outputs":
                            data = self.get_output(k, auto_convert=False)
                        if v == "sweep_params":
                            data = self.get_sweep(k, auto_convert=False)
                        # print(data, lb, ub)
                        if sum(np.diff(np.abs(data))) > 0:
                            if any((data - (data * nearness_test)) < lb):
                                print("LB_HIT", k, "with in:", nearness_test * 100, "%")
                                # print(data, lb)
                            if any((data + (nearness_test * data)) > ub):
                                print("UB_HIT", k, "with in:", nearness_test * 100, "%")
                                # print(data, ub)
                except:
                    pass

    def _get_data(self, selected_directory=None, keys=None):
        # print("Current key set!", keys, self.current_keys)
        self.cur_dir = None
        if selected_directory is not None:
            self.cur_dir = selected_directory
            # self.selected_directory = None
            self.raw_data_file = self.data_file[self.cur_dir]
            # print("Using directory: {}".format(self.cur_dir))
        elif self.search_keys:
            temp_keys = copy.deepcopy(self.current_keys)
            # print(temp_keys)
            if keys is not None:
                temp_keys = temp_keys + keys
            self.find_dir(temp_keys, self.data_file)
            # print("Opened directory {} ".format(self.cur_dir))

    def retrive_loop_data(
        self,
        key,
        loop_values,
        result_key=None,
        get_diff=False,
        filter_keys=None,
        stack_data=False,
        get_sweep=False,
        get_raw_data=False,
        return_loop_map=False,
        format_with_loop_value=False,
        only_feasible=True,
        return_absolute=False,
    ):
        result_array = []
        loop_map = []
        result_key_copy = result_key
        for loop_value in loop_values:
            key_temp = [[key, str(loop_value)]]
            self.search_keys = True
            # print(key_temp)
            self._get_data(key_temp)
            if format_with_loop_value or "{}" in result_key_copy:
                try:
                    result_key = result_key_copy.format(str(loop_value))
                except:
                    print("Failed to auto format loop value into key")
                # print(result_key, loop_value)
            try:
                self.search_keys = False
                if get_sweep:
                    data = self.get_sweep(str(result_key), only_feasible=only_feasible)
                elif get_diff:
                    data = self.get_diff(
                        str(result_key), return_absolute=return_absolute
                    )
                elif get_raw_data:
                    data = self._get_data_set(
                        str(loop_value), main_loc=key, only_feasible=False
                    )
                else:
                    data = self.get_output(str(result_key), only_feasible=only_feasible)
                # print(len(data))
                if filter_keys != None:
                    fileter_idxs = self.find_same_conditions(filter_keys)
                    # print(len(fileter_idxs))
                    data = data[fileter_idxs]
                if return_loop_map:
                    loop_ref = [loop_value for ij in range(len(data))]
                    if stack_data:
                        if len(loop_map) == 0:
                            loop_map = loop_ref
                        else:
                            loop_map = np.hstack((loop_map, loop_ref))
                    else:
                        loop_map.append(loop_ref)
                if stack_data:
                    if len(result_array) == 0:
                        result_array = data
                    else:
                        result_array = np.hstack((result_array, data))
                else:
                    result_array.append(data)
            except:
                if stack_data:
                    if len(result_array) == 0:
                        result_array = np.array([np.nan])
                    else:
                        result_array = np.hstack((result_array, np.array([np.nan])))
                else:
                    result_array.append(np.array([np.nan]))
        try:
            result_array = np.array(result_array, dtype=np.float64)
        except:
            print("Warnning returning object type array from loop data!")
            result_array = np.array(result_array, dtype=object)
        if return_loop_map:
            return result_array, loop_map
        else:
            return result_array

    def find_dir(self, dir_values, data_file, found_keys=[], cur_dir=""):
        if len(found_keys) == 0:
            found_keys = np.empty(len(dir_values), dtype=bool)
            found_keys[:] = False
            self.raw_data_file = None
        if dir_values == []:
            print("root_dir_mode")
            self.raw_data_file = self.data_file
            self.cur_dir = ""
        else:
            for i, key in enumerate(dir_values):
                test = False
                if isinstance(key, list):
                    key = list(map(str, key))
                    if (
                        key[0] in data_file.keys()
                        and key[1] in data_file[key[0]].keys()
                    ):
                        test = True
                        cur_dir = cur_dir + "/" + key[0] + "/" + key[1]
                else:
                    key = str(key)
                    if key in data_file.keys():
                        test = True
                        cur_dir = cur_dir + "/" + key
                if test:
                    if self.terminating_key in self.data_file[cur_dir].keys():
                        self.raw_data_file = self.data_file[cur_dir]
                        self.cur_dir = cur_dir
                        self.terminal_found = True
                        break
                    else:
                        self.find_dir(
                            dir_values, self.data_file[cur_dir], found_keys, cur_dir
                        )
                        if self.terminal_found:
                            break

    def set_data_keys(self, dlist):
        self.current_keys = dlist
        self.raw_data_file = None
