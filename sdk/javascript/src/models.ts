import type {
  ModelRegistration,
  ModelInfo,
  ModelComparison,
  TrainingJob,
  RequestOptions,
} from './types';

type RequestFn = (
  method: string,
  path: string,
  options?: { body?: unknown; formData?: FormData; options?: RequestOptions },
) => Promise<unknown>;

/**
 * Client for the model registry endpoints.
 */
export class ModelClient {
  constructor(private readonly _request: RequestFn) {}

  /** Register a new model. */
  async register(model: ModelRegistration, options?: RequestOptions): Promise<ModelInfo> {
    return this._request('POST', '/api/registry/register', { body: model, options }) as Promise<ModelInfo>;
  }

  /** List all registered models. */
  async list(options?: RequestOptions): Promise<ModelInfo[]> {
    return this._request('GET', '/api/registry/models', { options }) as Promise<ModelInfo[]>;
  }

  /** Get model details by ID. */
  async get(modelId: string, options?: RequestOptions): Promise<ModelInfo> {
    return this._request('GET', `/api/registry/models/${modelId}`, { options }) as Promise<ModelInfo>;
  }

  /** Promote / update model lifecycle status (e.g. staging -> production). */
  async promote(modelId: string, status: string, options?: RequestOptions): Promise<ModelInfo> {
    return this._request('PUT', `/api/registry/models/${modelId}/status`, { body: { status }, options }) as Promise<ModelInfo>;
  }

  /** Compare two or more models. */
  async compare(modelIds: string[], options?: RequestOptions): Promise<ModelComparison> {
    return this._request('POST', '/api/registry/compare', { body: { model_ids: modelIds }, options }) as Promise<ModelComparison>;
  }

  /** Rollback a model to a previous version. */
  async rollback(modelId: string, options?: RequestOptions): Promise<ModelInfo> {
    return this._request('POST', `/api/registry/models/${modelId}/rollback`, { options }) as Promise<ModelInfo>;
  }

  /** Start a training job. */
  async startTraining(body: Record<string, unknown>, options?: RequestOptions): Promise<TrainingJob> {
    return this._request('POST', '/api/transfer/start', { body, options }) as Promise<TrainingJob>;
  }
}
