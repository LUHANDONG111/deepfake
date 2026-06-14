const setupView = document.querySelector("#setupView");
const processingView = document.querySelector("#processingView");
const summaryView = document.querySelector("#summaryView");
const uploadForm = document.querySelector("#uploadForm");
const fileInput = document.querySelector("#fileInput");
const fileName = document.querySelector("#fileName");
const dropZone = document.querySelector("#dropZone");
const setupError = document.querySelector("#setupError");
const submitButton = document.querySelector("#submitButton");
const progressBar = document.querySelector("#progressBar");
const progressLabel = document.querySelector("#progressLabel");
const processingStatus = document.querySelector("#processingStatus");
const threshold = document.querySelector("#threshold");
const windowSize = document.querySelector("#windowSize");
const skipRate = document.querySelector("#skipRate");
const resultVideo = document.querySelector("#resultVideo");
const faceOverlay = document.querySelector("#faceOverlay");
const configSummary = document.querySelector("#configSummary");
const summaryCards = document.querySelector("#summaryCards");
const timelineChart = document.querySelector("#timelineChart");
const riskSegments = document.querySelector("#riskSegments");
let overlayTimeline = [];

function bindRange(input, label, formatter = (value) => value) {
  const update = () => {
    label.textContent = formatter(input.value);
  };
  input.addEventListener("input", update);
  update();
}

bindRange(threshold, document.querySelector("#thresholdValue"), (value) => Number(value).toFixed(2));
bindRange(windowSize, document.querySelector("#windowValue"));
bindRange(skipRate, document.querySelector("#skipValue"));

fileInput.addEventListener("change", () => {
  fileName.textContent = fileInput.files[0]?.name || "未选择文件";
});

["dragenter", "dragover"].forEach((eventName) => {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.add("drop-active");
  });
});

["dragleave", "drop"].forEach((eventName) => {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.remove("drop-active");
  });
});

dropZone.addEventListener("drop", (event) => {
  if (event.dataTransfer.files.length > 0) {
    fileInput.files = event.dataTransfer.files;
    fileName.textContent = fileInput.files[0].name;
  }
});

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideError();
  if (!fileInput.files.length) {
    showError("请选择一个 MP4 视频。");
    return;
  }

  submitButton.disabled = true;
  submitButton.textContent = "Uploading...";

  try {
    const formData = new FormData(uploadForm);
    const response = await fetch("/api/upload", { method: "POST", body: formData });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.message || "Upload failed");
    }
    showProcessing();
    pollStatus(payload.task_id);
  } catch (error) {
    showError(error.message);
    submitButton.disabled = false;
    submitButton.textContent = "Start Detection";
  }
});

document.querySelector("#newTaskButton").addEventListener("click", () => {
  summaryView.classList.add("hidden");
  setupView.classList.remove("hidden");
  resultVideo.removeAttribute("src");
  resultVideo.load();
  overlayTimeline = [];
  clearFaceOverlay();
  submitButton.disabled = false;
  submitButton.textContent = "Start Detection";
  progressBar.style.width = "0%";
  progressLabel.textContent = "0%";
});

["loadedmetadata", "timeupdate", "seeked", "play", "pause"].forEach((eventName) => {
  resultVideo.addEventListener(eventName, drawFaceOverlay);
});

window.addEventListener("resize", drawFaceOverlay);

function showProcessing() {
  setupView.classList.add("hidden");
  processingView.classList.remove("hidden");
}

async function pollStatus(taskId) {
  const response = await fetch(`/api/status/${taskId}`);
  const payload = await response.json();

  if (!response.ok) {
    showFailure(payload.message || "Task not found");
    return;
  }

  updateProgress(payload.progress, payload.status);

  if (payload.status === "SUCCESS") {
    await showResult(taskId);
    return;
  }
  if (payload.status === "FAILED") {
    showFailure(payload.error || "Detection failed");
    return;
  }

  window.setTimeout(() => pollStatus(taskId), 1000);
}

function updateProgress(progress, status) {
  const value = Math.max(0, Math.min(100, progress || 0));
  progressBar.style.width = `${value}%`;
  progressLabel.textContent = `${value}%`;
  processingStatus.textContent = status === "PENDING" ? "Task queued." : "Analyzing sampled frames.";
}

async function showResult(taskId) {
  const response = await fetch(`/api/result/${taskId}`);
  const payload = await response.json();
  if (!response.ok) {
    showFailure(payload.error || "Unable to fetch result");
    return;
  }

  processingView.classList.add("hidden");
  summaryView.classList.remove("hidden");
  const verdictPanel = document.querySelector("#verdictPanel");
  const verdictText = document.querySelector("#verdictText");
  verdictText.textContent = payload.final_verdict;
  document.querySelector("#scoreText").textContent = `Score: ${Number(payload.final_score).toFixed(4)}`;
  document.querySelector("#videoLink").href = payload.video_url;
  document.querySelector("#reportLink").href = payload.report_url;
  overlayTimeline = payload.timeline || [];
  clearFaceOverlay();
  resultVideo.src = payload.video_url;
  verdictPanel.className =
    payload.final_verdict === "FAKE"
      ? "rounded-lg border border-red-400 bg-red-500/10 p-5"
      : "rounded-lg border border-emerald-400 bg-emerald-500/10 p-5";
  renderConfig(payload.config || {});
  renderSummaryCards(payload.summary || {});
  renderTimeline(overlayTimeline, payload.config?.threshold ?? Number(threshold.value));
  renderRiskSegments(payload.risk_segments || []);
  drawFaceOverlay();
}

