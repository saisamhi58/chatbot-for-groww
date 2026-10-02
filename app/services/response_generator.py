"""Generate responses using the LLM with streaming support."""

from typing import Generator
from tenacity import retry, stop_after_attempt, wait_exponential
from app.config import get_settings

settings = get_settings()


class ResponseGenerator:
    """Generate responses using OpenAI's LLM."""

    def __init__(self):
        from openai import OpenAI
        # Groq exposes an OpenAI-compatible API
        self.client = OpenAI(
            api_key=settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
        )
        self.model = settings.groq_llm_model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def generate(self, messages: list[dict]) -> str:
        """Generate a complete response."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.1,
            max_tokens=2000,
        )
        return response.choices[0].message.content

    def generate_stream(self, messages: list[dict]) -> Generator[str, None, None]:
        """Generate a streaming response."""
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.1,
            max_tokens=2000,
            stream=True,
        )

        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
