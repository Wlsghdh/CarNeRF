import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

const JWT_KEY = 'carnerf.jwt';
const USER_KEY = 'carnerf.user';

const webStore = {
  async getItemAsync(key: string): Promise<string | null> {
    if (typeof window === 'undefined') return null;
    return window.localStorage.getItem(key);
  },
  async setItemAsync(key: string, value: string): Promise<void> {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem(key, value);
  },
  async deleteItemAsync(key: string): Promise<void> {
    if (typeof window === 'undefined') return;
    window.localStorage.removeItem(key);
  },
};

const store = Platform.OS === 'web' ? webStore : SecureStore;

export const storage = {
  async getToken(): Promise<string | null> {
    return store.getItemAsync(JWT_KEY);
  },
  async setToken(token: string) {
    await store.setItemAsync(JWT_KEY, token);
  },
  async clearToken() {
    await store.deleteItemAsync(JWT_KEY);
  },
  async getUser<T = unknown>(): Promise<T | null> {
    const raw = await store.getItemAsync(USER_KEY);
    return raw ? (JSON.parse(raw) as T) : null;
  },
  async setUser(user: unknown) {
    await store.setItemAsync(USER_KEY, JSON.stringify(user));
  },
  async clearUser() {
    await store.deleteItemAsync(USER_KEY);
  },
};
