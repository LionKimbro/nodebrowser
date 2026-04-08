"""Copyable main interaction module for nodebrowser."""

import math


canvas_widget = None
graph_data = None
widgets = {}
effects = []
callbacks = {
    "generate_node_id": None,
    "on_single_selection_changed": None,
    "on_graph_mutated": None,
}

g = {
    "mode": "IDLE",
    "selected_node_id": None,
    "active_canvas_name": None,
}

raw = {
    "event_name": None,
    "x": 0,
    "y": 0,
    "key": None,
    "shift_down": False,
    "button_1_down": False,
    "canvas_has_focus": False,
    "pointer_node_id": None,
}

raw_prev = {
    "event_name": None,
    "x": 0,
    "y": 0,
    "key": None,
    "shift_down": False,
    "button_1_down": False,
    "canvas_has_focus": False,
    "pointer_node_id": None,
}

derived = {
    "drag_distance": 0,
    "drag_threshold_crossed": False,
}

derived_prev = {
    "drag_distance": 0,
    "drag_threshold_crossed": False,
}

interaction = {
    "mouse_down_x": 0,
    "mouse_down_y": 0,
    "last_mouse_x": 0,
    "last_mouse_y": 0,
    "drag_node_id": None,
    "group_drag_origin": None,
    "marquee_start": None,
    "marquee_end": None,
    "press_node_id": None,
    "press_consumed": False,
    "ignore_release": False,
}

selection = {
    "group_selected_ids": [],
}

render = {
    "node_radius": 25,
    "selected_inner_radius": 20,
    "node_outline_width": 5,
    "selected_inner_width": 1,
    "marquee_outline_width": 1,
    "hit_slop": 3,
    "background_color": "black",
    "node_outline_color": "white",
    "node_fill_color": "",
    "selected_fill_color": "dark green",
    "selected_inner_color": "green",
    "edge_color": "white",
    "marquee_outline_color": "white",
    "marquee_dash": [4, 4],
    "group_halo_color": "blue",
    "group_halo_width": 1,
    "group_halo_radius_offset": 3,
    "edge_vertical_pull": 60,
    "drag_threshold": 4,
}

canvas_items = {
    "node_items_by_id": {},
    "edge_items": [],
    "marquee_item": None,
}

coordination = {
    "pointer-owner": None,
    "resource-holds": {},
    "leases": {},
}

current_organism = None


def _make_organism(name, fn):
    return {
        "NAME": name,
        "ACTIVE": True,
        "STATE": "IDLE",
        "HELD": {},
        "DATA": {},
        "FN": fn,
    }


organisms = []


def reset_runtime():
    """Reset mutable runtime state."""

    global canvas_widget, graph_data, current_organism

    canvas_widget = None
    graph_data = None
    current_organism = None
    effects.clear()
    widgets.clear()
    callbacks["generate_node_id"] = None
    callbacks["on_single_selection_changed"] = None
    callbacks["on_graph_mutated"] = None

    g["mode"] = "IDLE"
    g["selected_node_id"] = None
    g["active_canvas_name"] = None

    for target in (raw, raw_prev):
        target["event_name"] = None
        target["x"] = 0
        target["y"] = 0
        target["key"] = None
        target["shift_down"] = False
        target["button_1_down"] = False
        target["canvas_has_focus"] = False
        target["pointer_node_id"] = None

    derived["drag_distance"] = 0
    derived["drag_threshold_crossed"] = False
    derived_prev["drag_distance"] = 0
    derived_prev["drag_threshold_crossed"] = False

    interaction["mouse_down_x"] = 0
    interaction["mouse_down_y"] = 0
    interaction["last_mouse_x"] = 0
    interaction["last_mouse_y"] = 0
    interaction["drag_node_id"] = None
    interaction["group_drag_origin"] = None
    interaction["marquee_start"] = None
    interaction["marquee_end"] = None
    interaction["press_node_id"] = None
    interaction["press_consumed"] = False
    interaction["ignore_release"] = False

    selection["group_selected_ids"] = []

    canvas_items["node_items_by_id"] = {}
    canvas_items["edge_items"] = []
    canvas_items["marquee_item"] = None

    coordination["pointer-owner"] = None
    coordination["resource-holds"] = {}
    coordination["leases"] = {}

    _init_organisms()


