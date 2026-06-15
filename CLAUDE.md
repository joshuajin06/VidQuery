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

## Architecture

```
main.py              — FastAPI app, CORS middleware, mounts routers
routers/summarize.py — POST /summarize endpoint (stub)
services/transcript.py — fetches YouTube transcript via youtube-transcript-api
services/summarizer.py — calls OpenAI to summarize the transcript text
models/schemas.py    — Pydantic models (SummarizeRequest, response shape)
core/config.py       — loads env vars (OpenAI key, etc.)
frontend/            — static UI; js/api.js POSTs to /summarize, js/ui.js handles DOM
```

**Request flow:** `POST /summarize {url}` → router calls `transcript.py` to fetch transcript → passes text to `summarizer.py` → returns `{summary}` to frontend.

## Current State

Most service files (`routers/summarize.py`, `services/transcript.py`, `services/summarizer.py`, `core/config.py`, `models/schemas.py`) are stubs — the framework is scaffolded but implementation is incomplete. The CORS origin in `main.py` is misconfigured (`https://localhost:8000` should be `http://localhost:8000` to match the frontend).
