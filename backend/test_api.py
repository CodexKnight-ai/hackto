import os
import sys
from pathlib import Path
from dotenv import load_dotenv

out_file = Path(__file__).parent / "api_debug_log.txt"

def log(*args):
    text = " ".join(str(a) for a in args)
    with open(out_file, "a", encoding="utf-8") as f:
        f.write(text + "\n")

with open(out_file, "w", encoding="utf-8") as f:
    f.write("Starting test...\n")

try:
    load_dotenv(Path(__file__).parent / ".env")
    from google import genai
    from google.genai import types

    api_key = os.environ.get("GEMINI_API_KEY")
    log("API Key present:", bool(api_key))

    client = genai.Client(api_key=api_key)

    log("Testing models.list():")
    try:
        models = [m.name for m in client.models.list()]
        log("Models count:", len(models))
        log("Sample models:", models[:15])
    except Exception as e:
        log("models.list failed:", type(e), e)

    log("\nTesting gemma-4-26b-a4b-it:")
    try:
        resp = client.models.generate_content(
            model="gemma-4-26b-a4b-it",
            contents="Say hello",
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=8192,
            )
        )
        log("gemma-4-26b-a4b-it resp text:", resp.text)
    except Exception as e:
        log("gemma-4-26b-a4b-it failed:", type(e), e)

    log("\nTesting gemini-2.5-flash:")
    try:
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Say hello",
        )
        log("gemini-2.5-flash resp text:", resp.text)
    except Exception as e:
        log("gemini-2.5-flash failed:", type(e), e)

    log("\nTesting gemini-1.5-flash:")
    try:
        resp = client.models.generate_content(
            model="gemini-1.5-flash",
            contents="Say hello",
        )
        log("gemini-1.5-flash resp text:", resp.text)
    except Exception as e:
        log("gemini-1.5-flash failed:", type(e), e)

except Exception as outer_e:
    log("Outer exception:", type(outer_e), outer_e)

log("Done.")
