import os
from dotenv import load_dotenv

load_dotenv()

from bois import run
import json

while True:
    user_input = input("USER> ")
    result = run(user_input)
    print(json.dumps(result, indent=2, ensure_ascii=False))
