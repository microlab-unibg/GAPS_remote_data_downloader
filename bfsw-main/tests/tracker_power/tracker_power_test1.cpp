#include <tracker_power.hpp>

int main()
{
   std::string cmd;

   cmd = tracker_power::cmd_md(3,1);
   fmt::print("cmd_md card 3 on: {}\n",cmd);

   cmd = tracker_power::cmd_plw(5,2,0);
   fmt::print("cmd_plw card 5 ch 2 off: {}\n",cmd);

   fmt::print("cmd_p set hv to 250 for card 10: {}\n",tracker_power::cmd_p(10,250));

   fmt::print("cmd_en card 7, ch3, on: {}\n", tracker_power::cmd_en(7,3,1));

   fmt::print("cmd_plr card 2: {}\n", tracker_power::cmd_plr(2));

   fmt::print("cmd_rva card 10: {}\n", tracker_power::cmd_rva(10));

   fmt::print("cmd_ria card 9: {}\n", tracker_power::cmd_ria(9));

   return 0;

}


