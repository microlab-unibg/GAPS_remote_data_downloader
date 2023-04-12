import zmq
from argparse import ArgumentParser
p = ArgumentParser()
p.add_argument('url')
p.add_argument('sopath')
args = p.parse_args()
ctx = zmq.Context()
s = ctx.socket(zmq.SUB)
s.connect(args.url)
s.subscribe('')

from sys import path
path.append(args.sopath)
import gaps_science_formats1_wrap as gaps

while 1:
	b = s.recv()
	mep = gaps.MergedEventPacket()
	rc = mep.Deserialize(b,len(b),0)
	print("rc = %d" % rc)
	if(rc < 0):
		print('error rc = %d' % rc)
	else:
		nevents = mep.GetNEvents()
		for i in range(nevents):
			me = mep.GetEvent(i)
			hits = gaps.tracker_hits(me)
			print(hits)
