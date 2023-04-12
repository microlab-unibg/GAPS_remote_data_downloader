from PyQt5.QtWidgets import QWidget, QLineEdit, QTextEdit, QCompleter
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
import shlex
from argparse import ArgumentParser
from typing import Callable, Union, Iterable


class CommandParser(ArgumentParser):
    def __init__(self, *args, **kwargs):
        self.cmd_name = kwargs["prog"]
        super().__init__(*args, **kwargs)

    def exit(self, status=0, message=None):
        pass

    def error(self, message):
        E = Exception()
        E.help = self.format_help()
        raise E

    def print_help(self, file=None):
        self.error("")


class TerminalWidget(QWidget):
    def __init__(self, callback: Callable, fontsize=8):
        """
        callback: a callable, called with the parsed arguments
        fontsize: font size, default = 8
        """
        super().__init__()
        self.cmd = {}  # maps command strings to command parsers
        self.callback = callback

        # text edit
        self.text = QTextEdit(self)
        self.text.setReadOnly(True)
        self.red = QColor("red")
        self.black = QColor("black")
        self.green = QColor("green")
        self.purple = QColor("purple")

        # line edit
        self.line = QLineEdit(self)
        self.line.returnPressed.connect(self.line_enter)
        self.set_fontsize(fontsize)
        self.line_hist = []
        self.first_cmd = False

    def set_fontsize(self, sz):
        font = self.text.font()
        font.setPointSize(sz)
        self.text.setFont(font)
        font = self.line.font()
        font.setPointSize(sz)
        self.line.setFont(font)

    def add_command(self, cmds, parser):
        """
        cmds: a string or list of strings mapping to the command parser (multiple strings can call a command)
        parser: an instance of CommandParser
        """
        if isinstance(cmds, str):
            cmds = [cmds]
        assert isinstance(parser, CommandParser)
        for cmd in cmds:
            self.cmd[cmd] = parser
            # update QCompleter?

    def get_commands(self):
        return self.cmd.keys()

    def create_completer(self):
        co = QCompleter(list(self.cmd.keys()))
        self.line.setCompleter(co)

    def line_enter(self):
        self.first_cmd = True
        cmd = self.line.text()
        self.line_hist.append(cmd)
        self.hist_int = 0
        if cmd:
            self.log(f"cmd: {cmd}")
            ret = self.process_cmd(cmd)
            if ret is not None:
                self.callback(ret)
            self.line.clear()
        bar = self.text.verticalScrollBar()
        bar.setValue(bar.maximum())

    def process_cmd(self, cmd):
        sp = shlex.split(cmd)
        if sp[0] not in self.cmd:
            self.log(f"error: unknown command {sp[0]}")
            return None
        try:
            parser = self.cmd[sp[0]]
            args = parser.parse_args(sp[1:])
            args.cmd_name = parser.cmd_name
            return args
        except Exception as e:
            if hasattr(e, "help"):
                self.log(f"help: {e.help}")
            else:
                self.log(f"error: {repr(e)}")

    def log(self, string):
        if string.startswith("error:"):
            c = self.red
        elif string.startswith("warning:"):
            c = self.purple
        else:
            c = self.black
        self.text.setTextColor(c)
        self.text.append(string)
