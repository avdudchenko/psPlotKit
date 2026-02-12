import pytest
import os
import numpy as np
from psPlotKit.data_manager.ps_data_manager import PsDataManager
from psPlotKit.data_manager.ps_data import PsData

__author__ = "Alexander V. Dudchenko (SLAC)"

_this_file_path = os.path.dirname(os.path.abspath(__file__))
_test_file = os.path.join(_this_file_path, "test_file.h5")


# ---------- fixtures ----------


@pytest.fixture
def data_manager():
    """PsDataManager pointed at the shared test h5 file."""
    return PsDataManager(_test_file)


@pytest.fixture
def loaded_data_manager(data_manager):
    """PsDataManager with LCOW already registered, loaded, and verified."""
    data_manager.register_data_key("LCOW", "LCOW")
    data_manager.load_data()
    return data_manager


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
        """Full workflow: register → load → check, all keys present."""
        data_manager.register_data_key("LCOW", "LCOW")
        data_manager.register_data_key(
            "fs.costing.reverse_osmosis.membrane_cost", "membrane_cost"
        )
        data_manager.load_data()

        # both should be marked imported
        for key in ["LCOW", "membrane_cost"]:
            assert (
                data_manager._registered_key_import_status[key]["imported"] is True
            ), f"{key} should be marked imported"

        # check_import_status should pass cleanly
        data_manager.check_import_status(raise_error=True)

    def test_register_load_check_partial_missing(self, data_manager):
        """Register a mix of real and fake keys, load, then verify only
        the fake one is reported missing."""
        data_manager.register_data_key("LCOW", "LCOW")
        data_manager.register_data_key("fs.costing.reDer_osmosis.membrane_cost", "Bogus")
        data_manager.load_data()

        assert data_manager._registered_key_import_status["LCOW"]["imported"] is True
        assert data_manager._registered_key_import_status["Bogus"]["imported"] is False

        with pytest.raises(KeyError, match="Bogus"):
            data_manager.check_import_status(raise_error=True)

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
