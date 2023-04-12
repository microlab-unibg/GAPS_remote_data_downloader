#include <string>
#include <spdlog/spdlog.h>
#include <network.hpp>
#include <array>
#include <bfswutil.hpp>
#include <sqlite3.h>


using ::bfsw::to_bytes;
using ::bfsw::from_bytes;

//TODO crate eventually stops responding


//TODO in hv_on, check the LV voltages BEFORE turning anything on. currently turning on p and ep before doing the checks
//TODO plr, breakout values into named fields, instead of one big array
//TODO st: implement method that checks the hv status bit
//TODO st hv status bit as 
//TODO wrap unwrapped stoll calls
//TODO check LRC

namespace tracker_power
{
   //turn on card
   std::string cmd_md(int card, int onoff)
   {
      if(card < 1 || card > 10)
         return "";

      if(!(onoff == 0 || onoff == 1))
         return "";

      return fmt::format("< ms FF00 md{:x} 1 {} L \r", card, onoff);
   }

   //enable low voltage outputs on low voltage connector
   //ch determines which of the 3x LV d-subs is "turned on"
   std::string cmd_plw(int card, int ch, int onoff)
   {
      if(card < 1 || card > 10)
         return "";

      if(ch < 1 || ch > 3)
         return "";

      if(!(onoff == 0 || onoff == 1))
         return "";

      return fmt::format("< ms {:02x}{:02x} plw 1 {} L \r", card, ch, onoff);
   }

   //enables power to HV module
   std::string cmd_ep(int card, int onoff)
   {
      if(card < 1 || card > 10)
         return "";

      if(!(onoff == 0 || onoff == 1))
         return "";

      return fmt::format("< ms {:02x}00 ep 1 {} L \r", card, onoff);
   }

   //sets the primary HV value for a card. This must be higher than the desired HV for each channel
   //the HV for each channel is derived from this primary HV. 
   //i.e. there is only one HV supply per card, and each channel taps the output and divides it down
   std::string cmd_p(int card, int hv) 
   {
      if(card < 1 || card > 10)
         return "";

      if(hv < 0 || hv > 305)
         return "";

      return fmt::format("< ms {:02x}00 p 1 {} L \r", card, hv);
   }

   //ramp to HV set point. this command actually results in high voltage at the connector
   std::string cmd_en(int card, int ch, int onoff)
   {
      if(card < 1 || card > 10)
         return "";

      if(ch < 1 || ch > 3)
         return "";

      if(!(onoff == 0 || onoff == 1))
         return "";

      return fmt::format("< ms {:02x}{02x} en 1 {} L \r", card, ch, onoff);
   }

   //sets the high voltage value for a channel. must be lower than what was set with cmd_p
   std::string cmd_sv(int card, int ch, int hv)
   {
      if(card < 1 || card > 10)
         return "";

      if(ch < 1 || ch > 18)
         return "";

      if(hv < 0 || hv > 305)
         return "";

      return fmt::format("< ms {:02x}{:02x} sv 1 {} L \r", card, ch, hv);
   }

   //read low voltage voltage/current
   std::string cmd_plr(int card)
   {
      if(card < 1 || card > 10)
         return "";

      return fmt::format("< ms {:02x}00 plr 1 L \r", card);
   }

   //read hv output voltage measurements
   std::string cmd_rva(int card)
   {
      if(card < 1 || card > 10)
         return "";

      return fmt::format("< ms {:02x}01 rva 1 0 L \r", card);
   }

   //read hv output currents
   std::string cmd_ria(int card)
   {
      if(card < 1 || card > 10)
         return "";

      return fmt::format("< ms {:02x}01 ria 1 0 L \r", card);
   }

   //get card status
   std::string cmd_st(int card)
   {
      if(card < 1 || card > 10)
         return "";

      return fmt::format("< ms {:02x}01 st 1 0 L \r", card);
   }

   //get main board status
   std::string cmd_mds()
   {
      return "< ms FF00 mds 1 1 L \r";
   }

   std::string cmd_tem(int card)
   {
      if(card < 1 || card > 10)
         return "";

      return fmt::format("< ms {:02x}01 tem 1 0 L \r", card);
   }

   std::string cmd_rhv(int card)
   {
      if(card < 1 || card > 10)
         return "";

      return fmt::format("< ms {:02x}00 rhv 1 0 L \r", card);
   }


   std::string transact(std::string ip_address, std::string command, int timeout_ms)
   {
      bfsw::tcp_client client;
      int rc = client.connect_to(ip_address, 1000, timeout_ms);
      if(rc != 0)
      {
         spdlog::warn("failed to connect to sili power crate, rc = {}", rc);
         return "";
      }

      auto greeting = client.recv_until("\n\r",timeout_ms*1E-3); //TODO check validity of greeting, CR-LF is supposed to be reversed here
      rc = client.send_full(command, timeout_ms, 10);
      if(rc != 0)
      {
         spdlog::warn("failed to send_full command, rc = {}", rc);
         return "";
      }

      auto response = client.recv_until("\r", timeout_ms*1E-3); //response validity checked in unpack methods 
      return response;
   }

