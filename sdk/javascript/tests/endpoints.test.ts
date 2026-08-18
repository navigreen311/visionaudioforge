/**
 * Every client method exercised against a mocked transport.
 *
 * The SDK shipped with one test file covering a handful of methods on a client
 * that claims full API coverage. This drives every sub-client method and pins
 * the request path and HTTP method each one sends, so a path drifting away
 * from the API is caught here rather than as a 404 in production.
 */

import { VAFClient } from '../src';

const BASE = 'http://localhost:8000';

interface Call {
  url: string;
  init: RequestInit;
}

/** A fetch stub that records every call and returns `body`. */
function recordingFetch(body: unknown = {}, status = 200): {
  fetch: typeof globalThis.fetch;
  calls: Call[];
} {
  const calls: Call[] = [];
  const fn = (async (url: string | URL | Request, init?: RequestInit) => {
    calls.push({ url: url as string, init: init as RequestInit });
    return {
      ok: status >= 200 && status < 300,
      status,
      headers: new Map([['content-type', 'application/json']]) as unknown as Headers,
      json: async () => body,
      text: async () => JSON.stringify(body),
      arrayBuffer: async () => new ArrayBuffer(8),
      blob: async () => ({}) as Blob,
    };
  }) as unknown as typeof globalThis.fetch;
  return { fetch: fn, calls };
}

function makeClient(body: unknown = {}): { client: VAFClient; calls: Call[] } {
  const { fetch, calls } = recordingFetch(body);
  return {
    client: new VAFClient({ baseUrl: BASE, apiKey: 'k', fetch }),
    calls,
  };
}

/** Assert the last request went to `path` with `method`. */
function expectCall(calls: Call[], method: string, path: string): void {
  const match = calls.find(
    (c) => c.url === `${BASE}${path}` && (c.init?.method ?? 'GET') === method,
  );
  expect(
    match,
    // Surfacing every call makes a path drift obvious rather than cryptic.
  ).toBeDefined();
}

describe('credentials', () => {
  it('sends X-API-Key when only a key is configured', async () => {
    const { client, calls } = makeClient({ status: 'ok' });
    await client.health();
    const headers = calls[0].init.headers as Record<string, string>;
    expect(headers['X-API-Key']).toBe('k');
    expect(headers['Authorization']).toBeUndefined();
  });

  it('prefers a session token over the API key', async () => {
    const { client, calls } = makeClient({ status: 'ok' });
    client.setToken('jwt-abc');
    await client.health();
    const headers = calls[0].init.headers as Record<string, string>;
    expect(headers['Authorization']).toBe('Bearer jwt-abc');
    expect(headers['X-API-Key']).toBeUndefined();
  });

  it('sends neither header when nothing is configured', async () => {
    const { fetch, calls } = recordingFetch({ status: 'ok' });
    const bare = new VAFClient({ baseUrl: BASE, fetch });
    await bare.health();
    const headers = calls[0].init.headers as Record<string, string>;
    expect(headers['Authorization']).toBeUndefined();
    expect(headers['X-API-Key']).toBeUndefined();
  });
});

describe('client', () => {
  it('login posts to /api/auth/login and stores the token', async () => {
    const { client, calls } = makeClient({ access_token: 'jwt-abc' });
    await client.login('a@example.com', 'pw');
    expectCall(calls, 'POST', '/api/auth/login');

    // A subsequent call must carry the token it just learned.
    await client.health();
    const headers = calls[1].init.headers as Record<string, string>;
    expect(headers['Authorization']).toBe('Bearer jwt-abc');
  });

  it('me reads the current user', async () => {
    const { client, calls } = makeClient({ id: 'u1' });
    await client.me();
    expectCall(calls, 'GET', '/api/auth/me');
  });

  it('health reads /api/health', async () => {
    const { client, calls } = makeClient({ status: 'ok' });
    await client.health();
    expectCall(calls, 'GET', '/api/health');
  });
});

describe('vision', () => {
  it('drives every vision endpoint', async () => {
    const { client, calls } = makeClient({ detections: [] });
    const file = new Blob([new Uint8Array([1, 2, 3])]) as unknown as File;

    await client.vision.analyze(file);
    await client.vision.detect(file);
    await client.vision.opticalFlow(file);
    await client.vision.ocr(file);

    expectCall(calls, 'POST', '/api/vision/analyze');
    expectCall(calls, 'POST', '/api/vision/detect');
    expectCall(calls, 'POST', '/api/vision/optical-flow');
    expectCall(calls, 'POST', '/api/vision/ocr');
  });
});

