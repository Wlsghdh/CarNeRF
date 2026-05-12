import { api } from './client';
import { PipelineStatus, Quality } from '../types';

export const pipelineApi = {
  start: async (form: { video: { uri: string; name: string; type: string }; vehicle_id?: number; quality: Quality }) => {
    const fd = new FormData();
    // @ts-ignore — RN FormData accepts file objects
    fd.append('video', form.video);
    if (form.vehicle_id != null) fd.append('vehicle_id', String(form.vehicle_id));
    fd.append('quality', form.quality);
    const r = await api.post<{ job_id: string }>('/api/pipeline/start/', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000,
    });
    return r.data;
  },
  status: (jobId: string) =>
    api.get<PipelineStatus>(`/api/pipeline/status/${jobId}/`).then((r) => r.data),
};
