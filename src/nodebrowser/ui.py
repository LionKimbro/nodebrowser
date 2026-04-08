"""Tkinter UI framing for nodebrowser."""

import tkinter as tk

from . import nodebrowser as core


def create_default_graph():
    """Return a small starter graph for the demo UI."""

    return {
        "nodes": {
            "node-0001": {"id": "node-0001", "x": 180, "y": 140},
            "node-0002": {"id": "node-0002", "x": 360, "y": 300},
        },
        "edges": [
            {"from": "node-0001", "to": "node-0002"},
        ],
    }


def create_app(parent=None, graph_data=None, title="Node Browser", width=960, height=720):
    """Create the framing window and canvas, then attach nodebrowser core."""

    if parent is None:
        window = tk.Tk()
        owns_window = True
    else:
        window = tk.Toplevel(parent)
        owns_window = False

    window.title(title)
    window.geometry(f"{width}x{height}")

    frame = tk.Frame(window, bg="#202020")
    frame.pack(fill="both", expand=True)

    canvas = tk.Canvas(
        frame,
        bg="black",
        highlightthickness=0,
        takefocus=1,
    )
    canvas.pack(fill="both", expand=True, padx=12, pady=12)

    if graph_data is None:
        graph_data = create_default_graph()

    core.reset_runtime()
    core.use_canvas(canvas)
    core.use_graph_data(graph_data)

    app_state = {
        "window": window,
        "frame": frame,
        "canvas": canvas,
        "graph_data": graph_data,
        "owns_window": owns_window,
    }
    return app_state


def destroy_app(app_state):
    """Detach nodebrowser core and destroy the app window."""

    if not app_state:
        return

    canvas = app_state.get("canvas")
    if canvas is not None and core.canvas_widget is canvas:
        core.use_canvas(None)
        core.use_graph_data(None)

    window = app_state.get("window")
    if window is not None and window.winfo_exists():
        window.destroy()


def run_app(graph_data=None, title="Node Browser", width=960, height=720):
    """Create and run the default application."""

    app_state = create_app(
        parent=None,
        graph_data=graph_data,
        title=title,
        width=width,
        height=height,
    )
    app_state["window"].mainloop()
    return app_state
