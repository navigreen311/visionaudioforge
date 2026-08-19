/**
 * Attach the session token to bare `fetch` calls aimed at our own API.
 *
 * Why this exists
 * ---------------
 *
 * The axios client in `lib/api.ts` has an interceptor that adds
 * `Authorization: Bearer …` to every request. Most of the console does not use
 * it: there are 57 places that call `fetch("/api/…")` directly - the pipeline
 * builder's generate/templates/validate/create/run, cross-modal search, the
 * vertical pack catalogue, the agent switcher and conversation history,
 * annotation save, and more.
 *
 * Those were fine while the API was open. The moment authentication landed they
 * all started coming back 401, and because each one degrades quietly - an empty
 * template list, "Failed to load", a spinner that stops - the console looked
 * like a set of features that simply did not do much. The e2e suite found it by
 * clicking Templates and getting an empty panel.
 *
 * Rather than convert 57 call sites - each with its own `res.ok` handling, and
 * every new one free to forget again - this wraps `window.fetch` once. Same rule
 * as the axios interceptor, applied to the same origin's `/api` paths.
 *
 * Scope, deliberately narrow:
 * - only same-origin (or configured API base) requests whose path starts with
 *   `/api`, so third-party requests never see the token;
 * - never overwrites an Authorization header the caller set itself;
 * - a no-op on the server, where there is no `window` and no session.
 */

import { API_BASE_URL } from "@/lib/api";
import { readAccessToken } from "@/lib/session";

const INSTALLED = Symbol.for("vaf.authedFetchInstalled");

function isOurApi(url: string): boolean {
  if (url.startsWith("/api")) return true;
  if (API_BASE_URL && url.startsWith(`${API_BASE_URL}/api`)) return true;
  if (typeof window !== "undefined" && url.startsWith(window.location.origin)) {
    return url.slice(window.location.origin.length).startsWith("/api");
  }
  return false;
}

function requestUrl(input: RequestInfo | URL): string {
  if (typeof input === "string") return input;
  if (input instanceof URL) return input.toString();
  return input.url;
}

/** Idempotent: installing twice would double-wrap on every hot reload. */
export function installAuthedFetch(): void {
  if (typeof window === "undefined") return;

  const globalWithFlag = window as typeof window & { [INSTALLED]?: boolean };
  if (globalWithFlag[INSTALLED]) return;
  globalWithFlag[INSTALLED] = true;

  const original = window.fetch.bind(window);

  window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    if (!isOurApi(requestUrl(input))) return original(input, init);

    const token = readAccessToken();
    if (!token) return original(input, init);

    const headers = new Headers(init?.headers ?? (input instanceof Request ? input.headers : undefined));
    if (!headers.has("Authorization")) {
      headers.set("Authorization", `Bearer ${token}`);
    }

    return original(input, { ...init, headers });
  };
}
