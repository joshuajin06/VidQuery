# YT-Summarizer
Takes in a YouTube URL and uses FastAPI and an LLM to fetch and summarize the video transcript.

## Setup

**1. Create and activate the virtual environment**
```bash
python -m venv .venv
source .venv/bin/activate
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

**3. Create a `.env` file in the project root**
```
GROQ_API_KEY=your_key_here
```

Get a free API key at [console.groq.com](https://console.groq.com).

## Running the App

**Start the backend:**
```bash
source .venv/bin/activate
uvicorn main:app --reload
```

**Start the frontend:**

Open `frontend/index.html` directly in your browser.

The backend runs on `http://localhost:8000`. The frontend is hardcoded to that address.

## Stack

- **Backend:** FastAPI + `youtube-transcript-api` + Groq (LLaMA 3)
- **Frontend:** Vanilla HTML/CSS/JS
