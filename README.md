# Agentic_AI_University_Timetable_Scheduler
This project automates the complex task of university course scheduling.

**A Human-in-the-Loop Optimization System**
Combines Google OR-Tools for mathematical constraint solving with a Generative AI Agent (OpenAI GPT) for interactive schedule repair and analysis.

---

## Overview

This project is an intelligent, interactive system designed to automate the complex task of university course scheduling. It combines deterministic mathematical optimization with a Generative AI agent to create a "human-in-the-loop" workflow.

Unlike traditional "black-box" solvers, this system features an Agentic AI co-pilot. The system uses Google OR-Tools to solve hard constraints (room capacity, faculty availability, time clashes) and generate an initial valid schedule. It then employs an LLM-based "Inspector Agent" (powered by OpenAI GPT via Groq) to analyze the schedule for soft constraint violations. Crucially, the user can interact with the schedule using natural language (e.g., "Move CS102 to Tuesday morning"), prompting the AI to output structured actions that trigger the solver to re-calculate the schedule in real-time.

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

## Plan
I plan to excecute these steps to complete my project.:

1) [DONE]**Step 1: Data Modeling & Smart Ingestion**: Designed dataclasses for Courses, Rooms, and Faculty. Implemented a Smart Parser that accepts multiple CSV or Excel files, auto-detects the table type (Courses vs. Rooms) based on column keywords, and normalizes headers for the solver. (```models.py```)

2) [DONE] **Step 2: Constraint Solver Implementation and Official Timeslot Parser**: I implemented hard constraints (no double-booking, room type matching) and pattern constraints (forcing Monday/Wednesday/Friday symmetry for 3-credit courses). Converted the university PDF timeslot grid into a structured list of valid slots with day, start–end times, allowed components, and slot families. (```solver.py``` and ```timeslots.py```)

3) [DONE] **Step 3:  Build LangGraph Agent Pipeline**: Createed:
  - An **Inspector Agent** that summarizes schedule quality and finds issues.
  - A **Repair Agent** that applies overrides when the user issues commands. (```graph.py``` and ```inspector.py```)

4) **[DONE] Step 5 – Streamlit Dashboard**: Built a UI with:
  - file upload,
  - live schedule display,
  - chat panel for agent interaction,
  - override controls,
  - download/export options.

5) **[TODO] Step 6 – Testing With Real Data**: Use large real-world semester sheets to test performance, conflict accuracy, and the override workflow.