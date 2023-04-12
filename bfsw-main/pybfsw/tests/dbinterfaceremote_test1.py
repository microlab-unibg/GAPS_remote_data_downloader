from pybfsw.gse.gsequery import DBInterface
from argparse import ArgumentParser
p = ArgumentParse()
p.add_argument('table')
p.add_argument('column')
p.add_argument('start')
p.add_argument('stop')
args = p.parse_args()

dbi = DBInterface(path='local')
data = dbi.query(f'select gcutime,{args.column} from {args.table} where gcutime > {args.start} and gcutime < {args.stop}')
print(data)
