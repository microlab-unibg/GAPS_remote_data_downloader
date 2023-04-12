import psutil
from concurrent.futures import ThreadPoolExecutor
from pystemd.systemd1 import Unit
from time import sleep,time
import math
from struct import Struct
import zmq
from socket import gethostname
from fsw_packet_tools import make_header

class WatchedProcess:
	def __init__(self,prtype,name):
		self.prtype = prtype
		self.name = name
		self.pid = 0
		self.pid_changed = False
		self.cpu_percent = -1
		self.mem_percent = -1

	def update_pid(self):
		pid = -1
		if self.prtype == 'systemd':
			try:
				u = Unit(self.name)
				u.load()
				pid = u.Service.MainPID
			except Exception as e:
				print('exception while finding PID for systemd service %s:' % self.name,e)
		else:
			try:
				for p in psutil.process_iter():
					if self.name == p.name():
						pid = p.pid
						break
			except Exception as e:
				print('exception while finding PID for process name %s:' % self.name,e)
		if pid != self.pid:
			 self.pid_changed = True
		else:
			 self.pid_changed = False
		self.pid = pid

	def update_cpu(self,interval):
		percent = -1.0
		try:
			p = psutil.Process(self.pid)
			percent = p.cpu_percent(interval)
		except Exception as e:
			print('exception while measuring CPU usage for %s with PID = ' % (self.name,self.pid),e)
		self.cpu_percent = percent

	def update_mem(self):
		percent = -1.0
		try:
			p = psutil.Process(self.pid)
			percent = p.memory_percent()
		except Exception as e:
			print('exception while measuring memory usage for %s with PID = %d' % (self.name,self.pid),e)
		self.mem_percent = percent

class WatchedProcessManager:
	def __init__(self,watched_processes):
		self.wps = watched_processes
		self.nwps = len(watched_processes)
		assert(self.nwps <= 32)
		self.pad = [255]*(32-self.nwps)
		self.counter = 0
		self.body_formatter = Struct('>IB32B32B')
		self.hostid = 255
		hostname = gethostname()
		if hostname.startswith('gcu'):
			try:
				self.hostid = int(hostname.replace('gcu',''))
			except:
				self.hostid = 255

	def update_pids(self):
		for wp in self.wps:
			wp.update_pid()

	def update_cpu(self,interval=60):
		with ThreadPoolExecutor() as exe:
			exe.map(lambda wp: wp.update_cpu(interval), self.wps, chunksize=32)

	def update_mem(self):
		list(map(lambda wp:wp.update_mem(),self.wps))

	def update(self,interval=60):
		self.update_pids()
		self.update_cpu(interval)
		self.update_mem()
		self.counter += 1

	def percent2byte(self,x):
		'''three cases 1) valid float in range 0-253, maps to range 0-253 2) float is 254+, maps to 254 3) negative (invalid) float maps to 255'''
		if math.isnan(x) or math.isinf(x) or x < 0:
			y = 255
		else:
			y = round(x)
			if y >= 254:
				y = 254
		return y

	def make_packet(self):
		header = make_header(4, int(time()), self.counter, self.body_formatter.size)
		cpu = [self.percent2byte(wp.cpu_percent) for wp in self.wps]
		cpu += self.pad
		mem = [self.percent2byte(wp.mem_percent) for wp in self.wps]
		mem += self.pad
		pidchange = 0
		ip = 0
		for wp in self.wps:
			if wp.pid_changed:
				pidchange |= 1 << ip
			ip += 1
		body = self.body_formatter.pack(*([pidchange,self.nwps] + cpu + mem))
		return header + body
		
		
wps = []
wps.append(WatchedProcess('systemd','ssh.service'))
wps.append(WatchedProcess('systemd','dbus.service'))
wps.append(WatchedProcess('standalone','labjack_pub'))

wpm = WatchedProcessManager(wps)
wpm.update(interval=1)

print('INIT: watched processes: ',['(%s,%d)' % (wp.name,wp.pid) for wp in wps])

ctx = zmq.Context()
sock = ctx.socket(zmq.PUB)
sock.bind('ipc:///tmp/procmon_pub.ipc')

while 1:
	wpm.update(interval=1)
	print(' '.join(['(%s,%s,%.4f,%.4f)' % (wp.name,wp.pid,wp.cpu_percent,wp.mem_percent) for wp in wpm.wps]))
	packet = wpm.make_packet()
	sock.send(packet)
	sleep(1)