   std::vector<std::string> tokenize(const std::string& s)
   {
      std::vector<std::string> result;
      std::string token;
      for(auto c : s)
      {
         if(c == ' ')
         {
            if(token.size())
            {
               result.push_back(std::move(token));
               token.clear();
            }
         }
         else
         {
            token.push_back(c);
         }
      }

      if(token.size())
         result.push_back(std::move(token));

      return result;
   }

   uint16_t str_u16(std::string s)
   {
      try
      {
         auto y = std::stoll(s);
         if(y > 0xffff)
            y = 0xffff;
         else if(y < 0)
            y = 0;
         return static_cast<uint16_t>(y);
      } 
      catch(std::invalid_argument const& e)
      {
         return 0xffff;
      }
      catch(std::out_of_range const& e)
      {
         return 0xffff;
      }
   }

   int8_t str_i8(std::string s)
   {
      try
      {
         auto y = std::stoll(s);
         if(y > 127)
            y = 127;
         else if(y < -128)
            y = -128;
         return static_cast<int8_t>(y);
      }
      catch(std::invalid_argument const& e)
      {
         return -128;
      }
      catch(std::out_of_range const& e)
      {
         return -128;
      }
   }

   struct plr_response
   {
      std::array<uint16_t, 12> voltage;
      std::array<uint16_t, 12> current;
      plr_response()
      {
         voltage.fill(0xffff);
         current.fill(0xffff);
      }
      int unpack(const std::string& s)
      {
         const size_t num_tokens {31};
         auto tokens = tokenize(s);
         if(tokens.size() != num_tokens)
            return -1;

         if(tokens[3] != "plr")
            return -2;

         for(size_t i = 0; i < voltage.size(); ++i)
            voltage[i] = str_u16(tokens[5 + 2*i]);

         for(size_t i = 0; i < current.size(); ++i)
            current[i] = str_u16(tokens[6 + 2*i]);

         return 0;
      }
   };

   struct rvia_response
   {
      char iv;
      std::array<uint16_t,18> values;
      rvia_response(char iv_)
      {
         if(iv_ == 'i' || iv_ == 'v')
            iv = iv_;
         else
         {
            spdlog::error("contstructor parameter for tracker_power::rva_ria must be char = i or char = v. assuming char = v");
            exit(-1);
         }
         values.fill(0xffff);
      }

      int unpack(const std::string& s)
      {
         const size_t num_tokens {25};
         auto tokens = tokenize(s);
         if(tokens.size() != num_tokens)
         {
            return -1;
         }

         std::string which;
         if(iv == 'v')
            which = "rva";
         else
            which = "ria";

         if(tokens[3] != which)
            return -2;

         for(size_t i = 0; i < values.size(); ++i)
         {
            values[i] = str_u16(tokens[i + 5]);
         }

         return 0;
      }
   };

   struct tem_response
   {
      std::array<int8_t, 9> temperatures; //guessing this is in C and is signed, check on precision
      tem_response()
      {
         temperatures.fill(-128);
      }
      int unpack(const std::string& s)
      {
         const size_t num_tokens {16};
         auto tokens = tokenize(s);
         if(tokens.size() != num_tokens)
            return -1;

         if(tokens[3] != "tem") //might actually be tmp and not tem
            return -2;

         for(size_t i = 0; i < temperatures.size(); ++i)
            temperatures[i] = str_i8(tokens[i + 5]);

         return 0;
      }
   };

   struct st_response
   {
      uint32_t board_status {0xffffffff};
      std::array<uint32_t, 3> connector_status;
      st_response()
      {
         connector_status.fill(0xffff);
      }

      int unpack(const std::string& s)
      {
         const size_t num_tokens {11};
         auto tokens = tokenize(s);
         if(tokens.size() != num_tokens)
            return -1;

         if(tokens[3] != "st")
            return -2;

         board_status = std::stoll(tokens[5], nullptr, 16);
         connector_status[0] = std::stoll(tokens[6], nullptr, 16);
         connector_status[1] = std::stoll(tokens[7], nullptr, 16);
         connector_status[2] = std::stoll(tokens[8], nullptr, 16);

         return 0;
      }

      int ch_hv_status(int ch)
      {
         //return 1 if hv is enabled for this channel, 0 if disabled, and negative int if status could not be read
         int i = ch / 6;
         if(i < 0 || i > 2)
            return -1;
         int j = ch % 6;
         return (connector_status[i] >> (j*4)) & 1;
      }


   };

   struct mds_response
   {
      uint32_t status {0xffffffff};
      mds_response()
      {}

      int unpack(const std::string& s)
      {
         const size_t num_tokens {8};
         auto tokens = tokenize(s);
         if(tokens.size() != num_tokens)
            return -1;

         if(tokens[3] != "mds")
            return -2;

         status = std::stoll(tokens[5], nullptr, 16);

         return 0;
      }
   };

   struct rhv_response
   {
      uint16_t voltage {0xffff};
      uint16_t current {0xffff};

      rhv_response()
      {}

      int unpack(const std::string& s)
      {
         const size_t num_tokens {9};
         auto tokens = tokenize(s);
         if(tokens.size() != num_tokens)
            return -1;

         if(tokens[3] != "rhv")
            return -2;

         voltage = str_u16(tokens[5]);
         current = str_u16(tokens[6]);

         return 0;
      }
   };


