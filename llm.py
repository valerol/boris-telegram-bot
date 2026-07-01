import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def call_llm(prompt: str):
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a BOIS structured response generator."},
            {"role": "user", "content": prompt}
        ]
    )
    return resp.choices[0].message.content
