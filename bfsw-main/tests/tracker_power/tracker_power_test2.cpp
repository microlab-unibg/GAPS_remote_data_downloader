#include <tracker_power.hpp>

int main()
{
   std::string plr_string{"< sm 0101 plr 8 3745 0 2804 26 3262 0 2790 0 C4 \r\n"};
   tracker_power::plr_response plr;
   int rc = plr.unpack(plr_string);

   fmt::print("rc = {}\n",rc);
   fmt::print("plr string: {}\n", plr_string);
   for(auto v : plr.voltage)
      fmt::print("v: {}\n", v);
   for(auto i : plr.current)
      fmt::print("i:   {}\n", i);  

   std::string rva_string{"< sm 0101 rva 18 1 1 1 0 0 2 2 0 2 1 18446744073709510 0 0 0 0 1 1 0 DE \r\n"};
   tracker_power::rvia_response rva('v');
   rc = rva.unpack(rva_string);
   fmt::print("rc = {}\n",rc);
   fmt::print("rva string: {}\n", rva_string);
   for(auto val : rva.values)
      fmt::print("val: {}\n", val);

   return 0;

}
