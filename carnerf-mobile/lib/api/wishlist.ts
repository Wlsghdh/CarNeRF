import { api } from './client';
import { Wishlist } from '../types';

export const wishlistApi = {
  list: () => api.get<Wishlist[]>('/api/wishlist/').then((r) => r.data),
  toggle: (vehicleId: number) =>
    api.post<{ wishlisted: boolean }>(`/api/wishlist/toggle/${vehicleId}/`).then((r) => r.data),
  check: (vehicleId: number) =>
    api.get<{ wishlisted: boolean }>(`/api/wishlist/check/${vehicleId}/`).then((r) => r.data),
  count: (vehicleId: number) =>
    api.get<{ count: number }>(`/api/wishlist/count/${vehicleId}/`).then((r) => r.data),
};
