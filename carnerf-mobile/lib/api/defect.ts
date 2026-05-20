import { api } from './client';
import { DefectReport } from '../types';

export const defectApi = {
  byVehicle: (vehicleId: number) =>
    api.get<DefectReport>(`/api/defect/vehicles/${vehicleId}/`).then((r) => r.data),
};
