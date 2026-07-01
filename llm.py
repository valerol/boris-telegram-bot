import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

def get_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=api_key)

def call_llm(prompt: str):
    print("LLM_CALL_START")
    try:
        client = get_client()

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "BOIS generator"},
                {"role": "user", "content": prompt}
            ]
        )

        content = resp.choices[0].message.content
        if not content:
            raise RuntimeError("empty LLM response")
        print("LLM_CALL_OK")
        return content
    except Exception as error:
        print(f"LLM_CALL_ERROR: {error}")
        raise
