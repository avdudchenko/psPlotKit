# psPlotKit

**A Python plotting and analysis toolkit for parameter sweep and loop tool simulation data.**

psPlotKit imports hierarchical simulation results from HDF5 and JSON files (produced by WaterTAP/IDAES process simulations), manages unit conversions, computes levelized costs, and produces publication-quality matplotlib figures.

---

## Architecture

psPlotKit follows a two-layer pipeline:

```
data_manager/              →  data_plotter/
  PsDataImport                 FigureGenerator  (low-level matplotlib wrapper)
  PsData                       linePlotter, boxPlotter, BreakDownPlotter, MapPlotter
  PsDataManager (dict)         (each plotter consumes a PsDataManager)
  PsCosting
```

1. **Data Layer** — Import `.h5`/`.json` files, wrap arrays with physical units, manage composite keys, and compute derived quantities.
2. **Plot Layer** — High-level plotting classes that accept a `PsDataManager` and delegate rendering to `FigureGenerator`.

## Key Features

- **Automatic data discovery** from HDF5 parameter sweep outputs
- **Physical unit handling** via the `quantities` library with custom units (USD, PPM)
- **Arithmetic expressions** on imported data using an operator-overloaded expression tree
- **Costing breakdowns** (CAPEX/OPEX) with levelized cost computation
- **Publication-quality plots** — line, bar, box, area, map/contour, scatter, histogram, CDF
- **CSV data export** alongside every saved figure

## Quick Links

- [Installation](getting-started/installation.md)
- [Quick Start](getting-started/quickstart.md)
- [User Guide](guide/data-import.md)
- [API Reference](api/ps_data_manager.md)
- [Examples](examples/cost-plotting.md)
