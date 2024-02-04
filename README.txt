This is a toolkit for plotting data generated using Paramter sweep toll

To install download repo:
Create conda env if desired 
(1) conda create -n myenv python=3.9
(2) In the psPlotKit directory run 
    pip install -r requirments.txt 

(3) Use either the direct api or the panel holoviz UI 
    start ui by going into psPlotKit directory and running 
    panel serve ui/ui.py --show 
in cmd: python setup.py develop

to use:
from analysis_plot_kit.core import fig_generator, data_import
