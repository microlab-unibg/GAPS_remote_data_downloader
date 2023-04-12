#include <memory>
#include <utility>
#include <vector>
#include <array>
#include "sqlite3.h"

//! abstract base class for defining interface to 
//! packet classes
class PacketBase
{
	public:

		//! parse a raw byte buffer of tracker event data
		//! return 0 on success, and negative int on error
		virtual int Parse(const uint8_t* const b, int sz, int i) = 0;

		//! insert the data into the sqlite3
		//! database.  call this only after having parsed
		//! a buffer. the mode argument appears as a column
		//! in the db
		virtual int Insert(sqlite3* const db, int mode) = 0;

		//! clear internal data from previously parsed packet.
		//! call this method before parsing the next tracker
		//! event data packet buffer.
		virtual void Reset(void) = 0;

		//! finalize the sqlite3 prepared statements.  otherwise,
		//! closing the DB doesn't go as smoothly.  call this when
		//! you are done using this class for DB inserts (like when
		//! app is exiting)
		virtual void Finalize(void) = 0;
};

struct GfpTrackerHit
{
	int ChannelId;
	int ModuleId;
	int RowId;
	int AdcData;
	int AsicEventCode;
    size_t Serialize(std::vector<uint8_t>& bytes);
    int Deserialize(std::vector<uint8_t>& bytes, size_t i);
};
typedef std::shared_ptr<GfpTrackerHit> GfpTrackerHitPtr;

struct GfpTrackerEvent
{
	std::vector<GfpTrackerHitPtr> Hits;
	int NumHits;
	int EventIdValid;
    int Layer;
	uint32_t EventId;
	uint64_t EventTime;
    int Serialize(std::vector<uint8_t>& bytes);
    int Deserialize(std::vector<uint8_t>& bytes, size_t i);
};
typedef std::shared_ptr<GfpTrackerEvent> GfpTrackerEventPtr;

class GfpTrackerPacket : public PacketBase
{
	public: //members

		//telemetry header
		uint32_t mGcuTime;
		int mCounter;
		int mLength;
		int mChecksum;

		//daq header
		int mSysId;
		int mPacketId;
		int mDaqCount;
		uint64_t mSysTime;
		int mSettings1;
		int EB90;

		//event data
		std::vector<GfpTrackerEventPtr> mEvents;

		//database stuff
		bool mStatementsPrepared = false;
		sqlite3_stmt* mStmtPacket = NULL;
		sqlite3_stmt* mStmtEvent = NULL;
		sqlite3_stmt* mStmtHit = NULL;

		//misc
		bool mDataValid = false;
		bool mTableIsSetup = false;

	public: //methods

		int Parse(const uint8_t* const b, int sz, int i);
		int Insert(sqlite3* const db, int mode);
		void Reset(void);
		void Finalize(void);

		//! create the necessary sqlite3 tables for the
		//! tracker event data. returns 0 on success, and
		//! negative int on error
		static int CreateTables(sqlite3* const db);

};

class GfpTrackerCounters : public PacketBase
{
	public: //members

		//telem header
		uint32_t mGcuTime;
		int mCounter;
		int mLength;

		//daq header
		int mSysId;
		uint64_t mSysTime;
		int mCount;

		//daq body
		uint32_t mElapsedTime;
		uint32_t mBusyTime;
		uint32_t mBusyCount;
		int mLvSyncErrors;
		int mHvSyncErrors;
		int mLvPacketSizeErrors;
		int mHvPacketSizeErrors;
		int mLvBackplaneActivity;
		int mHvBackplaneActivity;
		int mLvWordsValid;
		int mHvWordsValid;
		uint32_t mTofTriggers;
		uint32_t mReboots;

		//misc
		bool mStatementsPrepared = false;
		bool mTableIsSetup = false;
		sqlite3_stmt* mStmt = NULL;
		bool mDataValid = false;

	public: //methods

		int Parse(const uint8_t* const b, int len, int i);
		int Insert(sqlite3* const db, int mode);
		void Reset(void){mDataValid = false;}
		void Finalize(void);

		//! create sqlite table.  return 0 on success
		//! or negative int on failure
		static int CreateTable(sqlite3* const db);
};

class GfpTrackerGps : public PacketBase
{
	public: //members

		//telem header
		uint32_t mGcuTime;
		int mCounter;
		int mLength;

		//daq header
		int mSysId;
		uint64_t mSysTime;
		int mCount;

		//daq body
		uint32_t mUtcTime;
		int mGpsInfo;

		//misc
		bool mStatementsPrepared = false;
		sqlite3_stmt* mStmt = NULL;
		bool mDataValid = false;
		bool mTableIsSetup = false;

	public: //methods
		GfpTrackerGps(void){};
		int Parse(const uint8_t* const b, int len, int i);
		static int CreateTable(sqlite3* const db);
		int Insert(sqlite3* const db, int mode);
		void Reset(void){mDataValid = false;}
		void Finalize(void);
};

class GfpTrackerTempleak : public PacketBase
{
	public:

		//telem header
		uint32_t mGcuTime;
		int mCounter;
		int mLength;

		//daq header
		int mSysId;
		int mCount;
		uint64_t mSysTime;

		//daq body
		int mRowOffset;
		std::array<std::array<int,6>,6> mTempleak;
		std::array<std::array<int,6>,6> mSEU;

		//misc
		bool mStatementsPrepared = false;
		sqlite3_stmt* mStmt = NULL;
		bool mDataValid = false;
		bool mTableIsSetup = false;

	public: //methods
		int Parse(const uint8_t* const b, int sz, int i);
		static int CreateTable(sqlite3* const db);
		int Insert(sqlite3* const db, int mode);
		void Reset(void){mDataValid = false;}
		void Finalize(void);
};
