import { api } from './client';
import { LoginHistory, Listing, User } from '../types';

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export const authApi = {
  register: (body: { email: string; username: string; password: string; phone?: string }) =>
    api.post<User>('/api/auth/register/', body).then((r) => r.data),
  login: (body: { email: string; password: string }) =>
    api.post<LoginResponse>('/api/auth/login/', body).then((r) => r.data),
  logout: () => api.post('/api/auth/logout/').then((r) => r.data),
  updateProfile: (body: Partial<Pick<User, 'username' | 'phone' | 'region'>>) =>
    api.put<User>('/api/auth/profile/', body).then((r) => r.data),
  myListings: () => api.get<Listing[]>('/api/auth/my-listings/').then((r) => r.data),
  updateListingStatus: (id: number, status: 'active' | 'reserved' | 'sold') =>
    api.put(`/api/auth/listings/${id}/status/`, { status }).then((r) => r.data),
  deleteListing: (id: number) =>
    api.delete(`/api/auth/listings/${id}/`).then((r) => r.data),
  loginHistory: () => api.get<LoginHistory[]>('/api/auth/login-history/').then((r) => r.data),
};
