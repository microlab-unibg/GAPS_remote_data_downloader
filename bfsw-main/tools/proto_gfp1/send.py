from pickle import load
import socket
from time import sleep

with open('packets.pickle','rb') as f:
	packets = load(f)

sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)

i = 0
while 1:
	for q in range(3):
		sock.sendto(packets[i % len(packets)],('localhost',47779))
		i += 1
	sleep(0.5)
