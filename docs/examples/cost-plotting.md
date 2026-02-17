# Cost Breakdown Plotting

This example demonstrates how to import simulation data, compute costing breakdowns, reduce data, and plot stacked cost breakdown charts with overlaid line plots.

## Full Example

```python
from psPlotKit.data_plotter.ps_break_down_plotter import BreakDownPlotter
from psPlotKit.data_plotter.ps_line_plotter import linePlotter
from psPlotKit.data_manager.ps_data_manager import PsDataManager

# Load data from an HDF5 file
costing_data = PsDataManager("data/bgw_analysis_analysisType_bgw_analysis.h5")

# Define device groups for costing
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

# Register and load sweep parameters
costing_data.load_data([
    {
        "filekey": "fs.water_recovery",
        "return_key": "Water recovery",
        "units": "%",
    },
    {
        "filekey": "fs.disposal.properties[0.0].conc_mass_phase_comp[Liq, NaCl]",
        "return_key": "Brine salinity",
        "units": "g/L",
    },
])

# Compute costing breakdowns
costing_data.get_costing(device_groups)

# Reduce data — stack by number_of_stages, keep minimum LCOW
costing_data.reduce_data(
    stack_keys="number_of_stages",
    data_key="LCOW",
    reduction_type="min",
)

# Select the stacked data for plotting
costing_data.select_data(["stacked_data"], True)

# Plot breakdown for different x-axis variables
x_type = {
    "Water recovery": [50, 70, 80, 90],
    "Brine salinity": [60, 100, 140, 180, 220, 260, 300, 340],
}

for x, xticks in x_type.items():
    wr = costing_data.get_selected_data()

    # Create breakdown plotter
    cost_plotter = BreakDownPlotter(wr)
    cost_plotter.define_area_groups({"RO": {}, "Pumps": {}})
    cost_plotter.define_hatch_groups({"CAPEX": {}, "OPEX": {"hatch": "//"}})

    # Plot the stacked breakdown bars
    cost_plotter.plotbreakdown(
        xdata=x,
        ydata=["cost_breakdown", "levelized"],
        axis_options={
            "yticks": [0, 0.5, 1.0, 1.5, 2.0],
            "xticks": xticks,
        },
        generate_figure=False,
    )

    # Overlay a line plot showing optimal number of stages
    num_stages = costing_data[("stacked_data", "number_of_stages")].data
    x_values = costing_data[("stacked_data", x)].data
    LCOW = costing_data[("stacked_data", "LCOW")].data

    cost_plotter.fig.plot_line(
        xdata=x_values,
        ydata=LCOW,
        marker_overlay=num_stages,
        color="black",
        markersize=5,
        marker_overlay_labels=[
            "RO",
            "1 stage LSRRO",
            "2 stage LSRRO",
            "3 stage LSRRO",
            "4 stage LSRRO",
            "5 stage LSRRO",
        ],
    )

    cost_plotter.generate_figure()
```

## Key Concepts

1. **Device groups** define how simulation units map to cost categories
2. **`reduce_data`** stacks multiple directories and picks the optimal configuration (minimum LCOW)
3. **`BreakDownPlotter`** renders stacked bars with hatching to distinguish CAPEX vs OPEX
4. **`FigureGenerator.plot_line`** can overlay lines with marker overlays on existing plots
