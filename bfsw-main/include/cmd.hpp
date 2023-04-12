#include <vector>
#include <cstdint>
#include <cassert>
#include <cstddef>

namespace bfsw
{
   struct command
   {
      int sync_eb;
      int sync_90;
      int crc1;
      int crc2;
      int sequence_number;
      int address;
      int command_id;
      int payload_length;
      std::vector<uint8_t> payload;

      template <typename T> int unpack(const T& bytes, size_t i)
      {
         const size_t header_size = 8;
         if((i + header_size) > bytes.size())
            return -1; //bad header

         auto byte = [&bytes](int j){return static_cast<uint8_t>(bytes[j]);};

         sync_eb = byte(i++);
         sync_90 = byte(i++);
         if((sync_eb != 0xeb) || (sync_90 != 0x90))
            return -2; //bad sync word
         crc1 = byte(i++);
         crc2 = byte(i++);
         sequence_number = byte(i++);
         address = byte(i++);
         command_id = byte(i++);
         payload_length = byte(i++);
         if((i + payload_length) != bytes.size())
            return -3; //failed length check

         payload.clear();
         for(; i < bytes.size(); ++i)
            payload.push_back(byte(i));

         return 0;
      }

      template <typename T = std::vector<uint8_t>> T pack()
      {
         T bytes;
         auto push = [&bytes](uint8_t byte){bytes.push_back(byte);};
         push(0xeb);
         push(0x90);
         push(crc1);
         push(crc2);
         push(sequence_number);
         push(address);
         push(command_id);
         assert(payload.size() <= 242);
         for(auto byte : payload)
            push(byte);
         return bytes;
      }

   };
}
