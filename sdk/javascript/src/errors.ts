/**
 * Base error class for all VAF SDK errors.
 */
export class VAFError extends Error {
  public readonly statusCode: number;
  public readonly detail: unknown;

  constructor(message: string, statusCode: number, detail?: unknown) {
    super(message);
    this.name = 'VAFError';
    this.statusCode = statusCode;
    this.detail = detail;
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

/**
 * Thrown when authentication fails (401).
 */
export class AuthError extends VAFError {
  constructor(message = 'Authentication failed', detail?: unknown) {
    super(message, 401, detail);
    this.name = 'AuthError';
  }
}

/**
 * Thrown when a resource is not found (404).
 */
export class NotFoundError extends VAFError {
  constructor(message = 'Resource not found', detail?: unknown) {
    super(message, 404, detail);
    this.name = 'NotFoundError';
  }
}

/**
 * Thrown when request validation fails (422).
 */
export class ValidationError extends VAFError {
  constructor(message = 'Validation error', detail?: unknown) {
    super(message, 422, detail);
    this.name = 'ValidationError';
  }
}

/**
 * Thrown when a server error occurs (500+).
 */
export class ServerError extends VAFError {
  constructor(message = 'Internal server error', detail?: unknown) {
    super(message, 500, detail);
    this.name = 'ServerError';
  }
}

/**
 * Maps an HTTP status code and response body to the appropriate error class.
 */
export function mapError(status: number, body: unknown): VAFError {
  const message =
    typeof body === 'object' && body !== null && 'detail' in body
      ? String((body as Record<string, unknown>).detail)
      : `Request failed with status ${status}`;

  if (status === 401 || status === 403) return new AuthError(message, body);
  if (status === 404) return new NotFoundError(message, body);
  if (status === 422) return new ValidationError(message, body);
  if (status >= 500) return new ServerError(message, body);
  return new VAFError(message, status, body);
}
