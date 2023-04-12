import struct
from time import time
from peewee import Model,SqliteDatabase,FloatField,IntegerField,DoubleField,ForeignKeyField,CompositeKey,AutoField
from sys import path
import bfsw.bind.gaps_science_formats1_wrap as gaps
from bfsw.common import pdu_parse

#TODO maybe only index on gsetime and not gcutime? one potential issue is when reading raw data back into DB
#the gsetime field should be null in that case, in which case queries would be on gcutime.  

db = SqliteDatabase(None,pragmas={'journal_mode':'wal','locking_mode':'deferred','cache_size':1<<16,'foreign_keys':1})

class GfpTrackerPacket(Model):
	rowid = IntegerField(primary_key=True)
	#telem
	gcutime = DoubleField(index=True)
	counter = IntegerField()
	length    = IntegerField()

	sysid = IntegerField()
	systime = IntegerField()
	counter2 = IntegerField()
	numevents = IntegerField()

	class Meta:
		database = db

class GfpTrackerPacketHelper:
	def ingest(self,msg):
		rc = gaps.gfp_tracker_packet_helper(msg,len(msg),0)
		if(rc != 0):
			print('rc = ',rc)
			assert(False)


class GfpTrackerEvent(Model):
	parent = ForeignKeyField(GfpTrackerPacket,field='rowid',column_name='parent')
	rowid = IntegerField(primary_key=True)
	numhits = IntegerField()
	eventidvalid = IntegerField()
	eventid = IntegerField()
	eventtime = IntegerField()

	class Meta:
		database = db

class GfpTrackerHit(Model):
	parent = ForeignKeyField(GfpTrackerEvent,field='rowid',column_name='parent')
#rowid = IntegerField(primary_key=True)
	row = IntegerField()
	module = IntegerField()
	channel = IntegerField()
	adcdata = IntegerField()
	asiceventcode = IntegerField()

	class Meta:
		database = db
		without_rowid = True
		primary_key = CompositeKey('parent','row','module','channel')

class GfpTrackerCounters(Model):
	id = AutoField()
	#telem header
	gcutime = DoubleField(index=True)
	counter = IntegerField()
	length    = IntegerField()
	#daq header
	sysid = IntegerField()
	systime = IntegerField()
	counter2 = IntegerField()
	#counter body
	elapsed_time             = IntegerField()
	busy_time                = IntegerField()
	busy_count               = IntegerField()
	lv_sync_errors           = IntegerField()
	hv_sync_errors           = IntegerField()
	lv_packet_size_errors    = IntegerField()
	hv_packet_size_errors    = IntegerField()
	lv_backplane_activity    = IntegerField()
	hv_backplane_activity    = IntegerField()
	lv_words_valid           = IntegerField()
	hv_words_valid           = IntegerField()
	tof_triggers             = IntegerField()
	reboots                  = IntegerField()

	class Meta:
		database = db
		#consider without rowid, composite primary key on (timestamp,counter)

	def parse(self,msg):
		telem_header = struct.unpack('<xxxIHHxx',msg[:13])
		gcutime = telem_header[0]
		self.gcutime = (gcutime * 64E-3) + 1631030675.
		self.counter = telem_header[1]
		self.length  = telem_header[2]
		daq_header   = struct.unpack('<HHBBHHHI',msg[13:13+16])
		sync = daq_header[0]
		crc  = daq_header[1]
		self.sysid = daq_header[2]
		pktid = daq_header[3]
		payload_length = daq_header[4]
		self.counter2 = daq_header[5]
		systime_lsb  = daq_header[6]
		systime_msb  = daq_header[7]
		self.systime = (systime_msb << 16) | systime_lsb
		daq_body = struct.unpack('<IIIHHHHHHHHII',msg[13+16:13+16+36])
		self.elapsed_time      = daq_body[0]
		self.busy_time         = daq_body[1]
		self.busy_count        = daq_body[2]
		self.lv_sync_errors    = daq_body[3]
		self.hv_sync_errors    = daq_body[4]
		self.lv_packet_size_errors = daq_body[5]
		self.hv_packet_size_errors = daq_body[6]
		self.lv_backplane_activity = daq_body[7]
		self.hv_backplane_activity = daq_body[8]
		self.lv_words_valid = daq_body[9]
		self.hv_words_valid = daq_body[10]
		self.tof_triggers = daq_body[11]
		self.reboots = daq_body[12]

	def ingest(self,msg):
		self.parse(msg)
		self.save()

	






