let credential: string | null = null;
let generation = 0;
const unauthorizedListeners = new Set<() => void>();
export function setAccessToken(token: string | null) { credential = token; generation++; }
export function getAccessToken() { return credential; }
export function onUnauthorized(listener: () => void) { unauthorizedListeners.add(listener); return () => { unauthorizedListeners.delete(listener); }; }
export class ApiError extends Error {
  constructor(public status: number, message: string, public fields: Record<string,string> = {}) { super(message); this.name = 'ApiError'; }
}
const messages: Record<number,string> = {
  401: 'Your session expired or your credentials are invalid. Please sign in again.',
  403: 'You do not have permission to perform this operation.',
  404: 'The requested record was not found.',
  409: 'This operation conflicts with existing data. Refresh and try again. For addresses used by orders, create a replacement address; delivery fields cannot be changed.',
  422: 'Please check the highlighted fields and try again.',
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
    if ((key === 'id' || key.endsWith('_id')) && (typeof value === 'number' || typeof value === 'string')) {
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
interface Options { method?: 'GET' | 'POST' | 'PATCH'; body?: unknown; auth?: boolean; signal?: AbortSignal }
export async function api<T>(path: string, { method = 'GET', body, auth = true, signal }: Options = {}): Promise<T> {
  const base = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1').replace(/\/$/, '');
  const headers = new Headers({ Accept: 'application/json' });
  if (body !== undefined) headers.set('Content-Type', 'application/json');
  const token = auth ? credential : null;
  const started = generation;
  if (token) headers.set('Authorization', `Bearer ${token}`);
  let response: Response;
  let raw: string;
  try {
    response = await fetch(`${base}${path}`, { method, headers, body: body === undefined ? undefined : JSON.stringify(body), signal, cache: 'no-store', credentials: 'omit' });
    raw = await response.text();
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
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
    throw new ApiError(response.status, messages[response.status] || 'The marketplace service is unavailable. Please try again later.', fields);
  }
  return data as T;
}
export function errorMessage(error: unknown) { return error instanceof ApiError ? error.message : 'Something went wrong. Please try again.'; }
