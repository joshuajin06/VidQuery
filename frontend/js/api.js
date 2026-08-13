const API_BASE = "https://vidquery-qr6z.onrender.com";

// SPEC — startSummarize(url)
// - POSTs { url } to /summarize
// - resolves to the job_id string on success (status 202)
// - throws an Error with a useful message if the server rejects the URL
//   (422 from bad request shape, 400/404 would show up later via polling,
//   not here -- POST only ever creates the job, it can't fail on "bad video")
async function startSummarize(url) {
  // TODO: same fetch() shape as the old summarizeVideo() had, but:
  //   - read data.job_id instead of data.summary
  //   - return that job_id
  

  const response = await fetch(`${API_BASE}/summarize`, {
    method: "POST",
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify( { url } )
  });

  const data = await response.json();

  if(!response.ok) {
    throw new Error(data.detail || "something went wrong")
  }

  return data.job_id
}

// startSummarizeText(transcript)
// - POSTs { transcript } to /summarize/text
// - resolves to the job_id string on success (status 202)
// - throws an Error with a useful message if the server rejects the transcript (422)
async function startSummarizeText(transcript) {
  const response = await fetch(`${API_BASE}/summarize/text`, {
    method: "POST",
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ transcript })
  });

  const data = await response.json();

  if(!response.ok) {
    throw new Error(data.detail || "something went wrong")
  }

  return data.job_id
}

// SPEC — pollJob(jobId)
// - GETs /summarize/{jobId}
// - resolves to the parsed JSON body: { status, progress_current,
//   progress_total, summary, error }
// - throws an Error if the job_id is unknown (404) or the request fails
async function pollJob(jobId) {
  // TODO: fetch(`${API_BASE}/summarize/${jobId}`), parse JSON, throw on
  // !response.ok (same pattern as startSummarize), otherwise return the
  // parsed body as-is -- the caller decides what to do with each status.
  const response = await fetch(`${API_BASE}/summarize/${jobId}`);

  const data = await response.json();

  if(!response.ok) {
    throw new Error(data.detail || "something went wrong")
  }

  return data
}
