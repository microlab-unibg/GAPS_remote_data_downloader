from pybfsw.gse.gsequery import GSEQuery
from time import time

tf = time()
ti = tf - 10
q = GSEQuery()
d = q.time_query3('gfptrackerpacket:counter',ti,tf)
if d is None:
	print('no data found in given time range')
else:
	print(d)
