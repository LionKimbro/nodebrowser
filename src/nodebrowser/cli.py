"""Bootloader for the nodebrowser demo application."""

import lionscliapp as app

from . import ui


def cmd_default():
    """Launch the default tkinter UI."""

    title = app.ctx["ui.title"]
    width = int(app.ctx["ui.width"])
    height = int(app.ctx["ui.height"])
    ui.run_app(title=title, width=width, height=height)


def main():
    """Configure lionscliapp and dispatch commands."""

    app.reset()
    app.declare_app("nodebrowser", "0.1.0")
    app.describe_app("Node browser bootloader and demo launcher.")
    app.declare_projectdir(".nodebrowser")
    app.declare_key("ui.title", "Node Browser")
    app.declare_key("ui.width", "960")
    app.declare_key("ui.height", "720")
    app.describe_key("ui.title", "Window title for the default UI.")
    app.describe_key("ui.width", "Window width in pixels for the default UI.")
    app.describe_key("ui.height", "Window height in pixels for the default UI.")
    app.declare_cmd("", cmd_default)
    app.describe_cmd("", "Launch the default node browser UI.")
    app.main()
