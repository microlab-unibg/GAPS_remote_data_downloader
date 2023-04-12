#pragma once
#include <vector>
#include <cstdint>
#include <cstdlib>
#include <sqlite3.h>
#include <algorithm>
#include <bfswutil.hpp>
#include <string>
#include <spdlog/spdlog.h>

using ::bfsw::extend_vector;
using ::bfsw::from_bytes;
using ::bfsw::to_bytes;

namespace tracker
{
   uint64_t make_systime(uint32_t lower, uint16_t upper)
   {
      return (static_cast<uint64_t>(upper) << 32) | static_cast<uint64_t>(lower);
   }

   struct header
   {
      uint16_t sync;
      uint16_t crc;
      uint8_t sys_id;
      uint8_t packet_id;
      uint16_t length;
      uint16_t daq_count;
      uint64_t sys_time;
      uint8_t version;
      uint8_t settings1;
      const size_t header_size = 18;

      template <typename T> int unpack(const T& bytes, size_t i)
      {
         if((i + header_size) > bytes.size())
            return -1;
         size_t i_start {i};
         i += from_bytes(&bytes[i], sync);
         i += from_bytes(&bytes[i], crc);
         i += from_bytes(&bytes[i], sys_id);
         i += from_bytes(&bytes[i], packet_id);
         i += from_bytes(&bytes[i], length);
         i += from_bytes(&bytes[i], daq_count);
         uint32_t lower; i += from_bytes(&bytes[i], lower);
         uint16_t upper; i += from_bytes(&bytes[i], upper);
         sys_time = make_systime(lower, upper);
         i += from_bytes(&bytes[i], version);
         i += from_bytes(&bytes[i], settings1);
         return i - i_start;
      }

      std::string repr()
      {
         return fmt::format("sync:{:x} crc:{:x} sys_id:{} packet_id:{} length:{} daq_count:{} sys_time:{} version:{} settings:{:b}",
                            sync, crc, sys_id, packet_id, length, daq_count, sys_time, version, settings1);
      }

   };

   struct hit
   {
      uint8_t row;
      uint8_t module;
      uint8_t channel;
      uint16_t adc;
      uint8_t asic_event_code;
      const size_t num_bytes = 6;

      hit()
      {}

      hit(uint8_t row, uint8_t module, uint8_t channel, uint16_t adc, uint8_t asic_event_code) :
         row(row),
         module(module),
         channel(channel),
         adc(adc),
         asic_event_code(asic_event_code)
      {}

      int pack(std::vector<uint8_t>& bytes, size_t i)
      {
         extend_vector(bytes, i + num_bytes);
         i += to_bytes(&bytes[i], row);
         i += to_bytes(&bytes[i], module);
         i += to_bytes(&bytes[i], channel);
         i += to_bytes(&bytes[i], adc);
         i += to_bytes(&bytes[i], asic_event_code);
         return num_bytes;
      }

      template <typename T> int unpack(const T& bytes, size_t i)
      {
         if((i + num_bytes) > bytes.size())
            return -1;
         i += from_bytes(&bytes[i], row);
         i += from_bytes(&bytes[i], module);
         i += from_bytes(&bytes[i], channel);
         i += from_bytes(&bytes[i], adc);
         i += from_bytes(&bytes[i], asic_event_code);
         return num_bytes;
      }

      std::string repr()
      {
         return fmt::format("row:{} module:{} channel:{} adc:{} asic_event_code:{}",
                             row, module, channel, adc, asic_event_code);
      }

   };

   struct event
   {
      uint8_t layer;
      uint8_t flags1;
      uint32_t event_id; 
      uint64_t event_time;
      std::vector<tracker::hit> hits;

      event() : layer{0xff}, flags1{0xff}, event_id{0xffffffff}, event_time{0xffffffffffffffff}
      {}

