from pybfsw.common.packet_tools import read_packets
import socket
from argparse import ArgumentParser
from time import sleep
p = ArgumentParser()
p.add_argument('filename')
p.add_argument('--address',default='localhost')
p.add_argument('--port',default=60501)
p.add_argument('--sleep',type=float,default=0.5)
p.add_argument('--batch',type=int,default = 5)
args = p.parse_args()

sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)

packets = read_packets(args.filename)

i = 0
while 1:
	for q in range(args.batch):
		sock.sendto(packets[i % len(packets)][13:],(args.address,args.port))
		i += 1
	sleep(args.sleep)

