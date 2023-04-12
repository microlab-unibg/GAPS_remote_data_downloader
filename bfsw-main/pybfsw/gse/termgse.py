from pybfsw.gse.gsequery import GSEQuery
from time import time
from subprocess import Popen, DEVNULL
from rich.text import Text
from rich.style import Style
from textual.app import App
from textual.widgets import Static
from textual.containers import Vertical, Horizontal
from yaml import safe_load

# TODO: add bar at bottom showing time difference between local clock and gcutime
# TODO: handle newrow
# TODO: hold ctrl and right click multiple to overplot in stripchart
# TODO: allow for multiple TextButtons to query the same name (currently using a dict, name only maps to 1 text button)
# TODO: make group width a configurable parameter

# colors here: https://rich.readthedocs.io/en/stable/appendix/colors.html


class TextButton(Static):
    def __init__(self, name, attrs):
        self.par_name = name
        self.attrs = {
            "style": "white on grey0",
            "format": ">8.3f",
            "alt": None,
            "min": -1e100,
            "max": 1e100,
        }
        self.attrs.update(attrs)
        super().__init__(expand=True)

    def on_click(self, event):
        if event.button == 3:  # right click
            project = ""
            if args.project is not None:
                project = f"--project={args.project}"
            path = ""
            if args.path is not None:
                path = f"--path={args.path}"
            cmd = f"python -m pybfsw.gse.stripchart --collapse {path} {project} {self.par_name}"
            Popen(cmd.split(), stdout=DEVNULL, stderr=DEVNULL)

    def update_text(self, res):
        if res is None:
            text = "none"
        else:
            gcutime, y, par = res
            if self.attrs["alt"]:
                name = self.attrs["alt"]
            else:
                name = self.par_name
            text = f"{name}: {y:{self.attrs['format']}} {par.units}"
        tt = Text.from_markup(
            text,
            style=self.attrs["style"],
            justify="left",
        )
        self.update(tt)


class TermGseApp(App):
    def __init__(self, yaml, path=None, project=None):
        with open(yaml) as fp:
            self.cfg = safe_load(fp)
        self.gsequery = GSEQuery(path=path, project=project)
        self.parameter_groups = None
        super().__init__()

    def compose(self):
        self.screen.styles.background = "black"
        yield Static(Text.from_markup(self.cfg["settings"]["title"]))
        self.map = {}
        verticals = []
        for group in self.cfg["groups"]:
            group_name, parameters = next(iter(group.items()))
            tbs = [Static(Text(group_name, style="bold", justify="center"))]
            for parameter in parameters:
                name, attrs = next(iter(parameter.items()))
                tb = TextButton(name, attrs)
                self.map[name] = tb
                tbs.append(tb)
            vertical = Vertical(*tbs)
            vertical.styles.width = 40  # fits 4 groups on lenovo x1 screen with default gnome terminal settings
            vertical.styles.border = ("round", "white")
            verticals.append(vertical)
        self.parameter_groups = self.gsequery.make_parameter_groups(self.map.keys())
        hz = Horizontal(*verticals)
        hz.styles.overflow_x = "scroll"
        yield hz

    def on_mount(self):
        self.set_interval(self.cfg["settings"]["refresh"], callback=self.get_new_values)
        self.get_new_values()

    def get_new_values(self):
        res = self.gsequery.get_latest_value_groups(self.parameter_groups)
        for name, tb in self.map.items():
            tb.update_text(res[name])


if __name__ == "__main__":
    from argparse import ArgumentParser

    p = ArgumentParser()
    p.add_argument("yaml")
    p.add_argument("--path", help="db path")
    p.add_argument("--project", help="project name (e.g. gaps)")
    args = p.parse_args()
    app = TermGseApp(args.yaml, path=args.path, project=args.project)
    app.run()
