from struct import Struct
from socket import gethostname
from time import time

header_formatter = Struct('<3BIHHH')
def make_header(ptype,timestamp,counter,body_length):
	assert((body_length + header_formatter.size) <= 8192)
	return header_formatter.pack(0xeb, 0x90, ptype & 0xff, int(timestamp) & 0xffffffff , counter & 0xffff, (body_length + header_formatter.size) & 0xffff,0)

def gethostid():
	try:
		hostname = gethostname()
		hostid = int(hostname.replace('gcu',''))
	except Exception as e:
		print('exception determining gcu hostname suffix number: ',e)
		hostid = 255
	return hostid

def make_fsw_timestamp():
	'''28 bit timestamp in seconds since 1590086985'''
	'''this will rollover in late September 2028'''
	tref = 1590086985.
	tnow = time()
	dt = int(tnow - tref)
	return dt & 0x0fffffff
