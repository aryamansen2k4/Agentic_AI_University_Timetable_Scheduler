from typing import List, Dict, Any, Tuple, Optional
import os
import json
import re

import pandas as pd
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

# -------------------------------------------------------------
# Table formatter (for limited-size schedule context)
# -------------------------------------------------------------
def format_schedule_as_table(schedule: List[Dict[str, Any]], limit: int = 60) -> str:
    if not schedule:
        return "No schedule."
    df = pd.DataFrame(schedule)
    cols = ["day", "time", "course", "component", "room", "faculty", "group"]
    cols = [c for c in cols if c in df.columns]
    # Sort for readability
    if not df.empty:
        df = df.sort_values(["day", "time"]).head(limit)
    return df.to_markdown(index=False)

# -------------------------------------------------------------
# Helper: Extract JSON from LLM response
# -------------------------------------------------------------
def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """Robustly extracts JSON object from LLM response text."""
    try:
        # 1. Look for explicit delimiters
        match = re.search(r"BEGIN_JSON(.*?)END_JSON", text, re.DOTALL)
        if match:
            return json.loads(match.group(1).strip())
        
        # 2. Look for markdown code blocks
        match = re.search(r"```json(.*?)```", text, re.DOTALL)
        if match:
            return json.loads(match.group(1).strip())
            
    except json.JSONDecodeError:
        pass
    return None

# -------------------------------------------------------------
# Schedule inspector (Fixed for LangGraph)
# -------------------------------------------------------------
def inspect_schedule(
    schedule: List[Dict[str, Any]], 
    return_overrides: bool = False
) -> Tuple[str, List[Dict[str, Any]]]:
    
    if not schedule:
        return "No schedule generated.", []

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        # Fallback: simple text summary without LLM
        df = pd.DataFrame(schedule)
        counts_by_day = df.groupby("day")["course"].count().to_dict()
        msg = (
            "Schedule summary (no LLM – GROQ_API_KEY missing):\n"
            + "\n".join(f"{d}: {n} slots" for d, n in counts_by_day.items())
        )
        return msg, []

    # Use a strong model for JSON instruction following
    llm = ChatGroq(
        groq_api_key=api_key,   # type: ignore
        model="openai/gpt-oss-20b", # Reliable model for logic
        temperature=0.1,
    )

    table = format_schedule_as_table(schedule, limit=80)

    # Base System Prompt (Analysis)
    system_instructions = """You are a timetable inspector. Produce a structured, detailed timetable analysis
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
            - Use bullet points and clear subheadings exactly as shown.
    """

    # Append Override Instructions if needed
    if return_overrides:
        system_instructions += """
        
        CRITICAL TASK:
        If you detect a MAJOR flaw (e.g., a Faculty double-booked, or a Group with 8 hours straight), 
        you MUST propose a fix using a JSON block.

        CRITICAL RULES FOR OVERRIDES:
        1. ONLY propose a fix if there is a CATASTROPHIC failure (e.g. Faculty double-booked).
        2. DO NOT optimize for preference. Only optimize for validity.
        3. DO NOT INVENT COURSES. Only move courses that are already in the schedule.
        4. If the schedule is valid, return an empty overrides list.
        
        Format if and ONLY IF a fix is needed:
        
        Format:
        BEGIN_JSON
        {
            "action": "add_override",
            "overrides": [
                { "course_id": "CS101", "component": "L", "day": "Mon", "time": "09:00-10:00", "force": true }
            ]
        }
        END_JSON
        
        If no critical fixes are needed, do NOT include the JSON block.
        """

    messages = [
        SystemMessage(content=system_instructions),
        HumanMessage(content=f"Here is the schedule snapshot:\n{table}")
    ]

    response = llm.invoke(messages)
    content = response.content

    # Extract overrides if requested
    overrides = []
    if return_overrides:
        data = extract_json_from_text(content) # type: ignore
        if data and data.get("action") == "add_override":
            overrides = data.get("overrides", [])

    return content, overrides # type: ignore


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
        return "❌ GROQ_API_KEY is not set."

    llm = ChatGroq(
        groq_api_key=api_key,   # type: ignore
        model="openai/gpt-oss-20b",
        temperature=0.1,
    )

    table = format_schedule_as_table(schedule_context, limit=60)

    system_prompt = """
    You are the Timetable Fixing Agent.

    You have access to the *current* schedule as a small table, and the user may ask:
    - questions about the timetable
    - to move or reschedule specific classes
    - to rebalance early/late loads

    ### YOUR JOB: INTERPRET LAZY INPUTS
    Users will be lazy. They might say:
    - "move bio205 l to tue 9:35-11"
    - "put cs101 lab on friday morning"
    
    You must CLEAN and NORMALIZE this into strict data:
    1. **Course Code**: Convert "bio 205" -> "BIO205" (Check table for correct code).
    2. **Component**: Convert "lecture"/"class" -> "L", "lab"/"practical" -> "P", "tut" -> "T".
    3. **Time**: Convert "9:35-11" -> "09:35-11:00". Convert "2pm" -> "14:00-15:00". 
       (Always use strict HH:MM-HH:MM 24-hour format).
    4. **Day**: Convert "tue" -> "Tue", "thurs" -> "Thu".

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
    Do NOT put curly-brace variables in the JSON.
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