def _init_organisms():
    """Create the organism inventory."""

    organisms[:] = [
        _make_organism("pointer-focus-organism", _run_pointer_focus_organism),
        _make_organism("mode-key-organism", _run_mode_key_organism),
        _make_organism("node-create-organism", _run_node_create_organism),
        _make_organism("node-click-select-organism", _run_node_click_select_organism),
        _make_organism("empty-click-clear-selection-organism", _run_empty_click_clear_selection_organism),
        _make_organism("delete-organism", _run_delete_organism),
    ]


def use_canvas(canvas):
    """Attach to a canvas, or detach by passing None."""

    global canvas_widget

    if canvas_widget is not None:
        unbind_canvas_events()

    canvas_widget = canvas

    if canvas_widget is not None:
        bind_canvas_events()
        _configure_canvas_surface()
        redraw_all()


def use_graph_data(data):
    """Attach graph data, or detach by passing None."""

    global graph_data

    graph_data = data
    _ensure_graph_data_shape()
    redraw_all()


def set_callback(name, fn):
    """Register an optional host callback."""

    callbacks[name] = fn


def bind_canvas_events():
    """Bind the required Tk event surface."""

    if canvas_widget is None:
        return

    canvas_widget.bind("<Button-1>", handle_button_1)
    canvas_widget.bind("<B1-Motion>", handle_button_motion)
    canvas_widget.bind("<ButtonRelease-1>", handle_button_release_1)
    canvas_widget.bind("<KeyPress>", handle_key_press)
    canvas_widget.bind("<KeyRelease>", handle_key_release)


def unbind_canvas_events():
    """Unbind the required Tk event surface."""

    if canvas_widget is None:
        return

    canvas_widget.unbind("<Button-1>")
    canvas_widget.unbind("<B1-Motion>")
    canvas_widget.unbind("<ButtonRelease-1>")
    canvas_widget.unbind("<KeyPress>")
    canvas_widget.unbind("<KeyRelease>")


def _configure_canvas_surface():
    """Apply core canvas configuration."""

    canvas_widget.configure(bg=render["background_color"], takefocus=1)


def handle_button_1(event):
    """Translate Button-1 into RAW and run a cycle."""

    _prepare_pointer_press(event)
    run_cycle()


def handle_button_motion(event):
    """Translate B1-Motion into RAW and run a cycle."""

    _prepare_pointer_motion(event)
    run_cycle()


def handle_button_release_1(event):
    """Translate ButtonRelease-1 into RAW and run a cycle."""

    _prepare_pointer_release(event)
    run_cycle()


def handle_key_press(event):
    """Translate KeyPress into RAW and run a cycle."""

    _prepare_key_event("key-press", event)
    run_cycle()


def handle_key_release(event):
    """Translate KeyRelease into RAW and run a cycle."""

    _prepare_key_event("key-release", event)
    run_cycle()


def _prepare_pointer_press(event):
    _preserve_previous_snapshots()
    interaction["mouse_down_x"] = event.x
    interaction["mouse_down_y"] = event.y
    interaction["last_mouse_x"] = event.x
    interaction["last_mouse_y"] = event.y
    interaction["press_node_id"] = find_node_at(event.x, event.y)
    interaction["press_consumed"] = False
    interaction["ignore_release"] = False
    _update_raw("button-1-press", event)
    _refresh_derived()


def _prepare_pointer_motion(event):
    _preserve_previous_snapshots()
    interaction["last_mouse_x"] = event.x
    interaction["last_mouse_y"] = event.y
    _update_raw("button-1-motion", event)
    _refresh_derived()


