# app.py
import os
import re
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List

import streamlit as st
import pandas as pd
from ics import Calendar, Event
from langchain_core.messages import HumanMessage, AIMessage

from models import Course, Room, Faculty
from graph import build_timetable_graph
from inspector import get_chat_response
from timeslots import TIME_SLOTS


# -----------------------------------------------------------
# Streamlit Config
# -----------------------------------------------------------
st.set_page_config(layout="wide", page_title="AI Timetable Agent") # type: ignore

st.markdown("""
<style>
    .stChatMessage { padding: 0.5rem; }
    .metric-card { background-color: #f0f2f6; padding: 10px; border-radius: 5px; text-align: center; }
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------
# Session State
# -----------------------------------------------------------
if "overrides" not in st.session_state:
    st.session_state.overrides = []
if "schedule" not in st.session_state:
    st.session_state.schedule = None
if "messages" not in st.session_state:
    st.session_state.messages: List[Dict[str, str]] = [] # type: ignore
if "history" not in st.session_state:
    st.session_state.history = []
if "domain_objects" not in st.session_state:
    st.session_state.domain_objects = {}
if "data_status" not in st.session_state:
    st.session_state.data_status = {
        "courses": False,
        "rooms": False,
        "faculty": False,
        "groups": False,
    }
if "trigger_solve" not in st.session_state:
    st.session_state.trigger_solve = False


# -----------------------------------------------------------
# Helpers: normalization & extraction
# -----------------------------------------------------------

def clean_header(col_name: str) -> str:
    return str(col_name).strip().lower().replace(" ", "_").replace("/", "_").replace(".", "")


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [clean_header(c) for c in df.columns]
    return df


def extract_entities_from_master_sheet(df: pd.DataFrame):
    """
    SPECIALIZED for your real CSV/Excel with columns like:

    Course Name, Course Code, Component, Major, Rooms, Day,
    Start Time, End Time, Seats, Faculty, L/T/P Hour, ...
    """
    df = normalize_dataframe(df)
    extracted = {"courses": [], "rooms": {}, "faculty": {}, "groups": set()}

    if "course_code" not in df.columns or "component" not in df.columns:
        return None

    for _, row in df.iterrows():
        course_id = str(row.get("course_code", "")).strip()
        if not course_id:
            continue

        # ---------- 1. COMPONENT (L/T/P) ----------
        raw_comp = str(row.get("component", "")).strip().lower()

        if raw_comp.startswith("lec"):
            comp = "L"
        elif raw_comp.startswith("tut"):
            comp = "T"
        elif raw_comp.startswith("prac"):
            comp = "P"
        else:
            # fallback via L/T/P Hour
            try:
                h_val = float(row.get("l_t_p_hour", 0))
            except Exception:
                h_val = 0
            if h_val >= 2:
                comp = "P"
            elif h_val == 1:
                comp = "T"
            else:
                comp = "L"

        # ---------- 2. HOURS ----------
        try:
            hours = float(row.get("l_t_p_hour", 3))
        except Exception:
            hours = 3.0

        # ---------- 3. FACULTY ----------
        raw_fac = str(row.get("faculty", "TBA")).strip()
        if "[" in raw_fac and "]" in raw_fac:
            fac_name = raw_fac.split("[")[0].strip()
            fac_id = raw_fac.split("[",1)[1].split("]")[0].strip()
        else:
            fac_name = raw_fac
            fac_id = raw_fac

        if fac_id not in extracted["faculty"]:
            extracted["faculty"][fac_id] = Faculty(id=fac_id, name=fac_name, max_days=5)

        # ---------- 4. ROOM ----------
        r_id = str(row.get("rooms", "")).strip()
        if r_id and r_id.lower() != "nan":
            # crude room type detection
            if "lab" in r_id.lower():
                r_type = "Lab"
            else:
                r_type = "Classroom"
            try:
                cap = int(row.get("seats", 40) or 40)
            except Exception:
                cap = 40
            extracted["rooms"][r_id] = Room(id=r_id, capacity=cap, type=r_type)

        # ---------- 5. GROUP (Major) ----------
        grp = str(row.get("major", "G1")).strip()
        if not grp or grp.lower() == "nan":
            grp = "G1"
        extracted["groups"].add(grp)

        # ---------- 6. Add course (component instance) ----------
        try:
            cap_needed = int(row.get("seats", 0) or 0)
        except Exception:
            cap_needed = 0

        extracted["courses"].append(
            Course(
                id=course_id,
                component=comp,
                hours=hours,
                group=grp,
                faculty_id=fac_id,             # ⬅ ID stored separately
                faculty_name=fac_name,         # ⬅ NEW: keep actual faculty name
                is_core=True,
                capacity_needed=int(row.get("seats", 0) or 0),
                room_id=r_id if r_id else "",
            )
        )

    # finalize containers
    rooms_list = list(extracted["rooms"].values())
    faculty_list = list(extracted["faculty"].values())
    groups_list = list(extracted["groups"])

    # If no rooms defined, auto-generate generic classrooms
    if not rooms_list:
        for i in range(1, 11):
            rooms_list.append(Room(id=f"Room_{i}", capacity=60, type="Classroom"))

    extracted["rooms"] = rooms_list
    extracted["faculty"] = faculty_list
    extracted["groups"] = groups_list

    return extracted


def process_uploaded_files(uploaded_files):
    master = {"courses": [], "rooms": [], "faculty": [], "groups": []}
    temp_rooms: Dict[str, Room] = {}
    temp_faculty: Dict[str, Faculty] = {}
    temp_groups = set()

    for file in uploaded_files:
        try:
            if file.name.lower().endswith(".csv"):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
        except Exception as e:
            st.error(f"Error reading {file.name}: {e}")
            continue

        if df.empty:
            continue

        extracted = extract_entities_from_master_sheet(df)
        if not extracted:
            continue

        master["courses"].extend(extracted["courses"])
        for r in extracted["rooms"]:
            temp_rooms[r.id] = r
        for f in extracted["faculty"]:
            temp_faculty[f.id] = f
        for g in extracted["groups"]:
            temp_groups.add(g)

        st.toast(f"✅ Extracted from {file.name}")

    master["rooms"] = list(temp_rooms.values())
    master["faculty"] = list(temp_faculty.values())
    master["groups"] = list(temp_groups)

    flags = {
        "courses": len(master["courses"]) > 0,
        "rooms": len(master["rooms"]) > 0,
        "faculty": len(master["faculty"]) > 0,
        "groups": len(master["groups"]) > 0,
    }

    # If no rooms, create generics
    if flags["courses"] and not flags["rooms"]:
        for i in range(1, 11):
            master["rooms"].append(Room(id=f"Room_{i}", capacity=60, type="Classroom"))
        flags["rooms"] = True
        st.warning("⚠ No rooms detected – auto-created 10 generic classrooms.")

    return master, flags


# -----------------------------------------------------------
# History / ICS helpers
# -----------------------------------------------------------

def save_state():
    st.session_state.history.append({
        "overrides": list(st.session_state.overrides),
        "schedule": st.session_state.schedule,
        "messages": list(st.session_state.messages),
    })


def perform_undo():
    if st.session_state.history:
        last = st.session_state.history.pop()
        st.session_state.overrides = last["overrides"]
        st.session_state.schedule = last["schedule"]
        st.session_state.messages = last["messages"]
        st.rerun()


def create_ics_file(schedule_data):
    c = Calendar()
    if not schedule_data:
        return c.serialize()

    today = datetime.now()
    days_ahead = 0 - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    next_monday = today + timedelta(days=days_ahead)
    day_map = {
        "Mon": next_monday,
        "Tue": next_monday + timedelta(days=1),
        "Wed": next_monday + timedelta(days=2),
        "Thu": next_monday + timedelta(days=3),
        "Fri": next_monday + timedelta(days=4),
    }

    for item in schedule_data:
        try:
            start_str, end_str = item["time"].split("-")
            base = day_map.get(item["day"])
            if not base:
                continue

            h1, m1 = map(int, start_str.split(":"))
            h2, m2 = map(int, end_str.split(":"))
            start_dt = base.replace(hour=h1, minute=m1, second=0)
            end_dt = base.replace(hour=h2, minute=m2, second=0)

            e = Event(
                name=f"{item['course']} ({item['component']})",
                begin=start_dt,
                end=end_dt,
            )
            e.location = f"Room {item['room']}"
            e.description = f"Faculty: {item['faculty']} | Group: {item['group']}"
            c.events.add(e)
        except Exception:
            continue

    return c.serialize()


# -----------------------------------------------------------
# LangGraph Solve
# -----------------------------------------------------------

def run_langgraph_cycle():
    objs = st.session_state.domain_objects
    state = {
        "courses": objs["courses"],
        "rooms": objs["rooms"],
        "faculty": objs["faculty"],
        "groups": objs["groups"],
        "overrides": st.session_state.overrides,
        "schedule": [],
        "analysis": "",
        "statistics": "",
        "status": "",
    }

    app_graph = build_timetable_graph()

    with st.spinner("🧮 Running solver → inspector..."):
        final_state = app_graph.invoke(state)  # type: ignore

    st.session_state.schedule = final_state.get("schedule", [])
    st.session_state.messages.append({
        "role": "assistant",
        "content": final_state.get("analysis", "No analysis."),
    })


# -----------------------------------------------------------
# Sidebar UI
# -----------------------------------------------------------

with st.sidebar:
    st.header("1. Data Upload")

    api_key = st.text_input("Groq API Key", type="password", value=os.getenv("GROQ_API_KEY", ""))
    if api_key:
        os.environ["GROQ_API_KEY"] = api_key

    uploaded_files = st.file_uploader(
        "Upload course data (.csv or .xlsx)",
        type=["csv", "xlsx", "xls"],
        accept_multiple_files=True,
    )

    if uploaded_files and st.button("Process Files"):
        objs, flags = process_uploaded_files(uploaded_files)
        st.session_state.domain_objects = objs
        st.session_state.data_status = flags
        st.session_state["TIME_SLOTS"] = TIME_SLOTS
        st.rerun()

    flags = st.session_state.data_status
    col_a, col_b = st.columns(2)
    col_a.markdown(f"{'✅' if flags['courses'] else '❌'} Courses")
    col_a.markdown(f"{'✅' if flags['rooms'] else '❌'} Rooms")
    col_b.markdown(f"{'✅' if flags['faculty'] else '❌'} Faculty")
    col_b.markdown(f"{'✅' if flags['groups'] else '❌'} Groups")

    ready = flags["courses"]

    if ready:
        st.header("2. Controls")
        c1, c2 = st.columns(2)
        if c1.button("🔄 Solve Cycle", type="primary"):
            st.session_state.overrides = []
            st.session_state.messages = []
            st.session_state.history = []
            st.session_state.schedule = None
            st.session_state.trigger_solve = True
            st.rerun()

        if c2.button("↩️ Undo"):
            perform_undo()

        # ==============================================================
        # 📌 MANUAL OVERRIDE PANEL (Completely Redesigned)
        # ==============================================================

        with st.expander("🔒 Manual Override — Lock a Course Component", expanded=True):

            st.markdown("""
            Use this panel to *force* a specific course component (L/T/P) into a specific
            official university slot. This override is applied **before** the solver runs.

            ✔ Only valid time-slots for the component (L/T/P) are shown  
            ✔ Course + Component appear as a single selectable item  
            ✔ Force override will clear conflicting classes in that slot  
            """)

            courses_available = st.session_state.domain_objects.get("courses", [])

            
            if not courses_available:
                st.warning("⚠️ Load data first to use overrides.")
            else:
                all_courses = courses_available
                TIME_SLOTS = st.session_state.get("TIME_SLOTS", [])
                
                if not TIME_SLOTS:
                    st.error("❌ TIME_SLOTS not found in session_state. Make sure you set st.session_state['TIME_SLOTS'] when loading timeslots.")
                else:


                    # ----------------------------------------------------------
                    # Build nice readable labels for selection
                    # ----------------------------------------------------------
                    course_options = []
                    for c in all_courses:
                        component_label = {"L": "Lecture", "T": "Tutorial", "P": "Practical"}[c.component]
                        label = f"{c.id} • {component_label} ({c.component}) • Group: {c.group}"
                        course_options.append((label, c))

                    selected_label = st.selectbox(
                        "Select Course Component",
                        [lbl for lbl, obj in course_options],
                        key="override_course_select"
                    )

                    selected_course = next(obj for lbl, obj in course_options if lbl == selected_label)
                    comp = selected_course.component  # L/T/P

                    # ----------------------------------------------------------
                    # Day select
                    # ----------------------------------------------------------
                    selected_day = st.selectbox("Select Day", ["Mon", "Tue", "Wed", "Thu", "Fri"])

                    # ----------------------------------------------------------
                    # Slot selection filtered by component type
                    # ----------------------------------------------------------
                    valid_slots = [
                        ts for ts in TIME_SLOTS
                        if comp in ts.get("allowed_components", [])
                        and selected_day in ts["days"]         # <-- ADD THIS LINE
                    ]


                    # Build readable options
                    slot_options_ui = [
                        f"{ts['start']}-{ts['end']}   |   Slot {ts['slot_id']}"
                        for ts in valid_slots
                    ]

                    selected_slot_label = st.selectbox(
                        "Select Time Slot (matches official TIME_SLOTS)",
                        slot_options_ui,
                        key="override_slot_select"
                    )

                    # Fetch the matching slot object
                    selected_slot = next(
                        ts for ts in valid_slots
                        if f"{ts['start']}-{ts['end']}   |   Slot {ts['slot_id']}" == selected_slot_label
                    )

                    force_override = st.checkbox(
                        "⚠️ Force override (clears conflicting classes in this slot family)",
                        value=False
                    )

                    if st.button("Apply Override", type="primary"):
                        ov = {
                            "course_id": selected_course.id,
                            "component": selected_course.component,
                            "day": selected_day,
                            "time": f"{selected_slot['start']}-{selected_slot['end']}",
                            "force": force_override,
                        }

                        # Add to state
                        if "overrides" not in st.session_state:
                            st.session_state["overrides"] = []

                        st.session_state["overrides"].append(ov)

                        st.success(f"Override added for **{selected_course.id} ({selected_course.component})**.")
                        st.json(ov)


        if st.session_state.overrides:
            st.subheader("Active Overrides")
            for i, ov in enumerate(st.session_state.overrides):
                ca, cb = st.columns([4, 1])
                ca.caption(f"{ov['course_id']} {ov['component']} → {ov['day']} {ov['time']} (force={ov.get('force', False)})")
                if cb.button("✖", key=f"ovd{i}"):
                    save_state()
                    st.session_state.overrides.pop(i)
                    st.session_state.trigger_solve = True
                    st.rerun()

        if st.session_state.schedule:
            st.divider()
            st.download_button(
                "📅 Download .ics",
                create_ics_file(st.session_state.schedule),
                "timetable.ics",
                "text/calendar",
            )


# -----------------------------------------------------------
# Main Layout
# -----------------------------------------------------------

st.title("📅 Agentic AI Timetable Scheduler (Strict Slots)")

if st.session_state.trigger_solve and st.session_state.data_status["courses"]:
    run_langgraph_cycle()
    st.session_state.trigger_solve = False

ready = st.session_state.data_status["courses"]

if not ready:
    st.info("👋 Upload at least one valid data file to begin.")
else:
    objs = st.session_state.domain_objects
    c_count = len(objs.get("courses", []))
    r_count = len(objs.get("rooms", []))
    f_count = len(objs.get("faculty", []))
    g_count = len(objs.get("groups", []))

    st.markdown("### 📊 Data Summary")
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Courses (components)", c_count)
    s2.metric("Rooms", r_count)
    s3.metric("Faculty", f_count)
    s4.metric("Groups", g_count)

    col_sched, col_chat = st.columns([2.2, 1])

    with col_sched:
        st.markdown("### 📌 Timetable")

        if st.session_state.schedule:
            df = pd.DataFrame(st.session_state.schedule)
            df = df.sort_values(["day", "time", "course"])

            fc1, fc2 = st.columns([1.5, 1])
            mode = fc1.selectbox("Filter By", ["All", "Group", "Faculty", "Room"])
            view_df = df.copy()

            if mode == "Group":
                val = fc2.selectbox("Group", sorted(df["group"].unique()))
                view_df = df[df["group"] == val]
            elif mode == "Faculty":
                val = fc2.selectbox("Faculty", sorted(df["faculty"].unique()))
                view_df = df[df["faculty"] == val]
            elif mode == "Room":
                val = fc2.selectbox("Room", sorted(df["room"].unique()))
                view_df = df[df["room"] == val]

            view_mode = st.radio("Display Mode", ["Grid", "List"], horizontal=True)

            if view_mode == "Grid":
                view_df["label"] = (
                    view_df["course"] + " (" + view_df["component"] + ") - " + view_df["room"]
                )
                grid = view_df.pivot_table(
                    index="time",
                    columns="day",
                    values="label",
                    aggfunc=lambda x: "\n".join(x),  # type: ignore
                    fill_value="",
                )
                st.dataframe(grid, width="stretch", height=700)
            else:
                st.dataframe(view_df, width="stretch", height=700)
        else:
            st.info("👈 Data processed. Click **Solve Cycle** in the sidebar to generate the timetable.")

    # Chat panel
    with col_chat:
        st.subheader("💬 AI Assistant")

        cont = st.container(height=600)
        with cont:
            if not st.session_state.messages:
                st.markdown("👋 *Ask me about the timetable, or request changes (e.g., 'Move BIO101 lecture to Tue 10:00-11:00').*")

            for m in st.session_state.messages:
                with st.chat_message(m["role"]):
                    txt = re.sub(r"```json.*?```", "", m["content"], flags=re.DOTALL).strip()
                    st.markdown(txt or m["content"])

        user_text = st.chat_input("Type your question or change request...")
        if user_text:
            st.session_state.messages.append({"role": "user", "content": user_text})
            with cont:
                with st.chat_message("user"):
                    st.markdown(user_text)

                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        hist_msgs = [
                            HumanMessage(content=m["content"]) if m["role"] == "user"
                            else AIMessage(content=m["content"])
                            for m in st.session_state.messages[:-1]
                        ]

                        resp = get_chat_response(
                            user_text,
                            st.session_state.schedule or [],
                            hist_msgs,
                        )

                        # show full assistant message
                        st.markdown(resp)
                        st.session_state.messages.append({"role": "assistant", "content": resp})

                        # ---------------------------------------------------------
                        # FIX: ROBUST JSON EXTRACTION
                        # ---------------------------------------------------------
                        json_str = None
                        
                        # 1. Try finding BEGIN_JSON ... END_JSON
                        match_tags = re.search(r"BEGIN_JSON(.*?)END_JSON", resp, re.DOTALL)
                        if match_tags:
                            json_str = match_tags.group(1).strip()
                        
                        # 2. If not found, try Markdown Code Blocks ```json ... ```
                        if not json_str:
                            match_code = re.search(r"```json(.*?)```", resp, re.DOTALL)
                            if match_code:
                                json_str = match_code.group(1).strip()

                        # 3. If valid JSON string found, parse and apply
                        if json_str:
                            try:
                                data = json.loads(json_str)
                                if data.get("action") == "add_override":
                                    overrides = data.get("overrides", [])
                                    if isinstance(overrides, list):
                                        save_state()
                                        
                                        # Append new overrides
                                        added_count = 0
                                        for ov in overrides:
                                            # Validate keys
                                            if all(k in ov for k in ("course_id", "component", "day", "time")):
                                                st.session_state.overrides.append({
                                                    "course_id": ov["course_id"],
                                                    "component": ov["component"],
                                                    "day": ov["day"],
                                                    "time": ov["time"],
                                                    "force": bool(ov.get("force", False)),
                                                })
                                                added_count += 1
                                        
                                        if added_count > 0:
                                            st.toast(f"🔄 Applying {added_count} overrides...", icon="🤖")
                                            st.session_state.trigger_solve = True
                                            st.rerun()
                                            
                            except json.JSONDecodeError:
                                st.error("Bot tried to change schedule but generated invalid JSON.")
                            except Exception as e:
                                st.error(f"Error applying override: {e}")
