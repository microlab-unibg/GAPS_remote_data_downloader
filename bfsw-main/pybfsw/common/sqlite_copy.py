from sqlite3 import connect
from argparse import ArgumentParser
from pybfsw.gse.gsequery import DBInterface
p = ArgumentParser()
p.add_argument('path')
p.add_argument('fname_out')
p.add_argument('t1')
p.add_argument('t2')
p.add_argument('--exclude')
p.add_argument('--batch_size',default=100000)
args = p.parse_args()

#TODO option to create indexes, do this at the very end (after inserts)

dbi = DBInterface(args.path)
c_out = connect(f"file:{args.fname_out}?mode=rwc")
tables = dbi.query("select name from sqlite_master where type='table' and name not like 'sqlite_%';")
tables = [t[0] for t in tables]

for table in tables:

    try:
        table_create_stmt = dbi.query(f"select sql from sqlite_master where name == '{table}'")[0][0] #depending on version, may need "sqlite_schema" instead of "sqlite_master"
        c_out.execute(table_create_stmt)
        rows = dbi.query(f"select * from {table} where gcutime >= {args.t1} and gcutime <= {args.t2}")
        if rows:
            ncols = len(rows[0])
            qm = ','.join(['?'] * ncols)
            c_out.executemany(f"insert into {table} values({qm})", rows)
            c_out.commit()

    except Exception as ex:
        print(f"failed on table {table}, exception: ",ex)

'''

# handle gfptrackerevent (no gcutime column)
res = c_in.execute(f"select min(rowid),max(rowid) from gfptrackerpacket where gcutime >= {args.t1} and gcutime <= {args.t2}").fetchall()
packet_row_min, packet_row_max = res[0]
res = c_in.execute(f"select * from gfptrackerevent where parent >= {packet_row_min} and parent <= {packet_row_max}")
while True:
    rows = res.fetchmany(args.batch_size)
    if rows:
        ncols = len(rows[0])
        qm = ','.join(['?'] * ncols)
        c_out.executemany(f"insert into gfptrackerevent values({qm})",rows)
        c_out.commit()
    else:
        break

# handle gfptracker hit
res = c_out.execute(f"select min(rowid),max(rowid) from gfptrackerevent").fetchall()
event_row_min,event_row_max = res[0]
res = c_in.execute(f"select * from gfptrackerhit where parent >= {event_row_min} and parent <= {event_row_max}")
while True:
    rows = res.fetchmany(args.batch_size)
    if rows:
        ncols = len(rows[0])
        qm = ','.join(['?'] * ncols)
        c_out.executemany(f"insert into gfptrackerhit values({qm})",rows)
        c_out.commit()
    else:
        break

# indexes 
index_names = [t[0] for t in c_in.execute("select name from sqlite_master where type == 'index'").fetchall()]
for index in index_names:
    create_statement = c_in.execute(f"select sql from sqlite_schema where name == '{index}'").fetchall()[0][0]
    c_out.execute(create_statement)
    c_out.commit()
'''

c_out.close()
