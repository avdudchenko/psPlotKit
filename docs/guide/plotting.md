# Plotting

psPlotKit provides several high-level plotters and a low-level `FigureGenerator` for creating publication-quality matplotlib figures.

## Plot Types

| Plotter | Class | Use Case |
|---------|-------|----------|
| Line plots | `linePlotter` | X-Y curves, parameter sweeps |
| Box plots | `boxPlotter` | Distribution comparisons |
| Breakdown plots | `BreakDownPlotter` | Stacked cost breakdowns (CAPEX/OPEX) |
| Map/contour plots | `MapPlotter` | 2D heatmaps, contour plots |
| Low-level | `FigureGenerator` | Direct matplotlib access |

## Using High-Level Plotters

All plotters follow the same pattern:

1. Prepare data with `PsDataManager.select_data()` + `get_selected_data()`
2. Create a plotter instance
3. Configure and plot
4. Generate the figure

### Line Plots

```python
from psPlotKit.data_plotter.ps_line_plotter import linePlotter

dm.select_data(["LCOW", "recovery"])
selected = dm.get_selected_data()

lp = linePlotter(selected, save_name="my_line_plot")
lp.plot_line(
    xdata="recovery",
    ydata="LCOW",
    axis_options={"xticks": [0, 25, 50, 75, 100]},
)
lp.generate_figure()
```

### Box Plots

```python
from psPlotKit.data_plotter.ps_box_plotter import boxPlotter

bp = boxPlotter(selected, save_name="my_box_plot")
bp.plot_tornado_plot(xdata="recovery", ydata="LCOW")
bp.generate_figure()
```

### Breakdown Plots

```python
from psPlotKit.data_plotter.ps_break_down_plotter import BreakDownPlotter

plotter = BreakDownPlotter(selected, save_name="cost_breakdown")
plotter.define_area_groups({"RO": {}, "Pumps": {}})
plotter.define_hatch_groups({"CAPEX": {}, "OPEX": {"hatch": "//"}})
plotter.plotbreakdown(
    xdata="Water recovery",
    ydata=["cost_breakdown", "levelized"],
)
plotter.generate_figure()
```

### Map / Contour Plots

```python
from psPlotKit.data_plotter.ps_map_plotter import MapPlotter

mp = MapPlotter(selected, save_name="my_map")
mp.plot_map(
    data_dir=dir_key,
    xdata="param_a",
    ydata="param_b",
    zdata="LCOW",
)
mp.generate_figure()
```

## Using FigureGenerator Directly

For full control, use `FigureGenerator`:

```python
from psPlotKit.data_plotter.fig_generator import FigureGenerator

fig = FigureGenerator(font_size=10, save_data=True)
fig.init_figure(width=3.25, height=3.25)

# Line
fig.plot_line(xdata=[1, 2, 3], ydata=[4, 5, 6], label="Series A")

# Bar
fig.plot_bar(x_pos=0, x_value=10, label="Bar 1")

# Scatter with color-mapped z
fig.plot_scatter(xdata=[1, 2], ydata=[3, 4], zdata=[0.1, 0.9])

# Error bars
fig.plot_errorbar(xdata=[1, 2], ydata=[3, 4], yerr=[0.5, 0.3])

# Histogram / CDF
fig.plot_hist(data=[1, 2, 2, 3, 3, 3])
fig.plot_cdf(data=[1, 2, 2, 3, 3, 3])

# Box plot
fig.plot_box(position=1, data=[1, 2, 3, 4, 5])

# Map / heatmap
fig.plot_map(xdata=x, ydata=y, zdata=z)

# Configure axes
fig.set_axis(
    xlabel="X Label",
    ylabel="Y Label",
    xlims=[0, 10],
    ylims=[0, 10],
)

# Legend and colorbar
fig.add_legend(loc="best")
fig.add_colorbar(zlabel="Z Values")

# Save
fig.save(save_location="figs/", file_name="my_figure")
fig.show()
```

## Figure Configuration

### `init_figure` Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `width` | 3.25 | Figure width in inches |
| `height` | 3.25 | Figure height in inches |
| `dpi` | 150 | Resolution |
| `nrows` / `ncols` | 1 | Subplot grid |
| `sharex` / `sharey` | False | Share axes across subplots |
| `twinx` / `twiny` | False | Create twin axes |
| `projection` | None | e.g., `"3d"` for 3D plots |

### Color Maps

```python
fig.gen_colormap(
    num_samples=10,
    map_name="viridis",  # any matplotlib colormap
)
```

### Saving Figures

Figures are saved as both JPG and SVG by default. When `save_data=True`, plotted data is also exported to CSV:

```python
fig = FigureGenerator(save_data=True)
# ... plot ...
fig.save(save_location="figs/", file_name="my_plot")
```
