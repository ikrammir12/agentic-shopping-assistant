from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

def get_llm():
    """Create and return a ChatGroq instance with the API key from the .env file."""
    
    # Load environment variables from .env file
    load_dotenv()

    # Retrieve the API key from environment variables
    api_key = os.getenv("GROQ_API_KEY")
    llm = ChatGroq(
    api_key=api_key,
    temperature=0.7,
    max_tokens=1020,
    model="openai/gpt-oss-20b",
    reasoning_effort="low",
    max_retries=2
)
    # Create and return a ChatGroq instance
    return llm