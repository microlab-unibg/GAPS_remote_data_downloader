from pybfsw.gse.gsequery import GSEQuery
from time import time
from pybfsw.gse.parameter import Parameter,ParameterBank

p = Parameter('@counter','gfptrackerpacket','counter',converter=lambda x: (10*x,'raww'))
pb = ParameterBank([p])

tf = time()
ti = tf - 10
q = GSEQuery(parameter_bank = pb)
d = q.time_query3('@counter',ti,tf)
if d is None:
	print('no data found in time range')
else:
	print(d)
