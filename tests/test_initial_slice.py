"""tkintertester coverage for the initial judge-pattern slice."""

from types import SimpleNamespace

import tkinter as tk
import tkintertester
import tkintertester.harness as harness

from nodebrowser import nodebrowser as core
from nodebrowser import ui


TEST_GRAPH = None
APP_STATE = {"app": None}
ORIGINAL_CANVAS_HAS_FOCUS = core._canvas_has_focus


def make_event(canvas, x=0, y=0, keysym=None, state=0):
    """Construct a minimal Tk-like event object."""

    return SimpleNamespace(widget=canvas, x=x, y=y, keysym=keysym, state=state)


def app_entry():
    """Create a fresh Toplevel-hosted app for tkintertester."""

    parent = tk._default_root
    APP_STATE["app"] = ui.create_app(parent=parent, graph_data=_copy_graph(TEST_GRAPH), title="nodebrowser-test")


def app_reset():
    """Destroy the hosted app between tests."""

    ui.destroy_app(APP_STATE["app"])
    APP_STATE["app"] = None


def setup_harness():
    """Reset tkintertester globals between pytest cases."""

    core._canvas_has_focus = ORIGINAL_CANVAS_HAS_FOCUS
    harness.tests.clear()
    harness.g["test_index"] = 0
    harness.g["current_test"] = None
    harness.g["current_step_index"] = 0
    harness.g["test_done"] = False
    harness.g["current_timeout_after_id"] = None
    harness.g["start_time"] = None
    harness.g["exit_requested"] = False
    tkintertester.set_resetfn(app_reset)
    tkintertester.set_timeout(1000)


def run_suite():
    """Run the registered tkintertester tests."""

    tkintertester.run_host(app_entry, "x")
    results = tkintertester.get_results("J")
    assert '"status": "fail"' not in results
    assert '"status": "timeout"' not in results


def _copy_graph(graph):
    if graph is None:
        return {"nodes": {}, "edges": []}

    return {
        "nodes": {
            node_id: dict(node)
            for node_id, node in graph["nodes"].items()
        },
        "edges": [dict(edge) for edge in graph["edges"]],
    }


def force_canvas_focus():
    """Force focused-canvas behavior for hidden-root tkintertester runs."""

    APP_STATE["app"]["canvas"].focus_set()
    core._canvas_has_focus = lambda: True


def force_canvas_blur():
    """Force unfocused-canvas behavior for tests that need it."""

    APP_STATE["app"]["window"].focus_set()
    core._canvas_has_focus = lambda: False


def get_organism(name):
    """Return the organism dict with the given name."""

    for organism in core.organisms:
        if organism["NAME"] == name:
            return organism
    raise AssertionError(f"missing organism: {name}")


def test_focus_click_is_consumed_before_create_mode_click():
    global TEST_GRAPH

    TEST_GRAPH = {"nodes": {}, "edges": []}
    setup_harness()

    def step_arm_create_mode():
        core.g["mode"] = "CREATE_NODE"
        return ("next", None)

    def step_blur_canvas():
        force_canvas_blur()
        return ("next", None)

    def step_click_without_focus():
        app = APP_STATE["app"]
        core.handle_button_1(make_event(app["canvas"], x=120, y=140))
        core.handle_button_release_1(make_event(app["canvas"], x=120, y=140))
        return ("next", None)

    def step_assert_consumed():
        nodes = APP_STATE["app"]["graph_data"]["nodes"]
        if nodes:
            return ("fail", "focus click should not create a node")
        if core.g["mode"] != "CREATE_NODE":
            return ("fail", "focus click should not leave create mode")
        return ("success", None)

    tkintertester.add_test(
        "focus click is consumed",
        [step_arm_create_mode, step_blur_canvas, step_click_without_focus, step_assert_consumed],
    )
    run_suite()


def test_key_n_then_click_creates_and_selects_node():
    global TEST_GRAPH

    TEST_GRAPH = {"nodes": {}, "edges": []}
    setup_harness()

    def step_focus_canvas():
        force_canvas_focus()
        return ("next", None)

    def step_press_n():
        app = APP_STATE["app"]
        core.handle_key_press(make_event(app["canvas"], keysym="n"))
        return ("next", None)

    def step_click_canvas():
        app = APP_STATE["app"]
        core.handle_button_1(make_event(app["canvas"], x=220, y=180))
        core.handle_button_release_1(make_event(app["canvas"], x=220, y=180))
        return ("next", None)

    def step_assert_created():
        nodes = APP_STATE["app"]["graph_data"]["nodes"]
        if len(nodes) != 1:
            return ("fail", "expected one node to be created")
        node_id = next(iter(nodes))
        node = nodes[node_id]
        if (node["x"], node["y"]) != (220, 180):
            return ("fail", "created node landed at the wrong coordinates")
        if core.g["selected_node_id"] != node_id:
            return ("fail", "created node should become the single selection")
        if core.g["mode"] != "IDLE":
            return ("fail", "create mode should return to IDLE after one click")
        return ("success", None)

    tkintertester.add_test(
        "n then click creates a node",
        [step_focus_canvas, step_press_n, step_click_canvas, step_assert_created],
    )
    run_suite()


