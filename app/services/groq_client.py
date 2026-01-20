import os
from groq import Groq

_client = None

def get_groq_client():
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not set")
        _client = Groq(api_key=api_key)
    return _client


def groq_chat(prompt: str, max_tokens=1024, temperature=0.7):
    client = get_groq_client()
    response = client.chat.completions.create(
        model="mixtral-8x7b-32768",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=temperature
    )
    return response.choices[0].message.content