      int pack(std::vector<uint8_t>& bytes, size_t i)
      {

         //intended for event builder.
         //thus, event id not part of event body
         //since event id appears in merged event header

         size_t i_start {i};
         extend_vector(bytes, i + 8); //TODO don't like this, extending of vector should take place outside of this method
         i += to_bytes(&bytes[i], static_cast<uint32_t>(event_time & 0xffffffff)); //4 lower bytes
         i += to_bytes(&bytes[i], static_cast<uint16_t>((event_time >> 32) & 0xffff)); //2 upper bytes
         i += to_bytes(&bytes[i], layer);
         i += to_bytes(&bytes[i], static_cast<uint8_t>(std::min(hits.size(), size_t{0xff})));

         for(auto& hit: hits)
         {
            int n = hit.pack(bytes, bytes.size());
            if(n < 0)
               return -2;
            else
               i += n;
         }

         return i - i_start;
      }

      template <typename T> int unpack(const T& bytes, size_t i)
      {

         //intended for event builder
         //unpacking of events from backend daq packet happens in tracker::event_packet::unpack

         size_t i_start {i};
         if((i + 8) > bytes.size())
            return -1;
         uint32_t lower; i += from_bytes(&bytes[i], lower);
         uint16_t upper; i += from_bytes(&bytes[i], upper);
         event_time = make_systime(lower, upper);
         i += from_bytes(&bytes[i], layer);
         uint8_t num_hits; i += from_bytes(&bytes[i], num_hits);

         for(size_t j = 0; j < num_hits; ++j)
         {
            tracker::hit h;
            int n = h.unpack(bytes, i);
            if(n < 0)
               return -2;
            else
            {
               i += n;
               hits.push_back(std::move(h));
            }
         }

         return i - i_start;
      }

      std::string repr()
      {
         return fmt::format("layer:{} event_id:{} event_time:{} flags1:{:b} num_hits:{}",
                             layer, event_id, event_time, flags1, hits.size());
      }

   };

   struct event_packet
   {
      bfsw::header header;
      tracker::header daq_header;
      std::vector<tracker::event> events;

      template <typename T> int unpack(const T& bytes, size_t i)
      {

         size_t i_start {i};
         int rc;
         rc = header.unpack(bytes, i);
         if(rc < 0)
            return -100 + rc;
         else
            i += rc;

         if(header.type != 80)
            return -8;

         rc = daq_header.unpack(bytes,i);
         if(rc < 0)
            return -200 + rc;
         else
            i += rc;

         if(daq_header.sync != 0xeb90)
            return -3;
         if((daq_header.packet_id & 0xf0) != 0xf0)
            return -4;

         while(1)
         {
            const size_t event_header_size = 12;
            if((i + event_header_size) > bytes.size())
               return -5;

            tracker::event event;
            event.layer = daq_header.sys_id;
            uint8_t num_hits; i += from_bytes(&bytes[i], num_hits);
            i += from_bytes(&bytes[i], event.flags1);
            i += from_bytes(&bytes[i], event.event_id);
            uint32_t lower; i += from_bytes(&bytes[i], lower);
            uint16_t upper; i += from_bytes(&bytes[i], upper);
            event.event_time = make_systime(lower, upper);
            if(num_hits > 192) //isn't a real event, looking at filler bytes. once event packets stop having filler, logic here will need to change
               break;

            if((i + (3*num_hits)) > bytes.size())
               return -6;

            for(size_t j = 0; j < num_hits; ++j)
            {
               uint8_t h0, h1, h2;
               i += from_bytes(&bytes[i], h0);
               i += from_bytes(&bytes[i], h1);
               i += from_bytes(&bytes[i], h2);
               uint8_t asic_event_code = h2 >> 6;
               uint8_t channel = h0 & 0b11111;
               uint8_t module = h0 >> 5;
               uint8_t row = h1 & 0b111;
               uint16_t adc = ((h2 & 0b00111111) << 5) | (h1 >> 3);
               event.hits.emplace_back(row, module, channel, adc, asic_event_code);
            }

            events.push_back(std::move(event));
            if(events.size() > 170)
               return -7;
         }

         return i - i_start;
      }

   };

   struct event_packet_db_writer
   {
      sqlite3_stmt* packet_statement;
      sqlite3_stmt* event_statement;
      sqlite3_stmt* hit_statement;
      sqlite3* db;

