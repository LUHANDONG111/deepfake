import { defineStore } from "pinia";
import { api } from "../api/client";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    token: localStorage.getItem("auth_token") || "",
    user: JSON.parse(localStorage.getItem("auth_user") || "null"),
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.token && state.user),
    isAdmin: (state) => ["admin", "super_admin"].includes(state.user?.role),
  },
  actions: {
    async login(credentials) {
      const { data } = await api.post("/api/auth/login", credentials);
      this.token = data.token;
      this.user = data.user;
      localStorage.setItem("auth_token", data.token);
      localStorage.setItem("auth_user", JSON.stringify(data.user));
    },
    async loadMe() {
      if (!this.token) {
        return;
      }
      try {
        const { data } = await api.get("/api/auth/me");
        this.user = data.user;
        localStorage.setItem("auth_user", JSON.stringify(data.user));
      } catch (error) {
        this.logout();
        throw error;
      }
    },
    logout() {
      this.token = "";
      this.user = null;
      localStorage.removeItem("auth_token");
      localStorage.removeItem("auth_user");
    },
  },
});
