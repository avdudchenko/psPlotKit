import pytest
import os
import numpy as np
from psPlotKit.data_manager.ps_data_manager import PsDataManager
from psPlotKit.data_manager.ps_data import PsData
from psPlotKit.data_manager.ps_expression import ExpressionNode, ExpressionKeys

__author__ = "Alexander V. Dudchenko "

_this_file_path = os.path.dirname(os.path.abspath(__file__))
_test_file = os.path.join(_this_file_path, "multi_dir_test.h5")

_test_single_file = os.path.join(_this_file_path, "single_dir_test.h5")


# ---------- fixtures ----------


@pytest.fixture
def data_manager():
    """PsDataManager pointed at the shared test h5 file."""
    return PsDataManager(_test_file)


@pytest.fixture
def data_manager_single_dir():
    """PsDataManager pointed at the shared test h5 file."""
    return PsDataManager(_test_single_file)


@pytest.fixture
def loaded_data_manager(data_manager):
    """PsDataManager with LCOW already registered, loaded, and verified."""
    data_manager.register_data_key("LCOW", "LCOW")
    data_manager.load_data()
    return data_manager


class TestSingleDirDataImport:
    def test_load_data(self, data_manager_single_dir):
        """Test that loading a file with only one directory works and marks keys."""
        data_manager_single_dir.register_data_key("output_c", "LCOW")
        data_manager_single_dir.register_data_key("output_c", "LCOW2")
        ek = data_manager_single_dir.get_expression_keys()
        data_manager_single_dir.register_expression(
            ek.LCOW + ek.LCOW2, return_key="LCOW_sum"
        )
        data_manager_single_dir.load_data()
        data_manager_single_dir.display()
        assert "LCOW" in data_manager_single_dir
        assert "LCOW2" in data_manager_single_dir
        assert "LCOW_sum" in data_manager_single_dir
        assert (
            data_manager_single_dir._registered_key_import_status["LCOW"]["imported"]
            is True
        )


# ---------- register_data_key tracking ----------


class TestRegisterDataKey:
    def test_register_populates_status_dict(self, data_manager):
        """Registering a key should create an entry in _registered_key_import_status
        with imported=False and the correct file_key."""
        data_manager.register_data_key("LCOW", "LCOW_return")
        assert "LCOW_return" in data_manager._registered_key_import_status
        entry = data_manager._registered_key_import_status["LCOW_return"]
        assert entry["file_key"] == "LCOW"
        assert entry["imported"] is False

    def test_register_multiple_keys(self, data_manager):
        """Each registered key gets its own tracking entry."""
        data_manager.register_data_key("LCOW", "LCOW")
        data_manager.register_data_key(
            "fs.costing.reverse_osmosis.membrane_cost", "membrane_cost"
        )

        assert len(data_manager._registered_key_import_status) == 2
        assert "LCOW" in data_manager._registered_key_import_status
        assert "membrane_cost" in data_manager._registered_key_import_status
        for entry in data_manager._registered_key_import_status.values():
            assert entry["imported"] is False


# ---------- _mark_key_imported ----------


class TestMarkKeyImported:
    def test_mark_string_key(self, data_manager):
        """A simple string key matching a registered return_key is marked imported."""
        data_manager.register_data_key("LCOW", "LCOW")
        data_manager._mark_key_imported("LCOW")

        assert data_manager._registered_key_import_status["LCOW"]["imported"] is True

    def test_mark_tuple_key(self, data_manager):
        """When __key is a tuple, any string element matching a return_key is marked."""
        data_manager.register_data_key("LCOW", "LCOW")
        data_manager._mark_key_imported(("cost_breakdown", "LCOW"))

        assert data_manager._registered_key_import_status["LCOW"]["imported"] is True

    def test_mark_list_key(self, data_manager):
        """When __key is a list, matching string elements are marked."""
        data_manager.register_data_key("LCOW", "LCOW")
        data_manager._mark_key_imported(["some_prefix", "LCOW"])

        assert data_manager._registered_key_import_status["LCOW"]["imported"] is True

    def test_unrelated_key_not_marked(self, data_manager):
        """Keys that don't match any registered return_key stay not-imported."""
        data_manager.register_data_key("LCOW", "LCOW")
        data_manager._mark_key_imported("unrelated_key")

        assert data_manager._registered_key_import_status["LCOW"]["imported"] is False

    def test_mark_non_string_key_is_noop(self, data_manager):
        """Non-string, non-sequence keys should not raise errors."""
        data_manager.register_data_key("LCOW", "LCOW")
        data_manager._mark_key_imported(12345)

        assert data_manager._registered_key_import_status["LCOW"]["imported"] is False


# ---------- add_data integration ----------


