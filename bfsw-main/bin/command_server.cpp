#include <czmq.h>
#include <string>
#include <bfswutil.hpp>
#include <spdlog/spdlog.h>
#include <cmd.hpp>
#include <stdlib.h>

class app
{
   private: //members

      zsock_t *cmd_pair = nullptr;
      zsock_t *cmd_pub = nullptr;
      int num_good_commands = 0;
      int num_bad_commands = 0;

   private: //methods

      int cmd_callback()
      {
         zframe_t *frame = zframe_recv(cmd_pair);
         bfsw::command cmd;
         int rc = cmd.unpack(bfsw::array_wrapper(zframe_data(frame), zframe_size(frame)), 0);

         if(rc == 0)
         {
            num_good_commands++;
            spdlog::info("cmd.address = {}, cmd.command_id = {}", cmd.address, cmd.command_id);
            zframe_send(&frame, cmd_pub, 0);
         }
         else
         {
            num_bad_commands++;
            spdlog::warn("cmd.serialize failed, rc = {}", rc);
         }
               
         zframe_destroy(&frame);
         return 0;
      }

      static int cmd_callback_wrap(zloop_t *zloop, zsock_t *sock, void *arg)
      {
         return static_cast<app*>(arg)->cmd_callback();
      }

      int timer_callback()
      {
         spdlog::info("num_good_commands = {}, num_bad_commands = {}", num_good_commands, num_bad_commands);
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
            fmt::print("1. cmd receive address (zmq pair)\n");
            fmt::print("2. cmd pub address (zmq pub)\n");
            exit(-1);
         }

         cmd_pair = zsock_new_pair("");
         assert(cmd_pair != nullptr);
         int rc = zsock_bind(cmd_pair, "%s", argv[1]);
         if(rc == -1)
         {
            spdlog::error("error binding command socket");
            exit(-1);
         }

         cmd_pub = zsock_new_pub(argv[2]);
         assert(cmd_pub != nullptr);

      }

      ~app()
      {
         zsock_destroy(&cmd_pair);
         zsock_destroy(&cmd_pub);
      }

      //TODO: rule of 3

      void run()
      {
         zloop_t *zloop = zloop_new();
         assert(zloop != nullptr);

         zloop_reader(zloop, cmd_pair, app::cmd_callback_wrap, this);
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
