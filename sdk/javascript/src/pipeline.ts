import type {
  PipelineDefinition,
  PipelineInfo,
  PipelineRunInfo,
  PipelineNodeType,
  RequestOptions,
} from './types';

type RequestFn = (
  method: string,
  path: string,
  options?: { body?: unknown; formData?: FormData; options?: RequestOptions },
) => Promise<unknown>;

/**
 * Client for pipeline builder endpoints.
 */
export class PipelineClient {
  constructor(private readonly _request: RequestFn) {}

  /** Create a new pipeline. */
  async create(definition: PipelineDefinition, options?: RequestOptions): Promise<PipelineInfo> {
    return this._request('POST', '/api/pipeline/create', { body: definition, options }) as Promise<PipelineInfo>;
  }

  /** Start a pipeline run. */
  async run(pipelineId: string, inputs?: Record<string, unknown>, options?: RequestOptions): Promise<PipelineRunInfo> {
    return this._request('POST', `/api/pipeline/run/${pipelineId}`, { body: inputs ?? {}, options }) as Promise<PipelineRunInfo>;
  }

  /** List all pipelines. */
  async list(options?: RequestOptions): Promise<PipelineInfo[]> {
    return this._request('GET', '/api/pipelines', { options }) as Promise<PipelineInfo[]>;
  }

  /** Get pipeline details. */
  async get(pipelineId: string, options?: RequestOptions): Promise<PipelineInfo> {
    return this._request('GET', `/api/pipelines/${pipelineId}`, { options }) as Promise<PipelineInfo>;
  }

  /** Get run status. */
  async getRunStatus(runId: string, options?: RequestOptions): Promise<PipelineRunInfo> {
    return this._request('GET', `/api/pipeline/runs/${runId}`, { options }) as Promise<PipelineRunInfo>;
  }

  /** Validate a pipeline definition. */
  async validate(definition: PipelineDefinition, options?: RequestOptions): Promise<{ valid: boolean; errors?: string[] }> {
    return this._request('POST', '/api/pipeline/validate', { body: definition, options }) as Promise<{ valid: boolean; errors?: string[] }>;
  }

  /** List available node types. */
  async listNodes(options?: RequestOptions): Promise<PipelineNodeType[]> {
    return this._request('GET', '/api/pipeline/nodes', { options }) as Promise<PipelineNodeType[]>;
  }

  /** Generate a pipeline from a natural language description. */
  async generateFromDescription(description: string, options?: RequestOptions): Promise<PipelineDefinition> {
    return this._request('POST', '/api/pipeline/generate', { body: { description }, options }) as Promise<PipelineDefinition>;
  }
}
