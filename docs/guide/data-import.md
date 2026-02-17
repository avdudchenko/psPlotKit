# Data Import

`PsDataImport` reads `.h5` and `.json` files produced by the Parameter Sweep (PS) tool and Loop tool, auto-discovers directories, and indexes data keys.

## File Structure

HDF5 files from the PS tool contain a hierarchical structure:

- **Single-directory sweeps** have three sub-groups: `outputs`, `solve_successful`, `sweep_params`
- **Loop tool results** have multiple named directories, each with the same sub-groups

`PsDataImport` handles both cases automatically.

## Basic Usage

```python
from psPlotKit.data_manager.data_importer import PsDataImport

importer = PsDataImport("my_results.h5")
```

### Specifying Data Keys

Data keys can be passed as dictionaries with the following fields:

| Field | Required | Description |
|-------|----------|-------------|
| `filekey` | Yes | The key path as it appears in the `.h5` file |
| `return_key` | Yes | Short name for referencing the data |
| `units` | No | Target units for conversion |
| `assign_units` | No | Units to assign (no conversion) |
| `conversion_factor` | No | Manual scaling factor |
| `directories` | No | Restrict import to specific directories |

```python
data_keys = [
    {"filekey": "fs.costing.LCOW", "return_key": "LCOW", "units": "USD/m**3"},
    {"filekey": "fs.water_recovery", "return_key": "recovery", "units": "%"},
]
```

### Key Matching

By default, keys are matched exactly. You can relax matching:

- `exact_keys=False` — allow partial/fuzzy matching
- `match_accuracy` — threshold for fuzzy match quality (0–1)
- `num_keys` — expected number of matches per key

## Inspecting File Contents

```python
# View all directories found in the file
importer.get_file_directories()

# View contents of each directory
importer.get_directory_contents()

# Display loaded data
importer.display_loaded_contents()
```

## Handling Import Errors

If a registered key is not found, the importer provides the closest matches:

```python
# This key has a typo
dm.register_data_key("fs.costing.reDer_osmosis.membrane_cost", "membrane cost")
dm.load_data()  # Raises error with suggestions
```

Output:
```
WARNING: return_key='membrane cost' (filekey='fs.costing.reDer_osmosis.membrane_cost') was not imported.
WARNING:   Nearest available keys in file:
WARNING:     fs.costing.reverse_osmosis.membrane_cost
WARNING:     fs.costing.reverse_osmosis.factor_membrane_replacement
```

Use `raise_error=False` to warn instead of raising:

```python
dm.load_data(raise_error=False)
```

## Working with Multiple Files

`PsDataManager` accepts a list of files:

```python
dm = PsDataManager(["sweep_run1.h5", "sweep_run2.h5"])
```

Each file's directories are discovered and merged. Unique directory labels are assigned automatically.
