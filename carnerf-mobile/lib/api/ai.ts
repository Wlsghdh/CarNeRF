import { api } from './client';
import { VehicleSummary } from '../types';

export const aiApi = {
  vehicleSummary: (vehicleId: number) =>
    api.get<VehicleSummary>(`/api/ai/vehicle-summary/${vehicleId}/`).then((r) => r.data),
};
