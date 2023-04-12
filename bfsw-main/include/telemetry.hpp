#include <bfswutil.hpp>
#include <vector>


namespace telemetry
{
   template <typename T>
   struct circular_buffer
   {
      std::vector<T> buffer;
      uint64_t wx;
      uint64_t rx;
      uint64_t mask;

      circular_buffer() : buffer(1 << 20,0), wx(0), rx(0)
      {
         mask = buffer.size() - 1;
      }

      uint64_t size()
      {
         return wx - rx;
      }

      void clear()
      {
         rx = wx;
      }

      template <typename T>
      int write(T& vec, size_t i)
      {
         if((wx + vec.size()) - rx > buffer.size())
            return -1;
         for(; i < vec.size(); ++i)
            buffer[wx++ & mask] = vec[i];
         return 0;
      }
      
      uint64_t read(std::vector<T>& vec, uint64_t n)
      {
         uint64_t nn;
         if(n <= this->size())
            nn = n;
         else
            nn = this->size();
         for(uint64_t i = 0; i < nn; ++i)
            vec.push_back(buffer[rx++ & mask]);
         return nn;
      }
   }

   struct framer
   {
      uint16_t counter;
      telemetry::circular_buffer<uint8_t> cb;
      uint64_t frame_size;

      framer(uint64_t frame_size) : frame_size(frame_size), counter(0)
      {}

      int write(std::vector<uint8_t>& bytes, size_t i = 0)
      {
         return cb.write(bytes,i);
      }

      std::vector<uint8_t> make_frame(bool compress)
      {
         std::vector<uint8_t> frame;
         if(cb.size() >= body_size)
         {
            frame = bfsw::make_packet_stub(254,counter++,0);
            if(compress)
            {
               frame.push_back(1);
               std::vector<uint8_t> bytes;
               int n = cb.read(bytes, frame_size - frame.size());
               compressed_bytes = telemetry::compress(bytes);
               for(auto b : compressed_bytes)
                  frame.push_back(b);
            }
            else
            {
               frame.push_back(0);
               int n = cb.read(frame,frame_size - frame.size());
            }
            int rc = bfsw::set_header_length_field(frame,frame.size());
            assert(rc == 0);
            //TODO checksum
         }
         return frame;
      }
   };

   //receives frames, reconstructs byte stream
   //must handle out of order packets, lost packets, rollovers
   struct deframer
   {
      telemetry::circular_buffer<uint8_t> cb;

      deframer()
      {}

      template <typename T> //works with std::vector and bfsw::array_wrapper
      int write(T& frame)
      {
         auto rc = bfsw::parse_header(frame);
         if(rc.second != 0)
            return -1;
         auto header = rc.first;
         if(header.type != 254)
            return -2;
         if(header.length <= 14)
            return -3;
         
         //group frames by timestamp, maintain sorted (by timetamp) list of frame groups
         //every so often, check the difference in time between front and back of list.
         //if the time difference is greater than some time, pop the oldest group.
         //within the popped group, sort by counter value. compute the differences between subsequent
         //counter values in the sort list.  If a difference larger than THRESH is found, then a 
         //rollover ocurred. Pop the frames out of the group starting on the THRESH element, and then wrapping
         //around to the beginning.  For example, if the sorted list of counters is [0,2,65534,65535], then
         //pop them out like [65534, 65535, 0, 2]

         //a good value for THRESH is determined based on the maximum data rate and the smallest packet size.
         //The smallest valid frame is 13 bytes (just a telemetry header for a type = 254 packet).  The maximum data rate is
         //100 megabit per second. This could result in 61538 packets per 64 ms. so a good value for THRESH would
         // be 65536 - 61538 = 3998.

         //this algorithm is robust against long gaps in telemetry. you might think that that long gaps would result
         //in multiple rollovers in a group, but it won't, since the later packets will just have a different
         //timestamp and belong to a later group.  The data rate and packet size argument limits the number of 
         //rollovers in a group to 0 or 1.

         //a single element group doesn't need any special handling. it is already coming out in order due to 
         //the sorting of the groups based on timestamp.



         return 0;

      }

   };

}