describe('audio', () => {
  it('drives every audio endpoint', async () => {
    const { client, calls } = makeClient({ text: 'hi' });
    const file = new Blob([new Uint8Array([1])]) as unknown as File;

    await client.audio.analyze(file);
    await client.audio.transcribe(file);
    await client.audio.diarize(file);
    await client.audio.classify(file);

    expectCall(calls, 'POST', '/api/audio/analyze');
    expectCall(calls, 'POST', '/api/audio/transcribe');
    expectCall(calls, 'POST', '/api/audio/diarize');
    expectCall(calls, 'POST', '/api/audio/classify');
  });
});

describe('assets', () => {
  it('lists, reads and deletes', async () => {
    const { client, calls } = makeClient({ items: [] });

    await client.assets.list();
    await client.assets.get('a1');
    await client.assets.delete('a1');

    expectCall(calls, 'GET', '/api/assets');
    expectCall(calls, 'GET', '/api/assets/a1');
    expectCall(calls, 'DELETE', '/api/assets/a1');
  });
});

describe('datasets', () => {
  it('creates, lists and reads', async () => {
    const { client, calls } = makeClient({ id: 'd1' });

    await client.datasets.create({ name: 'd' } as never);
    await client.datasets.list();
    await client.datasets.get('d1');

    expectCall(calls, 'POST', '/api/datasets');
    expectCall(calls, 'GET', '/api/datasets');
    expectCall(calls, 'GET', '/api/datasets/d1');
  });
});

describe('models', () => {
  it('targets the registry', async () => {
    const { client, calls } = makeClient({ id: 'm1' });

    await client.models.list();
    await client.models.get('m1');
    await client.models.compare(['m1', 'm2']);

    expectCall(calls, 'GET', '/api/registry/models');
    expectCall(calls, 'GET', '/api/registry/models/m1');
    expectCall(calls, 'POST', '/api/registry/compare');
  });
});

describe('search', () => {
  it('queries, indexes and reports stats', async () => {
    const { client, calls } = makeClient({ results: [] });

    await client.search.query({ text: 'cat' } as never);
    await client.search.index({ asset_id: 'a1' } as never);
    await client.search.stats();

    expectCall(calls, 'POST', '/api/search/query');
    expectCall(calls, 'POST', '/api/search/index');
    expectCall(calls, 'GET', '/api/search/stats');
  });
});

describe('pipeline', () => {
  it('creates, validates and lists nodes', async () => {
    const { client, calls } = makeClient({ id: 'p1' });

    await client.pipeline.create({ name: 'p' } as never);
    await client.pipeline.validate({ nodes: [] } as never);
    await client.pipeline.listNodes();
    await client.pipeline.generateFromDescription('blur faces');

    expectCall(calls, 'POST', '/api/pipeline/create');
    expectCall(calls, 'POST', '/api/pipeline/validate');
    expectCall(calls, 'GET', '/api/pipeline/nodes');
    expectCall(calls, 'POST', '/api/pipeline/generate');
  });
});

describe('agents', () => {
  it('chats and lists', async () => {
    const { client, calls } = makeClient({ response: 'hi' });

    await client.agents.chat({ message: 'hello' } as never);
    await client.agents.listAgents();

    expectCall(calls, 'POST', '/api/agents/chat');
    expectCall(calls, 'GET', '/api/agents');
  });
});

describe('alerts', () => {
  it('lists and creates rules', async () => {
    const { client, calls } = makeClient({ items: [] });

    await client.alerts.listAlerts();
    await client.alerts.createRule({ name: 'r' } as never);

    expectCall(calls, 'GET', '/api/alerts');
    expectCall(calls, 'POST', '/api/alerts/rules');
  });
});

describe('transform', () => {
  it('drives the audio transform endpoints', async () => {
    const { client, calls } = makeClient({ id: 't1' });
    const file = new Blob([new Uint8Array([1])]) as unknown as File;

    await client.transform.audioDenoise(file);
    await client.transform.audioChain(file, [] as never);

    expectCall(calls, 'POST', '/api/transform/audio/denoise');
    expectCall(calls, 'POST', '/api/transform/audio/chain');
  });
});
