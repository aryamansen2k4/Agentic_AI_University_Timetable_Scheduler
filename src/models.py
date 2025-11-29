# models.py
"""
Core domain models for the AI Timetable Scheduler.
These are used by:
- solver (hard constraints)
- LangGraph pipeline
- inspector agent
- Streamlit UI
"""

from dataclasses import dataclass, field
from typing import Dict


# ======================================================================
# Course
# ======================================================================

@dataclass
class Course:
    """
    Represents a *single component instance* of a course.

    id:        "BIO101/new code"
    component: "L" / "T" / "P"
    hours:     numeric (from L/T/P Hour)
    group:     student group (Major)
    faculty:   faculty ID (string)
    room_id:   optional fixed/preferred room
    """

    id: str
    component: str
    hours: float
    group: str
    faculty_id: str          # change from faculty → faculty_id
    faculty_name: str        # NEW field
    is_core: bool = True
    capacity_needed: int = 0
    room_id: str = ""

    def __post_init__(self):
        self.component = self.component.upper().strip()
        if self.component not in {"L", "T", "P"}:
            raise ValueError(f"Invalid component type for Course: {self.component!r}")


# ======================================================================
# Room
# ======================================================================

@dataclass
class Room:
    """
    Room model.
    type:
        - "Classroom" → can host L & T
        - "Lab"       → can host P only
    """

    id: str
    capacity: int
    type: str = "Classroom"  # or "Lab"

    def __post_init__(self):
        t = self.type.lower()
        if "lab" in self.id.lower() or "lab" in t:
            self.type = "Lab"
        else:
            self.type = "Classroom"


# ======================================================================
# Faculty
# ======================================================================

@dataclass
class Faculty:
    """
    Faculty member.
    max_days: soft constraint only (not used in strict solver yet).
    """

    id: str
    name: str
    max_days: int = 5
    preferences: Dict = field(default_factory=dict)


# ======================================================================
# Student Group
# ======================================================================

@dataclass
class Group:
    """
    Student group (e.g., BIO1YR, CHY1YR).
    Not used heavily by solver except for clash prevention.
    """

    id: str
    size: int = 0
    notes: str = ""


# ======================================================================
# Time Slot Model (optional high-level representation)
# ======================================================================

@dataclass
class TimeSlot:
    day: str       # "Mon" ... "Fri"
    start: str     # "09:00"
    end: str       # "10:00"
    duration: float
    type: str      # "L", "T", "P"

    def label(self) -> str:
        return f"{self.day} {self.start}-{self.end}"


# ======================================================================
# Scheduled Item (for UI / ICS export)
# ======================================================================

@dataclass
class ScheduledItem:
    course: str
    component: str
    faculty: str
    group: str
    room: str
    day: str
    time: str      # "HH:MM-HH:MM"
    duration: float

    def as_dict(self):
        return {
            "course": self.course,
            "component": self.component,
            "faculty": self.faculty,
            "group": self.group,
            "room": self.room,
            "day": self.day,
            "time": self.time,
            "duration": self.duration,
        }
