import type {
  SearchQuery,
  SearchResult,
  SearchIndexRequest,
  SearchStats,
  RequestOptions,
} from './types';

type RequestFn = (
  method: string,
  path: string,
  options?: { body?: unknown; formData?: FormData; options?: RequestOptions },
) => Promise<unknown>;

/**
 * Client for cross-modal search endpoints.
 */
export class SearchClient {
  constructor(private readonly _request: RequestFn) {}

  /** Execute a cross-modal search query. */
  async query(query: SearchQuery, options?: RequestOptions): Promise<SearchResult> {
    return this._request('POST', '/api/search/query', { body: query, options }) as Promise<SearchResult>;
  }

  /** Index items for search. */
  async index(request: SearchIndexRequest, options?: RequestOptions): Promise<{ indexed: number }> {
    return this._request('POST', '/api/search/index', { body: request, options }) as Promise<{ indexed: number }>;
  }

  /** Find similar items to a given item. */
  async similar(itemId: string, topK = 10, options?: RequestOptions): Promise<SearchResult> {
    return this._request('POST', '/api/search/query', {
      body: { query: itemId, top_k: topK, mode: 'similar' },
      options,
    }) as Promise<SearchResult>;
  }

  /** Get search index statistics. */
  async stats(options?: RequestOptions): Promise<SearchStats> {
    return this._request('GET', '/api/search/stats', { options }) as Promise<SearchStats>;
  }
}
