from sqlite3 import connect
from argparse import ArgumentParser
p = ArgumentParser()
p.add_argument('fname_in')
p.add_argument('fname_out')
p.add_argument('t1')
p.add_argument('t2')
p.add_argument('--exclude')
p.add_argument('--batch_size',default=100000)
args = p.parse_args()

c_in = connect(f"file:{args.fname_in}?mode=ro")
c_out = connect(f"file:{args.fname_out}?mode=rwc")
# todo no clobber on c_out 

tables = c_in.execute("select name from sqlite_master where type='table' and name not like 'sqlite_%';").fetchall()
tables = [t[0] for t in tables]

for table in tables:

    try:
        table_create_stmt = c_in.execute(f"select sql from sqlite_schema where name == '{table}'").fetchall()[0][0]
        # index create stmt?
        c_out.execute(table_create_stmt)
        res = c_in.execute(f"select * from {table} where gcutime >= {args.t1} and gcutime <= {args.t2}")
        while True:
            rows = res.fetchmany(args.batch_size)
            if rows:
                ncols = len(rows[0])
                print('ncols',ncols)
                qm = ','.join(['?'] * ncols)
                c_out.executemany(f"insert into {table} values({qm})", rows) 
                c_out.commit()
            else:
                break
    except:
        print(f"failed on table {table}")

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

c_in.close()
c_out.close()
