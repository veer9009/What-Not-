/** Public API routing only. Errors deliberately omit the supplied URL. */
export function apiBaseUrl(production: boolean, configured?: string, developmentBase = '/api/v1'): string {
  const base = configured?.trim() || (production ? '/api/v1' : developmentBase);
  if (base === '/api/v1' || base === '/api/v1/') return '/api/v1';
  try {
    const url = new URL(base);
    const host = url.hostname.toLowerCase().replace(/\.$/, '');
    const loopback = host === 'localhost' || host.endsWith('.localhost') ||
      host === '[::1]' || host === '[::]' || host === '0.0.0.0' ||
      /^127\./.test(host) || /^\[::ffff:(?:127\.|7f)/i.test(host);
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash ||
        !['/api/v1', '/api/v1/'].includes(url.pathname) ||
        (production && (url.protocol !== 'https:' || loopback))) throw new Error();
    return `${url.origin}/api/v1`;
  } catch {
    throw new Error('Invalid API configuration: use /api/v1 or an approved HTTPS API origin with /api/v1.');
  }
}
