import requests
from app.core import settings

class ElevenLabsClient:
    def __init__(self):
        self.api_key = settings.ELEVENLABS_API_KEY
        self.voice_id = settings.ELEVENLABS_VOICE_ID  # e.g. "Rachel"
        self.base_url = "https://api.elevenlabs.io/v1/text-to-speech"

    def synthesize(self, text: str) -> bytes:
        url = f"{self.base_url}/{self.voice_id}"
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.4,
                "similarity_boost": 0.6
            }
        }

        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.content
