#include <bfswutil.hpp>
#include <spdlog/spdlog.h>
#include <sqlite3.h>
#include <deque>
#include <vector>

//NOTE docs say little endian bytes (good) bits (had wtf moment but I think he just means the bit order wrt to the serial transmission, and lsb first is standard)

using ::bfsw::from_bytes;

namespace cooling
{

   class hkp_stream_parser
   {
      public:
         std::vector<uint8_t> buf;
         std::deque<std::vector<uint8_t>> queue;
         size_t num_dropped_bytes = 0;

         template <typename T> size_t ingest(T bytes, size_t i)
         {
            for(;i < bytes.size(); ++i)
               {
                  auto b = bytes[i];
                  if(buf.size() == 0)
                  {
                     if(b == 0x1e)
                        buf.push_back(b);
                  }
                  else
                  {
                     buf.push_back(b);
                     if(b == 0x0a && buf.size() == 182)
                     {
                        queue.emplace_back(std::move(buf));
                        if(queue.size() > 16)
                           queue.clear();
                        buf.clear();
                     }
                     if(buf.size() > 182)
                     {
                        num_dropped_bytes += buf.size();
                        buf.clear();
                     }
                  }
               }

               return queue.size();
            }

         std::vector<uint8_t> get()
         {
            if(queue.size())
            {
               auto res = std::move(queue.front());
               queue.pop_front();
               return res;
            }
            else
            {
               return {};
            }
         }
   };

   struct hkp_packet
   {
      bfsw::header header;
      uint32_t frame_counter {0xffffffff};
      uint8_t status_1 {0xff};
      uint8_t status_2 {0xff};
      uint8_t rx_byte_num {0xff};
      uint8_t rx_cmd_num {0xff};
      uint64_t last_cmd {0xffffffffffffffff};
      uint16_t rsv_t {0xffff};
      uint16_t rh_on {0xffff};
      uint16_t rh_off {0xffff};
      uint16_t fpga_board_v_in {0xffff};
      uint16_t fpga_board_i_in {0xffff};
      uint16_t fpga_board_t {0xffff};
      uint16_t fpga_board_p {0xffff};
      std::array<uint16_t, 64> rtd;
      uint16_t sh_current {0xffff};
      uint16_t rh_current {0xffff};
      uint16_t pw_board1_t {0xffff};
      uint16_t pw_board2_t {0xffff};
      uint16_t sh1_time_left {0xffff};
      uint16_t sh2_time_left {0xffff};
      uint16_t sh3_time_left {0xffff};

      const size_t expected_size {195};

      hkp_packet()
      {
         rtd.fill(0xffff);
      }

      template <typename T>
      int unpack(T const& bytes, size_t i)
      {
         if((i + bytes.size()) > expected_size)
            return -1;

         size_t i_start {i};
         int rc = header.unpack(bytes, i);
         if(rc < 0)
            return -100 + rc;
         else
            i += rc;

         uint8_t start_byte; 
         i += from_bytes(&bytes[i], start_byte);
         if(start_byte != 0x1e)
            return -2;
         //i += from_bytes(&bytes[i], frame_counter);
         from_bytes(&bytes[i], frame_counter);
         frame_counter &= 0xffffff;
         i += 3;
         i += from_bytes(&bytes[i], status_1);
         i += from_bytes(&bytes[i], status_2);
         i += from_bytes(&bytes[i], rx_byte_num);
         i += from_bytes(&bytes[i], rx_cmd_num);
         from_bytes(&bytes[i], last_cmd);
         last_cmd &= 0xffffffffffffff; //clear upper byte
         i += 7;
         i += from_bytes(&bytes[i], rsv_t);
         i += from_bytes(&bytes[i], rh_on);
         i += from_bytes(&bytes[i], rh_off);
         i += from_bytes(&bytes[i], fpga_board_v_in);
         i += from_bytes(&bytes[i], fpga_board_i_in);
         i += 2; //spare
         i += from_bytes(&bytes[i], fpga_board_t);
         i += from_bytes(&bytes[i], fpga_board_p);
         i += 6; //spares
         for(auto& r : rtd)
            i += from_bytes(&bytes[i], r);
         i += from_bytes(&bytes[i], sh_current);
         i += from_bytes(&bytes[i], rh_current);
         i += from_bytes(&bytes[i], pw_board1_t);
         i += from_bytes(&bytes[i], pw_board2_t);
         i += from_bytes(&bytes[i], sh1_time_left);
         i += from_bytes(&bytes[i], sh2_time_left);
         i += from_bytes(&bytes[i], sh3_time_left);
         i += 2; //spare
         uint8_t stop_byte;
         i += from_bytes(&bytes[i], stop_byte);
         if(stop_byte != 0x0a)
            return -3;

         if((i - i_start) != expected_size)
            return -4;

         return i - i_start;
      }
   };

   class hkp_packet_sqlite_writer
   {
      private:
         sqlite3_stmt* statement;
         std::vector<std::pair<std::string, std::string>> columns;
         sqlite3 *db_;

