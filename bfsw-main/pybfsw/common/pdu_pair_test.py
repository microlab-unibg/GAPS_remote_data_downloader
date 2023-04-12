#establish connection
import zmq
ctx = zmq.Context()
sock = ctx.socket(zmq.PAIR)
sock.bind("ipc:///tmp/pdu_serial_relay")

while 1:
    data = sock.recv()
    print(data)
    sock.send(b"GOTCHA ACK\r\n");

