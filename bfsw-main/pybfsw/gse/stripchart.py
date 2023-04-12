from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
    QSplitter,
    QShortcut,
    QPushButton,
    QStyle,
)
from PyQt5.QtCore import QTimer, Qt, QSize
from PyQt5.QtGui import QColor, QFont, QIcon
from pyqtgraph import GraphicsLayoutWidget, PlotDataItem, mkBrush, mkPen
from collections import OrderedDict
import time
from argparse import ArgumentParser
from subprocess import Popen
import sys
import json
import numpy as np
from pybfsw.gse.terminal import TerminalWidget, CommandParser
from pybfsw.gse.gsequery import GSEQuery
from pybfsw.gse.parameter import parameter_from_string
from datetime import datetime, timezone


def parse_time(st):
    """
    converts string to UTC timestamp. examples:
    1671574609.293378
    1671574609
    22/4/5-01:07:33 #UTC
    L22/4/5-01:07:33 #local time
    """

    try:
        fl = float(st)
        is_float = True
    except:
        is_float = False

    if is_float:
        return fl

    try:
        local = False
        if st[0] in ("l", "L"):
            local = True
            st = st[1:]
        left, right = st.split("-")
        y, mo, d = map(int, left.split("/"))
        h, mi, s = map(int, right.split(":"))
        y = y + 2000
        if local:
            tz = datetime.now().astimezone().tzinfo
        else:
            tz = timezone.utc
        return datetime(y, mo, d, h, mi, s, tzinfo=tz).timestamp()
    except:
        raise ValueError(
            "time string format is yy/mm/dd-hh:mm:ss with optional l or L prepended for local time"
        )


class StringSet:
    def __init__(self, *args):
        self.set = set(args)

    def __call__(self, x):
        if x in self.set:
            return x
        else:
            raise KeyError(f"invalid selection: {x} not in {self.set}")


