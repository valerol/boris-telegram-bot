import os
from dotenv import load_dotenv
from openai import OpenAI

from bois import run as run_bois

load_dotenv()

def get_client():
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class BOISRuntime:

    def run(self, user_text: str):
        return run_bois(user_text)

    def call_llm(self, parsed):

        client = get_client()

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a BOIS runtime assistant."
                },
                {
                    "role": "user",
                    "content": str(parsed)
                }
            ]
        )

        return response.choices[0].message.content
