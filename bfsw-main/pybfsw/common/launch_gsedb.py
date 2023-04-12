from argparse import ArgumentParser
from os import mkdir, chdir
from os.path import expandvars,expanduser
from subprocess import Popen
from time import sleep


p = ArgumentParser()
p.add_argument('--path',default='~/gsedb',help='path to directory where the gsedb SQLite will be opened')
p.add_argument('--zmq_address',default='tcp://127.0.0.1:55555',help='ZeroMQ address where packets are being published') 
p.add_argument('--bin_path',default='~/bfsw/build/bin/gsedb')
args = p.parse_args()

def expand(s):
	return expanduser(expandvars(s))

full_path = expand(args.path)

try:
	mkdir(full_path)
	print(f'created directory {full_path}')
except FileExistsError:
	print(f'directory {full_path} already exists')

try:
	chdir(full_path)
	print(f'changed to directory {full_path}')
except Exception as E:
	print('exception while trying to chdir: ',E)
	raise E

while 1:
	sleep(0.1)
	try:
		pipe = Popen(f'{args.bin_path} {args.zmq_address}',shell=True)
		print('launched gsedb')
		ret = pipe.wait()
		print(f'gsedb exited and returned {ret}')
	except KeyboardInterrupt:
		break
	except Exception as E:
		print('caught exception while running gsedb: ',E)
		print('restarting gsedb')

