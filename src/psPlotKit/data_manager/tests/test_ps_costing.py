import pytest
import numpy as np
import os

from psPlotKit.data_manager.ps_data_manager import PsDataManager
from psPlotKit.data_manager.ps_data import PsData
from psPlotKit.data_manager.ps_costing import (
    PsCostingGroup,
    PsCostingPackage,
    PsCostingManager,
)

__author__ = "Alexander V. Dudchenko "

# Path to real h5 test data produced by the parameter sweep tool.
_bgw_h5 = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "..",
    "examples",
    "data",
    "bgw_analysis_analysisType_bgw_analysis.h5",
)


# ---------------------------------------------------------------------------
# PsCostingGroup
# ---------------------------------------------------------------------------


class TestPsCostingGroup:
    def test_create_group(self):
        g = PsCostingGroup("RO")
        assert g.name == "RO"
        assert g.costing_block_key == "costing"
        assert g.units == {}

    def test_custom_costing_block(self):
        g = PsCostingGroup("Pre", costing_block_key="cost_block")
        assert g.costing_block_key == "cost_block"

    def test_add_unit_with_block_keys(self):
        g = PsCostingGroup("RO")
        g.add_unit(
            "ROUnits",
            capex_keys=["capital_cost"],
            fixed_opex_keys=["fixed_operating_cost"],
        )
        u = g.units["ROUnits"]
        assert u["capex_keys"] == ["capital_cost"]
        assert u["fixed_opex_keys"] == ["fixed_operating_cost"]
        assert u["capex_from_dm"] == {}
        assert u["fixed_opex_from_dm"] == {}

    def test_add_unit_with_dm_keys(self):
        g = PsCostingGroup("RO")
        g.add_unit(
            "PrimaryPumps",
            capex_keys=["capital_cost"],
            fixed_opex_from_data_manager={"energy": "pump_energy_cost"},
        )
        u = g.units["PrimaryPumps"]
        assert u["capex_keys"] == ["capital_cost"]
        assert u["fixed_opex_keys"] == []
        assert u["fixed_opex_from_dm"] == {"energy": "pump_energy_cost"}

    def test_add_multiple_units(self):
        g = PsCostingGroup("RO")
        g.add_unit("ROUnits", capex_keys=["capital_cost"])
        g.add_unit("PrimaryPumps", capex_keys=["capital_cost"])
        assert len(g.units) == 2

    def test_units_is_copy(self):
        g = PsCostingGroup("RO")
        g.add_unit("a", capex_keys=["capital_cost"])
        u = g.units
        u["b"] = {}  # mutating the returned dict
        assert "b" not in g.units  # should not affect internal state

    def test_add_unit_with_flow_keys(self):
        g = PsCostingGroup("Pumps")
        g.add_unit(
            "PrimaryPumps",
            capex_keys=["capital_cost"],
            flow_keys={"electricity": ["electricity_flow"]},
        )
        u = g.units["PrimaryPumps"]
        assert u["flow_keys"] == {"electricity": ["electricity_flow"]}
        assert u["flow_from_dm"] == {}

    def test_add_unit_with_flow_from_dm(self):
        g = PsCostingGroup("Pumps")
        g.add_unit(
            "PrimaryPumps",
            capex_keys=[],
            flow_from_data_manager={"electricity": {"pump_work": "pump_1_work"}},
        )
        u = g.units["PrimaryPumps"]
        assert u["flow_from_dm"] == {"electricity": {"pump_work": "pump_1_work"}}


# ---------------------------------------------------------------------------
# PsCostingPackage
# ---------------------------------------------------------------------------


class TestPsCostingPackage:
    def test_default_costing_block(self):
        pkg = PsCostingPackage()
        assert pkg.costing_block == "fs.costing"

    def test_custom_costing_block(self):
        pkg = PsCostingPackage(costing_block="m.costing")
        assert pkg.costing_block == "m.costing"

    def test_add_parameter_auto_filekey(self):
        pkg = PsCostingPackage()
        pkg.add_parameter("capital_recovery_factor")
        p = pkg.parameters["capital_recovery_factor"]
        assert p["file_key"] == "fs.costing.capital_recovery_factor"
        assert p["units"] is None
        assert p["assign_units"] is None

    def test_add_parameter_explicit_filekey(self):
        pkg = PsCostingPackage()
        pkg.add_parameter(
            "product_flow",
            file_key="fs.product.flow",
            units="m**3/year",
        )
        p = pkg.parameters["product_flow"]
        assert p["file_key"] == "fs.product.flow"
        assert p["units"] == "m**3/year"

    def test_add_parameter_with_assign_units(self):
        pkg = PsCostingPackage()
        pkg.add_parameter("LCOW", assign_units="USD/m**3")
        p = pkg.parameters["LCOW"]
        assert p["assign_units"] == "USD/m**3"

    def test_add_formula(self):
        pkg = PsCostingPackage()
        builder = lambda ek: ek.a + ek.b
        pkg.add_formula("total", builder, assign_units="USD")
        assert len(pkg.formulae) == 1
        assert pkg.formulae[0]["return_key"] == "total"
        assert pkg.formulae[0]["assign_units"] == "USD"

    def test_multiple_formulae_ordering(self):
        pkg = PsCostingPackage()
        pkg.add_formula("first", lambda ek: ek.a)
        pkg.add_formula("second", lambda ek: ek.b)
        assert [f["return_key"] for f in pkg.formulae] == ["first", "second"]

    def test_parameters_is_copy(self):
        pkg = PsCostingPackage()
        pkg.add_parameter("a")
        p = pkg.parameters
        p["b"] = {}
        assert "b" not in pkg.parameters

    def test_add_flow_cost(self):
        pkg = PsCostingPackage()
        pkg.add_flow_cost("electricity", "electricity_cost")
        assert pkg.flow_costs == {
            "electricity": {
                "cost_parameter": "electricity_cost",
                "units": "USD/yr",
                "assign_units": None,
            }
        }

    def test_flow_costs_is_copy(self):
        pkg = PsCostingPackage()
        pkg.add_flow_cost("electricity", "electricity_cost")
        fc = pkg.flow_costs
        fc["chemicals"] = {}
        assert "chemicals" not in pkg.flow_costs


# ---------------------------------------------------------------------------
# PsCostingManager — key discovery using real h5 keys
# ---------------------------------------------------------------------------


