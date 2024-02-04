import h5py
import yaml
import numpy as np
import glob
import copy


class waterTAP_dataImport:
    def __init__(self, data_location, nice_list_location=None):
        if ".h5" not in data_location:
            data_location = data_location + ".h5"
        self.h5_fileLocation = data_location
        self.nice_list_location = nice_list_location

        self.load_nice_names()
        self.get_h5_file(self.h5_fileLocation)
        self.terminating_key = "outputs"
        self.search_keys = True
        self.cur_dir = None
        self.selected_directory = None
        self.get_file_directories()

    def get_h5_file(self, location):
        self.data_file = h5py.File(location, "r")
        self.raw_data_file = self.data_file

    def get_output(
        self,
        key,
        only_feasible=True,
    ):
        self.get_data()

        return self.get_data_set(
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
        self.get_data()
        return self.get_data_set(
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
        sweep_reference_raw = self.get_data_set(
            nom_key,
            main_loc=nom_loc,
            sub_key="value",
        )
        sweep_reference = np.array(
            sweep_reference_raw[sweep_reference_raw == sweep_reference_raw], dtype=int
        )
        diff_reference_raw = self.get_data_set(
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

    def get_data_set(
        self,
        key=None,
        main_loc="outputs",
        sub_key="value",
        only_feasible=True,
        datatype=np.float64,
    ):
        self.get_data()
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
            print(
                "Failed to get data from",
                "got to dir",
                self.cur_dir,
            )
            return None

    def get_dir_keys(self, main_key):
        self.get_data()
        return self.raw_data_file[main_key].keys()

    def get_raw_data(self):
        self.get_data()
        return np.array(self.raw_data_file[()])

    def get_feasible_idxs(self, data=None, val=None):
        self.get_data()
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

    def find_same_conditions(self, keys, error_percent=1, mask=None):
        # idxs=np.array([])
        idxs = None
        for sub_key, value in keys:
            # (sub_key, value)
            data = self.get_output(sub_key, auto_convert=False)

            idxs_temp = np.where(
                (np.array(data) < (value * (1 + error_percent / 100)))
                & (np.array(data) > (value * (1 - error_percent / 100)))
            )[0]
            if len(idxs_temp) > 0:
                if idxs is None:
                    idxs = idxs_temp
                else:
                    idxs = np.hstack((idxs, idxs_temp))

        final_idx = np.zeros(len(data), dtype=bool)
        idxs = np.array(idxs).flatten()
        if len(idxs) > 2:
            counted_idxs, counts = np.unique(np.array(idxs), return_counts=True)
            counted_idxs = counted_idxs[counts == len(keys)]
            final_idx[counted_idxs] = True
        if mask is not None:
            final_idx[mask == False] = False
        return final_idx

    def get_file_directories(self, term_key="outputs"):
        self.directories = []

        def get_directory(current_file_loc, cur_dir=""):
            cur_dir_original = cur_dir
            if "outputs" in current_file_loc.keys():
                if cur_dir not in self.directories:
                    self.directories.append(cur_dir)
                    print("Added dir: {}".format(cur_dir))
                    return True
            for key in current_file_loc.keys():
                if cur_dir == "":
                    cur_dir = key
                else:
                    cur_dir = cur_dir_original + "/" + key
                get_directory(current_file_loc[key], cur_dir=cur_dir)

        get_directory(self.raw_data_file)

    def get_file_tree(self, directory, show_sub_key=False, show_only=None):
        # self.get_data()
        print("File tree for: {}".format(directory))
        for v in list(self.raw_data_file[directory].keys()):
            sb = ""
            for k in list(self.raw_data_file[directory][v].keys()):
                show = True
                if show_only is not None:
                    if show_only not in k:
                        show = False
                if show:
                    print("|---|-", k)
                    if show_sub_key:
                        try:
                            for d in list(self.raw_data_file[v][k].keys()):
                                print("|   |----", d)
                        except KeyError:
                            pass
                        print("|")

    def check_bounds(self, nearness_test=0.1):
        self.get_data()
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

    def load_nice_names(self):
        if self.nice_list_location is not None:
            with open(self.nice_list_location, "r") as ymlfile:
                self.nice_names = yaml.safe_load(ymlfile)
        else:
            self.nice_names = {}

    def get_data(self, keys=None):
        # print("Current key set!", keys, self.current_keys)
        self.cur_dir = None
        if self.selected_directory is not None:
            self.cur_dir = self.selected_directory

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
            self.get_data(key_temp)
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
                    data = self.get_data_set(
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


if __name__ == "__main__":
    data_manager = waterTAP_dataImport(
        r"C:\Users\avdud\Downloads\demo_kestrel_analysisType_parameter_analysis\demo_kestrel_analysisType_parameter_analysis.h5"
    )
    data_manager.get_file_directories()
    data_manager.get_file_tree(data_manager.directories[0])
    # print(list(data['value']))
#    print(list(data_manager.raw_data_file.keys()))
