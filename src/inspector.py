# inspector.py
from typing import List, Dict, Any
import os
import json

import pandas as pd
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq


# -------------------------------------------------------------
# Table formatter (for limited-size schedule context)
# -------------------------------------------------------------
def format_schedule_as_table(schedule: List[Dict[str, Any]], limit: int = 60) -> str:
    if not schedule:
        return "No schedule."
    df = pd.DataFrame(schedule)
    cols = ["day", "time", "course", "component", "room", "faculty", "group"]
    cols = [c for c in cols if c in df.columns]
    df = df[cols].sort_values(["day", "time"]).head(limit)
    return df.to_markdown(index=False)


# -------------------------------------------------------------
# Schedule inspector (for LangGraph node)
# -------------------------------------------------------------
def inspect_schedule(schedule: List[Dict[str, Any]]) -> str:
    if not schedule:
        return "No schedule generated."

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        # Fallback: simple text summary without LLM
        df = pd.DataFrame(schedule)
        counts_by_day = df.groupby("day")["course"].count().to_dict()
        return (
            "Schedule summary (no LLM – GROQ_API_KEY missing):\n"
            + "\n".join(f"{d}: {n} slots" for d, n in counts_by_day.items())
        )

    llm = ChatGroq(
        groq_api_key=api_key,   # type: ignore
        model="meta-llama/llama-4-maverick-17b-128e-instruct",
        temperature=0.0,
    )

    table = format_schedule_as_table(schedule, limit=80)

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """You are a timetable inspector. Produce a structured, detailed timetable analysis
            with clear headings and bullet points.

            Your response MUST follow this structure:

            ### 1. Daily Load Distribution
            - Compare the number of classes across days.
            - Highlight which days are heavy or light.

            ### 2. Time-of-Day Patterns
            - Identify early-morning clusters (before 10 AM).
            - Identify late-afternoon clusters (after 3 PM).
            - Mention any unusually long gaps or compressed schedules.

            ### 3. Component Balance (L / T / P)
            - Comment on how lectures, tutorials, and practicals are distributed.
            - Mention if any component type is overloaded on specific days.

            ### 4. Room Usage Observations
            - Comment on room/lab overload, near-clashes, or uneven distribution.

            ### 5. Faculty Load Notes
            - Identify days where any faculty teaches multiple classes.
            - Comment on reasonable vs. heavy teaching days.

            ### 6. Noticeable Anomalies / Potential Issues
            - Mention any suspicious patterns, sudden peaks, or missing components.
            - Note anything that appears unbalanced or problematic.

            GENERAL RULES:
            - Do NOT exceed 20 lines overall, but be detailed.
            - Write concisely but analytically.
            - Use bullet points and clear subheadings exactly as shown."""
        ),
        ("human", "Here is the schedule snapshot:\n{table}")
    ])

    chain = prompt | llm
    return chain.invoke({"table": table}).content # type: ignore


# -------------------------------------------------------------
# Chat Agent: returns natural language + optional JSON overrides
# -------------------------------------------------------------
def get_chat_response(
    user_input: str,
    schedule_context: List[Dict[str, Any]],
    chat_history,
) -> str:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return "❌ GROQ_API_KEY is not set. Please provide it in the Streamlit sidebar."

    llm = ChatGroq(
        groq_api_key=api_key,   # type: ignore
        model="meta-llama/llama-4-maverick-17b-128e-instruct",
        temperature=0.1,
    )

    table = format_schedule_as_table(schedule_context, limit=60)

    system_prompt = """
    You are the Timetable Fixing Agent.

    You have access to the *current* schedule as a small table, and the user may ask:
    - questions about the timetable
    - to move or reschedule specific classes
    - to rebalance early/late loads

    RULES:

    1. If the user is just asking a question (no change requested),
    reply normally in natural language.

    2. If the user requests a CHANGE (e.g., "Move CS101 Lecture to Tue 10-11"),
    respond with *both*:
    - a short natural language explanation, and
    - a JSON override block in the exact format below:

    ```json
    {{
    "action": "add_override",
    "overrides": [
        {{
        "course_id": "COURSE_CODE",
        "component": "L/T/P",
        "day": "Mon/Tue/Wed/Thu/Fri",
        "time": "HH:MM-HH:MM",
        "force": false
        }}
    ]
    }}
    ```

    You may include multiple overrides inside "overrides".
    Always ensure the JSON is valid.
    Do NOT put curly-brace variables in the JSON (no {course_id}, use real values).
    """

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="history"),
        ("human", "Current schedule snapshot:\n{table}\n\nUser: {input}")
    ])

    chain = prompt | llm

    result = chain.invoke({
        "history": chat_history,
        "input": user_input,
        "table": table,
    })

    return result.content # type: ignore
