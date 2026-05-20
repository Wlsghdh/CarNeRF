import { api } from './client';

export const uploadApi = {
  images: async (files: { uri: string; name: string; type: string }[]) => {
    const fd = new FormData();
    files.forEach((f) => {
      // @ts-ignore — RN FormData accepts file objects
      fd.append('files', f);
    });
    const r = await api.post<{ urls: string[]; thumbnails: string[] }>('/api/upload/images/', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000,
    });
    return r.data;
  },
};
