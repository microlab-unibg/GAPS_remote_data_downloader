#include <czmq.h>
#include <string>
#include <bfswutil.hpp>
#include <spdlog/spdlog.h>
#include <network.hpp>
#include <pdu.hpp>
#include <cmd.hpp>
#include <stdlib.h>

// TODO: publish command ack
// TODO: migrate to new version of recv_until
// TODO: handle case where recv_until returns too many bytes: truncate the message to size, or parse the byte stream

class app
{
   private: //members

      zsock_t *cmd_sub;
      zsock_t *data_pub;
      std::string serial_server_ip;
      int serial_server_port;
      int hkp_packet_counter = 0;

   private: //methods

      int cmd_callback()
      {
         zframe_t *frame = zframe_recv(cmd_sub);
         bfsw::command cmd;
         int rc = cmd.unpack(bfsw::array_wrapper(zframe_data(frame), zframe_size(frame)), 0);
         zframe_destroy(&frame);

         if( (rc == 0) && (cmd.address == 50) )
         {
            spdlog::info("COMMAND ID: {}", cmd.command_id);
            switch(cmd.command_id)
            {
               case 0:
                  pdu_onoff(0, 0, 1);  break;
               case 1:
                  pdu_onoff(0, 1, 1);  break;
               case 2:
                  pdu_onoff(0, 2, 1);  break;
               case 3:
                  pdu_onoff(0, 3, 1);  break;
               case 4:
                  pdu_onoff(0, 4, 1);  break;
               case 5:
                  pdu_onoff(0, 5, 1);  break;
               case 6:
                  pdu_onoff(0, 6, 1);  break;
               case 7:
                  pdu_onoff(0, 7, 1);  break;
               case 8:
                  pdu_onoff(0, 0, 0);  break;
               case 9:
                  pdu_onoff(0, 1, 0);  break;
               case 10:
                  pdu_onoff(0, 2, 0);  break;
               case 11:
                  pdu_onoff(0, 3, 0);  break;
               case 12:
                  pdu_onoff(0, 4, 0);  break;
               case 13:
                  pdu_onoff(0, 5, 0);  break;
               case 14:
                  pdu_onoff(0, 6, 0);  break;
               case 15:
                  pdu_onoff(0, 7, 0);  break;
               case 200:
                  timer_callback();  break;
               default:
                  spdlog::warn("invalid command id {}", cmd.command_id);
            }
         }
         else
         {
            spdlog::warn("cmd_callback(): bad command, cmd.serialize() returned rc = {} (should be 0), and cmd.address is {} (should be 50)", rc, cmd.address);
         }

         return 0;
      }

      std::string pdu_onoff(int pdu_id, int pdu_ch, int onoff)
      {
         std::string request = fmt::format("{} {}{} {}{}\r\n", onoff ? "pduon" : "pduoff", pdu_id, pdu_id, pdu_ch, pdu_ch);

         bfsw::tcp_client client;
         int rc = client.connect_to(serial_server_ip, serial_server_port, 1000); //fix API, take double as timeout parameter
         if(rc != 0)
         {
            spdlog::warn("pdu_ononff(): failed to connect");
            return "";
         }
         rc = client.send_full(request, 100, 10); //fix API, take double as timeout parameter
         if(rc != 0)
         {
            spdlog::warn("pdu_onoff(): failed to send request");
            return "";
         }

         std::string response = client.recv_until("ACK\r\n", 1.0);
         spdlog::info("pdu_onoff(): received {} bytes: {}", response.size(), response); 
         //TODO publish cmd ack
         return response;
      }


      static int cmd_callback_wrap(zloop_t *zloop, zsock_t *sock, void *arg)
      {
         return static_cast<app*>(arg)->cmd_callback();
      }

      std::string get_hkp(int pdu_id)
      {
         std::string request = fmt::format("hkp {}{}\r\n", pdu_id, pdu_id);
         bfsw::tcp_client client;

         int rc = client.connect_to(serial_server_ip, serial_server_port, 1000);
         if(rc != 0)
         {
            spdlog::warn("get_hkp(): failed to connect");
            return "";
         }

         rc = client.send_full(request, 100, 10);
         if(rc != 0)
         {
            spdlog::warn("get_hkp(): failed to send request");
            return "";
         }

         return client.recv_until("ACK\r\n", 1.0);
      }



      int verify_hkp(std::string& msg)
      {
         const int expected_size = 205;
         if(msg.size() != expected_size)
         {
            spdlog::warn("verify_hkp(): hkp message is {} bytes, not {}", msg.size(), expected_size);
            return -1;
         }
         bool good = true;
         good = good && (static_cast<uint8_t>(msg[0]) == 0xaa);
         good = good && (msg[msg.size() - 5] == 'A');
         good = good && (msg[msg.size() - 4] == 'C');
         good = good && (msg[msg.size() - 3] == 'K');
         good = good && (msg[msg.size() - 2] == '\r');
         good = good && (msg[msg.size() - 1] == '\n');
         if(good)
            return 0;
         else
            return -2;
      }
         
      int timer_callback()
      {
         std::vector<int> pdu_ids = {0};
         for(auto id : pdu_ids)
         {
            auto reply = get_hkp(id);
            spdlog::info("received {}-byte message from pdu_id {}", reply.size(), id);
            int rc = verify_hkp(reply);
            if(rc == 0)
            {
               auto packet = bfsw::make_packet_stub(50, hkp_packet_counter++, 0, 0);
               for(auto b : reply)
                  packet.push_back(static_cast<uint8_t>(b));
               int rc = bfsw::set_header_length_field(packet, packet.size());
               zframe_t *frame = zframe_new(packet.data(), packet.size());
               zframe_send(&frame, data_pub, 0);
            }
            else
            {
               spdlog::warn("timer_callback(): failed to verify hkp packet, rc = {}", rc);
            }
         }
         return 0;
      }

      static int timer_callback_wrap(zloop_t *zloop, int timer_id, void *arg)
      {
         return static_cast<app*>(arg)->timer_callback();
      }

   public: //methods

      app(int argc, char **argv)
      {
         if(argc != 5)
         {
            fmt::print("1. cmd address (zmq sub)\n");
            fmt::print("2. data address (zmq pub)\n");
            fmt::print("3. ip address of serial server\n");
            fmt::print("4. port of serial server\n");
            exit(-1);
         }

         cmd_sub = zsock_new_sub("","");
         assert(cmd_sub != nullptr);
         int rc = zsock_connect(cmd_sub, "%s", argv[1]);
         if(rc == -1)
         {
            spdlog::error("error binding command socket");
            exit(-1);
         }

         data_pub = zsock_new_pub(argv[2]);
         assert(data_pub != nullptr);

         serial_server_ip = argv[3];
         serial_server_port = strtol(argv[4], nullptr, 0);
      }

      ~app()
      {
         zsock_destroy(&cmd_sub);
         zsock_destroy(&data_pub);
      }

      void run()
      {
         zloop_t *zloop = zloop_new();
         assert(zloop != nullptr);


         zloop_reader(zloop, cmd_sub, app::cmd_callback_wrap, this);
         zloop_timer(zloop, 1000, 0, app::timer_callback_wrap, this);

         int rc = zloop_start(zloop);
         if(rc == 0)
            spdlog::info("zloop interrupted\n");
         else
            spdlog::info("zloop cancelled by handler\n");
      }

};

int main(int argc, char **argv)
{
   app the_app(argc, argv);
   the_app.run();
   return 0;
}
