from socket import socket, AF_INET, SOCK_DGRAM
import numpy as np
from time import sleep

from argparse import ArgumentParser
p = ArgumentParser()
p.add_argument('file')
p.add_argument('address')
p.add_argument('port', type=int)
args = p.parse_args()

f = open(args.file,'rb')
s = socket(AF_INET,SOCK_DGRAM)

try:
    while 1:
        n = np.random.randint(1,100)
        data = f.read(n)
        if len(data):
            s.sendto(data,(args.address,args.port))
            print(f'sent {n} bytes')
        else:
            f.close()
            f = open(args.file,'rb')
        sleep(np.random.uniform(0.01,0.1))
except KeyboardInterrupt:
    print('ctrl-c!')
    s.shutdown(SHUT_RDWR)
    s.close()
