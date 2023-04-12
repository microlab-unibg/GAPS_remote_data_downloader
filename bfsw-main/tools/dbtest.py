from peewee import Model,SqliteDatabase,IntegerField,ForeignKeyField
import numpy as np

db = SqliteDatabase(None,pragmas={'journal_mode':'wal','locking_mode':'deferred','cache_size':1<<16,'foreign_keys':1})

class Packet(Model):
	packet_id = IntegerField(primary_key=True)
	numevents = IntegerField()

	class Meta:
		database = db

	def ingest(self,events):
		self.numevents = len(events)
		self.save()
		packet_id = self.packet_id
		for event in events:
			E = Event()
			E.numhits = len(event)
			E.parent = packet_id
			E.save()
			event_id = E.event_id
			for hit in event:
				H = Hit()
				H.adc = hit
				H.parent = event_id
				H.save()

class Event(Model):
	parent = ForeignKeyField(Packet,field="packet_id",index=True)
	event_id = IntegerField(primary_key=True)
	numhits = IntegerField()

	class Meta:
		database = db

class Hit(Model):
	parent = ForeignKeyField(Event,field="event_id",index=True)
	hit_id = IntegerField(primary_key=True)
	adc = IntegerField()

	class Meta:
		database = db

def initialize(dbname):
	db.init(dbname)
	db.create_tables([Packet,Event,Hit])

def get_atomic():
	return db.atomic()

if __name__ == '__main__':
	initialize('test.sqlite')
	n = 100
	with get_atomic():
		for i in range(n):
			events = []
			for e in range(np.random.randint(5,10)):
				numhits = np.random.randint(1,20)
				events.append(list(np.random.randint(100,10000,numhits)))
			P = Packet()
			P.ingest(events)

'''
here is an example query that was tested and working in sqlitebrowser.
this is how i imagine the to-be-histogrammed event data will be queried.
except in a realistic case, we would probably update the where clause so 
that it selects on the packet time.

select packet.packet_id,packet.numevents,event.event_id,event.numhits,hit.adc
from hit
join event on hit.parent_id = event.event_id
join packet on event.parent_id = packet.packet_id
where packet.packet_id >= 20 and packet.packet_id <= 90
'''