class StripchartWidget(QWidget):
    def __init__(self, gsequery, json=None):
        super().__init__()  # might need to pass an arg here to nest this widget
        self.paused = False
        self.init_par(json=json)
        self.init_ui()
        self.gsequery = gsequery
        if json != None:
            self.load_json(json)
        self.data = {}
        # self.log(f"info: db path: {self.gsequery.full_path}") #doesn't work with RPC
        self.timer_callback()
        self.show_project_and_path()
        self.show_tables()

    def init_par(self, json=None):

        f = {}
        f["mode"] = StringSet("live", "history")
        f["refresh"] = float
        f["showquery"] = StringSet("t", "f")
        f["symbolsize"] = int
        f["dt"] = float
        f["t1"] = float
        f["t2"] = float
        f["width"] = int
        f["height"] = int
        f["terminal_height"] = int
        f["terminal_collapsed"] = bool
        f["traces"] = list
        f["aliases"] = list
        self.parfilters = f

        self.parameters = {}
        self.parameter("mode", "live")
        self.parameter("refresh", 2.1)
        self.parameter("showquery", "f")
        self.parameter("symbolsize", 8)
        self.parameter("dt", 1200)
        self.parameter("t2", time.time())
        self.parameter("t1", time.time() - 1200)
        self.parameter("width", 900)
        self.parameter("height", 300)
        self.parameter("terminal_height", 100)
        self.parameter("terminal_collapsed", False)
        self.parameter("traces", [])
        self.parameter("aliases", [])

        if json != None:
            self.load_json(json)

    # TODO connect window close signal to self.close, so that DB is closed if window is click-exited
    def init_ui(self):
        f1k = QShortcut(self)
        f1k.setKey(Qt.Key_F1)
        f1k.activated.connect(self.f1key_callback)

        f2k = QShortcut(self)
        f2k.setKey(Qt.Key_F2)
        f2k.activated.connect(self.f2key_callback)

        self.resize(self.parameter("width"), self.parameter("height"))
        self.resizeEvent = self.resize_callback

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(1, 1, 1, 1)
        self.layout.setSpacing(1)

        self.glw = GraphicsLayoutWidget(self)
        self.plotlayout = OrderedDict()
        self.pi = []
        self.pdi = {}

        self.splitter = QSplitter(self)
        self.splitter.setOrientation(Qt.Vertical)
        self.splitter.splitterMoved.connect(self.splitter_moved_callback)

        self.show_hide_button = QPushButton("")
        self.show_hide_button.setIcon(
            self.style().standardIcon(QStyle.SP_TitleBarUnshadeButton)
        )
        self.show_hide_button.setIconSize(QSize(10, 10))
        self.show_hide_button.setFixedHeight(12)
        self.show_hide_button.clicked.connect(self.toggle_collapse_callback)

        top_split_w = QWidget()
        top_split_layout = QVBoxLayout(top_split_w)
        top_split_layout.setContentsMargins(0, 0, 0, 0)
        top_split_layout.setSpacing(0)
        top_split_layout.addWidget(self.glw)
        top_split_layout.addWidget(self.show_hide_button)

        self.tw = TerminalWidget(callback=self.process_cmd)
        terminal_layout = QVBoxLayout(self.tw)
        terminal_layout.setContentsMargins(0, 0, 0, 0)
        terminal_layout.setSpacing(0)
        terminal_layout.addWidget(self.tw.text)
        terminal_layout.addWidget(self.tw.line)

        self.layout.addWidget(self.splitter)
        self.splitter.addWidget(top_split_w)
        self.splitter.addWidget(self.tw)
        self.splitter.setSizes(
            [
                self.parameter("height") - self.parameter("terminal_height"),
                self.parameter("terminal_height"),
            ]
        )

        self.colors = {
            "b": "blue",
            "g": "green",
            "r": "red",
            "c": "cyan",
            "m": "magenta",
            "y": "yellow",
            "k": "black",
            "w": "white",
        }

        p = CommandParser(prog="add", description="add a new trace to the plot")
        p.add_argument("name", help="the data name, in @parameter or table:column form")
        p.add_argument(
            "-c", "--color", default="w", choices=list("bgrcmykw"), help="trace color"
        )
        p.add_argument(
            "-s",
            "--symbol",
            default="o",
            choices=list("otsph+d") + ["t1", "t2", "t3", "star"],
            help="trace symbol",
        )
        self.tw.add_command(("add", "a"), p)

        p = CommandParser(prog="delete", description="remove a trace from the plot")
        p.add_argument(
            "name",
            help='the data name, in @alias or table:column form ("del @labjacktemp")',
        )
        self.tw.add_command(("del", "d"), p)

        p = CommandParser(prog="clear", description="clear all traces")
        self.tw.add_command(("clear", "c"), p)

        p = CommandParser(prog="set", description="set plot properties")
        p.add_argument("parameter", help="parameter name")
        p.add_argument("value")
        self.tw.add_command(("set", "s"), p)

        p = CommandParser(prog="show", description="show plot properties")
        p.add_argument(
            "-p", "--params", action="store_true", help='print parameters ("show -p")'
        )
        p.add_argument(
            "-t",
            "--tables",
            action="store_true",
            help='print tables from the DB ("show -t")',
        )
        p.add_argument(
            "-c",
            "--columns",
            type=str,
            help='print columns from a DB table ("show -c labjack")',
        )
        self.tw.add_command("show", p)

        p = CommandParser(prog="fork", description="spawn another plot window")
        self.tw.add_command(("fork", "f"), p)

        p = CommandParser(prog="save", description="save this plot configuration")
        p.add_argument(
            "fname", help='filename of the new configuration ("save example.cfg")'
        )
        self.tw.add_command("save", p)

        p = CommandParser(prog="load", description="load a plot configuration")
        p.add_argument(
            "fname", help='filename of the saved configuration ("load example.cfg")'
        )
        self.tw.add_command("load", p)

        p = CommandParser(prog="help", description="print the help statement")
        self.tw.add_command("help", p)

        p = CommandParser(prog="exit", description="exit the plot")
        self.tw.add_command(("exit", "q", "quit"), p)
        self.tw.create_completer()

        p = CommandParser(prog="home", description="home plots")
        self.tw.add_command(("home", "h"), p)

        p = CommandParser(
            prog="history", description="show historical data (i.e. not live)."
        )
        p.add_argument(
            "times",
            nargs="*",
            help="0, 1, or 2 times (unix time float). If 0, then just switch to history mode without specifying a time range. "
            "If 1, plot +/- 180 seconds around the given time. If 2, plot between the two provided times."
            "examples: 'history', 'history 1647803173.368', 'history 1647803173.368 1647803217.464'",
        )
        self.tw.add_command("history", p)

        p = CommandParser(
            prog="live", description="switch to live mode (i.e. not historical"
        )
        self.tw.add_command("live", p)

        p = CommandParser(prog="alias", description="give an @alias to a parameter")
        p.add_argument(
            "name",
            help="the alias name, in @alias form",
        )
        p.add_argument(
            "definition",
            help="the alias definition, in table:column[:where[:converter[:units]]] form",
        )
        self.tw.add_command(("alias"), p)

        p = CommandParser(
            prog="latest", description="find the latest (newest) timestamp in a table"
        )
        p.add_argument("table")
        self.tw.add_command("latest", p)

        # update timer
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.timer_callback)

    def process_cmd(self, a):
        cmd = a.cmd_name
        if cmd == "add":
            self.add_trace(a.name, a.color, a.symbol)
            self.update()
        elif cmd == "delete":
            self.del_trace(a.name)
            self.update()
        elif cmd == "clear":
            self.clear_traces()
            self.update()
        elif cmd == "set":
            self.parameter(a.parameter, a.value)
            self.update()
        elif cmd == "show":
            if a.params:
                self.log(f"info: {self.parameters}")
            if a.tables:
                self.show_tables()
            if a.columns != None:
                self.show_columns(a.columns)
        elif cmd == "fork":
            self.fork()
        elif cmd == "save":
            self.save_json(a.fname)
        elif cmd == "load":
            self.load_json(a.fname)
            self.update()
        elif cmd == "help":
            self.help()
        elif cmd == "exit":
            self.close()
        elif cmd == "home":
            self.home_plots()
        elif cmd == "history":
            self.history_plot(a.times)
        elif cmd == "live":
            self.set_live()
        elif cmd == "alias":
            self.alias(a.name, a.definition)
        elif cmd == "latest":
            t = self.gsequery.get_latest_time(a.table)
            self.log(f"info: latest timestamp in table {a.table} is {t}")
        else:
            self.log(f"warning: ignoring command {cmd}")

    def add_trace(self, name, color="w", symbol="o"):
        for tr in self.parameter("traces"):
            if tr["name"] == name:
                self.log(f"warning: already plotting {name}")
                return
        try:
            tr = {"name": name, "color": color, "symbol": symbol}
            ret = self.gsequery.time_query3(tr["name"], 0, 0)
            self.parameter("traces").append(tr)
        except Exception as e:
            self.log("error: exception when adding trace:" + repr(e))

    def del_trace(self, name):
        d = None
        for tr in self.parameter("traces"):
            if tr["name"] == name:
                d = tr
                break
        if d is None:
            self.log(f"error: no trace with name = {name} found")
        else:
            self.parameter("traces").remove(d)

    def clear_traces(self):
        self.parameter("traces", [])

    # TODO handle case where times are in format y/m/d-h:m:s
    def history_plot(self, times):
        if len(times) == 0:
            pass
        elif len(times) == 1:
            t1 = parse_time(times[0])
            self.parameter("t1", t1 - 180)
            self.parameter("t2", t1 + 180)
        elif len(times) == 2:
            self.parameter("t1", parse_time(times[0]))
            self.parameter("t2", parse_time(times[1]))
        self.parameter("mode", "history")
        self.update()
        self.home_plots()

    def show_console(self):
        self.console_status = "shown"
        self.tw.text.show()

    def hide_console(self):
        self.console_status = "hidden"
        self.tw.text.hide()

    def parameter(self, parameter, value=None):
        try:
            if value is None:
                return self.parameters[parameter]
            else:
                self.parameters[parameter] = self.parfilters[parameter](value)
        except:
            self.log(f"error: invalid parameter or value")

    def show_tables(self):
        try:
            tables = self.gsequery.get_table_names()
            self.log(f"info: table names: {tables}")
        except Exception as e:
            self.log(f"error: exception while getting table names: {repr(e)}")

    def show_project_and_path(self):
        try:
            project, path = self.gsequery.get_project_and_path()
            self.log(f"info: project = {project}, path = {path}")
        except Exception as e:
            self.log(f"error: exception while getting project and path: {repr(e)}")

    def show_columns(self, table):
        try:
            columns = self.gsequery.get_column_names(table)
            self.log(f"info: column names: {columns}")
        except Exception as e:
            self.log(f"error: exception while getting column names: {repr(e)}")

    def fork(self):
        try:
            Popen([sys.executable] + sys.argv)
        except Exception as e:
            self.log(f"error: self.fork raised exception: {repr(e)}")

    def save_json(self, fname):
        try:
            with open(fname, "w") as f:
                json.dump(self.parameters, f, indent=4)
            self.log(f"info: configuration saved to file {fname}")

        except Exception as e:
            self.log(f"error: exception in self.save_json(): {repr(e)}")

    def load_json(self, fname):
        try:
            with open(fname, "r") as f:
                self.parameters.update(json.load(f))
                for (alias, definition) in self.parameters["aliases"]:
                    self.add_alias(alias, definition)
                self.resize(self.parameter("width"), self.parameter("height"))
                self.splitter.setSizes(
                    [
                        self.parameter("height") - self.parameter("terminal_height"),
                        self.parameter("terminal_height"),
                    ]
                )
                self.collapse_terminal(self.parameter("terminal_collapsed"))

            self.log(f"info: configuration loaded from file {fname}")

        except Exception as e:
            self.log(f"error: exception in self.load_json(): {repr(e)}")

    def help(self):
        commands = [c for c in list(self.tw.get_commands())]
        self.log(f"available commands: {commands}")
        self.log(
            'for more help, type a command name followed by --help, like "add --help"'
        )
        self.log(
            "special keys:  F1 -> rehome x (time) axis    F2 -> pause updates in live mode"
        )

    def close(self):
        # TODO cleanup gsequery
        super().close()
        sys.exit()

    def log(self, s):
        try:
            self.tw.log(s)
        except:
            pass

    def keyPressEvent(self, event):
        key = event.key()
        if self.tw.first_cmd == True:
            if key == Qt.Key_Up:
                self.tw.hist_int -= 1
                if self.tw.hist_int >= (len(self.tw.line_hist) * -1):
                    self.tw.line.setText(self.tw.line_hist[self.tw.hist_int])
                else:
                    self.tw.hist_int += 1
                    self.tw.line.setText(self.tw.line_hist[self.tw.hist_int])
            elif key == Qt.Key_Down:
                self.tw.hist_int += 1
                if self.tw.hist_int < 0:
                    self.tw.line.setText(self.tw.line_hist[self.tw.hist_int])
                else:
                    self.tw.hist_int = 0
                    self.tw.line.setText("")
            else:
                super().keyPressEvent(event)

    def resize_callback(self, event):
        super().resizeEvent(event)
        width, height = self.width(), self.height()
        self.parameter("width", width)
        self.parameter("height", height)

    def f1key_callback(self):
        self.home_plots()

    def f2key_callback(self):
        mode = self.parameter("mode")
        if mode == "history":
            for pi in self.pi:
                xr, yr = pi.viewRange()
                xmin, xmax = xr
                self.parameter("t1", xmin)
                self.parameter("t2", xmax)
                self.update()
        else:
            assert mode == "live"
            if self.paused:
                self.paused = False
                self.log("info: unpaused")
            else:
                self.paused = True
                self.log("info: paused")

    def toggle_collapse_callback(self):
        self.collapse_terminal(not self.parameter("terminal_collapsed"))

    def collapse_terminal(self, collapse):
        if collapse:
            self.parameter("terminal_collapsed", True)
            self.show_hide_button.setIcon(
                self.style().standardIcon(QStyle.SP_TitleBarShadeButton)
            )
            self.splitter.setSizes([self.parameter("height"), 0])
        else:
            self.parameter("terminal_collapsed", False)
            self.show_hide_button.setIcon(
                self.style().standardIcon(QStyle.SP_TitleBarUnshadeButton)
            )
            self.splitter.setSizes(
                [
                    self.parameter("height") - self.parameter("terminal_height"),
                    self.parameter("terminal_height"),
                ]
            )

    def splitter_moved_callback(self, pos, index):
        if self.splitter.sizes()[-1] == 0:
            self.collapse_terminal(True)
        else:
            self.collapse_terminal(False)
            self.parameter("terminal_height", self.parameter("height") - pos)

    def timer_callback(self):
        self.timer.setInterval(int(self.parameter("refresh") * 1000))
        self.timer.start()
        if self.parameter("mode") == "live" and self.paused == False:
            self.update()

    def update(self):
        self.update_data()
        self.redraw()

    def update_data(self):
        if self.parameter("mode") == "live":
            t2 = time.time()
            t1 = t2 - self.parameter("dt")
        else:
            t1 = self.parameter("t1")
            t2 = self.parameter("t2")
        data = {}
        for tr in self.parameter("traces"):
            name = tr["name"]
            ret = self.gsequery.time_query3(name, t1, t2)
            if ret is None:
                self.log(f"warning: no data found for {name} in range [{t1},{t2}]")
            else:
                data[name] = self.gsequery.time_query3(name, t1, t2)
        if data.keys() != self.data.keys():
            self.regenerate_layout = True
        else:
            self.regenerate_layout = False
        self.data = data
        # self.data is a dictionary, where the keys are the trace names
        # and the values are tuples (timestamps, converted_values, units string)

    def redraw(self):

        # regenerate layout if necessary
        if self.regenerate_layout:
            self.regenerate_layout = False
            plotlayout = OrderedDict()

            # organize traces by units
            # TODO option to force non-sharing of y axis based on unit
            for tr in self.parameter("traces"):
                name = tr["name"]
                if name in self.data:
                    unit = self.data[name][2].units
                    if unit in plotlayout:
                        plotlayout[unit].append(tr)
                    else:
                        plotlayout[unit] = [tr]
            self.glw.clear()
            self.pdi = {}
            self.pi = []
            rownum = 1
            pi = None
            for unit, traces in plotlayout.items():
                pi = self.glw.addPlot(row=rownum, col=1)
                lg = pi.addLegend(offset=(-1, -1))
                pi.getAxis("left").setLabel(unit)
                pi.getAxis("bottom").setStyle(showValues=False)
                pi.showGrid(x=True, y=True, alpha=1.0)
                pi.enableAutoRange(y=True)
                pi.hideButtons()
                rownum += 1
                for tr in traces:
                    pdi = PlotDataItem(autoDownSample=True, clipToView=True)
                    vb = pdi.getViewBox()
                    pi.addItem(pdi)
                    lg.addItem(pdi, tr["name"])
                    self.pdi[tr["name"]] = pdi
                self.pi.append(pi)

            if self.pi:
                if len(self.pi) >= 2:
                    for pi in self.pi[:-1]:
                        pi.setXLink(self.pi[-1].getViewBox())
                # set up bottom-most x axis
                pi = self.pi[-1]
                ax = pi.getAxis("bottom")
                qf = QFont()
                qf.setPointSize(8)
                ax.setStyle(showValues=True)
                ax.setTickFont(qf)
                ax.setHeight(
                    28
                )  # empirically set on Alex's computer.  check on other machines
                ax.tickStrings = self.tick_format
            self.plotlayout = plotlayout

            self.home_plots()

        # update the data shown in the plot
        for unit, traces in self.plotlayout.items():
            for tr in traces:
                name, symbol, color = tr["name"], tr["symbol"], tr["color"]
                times, ydata, par = self.data[name]
                if self.parameter("mode") == "live":
                    self.tnow = time.time()
                else:
                    self.tnow = 0
                self.pdi[name].setData(
                    times - self.tnow,
                    ydata,
                    symbol=symbol,
                    pen=mkPen(color),
                    symbolPen=mkPen(color),
                    symbolBrush=mkBrush(color),
                    symbolSize=self.parameter("symbolsize"),
                )

        # window title
        window_title = [f" {name}" for name in self.data]
        window_title.append(f'  ~{self.parameter("mode")}~')
        self.setWindowTitle(" ".join(window_title))

        # causes absolute timestamp to update in live mode
        # this is super bad and hacky. resizeEvent expects the instance passed as ev to have these methods.
        if self.pi:

            class qqq:
                def oldSize(self):
                    return 5

                def newSize(self):
                    return 6

            self.pi[-1].getViewBox().resizeEvent(ev=qqq())
            pass

    def tick_format(self, values, scale, spacing):
        ret = []
        mode = self.parameter("mode")
        for t in values:
            if mode == "live":
                tabs = t + self.tnow
                pass
            else:
                tabs = t
            tfmt = time.strftime("%y/%m/%d-%H:%M:%S", time.gmtime(tabs))
            if mode == "live":
                if t < 0:
                    v = -t
                else:
                    v = t
                h, mod = divmod(v, 3600)
                m, mod = divmod(mod, 60)
                s = mod
                h, m, s = map(int, (h, m, s))
                r = [tfmt, "\n"]
                if t < 0:
                    r.append("-")
                r.append(f"{h:02d}:{m:02d}:{s:02d}")
                ret.append("".join(r))
            else:
                ret.append(tfmt)
        return ret

    def home_plots(self):
        for pi in self.pi:
            pi.enableAutoRange(y=True)
            if self.parameter("mode") == "live":
                pi.setXRange(-self.parameter("dt"), 0)
            else:
                pi.setXRange(self.parameter("t1"), self.parameter("t2"))

    def set_live(self):
        self.parameter("mode", "live")
        self.update()
        self.home_plots()

    def alias(self, alias, definition):
        self.add_alias(alias, definition)
        self.parameter("aliases").append((alias, definition))

    def add_alias(self, alias, definition):
        try:
            P = parameter_from_string(definition, alias)
            self.gsequery.get_parameter_bank().add(P)
        except Exception as e:
            self.log(f"warning: {str(e)}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--json", help="json configuration file")
    parser.add_argument(
        "--path",
        help="path to db, either path to local file or ip:host for remote db. if not provided, $GSE_DB_PATH is used",
    )
    parser.add_argument("--project")
    parser.add_argument("--collapse", action="store_true")
    parser.add_argument("traces", nargs="*")
    args = parser.parse_args()
    gsequery = GSEQuery(path=args.path, project=args.project)
    app = QApplication([])
    sc = StripchartWidget(gsequery, json=args.json)
    for trace in args.traces:
        sc.add_trace(trace)
    if args.collapse:
        sc.collapse_terminal(True)
    sc.show()
    sc.update()
    sc.tw.line.setFocus()
    app.exec_()
