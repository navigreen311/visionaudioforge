/**
 * Session storage primitives shared by the API client, the auth store and the
 * Next.js edge middleware.
 *
 * Deliberately dependency-free so `src/middleware.ts` can import it: middleware
 * runs on the edge runtime, where `window`, `localStorage` and most Node APIs
 * do not exist.
 *
 * Two places hold the session on purpose:
 *
 * - `localStorage` — read by the axios interceptor to build the
 *   `Authorization` header. Not visible to the server.
 * - a cookie — the only thing Next.js middleware can see, so it is what lets
 *   an anonymous visitor be bounced to `/login` *before* any dashboard HTML is
 *   streamed to them.
 *
 * The cookie is not a security control. It is readable by JavaScript and its
 * `exp` is checked without verifying the signature, because the edge runtime
 * has no business holding the JWT secret. The real trust boundary is the
 * backend's authentication middleware, which verifies every request.
 */

export const ACCESS_TOKEN_KEY = "access_token";
export const REFRESH_TOKEN_KEY = "refresh_token";
export const WORKSPACE_ID_KEY = "workspace_id";
export const SESSION_COOKIE = "vaf_session";

export interface JwtPayload {
  sub?: string;
  exp?: number;
  workspace_id?: string;
  [claim: string]: unknown;
}

/** Decode a JWT payload without verifying it. Returns null if unparseable. */
export function decodeJwt(token: string): JwtPayload | null {
  const segment = token.split(".")[1];
  if (!segment) return null;

  try {
    const base64 = segment.replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), "=");
    const json =
      typeof atob === "function"
        ? decodeURIComponent(
            atob(padded)
              .split("")
              .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
              .join(""),
          )
        : Buffer.from(padded, "base64").toString("utf-8");
    return JSON.parse(json) as JwtPayload;
  } catch {
    return null;
  }
}

/** True when the token is missing, malformed, or past its `exp`. */
export function isTokenExpired(token: string | undefined | null): boolean {
  if (!token) return true;
  const payload = decodeJwt(token);
  if (!payload || typeof payload.exp !== "number") return true;
  return payload.exp * 1000 <= Date.now();
}

function setCookie(name: string, value: string, maxAgeSeconds: number): void {
  const secure = typeof location !== "undefined" && location.protocol === "https:";
  document.cookie =
    `${name}=${encodeURIComponent(value)}; path=/; max-age=${maxAgeSeconds}; ` +
    `samesite=lax${secure ? "; secure" : ""}`;
}

function deleteCookie(name: string): void {
  document.cookie = `${name}=; path=/; max-age=0; samesite=lax`;
}

/**
 * Persist a freshly issued session.
 *
 * `workspaceId` comes from the authenticated session — the `workspace_id`
 * claim when the token carries one, otherwise the `user.workspace_id` the
 * server returned. It is never invented client-side.
 */
export function persistSession(
  token: string,
  workspaceId?: string | null,
  refreshToken?: string | null,
): void {
  if (typeof window === "undefined") return;

  localStorage.setItem(ACCESS_TOKEN_KEY, token);
  if (refreshToken) localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);

  const resolved = workspaceId ?? decodeJwt(token)?.workspace_id ?? null;
  if (resolved) {
    localStorage.setItem(WORKSPACE_ID_KEY, resolved);
  } else {
    localStorage.removeItem(WORKSPACE_ID_KEY);
  }

  const payload = decodeJwt(token);
  const maxAge = payload?.exp
    ? Math.max(0, Math.floor(payload.exp - Date.now() / 1000))
    : 60 * 30;
  setCookie(SESSION_COOKIE, token, maxAge);
}

/** Record the workspace once `/api/auth/me` has resolved it. */
export function persistWorkspaceId(workspaceId: string | null | undefined): void {
  if (typeof window === "undefined") return;
  if (workspaceId) {
    localStorage.setItem(WORKSPACE_ID_KEY, workspaceId);
  } else {
    localStorage.removeItem(WORKSPACE_ID_KEY);
  }
}

export function clearSession(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(WORKSPACE_ID_KEY);
  deleteCookie(SESSION_COOKIE);
}

/**
 * Attach the session token to a WebSocket URL.
 *
 * The browser `WebSocket` constructor cannot set request headers, so the token
 * has to ride in the query string. The backend honours `?token=` for websocket
 * handshakes only — see `docs/auth.md`.
 *
 * Call this at connect time, never at module scope: `localStorage` does not
 * exist during SSR, and a token read at import time would be stale by the time
 * the socket actually opens.
 *
 * Returns the URL unchanged when there is no session. The handshake is then
 * refused with close code 1008, which is the correct outcome — better a clean
 * rejection than a socket that looks connected and streams nothing.
 */
export function authenticatedWsUrl(url: string): string {
  const token = readAccessToken();
  if (!token) return url;

  const separator = url.includes("?") ? "&" : "?";
  return `${url}${separator}token=${encodeURIComponent(token)}`;
}

export function readAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

/**
 * The workspace of the current session, or null when there is no session.
 *
 * Order: the token's `workspace_id` claim first (it is signed, so it cannot be
 * edited in devtools), then the value stored from `/api/auth/me`. There is no
 * default — see `getWorkspaceId` in `lib/api.ts`.
 */
export function readWorkspaceId(): string | null {
  if (typeof window === "undefined") return null;

  const token = localStorage.getItem(ACCESS_TOKEN_KEY);
  if (token) {
    const claim = decodeJwt(token)?.workspace_id;
    if (typeof claim === "string" && claim) return claim;
  }
  return localStorage.getItem(WORKSPACE_ID_KEY);
}
