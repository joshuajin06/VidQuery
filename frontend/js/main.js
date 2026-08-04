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
