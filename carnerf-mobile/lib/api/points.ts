import { api } from './client';
import { PointTransaction } from '../types';

export const pointsApi = {
  balance: () => api.get<{ balance: number }>('/api/points/balance/').then((r) => r.data),
  history: (page = 1) =>
    api.get<{ items: PointTransaction[]; total: number }>('/api/points/history/', { params: { page } }).then((r) => r.data),
  charge: (amount: number) =>
    api.post<PointTransaction>('/api/points/charge/', { amount }).then((r) => r.data),
  use: (body: { amount: number; usage_type: 'ai_usage' | 'premium_listing'; description: string }) =>
    api.post<PointTransaction>('/api/points/use/', body).then((r) => r.data),
};
