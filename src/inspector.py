from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq
import os
import pandas as pd
import json

def format_schedule_as_table(schedule):
    """Converts JSON schedule to Markdown table for RAG-lite."""
    if not schedule: return "No data."
    df = pd.DataFrame(schedule)
    cols = ["day", "time", "course", "component", "room", "faculty", "group"]
    cols = [c for c in cols if c in df.columns]
    return df[cols].to_markdown(index=False)

def inspect_schedule(schedule):
    """Static analysis for initial report."""
    if not schedule: return "No valid schedule found."
    
    llm = ChatGroq(
        groq_api_key=os.getenv("GROQ_API_KEY"), # type: ignore
        model="openai/gpt-oss-20b",
        temperature=0
    )
    
    table_data = format_schedule_as_table(schedule)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """
        You are a Timetable Inspector. 
        Analyze the schedule data below and provide a brief executive summary.
        Focus on: Heaviest Day, Soft Constraint issues (8 AM classes), and General distribution.
        """),
        ("user", "Schedule Data:\n{schedule_data}")
    ])
    chain = prompt | llm
    return chain.invoke({"schedule_data": table_data}).content

def get_chat_response(user_input, schedule_context, chat_history):
    """Agentic Chat with Action Capabilities."""
    if not os.getenv("GROQ_API_KEY"): return "Please set API Key."
    
    llm = ChatGroq(
        groq_api_key=os.getenv("GROQ_API_KEY"), # type: ignore
        model="openai/gpt-oss-20b",
        temperature=0.1
    )
    
    context_table = format_schedule_as_table(schedule_context)
    
    system_prompt = """
    You are an intelligent University Timetable Agent.
    
    DATA CONTEXT:
    {schedule_table}
    
    CAPABILITIES:
    1. **Data Analyst:** Answer questions (e.g. "Who teaches Math?").
    2. **Scheduler:** If user asks to CHANGE something (e.g. "Move Math to Tue"), output JSON.
    
    JSON FORMAT:
    ```json
    {{
        "action": "add_override",
        "course_id": "COURSE_ID",
        "component": "L/T/P",
        "day": "Mon/Tue/Wed/Thu/Fri",
        "time": "HH:MM-HH:MM"
    }}
    ```
    """
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}")
    ])
    
    chain = prompt | llm
    return chain.invoke({
        "history": chat_history,
        "input": user_input,
        "schedule_table": context_table
    }).content