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


def test_focus_click_is_consumed_before_create_mode_click():
    global TEST_GRAPH

    TEST_GRAPH = {"nodes": {}, "edges": []}
    setup_harness()

    def step_arm_create_mode():
        core.g["mode"] = "CREATE_NODE"
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
        [step_arm_create_mode, step_click_without_focus, step_assert_consumed],
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
        if core.interaction["marquee_start"] != (120, 120):
            return ("fail", "marquee should remember its starting corner")
        if core.interaction["marquee_end"] != (240, 220):
            return ("fail", "marquee should track the current pointer corner")
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

    def step_drag_preview():
        app = APP_STATE["app"]
        core.handle_button_motion(make_event(app["canvas"], x=340, y=260, state=1))
        return ("next", None)

    def step_assert_preview():
        if core.coordination["pointer-owner"] != "edge-create-organism":
            return ("fail", "judge should grant pointer ownership during edge creation")
        if core.coordination["resource-holds"].get("edge-create") != "edge-create-organism":
            return ("fail", "judge should grant edge-create ownership during preview drag")
        if core.transient_effects.get("preview-edge") is None:
            return ("fail", "edge creation should render a live preview during drag")
        if core.interaction["edge_drag_source_id"] != "node-0001":
            return ("fail", "edge creation should remember its source node")
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
        if core.transient_effects.get("preview-edge") is not None:
            return ("fail", "preview edge should clear after release")
        return ("success", None)

    tkintertester.add_test(
        "edge create",
        [
            step_focus_canvas,
            step_press_source,
            step_drag_preview,
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
        if core.transient_effects.get("preview-edge") is not None:
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
