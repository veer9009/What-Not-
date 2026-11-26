import { apiBaseUrl } from './config';
import type { TokenResponse, User } from './types';

let credential: string | null = null;
let generation = 0;
let account: Pick<User, 'id' | 'role'> | null = null;
export function bindAccessIdentity(user: User) { account = { id: user.id, role: user.role }; }
const unauthorizedListeners = new Set<() => void>();
let expiresAt: number | null = null;
let renewal: Promise<TokenResponse> | null = null;
let cookieQueue: Promise<unknown> = Promise.resolve();
const tokenListeners = new Set<() => void>();
export function onTokenChanged(listener: () => void) { tokenListeners.add(listener); return () => { tokenListeners.delete(listener); }; }
export function accessExpiresAt() { return expiresAt; }
export function cancelPendingAuth() { generation++; renewal = null; }
function notifyToken() { tokenListeners.forEach(listener => listener()); }
export function setAccessToken(token: string | null) { credential = token; account = null; expiresAt = null; generation++; renewal = null; notifyToken(); }
function serialized<T>(action: () => Promise<T>): Promise<T> {
  const execute = () => typeof navigator !== 'undefined' && navigator.locks
    ? navigator.locks.request('what-not-auth-cookie', action) : action();
  const pending = cookieQueue.catch(() => {}).then(execute);
  cookieQueue = pending.catch(() => {}); return pending;
}
function acceptToken(result: TokenResponse, started: number) {
  if (generation !== started) throw new ApiError(0, 'Your session changed. Please try again.');
  if (!result.access_token || result.token_type !== 'bearer' || !Number.isFinite(result.expires_in) || result.expires_in <= 0)
    throw new ApiError(0, 'The API returned an invalid sign-in response.');
  if (account && (!result.user || result.user.id !== account.id || result.user.role !== account.role))
    throw new ApiError(401, 'Your account changed in another tab. Please sign in again.');
  if (result.user) bindAccessIdentity(result.user);
  credential = result.access_token; expiresAt = Date.now() + result.expires_in * 1000; notifyToken();
  return result;
}
function invalidate() { setAccessToken(null); unauthorizedListeners.forEach(listener => listener()); }
export function refreshSession(): Promise<TokenResponse> {
  if (renewal) return renewal;
  const started = generation;
  const hadCredential = credential !== null;
  const pending = serialized(async () => {
    if (started !== generation) throw new ApiError(0, 'Your session changed. Please try again.');
    return acceptToken(await api<TokenResponse>('/auth/refresh', { method: 'POST', auth: false }), started);
  }).catch(error => {
    if (started === generation && error instanceof ApiError && (error.status === 401 || error.status === 403)) {
      if (hadCredential) invalidate(); else setAccessToken(null);
    }
    throw error;
  });
  renewal = pending;
  void pending.finally(() => { if (renewal === pending) renewal = null; }).catch(() => {});
  return pending;
}
export function loginSession(email: string, password: string) {
  setAccessToken(null); const started = generation;
  return serialized(async () => {
    if (generation !== started) throw new ApiError(0, 'Your session changed. Please try again.');
    return acceptToken(await api<TokenResponse>('/auth/login', { method: 'POST', body: { email, password }, auth: false }), started);
  });
}
const channel = typeof window !== 'undefined' && typeof BroadcastChannel !== 'undefined' ? new BroadcastChannel('what-not-session') : null;
if (channel) channel.onmessage = event => { if (event.data === 'logout') invalidate(); };
export function logoutSession() {
  setAccessToken(null); channel?.postMessage('logout');
  return serialized(() => api<void>('/auth/logout', { method: 'POST', auth: false }));
}
export function resetPasswordSession(reset_token: string, password: string, signal?: AbortSignal) {
  return serialized(async () => {
    const result = await api<{ message: string }>('/auth/password-recovery/reset', {
      method: 'POST', body: { reset_token, password }, auth: false, signal,
    });
    invalidate(); channel?.postMessage('logout');
    return result;
  });
}
export function getAccessToken() { return credential; }
export function onUnauthorized(listener: () => void) { unauthorizedListeners.add(listener); return () => { unauthorizedListeners.delete(listener); }; }
export class ApiError extends Error {
  constructor(public status: number, message: string, public fields: Record<string,string> = {}, public code?: string, public retryAfter?: number) { super(message); this.name = 'ApiError'; }
}
const messages: Record<number,string> = {
  401: 'Your session expired or your credentials are invalid. Please sign in again.',
  403: 'You do not have permission to perform this operation.',
  404: 'The requested record was not found.',
  409: 'This operation conflicts with existing data. Refresh and try again. For addresses used by orders, create a replacement address; delivery fields cannot be changed.',
  422: 'Please check the highlighted fields and try again.',
  429: 'Too many requests. Please wait before trying again.',
  501: 'This feature is awaiting geographic eligibility support.',
};
const allowedFields = new Set(['name','email','phone','password','role','shop_name','description','latitude','longitude','price','stock_quantity','category','delivery_radius_km','image_url','rejection_reason','label','address_line1','address_line2','city','state','pincode','is_default','status']);
// Tokenize JSON strings/numbers together so digits inside quoted text are untouched.
// Preserve unsafe integer literals before JSON.parse can round them, then normalize IDs.
export function parseJson(text: string): unknown {
  const exact = text.replace(/"(?:[^"\\]|\\.)*"|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?/g, value => {
    if (!value.startsWith('"') && /^-?\d+$/.test(value) && !Number.isSafeInteger(Number(value))) return `"${value}"`;
    return value;
  });
  return JSON.parse(exact, (key, value) => {
    if ((key === 'id' || (key.endsWith('_id') && key !== 'upi_id')) && (typeof value === 'number' || typeof value === 'string')) {
      const id = String(value);
      if (!/^[1-9]\d*$/.test(id) || BigInt(id) > 9223372036854775807n) throw new Error('Invalid identifier');
      return id;
    }
    return value;
  });
}
export function identifier(id: string) {
  if (!/^[1-9]\d*$/.test(id) || BigInt(id) > 9223372036854775807n) throw new ApiError(404, messages[404]);
  return id;
}
interface Options { method?: 'GET' | 'POST' | 'PUT' | 'PATCH'; body?: unknown; bodyText?: string; auth?: boolean; signal?: AbortSignal; idempotencyKey?: string }
export async function api<T>(path: string, { method = 'GET', body, bodyText, auth = true, signal, idempotencyKey }: Options = {}): Promise<T> {
  if (!path.startsWith('/') || path.startsWith('//') || /^\/api(?:\/|$)/.test(path)) {
    throw new Error('Invalid API path: supply an endpoint without the API prefix.');
  }
  const base = apiBaseUrl(import.meta.env.PROD, import.meta.env.VITE_API_BASE_URL,
    '/api/v1');
  const headers = new Headers({ Accept: 'application/json' });
  if (body !== undefined || bodyText !== undefined) headers.set('Content-Type', 'application/json');
  const token = auth ? credential : null;
  const started = generation;
  if (token) headers.set('Authorization', `Bearer ${token}`);
  if (idempotencyKey) headers.set('Idempotency-Key', idempotencyKey);
  const cookieAuth = /^\/auth\/(login|refresh|logout|password-recovery\/(request|verify|reset))$/.test(path);
  if (cookieAuth) headers.set('X-WhatNot-CSRF', '1');
  let response: Response;
  let raw: string;
  try {
    response = await fetch(`${base}${path}`, { method, headers, body: bodyText ?? (body === undefined ? undefined : JSON.stringify(body)), signal, cache: 'no-store', credentials: cookieAuth ? 'include' : 'omit' });
    if (auth && token && response.status === 401 && generation === started) {
      if (credential === token) await refreshSession();
      if (generation !== started) throw new ApiError(0, 'Your session changed. Please try again.');
      headers.set('Authorization', `Bearer ${credential}`);
      response = await fetch(`${base}${path}`, { method, headers, body: bodyText ?? (body === undefined ? undefined : JSON.stringify(body)), signal, cache: 'no-store', credentials: 'omit' });
    }
    raw = await response.text();
  } catch (error) {
    if (error instanceof ApiError || (error instanceof DOMException && error.name === 'AbortError')) throw error;
    throw new ApiError(0, 'Unable to reach the marketplace API. Check your connection and try again.');
  }
  if (auth && generation !== started) throw new ApiError(0, 'Your session changed. Please try again.');
  let data: unknown;
  try { data = raw ? parseJson(raw) : undefined; }
  catch { if (response.ok) throw new ApiError(0, 'The API returned an invalid response. Please try again.'); }
  if (!response.ok) {
    if (auth && token && response.status === 401) { setAccessToken(null); unauthorizedListeners.forEach(listener => listener()); }
    const fields: Record<string,string> = {};
    if (response.status === 422 && data && typeof data === 'object' && 'detail' in data && Array.isArray(data.detail)) {
      for (const issue of data.detail) {
        if (!issue || !Array.isArray(issue.loc)) continue;
        const field = issue.loc[1];
        if (typeof field === 'string' && allowedFields.has(field)) fields[field] = 'Check this field against the form requirements.';
      }
    }
    const code = response.status === 409 && data && typeof data === 'object' && 'code' in data
      && (data.code === 'DELIVERY_INELIGIBLE' || data.code === 'IDEMPOTENCY_CONFLICT') ? data.code : undefined;
    // Recognize only this public denial; never render arbitrary server details.
    const betaDenied = response.status === 403 && /^\/auth\/(register|login|refresh|me)$/.test(path)
      && data && typeof data === 'object' && 'detail' in data
      && data.detail === 'This account is not admitted to the controlled beta';
    const recoveryInvalid = response.status === 400 && /^\/auth\/password-recovery\/(verify|reset)$/.test(path);
    const retryHeader = response.headers.get('Retry-After');
    const retryAfter = retryHeader && /^\d{1,4}$/.test(retryHeader) && Number(retryHeader) >= 1 && Number(retryHeader) <= 3600 ? Number(retryHeader) : undefined;
    throw new ApiError(response.status, recoveryInvalid
      ? 'This code or recovery request is invalid or expired. Request a new code and try again.'
      : betaDenied
      ? 'Use an approved beta email address or contact the beta organizer for access.'
      : messages[response.status] || 'The marketplace service is unavailable. Please try again later.', fields, code, retryAfter);
  }
  return data as T;
}
export function errorMessage(error: unknown) { return error instanceof ApiError ? error.message : 'Something went wrong. Please try again.'; }

