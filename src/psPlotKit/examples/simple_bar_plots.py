from psPlotKit.data_plotter.fig_generator import figureGenerator

if __name__ == "__main__":
    xdata = ["t1", "f2", "z3"]
    bar_start = [-10, -25, -30]
    bar_length = [20, 40, 50]
    fig = figureGenerator()
    fig.init_figure()
    for i, x in enumerate(xdata):
        fig.plot_bar(i, bar_length[i], bottom=bar_start[i])
    fig.set_axis_ticklabels(xticklabels=xdata, yticks=[-30, 0, 30])
    fig.save_fig("Test")

    fig_h = figureGenerator()
    fig_h.init_figure()
    for i, x in enumerate(xdata):
        fig_h.plot_bar(i, bar_length[i], bottom=bar_start[i], vertical=False)
    fig_h.set_axis_ticklabels(yticklabels=xdata, xticks=[-30, 0, 30])
    fig_h.save_fig("Test")
    fig.show()
