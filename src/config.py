# Timetable Configuration

# Define strict slot counts per day type
SLOTS_MWF = 8  # 1-hour slots
SLOTS_TTH = 6  # 1.5-hour slots

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]

# Human Readable Mappings
TIME_MAP = {
    "Mon": ["08:00-09:00", "09:00-10:00", "10:00-11:00", "11:00-12:00", 
            "12:00-13:00", "14:00-15:00", "15:00-16:00", "16:00-17:00"],
    "Tue": ["08:30-10:00", "10:00-11:30", "11:30-13:00", 
            "14:00-15:30", "15:30-17:00", "17:00-18:30"],
    "Wed": ["08:00-09:00", "09:00-10:00", "10:00-11:00", "11:00-12:00", 
            "12:00-13:00", "14:00-15:00", "15:00-16:00", "16:00-17:00"],
    "Thu": ["08:30-10:00", "10:00-11:30", "11:30-13:00", 
            "14:00-15:30", "15:30-17:00", "17:00-18:30"],
    "Fri": ["08:00-09:00", "09:00-10:00", "10:00-11:00", "11:00-12:00", 
            "12:00-13:00", "14:00-15:00", "15:00-16:00", "16:00-17:00"]
}

# Blocked slots (e.g., Lunch or Common Curriculum)
# Format: (Day, Slot_Index)
BLOCKED_SLOTS = [
    ("Mon", 4), # Lunch 12-1
    ("Wed", 4), 
    ("Fri", 4)
]

# Reverse Mapping for lookups
REVERSE_TIME_MAP = {}
for day, times in TIME_MAP.items():
    REVERSE_TIME_MAP[day] = {t: i for i, t in enumerate(times)}

def get_slot_from_time(day, time_str):
    """Returns slot index for a given day and time string."""
    return REVERSE_TIME_MAP.get(day, {}).get(time_str)