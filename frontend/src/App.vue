<template>
  <el-config-provider :locale="elementLocale">
    <router-view v-if="$route.meta.public" />
    <el-container v-else class="app-shell">
      <el-aside width="236px" class="sidebar">
        <div class="brand">
          <span class="brand-mark">D</span>
          <div>
            <strong>{{ t("app.brand") }}</strong>
            <small>{{ t("app.subtitle") }}</small>
          </div>
        </div>
        <el-menu router :default-active="$route.path" class="side-menu">
          <el-menu-item index="/detect"><el-icon><VideoCamera /></el-icon><span>{{ t("nav.detect") }}</span></el-menu-item>
          <el-menu-item index="/history"><el-icon><Clock /></el-icon><span>{{ t("nav.history") }}</span></el-menu-item>
          <template v-if="auth.isAdmin">
            <el-menu-item index="/admin/users"><el-icon><User /></el-icon><span>{{ t("nav.users") }}</span></el-menu-item>
            <el-menu-item index="/admin/tasks"><el-icon><Grid /></el-icon><span>{{ t("nav.adminTasks") }}</span></el-menu-item>
          </template>
        </el-menu>
      </el-aside>

      <el-container>
        <el-header class="topbar">
          <div>
            <h1>{{ title }}</h1>
            <p>{{ subtitle }}</p>
          </div>
          <div class="account">
            <el-select v-model="localeModel" class="language-select" :aria-label="t('app.language')" @change="setLocale">
              <el-option v-for="item in supportedLocales" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
            <el-tag :type="auth.isAdmin ? 'danger' : 'info'">{{ t(`app.role.${auth.user?.role || "user"}`) }}</el-tag>
            <span>{{ auth.user?.username }}</span>
            <el-button :icon="Lock" text @click="passwordVisible = true">{{ t("auth.changePassword") }}</el-button>
            <el-button :icon="SwitchButton" text @click="logout">{{ t("auth.logout") }}</el-button>
          </div>
        </el-header>
        <el-main class="content">
          <router-view v-slot="{ Component, route }">
            <transition name="page-shift" mode="out-in" appear>
              <div :key="route.fullPath" class="page-view">
                <component :is="Component" />
              </div>
            </transition>
          </router-view>
        </el-main>
      </el-container>
    </el-container>

    <el-dialog v-model="passwordVisible" :title="t('auth.changePassword')" width="420px">
      <el-form label-position="top" @submit.prevent>
        <el-form-item :label="t('auth.oldPassword')">
          <el-input v-model="passwordForm.old_password" type="password" show-password />
        </el-form-item>
        <el-form-item :label="t('auth.newPassword')">
          <el-input v-model="passwordForm.new_password" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordVisible = false">{{ t("common.cancel") }}</el-button>
        <el-button type="primary" :loading="savingPassword" @click="changePassword">{{ t("common.save") }}</el-button>
      </template>
    </el-dialog>
  </el-config-provider>
</template>

<script setup>
import { computed, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import en from "element-plus/es/locale/lang/en";
import zhCn from "element-plus/es/locale/lang/zh-cn";
import { Clock, Grid, Lock, SwitchButton, User, VideoCamera } from "@element-plus/icons-vue";
import { useI18n } from "vue-i18n";

import { api } from "./api/client";
import { setLocale as applyLocale, supportedLocales } from "./i18n";
import { useAuthStore } from "./stores/auth";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const { locale, t, tm } = useI18n();
const passwordVisible = ref(false);
const savingPassword = ref(false);
const passwordForm = reactive({ old_password: "", new_password: "" });
const localeModel = ref(locale.value);

const elementLocale = computed(() => (locale.value === "zh" ? zhCn : en));
const pageKey = computed(() => `pages.${route.name || "workspace"}`);
const titlePair = computed(() => tm(pageKey.value) || tm("pages.workspace"));

const title = computed(() => titlePair.value[0]);
const subtitle = computed(() => titlePair.value[1]);

function setLocale(nextLocale) {
  applyLocale(nextLocale);
  localeModel.value = nextLocale;
}

async function changePassword() {
  savingPassword.value = true;
  try {
    await api.post("/api/auth/change-password", passwordForm);
    ElMessage.success(t("auth.passwordUpdated"));
    passwordVisible.value = false;
    passwordForm.old_password = "";
    passwordForm.new_password = "";
  } catch (error) {
    ElMessage.error(error.response?.data?.message || t("auth.passwordUpdateFailed"));
  } finally {
    savingPassword.value = false;
  }
}

function logout() {
  auth.logout();
  router.push("/login");
}
</script>
