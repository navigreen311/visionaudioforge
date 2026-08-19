import { expect, type Page } from "@playwright/test";

export const AUTH_STATE = "e2e/.auth/user.json";

/** A password that satisfies whatever the backend's policy turns out to be. */
export const TEST_PASSWORD = "E2ePassw0rd!2026";

/**
 * A unique identity per run.
 *
 * Registration creates a workspace, and a workspace that already exists makes
 * the second run of the suite fail for a reason that has nothing to do with the
 * code under test. Uniqueness is cheap; debugging a stale fixture is not.
 */
/**
 * `example.com` rather than a `.test` / `.local` domain: the backend validates
 * with `pydantic[email]`, which rejects IANA special-use TLDs outright ("the
 * part after the @-sign is a special-use or reserved name"). A fixture that
 * fails validation looks exactly like a broken registration form.
 */
export function uniqueIdentity(tag = "e2e") {
  const stamp = `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 7)}`;
  return {
    email: `${tag}-${stamp}@example.com`,
    password: TEST_PASSWORD,
    workspace: `${tag}-${stamp}`,
  };
}

/** Register through the real form and land inside the console. */
export async function registerThroughUi(
  page: Page,
  identity: ReturnType<typeof uniqueIdentity>,
) {
  await page.goto("/register");
  await page.locator("#email").fill(identity.email);
  await page.locator("#password").fill(identity.password);
  await page.locator("#confirmPassword").fill(identity.password);
  await page.locator("#workspace").fill(identity.workspace);
  await page.getByRole("button", { name: /create|register|sign up/i }).click();

  // The console is anything that is not the way in. Asserting on "not /register"
  // rather than a specific landing page keeps this helper working if the
  // post-registration destination changes.
  await expect(page).not.toHaveURL(/\/(register|login)/, { timeout: 30_000 });
}

/** Sign in through the real form. */
export async function loginThroughUi(page: Page, email: string, password: string) {
  await page.goto("/login");
  await page.locator("#email").fill(email);
  await page.locator("#password").fill(password);
  await page.getByRole("button", { name: /sign in|log in|login/i }).click();
}

/**
 * A real 32x32 PNG, built in-process so the suite carries no binary fixtures.
 *
 * Big enough to decode: a 16x16 placeholder satisfied an upload, which only
 * stores bytes, but OpenCV refused it with "Invalid image file" when the vision
 * endpoint actually tried to read it.
 *
 * One unbroken string on purpose. Splitting the base64 across concatenated
 * lines corrupted it into a libpng "IDAT: CRC error" that looked exactly like a
 * broken endpoint.
 */
export function pngBytes(): Buffer {
  // prettier-ignore
  return Buffer.from("iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAIAAAD8GO2jAAAAhklEQVRIDbXBMQEAAAjDsNb5nIMBODhI5Jk8k2fyTJ7JM3kmz2RR4cQwkkWFE8NIFhVODCNZVDgxjGRR4cQwkkWFE8NIFhVODCNZVDgxjGRR4cQwkkWFE8NIFhVODCNZVDgxjGRR4cQwkkWFE8NIFhVODCNZVDgxjOSZPJNn8kyeyTN5Js8aPKwgIYMdLnoAAAAASUVORK5CYII=", "base64");
}