def test_quantized_create_node_snaps_to_grid():
    global TEST_GRAPH

    TEST_GRAPH = {"nodes": {}, "edges": []}
    setup_harness()

    def step_focus_canvas():
        force_canvas_focus()
        return ("next", None)

    def step_enable_quantizing():
        app = APP_STATE["app"]
        core.handle_key_press(make_event(app["canvas"], keysym="q"))
        return ("next", None)

    def step_press_n():
        app = APP_STATE["app"]
        core.handle_key_press(make_event(app["canvas"], keysym="n"))
        return ("next", None)

    def step_click_canvas():
        app = APP_STATE["app"]
        core.handle_button_1(make_event(app["canvas"], x=213, y=187))
        core.handle_button_release_1(make_event(app["canvas"], x=213, y=187))
        return ("next", None)

    def step_assert_created():
        nodes = APP_STATE["app"]["graph_data"]["nodes"]
        if len(nodes) != 1:
            return ("fail", "expected one quantized node to be created")
        node = next(iter(nodes.values()))
        if (node["x"], node["y"]) != (220, 180):
            return ("fail", "quantized node creation should snap to the grid")
        return ("success", None)

    tkintertester.add_test(
        "quantized create node",
        [
            step_focus_canvas,
            step_enable_quantizing,
            step_press_n,
            step_click_canvas,
            step_assert_created,
        ],
    )
    run_suite()


def test_click_selects_then_empty_click_clears_selection():
    global TEST_GRAPH

    TEST_GRAPH = {
        "nodes": {
            "node-0001": {"id": "node-0001", "x": 180, "y": 160},
        },
        "edges": [],
    }
    setup_harness()

    def step_focus_canvas():
        force_canvas_focus()
        return ("next", None)

    def step_select_node():
        app = APP_STATE["app"]
        core.handle_button_1(make_event(app["canvas"], x=180, y=160))
        core.handle_button_release_1(make_event(app["canvas"], x=180, y=160))
        return ("next", None)

    def step_assert_selected():
        if core.g["selected_node_id"] != "node-0001":
            return ("fail", "node click should select node-0001")
        return ("next", None)

    def step_click_empty_space():
        app = APP_STATE["app"]
        core.handle_button_1(make_event(app["canvas"], x=40, y=40))
        core.handle_button_release_1(make_event(app["canvas"], x=40, y=40))
        return ("next", None)

    def step_assert_cleared():
        if core.g["selected_node_id"] is not None:
            return ("fail", "empty click should clear single selection")
        return ("success", None)

    tkintertester.add_test(
        "select then clear",
        [
            step_focus_canvas,
            step_select_node,
            step_assert_selected,
            step_click_empty_space,
            step_assert_cleared,
        ],
    )
    run_suite()


def test_delete_removes_selected_node_and_incident_edges():
    global TEST_GRAPH

    TEST_GRAPH = {
        "nodes": {
            "node-0001": {"id": "node-0001", "x": 180, "y": 160},
            "node-0002": {"id": "node-0002", "x": 320, "y": 260},
        },
        "edges": [
            {"from": "node-0001", "to": "node-0002"},
        ],
    }
    setup_harness()

    def step_focus_canvas():
        force_canvas_focus()
        return ("next", None)

    def step_select_node():
        app = APP_STATE["app"]
        core.handle_button_1(make_event(app["canvas"], x=180, y=160))
        core.handle_button_release_1(make_event(app["canvas"], x=180, y=160))
        return ("next", None)

    def step_delete():
        app = APP_STATE["app"]
        core.handle_key_press(make_event(app["canvas"], keysym="Delete"))
        return ("next", None)

    def step_assert_deleted():
        graph = APP_STATE["app"]["graph_data"]
        if "node-0001" in graph["nodes"]:
            return ("fail", "selected node should be deleted")
        if graph["edges"]:
            return ("fail", "incident edges should be deleted with the node")
        if core.g["selected_node_id"] is not None:
            return ("fail", "selection should clear after deletion")
        return ("success", None)

    tkintertester.add_test(
        "delete selected node",
        [step_focus_canvas, step_select_node, step_delete, step_assert_deleted],
    )
    run_suite()


def test_q_toggles_quantizing_mode():
    global TEST_GRAPH

    TEST_GRAPH = {"nodes": {}, "edges": []}
    setup_harness()

    def step_focus_canvas():
        force_canvas_focus()
        return ("next", None)

    def step_press_q_once():
        app = APP_STATE["app"]
        core.handle_key_press(make_event(app["canvas"], keysym="q"))
        return ("next", None)

    def step_assert_on():
        if not core.g["quantizing"]:
            return ("fail", "q should turn quantizing on")
        return ("next", None)

    def step_press_q_again():
        app = APP_STATE["app"]
        core.handle_key_press(make_event(app["canvas"], keysym="q"))
        return ("next", None)

    def step_assert_off():
        if core.g["quantizing"]:
            return ("fail", "q should toggle quantizing back off")
        return ("success", None)

    tkintertester.add_test(
        "q toggles quantizing",
        [
            step_focus_canvas,
            step_press_q_once,
            step_assert_on,
            step_press_q_again,
            step_assert_off,
        ],
    )
    run_suite()


