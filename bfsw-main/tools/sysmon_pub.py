from time import sleep,time
sleep(1)
import psutil
from concurrent.futures import ThreadPoolExecutor,TimeoutError
import math
from struct import Struct
import zmq
from socket import gethostname
from fsw_packet_tools import make_header,gethostid

def percent2byte(x):
	'''three cases 1) valid float in range 0-253, maps to range 0-253 2) float is 254+, maps to 254 3) negative (invalid) float maps to 255'''
	if math.isnan(x) or math.isinf(x) or x < 0:
		y = 255
	else:
		y = round(x)
		if y >= 254:
			y = 254
	return y

def temperature2byte(x):
	'''three cases 1) valid float in range -127 to 127, maps to range -127 to 127 2) float is 254+, maps to 254 3) invalid maps to -128'''
	if math.isnan(x) or math.isinf(x):
		y = -128
	else:
		y = round(x)
		if y < -127:
		  y = -127
		elif y > 127:
		  y = 127
		else:
		  pass
	return y

ctx = zmq.Context()
sock = ctx.socket(zmq.PUB)
sock.bind('ipc:///tmp/sysmon_pub.ipc')

interval = 2
max_cores = 16
max_temps = 18
fmt = '>'
fmt += 'B' #host id
fmt += 'B' #valid bitmask
fmt += 'B' #cpu total precent
fmt += 'B' #num cpu's
fmt += 'B' #mem usage
fmt += 'B' #swap usage
fmt += 'I' #uptime (seconds)
fmt += '%dB' % max_cores #cpu per core percent
fmt += '%db' % max_temps #core temps in C
body_formatter = Struct(fmt)

hostid = gethostid()

counter = 0
while 1:

	valid = 0

	#total and per core cpu usage
	with ThreadPoolExecutor() as pool:
		f1 = pool.submit(psutil.cpu_percent,interval=interval)
		f2 = pool.submit(psutil.cpu_percent,interval=interval,percpu=True)
		try:
			cpu_percent_total = f1.result(timeout=2*interval)
			cpu_percent_core =  f2.result(timeout=2*interval)
			valid |= (1 << 0)
		except TimeoutError:
			print('cpu usage measurement timed out')
			cpu_percent_total = -1.
			cpu_percent_core =  [-1.]

	if len(cpu_percent_core) < max_cores:
		cpu_percent_core += [-1.]*(max_cores - len(cpu_percent_core))
	cpu_byte_core = [percent2byte(x) for x in cpu_percent_core][:max_cores]
	cpu_byte_total = percent2byte(cpu_percent_total)

	#number of cpu cores
	try:
		num_cpu = psutil.cpu_count()
		valid |= (1 << 1)
	except Exception as e:
		print('exception while getting cpu count: ',e)
		num_cpu = -1

	#uptime
	try:
		uptime = int(time() - psutil.boot_time()) 
		valid |= (1 << 2)
	except Exception as e:
		print('exception while computing uptime: ',e)
		uptime = 0

	#mem usage
	try:
		mem_usage = percent2byte(psutil.virtual_memory().percent)
		swap_usage = percent2byte(psutil.swap_memory().percent)
		valid |= (1 << 3)
	except Exception as e:
		print('exception while computing memory usage: ',e)
		mem_usage = -1.
		swap_usage = -1.

	#core temps
	try:
		core_temps = [shw.current for shw in psutil.sensors_temperatures()['coretemp']]
		valid |= (1 << 4)
	except Exception as e:
		print('exception while measuring core temperatures: ',e)
		core_temps = [math.nan]
	if len(core_temps) < max_temps:
		core_temps += [math.nan]*(max_temps - len(core_temps))
	core_temp_bytes = [temperature2byte(t) for t in core_temps][:max_temps]

	header = make_header(5,int(time()),counter,body_formatter.size)
	body = body_formatter.pack(*([hostid, valid, cpu_byte_total, num_cpu, mem_usage, swap_usage, uptime] + cpu_byte_core + core_temp_bytes))
	packet = header + body
	sock.send(packet)
	counter += 1
	print('cpu_core:',cpu_percent_core,'% cpu_total:',cpu_percent_total,'uptime:%d' % int(uptime),'mem_usage:',mem_usage,'% swap_usage:',swap_usage,'% core_temps:',core_temps,'C')
	sleep(1)