   struct card_hkp_packet
   {
      bfsw::header header;
      const size_t expected_size {512}; //TODO update
      uint8_t version {0};
      uint8_t crate {0xff};
      uint8_t card {0xff};
      uint32_t flags {0};
      plr_response plr;
      rvia_response ria, rva;
      rhv_response rhv;
      tem_response tem;
      st_response st;
      mds_response mds;

      card_hkp_packet() : ria('i'), rva('v')
      {}

      int read_crate(std::string ip_address, int card, int timeout_ms)
      {
         int rc;
         bfsw::tcp_client client;
         rc = client.connect_to(ip_address, 1000, timeout_ms);
         if(rc != 0)
            return -1;

         auto greeting = client.recv_until("\n\r",timeout_ms*1E-3); //TODO check validity of greeting

         //plr
         client.send_full(cmd_plr(card), timeout_ms, 10);
         auto res = client.recv_until2("\r", timeout_ms * 1E-3);
         rc = plr.unpack(res.msg);
         if(rc < 0)
            flags |= 1 << 0;

         //rva
         client.send_full(cmd_rva(card), timeout_ms, 10);
         res = client.recv_until2("\r", timeout_ms * 1E-3);
         rc = rva.unpack(res.msg);
         if(rc < 0)
            flags |= 1 << 1;

         //ria
         client.send_full(cmd_ria(card), timeout_ms, 10);
         res = client.recv_until2("\r", timeout_ms * 1E-3);
         rc = ria.unpack(res.msg);
         if(rc < 0)
            flags |= 1 << 2;

         //rhv
         client.send_full(cmd_rhv(card), timeout_ms, 10);
         res = client.recv_until2("\r", timeout_ms * 1E-3);
         rc = rhv.unpack(res.msg);
         if(rc < 0)
            flags |= 1 << 3;

         //tem
         client.send_full(cmd_tem(card), timeout_ms, 10);
         res = client.recv_until2("\r", timeout_ms * 1E-3);
         rc = tem.unpack(res.msg);
         if(rc < 0)
            flags |= 1 << 4;

         //st
         client.send_full(cmd_st(card), timeout_ms, 10);
         res = client.recv_until2("\r", timeout_ms * 1E-3);
         rc = st.unpack(res.msg);
         if(rc < 0)
            flags |= 1 << 5;

         //mds
         client.send_full(cmd_mds(), timeout_ms, 10);
         res = client.recv_until2("\r", timeout_ms * 1E-3);
         rc = mds.unpack(res.msg);
         if(rc < 0)
            flags |= 1 << 6;

         return 0;
      }

      std::vector<uint8_t> make_packet(uint16_t counter, uint32_t timestamp)
      {
         auto bytes = bfsw::make_packet_stub(30, counter, 0, timestamp);
         size_t i = bytes.size();
         bytes.resize(1024,0xff);

         i += to_bytes(&bytes[i], version);
         i += to_bytes(&bytes[i], crate);
         i += to_bytes(&bytes[i], card);
         i += to_bytes(&bytes[i], flags);

         for(auto voltage : plr.voltage)
            i += to_bytes(&bytes[i], voltage);

         for(auto current : plr.current)
            i += to_bytes(&bytes[i], current);

         for(auto voltage : rva.values)
            i += to_bytes(&bytes[i], voltage);

         i += to_bytes(&bytes[i], rhv.voltage);
         i += to_bytes(&bytes[i], rhv.current);

         for(auto current : ria.values)
            i += to_bytes(&bytes[i], current);

         for(auto temp : tem.temperatures)
            i += to_bytes(&bytes[i], temp);

         i += to_bytes(&bytes[i], st.board_status);
         for(auto status : st.connector_status)
            i += to_bytes(&bytes[i], status);

         i += to_bytes(&bytes[i], mds.status);

         //set length field
         bytes.resize(i,0);
         spdlog::info("tracker_power hkp packet is {} bytes long", bytes.size());
         bfsw::set_header_length_field(bytes, bytes.size());
         return bytes;
      }

      template <typename T> int unpack(const T& bytes, size_t i)
      {
         //check expected size
         int rc;
         size_t i_start {i};
         rc = header.unpack(bytes, i);
         if(rc < 0)
            return -1;
         else
            i += rc;

         i += from_bytes(&bytes[i], version);
         i += from_bytes(&bytes[i], crate);
         i += from_bytes(&bytes[i], card);
         i += from_bytes(&bytes[i], flags);

         for(auto& voltage : plr.voltage)
            i += from_bytes(&bytes[i], voltage);

         for(auto& current : plr.current)
            i += from_bytes(&bytes[i], current);

         for(auto& voltage : rva.values)
            i += from_bytes(&bytes[i], voltage);

         i += from_bytes(&bytes[i], rhv.voltage);
         i += from_bytes(&bytes[i], rhv.current);

         for(auto& current : ria.values)
            i += from_bytes(&bytes[i], current);

         for(auto& temp : tem.temperatures)
            i += from_bytes(&bytes[i], temp);

         i += from_bytes(&bytes[i], st.board_status);
         for(auto& status : st.connector_status)
            i += from_bytes(&bytes[i], status);

         i += from_bytes(&bytes[i], mds.status);

         return i - i_start;
      }
   };

   class hkp_packet_db_writer
   {
      private:
          sqlite3_stmt *statement;
          std::vector<std::pair<std::string, std::string>> columns;

