# solver.py
"""
Greedy timetable solver with support for:
- official strict TIME_SLOTS grid
- multi-section components (LEC1, TUT1, PRAC2 → L/T/P via parser)
- override + force override
- partial success (for large real-world data)
"""

from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Set
from models import Course, Room, Faculty
from timeslots import TIME_SLOTS   # strict grid


# ================================================================
# Scheduled class
# ================================================================

@dataclass
class ScheduledClass:
    day: str
    time: str       # "HH:MM-HH:MM"
    course: str
    component: str  # L/T/P
    room: str
    faculty: str
    group: str

    def as_dict(self):
        return {
            "day": self.day,
            "time": self.time,
            "course": self.course,
            "component": self.component,
            "room": self.room,
            "faculty": self.faculty,
            "group": self.group,
        }


# ================================================================
# Canonical component
# ================================================================

def canon_component(x: str) -> str:
    """
    Dataset patterns:
    LEC1, LEC2   → L
    TUT1, TUT2   → T
    PRAC1, PRAC2 → P
    (but usually we already pass L/T/P from the Excel parser)
    """
    if not x:
        return ""

    s = str(x).strip().lower()

    if s.startswith("lec"):
        return "L"
    if s.startswith("tut"):
        return "T"
    if s.startswith("prac") or s.startswith("lab"):
        return "P"

    if s[0] in ("l", "t", "p"):
        return s[0].upper()

    return "L"


# ================================================================
# Slot utilities
# ================================================================

def time_label(ts: Dict[str, Any]) -> str:
    return f"{ts['start']}-{ts['end']}"


def slot_family(ts: Dict[str, Any]) -> str:
    """MWF_4_L → MWF_4"""
    sid = ts["slot_id"]
    parts = sid.rsplit("_", 1)
    return parts[0] if len(parts) > 1 else sid


def iter_slots_for_component(comp: str):
    for ts in TIME_SLOTS:
        if comp in ts.get("allowed_components", []):
            yield ts


def find_slot_for_override(day: str, time_str: str, comp: str):
    """Find matching slot for forced scheduling."""
    for ts in TIME_SLOTS:
        if comp not in ts.get("allowed_components", []):
            continue
        if day not in ts["days"]:
            continue
        if time_label(ts) == time_str:
            return ts
    return None


def slot_family_for_label(day: str, label: str) -> str:
    """Reverse map (day, 'HH:MM-HH:MM') to slot family."""
    for ts in TIME_SLOTS:
        if day in ts["days"] and time_label(ts) == label:
            return slot_family(ts)
    return label


# ================================================================
# Room selection & clash checking
# ================================================================

def _find_room_for_course(
    course: Course,
    rooms: List[Room],
    day: str,
    family: str,
    room_busy: Set[Tuple[str, str, str]],
) -> str:
    comp = canon_component(course.component)

    def free(r_id: str) -> bool:
        return (day, family, r_id) not in room_busy

    # Preferred room
    if course.room_id:
        for r in rooms:
            if r.id == course.room_id and free(r.id):
                return r.id

    # Practicals → labs
    if comp == "P":
        for r in rooms:
            if r.type.lower() == "lab" and free(r.id):
                return r.id

    # L/T → classrooms
    if comp in ("L", "T"):
        for r in rooms:
            if r.type.lower() != "lab" and free(r.id):
                return r.id

    # Fallback: anything free
    for r in rooms:
        if free(r.id):
            return r.id

    return ""


def _slot_free(
    day: str,
    family: str,
    course: Course,
    room_id: str,
    room_busy: Set[Tuple[str, str, str]],
    faculty_busy: Dict[Tuple[str, str], str],
    group_busy: Dict[Tuple[str, str], str],
) -> bool:
    if (day, family, room_id) in room_busy:
        return False

    key = (day, family)

    if key in faculty_busy and faculty_busy[key] == course.faculty_name:
        return False

    if key in group_busy and group_busy[key] == course.group:
        return False

    return True


# ================================================================
# Main solver
# ================================================================