function drawFaceOverlay() {
  const context = faceOverlay.getContext("2d");
  const rect = faceOverlay.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  const canvasWidth = Math.max(1, Math.round(rect.width * dpr));
  const canvasHeight = Math.max(1, Math.round(rect.height * dpr));

  if (faceOverlay.width !== canvasWidth || faceOverlay.height !== canvasHeight) {
    faceOverlay.width = canvasWidth;
    faceOverlay.height = canvasHeight;
  }

  context.clearRect(0, 0, faceOverlay.width, faceOverlay.height);

  if (!overlayTimeline.length || !resultVideo.videoWidth || !resultVideo.videoHeight) {
    return;
  }

  const row = findNearestTimelineRow(resultVideo.currentTime);
  if (!row?.boxes?.length) {
    return;
  }

  const fit = getVideoFit(rect.width, rect.height, resultVideo.videoWidth, resultVideo.videoHeight);
  context.save();
  context.scale(dpr, dpr);
  context.lineWidth = 2;
  context.strokeStyle = row.verdict === "FAKE" ? "#f87171" : "#22d3ee";
  context.shadowColor = "rgba(0, 0, 0, 0.75)";
  context.shadowBlur = 4;

  row.boxes.forEach((box) => {
    const [x1, y1, x2, y2] = box.map(Number);
    if ([x1, y1, x2, y2].some((value) => !Number.isFinite(value))) {
      return;
    }

    const x = fit.offsetX + x1 * fit.scale;
    const y = fit.offsetY + y1 * fit.scale;
    const width = Math.max(0, (x2 - x1) * fit.scale);
    const height = Math.max(0, (y2 - y1) * fit.scale);
    context.strokeRect(x, y, width, height);
  });

  context.restore();
}

function clearFaceOverlay() {
  const context = faceOverlay.getContext("2d");
  context.clearRect(0, 0, faceOverlay.width, faceOverlay.height);
}

function findNearestTimelineRow(currentTime) {
  let nearest = overlayTimeline[0];
  let nearestDistance = Math.abs((Number(nearest.timestamp) || 0) - currentTime);

  for (const row of overlayTimeline) {
    const distance = Math.abs((Number(row.timestamp) || 0) - currentTime);
    if (distance < nearestDistance) {
      nearest = row;
      nearestDistance = distance;
    }
  }

  return nearest;
}

function getVideoFit(containerWidth, containerHeight, videoWidth, videoHeight) {
  const scale = Math.min(containerWidth / videoWidth, containerHeight / videoHeight);
  const width = videoWidth * scale;
  const height = videoHeight * scale;
  return {
    scale,
    offsetX: (containerWidth - width) / 2,
    offsetY: (containerHeight - height) / 2,
  };
}

function renderConfig(config) {
  const items = [
    ["Threshold", formatNumber(config.threshold, 2)],
    ["Window", config.window_size ?? "—"],
    ["Skip", config.skip_rate ?? "—"],
  ];
  configSummary.innerHTML = items
    .map(
      ([label, value]) => `
        <div class="rounded border border-zinc-800 bg-zinc-950/50 p-3">
          <p class="text-xs text-zinc-500">${label}</p>
          <p class="mt-1 font-semibold text-cyan-100">${value}</p>
        </div>
      `,
    )
    .join("");
}

function renderSummaryCards(summary) {
  const cards = [
    ["Sampled frames", summary.sampled_frames ?? 0],
    ["Face frames", summary.face_frames ?? 0],
    ["FAKE ratio", formatPercent(summary.fake_ratio)],
    ["Peak risk", formatNumber(summary.max_smoothed_score, 4)],
    ["FAKE frames", summary.fake_frames ?? 0],
    ["REAL frames", summary.real_frames ?? 0],
    ["Max raw", formatNumber(summary.max_raw_score, 4)],
    ["Risk time", formatTime(summary.highest_risk_time)],
  ];
  summaryCards.innerHTML = cards
    .map(
      ([label, value]) => `
        <div class="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          <p class="text-xs uppercase text-zinc-500">${label}</p>
          <p class="mt-2 text-2xl font-semibold text-zinc-100">${value}</p>
        </div>
      `,
    )
    .join("");
}

