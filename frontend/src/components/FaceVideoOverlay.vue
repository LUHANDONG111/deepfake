<template>
  <div class="video-overlay-frame">
    <video
      ref="videoRef"
      class="result-video"
      :src="src"
      controls
      preload="metadata"
      @loadedmetadata="draw"
      @timeupdate="draw"
      @seeked="draw"
      @play="draw"
      @pause="draw"
    ></video>
    <canvas ref="canvasRef" class="face-overlay"></canvas>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = defineProps({
  src: {
    type: String,
    required: true,
  },
  timeline: {
    type: Array,
    default: () => [],
  },
});

const videoRef = ref(null);
const canvasRef = ref(null);

watch(
  () => [props.src, props.timeline],
  async () => {
    await nextTick();
    draw();
  },
  { deep: true },
);

onMounted(() => {
  window.addEventListener("resize", draw);
  draw();
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", draw);
});

function draw() {
  const video = videoRef.value;
  const canvas = canvasRef.value;
  if (!video || !canvas) {
    return;
  }

  const context = canvas.getContext("2d");
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  const canvasWidth = Math.max(1, Math.round(rect.width * dpr));
  const canvasHeight = Math.max(1, Math.round(rect.height * dpr));

  if (canvas.width !== canvasWidth || canvas.height !== canvasHeight) {
    canvas.width = canvasWidth;
    canvas.height = canvasHeight;
  }

  context.clearRect(0, 0, canvas.width, canvas.height);

  if (!props.timeline.length || !video.videoWidth || !video.videoHeight) {
    return;
  }

  const row = findNearestTimelineRow(video.currentTime);
  if (!row?.boxes?.length) {
    return;
  }

  const fit = getVideoFit(rect.width, rect.height, video.videoWidth, video.videoHeight);
  context.save();
  context.scale(dpr, dpr);
  context.lineWidth = 2.5;
  context.strokeStyle = row.verdict === "FAKE" ? "#ff5d68" : "#6ff3f0";
  context.shadowColor = row.verdict === "FAKE" ? "rgba(255, 93, 104, 0.45)" : "rgba(111, 243, 240, 0.42)";
  context.shadowBlur = 8;

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

    context.save();
    context.shadowBlur = 0;
    context.fillStyle = row.verdict === "FAKE" ? "rgba(255, 93, 104, 0.12)" : "rgba(111, 243, 240, 0.1)";
    context.fillRect(x, y, width, height);
    context.restore();
  });

  context.restore();
}

function findNearestTimelineRow(currentTime) {
  let nearest = props.timeline[0];
  let nearestDistance = Math.abs((Number(nearest.timestamp) || 0) - currentTime);

  for (const row of props.timeline) {
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
</script>
