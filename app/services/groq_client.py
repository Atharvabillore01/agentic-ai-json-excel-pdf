import os
from dotenv import load_dotenv 
from groq import Groq

load_dotenv() 

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL = "llama-3.3-70b-versatile"

def groq_chat(messages, tools=None):
    return client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )