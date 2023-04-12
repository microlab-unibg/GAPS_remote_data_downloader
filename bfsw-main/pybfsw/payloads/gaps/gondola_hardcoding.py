# the Hardcoded class is a common repository for variables that are hard coded on the gondola 
# it tells us where things are plugged in 

# by Field rogers (fieldr@berkeley.edu)

class GAPSMaps():
	def __init__(self):
		

		# tracker 

		self.layers = [0,1,2,3,4,5,6,7,8,9]
		self.dummy_layers = [7,8,9]
		self.rows = [0,1,2,3,4,5]
		self.modules = [0,1,2,3,4,5]
		self.strips = range(4*8)

		# tracker power crate variables 

		connectors = ["c","b","a"] 	# LV, one per row, three per card
		self.tracker_power_channels = range(1,19) 		# HV, 6 per row, 18 per card
		crates = [1,2]
		cards = range(1,11)

		# map tracker layers and rows to tracker power crate variables
		self.tracker_power_card_mapping = {}
		for layer in self.layers:
			self.tracker_power_card_mapping[layer] = {}
			for row in self.rows:
				crate = layer%2
				card = layer + (layer+1)%2 + row//3
				connector = connectors[row%3]
				# to explain the logic above (c/o Gabe)
				# crate 0 is for even layers and crate 1 for odd so crate = layer%2
				# each crate has cards 1-10 with 2 cards per layer (card 1 and 2 power layer 0, 3 and 4 layer 1, etc)
				# layer number gives me simple ascending card order
				# (layer+1)%2 shifts even layers by 1 (0->1, 2->3, etc.) so even and odd layers have same card #s
				# row//3 offsets by 0 or 1 depending on if the row >= 3 (second half of layer)
				self.tracker_power_card_mapping[layer][row] = (crate, card, connector) # tuple (crate, card, connector

		# specify which ethernet port (0 or 1) to use for each crate:
		self.tracker_power_ethernet = {0:0,1:0}

		# map tracker power crate cards to layers and rows
		self.tracker_power_ASIC_mapping = {}
		for crate in crates:
			self.tracker_power_ASIC_mapping[crate] = {}
			for card in cards:
				self.tracker_power_ASIC_mapping[crate][card] = {}
				for i,connector in enumerate(connectors):
					layer = crate + card//2
					row = i + 3*(card%2)
					chans = self.tracker_power_channels[6*i:6*(i+1)]
					self.tracker_power_ASIC_mapping[crate][card][connector] = (layer,row,chans)


        # pdu

		self.pdu_channels = {}
		self.pdu_channels[0] = ["DAQ 0","DAQ 1","DAQ 2", "DAQ 3","Serial S","","",""]


		# serial server

		self.serial_server_ports = {0:"PDU RS 485",1:"PDU RS 232",2:"Thermal"}



