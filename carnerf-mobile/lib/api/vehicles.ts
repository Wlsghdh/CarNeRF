import { api } from './client';
import { DiagnosisReport, Vehicle } from '../types';

export const vehiclesApi = {
  list: (q: { brand?: string; fuel_type?: string; year_min?: number; year_max?: number } = {}) =>
    api.get<Vehicle[]>('/api/vehicles/', { params: q }).then((r) => r.data),
  get: (id: number) => api.get<Vehicle>(`/api/vehicles/${id}/`).then((r) => r.data),
  diagnosis: (id: number) =>
    api.get<DiagnosisReport>(`/api/vehicles/${id}/diagnosis/`).then((r) => r.data),
};
