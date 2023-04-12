#include<czmq.h>
#include<vector>
#include<string>
#include<memory>
#include<map>
#include<list>
#include<gfp.hpp>
#include<bfswutil.hpp>
#include<REventPacket.h>
#include<cstdint>
#include<utility> //pair
#include <tracker.hpp>
#include<iostream>
#include<sqlite3.h>
#include<event_builder.hpp>

//TODO: command sub socket

class app
{
   public:
      zsock_t *tracker_sub;
      zsock_t *tof_sub;
      zsock_t *data_pub;

      app(int argc, char ** argv)
      {
         if(argc != 5)
         {
            fmt::print("1) address for incoming tracker data (ZMQ-SUB)");
            fmt::print("2) address for incoming tof data (ZMQ-SUB)");
            fmt::print("3) address for outgoing merged event data (ZMQ-PUB)");
            fmt::print("4) time delay in seconds");
            exit(-1);
         }

         tracker_sub = zsock_new_sub("","");
         int rc = zsock_connect(tracker_sub, "%s", argv[1]);
         if(rc == -1)
         {
            spdlog::error("error connecting ZMQ-SUB socket for tracker");
            exit(-1);
         }

         tof_sub = zsock_new_sub("","");
         rc = zsock_connect(tracker_sub, "%s", argv[1]);
         if(rc == -1)
         {
            spdlog::error("error connecting ZMQ-SUB socket for tof");
            exit(-1);
         }

         data_pub = zsock_new_pub("","");






struct appdata_t
{
   uint64_t counter;
   double time;
   double time_delay;
   std::list<event_builder::merged_event_ptr> list;
   std::map<uint32_t, event_builder::merged_event_ptr> map;
   zsock_t *pub_socket;
};

int rx_callback(zloop_t *loop, zsock_t *socket, void *arg)
{
   auto *d = reinterpret_cast<appdata_t*>(arg);
   zframe_t *frame = zframe_recv(socket);

   std::vector<uint8_t> bytes;
   for(size_t i = 0; i < zframe_size(frame); ++i)
      bytes.push_back(zframe_data(frame)[i]);

   if(bytes[2] == 60) //tof event packet
   {
      bytes.erase(bytes.begin(), bytes.begin() + 13);
      REventPacket P;
      auto rc = P.deserialize(bytes);
      uint32_t event_id = P.event_ctr;
      event_builder::merged_event_ptr mev;
      if(d->map.count(event_id))
      {
         mev = d->map[event_id];
      }
      else
      {
         mev = std::make_shared<event_builder::merged_event>(event_id);
         d->map[event_id] = mev;
         d->list.push_back(mev);
      }
      mev->set_tof_data(bytes);

   }
   else if(bytes[2] == 80) //tracker event packet
   {
      tracker::event_packet p;
      int rc = p.parse_from_daq(bytes,0);
      if(rc)
      {
         std::cout << "[ERROR] tracker::parse_from_daq failed, rc = " << rc << std::endl;
      }
      else
      {
         for(const auto& e : p.events)
         {
            event_builder::merged_event_ptr mev;
            if(d->map.count(e->event_id))
            {
               mev = d->map[e->event_id];
            }
            else
            {
               mev = std::make_shared<event_builder::merged_event>(e->event_id);
               d->map[e->event_id] = mev;
               d->list.push_back(mev);
            }
            mev->add_tracker_event(e);
         }
      }

   }
   else
   {
      //ignore
   }

   return 0;
}

int timer_callback(zloop_t *loop, int timer_id, void *arg)
{

   appdata_t *d = (appdata_t*) arg;
   d->time = bfsw::timestamp_monotonic();

   for(int i = 0; i < 10000; ++i) // make sure we don't make more than 2**16 packets in one 64 ms time interval
   {
      if(d->list.size() == 0)
         break;
      auto mev = d->list.front();
      if((d->time - mev->creation_time) > d->time_delay)
      {
         d->list.pop_front();
         d->map.erase(mev->event_id);
         mev->print();
         auto rc = mev->serialize(d->counter,0);
         std::cout << "counter = " << d->counter << std::endl;
         if(rc.second != 0)
         {
            std::cout << "[ERROR] merged_event::serialize failed, rc = " << rc.second << std::endl;
         }
         else
         {
            std::cout << "[INFO] merged_event::serialize size = " << rc.first.size() << std::endl;
            auto& bytes = rc.first;
            zframe_t *frame = zframe_new(bytes.data(),bytes.size());
            zframe_send(&frame,d->pub_socket,0);
            zframe_destroy(&frame);
            d->counter++;
         }
      }
      else
      {
         break;
      }
   }

   return 0;
}

void help(int argc, char **argv)
{
   if(argc != 4)
   {
      std::cout << "1) zmq pub address for incoming data stream ";
      std::cout << "2) zmq pub address for outgoing merged event packets ";
      std::cout << "3) time delay in seconds" << std::endl;
      exit(-1);
   }
}


int main(int argc, char **argv)
{

   appdata_t d = {};

   help(argc,argv);

   //setup event loop
   zloop_t *loop = zloop_new();
   assert(loop != NULL);

   //setup timers
   int timer = zloop_timer(loop,100,0,timer_callback,&d);

   //setup zmq sub socket
   zsock_t *rx_socket = zsock_new_sub("","");
   assert(rx_socket != nullptr);
   assert(zsock_connect(rx_socket,"%s",argv[1]) == 0);
   zloop_reader(loop,rx_socket,rx_callback,&d);
   zsock_set_rcvhwm(rx_socket,0); //unlimited queueing depth

   //setup zmq pub socket
   d.pub_socket = zsock_new_pub(argv[2]);
   assert(d.pub_socket != NULL);
   zsock_set_sndhwm(d.pub_socket,0);

   d.time_delay = atof(argv[3]);

   //start event loop
   int rc = zloop_start(loop);
   if(rc)
      printf("zloop cancelled by handler\n");
   else
      printf("zloop interrupted\n");

   zsock_destroy(&rx_socket);
   zsock_destroy(&d.pub_socket);

   return 0;

}
