#include <czmq.h>
#include <string>
#include <bfswutil.hpp>
#include <spdlog/spdlog.h>
#include <cmd.hpp>
#include <deque>
#include <cooling.hpp>


class app
{
   private: //members

      zsock_t *cmd_sub;
      zsock_t *data_pub;
      zsock_t *tcp_stream;
      std::string serial_server_ip;
      int hkp_packet_counter = 0;
      std::vector<uint8_t> tcp_id_bytes;
      cooling::hkp_stream_parser parser;

   private: //methods

      int cmd_callback()
      {
         zframe_t *frame = zframe_recv(cmd_sub);
         bfsw::command cmd;
         int rc = cmd.unpack(bfsw::array_wrapper(zframe_data(frame), zframe_size(frame)), 0);
         zframe_destroy(&frame);

         if( (rc == 0) && (cmd.address == 40) )
         {
            spdlog::info("command id: {}", cmd.command_id);
            switch(cmd.command_id)
            {
               case 100:
                  send_raw_command(cmd);
                  break;
               default:
                  spdlog::warn("invalid command id {}", cmd.command_id);
            }
         }
         else
         {
            spdlog::warn("cmd_callback(): bad command, cmd.serialize() returned rc = {}", rc);
         }

         return 0;
      }

      void send_raw_command(const bfsw::command& cmd)
      {
         if(tcp_id_bytes.size())
         {
            zmsg_t *msg = zmsg_new();
            zmsg_addmem(msg, tcp_id_bytes.data(), tcp_id_bytes.size());
            zmsg_addmem(msg, cmd.payload.data(), cmd.payload.size());
            zmsg_send(&msg, tcp_stream);
         }
         else
         {
            spdlog::warn("send_raw_command(): routing id not available for tcp peer, can't send command");
         }
      }

      static int cmd_callback_wrap(zloop_t *zloop, zsock_t *sock, void *arg)
      {
         return static_cast<app*>(arg)->cmd_callback();
      }

      int timer_callback()
      {
         spdlog::info("hkp_packet_counter = {}, parser.num_dropped_bytes = {}", hkp_packet_counter, parser.num_dropped_bytes);
         return 0;
      }

      static int timer_callback_wrap(zloop_t *zloop, int timer_id, void *arg)
      {
         return static_cast<app*>(arg)->timer_callback();
      }

      int serial_callback()
      {
         zmsg_t *msg = zmsg_recv(tcp_stream);

         if(msg == nullptr)
         {
            spdlog::warn("unexpected msg == nullptr");
            return 0;
         }

         if(zmsg_size(msg) != 2)
         {
            spdlog::warn("expected 2 frames in msg, actually got {} frames", zmsg_size(msg));
            return 0;
         }

         zframe_t *id_frame = zmsg_first(msg);
         tcp_id_bytes.clear();
         for(size_t i = 0; i < zframe_size(id_frame); ++i)
            tcp_id_bytes.push_back(zframe_data(id_frame)[i]);

         zframe_t *data_frame = zmsg_next(msg);
         size_t n = parser.ingest(bfsw::array_wrapper(zframe_data(data_frame), zframe_size(data_frame)), 0);
         for(size_t i = 0; i < n; ++i)
         {
            auto hkp_bytes = parser.get();
            if(hkp_bytes.size())
            {
               auto packet = bfsw::make_packet_stub(40, hkp_packet_counter++, 0, 0);
               for(auto byte : hkp_bytes)
                  packet.push_back(byte);
               bfsw::set_header_length_field(packet, packet.size());
               zframe_t *pub_frame = zframe_new(packet.data(), packet.size());
               zframe_send(&pub_frame, data_pub, 0); //destroys frame after sending
            }
         }

         zmsg_destroy(&msg);

         return 0;
      }

      static int serial_callback_wrap(zloop_t *zloop, zsock_t *sock, void *arg)
      {
         return static_cast<app*>(arg)->serial_callback();
      }

   public: //methods

      app(int argc, char **argv)
      {
         if(argc != 4)
         {
            fmt::print("1. cmd address (zmq pair)\n");
            fmt::print("2. data address (zmq pub)\n");
            fmt::print("3. serial port tcp address (zmq stream)\n");
            exit(-1);
         }

         cmd_sub = zsock_new_sub("",""); //replace with sub socket
         assert(cmd_sub != nullptr);
         int rc = zsock_connect(cmd_sub, "%s", argv[1]);
         if(rc == -1)
         {
            spdlog::error("error binding command socket");
            exit(-1);
         }

         data_pub = zsock_new_pub(argv[2]);
         assert(data_pub != nullptr);

         tcp_stream = zsock_new_stream(argv[3]); //default action is connect
         //note that I was erroneously calling connect again after zsock_new_stream
         //this was causing data to be received twice lol
         assert(tcp_stream != nullptr);
      }

      ~app()
      {
         zsock_destroy(&cmd_sub);
         zsock_destroy(&data_pub);
         zsock_destroy(&tcp_stream);
      }

      void run()
      {
         zloop_t *zloop = zloop_new();
         assert(zloop != nullptr);


         zloop_reader(zloop, cmd_sub, app::cmd_callback_wrap, this);
         zloop_reader(zloop, tcp_stream, app::serial_callback_wrap, this);
         zloop_timer(zloop, 10000, 0, app::timer_callback_wrap, this);

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
