import h5py
import numpy as np
import glob
import copy
import re
from psPlotKit.util import logger
from psPlotKit.data_manager.ps_data import psData
from psPlotKit.data_manager.ps_data_manager import psDataManager
import difflib
import time

__author__ = "Alexander V. Dudchenko (SLAC)"

_logger = logger.define_logger(__name__, "psDataImport", level="DEBUG")


class psDataImport:
    def __init__(self, data_location):
        _logger.info("data import v0.2")
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
        self.num_keys = 1

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
                    for d in self.directories:
                        if k in d.split("/"):
                            kf = str_to_num(k)
                            # if isinstance(kf, int) or isinstance(kf, float):
                            idx = np.where(str(kf) == np.array(d.split("/")))[0]
                            if len(idx) == 1:
                                try:
                                    kf = tuple([d.split("/")[idx[0] - 1], kf])
                                except IndexError:
                                    pass
                            if kf not in self.directory_indexes:
                                self.directory_indexes[kf] = []
                            self.directory_indexes[kf].append(d)
                            if "unique_directory" not in self.file_index[d]:
                                self.file_index[d]["unique_directory"] = [kf]
                            else:
                                self.file_index[d]["unique_directory"].append(kf)
                            if kf not in self.global_unique_directories:
                                self.global_unique_directories.append(kf)
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
        self.unique_data_keys = []
        for d in self.file_index:
            file_data = self.raw_data_file[d]

            for k, sub_data in file_data.items():
                if k not in self.sub_contents:
                    self.sub_contents.append(k)
                self.file_index[d][k] = []
                for key in sub_data.keys():
                    self.file_index[d][k].append(key)
                    if key not in self.unique_data_keys:
                        self.unique_data_keys.append(key)
        _logger.info("Data types found: {}".format(self.sub_contents))

    def get_selected_directories(self):
        t = time.time()
        selected_directories = []

        if self.directory_keys == []:
            _logger.info("Searching in all directories")
            return self.directories
        else:
            for d in self.directories:
                if all(sdk in d for sdk in self.directory_keys):
                    selected_directories.append(d)
                    _logger.info("User selected {}".format(d))
            _logger.debug("get_selected_directories took: {}".format(time.time() - t))
            return selected_directories

    def get_data(self, data_key_list=None, num_keys=None):
        """method for autmatic retrivale of data from h5 file generated by
        ps tool or loop tool
            data_key_list : a list of keys to extract, can be list of keys
            or a list of dicts examples
                list example:
                data_key_list=['fs.costing.LCOW','fs.water_recovery']
                list of dicts example:
                    dict should contain:
                        'h5key': key in h5 file and unit model
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
        """

        ts = time.time()
        if num_keys != None:
            self.num_keys = num_keys
        if data_key_list == None:
            data_key_list = self.unique_data_keys
            _logger.info("User did not provide data key list, importing ALL data!")
        elif isinstance(data_key_list, list) == False:
            raise TypeError("Data key list must be type of list")

        selected_directories = self.get_selected_directories()
        collected_data = psDataManager()

        for directory in selected_directories:
            unique_labels = self.file_index[directory]["unique_directory"]
            for dkl in data_key_list:
                if isinstance(dkl, dict):
                    key = dkl["h5key"]
                    return_key = dkl["return_key"]
                    import_options = dkl
                else:
                    key = dkl
                    return_key = None
                    import_options = {}
                data_keys, data_type = self._get_nearest_key(directory, key)
                for i, dk in enumerate(data_keys):

                    if return_key == None:
                        return_key = dk

                    data = self._get_data_set_auto(
                        directory, data_type, dk, data_object_options=import_options
                    )
                    if len(data_keys) > 1:
                        index_str = data.key_index_str
                        if index_str == None:
                            index_str = i
                        _return_key = tuple(
                            [return_key, index_str]
                        )  # "{}_{}".format(return_key, index_str)
                    else:
                        _return_key = return_key
                    idx = copy.copy(unique_labels)
                    idx.append(_return_key)
                    data.set_label(_return_key)
                    collected_data.add_data(unique_labels, _return_key, data)
        _logger.info("Done importing data in {} seconds!".format(time.time() - ts))
        return collected_data

    def get_h5_file(self, location):
        self.data_file = h5py.File(location, "r")
        self.raw_data_file = self.data_file

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
        try:
            data = self.raw_data_file[data_type][data_key]["value"][()]
        except (KeyError, ValueError, TypeError):
            data = self.raw_data_file[data_type][data_key][()]
        try:
            units = self.raw_data_file[data_type][data_key]["units"][()].decode()
            if units == "None":
                units = "dimensionless"
            # units.decode()
            # print(units)
        except (KeyError, ValueError, TypeError):
            units = "dimensionless"

        if len(data) == 0:
            raise ValueError(
                "No data found for directory {} data type {} data key {}".format(
                    directory, data_type, data_key
                )
            )
        result = np.array(data, dtype=np.float64)
        _logger.debug("_get_data_set_auto took: {}".format(time.time() - t))
        t = time.time()
        idx, idx_str = self.get_key_indexes(data_key)
        data_object = psData(
            data_key,
            data_type,
            result,
            units,
            self.get_feasible_idxs(),
            **data_object_options,
        )
        data_object.key_index = idx
        data_object.key_index_str = idx_str
        return data_object

    def _get_nearest_key(self, directory, data_key):
        t = time.time()
        for data_type in self.sub_contents:
            available_keys = self.file_index[directory][data_type]
            if data_key in available_keys:
                return [data_key], data_type

            near_keys = difflib.get_close_matches(
                data_key, available_keys, cutoff=self.search_cut_off, n=self.num_keys
            )  # , n=0.8)
            _logger.debug("_get_nearest_key took: {}".format(time.time() - t))
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

    def _get_data(self, selected_directory=None, keys=None):
        # print("Current key set!", keys, self.current_keys)
        self.cur_dir = None
        if selected_directory is not None:
            self.cur_dir = selected_directory
            # self.selected_directory = None
            self.raw_data_file = self.data_file[self.cur_dir]
            # print("Using directory: {}".format(self.cur_dir))

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
