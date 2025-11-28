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
            # Room Type Hard Constraint
            if c.component == "P" and r.type.lower() != "lab": continue
            if c.component == "L" and r.type.lower() == "lab": continue
            
            for d in DAYS:
                # Decide valid slots based on course duration
                # 1.5 hour courses -> Use slots 8-13
                # 1.0 hour courses -> Use slots 0-7
                # Practicals -> Can typically use any, but let's default to 1H slots for modularity
                if c.hours == 1.5:
                    valid_slots = RANGE_1_5H
                else:
                    valid_slots = RANGE_1H

                for s in valid_slots:
                    if (d, s) in BLOCKED_SLOTS: continue
                    X[(c_idx, d, s, r.id)] = model.NewBoolVar(f"X_{c.id}_{d}_{s}_{r.id}")

    # --- 2. APPLY USER OVERRIDES ---
    for ov in overrides:
        target_slot = get_slot_from_time(ov['day'], ov['time'])
        if target_slot is None: continue

        # Find specific course index
        target_c_idx = next((i for i, c in enumerate(courses) 
                             if c.id == ov['course_id'] and c.component == ov['component']), None)
        
        if target_c_idx is not None:
            # Gather all variables for this course/day/slot (across all rooms)
            relevant_vars = [X[k] for k in X 
                             if k[0] == target_c_idx 
                             and k[1] == ov['day'] 
                             and k[2] == target_slot]
            
            if relevant_vars:
                # Force at least one room to be true
                model.Add(sum(relevant_vars) == 1)

    # --- 3. HARD CONSTRAINTS ---

    # A. Resource Usage (Room, Faculty, Group)
    # We must check for direct collisions (same slot) AND overlapping collisions (conflicting slots)
    
    for d in DAYS:
        # 1. Direct Slot Collisions (Standard)
        for s in range(TOTAL_SLOTS):
            # Room
            for r in rooms:
                model.Add(sum(X[k] for k in X if k[1]==d and k[2]==s and k[3]==r.id) <= 1)
            # Faculty
            for f in faculty:
                model.Add(sum(X[k] for k in X if k[1]==d and k[2]==s and courses[k[0]].faculty == f.id) <= 1)
            # Group
            for g in groups:
                model.Add(sum(X[k] for k in X if k[1]==d and k[2]==s and courses[k[0]].group == g) <= 1)

        # 2. Cross-Slot Time Overlaps (New)
        # Check pairs like (Slot 0, Slot 8) which overlap in time
        for (s1, s2) in SLOT_CONFLICTS:
            # Room Overlap
            for r in rooms:
                usage_s1 = sum(X[k] for k in X if k[1]==d and k[2]==s1 and k[3]==r.id)
                usage_s2 = sum(X[k] for k in X if k[1]==d and k[2]==s2 and k[3]==r.id)
                # Cannot use both slots at once
                model.Add(usage_s1 + usage_s2 <= 1)
            
            # Faculty Overlap
            for f in faculty:
                usage_s1 = sum(X[k] for k in X if k[1]==d and k[2]==s1 and courses[k[0]].faculty == f.id)
                usage_s2 = sum(X[k] for k in X if k[1]==d and k[2]==s2 and courses[k[0]].faculty == f.id)
                model.Add(usage_s1 + usage_s2 <= 1)

            # Group Overlap
            for g in groups:
                usage_s1 = sum(X[k] for k in X if k[1]==d and k[2]==s1 and courses[k[0]].group == g)
                usage_s2 = sum(X[k] for k in X if k[1]==d and k[2]==s2 and courses[k[0]].group == g)
                model.Add(usage_s1 + usage_s2 <= 1)

    # B. Pattern Enforcement
    for c_idx, c in enumerate(courses):
        
        # Pattern 1: Lecture 3.0h -> MWF (Using 1H Slots)
        if c.component == "L" and c.hours == 3.0:
            # Must appear exactly once on Mon, Wed, Fri (in 1H range)
            for day in ["Mon", "Wed", "Fri"]:
                 model.Add(sum(X[k] for k in X if k[0]==c_idx and k[1]==day and k[2] in RANGE_1H) == 1)
            
            # Not on Tue, Thu
            model.Add(sum(X[k] for k in X if k[0]==c_idx and k[1] in ["Tue", "Thu"]) == 0)

            # Symmetry: Slot on Mon == Slot on Wed == Slot on Fri
            for s in RANGE_1H:
                if ("Mon", s) in BLOCKED_SLOTS: continue
                mon = sum(X[k] for k in X if k[0]==c_idx and k[1]=="Mon" and k[2]==s)
                wed = sum(X[k] for k in X if k[0]==c_idx and k[1]=="Wed" and k[2]==s)
                fri = sum(X[k] for k in X if k[0]==c_idx and k[1]=="Fri" and k[2]==s)
                model.Add(mon == wed)
                model.Add(mon == fri)

        # Pattern 2: Lecture 1.5h -> T/Th (Using 1.5H Slots)
        elif c.component == "L" and c.hours == 1.5:
            # Must appear exactly once on Tue, Thu (in 1.5H range)
            for day in ["Tue", "Thu"]:
                 model.Add(sum(X[k] for k in X if k[0]==c_idx and k[1]==day and k[2] in RANGE_1_5H) == 1)
            
            # Not on MWF
            model.Add(sum(X[k] for k in X if k[0]==c_idx and k[1] in ["Mon", "Wed", "Fri"]) == 0)

            # Symmetry
            for s in RANGE_1_5H:
                tue = sum(X[k] for k in X if k[0]==c_idx and k[1]=="Tue" and k[2]==s)
                thu = sum(X[k] for k in X if k[0]==c_idx and k[1]=="Thu" and k[2]==s)
                model.Add(tue == thu)

        # Pattern 3: Practical (One block, any day)
        elif c.component == "P":
            model.Add(sum(X[k] for k in X if k[0]==c_idx) == 1)

    # C. Faculty Constraints (Max Days)
    for f in faculty:
        days_worked = []
        for d in DAYS:
            is_working = model.NewBoolVar(f"work_{f.id}_{d}")
            assignments = sum(X[k] for k in X if courses[k[0]].faculty == f.id and k[1] == d)
            model.Add(assignments > 0).OnlyEnforceIf(is_working)
            model.Add(assignments == 0).OnlyEnforceIf(is_working.Not())
            days_worked.append(is_working)
        model.Add(sum(days_worked) <= f.max_days)

        # No Back-to-Back (simplified for mixed slots: just ensure sum of adjacent indices is safe)
        if not f.allow_back_to_back:
            # Check 1H slots sequence
            for d in DAYS:
                for s in range(len(RANGE_1H) - 1):
                    s1 = sum(X[k] for k in X if k[1]==d and k[2]==s and courses[k[0]].faculty == f.id)
                    s2 = sum(X[k] for k in X if k[1]==d and k[2]==s+1 and courses[k[0]].faculty == f.id)
                    model.Add(s1 + s2 <= 1)

    # --- 4. SOFT CONSTRAINTS ---
    objectives = []
    for k, var in X.items():
        c = courses[k[0]]
        # Avoid 8 AM (Slot 0 or Slot 8) for Electives
        if not c.is_core and (k[2] == 0 or k[2] == 8):
            objectives.append(-10 * var)
        # Avoid Late Fri (Slot 7 or 13)
        if k[1] == "Fri" and (k[2] == 7 or k[2] == 13):
            objectives.append(-5 * var)

    model.Maximize(sum(objectives))

    # --- 5. SOLVE ---
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10
    status = solver.Solve(model)

    if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        return None

    # --- 6. FORMAT ---
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
    result.sort(key=lambda x: (day_order[x['day']], x['time'])) # Sort by time string roughly
    return result