<template>
  <el-card shadow="never">
    <template #header>
      <div class="card-header">
        <span>{{ t("tasks.globalTitle") }}</span>
        <el-button @click="load">{{ t("common.refresh") }}</el-button>
      </div>
    </template>
    <el-form :inline="true" class="filter-row">
      <el-form-item :label="t('common.status')">
        <el-select v-model="filters.status" clearable style="width: 140px">
          <el-option label="PENDING" value="PENDING" />
          <el-option label="PROCESSING" value="PROCESSING" />
          <el-option label="SUCCESS" value="SUCCESS" />
          <el-option label="FAILED" value="FAILED" />
        </el-select>
      </el-form-item>
      <el-form-item :label="t('common.verdict')">
        <el-select v-model="filters.verdict" clearable style="width: 120px">
          <el-option label="REAL" value="REAL" />
          <el-option label="FAKE" value="FAKE" />
        </el-select>
      </el-form-item>
      <el-form-item><el-button type="primary" @click="load">{{ t("common.filter") }}</el-button></el-form-item>
    </el-form>

    <el-table :data="tasks" v-loading="loading">
      <el-table-column prop="id" :label="t('common.taskId')" min-width="260" />
      <el-table-column prop="username" :label="t('common.user')" width="140" />
      <el-table-column prop="status" :label="t('common.status')" width="120" />
      <el-table-column prop="final_verdict" :label="t('common.verdict')" width="100" />
      <el-table-column prop="created_at" :label="t('common.createdAt')" width="210">
        <template #default="{ row }">{{ row.created_at ? new Date(row.created_at).toLocaleString() : "-" }}</template>
      </el-table-column>
      <el-table-column :label="t('common.actions')" width="180">
        <template #default="{ row }">
          <el-button text type="primary" @click="$router.push(`/tasks/${row.id}`)">{{ t("common.details") }}</el-button>
          <el-button text type="danger" @click="remove(row)">{{ t("common.delete") }}</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { useI18n } from "vue-i18n";

import { api } from "../api/client";

const { t } = useI18n();
const tasks = ref([]);
const loading = ref(false);
const filters = reactive({ status: "", verdict: "" });

onMounted(load);

async function load() {
  loading.value = true;
  try {
    const { data } = await api.get("/api/tasks", { params: filters });
    tasks.value = data.items || [];
  } catch (error) {
    ElMessage.error(error.response?.data?.message || t("tasks.loadFailed"));
  } finally {
    loading.value = false;
  }
}

async function remove(row) {
  await ElMessageBox.confirm(t("tasks.confirmDelete", { id: row.id }), t("tasks.confirmTitle"), { type: "warning" });
  try {
    await api.delete(`/api/admin/tasks/${row.id}`);
    ElMessage.success(t("tasks.deleted"));
    load();
  } catch (error) {
    ElMessage.error(error.response?.data?.message || t("tasks.deleteFailed"));
  }
}
</script>
