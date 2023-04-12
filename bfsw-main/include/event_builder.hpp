#include <vector>
#include <string>
#include <memory>
#include <bfswutil.hpp>
#include <cstdint>
#include <utility> 
#include <tracker.hpp>
#include <sqlite3.h>
#include <spdlog/spdlog.h>

//TODO maybe update pack to use bfsw::to_bytes

using ::bfsw::from_bytes;

namespace event_builder
{
   struct merged_event
   {
      bfsw::header header;
      double creation_time {0};
      uint32_t event_id {0};
      std::vector<tracker::event> tracker_events;
      std::vector<uint8_t> tof_data;
      std::vector<uint8_t> raw_data;
      uint8_t flags0 {0};
      uint8_t flags1 {0};

      merged_event()
      {}

      merged_event(uint32_t event_id, double time) : event_id(event_id)
      {
         if(time == 0)
            creation_time = bfsw::timestamp_monotonic();
         else
            creation_time = time;
      }

      void set_raw_data(std::vector<uint8_t> data)
      {
         raw_data = data;
      }

      int set_tof_data(std::vector<uint8_t>&& bytes) //caller should std::move bytes
      {
         if(tof_data.size())
            return -1;
         else
         {
            tof_data = bytes;
            return 0;
         }
      }

      void add_tracker_event(tracker::event& event)
      {
         tracker_events.push_back(event);
      }

      void add_tracker_event(tracker::event&& event)
      {
         tracker_events.push_back(std::move(event));
      }

      void print() const
      {
         fmt::print("id:{} ti:{} tof:{} trk:{}\n", event_id, creation_time, tof_data.size() ? 1 : 0, tracker_events.size());
      }

      std::pair<std::vector<uint8_t>,int> pack(uint16_t counter, uint32_t timestamp_64ms)
      {
         std::vector<uint8_t> bytes = bfsw::make_packet_stub(90,counter,0,timestamp_64ms);

         bytes.push_back(0); //version
         if(tof_data.size() && tracker_events.size())
            flags0 = 1;
         else
            flags0 = 0;
         flags1 = 0;
         bytes.push_back(flags0); //flags0
         bytes.push_back(flags1); //flags1

         //event id
         bytes.push_back(event_id & 0xff);
         bytes.push_back((event_id >> 8) & 0xff);
         bytes.push_back((event_id >> 16) & 0xff);
         bytes.push_back((event_id >> 24) & 0xff);

         //tof start delimiter
         bytes.push_back(0xAA);

         //tof size and data
         //assert(tof_data.size() <= (1<<16));
         if(tof_data.size() > 65535)
            return {bytes,-3};
         bytes.push_back(tof_data.size() & 0xff);
         bytes.push_back((tof_data.size() >> 8) & 0xff);
         for(const auto b : tof_data)
            bytes.push_back(b);

         //tracker start delimiter
         bytes.push_back(0xBB);

         //num tracker bytes
         size_t tracker_size_idx = bytes.size();
         bytes.push_back(0); //placeholder
         bytes.push_back(0); //placeholder

         for(auto& event : tracker_events)
         {
            int rc = event.pack(bytes,bytes.size());
            if(rc < 0)
               return {bytes,-2};
         }

         size_t num_tracker_bytes = bytes.size() - tracker_size_idx;
         assert(num_tracker_bytes <= (1<<16)); //TODO return error code
         bytes[tracker_size_idx] = num_tracker_bytes & 0xff;
         bytes[tracker_size_idx + 1] = (num_tracker_bytes >> 8) & 0xff;

         bfsw::set_header_length_field(bytes,bytes.size());

         //check that final packet size is less than 1 << 16
         if(bytes.size() > 1<<16)
            return {bytes,-1};
         else
            return {bytes,0};
      }

