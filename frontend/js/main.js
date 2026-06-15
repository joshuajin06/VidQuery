submitBtn.addEventListener("click", handleSubmit);

urlInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") handleSubmit();
});

async function handleSubmit() {
  const url = urlInput.value.trim();

  if (!url) {
    showError("Please enter a YouTube URL.");
    return;
  }

  clearError();
  showLoading();

  try {
    const summary = await summarizeVideo(url);
    showSummary(summary);
  } catch (err) {
    showError(err.message);
  } finally {
    hideLoading();
  }
}
