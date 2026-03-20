import { create } from "zustand";
import api from "@/lib/api";

interface User {
  id: string;
  email: string;
  role: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setAuth: (user: User, token: string) => void;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, workspace: string) => Promise<void>;
  logout: () => void;
  setUser: (user: User) => void;
  initialize: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token:
    typeof window !== "undefined"
      ? localStorage.getItem("access_token")
      : null,
  isAuthenticated: false,
  isLoading: true,

  setAuth: (user, token) => {
    if (typeof window !== "undefined") {
      localStorage.setItem("access_token", token);
    }
    set({ user, token, isAuthenticated: true, isLoading: false });
  },

  login: async (email, password) => {
    const res = await api.post("/api/auth/login", { email, password });
    const { user, access_token } = res.data;
    if (typeof window !== "undefined") {
      localStorage.setItem("access_token", access_token);
    }
    set({ user, token: access_token, isAuthenticated: true, isLoading: false });
  },

  register: async (email, password, workspace) => {
    const res = await api.post("/api/auth/register", {
      email,
      password,
      workspace_name: workspace,
    });
    const { user, access_token } = res.data;
    if (typeof window !== "undefined") {
      localStorage.setItem("access_token", access_token);
    }
    set({ user, token: access_token, isAuthenticated: true, isLoading: false });
  },

  logout: () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("access_token");
    }
    set({ user: null, token: null, isAuthenticated: false, isLoading: false });
  },

  setUser: (user) => set({ user }),

  initialize: async () => {
    if (typeof window === "undefined") {
      set({ isLoading: false });
      return;
    }
    const token = localStorage.getItem("access_token");
    if (!token) {
      set({ isLoading: false });
      return;
    }
    try {
      const res = await api.get("/api/auth/me");
      set({
        user: res.data,
        token,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch {
      localStorage.removeItem("access_token");
      set({ user: null, token: null, isAuthenticated: false, isLoading: false });
    }
  },
}));