      event_packet_db_writer(sqlite3* const db) : db(db)
      {
         int rc;

         //create tables
         std::string sql1 = "create table if not exists gfptrackerpacket "
            "(rowid INTEGER NOT NULL PRIMARY KEY,"
            "gsemode INTEGER NOT NULL,"
            "gcutime REAL NOT NULL,"
            "counter INTEGER NOT NULL,"
            "length INTEGER NOT NULL,"
            "sysid INTEGER NOT NULL,"
            "row INTEGER NOT NULL,"
            "systime INTEGER NOT NULL,"
            "daqcounter INTEGER NOT NULL,"
            "numevents INTEGER NOT NULL);"
            "create unique index if not exists gfptrackerpacket_idx0 on gfptrackerpacket (gcutime,counter)";
         std::string sql2 = "create table if not exists gfptrackerevent "
            "(rowid INTEGER NOT NULL PRIMARY KEY,"
            "parent INTEGER NOT NULL,"
            "numhits INTEGER NOT NULL,"
            "eventidvalid INTEGER NOT NULL,"
            "eventid INTEGER NOT NULL,"
            "eventtime INTEGER NOT NULL,"
            "foreign key (parent) references gfptrackerpacket (rowid));"
            "create index if not exists gfptrackerevent_parent on gfptrackerevent (parent)";
         std::string sql3 = "create table if not exists gfptrackerhit "
            "(parent INTEGER NOT NULL,"
            "row INTEGER NOT NULL,"
            "module INTEGER NOT NULL,"
            "channel INTEGER NOT NULL,"
            "adcdata INTEGER NOT NULL,"
            "asiceventcode INTEGER NOT NULL,"
            "foreign key (parent) references gfptrackerevent (rowid),"
            "primary key (parent,row,module,channel)) "
            "without rowid;";

         rc = sqlite3_exec(db,sql1.c_str(),NULL,NULL,NULL);
         if(rc != SQLITE_OK)
         {
            printf("failed to create gfptrackerpacket table\n");
            printf("%s\n",sqlite3_errmsg(db));
            exit(-1);
         }

         rc = sqlite3_exec(db,sql2.c_str(),NULL,NULL,NULL);
         if(rc != SQLITE_OK)
         {
            printf("failed to create gfptrackerevent table\n");
            printf("%s\n",sqlite3_errmsg(db));
            exit(-1);
         }

         rc = sqlite3_exec(db,sql3.c_str(),NULL,NULL,NULL);
         if(rc != SQLITE_OK)
         {
            printf("failed to create gfptrackerhit table\n");
            printf("%s\n",sqlite3_errmsg(db));
            exit(-1);
         }

         //prepare statements

         rc = sqlite3_prepare_v2(db,"insert into gfptrackerpacket(gcutime,counter,length,sysid,row,systime,daqcounter,numevents,gsemode) values (?,?,?,?,?,?,?,?,?)",-1,&packet_statement,NULL);
         if(rc != SQLITE_OK)
         {
            printf("failed to prepare insert statement for gfptrackerpacket\n");
            printf("%s\n",sqlite3_errmsg(db));
            exit(-1);
         }

         rc = sqlite3_prepare_v2(db,"insert into gfptrackerevent(parent,numhits,eventidvalid,eventid,eventtime) values (?,?,?,?,?)",-1,&event_statement,NULL);
         if(rc != SQLITE_OK)
         {
            printf("failed to prepare insert statement for gfptrackerevent\n");
            printf("%s\n",sqlite3_errmsg(db));
            exit(-1);
         }

         rc = sqlite3_prepare_v2(db,"insert into gfptrackerhit(parent,channel,module,row,adcdata,asiceventcode) values (?,?,?,?,?,?)",-1,&hit_statement,NULL);
         if(rc != SQLITE_OK)
         {
            printf("failed to prepare insert statement for gfptrackerhit\n");
            printf("%s\n",sqlite3_errmsg(db));
            exit(-1);
         }
      }

