import { api, loginSession, refreshSession, logoutSession } from './client';
import type { Registration, User } from './types';
export const authApi = {
  register: (body: Registration) => api<User>('/auth/register', { method: 'POST', body, auth: false }),
  login: loginSession,
  refresh: refreshSession,
  logout: logoutSession,
  me: () => api<User>('/auth/me'),
};
