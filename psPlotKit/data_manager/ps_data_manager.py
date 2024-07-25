import numpy as np
from psPlotKit.util.logger import define_logger
import quantities as qs
from psPlotKit.data_manager.ps_data import psData
from psPlotKit.data_manager.data_importer import psDataImport
from psPlotKit.data_manager.ps_costing_tool import psCosting
import copy

__author__ = "Alexander V. Dudchenko (SLAC)"

_logger = define_logger(__name__, "psDataManager", level="INFO")


class psDataManager(dict):
    def __init__(self, data_files=None):
        self.directory_keys = []
        self.data_keys = []
        self.selected_directories = []
        self.min = "min"
        self.max = "max"
        self.where = "where"
        self.reduced_data = "stacked_data"
        self.normalized_data = "normalized_data"
        self.reduced_data_idx = "reduction_idxs"
        self.mask_data = True
        self.global_reduction_directory = None
        if data_files is not None:

            self.psDataImportInstances = []
            if isinstance(data_files, str):
                self.psDataImportInstances.append(psDataImport(data_files))
            else:
                for df in data_files:
                    if isinstance(df, str):
                        self.psDataImportInstances.append(psDataImport(data_files))
                    else:
                        directory = df["return_directory"]
                        file_loc = df["file"]
                        self.psDataImportInstances.append(
                            psDataImport(file_loc, default_return_directory=directory)
                        )

    def load_data(
        self,
        data_key_list=None,
        directories=None,
        exact_keys=False,
        num_keys=None,
        match_accuracy=0.9,
    ):
        """mesthod for automatic retrivale of data from h5 file generated by
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
                exact_keys: (optional) - if exact keys should be imported
                match_accuracy: (optional) - how accurately the keys need to match if exact_keys == False
        """
        for instance in self.psDataImportInstances:
            instance.get_data(
                data_key_list=data_key_list,
                directories=directories,
                num_keys=num_keys,
                exact_keys=exact_keys,
                match_accuracy=match_accuracy,
                psDataManager=self,
            )

    def display(self):
        """func to show file data content in a clean manner"""
        _logger.info("---Displaying current data content---")
        for data in list(self.keys()):
            _logger.info("data_key: {}".format(data))
        _logger.info("-----------Contents end----------")

    def display_keys(self):
        """func to show data keys content in a clean manner"""
        _logger.info("---Displaying current data content---")
        for data in list(self.data_keys()):
            _logger.info("data_key: {}".format(data))
        _logger.info("-----------Contents end----------")

    def display_directories(self):
        """func to show directories content in a clean manner"""
        _logger.info("---Displaying current data content---")
        for data in list(self.directory_keys()):
            _logger.info("data_key: {}".format(data))
        _logger.info("-----------Contents end----------")

    def get_costing(
        self,
        costing_groups,
        costing_block="fs.costing",
        costing_key="costing",
        default_flow="fs.product.properties[0.0].flow_vol_phase[Liq]",
    ):
        for instance in self.psDataImportInstances:
            pscosting = psCosting(
                instance,
                costing_block=costing_block,
                costing_key=costing_key,
                default_flow=default_flow,
            )
            pscosting.define_groups(costing_groups)
            pscosting.get_costing_data(psDataManager=self)

    def _get_data_key(self, udir):
        if isinstance(udir, tuple):
            return udir[-1]
        else:
            return udir

    def _get_data_dir(self, udir):
        if isinstance(udir, tuple):
            return udir[:-1]
        else:
            return udir

    def add_key(self, __dir_key, __key):
        if str(__dir_key) not in str(self.directory_keys):
            self.directory_keys.append(__dir_key)
        if str(__key) not in str(self.data_keys):
            if isinstance(__key, list):
                if len(__key) == 1:
                    __key = __key[0]
                else:
                    __key = tuple(__key)
            self.data_keys.append(__key)

    def add_data(self, __dir_key, __key, __value) -> None:
        __dir_key, __key, __data_dir = self._process_dir_data_keys(__dir_key, __key)
        self.add_key(__dir_key, __key)
        __value.__key = __key
        __value.__dir_key = __dir_key
        return super().__setitem__(__data_dir, __value)

    def _dir_to_tuple(self, _dir_key):
        if isinstance(_dir_key, str):
            return _dir_key
        else:
            new_dir = []
            for subdir in _dir_key:
                if isinstance(subdir, list):
                    new_dir.append(tuple(subdir))
                else:
                    new_dir.append(subdir)
        return tuple(new_dir)

    def _process_dir_data_keys(self, __dir_key, __key):

        # def _process_key(dkey):
        #     if isinstance(dkey, str):
        #         dkey = list([dkey])
        #     return list(dkey)
        if isinstance(__key, list):
            if len(__key) == 1:
                __key = __key[0]
            else:
                __key = tuple(__key)
        # print(__dir_key)
        if isinstance(__dir_key, list):
            _temp_der_list = []
            if len(__dir_key) == 1:
                _temp_der_list.append(__dir_key[0])
            elif len(__dir_key) > 1:
                _temp_der_list = list(__dir_key)
            _temp_der_list.append(__key)
            __data_dir = tuple(_temp_der_list)
        elif isinstance(__dir_key, str):
            __data_dir = tuple((__dir_key, __key))
        elif isinstance(__dir_key, tuple):
            _temp_der_list = list(__dir_key)
            _temp_der_list.append(__key)
            __data_dir = tuple(_temp_der_list)

        return __dir_key, __key, __data_dir

    def get_data(self, __dir_key, __key) -> None:
        __dir_key, __key, __data_dir = self._process_dir_data_keys(__dir_key, __key)
        data = super().__getitem__(__data_dir)
        return data

    def __getitem__(self, __data_dir):
        data = super().__getitem__(__data_dir)
        if self.mask_data and self.reduced_data_idx not in str(__data_dir):
            data = self._check_reduced(self._get_data_dir(__data_dir), data)
        return data

    def _check_reduced(self, data_dir, data):
        _, _, reduced_dir = self._process_dir_data_keys(data_dir, self.reduced_data_idx)
        if reduced_dir in self:
            data.mask_data(self[reduced_dir])
        return data

    def copy_dataset(self, source, directory, key):
        data = self[source]
        self.add_data(directory, key, copy.deepcopy(data))

    def select_data(
        self,
        selected_keys,
        require_all_in_dir=True,
        exact_keys=False,
        add_to_existing=False,
    ):
        if isinstance(selected_keys, str):
            selected_keys = [selected_keys]
        selected_dir_keys = self.select_dir_keys(
            selected_keys, require_all_in_dir, exact_keys
        )
        if add_to_existing:
            self.selected_directories = self.selected_directories + selected_dir_keys
        else:
            self.selected_directories = selected_dir_keys
        return self.selected_directories

    def clear_selected_data(self):
        self.selected_directories = []

    def get_selected_data(self, flatten=False):
        return_list = []
        psData = psDataManager()
        for dir_key in self.selected_directories:
            psData.add_data(self[dir_key].__dir_key, self[dir_key].__key, self[dir_key])
        return psData

    def select_dir_keys(self, selected_keys, require_all_in_dir, exact) -> None:
        """find if provided keys are dir key, and return
        selected dir keys, otherwise return all"""
        dir_keys = []
        current_keys = list(self.keys())

        def _key_dive(key, test_key):
            if isinstance(key, list) or isinstance(key, tuple):
                for k in key:
                    result = _key_dive(k, test_key)
                    if result:
                        return result
            if key == test_key:
                return True
            return False

        for dkey in current_keys:
            num_keys_found = 0
            for key in selected_keys:
                if exact:
                    result = _key_dive(dkey, key)
                    if result:
                        num_keys_found += 1
                    # if isinstance(dkey, str):
                    #     if key == dkey:
                    #         num_keys_found += 1
                    # else:
                    #     for dl in dkey:
                    #         if str(key) == str(dl):
                    #             num_keys_found += 1
                else:
                    if str(key) in str(dkey):
                        num_keys_found += 1
            # assert False
            if len(selected_keys) == num_keys_found and require_all_in_dir:
                dir_keys.append(dkey)
            elif require_all_in_dir == False and num_keys_found > 0:
                # print(dkey, selected_keys)
                dir_keys.append(dkey)
        if len(dir_keys) == 0:
            dir_keys = current_keys[:]
        return dir_keys

    def get_directory_keys(self, selected_keys):
        """find if provided keys are dir key, and return
        selected dir keys, otherwise return all"""
        dir_keys = []
        for key in selected_keys:
            for dkey in self.directory_keys:
                if key in dkey:
                    dir_keys.append(dkey)
        if len(dir_keys) == 0:
            dir_keys = self.directory_keys[:]
        return dir_keys

    def get_data_keys(self, selected_keys):
        """find if provided keys are data key, and return
        selected data keys, otherwise return all"""
        data_keys = []
        for key in selected_keys:
            for dkey in self.data_keys:
                if key in dkey:
                    data_keys.append(dkey)
        if len(data_keys) == 0:
            data_keys = self.data_keys[:]
        return data_keys

    def normalize_data(self, base_value_dict, norm_units="%", related_keys=None):
        def get_nearest_vals(data, base_value):
            delta = np.abs(data - base_value)
            min_vals = np.argsort(delta)
            nearest_values = data[min_vals][:2]
            nearest_idxs = min_vals[:2]
            return nearest_idxs

        if related_keys != None:
            if isinstance(related_keys, (str, tuple)):
                related_keys = [related_keys]
        for key, base_value in base_value_dict.items():
            select_key = self.select_data([key])
            for skey in select_key:
                data = self[skey].data
                norm_data = (data - base_value) / base_value
                base_skey = list(skey)
                base_skey.remove(key)
                norm_base_skey = base_skey[:]
                norm_base_skey.append(self.normalized_data)
                # print(norm_base_skey, key)
                self.add_data(
                    norm_base_skey,
                    key,
                    psData(
                        key,
                        self.normalized_data,
                        norm_data,
                        import_units="dimensionless",
                        units=norm_units,
                    ),
                )
                for related_key in related_keys:
                    idx = np.where(data == base_value)[0]
                    if len(idx) == 0:
                        _logger.info(
                            "Could not find exact base value using interpolation on {} {}".format(
                                base_skey,
                                related_key,
                            )
                        )
                        nearest_idxs = get_nearest_vals(data, base_value)
                        related_data = self.get_data(base_skey, related_key).data

                        xp = data[nearest_idxs]

                        sort_idx = np.argsort(xp)
                        xp_sorted = xp[sort_idx]
                        if base_value > xp_sorted[0] and base_value < xp_sorted[1]:
                            interp = np.interp(
                                base_value,
                                data[nearest_idxs][sort_idx],
                                related_data[nearest_idxs][sort_idx],
                            )
                            # nearest_val_avg = np.average(related_data[nearest_idxs])
                            norm_related_data = (related_data - interp) / interp
                            self.add_data(
                                norm_base_skey,
                                related_key,
                                psData(
                                    related_key,
                                    self.normalized_data,
                                    norm_related_data,
                                    import_units="dimensionless",
                                    units=norm_units,
                                ),
                            )
                        else:
                            _logger.info(
                                "Could not interpolate as base_value is outside of input range"
                            )
                    elif len(idx) == 1:
                        related_data = self.get_data(base_skey, related_key).data
                        norm_related_data = (
                            related_data - related_data[idx]
                        ) / related_data[idx]
                        self.add_data(
                            norm_base_skey,
                            related_key,
                            psData(
                                related_key,
                                self.normalized_data,
                                norm_related_data,
                                import_units="dimensionless",
                                units=norm_units,
                            ),
                        )
                    else:
                        _logger.warning(
                            "Could not find base value in index, and could not modify related key"
                        )

    def eval_function(
        self, directory, name, function, function_dict, units="dimensionless"
    ):
        """
        used to perform math operations on imported data, will result of eval as new data set
            directory: the directory in which to save data
            name : name of new data set
            function : string that describes operations (e.g. np.sum(x)+10*y)
            function_dict : dictionary that connects variables keys in data set to variables in function
                Dictionary must contain the variable in the function, and keys relevant to dictionary, can be single key or a list of keys
                optionally pass in "units" key to specify which units the data should be converted to before operation
                {
                x: {'keys': ['fs.NaCl',fs.H2O],units='PPM'},
                y: {'keys': fs.recovery}
                }

        """

        def get_dim_data(key, to_units=None):

            if isinstance(key, list):
                key = tuple(key)
            if isinstance(key, np.ndarray):
                key = tuple(key)
            if to_units is not None:
                _data = self[key]
                _data.to_units(to_units)
                d = self[key].data
            else:
                d = self[key].data
            return d

        _function_dict = {}
        _function = copy.copy(function)
        for key, data_keys in function_dict.items():

            if isinstance(data_keys["keys"], list):
                data = []
                for k in data_keys["keys"]:
                    data.append(
                        np.array(get_dim_data(k, to_units=data_keys.get("units")))
                    )
            else:
                data = np.array(
                    get_dim_data(data_keys["keys"], to_units=data_keys.get("units"))
                )
            _function_dict[key] = np.array(data)
            # _function = _function.replace(key, f"np.array({key})")
        # if "np." in function:
        _function_dict["np"] = np
        _logger.info(
            "Evaluating function: {}, new dir and key {} {}".format(
                function, directory, name
            )
        )
        result_data = eval(_function, _function_dict)
        # if isinstance(directory, (tuple, list)):
        #     directory = [directory]
        print(result_data)
        self.add_data(
            directory,
            name,
            psData(
                name,
                "evaluated function",
                result_data,
                import_units=units,
            ),
        )

    def generate_data_stack(
        self, stack_keys, data_key, reduction_type, pad_missing_data=False
    ):
        """stacks data into single dataset from diffrent directories
        stack_keys: defines over which keys that data would be stacked, will auto identify indexes
        data_key: defines which datakey to stack,
        reduction_type: if data to be used to generate a reduction index global to given directory
        pad_missing_data: if global filter is available, and matches current directory will pad with specified value
        will add a new data set to unique directory with map, returns the newly generated keys
        """
        dir_to_stack = []
        stack_idxs = []
        unique_dirs = {}
        working_dirs = []

        def search_dir(stack_keys, dkey):
            for udir in stack_keys:
                if dkey in udir:
                    return udir
                else:
                    result = search_dir(udir, dkey)
            return result

        def sort_idxs(idxs):
            try:
                sorted_idxs = np.argsort(idxs)
                idxs = np.array(idxs)[sorted_idxs]
                idx_type = float
            except ValueError:
                _logger.info("Could not sort idxs {}".format(idxs))
                _logger.info("Stacking with default order")
                sorted_idxs = list(range(len(idxs)))
                idx_type = str
            return sorted_idxs, idxs, idx_type

        for udir in self.keys():
            # print("udir", udir)
            if "stacked_data" not in str(udir) and str(data_key) in str(
                self._get_data_key(udir)
            ):

                all_keys = all(dkey in str(udir) for dkey in stack_keys)

                if all_keys and str(data_key) in str(udir):
                    dir_to_stack.append(udir)
                    ukey = None
                    work_dir = None
                    for ud in udir:
                        all_keys = all(dkey in str(ud) for dkey in stack_keys)
                        if all_keys:
                            ukey = ud
                        elif str(data_key) not in str(ud):
                            if work_dir is None:
                                work_dir = ud
                            else:
                                work_dir.append(ud)
                    if ukey is None:
                        raise IndexError(
                            "Could not find index to stack over dir: {}, stack keys {}".format(
                                stack_keys, udir
                            )
                        )
                    ukey = list(ukey)
                    for dkey in stack_keys:
                        print(dkey, ukey)
                        ukey.remove(dkey)
                    if len(ukey) == 1:
                        ukey = ukey[0]
                    stack_dir = list(udir)[:]
                    stack_dir.remove(data_key)
                    stack_idxs.append(ukey)
                    if work_dir not in unique_dirs:
                        unique_dirs[work_dir] = {
                            "dirs": [udir],
                            "stack_dir": [stack_dir],
                            "idxs": [ukey],
                        }
                    else:
                        unique_dirs[work_dir]["dirs"].append(udir)
                        unique_dirs[work_dir]["stack_dir"].append(stack_dir)
                        unique_dirs[work_dir]["idxs"].append(ukey)
        if unique_dirs != {}:
            _logger.info("Stacking: {}".format(dir_to_stack))
            _logger.info("Stack indexes are: {}".format(stack_idxs))
            _logger.info("Unique stacks are: {}".format(unique_dirs))
            new_dirs = []
            new_keys = []

            for uq, items in unique_dirs.items():
                idxs = items["idxs"]
                dirs = items["dirs"]
                stack_dir = items["stack_dir"]
                stack_idxs, idxs, idx_type = sort_idxs(idxs)
                temp_map_data = []
                map_units = []
                temp_map_idxs = []
                print(stack_idxs, idxs)
                for i in stack_idxs:
                    data = self[tuple(dirs[i])]
                    print(tuple(dirs[i]), data.data_key)
                    # print(data.data_key)
                    temp_map_data.append(data.data)
                    data_shape = data.data.shape

                    ia = np.zeros(data_shape)
                    if isinstance(idxs[i], str):
                        ia = np.array(ia, dtype=str)
                        # print("string mode")
                    ia[:] = idxs[i]
                    temp_map_idxs.append(ia)
                    map_units.append(data.sunits)
                if (
                    self.global_reduction_directory is not None
                    and self.global_reduction_directory.get(uq) is not None
                    and pad_missing_data is not False
                ):
                    global_stack_idxs, global_idxs, idx_type = sort_idxs(
                        self.global_reduction_directory[uq]["idxs"]
                    )
                    global_stack_dirs = self.global_reduction_directory[uq]["stack_dir"]
                    map_data = []
                    map_idxs = []
                    appended_index = 0
                    for i in global_stack_idxs:
                        if str(global_stack_dirs[i]) not in str(stack_dir):
                            pad = np.zeros(data_shape) + pad_missing_data
                            map_data.append(pad)
                            ia = np.zeros(data_shape)
                            if isinstance(global_idxs[i], str):
                                ia = np.array(ia, dtype=str)
                            ia[:] = global_idxs[i]
                            map_idxs.append(ia)
                        else:
                            map_data.append(temp_map_data[appended_index])
                            map_idxs.append(temp_map_idxs[appended_index])
                            appended_index += 1
                else:
                    map_data = temp_map_data
                    map_idxs = temp_map_idxs
                units = np.unique(map_units)
                if len(units) > 1:
                    _logger.info("Units are inconsistent, using dimensionless")
                    units = "dimensionless"
                else:
                    units = units[0]
                print(data_key, map_data)
                new_data = psData(
                    data_key,
                    "stacked_data",
                    map_data,
                    units,
                    data_label=data.data_label,
                )
                idx_data = psData(
                    stack_keys, "stacked_data_idxs", map_idxs, "dimensionless"
                )
                new_dir = [self.reduced_data]
                if uq is not None:
                    new_dir.append(uq)

                self.add_data(new_dir, data_key, new_data)
                self.add_data(new_dir, stack_keys, idx_data)
                if reduction_type is not None:
                    reduced_idxs, sd = self._reduce_data(
                        reduction_type,
                        new_data.data,
                    )
                    idx_data = psData(
                        stack_keys, "stacked_data_idxs", reduced_idxs, "dimensionless"
                    )
                    idx_data.filter_type = "2D"
                    idx_data.filter_data_shape = sd
                    self.add_data(new_dir, self.reduced_data_idx, idx_data)
                    new_keys.append(self.reduced_data_idx)
                new_dirs.append(new_dir)
                new_keys.append(data_key)
                new_keys.append(stack_keys)
        return unique_dirs
        # _logger.info("Added data to dirs {}".format(new_dirs))
        # _logger.info("Created new data keys {}".format(new_keys))

    def add_mask(self, directory, indexes, data_shape=None, shape="1D"):
        idx_data = psData("filter_idx", "filter_idx", indexes, "dimensionless")
        idx_data.filter_type = shape
        if data_shape == None:
            idx_data.data_shape = indexes.shape
        else:
            idx_data.data_shape = data_shape
        self.add_data(directory, "reduction_idxs", idx_data)
        self.mask_data = True

    def _reduce_data(self, reduction_type, data):
        if reduction_type == "min":
            nan_max = np.nanmax(data)

            nan_max = 1e10
            data = np.nan_to_num(data, nan=nan_max)
            sd = data.shape
            idx = np.nanargmin(data, axis=0)
            min_data = np.take_along_axis(data, np.expand_dims(idx, axis=0), axis=0)[0]
            r_idx = np.array(idx, dtype=float)
            r_idx[min_data == nan_max] = np.nan
        else:
            raise TypeError("Reduction type {} not implemented".format(reduction_type))
        return r_idx, sd

    def stack_all_data(self, stack_keys, pad_missing_data):
        current_keys = self.data_keys[:]
        for data_key in current_keys:
            if self.reduced_data not in str(data_key):
                print("stack_keys", stack_keys, data_key)
                self.generate_data_stack(
                    stack_keys,
                    data_key,
                    reduction_type=None,
                    pad_missing_data=pad_missing_data,
                )

    def reduce_data(
        self,
        stack_keys=None,
        data_key=None,
        reduction_type=None,
        stack_all_data=True,
        pad_missing_data=0,
    ):
        """this function will stack data based on axis using min, max or unique function
        stack_keys: keys that identify a stack (example is 'number_of_stages' or 'flow_mass_phase_comp)
            if directory has multiple keys e.g. ((erd_type, x), (bgw, number_of_stages, 1), LCOW) then supply a list of keys that
            identify the unique axis excluding the index e.g stack_keys=['bgw','number_of_stages]
        data_key: data key that should be used in the stack todo reduction on
        reduction_type: if data should be reduced by finding minium, maximum, or exact value in specified axis_keys
        """
        if isinstance(stack_keys, str):
            stack_keys = [stack_keys]

        # for axk in axis_keys:
        mask_data = False
        if self.mask_data == True:
            mask_data = True
            self.mask_data = False
        self.global_reduction_directory = self.generate_data_stack(
            stack_keys, data_key, reduction_type
        )
        print("global_uq", self.global_reduction_directory)
        # assert False
        if stack_all_data:
            self.stack_all_data(stack_keys, pad_missing_data)
            # _logger.info("Added data to dirs {}".format(new_dirs))
            # _logger.info("Created new data keys {}".format(new_keys))
        self.mask_data = mask_data
