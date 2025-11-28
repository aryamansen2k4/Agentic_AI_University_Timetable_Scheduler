from datetime import datetime

# --- TIME SLOT DEFINITIONS ---

# Pattern A: 1-Hour Slots (Indices 0-7)
TIMES_1H = [
    "08:00-09:00", "09:00-10:00", "10:00-11:00", "11:00-12:00", 
    "12:00-13:00", "14:00-15:00", "15:00-16:00", "16:00-17:00"
]

# Pattern B: 1.5-Hour Slots (Indices 8-13)
TIMES_1_5H = [
    "08:30-10:00", "10:00-11:30", "11:30-13:00", 
    "14:00-15:30", "15:30-17:00", "17:00-18:30"
]

# Combined Master List
ALL_TIMES = TIMES_1H + TIMES_1_5H

# Counts/Indices for Solver logic
COUNT_1H = len(TIMES_1H)       # 8
COUNT_1_5H = len(TIMES_1_5H)   # 6
TOTAL_SLOTS = len(ALL_TIMES)   # 14

# Ranges for iteration
RANGE_1H = range(0, COUNT_1H)                 # 0 to 7
RANGE_1_5H = range(COUNT_1H, TOTAL_SLOTS)     # 8 to 13

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]

# Apply full list to every day
TIME_MAP = {d: ALL_TIMES for d in DAYS}

# Compatibility constants for solver imports (Legacy support)
SLOTS_MWF = TOTAL_SLOTS
SLOTS_TTH = TOTAL_SLOTS

# --- OVERLAP CALCULATION ---
# This ensures the solver knows that Slot 0 (08:00-09:00) overlaps with Slot 8 (08:30-10:00)

def parse_time(t_str): # type: ignore
    """Converts '08:30' to minutes from midnight."""
    t = datetime.strptime(t_str, "%H:%M")
    return t.hour * 60 + t.minute

def check_overlap(t1_str, t2_str): # type: ignore
    """Returns True if two time strings overlap."""
    s1, e1 = map(parse_time, t1_str.split('-'))
    s2, e2 = map(parse_time, t2_str.split('-'))
    # Overlap if Start1 < End2 and Start2 < End1
    return s1 < e2 and s2 < e1

# Pre-calculate conflicting index pairs
# Returns list of tuples: [(0, 8), (1, 8), ...]
SLOT_CONFLICTS = []
for i in range(TOTAL_SLOTS):
    for j in range(i + 1, TOTAL_SLOTS):
        if check_overlap(ALL_TIMES[i], ALL_TIMES[j]):
            SLOT_CONFLICTS.append((i, j))

# Blocked slots (Lunch 12-1)
# 12:00-13:00 is Index 4 in 1H list. 
# 11:30-13:00 is Index 10 (2nd in 1.5H list) which covers lunch too.
BLOCKED_SLOTS = []
for d in ["Mon", "Wed", "Fri"]:
    BLOCKED_SLOTS.append((d, 4))  # 12:00-13:00
    BLOCKED_SLOTS.append((d, 10)) # 11:30-13:00

# Helper
REVERSE_TIME_MAP = {}
for day, times in TIME_MAP.items():
    REVERSE_TIME_MAP[day] = {t: i for i, t in enumerate(times)}

def get_slot_from_time(day, time_str): # type: ignore
    return REVERSE_TIME_MAP.get(day, {}).get(time_str)