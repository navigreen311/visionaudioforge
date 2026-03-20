import type { AlertRule, AlertInfo, RequestOptions } from './types';

type RequestFn = (
  method: string,
  path: string,
  options?: { body?: unknown; formData?: FormData; options?: RequestOptions },
) => Promise<unknown>;

/**
 * Client for alert management endpoints.
 */
export class AlertClient {
  constructor(private readonly _request: RequestFn) {}

  /** List all alerts. */
  async listAlerts(options?: RequestOptions): Promise<AlertInfo[]> {
    return this._request('GET', '/api/alerts', { options }) as Promise<AlertInfo[]>;
  }

  /** Create a new alert rule. */
  async createRule(rule: AlertRule, options?: RequestOptions): Promise<AlertInfo> {
    return this._request('POST', '/api/alerts/rules', { body: rule, options }) as Promise<AlertInfo>;
  }

  /** Acknowledge an alert. */
  async acknowledge(alertId: string, options?: RequestOptions): Promise<AlertInfo> {
    return this._request('POST', `/api/alerts/${alertId}/acknowledge`, { options }) as Promise<AlertInfo>;
  }

  /** Resolve an alert. */
  async resolve(alertId: string, options?: RequestOptions): Promise<AlertInfo> {
    return this._request('POST', `/api/alerts/${alertId}/resolve`, { options }) as Promise<AlertInfo>;
  }
}
