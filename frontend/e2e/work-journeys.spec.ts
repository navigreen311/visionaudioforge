import { test, expect, type Page } from "@playwright/test";

import { authHeader, bankedSession, pngBytes, wavBytes } from "./helpers";

/**
 * Journeys for the pages where a user does real work.
 *
 * The console suite already proves each page mounts without an error boundary.
 * That catches a crash and nothing else: a page that renders its empty state
 * forever passes it. These drive the actual task and assert the outcome the
 * operator sees - a result on screen, a row in a list - rather than the network
 * call that produced it, because a 200 that renders nothing is still a failure
 * for the person using it.
 */

/** Upload through the first file input on the page. */
async function upload(page: Page, name: string, mimeType: string, buffer: Buffer) {
  await page.locator("input[type='file']").first().setInputFiles({ name, mimeType, buffer });
}

/** Fill the first field that matches, tolerating label/placeholder differences. */
async function fillFirst(page: Page, patterns: RegExp[], value: string) {
  for (const pattern of patterns) {
    const byLabel = page.getByLabel(pattern);
    if (await byLabel.count()) {
      await byLabel.first().fill(value);
      return true;
    }
    const byPlaceholder = page.getByPlaceholder(pattern);
    if (await byPlaceholder.count()) {
      await byPlaceholder.first().fill(value);
      return true;
    }
  }
  return false;
}

