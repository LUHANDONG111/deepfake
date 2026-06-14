<template>
  <el-card shadow="never" class="history-page">
    <template #header>
      <div class="card-header">
        <span>{{ t("history.title") }}</span>
        <div class="action-row">
          <el-button type="primary" @click="router.push('/detect')">{{ t("history.createTask") }}</el-button>
          <el-button @click="load">{{ t("common.refresh") }}</el-button>
        </div>
      </div>
    </template>
    <el-table :data="tasks" v-loading="loading" class="comfortable-table history-table">
      <el-table-column prop="id" :label="t('common.taskId')" min-width="360" show-overflow-tooltip />
      <el-table-column prop="status" :label="t('common.status')" width="116">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="final_verdict" :label="t('common.verdict')" width="104">
        <template #default="{ row }">{{ row.final_verdict || "-" }}</template>
      </el-table-column>
      <el-table-column prop="final_score" :label="t('common.score')" width="100">
        <template #default="{ row }">{{ formatScore(row.final_score) }}</template>
      </el-table-column>
      <el-table-column :label="t('history.config')" width="154">
        <template #default="{ row }">T {{ row.threshold }} / W {{ row.window_size }} / S {{ row.skip_rate }}</template>
      </el-table-column>
      <el-table-column prop="created_at" :label="t('common.createdAt')" width="190">
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column :label="t('common.actions')" width="246">
        <template #default="{ row }">
          <div class="table-actions">
            <el-button text type="primary" @click="openDetail(row)">{{ t("common.details") }}</el-button>
            <el-button text type="primary" @click="openEdit(row)">{{ t("common.edit") }}</el-button>
            <el-button text type="danger" @click="remove(row)">{{ t("common.delete") }}</el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <el-drawer v-model="detailVisible" :title="t('history.detailTitle')" size="520px">
    <div v-if="detailTask" class="detail-drawer">
      <el-descriptions :column="1" border>
        <el-descriptions-item :label="t('common.taskId')">{{ detailTask.id }}</el-descriptions-item>
        <el-descriptions-item :label="t('common.status')">{{ detailTask.status }}</el-descriptions-item>
        <el-descriptions-item :label="t('common.progress')">{{ detailTask.progress }}%</el-descriptions-item>
        <el-descriptions-item :label="t('common.verdict')">{{ detailTask.final_verdict || "-" }}</el-descriptions-item>
        <el-descriptions-item :label="t('common.score')">{{ formatScore(detailTask.final_score) }}</el-descriptions-item>
        <el-descriptions-item :label="t('history.config')">threshold {{ detailTask.threshold }} / window {{ detailTask.window_size }} / skip {{ detailTask.skip_rate }}</el-descriptions-item>
        <el-descriptions-item v-if="detailTask.remark" :label="t('common.remark')">{{ detailTask.remark }}</el-descriptions-item>
        <el-descriptions-item :label="t('common.error')">{{ detailTask.error_message || "-" }}</el-descriptions-item>
        <el-descriptions-item :label="t('common.createdAt')">{{ formatDate(detailTask.created_at) }}</el-descriptions-item>
      </el-descriptions>

      <el-card v-if="detailTask.result" shadow="never" class="drawer-card">
        <template #header>{{ t("result.summary") }}</template>
        <div class="drawer-summary-grid">
          <span>{{ t("detect.metrics.sampledFrames") }}<strong>{{ detailTask.result.summary?.sampled_frames ?? 0 }}</strong></span>
          <span>{{ t("detect.metrics.faceFrames") }}<strong>{{ detailTask.result.summary?.face_frames ?? 0 }}</strong></span>
          <span>{{ t("detect.metrics.fakeRatio") }}<strong>{{ formatPercent(detailTask.result.summary?.fake_ratio) }}</strong></span>
          <span>{{ t("detect.metrics.peakRisk") }}<strong>{{ formatScore(detailTask.result.summary?.max_smoothed_score) }}</strong></span>
        </div>
      </el-card>

      <div class="drawer-actions">
        <el-button @click="openEdit(detailTask)">{{ t("common.edit") }}</el-button>
        <el-button v-if="detailTask.status === 'SUCCESS'" type="primary" @click="router.push(`/tasks/${detailTask.id}`)">{{ t("detect.viewResult") }}</el-button>
      </div>
    </div>
  </el-drawer>

  <el-dialog v-model="editVisible" :title="t('history.editTitle')" width="520px">
    <el-form label-position="top">
      <el-form-item :label="t('common.taskId')">
        <el-input :model-value="editForm.id" disabled />
      </el-form-item>
      <el-form-item :label="t('common.remark')">
        <el-input v-model="editForm.remark" type="textarea" :rows="4" maxlength="500" show-word-limit :placeholder="t('history.remarkPlaceholder')" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="editVisible = false">{{ t("common.cancel") }}</el-button>
      <el-button type="primary" @click="saveRemark">{{ t("common.save") }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { useI18n } from "vue-i18n";

import { api } from "../api/client";

const { t } = useI18n();
const router = useRouter();
const tasks = ref([]);
const loading = ref(false);
const detailVisible = ref(false);
const detailTask = ref(null);
const editVisible = ref(false);
const editForm = reactive({ id: "", remark: "" });

onMounted(load);

async function load() {
  loading.value = true;
  try {
    const { data } = await api.get("/api/tasks");
    tasks.value = data.items || [];
  } catch (error) {
    ElMessage.error(error.response?.data?.message || t("history.loadFailed"));
  } finally {
    loading.value = false;
  }
}

async function openDetail(row) {
  try {
    const { data } = await api.get(`/api/tasks/${row.id}`);
    detailTask.value = data.task;
    detailVisible.value = true;
  } catch (error) {
    ElMessage.error(error.response?.data?.message || t("result.loadFailed"));
  }
}

function openEdit(row) {
  editForm.id = row.id;
  editForm.remark = row.remark || "";
  editVisible.value = true;
}

async function saveRemark() {
  try {
    const { data } = await api.patch(`/api/tasks/${editForm.id}`, { remark: editForm.remark });
    const index = tasks.value.findIndex((item) => item.id === editForm.id);
    if (index >= 0) {
      tasks.value[index] = data.task;
    }
    if (detailTask.value?.id === editForm.id) {
      detailTask.value = { ...detailTask.value, remark: data.task.remark };
    }
    ElMessage.success(t("history.updated"));
    editVisible.value = false;
  } catch (error) {
    ElMessage.error(error.response?.data?.message || t("history.updateFailed"));
  }
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(t("history.confirmDelete", { id: row.id }), t("history.confirmTitle"), { type: "warning" });
  } catch {
    return;
  }
  try {
    await api.delete(`/api/tasks/${row.id}`);
    tasks.value = tasks.value.filter((item) => item.id !== row.id);
    if (detailTask.value?.id === row.id) {
      detailVisible.value = false;
      detailTask.value = null;
    }
    ElMessage.success(t("history.deleted"));
  } catch (error) {
    ElMessage.error(error.response?.data?.message || t("history.deleteFailed"));
  }
}

function formatScore(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(4) : "-";
}

function formatPercent(value) {
  const number = Number(value);
  return Number.isFinite(number) ? `${Math.round(number * 100)}%` : "0%";
}

function formatDate(value) {
  return value ? new Date(value).toLocaleString() : "-";
}

function statusType(status) {
  if (status === "SUCCESS") {
    return "success";
  }
  if (status === "FAILED") {
    return "danger";
  }
  return "warning";
}
</script>
