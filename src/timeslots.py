# timeslots.py
#
# Authoritative list of time slots as defined in the official University timetable
# (Spring 2026 onwards). Extracted from Timeslots_From_Spring'26_Onwards.pdf.
#
# Each slot object:
# {
#    "slot_id": "MWF_2_L",
#    "days": ["Mon", "Wed", "Fri"],
#    "start": "09:05",
#    "end": "10:00",
#    "allowed_components": ["L"]   # L = Lecture, T = Tutorial, P = Practical
# }

TIME_SLOTS = [

    # ============================================================
    #  MON / WED / FRI  —  LECTURE / LAB / TUTORIAL
    # ============================================================

    # ---- Morning Lectures ----
    {
        "slot_id": "MWF_1_L",
        "days": ["Mon", "Wed", "Fri"],
        "start": "08:00",
        "end": "08:55",
        "allowed_components": ["L"],
    },
    {
        "slot_id": "MWF_2_L",
        "days": ["Mon", "Wed", "Fri"],
        "start": "09:05",
        "end": "10:00",
        "allowed_components": ["L"],
    },
    {
        "slot_id": "MWF_3_L",
        "days": ["Mon", "Wed", "Fri"],
        "start": "10:10",
        "end": "11:05",
        "allowed_components": ["L"],
    },

    # ---- Slot 3 — 1.5 hr Lecture Option ----
    {
        "slot_id": "MWF_1_LONG_L",
        "days": ["Mon", "Wed", "Fri"],
        "start": "08:00",
        "end": "09:25",
        "allowed_components": ["L"],
    },
    {
        "slot_id": "MWF_3_LONG_L",
        "days": ["Mon", "Wed", "Fri"],
        "start": "10:10",
        "end": "11:35",
        "allowed_components": ["L"],
    },

    # ---- CCC (NO TEACHING ALLOWED) ----
    {
        "slot_id": "MWF_CCC",
        "days": ["Mon", "Wed", "Fri"],
        "start": "11:45",
        "end": "12:40",
        "allowed_components": [],    # BLOCKED
    },

    # ---- Afternoon Lectures / Labs ----
    {
        "slot_id": "MWF_4_L",
        "days": ["Mon", "Wed", "Fri"],
        "start": "13:00",
        "end": "13:55",
        "allowed_components": ["L"],
    },
    {
        "slot_id": "MWF_4_LONG_L",
        "days": ["Mon", "Wed", "Fri"],
        "start": "13:00",
        "end": "14:25",
        "allowed_components": ["L"],
    },
    {
        "slot_id": "MWF_4_LAB",
        "days": ["Mon", "Wed", "Fri"],
        "start": "13:00",
        "end": "14:55",
        "allowed_components": ["P"],
    },

    {
        "slot_id": "MWF_5_L",
        "days": ["Mon", "Wed", "Fri"],
        "start": "14:05",
        "end": "15:00",
        "allowed_components": ["L"],
    },

    # ---- Slot 6: LAB or LEC ----
    {
        "slot_id": "MWF_6_LAB",
        "days": ["Mon", "Wed", "Fri"],
        "start": "15:05",
        "end": "17:00",
        "allowed_components": ["P"],
    },
    {
        "slot_id": "MWF_6_L",
        "days": ["Mon", "Wed", "Fri"],
        "start": "15:10",
        "end": "16:05",
        "allowed_components": ["L"],
    },
    {
        "slot_id": "MWF_6_LONG_L",
        "days": ["Mon", "Wed", "Fri"],
        "start": "15:10",
        "end": "16:35",
        "allowed_components": ["L"],
    },

    {
        "slot_id": "MWF_7_L",
        "days": ["Mon", "Wed", "Fri"],
        "start": "16:15",
        "end": "17:10",
        "allowed_components": ["L"],
    },

    # ---- Evening Tutorials ----
    {
        "slot_id": "MWF_8_T",
        "days": ["Mon", "Wed", "Fri"],
        "start": "17:10",
        "end": "18:05",
        "allowed_components": ["T"],
    },
    {
        "slot_id": "MWF_9_T",
        "days": ["Mon", "Wed", "Fri"],
        "start": "18:15",
        "end": "19:10",
        "allowed_components": ["T"],
    },


    # ============================================================
    #  TUE / THU  —  LECTURE / TUTORIAL
    # ============================================================

    # ---- Slot 1 ----
    {
        "slot_id": "TTH_1_LONG_L",
        "days": ["Tue", "Thu"],
        "start": "08:00",
        "end": "09:25",
        "allowed_components": ["L"],
    },
    {
        "slot_id": "TTH_1_L",
        "days": ["Tue", "Thu"],
        "start": "08:00",
        "end": "08:55",
        "allowed_components": ["L"],
    },

    # ---- Slot 2 ----
    {
        "slot_id": "TTH_2_LONG_L",
        "days": ["Tue", "Thu"],
        "start": "09:35",
        "end": "11:00",
        "allowed_components": ["L"],
    },
    {
        "slot_id": "TTH_2_L",
        "days": ["Tue", "Thu"],
        "start": "09:35",
        "end": "10:30",
        "allowed_components": ["L"],
    },

    # ---- Slot 3 ----
    {
        "slot_id": "TTH_3_LONG_L",
        "days": ["Tue", "Thu"],
        "start": "11:10",
        "end": "12:35",
        "allowed_components": ["L"],
    },
    {
        "slot_id": "TTH_3_L",
        "days": ["Tue", "Thu"],
        "start": "11:10",
        "end": "12:05",
        "allowed_components": ["L"],
    },

    # ---- Slot 4 (Thu: University Slot) ----
    {
        "slot_id": "TTH_4_LONG_L",
        "days": ["Tue", "Thu"],
        "start": "12:45",
        "end": "14:10",
        "allowed_components": ["L", "P"],
    },
    {
        "slot_id": "TTH_4_L",
        "days": ["Tue", "Thu"],
        "start": "12:45",
        "end": "13:40",
        "allowed_components": ["L"],
    },

    # ---- Slot 5 ----
    {
        "slot_id": "TTH_5_LONG_L",
        "days": ["Tue", "Thu"],
        "start": "14:10",
        "end": "15:35",
        "allowed_components": ["L"],
    },
    {
        "slot_id": "TTH_5_L",
        "days": ["Tue", "Thu"],
        "start": "14:10",
        "end": "15:05",
        "allowed_components": ["L"],
    },

    # ---- Slot 6 ----
    {
        "slot_id": "TTH_6_LONG_L",
        "days": ["Tue", "Thu"],
        "start": "15:45",
        "end": "17:10",
        "allowed_components": ["L"],
    },
    {
        "slot_id": "TTH_6_L",
        "days": ["Tue", "Thu"],
        "start": "15:45",
        "end": "16:40",
        "allowed_components": ["L"],
    },

    # ---- Tutorials ----
    {
        "slot_id": "TTH_7_T",
        "days": ["Tue", "Thu"],
        "start": "17:20",
        "end": "18:15",
        "allowed_components": ["T"],
    },
    {
        "slot_id": "TTH_8_T",
        "days": ["Tue", "Thu"],
        "start": "18:25",
        "end": "19:20",
        "allowed_components": ["T"],
    },

]
