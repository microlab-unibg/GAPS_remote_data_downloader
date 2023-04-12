# this script generates a gui to display merged event information
# it automatically queries the sqlite db at the location specified by the environment variable GSE_DB_PATH
# to run on any computer, first do ssh -L 44555:localhost:44555 gfp@128.32.13.79
# and then ensure GSE_DB_PATH is set to 127.0.0.1:44555
# by Field Rogers <fieldr@berkeley.edu> or, if deprecated <field.rogers.ssl@gmail.com>

import zmq, sys, time
from pybfsw.gse.gsequery import GSEQuery
from PyQt5 import sip
from argparse import ArgumentParser
from PyQt5.QtCore import QTimer, Qt
from subprocess import Popen, DEVNULL
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QWidget,
    QPushButton,
    QGridLayout,
    QFormLayout,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
)
from PyQt5.QtGui import QIntValidator
from pybfsw.bind.merged_event_bindings import merged_event
import gaps_tof as gt
from sqlite3 import connect # should go back to zmq connection in the future NOTE

class MergedEventWindow(QWidget):
    def __init__(self,path=None):

        super().__init__()
        self.init_par()  # initialize the data variable names
        self.init_ui()  # set up the gui layout

        # set up the gse query for use in "update" # NOTE keep for future use
        self.q = GSEQuery(project="gaps",path=path)
        #self.pg = {}
        #self.conn = connect("gsedb_merged_events_only.sqlite") #NOTE should go to zmq in the future

        #self.auto_update = True # turn to FALSE to print a specific event_id rather than auto update

        # set up the timer functionality and start timer
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.timer_callback)
        self.timer_callback()

        # begin updating the values
        self.update()
        self.show()

    def init_par(self):
        self.merged_event_vars = ["event_id", "flags0","tracker_events","row_id"]
        self.merged_event_vars = ["rowid","gsemode","gcutime","counter","length","eventid","ntofhits","ntrackerhits","flags0","flags1"]
        
        self.tracker_hit_vars = ["row","module","channel","adc","asic_event_code"]
        self.tracker_event_vars = ["layer","event_time","hits"]
        self.tracker_tree_headers = ["Tracker_event"] + self.tracker_event_vars + self.tracker_hit_vars

        self.tof_event_vars = ["event_crt","timestamp_32","timestamp_16","n_paddles","primary_beta","primary_beta_unc","primary_charge","primary_charge_unc","primary_outer_tof_x","primary_outer_tof_y","primary_outer_tof_z","primary_inner_tof_x","primary_inner_tof_y","primary_inner_tof_z","nhit_outer_tof","nhit_inner_tof","trigger_info","ctr_etx",]
        self.tof_event_vars = ["timestamp_32","timestamp_16","n_paddles","primary_beta","primary_beta_unc","primary_charge","primary_charge_unc","primary_outer_tof_x","primary_outer_tof_y","primary_outer_tof_z","primary_inner_tof_x","primary_inner_tof_y","primary_inner_tof_z"]
        
        self.tof_paddle_vars = ["paddle_id","time_a","time_b","peak_a","peak_b","charge_a","charge_b","charge_min_i","x_pos","t_average","timestamp_32","timestamp_16",]
        self.tof_paddle_vars = ["paddle_id","timestamp_32","timestamp_16","charge_a","charge_b","time_a","time_b"]

    def init_ui(self):

        # Create an outer layout
        outer_layout = QGridLayout()

        # create a layout to input event_level information
        self.ev_id = QLineEdit()
        self.ev_id.setValidator(QIntValidator())
        self.ev_id.returnPressed.connect(self.input_event_id)
        
        self.row_id = QLineEdit()
        self.row_id.setValidator(QIntValidator())
        self.row_id.returnPressed.connect(self.input_row_id)
        
        start_run = QPushButton("Real-time Mode")
        start_run.clicked.connect(self.timer_callback)

        back = QPushButton("Previous")
        back.clicked.connect(self.prev_event)
        forward = QPushButton("Next")
        forward.clicked.connect(self.next_event)

        self.error_message = QTextEdit()
        self.error_message.setReadOnly(True)

        self.input_layout = QGridLayout()
        
        self.input_layout.addWidget(start_run,0,0,1,2,alignment=Qt.AlignTop)
        
        self.input_layout.addWidget(back,1,0)
        self.input_layout.addWidget(forward,1,1)

        self.input_layout.addWidget(QLabel("Event ID"),2,0)
        self.input_layout.addWidget(self.ev_id,2,1)

        self.input_layout.addWidget(QLabel("Row ID"),3,0)
        self.input_layout.addWidget(self.row_id,3,1) 

        self.input_layout.addWidget(self.error_message,4,0,2,0,alignment=Qt.AlignTop)
        
        # create a layout to display merged_event_level information
        self.merged_event_layout = QFormLayout()
        self.merged_event_display = {}
        for var in self.merged_event_vars: 
            self.merged_event_display[var] = QLineEdit()
            self.merged_event_display[var].setReadOnly(True)
            self.merged_event_layout.addRow(var, self.merged_event_display[var])
        
        # create a tree layout to display tof paddle level information 
        self.tof_paddle_tree = QTreeWidget()
        self.tof_paddle_tree.setColumnCount(len(self.tof_paddle_vars))
        self.tof_paddle_tree.setHeaderLabels(self.tof_paddle_vars)

        # creat a layout to display the tof event level information
        self.tof_event_layout = QFormLayout()
        self.tof_event_display = {}
        for var in self.tof_event_vars:
            self.tof_event_display[var] = QLineEdit()
            self.tof_event_display[var].setReadOnly(True)
            self.tof_event_layout.addRow(var,self.tof_event_display[var])

        # create a tree layout to display tracker event level information: 
        self.tracker_tree = QTreeWidget()
        self.tracker_tree.setColumnCount(len(self.tracker_tree_headers))
        self.tracker_tree.setHeaderLabels(self.tracker_tree_headers)
        

        # Nest the inner layouts into the outer layout and declare the outer layout to be the main layout
        outer_layout.addWidget(QLabel("Input"), 0,1)
        outer_layout.addLayout(self.input_layout, 1,1,1,1,alignment = Qt.AlignTop) 
        outer_layout.setColumnStretch(1,1)
        
        outer_layout.addWidget(QLabel("Merged Event Info"),0,2,) # 
        outer_layout.addLayout(self.merged_event_layout, 1, 2,1,1) # This is the top left layout
        outer_layout.setColumnStretch(2,1)
        
        outer_layout.addWidget(QLabel("Tracker Data Tree"), 0,3)
        outer_layout.addWidget(self.tracker_tree,1,3)
        outer_layout.setColumnStretch(3,4)

        outer_layout.addWidget(QLabel("TOF Paddle Data Tree"),2,3)
        outer_layout.addWidget(self.tof_paddle_tree,3,3)        
        
        outer_layout.addWidget(QLabel("TOF Event Data"),2,2)
        outer_layout.addLayout(self.tof_event_layout,3,2)

        self.setLayout(outer_layout)
    
    def timer_callback(self):
        self.timer.setInterval(int(1000))
        self.timer.start()
        self.update()

    def update(self,row_id = None,event_id = None):
        print ("")
        sql = "select * from mergedevent where (rowid = (select max(rowid) from mergedevent))"
        if event_id != None:
            sql = "select * from mergedevent where (eventid = " + str(event_id) + ")"
        if row_id != None: 
            sql = "select * from mergedevent where (rowid = " + str(row_id) + ")"

        #row = self.conn.execute(sql).fetchone() 
        self.q.dbi.query_start(sql)
        row = self.q.dbi.query_fetch(1)

        # check that we are looking at a valid event, and retrieve the binary blob if so
        blob = 0
        try: blob = row[0][-1]
        except: 
            self.error_message.setText("event id: " + str(event_id) + " is not in the db.")
            return
        print (row[0][:-1])
        print ("rowid: ", row[0][0]) 

        # clear data trees and error message from previous event
        self.tracker_tree.clear()
        self.tof_paddle_tree.clear()
        self.error_message.setText("")

        # unpack into the  merged event object 
        mev = merged_event()
        print ("len(blob) = ",len(blob))
        success = mev.unpack_str(bytes(blob),0)
        print ("mev.unpack_str() return:", success)
        if success < 0:
            self.error_message.setText("failed to unpack the merged event")
            return

        # update event_level variables
        for i, var in enumerate(self.merged_event_vars):
            self.merged_event_display[var].setText(str(row[0][i]))
        #for var in self.merged_event_vars: 
        #    self.merged_event_display[var].setText(self.mev_values(mev,var))
    
        # update tracker tree view
        for i, trk in enumerate(mev.tracker_events):
            trk_item = QTreeWidgetItem(["Event "+str(i)]+[self.tev_values(trk,var) for var in self.tracker_event_vars])
            for k, hit in enumerate(trk.hits):
                hit_item = QTreeWidgetItem([""]+["" for item in self.tracker_event_vars] + [self.hit_values(hit,var) for var in self.tracker_hit_vars] )
                trk_item.addChild(hit_item)

            self.tracker_tree.addTopLevelItem(trk_item)
        
        # initialize  tof event level and variables
        tof_packet = gt.TofPacket()
        data = [k for k in mev.tof_data]
        
        # check received tof data, make a tof packet, and check that it is the correct packet type (exit if not)
        if len(data) == 0: 
            self.error_message.setText("empty tof packet!!")
            print ("data, mev.tof_data = ", data, mev.tof_data)
            return 
        tof_packet.from_bytestream(data,0)
        if tof_packet.packet_type != gt.PacketType.TofEvent: 
            self.error_message.setText("tof packet not a TofEvent packet!!")
            return

        # load tof packet payload into a tof event 
        tof_event = gt.REventPacket()
        data = [k for k in tof_packet.payload]
        tof_event.from_bytestream(data,0)
        #print ("tof_event.paddle_packets = ", tof_event.paddle_packets)
        print ("tof_event.primary_beta = ", tof_event.primary_beta)
        print ("event timestamp 32 = ", tof_event.timestamp_32)
        print ("event timestamp 16 = ", tof_event.timestamp_16)

        # update the tof event display with event info
        for var in self.tof_event_vars:
            self.tof_event_display[var].setText(str(tof_event.__getattribute__(var)))

        # update the tof paddle tree with tof paddle info
        for i, pad in enumerate(tof_event.paddle_packets):                    
            pad_item = QTreeWidgetItem([str(pad.__getattribute__(var)) for var in self.tof_paddle_vars])
            self.tof_paddle_tree.addTopLevelItem(pad_item)

    def mev_values(self,mev,var):
        if var == "event_id": return str(mev.event_id)
        if var == "flags0": return str(mev.flags0)
        if var == "tracker_events": return str(len(mev.tracker_events))
        #if var == "row_id": return str(mev.rowid)
        return str(0)

    def tev_values(self,tev,var):
        if var == "event_id": return str(tev.event_id)
        if var == "layer": return str(tev.layer)
        if var == "event_id_valid": return str(tev.flags1 & 0b1)
        if var == "event_time": return str(tev.event_time) # str(time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(tev.event_time)))
        if var == "hits": return str(len(tev.hits))
        return "0"

    def hit_values(self,hev, var):
        if var == "row": return str(hev.row)
        if var == "module": return str(hev.module)
        if var == "channel": return str(hev.channel)
        if var == "adc": return str(hev.adc)
        if var == "asic_event_code": return str(hev.asic_event_code)
        return "0"


    def input_event_id(self): 
        print (self.ev_id.text())
        self.timer.stop()
        self.update(event_id = self.ev_id.text())
   
    def input_row_id(self):
        print (self.row_id.text())
        self.timer.stop()
        self.update(row_id = self.row_id.text())

    def next_event(self): 
        ev_id = str(int(self.merged_event_display["eventid"].text()) +1)
        print (ev_id)
        self.timer.stop()
        self.update(event_id = ev_id)

    def prev_event(self):
        ev_id = str(int(self.merged_event_display["eventid"].text()) -1)
        print (ev_id)
        self.timer.stop()
        self.update(event_id = ev_id)


if __name__ == "__main__":

    # arg parser
    p = ArgumentParser()
    p.add_argument(
        "-p",
        "--db_path",
        help="path to sqlite db, /home/gfp/gfp_data/live/gsedb.sqlite on the gfp machine",
    )
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args()
    if args.verbose:
        print(args)

    path = "$GSE_DB_PATH"
    try: path = args.db_path
    except: print ("Using default database path")

    app = QApplication([])
    window = MergedEventWindow(path = path)
    window.show()
    sys.exit(app.exec_())
