from socket import socket, AF_INET, SOCK_STREAM, timeout, SHUT_RDWR
from time import sleep


class Commander:
    def __init__(self, ip, port=1000):
        self.ip = ip
        self.port = port

    def _recv(self, sock):
        response = b""
        while 1:
            try:
                res = sock.recv(256)
                response += res
                if response.endswith(b"\r\n") or response.endswith(b"\n\r"):
                    break
            except timeout:
                print("timed out on receive")
                break
        return response

    def _transact(self, cmd):

        cmd = cmd.encode("utf-8")
        print("cmd: ", cmd)

        sock = socket(AF_INET, SOCK_STREAM)
        sock.settimeout(1)

        try:
            sock.connect((self.ip, self.port))
        except timeout:
            print("timed out on connect")
            return ("", "")

        greeting = self._recv(sock)

        sock.send(cmd)
        response = self._recv(sock)

        sock.shutdown(SHUT_RDWR)

        return (greeting, response)

    def cmd_md(self, card: int, onoff: int):
        """
        power on/off for card/module
        md0 for all cards, md1...md10 (question, md10 or mda?)
        """
        assert card in range(11)
        assert onoff in (0, 1)
        return self._transact(f"< ms FF00 md{card:X} 1 {onoff} L\r")

    def cmd_ep(self, card: int, onoff: int):
        """
        power on/off for all HV modules on cards
        """
        assert card in range(11)
        assert onoff in (0, 1)
        return self._transact(f"< ms {card:02X}00 ep 1 {onoff} L\r")

    def cmd_p(self, card: int, hv: int):
        """
        set high voltage value for all HV modules on a card
        """
        assert card in range(11)
        assert hv >= 1 and hv <= 320
        return self._transact(f"< ms {card:02X}00 p 1 {hv} L \r")

    def cmd_en(self, card: int, ch: int, onoff: int):
        """
        turn on/off HV output (question: does this command actually start ramp up/down)
        """
        assert card in range(11)
        assert ch in range(1, 19)
        assert onoff in (0, 1)
        return self._transact(f"< ms {card:02X}{ch:02X} en 1 {onoff} L \r")

    def cmd_sv(self, card: int, ch: int, hv: int):
        """
        set high voltage value for a single module (channel) on a card
        ch = 0 -> all channels on a card (question: is ch -> 0 not the same as cmd_p?)
        """
        assert card in range(11)
        assert ch in range(1, 19)
        assert hv >= 1 and hv <= 320
        return self._transact(f"< ms {card:02X}{ch:02X} sv 1 {hv} L \r")

    def cmd_rva(self, card: int):
        """
        read all channels voltage
        """
        assert card in range(11)
        return self._transact(f"< ms {card:02X}01 rva 1 0 L \r")

    def cmd_ria(self, card: int):
        """
        read all channels current
        """
        assert card in range(11)
        return self._transact(f"< ms {card:02X}01 ria 1 0 L \r")

    def cmd_plw(self, card: int, ch: int, onoff: int):
        assert(card in range(11))
        assert(ch in range(4))
        assert(onoff in (0,1))
        return self._transact(f"< ms {card:02X}{ch:02X} plw 1 {onoff} L \r")

    def cmd_plr(self, card: int, ch: int):
        assert(card in range(11))
        assert(ch in range(4))
        return self._transact(f"< ms {card:02X}{ch:02X} plr 1 L \r")

    def cmd_mds(self):
        return self._transact(f"< ms FF00 mds 1 1 L\r\n")


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("ip")
    parser.add_argument("cmd_name")
    parser.add_argument("cmd_args", nargs="*", type=int)
    parser.add_argument("--port", default=1000)

    args = parser.parse_args()

    commander = Commander(args.ip, port=args.port)
    f = commander.__getattribute__(args.cmd_name)
    greeting, response = f(*args.cmd_args)
    print(f"greeting ({len(greeting)} bytes): ", greeting)
    print(f"response ({len(response)} bytes): ", response)
