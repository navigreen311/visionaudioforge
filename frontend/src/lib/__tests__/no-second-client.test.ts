import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";

/**
 * Two patterns must not come back.
 *
 * Both were removed from `lib/api.ts` rounds ago and survived everywhere else,
 * because nothing failed when a new file reintroduced them. That is the whole
 * reason this test exists: a rule that lives only in a reviewer's memory has to
 * be remembered on every new file, and 44 files proved it would not be.
 *
 * A grep is a blunt instrument and deliberately so — it costs nothing, it runs
 * on every commit, and it names the file.
 */

const SRC = path.join(__dirname, "..", "..");

/**
 * `lib/api.ts` is the one module allowed to name the host: it is where the
 * `NEXT_PUBLIC_API_URL ?? "http://localhost:8000"` default is documented, and
 * where the comment recording the removed nil-workspace constant lives.
 * Exempting it is the point of the rule, not a hole in it — every other file
 * gets the value from here.
 */
const ALLOWED = new Set([path.join(SRC, "lib", "api.ts")]);

function sourceFiles(dir: string): string[] {
  const found: string[] = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === "node_modules" || entry.name === "__tests__") continue;
      found.push(...sourceFiles(full));
    } else if (/\.tsx?$/.test(entry.name)) {
      found.push(full);
    }
  }
  return found;
}

function offenders(pattern: RegExp): string[] {
  return sourceFiles(SRC)
    .filter((file) => !ALLOWED.has(file))
    .filter((file) => pattern.test(fs.readFileSync(file, "utf8")))
    .map((file) => path.relative(SRC, file));
}

describe("one API client", () => {
  it("no file under src names the API host", () => {
    // A hardcoded host bypasses nginx: the deployed console is served from the
    // same origin as the API, so `localhost:8000` is cross-origin in the
    // browser and only resolves at all on a developer machine with the port
    // published. The base belongs in lib/api.ts, which reads it from the
    // environment and treats empty as "same origin".
    const found = offenders(/localhost:8000/);
    expect(
      found,
      `these files name the API host — import API_BASE_URL from "@/lib/api" ` +
        `or use a relative /api/... path:\n  ${found.join("\n  ")}`,
    ).toEqual([]);
  });

  it("no file under src picks a workspace for the user", () => {
    // The nil workspace is a tenant the signed-in user does not own.
    // TenantGuardMiddleware answers 403 to exactly that, so every one of these
    // was a page asking for someone else's data and getting refused. The
    // workspace comes from the session.
    const found = offenders(/00000000-0000-0000-0000-000000000001/);
    expect(
      found,
      `these files hardcode a workspace — use readWorkspaceId() from ` +
        `"@/lib/session", or omit it and let the token decide:\n  ${found.join("\n  ")}`,
    ).toEqual([]);
  });

  it("no file under src builds its own websocket host", () => {
    // Same rule, same reason: nginx proxies /ws on the console's own origin.
    const found = offenders(/ws:\/\/localhost/);
    expect(
      found,
      `these files name a websocket host — use wsBaseUrl() from "@/lib/api":\n  ${found.join("\n  ")}`,
    ).toEqual([]);
  });
});
