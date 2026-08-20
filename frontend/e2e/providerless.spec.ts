import { test, expect } from "@playwright/test";

import { authHeader, bankedSession, wavBytes } from "./helpers";

/**
 * Three endpoints have no provider behind them: speech translation, outbound
 * email, and PDF report export. Each is expected to say so.
 *
 * The failure mode being guarded against is not an outage — it is the opposite.
 * An endpoint with no provider is one refactor away from returning something
 * plausible: an echoed transcript presented as a translation, a `sent: true`
 * for mail nobody received, a text file with a .pdf name. Each of those reads
 * as success to a caller and is worse than an honest refusal, because nothing
 * downstream can tell the difference.
 *
 * So these tests do not assert that the features work. They assert that each
 * endpoint keeps admitting it cannot do the job.
 */

test.describe("endpoints with no provider configured", () => {
  test("outbound email reports that it was not delivered", async ({ request }) => {
    const response = await request.post("/api/integrations/email/send", {
      headers: authHeader(),
      data: {
        to: "nobody@example.com",
        subject: "e2e providerless check",
        body: "This must not be reported as delivered.",
      },
    });

    expect(response.status(), await response.text()).toBe(200);
    const body = (await response.json()) as {
      sent: boolean;
      method?: string;
      note?: string;
    };

    // The whole point: a 200 here must not mean "delivered".
    expect(
      body.sent,
      "email reported sent: true with no SMTP or SendGrid configured",
    ).toBe(false);
    expect(`${body.method ?? ""} ${body.note ?? ""}`).toMatch(
      /stub|not configured|not delivered/i,
    );
  });

  test("PDF report export does not claim to have produced a PDF", async ({ request }) => {
    const created = await request.post("/api/investigate/cases", {
      headers: authHeader(),
      data: {
        name: `e2e-providerless-${Date.now()}`,
        description: "Case created to exercise report export.",
        workspace_id: bankedSession().workspaceId,
      },
    });
    expect(created.status(), await created.text()).toBeLessThan(300);
    const caseId = ((await created.json()) as { id: string }).id;

    const exported = await request.post(
      `/api/investigate/cases/${caseId}/report/export`,
      { headers: authHeader(), data: { format: "pdf" } },
    );

    expect(exported.status(), await exported.text()).toBe(200);

    // Whatever it returns, it must not masquerade as a PDF: no application/pdf
    // content type, and no %PDF- magic bytes.
    const contentType = exported.headers()["content-type"] ?? "";
    expect(
      contentType,
      `export announced ${contentType} for a format it does not implement`,
    ).not.toMatch(/application\/pdf/i);

    const body = await exported.text();
    expect(
      body.startsWith("%PDF-"),
      "export returned PDF magic bytes from the stub renderer",
    ).toBe(false);
  });

  // Speech translation is the third providerless endpoint. It decodes the
  // upload with librosa before it can report that no translation provider is
  // configured, and that decode used to fail inside the shipped container:
  //
  //   400 {"detail":"Could not decode audio file: cannot cache function
  //   '__o_fold': no locator available for file
  //   '/usr/local/lib/python3.11/site-packages/librosa/core/notation.py'"}
  //
  // The image ran as non-root `appuser` with no writable home and no
  // NUMBA_CACHE_DIR, so numba tried to cache beside a read-only site-packages
  // and raised. Every audio decode in the deployed stack was down, not just
  // this endpoint.
  //
  // It passes now, so it is a real test again rather than a fixme. Which
  // change fixed it is not something this file should overclaim: on the
  // pinned numba (0.67.0) the decode also succeeds with NUMBA_CACHE_DIR
  // unset, so the original error appears to have been resolved by a numba
  // upgrade rather than by the Dockerfile. backend/Dockerfile now gives
  // appuser a writable home and an explicit NUMBA_CACHE_DIR regardless,
  // which is what keeps a future numba from reaching for site-packages
  // again. If this ever reverts to failing, the cache path is the first
  // thing to check and scripts/smoke-stack.sh asserts it independently.
  test("speech translation reports that no provider is configured", async ({ request }) => {
    const response = await request.post("/api/audio/translate", {
      headers: authHeader(),
      multipart: {
        file: { name: "tone.wav", mimeType: "audio/wav", buffer: wavBytes() },
        source_lang: "en",
        target_lang: "es",
      },
    });

    expect(response.status(), await response.text()).toBe(200);
    const body = (await response.json()) as { note?: string; translation?: string };
    expect(
      body.note ?? "",
      "translation returned no note admitting the provider is absent",
    ).toMatch(/not configured|no provider|set translation_api_key/i);
  });
});
