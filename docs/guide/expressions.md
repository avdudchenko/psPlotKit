# Expressions

psPlotKit provides an expression tree API for deriving new data from imported keys using Python arithmetic operators.

## Overview

Instead of writing expression strings, you build expression trees with the
`ExpressionNode` / `ExpressionKeys` API.  Expressions are registered on the
`PsDataManager` and can be evaluated:

- **Automatically** when `load_data()` finishes, or
- **Automatically** at registration time when data is already present
  (`auto_evaluate_expressions = True`, the default), or
- **Manually** by calling `evaluate_expressions()` when you need full control
  over timing.

## Quick Example

```python
from psPlotKit.data_manager.ps_data_manager import PsDataManager

dm = PsDataManager("my_sweep_results.h5")
dm.register_data_key("fs.costing.LCOW", "LCOW")
dm.register_data_key("fs.water_recovery", "recovery")

ek = dm.get_expression_keys()
dm.register_expression(ek.LCOW / ek.recovery, return_key="cost_per_recovery")

dm.load_data()
# "cost_per_recovery" is now available in every directory
```

---

## Building Expressions Step-by-Step

### 1. Obtain ExpressionKeys

```python
ek = dm.get_expression_keys()
```

`get_expression_keys()` returns a **live reference** — any keys you add later
via `add_data()` or `register_data_key()` are automatically visible on the
same `ek` object.  You never need to call `get_expression_keys()` a second
time.

```python
ek = dm.get_expression_keys()

dm.register_data_key("fs.pressure", "pressure")
# ek.pressure is already accessible — no need to re-fetch ek
dm.register_expression(ek.pressure * 0.001, return_key="pressure_kPa")
```

### 2. Access Keys

There are three ways to reference a key on the `ExpressionKeys` object:

#### Attribute access (simple string keys)

```python
ek.LCOW        # returns an ExpressionNode for "LCOW"
ek.recovery    # returns an ExpressionNode for "recovery"
```

#### Attribute access (sanitised names)

Keys that contain special characters or are tuples are automatically
converted into valid Python identifiers:

| Original key | Safe attribute | Rule |
|---|---|---|
| `"LCOW (m**3)"` | `ek.LCOW_m_3` | Non-alphanumeric chars → `_` |
| `"Ca_2+"` | `ek.Ca_2` | Trailing `+` stripped |
| `("group", "a")` | `ek.group_a` | Tuple parts joined with `_` |

Use `ek.print_mapping()` to log the full mapping of original keys to safe
attribute names.

#### Item access (original key)

Item access always works with the **original** key — no sanitisation needed:

```python
ek["Ca_2+"]             # string key with special characters
ek["LCOW (m**3)"]       # string key with parentheses
ek["group", "a"]        # tuple key (Python auto-packs the tuple)
```

!!! tip
    When a key has special characters, **item access** is the safest and
    most readable approach.

### 3. Combine with Arithmetic Operators

Standard Python operators produce a new `ExpressionNode` tree:

```python
ratio     = ek.LCOW / ek.recovery
scaled    = 100 * (ek.LCOW + ek.LCOW) ** 2 / ek.recovery
negated   = -ek.LCOW
with_const = ek.recovery + 0.05
```

### 4. Register the Expression

```python
dm.register_expression(
    ek.LCOW / ek.recovery,
    return_key="cost_per_recovery",
)

# Optionally set units on the result
dm.register_expression(
    ek.LCOW * ek.recovery,
    return_key="weighted_metric",
    assign_units="USD",
)

# Or convert the result to specific units
dm.register_expression(
    ek.LCOW * 1000,
    return_key="LCOW_per_kgal",
    units="USD/kgal",
)
```

### 5. Evaluate

