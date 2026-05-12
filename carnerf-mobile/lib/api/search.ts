import { api } from './client';
import { AIRecommendResult, Listing } from '../types';

export const searchApi = {
  autocomplete: (q: string, limit = 8) =>
    api.get<{ suggestions: string[] }>('/api/search/autocomplete/', { params: { q, limit } }).then((r) => r.data),
  compare: (ids: number[]) =>
    api.get<{ items: Listing[]; tags: Record<string, number> }>('/api/search/compare/', {
      params: { ids: ids.join(',') },
    }).then((r) => r.data),
  aiRecommend: (query: string) =>
    api.post<AIRecommendResult>('/api/search/ai-recommend/', { query }).then((r) => r.data),
  popularKeywords: () =>
    api.get<{ keywords: { text: string; count: number }[] }>('/api/search/popular-keywords/').then((r) => r.data),
};
