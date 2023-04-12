import dearpygui.dearpygui as dpg
import numpy as np

with dpg.window():
	with dpg.plot():
		dpg.add_plot_axis(dpg.mvXAxis,label='x')
		dpg.add_plot_axis(dpg.mvYAxis,label='y',id='yaxis')
		dpg.add_histogram_series(np.random.uniform(-1,1,1024),min_range=-2,max_range=2,bins=64,parent='yaxis')

dpg.start_dearpygui()
