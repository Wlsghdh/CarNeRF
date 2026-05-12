import { api } from './client';
import { PriceEstimate } from '../types';

export interface PricePredictBody {
  brand: string;
  model: string;
  year: number;
  mileage: number;
  fuel_type: string;
  transmission: string;
  engine_cc?: number;
  region?: string;
  accident_count?: number;
  defect_score?: number;
}

export const predictApi = {
  price: (body: PricePredictBody) =>
    api.post<PriceEstimate>('/api/predict/price/', body).then((r) => r.data),
  byVehicle: (id: number) =>
    api.get<PriceEstimate>(`/api/predict/vehicle/${id}/`).then((r) => r.data),
};