def test_drag_moves_node_and_releases_judge_holds_on_release():
    global TEST_GRAPH

    TEST_GRAPH = {
        "nodes": {
            "node-0001": {"id": "node-0001", "x": 180, "y": 160},
        },
        "edges": [],
    }
    setup_harness()

    def step_focus_canvas():
        force_canvas_focus()
        return ("next", None)

    def step_press_node():
        app = APP_STATE["app"]
        core.handle_button_1(make_event(app["canvas"], x=180, y=160))
        return ("next", None)

    def step_drag_node():
        app = APP_STATE["app"]
        core.handle_button_motion(make_event(app["canvas"], x=210, y=195))
        return ("next", None)

    def step_assert_dragged():
        node = APP_STATE["app"]["graph_data"]["nodes"]["node-0001"]
        if (node["x"], node["y"]) != (210, 195):
            return ("fail", "drag should move the node by pointer delta")
        if core.coordination["pointer-owner"] != "node-drag-organism":
            return ("fail", "judge should grant pointer ownership during drag")
        if core.coordination["resource-holds"].get("node:node-0001") != "node-drag-organism":
            return ("fail", "judge should grant node ownership during drag")
        if core.g["selected_node_id"] is not None:
            return ("fail", "drag should not imply single selection")
        return ("next", None)

    def step_release_node():
        app = APP_STATE["app"]
        core.handle_button_release_1(make_event(app["canvas"], x=210, y=195))
        return ("next", None)

    def step_assert_released():
        if core.coordination["pointer-owner"] is not None:
            return ("fail", "judge should release pointer ownership after drag ends")
        if core.coordination["resource-holds"]:
            return ("fail", "judge should clear drag resource holds after release")
        return ("success", None)

    tkintertester.add_test(
        "drag node",
        [
            step_focus_canvas,
            step_press_node,
            step_drag_node,
            step_assert_dragged,
            step_release_node,
            step_assert_released,
        ],
    )
    run_suite()


def test_quantized_drag_snaps_node_preview_and_release_position():
    global TEST_GRAPH

    TEST_GRAPH = {
        "nodes": {
            "node-0001": {"id": "node-0001", "x": 183, "y": 157},
        },
        "edges": [],
    }
    setup_harness()

    def step_focus_canvas():
        force_canvas_focus()
        return ("next", None)

    def step_enable_quantizing():
        app = APP_STATE["app"]
        core.handle_key_press(make_event(app["canvas"], keysym="q"))
        return ("next", None)

    def step_press_node():
        app = APP_STATE["app"]
        core.handle_button_1(make_event(app["canvas"], x=183, y=157))
        return ("next", None)

    def step_drag_node():
        app = APP_STATE["app"]
        core.handle_button_motion(make_event(app["canvas"], x=196, y=174))
        return ("next", None)

    def step_assert_quantized_preview():
        node = APP_STATE["app"]["graph_data"]["nodes"]["node-0001"]
        if (node["x"], node["y"]) != (200, 180):
            return ("fail", "quantized node drag should preview the snapped location")
        return ("next", None)

    def step_release_node():
        app = APP_STATE["app"]
        core.handle_button_release_1(make_event(app["canvas"], x=196, y=174))
        return ("next", None)

    def step_assert_quantized_release():
        node = APP_STATE["app"]["graph_data"]["nodes"]["node-0001"]
        if (node["x"], node["y"]) != (200, 180):
            return ("fail", "quantized node drag should keep the snapped location on release")
        return ("success", None)

    tkintertester.add_test(
        "quantized node drag",
        [
            step_focus_canvas,
            step_enable_quantizing,
            step_press_node,
            step_drag_node,
            step_assert_quantized_preview,
            step_release_node,
            step_assert_quantized_release,
        ],
    )
    run_suite()


def test_marquee_drag_selects_group_and_releases_judge_holds():
    global TEST_GRAPH

    TEST_GRAPH = {
        "nodes": {
            "node-0001": {"id": "node-0001", "x": 180, "y": 160},
            "node-0002": {"id": "node-0002", "x": 360, "y": 260},
        },
        "edges": [],
    }
    setup_harness()

    def step_focus_canvas():
        force_canvas_focus()
        return ("next", None)

    def step_press_empty():
        app = APP_STATE["app"]
        core.handle_button_1(make_event(app["canvas"], x=120, y=120))
        return ("next", None)

    def step_drag_marquee():
        app = APP_STATE["app"]
        core.handle_button_motion(make_event(app["canvas"], x=240, y=220))
        return ("next", None)

    def step_assert_dragging():
        if core.coordination["pointer-owner"] != "marquee-select-organism":
            return ("fail", "judge should grant pointer ownership during marquee drag")
        if core.coordination["resource-holds"].get("group-selection") != "marquee-select-organism":
            return ("fail", "judge should grant group-selection authority during marquee drag")
        if get_organism("marquee-select-organism")["STATE"] != "ACTIVE":
            return ("fail", "marquee organism should become ACTIVE after threshold is crossed")
        if core.derived["drag_rect"] != {"x1": 120, "y1": 120, "x2": 240, "y2": 220}:
            return ("fail", "drag tokenizer should publish the current drag rectangle")
        if core.canvas_items["marquee_item"] is None:
            return ("fail", "marquee preview should be rendered during drag")
        return ("next", None)

    def step_release():
        app = APP_STATE["app"]
        core.handle_button_release_1(make_event(app["canvas"], x=240, y=220))
        return ("next", None)

    def step_assert_selection():
        if core.selection["group_selected_ids"] != ["node-0001"]:
            return ("fail", "marquee release should replace group selection with enclosed nodes")
        if core.coordination["pointer-owner"] is not None:
            return ("fail", "judge should release pointer ownership after marquee drag")
        if core.coordination["resource-holds"]:
            return ("fail", "judge should clear marquee resource holds after release")
        if core.canvas_items["marquee_item"] is not None:
            return ("fail", "marquee preview should be cleared after release")
        return ("success", None)

    tkintertester.add_test(
        "marquee select",
        [
            step_focus_canvas,
            step_press_empty,
            step_drag_marquee,
            step_assert_dragging,
            step_release,
            step_assert_selection,
        ],
    )
    run_suite()


