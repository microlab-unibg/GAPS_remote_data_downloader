from argparse import ArgumentParser
p = ArgumentParser()
p.add_argument('glob')
p.add_argument('--address',default='ipc:///tmp/gsedbpair')
p.add_argument('--sleep',type=float,default=0.0)
args = p.parse_args()

#get filenames
import glob
fnames = glob.glob(args.glob)
fnames.sort()

#establish connection
import zmq
ctx = zmq.Context()
sock = ctx.socket(zmq.PAIR)
sock.connect(args.address)

import gzip
import time
from pybfsw.common.packet_tools import header_formatter

for fname in fnames:
	if fname.endswith('.bin.gz'):
		with gzip.open(fname,'r') as f:
			data = f.read()
	else:
		assert(fname.endswith('.bin'))
		with open(fname,'rb') as f:
			data = f.read()

	i = 0
	while 1:
		try:
			if i == len(data):
				print(f'reached end of file {fname}')
				break
			header = header_formatter.unpack(data[i:i+header_formatter.size])
			if header[0] == 0xEB and header[1] == 0x90:
				length = header[5]
				sock.send(data[i:i+length])
				if args.sleep != 0:
					time.sleep(args.sleep)
				i += length
			else:
				print('lost sync, looking for next 0xeb90...')
				ii = data.find(b'\xeb\x90')
				if ii == -1:
					print('no more eb90\'s found')
					break
				else:
					i = ii
		except Exception as e:
			print('unhandled exception: ',e,' .... skipping the rest of this file')
			break
