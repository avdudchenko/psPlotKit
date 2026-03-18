from psPlotKit.data_manager.ps_costing import PsCostingPackage


class WaterTapCostingPackage(PsCostingPackage):
    def __init__(self, costing_block="fs.costing", validation_key="fs.costing.LCOW"):
        super().__init__(costing_block=costing_block)
        self.costing_package_name = "watertap"

        self.add_parameter("utilization_factor")
        self.add_parameter("total_investment_factor")
        self.add_parameter("capital_recovery_factor")
        self.add_parameter("maintenance_labor_chemical_factor")
        self.add_parameter("electricity_cost")
        self.add_parameter("wacc")
        self.add_parameter("plant_lifetime")
        self.add_flow_cost("electricity", "electricity_cost", units="USD/yr")
        self.add_formula(
            "total_capital_cost",
            lambda ek: ek.aggregate_capital_cost * ek.total_investment_factor,
        )
        self.add_formula(
            "maintenance_labor_chemical_operating_cost",
            lambda ek: ek.aggregate_capital_cost * ek.maintenance_labor_chemical_factor,
        )
        self.add_formula(
            "total_fixed_operating_cost",
            lambda ek: ek.aggregate_fixed_operating_cost
            + ek.maintenance_labor_chemical_operating_cost,
        )
        self.add_formula(
            "total_operating_cost",
            lambda ek: ek.total_fixed_operating_cost
            + ek.aggregate_flow_cost * ek.utilization_factor,
        )
        self.add_formula(
            "total_annualized_cost",
            lambda ek: ek.total_capital_cost * ek.capital_recovery_factor
            + ek.total_operating_cost,
        )
        self.add_validation("LCOW", file_key=validation_key, rtol=1e-4)

    def register_product_flow(
        self, file_key="fs.product.properties[0.0].flow_vol_phase[Liq]"
    ):
        self.add_parameter("product_flow", file_key=file_key)
        self.add_formula(
            "LCOW",
            lambda ek: (ek.total_annualized_cost)
            / (ek.product_flow * ek.utilization_factor),
            units="USD/m**3",
        )
        self.add_formula(
            "LCOW_opex",
            lambda ek: (ek.total_operating_cost)
            / (ek.product_flow * ek.utilization_factor),
            units="USD/m**3",
        )
        self.add_formula(
            "LCOW_capex",
            lambda ek: (ek.total_capital_cost * ek.capital_recovery_factor)
            / (ek.product_flow * ek.utilization_factor),
            units="USD/m**3",
        )
