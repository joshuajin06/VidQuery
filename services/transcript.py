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