See [Evaluation Timing](#evaluation-timing) below for full details.

---

## Evaluation Timing

### Automatic on `load_data()` (default workflow)

When you register expressions **before** calling `load_data()`, they are
evaluated automatically at the end of the load:

```python
dm.register_data_key("fs.costing.LCOW", "LCOW")
ek = dm.get_expression_keys()
dm.register_expression(ek.LCOW * 100, return_key="scaled_LCOW")

dm.load_data()       # evaluates all registered expressions
dm.get_data(dir_key, "scaled_LCOW")  # ready to use
```

### Automatic on `register_expression()` (when data exists)

If data has already been loaded into the manager, calling
`register_expression()` immediately evaluates **all** pending expressions so
the result is available right away:

```python
dm.load_data()

ek = dm.get_expression_keys()
dm.register_expression(ek.LCOW / ek.recovery, return_key="ratio")
# "ratio" is available immediately — no extra call needed
```

This behaviour is controlled by the `auto_evaluate_expressions` flag
(default `True`).

### Manual evaluation

Set `auto_evaluate_expressions = False` to take full control:

```python
dm.auto_evaluate_expressions = False

ek = dm.get_expression_keys()
dm.register_expression(ek.LCOW + ek.recovery, return_key="sum_lr")
dm.register_expression(ek.LCOW - ek.recovery, return_key="diff_lr")

dm.load_data(evaluate_expressions=False)  # skip auto-eval in load_data too

# ... do other work ...

dm.evaluate_expressions()   # evaluate when you are ready
```

---

## Key Name Sanitisation

### How it works

`ExpressionKeys` converts every registered key into a valid Python
identifier so it can be used as an attribute name.  The rules are:

1. Tuple keys are joined into a single string with `_` separators.
2. Characters that are not alphanumeric or `_` are replaced with `_`.
3. Consecutive underscores are collapsed; leading/trailing underscores are
   stripped.
4. If the result starts with a digit, a leading `_` is added.

### Collision handling

When two different keys produce the same safe name (e.g. `"Ca_2+"` and
`"Ca_2"` both collapse to `Ca_2`), numeric suffixes `_1`, `_2`, … are
appended to **both** names to keep them unique.

### Inspecting the mapping

```python
ek = dm.get_expression_keys()
ek.print_mapping()
```

This logs one line per key at INFO level:

```
ExpressionKeys mapping (3 keys):
  'Ca_2' -> .Ca_2_1
  'Ca_2+' -> .Ca_2_2  (or ek['Ca_2+'])
  'LCOW' -> .LCOW
```

You can also enable a per-key warning at creation time:

```python
ek = dm.get_expression_keys(warn_on_sanitize=True)
```

### Iteration

`ExpressionKeys` is iterable and exposes `len()`:

```python
for key in ek:
    print(key)          # prints the original (unsanitised) key

len(ek)                 # number of registered keys
```

---

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
- An `ExpressionNode` and a numeric constant (either order)

---

## Working with Tuple Keys

Tuple return-keys are common when data is grouped by parameter:

```python
dm.add_data("dir_a", ("membrane", "cost"), cost_data)
dm.add_data("dir_a", ("membrane", "area"), area_data)

ek = dm.get_expression_keys()

# Attribute access — tuple parts joined with _
total = ek.membrane_cost * ek.membrane_area

# Or item access with the original tuple
total = ek["membrane", "cost"] * ek["membrane", "area"]

dm.register_expression(total, return_key="total_membrane_cost")
```

---

## Working with Special-Character Keys

```python
dm.add_data("dir_a", "Ca_2+", ca_data)
dm.add_data("dir_a", "SO4_2-", so4_data)

ek = dm.get_expression_keys()
ek.print_mapping()       # check the safe attribute names

# Item access is simplest for these keys
ratio = ek["Ca_2+"] / ek["SO4_2-"]
dm.register_expression(ratio, return_key="ca_so4_ratio")
```

---

## How It Works Under the Hood

1. **`ExpressionKeys.__getattr__`** / **`__getitem__`** returns an
   `ExpressionNode` leaf referencing a data key (preserving the original key).
2. Arithmetic operators create new `ExpressionNode` internal nodes storing
   `op`, `left`, and `right`.
3. **`ExpressionNode.required_keys`** traverses the tree to collect all
   referenced data keys.
4. **`PsDataManager.evaluate_expressions()`** iterates over every directory,
   builds a `{key → PsData}` dict for the required keys, and calls
   **`ExpressionNode.evaluate(data_dict)`** which recursively evaluates the
   tree using `PsData.data_with_units` (unit propagation is handled by the
   `quantities` library).
5. The result is wrapped in a new `PsData` and stored under the expression's
   `return_key`.

---

## Direct PsData Arithmetic

You can also perform arithmetic directly on `PsData` objects outside the
expression system:

```python
dir_key = dm.directory_keys[0]
lcow = dm.get_data(dir_key, "LCOW")
recovery = dm.get_data(dir_key, "recovery")

ratio = lcow / recovery
double = lcow + lcow
scaled = lcow * 100
inverted = 1.0 / recovery
squared = lcow ** 2
negative = -lcow

# Results carry descriptive keys
print(ratio.data_key)  # "(LCOW / recovery)"
```