      public:
         hkp_packet_sqlite_writer(sqlite3* const db)
         {
            db_ = db;
            columns.push_back({"gsemode","int"});
            columns.push_back({"gcutime","real"});
            columns.push_back({"counter","int"});
            columns.push_back({"length","int"});
            columns.push_back({"frame_counter","int"});
            columns.push_back({"status_1","int"});
            columns.push_back({"status_2","int"});
            columns.push_back({"rx_byte_num","int"});
            columns.push_back({"rx_cmd_num","int"});
            columns.push_back({"last_cmd","int"});
            columns.push_back({"rsv_t","int"});
            columns.push_back({"rh_on","int"});
            columns.push_back({"rh_off","int"});
            columns.push_back({"fpga_board_v_in","int"});
            columns.push_back({"fpga_board_i_in","int"});
            columns.push_back({"fpga_board_t","int"});
            columns.push_back({"fpga_board_p","int"});
            for(int i = 0; i < 64; ++i)
               columns.push_back({fmt::format("rtd_{}", i), "int"});
            columns.push_back({"sh_current","int"});
            columns.push_back({"rh_current","int"});
            columns.push_back({"pw_board1_t","int"});
            columns.push_back({"pw_board2_t","int"});
            columns.push_back({"sh1_time_left","int"});
            columns.push_back({"sh2_time_left","int"});
            columns.push_back({"sh3_time_left","int"});
            columns.push_back({"blob","blob"});

            std::string sql = "create table if not exists cooling(rowid integer not null primary key,";
            for(auto& col : columns)
               sql += fmt::format("{} {},", col.first, col.second);
            sql.pop_back();
            sql += "); create unique index if not exists cooling_idx0 on cooling(gcutime, counter)";
            int rc = sqlite3_exec(db, sql.c_str(), nullptr, nullptr, nullptr);
            if(rc != SQLITE_OK)
            {
               spdlog::error("failed to create table \"cooling\"");
               spdlog::error("sqlite errmsg: {}", sqlite3_errmsg(db));
               exit(-1);
            }

            sql = "insert into cooling(";
            for(auto& col : columns)
               sql += fmt::format("{},", col.first);
            sql.pop_back();
            sql += ") values (";
            for(size_t i = 0; i < columns.size(); ++i)
               sql += "?,";
            sql.pop_back();
            sql += ")";
            rc = sqlite3_prepare_v2(db, sql.c_str(), -1, &statement, nullptr);
            if(rc != SQLITE_OK)
            {
               spdlog::error("failed to prepare insert statement for \"cooling\" table");
               spdlog::error("sqlite errmsg: {}", sqlite3_errmsg(db));
               exit(-1);
            }
         }

         int insert(cooling::hkp_packet const& p, int mode)
         {
            int rc = sqlite3_reset(statement);
            if(rc != SQLITE_OK)
            {
               spdlog::warn("rc = -1, sqlite3: {}", sqlite3_errmsg(db_));
               return -1;
            }

            int j = 1;
            sqlite3_bind_int64(statement, j++, mode);
            sqlite3_bind_double(statement, j++, bfsw::timestamp_to_double(p.header.timestamp));
            sqlite3_bind_int64(statement, j++, p.header.counter);
            sqlite3_bind_int64(statement, j++, p.header.length);
            sqlite3_bind_int64(statement, j++, p.frame_counter);
            sqlite3_bind_int64(statement, j++, p.status_1);
            sqlite3_bind_int64(statement, j++, p.status_2);
            sqlite3_bind_int64(statement, j++, p.rx_byte_num);
            sqlite3_bind_int64(statement, j++, p.rx_cmd_num);
            sqlite3_bind_int64(statement, j++, p.last_cmd);
            sqlite3_bind_int64(statement, j++, p.rsv_t);
            sqlite3_bind_int64(statement, j++, p.rh_on);
            sqlite3_bind_int64(statement, j++, p.rh_off);
            sqlite3_bind_int64(statement, j++, p.fpga_board_v_in);
            sqlite3_bind_int64(statement, j++, p.fpga_board_i_in);
            sqlite3_bind_int64(statement, j++, p.fpga_board_t);
            sqlite3_bind_int64(statement, j++, p.fpga_board_p);
            for(auto r : p.rtd)
                sqlite3_bind_int64(statement, j++, r);
            sqlite3_bind_int64(statement, j++, p.sh_current);
            sqlite3_bind_int64(statement, j++, p.rh_current);
            sqlite3_bind_int64(statement, j++, p.pw_board1_t);
            sqlite3_bind_int64(statement, j++, p.pw_board2_t);
            sqlite3_bind_int64(statement, j++, p.sh1_time_left);
            sqlite3_bind_int64(statement, j++, p.sh2_time_left);
            sqlite3_bind_int64(statement, j++, p.sh3_time_left);

            rc = sqlite3_step(statement);
            if(rc != SQLITE_DONE)
            {
               spdlog::warn("rc = -2, sqlite3: {}", sqlite3_errmsg(db_));
               return -2;
            }

            return 0;
         }
   };
}
