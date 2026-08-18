import { VAFClient, AuthError, NotFoundError, ValidationError, ServerError, VAFError } from '../src';

// ─── Mock fetch ──────────────────────────────────────────────────────────────

function mockFetch(status: number, body: unknown, contentType = 'application/json'): typeof globalThis.fetch {
  return (async (_url: string | URL | Request, _init?: RequestInit) => ({
    ok: status >= 200 && status < 300,
    status,
    headers: new Map([['content-type', contentType]]) as unknown as Headers,
    json: async () => body,
    text: async () => (typeof body === 'string' ? body : JSON.stringify(body)),
  })) as unknown as typeof globalThis.fetch;
}

function capturingFetch(status = 200, body: unknown = {}): {
  fetch: typeof globalThis.fetch;
  calls: Array<{ url: string; init: RequestInit }>;
} {
  const calls: Array<{ url: string; init: RequestInit }> = [];
  const fn = (async (url: string | URL | Request, init?: RequestInit) => {
    calls.push({ url: url as string, init: init as RequestInit });
    return {
      ok: true,
      status,
      headers: new Map([['content-type', 'application/json']]) as unknown as Headers,
      json: async () => body,
      text: async () => JSON.stringify(body),
    };
  }) as unknown as typeof globalThis.fetch;
  return { fetch: fn, calls };
}

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('VAFClient', () => {
  it('should create a client with baseUrl', () => {
    const client = new VAFClient({
      baseUrl: 'http://localhost:8000',
      fetch: mockFetch(200, {}),
    });
    expect(client).toBeDefined();
  });

  it('should strip trailing slashes from baseUrl', async () => {
    const { fetch, calls } = capturingFetch(200, { status: 'ok' });
    const client = new VAFClient({ baseUrl: 'http://localhost:8000/', fetch });
    await client.health();
    expect(calls[0].url).toBe('http://localhost:8000/api/health');
  });

  describe('auth headers', () => {
    it('should send an API key on X-API-Key, not as a Bearer token', async () => {
      // An API key is not a JWT. Sending it as `Authorization: Bearer <key>`
      // means the server tries to decode it as a token and rejects it; the
      // API only accepts keys on X-API-Key.
      const { fetch, calls } = capturingFetch(200, { status: 'ok' });
      const client = new VAFClient({
        baseUrl: 'http://localhost:8000',
        apiKey: 'test-key-123',
        fetch,
      });
      await client.health();
      const headers = calls[0].init.headers as Record<string, string>;
      expect(headers['X-API-Key']).toBe('test-key-123');
      expect(headers['Authorization']).toBeUndefined();
    });

    it('should send Bearer token after login', async () => {
      const loginFetch = mockFetch(200, {
        access_token: 'jwt-token-abc',
        token_type: 'bearer',
      });
      const client = new VAFClient({
        baseUrl: 'http://localhost:8000',
        fetch: loginFetch,
      });
      await client.login('user', 'pass');

      // Now switch to a capturing fetch to verify the token
      const { fetch: capFetch, calls } = capturingFetch(200, { status: 'ok' });
      (client as unknown as { _fetch: typeof globalThis.fetch })._fetch = capFetch;
      await client.health();
      const headers = calls[0].init.headers as Record<string, string>;
      expect(headers['Authorization']).toBe('Bearer jwt-token-abc');
    });

    it('should allow setting token manually', async () => {
      const { fetch, calls } = capturingFetch(200, []);
      const client = new VAFClient({ baseUrl: 'http://localhost:8000', fetch });
      client.setToken('manual-token');
      await client.models.list();
      const headers = calls[0].init.headers as Record<string, string>;
      expect(headers['Authorization']).toBe('Bearer manual-token');
    });
  });

  describe('error mapping', () => {
    it('should throw AuthError on 401', async () => {
      const client = new VAFClient({
        baseUrl: 'http://localhost:8000',
        fetch: mockFetch(401, { detail: 'Invalid credentials' }),
      });
      await expect(client.health()).rejects.toThrow(AuthError);
    });

    it('should throw NotFoundError on 404', async () => {
      const client = new VAFClient({
        baseUrl: 'http://localhost:8000',
        fetch: mockFetch(404, { detail: 'Not found' }),
      });
      await expect(client.health()).rejects.toThrow(NotFoundError);
    });

    it('should throw ValidationError on 422', async () => {
      const client = new VAFClient({
        baseUrl: 'http://localhost:8000',
        fetch: mockFetch(422, { detail: 'Validation failed' }),
      });
      await expect(client.health()).rejects.toThrow(ValidationError);
    });

    it('should throw ServerError on 500', async () => {
      const client = new VAFClient({
        baseUrl: 'http://localhost:8000',
        fetch: mockFetch(500, { detail: 'Internal error' }),
      });
      await expect(client.health()).rejects.toThrow(ServerError);
    });

    it('should throw VAFError on other error codes', async () => {
      const client = new VAFClient({
        baseUrl: 'http://localhost:8000',
        fetch: mockFetch(429, { detail: 'Rate limited' }),
      });
      await expect(client.health()).rejects.toThrow(VAFError);
    });
  });

  describe('sub-client access', () => {
    it('should provide lazy-initialized sub-clients', () => {
      const client = new VAFClient({
        baseUrl: 'http://localhost:8000',
        fetch: mockFetch(200, {}),
      });

      expect(client.vision).toBeDefined();
      expect(client.audio).toBeDefined();
      expect(client.models).toBeDefined();
      expect(client.search).toBeDefined();
      expect(client.pipeline).toBeDefined();
      expect(client.agents).toBeDefined();
      expect(client.datasets).toBeDefined();
      expect(client.alerts).toBeDefined();
      expect(client.assets).toBeDefined();
      expect(client.transform).toBeDefined();
    });

    it('should return the same sub-client instance on repeated access', () => {
      const client = new VAFClient({
        baseUrl: 'http://localhost:8000',
        fetch: mockFetch(200, {}),
      });
      const v1 = client.vision;
      const v2 = client.vision;
      expect(v1).toBe(v2);
    });
  });

  describe('request building', () => {
    it('should send JSON body with Content-Type header', async () => {
      const { fetch, calls } = capturingFetch(200, { id: '1' });
      const client = new VAFClient({
        baseUrl: 'http://localhost:8000',
        apiKey: 'key',
        fetch,
      });
      await client.models.register({
        name: 'test',
        version: '1.0',
        framework: 'pytorch',
      });
      const headers = calls[0].init.headers as Record<string, string>;
      expect(headers['Content-Type']).toBe('application/json');
      expect(calls[0].init.body).toBe(
        JSON.stringify({ name: 'test', version: '1.0', framework: 'pytorch' }),
      );
    });

    it('should use correct HTTP method and path for sub-client calls', async () => {
      const { fetch, calls } = capturingFetch(200, []);
      const client = new VAFClient({
        baseUrl: 'http://localhost:8000',
        apiKey: 'key',
        fetch,
      });
      await client.alerts.listAlerts();
      expect(calls[0].url).toBe('http://localhost:8000/api/alerts');
      expect(calls[0].init.method).toBe('GET');
    });
  });
});