class TestAddDataMarksImported:
    def test_add_data_marks_registered_key(self, data_manager):
        """Calling add_data with a key that matches a registered return_key
        should flip imported to True."""
        data_manager.register_data_key("LCOW", "LCOW")
        ps = PsData("LCOW", "test", [1.0, 2.0])
        data_manager.add_data("test_dir", "LCOW", ps)

        assert data_manager._registered_key_import_status["LCOW"]["imported"] is True

    def test_add_data_with_tuple_key_marks_registered(self, data_manager):
        """add_data with a tuple key containing the return_key marks it imported."""
        data_manager.register_data_key("LCOW", "LCOW")
        ps = PsData("LCOW", "test", [1.0, 2.0])
        data_manager.add_data("test_dir", ("cost_breakdown", "LCOW"), ps)

        assert data_manager._registered_key_import_status["LCOW"]["imported"] is True

    def test_add_data_does_not_mark_unrelated(self, data_manager):
        """add_data with an unrelated key leaves registered keys not-imported."""
        data_manager.register_data_key("LCOW", "LCOW")
        ps = PsData("other", "test", [1.0, 2.0])
        data_manager.add_data("test_dir", "other", ps)

        assert data_manager._registered_key_import_status["LCOW"]["imported"] is False


# ---------- check_import_status ----------


class TestCheckImportStatus:
    def test_all_keys_imported_no_error(self, loaded_data_manager):
        """When every registered key was imported, check_import_status
        should complete silently even with raise_error=True."""
        loaded_data_manager.check_import_status(raise_error=True)

    def test_all_keys_imported_returns_none(self, loaded_data_manager):
        """Return value should be None when all keys are imported."""
        result = loaded_data_manager.check_import_status()
        assert result is None

    def test_missing_key_logs_warning(self, loaded_data_manager, caplog):
        """A registered-but-not-imported key should produce a warning log."""
        loaded_data_manager.register_data_key("fs.nonexistent.key", "Missing Key")

        import logging

        with caplog.at_level(logging.WARNING):
            loaded_data_manager.check_import_status(raise_error=False)

        assert "Missing Key" in caplog.text
        assert "fs.nonexistent.key" in caplog.text
        assert "NOT imported" in caplog.text

    def test_missing_key_raises_error(self, loaded_data_manager):
        """With raise_error=True the method should raise KeyError for
        keys that were not imported."""
        loaded_data_manager.register_data_key("fs.nonexistent.key", "Missing Key")

        with pytest.raises(KeyError, match="Missing Key"):
            loaded_data_manager.check_import_status(raise_error=True)

    def test_missing_key_shows_nearest_suggestions(self, loaded_data_manager, caplog):
        """For a slightly misspelled key the nearest-match suggestions from
        unique_data_keys should appear in the log output."""
        loaded_data_manager.register_data_key("LCOW_typo", "LCOW typo")

        import logging

        with caplog.at_level(logging.WARNING):
            loaded_data_manager.check_import_status(raise_error=False)

        assert "Nearest available keys" in caplog.text
        assert "LCOW" in caplog.text

    def test_completely_unrelated_key_no_nearest(self, loaded_data_manager, caplog):
        """A key with no resemblance to anything available should produce
        a 'No similar keys found' message."""
        loaded_data_manager.register_data_key(
            "zzzzzzzzzz_nothing_like_this", "Garbage Key"
        )

        import logging

        with caplog.at_level(logging.WARNING):
            loaded_data_manager.check_import_status(raise_error=False)

        assert "Garbage Key" in caplog.text
        assert "NOT imported" in caplog.text

    def test_mixed_imported_and_missing(self, loaded_data_manager, caplog):
        """Only the keys that were NOT imported should be reported."""
        loaded_data_manager.register_data_key("fs.nonexistent.key", "Missing Key")

        import logging

        with caplog.at_level(logging.WARNING):
            loaded_data_manager.check_import_status(raise_error=False)

        # LCOW was imported successfully — it should NOT be in the warnings
        warning_records = [r for r in caplog.records if r.levelno >= logging.WARNING]
        warning_text = " ".join(r.message for r in warning_records)
        assert "Missing Key" in warning_text
        # LCOW should only appear if it shows up as a nearest-match suggestion,
        # not as a missing key
        assert "return_key='LCOW'" not in warning_text

    def test_raise_error_lists_all_missing_keys(self, loaded_data_manager):
        """The KeyError message should contain every missing return_key."""
        loaded_data_manager.register_data_key("fs.fake.one", "Fake One")
        loaded_data_manager.register_data_key("fs.fake.two", "Fake Two")

        with pytest.raises(KeyError) as exc_info:
            loaded_data_manager.check_import_status(raise_error=True)

        error_msg = str(exc_info.value)
        assert "Fake One" in error_msg
        assert "Fake Two" in error_msg


# ---------- end-to-end with load_data ----------


