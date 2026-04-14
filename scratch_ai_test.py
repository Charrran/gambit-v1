import instructor
from groq import Groq, AsyncGroq
import asyncio
from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()

class TestModel(BaseModel):
    message: str

async def test_async():
    try:
        # Testing what happens with AsyncGroq
        client = instructor.from_groq(AsyncGroq(api_key=os.getenv("GROQ_API_KEY")), mode=instructor.Mode.JSON)
        print("Async Client initialized")
        # Check available methods
        print(f"Completions methods: {dir(client.chat.completions)}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_async())