def test_shift_empty_drag_pans_viewport_instead_of_marquee():
    global TEST_GRAPH

    TEST_GRAPH = {
        "nodes": {
            "node-0001": {"id": "node-0001", "x": 180, "y": 160},
        },
        "edges": [],
    }
    setup_harness()

    def step_focus_canvas():
        force_canvas_focus()
        return ("next", None)

    def step_press_empty_with_shift():
        app = APP_STATE["app"]
        core.handle_button_1(make_event(app["canvas"], x=40, y=40, state=1))
        return ("next", None)

    def step_drag_pan():
        app = APP_STATE["app"]
        core.handle_button_motion(make_event(app["canvas"], x=70, y=65, state=1))
        return ("next", None)

    def step_assert_panning():
        if core.coordination["pointer-owner"] != "pan-organism":
            return ("fail", "shift-empty drag should grant pointer ownership to pan-organism")
        if core.coordination["resource-holds"].get("viewport") != "pan-organism":
            return ("fail", "shift-empty drag should grant viewport ownership to pan-organism")
        if (core.viewport["offset_x"], core.viewport["offset_y"]) != (30, 25):
            return ("fail", "panning should move the viewport by the pointer delta")
        if core.canvas_items["marquee_item"] is not None:
            return ("fail", "shift-empty drag should not show a marquee preview")
        coords = APP_STATE["app"]["canvas"].coords(core.canvas_items["node_items_by_id"]["node-0001"]["outer"])
        if coords != [185.0, 160.0, 235.0, 210.0]:
            return ("fail", "node projection should shift by the viewport offset during pan")
        return ("next", None)

    def step_release():
        app = APP_STATE["app"]
        core.handle_button_release_1(make_event(app["canvas"], x=70, y=65, state=1))
        return ("next", None)

    def step_assert_release():
        if core.coordination["pointer-owner"] is not None:
            return ("fail", "judge should release pointer ownership after panning")
        if core.coordination["resource-holds"]:
            return ("fail", "judge should clear pan holds after release")
        return ("success", None)

    tkintertester.add_test(
        "shift empty drag pans viewport",
        [
            step_focus_canvas,
            step_press_empty_with_shift,
            step_drag_pan,
            step_assert_panning,
            step_release,
            step_assert_release,
        ],
    )
    run_suite()


def test_click_hit_testing_uses_viewport_offset_after_pan():
    global TEST_GRAPH

    TEST_GRAPH = {
        "nodes": {
            "node-0001": {"id": "node-0001", "x": 180, "y": 160},
        },
        "edges": [],
    }
    setup_harness()

    def step_focus_canvas():
        force_canvas_focus()
        return ("next", None)

    def step_seed_viewport_offset():
        core.viewport["offset_x"] = 30
        core.viewport["offset_y"] = 25
        core.redraw_all()
        return ("next", None)

    def step_click_shifted_node():
        app = APP_STATE["app"]
        core.handle_button_1(make_event(app["canvas"], x=210, y=185))
        core.handle_button_release_1(make_event(app["canvas"], x=210, y=185))
        return ("next", None)

    def step_assert_selected():
        if core.g["selected_node_id"] != "node-0001":
            return ("fail", "hit testing should account for viewport offset when selecting nodes")
        return ("success", None)

    tkintertester.add_test(
        "viewport-aware hit testing",
        [
            step_focus_canvas,
            step_seed_viewport_offset,
            step_click_shifted_node,
            step_assert_selected,
        ],
    )
    run_suite()


def test_marquee_selection_commit_uses_viewport_offset_after_pan():
    global TEST_GRAPH

    TEST_GRAPH = {
        "nodes": {
            "node-0001": {"id": "node-0001", "x": 180, "y": 160},
            "node-0002": {"id": "node-0002", "x": 360, "y": 260},
        },
        "edges": [],
    }
    setup_harness()

    def step_focus_canvas():
        force_canvas_focus()
        return ("next", None)

    def step_seed_viewport_offset():
        core.viewport["offset_x"] = 30
        core.viewport["offset_y"] = 25
        core.redraw_all()
        return ("next", None)

    def step_press_empty():
        app = APP_STATE["app"]
        core.handle_button_1(make_event(app["canvas"], x=150, y=140))
        return ("next", None)

    def step_drag_marquee():
        app = APP_STATE["app"]
        core.handle_button_motion(make_event(app["canvas"], x=250, y=210))
        return ("next", None)

    def step_release_marquee():
        app = APP_STATE["app"]
        core.handle_button_release_1(make_event(app["canvas"], x=250, y=210))
        return ("next", None)

    def step_assert_selection():
        if core.selection["group_selected_ids"] != ["node-0001"]:
            return ("fail", "marquee commit should use screen-space viewport-adjusted hit testing")
        return ("success", None)

    tkintertester.add_test(
        "viewport-aware marquee commit",
        [
            step_focus_canvas,
            step_seed_viewport_offset,
            step_press_empty,
            step_drag_marquee,
            step_release_marquee,
            step_assert_selection,
        ],
    )
    run_suite()