def solve_timetable(
    courses: List[Course],
    rooms: List[Room],
    faculty: List[Faculty],
    overrides: List[Dict[str, Any]],
):
    schedule: List[ScheduledClass] = []

    room_busy: Set[Tuple[str, str, str]] = set()
    faculty_busy: Dict[Tuple[str, str], str] = {}
    group_busy: Dict[Tuple[str, str], str] = {}

    scheduled_keys = set()  # (course_id, comp)

    # ------------------------------------------------------------
    # 1. Apply overrides
    # ------------------------------------------------------------
    for ov in overrides:
        c_id = ov.get("course_id")
        comp = canon_component(ov.get("component", ""))
        day = ov.get("day")
        time_str = ov.get("time")
        force = bool(ov.get("force", False))

        if not (c_id and comp and day and time_str):
            continue

        ts = find_slot_for_override(day, time_str, comp)
        if ts is None:
            continue

        fam = slot_family(ts)
        slot_key = (day, fam)

        matching = [
            c for c in courses
            if c.id == c_id and canon_component(c.component) == comp
        ]
        if not matching:
            continue

        if force:
            new_schedule: List[ScheduledClass] = []
            for sc in schedule:
                fam2 = slot_family_for_label(sc.day, sc.time)
                if sc.day == day and fam2 == fam:
                    room_busy = {(d, f, r) for (d, f, r) in room_busy if not (d == day and f == fam)}
                    faculty_busy.pop(slot_key, None)
                    group_busy.pop(slot_key, None)
                    scheduled_keys.discard((sc.course, sc.component))
                else:
                    new_schedule.append(sc)
            schedule = new_schedule

        for c in matching:
            key = (c.id, comp)
            if key in scheduled_keys and not force:
                continue

            room_id = _find_room_for_course(c, rooms, day, fam, room_busy)
            if not room_id:
                continue

            if not force and not _slot_free(day, fam, c, room_id, room_busy, faculty_busy, group_busy):
                continue

            sc = ScheduledClass(
                day=day,
                time=time_label(ts),
                course=c.id,
                component=comp,
                room=room_id,
                faculty=c.faculty_name,
                group=c.group,
            )
            schedule.append(sc)
            scheduled_keys.add(key)

            room_busy.add((day, fam, room_id))
            faculty_busy[slot_key] = c.faculty_name
            group_busy[slot_key] = c.group

    # ------------------------------------------------------------
    # 2. Greedy scheduling for remaining courses
    # ------------------------------------------------------------
    for c in courses:
        comp = canon_component(c.component)
        key = (c.id, comp)
        if key in scheduled_keys:
            continue

        placed = False
        for ts in iter_slots_for_component(comp):
            if placed:
                break
            fam = slot_family(ts)
            for day in ts["days"]:
                slot_key = (day, fam)
                room_id = _find_room_for_course(c, rooms, day, fam, room_busy)
                if not room_id:
                    continue

                if not _slot_free(day, fam, c, room_id, room_busy, faculty_busy, group_busy):
                    continue

                sc = ScheduledClass(
                    day=day,
                    time=time_label(ts),
                    course=c.id,
                    component=comp,
                    room=room_id,
                    faculty=c.faculty_name,
                    group=c.group,
                )
                schedule.append(sc)
                scheduled_keys.add(key)

                room_busy.add((day, fam, room_id))
                faculty_busy[slot_key] = c.faculty_name
                group_busy[slot_key] = c.group
                placed = True
                break

    # ------------------------------------------------------------
    # 3. Full vs partial success
    # ------------------------------------------------------------
    missing = []
    for c in courses:
        comp = canon_component(c.component)
        if (c.id, comp) not in scheduled_keys:
            missing.append(f"{c.id} ({comp})")

    placed = len(schedule)
    total = len(courses)

    if placed == 0:
        msg = (
            "Solver could not place ANY course in the strict university timeslots. "
            "Check TIME_SLOTS or relax constraints."
        )
        return False, [], msg

    if missing:
        preview = ", ".join(missing[:25])
        if len(missing) > 25:
            preview += f", ... (+{len(missing)-25} more)"
        msg = f"PARTIAL schedule: placed {placed}/{total}. Missing: {preview}"
        return True, schedule, msg

    return True, schedule, "ALL courses placed successfully in strict slots."
