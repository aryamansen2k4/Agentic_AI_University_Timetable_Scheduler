# graph.py

"""

LangGraph pipeline with a conditional override loop,

compatible with older LangGraph versions.



Flow:

    solve → inspect → apply_overrides

         ↘ (if overrides) loop → solve again

"""



from typing import Dict, Any

from langgraph.graph import StateGraph, END



from solver import solve_timetable

from inspector import inspect_schedule





# ---------------------------------------------------------

# NODES

# ---------------------------------------------------------



def solve_node(state: Dict[str, Any]) -> Dict[str, Any]:

    success, schedule, msg = solve_timetable(

        courses=state["courses"],

        rooms=state["rooms"],

        faculty=state["faculty"],

        overrides=state.get("overrides", []),

    )



    state["schedule"] = [s.as_dict() for s in schedule]

    state["analysis"] = msg

    state["status"] = "success" if success else "fail"

    return state





def inspect_node(state: Dict[str, Any]) -> Dict[str, Any]:

    # inspector MUST return overrides too

    analysis, overrides = inspect_schedule(

        state.get("schedule", []), return_overrides=True # type: ignore

    )

    state["analysis"] = analysis

    state["new_overrides"] = overrides

    return state





def apply_overrides_node(state: Dict[str, Any]) -> Dict[str, Any]:

    """Appends new overrides & sets loop flag."""

    new_ov = state.get("new_overrides", [])



    if new_ov:

        state.setdefault("overrides", [])

        state["overrides"].extend(new_ov)

        state["should_loop"] = True

    else:

        state["should_loop"] = False



    return state





# A passthrough for END

def end_node(state: Dict[str, Any]) -> Dict[str, Any]:

    return state


def decide_next_step(state: Dict[str, Any]) -> str:
    """
    Router function: Checks state and returns the NAME of the next node.
    """
    if state.get("should_loop", False):
        return "solve" # Go back to solve
    return "end"       # Go to end


# ---------------------------------------------------------

# GRAPH BUILD (older API)

# ---------------------------------------------------------



def build_timetable_graph():
    graph = StateGraph(dict)  # type: ignore

    graph.add_node("solve", solve_node)  # type: ignore
    graph.add_node("inspect", inspect_node)  # type: ignore
    graph.add_node("apply_overrides", apply_overrides_node)  # type: ignore
    graph.add_node("end", end_node)  # type: ignore

    # fixed sequential edges
    graph.set_entry_point("solve")
    graph.add_edge("solve", "inspect")
    graph.add_edge("inspect", "apply_overrides")

    # CONDITIONAL LOOP
    graph.add_conditional_edges(
        # 1. The node where the decision happens
        "apply_overrides",
        
        # 2. The function that determines the next step
        decide_next_step,
        
        # 3. The mapping: { Output of function : Name of Target Node }
        {
            "solve": "solve",
            "end": "end"
        }
    )

    return graph.compile()