test.describe("search", () => {
  // Text search is down in the deployed stack. POST /api/search/query answers
  // 500, and the container log gives the cause:
  //
  //   PermissionError: [Errno 13] Permission denied: '/home/appuser'
  //   at huggingface_hub/file_download.py -> os.makedirs
  //
  // The image runs as non-root `appuser` with no writable HOME, so the CLIP
  // weights cannot be fetched or cached and the embedding model never loads.
  // Same root cause as the audio failures below: caches that assume a writable
  // home directory in an image that does not give the runtime user one. The
  // fix is an env var (HF_HOME) and a writable path in the image, which this
  // workstream does not own.
  test("a query returns results or an explicit empty state", async ({ page }) => {
    await page.goto("/search");
    await expect(page.getByRole("heading", { name: /cross-modal search/i })).toBeVisible();

    // Addressed by its placeholder: the query box carries no label, and a
    // looser match picked up the filter sidebar's "Search..." field instead,
    // leaving the real query empty and the button disabled.
    await page.getByPlaceholder(/describe what you're looking for/i).fill("a person walking");

    const searchButton = page.getByRole("button", { name: /^search$/i }).first();
    await expect(searchButton, "the search button stayed disabled with a query typed").toBeEnabled();
    await searchButton.click();

    // Either results or a stated "no results" - what must not happen is the
    // console sitting on a spinner or showing nothing at all.
    await expect(
      page.getByText(/no results|no matches|0 results|result/i).first(),
    ).toBeVisible({ timeout: 30_000 });
  });
});

test.describe("alerts", () => {
  test("a created rule appears in the rules list", async ({ page }) => {
    await page.goto("/alerts");
    await expect(page.getByRole("heading", { name: /alerts/i }).first()).toBeVisible();

    const ruleName = `e2e-rule-${Date.now().toString(36)}`;

    // Rules live behind a tab; the inbox is what loads first.
    // `Tabs` renders plain buttons inside <nav aria-label="Tabs">, not role="tab".
    await page.getByRole("button", { name: /^rules$/i }).click();

    const createButton = page.getByRole("button", { name: /create rule/i }).first();
    await expect(createButton, "no way to create an alert rule").toBeVisible({ timeout: 20_000 });
    await createButton.click();

    // Addressed by placeholder: RuleBuilder renders "Rule Name" as a bare
    // <label> with no htmlFor and the input has no id, so the two are not
    // associated and getByLabel cannot resolve it. Worth fixing for screen
    // readers, but that is a src change this workstream does not own.
    await page.getByPlaceholder(/high cpu \+ memory compound alert/i).fill(ruleName);
    await page.getByRole("button", { name: /^create$/i }).click();

    // The rule the operator just made must be visible to them afterwards.
    await expect(page.getByText(ruleName).first()).toBeVisible({ timeout: 30_000 });
  });
});

test.describe("investigate", () => {
  // Creating a case cannot work from the console. `handleCreateCase` uses the
  // bare `axios` module rather than the configured client in lib/api.ts, so it
  // carries no Authorization header - the interceptor that adds one lives on
  // that client, and the window.fetch patch in lib/authed-fetch.ts does not
  // cover XHR. It also posts to `API_BASE` (http://localhost:8000) directly
  // rather than through nginx, and sends a hardcoded
  // DEFAULT_WORKSPACE_ID = "00000000-0000-0000-0000-000000000001" instead of
  // the signed-in user's workspace.
  //
  //   POST /api/investigate/cases -> 401 Missing authentication
  //
  // So the case is never created and the list stays empty. Even authenticated,
  // it would write into a workspace the operator does not own. The fix is in
  // app/(dashboard)/investigate/page.tsx, which this workstream does not own.
  test("a case can be created and evidence attached to it", async ({ page }) => {
    await page.goto("/investigate");

    const caseName = `e2e-case-${Date.now().toString(36)}`;
    const createButton = page.getByRole("button", { name: /^new case$/i }).first();
    await expect(createButton, "no way to open a case").toBeVisible({ timeout: 20_000 });
    await createButton.click();

    await page.getByPlaceholder(/intrusion investigation/i).fill(caseName);
    await page.getByRole("button", { name: /^create case$/i }).click();

    await expect(page.getByText(caseName).first()).toBeVisible({ timeout: 30_000 });
  });
});

test.describe("train", () => {
  test("the registry lists models, or says it has none", async ({ page }) => {
    await page.goto("/train");
    await expect(page.getByRole("heading", { name: /train/i }).first()).toBeVisible();

    // Registry/experiments/datasets live behind tabs on this page.
    const registryTab = page.getByRole("tab", { name: /registry|models/i }).first();
    if (await registryTab.count()) {
      await registryTab.click();
    }

    await expect(
      page.getByText(/no models|no registered|version|accuracy|registered/i).first(),
      "the registry rendered neither models nor an empty state",
    ).toBeVisible({ timeout: 30_000 });
  });
});

test.describe("annotate", () => {
  // This was fixme because the listing the studio depends on answered 500, for
  // a reason that had nothing to do with the client:
  //
  //   GET /api/annotate/assets?workspace_id=...&dataset_id=... -> 500
  //   asyncpg.exceptions.UndefinedFunctionError:
  //     could not identify an equality operator for type json
  //
  //   SELECT DISTINCT assets.type, ..., assets.metadata, ...
  //   FROM assets LEFT OUTER JOIN annotations ON ...
  //
  // `assets.metadata` is a `json` column, and PostgreSQL has no equality
  // operator for `json` - which SELECT DISTINCT requires to deduplicate rows.
  //
  // The route now asks the question directly with EXISTS: it returns each asset
  // once by construction and never compares a json value, so the DISTINCT that
  // needed the operator is gone.
  test("an asset in a dataset opens on the annotation canvas", async ({ page, request }) => {
    // The studio has no upload of its own: it annotates assets that already
    // belong to a dataset, so the dataset and its image are seeded through the
    // API with the same session the browser holds, and the annotating is done
    // through the UI.
    const workspaceId = bankedSession().workspaceId;

    const dataset = await request.post("/api/datasets", {
      headers: authHeader(),
      data: {
        name: `e2e-annotate-${Date.now().toString(36)}`,
        modality: "image",
        workspace_id: workspaceId,
      },
    });
    expect(dataset.status(), `seeding a dataset failed: ${await dataset.text()}`).toBeLessThan(300);
    const datasetId = ((await dataset.json()) as { id: string }).id;

    const uploaded = await request.post(`/api/datasets/${datasetId}/upload`, {
      headers: authHeader(),
      multipart: {
        files: { name: "e2e-annotate.png", mimeType: "image/png", buffer: pngBytes() },
      },
    });
    expect(uploaded.status(), `seeding the image failed: ${await uploaded.text()}`).toBeLessThan(300);

    await page.goto("/annotate");
    await expect(page.getByRole("heading", { name: /annotation studio/i })).toBeVisible();

    // The dataset picker is the second <select>: the first is the COCO/YOLO/VOC
    // export format, the third is the label vocabulary.
    const datasetPicker = page.locator("select").nth(1);
    await expect(datasetPicker, "no dataset picker on the annotation studio").toBeVisible({
      timeout: 20_000,
    });

    // It renders "Loading datasets..." first, so selecting immediately picks the
    // placeholder and loads nothing. Wait for the real options to arrive.
    await expect
      .poll(async () => (await datasetPicker.locator("option").allTextContents()).join(" "), {
        timeout: 20_000,
        message: "the dataset picker never finished loading",
      })
      .toContain("e2e-annotate");

    await datasetPicker.selectOption({ index: 1 });

    // Choosing a dataset only enables the button; loading is explicit.
    const loadAssets = page.getByRole("button", { name: /load assets/i });
    await expect(loadAssets, "Load Assets stayed disabled after picking a dataset").toBeEnabled({
      timeout: 20_000,
    });
    await loadAssets.click();

    // The strip lists the asset. Asserted by presence rather than visibility:
    // the filename sits in a scrollable thumbnail strip, so it can be attached
    // and rendered while off-screen.
    await expect(
      page.getByText(/e2e-annotate/i),
      "the studio listed no assets for a dataset that has one",
    ).not.toHaveCount(0, { timeout: 30_000 });

    await expect(
      page.locator("canvas").first(),
      "no annotation canvas rendered for a dataset that has an image",
    ).toBeVisible({ timeout: 30_000 });
  });
});

test.describe("audio", () => {
  // Every audio endpoint that decodes an upload is down in the deployed stack:
  //
  //   POST /api/audio/analyze    -> 400
  //   POST /api/transform/audio  -> 400
  //   POST /api/audio/translate  -> 400
  //   {"detail":"Could not decode audio file: cannot cache function '__o_fold':
  //    no locator available for file '.../librosa/core/notation.py'"}
  //
  // librosa's numba kernels are compiled with cache=True; numba writes that
  // cache beside the library, site-packages is not writable by the non-root
  // `appuser` the image runs as, and NUMBA_CACHE_DIR is unset, so it raises
  // instead of falling back. Verified inside the running container: with
  // NUMBA_CACHE_DIR pointed at a writable path, librosa decodes normally. The
  // fix is one env var in the image; this workstream owns no backend or Docker
  // file, so both journeys stay named rather than weakened.
  test("an uploaded clip comes back analysed", async ({ page }) => {
    await page.goto("/audio");
    await expect(page.getByRole("heading", { name: /audio analysis/i })).toBeVisible();

    await upload(page, "e2e-audio.wav", "audio/wav", wavBytes());
    await page.getByRole("button", { name: /analy[sz]e/i }).first().click();

    await expect(
      page.getByText(/duration|sample rate|spectrogram|mfcc|waveform/i).first(),
      "the analysis produced nothing the operator can read",
    ).toBeVisible({ timeout: 60_000 });
  });

  // The product defect this found is fixed: the studio built its operations as
  // `{ name, params }` while AudioTransformService reads `step.get("op")`, so
  // every transform the console sent arrived with no operation and failed with
  // 500 "Unknown transform op: ".
  //
  // The earlier version of this test could not reach a control because it was
  // driving the wrong component. `AudioTransformStudio` - the rich panel with
  // "Noise Reduction", "De-reverb" and collapsible sections - is imported with
  // `dynamic()` in app/(dashboard)/transform/page.tsx and never rendered. The
  // Audio tab renders an inline panel with its own mode buttons instead, so the
  // controls the old comment described are not on the page at all.
  //
  // This drives what the page really shows: pick the Audio tab, choose Denoise,
  // upload, and assert the endpoint answers.
  test("an audio transform returns processed audio", async ({ page }) => {
    await page.goto("/transform");
    await expect(page.getByRole("heading", { name: /transform studio/i })).toBeVisible();

    await page.getByRole("button", { name: "Audio", exact: true }).click();
    await page.getByRole("button", { name: "Denoise", exact: true }).click();

    await upload(page, "e2e-transform.wav", "audio/wav", wavBytes());

    const transformed = page.waitForResponse(
      (r) => r.url().includes("/api/transform/audio") && r.request().method() === "POST",
      { timeout: 90_000 },
    );

    await page.getByRole("button", { name: /transform audio/i }).click();

    const response = await transformed;
    expect(
      response.status(),
      `transform returned ${response.status()}: ${(await response.text()).slice(0, 300)}`,
    ).toBeLessThan(300);

    await expect(page.getByText(/unknown transform op|failed|error/i)).toHaveCount(0);
  });
});

test.describe("capture", () => {
  test("a capture session can be started and reports its state", async ({ page }) => {
    await page.goto("/capture");
    await expect(page.getByRole("heading", { name: /live capture/i })).toBeVisible();

    const start = page.getByRole("button", { name: /start|begin|connect/i }).first();
    await expect(start, "no control to start a capture session").toBeVisible({ timeout: 20_000 });
    await start.click();

    // Without a camera in CI the honest outcomes are "connected/live" or a
    // stated failure. A control that reports nothing at all is the defect.
    await expect(
      page.getByText(/live|connected|streaming|session|denied|unavailable|failed|error/i).first(),
    ).toBeVisible({ timeout: 30_000 });
  });
});