      public:
          hkp_packet_db_writer(sqlite3* const db)
          {
             columns.push_back({"gsemode", "integer"});
             columns.push_back({"gcutime", "integer"});
             columns.push_back({"counter", "integer"});
             columns.push_back({"length", "integer"});
             columns.push_back({"version", "integer"});
             columns.push_back({"crate", "integer"});
             columns.push_back({"card", "integer"});
             columns.push_back({"flags", "integer"});

             for(char c : std::string("abc"))
             {
                columns.push_back({fmt::format("lv_d3v8_{}",c), "integer"});
                columns.push_back({fmt::format("lv_d3i8_{}",c), "integer"});
                columns.push_back({fmt::format("lv_d2v8_{}",c), "integer"});
                columns.push_back({fmt::format("lv_d2i8_{}",c), "integer"});
                columns.push_back({fmt::format("lv_a3v3_{}",c), "integer"});
                columns.push_back({fmt::format("lv_a3i3_{}",c), "integer"});
                columns.push_back({fmt::format("lv_a2v8_{}",c), "integer"});
                columns.push_back({fmt::format("lv_a2i8_{}",c), "integer"});
             }

             for(int i = 1; i < 19; ++i)
             {
                columns.push_back({fmt::format("hv_voltage_{}",i), "integer"});
                columns.push_back({fmt::format("hv_current_{}",i), "integer"});
             }

             columns.push_back({"rhv_voltage","integer"});
             columns.push_back({"rhv_current","integer"});

             columns.push_back({"hv_tmp1","integer"});
             columns.push_back({"hv_tmp2","integer"});
             columns.push_back({"mcu_tmp","integer"});
             columns.push_back({"conn_tmp_a","integer"});
             columns.push_back({"mcu_tmp_a","integer"});
             columns.push_back({"conn_tmp_b","integer"});
             columns.push_back({"mcu_tmp_b","integer"});
             columns.push_back({"conn_tmp_c","integer"});
             columns.push_back({"mcu_tmp_c","integer"});

             columns.push_back({"board_status","integer"});
             columns.push_back({"conn_status_a","integer"});
             columns.push_back({"conn_status_b","integer"});
             columns.push_back({"conn_status_c","integer"});
             columns.push_back({"main_status","integer"});
             columns.push_back({"blob","blob"});

             std::string sql = "create table if not exists tracker_power(rowid integer not null primary key,";
             for(const auto& col : columns)
                sql += fmt::format("{} {},", col.first, col.second);
             sql.pop_back();
             sql += "); create unique index if not exists tracker_power_idx0 on tracker_power(gcutime, counter)";
             int rc = sqlite3_exec(db, sql.c_str(), nullptr, nullptr, nullptr);
             if(rc != SQLITE_OK)
             {
                fmt::print("failed to create tracker_power table\n");
                fmt::print("sqlite3 error: {}\n", sqlite3_errmsg(db));
                exit(-1);
             }

             sql = "insert into tracker_power(";
             for(const auto& col : columns)
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
                fmt::print("failed to create statement for tracker_power\n");
                fmt::print("sqlite3 error message: {}\n", sqlite3_errmsg(db));
                exit(-1);
             }
          }