def _prepare_pointer_release(event):
    _preserve_previous_snapshots()
    interaction["last_mouse_x"] = event.x
    interaction["last_mouse_y"] = event.y
    _update_raw("button-1-release", event)
    _refresh_derived()


def _prepare_key_event(event_name, event):
    _preserve_previous_snapshots()
    _update_raw(event_name, event)
    _refresh_derived()


def _preserve_previous_snapshots():
    raw_prev.update(raw)
    derived_prev.update(derived)


def _update_raw(event_name, event):
    raw["event_name"] = event_name
    raw["x"] = getattr(event, "x", raw["x"])
    raw["y"] = getattr(event, "y", raw["y"])
    raw["key"] = getattr(event, "keysym", None)
    state = getattr(event, "state", 0)
    raw["shift_down"] = bool(state & 0x0001)
    if event_name == "button-1-press":
        raw["button_1_down"] = True
    elif event_name == "button-1-release":
        raw["button_1_down"] = False
    raw["canvas_has_focus"] = _canvas_has_focus()
    raw["pointer_node_id"] = find_node_at(raw["x"], raw["y"])


def _refresh_derived():
    dx = raw["x"] - interaction["mouse_down_x"]
    dy = raw["y"] - interaction["mouse_down_y"]
    derived["drag_distance"] = math.hypot(dx, dy)
    derived["drag_threshold_crossed"] = derived["drag_distance"] >= render["drag_threshold"]


def run_cycle():
    """Run one judge-pattern cycle from current RAW/DERIVED."""

    if canvas_widget is None or graph_data is None:
        return

    maintain_judge()

    for organism in organisms:
        if not organism["ACTIVE"]:
            continue
        _run_organism(organism)

    apply_effects()
    _finish_cycle()


def _run_organism(organism):
    global current_organism

    current_organism = organism
    organism["FN"](organism)
    current_organism = None


def maintain_judge():
    """Keep coordination state minimal and current."""

    active_names = {organism["NAME"] for organism in organisms if organism["STATE"] != "IDLE"}
    stale_names = [name for name in coordination["leases"] if name not in active_names]

    for name in stale_names:
        _release_lease(name)

    pointer_owner = coordination["pointer-owner"]
    if pointer_owner is not None and pointer_owner not in coordination["leases"]:
        coordination["pointer-owner"] = None


def get_permission(request_type, resources=None):
    """Judge permission entrypoint."""

    if current_organism is None:
        return False

    if resources is None:
        resources = []

    owner = current_organism["NAME"]
    requested = list(resources)

    if request_type not in ("START", "HOLD-RESOURCE"):
        return False

    for resource in requested:
        held_by = coordination["resource-holds"].get(resource)
        if held_by is not None and held_by != owner:
            return False

    _ensure_lease(owner)
    for resource in requested:
        coordination["resource-holds"][resource] = owner
        coordination["leases"][owner]["resources"].add(resource)
        if resource == "pointer":
            coordination["pointer-owner"] = owner
    return True


def emit_effect(effect_type, payload=None):
    """Append an effect to the current effect queue."""

    if payload is None:
        payload = {}
    effects.append({"type": effect_type, "payload": payload})