function renderRiskSegments(segments) {
  if (!segments.length) {
    riskSegments.innerHTML = `<p class="rounded border border-zinc-800 bg-zinc-950/50 p-4 text-sm text-zinc-400">No frame-level scores available.</p>`;
    return;
  }

  riskSegments.innerHTML = segments
    .map(
      (segment, index) => `
        <button class="risk-segment w-full rounded border border-zinc-800 bg-zinc-950/50 p-4 text-left transition hover:border-cyan-400" type="button" data-time="${Number(segment.timestamp) || 0}">
          <div class="flex items-center justify-between gap-3">
            <span class="text-sm font-medium">#${index + 1} · ${formatTime(segment.timestamp)}</span>
            <span class="${segment.verdict === "FAKE" ? "text-red-300" : "text-emerald-300"} text-xs font-semibold">${segment.verdict}</span>
          </div>
          <div class="mt-3 grid grid-cols-3 gap-2 text-xs text-zinc-400">
            <span>Frame ${segment.frame_index}</span>
            <span>Raw ${formatNumber(segment.raw_score, 3)}</span>
            <span>Smooth ${formatNumber(segment.smoothed_score, 3)}</span>
          </div>
        </button>
      `,
    )
    .join("");

  riskSegments.querySelectorAll(".risk-segment").forEach((button) => {
    button.addEventListener("click", () => {
      resultVideo.currentTime = Number(button.dataset.time) || 0;
      resultVideo.play().catch(() => {});
    });
  });
}

function renderTimeline(timeline, thresholdValue) {
  if (!timeline.length) {
    timelineChart.innerHTML = `<div class="flex min-h-64 items-center justify-center text-sm text-zinc-400">No frame-level timeline available.</div>`;
    return;
  }

  const width = 720;
  const height = 280;
  const padding = { top: 18, right: 28, bottom: 34, left: 44 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const minTime = Number(timeline[0].timestamp) || 0;
  const maxTime = Number(timeline[timeline.length - 1].timestamp) || minTime + 1;
  const timeRange = Math.max(0.001, maxTime - minTime);
  const thresholdLine = Math.max(0, Math.min(1, Number(thresholdValue) || 0));

  const x = (time) => padding.left + (((Number(time) || 0) - minTime) / timeRange) * plotWidth;
  const y = (score) => padding.top + (1 - Math.max(0, Math.min(1, Number(score) || 0))) * plotHeight;
  const path = (field) => timeline.map((row, index) => `${index === 0 ? "M" : "L"} ${x(row.timestamp).toFixed(2)} ${y(row[field]).toFixed(2)}`).join(" ");
  const thresholdY = y(thresholdLine).toFixed(2);
  const tickValues = [0, 0.25, 0.5, 0.75, 1];

  timelineChart.innerHTML = `
    <svg class="h-full min-h-64 w-full" viewBox="0 0 ${width} ${height}" role="img" aria-label="Score timeline">
      <rect x="0" y="0" width="${width}" height="${height}" fill="transparent"></rect>
      ${tickValues
        .map((tick) => {
          const tickY = y(tick).toFixed(2);
          return `
            <line x1="${padding.left}" x2="${width - padding.right}" y1="${tickY}" y2="${tickY}" stroke="rgba(63,63,70,0.65)" stroke-width="1"></line>
            <text x="10" y="${Number(tickY) + 4}" fill="#a1a1aa" font-size="11">${tick.toFixed(2)}</text>
          `;
        })
        .join("")}
      <line x1="${padding.left}" x2="${width - padding.right}" y1="${thresholdY}" y2="${thresholdY}" stroke="#fbbf24" stroke-width="1.5" stroke-dasharray="6 5"></line>
      <path d="${path("raw_score")}" fill="none" stroke="#f0abfc" stroke-width="2" opacity="0.75"></path>
      <path d="${path("smoothed_score")}" fill="none" stroke="#67e8f9" stroke-width="3"></path>
      ${timeline
        .map((row) => {
          const cx = x(row.timestamp).toFixed(2);
          const cy = y(row.smoothed_score).toFixed(2);
          const color = row.verdict === "FAKE" ? "#f87171" : "#34d399";
          return `<circle cx="${cx}" cy="${cy}" r="3" fill="${color}"><title>${formatTime(row.timestamp)} · ${formatNumber(row.smoothed_score, 4)} · ${row.verdict}</title></circle>`;
        })
        .join("")}
      <text x="${padding.left}" y="${height - 8}" fill="#a1a1aa" font-size="11">${formatTime(minTime)}</text>
      <text x="${width - padding.right - 42}" y="${height - 8}" fill="#a1a1aa" font-size="11">${formatTime(maxTime)}</text>
    </svg>
  `;
}

function formatNumber(value, digits = 2) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(digits) : "—";
}

function formatPercent(value) {
  const number = Number(value);
  return Number.isFinite(number) ? `${Math.round(number * 100)}%` : "0%";
}

function formatTime(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) {
    return "—";
  }
  return `${number.toFixed(2)}s`;
}

function showFailure(message) {
  processingView.classList.add("hidden");
  setupView.classList.remove("hidden");
  showError(message);
  submitButton.disabled = false;
  submitButton.textContent = "Start Detection";
}

function showError(message) {
  setupError.textContent = message;
  setupError.classList.remove("hidden");
}

function hideError() {
  setupError.textContent = "";
  setupError.classList.add("hidden");
}
