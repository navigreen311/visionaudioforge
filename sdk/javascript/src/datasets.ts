import type {
  DatasetCreateRequest,
  DatasetInfo,
  DatasetSplitRequest,
  DatasetSplitResult,
  DatasetStats,
  RequestOptions,
} from './types';

type RequestFn = (
  method: string,
  path: string,
  options?: { body?: unknown; formData?: FormData; options?: RequestOptions },
) => Promise<unknown>;

/**
 * Client for dataset management endpoints.
 */
export class DatasetClient {
  constructor(private readonly _request: RequestFn) {}

  /** Create a new dataset. */
  async create(dataset: DatasetCreateRequest, options?: RequestOptions): Promise<DatasetInfo> {
    return this._request('POST', '/api/datasets', { body: dataset, options }) as Promise<DatasetInfo>;
  }

  /** List all datasets. */
  async list(options?: RequestOptions): Promise<DatasetInfo[]> {
    return this._request('GET', '/api/datasets', { options }) as Promise<DatasetInfo[]>;
  }

  /** Get dataset details. */
  async get(datasetId: string, options?: RequestOptions): Promise<DatasetInfo> {
    return this._request('GET', `/api/datasets/${datasetId}`, { options }) as Promise<DatasetInfo>;
  }

  /** Upload files to a dataset. */
  async upload(datasetId: string, files: Blob | FormData, options?: RequestOptions): Promise<{ uploaded: number }> {
    const form = files instanceof FormData ? files : (() => { const f = new FormData(); f.append('file', files); return f; })();
    return this._request('POST', `/api/datasets/${datasetId}/upload`, { formData: form, options }) as Promise<{ uploaded: number }>;
  }

  /** Split dataset into train/val/test sets. */
  async split(datasetId: string, splitConfig: DatasetSplitRequest, options?: RequestOptions): Promise<DatasetSplitResult> {
    return this._request('POST', `/api/datasets/${datasetId}/split`, { body: splitConfig, options }) as Promise<DatasetSplitResult>;
  }

  /** Compute dataset statistics. */
  async stats(datasetId: string, options?: RequestOptions): Promise<DatasetStats> {
    return this._request('POST', `/api/datasets/${datasetId}/stats`, { options }) as Promise<DatasetStats>;
  }

  /** Export dataset. */
  async export(datasetId: string, options?: RequestOptions): Promise<unknown> {
    return this._request('GET', `/api/datasets/${datasetId}/export`, { options });
  }
}