def test_empty_click_clears_group_selection_too():
    global TEST_GRAPH

    TEST_GRAPH = {
        "nodes": {
            "node-0001": {"id": "node-0001", "x": 180, "y": 160},
            "node-0002": {"id": "node-0002", "x": 360, "y": 260},
        },
        "edges": [],
    }
    setup_harness()

    def step_focus_canvas():
        force_canvas_focus()
        return ("next", None)

    def step_seed_selection():
        core.g["selected_node_id"] = "node-0002"
        core.selection["group_selected_ids"] = ["node-0001"]
        core.redraw_all()
        return ("next", None)

    def step_click_empty_space():
        app = APP_STATE["app"]
        core.handle_button_1(make_event(app["canvas"], x=40, y=40))
        core.handle_button_release_1(make_event(app["canvas"], x=40, y=40))
        return ("next", None)

    def step_assert_cleared():
        if core.g["selected_node_id"] is not None:
            return ("fail", "empty click should clear single selection")
        if core.selection["group_selected_ids"]:
            return ("fail", "empty click should clear group selection")
        return ("success", None)

    tkintertester.add_test(
        "empty click clears both selections",
        [
            step_focus_canvas,
            step_seed_selection,
            step_click_empty_space,
            step_assert_cleared,
        ],
    )
    run_suite()


def test_marquee_preview_adds_light_blue_halo_to_enclosed_nodes():
    global TEST_GRAPH

    TEST_GRAPH = {
        "nodes": {
            "node-0001": {"id": "node-0001", "x": 180, "y": 160},
            "node-0002": {"id": "node-0002", "x": 360, "y": 260},
        },
        "edges": [],
    }
    setup_harness()

    def step_focus_canvas():
        force_canvas_focus()
        return ("next", None)

    def step_start_marquee():
        app = APP_STATE["app"]
        core.handle_button_1(make_event(app["canvas"], x=120, y=120))
        core.handle_button_motion(make_event(app["canvas"], x=240, y=220))
        return ("next", None)

    def step_assert_preview_halo():
        item_ids = core.canvas_items["node_items_by_id"]["node-0001"]
        if "preview_halo" not in item_ids:
            return ("fail", "enclosed node should show preview halo during marquee drag")
        item_ids_2 = core.canvas_items["node_items_by_id"]["node-0002"]
        if "preview_halo" in item_ids_2:
            return ("fail", "non-enclosed node should not show preview halo during marquee drag")
        return ("success", None)

    tkintertester.add_test(
        "marquee preview halo",
        [
            step_focus_canvas,
            step_start_marquee,
            step_assert_preview_halo,
        ],
    )
    run_suite()


def test_group_drag_moves_all_group_selected_nodes():
    global TEST_GRAPH

    TEST_GRAPH = {
        "nodes": {
            "node-0001": {"id": "node-0001", "x": 180, "y": 160},
            "node-0002": {"id": "node-0002", "x": 260, "y": 220},
            "node-0003": {"id": "node-0003", "x": 420, "y": 320},
        },
        "edges": [],
    }
    setup_harness()

    def step_focus_canvas():
        force_canvas_focus()
        return ("next", None)

    def step_seed_group_selection():
        core.selection["group_selected_ids"] = ["node-0001", "node-0002"]
        core.redraw_all()
        return ("next", None)

    def step_press_group_node():
        app = APP_STATE["app"]
        core.handle_button_1(make_event(app["canvas"], x=180, y=160))
        return ("next", None)

    def step_drag_group():
        app = APP_STATE["app"]
        core.handle_button_motion(make_event(app["canvas"], x=210, y=195))
        return ("next", None)

    def step_assert_dragging():
        graph = APP_STATE["app"]["graph_data"]
        if (graph["nodes"]["node-0001"]["x"], graph["nodes"]["node-0001"]["y"]) != (210, 195):
            return ("fail", "group drag should move the pressed group node by pointer delta")
        if (graph["nodes"]["node-0002"]["x"], graph["nodes"]["node-0002"]["y"]) != (290, 255):
            return ("fail", "group drag should move every group-selected node by the same delta")
        if (graph["nodes"]["node-0003"]["x"], graph["nodes"]["node-0003"]["y"]) != (420, 320):
            return ("fail", "group drag should not move nodes outside the group selection")
        if core.coordination["pointer-owner"] != "group-drag-organism":
            return ("fail", "judge should grant pointer ownership to group-drag-organism during drag")
        if core.coordination["resource-holds"].get("group-selection") != "group-drag-organism":
            return ("fail", "judge should grant group-selection ownership during group drag")
        if core.coordination["resource-holds"].get("node:node-0001") is not None:
            return ("fail", "single-node drag ownership should not be taken during group drag")
        return ("next", None)

    def step_release():
        app = APP_STATE["app"]
        core.handle_button_release_1(make_event(app["canvas"], x=210, y=195))
        return ("next", None)

    def step_assert_released():
        if core.coordination["pointer-owner"] is not None:
            return ("fail", "judge should release pointer ownership after group drag")
        if core.coordination["resource-holds"]:
            return ("fail", "judge should clear group drag holds after release")
        return ("success", None)

    tkintertester.add_test(
        "group drag",
        [
            step_focus_canvas,
            step_seed_group_selection,
            step_press_group_node,
            step_drag_group,
            step_assert_dragging,
            step_release,
            step_assert_released,
        ],
    )
    run_suite()


