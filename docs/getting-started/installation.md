# Installation

## Via pip (from GitHub)

```bash
pip install git+https://github.com/avdudchenko/psPlotKit.git
```

## Development Setup (Conda)

Clone the repo and create the conda environment:

```bash
git clone https://github.com/avdudchenko/psPlotKit.git
cd psPlotKit
conda env create -f psplotkit.yml
conda activate psPlotKit
```

### Update an existing dev environment

```bash
conda env update -n psPlotKit --file psplotkit.yml
```

### Install into an existing environment

```bash
conda env update -n YOUR_ENV --file psplotkit.yml
```

## Dependencies

psPlotKit requires Python 3.11+ and the following packages:

| Package | Purpose |
|---------|---------|
| `h5py` | Reading HDF5 parameter sweep files |
| `quantities` | Physical unit handling and conversion |
| `matplotlib` | Plot generation |
| `numpy` | Array operations |
| `scipy` | Interpolation and scientific computing |
| `sigfig` | Significant figure formatting |
| `pyyaml` | YAML configuration support |
