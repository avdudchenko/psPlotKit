# Costing

`PsCosting` computes CAPEX/OPEX breakdowns and levelized costs from costing blocks in simulation data.

## Overview

The costing tool works with `PsDataManager` to:

1. Import costing block data from HDF5 files
2. Group devices into user-defined categories
3. Compute CAPEX, OPEX, and energy costs per group
4. Calculate levelized costs (e.g., LCOW — Levelized Cost of Water)

## Defining Device Groups

Device groups map logical names to simulation unit names:

```python
device_groups = {
    "RO": {"units": "ROUnits"},
    "Pumps": {
        "CAPEX": {
            "units": {"PrimaryPumps", "BoosterPumps", "EnergyRecoveryDevices"}
        },
        "OPEX": {
            "units": {"PrimaryPumps", "BoosterPumps", "EnergyRecoveryDevices"}
        },
    },
}
```

### Group Structure

- **Simple groups**: `{"units": "UnitName"}` — same units for CAPEX and OPEX
- **Split groups**: Separate `"CAPEX"` and `"OPEX"` sub-dicts with different unit sets

## Using PsCosting via PsDataManager

The simplest way is through `PsDataManager.get_costing()`:

```python
from psPlotKit.data_manager.ps_data_manager import PsDataManager

dm = PsDataManager("my_results.h5")
dm.load_data([
    {"filekey": "fs.water_recovery", "return_key": "Water recovery", "units": "%"},
])

dm.get_costing(device_groups)
```

### `get_costing` Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `costing_groups` | — | Device group definitions (see above) |
| `costing_block` | `"fs.costing"` | Root costing block in simulation |
| `costing_key` | `"costing"` | Sub-key for costing data |
| `default_flow` | `"fs.product.properties[0.0].flow_vol_phase[Liq]"` | Flow variable for levelized cost |
| `work_keys` | `["control_volume.work[0.0]"]` | Energy consumption keys |
| `include_indirect_in_device_costs` | `True` | Include indirect costs in device totals |

## Plotting Cost Breakdowns

After computing costing, use `BreakDownPlotter`:

```python
from psPlotKit.data_plotter.ps_break_down_plotter import BreakDownPlotter

dm.reduce_data(
    stack_keys="number_of_stages",
    data_key="LCOW",
    reduction_type="min",
)
dm.select_data(["stacked_data"], True)
selected = dm.get_selected_data()

plotter = BreakDownPlotter(selected)
plotter.define_area_groups({"RO": {}, "Pumps": {}})
plotter.define_hatch_groups({"CAPEX": {}, "OPEX": {"hatch": "//"}})
plotter.plotbreakdown(
    xdata="Water recovery",
    ydata=["cost_breakdown", "levelized"],
    axis_options={"yticks": [0, 0.5, 1.0, 1.5, 2.0]},
)
```
