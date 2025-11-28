from ortools.sat.python import cp_model
from config import DAYS, TIME_MAP, SLOTS_MWF, SLOTS_TTH, BLOCKED_SLOTS, get_slot_from_time

def solve_timetable(courses, rooms, faculty, groups, overrides=None):
    if overrides is None: overrides = []
    
    model = cp_model.CpModel()
    
    # --- 1. SETUP VARIABLES ---
    # X[(course_idx, day, slot, room_idx)] = boolean
    X = {}
    
    for c_idx, c in enumerate(courses):
        for r in rooms:
            # Check Room Type Compatibility (Hard Constraint)
            if c.component == "P" and r.type.lower() != "lab": continue
            if c.component == "L" and r.type.lower() == "lab": continue
            
            for d in DAYS:
                day_slots = SLOTS_TTH if d in ["Tue", "Thu"] else SLOTS_MWF
                for s in range(day_slots):
                    # Skip blocked slots
                    if (d, s) in BLOCKED_SLOTS: continue
                    
                    X[(c_idx, d, s, r.id)] = model.NewBoolVar(f"X_{c.id}_{d}_{s}_{r.id}")

    # --- 2. APPLY USER OVERRIDES ---
    # format: {"course_id": "CS102", "component": "L", "day": "Mon", "time": "08:00-09:00"}
    for ov in overrides:
        target_slot = get_slot_from_time(ov['day'], ov['time'])
        if target_slot is None: continue

        # Find specific course index
        target_c_idx = next((i for i, c in enumerate(courses) 
                             if c.id == ov['course_id'] and c.component == ov['component']), None)
        
        if target_c_idx is not None:
            relevant_vars = [X[k] for k in X 
                             if k[0] == target_c_idx 
                             and k[1] == ov['day'] 
                             and k[2] == target_slot]
            if relevant_vars:
                model.Add(sum(relevant_vars) == 1)

    # --- 3. HARD CONSTRAINTS ---

    # A. Single Assignment & Overlaps
    for d in DAYS:
        day_slots = SLOTS_TTH if d in ["Tue", "Thu"] else SLOTS_MWF
        for s in range(day_slots):
            # No room overlap
            for r in rooms:
                model.Add(sum(X[k] for k in X if k[1]==d and k[2]==s and k[3]==r.id) <= 1)
            # No faculty overlap
            for f in faculty:
                model.Add(sum(X[k] for k in X if k[1]==d and k[2]==s and courses[k[0]].faculty == f.id) <= 1)
            # No student group overlap
            for g in groups:
                model.Add(sum(X[k] for k in X if k[1]==d and k[2]==s and courses[k[0]].group == g) <= 1)

    # B. Pattern Enforcement
    for c_idx, c in enumerate(courses):
        
        # Pattern 1: Lecture (3 hours) -> MWF alignment
        if c.component == "L" and c.hours == 3.0:
            # Must be scheduled exactly once on Monday
            model.Add(sum(X[k] for k in X if k[0]==c_idx and k[1]=="Mon") == 1)
            # Force Symmetry: Mon[Slot S] == Wed[Slot S] == Fri[Slot S]
            for s in range(SLOTS_MWF):
                if ("Mon", s) in BLOCKED_SLOTS: continue
                mon_var = sum(X[k] for k in X if k[0]==c_idx and k[1]=="Mon" and k[2]==s)
                wed_var = sum(X[k] for k in X if k[0]==c_idx and k[1]=="Wed" and k[2]==s)
                fri_var = sum(X[k] for k in X if k[0]==c_idx and k[1]=="Fri" and k[2]==s)
                model.Add(mon_var == wed_var)
                model.Add(mon_var == fri_var)
            # Not on Tue/Thu
            model.Add(sum(X[k] for k in X if k[0]==c_idx and k[1] in ["Tue", "Thu"]) == 0)

        # Pattern 2: Lecture (1.5 hours) -> T/Th alignment
        elif c.component == "L" and c.hours == 1.5:
            model.Add(sum(X[k] for k in X if k[0]==c_idx and k[1]=="Tue") == 1)
            for s in range(SLOTS_TTH):
                tue_var = sum(X[k] for k in X if k[0]==c_idx and k[1]=="Tue" and k[2]==s)
                thu_var = sum(X[k] for k in X if k[0]==c_idx and k[1]=="Thu" and k[2]==s)
                model.Add(tue_var == thu_var)
            model.Add(sum(X[k] for k in X if k[0]==c_idx and k[1] in ["Mon", "Wed", "Fri"]) == 0)

        # Pattern 3: Practical (1 block)
        elif c.component == "P":
            model.Add(sum(X[k] for k in X if k[0]==c_idx) == 1)

    # C. Faculty Constraints
    for f in faculty:
        days_worked = []
        for d in DAYS:
            is_working = model.NewBoolVar(f"work_{f.id}_{d}")
            assignments = sum(X[k] for k in X if courses[k[0]].faculty == f.id and k[1] == d)
            model.Add(assignments > 0).OnlyEnforceIf(is_working)
            model.Add(assignments == 0).OnlyEnforceIf(is_working.Not())
            days_worked.append(is_working)
        model.Add(sum(days_worked) <= f.max_days)

        if not f.allow_back_to_back:
            for d in DAYS:
                day_slots = SLOTS_TTH if d in ["Tue", "Thu"] else SLOTS_MWF
                for s in range(day_slots - 1):
                    current_slot = sum(X[k] for k in X if k[1]==d and k[2]==s and courses[k[0]].faculty == f.id)
                    next_slot = sum(X[k] for k in X if k[1]==d and k[2]==s+1 and courses[k[0]].faculty == f.id)
                    model.Add(current_slot + next_slot <= 1)

    # --- 4. SOFT CONSTRAINTS ---
    objectives = []
    # Avoid 8 AM for Electives
    for k, var in X.items():
        c = courses[k[0]]
        if not c.is_core and k[2] == 0:
            objectives.append(-10 * var)
    # Penalize late Friday
    for k, var in X.items():
        if k[1] == "Fri" and k[2] >= 5:
            objectives.append(-5 * var)

    model.Maximize(sum(objectives))

    # --- 5. SOLVE ---
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10
    status = solver.Solve(model)

    if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        return None

    # --- 6. FORMAT OUTPUT ---
    result = []
    for k, var in X.items():
        if solver.Value(var) == 1:
            c_idx, day, slot, r_id = k
            time_str = TIME_MAP[day][slot] if slot < len(TIME_MAP[day]) else "Unknown"
            result.append({
                "course": courses[c_idx].id,
                "component": courses[c_idx].component,
                "day": day,
                "time": time_str,
                "slot_index": slot,
                "room": r_id,
                "faculty": courses[c_idx].faculty,
                "group": courses[c_idx].group
            })
    
    day_order = {"Mon":1, "Tue":2, "Wed":3, "Thu":4, "Fri":5}
    result.sort(key=lambda x: (day_order[x['day']], x['slot_index']))
    return result