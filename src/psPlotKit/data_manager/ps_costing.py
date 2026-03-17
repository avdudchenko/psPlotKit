"""Modular costing toolkit for computing unit-level and group-level costs.

The module provides three classes that work together with
:class:`PsDataManager` and :class:`ExpressionNode`:

* :class:`PsCostingGroup` — defines a named group of process units and
  the key patterns that identify each unit's CAPEX and OPEX data.
* :class:`PsCostingPackage` — defines global costing parameters (e.g.
  ``load_factor``, ``capital_recovery_factor``) and the formulae that
  compute derived costs (e.g. ``total_capex``, ``LCOW``).
* :class:`PsCostingManager` — orchestrator that discovers data keys in
  the :class:`PsDataManager` (or its import instances), registers them,
  builds :class:`ExpressionNode` trees from the package formulae,
  evaluates them, and stores results back in the data manager.

Example
-------
::

    dm = PsDataManager("results.h5")
    dm.load_data()

    # Define costing groups
    ro_group = PsCostingGroup("RO")
    ro_group.add_unit("reverse_osmosis",
                      capex_keys=["capital_cost"],
                      fixed_opex_keys=["fixed_operating_cost"])
    pump_group = PsCostingGroup("Pumps")
    pump_group.add_unit("pump",
                        capex_keys=["capital_cost"],
                        flow_keys={"electricity": ["electricity_flow"]})

    # Define costing package
    pkg = PsCostingPackage()
    pkg.add_parameter("capital_recovery_factor")
    pkg.add_parameter("electricity_cost")
    pkg.add_parameter("product_flow",
                      file_key="fs.product.properties[0.0].flow_vol_phase[Liq]",
                      units="m**3/year")
    pkg.add_flow_cost("electricity", "electricity_cost")
    pkg.add_formula("annualized_capex",
                    lambda ek: ek.aggregate_capital_cost * ek.capital_recovery_factor)
    pkg.add_formula("LCOW",
                    lambda ek: (ek.annualized_capex
                                + ek.aggregate_fixed_operating_cost
                                + ek.aggregate_flow_cost) / ek.product_flow,
                    assign_units="USD/m**3")

    # Run costing
    cm = PsCostingManager(dm, pkg, [ro_group, pump_group])
    cm.build()
"""

import numpy as np

from psPlotKit.data_manager.ps_expression import ExpressionNode
from psPlotKit.util.logger import define_logger

__author__ = "Alexander V. Dudchenko "

_logger = define_logger(__name__, "PsCosting", level="INFO")


def _ensure_list(value):
    """Wrap a bare string (or other scalar) into a single-element list.

    Passing ``capex_keys="capital_cost"`` is a common convenience
    shorthand.  Without this helper ``list("capital_cost")`` would
    split the string into individual characters.
    """
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return list(value)


def _split_key(key):
    """Split an h5 key by dots while keeping bracketed content intact.

    Standard ``str.split(".")`` breaks keys like
    ``fs.stage[1].pump.control_volume.work[0.0]`` because the ``[0.0]``
    contains a dot.  This helper respects bracket nesting.
    """
    parts = []
    current = []
    depth = 0
    for char in key:
        if char == "[":
            depth += 1
            current.append(char)
        elif char == "]":
            depth -= 1
            current.append(char)
        elif char == "." and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(char)
    if current:
        parts.append("".join(current))
    return parts


class _GroupExpressionKeys:
    """Proxy that aliases aggregate keys to per-group equivalents.

    Wraps a real :class:`ExpressionKeys` instance.  When an attribute
    (or item) is accessed whose name appears in *alias_map*, the
    mapped key is used instead.  If the mapped value is ``None`` a
    zero-constant :class:`ExpressionNode` is returned so that formulas
    referencing a cost type the group does not have evaluate to zero
    rather than raising an error.

    All other attribute / item accesses are forwarded to the real
    ExpressionKeys transparently.
    """

    def __init__(self, real_ek, alias_map):
        object.__setattr__(self, "_real_ek", real_ek)
        object.__setattr__(self, "_alias_map", alias_map)

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        alias_map = object.__getattribute__(self, "_alias_map")
        real_ek = object.__getattribute__(self, "_real_ek")
        if name in alias_map:
            target = alias_map[name]
            if target is None:
                return ExpressionNode._const_node(0)
            return real_ek[target]
        return getattr(real_ek, name)

    def __getitem__(self, key):
        alias_map = object.__getattribute__(self, "_alias_map")
        real_ek = object.__getattribute__(self, "_real_ek")
        if key in alias_map:
            target = alias_map[key]
            if target is None:
                return ExpressionNode._const_node(0)
            return real_ek[target]
        return real_ek[key]


# ---------------------------------------------------------------------------
# PsCostingGroup
# ---------------------------------------------------------------------------


