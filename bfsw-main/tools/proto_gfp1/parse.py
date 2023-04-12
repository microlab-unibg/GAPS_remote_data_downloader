from pickle import dump,load
from sys import argv

f = open(argv[1],'rb')
d = f.read()
f.close()
i = 0
packets = []
while 1:
	try:
		assert(d[i+0] == 0x90)
		assert(d[i+1] == 0xEB)
		length = (d[i+7] << 8) | d[i+6]
		length += 16
		packet = d[i:i+length]
		packets.append(packet)
		i += length
	except IndexError:
		print(f'reached end of file, i = {i}')
		break

with open('packets.pickle','wb') as f:
	dump(packets,f)


