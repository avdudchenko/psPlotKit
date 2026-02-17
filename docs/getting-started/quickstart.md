# Quick Start

This guide walks through the basic workflow: **import data → inspect → plot**.

## 1. Import Data

```python
from psPlotKit.data_manager.ps_data_manager import PsDataManager

# Point to an .h5 file produced by the PS tool or Loop tool
dm = PsDataManager("my_sweep_results.h5")

# Register the data keys you want to import
dm.register_data_key(file_key="fs.costing.LCOW", return_key="LCOW")
dm.register_data_key("fs.water_recovery", "recovery", units="%")
dm.register_data_key(
    "fs.costing.reverse_osmosis.membrane_cost",
    "membrane_cost",
    assign_units="USD/m**2",
)

# Load imports data, checks keys, and evaluates expressions
dm.load_data()
```

## 2. Inspect Loaded Data

```python
# Show all (directory, data_key) entries
dm.display()

# Show only unique data keys
dm.display_keys()

# Show only unique directory keys
dm.display_directories()
```

## 3. Access Data

Each entry in the manager is a `PsData` object wrapping a numpy array with physical units:

```python
dir_key = dm.directory_keys[0]
lcow = dm.get_data(dir_key, "LCOW")

# Raw numpy array
print(lcow.data)

# Array with units attached
print(lcow.data_with_units)

# Convert units
lcow.to_units("USD/gal")
```

## 4. Compute Derived Data

`PsData` objects support full arithmetic — results are new `PsData` objects:

```python
recovery = dm.get_data(dir_key, "recovery")

ratio = lcow / recovery
scaled = lcow * 100
result = 100 * (lcow + recovery) ** 2 / recovery

# Store back into the manager
dm.add_data(dir_key, "my_ratio", ratio)
```

Or use the expression API for deferred evaluation:

```python
ek = dm.get_expression_keys()
dm.register_expression(ek.LCOW / ek.recovery, return_key="cost_per_recovery")
dm.load_data()
```

## 5. Plot

```python
from psPlotKit.data_plotter.ps_line_plotter import linePlotter

# Select data for plotting
dm.select_data(["LCOW", "recovery"])
selected = dm.get_selected_data()

# Create and show a line plot
lp = linePlotter(selected)
lp.plot_line(xdata="recovery", ydata="LCOW")
lp.generate_figure()
```

## Next Steps

- [Data Import Guide](../guide/data-import.md) — detailed import options
- [Expressions Guide](../guide/expressions.md) — building expression trees
- [Plotting Guide](../guide/plotting.md) — all plot types
- [API Reference](../api/ps_data_manager.md) — full method signatures
