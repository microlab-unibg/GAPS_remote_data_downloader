import numpy as np
import yaml
from argparse import ArgumentParser
p = ArgumentParser()
p.add_argument('nevents',type=int)
args = p.parse_args()

events = []

for i in range(args.nevents):
	#counter and timestamp are assigned in following script
	event = {}
	event['count1'] = i

	#tracker
	num_layers = int(np.min((np.round(np.random.exponential(2)),10))) #quasi exponential distribution limited to range [0,10]
	layers = np.random.choice(np.arange(10),size=num_layers,replace=False) #choose the layers
	for l in layers:
		num_hits = int(np.min((np.round(1+np.random.exponential(6)),144))) #144 strips per layer
		hits = np.random.choice(np.arange(144),size=num_hits,replace=False) #choose the hit strip IDs
		event[int(l)] = [{'id':int(h),'adc':8888} for h in hits]

	#tof
	num_paddles = int(np.min((np.round(2 + np.random.exponential(5)),220))) #assuming 220 TOF paddles, can't remember total number
	paddles = np.random.choice(np.arange(220),size=num_paddles,replace = False)
	event['tof'] = [{'id':int(p),'c1':110,'c2':120,'t1':130,'t2':140} for p in paddles]

	events.append(event)

s = yaml.dump(events)
with open('out.out','w') as f:
	f.write(s)