// Binary uploads share the JSON client's base, bearer credentials and session boundary.
export function uploadBinary<T>(path: string, file: File, progress?: (percent: number) => void, signal?: AbortSignal): Promise<T> {
  const started = generation;
  if (credential && expiresAt !== null && expiresAt <= Date.now() + 30000) {
    return refreshSession().then(() => {
      if (generation !== started) throw new ApiError(0, 'Your session changed. Please try again.');
      return sendBinary<T>(path, file, progress, signal);
    });
  }
  return sendBinary<T>(path, file, progress, signal);
}
function sendBinary<T>(path: string, file: File, progress?: (percent: number) => void, signal?: AbortSignal): Promise<T> {
  if (!path.startsWith('/') || path.startsWith('//') || /^\/api(?:\/|$)/.test(path)) throw new Error('Invalid API path');
  const base = apiBaseUrl(import.meta.env.PROD, import.meta.env.VITE_API_BASE_URL,
    '/api/v1');
  const token = credential, started = generation;
  return new Promise((resolve, reject) => {
    if (signal?.aborted) { reject(new DOMException('Image upload cancelled.', 'AbortError')); return; }
    const request = new XMLHttpRequest();
    const abort = () => request.abort();
    const cleanup = () => signal?.removeEventListener('abort', abort);
    const fail = (error: Error) => { cleanup(); reject(error); };
    request.open('POST', `${base}${path}`);
    request.timeout = 120000;
    request.withCredentials = false;
    request.setRequestHeader('Accept', 'application/json');
    request.setRequestHeader('Content-Type', file.type || 'application/octet-stream');
    if (token) request.setRequestHeader('Authorization', `Bearer ${token}`);
    request.upload.onprogress = event => {
      if (!signal?.aborted && generation === started && event.lengthComputable) progress?.(Math.round(event.loaded / event.total * 100));
    };
    request.onload = () => {
      cleanup();
      if (generation !== started) { reject(new ApiError(0, 'Your session changed. Please try again.')); return; }
      if (request.status < 200 || request.status >= 300) {
        if (token && request.status === 401) { setAccessToken(null); unauthorizedListeners.forEach(listener => listener()); }
        reject(new ApiError(request.status, request.status === 422 ? 'The image could not be decoded or validated. Choose a valid JPG, PNG or WebP image, 5 MiB or smaller.' : messages[request.status] || (request.status === 413 ? 'Each image must be 5 MiB or smaller.' : request.status === 415 ? 'Choose a valid JPG, PNG or WebP image.' : 'Image upload failed. Please try again.'))); return;
      }
      try { resolve(parseJson(request.responseText) as T); }
      catch { reject(new ApiError(0, 'The API returned an invalid response. Please try again.')); }
    };
    request.onerror = () => fail(new ApiError(0, 'Unable to upload the image. Check your connection and try again.'));
    request.onabort = () => fail(new DOMException('Image upload cancelled.', 'AbortError'));
    request.ontimeout = () => fail(new ApiError(0, 'Image upload timed out. Check your connection and retry the remaining images.'));
    signal?.addEventListener('abort', abort, { once: true });
    request.send(file);
  });
}
