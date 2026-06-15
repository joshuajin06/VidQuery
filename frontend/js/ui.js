const urlInput = document.getElementById("url-input");
const submitBtn = document.getElementById("submit-btn");
const errorMsg = document.getElementById("error-msg");
const resultSection = document.getElementById("result-section");
const summaryOutput = document.getElementById("summary-output");
const loading = document.getElementById("loading");

function showLoading() {
  loading.classList.remove("hidden");
  resultSection.classList.add("hidden");
  errorMsg.classList.add("hidden");
  submitBtn.disabled = true;
}

function hideLoading() {
  loading.classList.add("hidden");
  submitBtn.disabled = false;
}

function showSummary(text) {
  summaryOutput.textContent = text;
  resultSection.classList.remove("hidden");
}

function showError(message) {
  errorMsg.textContent = message;
  errorMsg.classList.remove("hidden");
}

function clearError() {
  errorMsg.textContent = "";
  errorMsg.classList.add("hidden");
}