def test_quantized_group_drag_snaps_from_pressed_node_and_preserves_offsets():
    global TEST_GRAPH

    TEST_GRAPH = {
        "nodes": {
            "node-0001": {"id": "node-0001", "x": 183, "y": 157},
            "node-0002": {"id": "node-0002", "x": 263, "y": 217},
            "node-0003": {"id": "node-0003", "x": 420, "y": 320},
        },
        "edges": [],
    }
    setup_harness()

    def step_focus_canvas():
        force_canvas_focus()
        return ("next", None)

    def step_enable_quantizing():
        app = APP_STATE["app"]
        core.handle_key_press(make_event(app["canvas"], keysym="q"))
        return ("next", None)

    def step_seed_group_selection():
        core.selection["group_selected_ids"] = ["node-0001", "node-0002"]
        core.redraw_all()
        return ("next", None)

    def step_press_group_node():
        app = APP_STATE["app"]
        core.handle_button_1(make_event(app["canvas"], x=183, y=157))
        return ("next", None)

    def step_drag_group():
        app = APP_STATE["app"]
        core.handle_button_motion(make_event(app["canvas"], x=196, y=174))
        return ("next", None)

    def step_assert_quantized_preview():
        graph = APP_STATE["app"]["graph_data"]["nodes"]
        if (graph["node-0001"]["x"], graph["node-0001"]["y"]) != (200, 180):
            return ("fail", "quantized group drag should snap based on the pressed node")
        if (graph["node-0002"]["x"], graph["node-0002"]["y"]) != (280, 240):
            return ("fail", "quantized group drag should preserve relative offsets within the group")
        if (graph["node-0003"]["x"], graph["node-0003"]["y"]) != (420, 320):
            return ("fail", "quantized group drag should not move nodes outside the group")
        return ("next", None)

    def step_release_group():
        app = APP_STATE["app"]
        core.handle_button_release_1(make_event(app["canvas"], x=196, y=174))
        return ("next", None)

    def step_assert_quantized_release():
        graph = APP_STATE["app"]["graph_data"]["nodes"]
        if (graph["node-0001"]["x"], graph["node-0001"]["y"]) != (200, 180):
            return ("fail", "quantized group drag should keep the snapped anchor location on release")
        if (graph["node-0002"]["x"], graph["node-0002"]["y"]) != (280, 240):
            return ("fail", "quantized group drag should keep snapped relative positions on release")
        return ("success", None)

    tkintertester.add_test(
        "quantized group drag",
        [
            step_focus_canvas,
            step_enable_quantizing,
            step_seed_group_selection,
            step_press_group_node,
            step_drag_group,
            step_assert_quantized_preview,
            step_release_group,
            step_assert_quantized_release,
        ],
    )
    run_suite()


