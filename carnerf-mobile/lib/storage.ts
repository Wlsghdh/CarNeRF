import * as SecureStore from 'expo-secure-store';

const JWT_KEY = 'carnerf.jwt';
const USER_KEY = 'carnerf.user';

export const storage = {
  async getToken(): Promise<string | null> {
    return SecureStore.getItemAsync(JWT_KEY);
  },
  async setToken(token: string) {
    await SecureStore.setItemAsync(JWT_KEY, token);
  },
  async clearToken() {
    await SecureStore.deleteItemAsync(JWT_KEY);
  },
  async getUser<T = unknown>(): Promise<T | null> {
    const raw = await SecureStore.getItemAsync(USER_KEY);
    return raw ? (JSON.parse(raw) as T) : null;
  },
  async setUser(user: unknown) {
    await SecureStore.setItemAsync(USER_KEY, JSON.stringify(user));
  },
  async clearUser() {
    await SecureStore.deleteItemAsync(USER_KEY);
  },
};
