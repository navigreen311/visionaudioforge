import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end configuration.
 *
 * The suite runs against a *running stack*, not a dev server started by
 * Playwright. That is deliberate: the console's job is to talk to the real
 * backend through nginx, and a `webServer` that only starts Next would test the
 * console against nothing. Bring the stack up with `scripts/e2e.sh`, or point
 * E2E_BASE_URL at one that is already up.
 *
 * Default port is 8080 rather than 80 because a developer machine usually has
 * something on 80 already; `scripts/e2e.sh` publishes nginx there to match.
 */
const baseURL = process.env.E2E_BASE_URL || "http://localhost:8080";

export default defineConfig({
  testDir: "./e2e",
  // Serial by default: these tests create workspaces, upload assets and run
  // pipelines against one shared backend. Parallel writes to a single tenant
  // make failures that reproduce only in CI.
  workers: 1,
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  timeout: 60_000,
  expect: { timeout: 15_000 },
  reporter: process.env.CI
    ? [["list"], ["html", { open: "never" }], ["github"]]
    : [["list"], ["html", { open: "never" }]],
  use: {
    baseURL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    // The stack is HTTP on localhost; the session cookie is set without
    // `secure` in that case (see lib/session.ts).
    ignoreHTTPSErrors: true,
  },
  projects: [
    // Registers a real user through the real form and banks the session.
    { name: "setup", testMatch: /auth\.setup\.ts/ },
    {
      name: "chromium",
      // Anonymous specs are run by their own project below; without this they
      // would also run here *with* a session, which is the opposite of the point.
      testIgnore: [/auth\.setup\.ts/, /.*\.anon\.spec\.ts/],
      use: { ...devices["Desktop Chrome"], storageState: "e2e/.auth/user.json" },
      dependencies: ["setup"],
    },
    // Anonymous journeys must not inherit the banked session.
    {
      name: "anonymous",
      testMatch: /.*\.anon\.spec\.ts/,
      use: { ...devices["Desktop Chrome"], storageState: { cookies: [], origins: [] } },
    },
  ],
});
