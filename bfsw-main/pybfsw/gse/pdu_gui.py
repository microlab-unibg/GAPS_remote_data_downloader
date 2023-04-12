# this script generates a gui to display updated housekeeping data from the GAPS PDUs
# it automatically queries the sqlite db at the location specified by the environment variable GSE_DB_PATH
# to run on any computer, first do ssh -p 55225 -L 44555:localhost:44555 gaps@gamma1.ssl.berkeley.edu
# and then ensure GSE_DB_PATH is set to 127.0.0.1:44555
# by Field Rogers <fieldr@berkeley.edu>

import zmq, sys,os
from pybfsw.gse.gsequery import GSEQuery
from pybfsw.gse.gondola_hardcoding import GAPSMaps
import time
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
    QVBoxLayout,
    QHBoxLayout,
)

#pdu_list = [0]

gaps_map = GAPSMaps()
pdu_list = [x for x in gaps_map.pdu_channels]  # the PDUs to be sampled
print (pdu_list)


class PduHousekeepingWindow(QWidget):
    def __init__(self,path=None):

        super().__init__()
        self.init_par()  # initialize the data variable names
        self.init_ui()  # set up the gui layout

        # set up the gse query for use in "update"
        self.q = GSEQuery(project="gaps",path=path)
        self.pg = {}
        for pdu in pdu_list:
            self.pg[pdu] = self.q.make_parameter_groups(self.parameters[pdu])

        # set up the timer functionality and start timer
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.timer_callback)
        self.timer_callback()

        # begin updating the values
        self.update()
        self.show()

    def init_par(self):

        # list of the types of per-channel data items:
        self.grid_keys = [
            "chan",
            "temp",
            # "power",
            "accPower",
            # "current",
            "aveCurrent",
            # "voltage",
            "aveVoltage",
        ]

        # dictionary of display labels for the per-channel data items
        self.keyboard_labels = {
            "chan": "Channel",
            "temp": "Temp [C]",
            "current": "I [A]",
            "aveCurrent": "Ave I [A]",
            "power": "Power [W]",
            "accPower": "Power Acc [W]",
            "voltage": "Voltage [V]",
            "aveVoltage": "Ave Voltage [V]",
        }

        # dictionary parameter lookup names for the per-channel data items
        self.keyboard = {}
        for pdu in pdu_list:
            self.keyboard[pdu] = {
                "chan": [f"ch {i}" for i in range(0, 8)],
                "temp": [f"@temp_pdu{pdu}ch{i}" for i in range(0, 8)],
                "current": [f"@ibus_inst_pdu{pdu}ch{i}" for i in range(0, 8)],
                "aveCurrent": [f"@ibus_pdu{pdu}ch{i}" for i in range(0, 8)],
                "power": [f"@power_pdu{pdu}ch{i}" for i in range(0, 8)],
                "accPower": [f"@power_acc_pdu{pdu}ch{i}" for i in range(0, 8)],
                "voltage": [f"@vbus_inst_pdu{pdu}ch{i}" for i in range(0, 8)],
                "aveVoltage": [f"@vbus_pdu{pdu}ch{i}" for i in range(0, 8)],
            }

        # list of per-pdu rather than per-channel data items
        self.misc_keys = [
            "gcutime",
            "gsemode",
            "length",
            "vbat",
            "acc_count_pac0",
            "rowid",
            "error",
            "counter",
            "pdu_count",
            "acc_count_pac1",
        ]

        # list of all parameters to query for each pdu
        self.parameters = {}  # list of parameters to query
        self.mapping = {}  # type of parameter (for reference in "update" function)
        for pdu in pdu_list:
            self.parameters[pdu] = []
            self.mapping[pdu] = []
            for key in self.grid_keys[1:]:  # add per-channel items to list
                self.parameters[pdu] = self.parameters[pdu] + self.keyboard[pdu][key]
                for k in self.keyboard[pdu][key]:
                    self.mapping[pdu].append(key)

            for key in self.misc_keys:  # add the per-pdu items ot the update list
                self.parameters[pdu].append(f"@{key}_pdu{pdu}")
                self.mapping[pdu].append(key)

    def init_ui(self):

        self.setWindowTitle("PDU Housekeeping")

        # Create an outer layout
        self.outerLayout = QGridLayout()

        # create a left layout, to hold the column names
        leftLayout = QVBoxLayout()
        for row, key in enumerate(self.grid_keys):
            leftLayout.addWidget(QPushButton(self.keyboard_labels[key]), row)

        # create the top layout, to hold the PDU names:
        pduidLayout = {}
        for pdu in pdu_list:
            pduidLayout = QLabel("PDU " + str(pdu))
            pduidLayout.setAlignment(Qt.AlignCenter)

        # create and set up the grid layouts to hold the data
        self.dataLayout = {}
        self.buttonMap = {}
        for pdu in pdu_list:
            self.dataLayout[pdu] = QGridLayout()
            self.buttonMap[pdu] = {}

        for pdu in pdu_list:
            for row, key in enumerate(self.grid_keys):
                for col, label in enumerate(self.keyboard[pdu][key]):
                    self.buttonMap[pdu][label] = QPushButton(label)
                    if key != "chan":
                        self.buttonMap[pdu][label].clicked.connect(
                            self.command_execute(
                                f"python3 -m pybfsw.gse.stripchart {label} --collapse"
                            )
                        )  # click functionality to bring up a stripchart
                    else: # for the channel id, stripchart loads for all info
                        coms = ""
                        for k in self.grid_keys[1:]: coms = f"{coms}{self.keyboard[pdu][k][col]} "
                        self.buttonMap[pdu][label].clicked.connect(
                            self.command_execute(
                                f"python3 -m pybfsw.gse.stripchart {coms} --collapse"
                            )
                        )  # click functionality to bring up a stripchart
                    self.dataLayout[pdu].addWidget(self.buttonMap[pdu][label], row, col)
        # create the bottom layouts, to hold the misc per-pdu data
        self.miscDataLayout = {}
        self.miscButtonMap = {}
        for pdu in pdu_list:
            self.miscDataLayout[pdu] = QGridLayout()
            self.miscButtonMap[pdu] = {}

            for n, label in enumerate(self.misc_keys):
                self.miscButtonMap[pdu][label] = QPushButton(label)
                self.miscButtonMap[pdu][label].clicked.connect(
                    self.command_execute(
                        f"python3 -m pybfsw.gse.stripchart @{label}_pdu{pdu}"
                    )
                )
                self.miscDataLayout[pdu].addWidget(
                    self.miscButtonMap[pdu][label], int(n / 5), n % 5
                )

        # Nest the inner layouts into the outer layout and declare the outer layout to be the main layout
        self.outerLayout.addLayout(leftLayout, 1, 0)
        for pdu in pdu_list:
            self.outerLayout.addWidget(pduidLayout, 0, pdu + 1)
            self.outerLayout.addLayout(self.dataLayout[pdu], 1, pdu + 1)
            self.outerLayout.addLayout(self.miscDataLayout[pdu], 2, pdu + 1)
        self.setLayout(self.outerLayout)

    def timer_callback(self):
        self.timer.setInterval(int(1000))
        self.timer.start()
        self.update()

    def update(self):

        for pdu in pdu_list:
            res = self.q.get_latest_value_groups(self.pg[pdu])

            for r, mapkey in zip(res.items(), self.mapping[pdu]):
                if r[1] is None:
                    continue  # do not update values if no data found in db

                key = r[0]
                #print (key)
                val = r[1][1]
                low_range = r[1][2].low_range
                high_range = r[1][2].high_range
                units = r[1][2].units

                # update values and button color if misc key
                if mapkey in self.misc_keys:
                    if key == f"@gcutime_pdu{pdu}":
                        self.miscButtonMap[pdu][mapkey].setText(
                            time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(val))
                        )
                        self.update_button_style(
                            self.miscButtonMap[pdu][mapkey],
                            val,
                            time.time() - 3,
                            time.time() + 3,
                        )
                    else:
                        self.miscButtonMap[pdu][mapkey].setText(
                            mapkey + ": " + str(round(val, 1)) + units
                        )
                        self.update_button_style(
                            self.miscButtonMap[pdu][mapkey], val, low_range, high_range
                        )

                # update values and button color if in per-channel data keyboard
                else:

                    # divide out the accumulation time for power acc to take J to W 
                    if key in [f"@power_acc_pdu{pdu}ch{i}" for i in range(4)]:
                        val = val/(res[f"@acc_count_pac0_pdu{pdu}"][1]/1024)
                    elif key in [f"@power_acc_pdu{pdu}ch{i}" for i in range (4,8)]:
                        val = val/(res[f"@acc_count_pac1_pdu{pdu}"][1]/1024)
                    
                    self.buttonMap[pdu][key].setText('{:g}'.format(float('{:.4g}'.format(round(val,3)))))
                    #self.buttonMap[pdu][key].setText('{:g}'.format(float('{:.3g}')))
                    #self.buttonMap[pdu][key].setText(str(round(val,3)))
                    self.update_button_style(
                        self.buttonMap[pdu][key], val, low_range, high_range
                    )

    def update_button_style(self, button, val, low_range, high_range):
        if val < low_range or val > high_range:
            button.setStyleSheet("background-color : red")
        else:
            button.setStyleSheet("background-color : lightgreen")

    def command_execute(self, cmd):
        return lambda: Popen(cmd.split(), stdout=DEVNULL, stderr=DEVNULL)


if __name__ == "__main__":

    # arg parser
    p = ArgumentParser()
    p.add_argument(
        "-p",
        "--db_path",
        help="path to sqlite db, /home/gfp/gfp_data/live/gsedb.sqlite on the gfp machine",default=os.environ["GSE_DB_PATH"])
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args()
    if args.verbose:
        print(args)

    app = QApplication([])
    window = PduHousekeepingWindow(path =args.db_path)
    window.show()
    sys.exit(app.exec_())