class PsCostingGroup:
    """Define a group of process units and their cost-key patterns.

    A group (e.g. ``"RO"``, ``"Pretreatment"``) contains one or more
    *units*.  Each unit specifies:

    * **CAPEX key suffixes** — found on the unit's costing block.
    * **Fixed OPEX key suffixes** — direct operating costs (e.g.
      ``fixed_operating_cost``) found on the costing block.
    * **Flow key suffixes** — physical flow quantities (e.g.
      ``electricity_flow`` in kW) on the costing block that will be
      aggregated by flow type and multiplied by a cost rate registered
      on the costing package.

    Keys can also come directly from the data manager (bypassing
    costing-block discovery) via the ``*_from_data_manager`` parameters.

    Args:
        name: Human-readable group name (used as a label in results).
        costing_block_key: The sub-block name where per-unit costing data
            lives.  Defaults to ``"costing"``.
    """

    def __init__(self, name, costing_block_key="costing"):
        self.name = name
        self.costing_block_key = costing_block_key
        self._units = {}

    def add_unit(
        self,
        unit_name,
        capex_keys=None,
        fixed_opex_keys=None,
        flow_keys=None,
        capex_from_data_manager=None,
        fixed_opex_from_data_manager=None,
        flow_from_data_manager=None,
    ):
        """Register a process unit in this group.

        Args:
            unit_name: Name of the unit model as it appears in the h5
                key hierarchy (e.g. ``"reverse_osmosis"``).
            capex_keys: List of key suffixes on the costing block that
                contribute to CAPEX (e.g. ``["capital_cost"]``).
            fixed_opex_keys: List of key suffixes on the costing block
                for fixed operating costs (e.g.
                ``["fixed_operating_cost"]``).
            flow_keys: Dict mapping a flow type name to a list of
                costing-block suffixes for physical flows that will be
                multiplied by a cost rate.  Example:
                ``{"electricity": ["electricity_flow"]}``.
            capex_from_data_manager: Dict mapping a logical name to an
                existing return_key in PsDataManager that contributes to
                this unit's CAPEX (bypasses costing-block search).
            fixed_opex_from_data_manager: Same as above but for fixed
                OPEX.
            flow_from_data_manager: Dict mapping flow type to one of:
                - a single dm_key (string or tuple),
                - a list of dm_keys,
                - a dict of ``{logical_name: dm_key}``.
        """
        _flow_keys = {}
        if flow_keys:
            for ft, suffixes in flow_keys.items():
                _flow_keys[ft] = _ensure_list(suffixes)
        _flow_from_dm = {}
        if flow_from_data_manager:
            for ft, mapping in flow_from_data_manager.items():
                if isinstance(mapping, dict):
                    _flow_from_dm[ft] = dict(mapping)
                elif isinstance(mapping, list):
                    # List of dm_keys (each may be a string or tuple)
                    _flow_from_dm[ft] = {str(k): k for k in mapping}
                else:
                    # Single dm_key (string or tuple like ("stage 1", "key"))
                    _flow_from_dm[ft] = {str(mapping): mapping}
        self._units[unit_name] = {
            "capex_keys": _ensure_list(capex_keys),
            "fixed_opex_keys": _ensure_list(fixed_opex_keys),
            "flow_keys": _flow_keys,
            "capex_from_dm": dict(capex_from_data_manager or {}),
            "fixed_opex_from_dm": dict(fixed_opex_from_data_manager or {}),
            "flow_from_dm": _flow_from_dm,
        }

    @property
    def units(self):
        """Return the registered unit definitions (read-only view)."""
        return dict(self._units)


# ---------------------------------------------------------------------------
# PsCostingPackage
# ---------------------------------------------------------------------------


