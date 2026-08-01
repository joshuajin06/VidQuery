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


async function pollUntilDone(jobId) {
  return new Promise((resolve, reject) => {
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

        // TODO: this is the "still working" case (any status other than
        // done/failed). If job.status === "summarizing_chunk" and
        // job.progress_total is set, update some UI element with e.g.
        // `Summarizing part ${job.progress_current} of ${job.progress_total}...`
        // ui.js doesn't have an element for this yet -- you'll need to add
        // one (id, e.g. "progress-msg") to index.html, grab it in ui.js the
        // same way loading/errorMsg/etc are grabbed, and write a small
        // showProgress(text) helper alongside showError/showSummary.
        if(job.status === "summarizing_chunk" && job.progress_total != null) {
          showProgress(`Summarizing part ${job.progress_current} of ${job.progress_total}`);
        }
      } catch(err) {
        clearInterval(id);
        reject(err);
      }
    }, POLL_INTERVAL_MS);
  })
}
