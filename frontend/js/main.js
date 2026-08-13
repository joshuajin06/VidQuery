submitBtn.addEventListener("click", handleSubmit);
submitTextBtn.addEventListener("click", handleTextSubmit);

urlInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") handleSubmit();
});

modeUrlBtn.addEventListener("click", showUrlMode);
modeTextBtn.addEventListener("click", showTextMode);

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


async function handleTextSubmit() {
  const transcript = transcriptInput.value.trim();

  if (!transcript) {
    showError("Please paste a transcript first.");
    return;
  }

  clearError();
  showLoading();
  progressMsg.textContent = "Summarizing...";

  try {
    const jobId = await startSummarizeText(transcript);
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


// --- examples dropdown: load a cached real transcript, or download it ---

examplesToggle.addEventListener("click", (e) => {
  e.stopPropagation();
  toggleExamplesMenu();
});

document.addEventListener("click", (e) => {
  if (!examplesMenu.contains(e.target) && e.target !== examplesToggle) {
    closeExamplesMenu();
  }
});

function loadExample(example) {
  showTextMode();
  transcriptInput.value = example.transcript;
  clearError();
  closeExamplesMenu();
  transcriptInput.focus();
}

function renderExamplesMenu() {
  examplesMenu.innerHTML = "";

  EXAMPLE_TRANSCRIPTS.forEach((example) => {
    const item = document.createElement("div");
    item.className = "example-item";

    const info = document.createElement("div");
    info.className = "example-info";

    const title = document.createElement("span");
    title.className = "example-title";
    title.textContent = example.title;

    const meta = document.createElement("span");
    meta.className = "example-meta";
    meta.textContent = example.meta;

    info.appendChild(title);
    info.appendChild(meta);

    const actions = document.createElement("div");
    actions.className = "example-actions";

    const loadBtn = document.createElement("button");
    loadBtn.className = "example-load";
    loadBtn.type = "button";
    loadBtn.textContent = "Load";
    loadBtn.addEventListener("click", () => loadExample(example));

    const downloadLink = document.createElement("a");
    downloadLink.className = "example-download";
    downloadLink.textContent = ".txt";
    downloadLink.href = URL.createObjectURL(
      new Blob([example.transcript], { type: "text/plain" })
    );
    downloadLink.download = `${example.id}.txt`;

    actions.appendChild(loadBtn);
    actions.appendChild(downloadLink);

    item.appendChild(info);
    item.appendChild(actions);
    examplesMenu.appendChild(item);
  });
}

renderExamplesMenu();
