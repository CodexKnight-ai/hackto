from google import genai
from google.genai import types
import os
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

response = client.models.generate_content(
    model="gemma-4-26b-a4b-it",
    contents='Reply with exactly: {"ok": true}',
    config=types.GenerateContentConfig(
        temperature=0.1,
        max_output_tokens=1024,
    ),
)

print("Text:", repr(response.text))
print("Candidates:", repr(response.candidates))
print("Prompt feedback:", repr(response.prompt_feedback))