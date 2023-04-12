from argparse import ArgumentParser

p = ArgumentParser()
p.add_argument("--limit", type=int, default=8)
args = p.parse_args()

from rich.live import Live
from rich.table import Table
from pybfsw.gse.gsequery import GSEQuery
import time
import numpy as np

q = GSEQuery()


def make_table():

    global q
    rt = Table()
    tnow = time.time()
    data = q.tracker_query1(tnow - 10, tnow)
    data = np.array(data[-50:])

    for i in range(data.shape[1]):
        rt.add_column(f"c{i}")

    for row in data:
        rt.add_row(*[str(x) for x in row])

    return rt


with Live(make_table(), refresh_per_second=2) as live:
    time.sleep(0.5)
    while 1:
        live.update(make_table())
        time.sleep(2)
