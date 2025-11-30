# Agentic_AI_University_Timetable_Scheduler
This project automates the complex task of university course scheduling.

**A Human-in-the-Loop Optimization System**
Combines Google OR-Tools for mathematical constraint solving with a Generative AI Agent for interactive schedule repair and analysis.

---

## Overview
Our university always had issues in coming up with a fixed timetable for a semester. Not only are the time slots of courses not aligning with the majority of the student body,
changing the timetable alone is a tedious task faced by the short staffed academic office. Through the learnings in this course, I planned to use this project as an opportunity to potentially solve this timetabling issues with the help of Agentic Models.

TThis project implements an **AI-powered, fully interactive university timetable scheduler** that combines:

1) **Symbolic optimization** (Google OR-Tools)
2) **Agentic reasoning** (LLM running via LangGraph)
3) **Human-in-the-loop repair workflows**
4) **Strict university timeslot rules** extracted from the official PDF grid
5) **Conflict-free scheduling** for rooms, faculty, and student groups
6) **Override + forced override** (admin-style manual slot assignment)
7) **Interactive Streamlit dashboard**

The system first loads a semester-long **master sheet** (Excel/CSV) containing all courses, components (L/T/P), faculty, groups, and requested hours.  
Then:

1. A **strict deterministic solver** generates a valid baseline timetable using official university slots only.  
2. An **Inspector Agent (LLM)** analyzes the timetable and identifies issues such as:
   - uneven day-wise distribution,
   - overloads,
   - early-morning clusters,
   - room bottlenecks,
   - components assigned incorrectly.
3. A **Repair Agent** applies changes requested by the user such as:
   - *“Move BIO101 PRAC1 to Tuesday 11:00, even if occupied.”*
   - *“Swap these two lectures.”*
   - *“Force override this slot.”*

This creates a seamless **AI-assisted scheduling pipeline** aligned with real academic constraints.

## Reason for picking up this project
This project is directly aligned with the course’s learning objectives on integration of LangGraph and LangChain:


### **Agentic AI Workflows**: 
Building multi-step reasoning pipelines where the LLM:
1) analyzes structured input,
2) produces actionable insights,
3) assists in human-guided decision making.

### **Integrating LLMs with Tooling**: 
The project demonstrates the use of:
1) LangChain + LangGraph,
2) External tools (Hybrid solver),
3) State-machine graph execution,
4) Streaming LLM interactions.

### **Real-world Constraint Design**"
Timetable scheduling contains the following constraints:
1) faculty availability,
2) classroom capacity,
3) slot exclusivity,
4) group clash resolution,
5) override vs. forced override logic,
6) strict slot families (MWF / TTH based on the university's official timetable).

## Video Summary Link
> **([Drive Link for Video](https://drive.google.com/drive/folders/1HYUswl-fOarJ26HAtSB4NBmSM4q8My16?usp=sharing))**  

## Plan
I plan to excecute these steps to complete my project.:

1) [DONE]**Step 1: Data Modeling & Smart Ingestion**: Designed dataclasses for Courses, Rooms, and Faculty. Implemented a Smart Parser that accepts multiple CSV or Excel files, auto-detects the table type (Courses vs. Rooms) based on column keywords, and normalizes headers for the solver. (```models.py```)

2) [DONE] **Step 2: Constraint Solver Implementation and Official Timeslot Parser**: I implemented hard constraints (no double-booking, room type matching) and pattern constraints (forcing Monday/Wednesday/Friday symmetry for 3-credit courses). Converted the university PDF timeslot grid into a structured list of valid slots with day, start–end times, allowed components, and slot families. (```solver.py``` and ```timeslots.py```)

3) [DONE] **Step 3:  Build LangGraph Agent Pipeline**: Created:
    - An **Inspector Agent** that summarizes schedule quality and finds issues.
    - A **Repair Agent** that applies overrides when the user issues commands. (```graph.py``` and ```inspector.py```)

4) **[DONE] Step 5 – Streamlit Dashboard**: Built a UI with:
    - file upload,
    - live schedule display,
    - chat panel for agent interaction,
    - override controls,
    - download/export options.

5) **[DONE] Step 6 – Testing With Real Data**: Use large real-world semester sheets to test performance, conflict accuracy, and the override workflow.

Added ```images``` and ```exported_tables``` folders to show the working of program as well as provide the output.

## Conclusion
I planned to achieve the following goals:

- Parse messy real-world academic data reliably.  
- Enforce a strict, real university timetable slot grid.  
- Build a hybrid deterministic + LLM agentic scheduling framework.  
- Provide a user-friendly dashboard with real-time AI analysis.  
- Support override and forced override logic like an admin system.

I believe I have **successfully achieved** these goals:

    - The solver schedules most courses into official slots, resolving clashes accurately.  
    - The Inspector Agent produces clear, structured analyses.  
    - The Repair Agent handles user commands correctly.  
    - The UI demonstrates a realistic, interactive scheduling workflow.

Remaining limitations include:

    - Heavy requests to large LLMs can exceed model token limits.  
    - Some extreme cases of overlapping constraints require manual forced override.
    - Instances of AI "hallucinations" during overriding which can be fixed with better AI models
