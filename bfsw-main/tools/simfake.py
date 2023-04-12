import yaml
from argparse import ArgumentParser
from time import time,sleep
import numpy as np
import zmq
p = ArgumentParser()
p.add_argument('file')
p.add_argument('sleep',type=float)
args = p.parse_args()

#TODO include sim event number i.e. count1 field in json

class Packet:

	def __init__(self):
		self.packet_counter = 0
		self.size    = 0
		self.chunks  = []
		self.chunkslen = 0
		self.idd = 0

	def make(self):
		b = bytearray()
		b.extend((0xeb,0x90)) #sync
		b.append(self.idd) #tracker layer ID, 255 for TOF
		blen = self.chunkslen + 9
		b.append(blen & 0xff)
		b.append((blen >> 8) & 0xff)
		b.append(self.packet_counter & 0xff)
		b.append((self.packet_counter >> 8) & 0xff)
		evnum = len(self.chunks)
		b.append(evnum & 0xff)
		b.append((evnum >> 8) & 0xff)
		for chunk in self.chunks:
			b.extend(chunk)
		self.packet_counter += 1
		return b

class TrackerPacket(Packet):
	def __init__(self,x):
		super().__init__()
		self.idd = x
	def add(self,event):
		key = self.idd
		if key not in event:
			return None
		hits = event[key]
		b = bytearray()
		b.append(0xAE)
		b.append(0xE0)
		c = event['counter']
		b.append(c & 0xff) #counter
		b.append((c >> 8) & 0xff)
		b.append((c >> 16) & 0xff)
		b.append((c >> 24) & 0xff)
		b.extend((0xEF,0xBE,0,0,0,0,0,0)) #timestamp beefbeefbeefbeef
		b.append(key) #layer
		b.extend((0xEF,0xBE,0xAD,0xDE)) #status deadbeef
		nhits = len(hits)
		b.append(nhits & 0xff) #number of hits
		b.append((nhits >> 8) & 0xff)
		for h in hits:
			strip = h['id']
			b.append(strip & 0xff)
			b.append((strip >> 8) & 0xff)
			b.append(23) #dummy status
			adc = h['adc']
			b.append(adc & 0xff)
			b.append((adc >> 8) & 0xff)
		ret = None
		if (self.chunkslen + len(b)) > 1000:
			ret = self.make()
			self.chunkslen = 0
			self.chunks = []
		self.chunks.append(b)
		self.chunkslen += len(b)
		return ret

class TofPacket(Packet):
	def __init__(self,x):
		super().__init__()
		self.idd = x
	def add(self,event):
		assert('tof' in event)
		hits = event['tof']
		b = bytearray()
		b.append(0xAE) #sync
		b.append(0xE0) #sync
		b.append(201) #beta
		b.append(0)
		b.append(202) #beta error
		b.append(0)
		b.append(204) #primary charge
		b.append(0)
		b.append(206) #primary charge error
		b.append(0)
		c = event['counter']
		b.append(c & 0xff) #event counter
		b.append((c >> 8) & 0xff)
		b.append((c >> 16) & 0xff)
		b.append((c >> 24) & 0xff)
		b.extend([0x07,0,0xAA,0,0,0,0,0]) #timestamp
		b.append(208) #paddle hit pattern
		b.append(len(hits)) #number of paddles
		for h in hits:
			b.append(h['id'])
			b.append(h['t1'])
			b.append(0)
			b.append(h['t2'])
			b.append(0)
			b.append(h['c1'])
			b.append(0)
			b.append(h['c2'])
			b.append(0)
		ret = None
		if (self.chunkslen + len(b)) > 1000:
			ret = self.make()
			self.chunkslen = 0
			self.chunks = []
		self.chunks.append(b)
		self.chunkslen += len(b)
		return ret

with open(args.file) as f:
	events = yaml.load(f)
nevents = len(events)
tlast = time()
nlast = 0
layers = [TrackerPacket(i) for i in range(10)]
tof = TofPacket(10)

ctx = zmq.Context()
tracker_socket = ctx.socket(zmq.PUB)
tracker_socket.bind('tcp://0.0.0.0:30000')
tof_socket = ctx.socket(zmq.PUB)
tof_socket.bind('tcp://0.0.0.0:30001')

event_counter = 0

while 1:
	for i in range(100): #send a hundred events between sleeps
		event = events[np.random.randint(nevents)]
		event['counter'] = event_counter
		event_counter += 1
		for l in layers:
			packet = l.add(event)
			if packet is not None:
				tracker_socket.send(packet)
				nlast += len(packet)
		packet = tof.add(event)
		if packet is not None:
			tof_socket.send(packet)
			nlast += len(packet)
	sleep(args.sleep)
	tnow = time()
	dt = tnow - tlast
	if dt > 2.:
		rate = nlast * 8. / (1E6 * dt)
		print('rate = %.6f megabit/s' % rate)
		nlast = 0
		tlast = tnow
