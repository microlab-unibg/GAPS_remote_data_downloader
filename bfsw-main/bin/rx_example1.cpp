#include <czmq.h>
#include <bfswutil.hpp>
#include <iostream>
#include <string>
#include <tracker.hpp>

int main(int argc, char ** argv)
{
   if(argc != 3)
   {
      std::cout << "1. zmq socket type, \"sub\" or \"pair\"" << std::endl;
      std::cout << "2. zmq address, e.g. ipc:///tmp/data or tcp://127.0.0.1:45654" << std::endl;
      return -1;
   }

   std::string socket_type = argv[1];
   zsock_t *sock;
   if(socket_type == "sub")
   {
      sock = zsock_new_sub(argv[2], "");
   }
   else if(socket_type == "pair")
   {
      sock = zsock_new_pair("");
      zsock_bind(sock,"%s",argv[2]);
   }
   else
   {
      std::cout << "socket type must be \"sub\" or \"pair\"" << std::endl;
      return -1;
   }

   zpoller_t *poller = zpoller_new(sock);

   while(1)
   {
      if(zpoller_wait(poller, 1000) == nullptr)
      {
         if(zpoller_expired(poller))
            continue;
         else
            break;
      }
      else
      {
         zframe_t *frame = zframe_recv(sock);
         int packet_type = zframe_data(frame)[2];
         std::cout << "packet_type: " << packet_type << " length: " << zframe_size(frame) << std::endl;
         if(packet_type == 80)
         {
            tracker::event_packet p;
            bfsw::array_wrapper bytes(zframe_data(frame), zframe_size(frame));
            int rc = p.unpack(bytes, 0);
            if(rc < 0)
            {
               std::cout << "error parsing tracker event packet, rc = " << rc << std::endl;
            }
         }
         zframe_destroy(&frame);
      }
   }

   zsock_destroy(&sock);
   zpoller_destroy(&poller);

   return 0;
}