class Pdu0(Model):
	gsetime = DoubleField(index=True)
	gcutime = DoubleField(index=True)
	counter = IntegerField()
	vbus0   = IntegerField()
	vbus1   = IntegerField()
	vbus2   = IntegerField()
	vbus3   = IntegerField()
	vbus4   = IntegerField()
	vbus5   = IntegerField()
	vbus6   = IntegerField()
	vbus7   = IntegerField()
	vbus_avg0   = IntegerField()
	vbus_avg1   = IntegerField()
	vbus_avg2   = IntegerField()
	vbus_avg3   = IntegerField()
	vbus_avg4   = IntegerField()
	vbus_avg5   = IntegerField()
	vbus_avg6   = IntegerField()
	vbus_avg7   = IntegerField()
	vsense0   = IntegerField()
	vsense1   = IntegerField()
	vsense2   = IntegerField()
	vsense3   = IntegerField()
	vsense4   = IntegerField()
	vsense5   = IntegerField()
	vsense6   = IntegerField()
	vsense7   = IntegerField()
	vsense_avg0   = IntegerField()
	vsense_avg1   = IntegerField()
	vsense_avg2   = IntegerField()
	vsense_avg3   = IntegerField()
	vsense_avg4   = IntegerField()
	vsense_avg5   = IntegerField()
	vsense_avg6   = IntegerField()
	vsense_avg7   = IntegerField()
	vpower_acc0   = IntegerField()
	vpower_acc1   = IntegerField()
	vpower_acc2   = IntegerField()
	vpower_acc3   = IntegerField()
	vpower_acc4   = IntegerField()
	vpower_acc5   = IntegerField()
	vpower_acc6   = IntegerField()
	vpower_acc7   = IntegerField()
	temp0   = IntegerField()
	temp1   = IntegerField()
	temp2   = IntegerField()
	temp3   = IntegerField()
	temp4   = IntegerField()
	temp5   = IntegerField()
	temp6   = IntegerField()
	temp7   = IntegerField()
	vbat   = IntegerField()
	pducount = IntegerField()
	error = IntegerField()

	class Meta:
		database = db

	def parse(self,msg):
		#TODO use a cpp helper 

		d = pdu_parse.pdu_hkp_parse(msg)
		self.gcutime = d['gcu_time']
		self.counter = d['counter']
		ch = 0
		for i in [1,0]:
			for j in [2,1,4,3]:
				setattr(self,f'vbus{ch}',d[f'pac{i}_vbus{j}'])
				setattr(self,f'vbus_avg{ch}',d[f'pac{i}_vbus{j}_avg'])
				setattr(self,f'vsense{ch}',d[f'pac{i}_vsense{j}'])
				setattr(self,f'vsense_avg{ch}',d[f'pac{i}_vsense{j}_avg'])
				setattr(self,f'vpower_acc{ch}',d[f'pac{i}_vpower{j}_acc'])
				setattr(self,f'temp{ch}',d[f'temp{7-ch}'])
				ch += 1
		self.vbat = d['vbat']
		self.pducount = d['pducount']
		self.error = d['error']

	def ingest(self,msg):
		self.parse(msg)
		self.save()

class Pdu1(Pdu0):
	pass

class Labjack(Model):
	gsetime = DoubleField()
	gcutime = IntegerField()
	counter  = IntegerField()
	ain0 = FloatField()
	ain1 = FloatField()
	ain2 = FloatField()
	ain3 = FloatField()
	t20hz = IntegerField()

	class Meta:
		database = db

	def parse(self,msg):
		header = struct.unpack('>xxxiHxxxx',msg[:13])
		body   = struct.unpack('>81fI',msg[21:])
		self.gsetime = time()
		self.gcutime = header[0]
		self.counter = header[1]
		self.ain0 = body[0]
		self.ain1 = body[1]
		self.ain2 = body[2]
		self.ain3 = body[3]
		self.t20hz = body[81]

	def ingest(self,msg):
		self.parse(msg)
		self.save()

class LabjackStats(Model):
	gsetime = DoubleField()
	gcutime = IntegerField()
	counter  = IntegerField()
	good_query_count = IntegerField()
	bad_query_count = IntegerField()
	timer_count = IntegerField()

	class Meta:
		database = db

	def parse(self,msg):
		header = struct.unpack('>xxxiHxxxx',msg[:13])
		body   = struct.unpack('>BBB',msg[13:])
		self.gsetime = time()
		self.gcutime = header[0]
		self.counter = header[1]
		self.good_query_count = body[0]
		self.bad_query_count = body[1]
		self.timer_count = body[2]

	def ingest(self,msg):
		self.parse(msg)
		self.save()

