from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import YouTubeTranscriptApi

ytt_api = YouTubeTranscriptApi()


def extract_video_id(url):
  params = parse_qs(urlparse(url).query)
  if "v" not in params:
    raise ValueError("Could not find a video ID in the URL.")
  return params["v"][0]


def fetch_transcript(url):
  video_id = extract_video_id(url)
  transcript = ytt_api.fetch(video_id)
  return " ".join(chunk.text for chunk in transcript)


def fetch_transcript_chunks(url, window_seconds=45):
  video_id = extract_video_id(url)
  transcript = ytt_api.fetch(video_id)
  snippets = []
  current_group = []
  snippet_time = 0

  for chunk in transcript:
    snippet_time += chunk.duration
    current_group.append(chunk)
    if snippet_time > window_seconds:
      snippets.append({
        "text": " ".join(s.text for s in current_group),
        "start": current_group[0].start,
        "end": current_group[-1].start + current_group[-1].duration
      })
      current_group = []
      snippet_time = 0

  if current_group:
    snippets.append({
      "text": " ".join(s.text for s in current_group),
      "start": current_group[0].start,
      "end": current_group[-1].start + current_group[-1].duration
    })
  return snippets
