from socket import *
sock = socket(AF_INET, SOCK_STREAM)
sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
sock.bind(("127.0.0.1",45118))
sock.listen(1)

ss, addr = sock.accept()
print(addr)
data = ss.recv(2048)
ss.send(data + b'ACK\r\n')
ss.shutdown(SHUT_RDWR)
ss.close()


sock.close()
