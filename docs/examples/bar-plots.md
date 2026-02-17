# Simple Bar Plots

This example shows how to use `FigureGenerator` directly for basic bar charts.

## Vertical Bar Chart

```python
from psPlotKit.data_plotter.fig_generator import FigureGenerator

xdata = ["t1", "f2", "z3"]
bar_start = [-10, -25, -30]
bar_length = [20, 40, 50]

fig = FigureGenerator()
fig.init_figure()

for i, x in enumerate(xdata):
    fig.plot_bar(i, bar_length[i], bottom=bar_start[i])

fig.set_axis_ticklabels(xticklabels=xdata, yticks=[-30, 0, 30])
fig.save_fig("vertical_bars")
fig.show()
```

## Horizontal Bar Chart

Set `vertical=False` to create horizontal bars:

```python
fig_h = FigureGenerator()
fig_h.init_figure()

for i, x in enumerate(xdata):
    fig_h.plot_bar(i, bar_length[i], bottom=bar_start[i], vertical=False)

fig_h.set_axis_ticklabels(yticklabels=xdata, xticks=[-30, 0, 30])
fig_h.save_fig("horizontal_bars")
fig_h.show()
```

## Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `x_pos` | — | Position along the category axis |
| `x_value` | — | Bar height (vertical) or width (horizontal) |
| `bottom` | `None` | Starting position of the bar |
| `width` | 0.2 | Bar thickness |
| `color` | auto | Fill color (auto-cycles if not set) |
| `edgecolor` | `"black"` | Border color |
| `hatch` | `None` | Fill pattern (e.g., `"//"`, `"xx"`) |
| `label` | `None` | Legend label |
| `vertical` | `True` | Orientation |
