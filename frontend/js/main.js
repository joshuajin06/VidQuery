submitBtn.addEventListener("click", handleSubmit);

urlInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") handleSubmit();
});

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
    const summary = await summarizeVideo(url);
    showSummary(summary);
  } catch (err) {
    showError(err.message);
  } finally {
    hideLoading();
  }
}
