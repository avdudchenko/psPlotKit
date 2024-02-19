from psPlotKit.data_plotter.ps_break_down_plotter import breakDownPlotter
from psPlotKit.data_plotter.ps_line_plotter import linePlotter
from psPlotKit.data_manager.ps_data_manager import psDataManager

if __name__ == "__main__":
    costing_data = psDataManager("data/bgw_analysis_analysisType_bgw_analysis.h5")
    # costing_data.get_costing_block_data()
    device_groups = {
        "RO": {"units": "ROUnits"},
        "Pumps": {
            "CAPEX": {
                "units": {"PrimaryPumps", "BoosterPumps", "EnergyRecoveryDevices"}
            },
            "OPEX": {
                "units": {"PrimaryPumps", "BoosterPumps", "EnergyRecoveryDevices"}
            },
        },
        # "ERD": {
        #     "CAPEX": {"units": {"EnergyRecoveryDevices"}},
        # },
    }
    costing_data.load_data(
        [
            {
                "filekey": "fs.water_recovery",
                "return_key": "Water recovery",
                "units": "%",
            },
            {
                "filekey": "fs.disposal.properties[0.0].conc_mass_phase_comp[Liq, NaCl]",
                "return_key": "Brine salinity",
                "units": "g/L",
            },
        ]
    )
    costing_data.get_costing(device_groups)
    costing_data.reduce_data(
        stack_keys="number_of_stages", data_key="LCOW", reduction_type="min"
    )
    print(costing_data.keys())
    costing_data.select_data(["stacked_data"], True)
    x_type = {
        "Water recovery": [50, 70, 80, 90],
        "Brine salinity": [
            60,
            100,
            140,
            180,
            220,
            260,
            300,
            340,
        ],
    }
    for x, xticks in x_type.items():
        wr = costing_data.get_selected_data()
        # print(wr15.keys())
        cost_plotter = breakDownPlotter(wr)
        cost_plotter.define_area_groups({"RO": {}, "Pumps": {}})  # , "ERD": {}})
        cost_plotter.define_hatch_groups({"CAPEX": {}, "OPEX": {"hatch": "//"}})
        cost_plotter.plotbreakdown(
            xdata=x,
            ydata=["cost_breakdown", "levelized"],
            axis_options={
                "yticks": [0, 0.5, 1.0, 1.5, 2.0],
                "xticks": xticks,
            },
            generate_plot=False,
        )

        num_stages = costing_data[("stacked_data", "number_of_stages")].data
        brine_salinity = costing_data[("stacked_data", x)].data
        LCOW = costing_data[("stacked_data", "LCOW")].data
        print(num_stages, brine_salinity)

        cost_plotter.fig.plot_line(
            xdata=brine_salinity,
            ydata=LCOW,
            marker_overlay=num_stages,
            color="black",
            markersize=5,
            marker_overlay_labels=[
                "RO",
                "1 stage LSRRO",
                "2 stage LSRRO",
                "3 stage LSRRO",
                "4 stage LSRRO",
                "5 stage LSRRO",
            ],
        )
        cost_plotter.generate_figure()
    # line_plot = linePlotter(wr)
    # line_plot.plot_line(
    #     xdata="Brine salinity",
    #     ydata=["stacked_data", "number_of_stages"],
    #     generate_plot=False,
    # )
    # line_plot.generate_figure()