class TestKeyDiscovery:
    """Test _find_matching_keys against key patterns found in bgw h5 data."""

    def test_find_ROUnits_capital_cost(self):
        """Should match all ROUnits[N].costing.capital_cost keys."""
        keys = {
            "fs.ROUnits[1].costing.capital_cost",
            "fs.ROUnits[2].costing.capital_cost",
            "fs.ROUnits[1].costing.fixed_operating_cost",
            "fs.costing.LCOW",
        }
        matches = PsCostingManager._find_matching_keys(
            keys, "ROUnits", "costing", "capital_cost"
        )
        assert sorted(matches) == [
            "fs.ROUnits[1].costing.capital_cost",
            "fs.ROUnits[2].costing.capital_cost",
        ]

    def test_find_PrimaryPumps_capital_cost(self):
        keys = {
            "fs.PrimaryPumps[1].costing.capital_cost",
            "fs.ROUnits[1].costing.capital_cost",
            "fs.costing.LCOW",
        }
        matches = PsCostingManager._find_matching_keys(
            keys, "PrimaryPumps", "costing", "capital_cost"
        )
        assert matches == ["fs.PrimaryPumps[1].costing.capital_cost"]

    def test_find_EnergyRecoveryDevices_flow_cost(self):
        """flow_cost is an OPEX key specific to ERDs."""
        keys = {
            "fs.EnergyRecoveryDevices[1].costing.flow_cost",
            "fs.EnergyRecoveryDevices[1].costing.capital_cost",
            "fs.PrimaryPumps[1].costing.capital_cost",
        }
        matches = PsCostingManager._find_matching_keys(
            keys, "EnergyRecoveryDevices", "costing", "flow_cost"
        )
        assert matches == ["fs.EnergyRecoveryDevices[1].costing.flow_cost"]

    def test_find_no_match(self):
        keys = {"fs.PrimaryPumps[1].costing.capital_cost"}
        matches = PsCostingManager._find_matching_keys(
            keys, "ROUnits", "costing", "capital_cost"
        )
        assert matches == []

    def test_find_excludes_global_costing_block(self):
        """The global ``fs.costing.capital_recovery_factor`` should NOT
        match a unit search for ``costing.capital_recovery_factor``."""
        keys = {
            "fs.costing.capital_recovery_factor",
            "fs.ROUnits[1].costing.capital_cost",
        }
        matches = PsCostingManager._find_matching_keys(
            keys, "ROUnits", "costing", "capital_cost"
        )
        assert matches == ["fs.ROUnits[1].costing.capital_cost"]


# ---------------------------------------------------------------------------
# PsCostingManager — full h5-based test (single directory to keep fast)
# ---------------------------------------------------------------------------


@pytest.fixture
def bgw_dm():
    """PsDataManager with bgw h5 limited to the 1-stage directory."""
    dm = PsDataManager(_bgw_h5)
    return dm


class TestPsCostingManagerH5:
    """Integration tests using the real bgw analysis h5 file."""

    def test_discover_keys_for_ROUnits(self, bgw_dm):
        """Discovery should find ROUnits capital_cost and fixed_operating_cost."""
        pkg = PsCostingPackage()
        g = PsCostingGroup("Membrane")
        g.add_unit(
            "ROUnits",
            capex_keys=["capital_cost"],
            fixed_opex_keys=["fixed_operating_cost"],
        )

        cm = PsCostingManager(bgw_dm, pkg, [g])
        cm._discover_keys()

        capex = cm._group_capex_keys["Membrane"]
        opex = cm._group_fixed_opex_keys["Membrane"]
        # In a 1–5 stage h5, stages 1-5 exist; at least one capex+opex key found
        assert len(capex) >= 1
        assert len(opex) >= 1
        # Each return_key should have been registered in _discovered_keys
        for rk in capex + opex:
            assert rk in cm._discovered_keys

    def test_build_with_load(self, bgw_dm):
        """Full build() with real data should produce group aggregates."""
        pkg = PsCostingPackage()
        pkg.add_parameter("capital_recovery_factor")

        g = PsCostingGroup("Membrane")
        g.add_unit("ROUnits", capex_keys=["capital_cost"])

        cm = PsCostingManager(bgw_dm, pkg, [g])
        cm.build(load_data=True)

        # ("costing", "Membrane", "capex") should be available in at least one directory
        found = 0
        for dkey in bgw_dm.directory_keys:
            try:
                data = bgw_dm.get_data(dkey, ("costing", "Membrane", "capex"))
                assert data.data.shape[0] > 0
                # Some sweep points may be infeasible (NaN); just need some finite
                assert np.any(np.isfinite(data.data))
                found += 1
            except KeyError:
                pass  # directory may lack some ROUnits instances
        assert found >= 1

    def test_aggregate_capital_cost_sums_across_groups(self, bgw_dm):
        """Two groups → aggregate_capital_cost = sum of both group capex."""
        pkg = PsCostingPackage()
        g_ro = PsCostingGroup("Membrane")
        g_ro.add_unit("ROUnits", capex_keys=["capital_cost"])

        g_pump = PsCostingGroup("Pumps")
        g_pump.add_unit("PrimaryPumps", capex_keys=["capital_cost"])

        cm = PsCostingManager(bgw_dm, pkg, [g_ro, g_pump])
        cm.build(load_data=True)

        found = 0
        for dkey in bgw_dm.directory_keys:
            try:
                ro_capex = bgw_dm.get_data(dkey, ("costing", "Membrane", "capex")).data
                pump_capex = bgw_dm.get_data(dkey, ("costing", "Pumps", "capex")).data
                total = bgw_dm.get_data(
                    dkey, ("costing", "aggregate_capital_cost")
                ).data
                np.testing.assert_array_almost_equal(total, ro_capex + pump_capex)
                found += 1
            except KeyError:
                pass  # some directories have fewer unit instances
        assert found >= 1

    def test_formula_annualized_capex(self, bgw_dm):
        """Formula: annualized_capex = aggregate_capital_cost * capital_recovery_factor."""
        pkg = PsCostingPackage()
        pkg.add_parameter("capital_recovery_factor")
        pkg.add_formula(
            "annualized_capex",
            lambda ek: ek.aggregate_capital_cost * ek.capital_recovery_factor,
        )

        g = PsCostingGroup("RO")
        g.add_unit("ROUnits", capex_keys=["capital_cost"])

        cm = PsCostingManager(bgw_dm, pkg, [g])
        cm.build(load_data=True)

        found = 0
        for dkey in bgw_dm.directory_keys:
            try:
                total = bgw_dm.get_data(
                    dkey, ("costing", "aggregate_capital_cost")
                ).data
                crf = bgw_dm.get_data(dkey, ("costing", "capital_recovery_factor")).data
                ann = bgw_dm.get_data(dkey, ("costing", "annualized_capex")).data
                np.testing.assert_array_almost_equal(ann, total * crf)
                found += 1
            except KeyError:
                pass
        assert found >= 1


# ---------------------------------------------------------------------------
# PsCostingManager — unit tests with synthetic data
# ---------------------------------------------------------------------------


