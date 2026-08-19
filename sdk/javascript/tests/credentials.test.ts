import { VAFClient } from '../src';

/**
 * How the SDK presents its credential.
 *
 * This is pinned because getting it wrong is silent: the client compiles, the
 * request goes out, and the server answers 401 for what looks like a bad key
 * rather than a misplaced one. The JS SDK shipped exactly that defect — it sent
 * the API key as `Authorization: Bearer <key>`, which the backend tries to
 * decode as a JWT and rejects, because keys are only read from `X-API-Key`.
 * The Python SDK has pinned this since it was fixed there; this side had not.
 */

function capturingFetch(): {
  fetch: typeof globalThis.fetch;
  calls: Array<{ url: string; init: RequestInit }>;
} {
  const calls: Array<{ url: string; init: RequestInit }> = [];
  const fn = (async (url: string | URL | Request, init?: RequestInit) => {
    calls.push({ url: url as string, init: init as RequestInit });
    return {
      ok: true,
      status: 200,
      headers: new Map([['content-type', 'application/json']]) as unknown as Headers,
      json: async () => ({}),
      text: async () => '{}',
    };
  }) as unknown as typeof globalThis.fetch;
  return { fetch: fn, calls };
}

function headersOf(init: RequestInit): Record<string, string> {
  return (init.headers ?? {}) as Record<string, string>;
}

describe('credential transport', () => {
  it('sends an API key on X-API-Key, never as a bearer token', async () => {
    const { fetch, calls } = capturingFetch();
    const client = new VAFClient({ baseUrl: 'http://localhost:8000', apiKey: 'key-abc', fetch });

    await client.health();

    const headers = headersOf(calls[0].init);
    expect(headers['X-API-Key']).toBe('key-abc');
    // The defect this guards: a key smuggled into Authorization is rejected as
    // an undecodable JWT, which reads as "bad credentials" rather than "wrong
    // header".
    expect(headers['Authorization']).toBeUndefined();
  });

  it('sends a session token as a bearer token', async () => {
    const { fetch, calls } = capturingFetch();
    const client = new VAFClient({ baseUrl: 'http://localhost:8000', token: 'jwt-xyz', fetch });

    await client.health();

    const headers = headersOf(calls[0].init);
    expect(headers['Authorization']).toBe('Bearer jwt-xyz');
    expect(headers['X-API-Key']).toBeUndefined();
  });

  it('prefers a held session token over a static API key', async () => {
    const { fetch, calls } = capturingFetch();
    const client = new VAFClient({
      baseUrl: 'http://localhost:8000',
      apiKey: 'key-abc',
      token: 'jwt-xyz',
      fetch,
    });

    await client.health();

    const headers = headersOf(calls[0].init);
    expect(headers['Authorization']).toBe('Bearer jwt-xyz');
    expect(headers['X-API-Key']).toBeUndefined();
  });

  it('sends no credential header at all when none is configured', async () => {
    const { fetch, calls } = capturingFetch();
    const client = new VAFClient({ baseUrl: 'http://localhost:8000', fetch });

    await client.health();

    const headers = headersOf(calls[0].init);
    expect(headers['Authorization']).toBeUndefined();
    expect(headers['X-API-Key']).toBeUndefined();
  });

  it('carries the credential on a method set after construction', async () => {
    const { fetch, calls } = capturingFetch();
    const client = new VAFClient({ baseUrl: 'http://localhost:8000', fetch });
    client.setApiKey('key-late');

    await client.health();

    expect(headersOf(calls[0].init)['X-API-Key']).toBe('key-late');
  });
});
