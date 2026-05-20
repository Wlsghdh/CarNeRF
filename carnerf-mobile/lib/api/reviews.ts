import { api } from './client';
import { Rating, UserReview } from '../types';

export const reviewsApi = {
  forVehicle: (vehicleId: number, page = 1, limit = 10) =>
    api
      .get<{ items: UserReview[]; total: number }>(`/api/reviews/vehicle/${vehicleId}/`, {
        params: { page, limit },
      })
      .then((r) => r.data),
  create: (body: { vehicle_id: number; rating: Rating; content: string; review_type: 'buyer' | 'seller' }) =>
    api.post<UserReview>('/api/reviews/', body).then((r) => r.data),
  modelSummary: (brand: string, model: string) =>
    api
      .get<{ average_rating: number; total_reviews: number; summary: string }>(
        `/api/reviews/model-summary/${brand}/${model}/`,
      )
      .then((r) => r.data),
};
