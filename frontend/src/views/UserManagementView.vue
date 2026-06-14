<template>
  <div class="section-stack user-management-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>{{ t("users.createTitle") }}</span>
          <el-button type="primary" @click="createUser">{{ t("common.create") }}</el-button>
        </div>
      </template>
      <el-form class="user-create-form" label-position="top" :model="newUser">
        <el-form-item :label="t('common.username')"><el-input v-model="newUser.username" /></el-form-item>
        <el-form-item :label="t('common.password')"><el-input v-model="newUser.password" type="password" show-password /></el-form-item>
        <el-form-item :label="t('common.role')">
          <el-select v-model="newUser.role">
            <el-option :label="t('users.normalUser')" value="user" />
            <el-option :label="t('users.admin')" value="admin" />
          </el-select>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>{{ t("users.listTitle") }}</span>
          <el-button @click="load">{{ t("common.refresh") }}</el-button>
        </div>
      </template>
      <el-table :data="users" v-loading="loading" class="comfortable-table">
        <el-table-column prop="username" :label="t('common.username')" min-width="180" />
        <el-table-column prop="role" :label="t('common.role')" width="150">
          <template #default="{ row }">
            <el-tag :type="row.role === 'super_admin' ? 'danger' : row.role === 'admin' ? 'warning' : 'info'">
              {{ t(`app.role.${row.role}`) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" :label="t('common.status')" width="130">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? t("common.enabled") : t("common.disabled") }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" :label="t('common.createdAt')" min-width="190">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column :label="t('common.actions')" width="320">
          <template #default="{ row }">
            <div class="table-actions">
              <el-button text type="primary" @click="openEdit(row)">{{ t("common.edit") }}</el-button>
              <el-button text type="primary" @click="openReset(row)">{{ t("users.resetPassword") }}</el-button>
              <el-button text type="danger" :disabled="row.role === 'super_admin'" @click="removeUser(row)">{{ t("common.delete") }}</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>

  <el-dialog v-model="editVisible" :title="t('users.editTitle')" width="460px">
    <el-form v-if="editForm" label-position="top">
      <el-form-item :label="t('common.username')">
        <el-input :model-value="editForm.username" disabled />
      </el-form-item>
      <el-form-item :label="t('common.role')">
        <el-select v-model="editForm.role" :disabled="editForm.role === 'super_admin'" class="full-width">
          <el-option :label="t('app.role.super_admin')" value="super_admin" disabled />
          <el-option :label="t('users.normalUser')" value="user" />
          <el-option :label="t('users.admin')" value="admin" />
        </el-select>
      </el-form-item>
      <el-form-item :label="t('common.status')">
        <el-switch v-model="editForm.is_active" :disabled="editForm.role === 'super_admin'" :active-text="t('common.enabled')" :inactive-text="t('common.disabled')" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="editVisible = false">{{ t("common.cancel") }}</el-button>
      <el-button type="primary" :disabled="editForm?.role === 'super_admin'" @click="saveEditedUser">{{ t("common.save") }}</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="resetVisible" :title="t('users.resetPassword')" width="420px">
    <el-input v-model="resetPassword" type="password" show-password :placeholder="t('users.resetPlaceholder')" />
    <template #footer>
      <el-button @click="resetVisible = false">{{ t("common.cancel") }}</el-button>
      <el-button type="primary" @click="resetUserPassword">{{ t("common.save") }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { useI18n } from "vue-i18n";

import { api } from "../api/client";

const { t } = useI18n();
const users = ref([]);
const loading = ref(false);
const editVisible = ref(false);
const editForm = ref(null);
const resetVisible = ref(false);
const resetTarget = ref(null);
const resetPassword = ref("");
const newUser = reactive({ username: "", password: "", role: "user" });

onMounted(load);

async function load() {
  loading.value = true;
  try {
    const { data } = await api.get("/api/admin/users");
    users.value = data.items || [];
  } catch (error) {
    ElMessage.error(error.response?.data?.message || t("users.loadFailed"));
  } finally {
    loading.value = false;
  }
}

async function createUser() {
  try {
    await api.post("/api/admin/users", newUser);
    ElMessage.success(t("users.created"));
    newUser.username = "";
    newUser.password = "";
    newUser.role = "user";
    load();
  } catch (error) {
    ElMessage.error(error.response?.data?.message || t("users.createFailed"));
  }
}

async function updateUser(row) {
  try {
    await api.patch(`/api/admin/users/${row.id}`, { role: row.role, is_active: row.is_active });
    ElMessage.success(t("users.updated"));
  } catch (error) {
    ElMessage.error(error.response?.data?.message || t("users.updateFailed"));
    load();
  }
}

function openEdit(row) {
  editForm.value = { ...row };
  editVisible.value = true;
}

async function saveEditedUser() {
  if (!editForm.value) {
    return;
  }
  await updateUser(editForm.value);
  editVisible.value = false;
}

function openReset(row) {
  resetTarget.value = row;
  resetPassword.value = "";
  resetVisible.value = true;
}

async function resetUserPassword() {
  try {
    await api.post(`/api/admin/users/${resetTarget.value.id}/reset-password`, { password: resetPassword.value });
    ElMessage.success(t("users.resetDone"));
    resetVisible.value = false;
  } catch (error) {
    ElMessage.error(error.response?.data?.message || t("users.resetFailed"));
  }
}

async function removeUser(row) {
  if (row.role === "super_admin") {
    return;
  }
  try {
    await ElMessageBox.confirm(t("users.confirmDelete", { username: row.username }), t("users.confirmTitle"), { type: "warning" });
  } catch {
    return;
  }
  try {
    await api.delete(`/api/admin/users/${row.id}`);
    users.value = users.value.filter((item) => item.id !== row.id);
    ElMessage.success(t("users.deleted"));
  } catch (error) {
    ElMessage.error(error.response?.data?.message || t("users.deleteFailed"));
  }
}

function formatDate(value) {
  return value ? new Date(value).toLocaleString() : "-";
}
</script>
