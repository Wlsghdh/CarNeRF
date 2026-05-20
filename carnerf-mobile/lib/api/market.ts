import { api } from './client';
import { MarketPrice, PriceDistribution } from '../types';

export const marketApi = {
  price: (vehicleId: number) =>
    api.get<MarketPrice>(`/api/market/price/${vehicleId}/`).then((r) => r.data),
  average: (q: { brand: string; model: string; year_min?: number; year_max?: number }) =>
    api.get<{ average_price: number; sample_size: number }>('/api/market/average/', { params: q }).then((r) => r.data),
  distribution: (vehicleId: number) =>
    api.get<PriceDistribution>(`/api/market/distribution/${vehicleId}`).then((r) => r.data),
};
