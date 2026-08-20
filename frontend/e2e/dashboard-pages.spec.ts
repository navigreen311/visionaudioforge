import { test, expect, type Page, type Request, type Response } from "@playwright/test";

/**
 * Every dashboard page, opened in a browser against the real API.
 *
 * The suite covered 13 of 28 pages, and every defect found in the last round was
 * on one of the 15 it did not:
 *
 *  - the transform page rendered "No controls available for operation
 *    background-remove" on every video mode, because the page names modes in
 *    kebab-case and the panel map is keyed snake_case
 *  - the audio augmentation studio sent six step names the server rejected, so
 *    every augmentation came back 500
 *  - the alerts Incidents tab rendered three invented incidents from a
 *    `MOCK_INCIDENTS` constant
 *
 * None of these is subtle. All three are visible within a second of opening the
 * page. They survived because nothing opened the page.
 *
 * So this is deliberately shallow and total: visit all 28, and assert the three
 * things that are true of a working page regardless of what it does. Depth
 * belongs in the journey specs; this is the net that catches a screen nobody
 * looked at.
 */

/** Every route under (dashboard), with the heading it should show. */
const PAGES: Array<{ route: string; heading: RegExp }> = [
  { route: "/", heading: /dashboard/i },
  { route: "/agents", heading: /agent/i },
  { route: "/alerts", heading: /alert/i },
  { route: "/annotate", heading: /annotat/i },
  { route: "/assets", heading: /asset/i },
  { route: "/audio", heading: /audio/i },
  { route: "/capture", heading: /capture/i },
  { route: "/command-center", heading: /command/i },
  { route: "/developer", heading: /developer|api/i },
  { route: "/edge", heading: /edge/i },
  { route: "/evaluation", heading: /evaluat/i },
  { route: "/federated", heading: /federat/i },
  { route: "/investigate", heading: /investigat/i },
  { route: "/knowledge-graph", heading: /knowledge|graph/i },
  { route: "/marketplace", heading: /marketplace|plugin/i },
  { route: "/memory", heading: /memory/i },
  { route: "/observability", heading: /observab|telemetry|metric/i },
  { route: "/pipeline", heading: /pipeline/i },
  { route: "/profile", heading: /profile|account/i },
  { route: "/reviewops", heading: /review/i },
  { route: "/search", heading: /search/i },
  { route: "/settings", heading: /settings/i },
  { route: "/simulation", heading: /simulat/i },
  { route: "/train", heading: /train/i },
  { route: "/transform", heading: /transform/i },
  { route: "/validate", heading: /validat/i },
  { route: "/verticals", heading: /vertical|pack/i },
  { route: "/vision", heading: /vision/i },
];

/**
 * Text that means the page gave up.
 *
 * "No controls available for operation" is here because it is a real fallback a
 * real component renders - working code, valid output, and an empty screen. It
 * shipped that way on every transform mode.
 */
const FAILURE_TEXT =
  /application error|unhandled runtime error|something went wrong|failed to fetch|no controls available for operation/i;

interface PageWatch {
  serverErrors: string[];
  pageErrors: string[];
  apiCalls: string[];
}

function watch(page: Page): PageWatch {
  const w: PageWatch = { serverErrors: [], pageErrors: [], apiCalls: [] };

  page.on("response", (response: Response) => {
    const url = response.url();
    if (!url.includes("/api/")) return;
    if (response.status() >= 500) {
      w.serverErrors.push(`${response.status()} ${url}`);
    }
  });

  page.on("request", (request: Request) => {
    if (request.url().includes("/api/")) w.apiCalls.push(request.url());
  });

  page.on("pageerror", (err) => w.pageErrors.push(err.message));

  return w;
}

for (const { route, heading } of PAGES) {
  test(`${route} renders, calls its API, and raises nothing`, async ({ page }) => {
    const w = watch(page);

    const response = await page.goto(route);
    expect(response?.status(), `${route} returned ${response?.status()}`).toBeLessThan(400);
    await expect(page, `${route} bounced to login`).not.toHaveURL(/\/login/);

    await expect(
      page.getByRole("heading", { name: heading }).first(),
      `${route} has no heading matching ${heading}`,
    ).toBeVisible({ timeout: 15_000 });

    // Give client-side fetches a moment to land before judging them.
    await page.waitForLoadState("networkidle").catch(() => {});

    await expect(
      page.getByText(FAILURE_TEXT),
      `${route} rendered a failure state`,
    ).toHaveCount(0);

    expect(w.pageErrors, `${route} threw: ${w.pageErrors.join("; ")}`).toEqual([]);
    expect(
      w.serverErrors,
      `${route} received a server error: ${w.serverErrors.join("; ")}`,
    ).toEqual([]);
  });
}

/**
 * A page that asks the API for nothing is either static or lying.
 *
 * `IncidentView` rendered three fabricated incidents from a constant and made no
 * request at all - which looks identical to a working page in a screenshot and
 * in every assertion above. Requiring a call is the cheapest way to tell a
 * screen backed by the platform from one backed by a literal.
 *
 * The exceptions are pages that genuinely have nothing to fetch until the
 * operator acts.
 */
const STATIC_BY_DESIGN = new Set(["/transform", "/annotate"]);

for (const { route } of PAGES) {
  if (STATIC_BY_DESIGN.has(route)) continue;

  test(`${route} gets its data from the API, not from a constant`, async ({ page }) => {
    const w = watch(page);
    await page.goto(route);
    await page.waitForLoadState("networkidle").catch(() => {});

    expect(
      w.apiCalls.length,
      `${route} made no API request. Either it renders mock data, or it belongs ` +
        "in STATIC_BY_DESIGN with a reason.",
    ).toBeGreaterThan(0);
  });
}
