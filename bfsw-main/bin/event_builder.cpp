#include <czmq.h>
#include <cstdlib>
#include <vector>
#include <packets/REventPacket.h>
#include <packets/TofPacket.h>
#include <spdlog/spdlog.h>
#include <tracker.hpp>
#include <event_builder.hpp>
#include <list>
#include <map>

class app
{
   private:
      zsock_t *tracker_sub;
      zsock_t *tof_sub;
      zsock_t *data_pub;
      double time_delay;
      std::list<event_builder::merged_event_ptr> list;
      std::map<uint32_t, event_builder::merged_event_ptr> map;
      int num_tof_event_packets = 0;
      int num_all_tof_packets = 0;
      int num_tracker_event_packets = 0;
      double now_time;
      uint64_t merged_event_counter = 0;
      int num_tracker_packets_total = 0;

      std::shared_ptr<event_builder::merged_event> lookup_event(uint32_t event_id)
      {
         if(map.count(event_id))
         {
            return map[event_id];
         }
         else
         {
            auto mev = std::make_shared<event_builder::merged_event>(event_id, 0);
            map[event_id] = mev;
            list.push_back(mev);
            return mev;
         }
      }

      int tracker_callback()
      {
         zframe_t *frame = zframe_recv(tracker_sub);
         tracker::event_packet p;
         std::vector<uint8_t> bytes;
         for(size_t i = 0; i < zframe_size(frame); ++i)
            bytes.push_back(zframe_data(frame)[i]);
         zframe_destroy(&frame);

         num_tracker_packets_total++;
         if(bfsw::determine_packet_type(bytes) != 80)
         {
            //not a tracker event packet
            return 0;
         }
         num_tracker_event_packets++;
         int rc = p.unpack(bytes, 0);
         if(rc < 0)
         {
            spdlog::warn("event_packet::parse_from_daq: error, rc = {}", rc);
         }
         else
         {
            for(auto& event : p.events)
            {
               if(event.flags1 & 0b1) // check TOF event ID valid (lsb of flags1)
               {
                  auto mev = lookup_event(event.event_id);
                  mev->add_tracker_event(std::move(event));
               }
            }
         }

         return 0;
      }

      static int tracker_callback_wrap(zloop_t *zloop, zsock_t *sock, void *arg)
      {
         return static_cast<app*>(arg)->tracker_callback();
      }
      
      int tof_callback()
      {
         zframe_t *frame = zframe_recv(tof_sub);
         std::vector<uint8_t> bytes;
         for(size_t i = 0; i < zframe_size(frame); ++i)
            bytes.push_back(zframe_data(frame)[i]);
         zframe_destroy(&frame);
         TofPacket packet;
         int rc = packet.from_bytestream(bytes, 0);
         if(packet.packet_type == PACKET_TYPE_TOFEVENT)
         {
            num_tof_event_packets++;
            REventPacket rep;
            unsigned int rc = rep.deserialize(packet.payload, 0);
            if(rep.is_broken())
            {
               //achim suggesting we ignore this for now since there is an issue on the tof side
               //is_broken doesn't mean that the parsing failed
               //spdlog::warn("REventPacket::is_broken == true");
            }
            auto mev = lookup_event(rep.event_ctr);
            mev->set_tof_data(std::move(bytes));
         }
         num_all_tof_packets++;
         
         return 0;
      }

      static int tof_callback_wrap(zloop_t *zloop, zsock_t *sock, void *arg)
      {
         return static_cast<app*>(arg)->tof_callback();
      }

      int timer_callback()
      {
         now_time = bfsw::timestamp_monotonic();
         for(int i = 0; i < 100000; ++i)
         {
            if(list.size() == 0)
               break;

            auto mev = list.front();
            if((now_time - mev->creation_time) > time_delay)
            {
               list.pop_front();
               map.erase(mev->event_id);
               mev->print();
               auto rc = mev->pack(merged_event_counter, 0);
               if(rc.second != 0)
               {
                  spdlog::warn("failed to serialize merged event, rc = {}");
               }
               else
               {
                  auto& bytes = rc.first;
                  zframe_t *frame = zframe_new(bytes.data(), bytes.size());
                  zframe_send(&frame, data_pub, 0); //destroys after sending
                  merged_event_counter++;
               }
            }
         }

         fmt::print("list.size() = {}, num_tof_event_packets = {}, num_all_tof_packets = {}\n",list.size(), num_tof_event_packets, num_all_tof_packets);
         return 0;
      }

      static int timer_callback_wrap(zloop_t *zloop, int timer_id, void *arg)
      {
         return static_cast<app*>(arg)->timer_callback();
      }


   public:
      app(int argc, char ** argv)
      {
         if(argc != 5)
         {
            fmt::print("1) tracker data (ZMQ-SUB)\n");
            fmt::print("2) tof data (ZMQ-SUB)\n");
            fmt::print("3) output data (ZMQ-PUB)\n");
            fmt::print("4) time delay in seconds\n");
            exit(-1);
         }

         tracker_sub = zsock_new_sub("","");
         int rc = zsock_connect(tracker_sub,"%s",argv[1]);
         if(rc == -1)
         {
            spdlog::error("error connecting tracker socket");
            exit(-1);
         }

         tof_sub = zsock_new_sub("","");
         rc = zsock_connect(tof_sub,"%s",argv[2]);
         if(rc == -1)
         {
            spdlog::error("error connecting tof socket");
            exit(-1);
         }

         data_pub = zsock_new_pub(argv[3]);

         time_delay = std::stod(argv[4]);
         fmt::print("using time_delay = {}\n", time_delay);
         now_time = bfsw::timestamp_monotonic();
      }

      ~app()
      {
         zsock_destroy(&tracker_sub);
         zsock_destroy(&tof_sub);
         zsock_destroy(&data_pub);
      }

      void run()
      {
         zloop_t *zloop = zloop_new();
         assert(zloop != nullptr);

         zloop_reader(zloop, tracker_sub, app::tracker_callback_wrap, this);
         zloop_reader(zloop, tof_sub, app::tof_callback_wrap, this);
         zloop_timer(zloop, 1000, 0, app::timer_callback_wrap, this);

         int rc = zloop_start(zloop);
         if(rc == 0)
            spdlog::info("zloop interrupted\n");
         else
            spdlog::info("zloop cancelled by handler\n");

      }

};

int main(int argc,char ** argv)
{
   app the_app(argc, argv);
   the_app.run();
}