def _build_test_dm():
    """Create a PsDataManager with synthetic costing data (no h5 file)."""
    dm = PsDataManager()

    # Simulate two units: ROUnits and PrimaryPumps, with capital + opex
    dm.add_data("d", "Membrane_ROUnits_capital_cost", [1000.0, 2000.0], units="USD")
    dm.add_data(
        "d", "Membrane_ROUnits_fixed_operating_cost", [100.0, 200.0], units="USD/year"
    )
    dm.add_data("d", "Pumps_PrimaryPumps_capital_cost", [500.0, 800.0], units="USD")
    dm.add_data("d", "pump_energy_cost", [50.0, 80.0], units="USD/year")

    # Global parameters
    dm.add_data("d", "capital_recovery_factor", [0.1, 0.1])
    dm.add_data("d", "product_flow", [1000.0, 1000.0], units="m**3/year")

    return dm


class TestPsCostingManagerSynthetic:
    def test_build_group_expressions(self):
        """Group capex/opex expressions should aggregate the right keys."""
        dm = _build_test_dm()
        pkg = PsCostingPackage()
        g = PsCostingGroup("Membrane")

        cm = PsCostingManager(dm, pkg, [g])
        cm._group_capex_keys["Membrane"] = [
            "Membrane_ROUnits_capital_cost",
            "Pumps_PrimaryPumps_capital_cost",
        ]
        cm._group_fixed_opex_keys["Membrane"] = []

        cm._build_group_expressions()
        dm.evaluate_expressions()

        result = dm.get_data("d", ("costing", "Membrane", "capex"))
        np.testing.assert_array_almost_equal(result.data, [1500.0, 2800.0])

    def test_build_aggregate_capital_operating(self):
        """aggregate_capital_cost should sum across all groups."""
        dm = _build_test_dm()
        pkg = PsCostingPackage()
        g1 = PsCostingGroup("Membrane")
        g2 = PsCostingGroup("Pumps")

        cm = PsCostingManager(dm, pkg, [g1, g2])
        cm._group_capex_keys["Membrane"] = ["Membrane_ROUnits_capital_cost"]
        cm._group_capex_keys["Pumps"] = ["Pumps_PrimaryPumps_capital_cost"]
        cm._group_fixed_opex_keys["Membrane"] = []
        cm._group_fixed_opex_keys["Pumps"] = []

        cm._build_group_expressions()
        dm.evaluate_expressions()

        total = dm.get_data("d", ("costing", "aggregate_capital_cost"))
        np.testing.assert_array_almost_equal(total.data, [1500.0, 2800.0])

    def test_formula_evaluation(self):
        """Formulae should be evaluated after group expressions."""
        dm = _build_test_dm()

        pkg = PsCostingPackage()
        pkg.add_formula(
            "annualized_capex",
            lambda ek: ek.aggregate_capital_cost * ek.capital_recovery_factor,
        )

        g = PsCostingGroup("RO")
        cm = PsCostingManager(dm, pkg, [g])

        cm._group_capex_keys["RO"] = [
            "Membrane_ROUnits_capital_cost",
            "Pumps_PrimaryPumps_capital_cost",
        ]
        cm._group_fixed_opex_keys["RO"] = [
            "Membrane_ROUnits_fixed_operating_cost",
            "pump_energy_cost",
        ]

        cm._build_group_expressions()
        cm._build_formula_expressions()
        dm.evaluate_expressions()

        # annualized_capex = (1000+500)*0.1 = 150, (2000+800)*0.1 = 280
        ann = dm.get_data("d", ("costing", "annualized_capex"))
        np.testing.assert_array_almost_equal(ann.data, [150.0, 280.0])

        # aggregate_fixed_operating_cost = (100+50) = 150, (200+80) = 280
        opex = dm.get_data("d", ("costing", "aggregate_fixed_operating_cost"))
        np.testing.assert_array_almost_equal(opex.data, [150.0, 280.0])

    def test_fixed_opex_from_data_manager(self):
        """Keys referenced via fixed_opex_from_data_manager should be included."""
        dm = _build_test_dm()
        pkg = PsCostingPackage()

        g = PsCostingGroup("RO")
        g.add_unit(
            "PrimaryPumps",
            capex_keys=[],
            fixed_opex_from_data_manager={"energy": "pump_energy_cost"},
        )

        cm = PsCostingManager(dm, pkg, [g])
        cm._group_capex_keys["RO"] = []
        cm._group_fixed_opex_keys["RO"] = ["pump_energy_cost"]

        cm._build_group_expressions()
        dm.evaluate_expressions()

        opex = dm.get_data("d", ("costing", "RO", "fixed_opex"))
        np.testing.assert_array_almost_equal(opex.data, [50.0, 80.0])

    def test_sum_expression_single_key(self):
        """_sum_expression with one key should return a bare node."""
        dm = PsDataManager()
        dm.add_data("d", "a", [1.0])
        ek = dm.get_expression_keys()
        expr = PsCostingManager._sum_expression(ek, ["a"])
        assert expr.key == "a"

    def test_sum_expression_multiple_keys(self):
        """_sum_expression with multiple keys should build an add tree."""
        dm = PsDataManager()
        dm.add_data("d", "a", [1.0])
        dm.add_data("d", "b", [2.0])
        dm.add_data("d", "c", [3.0])
        ek = dm.get_expression_keys()
        expr = PsCostingManager._sum_expression(ek, ["a", "b", "c"])
        result = expr.evaluate(
            {
                "a": dm.get_data("d", "a"),
                "b": dm.get_data("d", "b"),
                "c": dm.get_data("d", "c"),
            }
        )
        assert float(np.asarray(result).item()) == pytest.approx(6.0)

    def test_empty_groups(self):
        """Manager with no groups should not crash."""
        dm = PsDataManager()
        dm.add_data("d", "a", [1.0])
        pkg = PsCostingPackage()
        cm = PsCostingManager(dm, pkg, [])
        cm._discover_keys()
        cm._build_group_expressions()
        dm.evaluate_expressions()
        assert len(dm.data_keys) == 1  # only "a"

    def test_multiple_groups_separate_aggregation(self):
        """Each group should get its own per-group capex/opex keys."""
        dm = _build_test_dm()
        dm.add_data("d", "Pre_filter_capex", [200.0, 300.0], units="USD")

        pkg = PsCostingPackage()
        g1 = PsCostingGroup("Membrane")
        g2 = PsCostingGroup("Pre")

        cm = PsCostingManager(dm, pkg, [g1, g2])
        cm._group_capex_keys["Membrane"] = ["Membrane_ROUnits_capital_cost"]
        cm._group_capex_keys["Pre"] = ["Pre_filter_capex"]
        cm._group_fixed_opex_keys["Membrane"] = []
        cm._group_fixed_opex_keys["Pre"] = []

        cm._build_group_expressions()
        dm.evaluate_expressions()

        ro_capex = dm.get_data("d", ("costing", "Membrane", "capex"))
        np.testing.assert_array_almost_equal(ro_capex.data, [1000.0, 2000.0])

        pre_capex = dm.get_data("d", ("costing", "Pre", "capex"))
        np.testing.assert_array_almost_equal(pre_capex.data, [200.0, 300.0])

        total = dm.get_data("d", ("costing", "aggregate_capital_cost"))
        np.testing.assert_array_almost_equal(total.data, [1200.0, 2300.0])

    def test_flow_cost_electricity(self):
        """Flow keys x cost parameter -> flow cost expression."""
        dm = PsDataManager()
        dm.add_data("d", "Pumps_pump1_electricity_flow", [10.0, 20.0], units="kW")
        dm.add_data("d", "Pumps_pump2_electricity_flow", [5.0, 8.0], units="kW")
        dm.add_data("d", ("costing", "electricity_cost"), [0.07, 0.07], units="USD/kWh")

        pkg = PsCostingPackage()
        pkg.add_flow_cost("electricity", "electricity_cost")

        g = PsCostingGroup("Pumps")
        cm = PsCostingManager(dm, pkg, [g])

        # Simulate discovered flow keys
        cm._flow_type_keys["electricity"] = [
            "Pumps_pump1_electricity_flow",
            "Pumps_pump2_electricity_flow",
        ]

        cm._build_group_expressions()
        cm._build_flow_expressions()
        dm.evaluate_expressions()

        # aggregate_electricity_flow = 15, 28
        agg_flow = dm.get_data("d", ("costing", "aggregate_electricity_flow"))
        np.testing.assert_array_almost_equal(agg_flow.data, [15.0, 28.0])

        # electricity_flow_cost = 15*0.07, 28*0.07
        flow_cost = dm.get_data("d", ("costing", "electricity_flow_cost"))
        np.testing.assert_array_almost_equal(
            flow_cost.data, [9204.103409, 17180.993031]
        )

        # aggregate_flow_cost = same (only one flow type)
        agg_cost = dm.get_data("d", ("costing", "aggregate_flow_cost"))
        np.testing.assert_array_almost_equal(agg_cost.data, [9204.103409, 17180.993031])

    def test_aggregate_flow_cost_multiple_types(self):
        """Two flow types should each aggregate separately; total sums them."""
        dm = PsDataManager()
        dm.add_data("d", "elec_flow_1", [10.0, 20.0])
        dm.add_data("d", "elec_flow_2", [5.0, 8.0])
        dm.add_data("d", "chem_flow_1", [2.0, 3.0])
        dm.add_data("d", ("costing", "electricity_cost"), [0.07, 0.07])
        dm.add_data("d", ("costing", "chemical_cost"), [1.0, 1.0])

        pkg = PsCostingPackage()
        pkg.add_flow_cost(
            "electricity", "electricity_cost", aggregate_units="dimensionless"
        )
        pkg.add_flow_cost("chemicals", "chemical_cost", aggregate_units="dimensionless")

        g = PsCostingGroup("RO")
        cm = PsCostingManager(dm, pkg, [g])
        cm._flow_type_keys["electricity"] = ["elec_flow_1", "elec_flow_2"]
        cm._flow_type_keys["chemicals"] = ["chem_flow_1"]

        cm._build_group_expressions()
        cm._build_flow_expressions()
        dm.evaluate_expressions()

        # aggregate_electricity_flow = 15, 28
        agg_elec = dm.get_data("d", ("costing", "aggregate_electricity_flow"))
        np.testing.assert_array_almost_equal(agg_elec.data, [15.0, 28.0])

        # aggregate_chemicals_flow = 2, 3
        agg_chem = dm.get_data("d", ("costing", "aggregate_chemicals_flow"))
        np.testing.assert_array_almost_equal(agg_chem.data, [2.0, 3.0])

        # electricity_flow_cost = 1.05, 1.96
        # chemicals_flow_cost = 2.0, 3.0
        # aggregate_flow_cost = 3.05, 4.96
        agg_cost = dm.get_data("d", ("costing", "aggregate_flow_cost"))
        np.testing.assert_array_almost_equal(agg_cost.data, [3.05, 4.96])

    def test_no_cost_param_for_flow_type(self):
        """Flow type without cost param: aggregate flow built, no cost expr."""
        dm = PsDataManager()
        dm.add_data("d", "elec_flow", [10.0, 20.0])

        pkg = PsCostingPackage()
        # No add_flow_cost call

        g = PsCostingGroup("RO")
        cm = PsCostingManager(dm, pkg, [g])
        cm._flow_type_keys["electricity"] = ["elec_flow"]

        cm._build_group_expressions()
        cm._build_flow_expressions()
        dm.evaluate_expressions()

        # aggregate_electricity_flow should exist
        agg_flow = dm.get_data("d", ("costing", "aggregate_electricity_flow"))
        np.testing.assert_array_almost_equal(agg_flow.data, [10.0, 20.0])

        # electricity_flow_cost should NOT exist
        with pytest.raises(KeyError):
            dm.get_data("d", ("costing", "electricity_flow_cost"))

        # aggregate_flow_cost should NOT exist
        with pytest.raises(KeyError):
            dm.get_data("d", ("costing", "aggregate_flow_cost"))

    # ------------------------------------------------------------------
    # Per-group flow expressions
    # ------------------------------------------------------------------

    def test_per_group_flow_expressions(self):
        """Per-group flow costs should be computed independently."""
        dm = PsDataManager()
        dm.add_data("d", "pump_elec_flow", [10.0, 20.0], units="kW")
        dm.add_data("d", "erd_elec_flow", [3.0, 5.0], units="kW")
        dm.add_data("d", ("costing", "electricity_cost"), [0.07, 0.07], units="USD/kWh")

        pkg = PsCostingPackage()
        pkg.add_flow_cost("electricity", "electricity_cost")

        g_pump = PsCostingGroup("Pumps")
        g_erd = PsCostingGroup("ERD")

        cm = PsCostingManager(dm, pkg, [g_pump, g_erd])
        cm._group_capex_keys["Pumps"] = []
        cm._group_capex_keys["ERD"] = []
        cm._group_fixed_opex_keys["Pumps"] = []
        cm._group_fixed_opex_keys["ERD"] = []
        cm._flow_type_keys["electricity"] = ["pump_elec_flow", "erd_elec_flow"]
        cm._group_flow_type_keys["Pumps"] = {"electricity": ["pump_elec_flow"]}
        cm._group_flow_type_keys["ERD"] = {"electricity": ["erd_elec_flow"]}

        cm._build_group_expressions()
        cm._build_flow_expressions()
        cm._build_per_group_flow_expressions()
        dm.evaluate_expressions()

        # Per-group flows
        pump_flow = dm.get_data("d", ("costing", "Pumps", "electricity_flow"))
        np.testing.assert_array_almost_equal(pump_flow.data, [10.0, 20.0])
        erd_flow = dm.get_data("d", ("costing", "ERD", "electricity_flow"))
        np.testing.assert_array_almost_equal(erd_flow.data, [3.0, 5.0])

        # Per-group flow costs
        pump_fc = dm.get_data("d", ("costing", "Pumps", "electricity_flow_cost"))
        np.testing.assert_array_almost_equal(pump_fc.data, [6136.06894, 12272.137879])
        erd_fc = dm.get_data("d", ("costing", "ERD", "electricity_flow_cost"))
        np.testing.assert_array_almost_equal(erd_fc.data, [1840.820682, 3068.03447])

        # Per-group aggregate flow cost
        pump_afc = dm.get_data("d", ("costing", "Pumps", "flow_cost"))
        np.testing.assert_array_almost_equal(pump_afc.data, [6136.06894, 12272.137879])
        erd_afc = dm.get_data("d", ("costing", "ERD", "flow_cost"))
        np.testing.assert_array_almost_equal(erd_afc.data, [1840.820682, 3068.03447])

        # Global aggregate should still be the sum
        agg = dm.get_data("d", ("costing", "aggregate_flow_cost"))
        np.testing.assert_array_almost_equal(agg.data, [7976.889621, 15340.172349])

    # ------------------------------------------------------------------
    # Per-group formula expressions
    # ------------------------------------------------------------------

    def test_per_group_formula_capex_only(self):
        """Per-group formulas should use group capex, zero for missing types."""
        dm = PsDataManager()
        dm.add_data("d", "RO_capex", [1000.0, 2000.0], units="USD")
        dm.add_data("d", "Pump_capex", [500.0, 800.0], units="USD")
        dm.add_data("d", "capital_recovery_factor", [0.1, 0.1])

        pkg = PsCostingPackage()
        pkg.add_formula(
            "annualized_capex",
            lambda ek: ek.aggregate_capital_cost * ek.capital_recovery_factor,
        )

        g_ro = PsCostingGroup("RO")
        g_pump = PsCostingGroup("Pumps")

        cm = PsCostingManager(dm, pkg, [g_ro, g_pump])
        cm._group_capex_keys["RO"] = ["RO_capex"]
        cm._group_capex_keys["Pumps"] = ["Pump_capex"]
        cm._group_fixed_opex_keys["RO"] = []
        cm._group_fixed_opex_keys["Pumps"] = []
        cm._group_flow_type_keys["RO"] = {}
        cm._group_flow_type_keys["Pumps"] = {}

        cm._build_group_expressions()
        cm._build_formula_expressions()
        cm._build_per_group_formula_expressions()
        dm.evaluate_expressions()

        # Global annualized_capex = (1000+500)*0.1, (2000+800)*0.1
        ann = dm.get_data("d", ("costing", "annualized_capex"))
        np.testing.assert_array_almost_equal(ann.data, [150.0, 280.0])

        # Per-group annualized_capex
        ro_ann = dm.get_data("d", ("costing", "RO", "annualized_capex"))
        np.testing.assert_array_almost_equal(ro_ann.data, [100.0, 200.0])
        pump_ann = dm.get_data("d", ("costing", "Pumps", "annualized_capex"))
        np.testing.assert_array_almost_equal(pump_ann.data, [50.0, 80.0])

    def test_per_group_formula_chained(self):
        """Chained formulas should reference per-group results of earlier formulas."""
        dm = PsDataManager()
        dm.add_data("d", "RO_capex", [1000.0, 2000.0], units="USD")
        dm.add_data("d", "capital_recovery_factor", [0.1, 0.1])
        dm.add_data("d", "maintenance_factor", [0.02, 0.02])

        pkg = PsCostingPackage()
        pkg.add_formula(
            "annualized_capex",
            lambda ek: ek.aggregate_capital_cost * ek.capital_recovery_factor,
        )
        pkg.add_formula(
            "maintenance_cost",
            lambda ek: ek.aggregate_capital_cost * ek.maintenance_factor,
        )
        pkg.add_formula(
            "total_annualized",
            lambda ek: ek.annualized_capex + ek.maintenance_cost,
        )

        g = PsCostingGroup("RO")
        cm = PsCostingManager(dm, pkg, [g])
        cm._group_capex_keys["RO"] = ["RO_capex"]
        cm._group_fixed_opex_keys["RO"] = []
        cm._group_flow_type_keys["RO"] = {}

        cm._build_group_expressions()
        cm._build_formula_expressions()
        cm._build_per_group_formula_expressions()
        dm.evaluate_expressions()

        # Per-group: group_RO_total_annualized = group_RO_annualized_capex + group_RO_maintenance_cost
        # = 1000*0.1 + 1000*0.02 = 120, 2000*0.1 + 2000*0.02 = 240
        result = dm.get_data("d", ("costing", "RO", "total_annualized"))
        np.testing.assert_array_almost_equal(result.data, [120.0, 240.0])

    def test_per_group_formula_with_flow(self):
        """Per-group formulas should use group flow cost when available."""
        dm = PsDataManager()
        dm.add_data("d", "pump_capex", [500.0, 800.0])
        dm.add_data("d", "pump_elec", [10.0, 20.0])
        dm.add_data("d", ("costing", "electricity_cost"), [0.07, 0.07])
        dm.add_data("d", "capital_recovery_factor", [0.1, 0.1])

        pkg = PsCostingPackage()
        pkg.add_flow_cost(
            "electricity", "electricity_cost", aggregate_units="dimensionless"
        )
        pkg.add_formula(
            "total_cost",
            lambda ek: (
                ek.aggregate_capital_cost * ek.capital_recovery_factor
                + ek.aggregate_flow_cost
            ),
        )

        g = PsCostingGroup("Pumps")
        cm = PsCostingManager(dm, pkg, [g])
        cm._group_capex_keys["Pumps"] = ["pump_capex"]
        cm._group_fixed_opex_keys["Pumps"] = []
        cm._flow_type_keys["electricity"] = ["pump_elec"]
        cm._group_flow_type_keys["Pumps"] = {"electricity": ["pump_elec"]}

        cm._build_group_expressions()
        cm._build_flow_expressions()
        cm._build_per_group_flow_expressions()
        cm._build_formula_expressions()
        cm._build_per_group_formula_expressions()
        dm.evaluate_expressions()

        # Per-group: group_Pumps_total_cost = 500*0.1 + 10*0.07, 800*0.1 + 20*0.07
        #                                   = 50 + 0.7, 80 + 1.4
        result = dm.get_data("d", ("costing", "Pumps", "total_cost"))
        np.testing.assert_array_almost_equal(result.data, [50.7, 81.4])

    def test_per_group_formula_missing_capex_uses_zero(self):
        """Group with no capex: aggregate_capital_cost aliases to zero."""
        dm = PsDataManager()
        dm.add_data("d", "pump_elec", [10.0, 20.0])
        dm.add_data("d", ("costing", "electricity_cost"), [0.07, 0.07])
        dm.add_data("d", "capital_recovery_factor", [0.1, 0.1])

        pkg = PsCostingPackage()
        pkg.add_flow_cost(
            "electricity", "electricity_cost", aggregate_units="dimensionless"
        )
        pkg.add_formula(
            "total_cost",
            lambda ek: (
                ek.aggregate_capital_cost * ek.capital_recovery_factor
                + ek.aggregate_flow_cost
            ),
        )

        g = PsCostingGroup("Pumps")
        cm = PsCostingManager(dm, pkg, [g])
        cm._group_capex_keys["Pumps"] = []
        cm._group_fixed_opex_keys["Pumps"] = []
        cm._flow_type_keys["electricity"] = ["pump_elec"]
        cm._group_flow_type_keys["Pumps"] = {"electricity": ["pump_elec"]}

        cm._build_group_expressions()
        cm._register_zero_sentinel()
        cm._build_flow_expressions()
        cm._build_per_group_flow_expressions()
        # Skip _build_formula_expressions — the global formula would fail
        # because aggregate_capital_cost doesn't exist (no group has capex).
        # The per-group builder should handle this via zero aliasing.
        cm._build_per_group_formula_expressions()
        dm.evaluate_expressions()

        # Group has no capex so aggregate_capital_cost → 0
        # total_cost = 0*0.1 + flow_cost = flow_cost only
        result = dm.get_data("d", ("costing", "Pumps", "total_cost"))
        np.testing.assert_array_almost_equal(result.data, [0.7, 1.4])

    def test_flow_from_data_manager(self):
        """flow_from_data_manager keys should be included in flow aggregation."""
        dm = PsDataManager()
        dm.add_data("d", "pump_work", [10.0, 20.0], units="kW")
        dm.add_data("d", ("costing", "electricity_cost"), [0.05, 0.05], units="USD/kWh")

        pkg = PsCostingPackage()
        pkg.add_flow_cost("electricity", "electricity_cost")

        g = PsCostingGroup("Pumps")
        g.add_unit(
            "PrimaryPumps",
            capex_keys=[],
            flow_from_data_manager={"electricity": {"pump_work": "pump_work"}},
        )

        cm = PsCostingManager(dm, pkg, [g])
        cm._flow_type_keys["electricity"] = ["pump_work"]

        cm._build_group_expressions()
        cm._build_flow_expressions()
        dm.evaluate_expressions()

        agg_flow = dm.get_data("d", ("costing", "aggregate_electricity_flow"))
        np.testing.assert_array_almost_equal(agg_flow.data, [10.0, 20.0])

        flow_cost = dm.get_data("d", ("costing", "electricity_flow_cost"))
        np.testing.assert_array_almost_equal(flow_cost.data, [4382.906385, 8765.812771])

    def test_formula_aggregate_flow_cost_per_type(self):
        """Formulas can reference individual flow-type costs via
        ek.aggregate_flow_cost_<type> or ek.<type>_flow_cost."""
        dm = PsDataManager()
        dm.add_data("d", "pump_elec", [10.0, 20.0])
        dm.add_data("d", ("costing", "electricity_cost"), [0.07, 0.07])
        dm.add_data("d", ("costing", "product_flow"), [1000.0, 1000.0])

        pkg = PsCostingPackage()
        pkg.add_parameter("product_flow", file_key="dummy")
        pkg.add_flow_cost(
            "electricity", "electricity_cost", aggregate_units="dimensionless"
        )
        pkg.add_formula(
            "levelized_electricity",
            lambda ek: ek.aggregate_flow_cost_electricity / ek.product_flow,
        )

        g = PsCostingGroup("Pumps")
        cm = PsCostingManager(dm, pkg, [g])
        cm._flow_type_keys["electricity"] = ["pump_elec"]
        cm._group_capex_keys["Pumps"] = []
        cm._group_fixed_opex_keys["Pumps"] = []
        cm._group_flow_type_keys["Pumps"] = {"electricity": ["pump_elec"]}

        cm._build_group_expressions()
        cm._build_flow_expressions()
        cm._build_per_group_flow_expressions()
        cm._build_formula_expressions()
        cm._build_per_group_formula_expressions()
        dm.evaluate_expressions()

        # Global: electricity_flow_cost = 10*0.07, 20*0.07 = 0.7, 1.4
        # levelized = 0.7/1000, 1.4/1000
        result = dm.get_data("d", ("costing", "levelized_electricity"))
        np.testing.assert_array_almost_equal(result.data, [0.0007, 0.0014])

        # Per-group should also work
        group_result = dm.get_data("d", ("costing", "Pumps", "levelized_electricity"))
        np.testing.assert_array_almost_equal(group_result.data, [0.0007, 0.0014])

    def test_total_formula_aggregation(self):
        """Total formula expressions should sum per-group results."""
        dm = PsDataManager()
        dm.add_data("d", "ro_cap", [100.0, 200.0])
        dm.add_data("d", "pump_cap", [50.0, 60.0])
        dm.add_data("d", ("costing", "crf"), [0.1, 0.1])
        dm.add_data("d", ("costing", "product_flow"), [1000.0, 1000.0])

        pkg = PsCostingPackage()
        pkg.add_parameter("crf", file_key="dummy")
        pkg.add_parameter("product_flow", file_key="dummy")
        pkg.add_formula(
            "annualized_capex",
            lambda ek: ek.aggregate_capital_cost * ek.crf,
        )
        pkg.add_formula(
            "LCOW",
            lambda ek: ek.annualized_capex / ek.product_flow,
        )

        ro = PsCostingGroup("RO")
        pumps = PsCostingGroup("Pumps")
        cm = PsCostingManager(dm, pkg, [ro, pumps])
        cm._group_capex_keys = {"RO": ["ro_cap"], "Pumps": ["pump_cap"]}
        cm._group_fixed_opex_keys = {"RO": [], "Pumps": []}
        cm._group_flow_type_keys = {"RO": {}, "Pumps": {}}

        cm._build_group_expressions()
        cm._build_flow_expressions()
        cm._build_per_group_flow_expressions()
        cm._build_formula_expressions()
        cm._build_per_group_formula_expressions()
        cm._build_total_formula_expressions()
        dm.evaluate_expressions()

        # Per-group: RO annualized = 100*0.1=10, 200*0.1=20
        #            Pumps annualized = 50*0.1=5, 60*0.1=6
        # Total annualized = 15, 26
        total_ann = dm.get_data("d", ("costing", "total", "annualized_capex"))
        np.testing.assert_array_almost_equal(total_ann.data, [15.0, 26.0])

        # Per-group LCOW: RO = 10/1000=0.01, 20/1000=0.02
        #                 Pumps = 5/1000=0.005, 6/1000=0.006
        # Total LCOW = 0.015, 0.026
        total_lcow = dm.get_data("d", ("costing", "total", "LCOW"))
        np.testing.assert_array_almost_equal(total_lcow.data, [0.015, 0.026])

        # Total should match the global formula result
        global_lcow = dm.get_data("d", ("costing", "LCOW"))
        np.testing.assert_array_almost_equal(total_lcow.data, global_lcow.data)

    def test_add_validation_with_file_key(self):
        """add_validation stores a validation entry with file_key."""
        pkg = PsCostingPackage()
        pkg.add_validation("LCOW", file_key="fs.costing.LCOW", rtol=1e-4)
        assert len(pkg.validations) == 1
        v = pkg.validations[0]
        assert v["formula_key"] == "LCOW"
        assert v["file_key"] == "fs.costing.LCOW"
        assert v["reference_key"] is None
        assert v["rtol"] == 1e-4

    def test_add_validation_with_reference_key(self):
        """add_validation stores a validation entry with reference_key."""
        pkg = PsCostingPackage()
        pkg.add_validation("LCOW", reference_key="my_lcow")
        v = pkg.validations[0]
        assert v["file_key"] is None
        assert v["reference_key"] == "my_lcow"

    def test_add_validation_requires_key(self):
        """add_validation raises if neither file_key nor reference_key given."""
        pkg = PsCostingPackage()
        with pytest.raises(ValueError, match="file_key or reference_key"):
            pkg.add_validation("LCOW")

    def test_validation_passes(self):
        """Validation should pass when total matches reference."""
        dm = PsDataManager()
        dm.add_data("d", "ro_cap", [100.0, 200.0])
        dm.add_data("d", "pump_cap", [50.0, 60.0])
        dm.add_data("d", ("costing", "crf"), [0.1, 0.1])
        dm.add_data("d", ("costing", "product_flow"), [1000.0, 1000.0])

        pkg = PsCostingPackage()
        pkg.add_parameter("crf", file_key="dummy")
        pkg.add_parameter("product_flow", file_key="dummy")
        pkg.add_formula(
            "annualized_capex",
            lambda ek: ek.aggregate_capital_cost * ek.crf,
        )
        pkg.add_formula(
            "LCOW",
            lambda ek: ek.annualized_capex / ek.product_flow,
        )
        # Reference is the global LCOW which should match total
        # (150*0.1)/1000 = 0.015, (260*0.1)/1000 = 0.026
        dm.add_data("d", "ref_lcow", [0.015, 0.026])
        pkg.add_validation("LCOW", reference_key="ref_lcow", rtol=1e-4)

        ro = PsCostingGroup("RO")
        pumps = PsCostingGroup("Pumps")
        cm = PsCostingManager(dm, pkg, [ro, pumps])
        cm._group_capex_keys = {"RO": ["ro_cap"], "Pumps": ["pump_cap"]}
        cm._group_fixed_opex_keys = {"RO": [], "Pumps": []}
        cm._group_flow_type_keys = {"RO": {}, "Pumps": {}}

        cm._build_group_expressions()
        cm._build_flow_expressions()
        cm._build_per_group_flow_expressions()
        cm._build_formula_expressions()
        cm._build_per_group_formula_expressions()
        cm._build_total_formula_expressions()
        dm.evaluate_expressions()

        assert cm._validate() is True

    def test_validation_fails(self):
        """Validation should fail when total does not match reference."""
        dm = PsDataManager()
        dm.add_data("d", "ro_cap", [100.0, 200.0])
        dm.add_data("d", ("costing", "crf"), [0.1, 0.1])
        dm.add_data("d", ("costing", "product_flow"), [1000.0, 1000.0])

        pkg = PsCostingPackage()
        pkg.add_parameter("crf", file_key="dummy")
        pkg.add_parameter("product_flow", file_key="dummy")
        pkg.add_formula(
            "LCOW",
            lambda ek: ek.aggregate_capital_cost * ek.crf / ek.product_flow,
        )
        # Reference is deliberately wrong
        dm.add_data("d", "ref_lcow", [999.0, 999.0])
        pkg.add_validation("LCOW", reference_key="ref_lcow", rtol=1e-4)

        ro = PsCostingGroup("RO")
        cm = PsCostingManager(dm, pkg, [ro])
        cm._group_capex_keys = {"RO": ["ro_cap"]}
        cm._group_fixed_opex_keys = {"RO": []}
        cm._group_flow_type_keys = {"RO": {}}

        cm._build_group_expressions()
        cm._build_flow_expressions()
        cm._build_per_group_flow_expressions()
        cm._build_formula_expressions()
        cm._build_per_group_formula_expressions()
        cm._build_total_formula_expressions()
        dm.evaluate_expressions()

        assert cm._validate(error_on_failure=False) is False

    def test_fraction_expressions(self):
        """Fraction expressions should give each group's share of the total."""
        dm = PsDataManager()
        dm.add_data("d", "ro_cap", [100.0, 200.0])
        dm.add_data("d", "pump_cap", [50.0, 60.0])
        dm.add_data("d", ("costing", "crf"), [0.1, 0.1])
        dm.add_data("d", ("costing", "product_flow"), [1000.0, 1000.0])

        pkg = PsCostingPackage()
        pkg.add_parameter("crf", file_key="dummy")
        pkg.add_parameter("product_flow", file_key="dummy")
        pkg.add_formula(
            "annualized_capex",
            lambda ek: ek.aggregate_capital_cost * ek.crf,
        )
        pkg.add_formula(
            "LCOW",
            lambda ek: ek.annualized_capex / ek.product_flow,
        )
        # Only register LCOW fraction — annualized_capex should NOT get one
        pkg.register_fraction("LCOW")

        ro = PsCostingGroup("RO")
        pumps = PsCostingGroup("Pumps")
        cm = PsCostingManager(dm, pkg, [ro, pumps])
        cm._group_capex_keys = {"RO": ["ro_cap"], "Pumps": ["pump_cap"]}
        cm._group_fixed_opex_keys = {"RO": [], "Pumps": []}
        cm._group_flow_type_keys = {"RO": {}, "Pumps": {}}

        cm._build_group_expressions()
        cm._build_flow_expressions()
        cm._build_per_group_flow_expressions()
        cm._build_formula_expressions()
        cm._build_per_group_formula_expressions()
        cm._build_total_formula_expressions()
        cm._build_fraction_expressions()
        dm.evaluate_expressions()

        # LCOW fractions (stored as percentages)
        # RO LCOW = 0.01, 0.02; Pumps LCOW = 0.005, 0.006
        # Total LCOW = 0.015, 0.026
        ro_lcow_frac = dm.get_data("d", ("costing", "RO", "LCOW_fraction"))
        np.testing.assert_array_almost_equal(
            ro_lcow_frac.data, [10.0 / 15.0 * 100, 20.0 / 26.0 * 100]
        )
        pump_lcow_frac = dm.get_data("d", ("costing", "Pumps", "LCOW_fraction"))
        np.testing.assert_array_almost_equal(
            pump_lcow_frac.data, [5.0 / 15.0 * 100, 6.0 / 26.0 * 100]
        )

        # Fractions should sum to 100%
        np.testing.assert_array_almost_equal(
            np.asarray(ro_lcow_frac.data) + np.asarray(pump_lcow_frac.data),
            [100.0, 100.0],
        )

        # annualized_capex_fraction should NOT exist (not registered)
        with pytest.raises(KeyError):
            dm.get_data("d", ("costing", "RO", "annualized_capex_fraction"))

    def test_fraction_with_custom_total_key(self):
        """register_fraction with a different total_key uses that as denominator."""
        dm = PsDataManager()
        dm.add_data("d", "ro_cap", [100.0, 200.0])
        dm.add_data("d", "pump_cap", [50.0, 60.0])
        dm.add_data("d", "ro_opex", [30.0, 40.0])
        dm.add_data("d", "pump_opex", [20.0, 30.0])
        dm.add_data("d", ("costing", "crf"), [0.1, 0.1])
        dm.add_data("d", ("costing", "product_flow"), [1000.0, 1000.0])

        pkg = PsCostingPackage()
        pkg.add_parameter("crf", file_key="dummy")
        pkg.add_parameter("product_flow", file_key="dummy")
        pkg.add_formula(
            "LCOW_capex",
            lambda ek: ek.aggregate_capital_cost * ek.crf / ek.product_flow,
        )
        pkg.add_formula(
            "LCOW_opex",
            lambda ek: ek.aggregate_fixed_operating_cost / ek.product_flow,
        )
        pkg.add_formula(
            "LCOW",
            lambda ek: ek.LCOW_capex + ek.LCOW_opex,
        )
        # Fraction of LCOW_capex relative to total LCOW (not total LCOW_capex)
        pkg.register_fraction("LCOW_capex", total_key="LCOW")
        pkg.register_fraction("LCOW_opex", total_key="LCOW")

        ro = PsCostingGroup("RO")
        pumps = PsCostingGroup("Pumps")
        cm = PsCostingManager(dm, pkg, [ro, pumps])
        cm._group_capex_keys = {"RO": ["ro_cap"], "Pumps": ["pump_cap"]}
        cm._group_fixed_opex_keys = {"RO": ["ro_opex"], "Pumps": ["pump_opex"]}
        cm._group_flow_type_keys = {"RO": {}, "Pumps": {}}

        cm._build_group_expressions()
        cm._build_flow_expressions()
        cm._build_per_group_flow_expressions()
        cm._build_formula_expressions()
        cm._build_per_group_formula_expressions()
        cm._build_total_formula_expressions()
        cm._build_fraction_expressions()
        dm.evaluate_expressions()

        # RO: capex=100, opex=30; Pumps: capex=50, opex=20
        # RO LCOW_capex = 100*0.1/1000 = 0.01
        # Pumps LCOW_capex = 50*0.1/1000 = 0.005
        # RO LCOW_opex = 30/1000 = 0.03
        # Pumps LCOW_opex = 20/1000 = 0.02
        # Total LCOW = (0.01+0.005) + (0.03+0.02) = 0.065
        total_lcow = np.asarray(dm.get_data("d", ("costing", "total", "LCOW")).data)
        np.testing.assert_array_almost_equal(total_lcow[:1], [0.065])

        # RO LCOW_capex_fraction = 0.01 / 0.065 * 100
        ro_capex_frac = dm.get_data("d", ("costing", "RO", "LCOW_capex_fraction"))
        np.testing.assert_array_almost_equal(
            ro_capex_frac.data[:1], [0.01 / 0.065 * 100]
        )

        # All four fractions should sum to 100%
        fracs = [
            dm.get_data("d", ("costing", "RO", "LCOW_capex_fraction")),
            dm.get_data("d", ("costing", "Pumps", "LCOW_capex_fraction")),
            dm.get_data("d", ("costing", "RO", "LCOW_opex_fraction")),
            dm.get_data("d", ("costing", "Pumps", "LCOW_opex_fraction")),
        ]
        total = sum(np.asarray(f.data) for f in fracs)
        np.testing.assert_array_almost_equal(total, [100.0, 100.0])


