import { mapError } from './errors';
import { VisionClient } from './vision';
import { AudioClient } from './audio';
import { ModelClient } from './models';
import { SearchClient } from './search';
import { PipelineClient } from './pipeline';
import { AgentClient } from './agents';
import { DatasetClient } from './datasets';
import { AlertClient } from './alerts';
import { AssetClient } from './assets';
import { TransformClient } from './transform';
import type { LoginResponse, HealthResponse, UserProfile, RequestOptions } from './types';

export interface VAFClientOptions {
  /** Base URL of the VAF API (e.g. "http://localhost:8000"). */
  baseUrl: string;
  /** Static API key for authentication (sent as Bearer token). */
  apiKey?: string;
  /** JWT token obtained from login(). Set automatically by login(). */
  token?: string;
  /** Custom fetch implementation (defaults to globalThis.fetch). */
  fetch?: typeof globalThis.fetch;
}

/**
 * Main client for the VisionAudioForge API.
 *
 * @example
 * ```ts
 * const client = new VAFClient({ baseUrl: 'http://localhost:8000' });
 * await client.login('user', 'pass');
 * const result = await client.vision.detect(imageBlob);
 * ```
 */
export class VAFClient {
  private _baseUrl: string;
  private _apiKey?: string;
  private _token?: string;
  private readonly _fetch: typeof globalThis.fetch;

  // Lazy-initialized sub-clients
  private _vision?: VisionClient;
  private _audio?: AudioClient;
  private _models?: ModelClient;
  private _search?: SearchClient;
  private _pipeline?: PipelineClient;
  private _agents?: AgentClient;
  private _datasets?: DatasetClient;
  private _alerts?: AlertClient;
  private _assets?: AssetClient;
  private _transform?: TransformClient;

  constructor(options: VAFClientOptions) {
    this._baseUrl = options.baseUrl.replace(/\/+$/, '');
    this._apiKey = options.apiKey;
    this._token = options.token;
    this._fetch = options.fetch ?? globalThis.fetch.bind(globalThis);
  }

  // ─── Auth ────────────────────────────────────────────────────────────

  /** Login with username/password. Stores the returned JWT for subsequent requests. */
  async login(username: string, password: string): Promise<LoginResponse> {
    const result = await this._request('POST', '/api/auth/login', {
      body: { username, password },
    }) as LoginResponse;
    this._token = result.access_token;
    return result;
  }

  /** Get the current user's profile. */
  async me(options?: RequestOptions): Promise<UserProfile> {
    return this._request('GET', '/api/auth/me', { options }) as Promise<UserProfile>;
  }

  /** Check service health. */
  async health(options?: RequestOptions): Promise<HealthResponse> {
    return this._request('GET', '/api/health', { options }) as Promise<HealthResponse>;
  }

  // ─── Sub-client getters ──────────────────────────────────────────────

  get vision(): VisionClient {
    return (this._vision ??= new VisionClient(this._request.bind(this)));
  }

  get audio(): AudioClient {
    return (this._audio ??= new AudioClient(this._request.bind(this)));
  }

  get models(): ModelClient {
    return (this._models ??= new ModelClient(this._request.bind(this)));
  }

  get search(): SearchClient {
    return (this._search ??= new SearchClient(this._request.bind(this)));
  }

  get pipeline(): PipelineClient {
    return (this._pipeline ??= new PipelineClient(this._request.bind(this)));
  }

  get agents(): AgentClient {
    return (this._agents ??= new AgentClient(this._request.bind(this)));
  }

  get datasets(): DatasetClient {
    return (this._datasets ??= new DatasetClient(this._request.bind(this)));
  }

  get alerts(): AlertClient {
    return (this._alerts ??= new AlertClient(this._request.bind(this)));
  }

  get assets(): AssetClient {
    return (this._assets ??= new AssetClient(this._request.bind(this)));
  }

  get transform(): TransformClient {
    return (this._transform ??= new TransformClient(this._request.bind(this)));
  }

  // ─── Token management ───────────────────────────────────────────────

  /** Set the JWT token manually (e.g. from localStorage). */
  setToken(token: string): void {
    this._token = token;
  }

  /** Set the API key manually. */
  setApiKey(apiKey: string): void {
    this._apiKey = apiKey;
  }

  // ─── Internal request method ────────────────────────────────────────

  async _request(
    method: string,
    path: string,
    opts?: { body?: unknown; formData?: FormData; options?: RequestOptions },
  ): Promise<unknown> {
    const url = `${this._baseUrl}${path}`;
    const headers: Record<string, string> = {
      ...(opts?.options?.headers ?? {}),
    };

    // Auth header
    const authToken = this._token ?? this._apiKey;
    if (authToken) {
      headers['Authorization'] = `Bearer ${authToken}`;
    }

    let requestBody: BodyInit | undefined;

    if (opts?.formData) {
      // Let the browser/runtime set Content-Type with boundary for multipart
      requestBody = opts.formData;
    } else if (opts?.body !== undefined) {
      headers['Content-Type'] = 'application/json';
      requestBody = JSON.stringify(opts.body);
    }

    const response = await this._fetch(url, {
      method,
      headers,
      body: requestBody,
      signal: opts?.options?.signal,
    });

    // For 204 No Content
    if (response.status === 204) {
      return undefined;
    }

    // Try to parse JSON; fall back to text
    const contentType = response.headers.get('content-type') ?? '';
    let data: unknown;

    if (contentType.includes('application/json')) {
      data = await response.json();
    } else {
      // For binary downloads, return the response itself
      if (!response.ok) {
        data = await response.text();
      } else if (
        contentType.includes('application/octet-stream') ||
        contentType.includes('image/') ||
        contentType.includes('audio/') ||
        contentType.includes('video/')
      ) {
        return response;
      } else {
        data = await response.text();
      }
    }

    if (!response.ok) {
      throw mapError(response.status, data);
    }

    return data;
  }
}
