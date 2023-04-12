#include <czmq.h>
#include <bfswutil.hpp>

int main(int argc, char ** argv)
{
   bfsw::packet_stats stats;
   zsock_t *sub = zsock_new_sub(argv[1], "");
   zpoller_t *poller = zpoller_new(sub);
   double t0 = bfsw::timestamp_monotonic();

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
         zframe_t *frame = zframe_recv(sub);
         uint8_t type = zframe_data(frame)[2];
         stats.push(type, zframe_size(frame));
      }
      double t = bfsw::timestamp_monotonic();
      if((t - t0) > 1)
      {
         t0 = t;
         fmt::print("=============\n");
         stats.print_count();
         stats.print_rates();
         stats.reset();
      }
   }

   zsock_destroy(&sub);
   zpoller_destroy(&poller);

   return 0;
}
