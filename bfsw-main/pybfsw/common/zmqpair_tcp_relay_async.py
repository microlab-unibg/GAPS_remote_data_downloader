import asyncio
from zmq import PAIR
from zmq.asyncio import Context
from argparse import ArgumentParser
p = ArgumentParser()
p.add_argument('tcp_addr')
p.add_argument('tcp_port',type=int)
p.add_argument('zmq_addr')
args = p.parse_args()

async def main():
   tcp_reader, tcp_writer = await asyncio.open_connection(args.tcp_addr,args.tcp_port)
   ctx = Context()
   zmq_socket = ctx.socket(PAIR)
   zmq_socket.bind(args.zmq_addr)
   count = {'zmq':0, 'tcp':0}
   async def tcp():
      while 1:
         data = await tcp_reader.read(2048)
         sz = len(data)
         if sz == 0:
            raise IOError('tcp read returned zero bytes')
         zmq_socket.send(data)
         count['tcp'] += len(data)
   async def zmqq():
      while 1:
         data = await zmq_socket.recv()
         tcp_writer.write(data)
         count['zmq'] += len(data)
   async def hkp():
      while 1:
         print(count)
         await asyncio.sleep(1)

   await asyncio.gather(tcp(),zmqq(),hkp())

asyncio.run(main())

