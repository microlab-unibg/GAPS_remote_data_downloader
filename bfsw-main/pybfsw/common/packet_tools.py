from struct import Struct
from socket import gethostname
from time import time
import gzip

header_formatter = Struct("<3BIHHH")


def make_header(ptype, timestamp, counter, body_length):
    assert (body_length + header_formatter.size) <= 8192
    return header_formatter.pack(
        0xEB,
        0x90,
        ptype & 0xFF,
        int(timestamp) & 0xFFFFFFFF,
        counter & 0xFFFF,
        (body_length + header_formatter.size) & 0xFFFF,
        0,
    )


def convert_timestamp(t):
    return 1631030675 + t * 64e-3


def parse_header(buf, convert=True):
    fields = header_formatter.unpack(buf)
    d = dict(
        zip(
            ["sync0", "sync1", "ptype", "timestamp", "counter", "length", "checksum"],
            fields,
        )
    )
    if convert:
        d["timestamp"] = convert_timestamp(d["timestamp"])
    return d


def gethostid():
    try:
        hostname = gethostname()
        hostid = int(hostname.replace("gcu", ""))
    except Exception as e:
        print("exception determining gcu hostname suffix number: ", e)
        hostid = 255
    return hostid


def read_packets(fname):
    if fname.endswith(".bin.gz"):
        with gzip.open(fname, "r") as f:
            data = f.read()
    else:
        assert fname.endswith(".bin")
        with open(fname, "rb") as f:
            data = f.read()

    packets = []
    i = 0
    while 1:
        try:
            if i == len(data):
                print(f"reached end of file {fname}")
                break
            header = header_formatter.unpack(data[i : i + header_formatter.size])
            if header[0] == 0xEB and header[1] == 0x90:
                length = header[5]
                # sock.send(data[i:i+length])
                packets.append(data[i : i + length])
                i += length
            else:
                print("lost sync, looking for next 0xeb90...")
                ii = data.find(b"\xeb\x90")
                if ii == -1:
                    print("no more eb90's found")
                    break
                else:
                    i = ii
        except Exception as e:
            print("unhandled exception: ", e, " .... skipping the rest of this file")
            break
    return packets