def apply_effects():
    """Apply all queued effects in order."""

    changed_selection = False
    changed_graph = False

    while effects:
        effect = effects.pop(0)
        effect_type = effect["type"]
        payload = effect["payload"]

        if effect_type == "focus-canvas":
            canvas_widget.focus_set()
        elif effect_type == "consume-pointer-gesture":
            interaction["press_consumed"] = True
            interaction["ignore_release"] = True
        elif effect_type == "set-mode":
            g["mode"] = payload["mode"]
        elif effect_type == "create-node":
            node_id = payload.get("node_id") or _generate_node_id()
            graph_data["nodes"][node_id] = {
                "id": node_id,
                "x": payload["x"],
                "y": payload["y"],
            }
            changed_graph = True
        elif effect_type == "set-single-selection":
            g["selected_node_id"] = payload["node_id"]
            changed_selection = True
        elif effect_type == "clear-single-selection":
            g["selected_node_id"] = None
            changed_selection = True
        elif effect_type == "delete-nodes":
            delete_node_ids(payload["node_ids"])
            changed_graph = True
            changed_selection = True

    if changed_selection and callbacks["on_single_selection_changed"] is not None:
        callbacks["on_single_selection_changed"](g["selected_node_id"])

    if changed_graph and callbacks["on_graph_mutated"] is not None:
        callbacks["on_graph_mutated"]()

    redraw_all()


def redraw_all():
    """Rebuild the canvas projection from graph state."""

    if canvas_widget is None:
        return

    canvas_widget.delete("all")
    canvas_items["node_items_by_id"] = {}
    canvas_items["edge_items"] = []
    canvas_items["marquee_item"] = None

    if graph_data is None:
        return

    for edge in graph_data["edges"]:
        edge_item = _draw_edge(edge)
        if edge_item is not None:
            canvas_items["edge_items"].append(edge_item)

    for node_id, node in graph_data["nodes"].items():
        canvas_items["node_items_by_id"][node_id] = _draw_node(node)


def _draw_edge(edge):
    from_node = graph_data["nodes"].get(edge["from"])
    to_node = graph_data["nodes"].get(edge["to"])
    if from_node is None or to_node is None:
        return None

    radius = render["node_radius"]
    pull = render["edge_vertical_pull"]
    p0 = (from_node["x"], from_node["y"] + radius)
    p1 = (from_node["x"], from_node["y"] + radius + pull)
    p2 = (to_node["x"], to_node["y"] - radius - pull)
    p3 = (to_node["x"], to_node["y"] - radius)

    return canvas_widget.create_line(
        p0[0], p0[1],
        p1[0], p1[1],
        p2[0], p2[1],
        p3[0], p3[1],
        fill=render["edge_color"],
        smooth=True,
        width=2,
    )


def _draw_node(node):
    x = node["x"]
    y = node["y"]
    radius = render["node_radius"]

    item_ids = {
        "outer": canvas_widget.create_oval(
            x - radius,
            y - radius,
            x + radius,
            y + radius,
            outline=render["node_outline_color"],
            width=render["node_outline_width"],
            fill=render["node_fill_color"],
        ),
    }

    if node["id"] in selection["group_selected_ids"]:
        halo_radius = radius + render["group_halo_radius_offset"]
        item_ids["halo"] = canvas_widget.create_oval(
            x - halo_radius,
            y - halo_radius,
            x + halo_radius,
            y + halo_radius,
            outline=render["group_halo_color"],
            width=render["group_halo_width"],
        )

    if node["id"] == g["selected_node_id"]:
        inner_radius = render["selected_inner_radius"]
        item_ids["inner"] = canvas_widget.create_oval(
            x - inner_radius,
            y - inner_radius,
            x + inner_radius,
            y + inner_radius,
            outline=render["selected_inner_color"],
            width=render["selected_inner_width"],
            fill=render["selected_fill_color"],
        )

    return item_ids


def find_node_at(x, y):
    """Return the topmost node hit by the point, or None."""

    if graph_data is None:
        return None

    radius = render["node_radius"] + render["hit_slop"]
    nodes = list(graph_data["nodes"].values())
    nodes.reverse()

    for node in nodes:
        dx = x - node["x"]
        dy = y - node["y"]
        if math.hypot(dx, dy) <= radius:
            return node["id"]

    return None


def create_node_at(x, y, node_id=None):
    """Create a node and redraw."""

    emit_effect("create-node", {"x": x, "y": y, "node_id": node_id})
    apply_effects()


