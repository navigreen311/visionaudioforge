import { test, expect } from "@playwright/test";

import { authHeader, bankedSession } from "./helpers";

/**
 * Every shipped template must validate against the backend's own node registry.
 *
 * This is the guard for the defect that kept the pipeline journey `fixme`: the
 * templates carried no wiring between their nodes, so loading one and saving it
 * came back 422 with "missing required param 'image'". The nodes name real
 * ports — NormalizeNode takes `image` and returns `image`, the audio nodes each
 * need `sr`, which only `input_audio` produces — and the definitions now wire
 * them.
 *
 * Asserted here rather than only through the console because a template that
 * cannot validate is broken for every caller, including the SDKs, and the
 * console has a separate defect that would mask this one.
 */
test.describe("shipped pipeline templates", () => {
  test("every template validates against the node registry", async ({ request }) => {
    const listed = await request.get("/api/pipeline/templates", {
      headers: authHeader(),
    });
    expect(listed.status(), await listed.text()).toBe(200);

    const templates = (await listed.json()) as {
      key: string;
      definition: { nodes: unknown[]; edges: unknown[] };
    }[];

    expect(templates.length, "no templates were returned at all").toBeGreaterThan(0);

    const invalid: string[] = [];
    for (const template of templates) {
      // A template with no edges cannot be valid for any graph of more than one
      // node, and that was the shape of the original defect — check it directly
      // rather than inferring it from the validator's message.
      if (template.definition.nodes.length > 1) {
        expect(
          template.definition.edges.length,
          `template '${template.key}' ships ${template.definition.nodes.length} nodes and no edges`,
        ).toBeGreaterThan(0);
      }

      const validated = await request.post("/api/pipeline/validate", {
        headers: authHeader(),
        data: { definition: template.definition },
      });
      expect(validated.status(), await validated.text()).toBe(200);

      const result = (await validated.json()) as { valid: boolean; errors: string[] };
      if (!result.valid) {
        invalid.push(`${template.key}: ${result.errors.join("; ")}`);
      }
    }

    expect(invalid, `templates that do not validate:\n${invalid.join("\n")}`).toEqual([]);
  });

  // Both persistence endpoints used to construct the ORM object with a column
  // the model did not have — `description` — so POST /api/pipeline/create and
  // POST /api/pipeline/save each answered 500 and no pipeline could be saved
  // by any client. Migration 026 adds the column; this drives the API path
  // directly, with the template exactly as the server ships it.
  test("a template can be saved through the API exactly as shipped", async ({ request }) => {
    const listed = await request.get("/api/pipeline/templates", {
      headers: authHeader(),
    });
    const templates = (await listed.json()) as {
      key: string;
      definition: Record<string, unknown>;
    }[];
    const template = templates[0];

    const saved = await request.post("/api/pipeline/create", {
      headers: authHeader(),
      data: {
        name: `e2e-template-${template.key}-${Date.now()}`,
        definition: template.definition,
        workspace_id: bankedSession().workspaceId,
      },
    });

    expect(
      saved.status(),
      `saving template '${template.key}' as shipped returned ${saved.status()}: ${(
        await saved.text()
      ).slice(0, 400)}`,
    ).toBe(201);
  });
});
