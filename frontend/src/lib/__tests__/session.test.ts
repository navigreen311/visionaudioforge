import { describe, it, expect, beforeEach } from "vitest";

import {
  ACCESS_TOKEN_KEY,
  REFRESH_TOKEN_KEY,
  WORKSPACE_ID_KEY,
  clearSession,
  decodeJwt,
  isTokenExpired,
  persistSession,
  persistWorkspaceId,
} from "../session";

/**
 * The session module decides whether the console believes it is signed in.
 * Every branch here has a failure mode that is silent in the browser: a token
 * treated as valid past its expiry sends the user into a wall of 401s, and one
 * treated as expired when it is not signs them out mid-task.
 */

function makeToken(payload: Record<string, unknown>): string {
  const encode = (value: unknown) =>
    Buffer.from(JSON.stringify(value)).toString("base64url");
  return `${encode({ alg: "HS256", typ: "JWT" })}.${encode(payload)}.signature`;
}

beforeEach(() => {
  localStorage.clear();
});

describe("decodeJwt", () => {
  it("reads the payload of a well-formed token", () => {
    const token = makeToken({ sub: "user-1", workspace_id: "ws-1" });
    expect(decodeJwt(token)).toMatchObject({ sub: "user-1", workspace_id: "ws-1" });
  });

  it("returns null rather than throwing on a token it cannot read", () => {
    // Anything that throws here would take down whatever rendered it, which is
    // the whole console.
    expect(decodeJwt("not-a-jwt")).toBeNull();
    expect(decodeJwt("")).toBeNull();
    expect(decodeJwt("a.b")).toBeNull();
  });
});

describe("isTokenExpired", () => {
  const now = Math.floor(Date.now() / 1000);

  it("treats a future expiry as live", () => {
    expect(isTokenExpired(makeToken({ exp: now + 3_600 }))).toBe(false);
  });

  it("treats a past expiry as expired", () => {
    expect(isTokenExpired(makeToken({ exp: now - 60 }))).toBe(true);
  });

  it("treats a missing or unreadable token as expired", () => {
    // Failing closed matters more than failing open: the cost of a needless
    // re-login is a login form, the cost of the opposite is a dead session
    // that keeps making requests.
    expect(isTokenExpired(undefined)).toBe(true);
    expect(isTokenExpired(null)).toBe(true);
    expect(isTokenExpired("garbage")).toBe(true);
  });

  it("treats a token with no exp claim as expired", () => {
    expect(isTokenExpired(makeToken({ sub: "user-1" }))).toBe(true);
  });
});

describe("persistSession", () => {
  it("stores the tokens the rest of the console reads", () => {
    persistSession(makeToken({ exp: Math.floor(Date.now() / 1000) + 60 }), null, "refresh-1");

    expect(localStorage.getItem(ACCESS_TOKEN_KEY)).toBeTruthy();
    expect(localStorage.getItem(REFRESH_TOKEN_KEY)).toBe("refresh-1");
  });

  it("takes the workspace from the token when one is not supplied", () => {
    const token = makeToken({
      exp: Math.floor(Date.now() / 1000) + 60,
      workspace_id: "ws-from-token",
    });
    persistSession(token);

    expect(localStorage.getItem(WORKSPACE_ID_KEY)).toBe("ws-from-token");
  });
});

describe("persistWorkspaceId", () => {
  it("stores a workspace and clears it when given nothing", () => {
    persistWorkspaceId("ws-9");
    expect(localStorage.getItem(WORKSPACE_ID_KEY)).toBe("ws-9");

    persistWorkspaceId(null);
    expect(localStorage.getItem(WORKSPACE_ID_KEY)).toBeNull();
  });
});

describe("clearSession", () => {
  it("leaves nothing behind that would look like a session", () => {
    persistSession(makeToken({ exp: Math.floor(Date.now() / 1000) + 60 }), "ws-1", "refresh-1");

    clearSession();

    expect(localStorage.getItem(ACCESS_TOKEN_KEY)).toBeNull();
    expect(localStorage.getItem(REFRESH_TOKEN_KEY)).toBeNull();
    expect(localStorage.getItem(WORKSPACE_ID_KEY)).toBeNull();
  });
});
