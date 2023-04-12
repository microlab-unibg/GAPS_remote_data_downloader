import zmq
from argparse import ArgumentParser

p = ArgumentParser()
p.add_argument('url')
a = p.parse_args()

context = zmq.Context()
sock = context.socket(zmq.SUB)
sock.connect(a.url)
sock.subscribe('')

while 1:
	message = sock.recv()
	print(len(message))
