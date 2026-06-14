<template>
  <main class="login-page">
    <section class="login-panel">
      <div class="login-copy">
        <span class="brand-mark">D</span>
        <h1>Deepfake Detection Console</h1>
        <p>{{ t("auth.loginCopy") }}</p>
      </div>
      <el-card class="login-card" shadow="never">
        <h2>{{ setupRequired ? t("auth.setupTitle") : t("auth.loginTitle") }}</h2>
        <p v-if="setupRequired" class="muted setup-note">{{ t("auth.setupNote") }}</p>
        <el-form label-position="top" @submit.prevent="submit">
          <el-form-item :label="t('common.username')">
            <el-input v-model="form.username" autocomplete="username" />
          </el-form-item>
          <el-form-item :label="t('common.password')">
            <el-input v-model="form.password" type="password" autocomplete="current-password" show-password />
          </el-form-item>
          <el-button type="primary" size="large" class="full-width" :loading="loading" @click="submit">
            {{ setupRequired ? t("auth.setupSubmit") : t("auth.login") }}
          </el-button>
        </el-form>
      </el-card>
    </section>
  </main>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { useI18n } from "vue-i18n";

import { useAuthStore } from "../stores/auth";
import { api } from "../api/client";

const router = useRouter();
const auth = useAuthStore();
const { t } = useI18n();
const loading = ref(false);
const setupRequired = ref(false);
const form = reactive({ username: "", password: "" });

onMounted(loadSetupStatus);

async function loadSetupStatus() {
  try {
    const { data } = await api.get("/api/auth/setup-status");
    setupRequired.value = Boolean(data.setup_required);
  } catch {
    setupRequired.value = false;
  }
}

async function submit() {
  loading.value = true;
  try {
    if (setupRequired.value) {
      await api.post("/api/auth/setup-admin", form);
    }
    await auth.login(form);
    router.push("/detect");
  } catch (error) {
    ElMessage.error(error.response?.data?.message || (setupRequired.value ? t("auth.setupFailed") : t("auth.loginFailed")));
  } finally {
    loading.value = false;
  }
}
</script>