          int insert(tracker_power::card_hkp_packet& p, int mode)
          {
             int rc = sqlite3_reset(statement);
             if(rc != SQLITE_OK)
                return -1;

             int j = 1;
             sqlite3_bind_int64(statement, j++, mode);
             sqlite3_bind_double(statement, j++, bfsw::timestamp_to_double(p.header.timestamp));
             sqlite3_bind_int64(statement, j++, p.header.counter);
             sqlite3_bind_int64(statement, j++, p.header.length);
             sqlite3_bind_int64(statement, j++, p.version);
             sqlite3_bind_int64(statement, j++, p.crate);
             sqlite3_bind_int64(statement, j++, p.card);
             sqlite3_bind_int64(statement, j++, p.flags);

             for(int i = 0; i < 3; ++i)
             {
                for(int k = 0; k < 4; ++k)
                {
                   sqlite3_bind_int64(statement, j++, p.plr.voltage[4*i + k]);
                   sqlite3_bind_int64(statement, j++, p.plr.current[4*i + k]);
                }
             }

             for(int i = 0; i < 18; ++i)
             {
                sqlite3_bind_int64(statement, j++, p.rva.values[i]);
                sqlite3_bind_int64(statement, j++, p.ria.values[i]);
             }

             sqlite3_bind_int64(statement, j++, p.rhv.voltage);
             sqlite3_bind_int64(statement, j++, p.rhv.current);

             for(int i = 0; i < 9; ++i)
                sqlite3_bind_int64(statement, j++, p.tem.temperatures[i]);

             sqlite3_bind_int64(statement, j++, p.st.board_status);
             for(int i = 0; i < 3; ++i)
                sqlite3_bind_int64(statement, j++, p.st.connector_status[i]);
             sqlite3_bind_int64(statement, j++, p.mds.status);

             rc = sqlite3_step(statement);
             if(rc != SQLITE_DONE)
                return -2;

             return 0;

          }
   };

   //command_id = 50
   int lv_onoff(std::string ip, int card, int mask, int onoff, int timeout_ms)
   {
      if(card < 1 || card > 10)
         return -1;

      const int voltage_threshold {5}; //units: volts
      const int current_threshold {5}; //units: nanoamps

      if(onoff == 0)
      {
         card_hkp_packet p;
         int rc = p.read_crate(ip, card, timeout_ms);
         if(rc != 0)
            return -100 + rc;
         if(p.flags != 0)
            return -2;

         if(p.rhv.voltage > voltage_threshold)
            return -3;

         if(p.rhv.current > current_threshold)
            return -4;

         //check each of 6 HV channels for specified LV channel
         for(int lv_ch = 0; lv_ch < 3; ++lv_ch)
         {
            if( !((mask >> lv_ch) & 1) )
               continue;

            for(int hv_ch = 0; hv_ch < 6; ++hv_ch)
            {
               auto hv_voltage = p.rva.values[(6*lv_ch) + hv_ch];
               auto hv_current = p.ria.values[(6*lv_ch) + hv_ch];
               if(hv_voltage > voltage_threshold)
               {
                  spdlog::warn("lv_onoff: voltage threshold check failed for lv_ch {} and hv_ch {}", lv_ch, hv_ch);
                  continue;
               }
               if(hv_current > current_threshold)
               {
                  spdlog::warn("lv_onoff: current threshold check failed for lv_ch {} and hv_ch {}", lv_ch, hv_ch);
                  continue;
               }
               //TODO check hv status bit
               std::string command = cmd_plw(card, lv_ch + 1, 1);
               spdlog::info("lv_onoff: command: {}", command);
               spdlog::info("lv_onoff: response: {}", transact(ip, command, timeout_ms));
            }
         }
         //TODO: what do we do about mds turnoff??? this would turn off the whole card, not just the specified connectors
         //could check that all LV connectors are off before powering card off
      }
      else
      {
         std::string command = cmd_md(card, 1);
         spdlog::info("lv_onoff: command: {}", command);
         spdlog::info("lv_onoff: response: {}", transact(ip, command, timeout_ms));

         for(int i = 0; i < 3; ++i)
         {
            if( !((mask >> i) & 1) )
               continue;

            command = cmd_plw(card, i + 1, 1);
            spdlog::info("lv_onoff: command: {}", command);
            spdlog::info("lv_onoff: response: {}", transact(ip, command, timeout_ms));
         }
      }

      return 0;
   }

   //command_id = 60
   int hv_on(std::string ip, int card, int mask, int hv, int timeout_ms)
   {
      if(card < 1 || card > 10)
         return -1;

      card_hkp_packet p;
      int rc = p.read_crate(ip, card, timeout_ms);
      if(rc != 0)
         return -100 + rc;
      if(p.flags != 0)
         return -2;

      std::string command, response;

      //TODO pre-conditions for ep and p?

      command = cmd_ep(card, 1);
      spdlog::info("hv_on: command: {}", command);
      spdlog::info("hv_on: response: {}", transact(ip, command, timeout_ms));

      command = cmd_p(card, 265);
      spdlog::info("hv_on: command: {}", command);
      spdlog::info("hv_on: response: {}", transact(ip, command, timeout_ms));

      //TODO check status after ep and p before proceeding?
      //TODO possibly short sleep before proceeding?

      //verify that lv is on for selected hv channels
      for(int hv_ch = 0; hv_ch < 18; ++hv_ch)
      {
         if( !((mask >> hv_ch) & 1) )
            continue;

         int lv_ch = hv_ch / 6; //TODO verify this mapping
         if(lv_ch < 0 || lv_ch > 2)
            return -3;

         auto d3v8 = p.plr.voltage[lv_ch*4 + 0];
         if(d3v8 < 3500)
         {
            spdlog::warn("hv_on: voltage check failed for hv_ch {}, d3v8 = {}", hv_ch, d3v8);
            continue;
         }
         auto d2v8 = p.plr.voltage[lv_ch*4 + 1];
         if(d2v8 < 2500)
         {
            spdlog::warn("hv_on: voltage check failed for hv_ch {}, d2v8 = {}", hv_ch, d2v8);
            continue;
         }
         auto a3v3 = p.plr.voltage[lv_ch*4 + 2];
         if(a3v3 < 3000)
         {
            spdlog::warn("hv_on: voltage check failed for hv_ch {}, a3v3 = {}", hv_ch, a3v3);
            continue;
         }
         auto a2v8 = p.plr.voltage[lv_ch*4 + 3];
         if(a2v8 < 2500)
         {
            spdlog::warn("hv_on: voltage check failed for hv_ch {}, a2v8 = {}", hv_ch, a2v8);
            continue;
         }

         //en
         command = cmd_en(card, hv_ch + 1, 1);
         spdlog::info("hv_on: command: {}", command);
         spdlog::info("hv_on: response: {}", transact(ip, command, timeout_ms));

         //sv
         command = cmd_sv(card, hv_ch + 1, hv);
         spdlog::info("hv_on: command: {}", command);
         spdlog::info("hv_on: response: {}", transact(ip, command, timeout_ms));
      }

      return 0;
   }

   //command_id = 65
   int hv_ramp_down(std::string ip, int card, int mask, int timeout_ms)
   {
      if(card < 1 || card > 10)
         return -1;

      for(int hv_ch = 0; hv_ch < 18; ++hv_ch)
      {
         if( !((mask >> hv_ch) & 1) )
            continue;

         std::string command = cmd_sv(card, hv_ch + 1, 0);
         spdlog::info("hv_ramp_down: command: {}", command);
         spdlog::info("hv_ramp_down: response: {}", transact(ip, command, timeout_ms));
      }

      //TODO tell Field that that en doesn't happen here, since ramp down takes a long time

      return 0;
   }

   //command_id = 66
   int hv_off(std::string ip, int card, int timeout_ms)
   {
      if(card < 1 || card > 10)
         return -1;

      card_hkp_packet p;
      int rc = p.read_crate(ip, card, timeout_ms);
      if(rc != 0)
         return -100 + rc;
      if(p.flags != 0)
         return -2;

      const int voltage_threshold {5}; //units: volts
      const int current_threshold {5}; //units: nanoamps

      //check rva and ria
      bool rva_ria_verified = true;
      for(int hv_ch = 0; hv_ch < 18; ++hv_ch)
      {
         if(p.rva.values[hv_ch] > voltage_threshold)
         {
            spdlog::warn("hv_off: failed hv voltage check for {}, voltage = {}", hv_ch, p.rva.values[hv_ch]);
            rva_ria_verified = false;
            break;
         }
         if(p.ria.values[hv_ch] > current_threshold)
         {
            spdlog::warn("hv_off: failed hv current check for ch {}, current = {}", hv_ch, p.ria.values[hv_ch]);
            rva_ria_verified = false;
            break;
         }
      }
      if(!rva_ria_verified)
         return -3;

      //check rhv
      bool rhv_verified = true;
      if(p.rhv.voltage > voltage_threshold)
      {
         spdlog::warn("hv_off: rhv voltage check failed, rhv.voltage = {}", p.rhv.voltage);
         rhv_verified = false;
      }
      if(p.rhv.current > current_threshold)
      {
         spdlog::warn("hv_off: rhv current check failed, rhv.current = {}", p.rhv.current);
         rhv_verified = false;
      }
      if(!rhv_verified)
         return -4;

      std::string command;

      //en
      for(int hv_ch = 0; hv_ch < 18; ++hv_ch)
      {
         command = cmd_en(card, hv_ch + 1, 0);
         spdlog::info("hv_off: command:{}\n response:{}", command, transact(ip, command, timeout_ms));
      }

      //p
      command = cmd_p(card, 0);
      spdlog::info("hv_off: command:{}\n response:{}", command, transact(ip, command, timeout_ms));

      //ep
      command = cmd_ep(card, 0);
      spdlog::info("hv_off: command:{}\n response:{}", command, transact(ip, command, timeout_ms));

      return 0;
   }
}

