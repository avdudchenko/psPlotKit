from psPlotKit.data_manager.costing_packages.watertap_costing import (
    WaterTapCostingPackage,
)
from psPlotKit.data_manager.ps_costing import (
    PsCostingPackage,
    PsCostingGroup,
    PsCostingManager,
)
from psPlotKit.data_manager.ps_data_manager import PsDataManager
import numpy as np
import os

_h5_file = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "RO_w_ERD_analysisType_BW_sweep.h5",
)


def test_watertap_costing_package():
    dm = PsDataManager(_h5_file)
    RO = PsCostingGroup("RO")
    RO.add_unit(
        "RO",
        capex_keys="capital_cost",
        fixed_opex_keys="fixed_operating_cost",
    )
    pumps = PsCostingGroup("Pumps")
    pumps.add_unit(
        "pump",
        capex_keys="capital_cost",
        flow_keys={"electricity": "control_volume.work"},
    )
    erd = PsCostingGroup("ERD")
    erd.add_unit(
        "ERD",
        capex_keys="capital_cost",
        flow_keys={"electricity": "control_volume.work"},
    )

    pkg = WaterTapCostingPackage()
    pkg.register_product_flow()
    cm = PsCostingManager(dm, pkg, [RO, pumps, erd])
    cm.build()
    # Verify the total key was created and matches the reference in ALL directories
    for dkey in dm.directory_keys:
        total_lcow = dm[(*dkey, ("costing", "total", "LCOW"))].data
        ref_lcow = dm[(*dkey, ("costing", "validation", "LCOW"))].data
        mask = np.isfinite(total_lcow) & np.isfinite(ref_lcow)
        assert np.any(mask), "No finite values in directory {}".format(dkey)
        np.testing.assert_allclose(
            np.asarray(total_lcow)[mask],
            np.asarray(ref_lcow)[mask],
            rtol=1e-4,
            err_msg="LCOW mismatch in directory {}".format(dkey),
        )


def test_with_stages():
    dm = PsDataManager(_h5_file)
    stage_1 = PsCostingGroup("stage 1")
    stage_1.add_unit(
        "stage[1].RO",
        capex_keys="capital_cost",
        fixed_opex_keys="fixed_operating_cost",
    )
    stage_1.add_unit(
        "stage[1].pump",
        capex_keys="capital_cost",
        flow_keys={"electricity": "control_volume.work"},
    )
    stage_2 = PsCostingGroup("stage 2")
    stage_2.add_unit(
        "stage[2].RO",
        capex_keys="capital_cost",
        fixed_opex_keys="fixed_operating_cost",
    )
    stage_2.add_unit(
        "stage[2].pump",
        capex_keys="capital_cost",
        flow_keys={"electricity": "control_volume.work"},
    )
    erd = PsCostingGroup("ERD")
    erd.add_unit(
        "ERD",
        capex_keys="capital_cost",
        flow_keys={"electricity": "control_volume.work"},
    )

    pkg = WaterTapCostingPackage()
    pkg.register_product_flow()
    cm = PsCostingManager(dm, pkg, [stage_1, stage_2, erd])
    cm.build()
    dm.display()
    # Verify the total key was created and matches the reference in ALL directories
    for dkey in dm.directory_keys:
        total_lcow = dm[(*dkey, ("costing", "total", "LCOW"))].data
        ref_lcow = dm[(*dkey, ("costing", "validation", "LCOW"))].data
        mask = np.isfinite(total_lcow) & np.isfinite(ref_lcow)
        assert np.any(mask), "No finite values in directory {}".format(dkey)
        np.testing.assert_allclose(
            np.asarray(total_lcow)[mask],
            np.asarray(ref_lcow)[mask],
            rtol=1e-4,
            err_msg="LCOW mismatch in directory {}".format(dkey),
        )


