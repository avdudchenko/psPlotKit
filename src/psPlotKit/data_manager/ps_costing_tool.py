from psPlotKit.util import logger
import numpy as np
import quantities as qs
from psPlotKit.data_manager.ps_data import PsData

__author__ = "Alexander V. Dudchenko (SLAC)"

_logger = logger.define_logger(__name__, "PsCosting")


class PsCosting:
    def __init__(
        self,
        psManager,
        costing_block="fs.costing",
        costing_key="costing",
        default_flow="fs.product.properties[0.0].flow_vol_phase[Liq]",
        include_indirect_in_device_costs=True,
    ):
        self.default_costing_block = costing_block
        self.costing_key = costing_key
        self.psManager = psManager
        self.default_flow = default_flow
        self.define_device_energy_pars()
        self.default_costing()
        self.USD = qs.UnitQuantity("USD")
        self.fixed_operating_cost_ref = ["fixed_operating_cost"]
        self.include_indirect_in_device_costs = include_indirect_in_device_costs

    def default_costing(self):
        self.default_costing_params = {
            "utilization_factor": {},
            "load_factor": {},
            "specific_energy_consumption": {},
            "factor_total_investment": {},
            "factor_maintenance_labor_chemical": {},
            "factor_capital_annualization": {},
            "capital_recovery_factor": {},
            "maintenance_labor_chemical_factor": {},
            "electricity_cost": {},
            "TIC": {},
            "TPEC": {},
            self.default_flow: {"units": "m**3/year"},
            "LCOW": {"assign_units": "USD/m**3"},
        }

    def define_device_energy_pars(self, device_dict=None):
        self.default_device_work_keys = ["control_volume.work[0.0]"]

    def define_groups(self, groups):
        self.costed_groups = {}
        self.expected_units = {"CAPEX": [], "OPEX": []}
        for group, items in groups.items():
            self.costed_groups[group] = {
                "CAPEX": {},
                "OPEX": {},
                "block_name": items.get("block_name"),
            }
            for ct in ["CAPEX", "OPEX"]:
                if "units" in items:
                    if isinstance(items["units"], str):
                        units = [items["units"]]

                    else:
                        units = items["units"]
                    self.expected_units[ct] = self.expected_units[ct] + list(units)
                    self.costed_groups[group][ct] = units
                elif ct in items:
                    if isinstance(items[ct]["units"], str):
                        units = [items[ct]["units"]]
                    else:
                        units = items[ct]["units"]
                    self.expected_units[ct] = self.expected_units[ct] + list(units)
                    self.costed_groups[group][ct] = units
                else:
                    self.costed_groups[group][ct] = []

        self.costing_group_keys = {}

    def get_costing_data(self, PsDataManager):
        self.get_costing_block_data()
        self.PsDataManager = PsDataManager
        self.PsDataManager.load_data(self.costing_block_keys, exact_keys=True)
        self.unique_directory_keys = self.PsDataManager.directory_keys
        # print(self.unique_directory_keys)
        # for key in self.PsDataManager.keys():
        #     print(key)
        self.calculate_costs()

    def normalize_cost(self, cost):
        flow_total = (
            self.global_costs[self.default_flow]
            * self.global_costs["utilization_factor"]
        )
        levelized_cost = cost / flow_total
        return levelized_cost

    def calculate_costs(self):
        for udir in self.unique_directory_keys:
            self.get_global_cost(udir)
            sum_ltotal = None
            sum_lpex = None
            sum_lcapex = None
            sum_opex = None
            sum_capex = None
            sum_total = None
            sum_total_indirect = None
            sum_levelized_indirect = None
            for group, cost_breakdown in self.costed_groups.items():
                capex = self.get_device_cost(
                    cost_breakdown["CAPEX"], udir, "CAPEX", cost_breakdown["block_name"]
                )
                opex = self.get_device_cost(
                    cost_breakdown["OPEX"], udir, "OPEX", cost_breakdown["block_name"]
                )
                if capex is not None and opex is not None:
                    if "factor_maintenance_labor_chemical" in self.global_costs:
                        factor_maintenance_labor_chemical = self.global_costs[
                            "factor_maintenance_labor_chemical"
                        ]
                    elif "maintenance_labor_chemical_factor" in self.global_costs:
                        factor_maintenance_labor_chemical = self.global_costs[
                            "maintenance_labor_chemical_factor"
                        ]
                    indirect_cost = capex * factor_maintenance_labor_chemical
                    if sum_total_indirect is None:
                        sum_total_indirect = indirect_cost
                    else:
                        sum_total_indirect += indirect_cost
                    if self.include_indirect_in_device_costs:
                        opex = opex + indirect_cost
                if "factor_capital_annualization" in self.global_costs:
                    factor_capital_annualization = self.global_costs[
                        "factor_capital_annualization"
                    ]
                elif "capital_recovery_factor" in self.global_costs:
                    factor_capital_annualization = self.global_costs[
                        "capital_recovery_factor"
                    ]
                anualized_capex = capex * factor_capital_annualization
                if self.include_indirect_in_device_costs:
                    total = anualized_capex + opex
                else:
                    total = anualized_capex + opex + indirect_cost
                lcapex = self.normalize_cost(anualized_capex)
                lopex = self.normalize_cost(opex)
                lindirect = self.normalize_cost(indirect_cost)
                if sum_levelized_indirect is None:
                    sum_levelized_indirect = lindirect
                else:
                    sum_levelized_indirect += lindirect
                if self.include_indirect_in_device_costs:
                    ltotal = lcapex + lopex
                else:
                    ltotal = lcapex + lopex + lindirect
                if sum_ltotal is None:
                    sum_ltotal = ltotal
                    sum_lpex = lopex
                    sum_lcapex = lcapex
                    sum_opex = opex
                    sum_capex = anualized_capex / factor_capital_annualization.magnitude
                    sum_total = total
                else:
                    sum_ltotal = sum_ltotal + ltotal
                    sum_lpex = sum_lpex + lopex
                    sum_lcapex = sum_lcapex + lcapex
                    sum_opex = sum_opex + opex
                    sum_capex = (
                        sum_capex
                        + anualized_capex / factor_capital_annualization.magnitude
                    )
                    sum_total = total + sum_total
                self.PsDataManager.add_data(
                    udir,
                    ("cost_breakdown", group, "Absolute", "CAPEX"),
                    PsData(
                        "capex",
                        "cost_tool",
                        capex.magnitude,
                        "USD",
                        data_label="Annual cost",
                    ),
                )
                self.PsDataManager.add_data(
                    udir,
                    ("cost_breakdown", group, "Annualized", "CAPEX"),
                    PsData(
                        "capex",
                        "cost_tool",
                        anualized_capex.magnitude,
                        "USD/year",
                        data_label="Annual cost",
                    ),
                )
                self.PsDataManager.add_data(
                    udir,
                    ("cost_breakdown", group, "Absolute", "OPEX"),
                    PsData(
                        "opex",
                        "cost_tool",
                        opex.magnitude,
                        "USD/year",
                        data_label="Annual cost",
                    ),
                )
                self.PsDataManager.add_data(
                    udir,
                    ("cost_breakdown", group, "INDIRECT"),
                    PsData(
                        "indirect_cost",
                        "cost_tool",
                        indirect_cost.magnitude,
                        "USD/year",
                        data_label="Annual cost",
                    ),
                )
                self.PsDataManager.add_data(
                    udir,
                    ("cost_breakdown", group, "TOTAL"),
                    PsData(
                        "total",
                        "cost_tool",
                        total.magnitude,
                        "USD/year",
                        data_label="Annual cost",
                    ),
                )

                self.PsDataManager.add_data(
                    udir,
                    ("cost_breakdown", group, "levelized", "CAPEX"),
                    PsData(
                        "levelized_capex",
                        "cost_tool",
                        lcapex.magnitude,
                        "USD/m**3",
                        data_label="LCOW",
                    ),
                )
                self.PsDataManager.add_data(
                    udir,
                    ("cost_breakdown", group, "levelized", "INDIRECT"),
                    PsData(
                        "levelized_indirect_cost",
                        "cost_tool",
                        lindirect.magnitude,
                        "USD/m**3",
                        data_label="LCOW",
                    ),
                )
                self.PsDataManager.add_data(
                    udir,
                    ("cost_breakdown", group, "levelized", "OPEX"),
                    PsData(
                        "levelized_opex",
                        "cost_tool",
                        lopex.magnitude,
                        "USD/m**3",
                        data_label="LCOW",
                    ),
                )
                self.PsDataManager.add_data(
                    udir,
                    ("cost_breakdown", group, "levelized", "TOTAL"),
                    PsData(
                        "levelized_total",
                        "cost_tool",
                        ltotal.magnitude,
                        "USD/m**3",
                        data_label="LCOW",
                    ),
                )
            # print(sum_total_indirect.magnitude)
            # assert false
            self.PsDataManager.add_data(
                udir,
                ("cost_breakdown", "INDIRECT", "INDIRECT_TOTAL"),
                PsData(
                    "indirect_cost",
                    "cost_tool",
                    indirect_cost.magnitude,
                    "USD/year",
                    data_label="Annual cost",
                ),
            )
            self.PsDataManager.add_data(
                udir,
                ("cost_breakdown", "INDIRECT", "levelized", "INDIRECT_TOTAL"),
                PsData(
                    "levelized_indirect_cost",
                    "cost_tool",
                    sum_levelized_indirect.magnitude,
                    "USD/m**3",
                    data_label="LCOW",
                ),
            )
            if len(sum_ltotal[sum_lcapex == sum_lcapex]) > 1:
                error = np.nanmax(np.abs(self.global_costs["LCOW"] - sum_ltotal)) > 0.01
                if error:
                    _logger.warning("Manually calculated LCOW differs from h5 LCOW!")
                    _logger.warning(
                        "h5file LCOW is {}".format(self.global_costs["LCOW"])
                    )
                    _logger.warning("calculated LCOW is {}".format(sum_ltotal))
                    _logger.warning(
                        "Likely error is missed device key, or missed fixed operating cost"
                    )
                    _logger.warning(
                        "Current key words for fixed_operating_cost_ref are {}".format(
                            self.fixed_operating_cost_ref
                        )
                    )

    def get_global_cost(self, udir):
        udir = self.PsDataManager._dir_to_tuple(udir)
        self.global_costs = {}
        for key in self.loaded_costing_pars:
            data = self.PsDataManager.get_data(udir, key)
            self.global_costs[
                key.replace("{}.".format(self.default_costing_block), "")
            ] = data.udata

    def check_key_block_in_key(self, block, test_key, d_key):
        d_split = d_key.split(".")
        for i, sub_key in enumerate(d_split[:-1]):
            if block == sub_key and sub_key != test_key:
                return True
            elif sub_key == test_key:
                if f"{block}.{test_key}" == f"{sub_key}.{d_split[i+1]}":
                    # print(block, sub_key, d_key, test_key)
                    return True
                else:
                    print(f"{block}.{test_key}", f"{sub_key}.{d_split[i+1]}")
        return False

    def get_device_cost(self, device_keys, udir, cost_type, block_name=None):
        data_sum = None
        udir = self.PsDataManager._dir_to_tuple(udir)
        # print("import request", device_keys, cost_type)
        # print(device_keys, self.costed_devices)
        # assert False
        for device in device_keys:
            if isinstance(device_keys, dict):
                block_name = device_keys.get(device, None)
            for fs_device in self.costed_devices:
                if device == fs_device:
                    for d_key in self.costed_devices[fs_device][cost_type]:
                        get_data = True
                        if (
                            block_name != None
                            and self.check_key_block_in_key(block_name, device, d_key)
                            == False
                        ):
                            # print(
                            #     "Block name {} not in key {}".format(block_name, d_key)
                            # )
                            get_data = False

                        if get_data:
                            # print(block_name,fs_device, d_key)
                            try:
                                sdata = self.PsDataManager.get_data(udir, d_key)
                                if "USD" not in sdata.sunits:
                                    data = sdata.udata.rescale(qs.W)
                                    data = data * qs.year
                                    data = data.rescale(qs.kWh)
                                    data = data * self.global_costs["electricity_cost"]
                                    data = (
                                        data.rescale(self.USD)
                                        / qs.year
                                        # * self.global_costs["utilization_factor"]
                                    )
                                    # print(data)
                                elif "USD/year" in sdata.sunits and cost_type == "OPEX":
                                    data = (
                                        sdata.udata
                                        # * self.global_costs["utilization_factor"]
                                    )
                                else:
                                    data = sdata.udata
                                if cost_type == "OPEX":
                                    # make sure current d_key is not a fixed_opertaing_cost
                                    fixed_check = all(
                                        [
                                            key_option in d_key
                                            for key_option in self.fixed_operating_cost_ref
                                        ]
                                    )
                                    if fixed_check == False:
                                        # print(d_key)
                                        data = (
                                            data
                                            * self.global_costs["utilization_factor"]
                                        )
                                # else:
                                #     print(d_key, data)
                                # print(data)
                                if data_sum is None:
                                    data_sum = data
                                else:
                                    data_sum = data_sum + data
                            except KeyError:
                                pass

        if data_sum is None:
            if cost_type == "OPEX":
                data_sum = 0 * self.USD / qs.year
            elif cost_type == "CAPEX":
                data_sum = 0 * self.USD
            # print("cost import error for device {}".format(device_keys))
        # assert False
        return data_sum

    def get_costing_block_data(self):
        self.costing_block_keys = []
        self.loaded_costing_pars = []
        self.costed_devices = {}
        for key in self.psManager.unique_data_keys:

            for sf, config in self.default_costing_params.items():
                if "{}.{}".format(self.default_costing_block, sf) == key or sf == key:
                    key_setup = {"filekey": key, "return_key": sf}
                    key_setup.update(config)
                    self.loaded_costing_pars.append(sf)
                    self.costing_block_keys.append(key_setup)
            if self.default_costing_block not in key and self.costing_key in key:

                skey = key.split(".costing")
                key_device = skey[0]

                device = skey[0].split(".")[-1]
                device = device.split("[")[0]
                if device not in self.costed_devices:
                    self.costed_devices[device] = {
                        "OPEX": [],
                        "CAPEX": [],
                        "UNDEFINED": [],
                    }

                if "capital_cost" in key and "direct_capital_cost" not in key:
                    if (
                        key not in self.costed_devices[device]["CAPEX"]
                        and device in key
                    ):
                        self.costed_devices[device]["CAPEX"].append(key)
                        self.costing_block_keys.append(key)
                elif "fixed_operating_cost" in key:
                    if key not in self.costed_devices[device]["OPEX"] and device in key:
                        self.costed_devices[device]["OPEX"].append(key)
                        self.costing_block_keys.append(key)

                elif device in key:
                    self.costed_devices[device]["UNDEFINED"].append(key)
                    _logger.warning(
                        "{} in device {} is not related to OPEX or CAPEX!".format(
                            device, key
                        )
                    )
                for work_key in self.default_device_work_keys:
                    if (
                        "{}.{}".format(key_device, work_key)
                        in self.psManager.unique_data_keys
                    ):
                        if (
                            "{}.{}".format(key_device, work_key)
                            not in self.costed_devices[device]["OPEX"]
                        ):
                            self.costed_devices[device]["OPEX"].append(
                                "{}.{}".format(key_device, work_key)
                            )
                            self.costing_block_keys.append(
                                "{}.{}".format(key_device, work_key)
                            )
            capex_dev = [device == key for device in self.expected_units["CAPEX"]]
            opex_dev = [device == key for device in self.expected_units["OPEX"]]
            for ct, dev in {"CAPEX": capex_dev, "OPEX": opex_dev}.items():
                if any(dev):
                    device = np.array(self.expected_units[ct])[dev][0]
                    if device in self.costed_devices:
                        if key not in self.costed_devices[device][ct]:
                            self.costed_devices[device][ct].append(key)
                    else:
                        self.costed_devices[device] = {
                            "OPEX": [],
                            "CAPEX": [],
                            "UNDEFINED": [],
                        }
                        self.costed_devices[device][ct] = [key]
                        self.costing_block_keys.append(key)
        # for dev, items in self.costed_devices.items():
        #     print(dev, items)
        # print(self.PsDataManager.keys())

        _logger.info("Found costing block keys {}".format(self.costing_block_keys))
        # _logger.info("Found costing device keys {}".format(self.costed_devices))
        # assert False
        # for device in self.costed_devices:
        #     for gdev in self.costing_groups:
        #         if gdev in device:
        #             self.costing_group[gdev]["CAPEX"] = self.costed_devices[device]
