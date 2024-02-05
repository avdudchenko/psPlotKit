import pytest
import os
from psPlotKit.data_manager.data_importer import psDataImport

__author__ = "Alexander V. Dudchenko (SLAC)"

_this_file_path = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def get_data():
    return psDataImport(os.path.join(_this_file_path, "test_file.h5"))


def test_data_importer(get_data):
    datamanager = (
        get_data  # psDataImport(os.path.join(_this_file_path, "test_file.h5"))
    )
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
            "unique_directory": ["pressure_exchanger", "membrane_cost"],
        },
        "ro_analysis/erd_type/pressure_exchanger/membrane_group": {
            "outputs": ["LCOW"],
            "solve_successful": ["solve_successful"],
            "sweep_params": [
                "fs.costing.reverse_osmosis.factor_membrane_replacement",
                "fs.costing.reverse_osmosis.membrane_cost",
            ],
            "unique_directory": ["pressure_exchanger", "membrane_group"],
        },
        "ro_analysis/erd_type/pump_as_turbine/membrane_cost": {
            "outputs": ["LCOW"],
            "solve_successful": ["solve_successful"],
            "sweep_params": ["fs.costing.reverse_osmosis.membrane_cost"],
            "unique_directory": ["pump_as_turbine", "membrane_cost"],
        },
        "ro_analysis/erd_type/pump_as_turbine/membrane_group": {
            "outputs": ["LCOW"],
            "solve_successful": ["solve_successful"],
            "sweep_params": [
                "fs.costing.reverse_osmosis.factor_membrane_replacement",
                "fs.costing.reverse_osmosis.membrane_cost",
            ],
            "unique_directory": ["pump_as_turbine", "membrane_group"],
        },
    }
    for key, sub_dict in expected_file_index.items():
        for sub_key, sub_item in sub_dict.items():
            for i, v in enumerate(sub_item):
                assert sub_item[i] == datamanager.file_index[key][sub_key][i]
    expected_contents = ["outputs", "solve_successful", "sweep_params"]
    for i, key in enumerate(datamanager.sub_contents):
        assert key == expected_contents[i]


def test_getting_data(get_data):
    data_manager = get_data

    all_lcow = data_manager.get_data(["LCOW"])

    assert pytest.approx(
        all_lcow["pressure_exchanger:membrane_cost"]["LCOW"].data, 1e-2
    ) == [
        0.41994862,
        0.42486556,
        0.42978251,
        0.43469945,
        0.43961639,
    ]

    close_key = data_manager.get_data(["reverse_osmosis.factor_membrane_replacement"])
    print(close_key)
    assert pytest.approx(
        close_key["pressure_exchanger:membrane_cost"][
            "fs.costing.reverse_osmosis.membrane_cost"
        ].data,
        1e-1,
    ) == [20.0, 22.5, 25.0, 27.5, 30.0]

    data_manager.directory_keys = ["pressure_exchanger", "membrane_cost"]
    specific_directory = data_manager.get_data(
        ["reverse_osmosis.factor_membrane_replacement"]
    )
    print(specific_directory)
    assert pytest.approx(
        specific_directory["pressure_exchanger:membrane_cost"][
            "fs.costing.reverse_osmosis.membrane_cost"
        ].data,
        1e-1,
    ) == [20.0, 22.5, 25.0, 27.5, 30.0]

    assert "pump_as_turbine:membrane_group" not in specific_directory
