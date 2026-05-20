import { useQuery } from '@tanstack/react-query';

import { listingsApi } from '../api/listings';
import { Listing } from '../types';
import { hashSeed, mulberry32, weekKey } from '../utils/week';

export interface SpecialListing extends Listing {
  discount_rate: number;
  original_price: number;
  special_price: number;
  week_label: string;
}

const PICK_COUNT = 8;

export function useWeeklySpecials() {
  return useQuery({
    queryKey: ['weekly-specials', weekKey()],
    staleTime: 1000 * 60 * 60,
    queryFn: async (): Promise<SpecialListing[]> => {
      const pool = await listingsApi.list({ sort: 'newest', limit: 60 });
      if (!pool.length) return [];

      const wk = weekKey();
      const rand = mulberry32(hashSeed(wk));

      // 결정론적 Fisher-Yates 셔플
      const arr = [...pool];
      for (let i = arr.length - 1; i > 0; i--) {
        const j = Math.floor(rand() * (i + 1));
        [arr[i], arr[j]] = [arr[j], arr[i]];
      }

      const picked = arr.slice(0, PICK_COUNT);

      return picked.map((l) => {
        const discount = 0.1 + rand() * 0.15;
        const discountRate = Math.round(discount * 100) / 100;
        const special_price = l.price;
        const original_price = Math.round(special_price / (1 - discountRate));
        return {
          ...l,
          discount_rate: discountRate,
          original_price,
          special_price,
          week_label: wk,
        };
      });
    },
  });
}
