import { test as setup, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

import { AUTH_STATE, registerThroughUi, uniqueIdentity } from "./helpers";

/**
 * Bank a real session for the authenticated project.
 *
 * This registers through the browser rather than POSTing to the API, because
 * `persistSession` writes *both* a localStorage token and the `vaf_session`
 * cookie the edge middleware reads. A session minted by curl would satisfy the
 * backend and still be bounced by the console.
 *
 * Note what this does NOT do: it does not set AUTH_REQUIRED=false, and it does
 * not stub a token. If registration or login is broken, this fails and the whole
 * suite fails — which is correct. The point of the suite is to find that out.
 */
setup("create a real session", async ({ page }) => {
  const identity = uniqueIdentity("setup");
  await registerThroughUi(page, identity);

  // Prove the session is real before banking it.
  const token = await page.evaluate(() => localStorage.getItem("access_token"));
  expect(token, "registration did not persist an access token").toBeTruthy();

  fs.mkdirSync(path.dirname(AUTH_STATE), { recursive: true });
  await page.context().storageState({ path: AUTH_STATE });

  // Hand the identity to the specs that need to log in again as this user.
  fs.writeFileSync(
    path.join(path.dirname(AUTH_STATE), "identity.json"),
    JSON.stringify(identity, null, 2),
  );
});
