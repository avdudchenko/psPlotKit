To use, import psPlotKit

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
    dm.register_data_key("fs.costing.LCOW",  "LCOW")
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

### Registering and evaluating expressions

Expressions let you derive new data from already-imported keys using
Python arithmetic operators.  Instead of writing expression strings, you
build expression trees with the ExpressionNode / ExpressionKeys API.

    dm = PsDataManager("my_sweep_results.h5")

    dm.register_data_key("fs.costing.LCOW", "LCOW")
    dm.register_data_key("fs.water_recovery", "recovery")

    # Obtain an ExpressionKeys helper — attribute access returns
    # ExpressionNode leaves that can be combined with +, -, *, /, **.
    ek = dm.get_expression_keys()

    # Build an expression tree — the result will be stored under
    # return_key "cost_per_recovery" in every directory that contains
    # both "LCOW" and "recovery".
    dm.register_expression(
        ek.LCOW / ek.recovery,
        return_key="cost_per_recovery",
    )

    # Complex expressions with constants, power, and grouping
    dm.register_expression(
        100 * (ek.LCOW + ek.LCOW) ** 2 / ek.recovery,
        return_key="custom_metric",
    )

    # You can also assign units to the result
    dm.register_expression(
        ek.LCOW * ek.recovery,
        return_key="weighted_metric",
        assign_units="USD",
    )

    # load_data will import keys and then evaluate all expressions
    dm.load_data()

    # The expression results are now available just like any other key
    dm.display()

Note: string expressions are no longer supported — pass an ExpressionNode
tree instead.  If you pass a string you will get a TypeError with
instructions for migrating.

### Accessing and computing on data directly

Each entry in the manager is a PsData object that wraps a numpy array
with physical units. You can retrieve data by directory and key, and
perform arithmetic on PsData objects directly.

    # Retrieve a PsData object for a specific directory
    dir_key = dm.directory_keys[0]
    lcow = dm.get_data(dir_key, "LCOW")

    # Access the raw numpy array
    print(lcow.data)          # e.g. array([0.45, 0.52, 0.61, ...])

    # Access the array with units attached (quantities object)
    print(lcow.data_with_units)

    # Convert units
    lcow.to_units("USD/gal")

    # PsData supports full arithmetic — results are new PsData objects
    recovery = dm.get_data(dir_key, "recovery")

    # Basic operations between two PsData objects
    ratio = lcow / recovery
    double_lcow = lcow + lcow

    # Scalar operations (int/float on either side)
    scaled = lcow * 100
    shifted = lcow + 0.5
    inverted = 1.0 / recovery        # reflected operator

    # Power
    squared = lcow ** 2

    # Negation
    negative = -lcow

    # Chain arbitrarily complex expressions
    result = 100 * (lcow + recovery) ** 2 / recovery

    # The result carries a descriptive data_key
    print(ratio.data_key)      # "(LCOW / recovery)"

    # Store a computed result back into the manager
    dm.add_data(dir_key, "my_ratio", ratio)

This is a toolkit for plotting data generated using Paramter sweep toll

To install download repo:
Install via pip or create new env for development:
    
    conda env create -f psPlotKit.yml

Update via conda:

    conda env update -n psPlotKit --file psPlotKit.yml

Install via conda in existing  (YOUR_ENV) env:

    conda env update -n YOUR_ENV --file psPlotKit.yml