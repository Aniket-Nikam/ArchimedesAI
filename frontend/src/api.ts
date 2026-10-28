let csrfToken = '';
export const setCsrfToken = (token: string) => { csrfToken = token; };

export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  if (!['GET', 'HEAD', 'OPTIONS'].includes((init.method || 'GET').toUpperCase()) && csrfToken) {
    headers.set('X-CSRF-Token', csrfToken);
  }
  const response = await fetch(path, { ...init, headers, credentials: 'same-origin' });
  if (!response.ok) {
    let detail = `Request failed (${response.status}).`;
    try {
      const body = await response.json();
      if (typeof body.detail === 'string') detail = body.detail;
      else if (Array.isArray(body.detail)) detail = body.detail.map((error: {msg: string}) => error.msg).join('. ');
    } catch { /* retain the HTTP status for non-JSON failures */ }
    if (response.status === 401 && !path.startsWith('/api/auth/')) {
      window.dispatchEvent(new Event('archimedes:session-expired'));
    }
    throw new Error(detail);
  }
  return response;
}
