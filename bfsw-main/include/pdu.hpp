#include <array>
#include <spdlog/spdlog.h>
#include <bfswutil.hpp>
#include <array>
#include <utility>
#include <sqlite3.h>

namespace pdu
{
   struct pac_1934
   {
      int ctrl;
      int acc_count;
      struct channel
      {
         int64_t vpower_acc;
         int vbus;
         int vsense;
         int vbus_avg;
         int vsense_avg;
         int vpower;
      };
      std::array<channel, 4> channels;
      int channel_dis;
      int neg_pwr;
      int slow;
      int ctrl_act;
      int channel_dis_act;
      int neg_pwr_act;
      int ctrl_lat;
      int channel_dis_lat;
      int neg_pwr_lat;
      int pid;
      int mid;
      int rev;

      template <typename T>
      int parse(T bytes, int i)
      {
         const int expected_size = 88;
         if((bytes.size() - i) < expected_size)
            return -1;
         int i_start = i;

         auto b = [&bytes](int i){return static_cast<uint64_t>(bytes[i]);};
         ctrl = b(i); i += 1;
         acc_count = (b(i) << 16) | (b(i+1) << 8) | b(i+2); i += 3;
         for(auto& ch : channels) {ch.vpower_acc = (b(i) << 40) | (b(i+1) << 32) | (b(i+2) << 24) | (b(i+3) << 16) | (b(i+4) << 8) | b(i+5); i += 6;}
         for(auto& ch : channels) {ch.vbus = (b(i) << 8) | b(i+1); i += 2;}
         for(auto& ch : channels) {ch.vsense = (b(i) << 8) | b(i+1); i += 2;}
         for(auto& ch : channels) {ch.vbus_avg = (b(i) << 8) | b(i+1); i += 2;}
         for(auto& ch : channels) {ch.vsense_avg = (b(i) << 8) | b(i+1); i += 2;}
         for(auto& ch : channels) {ch.vpower = (b(i) << 24) | (b(i+1) << 16) | (b(i+2) << 8) | b(i+3); i += 4;}

         channel_dis = b(i); i += 1;
         neg_pwr = b(i); i += 1;
         slow = b(i); i += 1;
         ctrl_act = b(i); i += 1;
         channel_dis_act = b(i); i += 1;
         neg_pwr_act = b(i); i += 1;
         ctrl_lat = b(i); i += 1;
         channel_dis_lat = b(i); i += 1;
         neg_pwr_lat = b(i); i += 1;
         pid = b(i); i += 1;
         mid = b(i); i += 1;
         rev = b(i); i += 1;

         assert((i - i_start) == expected_size);
         return expected_size;
      }
   };

   struct hkp_packet
   {
      bfsw::header header;
      int pdu_type;
      int pdu_id;
      std::array<int,8> ads7828_voltages;
      std::array<pac_1934,2> pacs;
      int vbat;
      int pdu_count;
      int error;

      template <typename T> int unpack(const T& bytes, size_t i)
      {
         const int expected_size = 218;
         if((bytes.size() - i) < expected_size)
            return -1;
         size_t i_start {i};
         int rc;

         rc = header.unpack(bytes, i);
         if(rc < 0)
            return -100 + rc;
         else
            i += rc;

         auto b = [&bytes](int i){return static_cast<uint64_t>(bytes[i]);};
         pdu_type = b(i); i += 1;
         pdu_id = b(i); i += 1;
         for(auto& voltage : ads7828_voltages)
         {
            voltage = (b(i) << 8) | b(i+1); 
            i += 2;
         }
         for(auto& pac : pacs)
         {
            int rc = pac.parse(bytes,i);
            if(rc < 0)
            {
               spdlog::warn("hkp_packet::parse(): failed while parsing pac1934 data. rc = {}", rc);
               return -3;
            }
            else
            {
               i += rc;
            }
         }

         //NOTE: old code had vbat bytes little endian, but everything else is big endian.
         //from my testing with pdu, i know that this value wasn't reading properly
         //i assumed it was an issue with the board (wrong reistors or something)
         //but maybe it was just an endianness error.
         vbat = (b(i) << 8) | b(i+1); i += 2;
         i += 2;
         pdu_count = b(i); i += 1;
         error = b(i); i += 1;

	 i += 5; //ACK\r\n

         assert((i - i_start) == expected_size);
         return expected_size;
      }

      void print()
      {
         fmt::print("pdu_type: {}\n", pdu_type);
         fmt::print("pdu_id: {}\n", pdu_id);
         for(auto& pac : pacs)
         {
            fmt::print("pac.pid: {}\n", pac.pid);
            fmt::print("pac.mid: {}\n", pac.mid);
            fmt::print("pac.rev: {}\n", pac.rev);
         }
         fmt::print("pdu_count: {}\n", pdu_count);
      }
   };

