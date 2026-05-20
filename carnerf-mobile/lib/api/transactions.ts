import { api } from './client';
import { TransactionHistory } from '../types';

export const transactionsApi = {
  forVehicle: (id: number) =>
    api.get<TransactionHistory[]>(`/api/transactions/vehicle/${id}/`).then((r) => r.data),
  marketPrice: (id: number) =>
    api
      .get<{ monthly: { month: string; price: number }[] }>(`/api/transactions/market-price/${id}/`)
      .then((r) => r.data),
};
