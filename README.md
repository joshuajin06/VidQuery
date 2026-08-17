# VidQuery

**[Live demo →](https://joshuajin06.github.io/VidQuery/)**

VidQuery takes a YouTube video and turns it into an AI-generated summary — paste a URL, or paste a transcript directly, and get back a concise, coherent summary in seconds, with live progress as it works. Under the hood it's also a full RAG (retrieval-augmented generation) pipeline: every transcript is chunked, embedded, and stored in a vector database, laying the groundwork for semantic search and chat-with-citations over video content.

It's a solo full-stack project — FastAPI backend, vanilla JS frontend, an LLM pipeline, a vector database, and a from-scratch deployment onto entirely free-tier infrastructure — built to be genuinely useful, not a tutorial clone.

## What it does

- **Paste a YouTube URL** → the backend fetches the transcript, summarizes it via an LLM, and streams progress back to the UI in real time.
- **Long videos are handled properly.** Transcripts over ~36K characters are automatically split into overlapping chunks, summarized in a map-reduce pass, and merged into one coherent summary — so a 90-minute keynote doesn't get truncated or produce a shallow result the way a naive single-prompt approach would.
- **Paste a transcript directly**, no URL required — the same summarization pipeline runs on raw pasted text, decoupling the AI pipeline from any single upstream data source.
- **Try an example** — a curated set of real, pre-captured transcripts (spanning a 19-second clip to a 92-minute keynote) let anyone see the full pipeline work instantly, including the multi-chunk summarization path, without depending on a live fetch.
- **Transcript ingestion pipeline** (`/index`) chunks each transcript with timestamps, embeds every chunk, and upserts it into a Postgres/pgvector store keyed by video — the foundation for the chat-with-citations feature described below.

## Why this project is worth a second look

A lot of "AI wrapper" projects stop at calling an LLM API. This one required solving real production problems along the way:

- **Diagnosed a live production issue down to the network layer.** After deploying, transcript fetching started failing in the cloud but not locally. Rather than guessing, I reproduced the failure from the deployed environment, cross-tested from a different network, and traced it to YouTube's cloud-IP/bot-detection measures — a known, actively-evolving arms race with no reliable free fix as of 2026. Instead of burning time chasing an unwinnable fight, I redesigned around it: a transcript-paste mode that decouples the actual value (summarization + RAG) from the fragile part (scraping), plus pre-verified example content so the app always has a reliable demo path.
- **Found and fixed a subtle pgvector bootstrap bug.** A brand-new Postgres database crashed on every deploy with `vector type not found in the database` — a chicken-and-egg problem where the code tried to register the `vector` type before the extension that defines it had been created. Worked locally (the dev database already had the extension from prior runs) but broke on a fresh production database. Traced it from a raw stack trace to the exact line, fixed it, and caught a test-suite regression the fix introduced along the way.
- **Cut the deployable footprint by ~92%.** The original embedding pipeline pulled in `torch` + `transformers` + `sentence-transformers` — over 1.2GB, well past what free-tier hosts allow. Rebuilt it to call the same embedding model through a hosted inference API instead of loading it locally, verified the swap preserved exact output dimensionality (no schema changes needed), and got the deployable footprint down to ~100MB.
- **Debugged infrastructure issues empirically, not by guessing.** A GitHub Pages deploy kept serving the README instead of the app — traced it via the GitHub API to a config flag silently still pointing at the legacy branch-deploy pipeline despite the Actions workflow reporting success. A monitoring integration returned 405s — reproduced it with `curl -I`, found the route only accepted `GET`, not `HEAD`, and fixed it.
- **Verified the frontend without a browser in the loop.** When no browser automation was available, built a real headless-DOM test harness (jsdom) that injects the actual shipped JS files and simulates real clicks and a real network round-trip against the live backend — rather than shipping UI changes on faith.
- **Deployed a full multi-service stack at $0/month by design**, not by accident: Render (backend), Neon (Postgres + pgvector), Hugging Face (embeddings), Groq (LLM inference), and GitHub Pages (frontend) — each chosen deliberately, with real tradeoffs (cold starts, compute-hour budgets, rate limits) understood and worked around rather than ignored.

## Architecture

| Layer | Technology | Notes |
|---|---|---|
| Frontend | Vanilla HTML/CSS/JS | No framework/build step — deployed as a static site |
| Backend | FastAPI | Async job pattern: POST kicks off a background job, GET polls status/progress |
| Transcript fetch | `youtube-transcript-api` | No official API key needed |
| Summarization | Groq (Llama 3.3 70B) | Map-reduce chunking for long transcripts, live per-chunk progress |
| Embeddings | Hugging Face Inference API (`all-MiniLM-L6-v2`) | Hosted, not loaded locally — keeps the deploy footprint small |
| Vector storage | Postgres + pgvector (Neon) | Chunk-level storage with timestamps, keyed by video |
| Hosting | Render (API) · GitHub Pages (frontend) | Both free tier; kept warm via scheduled health-check pings |
| CI/CD | GitHub Actions | Auto-deploys the frontend to Pages on every push to `frontend/` |

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
GROQ_API_KEY=your_groq_key
HF_API_TOKEN=your_huggingface_token
DATABASE_URL=your_postgres_connection_string
```

Get a free Groq key at [console.groq.com](https://console.groq.com) and a free Hugging Face token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens). `DATABASE_URL` can point at a local Postgres (see `docker-compose.yml`) or a free [Neon](https://neon.tech) project with the `pgvector` extension enabled.

## Running the App

**Start the backend:**
```bash
source .venv/bin/activate
uvicorn main:app --reload
```

**Start the frontend:**

Open `frontend/index.html` directly in your browser, or serve it locally — it's a static site with no build step.

## Future additions

- **Chat with citations** — the ingestion pipeline and vector store already exist; the next step is a chat UI that answers questions about a video and cites the exact transcript timestamp each answer came from.
- **Video-to-video comparison** — surface similarities and differences across multiple summarized videos using the same embedding space.
- **Resilient live fetching** — revisit YouTube's anti-bot measures as the ecosystem's workarounds mature, so cloud-hosted live fetching can be re-enabled without relying on a paid proxy.
