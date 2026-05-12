import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

import { storage } from '../storage';

const baseURL = process.env.EXPO_PUBLIC_API_URL ?? 'http://223.195.111.31:5199';

export const api = axios.create({
  baseURL,
  timeout: 15000,
});

api.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
  const token = await storage.getToken();
  if (token) {
    config.headers.set?.('Authorization', `Bearer ${token}`);
    (config.headers as any).Authorization = `Bearer ${token}`;
  }
  if (config.url && !config.url.includes('?') && !/\/$/.test(config.url) && config.method?.toLowerCase() === 'get') {
    config.url = config.url + '/';
  }
  return config;
});

let onUnauthorized: (() => void) | null = null;
export const setUnauthorizedHandler = (fn: () => void) => {
  onUnauthorized = fn;
};

api.interceptors.response.use(
  (r) => r,
  async (err: AxiosError) => {
    if (err.response?.status === 401) {
      await storage.clearToken();
      await storage.clearUser();
      onUnauthorized?.();
    }
    throw err;
  },
);

export type ApiError = AxiosError<{ detail?: string; message?: string }>;
export const extractError = (err: unknown): string => {
  const e = err as ApiError;
  return e?.response?.data?.detail || e?.response?.data?.message || e?.message || '알 수 없는 오류';
};
