import os
from google import genai

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY is not set")

client = genai.Client(api_key=api_key)

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="""
Summarize this discussion in 2 sentences:

Python is a popular programming language.
Variables store data values.
Functions help organize and reuse code.
Loops are useful for repeating operations.
"""
)

print("\nGEMINI RESPONSE:\n")
print(response.text)