class PsCostingPackage:
    """Define global costing parameters and derived-cost formulae.

    Parameters are scalar values imported from the h5 costing block
    (e.g. ``capital_recovery_factor``).  Formulae define how to combine
    group aggregates and parameters into final metrics.

    Args:
        costing_block: Dot-separated path to the global costing block
            in the h5 data (e.g. ``"fs.costing"``).
    """

    def __init__(self, costing_block="fs.costing"):
        self.costing_block = costing_block
        self._parameters = {}
        self._formulae = []
        self._flow_costs = {}  # flow_type → {"cost_parameter": name}
        self._validations = []

    def add_parameter(
        self,
        name,
        file_key=None,
        units=None,
        assign_units=None,
    ):
        """Register a global costing parameter.

        If *file_key* is omitted it defaults to
        ``"{costing_block}.{name}"``.

        Args:
            name: Return key / label for this parameter.
            file_key: Full h5 key.  Defaults to ``costing_block.name``.
            units: Units to convert the imported value to.
            assign_units: Units to assign (overriding auto-detection).
        """
        if file_key is None:
            file_key = "{}.{}".format(self.costing_block, name)
        self._parameters[name] = {
            "file_key": file_key,
            "units": units,
            "assign_units": assign_units,
        }

    def add_formula(self, return_key, builder, units=None, assign_units=None):
        """Register a derived-cost formula.

        The *builder* is a callable ``(expression_keys) → ExpressionNode``
        so that the user can freely combine parameters and group totals
        using arithmetic operators.

        Args:
            return_key: Key under which the result will be stored.
            builder: ``callable(ek) → ExpressionNode``.
            units: Units to convert the result to.
            assign_units: Units to assign to the result.
        """
        self._formulae.append(
            {
                "return_key": return_key,
                "builder": builder,
                "units": units,
                "assign_units": assign_units,
            }
        )

    def add_flow_cost(self, flow_type, cost_parameter, units=None, assign_units=None):
        """Register the cost multiplier for a flow type.

        The *cost_parameter* must be a parameter name registered via
        :meth:`add_parameter`.  During build the aggregate flow for
        *flow_type* is multiplied by this parameter to produce
        ``{flow_type}_flow_cost``.

        Args:
            flow_type: Name of the flow type (e.g. ``"electricity"``).
            cost_parameter: Parameter name giving the unit cost
                (e.g. ``"electricity_cost"`` in $/kWh).
            units: Units to convert the flow cost to after evaluation.
            assign_units: Units to assign to the flow cost result.
        """
        self._flow_costs[flow_type] = {
            "cost_parameter": cost_parameter,
            "units": units,
            "assign_units": assign_units,
        }

    @property
    def parameters(self):
        """Return the registered parameter definitions (read-only view)."""
        return dict(self._parameters)

    @property
    def formulae(self):
        """Return the registered formulae (read-only view)."""
        return list(self._formulae)

    def add_validation(
        self,
        formula_key,
        file_key=None,
        reference_key=None,
        rtol=1e-3,
        atol=0,
    ):
        """Register a validation check for a formula result.

        After the costing pipeline builds and evaluates all expressions,
        the *total* (sum across all groups) of the per-group formula
        results for *formula_key* is compared against a reference
        dataset.

        Provide either *file_key* (an h5 key to auto-register on the
        data manager) or *reference_key* (an existing return key
        already in the data manager).

        Args:
            formula_key: The formula return key to validate (must match
                a key passed to :meth:`add_formula`).
            file_key: Full h5 key for the reference data.  Will be
                auto-registered as ``("costing", "validation",
                formula_key)``.
            reference_key: Return key already registered on the data
                manager that holds the reference data.
            rtol: Relative tolerance for comparison.
            atol: Absolute tolerance for comparison.
        """
        if file_key is None and reference_key is None:
            raise ValueError(
                "add_validation requires either file_key or reference_key."
            )
        self._validations.append(
            {
                "formula_key": formula_key,
                "file_key": file_key,
                "reference_key": reference_key,
                "rtol": rtol,
                "atol": atol,
            }
        )

    @property
    def validations(self):
        """Return the registered validations (read-only view)."""
        return list(self._validations)

    @property
    def flow_costs(self):
        """Return the registered flow-cost definitions (read-only view)."""
        return dict(self._flow_costs)


# ---------------------------------------------------------------------------
# PsCostingManager
# ---------------------------------------------------------------------------


