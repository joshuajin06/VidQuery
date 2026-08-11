from dotenv import load_dotenv
import os

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ytsummarizer:ytsummarizer@localhost:5432/ytsummarizer")