def test_with_separate_capex_opex():
    dm = PsDataManager(_h5_file)
    stage_1 = PsCostingGroup("stage 1")
    stage_1.add_unit(
        "stage[1].RO",
        capex_keys="capital_cost",
        fixed_opex_keys="fixed_operating_cost",
    )
    stage_1.add_unit(
        "stage[1].pump",
        capex_keys="capital_cost",
    )
    stage_2 = PsCostingGroup("stage 2")
    stage_2.add_unit(
        "stage[2].RO",
        capex_keys="capital_cost",
        fixed_opex_keys="fixed_operating_cost",
    )
    stage_2.add_unit(
        "stage[2].pump",
        capex_keys="capital_cost",
    )
    erd = PsCostingGroup("ERD")
    erd.add_unit(
        "ERD",
        capex_keys="capital_cost",
    )
    power = PsCostingGroup("Power")
    power.add_unit(
        "stage[1].pump",
        flow_keys={"electricity": "control_volume.work"},
    )
    power.add_unit(
        "stage[2].pump",
        flow_keys={"electricity": "control_volume.work"},
    )
    power.add_unit(
        "ERD",
        flow_keys={"electricity": "control_volume.work"},
    )
    pkg = WaterTapCostingPackage()
    pkg.register_product_flow()
    cm = PsCostingManager(dm, pkg, [stage_1, stage_2, erd, power])
    cm.build()
    dm.display()
    # Verify the total key was created and matches the reference in ALL directories
    for dkey in dm.directory_keys:
        total_lcow = dm[(*dkey, ("costing", "total", "LCOW"))].data
        ref_lcow = dm[(*dkey, ("costing", "validation", "LCOW"))].data
        mask = np.isfinite(total_lcow) & np.isfinite(ref_lcow)
        assert np.any(mask), "No finite values in directory {}".format(dkey)
        np.testing.assert_allclose(
            np.asarray(total_lcow)[mask],
            np.asarray(ref_lcow)[mask],
            rtol=1e-4,
            err_msg="LCOW mismatch in directory {}".format(dkey),
        )


def test_with_custom_expressions():
    dm = PsDataManager(_h5_file)
    dm.register_data_key(
        "fs.stage[1].pump.control_volume.work[0.0]", ("stage 1", "pump_work")
    )
    dm.register_data_key(
        "fs.stage[2].pump.control_volume.work[0.0]", ("stage 2", "pump_work")
    )
    dm.load_data()
    ek = dm.get_expression_keys()
    dm.register_expression(ek.stage_1_pump_work * 1.0, ("stage 1", "pump_work_expr"))
    dm.register_expression(ek.stage_2_pump_work * 1.0, ("stage 2", "pump_work_expr"))
    RO = PsCostingGroup("RO")
    RO.add_unit(
        "RO",
        capex_keys="capital_cost",
        fixed_opex_keys="fixed_operating_cost",
    )
    pumps = PsCostingGroup("Pumps")
    pumps.add_unit(
        "pump",
        capex_keys="capital_cost",
        flow_from_data_manager={
            "electricity": [
                ("stage 1", "pump_work_expr"),
                ("stage 2", "pump_work_expr"),
            ]
        },
    )
    erd = PsCostingGroup("ERD")
    erd.add_unit(
        "ERD",
        capex_keys="capital_cost",
        flow_keys={"electricity": "control_volume.work"},
    )

    pkg = WaterTapCostingPackage()
    pkg.register_product_flow()
    pkg.add_validation("LCOW", file_key="fs.costing.LCOW", rtol=1e-4)
    cm = PsCostingManager(dm, pkg, [RO, pumps, erd])
    cm.build()
    # Verify total LCOW matches the reference via the total key
    dkey = (("add_erd", "True"), ("stage_sim_cases", "2_stage_2_pump"))
    total_lcow = dm[(*dkey, ("costing", "total", "LCOW"))].data
    ref_lcow = dm[(*dkey, ("costing", "validation", "LCOW"))].data
    mask = np.isfinite(total_lcow) & np.isfinite(ref_lcow)
    assert np.any(mask), "No finite values to compare"
    np.testing.assert_allclose(
        np.asarray(total_lcow)[mask],
        np.asarray(ref_lcow)[mask],
        rtol=1e-4,
    )


_ccro_h5_file = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "ccro_recovery_sweep_analysisType_PW_recovery_sweep.h5",
)


