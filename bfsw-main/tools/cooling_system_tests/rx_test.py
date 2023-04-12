from socket import socket, AF_INET, SOCK_STREAM, SHUT_RDWR
import numpy as np
from time import sleep

from argparse import ArgumentParser
p = ArgumentParser()
p.add_argument('address')
p.add_argument('port', type=int)
args = p.parse_args()

s = socket(AF_INET,SOCK_STREAM)


try:
    s.connect((args.address,args.port))
    print('connected.')
    while 1:
        data = s.recv(128)
        print(len(data))
except KeyboardInterrupt:
    print('ctrl-c!')
    s.shutdown(SHUT_RDWR)
    s.close()
