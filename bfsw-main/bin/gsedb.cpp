#include <czmq.h>
#include <cstdint>
#include <string>
#include <cstdio>
#include <cstdlib>
#include <sqlite3.h>
#include <spdlog/spdlog.h>
#include <gfp.hpp>
#include <tracker.hpp>
#include <event_builder.hpp>
#include <pdu.hpp>
#include <tracker_power.hpp>
#include <cooling.hpp>

//todo
// refactor: make db wrapper class with ctor/dtor, enforce ordering of writer and db dtors
// refactor: don't use pointers for writers
// refactor: move finalize() -> dtor for writers
// improve logging / stats

//functions
int data_callback(zloop_t *zloop, zsock_t *sock, void *arg);
int pair_callback(zloop_t *zloop, zsock_t *sock, void *arg);
int timer_callback(zloop_t *zloop, int timer_id, void *arg);
void help(int argc, char **argv);
int check_packet(uint8_t *buf, int len);
sqlite3* init_db(void);
int db_start_transaction(sqlite3 *db);
int db_end_transaction(sqlite3 *db);
int db_close(sqlite3 *db);

class sqlite_db
{
   public:
      sqlite3* db;
      sqlite_db(std::string path)
      {
         int rc = sqlite3_open(path.c_str(), &db);
         if(rc != SQLITE_OK)
         {
            spdlog::error("sqlite_db(): failed to open db, sqlite says: {}", sqlite3_errstr(rc));
            exit(-1);
         }

         std::string sql = "pragma foreign_keys = true;"
                           "pragma page_size = 65536;"
                           "pragma journal_mode = wal";
         rc = sqlite3_exec(db, sql.c_str(), nullptr, nullptr, nullptr);
         if(rc != SQLITE_OK)
            spdlog::warn("sqlite_db(): error executing pragmas, sqlite says: {}", sqlite3_errstr(rc));
      }

      ~sqlite_db()
      {
         int rc = sqlite3_close(db);
         if(rc != SQLITE_OK)
            spdlog::warn("~sqlite_db(): error closing db, sqlite says: {}", sqlite3_errstr(rc));
      }

      int start_transaction()
      {
         int rc = sqlite3_exec(db,"begin transaction",nullptr,nullptr,nullptr);
         if(rc != SQLITE_OK)
            spdlog::error("sqlite_db::start_transaction(): error starting transaction, sqlite says: {}", sqlite3_errstr(rc));
         return rc;
      }

      int end_transaction()
      {
         int rc = sqlite3_exec(db,"commit",nullptr,nullptr,nullptr);
         if(rc != SQLITE_OK)
            spdlog::error("db_start_transaction(): error ending transaction, sqlite says: {}", sqlite3_errstr(rc));
         return rc;
      }
};

//WIP
class app
{
   public:
      uint64_t n_good = 0;
      sqlite_db db;
      tracker::event_packet_db_writer tracker_event_packet_writer;
      tracker::counter_packet_db_writer tracker_counter_packet_writer;
      tracker::templeak_packet_db_writer tracker_templeak_packet_writer;
      tracker::gps_packet_db_writer tracker_gps_packet_writer;
      event_builder::merged_event_db_writer merged_event_writer;
      pdu::hkp_packet_db_writer pdu_hkp_packet_writer;

      app(std::string db_path) : 
         db(db_path),
         tracker_event_packet_writer(db.db),
         tracker_counter_packet_writer(db.db),
         tracker_templeak_packet_writer(db.db),
         tracker_gps_packet_writer(db.db),
         merged_event_writer(db.db),
         pdu_hkp_packet_writer(db.db)
      {
         //setup zmq, callbacks
      }

      ~app()
      {
         //for db writers, move finalize() code to dtor
         //then nothing needed here
      }
};



struct app_data
{
   uint64_t n_good;
   sqlite3 *db;
   std::unique_ptr<tracker::event_packet_db_writer> tracker_event_packet_writer;
   std::unique_ptr<tracker::counter_packet_db_writer> counter_packet_writer;
   std::unique_ptr<tracker::templeak_packet_db_writer> templeak_packet_writer;
   std::unique_ptr<tracker::gps_packet_db_writer> gps_packet_writer;
   std::unique_ptr<event_builder::merged_event_db_writer> merged_event_writer;
   std::unique_ptr<pdu::hkp_packet_db_writer> pdu_hkp_packet_writer;
   std::unique_ptr<tracker_power::hkp_packet_db_writer> tracker_power_writer;
   std::unique_ptr<cooling::hkp_packet_sqlite_writer> cooling_writer;