def select_single_node(node_id):
    """Set single selection."""

    emit_effect("set-single-selection", {"node_id": node_id})
    apply_effects()


def clear_single_selection():
    """Clear single selection."""

    emit_effect("clear-single-selection")
    apply_effects()


def delete_selected():
    """Delete group selection or single selection."""

    node_ids = []
    if selection["group_selected_ids"]:
        node_ids = list(selection["group_selected_ids"])
    elif g["selected_node_id"] is not None:
        node_ids = [g["selected_node_id"]]

    if node_ids:
        emit_effect("delete-nodes", {"node_ids": node_ids})
        apply_effects()


def delete_node_ids(node_ids):
    """Delete nodes and any edges touching them."""

    node_id_set = set(node_ids)
    for node_id in node_id_set:
        graph_data["nodes"].pop(node_id, None)

    graph_data["edges"] = [
        edge
        for edge in graph_data["edges"]
        if edge["from"] not in node_id_set and edge["to"] not in node_id_set
    ]

    selection["group_selected_ids"] = [
        node_id
        for node_id in selection["group_selected_ids"]
        if node_id not in node_id_set
    ]

    if g["selected_node_id"] in node_id_set:
        g["selected_node_id"] = None


def _run_pointer_focus_organism(organism):
    if raw["event_name"] != "button-1-press":
        organism["STATE"] = "IDLE"
        organism["HELD"] = {}
        return

    if raw["canvas_has_focus"]:
        organism["STATE"] = "IDLE"
        organism["HELD"] = {}
        return

    if not get_permission("START", ["pointer"]):
        return

    organism["STATE"] = "HANDLED"
    organism["HELD"] = {"pointer": True}
    emit_effect("focus-canvas")
    emit_effect("consume-pointer-gesture")


def _run_mode_key_organism(organism):
    if raw["event_name"] != "key-press":
        organism["STATE"] = "IDLE"
        organism["HELD"] = {}
        return

    if not raw["canvas_has_focus"]:
        organism["STATE"] = "IDLE"
        organism["HELD"] = {}
        return

    mode = None
    if raw["key"] in ("n", "N"):
        mode = "CREATE_NODE"
    elif raw["key"] == "Escape":
        mode = "IDLE"

    if mode is None:
        organism["STATE"] = "IDLE"
        organism["HELD"] = {}
        return

    if not get_permission("START", ["interaction-mode"]):
        return

    organism["STATE"] = "HANDLED"
    organism["HELD"] = {"mode": mode}
    emit_effect("set-mode", {"mode": mode})


def _run_node_create_organism(organism):
    if raw["event_name"] != "button-1-release":
        organism["STATE"] = "IDLE"
        organism["HELD"] = {}
        return

    if g["mode"] != "CREATE_NODE":
        organism["STATE"] = "IDLE"
        organism["HELD"] = {}
        return

    if interaction["ignore_release"] or interaction["press_consumed"]:
        organism["STATE"] = "IDLE"
        organism["HELD"] = {}
        return

    if interaction["press_node_id"] is not None:
        organism["STATE"] = "IDLE"
        organism["HELD"] = {}
        return

    if not get_permission("START"):
        return

    organism["STATE"] = "HANDLED"
    organism["HELD"] = {}
    emit_effect("create-node", {"x": raw["x"], "y": raw["y"]})
    next_id = _peek_next_node_id()
    emit_effect("set-single-selection", {"node_id": next_id})
    emit_effect("set-mode", {"mode": "IDLE"})


