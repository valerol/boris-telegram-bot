import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class BOISRuntime:

    def parse(self, text: str):
        intent = "general"

        t = text.lower()

        if "what is" in t:
            intent = "explanation"
        elif "how" in t:
            intent = "instruction"

        risk = 0.1
        uncertainty = 0.4

        return {
            "raw": text,
            "intent": intent,
            "risk": risk,
            "uncertainty": uncertainty
        }

    def route(self, parsed):
        # пока простая логика
        return "LLM"

    def call_llm(self, parsed):

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a BOIS runtime assistant. Return structured answer."
                },
                {
                    "role": "user",
                    "content": str(parsed)
                }
            ]
        )

        return response.choices[0].message.content

    def run(self, text: str):

        parsed = self.parse(text)
        route = self.route(parsed)

        if route == "LLM":
            llm_response = self.call_llm(parsed)
        else:
            llm_response = "RULE_EXECUTED"

        return {
            "bois_version": "0.1",
            "input": parsed,
            "decision": {
                "route": route
            },
            "output": {
                "answer": llm_response
            }
        }