   class hkp_packet_db_writer
   {
      private:
         sqlite3_stmt* packet_statement;
         std::vector<std::pair<std::string, std::string>> columns;

      public:
         hkp_packet_db_writer(sqlite3* const db)
         {
            columns.push_back({"gsemode","integer"});
            columns.push_back({"gcutime","real"});
            columns.push_back({"counter","integer"});
            columns.push_back({"length","integer"});
            columns.push_back({"pdu_id","integer"});
            columns.push_back({"pdu_count","integer"});
            columns.push_back({"acc_count_pac0","integer"});
            columns.push_back({"acc_count_pac1","integer"});
            for(int i = 0; i < 8; ++i)
            {
               columns.push_back({fmt::format("vbus{}",i),"integer"});
               columns.push_back({fmt::format("vbus_avg{}",i),"integer"});
               columns.push_back({fmt::format("vsense{}",i),"integer"});
               columns.push_back({fmt::format("vsense_avg{}",i),"integer"});
               columns.push_back({fmt::format("vpower{}",i),"integer"});
               columns.push_back({fmt::format("vpower_acc{}",i),"integer"});
            }
            for(int i = 0; i < 8; ++i)
               columns.push_back({fmt::format("temp{}",i),"integer"});
            columns.push_back({"vbat","integer"});
            columns.push_back({"error","integer"});

            //create table 
            std::string sql = "create table if not exists pdu_hkp(rowid integer not null primary key,";
            for(auto& column : columns)
               sql += fmt::format("{} {} not null,", column.first, column.second);
            sql.pop_back(); //remove last comma
            sql += "); create unique index if not exists pdu_hkp_idx0 on pdu_hkp(gcutime, counter)";
            int rc = sqlite3_exec(db, sql.c_str(), nullptr, nullptr, nullptr);
            if(rc != SQLITE_OK)
            {
               printf("failed to create table pdu_hkp\n");
               printf("%s\n",sqlite3_errmsg(db));
               exit(-1);
            }

            //prepare insert statement
            sql = "insert into pdu_hkp(";
            for(auto& column : columns)
               sql += fmt::format("{},",column.first);
            sql.pop_back(); //remove last comma
            sql += ") values (";
            for(size_t i = 0; i < columns.size(); ++i)
               sql += "?,";
            sql.pop_back();
            sql += ")";
            rc = sqlite3_prepare_v2(db, sql.c_str(), -1, &packet_statement, nullptr);
            if(rc != SQLITE_OK)
            {
               printf("failed to prepare insert statement for pdu_hkp\n");
               printf("%s\n",sqlite3_errmsg(db));
               exit(-1);
            }
        }

        int insert(pdu::hkp_packet& p, int mode)
        {
           int rc = sqlite3_reset(packet_statement);
           if(rc != SQLITE_OK)
              return -1;

           int j = 1;
           sqlite3_bind_int64(packet_statement, j++, mode);
           sqlite3_bind_double(packet_statement, j++, bfsw::timestamp_to_double(p.header.timestamp));
           sqlite3_bind_int64(packet_statement, j++, p.header.counter);
           sqlite3_bind_int64(packet_statement, j++, p.header.length);
           sqlite3_bind_int64(packet_statement, j++, p.pdu_id);
           sqlite3_bind_int64(packet_statement, j++, p.pdu_count);
           sqlite3_bind_int64(packet_statement, j++, p.pacs[0].acc_count);
           sqlite3_bind_int64(packet_statement, j++, p.pacs[1].acc_count);

           //const std::array<std::pair<int,int>,8> cmap = {{{0,1},{0,0},{0,3},{0,2},{1,1},{1,0},{1,3},{1,2}}};
           const std::array<std::pair<int,int>,8> cmap = {{{1,1},{1,0},{1,3},{1,2},{0,1},{0,0},{0,3},{0,2}}};
           for(int i = 0; i < 8; ++i)
           {
              auto& ch = p.pacs[ cmap[i].first ].channels[ cmap[i].second ];
              sqlite3_bind_int64(packet_statement, j++, ch.vbus);
              sqlite3_bind_int64(packet_statement, j++, ch.vbus_avg);
              sqlite3_bind_int64(packet_statement, j++, ch.vsense);
              sqlite3_bind_int64(packet_statement, j++, ch.vsense_avg);
              sqlite3_bind_int64(packet_statement, j++, ch.vpower);
              sqlite3_bind_int64(packet_statement, j++, ch.vpower_acc);
           }

           for(int i = 0; i < 8; ++i)
              sqlite3_bind_int64(packet_statement, j++, p.ads7828_voltages[i]);

           sqlite3_bind_int64(packet_statement, j++, p.vbat);
           sqlite3_bind_int64(packet_statement, j++, p.error);

           rc = sqlite3_step(packet_statement);
           if(rc != SQLITE_DONE)
              return -2;

           return 0;
        }
   };
}
