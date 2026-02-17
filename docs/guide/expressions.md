# Expressions

psPlotKit provides an expression tree API for deriving new data from imported keys using Python arithmetic operators.

## Overview

Instead of writing expression strings, you build expression trees with the `ExpressionNode` / `ExpressionKeys` API. Expressions are registered on the `PsDataManager` and evaluated automatically when `load_data()` is called.

## Building Expressions

### Step 1: Get Expression Keys

```python
from psPlotKit.data_manager.ps_data_manager import PsDataManager

dm = PsDataManager("my_sweep_results.h5")
dm.register_data_key("fs.costing.LCOW", "LCOW")
dm.register_data_key("fs.water_recovery", "recovery")

# Get an ExpressionKeys helper
ek = dm.get_expression_keys()
```

`ExpressionKeys` exposes every registered `return_key` as an attribute. Attribute access returns an `ExpressionNode` leaf.

### Step 2: Build Expression Trees

Combine nodes with standard arithmetic operators:

```python
# Simple ratio
expr = ek.LCOW / ek.recovery

# Complex expression with constants, power, grouping
expr = 100 * (ek.LCOW + ek.LCOW) ** 2 / ek.recovery
```

### Step 3: Register the Expression

```python
dm.register_expression(
    ek.LCOW / ek.recovery,
    return_key="cost_per_recovery",
)

# Optionally assign units to the result
dm.register_expression(
    ek.LCOW * ek.recovery,
    return_key="weighted_metric",
    assign_units="USD",
)
```

### Step 4: Load Data

```python
dm.load_data()
# Expression results are now available like any other key
dm.display()
```

## Supported Operators

| Operator | Example | Description |
|----------|---------|-------------|
| `+` | `ek.a + ek.b` | Addition |
| `-` | `ek.a - ek.b` | Subtraction |
| `*` | `ek.a * ek.b` | Multiplication |
| `/` | `ek.a / ek.b` | Division |
| `**` | `ek.a ** 2` | Power |
| `-` (unary) | `-ek.a` | Negation |

All operators work with:

- Two `ExpressionNode` objects
- An `ExpressionNode` and a numeric constant (either side)

## How It Works

Under the hood:

1. `ExpressionKeys.__getattr__` returns an `ExpressionNode` leaf referencing a data key
2. Arithmetic operators create new `ExpressionNode` internal nodes with `left`, `right`, and `op`
3. `ExpressionNode.required_keys` traverses the tree to find all referenced data keys
4. `ExpressionNode.evaluate(data_dict)` recursively evaluates the tree using `PsData` arithmetic (which handles unit propagation via the `quantities` library)

## Direct PsData Arithmetic

You can also perform arithmetic directly on `PsData` objects:

```python
dir_key = dm.directory_keys[0]
lcow = dm.get_data(dir_key, "LCOW")
recovery = dm.get_data(dir_key, "recovery")

# All standard operators work
ratio = lcow / recovery
double = lcow + lcow
scaled = lcow * 100
inverted = 1.0 / recovery
squared = lcow ** 2
negative = -lcow

# Results carry descriptive keys
print(ratio.data_key)  # "(LCOW / recovery)"
```
