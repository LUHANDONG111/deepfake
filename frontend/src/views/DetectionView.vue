<template>
  <div class="page-grid">
    <el-card shadow="never" class="tool-card">
      <template #header>{{ t("detect.newTask") }}</template>
      <el-form label-position="top">
        <el-form-item :label="t('detect.video')">
          <input ref="fileInput" class="hidden-input" type="file" accept="video/mp4" @change="selectFile" />
          <button
            class="drive-upload"
            :class="{ 'is-dragging': dragging, 'has-file': file }"
            type="button"
            @click="openFilePicker"
            @dragenter.prevent="dragging = true"
            @dragover.prevent="dragging = true"
            @dragleave.prevent="dragging = false"
            @drop.prevent="handleDrop"
          >
            <span class="upload-icon">
              <UploadCloud :size="26" :stroke-width="2.2" />
            </span>
            <span class="upload-copy">
              <span class="upload-main">{{ file ? file.name : t("detect.uploadMain") }}</span>
              <span class="upload-sub">{{ file ? fileSummary : t("detect.uploadSub") }}</span>
            </span>
            <span class="upload-action">
              <FileVideo2 :size="16" />
              {{ t("detect.chooseFile") }}
            </span>
          </button>
        </el-form-item>
        <el-form-item :label="t('detect.threshold', { value: form.threshold.toFixed(2) })">
          <el-slider v-model="form.threshold" :min="0" :max="1" :step="0.01" />
        </el-form-item>
        <el-form-item :label="t('detect.window', { value: form.window_size })">
          <el-slider v-model="form.window_size" :min="1" :max="30" :step="1" />
        </el-form-item>
        <el-form-item :label="t('detect.skipRate', { value: form.skip_rate })">
          <el-slider v-model="form.skip_rate" :min="1" :max="20" :step="1" />
        </el-form-item>
        <el-button type="primary" size="large" class="full-width" :loading="uploading" @click="upload">{{ t("detect.start") }}</el-button>
      </el-form>
    </el-card>

    <el-card shadow="never" class="tool-card">
      <template #header>{{ t("detect.processing") }}</template>
      <el-progress :percentage="progress" :status="progressStatus" />
      <p class="status-text">{{ statusText }}</p>
      <el-button v-if="taskId" @click="loadResult(taskId)">{{ t("detect.refreshResult") }}</el-button>
    </el-card>
  </div>

</template>

<script setup>
import { computed, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { FileVideo2, UploadCloud } from "@lucide/vue";
import { useI18n } from "vue-i18n";

import { api } from "../api/client";

const { locale, t } = useI18n();
const router = useRouter();
const file = ref(null);
const fileInput = ref(null);
const dragging = ref(false);
const uploading = ref(false);
const taskId = ref("");
const progress = ref(0);
const statusText = ref(t("detect.waiting"));
const form = reactive({ threshold: 0.5, window_size: 5, skip_rate: 2 });

const progressStatus = computed(() => (progress.value === 100 ? "success" : undefined));
const fileSummary = computed(() => {
  if (!file.value) {
    return "";
  }
  const size = file.value.size / 1024 / 1024;
  return `${size.toFixed(size >= 10 ? 0 : 1)} MB · ${file.value.type || "video/mp4"}`;
});

watch(locale, () => {
  if (!taskId.value) {
    statusText.value = t("detect.waiting");
  } else if (progress.value === 100) {
    statusText.value = t("detect.completed");
  }
});

function openFilePicker() {
  fileInput.value?.click();
}

function selectFile(event) {
  setFile(event.target.files?.[0]);
}

function handleDrop(event) {
  dragging.value = false;
  setFile(event.dataTransfer.files?.[0]);
}

function setFile(nextFile) {
  if (!nextFile) {
    file.value = null;
    return;
  }
  if (!nextFile.name.toLowerCase().endsWith(".mp4")) {
    ElMessage.warning(t("detect.selectMp4"));
    return;
  }
  file.value = nextFile;
}

async function upload() {
  if (!file.value) {
    ElMessage.warning(t("detect.selectMp4"));
    return;
  }
  uploading.value = true;
  const payload = new FormData();
  payload.append("file", file.value);
  payload.append("threshold", form.threshold);
  payload.append("window_size", form.window_size);
  payload.append("skip_rate", form.skip_rate);
  try {
    const { data } = await api.post("/api/upload", payload);
    taskId.value = data.task_id;
    statusText.value = t("detect.queued");
    poll(data.task_id);
  } catch (error) {
    ElMessage.error(error.response?.data?.message || t("detect.uploadFailed"));
  } finally {
    uploading.value = false;
  }
}

async function poll(id) {
  const { data } = await api.get(`/api/status/${id}`);
  progress.value = Number(data.progress) || 0;
  statusText.value = data.status === "PENDING" ? t("detect.queued") : t("detect.analyzing");
  if (data.status === "SUCCESS") {
    await loadResult(id);
    return;
  }
  if (data.status === "FAILED") {
    statusText.value = data.error || t("detect.failed");
    return;
  }
  window.setTimeout(() => poll(id), 1000);
}

async function loadResult(id) {
  try {
    const { data } = await api.get(`/api/result/${id}`);
    progress.value = 100;
    statusText.value = t("detect.completed");
    router.push(`/tasks/${data.task_id}`);
  } catch (error) {
    ElMessage.error(error.response?.data?.message || error.response?.data?.error || t("detect.resultUnavailable"));
  }
}
</script>
