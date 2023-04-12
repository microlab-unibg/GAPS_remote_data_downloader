import sqlite3
from bfsw.payloads import gapsparse

def fromzmq(url,dbname='gse.db'):
	import zmq
	from time import monotonic,sleep,time
	ctx = zmq.Context()
	sock = ctx.socket(zmq.SUB)
	sock.connect(url)
	sock.subscribe('')
	sock.setsockopt(zmq.RCVTIMEO,1000)
	#set up timeout

	gapsparse.initialize(dbname)

	t0 = monotonic()
	nbytes = 0
	while 1:
		try:
			msg = sock.recv()
			gapsparse.parse(msg)
			nbytes += len(msg)
		except zmq.error.Again:
			pass #timeout
		t = monotonic()
		if (t - t0) > 2:
			t0 = t
			print('time:',time(),'nbytes:',nbytes)
			nbytes = 0

def fromfile():
	print('file reading not yet implemented')

if __name__ == '__main__':
	from argparse import ArgumentParser
	p = ArgumentParser()
	p.add_argument('url',help='either 1) a zmq url like tcp://192.168.37.2 or 2) a file url like file:rawdata.bin')
	p.add_argument('--dbname',default='gsedb.sqlite',help='default is gsedb.sqlite')
	p.add_argument('--db_backend',default='sqlite3',help='DB backend to use, either 1) sqlite3 or 2) postgresql. default is sqlite3')
	p.add_argument('--saveraw',action='store_true',help='set this flag to save raw data, in addition to parsing it to the DB')
	p.add_argument('--tflush',type=float,help='flush interval for DB')
	args = p.parse_args()

	if args.url.startswith('file:'):
		fname = args.url[5:]
		fromfile(fname,args.dbname)
	else:
		fromzmq(args.url,args.dbname)