# ---------------------------------------------------------------------------
# _check_discovery_status
# ---------------------------------------------------------------------------


class TestCheckDiscoveryStatus:
    def test_no_error_when_all_keys_found(self, bgw_dm):
        """When all requested keys match, _check_discovery_status should not raise."""
        pkg = PsCostingPackage()
        g = PsCostingGroup("Membrane")
        g.add_unit("ROUnits", capex_keys=["capital_cost"])

        cm = PsCostingManager(bgw_dm, pkg, [g])
        cm._discover_keys()
        # Should not raise
        cm._check_discovery_status()

    def test_error_on_unfound_capex_key(self, bgw_dm):
        """A capex key suffix that matches nothing should raise KeyError."""
        pkg = PsCostingPackage()
        g = PsCostingGroup("Membrane")
        g.add_unit("ROUnits", capex_keys=["nonexistent_cost_key"])

        cm = PsCostingManager(bgw_dm, pkg, [g])
        cm._discover_keys()
        with pytest.raises(KeyError, match="nonexistent_cost_key"):
            cm._check_discovery_status()

    def test_error_on_unfound_fixed_opex_key(self, bgw_dm):
        """A fixed_opex key suffix that matches nothing should raise KeyError."""
        pkg = PsCostingPackage()
        g = PsCostingGroup("Membrane")
        g.add_unit("ROUnits", fixed_opex_keys=["nonexistent_opex"])

        cm = PsCostingManager(bgw_dm, pkg, [g])
        cm._discover_keys()
        with pytest.raises(KeyError, match="nonexistent_opex"):
            cm._check_discovery_status()

    def test_error_on_unfound_flow_key(self, bgw_dm):
        """A flow key suffix that matches nothing should raise KeyError."""
        pkg = PsCostingPackage()
        g = PsCostingGroup("Membrane")
        g.add_unit(
            "ROUnits",
            flow_keys={"electricity": ["nonexistent_flow"]},
        )

        cm = PsCostingManager(bgw_dm, pkg, [g])
        cm._discover_keys()
        with pytest.raises(KeyError, match="nonexistent_flow"):
            cm._check_discovery_status()

    def test_build_raises_on_unfound_key(self, bgw_dm):
        """Full build() should raise KeyError when a requested key is not found."""
        pkg = PsCostingPackage()
        g = PsCostingGroup("Membrane")
        g.add_unit("ROUnits", capex_keys=["capital_cost", "bogus_key"])

        cm = PsCostingManager(bgw_dm, pkg, [g])
        with pytest.raises(KeyError, match="bogus_key"):
            cm.build()

    def test_mixed_found_and_unfound(self, bgw_dm):
        """Only unfound keys should appear in the error — found ones should not."""
        pkg = PsCostingPackage()
        g = PsCostingGroup("Membrane")
        g.add_unit(
            "ROUnits",
            capex_keys=["capital_cost"],
            fixed_opex_keys=["missing_opex_key"],
        )

        cm = PsCostingManager(bgw_dm, pkg, [g])
        cm._discover_keys()
        # capital_cost should have been found
        assert len(cm._group_capex_keys["Membrane"]) >= 1
        # missing_opex_key should be unfound; capital_cost (found) must NOT appear
        with pytest.raises(KeyError, match="missing_opex_key") as exc_info:
            cm._check_discovery_status()
        assert "capital_cost" not in str(exc_info.value)
