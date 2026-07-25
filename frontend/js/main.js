submitBtn.addEventListener("click", handleSubmit);

urlInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") handleSubmit();
});

const POLL_INTERVAL_MS = 2000;

async function handleSubmit() {
  const url = urlInput.value.trim();

  const url_pattern = /^(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=[A-Za-z\d\-_]{11}$/i;

  if (!url) {
    showError("Please enter a YouTube URL.");
    return;
  }

  if (!url_pattern.test(url)) {
    showError("Please enter a valid YouTube URL.");
    return;
  }

  clearError();
  showLoading();

  try {
    const jobId = await startSummarize(url);
    await pollUntilDone(jobId);
  } catch (err) {
    showError(err.message);
    hideLoading();
  }
}

// SPEC — pollUntilDone(jobId)
// Returns a Promise that resolves once the job reaches a terminal state.
// Behavior to implement:
//   1. every POLL_INTERVAL_MS, call pollJob(jobId)
//   2. if job.status === "done":
//        - stop polling
//        - hideLoading()
//        - showSummary(job.summary)
//        - resolve the promise
//   3. if job.status === "failed":
//        - stop polling
//        - hideLoading()
//        - showError(job.error)
//        - resolve the promise (this is a *handled* outcome, not a bug --
//          don't reject/throw, or handleSubmit's catch block would show a
//          confusing double error)
//   4. any other status ("pending" / "fetching_transcript" / "summarizing"
//      / "summarizing_chunk") just means "not done yet" -- do nothing this
//      tick, the next interval will check again
//   5. if pollJob() itself throws (network error, unknown job_id) -- stop
//      polling and let the error propagate out so handleSubmit's catch
//      block handles it the same as any other failure
//
// Syntax hints:
//   - wrap the whole thing in `return new Promise((resolve) => { ... })`
//     so handleSubmit's `await pollUntilDone(jobId)` waits for a terminal
//     state before moving on
//   - setInterval(callback, ms) returns an id; save it so you can
//     clearInterval(id) once you hit a terminal state or an error
//   - the interval callback itself needs to be `async` if it awaits
//     pollJob() inside -- but setInterval doesn't await its callback, so
//     wrap the polling logic in a try/catch *inside* the callback, don't
//     rely on the outer function's try/catch to see errors from inside it
async function pollUntilDone(jobId) {
  return new Promise((resolve) => {
    const id = setInterval(async () => {
      try {
        const job = await pollJob(jobId);

        if(job.status === "done") {
          clearInterval(id);
          hideLoading();
          showSummary(job.summary);
          resolve("Summary retrieved");
        }

        if(job.status === "failed") {
          clearInterval(id);
          hideLoading();
          showError(job.error);
          resolve("Summary retrieval failed");
        }
      } catch(err) {
        clearInterval(id);
        reject(err);
      }
    }, POLL_INTERVAL_MS);
  })
}
