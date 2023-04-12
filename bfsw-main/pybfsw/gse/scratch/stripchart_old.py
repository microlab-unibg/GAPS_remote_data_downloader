from PyQt5.QtWidgets import QApplication, QWidget, QLineEdit, QTextEdit, QVBoxLayout, QSplitter, QShortcut
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QColor, QFont, QIcon
from pyqtgraph import GraphicsLayoutWidget, PlotDataItem,mkBrush,mkPen
from collections import OrderedDict
import time
from argparse import ArgumentParser
from subprocess import Popen
import sys
import json
import numpy as np
from datetime import datetime,timezone
from bfsw.gse.terminal import TerminalWidget,CommandParser
#from db_interface import DBInterface
from bfsw.gse.db_interface import DBInterface

def timestring2unix(st):
	assert(len(st) == 13)
	assert(st[6] == '_')
	st = st.replace('_','')
	assert(st.isnumeric())
	y,mo,d,h,mi,s = [int(st[i:i+2]) for i in range(0,12,2)]
	y += 2000
	dt = datetime(y,mo,d,h,mi,s,tzinfo=timezone.utc)
	return dt.timestamp()

class StringSet:
	def __init__(self,*args):
		self.set = set(args)
	def __call__(self,x):
		if x in self.set:
			return x
		else:
			raise KeyError(f'invalid selection: {x} not in {self.set}')

