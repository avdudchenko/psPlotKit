import h5py
import numpy as np
import glob
import copy
import re
from psPlotKit.util import logger
from psPlotKit.data_manager.ps_data import psData
import difflib
import time
import json

__author__ = "Alexander V. Dudchenko (SLAC)"

_logger = logger.define_logger(__name__, "psDataImport", level="INFO")


class psDataImport:
    def __init__(
        self,
        data_location,
        group_keys=["outputs"],
        data_keys=["values", "value"],
        default_return_directory=None,
    ):
        _logger.info("data import v0.2")
        _logger.info("Importing file {}".format(data_location))
        self.default_return_directory = default_return_directory
        if ".h5" in data_location:
            self.h5_fileLocation = data_location
            self.get_h5_file(self.h5_fileLocation)
            self.json_mode = False
        elif ".json" in data_location:
            self.json_fileLocation = data_location
            self.get_json_file(self.json_fileLocation)
            self.h5_mode = False
        else:
            raise ImportError(
                "File type provided is not supported. Please provide .json or .h5 file format"
            )
        self.group_keys = group_keys
        self.data_keys = data_keys
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
        self.num_keys = 1

    def _perform_data_tests(self, directory_contents):
        # print(directory_contents.keys())
        termination_test = any(
            [term_key in directory_contents.keys() for term_key in self.group_keys]
        )
        data_test = any(
            [term_key in directory_contents.keys() for term_key in self.data_keys]
        )
        return termination_test, data_test

    def get_file_directories(self):
        self.directories = []

        def get_directory(current_file_loc, cur_dir="", prior_dir=""):
            cur_dir_original = cur_dir
            if hasattr(current_file_loc, "keys"):
                termination_test, data_test = self._perform_data_tests(current_file_loc)
                # print(cur_dir, termination_test, data_test)
                if termination_test:
                    if cur_dir not in self.directories:
                        self.directories.append(cur_dir)
                        return False
                elif data_test:
                    if prior_dir not in self.directories:
                        self.directories.append(prior_dir)
                        return False
                for key in current_file_loc.keys():
                    if cur_dir == "":
                        cur_dir = key
                    else:
                        cur_dir = cur_dir_original + "/" + key
                    # print(cur_dir)
                    termination_found = get_directory(
                        current_file_loc[key],
                        cur_dir=cur_dir,
                        prior_dir=cur_dir_original,
                    )
                    if termination_found:
                        break
            # else:
            #     if cur_dir not in self.directories:
            #         if prior_dir not in self.directories:
            #             self.directories.append(prior_dir)
            #         return False

        get_directory(self.raw_data_file)
        # assert False
        for d in self.directories:
            self.file_index[d] = {}
            # print(d)
        # assert False
        self.get_unique_directories()
        # assert False
        for directory in self.directories:
            _logger.info("Found directory: {}".format(directory))
        # assert False

    def get_unique_directories(self):
        """this will go through all file directories and pull out only unieque ones
        adding reference to file_index, global_unique_directories, and directory_indexes
        """

        def str_to_num(str_val):
            try:
                str_val = int(str_val)
            except ValueError:
                try:
                    str_val = float(str_val)
                except ValueError:
                    pass
            return str_val

        _logger.info("Getting directories")
        self.global_unique_directories = []
        key_arr = []
        key_len = []
        for d in self.directories:
            keys = d.split("/")
            if "" in keys:
                keys.remove("")
            key_arr.append(keys)
            key_len.append(len(keys))
        key_length = np.unique(key_len)
        unique_dir = []
        # print(len(self.directories), self.directories)
        # assert False
        if len(self.directories) == 1:
            unique_dir = self.directories
            self.global_unique_directories = self.directories
            self.file_index[d]["unique_directory"] = self.directories[0]
        else:
            for idx, d in enumerate(self.directories):
                num_unique_keys = key_len[idx]
                unique_dir = []
                if num_unique_keys == 1:
                    idx = np.where(np.array(key_len) == 1)[0]
                    for i in idx:
                        unique_dir = unique_dir + list(key_arr[i])
                else:
                    idx = np.where(np.array(key_len) == num_unique_keys)[0]
                    ka = []
                    for i in idx:
                        ka.append(key_arr[i])
                    ka = np.array(ka, dtype=str)
                    for row in ka.T:
                        # print("row", row)
                        uq_dirs = np.unique(row)
                        if len(uq_dirs) > 1:
                            unique_dir = unique_dir + list(uq_dirs)
                used_dir_keys = []
                for k in unique_dir:
                    if k in d.split("/"):
                        # print(k)
                        kf = str_to_num(k)
                        split = d.split("/")
                        if "" in split:
                            split.remove("")
                        idx = np.where(str(kf) == np.array(split))[0]
                        if len(idx) == 1:
                            try:
                                prior_idx = idx[0] - 1
                                if prior_idx >= 0 and split[idx[0] - 1] not in str(
                                    used_dir_keys
                                ):

                                    ldir = tuple([split[idx[0] - 1], kf])
                                else:
                                    ldir = kf
                            except IndexError:
                                pass
                        else:
                            ldir = kf
                        used_dir_keys.append(ldir)
                        # print(d, ldir)
                        if ldir not in self.directory_indexes:
                            self.directory_indexes[ldir] = []
                        self.directory_indexes[ldir].append(d)
                        if "unique_directory" not in self.file_index[d]:
                            self.file_index[d]["unique_directory"] = [ldir]
                        else:
                            self.file_index[d]["unique_directory"].append(ldir)
                        if kf not in self.global_unique_directories:
                            self.global_unique_directories.append(ldir)
        _logger.info(
            "global unique directory keys: {}".format(self.global_unique_directories)
        )
        clean_up = []
        for d in self.directories:
            if "unique_directory" not in self.file_index[d]:
                clean_up.append(d)
                _logger.info("{} contains no directory, is it empty?, removing!")
            else:
                _logger.info(
                    "{} contains unique directory {}".format(
                        d, self.file_index[d]["unique_directory"]
                    )
                )
        print(self.directories, self.file_index)
        for cl in clean_up:
            self.directories.remove(cl)
            del self.file_index[cl]

    def get_directory_contents(self):

        self.sub_contents = []
        self.unique_data_keys = []
        for d in self.file_index:
            _logger.info(f"Getting directory contents for {d}")
            ts = time.time()
            file_data = self._get_raw_data_contents(d)
            ts = time.time()
            termination_test, _ = self._perform_data_tests(file_data)
            ts = time.time()
            for k, sub_data in file_data.items():
                if hasattr(sub_data, "keys"):
                    _, data_test = self._perform_data_tests(sub_data)
                    ts = time.time()
                    if termination_test:
                        if k not in self.sub_contents:
                            self.sub_contents.append(k)
                        if k not in self.file_index[d]:
                            self.file_index[d][k] = {}
                            self.file_index[d][k]["data_keys"] = []
                        for key in sub_data.keys():
                            self.file_index[d][k]["data_keys"].append(key)
                            if key not in self.unique_data_keys:
                                self.unique_data_keys.append(key)
                    elif data_test:
                        if "data_keys" not in self.file_index[d]:
                            self.file_index[d]["data_keys"] = []
                        self.file_index[d]["data_keys"].append(k)
                        self.unique_data_keys.append(k)
                else:
                    if "_data" not in self.file_index[d]:
                        self.file_index[d]["_data"] = [k]
                        self.sub_contents.append("_data")
                        _logger.info("created auto data directory _data")
                    if k not in self.file_index[d]["_data"]:
                        self.file_index[d]["_data"].append(k)
        self.unique_data_keys = np.unique(self.unique_data_keys).tolist()
        if len(self.sub_contents) == 0:
            _logger.info("Unique data keys found {}".format(self.unique_data_keys))
        else:
            _logger.info("Data types found: {}".format(self.sub_contents))

    def get_selected_directories(self, directory_keys):
        t = time.time()
        selected_directories = []
        if directory_keys is None:
            _logger.info("Searching in all directories")
            return self.directories
        else:
            for d in self.directories:
                if all(sdk in d for sdk in directory_keys):
                    selected_directories.append(d)
                    _logger.info("User selected {}".format(d))
            _logger.debug("get_selected_directories took: {}".format(time.time() - t))
            return selected_directories

    def get_data(
        self,
        data_key_list=None,
        directories=None,
        num_keys=None,
        exact_keys=False,
        match_accuracy=None,
        psDataManager=None,
    ):
        """method for automatic retrivale of data from h5 file generated by
        ps tool or loop tool
            data_key_list : a list of keys to extract, can be list of keys
            or a list of dicts examples
                list example:
                psDataManager: psDataManager instance into which the data is to be loaded
                data_key_list=['fs.costing.LCOW','fs.water_recovery']
                exact_keys: if exact h5keys are provided or not
                list of dicts example:
                    dict should contain:
                        'filekey': key in h5 or json file
                        'return_key': key to use when returning data (this will replace h5key)
                        'units': (optional) - this will convert imported units if avaialble to supplied units
                        'assign_units': (optional) - this will overwrite default units to specified unit
                        'conversion_factor': (optional) - this will apply manual conversion factor to raw data before assigning units
                            only works when user passes in 'assign_units' option.
                data_key_list=[{'h5key':'fs.costing.LCOW',
                                'return_key':'LCOW'
                                "assign_units": "USD/m**3"},
                                {'h5key':'fs.water_recovery',
                                'return_key':'Water recovery',
                                'units': '%'}]
                num_keys: (optional) - how many keys to return if more the 1 is found for similar named keys
                exact_keys: (optional) - if exact keys should be imported
                match_accuracy: (optional) - how accurately the keys need to match if exact_keys == False
        """

        ts = time.time()
        if num_keys != None:
            self.num_keys = num_keys
        if match_accuracy != None:
            self.search_cut_off = match_accuracy / 100
        if data_key_list == None:
            data_key_list = self.unique_data_keys
            exact_keys = True
            _logger.info("User did not provide data key list, importing ALL data!")
        if directories is None:
            _logger.info("No directories specified, importing all directories!")
        elif isinstance(data_key_list, list) == False:
            raise TypeError("Data key list must be type of list")

        selected_directories = self.get_selected_directories(directories)
        for directory in selected_directories:

            unique_labels = self.file_index[directory]["unique_directory"]
            # print(unique_labels)
            for dkl in data_key_list:
                if isinstance(dkl, dict):
                    key = dkl["filekey"]
                    return_key = dkl["return_key"]
                    import_options = dkl
                else:
                    key = dkl
                    return_key = None
                    import_options = {}
                # print(directory, key)

                data_keys, data_type = self._get_nearest_key(directory, key, exact_keys)

                if data_keys != None:
                    # print("data_keys", data_keys)
                    for i, dk in enumerate(data_keys):
                        # print("data_keys", dk)
                        data = self._get_data_set_auto(
                            directory, data_type, dk, data_object_options=import_options
                        )
                        # print(data)
                        if data is not None:
                            if return_key == None:
                                return_key = dk

                            if len(data_keys) > 1:
                                index_str = data.key_index_str
                                if index_str == None:
                                    index_str = i
                                _return_key = tuple(
                                    [return_key, index_str]
                                )  # "{}_{}".format(return_key, index_str)
                            else:
                                _return_key = return_key
                            return_dir = copy.copy(unique_labels)
                            if "_auto_temp" in return_dir:
                                return_dir.remove("_auto_temp")
                            if self.default_return_directory is not None:
                                idx = [self.default_return_directory]
                                return_dir = idx + return_dir
                            if len(_return_key) == 1:
                                return_dir = idx[0]
                            data.set_label(_return_key)
                            psDataManager.add_data(return_dir, _return_key, data)
        _logger.info("Done importing data in {} seconds!".format(time.time() - ts))
        return psDataManager

    def get_h5_file(self, location):
        self.data_file = h5py.File(location, "r")
        self.raw_data_file = self.data_file
        self.h5_mode = True

    def get_json_file(self, location):
        with open(location) as f:
            self.data_file = json.load(f)
            self.raw_data_file = self.data_file
        self.json_mode = True

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

    def _get_data_set_auto(
        self, directory, data_type, data_key, data_object_options={}
    ):
        self._get_data(directory)
        t = time.time()
        units = "dimensionless"
        data = None

        def _get_data_from_file(data_type, data_key):
            if data_type is None:
                if "value" in self.raw_data_file[data_key]:
                    data = self.raw_data_file[data_key]["value"]
                elif "values" in self.raw_data_file[data_key]:
                    data = self.raw_data_file[data_key]["values"]
                else:
                    data = self.raw_data_file[data_key]
                if "units" in self.raw_data_file[data_key]:
                    units = self.raw_data_file[data_key]["units"]
                else:
                    _logger.info(f"No units for {data_key}")
                    # _logger.warning(f"No units for {data_key}")
                    units = "dimensionless"
            else:
                if "value" in self.raw_data_file[data_type][data_key]:
                    data = self.raw_data_file[data_type][data_key]["value"]
                elif "values" in self.raw_data_file[data_type][data_key]:
                    data = self.raw_data_file[data_type][data_key]["values"]
                else:
                    data = self.raw_data_file[data_type][data_key]
                if "units" in self.raw_data_file[data_type][data_key]:
                    units = self.raw_data_file[data_type][data_key]["units"]
                else:
                    # _logger.warning(f"No units for {data_key}")
                    units = "dimensionless"

            return data, units

        if self.h5_mode:
            data, units = _get_data_from_file(data_type, data_key)
            data = data[()]
            if units != "dimensionless":
                units = units[()].decode()
        if self.json_mode:
            data, units = _get_data_from_file(data_type, data_key)
        if units == "None":
            units = "dimensionless"
        # print(data_key, data, units)
        if isinstance(data, (np.ndarray, list)):
            if len(data) == 0:
                raise ValueError(
                    "No data found for directory {} data type {} data key {}".format(
                        directory, data_type, data_key
                    )
                )
            result = data
            _logger.debug("_get_data_set_auto took: {}".format(time.time() - t))
            t = time.time()
            idx, idx_str = self.get_key_indexes(data_key)
            try:
                data_object = psData(
                    data_key,
                    data_type,
                    result,
                    units,
                    self.get_feasible_idxs(data=result),
                    **data_object_options,
                )
                data_object.key_index = idx
                data_object.key_index_str = idx_str
                return data_object
            except RuntimeError:
                return None
        return None

    def _get_nearest_key(self, directory, data_key, exact_key):
        t = time.time()

        def get_key(data_key, available_keys):
            if data_key in available_keys:
                _logger.debug(
                    "_get_nearest_key took (exact): {}".format(time.time() - t)
                )
                return [data_key]
            elif exact_key:
                return None
            near_keys = difflib.get_close_matches(
                data_key,
                available_keys,
                cutoff=self.search_cut_off,
                n=self.num_keys,
            )
            _logger.debug(
                "_get_nearest_key took (nearest): {}".format(time.time() - t),
            )
            if near_keys != []:
                return near_keys
            else:
                return None

        if self.sub_contents != []:
            for data_type in self.sub_contents:
                if data_type in self.file_index[directory]:
                    available_keys = self.file_index[directory][data_type]["data_keys"]
                    near_keys = get_key(data_key, available_keys)
                    if near_keys is not None:
                        break
        else:
            available_keys = self.file_index[directory]["data_keys"]
            near_keys = get_key(data_key, available_keys)
            data_type = None
        return near_keys, data_type

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

    def _get_raw_data_contents(self, d):
        if self.h5_mode:
            data_file = self.data_file[d]
        elif self.json_mode:
            data_file = self.data_file
            if isinstance(self.raw_data_file, dict):
                for d in d.split("/"):
                    if d != "":
                        data_file = data_file[d]

        return data_file

    def get_dir_keys(self, main_key):
        self._get_data()
        return self.raw_data_file[main_key].keys()

    def get_raw_data(self):
        self._get_data()
        return np.array(self.raw_data_file[()])

    def get_feasible_idxs(self, data=None, val=None):
        if val is None:
            if "solve_successful" in self.raw_data_file:
                filtered = np.array(
                    self.raw_data_file["solve_successful"]["solve_successful"][()],
                    dtype=bool,
                )
            else:
                filtered = False
        elif data is not None:
            feasible = np.zeros(len(data), dtype=bool)
            filtered = np.where(np.array(data) != val)
            feasible[filtered] = True
        return filtered

    def _get_data(self, selected_directory=None, keys=None):
        self.cur_dir = None
        if selected_directory is not None:
            self.cur_dir = selected_directory
            self.raw_data_file = self._get_raw_data_contents(self.cur_dir)

    def get_key_indexes(self, key):
        skey = key.split("[")
        index_list = []
        if len(skey) > 1:
            for s in skey:

                if "]" in s:
                    index = s.split("]")[0]
                    index = index.split(",")
                    for idx in index:
                        try:
                            idx = float(idx)
                        except ValueError:
                            pass
                        index_list.append(idx)
            return index_list, ",".join(map(str, index_list))
        return None, None
