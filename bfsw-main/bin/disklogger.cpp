#include <czmq.h>
#include <cstdint>
#include <string>
#include <cstdio>
#include <cstdlib>
#include <disk_logger.hpp>
#include "bfswutil.hpp"
#include <memory>
#include <spdlog/spdlog.h>

int check_packet(uint8_t *buf, int len);

class app
{
   private:
      zsock_t *data_sub;
      std::unique_ptr<disk_logger> logger;
      std::vector<uint64_t> typecount;
      uint64_t n_bytes = 0;
      uint64_t n_bad = 0;
      double tlast;

      int data_callback()
      {
         zframe_t *frame = zframe_recv(data_sub);
         uint8_t *buf = zframe_data(frame);
         int len = zframe_size(frame);
         int type = check_packet(buf,len);
         if(type >= 0)
         {
            logger->write(buf,len);
            typecount[type]++;
            n_bytes += len;
         }
         else
         {
            n_bad++;
         }

         zframe_destroy(&frame);

         return 0;
      }

      static int data_callback_wrap(zloop_t *zloop, zsock_t *sock, void *arg)
      {
         return static_cast<app*>(arg)->data_callback();
      }

      int timer_callback()
      {

         double tnow = bfsw::timestamp_monotonic();
         printf("%7.6f kbps ",(n_bytes * 8)*1E-3/(tnow - tlast));
         tlast = tnow;
         n_bytes = 0;

         for(int i = 0; i < 256; ++i)
         {
            if(typecount[i])
               printf("%d:%lu ",i,typecount[i]);
         }
         printf(" bad:%lu",n_bad);
         printf("\n");
         fflush(stdout);

         logger->maintain();

         return 0;
      }

      static int timer_callback_wrap(zloop_t *zloop, int timer_id, void *arg)
      {
         return static_cast<app*>(arg)->timer_callback();
      }


   public:
      app(int argc, char ** argv) : typecount(256, 0)
      {
         if(argc < 3)
         {
            fmt::print("receive packets on ZMQ-PUB socket, and write them to disk(s)\n");
            fmt::print("1. ZMQ-SUB address, e.g. tcp://192.168.37.2:55555\n");
            fmt::print("2. between 1 and N paths to folders where raw data files should be written. a file named im_here must exist in the specified folder in order for data to be written\n");
            exit(-1);
         }

         std::vector<std::string> paths;
         for(int i = 2; i < argc; ++i)
            paths.push_back(argv[i]);
         logger = std::make_unique<disk_logger>(paths);

         data_sub = zsock_new_sub(argv[1], "");
         assert(data_sub != nullptr);

         tlast = bfsw::timestamp_monotonic();
      }

      ~app()
      {
         zsock_destroy(&data_sub);
      }

      void run()
      {
         zloop_t *zloop = zloop_new();
         zloop_reader(zloop, data_sub, app::data_callback_wrap, this);
         zloop_timer(zloop, 1000, 0, app::timer_callback_wrap, this);
         int rc = zloop_start(zloop);
         if(rc == 0)
            spdlog::info("zloop interrupted\n");
         else
            spdlog::info("zloop cancelled by handler\n");
      }
};

int main(int argc, char ** argv)
{
   app the_app(argc, argv);
   the_app.run();
   return 0;
}

int check_packet(uint8_t *buf, int len)
{
   if(len < 13) 
      return -1; 
   uint16_t eb90 = *((uint16_t*)&buf[0]);
   if(eb90 != 0x90EB)
      return -2; 
   uint16_t plen = *((uint16_t*)&buf[9]);
   if(len != plen)
      return -3; 

   return (int) buf[2];
}

