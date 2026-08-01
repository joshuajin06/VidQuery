from openai import OpenAI

from core.config import GROQ_API_KEY

# Groq exposes an OpenAI-compatible API, so the openai client works with a custom
# base_url. max_retries is high because Groq's free tier allows 12k tokens/minute:
# consecutive map calls get 429s with a retry-after, and the SDK waits it out.
client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1", max_retries=8)

MODEL = "llama-3.3-70b-versatile"

# Transcripts up to this size are summarized in a single call; anything longer
# goes through map-reduce so no part of the transcript is dropped. Sized so one
# chunk (~4 chars/token) plus prompt and output fits Groq's 12k-TPM free tier.
MAX_TRANSCRIPT_CHARS = 36_000
CHUNK_CHARS = 36_000
CHUNK_OVERLAP_CHARS = 500
# Free-tier TPM makes parallel calls pointless (they'd just 429 and retry);
# raise this on a paid tier to cut latency.
MAX_CONCURRENT_REQUESTS = 1

SINGLE_PASS_PROMPT = (
  "You summarize YouTube video transcripts. "
  "Give a concise summary of the video's main points."
)
MAP_PROMPT = (
  "You are summarizing one section of a longer video transcript. "
  "Write a detailed summary of just this section, preserving key points, "
  "names, numbers, decisions, and conclusions."
)
REDUCE_PROMPT = (
  "You are given sequential section summaries of a single video. "
  "Merge them into one coherent, concise summary of the whole video, "
  "in chronological order, without referring to the sections themselves. "
  "Output only the summary itself, with no preamble."
)


def _complete(system_prompt, user_content):
  response = client.chat.completions.create(
    model=MODEL,
    messages=[
      {"role": "system", "content": system_prompt},
      {"role": "user", "content": user_content},
    ],
  )
  return response.choices[0].message.content


def split_into_chunks(text, chunk_chars, overlap_chars):
  """Split text into chunks of at most chunk_chars, breaking on spaces where
  possible, with each chunk repeating the tail of the previous one so meaning
  that straddles a boundary is seen with context by both sides."""
  chunks = []
  start = 0
  while True:
    end = min(start + chunk_chars, len(text))
    if end < len(text):
      space = text.rfind(" ", start, end)
      if space > start:
        end = space
    chunks.append(text[start:end])
    if end >= len(text):
      return chunks
    start = max(end - overlap_chars, start + 1)
    # keep the overlapped start on a word boundary too
    if text[start - 1] != " ":
      space = text.find(" ", start, end)
      if space != -1:
        start = space + 1


def summarize_text(transcript, on_progress=None):
  if len(transcript) <= MAX_TRANSCRIPT_CHARS:
    return _complete(SINGLE_PASS_PROMPT, transcript)

  # Map: summarize each chunk in turn, reporting progress as each one lands.
  # If even the combined summaries are too long, collapse them the same way.
  text = transcript
  while len(text) > MAX_TRANSCRIPT_CHARS:
    chunks = split_into_chunks(text, CHUNK_CHARS, CHUNK_OVERLAP_CHARS)
    labeled = [
      f"Part {i} of {len(chunks)}:\n{chunk}"
      for i, chunk in enumerate(chunks, start=1)
    ]

    part_summaries = list()
    for i, part in enumerate(labeled):
      part_summaries.append(_complete(MAP_PROMPT, part))
      if on_progress: 
        on_progress(i+1, len(labeled))

    combined = "\n\n".join(part_summaries)

    if len(combined) >= len(text):
      # Summarizing failed to shrink the text; truncate rather than loop forever.
      combined = combined[:MAX_TRANSCRIPT_CHARS]
      
    text = combined

  # Reduce: merge the section summaries into the final answer.
  return _complete(REDUCE_PROMPT, text)