class TestEndToEnd:
    def test_register_load_check_all_found(self, data_manager):
        """Full workflow: register → load → check, all keys present.
        load_data now auto-calls check_import_status(raise_error=True)."""
        data_manager.register_data_key("LCOW", "LCOW")
        data_manager.register_data_key(
            "fs.costing.reverse_osmosis.membrane_cost", "membrane_cost"
        )
        data_manager.load_data()

        data_manager.display()
        # both should be marked imported
        for key in ["LCOW", "membrane_cost"]:
            assert (
                data_manager._registered_key_import_status[key]["imported"] is True
            ), f"{key} should be marked imported"

    def test_register_load_check_partial_missing(self, data_manager):
        """Register a mix of real and fake keys, load with raise_error=True
        should raise KeyError for the missing key."""
        data_manager.register_data_key("LCOW", "LCOW")
        data_manager.register_data_key(
            "fs.costing.reDer_osmosis.membrane_cost", "Bogus"
        )

        with pytest.raises(KeyError, match="Bogus"):
            data_manager.load_data()

    def test_register_load_check_partial_missing_no_raise(self, data_manager):
        """Register a mix of real and fake keys, load with raise_error=False
        should allow inspection of import status."""
        data_manager.register_data_key("LCOW", "LCOW")
        data_manager.register_data_key(
            "fs.costing.reDer_osmosis.membrane_cost", "Bogus"
        )
        data_manager.load_data(raise_error=False)

        assert data_manager._registered_key_import_status["LCOW"]["imported"] is True
        assert data_manager._registered_key_import_status["Bogus"]["imported"] is False

    def test_loaded_data_is_correct(self, data_manager):
        """Verify that the data imported through register + load is
        numerically correct for a known key."""
        data_manager.register_data_key("LCOW", "LCOW")
        data_manager.load_data()

        # LCOW should exist in multiple directories — just verify we got data
        lcow_keys = [k for k in data_manager.keys() if "LCOW" in str(k)]
        assert len(lcow_keys) > 0, "Expected at least one LCOW entry"

        for k in lcow_keys:
            ps_data = data_manager[k]
            assert isinstance(ps_data, PsData)
            assert len(ps_data.data) > 0
            assert np.all(np.isfinite(ps_data.data))


# ---------- register_expression / evaluate_expressions ----------


class TestRegisterExpression:
    def test_register_stores_expression(self, data_manager):
        """register_expression should append to _registered_expressions."""
        data_manager.register_data_key("LCOW", "a")
        data_manager.register_data_key("LCOW", "b")
        ek = data_manager.get_expression_keys()
        data_manager.register_expression(ek.a + ek.b, return_key="sum_ab")

        assert len(data_manager._registered_expressions) == 1
        entry = data_manager._registered_expressions[0]
        assert isinstance(entry["expression"], ExpressionNode)
        assert entry["return_key"] == "sum_ab"

    def test_register_multiple_expressions(self, data_manager):
        """Multiple registrations should all be tracked."""
        data_manager.register_data_key("LCOW", "a")
        data_manager.register_data_key("LCOW", "b")
        ek = data_manager.get_expression_keys()
        data_manager.register_expression(ek.a + ek.b, return_key="sum")
        data_manager.register_expression(ek.a * ek.b, return_key="product")
        data_manager.register_expression(ek.a / ek.b, return_key="ratio")

        assert len(data_manager._registered_expressions) == 3

    def test_register_with_units(self, data_manager):
        """units and assign_units should be stored."""
        data_manager.register_data_key("LCOW", "a")
        data_manager.register_data_key("LCOW", "b")
        ek = data_manager.get_expression_keys()
        data_manager.register_expression(
            ek.a - ek.b, return_key="diff", units="m", assign_units="km"
        )
        entry = data_manager._registered_expressions[0]
        assert entry["units"] == "m"
        assert entry["assign_units"] == "km"

    def test_string_expression_raises_type_error(self, data_manager):
        """Passing a string expression should raise a TypeError."""
        with pytest.raises(TypeError, match="String expressions are no longer"):
            data_manager.register_expression("a + b", return_key="sum_ab")

    def test_non_node_expression_raises_type_error(self, data_manager):
        """Passing something other than ExpressionNode should raise TypeError."""
        with pytest.raises(TypeError, match="ExpressionNode"):
            data_manager.register_expression(42, return_key="bad")


# ---------- ExpressionNode / ExpressionKeys ----------