      int insert(tracker::event_packet& p, int mode)
      {
         int rc;
         rc = sqlite3_reset(packet_statement);
         if(rc != SQLITE_OK)
            return -6;

         sqlite3_bind_double(packet_statement,1,bfsw::timestamp_to_double(p.header.timestamp));
         sqlite3_bind_int(packet_statement,2,p.header.counter);         
         sqlite3_bind_int(packet_statement,3,p.header.length);       
         sqlite3_bind_int(packet_statement,4,p.daq_header.sys_id);
         sqlite3_bind_int(packet_statement,5,p.daq_header.packet_id & 0x0F);
         sqlite3_bind_int64(packet_statement,6,p.daq_header.sys_time);
         sqlite3_bind_int(packet_statement,7,p.daq_header.daq_count);
         sqlite3_bind_int(packet_statement,8,p.events.size());
         sqlite3_bind_int(packet_statement,9,mode);
         rc = sqlite3_step(packet_statement);
         if(rc != SQLITE_DONE)
            return -1;

         sqlite3_int64 packet_row = sqlite3_last_insert_rowid(db);

         for(const auto& event : p.events)
         {
            rc = sqlite3_reset(event_statement);
            if(rc != SQLITE_OK)
               return -2;

            sqlite3_bind_int(event_statement,1,packet_row);
            sqlite3_bind_int(event_statement,2,event.hits.size());
            sqlite3_bind_int(event_statement,3,event.flags1);
            sqlite3_bind_int64(event_statement,4,event.event_id);
            sqlite3_bind_int64(event_statement,5,event.event_time);

            rc = sqlite3_step(event_statement);
            if(rc != SQLITE_DONE)
               return -3;

            sqlite3_int64 event_row = sqlite3_last_insert_rowid(db);

            for(const auto& hit : event.hits)
            {
               rc = sqlite3_reset(hit_statement);
               if(rc != SQLITE_OK)
                  return -4;

               sqlite3_bind_int(hit_statement,1,event_row);
               sqlite3_bind_int(hit_statement,2,hit.channel);
               sqlite3_bind_int(hit_statement,3,hit.module);
               sqlite3_bind_int(hit_statement,4,hit.row);
               sqlite3_bind_int(hit_statement,5,hit.adc);
               sqlite3_bind_int(hit_statement,6,hit.asic_event_code);

               rc = sqlite3_step(hit_statement);
               if(rc != SQLITE_DONE)
                  return -5;
            }
         }

         return 0;
      }

      void finalize()
      {
         sqlite3_finalize(packet_statement);
         sqlite3_finalize(event_statement);
         sqlite3_finalize(hit_statement);
      }

   };

   struct counter_packet
   {
      bfsw::header header;
      tracker::header daq_header;
      uint32_t elapsed_time;
      uint32_t busy_time;
      uint32_t busy_count;
      uint16_t lv_sync_errors;
      uint16_t hv_sync_errors;
      uint16_t lv_packet_size_errors;
      uint16_t hv_packet_size_errors;
      uint16_t lv_backplane_activity;
      uint16_t hv_backplane_activity;
      uint16_t lv_words_valid;
      uint16_t hv_words_valid;
      uint32_t tof_triggers;
      uint32_t reboots;

      template <typename T> int unpack(const T& bytes, size_t i)
      {
         size_t i_start {i};

         if(bytes.size() != 109)
            return -1;

         /*
         auto rc = bfsw::parse_header(bytes, i); //TODO fix API, see previous call
         if(rc.second != 0)
            return -2;
         header = rc.first;
         */
         int rc;
         rc = header.unpack(bytes, i);
         if(rc < 0)
            return -2;
         else
            i += rc;

         if(header.type != 81)
            return -3;

         if(bytes.size() != header.length)
            return -4;

         i += 13;

         int ret = daq_header.unpack(bytes, i);
         if(ret < 0)
            return -1000 + ret;

         i += ret;

         i += from_bytes(&bytes[i], elapsed_time);
         i += from_bytes(&bytes[i], busy_time);
         i += from_bytes(&bytes[i], busy_count);
         i += 8; //empty bytes
         i += from_bytes(&bytes[i], lv_sync_errors);
         i += from_bytes(&bytes[i], hv_sync_errors);
         i += from_bytes(&bytes[i], lv_packet_size_errors);
         i += from_bytes(&bytes[i], hv_packet_size_errors);
         i += from_bytes(&bytes[i], lv_backplane_activity);
         i += from_bytes(&bytes[i], hv_backplane_activity);
         i += from_bytes(&bytes[i], lv_words_valid);
         i += from_bytes(&bytes[i], hv_words_valid);
         i += 20; //empty bytes
         i += from_bytes(&bytes[i], tof_triggers);
         i += from_bytes(&bytes[i], reboots);

         //TODO check size against expected size!

         return i - i_start;
      }

   };

