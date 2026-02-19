"""Expression tree for building and evaluating arithmetic on PsData keys.

Users build expressions using Python operators on :class:`ExpressionNode`
objects obtained from :class:`ExpressionKeys`.  The resulting tree is
passed to ``PsDataManager.register_expression`` and evaluated once the
data is loaded.

Example::

    dm = PsDataManager("results.h5")
    dm.register_data_key("fs.costing.LCOW", "LCOW")
    dm.register_data_key("fs.water_recovery", "recovery")

    ek = dm.get_expression_keys()
    dm.register_expression(100 * (ek.LCOW + ek.LCOW) ** 2 / ek.recovery,
                           return_key="custom_metric")
    dm.load_data()
"""

import re
import numpy as np
from collections import defaultdict
from psPlotKit.util.logger import define_logger

__author__ = "Alexander V. Dudchenko "

_logger = define_logger(__name__, "PsExpression", level="INFO")


def _sanitize_key_to_attr(key):
    """Convert any key (str or tuple) into a valid Python identifier.

    Tuple keys are joined with ``_`` before sanitisation.  Characters
    that are not alphanumeric or underscore are replaced with ``_``.
    Runs of underscores are collapsed, leading/trailing underscores
    stripped, and a leading digit is prefixed with ``_``.
    """
    if isinstance(key, (tuple, list)):
        raw = "_".join(str(part) for part in key)
    else:
        raw = str(key)
    safe = re.sub(r"[^a-zA-Z0-9_]", "_", raw)
    safe = re.sub(r"_+", "_", safe)
    safe = safe.strip("_")
    if safe and safe[0].isdigit():
        safe = "_" + safe
    if not safe:
        safe = "_key"
    return safe


class ExpressionNode:
    """A node in an arithmetic expression tree.

    Leaf nodes hold either a data-key reference (``key``) or a numeric
    constant (``value``).  Internal nodes store an ``op`` string and
    ``left`` / ``right`` children.

    All standard arithmetic operators are overloaded so that combining
    nodes (or a node with a number) produces a new tree.
    """

    # ------------------------------------------------------------------
    # construction helpers
    # ------------------------------------------------------------------

    def __init__(self, *, key=None, value=None, op=None, left=None, right=None):
        self.key = key  # str – a return_key reference (leaf)
        self.value = value  # numeric constant (leaf)
        self.op = op  # str – one of +, -, *, /, **
        self.left = left  # ExpressionNode
        self.right = right  # ExpressionNode

    @classmethod
    def _key_node(cls, key):
        """Create a leaf that references a data key."""
        return cls(key=key)

    @classmethod
    def _const_node(cls, value):
        """Create a leaf that holds a numeric constant."""
        return cls(value=value)

    @classmethod
    def _op_node(cls, op, left, right):
        """Create an internal operation node."""
        return cls(op=op, left=left, right=right)

    # ------------------------------------------------------------------
    # coerce plain numbers into constant nodes
    # ------------------------------------------------------------------

    @staticmethod
    def _as_node(other):
        if isinstance(other, ExpressionNode):
            return other
        if isinstance(other, (int, float, np.integer, np.floating)):
            return ExpressionNode._const_node(other)
        raise TypeError(
            "Cannot combine ExpressionNode with type {}".format(type(other))
        )

    # ------------------------------------------------------------------
    # operators — return new ExpressionNode trees
    # ------------------------------------------------------------------

    def __add__(self, other):
        return ExpressionNode._op_node("+", self, self._as_node(other))

    def __radd__(self, other):
        return ExpressionNode._op_node("+", self._as_node(other), self)

    def __sub__(self, other):
        return ExpressionNode._op_node("-", self, self._as_node(other))

    def __rsub__(self, other):
        return ExpressionNode._op_node("-", self._as_node(other), self)

    def __mul__(self, other):
        return ExpressionNode._op_node("*", self, self._as_node(other))

    def __rmul__(self, other):
        return ExpressionNode._op_node("*", self._as_node(other), self)

    def __truediv__(self, other):
        return ExpressionNode._op_node("/", self, self._as_node(other))

    def __rtruediv__(self, other):
        return ExpressionNode._op_node("/", self._as_node(other), self)

    def __pow__(self, other):
        return ExpressionNode._op_node("**", self, self._as_node(other))

    def __rpow__(self, other):
        return ExpressionNode._op_node("**", self._as_node(other), self)

    def __neg__(self):
        return ExpressionNode._op_node("*", self._const_node(-1), self)

    # ------------------------------------------------------------------
    # introspection
    # ------------------------------------------------------------------

    @property
    def required_keys(self):
        """Return the set of data-key names referenced by this tree."""
        keys = set()
        self._collect_keys(keys)
        return keys

    def _collect_keys(self, accum):
        if self.key is not None:
            accum.add(self.key)
        if self.left is not None:
            self.left._collect_keys(accum)
        if self.right is not None:
            self.right._collect_keys(accum)

    # ------------------------------------------------------------------
    # evaluation
    # ------------------------------------------------------------------

    def evaluate(self, data_dict):
        """Evaluate the expression tree given a mapping of key → PsData.

        Performs arithmetic on the ``data_with_units`` quantities objects
        so that unit compatibility and propagation is handled by the
        ``quantities`` library.

        Args:
            data_dict: ``{return_key: PsData}`` for every key in
                       :attr:`required_keys`.

        Returns:
            A ``quantities.Quantity`` array (or scalar) with the result.
        """
        # --- leaf: data-key reference ---
        if self.key is not None:
            return data_dict[self.key].data_with_units

        # --- leaf: numeric constant ---
        if self.value is not None:
            return self.value

        # --- internal: operation ---
        left_val = self.left.evaluate(data_dict)
        right_val = self.right.evaluate(data_dict)
        if self.op == "+":
            return left_val + right_val
        elif self.op == "-":
            return left_val - right_val
        elif self.op == "*":
            return left_val * right_val
        elif self.op == "/":
            return left_val / right_val
        elif self.op == "**":
            return left_val**right_val
        else:
            raise ValueError("Unknown operator '{}'".format(self.op))

    # ------------------------------------------------------------------
    # readable representation
    # ------------------------------------------------------------------

    def __repr__(self):
        if self.key is not None:
            return self.key if isinstance(self.key, str) else str(self.key)
        if self.value is not None:
            return str(self.value)
        return "({} {} {})".format(repr(self.left), self.op, repr(self.right))


