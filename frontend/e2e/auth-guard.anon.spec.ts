import { test, expect } from "@playwright/test";

import { loginThroughUi, registerThroughUi, uniqueIdentity } from "./helpers";

/**
 * The regression net for the trust boundary.
 *
 * Before this existed, every dashboard page rendered for an anonymous visitor.
 * These tests run with an explicitly empty storage state — see the `anonymous`
 * project in playwright.config.ts — so they cannot accidentally inherit the
 * session the setup project banks.
 */
test.describe("anonymous visitors", () => {
  for (const route of ["/", "/capture", "/settings", "/command-center", "/assets", "/vision"]) {
    test(`are redirected away from ${route}`, async ({ page }) => {
      await page.goto(route);
      await expect(page).toHaveURL(/\/login/);
      await expect(page.getByRole("heading", { name: /sign in/i })).toBeVisible();
    });
  }

  test("do not see protected content before the redirect", async ({ page }) => {
    // The middleware runs at the edge, so the dashboard HTML must never be sent.
    const response = await page.goto("/settings");
    const body = await response!.text();
    expect(body).not.toContain("Workspace Settings");
    expect(page.url()).toMatch(/\/login/);
  });

  test("are returned to the page they asked for after signing in", async ({ page }) => {
    const identity = uniqueIdentity("next");
    await registerThroughUi(page, identity);
    await page.evaluate(() => {
      localStorage.clear();
      document.cookie = "vaf_session=; path=/; max-age=0";
    });

    await page.goto("/assets");
    await expect(page).toHaveURL(/\/login\?next=%2Fassets|\/login\?next=\/assets/);

    await page.locator("#email").fill(identity.email);
    await page.locator("#password").fill(identity.password);
    await page.getByRole("button", { name: /sign in/i }).click();

    await expect(page).toHaveURL(/\/assets/, { timeout: 30_000 });
  });

  test("a wrong password is refused without leaking backend detail", async ({ page }) => {
    await loginThroughUi(page, "nobody-e2e@example.com", "definitely-wrong");
    await expect(page.getByText(/invalid email or password/i)).toBeVisible();
    await expect(page).toHaveURL(/\/login/);
  });

  test("the login page itself stays reachable", async ({ page }) => {
    await page.goto("/login");
    await expect(page).toHaveURL(/\/login$/);
    await expect(page.locator("#email")).toBeVisible();
  });
});

test.describe("registration", () => {
  test("creates a workspace and lands inside the console", async ({ page }) => {
    const identity = uniqueIdentity("reg");
    await registerThroughUi(page, identity);
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible({
      timeout: 30_000,
    });
  });
});
