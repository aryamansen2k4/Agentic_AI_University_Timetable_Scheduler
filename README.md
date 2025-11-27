# Agentic_AI_University_Timetable_Scheduler
This project automates the complex task of university course scheduling.

**A Human-in-the-Loop Optimization System**
Combines Google OR-Tools for mathematical constraint solving with a Generative AI Agent (OpenAI GPT) for interactive schedule repair and analysis.

---

## Overview

This project is an intelligent, interactive system designed to automate the complex task of university course scheduling. It combines deterministic mathematical optimization with a Generative AI agent to create a "human-in-the-loop" workflow.

Unlike traditional "black-box" solvers, this system features an Agentic AI co-pilot. The system uses Google OR-Tools to solve hard constraints (room capacity, faculty availability, time clashes) and generate an initial valid schedule. It then employs an LLM-based "Inspector Agent" (powered by OpenAI GPT via Groq) to analyze the schedule for soft constraint violations. Crucially, the user can interact with the schedule using natural language (e.g., "Move CS102 to Tuesday morning"), prompting the AI to output structured actions that trigger the solver to re-calculate the schedule in real-time.

## Reason for picking up this project
This project was chosen to demonstrate the powerful integration of LangGraph and LangChain. It aligns with the course content by implementing advanced concepts such as:

1) Constraint Satisfaction Problems (CSP): Implementing hard constraints (no double-booking) and soft constraints (optimizing for preferred times) to solve NP-hard scheduling problems.

2) Agentic AI & Tool Use: Moving beyond simple chatbots to agents that can output structured JSON commands to control underlying application logic.

3) Human-in-the-Loop Systems: Designing an architecture where the AI proposes solutions and the human supervisor provides feedback or overrides via natural language.

4) State Management: Handling complex session states (overrides, chat history, schedule data) within a reactive web application.

## Plan
I plan to excecute these steps to complete my project.:

1) [TODO]**Step 1: Data Modeling & Smart Ingestion**
Designed dataclasses for Courses, Rooms, and Faculty. Implemented a Smart Parser that accepts multiple CSV or Excel files, auto-detects the table type (Courses vs. Rooms) based on column keywords, and normalizes headers for the solver.