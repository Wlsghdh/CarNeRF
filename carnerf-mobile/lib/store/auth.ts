import { create } from 'zustand';

import { authApi, LoginResponse } from '../api/auth';
import { storage } from '../storage';
import { User } from '../types';

interface AuthState {
  user: User | null;
  hydrated: boolean;
  hydrate: () => Promise<void>;
  login: (email: string, password: string) => Promise<LoginResponse>;
  register: (body: { email: string; username: string; password: string; phone?: string }) => Promise<User>;
  logout: () => Promise<void>;
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  hydrated: false,
  hydrate: async () => {
    const user = await storage.getUser<User>();
    set({ user, hydrated: true });
  },
  login: async (email, password) => {
    const res = await authApi.login({ email, password });
    await storage.setToken(res.access_token);
    await storage.setUser(res.user);
    set({ user: res.user });
    return res;
  },
  register: async (body) => {
    const user = await authApi.register(body);
    return user;
  },
  logout: async () => {
    try {
      await authApi.logout();
    } catch {}
    await storage.clearToken();
    await storage.clearUser();
    set({ user: null });
  },
}));
