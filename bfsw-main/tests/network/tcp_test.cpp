#include <network.hpp>

int main(void)
{
   bfsw::tcp_client client;

   int rc = client.connect_to("127.0.0.1",45118,1000);
   if(rc != 0)
   {
      spdlog::error("connect failed, rc = {}\n",rc);
      return -1;
   }

   rc = client.send_full("hello",100,10);
   if(rc != 0)
   {
      spdlog::error("send failed, rc = {}\n", rc);
      return -2;
   }

   std::string msg = client.recv_until("ACK\r\n", 1);
   spdlog::info("received {}-byte message: {}\n", msg.size(), msg);

   return 0;

}
