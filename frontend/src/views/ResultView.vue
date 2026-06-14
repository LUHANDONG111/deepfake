<template>
  <div v-if="task" class="section-stack result-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>{{ task.id }}</span>
          <el-tag>{{ task.status }}</el-tag>
        </div>
      </template>
      <div class="result-layout" v-if="task.result">
        <FaceVideoOverlay :src="assetUrl(task.result.video_url)" :timeline="task.result.timeline || []" />
        <div :class="task.result.final_verdict === 'FAKE' ? 'detail-verdict fake' : 'detail-verdict real'">
          <p class="muted">{{ t("common.finalVerdict") }}</p>
          <strong>{{ task.result.final_verdict }}</strong>
          <span>{{ t("common.score") }}: {{ Number(task.result.final_score).toFixed(4) }}</span>
          <div class="action-row">
            <el-button :href="assetUrl(task.result.video_url)" tag="a" target="_blank">{{ t("common.openVideo") }}</el-button>
            <el-button type="primary" :href="assetUrl(task.result.report_url)" tag="a" target="_blank">{{ t("common.downloadCsv") }}</el-button>
          </div>
        </div>
      </div>
      <el-descriptions v-else :column="2" border>
        <el-descriptions-item :label="t('common.status')">{{ task.status }}</el-descriptions-item>
        <el-descriptions-item :label="t('common.progress')">{{ task.progress }}%</el-descriptions-item>
        <el-descriptions-item :label="t('common.error')">{{ task.error_message || "-" }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <template v-if="task.result">
      <div class="metric-grid">
        <el-card v-for="metric in metrics" :key="metric.label" shadow="never">
          <p class="muted">{{ metric.label }}</p>
          <strong class="metric-value">{{ metric.value }}</strong>
        </el-card>
      </div>

      <el-card shadow="never">
        <template #header>{{ t("result.timeline") }}</template>
        <svg v-if="timelinePath" class="timeline" viewBox="0 0 720 280" role="img">
          <line x1="44" x2="692" :y1="thresholdY" :y2="thresholdY" class="threshold-line" />
          <path :d="rawPath" class="raw-line" />
          <path :d="timelinePath" class="smooth-line" />
          <circle v-for="point in points" :key="point.key" :cx="point.x" :cy="point.y" r="3" :class="point.verdict === 'FAKE' ? 'dot-fake' : 'dot-real'" />
        </svg>
        <el-empty v-else :description="t('result.noTimeline')" />
      </el-card>

      <el-card shadow="never">
        <template #header>{{ t("result.riskSegments") }}</template>
        <el-table :data="task.result.risk_segments || []" size="small">
          <el-table-column prop="frame_index" :label="t('detect.frame')" width="90" />
          <el-table-column prop="timestamp" :label="t('detect.time')" width="110" />
          <el-table-column prop="raw_score" label="Raw" />
          <el-table-column prop="smoothed_score" label="Smooth" />
          <el-table-column prop="verdict" :label="t('common.verdict')" />
        </el-table>
      </el-card>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import { useI18n } from "vue-i18n";

import { api, assetUrl } from "../api/client";
import FaceVideoOverlay from "../components/FaceVideoOverlay.vue";

const route = useRoute();
const { t } = useI18n();
const task = ref(null);

const metrics = computed(() => {
  const summary = task.value?.result?.summary || {};
  return [
    [t("detect.metrics.sampledFrames"), summary.sampled_frames ?? 0],
    [t("detect.metrics.faceFrames"), summary.face_frames ?? 0],
    [t("detect.metrics.fakeRatio"), formatPercent(summary.fake_ratio)],
    [t("detect.metrics.peakRisk"), formatNumber(summary.max_smoothed_score, 4)],
  ].map(([label, value]) => ({ label, value }));
});

const chart = computed(() => buildChart(task.value?.result?.timeline || [], task.value?.result?.config?.threshold ?? 0.5));
const timelinePath = computed(() => chart.value.smoothPath);
const rawPath = computed(() => chart.value.rawPath);
const points = computed(() => chart.value.points);
const thresholdY = computed(() => chart.value.thresholdY);

onMounted(async () => {
  try {
    const { data } = await api.get(`/api/tasks/${route.params.id}`);
    task.value = data.task;
  } catch (error) {
    ElMessage.error(error.response?.data?.message || t("result.loadFailed"));
  }
});

function buildChart(rows, threshold) {
  if (!rows.length) {
    return { smoothPath: "", rawPath: "", points: [], thresholdY: 140 };
  }
  const padding = { top: 18, right: 28, bottom: 34, left: 44 };
  const width = 720;
  const height = 280;
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const minTime = Number(rows[0].timestamp) || 0;
  const maxTime = Number(rows[rows.length - 1].timestamp) || minTime + 1;
  const range = Math.max(0.001, maxTime - minTime);
  const x = (time) => padding.left + (((Number(time) || 0) - minTime) / range) * plotWidth;
  const y = (score) => padding.top + (1 - Math.max(0, Math.min(1, Number(score) || 0))) * plotHeight;
  const path = (field) => rows.map((row, index) => `${index === 0 ? "M" : "L"} ${x(row.timestamp).toFixed(2)} ${y(row[field]).toFixed(2)}`).join(" ");
  return {
    smoothPath: path("smoothed_score"),
    rawPath: path("raw_score"),
    thresholdY: y(threshold),
    points: rows.map((row, index) => ({ key: index, x: x(row.timestamp), y: y(row.smoothed_score), verdict: row.verdict })),
  };
}

function formatNumber(value, digits = 2) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(digits) : "-";
}

function formatPercent(value) {
  const number = Number(value);
  return Number.isFinite(number) ? `${Math.round(number * 100)}%` : "0%";
}
</script>
