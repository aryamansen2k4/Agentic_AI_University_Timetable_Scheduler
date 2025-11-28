from typing import TypedDict, List, Any, Dict, Literal
from langgraph.graph import StateGraph, END
import pandas as pd

# Import logic
from solver import solve_timetable
from inspector import inspect_schedule

# --- 1. STATE DEFINITION ---
class ScheduleState(TypedDict):
    # Inputs
    courses: List[Any]
    rooms: List[Any]
    faculty: List[Any]
    groups: List[Any]
    overrides: List[Dict]
    
    # Outputs
    schedule: List[Dict]
    analysis: str          # Output from Inspector Node
    statistics: str        # Output from Statistics Node (NEW)
    status: str

# --- 2. NODES ---

def node_solver(state: ScheduleState):
    """NODE 1: Solver (Sequential)"""
    print("--- NODE: Solver ---")
    schedule_result = solve_timetable(
        state["courses"], state["rooms"], state["faculty"], 
        state["groups"], state["overrides"]
    )
    if schedule_result:
        return {"schedule": schedule_result, "status": "success", "analysis": "", "statistics": ""}
    else:
        return {
            "schedule": [], "status": "error", 
            "analysis": "❌ **Solver Failed.** Check constraints.",
            "statistics": ""
        }

def node_inspector(state: ScheduleState):
    """NODE 2A: Inspector (Parallel)"""
    print("--- NODE: Inspector ---")
    report = inspect_schedule(state["schedule"])
    return {"analysis": report}

def node_statistics(state: ScheduleState):
    """NODE 2B: Statistics (Parallel)"""
    print("--- NODE: Statistics ---")
    schedule = state["schedule"]
    if not schedule: return {"statistics": ""}
    
    # Calculate simple stats using Pandas
    df = pd.DataFrame(schedule)
    total_classes = len(df)
    busy_rooms = df['room'].nunique()
    day_counts = df['day'].value_counts().to_dict()
    
    stats_msg = f"""
    **📊 Quick Stats**
    - **Total Classes:** {total_classes}
    - **Rooms Used:** {busy_rooms}
    - **Distribution:** {day_counts}
    """
    return {"statistics": stats_msg}

# --- 3. ROUTER (The Parallelizer) ---

def router(state: ScheduleState) -> List[str]:
    """
    Returns a LIST of nodes to run in parallel.
    """
    if state["status"] == "success":
        # Run BOTH Inspector and Statistics at the same time
        return ["inspector", "statistics"]
    else:
        return [END]

# --- 4. BUILD ---

def build_timetable_graph():
    workflow = StateGraph(ScheduleState)

    # Add Nodes
    workflow.add_node("solver", node_solver)
    workflow.add_node("inspector", node_inspector)
    workflow.add_node("statistics", node_statistics)

    # Edges
    workflow.set_entry_point("solver")
    
    # Conditional Fan-Out
    workflow.add_conditional_edges(
        "solver",
        router,
        {
            "inspector": "inspector",
            "statistics": "statistics",
            END: END
        }
    )
    
    # Fan-In (Both parallel nodes go to End)
    workflow.add_edge("inspector", END)
    workflow.add_edge("statistics", END)

    return workflow.compile()