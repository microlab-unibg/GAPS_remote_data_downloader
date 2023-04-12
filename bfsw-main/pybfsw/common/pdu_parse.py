from pybfsw.common.packet_tools import header_formatter

def parse_pac1934(data,pacid=0):
	d = {}
	idx = 0;
	d[f'pac{pacid}_ctrl'] = data[idx]; idx += 1
	d[f'pac{pacid}_acc_count'] = (data[idx] << 16) | (data[idx+1] << 8) | data[idx+2]; idx += 3
	d[f'pac{pacid}_vpower1_acc'] = (data[idx] << 40) | (data[idx+1] << 32) | (data[idx+2] << 24) | (data[idx+3] << 16) | (data[idx+4] << 8) | data[idx+5]; idx += 6
	d[f'pac{pacid}_vpower2_acc'] = (data[idx] << 40) | (data[idx+1] << 32) | (data[idx+2] << 24) | (data[idx+3] << 16) | (data[idx+4] << 8) | data[idx+5]; idx += 6
	d[f'pac{pacid}_vpower3_acc'] = (data[idx] << 40) | (data[idx+1] << 32) | (data[idx+2] << 24) | (data[idx+3] << 16) | (data[idx+4] << 8) | data[idx+5]; idx += 6
	d[f'pac{pacid}_vpower4_acc'] = (data[idx] << 40) | (data[idx+1] << 32) | (data[idx+2] << 24) | (data[idx+3] << 16) | (data[idx+4] << 8) | data[idx+5]; idx += 6
	d[f'pac{pacid}_vbus1'] = (data[idx] << 8) | data[idx+1]; idx += 2
	d[f'pac{pacid}_vbus2'] = (data[idx] << 8) | data[idx+1]; idx += 2
	d[f'pac{pacid}_vbus3'] = (data[idx] << 8) | data[idx+1]; idx += 2
	d[f'pac{pacid}_vbus4'] = (data[idx] << 8) | data[idx+1]; idx += 2
	d[f'pac{pacid}_vsense1'] = (data[idx] << 8) | data[idx+1]; idx += 2
	d[f'pac{pacid}_vsense2'] = (data[idx] << 8) | data[idx+1]; idx += 2
	d[f'pac{pacid}_vsense3'] = (data[idx] << 8) | data[idx+1]; idx += 2
	d[f'pac{pacid}_vsense4'] = (data[idx] << 8) | data[idx+1]; idx += 2
	d[f'pac{pacid}_vbus1_avg'] = (data[idx] << 8) | data[idx+1]; idx += 2
	d[f'pac{pacid}_vbus2_avg'] = (data[idx] << 8) | data[idx+1]; idx += 2
	d[f'pac{pacid}_vbus3_avg'] = (data[idx] << 8) | data[idx+1]; idx += 2
	d[f'pac{pacid}_vbus4_avg'] = (data[idx] << 8) | data[idx+1]; idx += 2
	d[f'pac{pacid}_vsense1_avg'] = (data[idx] << 8) | data[idx+1]; idx += 2
	d[f'pac{pacid}_vsense2_avg'] = (data[idx] << 8) | data[idx+1]; idx += 2
	d[f'pac{pacid}_vsense3_avg'] = (data[idx] << 8) | data[idx+1]; idx += 2
	d[f'pac{pacid}_vsense4_avg'] = (data[idx] << 8) | data[idx+1]; idx += 2
	d[f'pac{pacid}_vpower1'] = (data[idx] << 24) | (data[idx+1] << 16) | (data[idx+2] << 8) | data[idx+3]; idx += 4
	d[f'pac{pacid}_vpower2'] = (data[idx] << 24) | (data[idx+1] << 16) | (data[idx+2] << 8) | data[idx+3]; idx += 4
	d[f'pac{pacid}_vpower3'] = (data[idx] << 24) | (data[idx+1] << 16) | (data[idx+2] << 8) | data[idx+3]; idx += 4
	d[f'pac{pacid}_vpower4'] = (data[idx] << 24) | (data[idx+1] << 16) | (data[idx+2] << 8) | data[idx+3]; idx += 4
	d[f'pac{pacid}_channel_dis'] = data[idx]; idx += 1;
	d[f'pac{pacid}_neg_pwr'] = data[idx]; idx += 1;
	d[f'pac{pacid}_slow'] = data[idx]; idx += 1;
	d[f'pac{pacid}_ctrl_act'] = data[idx]; idx += 1;
	d[f'pac{pacid}_channel_dis_act'] = data[idx]; idx += 1;
	d[f'pac{pacid}_neg_pwr_act'] = data[idx]; idx += 1;
	d[f'pac{pacid}_ctrl_lat'] = data[idx]; idx += 1;
	d[f'pac{pacid}_channel_dis_lat'] = data[idx]; idx += 1;
	d[f'pac{pacid}_neg_pwr_lat'] = data[idx]; idx += 1;
	d[f'pac{pacid}_pid'] = data[idx]; idx += 1; #pacid = 0x5B
	d[f'pac{pacid}_mid'] = data[idx]; idx += 1; #mid = 0x5D
	d[f'pac{pacid}_rev'] = data[idx]; idx += 1; #rev = 0x03 

	return d

