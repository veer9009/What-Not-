import { api, loginSession, refreshSession, logoutSession, resetPasswordSession } from './client';
import type { Registration, User } from './types';
export const authApi = {
  register: (body: Registration) => api<User>('/auth/register', { method: 'POST', body, auth: false }),
  login: loginSession,
  refresh: refreshSession,
  logout: logoutSession,
  me: () => api<User>('/auth/me'),
  requestPasswordRecovery: (email: string, signal?: AbortSignal) => api<{ message: string; challenge: string; resend_after: number }>('/auth/password-recovery/request', { method: 'POST', body: { email }, auth: false, signal }),
  verifyPasswordRecovery: (challenge: string, otp: string, signal?: AbortSignal) => api<{ reset_token: string }>('/auth/password-recovery/verify', { method: 'POST', body: { challenge, otp }, auth: false, signal }),
  resetPassword: resetPasswordSession,
};
