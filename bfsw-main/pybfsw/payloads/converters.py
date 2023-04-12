import numpy as np

converter_map = {}
alias_map = {}

def labjack_ain_volts(y):
	return y,'volts'
for i in range(81):
	name = f'labjack:ain{i}'
	converter_map[name] = labjack_ain_volts
	alias_map[f'@ain{i}'] = name

def labjack_temp(y):
	return y,'deg K'
alias = '@labjacktemp'
alias_map[alias] = 'labjack:ain80'
converter_map[alias] = labjack_temp

def labjack_temp_c(y):
	return y - 273.15,'deg C'
alias = '@labjacktemp_c'
alias_map[alias] = 'labjack:ain80'
converter_map[alias] = labjack_temp_c

def labjack_t20hz(y):
	return y,'count'
converter_map['labjack:t20hz'] = labjack_t20hz
alias_map['@t20hz'] = 'labjack:t20hz'

def pdu_voltage(vbus):
	return (32./65536.) * vbus,'volts'

def pdu_current(v_sense):
	r_sense = 0.010
	fsc = 0.1/r_sense
	return (fsc/65536.) * v_sense,'amps'

def pdu_power(x):
	pass

def pdu_temp(x):
	volt = (2.5/(1<<12)) * x
	temp = (1/.010)*(volt - 0.750) + 25
	return temp,'deg C'

for i in range(8):
	alias = f'@vpdu{i}'
	alias_map[alias] = f'pdu0:vbus_avg{i}'
	converter_map[alias] = pdu_voltage
	alias = f'@ipdu{i}'
	alias_map[alias] = f'pdu0:vsense_avg{i}'
	converter_map[alias] = pdu_current
	alias = f'@tpdu{i}'
	alias_map[alias] = f'pdu0:temp{i}'
	converter_map[alias] = pdu_temp



'''
the below checks fail in the case that we have a converter for an alias, but 
but no converter for the unaliased parameter.  TODO: fix this
'''
'''
##################################
##################################
#check converter_map and alias_map
t = np.array([1.,2.,3.])
for name in converter_map:
	if name[0] == '@':
		assert(name in alias_map)
		name = alias_map[name]
	sp = name.split(':')
	assert(len(sp) == 2)
	tup = converter_map[name](t)
	assert(len(tup) == 2)
	array,unit = tup
	assert(isinstance(array,np.ndarray))
	assert(t.shape == array.shape)
	assert(isinstance(unit,str))
		
for name in alias_map:
	name = alias_map[name]
	sp = name.split(':')
	assert(len(sp) == 2)
'''
