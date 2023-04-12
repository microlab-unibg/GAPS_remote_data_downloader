from pybfsw.gse.gsequery import GSEQuery
from time import time
import numpy as np

tf = time()
ti = tf - 10
q = GSEQuery()
d = q.tracker_query1(ti,tf)
if d is None:
	print('no tracker data found in time range')
else:
	d = np.array(d)
	print('shape: ',d.shape)
	print(d)