class Sysmon(Model):
	gsetime = DoubleField()
	gcutime = IntegerField()
	counter  = IntegerField()
	hostid  = IntegerField()
	validmask = IntegerField() #TODO use bitfield
	cputotal = IntegerField()
	cpunum = IntegerField()
	memusage = IntegerField()
	swapusage = IntegerField()
	uptime = IntegerField()
	cpu0 = IntegerField()
	cpu1 = IntegerField()
	cpu2 = IntegerField()
	cpu3 = IntegerField()
	cpu4 = IntegerField()
	cpu5 = IntegerField()
	cpu6 = IntegerField()
	cpu7 = IntegerField()
	cpu8 = IntegerField()
	cpu9 = IntegerField()
	cpu10 = IntegerField()
	cpu11 = IntegerField()
	cpu12 = IntegerField()
	cpu13 = IntegerField()
	cpu14 = IntegerField()
	cpu15 = IntegerField()
	cputemp0 = IntegerField()
	cputemp1 = IntegerField()
	cputemp2 = IntegerField()
	cputemp3 = IntegerField()
	cputemp4 = IntegerField()
	cputemp5 = IntegerField()
	cputemp6 = IntegerField()
	cputemp7 = IntegerField()
	cputemp8 = IntegerField()
	cputemp9 = IntegerField()
	cputemp10 = IntegerField()
	cputemp11 = IntegerField()
	cputemp12 = IntegerField()
	cputemp13 = IntegerField()
	cputemp14 = IntegerField()
	cputemp15 = IntegerField()
	cputemp16 = IntegerField()
	cputemp17 = IntegerField()

	class Meta:
		database = db

	def parse(self,msg):
		header = struct.unpack('>xxxiHxxxx',msg[:13])
		body   = struct.unpack('>6BI16B18b',msg[13:])
		self.gsetime = time()
		self.gcutime = header[0]
		self.counter = header[1]
		self.hostid = body[0]
		self.validmask = body[1]
		self.cputotal = body[2]
		self.cpunum = body[3]
		self.memusage = body[4]
		self.swapusage = body[5]
		self.uptime = body[6]
		self.cpu0 = body[7]
		self.cpu1 = body[8]
		self.cpu2 = body[9]
		self.cpu3 = body[10]
		self.cpu4 = body[11]
		self.cpu5 = body[12]
		self.cpu6 = body[13]
		self.cpu7 = body[14]
		self.cpu8 = body[15]
		self.cpu9 = body[16]
		self.cpu10 = body[17]
		self.cpu11 = body[18]
		self.cpu12 = body[19]
		self.cpu13 = body[20]
		self.cpu14 = body[21]
		self.cpu15 = body[22]
		self.cputemp0 = body[23]
		self.cputemp1 = body[24]
		self.cputemp2 = body[25]
		self.cputemp3 = body[26]
		self.cputemp4 = body[27]
		self.cputemp5 = body[28]
		self.cputemp6 = body[29]
		self.cputemp7 = body[30]
		self.cputemp8 = body[31]
		self.cputemp9 = body[32]
		self.cputemp10 = body[33]
		self.cputemp11 = body[34]
		self.cputemp12 = body[35]
		self.cputemp13 = body[36]
		self.cputemp14 = body[37]
		self.cputemp15 = body[38]
		self.cputemp16 = body[39]
		self.cputemp17 = body[40]

	def ingest(self,msg):
		self.parse(msg)
		self.save()

class GcuPower(Model):
	gsetime = DoubleField()
	gcutime = IntegerField()
	counter  = IntegerField()
	v5    = FloatField() #use avg for now
	v12   = FloatField()
	v3v3  = FloatField()
	i5    = FloatField() #use avg for now
	i12   = FloatField()
	i3v3  = FloatField()

	class Meta:
		database = db

	def voltage(self,x):
		return 32. * (x/65535)

	def current(self,vsense,rsense=.050):
		fsc = 0.1/rsense
		return fsc * vsense / 65536.

	def parse(self,msg):
		header = struct.unpack('>xxxiHxxxx',msg[:13])
		self.gsetime = time()
		self.gcutime = header[0]
		self.counter = header[1]
		self.v5 = self.voltage(msg[47] << 8 | msg[48])
		self.v12 = self.voltage(msg[49] << 8 | msg[50])
		self.v3v3 = self.voltage(msg[51] << 8 | msg[52])
		self.i5 = self.current(msg[53] << 8 | msg[54])
		self.i12 = self.current(msg[55] << 8 | msg[56])
		self.i3v3 = self.current(msg[57] << 8 | msg[58])

	def ingest(self,msg):
		self.parse(msg)
		self.save()

def initialize(dbname):
	db.init(dbname)
	#hash table names + columns, possibly do a migration
	db.create_tables([Labjack,LabjackStats,Sysmon,GcuPower,Pdu0,Pdu1,GfpTrackerPacket,GfpTrackerEvent,GfpTrackerHit,GfpTrackerCounters])

def get_atomic():
	return db.atomic()

def parse(msg):
	ptype = msg[2]
	if ptype == 0:
		P = Labjack()
	elif ptype == 3:
		P = LabjackStats()
	elif ptype == 5:
		P = Sysmon()
	elif ptype == 6:
		P = GcuPower()
	elif ptype == 20:
		P = Pdu0()
	elif ptype == 21:
		P = Pdu1()
	elif ptype == 80:
		P = GfpTrackerPacketHelper()
	elif ptype == 81:
		return 
		#P = GfpTrackerCounters()
	else:
		print('unknown packet with type %d' % ptype)
		return
	P.ingest(msg)
