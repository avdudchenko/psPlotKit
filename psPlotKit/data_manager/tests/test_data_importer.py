import pytest
import os
from psPlotKit.data_manager.data_importer import waterTAP_dataImport

__author__ = "Alexander V. Dudchenko (SLAC)"

_this_file_path = os.path.dirname(os.path.abspath(__file__))


def test_data_importer():
    datamanager = waterTAP_dataImport(os.path.join(_this_file_path, "test_file.h5"))
    expected_dirs = [
        "ro_analysis/erd_type/pressure_exchanger/membrane_cost",
        "ro_analysis/erd_type/pressure_exchanger/membrane_group",
        "ro_analysis/erd_type/pump_as_turbine/membrane_cost",
        "ro_analysis/erd_type/pump_as_turbine/membrane_group",
    ]
    for f_dir in datamanager.directories:
        assert f_dir in expected_dirs
    expected_file_index = {
        "ro_analysis/erd_type/pressure_exchanger/membrane_cost": {
            "outputs": ["LCOW"],
            "solve_successful": ["solve_successful"],
            "sweep_params": ["fs.costing.reverse_osmosis.membrane_cost"],
        },
        "ro_analysis/erd_type/pressure_exchanger/membrane_group": {
            "outputs": ["LCOW"],
            "solve_successful": ["solve_successful"],
            "sweep_params": [
                "fs.costing.reverse_osmosis.factor_membrane_replacement",
                "fs.costing.reverse_osmosis.membrane_cost",
            ],
        },
        "ro_analysis/erd_type/pump_as_turbine/membrane_cost": {
            "outputs": ["LCOW"],
            "solve_successful": ["solve_successful"],
            "sweep_params": ["fs.costing.reverse_osmosis.membrane_cost"],
        },
        "ro_analysis/erd_type/pump_as_turbine/membrane_group": {
            "outputs": ["LCOW"],
            "solve_successful": ["solve_successful"],
            "solve_successful": ["solve_successful"],
            "sweep_params": [
                "fs.costing.reverse_osmosis.factor_membrane_replacement",
                "fs.costing.reverse_osmosis.membrane_cost",
            ],
        },
    }
    for key, sub_dict in expected_file_index.items():
        for sub_key, sub_item in sub_dict.items():
            for i, v in enumerate(sub_item):
                assert sub_item[i] == datamanager.file_index[key][sub_key][i]
