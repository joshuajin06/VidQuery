# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YT-Summarizer is a FastAPI backend + vanilla JS frontend that accepts a YouTube URL, fetches the video transcript via `youtube-transcript-api`, summarizes it using OpenAI, and returns the result to the browser.

## Running the App

```bash
source .venv/bin/activate
uvicorn main:app --reload
```

The frontend is static HTML/CSS/JS in `frontend/` — open `frontend/index.html` directly in a browser. The JS hardcodes `http://localhost:8000` as the API base.

## Environment

Requires a `.env` file with an OpenAI API key. Config is loaded in `core/config.py`.

