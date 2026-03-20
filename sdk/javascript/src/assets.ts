import type { AssetInfo, AssetUploadResult, RequestOptions } from './types';

type RequestFn = (
  method: string,
  path: string,
  options?: { body?: unknown; formData?: FormData; options?: RequestOptions },
) => Promise<unknown>;

/**
 * Client for asset management endpoints.
 */
export class AssetClient {
  constructor(private readonly _request: RequestFn) {}

  /** Upload an asset file. */
  async upload(file: Blob | FormData, options?: RequestOptions): Promise<AssetUploadResult> {
    const form = file instanceof FormData ? file : (() => { const f = new FormData(); f.append('file', file); return f; })();
    return this._request('POST', '/api/assets/upload', { formData: form, options }) as Promise<AssetUploadResult>;
  }

  /** List all assets. */
  async list(options?: RequestOptions): Promise<AssetInfo[]> {
    return this._request('GET', '/api/assets', { options }) as Promise<AssetInfo[]>;
  }

  /** Get asset details by ID. */
  async get(assetId: string, options?: RequestOptions): Promise<AssetInfo> {
    return this._request('GET', `/api/assets/${assetId}`, { options }) as Promise<AssetInfo>;
  }

  /** Delete an asset. */
  async delete(assetId: string, options?: RequestOptions): Promise<void> {
    await this._request('DELETE', `/api/assets/${assetId}`, { options });
  }

  /** Download an asset (returns the raw Response for streaming). */
  async download(assetId: string, options?: RequestOptions): Promise<Response> {
    return this._request('GET', `/api/assets/${assetId}/download`, { options }) as Promise<Response>;
  }
}
