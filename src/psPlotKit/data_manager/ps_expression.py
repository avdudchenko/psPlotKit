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

import numpy as np
from psPlotKit.util.logger import define_logger

__author__ = "Alexander V. Dudchenko (SLAC)"

_logger = define_logger(__name__, "PsExpression", level="INFO")


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
            return self.key
        if self.value is not None:
            return str(self.value)
        return "({} {} {})".format(repr(self.left), self.op, repr(self.right))


class ExpressionKeys:
    """Container that exposes registered return_keys as :class:`ExpressionNode` leaves.

    Attribute access returns an ``ExpressionNode`` referencing that key,
    which can then be combined with arithmetic operators to build an
    expression tree.

    Example::

        ek = ExpressionKeys(["LCOW", "recovery"])
        expr = 100 * (ek.LCOW + ek.LCOW) ** 2 / ek.recovery
    """

    def __init__(self, key_names):
        """
        Args:
            key_names: iterable of return_key strings.
        """
        self._keys = set(key_names)

    def __getattr__(self, name):
        # Avoid infinite recursion for dunder / private lookups
        if name.startswith("_"):
            raise AttributeError(name)
        if name not in self._keys:
            raise AttributeError(
                "'{}' is not a registered return_key.  "
                "Available keys: {}".format(name, sorted(self._keys))
            )
        return ExpressionNode._key_node(name)

    def __dir__(self):
        """Enable tab-completion in interactive sessions."""
        return list(self._keys) + list(super().__dir__())

    def __repr__(self):
        return "ExpressionKeys({})".format(sorted(self._keys))
