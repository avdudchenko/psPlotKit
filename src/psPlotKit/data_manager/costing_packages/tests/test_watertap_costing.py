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


# def test_with_custom_expressions():
#     dm = PsDataManager(_h5_file)
#     dm.register_data_key(
#         "fs.stage[1].pump.control_volume.work[0.0]", ("stage 1", "pump_work")
#     )
#     dm.register_data_key(
#         "fs.stage[2].pump.control_volume.work[0.0]", ("stage 2", "pump_work")
#     )
#     dm.load_data()
#     ek = dm.get_expression_keys()
#     dm.register_expression(ek.stage_1_pump_work * 1.0, ("stage 1", "pump_work_expr"))
#     dm.register_expression(ek.stage_2_pump_work * 1.0, ("stage 2", "pump_work_expr"))
#     RO = PsCostingGroup("RO")
#     RO.add_unit(
#         "RO",
#         capex_keys="capital_cost",
#         fixed_opex_keys="fixed_operating_cost",
#     )
#     pumps = PsCostingGroup("Pumps")
#     pumps.add_unit(
#         "pump",
#         capex_keys="capital_cost",
#         flow_from_data_manager={
#             "electricity": [
#                 ("stage 1", "pump_work_expr"),
#                 ("stage 2", "pump_work_expr"),
#             ]
#         },
#     )
#     erd = PsCostingGroup("ERD")
#     erd.add_unit(
#         "ERD",
#         capex_keys="capital_cost",
#         flow_keys={"electricity": "control_volume.work"},
#     )

#     pkg = WaterTapCostingPackage()
#     pkg.register_product_flow()
#     pkg.add_validation("LCOW", file_key="fs.costing.LCOW", rtol=1e-4)
#     cm = PsCostingManager(dm, pkg, [RO, pumps, erd])
#     cm.build()
#     # Verify total LCOW matches the reference via the total key
#     dkey = (("add_erd", "True"), ("stage_sim_cases", "2_stage_2_pump"))
#     total_lcow = dm[(*dkey, ("costing", "total", "LCOW"))].data
#     ref_lcow = dm[(*dkey, ("costing", "validation", "LCOW"))].data
#     mask = np.isfinite(total_lcow) & np.isfinite(ref_lcow)
#     assert np.any(mask), "No finite values to compare"
#     np.testing.assert_allclose(
#         np.asarray(total_lcow)[mask],
#         np.asarray(ref_lcow)[mask],
#         rtol=1e-4,
#     )
