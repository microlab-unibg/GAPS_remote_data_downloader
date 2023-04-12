import dearpygui.dearpygui as dpg
import numpy as np
from time import time

parameters = []
ctrl = {'pressed':False,'list':[]}
plots = []
n = 128

def make_plot(name):
	sname = f'series_{name}'
	if dpg.does_item_exist(sname):
		return
	with dpg.window(label=name,width=100,height=100,on_close=lambda x: dpg.delete_item(x)):
		with dpg.plot(height=-1,width=-1):
			dpg.add_plot_axis(dpg.mvXAxis, label='x')
			yaxisname = f'yaxis_{name}'
			dpg.add_plot_axis(dpg.mvYAxis, label='y',id=yaxisname)
			dpg.add_line_series(np.arange(n),np.random.normal(size=n),parent=yaxisname,id=sname)
			plots.append(sname)

def callback_timer():
	for p in plots:
		if dpg.does_item_exist(p):
			dpg.set_value(p,[np.arange(128) + 128,np.random.normal(size=n)])
		else:
			plots.remove(p)

		
def callback_click(sender,data,user_data):
	print('you clicked',dpg.get_item_alias(sender))
	name = dpg.get_item_alias(sender)
	if ctrl['pressed']:
		if name not in ctrl['list']:
			ctrl['list'].append(dpg.get_item_alias(name))
	else:
		make_plot(name)

def make_buttons():
	for p in parameters:
		dpg.add_button(label=p,id=p,before='input',callback=callback_click)

def clear_buttons():
	for p in parameters:
			dpg.delete_item(p) 

def callback_text(sender,data):
	p = dpg.get_value("input")
	dpg.set_value('input','')
	dpg.focus_item('input')
	if p and p not in parameters:
		clear_buttons()
		parameters.append(p)
		make_buttons()

def callback_ctrlpress(sender,data,user_data):
	if (data == 341) or (data == 345):
		if not ctrl['pressed']:
			ctrl['pressed'] = True
			ctrl['list'] = []

def callback_ctrlrelease(sender,data,user_data):
	if (data == 341) or (data == 345):
		ctrl['pressed'] = False
		print(ctrl)

with dpg.window(label='window',id='primwindow',width=100,autosize=True):
	with dpg.handler_registry():
		dpg.add_key_press_handler(callback=callback_ctrlpress)
		dpg.add_key_release_handler(callback=callback_ctrlrelease)
	dpg.add_input_text(id='input',callback=callback_text,on_enter=True,label='command',width=100)
	dpg.focus_item('input')

dpg.set_primary_window('primwindow',True)
dpg.setup_viewport()
dpg.set_viewport_title('minigse')
dpg.set_viewport_width(100)
dpg.set_viewport_height(100)

ti = dpg.get_total_time()
while dpg.is_dearpygui_running():
	tf = dpg.get_total_time()
	if(tf - ti) > 1:
		ti = tf
		callback_timer()
	dpg.render_dearpygui_frame()
