import dearpygui.dearpygui as dpg
import numpy as np
from pybfsw.gse.gsequery import GSEQuery
from pybfsw.payloads.gaps import parameter_bank
from time import time

dpg.create_context()
dpg.create_viewport(title='stripchart',width=600,height=500)

q = GSEQuery(parameter_bank=parameter_bank)

def callback_timer():
	tnow = time()
	t,y,par = q.time_query3('@asictemp_r0m1',tnow - 120,tnow)
	if not dpg.does_item_exist('series'):
		dpg.add_line_series(t-tnow,y,parent='yaxis1',tag='series')
		dpg.fit_axis_data('yaxis1')
		dpg.fit_axis_data('xaxis')
	dpg.set_value('series',[t-tnow,y])

with dpg.window(tag='window',width=600,height=500):
	with dpg.plot(tag='plot',width=-1,height=-1):
		dpg.add_plot_axis(dpg.mvXAxis,label='x',tag='xaxis')
		dpg.add_plot_axis(dpg.mvYAxis,label='y',tag='yaxis1')

dpg.setup_dearpygui()
dpg.show_viewport()
dpg.set_primary_window('window',True)
ti = dpg.get_total_time()
while dpg.is_dearpygui_running():
	tf = dpg.get_total_time()
	if(tf - ti) > 1:
		ti = tf
		callback_timer()
	dpg.render_dearpygui_frame()
dpg.destroy_context()
