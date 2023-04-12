#include <cmd.hpp>
#include <iostream>
#include <string>

int main()
{
   bfsw::command c = {};

   for(auto b : c.pack<std::vector<uint8_t>>())
      std::cout << (unsigned int)b << std::endl;

   std::cout << "---" << std::endl;
   for(auto b : c.pack())
      std::cout << (unsigned int)b << std::endl;

   std::cout << "---" << std::endl;
   for(auto b : c.pack<std::string>())
      std::cout << (int) *reinterpret_cast<uint8_t*>(&b) << std::endl; //just casting to unsigned int doesn't work, since string elements are signed char. final (int) cast is just to get iostream to actually print the value smh


   return 0;
}