class StripchartWidget(QWidget):
	def __init__(self, par = None, traces = None, json = None, converter_map = None, alias_map = None):
		self.paused = False
		super().__init__()
		self.init_par(par, traces, json)
		self.init_ui()
		if converter_map is None:
			converter_map = {}
		self.converter_map = converter_map
		if alias_map is None:
			alias_map = {}
		self.alias_map = alias_map
		if json != None:
			self.load_json(json)
		self.dbi = None
		self.timer_callback()


	def init_par(self, par = None, traces = None, json = None):
		if not hasattr(self, 'par'):
			self.parfilters = {}
			self.par = {}

		f = {}
		f['mode'] = StringSet('live','history');
		f['refresh'] = float;
		f['dbpath'] = str;
		f['showquery'] = StringSet('t','f');
		f['symbolsize'] = int
		f['dt'] = float
		f['t1'] = float
		f['t2'] = float
		f['width'] = int
		f['height'] = int
		f['traces'] = list
		self.parfilters.update(f)

		self.parameters(['mode', 'live'])
		self.parameters(['refresh', 1.0])
		self.parameters(['dbpath', 'file:gsedb.sqlite?mode=ro'])
		self.parameters(['showquery', 'f'])
		self.parameters(['symbolsize', 8])
		self.parameters(['dt', 1800])
		self.parameters(['t2', time.time()])
		self.parameters(['t1', time.time() - 1800])
		self.parameters(['width', 900])
		self.parameters(['height', 300])
		self.par['traces'] = []

		self.window_name = 'Plot Widget'
		self.console_status = 'shown'
		self.window_color = None

		if par != None:
			for k, v in par.items():
				self.parameters([k, v])

		if json != None:
			self.load_json(json)

		if traces != None:
			colors = 'bgrcmykw'
			i = 0
			for tr in traces:
				try:
					self.add_trace(tr, colors[i])
				except:
					self.add_trace(tr, 'w')
				i += 1

	#TODO connect window close signal to self.close, so that DB is closed if window is click-exited
	def init_ui(self):
		f1k = QShortcut(self)
		f1k.setKey(Qt.Key_F1)
		f1k.activated.connect(self.f1key_callback)

		self.resize(self.par['width'], self.par['height'])
		self.resizeEvent = self.resize_callback

		self.layout = QVBoxLayout(self)
		self.layout.setContentsMargins(1, 1, 1, 1)
		self.layout.setSpacing(1)

		self.glw = GraphicsLayoutWidget(self)
		self.plotlayout = OrderedDict()
		self.pi = []
		self.pdi = {}

		self.splitter = QSplitter(self)
		self.splitter.setOrientation(Qt.Vertical)

		self.tw = TerminalWidget(callback=self.process_cmd)
		self.layout.addWidget(self.splitter)
		self.splitter.addWidget(self.glw)
		self.splitter.addWidget(self.tw.text)
		self.layout.addWidget(self.tw.line)
		self.splitter.setSizes([250, 50])

		self.colors = {'b':'blue', 'g':'green', 'r':'red', 'c':'cyan', 'm':'magenta', 'y':'yellow', 'k':'black', 'w':'white'}
		
		p = CommandParser(prog = 'add', description = 'add a new trace to the plot')
		p.add_argument('name', help = 'the data name, in @alias or table:column form ("add @labjacktemp")')
		p.add_argument('-c', '--color', default = 'w', choices = list('bgrcmykw'), help = 'trace color for StripchartWidget ("add @labjacktemp -c b")')
		p.add_argument('-s', '--symbol', default = 'o', choices = list('otsph+d')+['t1','t2','t3','star'], help = 'trace symbols for StripchartWidget ("add @labjacktemp -s o")')
		p.add_argument('-b', '--bins', type = int, default = 100, help = 'number of bins for HistogramWidget ("add @labjacktemp -b 50")')
		self.tw.add_command(('add', 'a'), p)
		
		p = CommandParser(prog = 'delete', description = 'remove a trace from the plot')
		p.add_argument('name', help = 'the data name, in @alias or table:column form ("del @labjacktemp")')
		self.tw.add_command(('del', 'd'), p)
		
		p = CommandParser(prog = 'clear', description = 'clear all traces')
		self.tw.add_command(('clear', 'c'), p)

		p = CommandParser(prog = 'set', description = 'set plot properties')
		p.add_argument('-c', '--color', choices = ['b', 'g', 'r', 'c', 'm', 'y', 'k', 'w', 'clear'], help = 'outline color of the window, use "clear" to reset ("set -c b")')
		p.add_argument('-s', '--size', nargs = 2, type = int, help = 'desired width and height of the window ("set -s 1200 400")')
		p.add_argument('-t', '--title', type = str, help = 'title of the window ("set -t LABJACKS")')
		p.add_argument('-p', '--param', nargs = 2, help = 'manually change a parameter ("set -p refresh 5")')
		p.add_argument('-v', '--visible', action = 'store_true', help = 'toggle the console visibility ("set -v")')
		self.tw.add_command(('set', 'e'), p)

		p = CommandParser(prog = 'show', description = 'show plot properties')
		p.add_argument('-p', '--params', action = 'store_true', help = 'print HUD parameters ("show -p")')
		p.add_argument('-t', '--tables', action = 'store_true', help = 'print tables from the DB ("show -t")')
		p.add_argument('-c', '--columns', type = str, help = 'print columns from a DB table ("show -c labjack")')
		self.tw.add_command(('show', 'o'), p)
		
		p = CommandParser(prog = 'fork', description = 'spawn another plot window')
		self.tw.add_command('fork', p)
		
		p = CommandParser(prog = 'save', description = 'save this plot configuration')
		p.add_argument('fname', help = 'filename of the new configuration ("save example.cfg")')
		self.tw.add_command('save', p)
		
		p = CommandParser(prog = 'load', description = 'load a plot configuration')
		p.add_argument('fname', help = 'filename of the saved configuration ("load example.cfg")')
		self.tw.add_command('load', p)

		p = CommandParser(prog = 'help', description = 'print the help statement')
		self.tw.add_command('help', p)

		p = CommandParser(prog = 'exit', description = 'exit the plot')
		self.tw.add_command('exit', p)
		self.tw.create_completer()

		#update timer
		self.timer = QTimer(self)
		self.timer.setSingleShot(True)
		self.timer.timeout.connect(self.timer_callback)


	def update(self):
		self.update_data()
		self.redraw()


	def timer_callback(self):
		if self.par['mode'] == 'live' and self.paused == False:
			self.update()
		self.resize(self.par['width'], self.par['height'])
		self.timer.setInterval(int(self.par['refresh']*1000))
		self.timer.start()


	def process_cmd(self,a):
		cmd = a.cmd_name
		if cmd == 'add':
			self.add_trace(a.name, a.color, a.symbol, a.bins)
			self.update()
		elif cmd == 'delete':
			self.del_trace(a.name)
			self.update()
		elif cmd == 'clear':
			self.clear_traces()
			self.update()
		elif cmd == 'set':
			if a.color != None or a.size != None or a.title != None:
				self.change_window(a.color, a.size, a.title)
			if a.param != None:
				self.parameters(a.param)
				self.update_data()
			if a.visible != None:
				if self.console_status == 'shown':
					self.console_status = 'hidden'
					self.tw.text.hide()
					return			
				if self.console_status == 'hidden':
					self.console_status = 'shown'
					self.tw.text.show()
					return
		elif cmd == 'show':
			if a.params != None:
				self.log(f'INFO: {self.par}')
			if a.tables != None:
				self.show_tables()
			if a.columns != None:
				self.show_columns(a.columns)
		elif cmd == 'fork':
			self.fork()
		elif cmd == 'save':
			self.save_json(a.fname)
		elif cmd == 'load':
			self.load_json(a.fname)
			self.update()
		elif cmd == 'help':
			self.help()
		elif cmd == 'exit':
			self.close()
		else:
			self.log(f'WARN: ignoring command {cmd}')


	def add_trace(self, name, color, symbol, bins):
		for tr in self.par['traces']:
			if tr['name'] == name:
				self.log(f'WARN: already plotting {name}')
				return
		tr = {'name':name, 'color':color, 'symbol':symbol, 'bins':bins}
		self.par['traces'].append(tr)


	def del_trace(self, name):
		d = None
		for tr in self.par['traces']:
			if tr['name'] == name:
				d = tr
				break
		if d is None:
			self.log(f'ERROR: no trace with name = {name} found')
		else:
			self.par['traces'].remove(d)


	def clear_traces(self):
		self.par['traces'] = []
		self.window_name = 'Plot Widget'
		self.window_color = 'clear'
		self.change_window(self.window_color, None, None)


	def change_window(self, color, size, title):
		if color == 'clear':
			self.glw.setStyleSheet('')
			self.window_color = None
		elif color != None:
			color = self.colors[color]
			self.glw.setStyleSheet(f'border: 4px solid \'{color}\'')
			self.window_color = color

		if size != None:
			self.resize(size[0], size[1])

		if title != None:
			self.window_name = title


	#TODO handle case where t1 and t2 are unix timestamp floats
	def history_plot(self, times):
		t1 = times[0]
		t2 = times[1]
		t1 = timestring2unix(t1)
		if '_' in t2:
			t2 = timestring2unix(t2)
		else:
			if t2[0] == '+':
				t2 = t1 + float(t2)
			elif t2[0] == '-':
				t2 = t1
				t1 = t2 + float(t2)
			else:
				r = float(t2)
				t2 = t1 + (r/2)
				t1 = t1 - (r/2)
		self.parameters(['t1', t1])
		self.parameters(['t2', t2])
		if self.par['mode'] == 'live':
			self.parameters(['mode', 'history'])


	def show_console(self):
		self.console_status = 'shown'
		self.tw.text.show()


	def hide_console(self):
		self.console_status = 'hidden'
		self.tw.text.hide()


	def parameters(self, param, log = True):
		parameter = param[0]
		value = param[1]
		try:
			self.par[parameter] = self.parfilters[parameter](value)
			if log:
				self.log(f'INFO: {parameter} set to {value}')
		except KeyError:
			if log:
				self.log(f'ERROR: invalid parameter "{parameter}"')


	def show_tables(self):
		try:
			if self.dbi is None:
				self.dbi = DBInterface(self.par['dbpath'])
			tables = self.dbi.get_table_names()
			self.log(f'INFO: table names: {tables}')
		except Exception as e:
			self.log(f'ERROR: exception while getting table names: {repr(e)}')


	def show_columns(self, table):
		try:
			if self.dbi is None:
				self.dbi = DBInterface(self.par['dbpath'])
			schema = self.dbi.get_table_schema(table)
			columns = [t[0] for t in schema]
			self.log(f'INFO: column names: {columns}')
		except Exception as e:
			self.log(f'ERROR: exception while getting column names: {repr(e)}')


	def fork(self):
		try:
			Popen([sys.executable] + sys.argv)
		except Exception as e:
			self.log(f'ERROR: self.fork raised exception: {repr(e)}')


	def save_json(self, fname):
		try:
			with open(fname, 'w') as f:
				dump_data = {'par':self.par, 'console_status':self.console_status, \
				'window_name':self.window_name, 'window_color':self.window_color, \
				'window_size':[self.par['width'], self.par['height']]}
				json.dump(dump_data, f, indent = 4)
			self.log(f'INFO: configuration saved to file {fname}')
			
		except Exception as e:
			self.log(f'ERROR: exception in self.save_json(): {repr(e)}')


	#TODO filter keys
	def load_json(self, fname):
		try:
			with open(fname, 'r') as f:
				dump_data = json.load(f)

				self.par = dump_data['par']
				self.console_status = dump_data['console_status']
				self.window_name = dump_data['window_name']
				self.window_color = dump_data['window_color']
				self.par['width'] = dump_data['window_size'][0]
				self.par['height'] = dump_data['window_size'][1]

				self.resize(self.par['width'], self.par['height'])
				self.splitter.setSizes([self.par['height']-50, 50])

				if self.console_status == 'hidden':
					self.tw.text.hide()
				else:
					self.tw.text.show()

				if self.window_name == 'HUD Widget':
					self.window_name = fname
				self.change_window(self.window_color, None, None)

			self.log(f'INFO: configuration loaded from file {fname}')

		except Exception as e:
			self.log(f'ERROR: exception in self.load_json(): {repr(e)}')


	def help(self):
		self.log(f'Available Commands: \n' + \
			'add / a "name"     (add a new trace to the plot) \n' + \
			'del / d "name"     (remove a trace from the plot) \n' + \
			'clear / c   (clear all traces) \n' + \
			'set / e     (set plot properties) \n' + \
			'show / o     (show plot properties) \n' + \
			'fork / f     (spawn another plot window) \n' + \
			'save / sv "filename"     (save this plot configuration) \n' + \
			'load / l "filename"     (load a plot configuration) \n' + \
			'help / he    (print the help statement) \n' + \
			'exit     (exit the plot) \n \n' + \
			'use the -h flag on any command for optional arguements and examples \n \n' + \
			'use the "show" command to find the names of displayable data \n \n' + \
			'you can load a configuration file from the terminal by using the --json flag \n \n' + \
			'use the up and down keys in the command line to cycle through previous commands \n \n' + \
			'the F1 key will pause and unpause data updates \n')


	def close(self):
		if self.dbi is not None:
			self.dbi.close()
		super().close()
		sys.exit()


	def update_data(self):
		if self.dbi is None:
			self.dbi = DBInterface(self.par['dbpath'])

		mode = self.par['mode']
		self.window_time = time.strftime('%m/%d/%y %H:%M:%S', time.gmtime(time.time()))

		self.data = {}
		self.units = {}
		bad_traces = []
		for tr in self.par['traces']:
			try:
				name = tr['name']
				if name[0] == '@':
					rname = self.alias_map[name]
					table, column = rname.split(':')
					if name in self.converter_map:
						converter = self.converter_map[name]
					elif rname in self.converter_map:
						converter = self.converter_map[rname]
					else:
						converter = lambda y: (y,'raw')
				else:
					table, column = name.split(':')
					if name in self.converter_map:
						converter = self.converter_map[name]
					else:
						converter = lambda y: (y,'raw')

				if mode == 'live':
					t2 = time.time()
					t1 = t2 - self.par['dt']
				else:
					t1, t2 = self.par['t1'], self.par['t2']

				t1fmt = time.strftime('%m/%d/%y %H:%M:%S', time.gmtime(t1))
				t2fmt = time.strftime('%m/%d/%y %H:%M:%S', time.gmtime(t2))
				self.window_time = f'{t1fmt} to {t2fmt}'

				a, sql = self.dbi.time_query1(table, ('gse_time', column), (t1, t2), return_sql = True)
				a = np.array(a, dtype=np.double)
				if len(a):
					if mode == 'live':
						a[:,0] -= time.time()
					a[:,1],unit = converter(a[:,1])
					#apply user supplied offset and scale
				else:
					a = None
					unit = None
					self.log(f'WARN: no data found for {name} in time range')
				self.data[name] = a
				self.units[name] = unit
				if self.par['showquery'] == 't':
					self.log(f'INFO: SQL -> {sql} -> got {len(a)} rows')
			except Exception as e:
				self.log(f'ERROR: removing trace {tr["name"]} due to exception: {repr(e)}')
				bad_traces.append(tr)
				continue

		for tr in bad_traces:
			self.par['traces'].remove(tr)

		self.setWindowTitle(f'{self.window_name} ({self.window_time} UTC)')


	def log(self, s):
		try:
			self.tw.log(s)
		except:
			pass


	def keyPressEvent(self, event):
		key = event.key()
		if self.tw.first_cmd == True:
			if key == Qt.Key_Up:
				self.tw.hist_int -= 1
				if self.tw.hist_int >= (len(self.tw.line_hist)*-1):
					self.tw.line.setText(self.tw.line_hist[self.tw.hist_int])
				else:
					self.tw.hist_int += 1
					self.tw.line.setText(self.tw.line_hist[self.tw.hist_int])
			elif key == Qt.Key_Down:
				self.tw.hist_int += 1
				if self.tw.hist_int < 0:
					self.tw.line.setText(self.tw.line_hist[self.tw.hist_int])
				else:
					self.tw.hist_int = 0
					self.tw.line.setText('')
			else:
				super().keyPressEvent(event)


	def resize_callback(self, event):
		super().resizeEvent(event)
		width, height = self.width(), self.height()
		try:
			self.parameters(['width', width], log = False)
			self.parameters(['height', height], log = False)
		except:
			pass


	def f1key_callback(self):
		if self.paused:
			self.paused = False
			self.log('INFO: data unpaused')
		else:
			self.paused = True
			self.log('INFO: data paused')

	def redraw(self):
		bad_traces = []
		plotlayout = OrderedDict()
		for tr in self.par['traces']:
			try:
				name = tr['name']
				a = self.data[name]
				unit = self.units[name]
				if a is not None:
					#apply user offset and scale
					if unit in plotlayout:
						plotlayout[unit].append(tr)
					else:
						plotlayout[unit] = [tr]
			except Exception as e:
				self.log(f'ERROR: removing trace {tr["name"]} due to exception: {repr(e)}')
				bad_traces.append(tr)
				continue

		#regenerate layout if necessary
		if plotlayout != self.plotlayout:
			self.glw.clear()
			self.pdi = {}
			self.pi = []
			rownum = 1
			pi = None
			for unit,traces in plotlayout.items():
				pi = self.glw.addPlot(row=rownum,col=1)
				lg = pi.addLegend(offset=(-1,-1))
				pi.getAxis('left').setLabel(unit)
				pi.getAxis('bottom').setStyle(showValues=False)
				#pi.getAxis('bottom').setLabel('absolute time/relative time',**{'color':'#FFF','font-size':'8pt'})
				pi.showGrid(x=True,y=True,alpha=1.0)
				rownum += 1
				for tr in traces:
					pdi = PlotDataItem(autoDownSample=True,clipToView=True)
					vb = pdi.getViewBox()
					pi.addItem(pdi)
					lg.addItem(pdi,tr['name'])
					self.pdi[tr['name']] = pdi
				self.pi.append(pi)

			if self.pi:
				if len(self.pi) >= 2:
					for pi in self.pi[:-1]:
						pi.setXLink(self.pi[-1].getViewBox())
				#set up bottom-most x axis
				pi = self.pi[-1]
				ax = pi.getAxis('bottom')
				qf = QFont()
				#qf.setPixelSize(11)
				qf.setPointSize(8)
				ax.setStyle(showValues=True)
				ax.setTickFont(qf)
				ax.setHeight(28) #empirically set on Alex's computer.  check on other machines
				#ax.tickFont = qf
				ax.tickStrings = self.tick_format
			self.plotlayout = plotlayout

		for unit,traces in self.plotlayout.items():
			for tr in traces:
				name,symbol,color = tr['name'],tr['symbol'],tr['color']
				if a is not None:
					self.pdi[name].setData(self.data[name],symbol=symbol,pen=mkPen(color),symbolBrush=mkBrush(color),symbolSize=self.par['symbolsize'])

		if self.pi:
			#causes absolute timestamp to update in live mode
			#this is super bad and hacky. resizeEvent expects the instance passed as ev to have these methods.
			#still not quite working though... relative timestamps are not updating.
			class qqq:
				def oldSize(self):
					return 5
				def newSize(self):
					return 6
			self.pi[-1].getViewBox().resizeEvent(ev=qqq())
			pass

		for tr in bad_traces:
			self.par['traces'].remove(tr)

		self.setWindowTitle(f'{self.window_name} ({self.window_time} UTC)')


	def tick_format(self,values,scale,spacing):
		ret = []
		mode = self.par['mode']
		for t in values:
			if mode == 'live':
				tabs = t + time.time()
			else:
				tabs = t
			tfmt = time.strftime('%y/%m/%d-%H:%M:%S',time.gmtime(tabs))
			if mode == 'live':
				if t < 0:
					v = -t
				else:
					v = t
				h,mod = divmod(v,3600)
				m,mod = divmod(mod,60)
				s = mod
				h,m,s = map(int,(h,m,s))
				r = [tfmt,'\n']
				if t < 0:
					r.append('-')
				r.append(f'{h:02d}:{m:02d}:{s:02d}')
				ret.append(''.join(r))
		return ret

if __name__ == '__main__':
	#from converters import converter_map,alias_map
	from bfsw.payloads.converters import converter_map,alias_map
	import argparse
	parser = argparse.ArgumentParser()
	parser.add_argument('--traces', dest='traces', nargs="*", help='space-delimited list of trace names')
	parser.add_argument('--json', dest='json', help='JSON-formatted configuration file')
	args = parser.parse_args()

	app =QApplication([])
	sc = StripchartWidget(traces=args.traces, json=args.json, converter_map=converter_map,alias_map=alias_map)
	sc.show()
	sc.tw.line.setFocus()
	app.exec_()