def test_complex():
    dm = PsDataManager()
    dm.register_data_file(
        _ccro_h5_file,
    )

    dm.register_data_key("costing.LCOW", "LCOW", assign_units="USD/m^3")
    dm.register_data_key("avg_feed_flow_rate", "Average feed flow rate")
    dm.register_data_key("avg_product_flow_rate", "Average product flow rate", "L/hr")
    dm.register_data_key("filtration_ramp_rate", "Filtration ramp rate", "bar/min")
    dm.register_data_key("total_cycle_time", "Total cycle time", "min")

    # we will manually calculate the average pump power, since the data is stored in a time series, and we want to calculate the average over the cycle time
    for t in range(25):

        dm.register_data_key(
            f"operation_time_points[{t}]",
            (t, "Operation Time Points"),
            conversion_factor=1 / 60,
            assign_units="min",
        )
        dm.register_data_key(
            f"blocks[{t}].process.fs.P1.control_volume.work[0.0]",
            (
                t,
                "Pump 1 Power",
            ),
            "kW",
        )
        dm.register_data_key(
            f"blocks[{t}].process.fs.P2.control_volume.work[0.0]",
            (
                t,
                "Pump 2 Power",
            ),
            "kW",
        )

    dm.load_data()

    fs_keys = dm.get_expression_keys()
    fs_keys.print_mapping()
    # Calculating fractional operational time
    for t in range(25):
        if t == 0:
            dm.register_expression(
                fs_keys[(0, "Operation Time Points")] / fs_keys["Total cycle time"],
                (t, "fractional_time"),
                assign_units="dimensionless",
            )
        else:
            dm.register_expression(
                (
                    fs_keys[(t, "Operation Time Points")]
                    - fs_keys[(t - 1, "Operation Time Points")]
                )
                / fs_keys["Total cycle time"],
                (t, "fractional_time"),
                assign_units="dimensionless",
            )
    dm.evaluate_expressions()
    # getting tolal power for each pump
    p1_power = 0
    p2_power = 0
    for t in range(25):
        p1_power += fs_keys[(t, "Pump 1 Power")] * fs_keys[(t, "fractional_time")]
        p2_power += fs_keys[(t, "Pump 2 Power")] * fs_keys[(t, "fractional_time")]

    dm.register_expression(p1_power, "Total Pump 1 Power")  # , assign_units="kW")
    dm.register_expression(p2_power, "Total Pump 2 Power")  # , assign_units="kW")
    dm.evaluate_expressions()
    dm.display()

    # lets create costing pacakage
    package = WaterTapCostingPackage(
        costing_block="costing", validation_key="costing.LCOW"
    )
    package.register_product_flow("avg_product_flow_rate")

    # Lets create our groups
    RO = PsCostingGroup("RO")
    RO.add_unit(
        "blocks[0].process.fs.RO",  # only adding "block[0] to specify wher capex is, normally acn just say "RO
        capex_keys="capital_cost",
        fixed_opex_keys="fixed_operating_cost",
    )
    feed_pump = PsCostingGroup("Feed pump")
    feed_pump.add_unit(
        "blocks[19].process.fs.P1",
        capex_keys="capital_cost",
        flow_from_data_manager={"electricity": "Total Pump 1 Power"},
    )
    recycle_pump = PsCostingGroup("Recycle pump")
    recycle_pump.add_unit(
        "blocks[19].process.fs.P2",
        capex_keys="capital_cost",
        flow_from_data_manager={"electricity": "Total Pump 2 Power"},
    )
    conduit = PsCostingGroup("Conduit")
    conduit.add_unit(
        "conduit",
        capex_keys="capital_cost",
    )

    cm = PsCostingManager(dm, package, [RO, feed_pump, recycle_pump, conduit])
    cm.build()
    total_lcow = dm[("costing", "total", "LCOW")].data
    ref_lcow = dm[("costing", "validation", "LCOW")].data
    mask = np.isfinite(total_lcow) & np.isfinite(ref_lcow)
    assert np.any(mask), "No finite values to compare"
    np.testing.assert_allclose(
        np.asarray(total_lcow)[mask],
        np.asarray(ref_lcow)[mask],
        rtol=1e-4,
    )