def test_shift_drag_creates_edge_with_preview_and_judge_holds():
    global TEST_GRAPH

    TEST_GRAPH = {
        "nodes": {
            "node-0001": {"id": "node-0001", "x": 180, "y": 160},
            "node-0002": {"id": "node-0002", "x": 340, "y": 260},
        },
        "edges": [],
    }
    setup_harness()

    def step_focus_canvas():
        force_canvas_focus()
        return ("next", None)

    def step_press_source():
        app = APP_STATE["app"]
        core.handle_button_1(make_event(app["canvas"], x=180, y=160, state=1))
        return ("next", None)

    def step_assert_preview_on_press():
        if core.coordination["pointer-owner"] != "edge-create-organism":
            return ("fail", "judge should grant pointer ownership as soon as edge creation starts")
        if core.coordination["resource-holds"].get("edge-create") != "edge-create-organism":
            return ("fail", "judge should grant edge-create ownership on shift-press")
        if core.canvas_items["preview_edge_item"] is None:
            return ("fail", "edge preview should appear even before the pointer moves")
        if core.interaction["edge_drag_source_id"] != "node-0001":
            return ("fail", "edge creation should remember its source node on press")
        return ("next", None)

    def step_drag_preview():
        app = APP_STATE["app"]
        core.handle_button_motion(make_event(app["canvas"], x=340, y=260, state=1))
        return ("next", None)

    def step_repeat_shift_without_motion():
        app = APP_STATE["app"]
        core.handle_key_press(make_event(app["canvas"], keysym="Shift_L", state=1))
        return ("next", None)

    def step_assert_preview():
        if core.coordination["pointer-owner"] != "edge-create-organism":
            return ("fail", "judge should grant pointer ownership during edge creation")
        if core.coordination["resource-holds"].get("edge-create") != "edge-create-organism":
            return ("fail", "judge should grant edge-create ownership during preview drag")
        if core.canvas_items["preview_edge_item"] is None:
            return ("fail", "edge creation should render a live preview during drag")
        if core.interaction["edge_drag_source_id"] != "node-0001":
            return ("fail", "edge creation should remember its source node")
        preview_color = APP_STATE["app"]["canvas"].itemcget(core.canvas_items["preview_edge_item"], "fill")
        if preview_color != core.render["preview_create_edge_color"]:
            return ("fail", "create-edge preview should render in green")
        return ("next", None)

    def step_release_on_target():
        app = APP_STATE["app"]
        core.handle_button_release_1(make_event(app["canvas"], x=340, y=260, state=1))
        return ("next", None)

    def step_assert_edge_created():
        edges = APP_STATE["app"]["graph_data"]["edges"]
        if edges != [{"from": "node-0001", "to": "node-0002"}]:
            return ("fail", "shift-drag release over a target node should create one edge")
        if core.coordination["pointer-owner"] is not None:
            return ("fail", "judge should release pointer ownership after edge creation")
        if core.coordination["resource-holds"]:
            return ("fail", "judge should clear edge-create holds after release")
        if core.canvas_items["preview_edge_item"] is not None:
            return ("fail", "preview edge should clear after release")
        return ("success", None)

    tkintertester.add_test(
        "edge create",
        [
            step_focus_canvas,
            step_press_source,
            step_assert_preview_on_press,
            step_drag_preview,
            step_repeat_shift_without_motion,
            step_assert_preview,
            step_release_on_target,
            step_assert_edge_created,
        ],
    )
    run_suite()


def test_shift_drag_release_off_target_cancels_edge_creation():
    global TEST_GRAPH

    TEST_GRAPH = {
        "nodes": {
            "node-0001": {"id": "node-0001", "x": 180, "y": 160},
            "node-0002": {"id": "node-0002", "x": 340, "y": 260},
        },
        "edges": [],
    }
    setup_harness()

    def step_focus_canvas():
        force_canvas_focus()
        return ("next", None)

    def step_press_source():
        app = APP_STATE["app"]
        core.handle_button_1(make_event(app["canvas"], x=180, y=160, state=1))
        return ("next", None)

    def step_drag_preview():
        app = APP_STATE["app"]
        core.handle_button_motion(make_event(app["canvas"], x=260, y=210, state=1))
        return ("next", None)

    def step_release_off_target():
        app = APP_STATE["app"]
        core.handle_button_release_1(make_event(app["canvas"], x=260, y=210, state=1))
        return ("next", None)

    def step_assert_cancelled():
        edges = APP_STATE["app"]["graph_data"]["edges"]
        if edges:
            return ("fail", "releasing edge-create off-target should not create an edge")
        if core.canvas_items["preview_edge_item"] is not None:
            return ("fail", "preview edge should clear when edge creation is cancelled")
        return ("success", None)

    tkintertester.add_test(
        "edge create cancel",
        [
            step_focus_canvas,
            step_press_source,
            step_drag_preview,
            step_release_off_target,
            step_assert_cancelled,
        ],
    )
    run_suite()


def test_shift_drag_existing_edge_unlinks_and_preview_turns_red():
    global TEST_GRAPH

    TEST_GRAPH = {
        "nodes": {
            "node-0001": {"id": "node-0001", "x": 180, "y": 160},
            "node-0002": {"id": "node-0002", "x": 340, "y": 260},
        },
        "edges": [
            {"from": "node-0001", "to": "node-0002"},
        ],
    }
    setup_harness()

    def step_focus_canvas():
        force_canvas_focus()
        return ("next", None)

    def step_press_source():
        app = APP_STATE["app"]
        core.handle_button_1(make_event(app["canvas"], x=180, y=160, state=1))
        return ("next", None)

    def step_drag_to_existing_target():
        app = APP_STATE["app"]
        core.handle_button_motion(make_event(app["canvas"], x=340, y=260, state=1))
        return ("next", None)

    def step_assert_red_preview():
        preview_item = core.canvas_items["preview_edge_item"]
        if preview_item is None:
            return ("fail", "existing edge toggle should still show a live preview")
        preview_color = APP_STATE["app"]["canvas"].itemcget(preview_item, "fill")
        if preview_color != core.render["preview_unlink_edge_color"]:
            return ("fail", "unlink preview should render in red")
        return ("next", None)

    def step_release_on_existing_target():
        app = APP_STATE["app"]
        core.handle_button_release_1(make_event(app["canvas"], x=340, y=260, state=1))
        return ("next", None)

    def step_assert_unlinked():
        if APP_STATE["app"]["graph_data"]["edges"]:
            return ("fail", "shift-dragging an existing edge should remove it")
        if core.canvas_items["preview_edge_item"] is not None:
            return ("fail", "unlink preview should clear after release")
        return ("success", None)

    tkintertester.add_test(
        "edge unlink toggle",
        [
            step_focus_canvas,
            step_press_source,
            step_drag_to_existing_target,
            step_assert_red_preview,
            step_release_on_existing_target,
            step_assert_unlinked,
        ],
    )
    run_suite()


