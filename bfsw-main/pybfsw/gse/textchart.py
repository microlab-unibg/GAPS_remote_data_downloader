from argparse import ArgumentParser

p = ArgumentParser()
p.add_argument("table")
p.add_argument("--limit", type=int, default=8)
args = p.parse_args()

from rich.live import Live
from rich.table import Table
from pybfsw.gse.gsequery import GSEQuery
import time

q = GSEQuery()

names = q.get_column_names(args.table)


def make_table():

    global q, last
    rt = Table()
    data = q.get_latest_n_rows(args.table, args.limit)

    for name in names:
        rt.add_column(name)

    if data:
        for row in data:
            rt.add_row(*[str(x) for x in row[:-2]])

    return rt


with Live(make_table(), refresh_per_second=2) as live:
    time.sleep(0.5)
    while 1:
        live.update(make_table())
        time.sleep(2)