class TestExpressionKeys:
    def test_getattr_returns_node(self):
        ek = ExpressionKeys(["LCOW", "recovery"])
        node = ek.LCOW
        assert isinstance(node, ExpressionNode)
        assert node.key == "LCOW"

    def test_missing_attr_raises(self):
        ek = ExpressionKeys(["LCOW"])
        with pytest.raises(AttributeError, match="not a registered"):
            _ = ek.nonexistent

    def test_get_expression_keys_from_manager(self, data_manager):
        data_manager.register_data_key("LCOW", "LCOW")
        data_manager.register_data_key("LCOW", "recovery")
        ek = data_manager.get_expression_keys()
        assert isinstance(ek, ExpressionKeys)
        assert isinstance(ek.LCOW, ExpressionNode)
        assert isinstance(ek.recovery, ExpressionNode)

    # --- tuple key support ---

    def test_tuple_key_attr_access(self):
        """Tuple key ('kay_a', 'a') should be accessible as ek.kay_a_a."""
        ek = ExpressionKeys([("kay_a", "a")])
        node = ek.kay_a_a
        assert isinstance(node, ExpressionNode)
        assert node.key == ("kay_a", "a")

    def test_tuple_key_item_access(self):
        """ek['kay_a', 'a'] should return a node with the original tuple key."""
        ek = ExpressionKeys([("kay_a", "a"), "LCOW"])
        node = ek["kay_a", "a"]
        assert isinstance(node, ExpressionNode)
        assert node.key == ("kay_a", "a")

    def test_item_access_string_key(self):
        """ek['LCOW'] should work for normal string keys."""
        ek = ExpressionKeys(["LCOW"])
        node = ek["LCOW"]
        assert node.key == "LCOW"

    def test_item_access_missing_key_raises(self):
        """ek['missing'] should raise KeyError."""
        ek = ExpressionKeys(["LCOW"])
        with pytest.raises(KeyError, match="not a registered"):
            _ = ek["missing"]

    # --- unsafe character handling ---

    def test_unsafe_chars_sanitised(self):
        """Keys with special characters get safe attribute names."""
        ek = ExpressionKeys(["LCOW (m**3)"])
        node = ek.LCOW_m_3
        assert isinstance(node, ExpressionNode)
        assert node.key == "LCOW (m**3)"

    def test_unsafe_chars_item_access(self):
        """Original key with special characters accessible via ek[key]."""
        ek = ExpressionKeys(["LCOW (m**3)"])
        node = ek["LCOW (m**3)"]
        assert node.key == "LCOW (m**3)"

    def test_collision_disambiguation(self):
        """'Ca_2+' and 'Ca_2' should get distinct safe names with suffixes."""
        ek = ExpressionKeys(["Ca_2+", "Ca_2"])
        # Both should have different safe names
        safe_ca2 = ek._original_to_safe["Ca_2"]
        safe_ca2_plus = ek._original_to_safe["Ca_2+"]
        assert safe_ca2 != safe_ca2_plus
        # Both should be accessible via attribute
        assert getattr(ek, safe_ca2).key == "Ca_2"
        assert getattr(ek, safe_ca2_plus).key == "Ca_2+"
        # And via item access
        assert ek["Ca_2"].key == "Ca_2"
        assert ek["Ca_2+"].key == "Ca_2+"

    def test_no_collision_no_suffix(self):
        """Keys that sanitise to unique names should NOT get numeric suffixes."""
        ek = ExpressionKeys(["Ca_2+", "LCOW"])
        assert ek._original_to_safe["LCOW"] == "LCOW"
        # Ca_2+ sanitises to Ca_2 which is unique in this set
        assert ek._original_to_safe["Ca_2+"] == "Ca_2"

    # --- iteration / len / dir ---

    def test_iter_returns_original_keys(self):
        """Iteration should yield original keys (including tuples)."""
        keys = [("kay_a", "a"), "LCOW", "Ca_2+"]
        ek = ExpressionKeys(keys)
        assert set(ek) == set(keys)

    def test_len(self):
        ek = ExpressionKeys(["a", "b", ("c", "d")])
        assert len(ek) == 3

    def test_dir_contains_safe_names(self):
        """dir(ek) should include the sanitised attribute names."""
        ek = ExpressionKeys(["LCOW (m**3)", ("kay_a", "a")])
        d = dir(ek)
        assert "LCOW_m_3" in d
        assert "kay_a_a" in d

    # --- arithmetic with tuple keys ---

    def test_arithmetic_with_tuple_key(self):
        """Expression tree built from tuple keys should track them in required_keys."""
        ek = ExpressionKeys([("kay_a", "a"), "LCOW"])
        expr = ek.kay_a_a + ek.LCOW
        assert ("kay_a", "a") in expr.required_keys
        assert "LCOW" in expr.required_keys

    # --- print_mapping / warn_on_sanitize ---

    def test_print_mapping(self, caplog):
        """print_mapping should log all key-to-attribute mappings."""
        import logging

        ek = ExpressionKeys(["LCOW", "Ca_2+", ("group", "a")])
        with caplog.at_level(logging.INFO):
            ek.print_mapping()
        # Should mention all three keys in the log
        assert "Ca_2+" in caplog.text
        assert "LCOW" in caplog.text
        assert "group" in caplog.text

    def test_warn_on_sanitize_false_by_default(self, caplog):
        """With default warn_on_sanitize=False, no sanitisation warnings are logged."""
        import logging

        with caplog.at_level(logging.INFO):
            ExpressionKeys(["Ca_2+", ("group", "a")])
        # Should NOT contain the "is accessible as attribute" message
        assert "is accessible as attribute" not in caplog.text

    def test_warn_on_sanitize_true_logs_warnings(self, caplog):
        """With warn_on_sanitize=True, sanitised keys should trigger info messages."""
        import logging

        with caplog.at_level(logging.INFO):
            ExpressionKeys(["Ca_2+", ("group", "a")], warn_on_sanitize=True)
        assert "is accessible as attribute" in caplog.text
        assert "Ca_2+" in caplog.text

    # --- add_key (dynamic) ---

    def test_add_key_grows_expression_keys(self):
        """add_key on ExpressionKeys should make the new key accessible."""
        ek = ExpressionKeys(["LCOW"])
        ek.add_key("recovery")
        assert len(ek) == 2
        assert ek.recovery.key == "recovery"

    def test_add_key_duplicate_is_noop(self):
        """Adding the same key twice should not change the container."""
        ek = ExpressionKeys(["LCOW"])
        ek.add_key("LCOW")
        assert len(ek) == 1

    def test_add_key_collision_disambiguates(self):
        """Adding a key that collides with an existing safe name should
        trigger numeric suffix disambiguation for both."""
        ek = ExpressionKeys(["Ca_2"])
        assert ek._original_to_safe["Ca_2"] == "Ca_2"
        ek.add_key("Ca_2+")
        # Both should now have suffixed safe names
        assert ek._original_to_safe["Ca_2"] != ek._original_to_safe["Ca_2+"]
        assert ek["Ca_2"].key == "Ca_2"
        assert ek["Ca_2+"].key == "Ca_2+"

    # --- live reference through PsDataManager ---

    def test_expression_keys_live_after_add_data(self):
        """ExpressionKeys obtained before add_data should see keys added later."""
        dm = PsDataManager()
        dm.add_data("d", "LCOW", PsData("LCOW", "t", np.array([1.0])))
        ek = dm.get_expression_keys()
        assert ek.LCOW.key == "LCOW"

        # Add new data after grabbing ek
        dm.add_data("d", "recovery", PsData("recovery", "t", np.array([0.5])))
        # ek should see the new key without re-calling get_expression_keys
        assert ek.recovery.key == "recovery"
        assert len(ek) == 2

    def test_expression_keys_live_after_register_data_key(self):
        """register_data_key after get_expression_keys should update the live ref."""
        dm = PsDataManager()
        dm.register_data_key("fs.LCOW", "LCOW")
        ek = dm.get_expression_keys()
        assert ek.LCOW.key == "LCOW"

        dm.register_data_key("fs.recovery", "recovery")
        assert ek.recovery.key == "recovery"

    def test_get_expression_keys_returns_same_object(self):
        """Multiple calls to get_expression_keys should return the same instance."""
        dm = PsDataManager()
        dm.register_data_key("fs.LCOW", "LCOW")
        ek1 = dm.get_expression_keys()
        ek2 = dm.get_expression_keys()
        assert ek1 is ek2