def test_h_and_v_align_group_selection_to_single_selection_anchor():
    global TEST_GRAPH

    TEST_GRAPH = {
        "nodes": {
            "node-0001": {"id": "node-0001", "x": 100, "y": 100},
            "node-0002": {"id": "node-0002", "x": 220, "y": 160},
            "node-0003": {"id": "node-0003", "x": 340, "y": 280},
            "node-0004": {"id": "node-0004", "x": 480, "y": 420},
        },
        "edges": [],
    }
    setup_harness()

    def step_focus_canvas():
        force_canvas_focus()
        return ("next", None)

    def step_seed_group_selection():
        core.selection["group_selected_ids"] = ["node-0001", "node-0002", "node-0003"]
        core.g["selected_node_id"] = "node-0002"
        return ("next", None)

    def step_press_h():
        app = APP_STATE["app"]
        core.handle_key_press(make_event(app["canvas"], keysym="h"))
        return ("next", None)

    def step_assert_h():
        graph = APP_STATE["app"]["graph_data"]["nodes"]
        expected_y = 160
        for node_id in ("node-0001", "node-0002", "node-0003"):
            if graph[node_id]["y"] != expected_y:
                return ("fail", "h should align group-selected nodes to the selected node y coordinate")
        if graph["node-0004"]["y"] != 420:
            return ("fail", "h should not move unselected nodes")
        return ("next", None)

    def step_press_v():
        app = APP_STATE["app"]
        core.handle_key_press(make_event(app["canvas"], keysym="v"))
        return ("next", None)

    def step_assert_v():
        graph = APP_STATE["app"]["graph_data"]["nodes"]
        expected_x = 220
        for node_id in ("node-0001", "node-0002", "node-0003"):
            if graph[node_id]["x"] != expected_x:
                return ("fail", "v should align group-selected nodes to the selected node x coordinate")
        if graph["node-0004"]["x"] != 480:
            return ("fail", "v should not move unselected nodes")
        return ("success", None)

    tkintertester.add_test(
        "align nodes with h and v around single selection",
        [
            step_focus_canvas,
            step_seed_group_selection,
            step_press_h,
            step_assert_h,
            step_press_v,
            step_assert_v,
        ],
    )
    run_suite()


def test_H_and_V_distribute_nodes_evenly_between_extremes():
    global TEST_GRAPH

    TEST_GRAPH = {
        "nodes": {
            "node-0001": {"id": "node-0001", "x": 100, "y": 300},
            "node-0002": {"id": "node-0002", "x": 170, "y": 220},
            "node-0003": {"id": "node-0003", "x": 260, "y": 180},
            "node-0004": {"id": "node-0004", "x": 400, "y": 100},
            "node-0005": {"id": "node-0005", "x": 520, "y": 360},
        },
        "edges": [],
    }
    setup_harness()

    def step_focus_canvas():
        force_canvas_focus()
        return ("next", None)

    def step_seed_group_selection():
        core.selection["group_selected_ids"] = ["node-0001", "node-0002", "node-0003", "node-0004"]
        return ("next", None)

    def step_press_shift_h():
        app = APP_STATE["app"]
        core.handle_key_press(make_event(app["canvas"], keysym="H"))
        return ("next", None)

    def step_assert_shift_h():
        graph = APP_STATE["app"]["graph_data"]["nodes"]
        if graph["node-0001"]["x"] != 100:
            return ("fail", "H should keep the leftmost node at its original x")
        if graph["node-0004"]["x"] != 400:
            return ("fail", "H should keep the rightmost node at its original x")
        if graph["node-0002"]["x"] != 200:
            return ("fail", "H should place the second node one equal step from the left edge")
        if graph["node-0003"]["x"] != 300:
            return ("fail", "H should place the third node two equal steps from the left edge")
        if graph["node-0005"]["x"] != 520:
            return ("fail", "H should not move unselected nodes")
        return ("next", None)

    def step_press_shift_v():
        app = APP_STATE["app"]
        core.handle_key_press(make_event(app["canvas"], keysym="V"))
        return ("next", None)

    def step_assert_shift_v():
        graph = APP_STATE["app"]["graph_data"]["nodes"]
        if graph["node-0004"]["y"] != 100:
            return ("fail", "V should keep the topmost node at its original y")
        if graph["node-0001"]["y"] != 300:
            return ("fail", "V should keep the bottommost node at its original y")
        if graph["node-0003"]["y"] != (100 + (200 / 3)):
            return ("fail", "V should place upper-middle nodes at equal vertical spacing")
        if graph["node-0002"]["y"] != (100 + (400 / 3)):
            return ("fail", "V should place lower-middle nodes at equal vertical spacing")
        if graph["node-0005"]["y"] != 360:
            return ("fail", "V should not move unselected nodes")
        return ("success", None)

    tkintertester.add_test(
        "distribute nodes with H and V",
        [
            step_focus_canvas,
            step_seed_group_selection,
            step_press_shift_h,
            step_assert_shift_h,
            step_press_shift_v,
            step_assert_shift_v,
        ],
    )
    run_suite()
