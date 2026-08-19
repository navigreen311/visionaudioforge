import fs from "node:fs";
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

/**
 * The session banked by `auth.setup.ts`, read back for API-level specs.
 *
 * These specs assert on contracts the console cannot show — that a template
 * validates, that a providerless endpoint keeps saying so. They still use the
 * credential a real registration produced rather than minting one: the point of
 * this suite is that nothing here trusts a token it made up.
 */
export function bankedSession(): { token: string; workspaceId: string } {
  const state = JSON.parse(fs.readFileSync(AUTH_STATE, "utf8")) as {
    origins?: { localStorage?: { name: string; value: string }[] }[];
  };
  const entries = state.origins?.flatMap((o) => o.localStorage ?? []) ?? [];
  const read = (name: string) => entries.find((e) => e.name === name)?.value ?? "";

  const token = read("access_token");
  if (!token) {
    throw new Error(
      `no access_token in ${AUTH_STATE} — the setup project did not bank a session`,
    );
  }
  return { token, workspaceId: read("workspace_id") };
}

/** Authorization header for the banked session. */
export function authHeader(): Record<string, string> {
  return { Authorization: `Bearer ${bankedSession().token}` };
}

/**
 * A real mono 16 kHz WAV carrying a 440 Hz tone, built in-process.
 *
 * Silence is not enough: several analysers divide by the signal's energy and a
 * zero-filled buffer takes a different path from real audio, so a test built on
 * silence can pass while the endpoint is broken for anything a user uploads.
 */
export function wavBytes(seconds = 1, sampleRate = 16_000, hz = 440): Buffer {
  const frames = Math.floor(seconds * sampleRate);
  const data = Buffer.alloc(frames * 2);
  for (let i = 0; i < frames; i += 1) {
    data.writeInt16LE(Math.round(12_000 * Math.sin((2 * Math.PI * hz * i) / sampleRate)), i * 2);
  }

  const header = Buffer.alloc(44);
  header.write("RIFF", 0);
  header.writeUInt32LE(36 + data.length, 4);
  header.write("WAVE", 8);
  header.write("fmt ", 12);
  header.writeUInt32LE(16, 16); // PCM chunk size
  header.writeUInt16LE(1, 20); // PCM
  header.writeUInt16LE(1, 22); // mono
  header.writeUInt32LE(sampleRate, 24);
  header.writeUInt32LE(sampleRate * 2, 28); // byte rate
  header.writeUInt16LE(2, 32); // block align
  header.writeUInt16LE(16, 34); // bits per sample
  header.write("data", 36);
  header.writeUInt32LE(data.length, 40);

  return Buffer.concat([header, data]);
}