class TestExpressionNode:
    def test_add_builds_tree(self):
        a = ExpressionNode._key_node("a")
        b = ExpressionNode._key_node("b")
        expr = a + b
        assert expr.op == "+"
        assert expr.left.key == "a"
        assert expr.right.key == "b"

    def test_sub_builds_tree(self):
        a = ExpressionNode._key_node("a")
        b = ExpressionNode._key_node("b")
        expr = a - b
        assert expr.op == "-"

    def test_mul_builds_tree(self):
        a = ExpressionNode._key_node("a")
        b = ExpressionNode._key_node("b")
        expr = a * b
        assert expr.op == "*"

    def test_div_builds_tree(self):
        a = ExpressionNode._key_node("a")
        b = ExpressionNode._key_node("b")
        expr = a / b
        assert expr.op == "/"

    def test_pow_builds_tree(self):
        a = ExpressionNode._key_node("a")
        expr = a**2
        assert expr.op == "**"
        assert expr.right.value == 2

    def test_scalar_left_mul(self):
        a = ExpressionNode._key_node("a")
        expr = 100 * a
        assert expr.op == "*"
        assert expr.left.value == 100

    def test_scalar_right_add(self):
        a = ExpressionNode._key_node("a")
        expr = a + 5
        assert expr.op == "+"
        assert expr.right.value == 5

    def test_complex_expression(self):
        """100 * (a + b) ** 2 / c should build a valid tree."""
        a = ExpressionNode._key_node("a")
        b = ExpressionNode._key_node("b")
        c = ExpressionNode._key_node("c")
        expr = 100 * (a + b) ** 2 / c
        assert isinstance(expr, ExpressionNode)
        assert expr.required_keys == {"a", "b", "c"}

    def test_required_keys(self):
        a = ExpressionNode._key_node("a")
        b = ExpressionNode._key_node("b")
        expr = (a + b) * a
        assert expr.required_keys == {"a", "b"}

    def test_repr(self):
        a = ExpressionNode._key_node("a")
        b = ExpressionNode._key_node("b")
        expr = a + b
        assert "a" in repr(expr)
        assert "b" in repr(expr)
        assert "+" in repr(expr)

    def test_neg(self):
        a = ExpressionNode._key_node("a")
        expr = -a
        assert expr.op == "*"
        assert expr.left.value == -1


