#include <czmq.h>
#include <string>
#include <bfswutil.hpp>
#include <spdlog/spdlog.h>
#include <network.hpp>
#include <cmd.hpp>
#include <stdlib.h>
#include <tracker_power.hpp>

class app
{
   private: //members

      zsock_t *cmd_sub;
      zsock_t *data_pub;
      uint16_t hkp_packet_counter {0};

   private: //methods

      int cmd_callback()
      {
         zframe_t *frame = zframe_recv(cmd_sub);
         bfsw::command cmd;
         int rc = cmd.unpack(bfsw::array_wrapper(zframe_data(frame), zframe_size(frame)), 0);
         zframe_destroy(&frame);

         if( (rc == 0) && (cmd.address == 30) )
         {
            struct addr_t
            {
               uint8_t crate {0xff}, ip{0xff}, card{0xff};
               void parse(uint8_t x)
               {
                  crate = (x >> 5) & 1;
                  ip = (x >> 4) & 1;
                  card = x & 0b1111;
               }
            } addr;

            const std::string ip{"192.168.37.101"};

            int ret = -1000;
            spdlog::info("CMD {}", cmd.command_id);
            switch(cmd.command_id)
            {
               case 0: //noop
                  {
                     ret = 0;
                     break;
                  }
               case 50:
                  {
                     if(cmd.payload.size() == 3)
                     {
                        uint8_t onoff = cmd.payload[0];
                        addr.parse(cmd.payload[1]);
                        uint8_t mask = cmd.payload[2];
                        spdlog::info("cmd 50: onoff:{} addr.crate:{} addr.ip:{} addr.card:{} mask:0b{:b}", onoff, addr.crate, addr.ip, addr.card, mask);
                        //ret = tracker_power::lv_onoff(ip, addr.card, mask, onoff, 1000);
                     }
                     break;
                  }
               case 60:
                  {
                     if(cmd.payload.size() == 6)
                     {
                        uint8_t p = cmd.payload[0]; //ignored
                        uint8_t hv = cmd.payload[1];
                        addr.parse(cmd.payload[2]);
                        uint32_t mask; from_bytes(&cmd.payload[2], mask);
                        mask = mask >> 8;
                        spdlog::info("cmd 60: p:{} hv:{} addr.crate:{} addr.ip:{} addr.card:{} mask:0b{:b}", p, hv, addr.crate, addr.ip, addr.card, mask);
                        //ret = tracker_power::hv_on(ip, addr.card, mask, hv, 1000);
                     }
                     break;
                  }
               case 65:
                  {
                     if(cmd.payload.size() == 4)
                     {
                        addr.parse(cmd.payload[0]);
                        uint32_t mask; from_bytes(&cmd.payload[0], mask);
                        mask = mask >> 8;
                        spdlog::info("cmd 65: addr.crate:{} addr.ip:{} addr.card:{} mask:0b{:b}", addr.crate, addr.ip, addr.card, mask);
                        //ret = tracker_power::hv_ramp_down(ip, addr.card, mask, 1000);
                     }
                     break;
                  }
               case 66:
                  {
                     if(cmd.payload.size() ==1 )
                     {
                        addr.parse(cmd.payload[0]);
                        spdlog::info("cmd 66: addr.crate:{} addr.ip:{} addr.card:{}", addr.crate, addr.ip, addr.card);
                        //ret = tracker_power::hv_off(ip, addr.card, 1000);
                     }
                     break;
                  }
               case 100: //tracker_power::hv_on
                  {
                     if(cmd.payload.size() == 5)
                     {
                        addr.parse(cmd.payload[0]);
                        uint8_t hv = cmd.payload[1];
                        uint8_t mask_lsb; from_bytes(&cmd.payload[2], mask_lsb);
                        uint16_t mask_msb; from_bytes(&cmd.payload[3], mask_msb);
                        int mask = (static_cast<int>(mask_msb) << 16) | static_cast<int>(mask_lsb);
                        //ret = tracker_power::hv_on(ip_address, addr.card, mask, hv, 1000);
                     }
                     break;
                  }
               case 105: //tracker_power::hv_ramp_down
                  {
                     if(cmd.payload.size() == 4)
                     {
                        addr.parse(cmd.payload[0]);
                        uint8_t mask_lsb; from_bytes(&cmd.payload[1], mask_lsb);
                        uint16_t mask_msb; from_bytes(&cmd.payload[2], mask_msb);
                        int mask = (static_cast<int>(mask_msb) << 16) | static_cast<int>(mask_lsb);
                        //ret = tracker_power::hv_ramp_down(ip_address, addr.card, mask, 1000);
                     }
                     break;
                  }
               case 110: //tracker_power::hv_disable
                  {
                     if(cmd.payload.size() == 4)
                     {
                        addr.parse(cmd.payload[0]);
                        uint8_t mask_lsb; from_bytes(&cmd.payload[1], mask_lsb);
                        uint16_t mask_msb; from_bytes(&cmd.payload[2], mask_msb);
                        int mask = (static_cast<int>(mask_msb) << 16) | static_cast<int>(mask_lsb);
                        //ret = tracker_power::hv_disable(ip_address, addr.card, mask, 1000);
                     }
                     break;
                  }
               default:
                  spdlog::warn("invalid command id {}", cmd.command_id);
            }
         }
         else
         {
            spdlog::warn("cmd_callback(): bad command, cmd.serialize() returned rc = {} (should be 0), and cmd.address is {} (should be 30)", rc, cmd.address);
         }

         return 0;
      }

      static int cmd_callback_wrap(zloop_t *zloop, zsock_t *sock, void *arg)
      {
         return static_cast<app*>(arg)->cmd_callback();
      }

      int timer_callback()
      {
         uint8_t crate {0};
         uint8_t card {1};
         std::string ip {"192.168.37.101"};
         tracker_power::card_hkp_packet p;
         p.crate = 0;
         p.card = 1;
         int rc = p.read_crate(ip, card, 100);
         spdlog::info("flags: {:b}", p.flags);
         if(rc == 0)
         {
            auto packet = p.make_packet(hkp_packet_counter++, 0);
            zframe_t *frame = zframe_new(packet.data(), packet.size());
            zframe_send(&frame, data_pub, 0);
         }
         else
            spdlog::warn("error with read_crate, rc = {}", rc);

         return 0;
      }

      static int timer_callback_wrap(zloop_t *zloop, int timer_id, void *arg)
      {
         return static_cast<app*>(arg)->timer_callback();
      }

   public: //methods

      app(int argc, char **argv)
      {
         if(argc != 3)
         {
            fmt::print("1. cmd address (zmq sub)\n");
            fmt::print("2. data address (zmq pub)\n");
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
         zloop_timer(zloop, 5000, 0, app::timer_callback_wrap, this);

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
