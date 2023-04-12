# this script parses pdu on/off commands,
# puts them in the unified command bytestring format,
# and publishes them to a socket.
# they will be parsed by the script in bfsw/bin/pdu_server.cpp

# for usage, see python3 send_pdu_commands.py -h
# by Field Rogers (fieldr@berkeley.edu)

import sys,zmq
from argparse import ArgumentParser

# arg parser
p = ArgumentParser()
p.add_argument('-a','--zmq_addr',default='tcp://192.168.37.200:48112')
p.add_argument('-p','--pdu',required=True,help="pdu number from 0 to 2",type=int)
p.add_argument('-c','--chan',required=True,help="channel number from 0 to 7",type=int)
p.add_argument('-o','--com',required=True,help="command: 1 to turn on, 0 to turn off",type=int)
p.add_argument('-v','--verbose',action="store_true")
args = p.parse_args()
if (args.verbose): print (args) 

# check that all input is valid and calculate command id
if not args.pdu in range(3):
    print (args.pdu,"is not a valid pdu number")
    sys.exit(1) # should write to sys.sterr
if not args.chan in range(8):
    print (args.chan," is not a valid channel number")
    sys.exit(1) # shoulw write to sys.sterr
if not args.com in range(2):
    print (args.com, "is not a valid on/off command")
    sys.exit(1) # should write to sys.sterr
com_id = args.chan + 8*(1-args.com) + 16*args.pdu
if (args.verbose): print (args.pdu,args.chan,args.com,com_id)

# make the byte array
b = bytearray()
b.append(0xEB)  # byte 0 - fixed SYNC word
b.append(0x90)  # byte 1 - SYNC
b.append(0)     # byte 2 - reserved for CRC
b.append(0)     # byte 3 - reserved for CRC
b.append(0)     # byte 4 - sequence number
b.append(50)    # byte 5 - address for the PDU
b.append(com_id)# byte 6 - command identifier
b.append(0)     # byte 7 - payload length in bytes
#print(b)

# write to pair socket
context = zmq.Context()
socket = context.socket(zmq.PAIR)
socket.connect(args.zmq_addr)

socket.send(b)
