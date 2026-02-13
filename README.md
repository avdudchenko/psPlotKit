## PsDataManager

PsDataManager is the central data store for importing, inspecting, and
computing on parameter-sweep data from HDF5 (or JSON) files. The typical
workflow is: create a manager → register keys → (optionally) register
expressions → call load_data().

### Basic import

    from psPlotKit.data_manager.ps_data_manager import PsDataManager

    # Point to one or more .h5 files produced by the PS tool
    dm = PsDataManager("my_sweep_results.h5")

    # Register the data keys you want to import.
    # file_key  : the key as it appears in the .h5 file
    # return_key: the short name you will use to refer to the data
    dm.register_data_key(file_key="fs.costing.LCOW",  return_key="LCOW")
    dm.register_data_key("fs.water_recovery", "recovery", units="%")
    dm.register_data_key(
        "fs.costing.reverse_osmosis.membrane_cost",
        "membrane_cost",
        assign_units="USD/m**2",
    )

    # load_data imports the data AND automatically:
    #   1. checks that every registered key was found  (check_import_status)
    #   2. evaluates any registered expressions         (evaluate_expressions)
    dm.load_data()


All three post-load steps can be controlled individually:

    # Warn instead of raising on missing keys
    dm.load_data(raise_error=False)

    # Skip import-status checking entirely
    dm.load_data(check_import_status=False)

    # Skip expression evaluation
    dm.load_data(evaluate_expressions=False)

### Inspecting loaded data

    # Show every (directory, data_key) entry stored in the manager
    dm.display()

    # Show only the unique data keys
    dm.display_keys()

    # Show only the unique directory keys
    dm.display_directories()
If the file has a single directory generated paramter sweep tool, it will have three sub-directories (outputs, solve_successful, sweep_params) that data manager will import data directly and no sub-directories will exist and can be viewed by calling     

Resulting in: 

    PsDataManager 00:27:31 INFO: ---Displaying current data content---
    PsDataManager 00:27:31 INFO: data_key: LCOW
    PsDataManager 00:27:31 INFO: data_key: membrane_cost
    PsDataManager 00:27:31 INFO: -----------Contents end----------

If a loop_tool is used for example and multiple directories exist, it will look like this:

    PsDataManager 00:25:58 INFO: ---Displaying current data content---
    PsDataManager 00:25:58 INFO: data_key: (('erd_type', 'pressure_exchanger'), 'membrane_cost', 'LCOW')
    PsDataManager 00:25:58 INFO: data_key: (('erd_type', 'pressure_exchanger'), 'membrane_cost', 'membrane_cost')
    PsDataManager 00:25:58 INFO: data_key: (('erd_type', 'pressure_exchanger'), 'membrane_group', 'LCOW')
    PsDataManager 00:25:58 INFO: data_key: (('erd_type', 'pressure_exchanger'), 'membrane_group', 'membrane_cost')
    PsDataManager 00:25:58 INFO: data_key: (('erd_type', 'pump_as_turbine'), 'membrane_cost', 'LCOW')
    PsDataManager 00:25:58 INFO: data_key: (('erd_type', 'pump_as_turbine'), 'membrane_cost', 'membrane_cost')
    PsDataManager 00:25:58 INFO: data_key: (('erd_type', 'pump_as_turbine'), 'membrane_group', 'LCOW')
    PsDataManager 00:25:58 INFO: data_key: (('erd_type', 'pump_as_turbine'), 'membrane_group', 'membrane_cost')
    PsDataManager 00:25:58 INFO: -----------Contents end----------

### Deal with bad imports

The file_key is the name of they key saved in the .h5 and or .json file. It is easy to not get it right. If you use standard load_data method, the load will fail and a error will be raised, it will include missing file_keys that were not imported and closest matches, something like this:

    # import bad data key 
    data_manager.register_data_key(
            "fs.costing.reDer_osmosis.membrane_cost", "membrane cost"
        )

The error wil look like this:

    PsDataManager 00:36:06 WARNING: 1 registered key(s) were NOT imported.
    PsDataManager 00:36:06 WARNING:   return_key='membrane cost' (filekey='fs.costing.reDer_osmosis.membrane_cost') was not imported.
    PsDataManager 00:36:06 WARNING:     Nearest available keys in file D:\github\psPlotKit\src\psPlotKit\data_manager\tests\multi_dir_test.h5 (instance 0):
    PsDataManager 00:36:06 WARNING:       fs.costing.reverse_osmosis.membrane_cost
    PsDataManager 00:36:06 WARNING:       fs.costing.reverse_osmosis.factor_membrane_replacement

### Registering and evaluating expressions

Expressions let you derive new data from already-imported keys using
arithmetic (+, -, *, /) and parentheses. The expression string uses the
return_keys you chose during registration.

    dm = PsDataManager("my_sweep_results.h5")

    dm.register_data_key("fs.costing.LCOW", "LCOW")
    dm.register_data_key("fs.water_recovery", "recovery")

    # Register an expression — the result will be stored under the
    # return_key "cost_per_recovery" in every directory that contains
    # both "LCOW" and "recovery".
    dm.register_expression(
        "LCOW / recovery",
        return_key="cost_per_recovery",
    )

    # You can also assign units to the result
    dm.register_expression(
        "(LCOW + LCOW) * recovery",
        return_key="weighted_metric",
        assign_units="USD",
    )

    # load_data will import keys and then evaluate all expressions
    dm.load_data()

    # The expression results are now available just like any other key
    dm.display()

### Accessing and computing on data directly

Each entry in the manager is a PsData object that wraps a numpy array
with physical units. You can retrieve data by directory and key, and
perform arithmetic on PsData objects directly.

    # Retrieve a PsData object for a specific directory
    dir_key = dm.directory_keys[0]
    lcow = dm.get_data(dir_key, "LCOW")

    # You can also access it as a regular dicitonary
    lcow = dm[dir_key, "LCOW]

    # Access the raw numpy array
    print(lcow.data)          # e.g. array([0.45, 0.52, 0.61, ...])

    # Access the array with units attached (quantities object)
    print(lcow.data_with_units)

    # Convert units
    lcow.to_units("USD/gal")

    # PsData supports arithmetic — results are new PsData objects
    recovery = dm.get_data(dir_key, "recovery")
    ratio = lcow / recovery
    double_lcow = lcow + lcow

    # The result carries a descriptive data_key
    print(ratio.data_key)      # "(LCOW / recovery)"

    # Store a computed result back into the manager
    dm.add_data(dir_key, "my_ratio", ratio)


# Installation 

To install:

    pip install git+https://github.com/avdudchenko/psPlotKit.git

Install via conda env for development after cloning the repo:
    
    conda env create -f psPlotKit.yml

Update via conda:

    conda env update -n psPlotKit --file psPlotKit.yml

Install via conda in existing  (YOUR_ENV) env:

    conda env update -n YOUR_ENV --file psPlotKit.yml