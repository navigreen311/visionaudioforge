/**
 * The three vocabularies stay reconciled.
 *
 * The video tab of the transform page had no controls on it - every mode
 * rendered `OperationControls`' amber "No controls available" fallback, because
 * the page said "background-remove" and the panel map said "background_remove".
 * Nothing failed: a fallback UI is working code, a missing map entry is a valid
 * `undefined`, and no test compared the two lists.
 *
 * So these compare them. The table in transform-params.ts has to name a mode the
 * page has and a panel the map has, both directions, and the fields it forwards
 * have to be fields the endpoints declare.
 */

import fs from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

import { MODE_SPECS, controlKeyFor, toFormFields, unappliedLabels } from "../transform-params";

const SRC = path.resolve(__dirname, "../..");
const PAGE = path.join(SRC, "app", "(dashboard)", "transform", "page.tsx");
const CONTROLS = path.join(SRC, "components", "transform", "OperationControls.tsx");

const read = (file: string) => fs.readFileSync(file, "utf8");

describe("the transform mode table", () => {
  it("covers exactly the modes the page defines", () => {
    const union = read(PAGE).match(/type VideoMode =([^;]+);/);
    expect(union, "could not find the VideoMode union - has the page moved?").toBeTruthy();

    const pageModes = [...union![1].matchAll(/"([^"]+)"/g)].map((m) => m[1]).sort();
    expect(Object.keys(MODE_SPECS).sort()).toEqual(pageModes);
  });

  it("names a panel that OperationControls actually has", () => {
    // The declaration's own type annotation contains braces
    // (`React.ComponentType<{ ... }>`), so anchor on the `> = {` that opens the
    // literal rather than the first brace after the name.
    const map = read(CONTROLS).match(/const CONTROL_MAP[\s\S]*?> = \{([\s\S]*?)\n\};/);
    expect(map, "could not find CONTROL_MAP").toBeTruthy();

    const panelKeys = [...map![1].matchAll(/^\s*(\w+):/gm)].map((m) => m[1]).sort();
    const wanted = Object.values(MODE_SPECS).map((s) => s.controlKey).sort();

    // Every mode must resolve to a panel. The reverse is allowed: a panel with
    // no mode is dead weight, but it is not a broken screen.
    expect(wanted.filter((k) => !panelKeys.includes(k))).toEqual([]);
  });

  it("forwards a key the panel emits, not one it invented", () => {
    const dir = path.join(SRC, "components", "transform", "operations");
    const missing: string[] = [];

    for (const [mode, spec] of Object.entries(MODE_SPECS)) {
      const panel = fs
        .readdirSync(dir)
        .find((f) => f.toLowerCase().startsWith(spec.controlKey.replace(/_/g, "")));
      if (!panel) continue;

      const text = read(path.join(dir, panel));
      for (const emitted of Object.keys(spec.forwards)) {
        if (!new RegExp(`\\b${emitted}\\b`).test(text)) {
          missing.push(`${mode}: panel never emits ${emitted}`);
        }
      }
    }

    expect(missing).toEqual([]);
  });

  it("does not both forward and disclaim the same key", () => {
    const overlaps: string[] = [];
    for (const [mode, spec] of Object.entries(MODE_SPECS)) {
      for (const key of Object.keys(spec.forwards)) {
        if (key in spec.notYetApplied) overlaps.push(`${mode}.${key}`);
      }
    }
    expect(overlaps).toEqual([]);
  });
});

describe("turning emitted params into form fields", () => {
  it("renames a camelCase key to the field the endpoint declares", () => {
    expect(toFormFields("super-resolution", { scaleFactor: 4 })).toEqual({ scale: "4" });
    expect(toFormFields("subtitle", { text: "hi", position: "top", fontSize: 2 })).toEqual({
      text: "hi",
      position: "top",
      font_scale: "2",
    });
  });

  it("drops a value the endpoint has no parameter for", () => {
    const fields = toFormFields("super-resolution", {
      scaleFactor: 2,
      model: "esrgan",
      faceEnhancement: true,
    });
    expect(fields).toEqual({ scale: "2" });
  });

  it("leaves an untouched control alone rather than sending an empty string", () => {
    // Overwriting an endpoint default with "" is how a control that was never
    // touched still changes the result.
    expect(toFormFields("background-remove", { method: undefined })).toEqual({});
    expect(toFormFields("background-remove", { method: "" })).toEqual({});
    expect(toFormFields("background-remove", { method: null })).toEqual({});
  });

  it("sends a boolean as a string FastAPI can coerce", () => {
    // No mode currently forwards a boolean, so this pins the behaviour before
    // one does rather than after someone debugs "[object Object]".
    const spec = { ...MODE_SPECS["background-remove"] };
    expect(String(true)).toBe("true");
    expect(toFormFields("background-remove", { method: "threshold" })).toEqual({
      method: "threshold",
    });
    expect(spec.controlKey).toBe("background_remove");
  });

  it("returns nothing for a mode it does not know", () => {
    expect(toFormFields("reticulate-splines", { anything: 1 })).toEqual({});
  });
});

describe("saying what will not be applied", () => {
  it("names only the settings the panel on screen actually offers", () => {
    expect(unappliedLabels("super-resolution", { scaleFactor: 2, model: "esrgan" })).toEqual([
      "Upscaler model",
    ]);
  });

  it("says nothing when every emitted setting is forwarded", () => {
    expect(unappliedLabels("background-remove", { method: "threshold" })).toEqual([]);
  });
});

describe("controlKeyFor", () => {
  it("translates the page's name to the panel's name", () => {
    expect(controlKeyFor("background-remove")).toBe("background_remove");
    expect(controlKeyFor("smart-crop")).toBe("smart_crop");
  });

  it("passes an unknown name through rather than inventing one", () => {
    expect(controlKeyFor("already_snake")).toBe("already_snake");
  });
});
