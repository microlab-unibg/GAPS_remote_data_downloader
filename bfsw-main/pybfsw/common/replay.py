from time import monotonic, sleep
from glob import glob
from zmq import Context, PUB, LINGER, NOBLOCK
from struct import Struct
from argparse import ArgumentParser
from pybfsw.common.packet_tools import read_packets, parse_header

p = ArgumentParser()
p.add_argument('glob')
p.add_argument('--fastmode',action='store_true')
p.add_argument('--addr',default="ipc:///tmp/pybfsw_replay_pub")
args = p.parse_args()
ctx = Context()
sock = ctx.socket(PUB)
sock.set_hwm(0)
sock.bind(args.addr)
sleep(1)

fnames = glob(args.glob)
fnames.sort()
for fname in fnames:
    packets = read_packets(fname)
    h = parse_header(packets[0][:13])
    t_start = h['timestamp']
    t_offset = monotonic()

    for packet in packets:
        if args.fastmode:
            sock.send(packet,flags=NOBLOCK)
        else:
            h = parse_header(packet[:13])
            t_packet = h['timestamp']
            while 1:
                t_now = t_start + (monotonic() - t_offset)
                if t_packet <= t_now:
                    print(h)
                    sock.send(packet)
                    break
                else:
                    sleep(0.020)

ctx.destroy()