class TestEvaluateExpressions:
    def test_add_expression(self, data_manager):
        """LCOW + LCOW2 (same units) should produce a result in each directory."""
        data_manager.register_data_key("LCOW", "LCOW")
        data_manager.register_data_key("LCOW", "LCOW2")
        ek = data_manager.get_expression_keys()
        data_manager.register_expression(
            ek.LCOW + ek.LCOW2, return_key="lcow_plus_lcow2"
        )
        data_manager.load_data()

        result_keys = [k for k in data_manager.keys() if "lcow_plus_lcow2" in str(k)]
        assert len(result_keys) > 0, "Expression result should exist"

        for k in result_keys:
            result = data_manager[k]
            assert isinstance(result, PsData)
            assert result.data_key == "lcow_plus_lcow2"
            assert len(result.data) > 0

    def test_subtract_expression(self, data_manager):
        """Subtraction expression should work with compatible units."""
        data_manager.register_data_key("LCOW", "LCOW")
        data_manager.register_data_key("LCOW", "LCOW2")
        ek = data_manager.get_expression_keys()
        data_manager.register_expression(
            ek.LCOW - ek.LCOW2, return_key="lcow_minus_lcow2"
        )
        data_manager.load_data()

        result_keys = [k for k in data_manager.keys() if "lcow_minus_lcow2" in str(k)]
        assert len(result_keys) > 0

    def test_multiply_expression(self, data_manager):
        """Multiplication expression should work."""
        data_manager.register_data_key("LCOW", "LCOW")
        data_manager.register_data_key(
            "fs.costing.reverse_osmosis.membrane_cost", "membrane_cost"
        )
        ek = data_manager.get_expression_keys()
        data_manager.register_expression(
            ek.LCOW * ek.membrane_cost, return_key="lcow_times_mc"
        )
        data_manager.load_data()

        result_keys = [k for k in data_manager.keys() if "lcow_times_mc" in str(k)]
        assert len(result_keys) > 0

    def test_divide_expression(self, data_manager):
        """Division expression should work."""
        data_manager.register_data_key("LCOW", "LCOW")
        data_manager.register_data_key(
            "fs.costing.reverse_osmosis.membrane_cost", "membrane_cost"
        )
        ek = data_manager.get_expression_keys()
        data_manager.register_expression(
            ek.LCOW / ek.membrane_cost, return_key="lcow_per_mc"
        )
        data_manager.load_data()

        result_keys = [k for k in data_manager.keys() if "lcow_per_mc" in str(k)]
        assert len(result_keys) > 0

    def test_power_expression(self, data_manager):
        """Power expression with a scalar exponent should work."""
        data_manager.register_data_key("LCOW", "LCOW")
        ek = data_manager.get_expression_keys()
        data_manager.register_expression(ek.LCOW**2, return_key="lcow_squared")
        data_manager.load_data()

        result_keys = [k for k in data_manager.keys() if "lcow_squared" in str(k)]
        assert len(result_keys) > 0

        dir_key = data_manager.directory_keys[0]
        lcow = data_manager.get_data(dir_key, "LCOW")
        result = data_manager.get_data(dir_key, "lcow_squared")
        np.testing.assert_array_almost_equal(result.data, lcow.data**2)

    def test_scalar_multiply_expression(self, data_manager):
        """Scalar * key expression should work — e.g. 100 * LCOW."""
        data_manager.register_data_key("LCOW", "LCOW")
        ek = data_manager.get_expression_keys()
        data_manager.register_expression(100 * ek.LCOW, return_key="lcow_x100")
        data_manager.load_data()

        dir_key = data_manager.directory_keys[0]
        lcow = data_manager.get_data(dir_key, "LCOW")
        result = data_manager.get_data(dir_key, "lcow_x100")
        np.testing.assert_array_almost_equal(result.data, 100 * lcow.data)

    def test_complex_expression(self, data_manager):
        """100 * (LCOW + LCOW2) ** 2 should work end-to-end."""
        data_manager.register_data_key("LCOW", "LCOW")
        data_manager.register_data_key("LCOW", "LCOW2")
        ek = data_manager.get_expression_keys()
        data_manager.register_expression(
            100 * (ek.LCOW + ek.LCOW2) ** 2, return_key="complex_expr"
        )
        data_manager.load_data()

        result_keys = [k for k in data_manager.keys() if "complex_expr" in str(k)]
        assert len(result_keys) > 0

        dir_key = data_manager.directory_keys[0]
        lcow = data_manager.get_data(dir_key, "LCOW")
        lcow2 = data_manager.get_data(dir_key, "LCOW2")
        result = data_manager.get_data(dir_key, "complex_expr")
        expected = 100 * (lcow.data + lcow2.data) ** 2
        np.testing.assert_array_almost_equal(result.data, expected)

    def test_expression_numerical_correctness(self, data_manager):
        """Verify the expression result matches manual arithmetic."""
        data_manager.register_data_key("LCOW", "LCOW")
        data_manager.register_data_key("LCOW", "LCOW2")
        ek = data_manager.get_expression_keys()
        data_manager.register_expression(ek.LCOW + ek.LCOW2, return_key="manual_sum")
        data_manager.load_data()

        # Pick the first directory and verify manually
        dir_key = data_manager.directory_keys[0]
        lcow = data_manager.get_data(dir_key, "LCOW")
        lcow2 = data_manager.get_data(dir_key, "LCOW2")
        result = data_manager.get_data(dir_key, "manual_sum")

        expected = lcow.data + lcow2.data
        np.testing.assert_array_almost_equal(result.data, expected)

    def test_missing_key_warns_and_skips(self, data_manager, caplog):
        """If a key in the expression doesn't exist in a directory,
        a warning should be logged and that directory skipped."""
        data_manager.register_data_key("LCOW", "LCOW")
        ek = data_manager.get_expression_keys()
        # Manually build an expression that references a non-existent key
        nonexistent = ExpressionNode._key_node("nonexistent_key")
        data_manager.register_expression(ek.LCOW + nonexistent, return_key="bad_expr")

        import logging

        with caplog.at_level(logging.WARNING):
            data_manager.load_data()

        assert "nonexistent_key" in caplog.text
        assert (
            "skipping" in caplog.text.lower() or "could not find" in caplog.text.lower()
        )

        # Should not have produced any results
        result_keys = [k for k in data_manager.keys() if "bad_expr" in str(k)]
        assert len(result_keys) == 0

    def test_all_keys_missing_warns_no_evaluation(self, data_manager, caplog):
        """If no directory can satisfy the expression, warn that zero
        directories were evaluated."""
        data_manager.register_data_key("LCOW", "LCOW")
        fake_a = ExpressionNode._key_node("fake_a")
        fake_b = ExpressionNode._key_node("fake_b")
        data_manager.register_expression(fake_a + fake_b, return_key="totally_fake")

        import logging

        with caplog.at_level(logging.WARNING):
            data_manager.load_data()

        assert (
            "not evaluated" in caplog.text.lower()
            or "was not evaluated" in caplog.text.lower()
        )

    def test_no_expressions_registered(self, data_manager):
        """evaluate_expressions with nothing registered should be a no-op."""
        data_manager.register_data_key("LCOW", "LCOW")
        # load_data auto-calls evaluate_expressions; should not raise
        data_manager.load_data()

    def test_expression_evaluates_in_all_directories(self, data_manager):
        """The expression should be evaluated once per unique directory."""
        data_manager.register_data_key("LCOW", "LCOW")
        data_manager.register_data_key("LCOW", "LCOW2")
        ek = data_manager.get_expression_keys()
        data_manager.register_expression(ek.LCOW + ek.LCOW2, return_key="per_dir_sum")
        data_manager.load_data()

        num_dirs_with_both = 0
        for dk in data_manager.directory_keys:
            try:
                data_manager.get_data(dk, "LCOW")
                data_manager.get_data(dk, "LCOW2")
                num_dirs_with_both += 1
            except KeyError:
                pass

        result_keys = [k for k in data_manager.keys() if "per_dir_sum" in str(k)]
        assert len(result_keys) == num_dirs_with_both

    def test_expression_with_units_conversion(self, data_manager):
        """Expression result should have units applied when specified."""
        data_manager.register_data_key("LCOW", "LCOW")
        data_manager.register_data_key(
            "fs.costing.reverse_osmosis.membrane_cost", "membrane_cost"
        )
        ek = data_manager.get_expression_keys()
        data_manager.register_expression(
            ek.LCOW * ek.membrane_cost,
            return_key="with_assign",
            assign_units="USD",
        )
        data_manager.load_data()

        result_keys = [k for k in data_manager.keys() if "with_assign" in str(k)]
        assert len(result_keys) > 0
        for k in result_keys:
            assert data_manager[k].sunits == "USD"

    def test_multiple_expressions(self, data_manager):
        """Multiple registered expressions should all be evaluated."""
        data_manager.register_data_key("LCOW", "LCOW")
        data_manager.register_data_key("LCOW", "LCOW2")
        ek = data_manager.get_expression_keys()
        data_manager.register_expression(ek.LCOW + ek.LCOW2, return_key="expr_sum")
        data_manager.register_expression(ek.LCOW - ek.LCOW2, return_key="expr_diff")
        data_manager.load_data()
        data_manager.display()
        sum_keys = [k for k in data_manager.keys() if "expr_sum" in str(k)]
        diff_keys = [k for k in data_manager.keys() if "expr_diff" in str(k)]
        assert len(sum_keys) > 0
        assert len(diff_keys) > 0

    def test_expression_with_special_char_keys(self):
        """Expressions using keys with unsafe characters should evaluate
        correctly using the original key names, not sanitised attribute names."""
        dm = PsDataManager()
        ps1 = PsData("Ca_2+", "test", np.array([1.0, 2.0, 3.0]))
        ps2 = PsData("LCOW (m**3)", "test", np.array([10.0, 20.0, 30.0]))
        dm.add_data("dir_a", "Ca_2+", ps1)
        dm.add_data("dir_a", "LCOW (m**3)", ps2)
        dm.register_data_key("Ca_2+", "Ca_2+")
        dm.register_data_key("LCOW (m**3)", "LCOW (m**3)")

        ek = dm.get_expression_keys()
        # Verify nodes carry original keys, not sanitised names
        assert ek.Ca_2.key == "Ca_2+"
        assert ek.LCOW_m_3.key == "LCOW (m**3)"

        dm.register_expression(ek.Ca_2 * ek.LCOW_m_3, return_key="product")
        dm.evaluate_expressions()

        result = dm.get_data("dir_a", "product")
        np.testing.assert_array_almost_equal(result.data, [10.0, 40.0, 90.0])

    def test_expression_with_tuple_keys(self):
        """Expressions using tuple return_keys should evaluate correctly
        by looking up the original tuple key in PsDataManager."""
        dm = PsDataManager()
        ps1 = PsData("a", "test", np.array([2.0, 4.0]))
        ps2 = PsData("b", "test", np.array([3.0, 5.0]))
        dm.add_data("dir_b", ("group", "a"), ps1)
        dm.add_data("dir_b", ("group", "b"), ps2)
        dm.register_data_key(("group", "a"), ("group", "a"))
        dm.register_data_key(("group", "b"), ("group", "b"))

        ek = dm.get_expression_keys()
        # Attr access should resolve to original tuple key
        assert ek.group_a.key == ("group", "a")
        assert ek.group_b.key == ("group", "b")
        # Item access should also work
        assert ek["group", "a"].key == ("group", "a")

        dm.register_expression(ek.group_a + ek.group_b, return_key="sum_ab")
        dm.evaluate_expressions()

        result = dm.get_data("dir_b", "sum_ab")
        np.testing.assert_array_almost_equal(result.data, [5.0, 9.0])

    def test_expression_item_access_evaluates(self):
        """Expressions built via ek[key] item access should evaluate correctly."""
        dm = PsDataManager()
        dm.add_data("d", "Ca_2+", PsData("Ca_2+", "t", np.array([2.0])))
        dm.add_data("d", "simple", PsData("simple", "t", np.array([3.0])))
        dm.register_data_key("Ca_2+", "Ca_2+")
        dm.register_data_key("simple", "simple")

        ek = dm.get_expression_keys()
        dm.register_expression(ek["Ca_2+"] * ek["simple"], return_key="res")
        dm.evaluate_expressions()

        result = dm.get_data("d", "res")
        np.testing.assert_array_almost_equal(result.data, [6.0])

    # --- auto_evaluate_expressions ---

    def test_auto_evaluate_on_register_with_data(self):
        """register_expression should auto-evaluate when data is present."""
        dm = PsDataManager()
        dm.add_data("d", "a", PsData("a", "t", np.array([2.0, 3.0])))
        dm.add_data("d", "b", PsData("b", "t", np.array([10.0, 20.0])))

        ek = dm.get_expression_keys()
        # auto_evaluate_expressions is True by default
        dm.register_expression(ek.a + ek.b, return_key="sum_ab")

        # Result should already be available without calling evaluate_expressions
        result = dm.get_data("d", "sum_ab")
        np.testing.assert_array_almost_equal(result.data, [12.0, 23.0])

    def test_auto_evaluate_disabled(self):
        """Setting auto_evaluate_expressions=False should skip auto-evaluation."""
        dm = PsDataManager()
        dm.auto_evaluate_expressions = False
        dm.add_data("d", "a", PsData("a", "t", np.array([2.0])))
        dm.add_data("d", "b", PsData("b", "t", np.array([3.0])))

        ek = dm.get_expression_keys()
        dm.register_expression(ek.a + ek.b, return_key="sum_ab")

        # Result should NOT be available yet
        with pytest.raises(KeyError):
            dm.get_data("d", "sum_ab")

        # Now call manually
        dm.evaluate_expressions()
        result = dm.get_data("d", "sum_ab")
        np.testing.assert_array_almost_equal(result.data, [5.0])

    def test_auto_evaluate_no_data_yet(self):
        """register_expression before data is loaded should not fail."""
        dm = PsDataManager()
        ek = ExpressionKeys(["a", "b"])
        dm._expression_keys = ek  # set up keys without data
        # No data yet — register should not crash even with auto_evaluate on
        dm.register_expression(ek.a + ek.b, return_key="sum_ab")
        # And nothing should be evaluated
        assert len(dm) == 0