      template <typename T> int unpack(const T& bytes, size_t i) 
      {

         size_t i_start {i};
         int rc;
         rc = header.unpack(bytes, i);
         if(rc < 0)
            return -100 + rc;
         else
            i += rc;

         //TODO 

         //check that we have enough bytes to parse up to num_tof_bytes
         if((i + 10) > bytes.size())
            return -2;

         //sub header
         uint8_t version; i += from_bytes(&bytes[i], version);
         i += from_bytes(&bytes[i], flags0);
         i += from_bytes(&bytes[i], flags1);
         i += from_bytes(&bytes[i], event_id);

         //tof delimiter
         uint8_t tof_delimiter; i += from_bytes(&bytes[i], tof_delimiter);
         if(tof_delimiter != 0xaa)
            return -4;

         //tof size
         uint16_t num_tof_bytes; i += from_bytes(&bytes[i], num_tof_bytes);
         if((i + num_tof_bytes) > bytes.size())
            return -5;

         //copy tof data
         tof_data.clear();
         for(int j = 0; j < num_tof_bytes; ++j)
         {
            tof_data.push_back(bytes[i]); i += 1;
         }

         //check for enough bytes to parse tracker delimiter and size
         if((i + 3) > bytes.size())
            return -6;

         //tracker delimiter
         uint8_t tracker_delimiter; i += from_bytes(&bytes[i], tracker_delimiter);
         if(tracker_delimiter != 0xbb)
            return -7;

         //num tracker bytes
         uint16_t num_tracker_bytes; i += from_bytes(&bytes[i], num_tracker_bytes); 
         if((i + num_tracker_bytes - 2) > bytes.size()) //note this size check was being done differently before, and I think it was wrong. this size check was done before advancing the index
            return -8;

         //unpack tracker data
         while(1)
         {
            if(i >= bytes.size())
               break;
            tracker::event event;
            int rc = event.unpack(bytes,i);
            if(rc < 0)
            {
               spdlog::info("DEBUG event.unpack rc = {}", rc);
               return -9;
            }
            else
            {
                tracker_events.push_back(std::move(event));
                i += rc;
            }
         }

         if(i != bytes.size())
            return -10;

         return i - i_start;
      }

      int unpack_str(std::string& bytes, size_t i)
      {
         bfsw::array_wrapper wrap{reinterpret_cast<uint8_t*>(bytes.data()), bytes.size()};
         return unpack(wrap, i);
      }

   };


   struct merged_event_db_writer
   {
      sqlite3_stmt* packet_statement;
      sqlite3* db;

      merged_event_db_writer(sqlite3* const db_)
      {
         db = db_;
         int rc;

         std::string sql = "create table if not exists mergedevent "
            "(rowid INTEGER NOT NULL PRIMARY KEY,"
            "gsemode INTEGER NOT NULL,"
            "gcutime REAL NOT NULL,"
            "counter INTEGER NOT NULL,"
            "length INTEGER NOT NULL,"
            "eventid INTEGER NOT NULL,"
            "ntofhits INTEGER NOT NULL,"
            "ntrackerhits INTEGER NOT NULL,"
            "flags0 INTEGER NOT NULL,"
            "flags1 INTEGER NOT NULL,"
            "rawdata BLOB);"
            "create unique index if not exists mergedevent_idx0 on mergedevent (gcutime,counter)";

         rc = sqlite3_exec(db,sql.c_str(),NULL,NULL,NULL);
         if(rc != SQLITE_OK)
         {
            spdlog::error("failed to create mergedevent table, sqlite says: {}", sqlite3_errmsg(db));
            exit(-1);
         }

         sql = "insert into mergedevent "
            "(gsemode,gcutime,counter,length,eventid,ntofhits,ntrackerhits,flags0,flags1,rawdata) "
            "values (?,?,?,?,?,?,?,?,?,?)";

         rc = sqlite3_prepare_v2(db,sql.c_str(),-1,&packet_statement,NULL);
         if(rc != SQLITE_OK)
         {
            spdlog::error("failed to create statement for mergedevent table, sqlite says: {}", sqlite3_errmsg(db));
            exit(-1);
         }
      }

      template <typename T> int insert(merged_event& mev, int mode, T&& bytes)
      {
         int rc;
         rc = sqlite3_reset(packet_statement);
         if(rc != SQLITE_OK)
            return -1;

         sqlite3_bind_int(packet_statement,1,mode);
         sqlite3_bind_double(packet_statement,2,bfsw::timestamp_to_double(mev.header.timestamp));
         sqlite3_bind_int(packet_statement,3,mev.header.counter);
         sqlite3_bind_int(packet_statement,4,mev.header.length);
         sqlite3_bind_int(packet_statement,5,mev.event_id);
         sqlite3_bind_int(packet_statement,6,0); //ntofhits

         int n = 0;
         for(const auto& event : mev.tracker_events)
            n += event.hits.size();

         sqlite3_bind_int(packet_statement,7,n); //ntrackerhits
         sqlite3_bind_int(packet_statement,8,mev.flags0);
         sqlite3_bind_int(packet_statement,9,mev.flags1);
         sqlite3_bind_blob(packet_statement,10, bytes.data(), bytes.size(), SQLITE_TRANSIENT); 
         //optimization opportunity: SQLITE_STATIC instead of SQLITE_TRANSIENT
         //sqlite docs say you can use SQLITE_STATIC if the parameter is then bound to something after the blob. some googling indicates that you can bind NULL (which I think we would do after calling sqlite3_step).
         // https://stackoverflow.com/questions/48138521/sqlite3-bind-blob-when-is-safe-to-free-memory
         rc = sqlite3_step(packet_statement);
         if(rc != SQLITE_DONE)
            return -2;


         return 0;
      }

      void finalize()
      {
         sqlite3_finalize(packet_statement);
      }
   };

   using merged_event_ptr = std::shared_ptr<merged_event>;
}
