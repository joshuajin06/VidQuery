const urlInput = document.getElementById("url-input");
const submitBtn = document.getElementById("submit-btn");
const errorMsg = document.getElementById("error-msg");
const resultSection = document.getElementById("result-section");
const summaryOutput = document.getElementById("summary-output");
const loading = document.getElementById("loading");
const progressMsg = document.getElementById("show-progress");

// --- paste-URL vs paste-transcript mode toggle ---
const modeUrlBtn = document.getElementById("mode-url-btn");
const modeTextBtn = document.getElementById("mode-text-btn");
const urlInputGroup = document.getElementById("url-input-group");
const textInputGroup = document.getElementById("text-input-group");
const transcriptInput = document.getElementById("transcript-input");
const submitTextBtn = document.getElementById("submit-text-btn");

function showUrlMode() {
  modeUrlBtn.classList.add("active");
  modeTextBtn.classList.remove("active");
  urlInputGroup.classList.remove("hidden");
  textInputGroup.classList.add("hidden");
}

function showTextMode() {
  modeTextBtn.classList.add("active");
  modeUrlBtn.classList.remove("active");
  textInputGroup.classList.remove("hidden");
  urlInputGroup.classList.add("hidden");
}

// --- examples dropdown ---
const examplesToggle = document.getElementById("examples-toggle");
const examplesMenu = document.getElementById("examples-menu");

function toggleExamplesMenu() {
  examplesMenu.classList.toggle("hidden");
}

function closeExamplesMenu() {
  examplesMenu.classList.add("hidden");
}

function showLoading() {
  loading.classList.remove("hidden");
  resultSection.classList.add("hidden");
  errorMsg.classList.add("hidden");
  submitBtn.disabled = true;
  progressMsg.textContent = "Fetching and summarizing...";
}

function hideLoading() {
  loading.classList.add("hidden");
  submitBtn.disabled = false;
}

function showSummary(text) {
  summaryOutput.textContent = text;
  resultSection.classList.remove("hidden");
}

function showProgress(text) {
  progressMsg.textContent = text;
}

function showError(message) {
  errorMsg.textContent = message;
  errorMsg.classList.remove("hidden");
}

function clearError() {
  errorMsg.textContent = "";
  errorMsg.classList.add("hidden");
}
