import { test, expect } from "@playwright/test";

import { pngBytes } from "./helpers";

/**
 * The authenticated journeys.
 *
 * These run with the session banked by auth.setup.ts against a real backend, so
 * a failure here means the console and the API genuinely disagree — which is the
 * class of defect 25 mocked unit tests cannot see.
 */

test.describe("the console renders for a signed-in user", () => {
  const pages: Array<[string, string | RegExp]> = [
    ["/", "Dashboard"],
    ["/assets", "Media Asset Library"],
    ["/vision", "Vision Analysis"],
    ["/settings", "Settings"],
  ];

  for (const [route, heading] of pages) {
    test(`${route} shows its heading`, async ({ page }) => {
      await page.goto(route);
      await expect(page.getByRole("heading", { name: heading, level: 1 })).toBeVisible();
      await expect(page).not.toHaveURL(/\/login/);
    });
  }

  test("every sidebar destination loads without an error boundary", async ({ page }) => {
    await page.goto("/");
    const hrefs = await page
      .locator("nav a[href^='/']")
      .evaluateAll((links) =>
        Array.from(new Set(links.map((a) => (a as HTMLAnchorElement).getAttribute("href")!))),
      );
    expect(hrefs.length, "sidebar produced no links").toBeGreaterThan(10);

    for (const href of hrefs) {
      const response = await page.goto(href);
      expect(response?.status(), `${href} returned ${response?.status()}`).toBeLessThan(400);
      await expect(page).not.toHaveURL(/\/login/);
      // Next's error overlay and the App Router error boundary both render this.
      await expect(page.getByText(/application error|unhandled runtime error/i)).toHaveCount(0);
    }
  });
});

test.describe("the dashboard reports real numbers", () => {
  test("stats come from the API, not a hardcoded stub", async ({ page }) => {
    const statsCall = page.waitForResponse(
      (r) => r.url().includes("/api/dashboard/stats") && r.status() === 200,
    );
    await page.goto("/");
    const response = await statsCall;
    const body = await response.json();

    // The endpoint used to return a fixed shape of zeros with the docstring
    // "will be wired to real services later". Assert the contract, not a value:
    // a fresh workspace legitimately has zero assets.
    expect(body).toHaveProperty("total_assets");
    expect(body).toHaveProperty("active_streams");
    expect(Array.isArray(body.assets_history)).toBe(true);

    await expect(page.getByText("Total Assets")).toBeVisible();
    await expect(page.getByText("Active Streams")).toBeVisible();
  });

  test("the activity feed endpoint answers", async ({ page }) => {
    const activity = page.waitForResponse((r) => r.url().includes("/api/dashboard/activity"));
    await page.goto("/");
    expect((await activity).status()).toBe(200);
  });
});

test.describe("assets", () => {
  test("an uploaded image appears in the library", async ({ page }) => {
    await page.goto("/assets");

    // The file input lives inside the upload modal, so it has to be opened
    // first. Two buttons can open it -- the header action and the empty-state
    // call to action -- and which is present depends on whether this workspace
    // already has assets.
    await page.getByRole("button", { name: /upload asset/i }).first().click();

    const dialog = page.getByRole("dialog");

    // Scoped to the dialog: the page behind it renders its own drag-and-drop
    // zone with a second file input, and filling that one leaves the modal
    // empty -- which surfaces as its Upload button staying disabled.
    await dialog.locator("input[type='file']").first().setInputFiles({
      name: "e2e-fixture.png",
      mimeType: "image/png",
      buffer: pngBytes(),
    });

    // Selecting a file only queues it; the modal uploads on confirmation.
    await dialog.getByRole("button", { name: /^upload/i }).click();

    // Assert the outcome a user would see rather than the network call that
    // produced it: the modal closes only when every upload succeeded, and the
    // library refetches. This is what a 422 on the upload endpoint broke --
    // asset upload had never once worked from the console.
    await expect(dialog).toBeHidden({ timeout: 30_000 });
    await expect(page.getByText("e2e-fixture.png").first()).toBeVisible({
      timeout: 30_000,
    });
  });
});

test.describe("settings", () => {
  // These five tabs were 404ing against unmounted routers until recently. A test
  // here is what stops that regressing in silence.
  for (const tab of ["General", "API Keys", "Users", "Appearance", "Integrations"]) {
    test(`the ${tab} tab renders`, async ({ page }) => {
      await page.goto("/settings");
      await page.getByRole("button", { name: tab, exact: true }).click();
      await expect(page.getByText(/failed to load|something went wrong/i)).toHaveCount(0);
    });
  }
});
