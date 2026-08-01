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
  """Fetch a transcript and group it into timestamped chunks for RAG indexing.

  Each raw transcript snippet from youtube-transcript-api has:
    - snippet.text     (str)
    - snippet.start    (float, seconds from video start)
    - snippet.duration (float, seconds)

  TODO: implement this function.
  

  Spec:
    1. Get video_id via extract_video_id(url) and fetch raw snippets via
       ytt_api.fetch(video_id) (same as fetch_transcript above).
    2. Walk the snippets in order, grouping consecutive snippets into a chunk
       until the chunk would span more than `window_seconds` (i.e. current
       snippet's start - chunk's own start > window_seconds). Then close that
       chunk and start a new one.
    3. Each closed chunk should become a dict:
         {
           "text": " ".join of the snippets' .text in that chunk,
           "start": the start time of the chunk's FIRST snippet,
           "end": the start + duration of the chunk's LAST snippet,
         }
    4. Return the list of chunk dicts, in order. Don't forget to flush the
       last in-progress chunk after the loop ends (it won't hit the
       "too long" condition since there's no next snippet to compare against).

  Hints:
    - This is the same "accumulate until threshold, then flush" pattern as
      split_into_chunks in services/summarizer.py, just keyed on time instead
      of character count.
    - Keep window_seconds generous enough that a chunk still has enough
      context to be useful as a standalone retrieval unit (30-60s is a
      reasonable range) but small enough that citations feel precise.
  """

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
