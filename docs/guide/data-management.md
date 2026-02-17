# Data Management

`PsDataManager` is the central data store. It extends Python's `dict`, using composite tuple keys to store `PsData` objects.

## Creating a Manager

```python
from psPlotKit.data_manager.ps_data_manager import PsDataManager

dm = PsDataManager("my_sweep_results.h5")
```

## Registering Data Keys

Before loading, tell the manager which keys to import:

```python
dm.register_data_key(
    file_key="fs.costing.LCOW",   # key in the .h5 file
    return_key="LCOW",            # your short name
    units="USD/m**3",             # optional: convert to these units
)

dm.register_data_key(
    "fs.water_recovery",
    "recovery",
    assign_units="%",             # assign units without conversion
)
```

### `register_data_key` Parameters

| Parameter | Description |
|-----------|-------------|
| `file_key` | Key path in the HDF5/JSON file |
| `return_key` | Short name for referencing |
| `units` | Convert imported data to these units |
| `assign_units` | Assign units without converting |
| `conversion_factor` | Manual scaling factor |
| `directories` | Restrict to specific directories |

## Loading Data

```python
dm.load_data()
```

`load_data` performs three steps:

1. **Import** — reads data from files for all registered keys
2. **Check import status** — verifies all keys were found (controllable via `check_import_status`)
3. **Evaluate expressions** — computes any registered expressions (controllable via `evaluate_expressions`)

```python
# Warn on missing keys instead of raising
dm.load_data(raise_error=False)

# Skip import checking
dm.load_data(check_import_status=False)

# Skip expression evaluation
dm.load_data(evaluate_expressions=False)
```

## Composite Tuple Keys

Data is stored under composite tuple keys built from directory labels and data keys:

- **Single-directory files:** `("LCOW",)` or simply `"LCOW"`
- **Multi-directory files:** `(("erd_type", "pressure_exchanger"), "membrane_cost", "LCOW")`

## Inspecting Data

```python
dm.display()              # all (directory, data_key) entries
dm.display_keys()         # unique data keys only
dm.display_directories()  # unique directory keys only
```

## Accessing Data

```python
dir_key = dm.directory_keys[0]
lcow = dm.get_data(dir_key, "LCOW")  # returns PsData object
```

## Adding Computed Data

```python
ratio = lcow / recovery
dm.add_data(dir_key, "my_ratio", ratio)
```

## Selecting Data for Plotting

```python
dm.select_data(["LCOW", "recovery"])
selected = dm.get_selected_data()        # dict for plotters
dm.clear_selected_data()                 # reset selection
```

### Selection Parameters

| Parameter | Description |
|-----------|-------------|
| `selected_keys` | List of key names to select |
| `require_all_in_dir` | Only include directories with all keys |
| `exact_keys` | Require exact key match |
| `add_to_existing` | Append to current selection |
| `return_all_if_non_found` | Fall back to all data if no match |

## Reducing / Stacking Data

Combine data across directories:

```python
dm.reduce_data(
    stack_keys="number_of_stages",
    data_key="LCOW",
    reduction_type="min",
)
```

This stacks data from directories sharing `stack_keys`, then applies the reduction (`"min"`, `"max"`, `"unique"`).

## Normalizing Data

```python
dm.normalize_data(
    base_value_dict={"LCOW": 1.0},
    norm_units="%",
)
```

## Evaluating Custom Functions

```python
dm.eval_function(
    directory=dir_key,
    name="custom_calc",
    function=my_function,
    function_dict={"x": "LCOW", "y": "recovery"},
    units="dimensionless",
)
```