   struct counter_packet_db_writer
   {

      sqlite3_stmt* packet_statement;
      sqlite3* db;

      counter_packet_db_writer(sqlite3* const db) : db(db)
      {
         int rc;

         std::string sql = "create table if not exists gfptrackercounters"
            "(rowid INTEGER NOT NULL PRIMARY KEY,"
            "gsemode INTEGER NOT NULL,"
            "gcutime REAL NOT NULL,"
            "counter INTEGER NOT NULL,"
            "length INTEGER NOT NULL,"
            "sysid INTEGER NOT NULL,"
            "systime INTEGER NOT NULL,"
            "count INTEGER NOT NULL,"
            "elapsedtime INTEGER NOT NULL,"
            "busytime INTEGER NOT NULL,"
            "busycount INTEGER NOT NULL,"
            "lvsyncerrors INTEGER NOT NULL,"
            "hvsyncerrors INTEGER NOT NULL,"
            "lvpacketsizeerrors INTEGER NOT NULL,"
            "hvpacketsizeerrors INTEGER NOT NULL,"
            "lvbackplaneactivity INTEGER NOT NULL,"
            "hvbackplaneactivity INTEGER NOT NULL,"
            "lvwordsvalid INTEGER NOT NULL,"
            "hvwordsvalid INTEGER NOT NULL,"
            "toftriggers INTEGER NOT NULL,"
            "reboots INTEGER NOT NULL);"
            "create unique index if not exists gfptrackercounters_idx0 on gfptrackercounters(gcutime,counter)";

         rc = sqlite3_exec(db,sql.c_str(),NULL,NULL,NULL);
         if(rc != SQLITE_OK)
         {
            printf("failed to create table gfptrackercounters\n");
            printf("%s\n",sqlite3_errmsg(db));
            exit(-1);
         }

         sql = "insert into gfptrackercounters"
            "(gcutime,"
            "counter,"
            "length,"
            "sysid,"
            "systime,"
            "count,"
            "elapsedtime,"
            "busytime,"
            "busycount,"
            "lvsyncerrors,"
            "hvsyncerrors,"
            "lvpacketsizeerrors,"
            "hvpacketsizeerrors,"
            "lvbackplaneactivity,"
            "hvbackplaneactivity,"
            "lvwordsvalid,"
            "hvwordsvalid,"
            "toftriggers,"
            "reboots,"
            "gsemode) "
            "values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)";
         rc = sqlite3_prepare_v2(db,sql.c_str(),-1,&packet_statement,NULL);
         if(rc != SQLITE_OK)
         {
            printf("failed to prepare counter packet statement\n");
            printf("%s\n",sqlite3_errmsg(db));
            exit(-1);
         }
      }