   app_data() : n_good(0)
   {
      db = init_db();
      if(db == nullptr)
      {
         spdlog::error("failed to open database");
         exit(-1);
      }
      tracker_event_packet_writer = std::make_unique<tracker::event_packet_db_writer>(db);
      counter_packet_writer = std::make_unique<tracker::counter_packet_db_writer>(db);
      templeak_packet_writer = std::make_unique<tracker::templeak_packet_db_writer>(db);
      gps_packet_writer = std::make_unique<tracker::gps_packet_db_writer>(db);
      merged_event_writer = std::make_unique<event_builder::merged_event_db_writer>(db);
      pdu_hkp_packet_writer = std::make_unique<pdu::hkp_packet_db_writer>(db);
      tracker_power_writer = std::make_unique<tracker_power::hkp_packet_db_writer>(db);
      cooling_writer = std::make_unique<cooling::hkp_packet_sqlite_writer>(db);

   }

   int start_transaction()
   {
      return db_start_transaction(db);
   }

   int end_transaction()
   {
      return db_end_transaction(db);
   }

   ~app_data()
   {
      end_transaction();
      tracker_event_packet_writer->finalize();
      counter_packet_writer->finalize();
      templeak_packet_writer->finalize();
      gps_packet_writer->finalize();
      db_close(db);
   }
};

int post_data(app_data *d, uint8_t *buf, size_t len, int mode);

//main
int main(int argc, char ** argv)
{

	int rc;

	help(argc,argv);

	app_data d;

	zloop_t *loop = zloop_new();
	assert(loop != nullptr);

	int timer = zloop_timer(loop,2000,0,timer_callback,&d);

	//setup sub socket
	std::string sub_addr = argv[1];
	zsock_t *sock = zsock_new_sub(sub_addr.c_str(),"");
	assert(sock != nullptr);
	zloop_reader(loop,sock,data_callback,&d);

	//setup pair socket
	zsock_t *pairsock = zsock_new_pair("");
	assert(pairsock != NULL);
	rc = zsock_bind(pairsock,"%s","ipc:///tmp/gsedbpair");
    if(rc != 0)
    {
       spdlog::error("failed to open pair socket");
       exit(-1);
    }
	zloop_reader(loop,pairsock,pair_callback,&d);

    d.start_transaction();

	//start the event loop
	rc = zloop_start(loop);
	if(rc == 0)
        spdlog::info("zloop interrupted");
	else
        spdlog::info("zloop cancelled by handler");

	zsock_destroy(&sock);
	zsock_destroy(&pairsock);

	return 0;
}

int timer_callback(zloop_t *zloop, int timer_id, void *arg)
{
	app_data *d = (app_data*) arg;

	//print some statistics
    spdlog::info("n_good = {}", d->n_good);

	//manage transaction
    d->end_transaction();
    d->start_transaction();

	return 0;
}

int pair_callback(zloop_t *zloop, zsock_t *sock, void *arg)
{
	//read socket
	app_data *d = (app_data*)arg;
	zframe_t *frame = zframe_recv(sock);
	uint8_t *buf = zframe_data(frame);
	int len = zframe_size(frame);

	const int mode = 2;
	int rc = post_data(d,buf,len,mode);

	zframe_destroy(&frame);

	return 0;

}

int data_callback(zloop_t *zloop, zsock_t *sock, void *arg)
{
	//read socket
	app_data *d = (app_data*)arg;
	zframe_t *frame = zframe_recv(sock);
	uint8_t *buf = zframe_data(frame);
	int len = zframe_size(frame);

	const int mode = 1;
	int rc = post_data(d,buf,len,mode);

	zframe_destroy(&frame);

	return 0;
}