/*
   int verify_hv_off_rva_ria_rhv(std::string ip, int card, int timeout_ms)
   {
      //TODO rename to is_rva_ria_rhv_off

      //returns 0 if rva/ria/rhv are all below threshold (off)
      //otherwise, returns negative int

      const uint16_t voltage_threshold {10}; //units: volts
      const uint16_t current_threshold {10}; //units: nanoamps

      card_hkp_packet p;
      int rc = p.read_crate(ip, card, timeout_ms);
      if(rc != 0)
         return -1;
      if(p.flags != 0)
         return -2;
      bool good = true;
      for(auto voltage : p.rva.values)
         good = good && (voltage < voltage_threshold);
      if(!good)
         return -3;
      for(auto current : p.ria.values)
         good = good && (current < current_threshold); 
      if(!good)
         return -4;
      good = good && (p.rhv.voltage < voltage_threshold);
      if(!good)
         return -5;
      good = good && (p.rhv.current < current_threshold);
      if(!good)
         return -6;
      return 0;
   }

   int verify_hv_off_rva_ria(std::string ip, int card, int timeout_ms)
   {
      //TODO rename to is_rva_ria_off

      //returns 0 if rva/ria are all below threshold (off)
      //difference between this and is_hv_off1 is that this doesn't check rhv
      //otherwise, returns negative int

      const uint16_t voltage_threshold {10};
      const uint16_t current_threshold {10};

      card_hkp_packet p;
      int rc = p.read_crate(ip, card, timeout_ms);
      if(rc != 0)
         return -1;
      if(p.flags != 0)
         return -2;
      bool good = true;
      for(auto voltage : p.rva.values)
         good = good && (voltage < voltage_threshold);
      if(!good)
         return -3;
      for(auto current : p.ria.values)
         good = good && (current < current_threshold); //units: nanoamps
      if(!good)
         return -4;
      return 0;
   }

   int cmd_md_execute(std::string ip, int card, int onoff, int timeout_ms)
   {
      if(card < 1 || card > 10)
         return -1;

      if(onoff == 0)
      {
         int hv = verify_hv_off_rva_ria_rhv(ip, card, timeout_ms);
         if(hv != 0)
            return -100 + hv;
      }

      auto command = cmd_md(card, onoff);
      auto response = transact(ip, command, timeout_ms);
      spdlog::info("cmd_md_execute ip:{} card:{} onoff:{}", ip, card, onoff);
      spdlog::info("command: {}", command);
      spdlog::info("response: {}", response);
      return 0;
   }

   int cmd_plw_execute(std::string ip, int card, int ch, int onoff, int timeout_ms)
   {
      if(card < 1 || card > 10)
         return -1;

      if(ch < 1 || ch > 3)
         return -2;

      if(onoff == 0)
      {
         int hv = verify_hv_off_rva_ria_rhv(ip, card, timeout_ms);
         if(hv != 0)
            return -100 + hv;
      }

      auto command = cmd_plw(card, ch, onoff);
      auto response = transact(ip, command, timeout_ms);
      spdlog::info("cmd_plw_execute ip:{} card:{} ch:{} onoff:{}", ip, card, ch, onoff);
      spdlog::info("command: {}", command);
      spdlog::info("response: {}", response);
      return 0;
   }

   int cmd_ep_execute(std::string ip, int card, int onoff, int timeout_ms)
   {

      //TODO check that LV is on? 
      //but there is a possibility that we would disable an LV output
      //but still need to do "ep" and "p" for the other functional LV outputs

      //check channel status with st, only execute ep if hv enabled status bit is off

      if(card < 1 || card > 10)
         return -1;

      if(onoff == 0)
      {
         int hv = verify_hv_off_rva_ria(ip, card, timeout_ms); //checks rva/ria, but not rhv
         if(hv != 0)
            return -100 + hv;
      }

      auto command = cmd_ep(card, onoff);
      auto response = transact(ip, command, timeout_ms);
      spdlog::info("cmd_ep_execute ip:{} card:{} onoff:{}", ip, card, onoff);
      spdlog::info("command: {}", command);
      spdlog::info("response: {}", response);
      return 0;
   }

   int cmd_p_execute(std::string ip, int card, int hv, int timeout_ms)
   {

      //check channel status with st, only execute ep if hv enabled status bit is off

      if(card < 1 || card > 10)
         return -1;

      if(hv < 0 || hv > 255)
         return -2;

      if(onoff == 0)
      {
         int hv = verify_hv_off_rva_ria(ip, card, timeout_ms); //checks rva/ria, but not rhv
         if(hv != 0)
            return -100 + hv;
      }

      auto command = cmd_p(card, hv);
      auto response = transact(ip, command, timeout_ms);
      spdlog::info("cmd_p_execute ip:{} card:{} hv:{}", ip, card, hv);
      spdlog::info("command: {}", command);
      spdlog::info("response: {}", response);
      return 0;
   }

   int cmd_en_execute(std::string ip, int card, int ch, int onoff, int timeout_ms)
   {
      if(card < 1 || card > 10)
         return -1;

      if(ch < 1 || ch > 18)
         return -2;

      int hv = verify_hv_off_rva_ria(ip, card, timeout_ms); //checks rva/ria, but not rhv
      if(hv != 0)
         return -100 + hv;

      auto command = cmd_en(card, onoff);
      auto response = transact(ip, command, timeout_ms);
      spdlog::info("cmd_en_execute ip:{} card:{} ch:{} onoff:{}", ip, card, ch, onoff);
      spdlog::info("command: {}", command);
      spdlog::info("response: {}", response);
      return 0;
   }

   int verify_lv_on(std::string ip, int card, int ch, int timeout_ms)
   {

      //return 0 if LV connector ch (1 - 3) is on
      //otherwise, negative int

      //card check
      if(card < 1 || card > 10)
         return -1;

      //channel check, channel = 0 is invalid
      if(ch < 1 || ch > 3)
         return -2;
      
      card_hkp_packet p;
      int rc = p.read_crate(ip, card, timeout_ms);
      if(rc != 0)
         return -3;
      if(p.flags != 0)
         return -4;

      int offset = 4 * (ch - 1);
      if(p.plr.voltage[offset + 0] < 3500) //d3v8
         return -5;
      if(p.plr.voltage[offset + 1] < 2500) //d2v8
         return -6;
      if(p.plr.voltage[offset + 2] < 3000) //a3v3
         return -7;
      if(p.plr.voltage[offset + 3] < 2500) //a2v8
         return -8;

      return 0;
   }

   int cmd_sv_execute(std::string ip, int card, int ch, int hv, int timeout_ms)
   {

      //TODO consider sending sv command earlier as part of startup sequence
      //TODO ^ this would ensure that a spurious hv setting doesn't cause a problem
      //TODO verify that LV connector A is HV 1-6, LV B is HV 7-12, LV C is HV 13-18 

      if(card < 1 || card > 10)
         return -1;

      if(ch < 1 || ch > 18)
         return -2;

      if(hv < 0 || hv > 255)
         return -3;

      int lv_conn;
      if(ch >= 1 && ch <= 6)
         lv_conn = 1;
      else if(ch >= 7 && ch <= 12)
         lv_conn = 2;
      else
         lv_conn = 3;
      int lv = verify_lv_on(ip, card, lv_conn, timeout_ms);
      if(lv != 0)
         return -100 + lv;

      auto command = cmd_sv(card, ch, hv);
      auto response = transact(ip, command, timeout_ms);
      spdlog::info("cmd_sv_execute ip:{} card:{} ch:{} hv:{}", ip, card, ch, hv);
      spdlog::info("command: {}", command);
      spdlog::info("response: {}", response);
      return 0;
   }

   //problem: ramping takes time, need to wait for ramp down before disabling channel hv
*/















   /*

   int hv_on(std::string const& ip, int card, int channel_mask, int hv, int timeout_ms)
   {
      if(card < 1 || card > 10)
         return -1;

      if(hv < 0 || hv > 250)
         return -2;

      std::string command;

      //md
      command = cmd_md(card, 1);
      spdlog::info("hv_on2: command:{}\n response:{}", command, transact(ip, command, timeout_ms));

      int num_success = 0;
      for(int hv_channel = 0; hv_channel < 18; hv_channel++)
      {

         if( !((channel_mask >> hv_channel) & 1) )
            continue;

         //plw
         int lv_channel = hv_channel / 6; //TODO verify mapping
         command = cmd_plw(card, lv_channel + 1, 1);
         spdlog::info("hv_on2: plw hv_channel:{} lv_channel:{}", hv_channel, lv_channel);
         spdlog::info("hv_on2: command:{}\n response:{}", command, transact(ip, command, timeout_ms));

         //verify plr
         bool plr_verified = false;
         for(int tries = 0; tries < 5; ++tries)
         {
            card_hkp_packet p;
            int rc = p.read_crate(ip, card, timeout_ms);
            if(rc != 0)
            {
               spdlog::warn("hv_on2: read_crate failed, rc = {}", rc);
               continue;
            }
            if(p.flags != 0)
            {
               spdlog::warn("hv_on2: read_crate bad flags, flags = 0b{:b}",p.flags);
               continue;
            }

            auto d3v8 = p.plr.voltage[lv_channel*4 + 0];
            if(d3v8 < 3500)
            {
               spdlog::warn("hv_on2: voltage check failed for hv_channel {}, d3v8 = {}", hv_channel, d3v8);
               continue;
            }
            auto d2v8 = p.plr.voltage[lv_channel*4 + 1];
            if(d2v8 < 2500)
            {
               spdlog::warn("hv_on2: voltage check failed for hv_channel {}, d2v8 = {}", hv_channel, d2v8);
               continue;
            }
            auto a3v3 = p.plr.voltage[lv_channel*4 + 1];
            if(a3v3 < 3000)
            {
               spdlog::warn("hv_on2: voltage check failed for hv_channel {}, a3v3 = {}", hv_channel, a3v3);
               continue;
            }
            auto a2v8 = p.plr.voltage[lv_channel*4 + 1];
            if(a2v8 < 2500)
            {
               spdlog::warn("hv_on2: voltage check failed for hv_channel {}, a2v8 = {}", hv_channel, a2v8);
               continue;
            }

            plr_verified = true;
            break;
         }
         if(!plr_verified)
            continue; 

         //ep
         command = cmd_ep(card, 1);
         spdlog::info("hv_on2: command:{}\n response:{}", command, transact(ip, command, timeout_ms));

         //p
         command = cmd_p(card, 265);
         spdlog::info("hv_on2: command:{}\n response:{}", command, transact(ip, command, timeout_ms));

         //verify rhv 
         bool rhv_verified = false;
         for(int tries = 0; tries < 5; ++tries)
         {
            card_hkp_packet p;
            int rc = p.read_crate(ip, card, timeout_ms);
            if(rc != 0)
            {
               spdlog::warn("hv_on2: read_crate failed, rc = {}", rc);
               continue;
            }
            if(p.flags != 0)
            {
               spdlog::warn("hv_on2: read_crate bad flags, flags = 0b{:b}",p.flags);
               continue;
            }

            if(p.rhv.voltage < 250) //TODO figure out number here
               continue;

            rhv_verified = true;
            break;
         }
         if(!rhv_verified)
            continue;

         //en
         command = cmd_en(card, hv_channel + 1, 1);
         spdlog::info("hv_on2: command:{}\n response:{}", command, transact(ip, command, timeout_ms));

         //sv
         command = cmd_sv(card, hv_channel + 1, hv);
         spdlog::info("hv_on2: command:{}\n response:{}", command, transact(ip, command, timeout_ms));

         spdlog::info("hv_on2: SUCCESS card:{} hv_channel+1:{}", card, hv_channel + 1);
         num_success++;

      } //for hv_channel

      return num_success;
   }

   int hv_ramp_down(std::string const& ip, int card, int channel_mask, int timeout_ms)
   {
      if(card < 1 || card > 10)
         return -1;

      std::string command;

      for(int hv_channel = 0; hv_channel < 18; ++hv_channel)
      {

         if( !((channel_mask >> hv_channel) & 1) )
            continue;

         //sv
         command = cmd_sv(card, hv_channel + 1, 0);
         spdlog::info("hv_on2: command:{}\n response:{}", command, transact(ip, command, timeout_ms));
      }

      return 0;
   }

   int hv_disable(std::string const& ip, int card, int channel_mask, int timeout_ms)
   {
      if(card < 1 || card > 10)
         return -1;

      //read_crate
      card_hkp_packet p;
      int rc = p.read_crate(ip, card, timeout_ms);
      if(rc != 0)
         return -2;
      if(p.flags != 0)
         return -3;

      for(int hv_channel = 0; hv_channel < 18; ++hv_channel)
      {

         if( !((channel_mask >> hv_channel) & 1) )
            continue;

         //check rva and ria
         if(p.rva.values[hv_channel] > 5)
            continue;

         if(p.ria.values[hv_channel] > 5)
            continue;

         //en
         std::string command = cmd_en(card, hv_channel + 1, 0);
         spdlog::info("hv_on2: command:{}\n response:{}", command, transact(ip, command, timeout_ms));
      }

      return 0;
   }
}


*/