# ---------- add_data auto-wrapping ----------


class TestAddDataAutoWrap:
    """Tests for add_data when a non-PsData value is provided."""

    def test_add_raw_list(self, data_manager):
        """Passing a plain list should auto-wrap it into a PsData."""
        data_manager.add_data("test_dir", "my_key", [1.0, 2.0, 3.0])
        result = data_manager.get_data("test_dir", "my_key")
        assert isinstance(result, PsData)
        np.testing.assert_array_equal(result.data, [1.0, 2.0, 3.0])
        assert str(result.data_with_units.dimensionality) == "dimensionless"
        assert result.data_type == "created"

    def test_add_numpy_array(self, data_manager):
        """Passing a numpy array should auto-wrap it into a PsData."""
        data_manager.add_data("test_dir", "arr", np.array([10, 20, 30]))
        result = data_manager.get_data("test_dir", "arr")
        assert isinstance(result, PsData)
        np.testing.assert_array_equal(result.data, [10, 20, 30])

    def test_add_with_units(self, data_manager):
        """The units kwarg should set import_units on the auto-created PsData."""
        data_manager.add_data("test_dir", "pressure", [100, 200], units="kPa")
        result = data_manager.get_data("test_dir", "pressure")
        assert isinstance(result, PsData)
        assert "kPa" in str(result.data_with_units.dimensionality)

    def test_add_with_assign_units(self, data_manager):
        """The assign_units kwarg should assign units without conversion."""
        data_manager.add_data("test_dir", "cost", [5.5, 6.6], assign_units="USD/m**3")
        result = data_manager.get_data("test_dir", "cost")
        assert isinstance(result, PsData)
        assert "USD/m**3" in str(result.data_with_units.dimensionality)

    def test_add_with_data_type(self, data_manager):
        """The data_type kwarg should override the default 'created' type."""
        data_manager.add_data("test_dir", "custom", [1, 2], data_type="sweep_params")
        result = data_manager.get_data("test_dir", "custom")
        assert result.data_type == "sweep_params"

    def test_add_psdata_passthrough(self, data_manager):
        """Passing a PsData object directly should still work unchanged."""
        ps = PsData("x", "output", np.array([9, 8, 7]))
        data_manager.add_data("test_dir", "existing_ps", ps)
        result = data_manager.get_data("test_dir", "existing_ps")
        assert result is ps
        np.testing.assert_array_equal(result.data, [9, 8, 7])

    def test_add_scalar(self, data_manager):
        """Passing a scalar value should auto-wrap it into a PsData."""
        data_manager.add_data("test_dir", "single", 42.0)
        result = data_manager.get_data("test_dir", "single")
        assert isinstance(result, PsData)
        assert float(result.data) == 42.0
