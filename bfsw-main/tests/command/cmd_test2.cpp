#include <cmd.hpp>
#include <iostream>
#include <string>
#include <cstdlib>

int main()
{

   std::vector<uint8_t> bytes;
   auto push = [&bytes](uint8_t byte){bytes.push_back(byte);};
   push(0xeb);
   push(0x90);
   push(1); //crc1
   push(2); //crc2
   push(3); //sequence number
   push(4); //address
   push(5); //command_id
   const int length = 6;
   push(length);
   for(int i = 0; i < length; ++i)
      push(9);

   bfsw::command c;

   int rc = c.unpack(bytes, 0);

   auto check  = [](bool b){if(!b) std::abort(); };


   check(rc == 0);
   check(c.sync_eb == 0xeb);
   check(c.sync_90 == 0x90);
   check(c.crc1 == 1);
   check(c.crc2 == 2);
   check(c.sequence_number == 3);
   check(c.address == 4);
   check(c.command_id == 5);
   check(c.payload.size() == length);
   for(auto b : c.payload)
      check(b == 9);

   std::cout << "test passed :)" << std::endl;

   return 0;
}
