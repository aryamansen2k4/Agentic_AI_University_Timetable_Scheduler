from ortools.sat.python import cp_model
from config import (
    DAYS, TIME_MAP, BLOCKED_SLOTS, get_slot_from_time,
    TOTAL_SLOTS, RANGE_1H, RANGE_1_5H, SLOT_CONFLICTS
)

def solve_timetable(courses, rooms, faculty, groups, overrides=None):
    if overrides is None: overrides = []
    
    model = cp_model.CpModel()
    
    # --- 1. SETUP VARIABLES ---
    # X[(course_idx, day, slot, room_idx)] = boolean
    X = {}
    
    for c_idx, c in enumerate(courses):
        for r in rooms:
            # OPTIMIZATION: PRUNING
            # 1. Capacity Check: Don't schedule big classes in small rooms
            if c.capacity_needed > 0 and r.capacity < c.capacity_needed:
                continue
            
            # 2. Room Type Check
            if c.component == "P" and r.type.lower() != "lab": continue
            if c.component == "L" and r.type.lower() == "lab": continue
            
            for d in DAYS:
                # Valid slots based on hours
                if c.hours == 1.5:
                    valid_slots = RANGE_1_5H
                else:
                    valid_slots = RANGE_1H

                for s in valid_slots:
                    if (d, s) in BLOCKED_SLOTS: continue
                    X[(c_idx, d, s, r.id)] = model.NewBoolVar(f"X_{c.id}_{d}_{s}_{r.id}")

    # --- 2. OVERRIDES ---
    for ov in overrides:
        target_slot = get_slot_from_time(ov['day'], ov['time'])
        if target_slot is None: continue

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

    # A. Resource Usage
    for d in DAYS:
        for s in range(TOTAL_SLOTS):
            # No room overlap
            for r in rooms:
                model.Add(sum(X[k] for k in X if k[1]==d and k[2]==s and k[3]==r.id) <= 1)
            # No faculty overlap
            for f in faculty:
                model.Add(sum(X[k] for k in X if k[1]==d and k[2]==s and courses[k[0]].faculty == f.id) <= 1)
            # No student group overlap
            for g in groups:
                model.Add(sum(X[k] for k in X if k[1]==d and k[2]==s and courses[k[0]].group == g) <= 1)

        # Cross-Slot Overlaps (Mixing 1h and 1.5h)
        for (s1, s2) in SLOT_CONFLICTS:
            for r in rooms:
                u1 = sum(X[k] for k in X if k[1]==d and k[2]==s1 and k[3]==r.id)
                u2 = sum(X[k] for k in X if k[1]==d and k[2]==s2 and k[3]==r.id)
                model.Add(u1 + u2 <= 1)
            
            for f in faculty:
                u1 = sum(X[k] for k in X if k[1]==d and k[2]==s1 and courses[k[0]].faculty == f.id)
                u2 = sum(X[k] for k in X if k[1]==d and k[2]==s2 and courses[k[0]].faculty == f.id)
                model.Add(u1 + u2 <= 1)

            for g in groups:
                u1 = sum(X[k] for k in X if k[1]==d and k[2]==s1 and courses[k[0]].group == g)
                u2 = sum(X[k] for k in X if k[1]==d and k[2]==s2 and courses[k[0]].group == g)
                model.Add(u1 + u2 <= 1)

    # B. Pattern Enforcement
    for c_idx, c in enumerate(courses):
        if c.component == "L" and c.hours == 3.0:
            for day in ["Mon", "Wed", "Fri"]:
                 model.Add(sum(X[k] for k in X if k[0]==c_idx and k[1]==day and k[2] in RANGE_1H) == 1)
            model.Add(sum(X[k] for k in X if k[0]==c_idx and k[1] in ["Tue", "Thu"]) == 0)
            
            # Symmetry
            for s in RANGE_1H:
                mon = sum(X[k] for k in X if k[0]==c_idx and k[1]=="Mon" and k[2]==s)
                wed = sum(X[k] for k in X if k[0]==c_idx and k[1]=="Wed" and k[2]==s)
                fri = sum(X[k] for k in X if k[0]==c_idx and k[1]=="Fri" and k[2]==s)
                model.Add(mon == wed)
                model.Add(mon == fri)

        elif c.component == "L" and c.hours == 1.5:
            for day in ["Tue", "Thu"]:
                 model.Add(sum(X[k] for k in X if k[0]==c_idx and k[1]==day and k[2] in RANGE_1_5H) == 1)
            model.Add(sum(X[k] for k in X if k[0]==c_idx and k[1] in ["Mon", "Wed", "Fri"]) == 0)
            
            # Symmetry
            for s in RANGE_1_5H:
                tue = sum(X[k] for k in X if k[0]==c_idx and k[1]=="Tue" and k[2]==s)
                thu = sum(X[k] for k in X if k[0]==c_idx and k[1]=="Thu" and k[2]==s)
                model.Add(tue == thu)

        elif c.component == "P":
            model.Add(sum(X[k] for k in X if k[0]==c_idx) == 1)

    # C. Faculty (Max Days & Back-to-Back)
    for f in faculty:
        days_worked = []
        for d in DAYS:
            is_working = model.NewBoolVar(f"work_{f.id}_{d}")
            load = sum(X[k] for k in X if courses[k[0]].faculty == f.id and k[1] == d)
            model.Add(load > 0).OnlyEnforceIf(is_working)
            model.Add(load == 0).OnlyEnforceIf(is_working.Not())
            days_worked.append(is_working)
        model.Add(sum(days_worked) <= f.max_days)

        if not f.allow_back_to_back:
            for d in DAYS:
                for s in range(len(RANGE_1H) - 1):
                    s1 = sum(X[k] for k in X if k[1]==d and k[2]==s and courses[k[0]].faculty == f.id)
                    s2 = sum(X[k] for k in X if k[1]==d and k[2]==s+1 and courses[k[0]].faculty == f.id)
                    model.Add(s1 + s2 <= 1)

    # --- 4. SOFT CONSTRAINTS ---
    objectives = []
    for k, var in X.items():
        c = courses[k[0]]
        if not c.is_core and (k[2] == 0 or k[2] == 8):
            objectives.append(-10 * var)
        if k[1] == "Fri" and (k[2] == 7 or k[2] == 13):
            objectives.append(-5 * var)

    model.Maximize(sum(objectives))

    # --- 5. SOLVE ---
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 20 # Increased slightly for bigger datasets
    status = solver.Solve(model)

    if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        return None

    # --- 6. OUTPUT ---
    result = []
    for k, var in X.items():
        if solver.Value(var) == 1:
            c_idx, day, slot, r_id = k
            time_str = TIME_MAP[day][slot]
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
    result.sort(key=lambda x: (day_order[x['day']], x['time']))
    return result