def _run_node_click_select_organism(organism):
    if raw["event_name"] != "button-1-release":
        organism["STATE"] = "IDLE"
        organism["HELD"] = {}
        return

    if g["mode"] != "IDLE":
        organism["STATE"] = "IDLE"
        organism["HELD"] = {}
        return

    if interaction["ignore_release"] or interaction["press_consumed"]:
        organism["STATE"] = "IDLE"
        organism["HELD"] = {}
        return

    if derived["drag_threshold_crossed"]:
        organism["STATE"] = "IDLE"
        organism["HELD"] = {}
        return

    node_id = interaction["press_node_id"]
    if node_id is None or raw["pointer_node_id"] != node_id:
        organism["STATE"] = "IDLE"
        organism["HELD"] = {}
        return

    if not get_permission("START", ["selection:single"]):
        return

    organism["STATE"] = "HANDLED"
    organism["HELD"] = {"selection": "single"}
    emit_effect("set-single-selection", {"node_id": node_id})


def _run_empty_click_clear_selection_organism(organism):
    if raw["event_name"] != "button-1-release":
        organism["STATE"] = "IDLE"
        organism["HELD"] = {}
        return

    if g["mode"] != "IDLE":
        organism["STATE"] = "IDLE"
        organism["HELD"] = {}
        return

    if interaction["ignore_release"] or interaction["press_consumed"]:
        organism["STATE"] = "IDLE"
        organism["HELD"] = {}
        return

    if derived["drag_threshold_crossed"]:
        organism["STATE"] = "IDLE"
        organism["HELD"] = {}
        return

    if interaction["press_node_id"] is not None:
        organism["STATE"] = "IDLE"
        organism["HELD"] = {}
        return

    if raw["pointer_node_id"] is not None:
        organism["STATE"] = "IDLE"
        organism["HELD"] = {}
        return

    if not get_permission("START", ["selection:single"]):
        return

    organism["STATE"] = "HANDLED"
    organism["HELD"] = {"selection": "single"}
    emit_effect("clear-single-selection")


def _run_delete_organism(organism):
    if raw["event_name"] != "key-press" or raw["key"] != "Delete":
        organism["STATE"] = "IDLE"
        organism["HELD"] = {}
        return

    if not raw["canvas_has_focus"]:
        organism["STATE"] = "IDLE"
        organism["HELD"] = {}
        return

    node_ids = []
    if selection["group_selected_ids"]:
        node_ids = list(selection["group_selected_ids"])
    elif g["selected_node_id"] is not None:
        node_ids = [g["selected_node_id"]]

    if not node_ids:
        organism["STATE"] = "IDLE"
        organism["HELD"] = {}
        return

    if not get_permission("START"):
        return

    organism["STATE"] = "HANDLED"
    organism["HELD"] = {}
    emit_effect("delete-nodes", {"node_ids": node_ids})


def _ensure_graph_data_shape():
    if graph_data is None:
        return

    if "nodes" not in graph_data:
        graph_data["nodes"] = {}
    if "edges" not in graph_data:
        graph_data["edges"] = []


def _ensure_lease(owner):
    if owner not in coordination["leases"]:
        coordination["leases"][owner] = {
            "resources": set(),
            "kind": "exclusive",
            "valid": True,
        }


def _release_lease(owner):
    lease = coordination["leases"].pop(owner, None)
    if lease is None:
        return

    for resource in lease["resources"]:
        if coordination["resource-holds"].get(resource) == owner:
            coordination["resource-holds"].pop(resource, None)

    if coordination["pointer-owner"] == owner:
        coordination["pointer-owner"] = None


def _finish_cycle():
    if raw["event_name"] == "button-1-release":
        interaction["press_node_id"] = None
        interaction["press_consumed"] = False
        interaction["ignore_release"] = False


def _canvas_has_focus():
    if canvas_widget is None:
        return False
    return canvas_widget.focus_get() == canvas_widget


def _generate_node_id():
    fn = callbacks["generate_node_id"]
    if fn is not None:
        return fn()
    return _peek_next_node_id()


def _peek_next_node_id():
    index = 1
    if graph_data is None:
        return "node-0001"

    while True:
        node_id = f"node-{index:04d}"
        if node_id not in graph_data["nodes"]:
            return node_id
        index += 1


reset_runtime()
