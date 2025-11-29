"""
Greedy timetable solver with support for:
- official strict TIME_SLOTS grid
- multi-section components (LEC1, TUT1, PRAC2 -> L/T/P via parser)
- override + force override
- partial success (for large real-world data)
"""

from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Set
from models import Course, Room, Faculty
from timeslots import TIME_SLOTS   # strict grid
import streamlit as st


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
    if not x:
        return ""
    s = str(x).strip().lower()
    if s.startswith("lec"): return "L"
    if s.startswith("tut"): return "T"
    if s.startswith("prac") or s.startswith("lab"): return "P"
    if s[0] in ("l", "t", "p"): return s[0].upper()
    return "L"


# ================================================================
# Slot utilities
# ================================================================

def time_label(ts: Dict[str, Any]) -> str:
    return f"{ts['start']}-{ts['end']}"


def slot_family(ts: Dict[str, Any]) -> str:
    """
    Groups slots that share the same physical time block.
    Example: MWF_1_L and MWF_1_LONG_L should clash.
    Logic: Remove '_LONG' and remove suffix component.
    """
    sid = ts["slot_id"]
    # 1. Normalize LONG slots to standard slots for clash detection
    sid = sid.replace("_LONG", "") 
    
    # 2. Remove component suffix (e.g., _L, _T, _LAB)
    parts = sid.rsplit("_", 1)
    base = parts[0] if len(parts) > 1 else sid
    
    return base


def iter_slots_for_component(comp: str):
    for ts in TIME_SLOTS:
        if comp in ts.get("allowed_components", []):
            yield ts

def parse_time_to_minutes(time_str: str) -> int:
    """Converts '14:05' to 845 (minutes from midnight)."""
    try:
        h, m = map(int, time_str.split(":"))
        return h * 60 + m
    except:
        return -1

def find_slot_for_override(day: str, time_str: str, comp: str):
    """
    Finds a slot using Fuzzy Matching (snaps to nearest official slot).
    """
    # 1. STRICT MATCH
    def clean(s): return s.replace(" ", "").replace("0", "").replace(":", "")
    target_clean = clean(time_str)

    for ts in TIME_SLOTS:
        if comp in ts.get("allowed_components", []) and day in ts["days"]:
            if clean(time_label(ts)) == target_clean:
                return ts

    # 2. FUZZY MATCH (Snap to grid)
    # If AI says "09:00" but slot is "09:05", we accept it.
    try:
        target_start_str = time_str.split("-")[0]
        target_start_min = parse_time_to_minutes(target_start_str)
        
        best_slot = None
        min_diff = 45 # Allow snapping if within 45 mins (generous)

        for ts in TIME_SLOTS:
            if comp not in ts.get("allowed_components", []) or day not in ts["days"]:
                continue
            
            slot_start_min = parse_time_to_minutes(ts["start"])
            diff = abs(slot_start_min - target_start_min)
            
            if diff < min_diff:
                min_diff = diff
                best_slot = ts

        if best_slot:
            # Silent auto-correct (or use st.toast if you want to see it)
            return best_slot

    except Exception:
        pass

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

    # 1. Preferred room
    if course.room_id:
        for r in rooms:
            if r.id == course.room_id and free(r.id):
                return r.id

    # 2. Type matching (Labs vs Classrooms)
    if comp == "P":
        for r in rooms:
            if r.type.lower() == "lab" and free(r.id):
                return r.id
    else:
        # Lectures/Tutorials prefer non-labs
        for r in rooms:
            if r.type.lower() != "lab" and free(r.id):
                return r.id

    # 3. Fallback: Any free room (Desperate mode)
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
) -> Tuple[bool, str]:
    """Returns (IsFree, Reason)"""
    
    # Check Room
    if (day, family, room_id) in room_busy:
        return False, f"Room {room_id} busy"

    key = (day, family)

    # Check Faculty
    if key in faculty_busy and faculty_busy[key] == course.faculty_id:
        return False, f"Faculty {course.faculty_name} busy"

    # Check Group
    if key in group_busy and group_busy[key] == course.group:
        return False, f"Group {course.group} busy"

    return True, "OK"


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

    room_busy: Set[Tuple[str, str, str]] = set()     # (day, family, room_id)
    faculty_busy: Dict[Tuple[str, str], str] = {}    # (day, family) -> faculty_id
    group_busy: Dict[Tuple[str, str], str] = {}      # (day, family) -> group_id

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
            st.error(f"❌ Override failed: Time slot {time_str} on {day} not found in official list.")
            continue

        fam = slot_family(ts)
        slot_key = (day, fam)

        # Find the course object
        matching = [
            c for c in courses
            if c.id == c_id and canon_component(c.component) == comp
        ]
        if not matching:
            st.warning(f"⚠️ Override ignored: Course {c_id} ({comp}) not found in data.")
            continue

        # If FORCE: Clear conflicts
        if force:
            new_schedule: List[ScheduledClass] = []
            for sc in schedule:
                fam2 = slot_family_for_label(sc.day, sc.time)
                # If clash in same day & same slot family
                if sc.day == day and fam2 == fam:
                    # Remove from busy sets
                    room_busy = {(d, f, r) for (d, f, r) in room_busy if not (d == day and f == fam)}
                    faculty_busy.pop(slot_key, None)
                    group_busy.pop(slot_key, None)
                    scheduled_keys.discard((sc.course, sc.component))
                else:
                    new_schedule.append(sc)
            schedule = new_schedule

        # Place the overridden course
        for c in matching:
            key = (c.id, comp)
            if key in scheduled_keys and not force:
                continue

            room_id = _find_room_for_course(c, rooms, day, fam, room_busy)
            
            # If no room found normally, and it's an override, TRY HARDER
            if not room_id and rooms:
                # Grab first room that isn't strictly busy for this family
                for r in rooms:
                    if (day, fam, r.id) not in room_busy:
                        room_id = r.id
                        break
            
            if not room_id:
                st.error(f"❌ Override failed for {c.id}: No rooms available at {day} {time_str}.")
                continue

            is_free, reason = _slot_free(day, fam, c, room_id, room_busy, faculty_busy, group_busy)
            if not force and not is_free:
                st.toast(f"⚠️ Override skipped for {c.id}: {reason}. Use 'Force' to overwrite.", icon="🚫")
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
            faculty_busy[slot_key] = c.faculty_id
            group_busy[slot_key] = c.group
            
            st.toast(f"✅ Override applied: {c.id} at {day} {time_str}", icon="🔒")

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

                is_free, _ = _slot_free(day, fam, c, room_id, room_busy, faculty_busy, group_busy)
                if not is_free:
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
                faculty_busy[slot_key] = c.faculty_id
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

    return True, schedule, "ALL courses placed successfully."