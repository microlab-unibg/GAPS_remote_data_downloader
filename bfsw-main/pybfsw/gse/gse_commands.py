# The Commander class is used to send commands
# from the GSE to the flight computer 
# 
# Running this program requires either a yaml-formatted command
# or a yaml config file as a command-line argument 
#
# All of the commands are documented in sample config files 
# located in bfsw/pybfsw/gse/com_config/run_all_<subsystem>_commands.yaml
#
# need to connect to GSE db to query on db
# to run on any computer, first do ssh -p 55225 -L 44555:localhost:44555 gaps@gamma1.ssl.berkeley.edu
# and then ensure GSE_DB_PATH is set to 127.0.0.1:44555
# 
# by Field Rogers <fieldr@berkeley.edu> or, if deprecated, <field.rogers.ssl@gmail.com>

import sys,zmq,yaml,os
from time import sleep
from pybfsw.gse.gsequery import GSEQuery
from pybfsw.payloads.gaps.gondola_hardcoding import GAPSMaps

gaps_map = GAPSMaps()    


class Commander():
    def __init__(self,com_list=None,config=None,zmq_addr='tcp://192.168.37.200:48112',verbose=False,path=None):
        
        self.verbose=verbose

        self.path=path
        
        # open a pair socket
        context = zmq.Context()
        self.socket = context.socket(zmq.PAIR)
        self.socket.setsockopt(zmq.LINGER,1000) # allows program to close if not able to send commands NOTE 
        self.socket.connect(zmq_addr)


        # parse commands from command line 
        if com_list != None: 
            try: 
                com = yaml.safe_load(" ".join(com_list))
                if self.verbose: print (com)
                self.parse_command_type(com)
            except: 
                print ("couldn't parse", " ".join(com_list), "as yaml")

        # parse commands from yaml command file
        if config != None: 
            print ("parsing commands in", config)
            with open(config,"r") as stream: 
                try: 
                    com_list = (yaml.safe_load(stream))
                except yaml.YAMLError as exc: 
                    print (exc)
                    sys.exit(1)
            if self.verbose: 
                print ("\nCommand lists:")
                for com in com_list: print(com)
                print ("\nParsing commands:")
            for command_dict in com_list: 
                if self.verbose: print (command_dict) #key + " : " + str(value))
                self.parse_command_type(command_dict)
            print ("finished parsing commands!") 
        
        self.socket.close()
        print ("closed socket") 
        context.term() 
        print ("terminated context")

    def parse_command_type(self,command_dict):
        for key in command_dict: # should only be one key per dict passed to this function
            if key == "pdu_on": self.pdu_on(command_dict[key])
            elif key == "pdu_off": self.pdu_off(command_dict[key])
           
            elif key == "sleep" or key == "wait": self.wait(float(command_dict[key]))
            
            elif key == "rh_ctrl_on": self.rh_ctrl_on(command_dict[key])
            elif key == "rh_ctrl_off": self.rh_ctrl_off(command_dict[key])
            elif key == "rh_dcdc_on": self.rh_dcdc_on(command_dict[key])
            elif key == "rh_dcdc_off": self.rh_dcdc_off(command_dict[key])
            elif key == "rh_switch": self.rh_switch(command_dict[key])
            elif key == "rsv_rtd_switch": self.rsv_rtd_switch(command_dict[key])
            elif key == "sh_on": self.sh_on(command_dict[key])
            elif key == "sh_off": self.sh_off(command_dict[key])
            elif key == "sh_dcdc_on": self.sh_dcdc_on(command_dict[key])
            elif key == "sh_dcdc_off": self.sh_dcdc_off(command_dict[key])

            elif key == "tracker_power_card_on": self.tracker_power_card_on_off(command_dict[key],on_off=1)
            elif key == "tracker_power_card_off": self.tracker_power_card_on_off(command_dict[key], on_off=0)
            elif key == "tracker_power_lv_on": self.tracker_power_lv_on_off(command_dict[key],on_off = 1)
            elif key == "tracker_power_lv_off": self.tracker_power_lv_on_off(command_dict[key],on_off = 0)
            elif key == "tracker_power_hv_supply_on": self.tracker_power_hv_supply_on_off(command_dict[key],on_off=1)
            elif key == "tracker_power_hv_supply_off": self.tracker_power_hv_supply_on_off(command_dict[key],on_off=0)
            elif key == "tracker_power_hv_supply_set": self.tracker_power_hv_supply_setting(command_dict[key])
            elif key == "tracker_power_hv_channel_set": self.tracker_power_hv_channel_setting(command_dict[key])
            elif key == "tracker_power_hv_on": self.tracker_power_hv_on_off(command_dict[key],on_off = 1)
            elif key == "tracker_power_hv_off": self.tracker_power_hv_on_off(command_dict[key],on_off = 0)
            elif key == "tracker_power_turn_on_lv": self.tracker_power_turn_lv_on_off(command_dict[key],on_off=1)
            elif key == "tracker_power_turn_off_lv": self.tracker_power_turn_lv_on_off(command_dict[key],on_off=0)
            elif key == "tracker_power_turn_on_hv": self.tracker_power_turn_hv_on(command_dict[key])
            #elif key == "tracker_power_turn_off_hv": self.tracker_power_turn_hv_on_off(command_dict[key],on_off = 0)
            elif key == 'tracker_power_ramp_down_hv': self.tracker_power_ramp_down_hv(command_dict[key])
            elif key== 'tracker_power_power_off_hv': self.tracker_power_power_off_hv(command_dict[key])

            else : print ("Command type", key, "is not reconized!!! \n\n")

    #################################
    # Possible config file commands #
    #################################

    # timeout

    def wait(self, t):
        print("\t- waiting for", t,"seconds... ")
        sleep(t)

    # pdu

    def pdu_on(self,pdu_on_dict):
        
        for key in pdu_on_dict: 
            if key == 'pdu0' or key == 'pdu1' or key == 'pdu2':
                pdu = int(key[-1])
                for chan in pdu_on_dict[key]:
                    if chan in range(8):
                        self.pdu_on_off_command(pdu,chan,1)
                        print ("\t- turning on pdu", pdu," channel ", chan)
                    else: print ("Error: pdu", pdu, "chan ", chan, "is not a valid pdu channel!!!\n")
            else: print ("Error: Invalid pdu specification!! ", key, "is not a valid pdu designation!!!\n")

    def pdu_off(self,pdu_off_dict):
        
        for key in pdu_off_dict: 
            if key == 'pdu0' or key == 'pdu1' or key == 'pdu2':
                pdu = int(key[-1])
                for chan in pdu_off_dict[key]:
                    if chan in range(8):
                        self.pdu_on_off_command(pdu,chan,0)
                        print ("\t- turning off pdu", pdu," channel ", chan)
                    else: print ("Error: pdu", pdu, "chan ", chan, "is not a valid pdu channel!!!\n")
            else: print ("Error: Invalid pdu specification!! ", key, "is not a valid pdu designation!!!\n")

    # thermal

    def rh_ctrl_on(self,rh_ctrl_on_dict):
        temp_on, temp_off = -45.5,-45.0
        try: temp_on = rh_ctrl_on_dict["temp_on"]
        except: pass
        try: temp_off = rh_ctrl_on_dict["temp_off"]
        except: pass

        self.thermal_command(1,arg1=self.rtd_to_binary(temp_on), arg2=self.rtd_to_binary(temp_off))
        print("\t- turning on reservoir heater control! Heater on:",temp_on, "C; Heater off:",temp_off, "C")

        # NOTE - any checks to add? 

    def rh_ctrl_off(self, check): 
        if check == 0: 
            self.thermal_command(2)
            print("\t- turning off reservoir heater control")
        else: print ("Warning! Bad value for rh_ctrl_off check: ", check, "!!!\n")

    def rh_dcdc_on(self,dcdcs): 
        for dcdc in dcdcs: 
            if dcdc == "24V":
                self.thermal_command(11)
                print("\t- activating reservoir heater 24V DCDC converter")
            elif dcdc == "12V": 
                self.thermal_command(12)
                print("\t- activating reservoir heater 12V DCDC converter")
            
            else: print ("Warning! Bad value for rh dcdc activation:", dcdc, "!!!\n")

    def rh_dcdc_off(self, check):
        if check == 0:
            self.thermal_command(13)
            print("\t- deactivating reservoir heater DCDC converters")
        else: print ("Warning! Bad value for rh_dcdc_off check", check, "!!!\n")

    def rh_switch(self, check): 
        if check == 0: 
            self.thermal_command(21)
            print ("\t- switching the reservoir heater and its power line into spare")
        else: print ("Warning! Bad value for rh_dcdc_switch check", check, "!!!\n")

    def rsv_rtd_switch(self, check):
        if check == 0: 
            self.thermal_command(22)
            print("\t- switching the reservoir RTD into spare")
        else: print ("Warning! Bad value for rsv_rtd_switch check", check, "!!!\n")

    def sh_on(self, sh_dic): 
        for sh in sh_dic:
            if sh == 'sh1' or sh =='sh2' or sh =='sh3': # command with default time of 60
                self.thermal_command(29+2*int(sh[-1]),arg1=60) 
                print ("\t- turning on subheater", sh, "on-off, for default of 60 s")  
            elif (type(sh) is dict):
                for shkey in sh:
                    if shkey == "sh1" or shkey == "sh2" or shkey == "sh3":
                        on_time = sh[shkey] # see if argumement for time was passed
                        self.thermal_command(29+2*int(shkey[-1]),arg1=on_time)### NOTE need to test ON toime!!
                        print ("\t- turning on subheater", shkey, "on-off, for", on_time, "s")
                    else: print ("Warning! Bad value for sh_on", sh, "!!!\n")
            else: print ("Warning! Bad value for sh_on", sh, "!!!\n")

    def sh_off(self, sh_list):
        for sh in sh_list: 
            if sh == 'sh1' or sh =='sh2' or sh =='sh3':
                self.thermal_command(30+2*int(sh[-1]))
                print ("\t- turning off subheater", sh, "on-off")
            else: print ("Warning! Bad value for sh_off", sh, "!!!\n")
    
    def sh_dcdc_on(self, dcdc_list):
        for dcdc in dcdc_list: 
            if dcdc == "48V": 
                self.thermal_command(41)
                print("\t- activating",dcdc, "DCDC converter for subheater")
            elif dcdc == "38V": 
                self.thermal_command(42)
                print("\t- activating",dcdc, "DCDC convertor for subheater")
            elif dcdc == "24V": 
                self.thermal_command(43)
                print("\t- activating", dcdc, "DCDC convertor for subheaters")
            else: print ("Warning! Bad value for sh_dcdc_activate", dcdc, "!!!\n") 

    def sh_dcdc_off(self, check):
        if check == 0: 
            self.thermal_command(44)
            print("\t- deactivating all DCDC convertors for subheaters")
        else: print ("Warning! Bad value for sh_dcdc_off check", check, "!!!\n")

    # tracker power

    def tracker_power_card_on_off(self,tracker_power_on_off_dict,on_off):
        if not on_off in range(2):
            print ("bad value")
            return -10
        for key in tracker_power_on_off_dict: 
            if key == 'crate0' or key == 'crate1':
                crate_id = int(key[-1])
                for card_id in tracker_power_on_off_dict[key]:
                    if card_id in range(1,11):

                        if on_off == 0 and not self.check_hv_off(crate_id,card_id,0):
                            return -1

                        self.tracker_power_command(com_id=10,data=on_off,crate_id=crate_id,card_id=card_id)
                        if on_off == 1: print ("\t- turning on tracker power crate", crate_id,"card",card_id)
                        else: print ("\t- turning off tracker power crate", crate_id,"card",card_id)
                    #elif card_id == 0: # CAN WE turn on all cards at once? 
                    #    self.tracker_power_command(crate_id=crate_id, )
                    else: print ("Error: tracker power card", card_id, "is not valid!!!\n")
            else: print ("Error: Invalid tracker power specification!! ", key, "is not a valid crate designation!!!\n")

    # should we only be able to turn on all three connectors at once, and only turn on card (10) if also turn on lv?
    def tracker_power_lv_on_off(self,tracker_power_lv_on_off_dict,on_off):
        if not on_off in range(2):
            print ("bad value")
            return -10
        for key in tracker_power_lv_on_off_dict:
            if key == 'crate0' or key == 'crate1':
                crate_id = int(key[-1])
                for card in tracker_power_lv_on_off_dict[key]:
                    card_id=int(card[4:])
                    if card_id in range(1,11):
                        for conn_id in tracker_power_lv_on_off_dict[key][card]:
                            if conn_id in range(4):

                                if on_off == 0 and not self.check_hv_off(crate_id,card_id,conn_id):
                                    return -1

                                self.tracker_power_command(com_id=20,data=on_off,crate_id=crate_id,card_id=card_id,conn_id = conn_id)
                                if on_off == 1: print ("\t- turning on lv for tracker power crate", crate_id,"card",card_id, "connector", conn_id)#  should specify A, B, C, or 0
                                else: print ("\t- turning off lv for tracker power crate", crate_id,"card",card_id, "connector", conn_id)#  should specify A, B, C, or 0
                            else: print("Error: tracker power connector", conn_id,"is not a valid connector identifier.\n Should be 1 (A), 2 (B), 3 (C), or 0 (all)!\n")
                    #elif card_id == 0: # CAN WE turn on all cards at once? 
                    #    self.tracker_power_command(crate_id=crate_id, )
                    else: print ("Error: tracker power card", card, "is not valid!!!\n")
            else: print ("Error: Invalid tracker power specification!! ", key, "is not a valid crate designation!!!\n")

    def tracker_power_hv_supply_on_off(self,tracker_power_hv_supply_on_off_dict,on_off):
        if not on_off in range(2):
            print ("bad value")
            return -10
        for key in tracker_power_hv_supply_on_off_dict: 
            if key == 'crate0' or key == 'crate1':
                crate_id = int(key[-1])
                for card_id in tracker_power_hv_supply_on_off_dict[key]:
                    if card_id in range(1,11):

                        if on_off == 0 and not self.check_hv_off(crate_id,card_id): # do not turn off if hv is on 
                            return -1

                        if on_off == 1 and not self.check_lv_on(crate_id,card_id): # do not turn on if lv is off
                            return -1

                        self.tracker_power_command(com_id=30,data=on_off,crate_id=crate_id,card_id=card_id)
                        if on_off == 1: print ("\t- turning on hv power supply for tracker power crate", crate_id,"card",card_id)
                        else: print ("\t- turning off hv power supply for tracker power crate", crate_id,"card",card_id)
                    #elif card_id == 0: # CAN WE turn on all cards at once? 
                    #    self.tracker_power_command(crate_id=crate_id, )
                    else: print ("Error: tracker power card", card_id, "is not valid!!!\n")
            else: print ("Error: Invalid tracker power specification!! ", key, "is not a valid crate designation!!!\n")

    def tracker_power_hv_supply_setting(self,tracker_power_hv_supply_setting_dict):
        set_v = 250
        try: 
            set_v = tracker_power_hv_supply_setting_dict["set_v"]
            if not set_v in range(2**8): 
                print ("Error: tracker power hv setting ", set_v, "is not an int in range(256)\n")
                return
        except:
            if self.verbose: print ("reverting to default voltage setting of",set_v,"V")
        for key in tracker_power_hv_supply_setting_dict: 
            if key == 'crate0' or key == 'crate1':
                crate_id = int(key[-1])
                for card_id in tracker_power_hv_supply_setting_dict[key]:
                    if card_id in range(1,11):
                        self.tracker_power_command(com_id=32,data=set_v,crate_id=crate_id,card_id=card_id)
                        print ("\t- setting hv power supply to",set_v,"for tracker power crate", crate_id,"card",card_id)
                    #elif card_id == 0: # CAN WE turn on all cards at once? 
                    #    self.tracker_power_command(crate_id=crate_id, )
                    else: print ("Error: tracker power card", card_id, "is not valid!!!\n")
            elif key == "set_v": pass
            else: print ("Error: Invalid tracker power specification!! ", key, "is not a valid crate designation!!!\n")

    def tracker_power_hv_channel_setting(self,tracker_power_hv_channel_setting_dict):
        set_v = 250
        try: 
            print(set_v)
            set_v = tracker_power_hv_channel_setting_dict["set_v"]
            print(set_v)
            if not set_v in range(2**8): 
                print ("Error: tracker power hv setting ", set_v, "is not an int in range(256)\n")
                return
        except:
            if self.verbose: print ("reverting to default voltage setting of",set_v,"V")
        for key in tracker_power_hv_channel_setting_dict: 
            if key == 'crate0' or key == 'crate1':
                crate_id = int(key[-1])
                for card in tracker_power_hv_channel_setting_dict[key]:
                    card_id = int(card[4:])
                    if card_id in range(11):
                        for chan in tracker_power_hv_channel_setting_dict[key][card]:
                            self.tracker_power_command(com_id=34,data=set_v,crate_id=crate_id,card_id=card_id,chan_id=chan)
                            if chan == 0: print ("\t- setting the HV at ", set_v,"volts for all channels on tracker power crate", crate_id,"card",card_id)
                            else: print ("\t- setting the HV at ", set_v,"volts for channel", chan,"on tracker power crate", crate_id,"card",card_id)
                    #elif card_id == 0: # CAN WE turn on all cards at once? 
                    #    self.tracker_power_command(crate_id=crate_id, )
                    else: print ("Error: tracker power card", card_id, "is not valid!!!\n")
            elif key == "set_v": pass
            else: print ("Error: Invalid tracker power specification!! ", key, "is not a valid crate designation!!!\n")

    def tracker_power_hv_channel_setting(self,tracker_power_hv_channel_setting_dict):
        set_v = 250
        try: 
            set_v = tracker_power_hv_supply_setting_dict["set_v"]
            if not set_v in range(2**8): 
                print ("Error: tracker power hv setting ", set_v, "is not an int in range(256)\n")
                return
        except:
            pass # default is 250
        for key in tracker_power_hv_channel_setting_dict: 
            if key == 'crate0' or key == 'crate1':
                crate_id = int(key[-1])
                for card in tracker_power_hv_channel_setting_dict[key]:
                    card_id = int(card[4:])
                    if card_id in range(11):
                        for chan in tracker_power_hv_channel_setting_dict[key][card]:
                            self.tracker_power_command(com_id=34,data=set_v,crate_id=crate_id,card_id=card_id,chan_id=chan)
                            if chan == 0: print ("\t- setting the HV at ", set_v,"volts for all channels on tracker power crate", crate_id,"card",card_id)
                            else: print ("\t- setting the HV at ", set_v,"volts for channel", chan,"on tracker power crate", crate_id,"card",card_id)
                    #elif card_id == 0: # CAN WE turn on all cards at once? 
                    #    self.tracker_power_command(crate_id=crate_id, )
                    else: print ("Error: tracker power card", card_id, "is not valid!!!\n")
            elif key == "set_v": pass
            else: print ("Error: Invalid tracker power specification!! ", key, "is not a valid crate designation!!!\n")
    
    def tracker_power_hv_on_off(self,tracker_power_hv_on_off_dict,on_off):
        if not on_off in range(2):
            print ("bad value")
            return -10
        for key in tracker_power_hv_on_off_dict:
            if key == 'crate0' or key == 'crate1':
                crate_id = int(key[-1])
                for card in tracker_power_hv_on_off_dict[key]:
                    card_id = int(card[4:])
                    if card_id in range(11):
                        for chan in tracker_power_hv_on_off_dict[key][card]:
                        
                            if on_off == 1 and not self.check_lv_on(crate_id,card_id,chan_id=chan): # do not turn on if lv is off
                                return -1

                            self.tracker_power_command(com_id=40,data=on_off,crate_id=crate_id,card_id=card_id,chan_id=chan)
                            if chan == 0: print ("\t- turning on the HV for all channels on tracker power crate", crate_id,"card",card_id)
                            else: print ("\t- turning on the HV for channel", chan,"on tracker power crate", crate_id,"card",card_id)
                    #elif card_id == 0: # CAN WE turn on all cards at once? 
                    #    self.tracker_power_command(crate_id=crate_id, )
                    else: print ("Error: tracker power card", card_id, "is not valid!!!\n")
            elif key == "set_v": pass
            else: print ("Error: Invalid tracker power specification!! ", key, "is not a valid crate designation!!!\n")

    def tracker_power_turn_lv_on_off(self, tracker_power_turn_lv_on_off_dict,on_off):
        if not on_off in range(2):
            print ("bad value")
            return -10
        crate_id, card_id, conns = -1, -1, []
        try:
            crate_id = tracker_power_turn_lv_on_off_dict["crate"]
            card_id = tracker_power_turn_lv_on_off_dict["card"]
        except: 
            print ("Error: need to specify a crate value, a card value, and a channel value to turn on lv card.")
            return -5
        try: conns = tracker_power_turn_lv_on_off_dict["conn"]
        except: conns = [0]
        
        # byte specifies connectors to turn on as 0b00000CBA
        conn_id_bitwise = 0b0
        for conn in conns: 
            if conn in range(1,4): conn_id_bitwise |= 2**(conn-1)
            elif conn == 0: conn_id_bitwise |= 0b111
            else: print("Warning!!", conn, "is not a valid connector identifier!!\n")

            # check that HV is off if sending "turn off" command
            if on_off == 0 and not self.check_hv_off(crate_id,card_id,conn):
                return -1
        self.tracker_power_command(com_id=50,data=on_off,crate_id=crate_id,card_id=card_id,conn_bitwise=conn_id_bitwise)
        if on_off: print ("\t- turning on the LV card and power for connectors", conns,"on tracker power crate",crate_id,"card",card_id)
        else: print ("\t- turning off the LV card and power for connectors", conns,"on tracker power crate",crate_id,"card",card_id)

    def tracker_power_turn_hv_on(self, tracker_power_turn_hv_on_dict):
        crate_id, card_id, chans,pset,vset = -1, -1, [],255,250
        try: 
            crate_id = tracker_power_turn_hv_on_dict["crate"]
            card_id = tracker_power_turn_hv_on_dict["card"]
            chans = tracker_power_turn_hv_on_dict["chan"]
        except: 
            print ("Error: need to specify a crate value, a card value, and a channel value to turn on and ramp up hv card.")
            return -5
        try: pset = tracker_power_turn_hv_on_dict["pset"]
        except: 
            if self.verbose: print("No Power supply setting specified, defaulting to 255 V")
        try: vset = tracker_power_turn_hv_on_dict["vset"]
        except: 
            if self.verbose: print ("No HV bias voltage setting specified, defaulting to 250 V")

        # 3 bytes specify channels to turn on as 0b00000CBA
        chan_id_bitwise = [0b0,0b0,0b0]
        for chan in chans:
            if chan in range(1,9): chan_id_bitwise[0] |= 2**(chan-1)
            elif chan in range(9,17): chan_id_bitwise[1] |= 2**(chan-9)
            elif chan in range(17,19): chan_id_bitwise[2] |= 2**(chan-17)
            elif chan == 0: chan_id_bitwise [0b11111111,0b11111111,0b00000011]
            else: print("Warning!!", chan, "is not a valid channel identifier!!\n")

            # check that LV is on if sending "turn on" command
            if not self.check_lv_on(crate_id,card_id,chan):
                return -1
        self.tracker_power_command(com_id=60,crate_id=crate_id,card_id=card_id,p_set=pset,v_set=vset,chan_bitwise=chan_id_bitwise)
        print ("\t- turning on the HV card and powering up channels", chans,"on tracker power crate",crate_id,"card",card_id)

    def tracker_power_ramp_down_hv(self, tracker_power_ramp_down_hv_dict):
        crate_id, card_id, chans = -1, -1, []
        try: 
            crate_id = tracker_power_ramp_down_hv_dict["crate"]
            card_id = tracker_power_ramp_down_hv_dict["card"]
        except: 
            print ("Error: need to specify a crate value and a card value to ramp down the hv.")
            return -5
        try: chans = tracker_power_ramp_down_hv_dict["chan"]
        except: 
            chans = [0]
            if self.verbose: print ("defaulting to all channels")

        # 3 bytes specify channels to turn on as 0b00000CBA
        chan_id_bitwise = [0b0,0b0,0b0]
        for chan in chans:
            if chan in range(1,9): chan_id_bitwise[0] |= 2**(chan-1)
            elif chan in range(9,17): chan_id_bitwise[1] |= 2**(chan-9)
            elif chan in range(17,19): chan_id_bitwise[2] |= 2**(chan-17)
            elif chan == 0: chan_id_bitwise = [0b11111111,0b11111111,0b00000011]
            else: print("Warning!!", chan, "is not a valid channel identifier!!\n")

        self.tracker_power_command(com_id=65,crate_id=crate_id,card_id=card_id,chan_bitwise=chan_id_bitwise)
        print ("\t- ramping down HV for channels", chans,"on tracker power crate",crate_id,"card",card_id)

    def tracker_power_power_off_hv(self, tracker_power_power_off_hv_dict):
        crate_id, card_id, chans = -1, -1, []
        try: 
            crate_id = tracker_power_power_off_hv_dict["crate"]
            card_id = tracker_power_power_off_hv_dict["card"]
        except: 
            print ("Error: need to specify a crate value and a card value to turn off the hv card.")
            return -5

        if not self.check_hv_off(crate_id,card_id):
            return -1

        self.tracker_power_command(com_id=66,crate_id=crate_id,card_id=card_id)
        print ("\t- powering off HV card",card_id,"on tracker power crate",crate_id)



    ###################################
    # final subsystem-level functions #
    ###################################

    def pdu_on_off_command(self,pdu,chan,com):
        
        # check that all input is valid. If we got to this point with an error, something has gone wrong
        if not pdu in range(3):
            print (pdu,"is not a valid pdu number")
            sys.exit(1) # should write to sys.sterr
        if not chan in range(8):
            print (chan," is not a valid channel number")
            sys.exit(1) # shoulw write to sys.sterr
        if not com in range(2):
            print (com, "is not a valid on/off command")
            sys.exit(1) # should write to sys.sterr

        # calculate command id
        com_id = chan + 8*(1-com) + 16*pdu
        #if (self.verbose): print (pdu,chan,com,com_id)
        
        b = self.make_bytearray(50,com_id)
        self.write_to_pair(b)

    def thermal_command(self, byte2, arg1=0, arg2=0):
        
        arg1bytes = arg1.to_bytes(2,byteorder='big',signed=False) # NOTE: confirm byteorder 'big' vs 'little'
        arg2bytes = arg2.to_bytes(2,byteorder='big',signed=False) 
        #print (arg1bytes, arg1bytes[0],arg1bytes[1], hex(arg1bytes[0]),arg2bytes)

        # first build the thermal command payload
        pl = bytearray()
        pl.append(0xE1)         # byte 1 - header # NOTE - check with alex this is correct
        pl.append(byte2)        # byte 2 - code  #NOTE check with alex this is correct if byte2 is an int
        pl.append(arg1bytes[0]) # bytes 3-4 - arg 1
        pl.append(arg1bytes[1])
        pl.append(arg2bytes[0]) # bytes 4-5 - arg 2
        pl.append(arg2bytes[1])
        pl.append(self.xor_check(pl))# byte 7 - checksum
        
        # then make a general command with the thermal address and append the payload
        b = self.make_bytearray(40,100,len_payload=len(pl),payload=pl)
        
        self.write_to_pair(b)

    def tracker_power_command(self,com_id,crate_id,card_id,data=None,conn_id=None,chan_id=None,p_set=None,v_set=None,conn_bitwise=None,chan_bitwise=None):
        if not crate_id in range(2):
            print (crate_id,"not a valid tracker power crate number")
            sys.exit(1) # should write to sys.sterr
        
        if not card_id in range(1,11):
            print(card_id, "is not a valid card number for the tracker power crate!")
            sys.exit(1)

        if not conn_id == None and not conn_id in range(4):
            print (conn_id, "is not a valid connector number for the tracker power crate!")
            sys.exit(1)

        if not chan_id == None and not chan_id in range(19):
            print (conn_id, "is not a valid connector number for the tracker power crate!")
            sys.exit(1)

        if not data == None and not data in range(256): 
            print (data,"is out of range")
            sys.exit(1)

        # one byte gives you:
        # the card number (1-10; 0 == all 10), 
        # crate number (0 or 1) 
        # the ethernet number (0 or 1)
        card_identifier = card_id + 32*crate_id + 16*gaps_map.tracker_power_ethernet[crate_id]

        # arguments for the command
        pl = bytearray()
        if not data == None: pl.append(data)                 # eg the hv voltage, default 1
        if not p_set == None:           # for tracker_power_turn_hv_on/off only
            pl.append(p_set)
            pl.append(v_set)
        pl.append(card_identifier)      # gives you the crate, ethernet switch, and card id
        if not conn_id == None: pl.append(conn_id)
        elif not chan_id == None: pl.append(chan_id)
        elif not conn_bitwise == None: pl.append(conn_bitwise)
        elif not chan_bitwise == None: 
            for byte_N in chan_bitwise: pl.append(byte_N)
        b = self.make_bytearray(sys_addr=30,com_id=com_id,len_payload=len(pl),payload=pl)

        self.write_to_pair(b)

    
    def make_bytearray(self,sys_addr,com_id,len_payload=0,payload=None):
        
        b = bytearray()
        b.append(0xEB)      # byte 0 - fixed SYNC word
        b.append(0x90)      # byte 1 - SYNC
        b.append(0)         # byte 2 - reserved for CRC
        b.append(0)         # byte 3 - reserved for CRC
        b.append(0)         # byte 4 - sequence number
        b.append(sys_addr)  # byte 5 - address for the system / part
        b.append(com_id)    # byte 6 - command identifier
        b.append(len_payload)# byte 7 - payload length in bytes
        if len_payload !=0:
            b+=payload      # append the command payload
        
        if (self.verbose): print ("\t\t\t",b)
        return (b)

    def write_to_pair(self,com):

        self.socket.send(com)

    # #####################
    # Auxiliary functions #
    #######################

    def check_hv_off(self,crate_id,card_id,conn_id = None,chan_id = None):
        # return false if any HV is on for the specified conn_id 
        # default: check all modules for an entire card (3 rows) if conn_id == 0

        maxV = 2 # V 
        maxI = 4 # nA

        # calculate the relevant channels based on the conn_id
        # NOTE: update if we update to 1-18 rather than 0-17
        minR, maxR = gaps_map.tracker_power_channels[0],gaps_map.tracker_power_channels[-1]
        if not conn_id == None and not conn_id ==0: 
            minR, maxR = gaps_map.tracker_power_channels[6*conn_id],gaps_map.tracker_power_channels[6*(i+1)]
        elif not chan_id == None and not chan_id ==0:
            minR, maxR = chan_id
        #print (conn_id, minR, maxR)
        
        # check HV less than threshold for indicated channels 
        q = GSEQuery(project="gaps",path=self.path)
        pg = q.make_parameter_groups([f"@crate{crate_id}_card{card_id}_hv_voltage{x}" for x in range(minR,maxR+1)]) 
        res = q.get_latest_value_groups(pg)
        for r in res.items():
            if r[1][1] > maxV: 
        
                print ("Warning!!! GSE detected bias >",maxV,"for",r[0])
                print ("not sending that command!\nlove from your gse safety checker\n\n\n")
                return False

        # also add a check for hv_currents
        pg = q.make_parameter_groups([f"@crate{crate_id}_card{card_id}_hv_current{x}" for x in range(minR,maxR+1)]) 
        res = q.get_latest_value_groups(pg)
        for r in res.items():
            if r[1][1] > maxI:
        
                print ("Warning!!! GSE detected current >",maxI,"for",r[0])
                print ("not sending that command!\nlove from your gse safety checker\n\n\n")
                return False

        # any other checks?

        return True

    def check_lv_on(self,crate_id,card_id,chan_id = None, conn_id = None):
        # return false if LV is off for the connector corresponding to the specified channel
        # default (chan_id=0) is to check for all connectors on the card

        maxvar = 0.2

        # calculate the relevant connectors based on the chan_id
        conns = []
        if chan_id in range(1,7): conns = ["a"]
        elif chan_id in range(7,13): conns = ["b"]
        elif chan_id in range(13,19): conns = ["c"]                                                           
        elif chan_id == 0 or conn_id == 0 or (conn_id == None and chan_id == None): conn = ["a","b","c"]
        else: 
            print ("Not a valid channel id to check")
            return False

        # check LV status good for indicated channels
        q = GSEQuery(project="gaps",path=self.path)
        for conn_id in conns:
                                                                                
            # NOTE: can i use conn_a_status instead? 
            pg = q.make_parameter_groups([f"@crate{crate_id}_card{card_id}_lv_{x}_{conn_id}" for x in ["d3v8","d2v8","a3v3","a2v8"]]) 
            res = q.get_latest_value_groups(pg)
            #print (res)
            for r,v in zip(res.items(),[3.8,2.8,3.3,2.8]):
                if r[1][1] > v+ maxvar or r[1][1] < v-maxvar: 
        
                    print("Warning!!! GSE detected LV is not correct for", r[0])
                    print ("not sending that command!\nlove from your gse safety checker\n\n\n")
                    return False

        return True

    def rtd_to_binary(self,temp):
        r = 1 + 3.9083e-3*temp - 5.775e-7*temp**2 # ohms 
        L = 4 # m, on average, depends on RTD channel. need to update
        r_corr = r + 0.253*2*L/1000 # kOhm
        V = 21.58*1.25*(r_corr-1)*3.3/((3.3+r_corr)*(3.3+1)) # V ## NOTE confirm should be r_corr not r
        if abs(V) > 5: 
            print ("bad rtd to binary conversion")
            sys.exit(1)
        if V < 0: 
            return int(round(4096 + V*4096/(2*5),0))
        return int(round(V*4096/(2*5),0))
    
    def xor_check(self, packet): # NOTE test this!
        checksum = 0
        for el in packet: 
            #print (hex(el), chr(el))
            checksum ^=el
        #print (checksum, hex(checksum), chr(checksum))
        return checksum

