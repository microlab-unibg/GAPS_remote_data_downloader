import numpy as np
from time import time,sleep

class TofGen:
	def __init__(self):
		self.maxsize = 2048 - 13
		self.new_body()
		self.events = []
		self.counter = 0
		for i in range(1024):
			pids = list(range(256))
			b = bytearray()
			npaddles = int(10 + np.random.exponential(15))
			if npaddles > 255:
				npaddles = 255
			b.append(npaddles)
			for i in range(npaddles):
				pid = pids[np.random.randint(len(pids))]
				pids.remove(pid)
				b.append(pid)
				timing = np.random.normal(pid*64,16,2).astype(int)
				charge = np.random.normal(pid*128,32,2).astype(int)
				timing[timing < 0] = 0
				timing[timing > 0xffff] = 0xffff
				charge[charge < 0] = 0
				charge[charge > 0xffff] = 0xffff
				t1,t2 = timing
				c1,c2 = charge
				b.append((t1 >> 8) & 255)
				b.append((t1 >> 0) & 255)
				b.append((t2 >> 8) & 255)
				b.append((t2 >> 0) & 255)
				b.append((c1 >> 8) & 255)
				b.append((c1 >> 0) & 255)
				b.append((c2 >> 8) & 255)
				b.append((c2 >> 0) & 255)
			self.events.append(b)

	def new_body(self):
		self.body = bytearray([0])

	def event(self,evid,timestamp):

		b = bytearray()
		b.append((evid >> 24) & 255)
		b.append((evid >> 16) & 255)
		b.append((evid >>  8) & 255)
		b.append((evid >>  0) & 255)
		b.append((timestamp >> 56) & 255)
		b.append((timestamp >> 48) & 255)
		b.append((timestamp >> 40) & 255)
		b.append((timestamp >> 32) & 255)
		b.append((timestamp >> 24) & 255)
		b.append((timestamp >> 16) & 255)
		b.append((timestamp >>  8) & 255)
		b.append((timestamp >>  0) & 255)
		b += self.events[np.random.randint(len(self.events))]

		if (len(self.body) + len(b)) > self.maxsize:
			ret = self.body
			self.new_body()
		else:
			ret = None

		self.body[0] += 1
		self.body += b
		
		return ret

class LayerGen:
	def __init__(self,layer_num):
		self.maxsize = 2048 - 13
		self.layer_num = layer_num
		self.new_body()
		self.events = []
		self.counter = 0
		for i in range(64):
			maxstrips = 12*12*8
			pids = list(range(maxstrips))
			b = bytearray()
			npaddles = int(10 + np.random.exponential(15))
			nstrips = int(np.random.exponential(20))
			if nstrips > maxstrips:
				nstrips = maxstrips
			b.append((nstrips >> 8) & 255)
			b.append((nstrips >> 0) & 255)
			for i in range(nstrips):
				pid = pids[np.random.randint(len(pids))]
				pids.remove(pid)
				b.append((pid >> 8) & 255)
				b.append((pid >> 0) & 255)
				charge = int(np.random.normal(pid,32))
				if charge < 0:
					charge = 0
				elif charge > 0xffff:
					charge = 0xffff
				b.append((charge >> 8) & 255)
				b.append((charge >> 0) & 255)
			self.events.append(b)
	def new_body(self):
		self.body = bytearray([0,self.layer_num])

	def event(self,evid,timestamp):

		b = bytearray()
		b.append((evid >> 24) & 255)
		b.append((evid >> 16) & 255)
		b.append((evid >>  8) & 255)
		b.append((evid >>  0) & 255)
		b.append((timestamp >> 56) & 255)
		b.append((timestamp >> 48) & 255)
		b.append((timestamp >> 40) & 255)
		b.append((timestamp >> 32) & 255)
		b.append((timestamp >> 24) & 255)
		b.append((timestamp >> 16) & 255)
		b.append((timestamp >>  8) & 255)
		b.append((timestamp >>  0) & 255)
		b += self.events[np.random.randint(len(self.events))]

		if (len(self.body) + len(b)) > self.maxsize:
			ret = self.body
			self.new_body()
		else:
			ret = None

		self.body[0] += 1
		self.body += b

		return ret

if __name__ == '__main__':
	import zmq
	ctx = zmq.Context()
	tof_sock = ctx.socket(zmq.PUB)
	tof_sock.bind('tcp://*:41444')
	tracker_sock = ctx.socket(zmq.PUB)
	tracker_sock.bind('tcp://*:41666')
	tof = TofGen()
	layers = [LayerGen(i) for i in range(10)]

	nevents = 1
	tlast = time()
	tstats = time()
	event_counter = 0
	p = 0.1
	n_tof_bytes = 0
	n_tracker_bytes = 0
	while 1:
		sleep(0.1)
		tnow = time()
		timestamps = np.linspace(tlast,tnow,nevents)
		for n in range(nevents):
			t = int(timestamps[n]*1E9)
			r = tof.event(event_counter, t)
			if r is not None:
				tof_sock.send(r)
				n_tof_bytes += len(r)
			player = np.random.uniform(0,1,len(layers))
			for j in range(len(layers)):
				if player[j] < p:
					r = layers[j].event(event_counter,t)
					if r is not None:
						tracker_sock.send(r)
						n_tracker_bytes += len(r)
			event_counter += 1

		if((tnow - tstats) > 5):
			dt = tnow - tstats
			tstats = tnow
			tof_kbps = n_tof_bytes * 8 / (dt*1E3)
			tracker_kbps = n_tracker_bytes * 8 / (dt*1E3)
			print('data rate: %.3f kbps (TOF: %.3f, Tracker: %.3f)' % (tof_kbps + tracker_kbps,tof_kbps,tracker_kbps))
			n_tof_bytes = 0
			n_tracker_bytes = 0
