import zmq
from argparse import ArgumentParser
p = ArgumentParser()
p.add_argument('url')
args = p.parse_args()
ctx = zmq.Context()
s = ctx.socket(zmq.SUB)
s.connect(args.url)
s.subscribe('')

while 1:
	d = s.recv()
	print(d)