int post_data(app_data *d, uint8_t *buf, size_t len, int mode)
{
    int rc;
	rc = check_packet(buf,len);
	if(rc < 0)
	{
        spdlog::warn("post_data(): bad packet, rc = {}",rc);
		return -1;
	}
    else
    {
       bfsw::array_wrapper bytes{buf, len};
       d->n_good++;
       switch(rc)
       {
          case 80:
             {
                tracker::event_packet p;
                rc = p.unpack(bytes,0);
                if(rc < 0)
                {
                   spdlog::warn("post_data(): failed to parse tracker::event_packet (80), rc = {}", rc);
                }
                else
                {
                   rc = d->tracker_event_packet_writer->insert(p, mode);
                   if(rc)
                      spdlog::warn("post_data(): bad insert for tracker::event_packet (80), rc = {}",rc);
                }
             }
             break;
          case 81:
             {
                tracker::counter_packet p;
                rc = p.unpack(bytes,0);
                if(rc < 0)
                {
                   spdlog::warn("post_data(): failed to parse tracker::counter_packet (81), rc = {}", rc);
                }
                else
                {
                   rc = d->counter_packet_writer->insert(p,mode);
                   if(rc)
                      spdlog::warn("post_data(): bad insert for tracker::counter_packet (81), rc = {}", rc);
                }

             }
             break;
          case 82:
             {
                tracker::gps_packet p;
                rc = p.unpack(bytes,0);
                if(rc < 0)
                {
                   spdlog::warn("post_data(): failed to parse tracker::gps_packet (82), rc = {}", rc);
                }
                else
                {
                   rc = d->gps_packet_writer->insert(p,mode);
                   if(rc)
                      spdlog::warn("post_data(): bad insert for tracker::gps_packet (82), rc = {}", rc);
                }
             }
             break;
          case 83:
             {
                tracker::templeak_packet p;
                rc = p.unpack(bytes,0);
                if(rc < 0)
                {
                   spdlog::warn("post_data(): failed to parse tracker::templeak_packet (83), rc = {}", rc);
                }
                else
                {
                   rc = d->templeak_packet_writer->insert(p,mode);
                   if(rc)
                      spdlog::warn("post_data(): bad insert for tracker::templeak_packet (83), rc = {}", rc);
                }
             }
             break;
          case 90:
             {
                event_builder::merged_event mev(0,1);
                rc = mev.unpack(bytes, 0);
                if(rc < 0)
                {
                   spdlog::warn("post_data(): event_builder::merged_event.deserialize() failed, rc = {}", rc);
                }
                else
                {
                   rc = d->merged_event_writer->insert(mev, mode, bytes);
                   if(rc)
                      spdlog::warn("post_data(): bad insert for event_builder::merged_event (90), rc = {}", rc);
                }
             }
             break;
          case 50:
             {
                pdu::hkp_packet p;
                rc = p.unpack(bytes, 0);
                if(rc < 0)
                {
                   spdlog::warn("pdu::hkp_packet.parse() failed, rc = {}",rc);
                }
                else
                {
                   rc = d->pdu_hkp_packet_writer->insert(p, mode);
                   if(rc != 0)
                      spdlog::warn("pdu_hkp_packet_writer->insert() failed, rc = {}",rc);
                }
             }
             break;

          case 30:
             {
                tracker_power::card_hkp_packet p;
                rc = p.unpack(bytes, 0);
                if(rc < 0)
                {
                   spdlog::warn("tracker_power::card_hkp_power::unpack failed, rc = {}", rc);
                }
                else
                {
                   rc = d->tracker_power_writer->insert(p, mode);
                   if(rc != 0)
                      spdlog::warn("tracker_power_writer->insert() failed, rc = {}", rc);
                }
             }
             break;
          case 40:
             {
                cooling::hkp_packet p;
                rc = p.unpack(bytes, 0);
                if(rc < 0)
                {
                   spdlog::warn("cooling::hkp_packet::unpack failed, rc = {}", rc);
                }
                else
                {
                   rc = d->cooling_writer->insert(p, mode);
                   if(rc != 0)
                      spdlog::warn("failed to insert cooling hkp packet, rc = {}", rc);
                }
             }
             break;

          default:
             break;
       }
    }

    return 0;

}

//return positive packet type on success
//return a negative int on failure
//TODO: compute checksum
int check_packet(uint8_t *buf, int len)
{
   if(len < 13)
      return -1;
   uint16_t eb90 = *((uint16_t*)&buf[0]);
   if(eb90 != 0x90EB)
      return -2;
   uint16_t plen = *((uint16_t*)&buf[9]);
   if(len != plen)
      return -3;

   return (int) buf[2];
}

void help(int argc,char ** argv)
{
   if(argc != 2)
   {
      fmt::print("1) ZeroMQ subscribe address.  e.g. ipc:///tmp/gse_pub\n");
      exit(-1);
   }
}

sqlite3* init_db(void)
{
   int rc;
   sqlite3* db;
   rc = sqlite3_open("gsedb.sqlite",&db);
   if(rc != SQLITE_OK)
   {
      spdlog::error("init_db(): failed, sqlite3 says: {}", sqlite3_errstr(rc));
      return NULL;
   }

   //set pragmas
   std::string sql = "pragma foreign_keys = true;"
      "pragma page_size = 65536;"
      "pragma journal_mode = wal";
   rc = sqlite3_exec(db,sql.c_str(),NULL,NULL,NULL);
   if(rc != SQLITE_OK)
      spdlog::error("error executing pragma statemens");

   return db;
}

int db_start_transaction(sqlite3 *db)
{
	int rc = sqlite3_exec(db,"begin transaction",NULL,NULL,NULL);
	if(rc != SQLITE_OK)
       spdlog::error("db_start_transaction(): error starting transaction, sqlite says: {}", sqlite3_errstr(rc));
	return rc;
}

int db_end_transaction(sqlite3 *db)
{
	int rc = sqlite3_exec(db,"commit",NULL,NULL,NULL);
	if(rc != SQLITE_OK)
       spdlog::error("db_start_transaction(): error ending transaction, sqlite says: {}", sqlite3_errstr(rc));
	return rc;
}

int db_close(sqlite3* db)
{
	int rc = sqlite3_close(db);
	if(rc != SQLITE_OK)
       spdlog::error("db_close(): error while closing db, sqlite says: {}", sqlite3_errstr(rc));
	return rc;
}

