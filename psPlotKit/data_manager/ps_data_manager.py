import numpy as np
from psPlotKit.util.logger import define_logger
import quantities as qs
from psPlotKit.data_manager.ps_data import psData

_logger = define_logger(__name__, "psDataManager")


class psDataManager(dict):
    def __init__(self):
        self.directory_keys = []
        self.data_keys = []
        self.min = "min"
        self.max = "max"
        self.where = "where"

    def add_key(self, __dir_key, __key):
        if tuple(__dir_key) not in self.directory_keys:
            self.directory_keys.append(__dir_key)
        if __key not in self.data_keys:
            self.data_keys.append(__key)

    def add_data(self, __dir_key, __key, __value) -> None:
        self.add_key(__dir_key, __key)
        return super().__setitem__(
            self._process_dir_data_keys(__dir_key, __key), __value
        )

    def _process_dir_data_keys(self, __dir_key, __key):
        def _process_key(dkey):
            if isinstance(dkey, str):
                dkey = list([dkey])
            return list(dkey)

        __dir_key = _process_key(__dir_key)
        __key = _process_key(__key)
        __data_dir = __dir_key[:]
        if len(__key) > 1:
            __key = tuple(__key)
            __data_dir.append(__key)
        elif len(__key) == 1:
            __data_dir.append(__key[0])
        __data_dir = tuple(__data_dir)
        return __data_dir

    def get_data(self, __dir_key, __key) -> None:

        return super().__getitem__(self._process_dir_data_keys(__dir_key, __key))

    def select_data(self, selected_keys) -> None:
        current_keys = self.keys()
        self.selected_dir_keys = self.select_dir_keys(selected_keys)
        # self.selected_dir_keys = self.get_directory_keys(selected_keys)
        # self.selected_data_keys = self.get_data_keys(selected_keys)
        print(self.selected_dir_keys)

    def get_selected_data(self, flatten=False):
        return_list = []
        psData = psDataManager()
        for dir_key in self.selected_dir_keys:
            psData[dir_key] = self[dir_key]
        return psData

    def select_dir_keys(self, selected_keys):
        """find if provided keys are dir key, and return
        selected dir keys, otherwise return all"""
        dir_keys = []
        current_keys = self.keys()
        for key in selected_keys:
            for dkey in current_keys:
                if key in str(dkey):
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
                print(key, dkey)
                if key in dkey:
                    data_keys.append(dkey)
        if len(data_keys) == 0:
            data_keys = self.data_keys[:]
        return data_keys

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
            if to_units is not None:
                self[key].to_units(to_units)
                d = self[key].data
            else:
                d = self[key].data
            return d

        for key, data_keys in function_dict.items():

            if isinstance(data_keys["keys"], list):
                data = []
                for k in data_keys["keys"]:
                    data.append(get_dim_data(k, data_keys.get("units")))
            else:
                data = get_dim_data(data_keys["keys"], data_keys.get("units"))
            function_dict[key] = data
        if "np." in function:
            function_dict["np"] = np
        _logger.info("Evaluating function: {}".format(function))
        result_data = eval(function, function_dict)
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

    def generate_data_stack(self, dir_keys, data_key):
        """stacks data into single dataset from diffrent directories
        'dir_keys: defines over which keys that data would be stacked, will auto identify indexes

        will add a new data set to unique directory with map, returns the newly generated keys
        """
        dir_to_stack = []
        stack_idxs = []
        unique_dirs = {}

        def search_dir(dir_keys, dkey):
            for udir in dir_keys:
                if dkey in udir:
                    return udir
                else:
                    result = search_dir(udir, dkey)
            return result

        for udir in self.directory_keys:
            for ukey in udir:
                for dkey in dir_keys:
                    if dkey in ukey:
                        dir_to_stack.append(udir)
                        ukey = list(ukey)
                        ukey.remove(dkey)
                        if len(ukey) == 1:
                            ukey = ukey[0]
                        stack_idxs.append(ukey)
                    else:
                        if ukey not in unique_dirs:
                            unique_dirs[ukey] = {"dirs": [], "idxs": []}
        if unique_dirs == {}:
            unique_dirs[""] = {"dirs": [], "idxs": []}
        for key, dir_data in unique_dirs.items():
            for i, dts in enumerate(dir_to_stack):
                if str(key) in str(dts) or key == "":
                    unique_dirs[key]["dirs"].append(dts)
                    unique_dirs[key]["idxs"].append(stack_idxs[i])
        _logger.info("Stacking: {}".format(dir_to_stack))
        _logger.info("Stack indexes are: {}".format(stack_idxs))
        _logger.info("Unique stacks are: {}".format(unique_dirs))
        new_dirs = []
        new_keys = []
        for uq, items in unique_dirs.items():
            idxs = items["idxs"]
            dirs = items["dirs"]
            try:
                sidxs = np.argsort(idxs)
            except ValueError:
                _logger.info("Could not sort idxs {}".format(idxs))
                _logger.info("Stacking with default order")
                sidxs = list(range(len(idxs)))
            map_data = []
            map_units = []
            map_idxs = []
            for i in sidxs:

                print(tuple(dirs[i]), idxs[i])

                data = self.get_data(tuple(dirs[i]), data_key)
                map_data.append(data.data)
                ia = np.zeros(data.data.shape)
                ia[:] = idxs[i]
                map_idxs.append(ia)
                map_units.append(data.sunits)
            units = np.unique(map_units)
            if len(units) > 1:
                _logger.info("Units are inconsistent, using dimensionless")
                units = "dimensionless"
            else:
                units = units[0]
            new_data = psData(data_key, "stacked_data", map_data, units)
            idx_data = psData(dir_keys, "stacked_data_idxs", map_idxs, "dimensionless")
            self.add_data(uq, "{}_stack".format(data_key), new_data)
            self.add_data(uq, "{}".format(" ".join(dir_keys)), idx_data)
            new_dirs.append(uq)
            new_keys.append("{}_stack".format(data_key))
            new_keys.append("{}".format(" ".join(dir_keys)))
        _logger.info("Added data to dirs {}".format((new_dirs)))
        _logger.info("Created new data keys {}".format(np.unique(new_keys)))

    def reduce_data(self, dir_keys=None, axis_keys=None, reduction_type=None):
        """this function will a selected stack based on axis using min, max or unique function
        dir_keys: keys that identify a stack (example is 'number_of_stages' or 'flow_mass_phase_comp)
        axis_key: data key that should be used in the stack todo reduction on
        reduction_type: if data should be reduced by finding minium, maximum, or exact value in specified axis_keys
        """
        if isinstance(dir_keys, str):
            dir_keys = [dir_keys]
        if isinstance(axis_keys, str):
            axis_keys = [axis_keys]
        for axk in axis_keys:
            stack_keys = self.generate_data_stack(dir_keys, axk)
