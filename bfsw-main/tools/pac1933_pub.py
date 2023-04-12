from time import sleep,time
from struct import Struct
import zmq
from fsw_packet_tools import make_header
from serial import Serial
from argparse import ArgumentParser

p = ArgumentParser()
p.add_argument('--port',default='/dev/ttyS0')
args = p.parse_args()

port = Serial(args.port, baudrate=9600, bytesize=8, parity='N', stopbits=1)

ctx = zmq.Context()
sock = ctx.socket(zmq.PUB)
sock.bind('ipc:///tmp/pac1933_pub.ipc')

counter = 0
while 1:
	data = port.read_until(b'STOP')
	if data.startswith(b'START') and data.endswith(b'STOP') and len(data) == 98:
		print('good pac1934 message received')
		header = make_header(6,int(time()),counter,102)
		packet = header + data[5:-4]
		print('packet length is %d' % len(packet))
		sock.send(packet)
		counter += 1
		sleep(0.1)
	else:
		print('BAD pac1934 message!')
