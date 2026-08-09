#AQ.Ab8RN6K6mfKNfEcs9XDyG2WvXda9lYqX80YUnGe5vBR3IQyVLQ
import os
from google import genai

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(
    api_key=GEMINI_API_KEY
)


def summarize_discussion(title, comments):

    if not comments:
        return "No comments yet on this topic."

    combined_text = "\n\n".join(comments)

    prompt = f"""
Summarize the following community discussion in 3-4 clear sentences.

Topic: {title}

Comments:
{combined_text}

Give a neutral and factual summary of what was discussed.
Do not add information that is not present in the discussion.
"""

    try:

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        return response.text.strip()

    except Exception as e:

        print("GEMINI ERROR:", e)

        return "Summary temporarily unavailable."