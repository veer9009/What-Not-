import { api } from './client';
import type { Registration, TokenResponse, User } from './types';
export const authApi = {
  register: (body: Registration) => api<User>('/auth/register', { method: 'POST', body, auth: false }),
  login: (email: string, password: string) => api<TokenResponse>('/auth/login', { method: 'POST', body: { email, password }, auth: false }),
  me: () => api<User>('/auth/me'),
};
