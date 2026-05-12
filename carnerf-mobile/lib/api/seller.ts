import { api } from './client';

export const sellerApi = {
  status: () =>
    api.get<{ is_verified: boolean; pending: boolean }>('/api/seller/status/').then((r) => r.data),
  upgrade: (body: { name: string; phone: string; vehicle_registration: string; region: string }) =>
    api.post('/api/seller/upgrade/', body).then((r) => r.data),
};
