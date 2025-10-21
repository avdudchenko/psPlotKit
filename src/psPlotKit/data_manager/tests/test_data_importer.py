import pytest
import os
from psPlotKit.data_manager.data_importer import PsDataImport

__author__ = "Alexander V. Dudchenko (SLAC)"

_this_file_path = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def get_data():
    return PsDataImport(os.path.join(_this_file_path, "test_file.h5"))


def test_data_importer(get_data):
    datamanager = get_data
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
            "unique_directory": [("erd_type", "pressure_exchanger"), "membrane_cost"],
            "outputs": {"data_keys": ["LCOW"]},
            "solve_successful": {"data_keys": ["solve_successful"]},
            "sweep_params": {"data_keys": ["fs.costing.reverse_osmosis.membrane_cost"]},
        },
        "ro_analysis/erd_type/pressure_exchanger/membrane_group": {
            "unique_directory": [("erd_type", "pressure_exchanger"), "membrane_group"],
            "outputs": {"data_keys": ["LCOW"]},
            "solve_successful": {"data_keys": ["solve_successful"]},
            "sweep_params": {
                "data_keys": [
                    "fs.costing.reverse_osmosis.factor_membrane_replacement",
                    "fs.costing.reverse_osmosis.membrane_cost",
                ]
            },
        },
        "ro_analysis/erd_type/pump_as_turbine/membrane_cost": {
            "unique_directory": [("erd_type", "pump_as_turbine"), "membrane_cost"],
            "outputs": {"data_keys": ["LCOW"]},
            "solve_successful": {"data_keys": ["solve_successful"]},
            "sweep_params": {"data_keys": ["fs.costing.reverse_osmosis.membrane_cost"]},
        },
        "ro_analysis/erd_type/pump_as_turbine/membrane_group": {
            "unique_directory": [("erd_type", "pump_as_turbine"), "membrane_group"],
            "outputs": {"data_keys": ["LCOW"]},
            "solve_successful": {"data_keys": ["solve_successful"]},
            "sweep_params": {
                "data_keys": [
                    "fs.costing.reverse_osmosis.factor_membrane_replacement",
                    "fs.costing.reverse_osmosis.membrane_cost",
                ]
            },
        },
    }
    print(datamanager.file_index)
    for key, sub_dict in expected_file_index.items():
        for sub_key, sub_item in sub_dict.items():
            assert sub_item == datamanager.file_index[key][sub_key]
    expected_contents = ["outputs", "solve_successful", "sweep_params"]
    for i, key in enumerate(datamanager.sub_contents):
        assert key == expected_contents[i]


# def test_getting_data(get_data):
#     data_manager = get_data

#     all_lcow = data_manager.get_data(["LCOW"])
#     print(all_lcow)
#     got_lcow = {}
#     for key, d in all_lcow.items():
#         got_lcow[key] = d.data
#         # got_lcow = all_lcow[d]["LCOW"].data
#     expected_dict = {
#         ((("erd_type", "pressure_exchanger"), "membrane_cost"), "LCOW"): [
#             0.41994862,
#             0.42486556,
#             0.42978251,
#             0.43469945,
#             0.43961639,
#         ],
#         ((("erd_type", "pressure_exchanger"), "membrane_group"), "LCOW"): [
#             0.424438,
#             0.42711026,
#             0.42978251,
#             0.4288205,
#             0.43175997,
#             0.43469945,
#             0.43320299,
#             0.43640969,
#             0.43961639,
#         ],
#         ((("erd_type", "pump_as_turbine"), "membrane_cost"), "LCOW"): [
#             0.60846028,
#             0.61337722,
#             0.61829417,
#             0.62321111,
#             0.62812806,
#         ],
#         ((("erd_type", "pump_as_turbine"), "membrane_group"), "LCOW"): [
#             0.61294966,
#             0.61562192,
#             0.61829417,
#             0.61733216,
#             0.62027163,
#             0.62321111,
#             0.62171465,
#             0.62492135,
#             0.62812806,
#         ],
#     }
#     for key, d in all_lcow.items():
#         assert pytest.approx(d.data, 1e-2) == expected_dict[key]

#     close_key = data_manager.get_data(["reverse_osmosis.factor_membrane_replacement"])

#     got_lcow = {}
#     for key, d in close_key.items():
#         got_lcow[key] = d.data
#     print(got_lcow)
#     expected_lcow = {
#         (
#             (("erd_type", "pressure_exchanger"), "membrane_cost"),
#             "fs.costing.reverse_osmosis.membrane_cost",
#         ): [20.0, 22.5, 25.0, 27.5, 30.0],
#         (
#             (("erd_type", "pressure_exchanger"), "membrane_group"),
#             "fs.costing.reverse_osmosis.factor_membrane_replacement",
#         ): [0.15, 0.175, 0.2, 0.15, 0.175, 0.2, 0.15, 0.175, 0.2],
#         (
#             (("erd_type", "pump_as_turbine"), "membrane_cost"),
#             "fs.costing.reverse_osmosis.membrane_cost",
#         ): [20.0, 22.5, 25.0, 27.5, 30.0],
#         (
#             (("erd_type", "pump_as_turbine"), "membrane_group"),
#             "fs.costing.reverse_osmosis.factor_membrane_replacement",
#         ): [0.15, 0.175, 0.2, 0.15, 0.175, 0.2, 0.15, 0.175, 0.2],
#     }
#     for key, d in close_key.items():
#         assert pytest.approx(d.data, 1e-2) == expected_lcow[key]

#     test_idx = "fs.RO1.ro_retentate_translator.properties_out[0.0].flow_mass_phase_comp[Liq,Ca]"
#     index_list, index_str = data_manager.get_key_indexes(test_idx)
#     print(index_list, index_str)
#     assert index_list == [0.0, "Liq", "Ca"]
#     assert index_str == "0.0,Liq,Ca"
#     test_idx = "fs.RO1.ro_retentate_translator.properties_out.flow_mass_phase_comp"
#     index_list, index_str = data_manager.get_key_indexes(test_idx)
#     print(index_list, index_str)
#     assert index_list == None
#     assert index_str == None
