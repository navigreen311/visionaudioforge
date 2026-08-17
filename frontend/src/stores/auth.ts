import { create } from "zustand";
import api from "@/lib/api";
import {
  clearSession,
  persistSession,
  persistWorkspaceId,
  readAccessToken,
  readWorkspaceId,
} from "@/lib/session";

interface User {
  id: string;
  email: string;
  role: string;
  workspace_id?: string | null;
}

interface AuthState {
  user: User | null;
  token: string | null;
  /** The tenant this session acts in. Comes from the server, never a default. */
  workspaceId: string | null;
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
  token: readAccessToken(),
  workspaceId: readWorkspaceId(),
  isAuthenticated: false,
  isLoading: true,

  setAuth: (user, token) => {
    persistSession(token, user.workspace_id ?? null);
    set({
      user,
      token,
      workspaceId: readWorkspaceId(),
      isAuthenticated: true,
      isLoading: false,
    });
  },

  login: async (email, password) => {
    const res = await api.post("/api/auth/login", { email, password });
    const { user, access_token, refresh_token } = res.data;
    persistSession(access_token, user?.workspace_id ?? null, refresh_token);
    set({
      user,
      token: access_token,
      workspaceId: readWorkspaceId(),
      isAuthenticated: true,
      isLoading: false,
    });
  },

  register: async (email, password, workspace) => {
    const res = await api.post("/api/auth/register", {
      email,
      password,
      workspace_name: workspace,
    });
    const { user, access_token, refresh_token } = res.data;
    persistSession(access_token, user?.workspace_id ?? null, refresh_token);
    set({
      user,
      token: access_token,
      workspaceId: readWorkspaceId(),
      isAuthenticated: true,
      isLoading: false,
    });
  },

  logout: () => {
    clearSession();
    set({
      user: null,
      token: null,
      workspaceId: null,
      isAuthenticated: false,
      isLoading: false,
    });
  },

  setUser: (user) => set({ user }),

  initialize: async () => {
    if (typeof window === "undefined") {
      set({ isLoading: false });
      return;
    }
    const token = readAccessToken();
    if (!token) {
      // No token means no session — and no workspace. Drop any stale
      // workspace left behind by a previous user on this machine.
      clearSession();
      set({
        user: null,
        token: null,
        workspaceId: null,
        isAuthenticated: false,
        isLoading: false,
      });
      return;
    }
    try {
      const res = await api.get("/api/auth/me");
      // Re-stamp the session: /api/auth/me is the authority on which workspace
      // this token belongs to, and it also refreshes the cookie the edge
      // middleware reads.
      persistSession(token, res.data?.workspace_id ?? null);
      persistWorkspaceId(res.data?.workspace_id ?? null);
      set({
        user: res.data,
        token,
        workspaceId: readWorkspaceId(),
        isAuthenticated: true,
        isLoading: false,
      });
    } catch {
      clearSession();
      set({
        user: null,
        token: null,
        workspaceId: null,
        isAuthenticated: false,
        isLoading: false,
      });
    }
  },
}));