def current(v_sense,r_sense=.010):
	fsc = 0.1/r_sense
	return fsc * v_sense / 65536.

def voltage(x):
	return 32. * (x/65535.)

def ads_temp(x):
	voltage = (x/(1<<12)) * 2.5
	voltage = (x * 2.5)/(1 << 12)
	temp = ((voltage - 0.750)/.010) + 25
	return voltage

def pdu_hkp_parse(data):

	d = {}
	assert(len(data) == 218)
	xeb,x90,ptype,gcu_time,counter,pkt_length,checksum = header_formatter.unpack(data[0:13])
	d['gcu_time'] = gcu_time
	d['counter'] = counter
	idx = 13
	assert(data[idx] == 0xAA)
	d['type'] = data[idx]; idx += 1
	d['id'] = data[idx]; idx += 1
	d.update([(f'temp{i}',(data[idx + 2*i] << 8) | data[idx + 1 + 2*i]) for i in range(8)]); idx += 16;
	d.update(parse_pac1934(data[idx:],pacid=0)); idx += 88
	d.update(parse_pac1934(data[idx:],pacid=1)); idx += 88
	assert(d['pac0_pid'] == 0x5B)
	assert(d['pac1_pid'] == 0x5B)
	d['vbat'] = (data[idx + 1] << 8) | data[idx]; idx += 2
	idx += 2
	d['pducount'] = data[idx]; idx += 1
	d['error'] = data[idx]; idx += 1

	return d


		





'''
if __name__ == '__main__':
	from serial import Serial
	from argparse import ArgumentParser
	from time import sleep
	p = ArgumentParser()
	p.add_argument('--port',default='/dev/ttyUSB0')
	a = p.parse_args()

	while 1:
		
		s = Serial(a.port, baudrate=9600, bytesize=8, parity='N', stopbits=1)
		s.write(b'hkp\r\n')
		data = s.read_until(b'ACK\r\n')
		print('len = ',len(data),'head = ',hex(data[0]))
		pac0 = parse_pac1934(data[17:17+88])
		pac1 = parse_pac1934(data[17+88:17+88+88])
		pac0_volts = list(map(lambda x: 32.*(x/65535),[pac0['vbus1_avg'],pac0['vbus2_avg'],pac0['vbus3_avg'],pac0['vbus4_avg']]))
		pac1_volts = list(map(lambda x: 32.*(x/65535),[pac1['vbus1_avg'],pac1['vbus2_avg'],pac1['vbus3_avg'],pac1['vbus4_avg']]))
		print('pac0_volts',pac0_volts)
		print('pac1_volts',pac1_volts)
		sleep(1)
'''
		
	


'''

		volts = list(map(lambda x: 32.*(x/65535),[vbus1_avg,vbus2_avg,vbus3_avg]))
		currents = list(map(current,[vsense1_avg,vsense2_avg,vsense3_avg]))
		print('vbus_avg: ',volts)
		print('current_avg: ',currents)
		print('pid: ',hex(pid),' mid: ',hex(mid),' rev: ',hex(rev))
		# prints [5.000564583810178, 0.0, 3.2930189974822612]

'''

		

