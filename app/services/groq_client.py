import os
from groq import Groq

_client = None

class GroqClient:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not set")
        self.client = Groq(api_key=self.api_key)
        self.model = "mixtral-8x7b-32768"

    def query(self, prompt: str, max_tokens=1024, temperature=0.7) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature
        )
        return response.choices[0].message.content

    def summarize_for_voice(self, text: str) -> str:
        prompt = f"Summarize for voice (concise, conversational, <3 sentences, ask follow-ups clearly): {text}"
        return self.query(prompt, max_tokens=200, temperature=0.6)

def get_groq_client() -> GroqClient:
    global _client
    if _client is None:
        _client = GroqClient()
    return _client


def groq_chat(prompt: str, max_tokens=1024, temperature=0.7):
    client = get_groq_client()
    return client.query(prompt, max_tokens, temperature)
