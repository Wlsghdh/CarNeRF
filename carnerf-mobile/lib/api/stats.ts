import { api } from './client';

export const statsApi = {
  dashboard: () =>
    api
      .get<{
        total_listings: number;
        active_listings: number;
        sold_this_week: number;
        average_price: number;
        brand_distribution: { brand: string; count: number }[];
      }>('/api/stats/dashboard/')
      .then((r) => r.data),
  priceTrends: (q: { brand?: string; model?: string }) =>
    api
      .get<{ trends: { month: string; price: number }[] }>('/api/stats/price-trends/', { params: q })
      .then((r) => r.data),
};
