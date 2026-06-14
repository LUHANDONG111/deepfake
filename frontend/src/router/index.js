import { createRouter, createWebHistory } from "vue-router";

import { useAuthStore } from "../stores/auth";
import LoginView from "../views/LoginView.vue";
import DetectionView from "../views/DetectionView.vue";
import HistoryView from "../views/HistoryView.vue";
import ResultView from "../views/ResultView.vue";
import UserManagementView from "../views/UserManagementView.vue";
import TaskManagementView from "../views/TaskManagementView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", name: "login", component: LoginView, meta: { public: true } },
    { path: "/", redirect: "/detect" },
    { path: "/detect", name: "detect", component: DetectionView },
    { path: "/history", name: "history", component: HistoryView },
    { path: "/tasks/:id", name: "result", component: ResultView },
    { path: "/admin/users", name: "users", component: UserManagementView, meta: { admin: true } },
    { path: "/admin/tasks", name: "adminTasks", component: TaskManagementView, meta: { admin: true } },
  ],
});

router.beforeEach(async (to) => {
  const auth = useAuthStore();
  if (to.meta.public) {
    return true;
  }
  if (!auth.isAuthenticated) {
    return { name: "login" };
  }
  try {
    await auth.loadMe();
  } catch {
    return { name: "login" };
  }
  if (to.meta.admin && !auth.isAdmin) {
    return { name: "detect" };
  }
  return true;
});

export default router;