class PsCostingManager:
    """Orchestrate key discovery, registration, and cost evaluation.

    Given a :class:`PsDataManager`, a :class:`PsCostingPackage`, and one
    or more :class:`PsCostingGroup` instances, this class:

    1. Discovers matching cost keys from the data-manager's import
       instances or existing data keys.
    2. Registers those keys (and global parameters) on the data manager.
    3. Loads the data.
    4. Builds per-group expressions (``("costing", name, "capex")``,
       ``("costing", name, "fixed_opex")``).
    5. Builds flow aggregates (``("costing", "aggregate_<flow_type>_flow")``)
       and multiplies by cost parameters to produce
       ``("costing", "<flow_type>_flow_cost")`` and finally
       ``("costing", "aggregate_flow_cost")``.
    6. Builds ``("costing", "aggregate_capital_cost")`` and
       ``("costing", "aggregate_fixed_operating_cost")``.
    7. Registers and evaluates any formulae from the costing package,
       stored as ``("costing", return_key)`` for global and
       ``("costing", group_name, return_key)`` for per-group results.
    8. Parameters are stored as ``("costing", parameter_name)``.

    Args:
        data_manager: A :class:`PsDataManager` instance.
        costing_package: A :class:`PsCostingPackage` instance.
        costing_groups: A list of :class:`PsCostingGroup` instances.
    """

    def __init__(self, data_manager, costing_package, costing_groups=None):
        self.data_manager = data_manager
        self.costing_package = costing_package
        self.costing_groups = list(costing_groups or [])
        self._discovered_keys = {}  # return_key → file_key
        self._group_capex_keys = {}  # group_name → [return_keys]
        self._group_fixed_opex_keys = {}  # group_name → [return_keys]
        self._flow_type_keys = {}  # flow_type → [return_keys]
        self._group_flow_type_keys = {}  # group_name → {flow_type → [return_keys]}
        self._per_group_formula_keys = {}  # formula_return_key → [per-group rks]

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def build(self, load_data=True):
        """Run the full costing pipeline.

        1. Discover cost keys from import instances / data manager.
        2. Register parameters and discovered keys.
        3. Optionally load data.
        4. Build group aggregate expressions.
        5. Build flow aggregate and flow-cost expressions.
        6. Build and evaluate package formulae.

        Args:
            load_data: If *True* (default) call ``data_manager.load_data()``
                after key registration.  Set to *False* if data is already
                loaded.
        """
        self._discover_keys()
        self._register_parameters()
        self._register_discovered_keys()
        self._register_validation_keys()

        if load_data:
            self.data_manager.load_data(evaluate_expressions=False)

        self._build_group_expressions()
        self._build_flow_expressions()
        self._build_per_group_flow_expressions()
        self._build_formula_expressions()
        self._build_per_group_formula_expressions()
        self._build_total_formula_expressions()

        self.data_manager.evaluate_expressions()

        _logger.info(
            "Costing build complete - {} group(s), {} formula(e).".format(
                len(self.costing_groups),
                len(self.costing_package.formulae),
            )
        )

        self._validate()

    # ------------------------------------------------------------------
    # key discovery
    # ------------------------------------------------------------------

    def _get_all_available_keys(self):
        """Collect unique data keys from all import instances and from
        keys already present in the data manager."""
        keys = set()
        for inst in self.data_manager.PsDataImportInstances:
            if hasattr(inst, "unique_data_keys"):
                keys.update(inst.unique_data_keys)
        # Also include any return_keys already registered or loaded
        for k in self.data_manager.data_keys:
            if isinstance(k, str):
                keys.add(k)
        return keys

    def _discover_keys(self):
        """Search available keys for each unit's cost patterns."""
        available = self._get_all_available_keys()
        _logger.info(
            "Searching {} available keys for costing data.".format(len(available))
        )

        for group in self.costing_groups:
            capex_return_keys = []
            fixed_opex_return_keys = []
            flow_type_return_keys = {}  # flow_type → [return_keys]

            for unit_name, unit_def in group.units.items():
                # -- costing-block based CAPEX keys --
                for suffix in unit_def["capex_keys"]:
                    found = self._find_matching_keys(
                        available, unit_name, group.costing_block_key, suffix
                    )
                    for file_key in found:
                        rk = self._make_return_key(
                            group.name, unit_name, "capex", suffix, file_key
                        )
                        self._discovered_keys[rk] = file_key
                        capex_return_keys.append(rk)

                # -- costing-block based fixed OPEX keys --
                for suffix in unit_def["fixed_opex_keys"]:
                    found = self._find_matching_keys(
                        available, unit_name, group.costing_block_key, suffix
                    )
                    for file_key in found:
                        rk = self._make_return_key(
                            group.name, unit_name, "fixed_opex", suffix, file_key
                        )
                        self._discovered_keys[rk] = file_key
                        fixed_opex_return_keys.append(rk)

                # -- costing-block based flow keys --
                for flow_type, suffixes in unit_def["flow_keys"].items():
                    for suffix in suffixes:
                        found = self._find_matching_unit_keys(
                            available,
                            unit_name,
                            suffix,
                        )
                        for file_key in found:
                            rk = self._make_return_key(
                                group.name, unit_name, "flow", suffix, file_key
                            )
                            self._discovered_keys[rk] = file_key
                            flow_type_return_keys.setdefault(flow_type, []).append(rk)

                # -- data-manager-direct keys --
                for logical_name, dm_key in unit_def["capex_from_dm"].items():
                    capex_return_keys.append(dm_key)

                for logical_name, dm_key in unit_def["fixed_opex_from_dm"].items():
                    fixed_opex_return_keys.append(dm_key)

                for flow_type, dm_map in unit_def["flow_from_dm"].items():
                    for logical_name, dm_key in dm_map.items():
                        flow_type_return_keys.setdefault(flow_type, []).append(dm_key)

            self._group_capex_keys[group.name] = capex_return_keys
            self._group_fixed_opex_keys[group.name] = fixed_opex_return_keys

            # Store per-group flow keys and merge into global
            self._group_flow_type_keys[group.name] = flow_type_return_keys
            for flow_type, keys in flow_type_return_keys.items():
                self._flow_type_keys.setdefault(flow_type, []).extend(keys)

            _logger.info(
                "Group '{}': {} CAPEX, {} fixed OPEX, {} flow type(s).".format(
                    group.name,
                    len(capex_return_keys),
                    len(fixed_opex_return_keys),
                    len(flow_type_return_keys),
                )
            )

    @staticmethod
    def _find_matching_keys(available_keys, unit_name, costing_block_key, suffix):
        """Return h5 keys that match ``*unit_name*costing_block_key*suffix``.

        The match is substring-based: the key must contain
        ``unit_name``, ``costing_block_key``, and end with (or contain)
        ``suffix``, and the costing block segment must follow the unit
        segment.
        """
        matches = []
        for key in sorted(available_keys):
            parts = _split_key(key)
            # Find segments containing unit_name and costing_block_key
            unit_idx = None
            costing_idx = None
            for i, p in enumerate(parts):
                # strip array index (e.g. "pump[0.0]" → "pump")
                base = p.split("[")[0]
                if base == unit_name and unit_idx is None:
                    unit_idx = i
                if (
                    base == costing_block_key
                    and costing_idx is None
                    and unit_idx is not None
                ):
                    costing_idx = i
            if (
                unit_idx is not None
                and costing_idx is not None
                and costing_idx > unit_idx
            ):
                # Check that suffix matches exactly after the costing block
                remainder = ".".join(parts[costing_idx + 1 :])
                if remainder == suffix:
                    matches.append(key)
        return matches

    @staticmethod
    def _find_matching_unit_keys(available_keys, unit_name, suffix):
        """Return h5 keys matching ``*unit_name*suffix`` (no costing block).

        Used for flow-quantity keys (e.g. ``control_volume.work``) that
        live directly on a unit model rather than on a costing sub-block.
        Array indices on individual segments are stripped before
        comparing to *suffix*.
        """
        matches = []
        for key in sorted(available_keys):
            parts = _split_key(key)
            unit_idx = None
            for i, p in enumerate(parts):
                base = p.split("[")[0]
                if base == unit_name and unit_idx is None:
                    unit_idx = i
                    break
            if unit_idx is not None:
                remainder_parts = parts[unit_idx + 1 :]
                stripped = ".".join(p.split("[")[0] for p in remainder_parts)
                if stripped == suffix:
                    matches.append(key)
        return matches

    @staticmethod
    def _make_return_key(group_name, unit_name, cost_type, suffix, file_key):
        """Build a unique return key for a discovered cost entry.

        When the *file_key* contains array indices on or before the unit
        segment (e.g. ``stage[1].pump`` or ``ROUnits[1]``) those indices
        are included so that every instance gets a distinct name.
        Dots in *suffix* are replaced with underscores.
        """
        safe_suffix = suffix.replace(".", "_")
        parts = _split_key(file_key)
        # Find the unit segment
        unit_idx = None
        for i, p in enumerate(parts):
            base = p.split("[")[0]
            if base == unit_name:
                unit_idx = i
                break
        if unit_idx is not None:
            path_parts = parts[: unit_idx + 1]
            has_index = any("[" in p for p in path_parts)
            if has_index:
                label = ".".join(path_parts)
                label = label.replace("[", "_").replace("]", "").replace(".", "_")
                # Strip leading "fs_" prefix for cleanliness
                if label.startswith("fs_"):
                    label = label[3:]
                return "{}_{}".format(label, safe_suffix)
        return "{}_{}_{}".format(group_name, unit_name, safe_suffix)

    # ------------------------------------------------------------------
    # registration
    # ------------------------------------------------------------------

    def _register_parameters(self):
        """Register global parameters from the costing package."""
        for name, pdef in self.costing_package.parameters.items():
            rk = ("costing", name)
            self.data_manager.register_data_key(
                file_key=pdef["file_key"],
                return_key=rk,
                units=pdef["units"],
                assign_units=pdef["assign_units"],
            )
            _logger.info("Registered parameter '{}'.".format(rk))

    def _register_discovered_keys(self):
        """Register discovered cost keys on the data manager."""
        for return_key, file_key in self._discovered_keys.items():
            self.data_manager.register_data_key(
                file_key=file_key,
                return_key=return_key,
            )
            _logger.info(
                "Registered cost key '{}' -> '{}'.".format(return_key, file_key)
            )

    # ------------------------------------------------------------------
    # expression building
    # ------------------------------------------------------------------

    def _build_group_expressions(self):
        """Build per-group capex / fixed-opex and the two aggregate
        expressions ``("costing", "aggregate_capital_cost")`` and
        ``("costing", "aggregate_fixed_operating_cost")``."""
        ek = self.data_manager.get_expression_keys()

        all_capex_return_keys = []
        all_fixed_opex_return_keys = []

        for group in self.costing_groups:
            # -- per-group CAPEX --
            capex_keys = self._group_capex_keys.get(group.name, [])
            if capex_keys:
                group_capex_rk = ("costing", group.name, "capex")
                expr = self._sum_expression(ek, capex_keys)
                self.data_manager.register_expression(
                    expr,
                    return_key=group_capex_rk,
                    zero_if_missing=True,
                )
                all_capex_return_keys.append(group_capex_rk)
                _logger.info(
                    "Expression '{}' = sum of {}.".format(group_capex_rk, capex_keys)
                )

            # -- per-group fixed OPEX --
            fixed_opex_keys = self._group_fixed_opex_keys.get(group.name, [])
            if fixed_opex_keys:
                group_fixed_opex_rk = ("costing", group.name, "fixed_opex")
                expr = self._sum_expression(ek, fixed_opex_keys)
                self.data_manager.register_expression(
                    expr,
                    return_key=group_fixed_opex_rk,
                    zero_if_missing=True,
                )
                all_fixed_opex_return_keys.append(group_fixed_opex_rk)
                _logger.info(
                    "Expression '{}' = sum of {}.".format(
                        group_fixed_opex_rk, fixed_opex_keys
                    )
                )

        # Refresh ek so that the newly registered group keys are available
        ek = self.data_manager.get_expression_keys()

        # -- aggregate CAPEX across all groups --
        if all_capex_return_keys:
            agg_capex_rk = ("costing", "aggregate_capital_cost")
            self.data_manager.register_expression(
                self._sum_expression(ek, all_capex_return_keys),
                return_key=agg_capex_rk,
                zero_if_missing=True,
            )
            _logger.info(
                "Expression '{}' = sum of {}.".format(
                    agg_capex_rk, all_capex_return_keys
                )
            )

        # -- aggregate fixed operating cost --
        if all_fixed_opex_return_keys:
            agg_fop_rk = ("costing", "aggregate_fixed_operating_cost")
            self.data_manager.register_expression(
                self._sum_expression(ek, all_fixed_opex_return_keys),
                return_key=agg_fop_rk,
                zero_if_missing=True,
            )
            _logger.info(
                "Expression '{}' = sum of {}.".format(
                    agg_fop_rk, all_fixed_opex_return_keys
                )
            )

    def _build_flow_expressions(self):
        """Build flow aggregate and flow-cost expressions.

        For each registered flow type:

        * ``("costing", "aggregate_<flow_type>_flow")`` — sum of all
          discovered flow keys of that type across every group.
        * ``("costing", "<flow_type>_flow_cost")`` — aggregate flow ×
          the cost parameter registered via
          :meth:`PsCostingPackage.add_flow_cost`.

        Finally:

        * ``("costing", "aggregate_flow_cost")`` — sum of all
          individual flow-type costs.
        """
        if not self._flow_type_keys:
            return

        flow_cost_return_keys = []

        for flow_type, keys in self._flow_type_keys.items():
            if not keys:
                continue

            ek = self.data_manager.get_expression_keys()
            agg_flow_rk = ("costing", "aggregate_{}_flow".format(flow_type))
            expr = self._sum_expression(ek, keys)
            self.data_manager.register_expression(
                expr,
                return_key=agg_flow_rk,
                zero_if_missing=True,
            )
            _logger.info("Expression '{}' = sum of {}.".format(agg_flow_rk, keys))

            # Multiply by cost parameter if one was registered
            flow_cost_info = self.costing_package.flow_costs.get(flow_type)
            if flow_cost_info:
                cost_param_name = flow_cost_info["cost_parameter"]
                cost_param_rk = ("costing", cost_param_name)
                ek = self.data_manager.get_expression_keys()
                flow_cost_rk = ("costing", "{}_flow_cost".format(flow_type))
                expr = ek[agg_flow_rk] * ek[cost_param_rk]
                self.data_manager.register_expression(
                    expr,
                    return_key=flow_cost_rk,
                    units=flow_cost_info.get("units"),
                    assign_units=flow_cost_info.get("assign_units"),
                )
                flow_cost_return_keys.append(flow_cost_rk)
                _logger.info(
                    "Expression '{}' = '{}' * '{}'.".format(
                        flow_cost_rk, agg_flow_rk, cost_param_rk
                    )
                )
            else:
                _logger.warning(
                    "No cost parameter registered for flow type '{}' — "
                    "aggregate flow computed but no cost expression built.".format(
                        flow_type
                    )
                )

        if flow_cost_return_keys:
            ek = self.data_manager.get_expression_keys()
            agg_fc_rk = ("costing", "aggregate_flow_cost")
            self.data_manager.register_expression(
                self._sum_expression(ek, flow_cost_return_keys),
                return_key=agg_fc_rk,
            )
            _logger.info(
                "Expression '{}' = sum of {}.".format(agg_fc_rk, flow_cost_return_keys)
            )

    def _build_per_group_flow_expressions(self):
        """Build per-group flow aggregate and flow-cost expressions.

        For each group that has flow keys, builds:

        * ``("costing", name, "<flow_type>_flow")`` — sum of that
          group's flow keys for the given flow type.
        * ``("costing", name, "<flow_type>_flow_cost")`` — group flow
          × cost parameter.
        * ``("costing", name, "flow_cost")`` — sum of all per-group
          flow-type costs.
        """
        for group in self.costing_groups:
            group_flow_types = self._group_flow_type_keys.get(group.name, {})
            if not group_flow_types:
                continue

            group_flow_cost_rks = []
            for flow_type, keys in group_flow_types.items():
                if not keys:
                    continue

                ek = self.data_manager.get_expression_keys()
                agg_rk = ("costing", group.name, "{}_flow".format(flow_type))
                self.data_manager.register_expression(
                    self._sum_expression(ek, keys),
                    return_key=agg_rk,
                    zero_if_missing=True,
                )
                _logger.info("Expression '{}' = sum of {}.".format(agg_rk, keys))

                flow_cost_info = self.costing_package.flow_costs.get(flow_type)
                if flow_cost_info:
                    cost_param_name = flow_cost_info["cost_parameter"]
                    cost_param_rk = ("costing", cost_param_name)
                    ek = self.data_manager.get_expression_keys()
                    cost_rk = ("costing", group.name, "{}_flow_cost".format(flow_type))
                    self.data_manager.register_expression(
                        ek[agg_rk] * ek[cost_param_rk],
                        return_key=cost_rk,
                        units=flow_cost_info.get("units"),
                        assign_units=flow_cost_info.get("assign_units"),
                    )
                    group_flow_cost_rks.append(cost_rk)
                    _logger.info(
                        "Expression '{}' = '{}' * '{}'.".format(
                            cost_rk, agg_rk, cost_param_rk
                        )
                    )

            if group_flow_cost_rks:
                ek = self.data_manager.get_expression_keys()
                rk = ("costing", group.name, "flow_cost")
                self.data_manager.register_expression(
                    self._sum_expression(ek, group_flow_cost_rks),
                    return_key=rk,
                )
                _logger.info(
                    "Expression '{}' = sum of {}.".format(rk, group_flow_cost_rks)
                )

    def _build_formula_expressions(self):
        """Build and register expressions from the costing package formulae.

        A proxy wraps the expression keys so that formula lambdas can
        reference parameters and aggregates by their simple names (e.g.
        ``ek.aggregate_capital_cost``) even though the underlying keys
        are now tuples.
        """
        alias_map = self._build_global_alias_map()

        for fdef in self.costing_package.formulae:
            ek = self.data_manager.get_expression_keys()
            proxy_ek = _GroupExpressionKeys(ek, alias_map)
            rk = ("costing", fdef["return_key"])
            expr = fdef["builder"](proxy_ek)
            self.data_manager.register_expression(
                expr,
                return_key=rk,
                units=fdef["units"],
                assign_units=fdef["assign_units"],
            )
            # Alias so chained formulas reference the tuple version
            alias_map[fdef["return_key"]] = rk
            _logger.info("Registered formula '{}'.".format(rk))

    def _build_per_group_formula_expressions(self):
        """Build per-group versions of all package formulae.

        For each group, a proxy :class:`_GroupExpressionKeys` is created
        that maps aggregate names to the group's own keys:

        * ``aggregate_capital_cost`` → ``("costing", name, "capex")``
        * ``aggregate_fixed_operating_cost`` → ``("costing", name, "fixed_opex")``
        * ``aggregate_flow_cost`` → ``("costing", name, "flow_cost")``

        Each formula result is also aliased so that chained formulas
        (where formula N references result of formula N-1) resolve to
        the per-group version.  Results are stored as
        ``("costing", name, formula_return_key)``.
        """
        for group in self.costing_groups:
            # Start with parameter mappings (shared across all groups)
            alias_map = self._build_parameter_alias_map()

            # Map aggregate capex (None → zero constant for missing types)
            gcap_rk = ("costing", group.name, "capex")
            alias_map["aggregate_capital_cost"] = (
                gcap_rk if self._group_capex_keys.get(group.name) else None
            )

            # Map aggregate fixed opex
            gfop_rk = ("costing", group.name, "fixed_opex")
            alias_map["aggregate_fixed_operating_cost"] = (
                gfop_rk if self._group_fixed_opex_keys.get(group.name) else None
            )

            # Map aggregate flow cost
            gfc_rk = ("costing", group.name, "flow_cost")
            alias_map["aggregate_flow_cost"] = (
                gfc_rk if self._group_flow_type_keys.get(group.name) else None
            )

            # Map per-flow-type costs to group-level equivalents
            group_flow_types = self._group_flow_type_keys.get(group.name, {})
            for flow_type in group_flow_types:
                gft_rk = ("costing", group.name, "{}_flow_cost".format(flow_type))
                has_cost = (
                    flow_type in self.costing_package.flow_costs
                    and group_flow_types.get(flow_type)
                )
                alias_map["{}_flow_cost".format(flow_type)] = (
                    gft_rk if has_cost else None
                )
                alias_map["aggregate_flow_cost_{}".format(flow_type)] = (
                    gft_rk if has_cost else None
                )

            for fdef in self.costing_package.formulae:
                ek = self.data_manager.get_expression_keys()
                proxy_ek = _GroupExpressionKeys(ek, alias_map)
                group_rk = ("costing", group.name, fdef["return_key"])
                try:
                    expr = fdef["builder"](proxy_ek)
                except AttributeError as exc:
                    _logger.info(
                        "Skipping formula '{}' for group '{}': {}".format(
                            fdef["return_key"], group.name, exc
                        )
                    )
                    continue

                self.data_manager.register_expression(
                    expr,
                    return_key=group_rk,
                    units=fdef["units"],
                    assign_units=fdef["assign_units"],
                )
                # Alias so chained formulas reference the per-group version
                alias_map[fdef["return_key"]] = group_rk
                self._per_group_formula_keys.setdefault(fdef["return_key"], []).append(
                    group_rk
                )
                _logger.info("Registered per-group formula '{}'.".format(group_rk))

    def _build_total_formula_expressions(self):
        """Build total (sum across groups) expressions for each formula.

        For each formula, registers an expression that sums all per-group
        results using ``zero_if_missing=True`` so that groups absent from
        a directory contribute zero.  The result is stored as
        ``("costing", "total", formula_key)``.
        """
        for fdef in self.costing_package.formulae:
            group_rks = self._per_group_formula_keys.get(fdef["return_key"], [])
            if not group_rks:
                continue

            ek = self.data_manager.get_expression_keys()
            total_rk = ("costing", "total", fdef["return_key"])
            self.data_manager.register_expression(
                self._sum_expression(ek, group_rks),
                return_key=total_rk,
                zero_if_missing=True,
            )
            _logger.info("Expression '{}' = sum of {}.".format(total_rk, group_rks))

    # ------------------------------------------------------------------
    # validation
    # ------------------------------------------------------------------

    def _register_validation_keys(self):
        """Register h5 file keys for any validations that need them."""
        for vdef in self.costing_package.validations:
            if vdef["file_key"] is not None and vdef["reference_key"] is None:
                ref_rk = ("costing", "validation", vdef["formula_key"])
                self.data_manager.register_data_key(
                    file_key=vdef["file_key"],
                    return_key=ref_rk,
                )
                vdef["reference_key"] = ref_rk
                _logger.info(
                    "Registered validation reference '{}' → '{}'.".format(
                        ref_rk, vdef["file_key"]
                    )
                )

    def _validate(self):
        """Compare total formula results against reference data.

        For each registered validation, the total (sum of per-group
        results) stored at ``("costing", "total", formula_key)`` is
        compared against the reference data.  Only finite values in
        both arrays are compared.

        Logs a per-directory result (PASS/FAIL with max relative error)
        and an overall summary for each validation.

        Returns:
            True if all validations pass, False otherwise.
        """
        if not self.costing_package.validations:
            return True

        all_passed = True
        for vdef in self.costing_package.validations:
            formula_key = vdef["formula_key"]
            ref_key = vdef["reference_key"]
            total_rk = ("costing", "total", formula_key)
            rtol = vdef["rtol"]
            atol = vdef["atol"]

            formula_passed = True
            dirs_tested = 0
            for dir_key in self.data_manager.directory_keys:
                try:
                    total_data = np.asarray(
                        self.data_manager[(*dir_key, total_rk)].data
                    )
                    ref_data = np.asarray(self.data_manager[(*dir_key, ref_key)].data)
                except KeyError:
                    continue

                mask = np.isfinite(total_data) & np.isfinite(ref_data)
                if not np.any(mask):
                    continue

                dirs_tested += 1
                max_rel = np.max(
                    np.abs(
                        (total_data[mask] - ref_data[mask])
                        / np.where(ref_data[mask] != 0, ref_data[mask], 1)
                    )
                )
                dir_ok = np.allclose(
                    total_data[mask], ref_data[mask], rtol=rtol, atol=atol
                )

                if dir_ok:
                    _logger.info(
                        "Validation '{}' PASSED for directory {}: "
                        "max relative error {:.6g} (rtol={})".format(
                            formula_key, dir_key, max_rel, rtol
                        )
                    )
                else:
                    _logger.warning(
                        "Validation '{}' FAILED for directory {}: "
                        "max relative error {:.6g} exceeds rtol={}".format(
                            formula_key, dir_key, max_rel, rtol
                        )
                    )
                    formula_passed = False

            if formula_passed:
                _logger.info(
                    "Validation PASSED for '{}' across {} directory(ies) "
                    "(rtol={}).".format(formula_key, dirs_tested, rtol)
                )
            else:
                _logger.warning(
                    "Validation FAILED for '{}' (rtol={}).".format(formula_key, rtol)
                )
                all_passed = False

        return all_passed

    # ------------------------------------------------------------------
    # alias map helpers
    # ------------------------------------------------------------------

    def _build_parameter_alias_map(self):
        """Map simple parameter names to their ``("costing", name)`` keys."""
        alias_map = {}
        for name in self.costing_package.parameters:
            alias_map[name] = ("costing", name)
        return alias_map

    def _build_global_alias_map(self):
        """Build an alias map for global formula evaluation.

        Maps simple attribute names (used in formula lambdas) to the
        corresponding tuple keys stored in the data manager.
        """
        alias_map = self._build_parameter_alias_map()

        # Aggregate keys
        alias_map["aggregate_capital_cost"] = ("costing", "aggregate_capital_cost")
        alias_map["aggregate_fixed_operating_cost"] = (
            "costing",
            "aggregate_fixed_operating_cost",
        )
        alias_map["aggregate_flow_cost"] = ("costing", "aggregate_flow_cost")

        # Per-flow-type aggregates
        for flow_type in self._flow_type_keys:
            alias_map["aggregate_{}_flow".format(flow_type)] = (
                "costing",
                "aggregate_{}_flow".format(flow_type),
            )
            alias_map["{}_flow_cost".format(flow_type)] = (
                "costing",
                "{}_flow_cost".format(flow_type),
            )
            # Allow ek.aggregate_flow_cost_<flow_type> as a convenience alias
            alias_map["aggregate_flow_cost_{}".format(flow_type)] = (
                "costing",
                "{}_flow_cost".format(flow_type),
            )

        return alias_map

    @staticmethod
    def _sum_expression(ek, return_keys):
        """Build an expression that sums the given return_keys."""
        expr = None
        for rk in return_keys:
            node = ek[rk]
            if expr is None:
                expr = node
            else:
                expr = expr + node
        return expr