      int insert(tracker::counter_packet& p, int mode)
      {
         int rc;

         rc = sqlite3_reset(packet_statement);
         if(rc != SQLITE_OK)
            return -1;
         sqlite3_bind_double(packet_statement,1,bfsw::timestamp_to_double(p.header.timestamp));
         sqlite3_bind_int(packet_statement,2,p.header.counter);
         sqlite3_bind_int(packet_statement,3,p.header.length);
         sqlite3_bind_int(packet_statement,4,p.daq_header.sys_id);
         sqlite3_bind_int64(packet_statement,5,p.daq_header.sys_time);
         sqlite3_bind_int(packet_statement,6,p.daq_header.daq_count);
         sqlite3_bind_int(packet_statement,7,p.elapsed_time);
         sqlite3_bind_int(packet_statement,8,p.busy_time);
         sqlite3_bind_int(packet_statement,9,p.busy_count);
         sqlite3_bind_int(packet_statement,10,p.lv_sync_errors);
         sqlite3_bind_int(packet_statement,11,p.hv_sync_errors);
         sqlite3_bind_int(packet_statement,12,p.lv_packet_size_errors);
         sqlite3_bind_int(packet_statement,13,p.hv_packet_size_errors);
         sqlite3_bind_int(packet_statement,14,p.lv_backplane_activity);
         sqlite3_bind_int(packet_statement,15,p.hv_backplane_activity);
         sqlite3_bind_int(packet_statement,16,p.lv_words_valid);
         sqlite3_bind_int(packet_statement,17,p.hv_words_valid);
         sqlite3_bind_int(packet_statement,18,p.tof_triggers);
         sqlite3_bind_int(packet_statement,19,p.reboots);
         sqlite3_bind_int(packet_statement,20,mode);

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

   struct templeak_packet
   {
      bfsw::header header;
      tracker::header daq_header;
      uint8_t row_offset;
      std::array<std::array<int,6>,6> templeak;
      std::array<std::array<int,6>,6> seu;

         template <typename T> int unpack(const T& bytes, size_t i)
         {
            size_t i_start {i};
            int rc;

            if(bytes.size() != 85)
               return -1;

            rc = header.unpack(bytes, i);
            if(rc < 0)
               return -1000 + rc;
            else
               i += rc;

            rc = daq_header.unpack(bytes, i);
            if(rc < 0)
               return -2000 + rc;
            else
                i += rc;

            uint8_t version; i += from_bytes(&bytes[i], version);
            uint8_t row_info; i += from_bytes(&bytes[i], row_info);
            uint8_t row_offset_valid = row_info & 0b1000;
            row_offset = row_info & 0b111;
            row_offset_valid = 1; //old comment: "forcing this, ask Brent why I'm getting zero" //TODO check with Brent
            if(row_offset_valid)
            {
               for(int row = 0; row < 3; ++row)
               {
                  for(int mod = 0; mod < 6; ++mod)
                  {
                     uint8_t b0, b1, b2;
                     i += from_bytes(&bytes[i], b0);
                     i += from_bytes(&bytes[i], b1);
                     i += from_bytes(&bytes[i], b2);
                     int seu_ = b2 >> 1;
                     int templeak_ = (b2 << 10) | (b1 << 2) | (b0 >> 6);
                     templeak_ &= 0b11111111111;
                     templeak[row][mod] = templeak_;
                     seu[row][mod] = seu_;
                  }
               }
            }
            else
            {
               return -3;
            }

            return i - i_start;
         }
   };

   struct templeak_packet_db_writer
   {
      sqlite3_stmt* packet_statement;
      sqlite3* db;

      templeak_packet_db_writer(sqlite3* const db) : db(db)
      {
         int rc;

         std::string sql = "create table if not exists gfptrackertempleak"
            "(rowid INTEGER NOT NULL PRIMARY KEY,"
            "gsemode INTEGER NOT NULL,"
            "gcutime REAL NOT NULL,"
            "counter INTEGER NOT NULL,"
            "length INTEGER NOT NULL,"
            "sysid INTEGER NOT NULL,"
            "systime INTEGER NOT NULL,"
            "daqcount INTEGER NOT NULL,"
            "rowoffset INTEGER NOT NULL,"
            "templeak_r0m0 INTEGER NOT NULL,"
            "templeak_r0m1 INTEGER NOT NULL,"
            "templeak_r0m2 INTEGER NOT NULL,"
            "templeak_r0m3 INTEGER NOT NULL,"
            "templeak_r0m4 INTEGER NOT NULL,"
            "templeak_r0m5 INTEGER NOT NULL,"
            "templeak_r1m0 INTEGER NOT NULL,"
            "templeak_r1m1 INTEGER NOT NULL,"
            "templeak_r1m2 INTEGER NOT NULL,"
            "templeak_r1m3 INTEGER NOT NULL,"
            "templeak_r1m4 INTEGER NOT NULL,"
            "templeak_r1m5 INTEGER NOT NULL,"
            "templeak_r2m0 INTEGER NOT NULL,"
            "templeak_r2m1 INTEGER NOT NULL,"
            "templeak_r2m2 INTEGER NOT NULL,"
            "templeak_r2m3 INTEGER NOT NULL,"
            "templeak_r2m4 INTEGER NOT NULL,"
            "templeak_r2m5 INTEGER NOT NULL,"
            "seu_r0m0 INTEGER NOT NULL,"
            "seu_r0m1 INTEGER NOT NULL,"
            "seu_r0m2 INTEGER NOT NULL,"
            "seu_r0m3 INTEGER NOT NULL,"
            "seu_r0m4 INTEGER NOT NULL,"
            "seu_r0m5 INTEGER NOT NULL,"
            "seu_r1m0 INTEGER NOT NULL,"
            "seu_r1m1 INTEGER NOT NULL,"
            "seu_r1m2 INTEGER NOT NULL,"
            "seu_r1m3 INTEGER NOT NULL,"
            "seu_r1m4 INTEGER NOT NULL,"
            "seu_r1m5 INTEGER NOT NULL,"
            "seu_r2m0 INTEGER NOT NULL,"
            "seu_r2m1 INTEGER NOT NULL,"
            "seu_r2m2 INTEGER NOT NULL,"
            "seu_r2m3 INTEGER NOT NULL,"
            "seu_r2m4 INTEGER NOT NULL,"
            "seu_r2m5 INTEGER NOT NULL); "
            "create unique index if not exists gfptrackertempleak_idx0 on gfptrackertempleak(gcutime,counter)";

         rc = sqlite3_exec(db,sql.c_str(),NULL,NULL,NULL);
         if(rc != SQLITE_OK)
         {
            printf("failed to create table gfptrackertempleak\n");
            printf("%s\n",sqlite3_errmsg(db));
            exit(-1);
         }
        
         sql = "insert into gfptrackertempleak"
            "(gcutime,"
            "counter,"
            "length,"
            "sysid,"
            "systime,"
            "daqcount,"
            "gsemode,"
            "rowoffset,"
            "templeak_r0m0,"
            "templeak_r0m1,"
            "templeak_r0m2,"
            "templeak_r0m3,"
            "templeak_r0m4,"
            "templeak_r0m5,"
            "templeak_r1m0,"
            "templeak_r1m1,"
            "templeak_r1m2,"
            "templeak_r1m3,"
            "templeak_r1m4,"
            "templeak_r1m5,"
            "templeak_r2m0,"
            "templeak_r2m1,"
            "templeak_r2m2,"
            "templeak_r2m3,"
            "templeak_r2m4,"
            "templeak_r2m5,"
            "seu_r0m0,"
            "seu_r0m1,"
            "seu_r0m2,"
            "seu_r0m3,"
            "seu_r0m4,"
            "seu_r0m5,"
            "seu_r1m0,"
            "seu_r1m1,"
            "seu_r1m2,"
            "seu_r1m3,"
            "seu_r1m4,"
            "seu_r1m5,"
            "seu_r2m0,"
            "seu_r2m1,"
            "seu_r2m2,"
            "seu_r2m3,"
            "seu_r2m4,"
            "seu_r2m5) "
            "values ("
            "?,?,?,?,?,?,?,?,?,?,"
            "?,?,?,?,?,?,?,?,?,?,"
            "?,?,?,?,?,?,?,?,?,?,"
            "?,?,?,?,?,?,?,?,?,?,"
            "?,?,?,?)";

         rc = sqlite3_prepare_v2(db,sql.c_str(),-1,&packet_statement,NULL);
         if(rc != SQLITE_OK)
         {
            printf("failed to prepare insert statement for gfptrackertempleak\n");
            printf("%s\n",sqlite3_errmsg(db));
            exit(-1);
         }
         
      }

      int insert(tracker::templeak_packet p, int mode)
      {
         int rc;

         rc = sqlite3_reset(packet_statement);
         if(rc != SQLITE_OK)
            return -1;

         sqlite3_bind_double(packet_statement,1,bfsw::timestamp_to_double(p.header.timestamp));
         sqlite3_bind_int(packet_statement,2,p.header.counter);
         sqlite3_bind_int(packet_statement,3,p.header.length);
         sqlite3_bind_int(packet_statement,4,p.daq_header.sys_id);
         sqlite3_bind_int64(packet_statement,5,p.daq_header.sys_time);
         sqlite3_bind_int64(packet_statement,6,p.daq_header.daq_count);
         sqlite3_bind_int64(packet_statement,7,mode);
         sqlite3_bind_int64(packet_statement,8,p.row_offset);

         int arg = 9;

         for(int row = 0; row < 3; ++row)
            for(int mod = 0; mod < 6; ++mod)
               sqlite3_bind_int(packet_statement,arg++,p.templeak[row][mod]);

         for(int row = 0; row < 3; ++row)
            for(int mod = 0; mod < 6; ++mod)
               sqlite3_bind_int(packet_statement,arg++,p.seu[row][mod]);

         //assert(arg == 45);

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

   struct gps_packet
   {
      bfsw::header header;
      tracker::header daq_header;
      uint32_t utc_time;
      uint8_t gps_info;

      template <typename T> int unpack(const T& bytes, size_t i)
      {
         size_t i_start {i};
         int rc;

         if(bytes.size() != 35)
            return -1;

         rc = header.unpack(bytes, i);
         if(rc < 0)
            return -1000 + rc;
         else
            i += rc;

         rc = daq_header.unpack(bytes, i);
         if(rc < 0)
            return -2000 + rc;
         else
            i += rc;

         i += from_bytes(&bytes[i], utc_time);
         i += from_bytes(&bytes[i], gps_info);
         uint8_t footer; i += from_bytes(&bytes[i], footer);

         return i - i_start;
      }

   };

   struct gps_packet_db_writer
   {
      sqlite3_stmt* packet_statement;
      sqlite3* db;

      gps_packet_db_writer(sqlite3* const db) : db(db)
      {
         int rc;
         std::string sql = "create table if not exists gfptrackergps"
            "(rowid INTEGER NOT NULL PRIMARY KEY,"
            "gsemode INTEGER NOT NULL,"
            "gcutime REAL NOT NULL,"
            "counter INTEGER NOT NULL,"
            "length INTEGER NOT NULL,"
            "sysid INTEGER NOT NULL,"
            "systime INTEGER NOT NULL,"
            "count INTEGER NOT NULL,"
            "utctime INTEGER NOT NULL,"
            "gpsinfo INTEGER NOT NULL);"
            "create unique index if not exists gfptrackergps_idx0 on gfptrackergps(gcutime,counter)";
         rc = sqlite3_exec(db,sql.c_str(),NULL,NULL,NULL);
         if(rc != SQLITE_OK)
         {
            printf("failed to create table gfptrackergps\n");
            printf("%s\n",sqlite3_errmsg(db));
            exit(-1);
         }
         
         sql = "insert into gfptrackergps"
            "(gcutime,"
            "counter,"
            "length,"
            "sysid,"
            "systime,"
            "count,"
            "utctime,"
            "gpsinfo,"
            "gsemode) "
            "values (?,?,?,?,?,?,?,?,?)";
         rc = sqlite3_prepare_v2(db,sql.c_str(),-1,&packet_statement,NULL);
         if(rc != SQLITE_OK)
         {
            printf("failed to prepare insert statement for gfptrackertempleak\n");
            printf("%s\n",sqlite3_errmsg(db));
            exit(-1);
         }
      }

      int insert(tracker::gps_packet p, int mode)
      {
         int rc;
         rc = sqlite3_reset(packet_statement);
         if(rc != SQLITE_OK)
            return -1;

         sqlite3_bind_double(packet_statement,1,bfsw::timestamp_to_double(p.header.timestamp));
         sqlite3_bind_int(packet_statement,2,p.header.counter);
         sqlite3_bind_int(packet_statement,3,p.header.length);
         sqlite3_bind_int(packet_statement,4,p.daq_header.sys_id);
         sqlite3_bind_int64(packet_statement,5,p.daq_header.sys_time);
         sqlite3_bind_int(packet_statement,6,p.daq_header.daq_count);
         sqlite3_bind_int(packet_statement,7,p.utc_time);
         sqlite3_bind_int(packet_statement,8,p.gps_info);
         sqlite3_bind_int(packet_statement,9,mode);
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

}