if __name__ == "__main__":

    # arg parser
    from argparse import ArgumentParser
    p = ArgumentParser()
    p.add_argument('-a','--zmq_addr',default='tcp://192.168.37.3:48112')
    p.add_argument('-c','--config',help="path to yaml config file",default=None)
    p.add_argument('-l','--command',nargs='+',help="pass one command in a yaml-parsable form. \neg, `python3 gse_commands.py -l sleep: 1'\n or `python3 gse_commands.py -l pdu_on: {pdu0: [1,2]}'\n note spaces are required for proper parsing",default=None)
    p.add_argument('-v','--verbose',action="store_true",default=False)
    p.add_argument("-p","--db_path",help="path to sqlite db, /home/gfp/gfp_data/live/gsedb.sqlite on the gfp machine",default=os.environ["GSE_DB_PATH"])
    args = p.parse_args()
    if (args.verbose): print (args)

    if args.config == None and args.command == None: 
        print ("please specify a command! use option -c to pass a config file. use option -l to pass a single command directly\n run `python3 gse_commands.py -h' for help")

        sys.exit(1)
    elif args.config != None and args.command !=None:
        print ("please use either option '-c' or option '-l', not both")
        sys.exit(1)


    if args.config != None: 
        Commander(config=args.config,zmq_addr=args.zmq_addr,verbose=args.verbose,path=args.db_path)
        sys.exit()

    else:
        Commander(com_list=args.command,zmq_addr=args.zmq_addr, verbose=args.verbose,path=args.db_path)
        sys.exit()