class ExpressionKeys:
    """Container that exposes registered return_keys as :class:`ExpressionNode` leaves.

    Attribute access returns an ``ExpressionNode`` referencing that key,
    which can then be combined with arithmetic operators to build an
    expression tree.

    Keys that are tuples or contain characters invalid in Python
    identifiers are automatically sanitised into safe attribute names.
    The original key is always preserved inside the :class:`ExpressionNode`
    so that downstream look-ups (e.g. in ``PsDataManager.evaluate_expressions``)
    resolve correctly.

    Access styles::

        # simple string key
        ek = ExpressionKeys(["LCOW", "recovery"])
        ek.LCOW                      # attribute access

        # tuple key
        ek = ExpressionKeys([("kay_a", "a")])
        ek.kay_a_a                   # sanitised attribute access
        ek["kay_a", "a"]             # item access with original key

        # key with special characters
        ek = ExpressionKeys(["Ca_2+", "LCOW (m**3)"])
        ek.Ca_2_                     # sanitised — see logged warnings
        ek["Ca_2+"]                  # item access with original key
    """

    def __init__(self, key_names, warn_on_sanitize=False):
        """
        Args:
            key_names: iterable of return_key values (strings or tuples).
            warn_on_sanitize: if *True*, log an info message for every key
                whose safe attribute name differs from its original
                representation.  Defaults to *False*.
        """
        self._keys = set(key_names)

        # --- build safe-name mappings ---
        # First pass: compute base safe name for every original key
        base_names = {}
        for key in self._keys:
            base_names[key] = _sanitize_key_to_attr(key)

        # Group by base name to detect collisions
        groups = defaultdict(list)
        for key, base in base_names.items():
            groups[base].append(key)

        self._safe_to_original = {}  # safe_attr  → original key
        self._original_to_safe = {}  # original key → safe_attr

        for base, keys_in_group in groups.items():
            if len(keys_in_group) == 1:
                key = keys_in_group[0]
                self._safe_to_original[base] = key
                self._original_to_safe[key] = base
            else:
                # Collision — disambiguate with numeric suffix
                for i, key in enumerate(sorted(keys_in_group, key=lambda k: str(k)), 1):
                    safe = "{}_{}".format(base, i)
                    self._safe_to_original[safe] = key
                    self._original_to_safe[key] = safe

        # --- optionally warn about any keys whose safe name differs ---
        if warn_on_sanitize:
            for key in sorted(self._keys, key=str):
                safe = self._original_to_safe[key]
                if isinstance(key, str) and safe == key:
                    continue
                _logger.info(
                    "Key {} is accessible as attribute '{}'".format(repr(key), safe)
                )

    # ------------------------------------------------------------------
    # attribute access  (ek.LCOW, ek.kay_a_a)
    # ------------------------------------------------------------------

    def __getattr__(self, name):
        # Avoid infinite recursion for dunder / private lookups
        if name.startswith("_"):
            raise AttributeError(name)
        if name in self._safe_to_original:
            return ExpressionNode._key_node(self._safe_to_original[name])
        raise AttributeError(
            "'{}' is not a registered return_key.  "
            "Available attributes: {}".format(name, sorted(self._safe_to_original))
        )

    # ------------------------------------------------------------------
    # item access  (ek["Ca_2+"], ek["kay_a", "a"])
    # ------------------------------------------------------------------

    def __getitem__(self, key):
        """Look up by original key (string or tuple).

        Usage::

            ek["Ca_2+"]       # string key with special chars
            ek["kay_a", "a"]  # tuple key  (Python auto-packs the tuple)
        """
        if key not in self._keys:
            raise KeyError(
                "{!r} is not a registered return_key.  "
                "Available keys: {}".format(key, sorted(self._keys, key=str))
            )
        return ExpressionNode._key_node(key)

    # ------------------------------------------------------------------
    # iteration / length
    # ------------------------------------------------------------------

    def __iter__(self):
        """Iterate over the stored (original) key names."""
        return iter(self._keys)

    def __len__(self):
        """Return the number of stored key names."""
        return len(self._keys)

    # ------------------------------------------------------------------
    # mapping display
    # ------------------------------------------------------------------

    def print_mapping(self):
        """Log the mapping of original keys to safe attribute names.

        Uses the psPlotKit logger at INFO level.
        """
        _logger.info("ExpressionKeys mapping ({} keys):".format(len(self._keys)))
        for key in sorted(self._keys, key=str):
            safe = self._original_to_safe[key]
            if isinstance(key, str) and safe == key:
                _logger.info("  {} -> .{}".format(repr(key), safe))
            else:
                _logger.info(
                    "  {} -> .{}  (or ek[{}])".format(repr(key), safe, repr(key))
                )

    # ------------------------------------------------------------------
    # introspection
    # ------------------------------------------------------------------

    def __dir__(self):
        """Enable tab-completion with safe attribute names."""
        return sorted(self._safe_to_original) + list(super().__dir__())

    def __repr__(self):
        return "ExpressionKeys({})".format(sorted(self._keys, key=str))
