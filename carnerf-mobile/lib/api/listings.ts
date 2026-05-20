import { api } from './client';
import { Listing } from '../types';

export type Sort = 'newest' | 'price_asc' | 'price_desc' | 'mileage' | 'region_match';

export interface ListingQuery {
  brand?: string;
  fuel_type?: string;
  region?: string;
  price_min?: number;
  price_max?: number;
  year_min?: number;
  year_max?: number;
  search?: string;
  sort?: Sort;
  page?: number;
  limit?: number;
}

export const listingsApi = {
  list: (q: ListingQuery = {}) =>
    api.get<Listing[]>('/api/listings/', { params: q }).then((r) => r.data),
  count: (q: ListingQuery = {}) =>
    api.get<{ count: number; total_pages: number }>('/api/listings/count/', { params: q }).then((r) => r.data),
  get: (id: number) => api.get<Listing>(`/api/listings/${id}/`).then((r) => r.data),
  create: (body: Record<string, any>) =>
    api.post<Listing>('/api/listings/', body).then((r) => r.data),
};
