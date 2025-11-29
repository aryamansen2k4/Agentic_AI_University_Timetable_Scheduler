# graph.py
"""
LangGraph pipeline for the AI Timetable Scheduler.

Graph:
    solve_node   →   inspect_node   →   END

State keys:
    "courses", "rooms", "faculty", "groups", "overrides",
    "schedule", "analysis", "statistics", "status"
"""

from typing import Dict, Any
from langgraph.graph import StateGraph, END
from solver import solve_timetable
from inspector import inspect_schedule


def solve_node(state: Dict[str, Any]) -> Dict[str, Any]:
    courses = state["courses"]
    rooms = state["rooms"]
    faculty = state["faculty"]
    overrides = state.get("overrides", [])

    success, schedule, msg = solve_timetable(
        courses=courses,
        rooms=rooms,
        faculty=faculty,
        overrides=overrides,
    )

    state["schedule"] = [s.as_dict() for s in schedule]
    state["analysis"] = msg
    state["statistics"] = f"Total assigned slots: {len(schedule)}"
    state["status"] = "success" if success else "fail"

    return state


def inspect_node(state: Dict[str, Any]) -> Dict[str, Any]:
    schedule = state.get("schedule", [])
    analysis = inspect_schedule(schedule)
    state["analysis"] = analysis
    return state


def build_timetable_graph():
    graph = StateGraph(dict)  # type: ignore # simple dict state

    graph.add_node("solve", solve_node)     # type: ignore
    graph.add_node("inspect", inspect_node) # type: ignore

    graph.set_entry_point("solve")
    graph.add_edge("solve", "inspect")
    graph.add_edge("inspect", END)

    return graph.compile()
