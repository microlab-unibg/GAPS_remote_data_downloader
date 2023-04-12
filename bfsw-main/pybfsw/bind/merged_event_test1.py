from sqlite3 import connect

conn = connect("gsedb_merged_events_only.sqlite")
row = conn.execute("select * from mergedevent where rowid = 308092").fetchone()
blob = row[-1]
print(blob)

from merged_event_bindings import merged_event
mev = merged_event()
rc = mev.unpack_str(blob, 0)
print("rc = ",rc)
print("event_id = ",mev.event_id)
print("mev.tof_data = ",mev.tof_data)
print("mev.tracker_events.size() = ",len(mev.tracker_events))
for event in mev.tracker_events:
    print("event time: ", event.event_time)
    print("event id: ", event.event_id)
    for hit in event.hits:
        print("adc: ", hit.adc)

