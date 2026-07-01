import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

def get_client():
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def call_llm(prompt: str):
    client = get_client()

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "BOIS generator"},
            {"role": "user", "content": prompt}
        ]
    )

    return resp.choices[0].message.content
